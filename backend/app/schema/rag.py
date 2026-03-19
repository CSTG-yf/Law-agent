from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    success: bool
    message: str
    code: int = 200


class UploadResponse(BaseResponse):
    file_name: Optional[str] = None
    file_hash: Optional[str] = None
    chunks_count: Optional[int] = None
    document_ids: Optional[List[str]] = None


class QueryRequest(BaseModel):
    query: str = Field(..., description="查询文本")
    n_results: int = Field(5, ge=1, le=20, description="返回结果数量")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    strategy: str = Field("basic", description="检索策略: basic/hybrid/mmr/multi_query")
    enable_rerank: bool = Field(False, description="是否启用重排序")
    fetch_k: int = Field(20, description="MMR初始获取数量")
    lambda_mult: float = Field(0.5, description="MMR多样性因子(0-1)")


class QueryResult(BaseModel):
    document: str
    metadata: Dict[str, Any]
    distance: Optional[float] = None
    id: Optional[str] = None


class QueryResponse(BaseResponse):
    query: str
    results: List[QueryResult]
    total: int


class DeleteRequest(BaseModel):
    file_hash: str = Field(..., description="文件哈希值")


class DeleteResponse(BaseResponse):
    file_hash: str
    deleted_chunks: Optional[int] = None


class DocumentInfo(BaseModel):
    file_hash: str
    file_name: str
    chunks_count: int
    uploaded_at: Optional[str] = None


class DocumentsListResponse(BaseModel):
    documents: List[DocumentInfo]
    total: int


class StatisticsResponse(BaseModel):
    total_documents: int
    total_chunks: int
    vector_db_count: int


class TaskSubmitResponse(BaseModel):
    success: bool
    message: str
    code: int = 202
    task_id: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None


class TaskResultResponse(BaseModel):
    success: bool
    message: str
    code: int = 200
    task_id: str
    file_name: Optional[str] = None
    file_hash: Optional[str] = None
    chunks_count: Optional[int] = None
    document_ids: Optional[List[str]] = None
    deleted_chunks: Optional[int] = None