from typing import Literal, Optional
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from app.service.agent.conversation_state import ConversationState
from app.service.agent.rag_retriever import RAGRetriever
from app.service.agent.retrieval_pipeline import SmartRetrievalPipeline
from app.service.vector_db import ChromaVectorStore
from app.service.agent.official_tools import (
    search_cases, 
    search_laws, 
    _search_cases_impl, 
    _search_laws_impl,
    CaseSearchInput, 
    LawSearchInput
)
from app.service.prompts.conversation_prompts import ConversationPrompts
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("legal_agent")


class LegalConversationAgent:
    def __init__(
        self,
        llm: ChatOpenAI,
        rag_retriever: Optional[RAGRetriever] = None,
        vector_db: Optional[ChromaVectorStore] = None,
        max_history: int = 10,
        enable_parallel: bool = True,
        use_ner: bool = True
    ):
        self.llm = llm
        self.rag_retriever = rag_retriever
        self.vector_db = vector_db
        self.max_history = max_history
        self.checkpointer = MemorySaver()
        self.tools = [search_cases, search_laws]
        self.llm_with_tools = llm.bind_tools(self.tools)
        self.enable_parallel = enable_parallel
        self.use_ner = use_ner
        
        if rag_retriever:
            self.retrieval_pipeline = SmartRetrievalPipeline(
                llm=llm,
                rag_retriever=rag_retriever,
                vector_store=vector_db,
                enable_parallel=enable_parallel,
                use_ner=use_ner
            )
            logger.info(f"智能检索管道初始化成功 - enable_parallel: {enable_parallel}, use_ner: {use_ner}")
        else:
            self.retrieval_pipeline = None
            logger.warning("RAG检索器未初始化，智能检索管道不可用")
        
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(ConversationState)

        builder.add_node("check_rag", self._check_rag_node)
        builder.add_node("retrieve", self._retrieve_node)
        builder.add_node("check_tools", self._check_tools_node)
        builder.add_node("call_tools", self._call_tools_node)
        builder.add_node("generate", self._generate_node)

        builder.add_edge(START, "check_rag")
        builder.add_conditional_edges(
            "check_rag",
            self._should_retrieve,
            {
                "retrieve": "retrieve",
                "check_tools": "check_tools"
            }
        )
        builder.add_edge("retrieve", "check_tools")
        builder.add_conditional_edges(
            "check_tools",
            self._should_use_tools,
            {
                "call_tools": "call_tools",
                "generate": "generate"
            }
        )
        builder.add_edge("call_tools", "generate")
        builder.add_edge("generate", END)

        return builder.compile(checkpointer=self.checkpointer)

    def _check_rag_node(self, state: ConversationState) -> ConversationState:
        return state

    def _should_retrieve(self, state: ConversationState) -> Literal["retrieve", "check_tools"]:
        if state.get("use_rag", False) and self.rag_retriever:
            return "retrieve"
        return "check_tools"

    def _check_tools_node(self, state: ConversationState) -> ConversationState:
        return state

    def _should_use_tools(self, state: ConversationState) -> Literal["call_tools", "generate"]:
        if state.get("enable_tools", False):
            return "call_tools"
        return "generate"

    async def _retrieve_node(self, state: ConversationState) -> ConversationState:
        if not self.rag_retriever:
            return {**state, "context": [], "retrieval_metadata": None}

        last_message = state["messages"][-1]
        query = last_message.content if isinstance(last_message, HumanMessage) else ""

        strategy = state.get("retrieval_strategy", "vector")
        enable_rerank = state.get("enable_rerank", False)
        use_rag = state.get("use_rag", False)
        top_k = 5

        conversation_history = state["messages"][:-1]

        if self.retrieval_pipeline:
            logger.info(f"使用智能检索管道 - query: {query[:100]}")
            
            documents, metadata = await self.retrieval_pipeline.process(
                query=query,
                conversation_history=conversation_history,
                use_rag=use_rag,
                retrieval_strategy=strategy,
                enable_rerank=enable_rerank,
                top_k=top_k
            )
            
            metadata_dict = {
                "original_query": metadata.original_query,
                "rewritten_query": metadata.rewritten_query,
                "intent": metadata.intent,
                "intent_confidence": metadata.intent_confidence,
                "rewrite_type": metadata.rewrite_type,
                "retrieval_skipped": metadata.retrieval_skipped,
                "skip_reason": metadata.skip_reason,
                "documents_count": metadata.documents_count,
                "retrieval_strategy": metadata.retrieval_strategy,
                "entities": metadata.entities,
                "pre_retrieval_used": metadata.pre_retrieval_used,
                "parallel_execution": metadata.parallel_execution,
                "total_time": metadata.total_time
            }
            
            logger.info(f"智能检索完成 - intent: {metadata.intent}, rewrite_type: {metadata.rewrite_type}, documents: {len(documents)}, parallel: {metadata.parallel_execution}, pre_retrieval_used: {metadata.pre_retrieval_used}")
            
            return {
                **state,
                "context": documents,
                "retrieval_metadata": metadata_dict
            }
        else:
            logger.info(f"使用传统检索 - query: {query[:100]}, strategy: {strategy}, enable_rerank: {enable_rerank}, top_k: {top_k}")

            documents = await self.rag_retriever.retrieve(
                query=query,
                strategy=strategy,
                top_k=top_k,
                enable_rerank=enable_rerank
            )

            logger.info(f"传统检索完成 - 检索到 {len(documents)} 个文档")
            return {
                **state,
                "context": documents,
                "retrieval_metadata": {
                    "original_query": query,
                    "rewritten_query": query,
                    "intent": "new_question",
                    "intent_confidence": 1.0,
                    "rewrite_type": "无需改写",
                    "retrieval_skipped": False,
                    "skip_reason": None,
                    "documents_count": len(documents),
                    "retrieval_strategy": strategy,
                    "entities": None,
                    "pre_retrieval_used": False,
                    "parallel_execution": False,
                    "total_time": 0.0
                }
            }

    async def _call_tools_node(self, state: ConversationState) -> ConversationState:
        last_message = state["messages"][-1]
        query = last_message.content if isinstance(last_message, HumanMessage) else ""

        logger.info(f"开始工具调用 - query: {query[:100]}")

        response = await self.llm_with_tools.ainvoke(state["messages"])

        tool_calls = response.tool_calls
        tool_results = {}

        if tool_calls:
            logger.info(f"检测到 {len(tool_calls)} 个工具调用")
            
            tool_decision_message = AIMessage(content=response.content, tool_calls=tool_calls)
            state["messages"].append(tool_decision_message)
            
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                logger.info(f"调用工具: {tool_name}, 参数: {tool_args}")

                try:
                    if tool_name == "search_cases":
                        validated_args = CaseSearchInput(**tool_args)
                        result = await _search_cases_impl(**validated_args.dict())
                    elif tool_name == "search_laws":
                        validated_args = LawSearchInput(**tool_args)
                        result = await _search_laws_impl(**validated_args.dict())
                    else:
                        result = f"未知工具: {tool_name}"

                    tool_results[tool_name] = result
                    logger.info(f"工具 {tool_name} 执行成功，结果长度: {len(result)}")

                    tool_message = ToolMessage(
                        content=result,
                        tool_call_id=tool_call["id"],
                        name=tool_name
                    )
                    state["messages"].append(tool_message)
                except Exception as e:
                    error_msg = f"工具 {tool_name} 执行失败: {str(e)}"
                    logger.error(error_msg)
                    tool_results[tool_name] = error_msg

            return {
                **state,
                "tool_calls": tool_calls,
                "tool_results": tool_results
            }
        else:
            logger.info("未检测到工具调用")
            return {**state, "tool_calls": [], "tool_results": {}}

    async def _generate_node(self, state: ConversationState) -> ConversationState:
        last_message = state["messages"][-1]
        query = last_message.content if isinstance(last_message, HumanMessage) else ""

        tool_results = state.get("tool_results", {})
        has_tool_results = bool(tool_results)

        if state.get("context") and len(state["context"]) > 0:
            context_text = ConversationPrompts.get_context_with_sources(state["context"])
            system_prompt = ConversationPrompts.RAG_SYSTEM_PROMPT
            user_prompt = ConversationPrompts.get_rag_user_prompt(query, context_text)
            messages = [AIMessage(content=system_prompt)] + state["messages"][:-1] + [HumanMessage(content=user_prompt)]
            llm_to_use = self.llm
        elif has_tool_results:
            system_prompt = """你是一个专业的法律AI助手。

你刚刚调用了官方检索工具获取了相关信息。请基于工具返回的结果为用户提供准确、有用的回答。

重要约束：
- 必须基于工具返回的结果回答问题
- 如果工具返回的结果为空或不相关，请明确说明
- 可以适当引用工具返回的案例或法规信息
- 保持回答的专业性和准确性"""
            messages = [AIMessage(content=system_prompt)] + state["messages"]
            llm_to_use = self.llm_with_tools
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
            llm_to_use = self.llm

        response = await llm_to_use.ainvoke(messages)

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
