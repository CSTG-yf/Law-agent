from typing import Annotated, TypedDict, List, Optional, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.documents import Document
from langgraph.graph import add_messages


class ConversationState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    context: Annotated[List[Document], "retrieved documents for RAG"]
    use_rag: bool
    retrieval_strategy: Optional[str]
    session_id: str
    user_id: str
    max_history: int


class RAGConfig(TypedDict):
    enabled: bool
    strategy: Literal["vector", "hybrid", "none"]
    top_k: int
    score_threshold: float
