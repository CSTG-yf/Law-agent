from typing import Literal, Optional, List
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
import asyncio

from app.core.config import settings
from app.core.logger import get_logger
from .state import CyberJudgeState, IntentInfo, ExtractedFacts, CaseInfo, LawInfo, LawDetail, FileInfo, AnalysisResult
from .intent_analyzer import IntentAnalyzer, IntentResult
from .fact_extractor import FactExtractor
from .tools import CyberJudgeTools
from .prompts import CyberJudgePrompts

logger = get_logger("cyber_judge_agent")


class CyberJudgeAgent:
    """赛博判官Agent核心"""
    
    def __init__(
        self,
        llm: ChatOpenAI,
        max_history: int = None
    ):
        self.llm = llm
        self.max_history = max_history or settings.MAX_HISTORY_LENGTH
        self.checkpointer = MemorySaver()
        
        self.intent_analyzer = IntentAnalyzer(llm)
        self.fact_extractor = FactExtractor(llm)
        
        self.graph = self._build_graph()
        
        logger.info("赛博判官Agent初始化完成")

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(CyberJudgeState)

        builder.add_node("analyze_intent", self._analyze_intent_node)
        builder.add_node("extract_facts", self._extract_facts_node)
        builder.add_node("generate_keywords", self._generate_keywords_node)
        builder.add_node("search_tools", self._search_tools_node)
        builder.add_node("generate_response", self._generate_response_node)

        builder.add_edge(START, "analyze_intent")
        builder.add_conditional_edges(
            "analyze_intent",
            self._should_extract_facts,
            {
                "extract_facts": "extract_facts",
                "generate_keywords": "generate_keywords"
            }
        )
        builder.add_edge("extract_facts", "generate_keywords")
        builder.add_edge("generate_keywords", "search_tools")
        builder.add_conditional_edges(
            "search_tools",
            self._should_search_more,
            {
                "search_tools": "search_tools",
                "generate_response": "generate_response"
            }
        )
        builder.add_edge("generate_response", END)

        return builder.compile(checkpointer=self.checkpointer)

    async def _analyze_intent_node(self, state: CyberJudgeState) -> dict:
        last_message = state["messages"][-1]
        query = last_message.content if isinstance(last_message, HumanMessage) else ""
        
        has_files = bool(state.get("uploaded_files"))
        conversation_history = state["messages"][:-1]
        
        result = await self.intent_analyzer.analyze(
            current_query=query,
            conversation_history=conversation_history,
            extracted_facts=state.get("extracted_facts"),
            has_files=has_files
        )
        
        intent_info = self.intent_analyzer.to_intent_info(result)
        
        logger.info(f"意图分析完成 - intent: {result.intent_type}, confidence: {result.confidence}")
        
        return {"intent_info": intent_info}

    def _should_extract_facts(self, state: CyberJudgeState) -> Literal["extract_facts", "generate_keywords"]:
        intent_info = state.get("intent_info")
        if not intent_info:
            return "generate_keywords"
        
        if intent_info.get("needs_file_analysis") and state.get("uploaded_files"):
            return "extract_facts"
        
        return "generate_keywords"

    async def _extract_facts_node(self, state: CyberJudgeState) -> dict:
        uploaded_files = state.get("uploaded_files", [])
        
        if not uploaded_files:
            return {"extracted_facts": None}
        
        all_facts = []
        for file_info in uploaded_files:
            if file_info.get("extracted_text"):
                facts = await self.fact_extractor.extract_from_text(file_info["extracted_text"])
                all_facts.append(facts)
        
        if all_facts:
            merged_facts = self._merge_facts(all_facts)
            logger.info(f"事实提取完成 - summary: {merged_facts.get('summary', 'N/A')}")
            return {"extracted_facts": merged_facts}
        
        return {"extracted_facts": None}

    async def _generate_keywords_node(self, state: CyberJudgeState) -> dict:
        last_message = state["messages"][-1]
        query = last_message.content if isinstance(last_message, HumanMessage) else ""
        
        case_keywords, law_keywords = await self.fact_extractor.generate_search_keywords(
            user_question=query,
            extracted_facts=state.get("extracted_facts")
        )
        
        logger.info(f"关键词生成完成 - case: {case_keywords}, law: {law_keywords}")
        
        return {
            "tool_calls": [{"case_keywords": case_keywords, "law_keywords": law_keywords}],
            "tool_results": {}
        }

    async def _search_tools_node(self, state: CyberJudgeState) -> dict:
        intent_info = state.get("intent_info")
        tool_results = state.get("tool_results", {})
        tool_calls = state.get("tool_calls", [])
        
        if not tool_calls:
            return {"tool_results": tool_results}
        
        keywords_info = tool_calls[-1] if tool_calls else {}
        case_keywords = keywords_info.get("case_keywords", [])
        law_keywords = keywords_info.get("law_keywords", [])
        
        related_cases = state.get("related_cases", [])
        related_laws = state.get("related_laws", [])
        law_details = state.get("law_details", [])
        
        tasks = []
        
        if intent_info and intent_info.get("needs_case_search") and case_keywords:
            logger.info(f"准备搜索案例 - keywords: {case_keywords}")
            tasks.append(("cases", CyberJudgeTools.search_cases(keywords=case_keywords, page_size=5)))
        
        if intent_info and intent_info.get("needs_law_search") and law_keywords:
            logger.info(f"准备搜索法规 - keywords: {law_keywords}")
            tasks.append(("laws", CyberJudgeTools.search_laws(keywords=law_keywords, page_size=5)))
        
        if tasks:
            results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
            
            for i, (task_type, _) in enumerate(tasks):
                result = results[i]
                if isinstance(result, Exception):
                    logger.error(f"工具调用失败 - type: {task_type}, error: {str(result)}")
                    continue
                
                if task_type == "cases":
                    related_cases = result
                elif task_type == "laws":
                    related_laws = result
        
        if intent_info and intent_info.get("needs_law_detail") and related_laws:
            law_ids = [law.get("law_id") for law in related_laws[:3] if law.get("law_id")]
            if law_ids:
                logger.info(f"准备获取法规详情 - law_ids: {law_ids}")
                law_details = await CyberJudgeTools.batch_get_law_details(law_ids, max_count=3)
        
        return {
            "related_cases": related_cases,
            "related_laws": related_laws,
            "law_details": law_details,
            "tool_results": {
                "case_count": len(related_cases),
                "law_count": len(related_laws),
                "detail_count": len(law_details)
            }
        }

    def _should_search_more(self, state: CyberJudgeState) -> Literal["search_tools", "generate_response"]:
        return "generate_response"

    async def _generate_response_node(self, state: CyberJudgeState) -> dict:
        last_message = state["messages"][-1]
        query = last_message.content if isinstance(last_message, HumanMessage) else ""
        
        intent_info = state.get("intent_info")
        extracted_facts = state.get("extracted_facts")
        related_cases = state.get("related_cases", [])
        related_laws = state.get("related_laws", [])
        law_details = state.get("law_details", [])
        
        intent_type = intent_info.get("intent_type", "legal_consultation") if intent_info else "legal_consultation"
        
        prompt = self._build_prompt(
            intent_type=intent_type,
            query=query,
            extracted_facts=extracted_facts,
            related_cases=related_cases,
            related_laws=related_laws,
            law_details=law_details
        )
        
        messages = [AIMessage(content=CyberJudgePrompts.SYSTEM_PROMPT)] + state["messages"]
        
        response = await self.llm.ainvoke(messages + [HumanMessage(content=prompt)])
        
        ai_message = AIMessage(content=response.content)
        
        analysis_result = self._build_analysis_result(
            intent_type=intent_type,
            content=response.content,
            related_cases=related_cases,
            related_laws=related_laws
        )
        
        logger.info(f"响应生成完成 - intent: {intent_type}, response_length: {len(response.content)}")
        
        return {
            "messages": [ai_message],
            "analysis_result": analysis_result
        }

    def _build_prompt(
        self,
        intent_type: str,
        query: str,
        extracted_facts: Optional[ExtractedFacts],
        related_cases: List[CaseInfo],
        related_laws: List[LawInfo],
        law_details: List[LawDetail]
    ) -> str:
        facts_text = CyberJudgePrompts.format_extracted_facts(extracted_facts)
        cases_text = CyberJudgePrompts.format_cases(related_cases)
        laws_text = CyberJudgePrompts.format_laws(related_laws)
        details_text = CyberJudgePrompts.format_law_details(law_details)
        
        if intent_type == "case_analysis":
            return CyberJudgePrompts.CASE_ANALYSIS_PROMPT.format(
                user_question=query,
                extracted_facts=facts_text,
                related_cases=cases_text
            )
        elif intent_type == "law_inquiry":
            return CyberJudgePrompts.LAW_ANALYSIS_PROMPT.format(
                user_question=query,
                related_laws=laws_text,
                law_details=details_text
            )
        elif intent_type == "rights_protection":
            return CyberJudgePrompts.RIGHTS_PROTECTION_PROMPT.format(
                user_question=query,
                extracted_facts=facts_text,
                legal_basis=laws_text + "\n\n" + details_text
            )
        elif intent_type == "compensation_calc":
            return CyberJudgePrompts.COMPENSATION_CALC_PROMPT.format(
                user_question=query,
                extracted_facts=facts_text,
                legal_basis=laws_text + "\n\n" + details_text
            )
        elif intent_type == "procedure_guidance":
            return CyberJudgePrompts.PROCEDURE_GUIDANCE_PROMPT.format(
                user_question=query,
                procedure_info=laws_text + "\n\n" + details_text
            )
        else:
            return CyberJudgePrompts.COMPREHENSIVE_ANALYSIS_PROMPT.format(
                user_question=query,
                extracted_facts=facts_text,
                related_cases=cases_text,
                related_laws=laws_text,
                law_details=details_text
            )

    def _merge_facts(self, facts_list: List[ExtractedFacts]) -> ExtractedFacts:
        merged = ExtractedFacts(
            parties=[],
            events=[],
            disputes=[],
            claims=[],
            key_dates=[],
            amounts=[],
            locations=[],
            summary=""
        )
        
        summaries = []
        for facts in facts_list:
            merged["parties"].extend(facts.get("parties", []))
            merged["events"].extend(facts.get("events", []))
            merged["disputes"].extend(facts.get("disputes", []))
            merged["claims"].extend(facts.get("claims", []))
            merged["key_dates"].extend(facts.get("key_dates", []))
            merged["amounts"].extend(facts.get("amounts", []))
            merged["locations"].extend(facts.get("locations", []))
            if facts.get("summary"):
                summaries.append(facts["summary"])
        
        merged["parties"] = list(set(merged["parties"]))
        merged["events"] = list(set(merged["events"]))
        merged["disputes"] = list(set(merged["disputes"]))
        merged["claims"] = list(set(merged["claims"]))
        merged["key_dates"] = list(set(merged["key_dates"]))
        merged["amounts"] = list(set(merged["amounts"]))
        merged["locations"] = list(set(merged["locations"]))
        merged["summary"] = "；".join(summaries) if summaries else ""
        
        return merged

    def _build_analysis_result(
        self,
        intent_type: str,
        content: str,
        related_cases: List[CaseInfo],
        related_laws: List[LawInfo]
    ) -> AnalysisResult:
        legal_basis = []
        for law in related_laws:
            if law.get("title"):
                legal_basis.append(law["title"])
        
        return AnalysisResult(
            legal_basis=legal_basis,
            risk_assessment="",
            suggestions=[],
            key_points=[]
        )

    async def astream(self, state: CyberJudgeState, config: dict):
        async for event in self.graph.astream_events(state, config=config, version="v2"):
            yield event

    async def ainvoke(self, state: CyberJudgeState, config: dict) -> CyberJudgeState:
        return await self.graph.ainvoke(state, config=config)

    def get_compiled_graph(self):
        return self.graph
