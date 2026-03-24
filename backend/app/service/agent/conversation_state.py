from typing import Annotated, TypedDict, List, Optional, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.documents import Document
from langgraph.graph import add_messages


class RetrievalMetadata(TypedDict, total=False):
    original_query: str
    rewritten_query: str
    intent: str
    intent_confidence: float
    rewrite_type: str
    retrieval_skipped: bool
    skip_reason: Optional[str]
    documents_count: int
    retrieval_strategy: Optional[str]


class ConversationState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    context: Annotated[List[Document], "retrieved documents for RAG"]
    use_rag: bool
    retrieval_strategy: Optional[str]
    enable_rerank: bool
    session_id: str
    user_id: str
    max_history: int
    enable_tools: bool
    tool_calls: Annotated[List[dict], "tool call history"]
    tool_results: Annotated[dict, "tool execution results"]
    retrieval_metadata: Annotated[Optional[RetrievalMetadata], "retrieval process metadata"]


class RAGConfig(TypedDict):
    enabled: bool
    strategy: Literal["vector", "hybrid", "none"]
    top_k: int
    score_threshold: float
