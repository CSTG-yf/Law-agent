from typing import Annotated, TypedDict, List, Optional, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class IntentInfo(TypedDict, total=False):
    intent_type: str
    confidence: float
    sub_intents: List[str]
    reasoning: str
    needs_case_search: bool
    needs_law_search: bool
    needs_law_detail: bool
    needs_file_analysis: bool


class CaseInfo(TypedDict, total=False):
    title: str
    case_number: str
    court: str
    judgement_date: str
    cause: str
    content: str
    case_type: str
    level_of_trial: str
    relevance_score: float


class LawInfo(TypedDict, total=False):
    title: str
    publisher: str
    publish_date: str
    active_date: str
    timeliness: str
    law_id: str
    level_name: str
    issued_no: str
    relevance_score: float


class LawDetail(TypedDict, total=False):
    title: str
    publisher: str
    publish_date: str
    active_date: str
    timeliness: str
    content: str
    law_id: str


class ExtractedFacts(TypedDict, total=False):
    parties: List[str]
    events: List[str]
    disputes: List[str]
    claims: List[str]
    key_dates: List[str]
    amounts: List[str]
    locations: List[str]
    summary: str


class AnalysisResult(TypedDict, total=False):
    legal_basis: List[str]
    risk_assessment: str
    suggestions: List[str]
    key_points: List[str]


class FileInfo(TypedDict, total=False):
    filename: str
    file_type: str
    file_path: str
    extracted_text: str
    extracted_text_length: int


class CyberJudgeState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    session_id: str
    user_id: str
    
    intent_info: Optional[IntentInfo]
    
    uploaded_files: Annotated[List[FileInfo], "uploaded files"]
    extracted_facts: Optional[ExtractedFacts]
    
    related_cases: Annotated[List[CaseInfo], "related cases"]
    related_laws: Annotated[List[LawInfo], "related laws"]
    law_details: Annotated[List[LawDetail], "law details"]
    
    analysis_result: Optional[AnalysisResult]
    
    tool_calls: Annotated[List[dict], "tool call history"]
    tool_results: Annotated[dict, "tool execution results"]
    
    enable_tools: bool
    max_history: int
