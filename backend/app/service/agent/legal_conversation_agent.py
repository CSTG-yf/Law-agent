from typing import Literal, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from app.service.agent.conversation_state import ConversationState
from app.service.agent.rag_retriever import RAGRetriever
from app.service.prompts.conversation_prompts import ConversationPrompts
from app.core.config import settings


class LegalConversationAgent:
    def __init__(
        self,
        llm: ChatOpenAI,
        rag_retriever: Optional[RAGRetriever] = None,
        max_history: int = 10
    ):
        self.llm = llm
        self.rag_retriever = rag_retriever
        self.max_history = max_history
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(ConversationState)

        builder.add_node("check_rag", self._check_rag_node)
        builder.add_node("retrieve", self._retrieve_node)
        builder.add_node("generate", self._generate_node)

        builder.add_edge(START, "check_rag")
        builder.add_conditional_edges(
            "check_rag",
            self._should_retrieve,
            {
                "retrieve": "retrieve",
                "generate": "generate"
            }
        )
        builder.add_edge("retrieve", "generate")
        builder.add_edge("generate", END)

        return builder.compile(checkpointer=self.checkpointer)

    def _check_rag_node(self, state: ConversationState) -> ConversationState:
        return state

    def _should_retrieve(self, state: ConversationState) -> Literal["retrieve", "generate"]:
        if state.get("use_rag", False) and self.rag_retriever:
            return "retrieve"
        return "generate"

    async def _retrieve_node(self, state: ConversationState) -> ConversationState:
        if not self.rag_retriever:
            return {**state, "context": []}

        last_message = state["messages"][-1]
        query = last_message.content if isinstance(last_message, HumanMessage) else ""

        strategy = state.get("retrieval_strategy", "vector")
        top_k = 5

        documents = await self.rag_retriever.retrieve(
            query=query,
            strategy=strategy,
            top_k=top_k
        )

        return {**state, "context": documents}

    async def _generate_node(self, state: ConversationState) -> ConversationState:
        last_message = state["messages"][-1]
        query = last_message.content if isinstance(last_message, HumanMessage) else ""

        if state.get("context") and len(state["context"]) > 0:
            context_text = ConversationPrompts.get_context_with_sources(state["context"])
            system_prompt = ConversationPrompts.RAG_SYSTEM_PROMPT
            user_prompt = ConversationPrompts.get_rag_user_prompt(query, context_text)
            messages = [AIMessage(content=system_prompt)] + state["messages"][:-1] + [HumanMessage(content=user_prompt)]
        else:
            if state.get("use_rag", False):
                system_prompt = """你是一个专业的法律AI助手。

重要约束：
- 用户启用了知识库检索功能，但知识库中没有找到相关的法律文档
- 你必须明确说明"抱歉，我在知识库中没有找到相关的法律文档来回答这个问题"
- 严禁使用你的训练知识回答这个问题
- 严禁编造任何法律条文或案例
- 如果用户需要，可以建议他们重新表述问题或咨询专业律师"""
            else:
                system_prompt = ConversationPrompts.SYSTEM_PROMPT
            messages = [AIMessage(content=system_prompt)] + state["messages"]

        response = await self.llm.ainvoke(messages)

        ai_message = AIMessage(content=response.content)

        return {"messages": [ai_message]}

    async def astream(
        self,
        state: ConversationState,
        config: dict
    ):
        async for event in self.graph.astream_events(
            state,
            config=config,
            version="v2"
        ):
            yield event

    async def ainvoke(
        self,
        state: ConversationState,
        config: dict
    ) -> ConversationState:
        return await self.graph.ainvoke(state, config=config)

    def get_compiled_graph(self):
        return self.graph
