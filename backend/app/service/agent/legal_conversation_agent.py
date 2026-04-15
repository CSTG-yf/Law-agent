from typing import Literal, Optional
import re
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from app.service.agent.conversation_state import ConversationState
from app.service.agent.rag_retriever import RAGRetriever
from app.service.agent.retrieval_pipeline import SmartRetrievalPipeline
from app.service.vector_db import ChromaVectorStore
from app.core.config import settings
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
    LAW_KEYWORD_MAPPING = [
        (r"道路交通事故|交通事故|闯红灯|非机动车|机动车|逆行|酒驾|醉驾|无证驾驶|电瓶车|电动车|摩托车|违规带人|超员|载人", ["道路交通安全法"]),
        (r"劳动合同|辞退|辞退赔偿|解除劳动合同|加班|工资|社保|工伤", ["劳动合同法", "劳动法", "工伤保险条例"]),
        (r"借款|欠款|民间借贷|利息|逾期还款", ["民法典", "最高人民法院关于审理民间借贷案件适用法律若干问题的规定"]),
        (r"租赁|房屋租赁|退租|押金|租金", ["民法典", "商品房屋租赁管理办法"]),
        (r"婚姻|离婚|抚养权|抚养费|夫妻共同财产", ["民法典", "妇女权益保障法"]),
        (r"消费者|退款|退一赔三|假一赔三|产品质量", ["消费者权益保护法", "产品质量法"]),
        (r"侵权|人身损害|受伤|医疗费|误工费|残疾赔偿金", ["民法典", "最高人民法院关于审理人身损害赔偿案件适用法律若干问题的解释"]),
        (r"诈骗|盗窃|故意伤害|刑事责任", ["刑法", "刑事诉讼法"]),
        (r"公司|股东|工商|清算|法定代表人", ["公司法"]),
        (r"行政处罚|行政复议|行政诉讼|罚款|吊销", ["行政处罚法", "行政复议法", "行政诉讼法"])
    ]
    LAW_GENERIC_TERMS = {
        "处罚", "责任", "违法", "违规", "后果", "处理", "规定", "依据", "措施", "流程", "标准", "法律", "法律法规", "法律责任"
    }

    def __init__(
        self,
        llm: ChatOpenAI,
        rag_retriever: Optional[RAGRetriever] = None,
        vector_db: Optional[ChromaVectorStore] = None,
        max_history: int = None,
        enable_parallel: bool = True,
        use_ner: bool = True
    ):
        self.llm = llm
        self.rag_retriever = rag_retriever
        self.vector_db = vector_db
        self.max_history = max_history or settings.MAX_HISTORY_LENGTH
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
                "pre_retrieval_hint": metadata.pre_retrieval_hint,
                "parallel_execution": metadata.parallel_execution,
                "total_time": metadata.total_time
            }
            
            logger.info(f"智能检索完成 - intent: {metadata.intent}, rewrite_type: {metadata.rewrite_type}, documents: {len(documents)}, parallel: {metadata.parallel_execution}, pre_retrieval_hint: {metadata.pre_retrieval_hint}")
            
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
                    "pre_retrieval_hint": None,
                    "parallel_execution": False,
                    "total_time": 0.0
                }
            }

    def _normalize_law_keywords(self, query: str, keywords: list[str] | None) -> list[str]:
        def is_law_name(text: str) -> bool:
            return bool(re.search(r"(法|条例|规定|办法|解释|规则|细则|通则|章程)$", text)) or text in {
                "民法典", "刑法", "劳动法", "公司法", "行政处罚法", "行政复议法", "行政诉讼法", "消费者权益保护法"
            }

        named_laws = []
        seen_named = set()
        for keyword in keywords or []:
            text = (keyword or "").strip()
            if not text or text in self.LAW_GENERIC_TERMS:
                continue
            if len(text) <= 1:
                continue
            if is_law_name(text) and text not in seen_named:
                seen_named.add(text)
                named_laws.append(text)

        mapped_laws = []
        seen_mapped = set(named_laws)
        query_text = query or ""
        candidate_text = f"{query_text} {' '.join(keywords or [])}"
        for pattern, law_names in self.LAW_KEYWORD_MAPPING:
            if re.search(pattern, candidate_text):
                for law_name in law_names:
                    if law_name not in seen_mapped:
                        seen_mapped.add(law_name)
                        mapped_laws.append(law_name)

        normalized = (mapped_laws + named_laws)[:5]
        if normalized:
            logger.info(f"法规关键词规范化完成 - original: {keywords}, normalized: {normalized}")
            return normalized

        fallback = ["民法典"]
        logger.info(f"法规关键词规范化回退 - original: {keywords}, fallback: {fallback}")
        return fallback

    def _get_latest_user_query(self, messages: list[BaseMessage]) -> str:
        for message in reversed(messages):
            if isinstance(message, HumanMessage):
                return message.content
        return ""

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
                        normalized_tool_args = dict(tool_args)
                        normalized_tool_args["keywords"] = self._normalize_law_keywords(query, normalized_tool_args.get("keywords"))
                        logger.info(f"调用工具: {tool_name}, 规范化后参数: {normalized_tool_args}")
                        validated_args = LawSearchInput(**normalized_tool_args)
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
        query = self._get_latest_user_query(state["messages"])

        tool_results = state.get("tool_results", {})
        has_tool_results = bool(tool_results)

        if state.get("context") and len(state["context"]) > 0:
            context_text = ConversationPrompts.get_context_with_sources(state["context"])
            system_prompt = ConversationPrompts.RAG_SYSTEM_PROMPT
            user_prompt = ConversationPrompts.get_rag_user_prompt(query, context_text)
            messages = [AIMessage(content=system_prompt)] + state["messages"][:-1] + [HumanMessage(content=user_prompt)]
            llm_to_use = self.llm
        elif has_tool_results:
            tool_context_parts = []
            for tool_name, tool_result in tool_results.items():
                tool_context_parts.append(f"[{tool_name}]\n{tool_result}")
            tool_context = "\n\n".join(tool_context_parts)

            system_prompt = """你是一个专业的法律AI助手。

你已经拿到了法规检索、案例检索等工具结果。现在你的任务是：基于这些结果，直接生成一版最终答复，而不是把工具原始结果分段复述一遍。

回答要求：
- 先直接回答用户问题，给出结论
- 再把最相关的法律依据和案例启示自然融合进答案
- 不要先输出一段案例结果，再输出一段法规结果
- 不要机械复述工具返回的长列表
- 只保留与用户问题直接相关的信息
- 可以引用1到2个最相关案例的法院、案号、裁判日期
- 如果工具结果不足以支持确定结论，要明确说明局限
- 严禁编造工具结果中不存在的法律条文、案例或处罚结论
- 语言要像最终答复，简洁、自然、专业"""
            user_prompt = f"""用户问题：{query}

工具检索结果：
{tool_context}

请基于以上检索结果，直接输出整合后的最终答复。"""
            messages = [AIMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            llm_to_use = self.llm
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
