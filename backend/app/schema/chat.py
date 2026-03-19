from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    timestamp: Optional[str] = Field(None, description="消息时间戳")


class RAGConfig(BaseModel):
    enabled: bool = Field(False, description="是否启用RAG")
    strategy: Literal["vector", "hybrid", "mmr", "multi_query"] = Field("vector", description="检索策略")
    top_k: int = Field(5, ge=1, le=20, description="检索文档数量")
    score_threshold: float = Field(0.7, ge=0.0, le=1.0, description="相似度阈值")


class ConversationConfig(BaseModel):
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    max_history: int = Field(10, ge=1, le=50, description="最大历史记录数")
    rag_config: Optional[RAGConfig] = Field(None, description="RAG配置")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID（可选，不传则自动生成）")
    user_id: str = Field(..., description="用户ID")
    use_rag: bool = Field(False, description="是否使用RAG")
    retrieval_strategy: Optional[Literal["vector", "hybrid", "mmr", "multi_query"]] = Field(
        "vector",
        description="检索策略: vector-向量检索, hybrid-混合检索, mmr-最大边际相关性, multi_query-多查询检索"
    )
    max_history: Optional[int] = Field(10, ge=1, le=50, description="最大历史记录数")
    stream: bool = Field(False, description="是否使用流式输出")


class ChatResponse(BaseModel):
    message_id: str = Field(..., description="消息ID")
    session_id: str = Field(..., description="会话ID")
    role: Literal["assistant"] = Field("assistant", description="消息角色")
    content: str = Field(..., description="回复内容")
    timestamp: str = Field(..., description="回复时间戳")
    sources: Optional[List[dict]] = Field(None, description="引用来源（如果使用RAG）")
    rag_used: bool = Field(False, description="是否使用了RAG")
    retrieval_strategy: Optional[str] = Field(None, description="使用的检索策略")


class ConversationHistory(BaseModel):
    session_id: str = Field(..., description="会话ID")
    messages: List[ChatMessage] = Field(default_factory=list, description="对话历史")
    total_messages: int = Field(..., description="消息总数")
    created_at: str = Field(..., description="会话创建时间")
    updated_at: str = Field(..., description="会话更新时间")


class SessionInfo(BaseModel):
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    created_at: str = Field(..., description="创建时间")
    message_count: int = Field(..., description="消息数量")
    rag_enabled: bool = Field(False, description="是否启用RAG")


class StreamEvent(BaseModel):
    type: Literal["token", "tool_start", "tool_end", "complete", "done", "error"] = Field(..., description="事件类型")
    data: dict = Field(default_factory=dict, description="事件数据")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="错误信息")
    code: int = Field(..., description="错误码")
    detail: Optional[str] = Field(None, description="详细信息")
