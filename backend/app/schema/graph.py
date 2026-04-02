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
