from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class GraphUploadResponse(BaseModel):
    success: bool
    message: str
    code: int = 200
    file_name: Optional[str] = None
    document_type: Optional[str] = None
    nodes_count: Optional[int] = None
    relationships_count: Optional[int] = None
    task_id: Optional[str] = None
    file_hash: Optional[str] = None


class GraphQueryRequest(BaseModel):
    query_type: str = Field(..., description="查询类型: entity/relation/cypher")
    query: str = Field(..., description="查询内容")
    entity_type: Optional[str] = Field(None, description="实体类型（可选）")
    relation_type: Optional[str] = Field(None, description="关系类型（可选）")
    limit: Optional[int] = Field(10, description="返回结果数量限制")


class GraphQueryResponse(BaseModel):
    success: bool
    message: str
    code: int = 200
    results: List[Dict[str, Any]]
    total: int


class GraphStatisticsResponse(BaseModel):
    success: bool
    message: str
    code: int = 200
    total_nodes: int
    total_relationships: int
    node_types: List[Dict[str, Any]]
    relationship_types: List[Dict[str, Any]]
    document_stats: Optional[Dict[str, Any]] = None


class GraphDocumentInfo(BaseModel):
    file_hash: str
    file_name: str
    file_path: str
    document_type: str
    nodes_count: int
    relationships_count: int
    uploaded_at: str
    status: str
    error_message: Optional[str] = None


class VisualizationNode(BaseModel):
    id: str = Field(..., description="节点ID")
    labels: List[str] = Field(default_factory=list, description="节点标签列表")
    properties: Dict[str, Any] = Field(default_factory=dict, description="节点属性")


class VisualizationRelationship(BaseModel):
    id: str = Field(..., description="关系ID")
    type: str = Field(..., description="关系类型")
    startNode: str = Field(..., description="起始节点ID")
    endNode: str = Field(..., description="目标节点ID")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系属性")


class VisualizationRequest(BaseModel):
    node_types: Optional[List[str]] = Field(None, description="过滤节点类型，为空则返回所有类型")
    relation_types: Optional[List[str]] = Field(None, description="过滤关系类型，为空则返回所有类型")
    node_limit: Optional[int] = Field(100, description="节点数量限制", ge=1, le=1000)
    depth: Optional[int] = Field(2, description="关系深度（1-3）", ge=1, le=3)
    search_term: Optional[str] = Field(None, description="搜索关键词，匹配节点名称")
    file_hash: Optional[str] = Field(None, description="文档哈希值，根据source_documents属性过滤特定文档的节点")


class VisualizationResponse(BaseModel):
    success: bool
    message: str
    code: int = 200
    nodes: List[VisualizationNode]
    relationships: List[VisualizationRelationship]
    total_nodes: int
    total_relationships: int
