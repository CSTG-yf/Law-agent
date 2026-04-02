from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from pathlib import Path
import shutil
from app.service.graph.graph_db import Neo4jGraphStore
from app.service.graph.graph_builder_v2 import KnowledgeGraphBuilderV2
from app.schema.graph import (
    GraphUploadResponse,
    GraphQueryRequest,
    GraphQueryResponse,
    GraphStatisticsResponse
)
from app.core.logger import get_logger

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])
logger = get_logger("graph_api")

graph_store = Neo4jGraphStore()


@router.post("/upload", response_model=GraphUploadResponse)
async def upload_to_graph(
    file: UploadFile = File(..., description="上传的文件"),
    document_type: str = Form("legal", description="文档类型: legal/case/general"),
    strict_mode: bool = Form(True, description="是否启用严格模式")
):
    """
    上传文档并使用 LangChain LLMGraphTransformer 构建知识图谱
    
    特点：
    - Schema 约束：只提取预定义的实体类型和关系类型
    - 严格模式：确保提取结果符合 Schema 定义
    - 结构化输出：保证提取结果的格式一致性
    
    支持的文档类型：
    - legal: 法律文档（法条、法规等）
    - case: 案例文档（判决书、案例等）
    - general: 通用文档
    """
    try:
        logger.info(
            f"上传文档构建知识图谱 - "
            f"filename: {file.filename}, type: {document_type}, strict: {strict_mode}"
        )
        
        if document_type not in ["legal", "case", "general"]:
            logger.error(f"不支持的文档类型: {document_type}")
            raise HTTPException(status_code=400, detail="不支持的文档类型")
        
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        file_path = upload_dir / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"文件保存成功 - path: {file_path}")
        
        graph_builder = KnowledgeGraphBuilderV2()
        
        result = await graph_builder.build_from_document(
            file_path=str(file_path),
            document_type=document_type
        )
        
        if result.get("success"):
            logger.info(
                f"知识图谱构建成功 - "
                f"nodes: {result['nodes_count']}, "
                f"relationships: {result['relationships_count']}"
            )
            return GraphUploadResponse(
                success=True,
                message="知识图谱构建成功",
                code=200,
                file_name=file.filename,
                document_type=document_type,
                nodes_count=result["nodes_count"],
                relationships_count=result["relationships_count"]
            )
        else:
            logger.error(f"知识图谱构建失败 - error: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "知识图谱构建失败")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"上传文档构建知识图谱失败 - "
            f"filename: {file.filename}, error: {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"上传文档构建知识图谱失败: {str(e)}"
        )


@router.post("/query", response_model=GraphQueryResponse)
async def query_graph(request: GraphQueryRequest):
    """
    查询知识图谱
    
    支持的查询类型：
    - entity: 基于实体名称查询
    - relation: 基于关系类型查询
    - cypher: 执行Cypher查询
    """
    try:
        logger.info(
            f"查询知识图谱 - "
            f"type: {request.query_type}, query: {request.query}"
        )
        
        if request.query_type == "entity":
            query = f"""
            MATCH (n {{name: $name}})
            """
            if request.entity_type:
                query += f"WHERE n:{request.entity_type}"
            
            query += """
            CALL {
                WITH n
                MATCH (n)-[r*1..2]-(related)
                RETURN related, r
                LIMIT $limit
            }
            RETURN n, related, r
            """
            
            results = graph_store.execute_query(query, {
                "name": request.query,
                "limit": request.limit or 10
            })
            
        elif request.query_type == "relation":
            if not request.relation_type:
                raise HTTPException(
                    status_code=400,
                    detail="关系查询需要提供 relation_type 参数"
                )
            
            query = f"""
            MATCH (a)-[r:{request.relation_type}]->(b)
            """
            if request.entity_type:
                query += f"WHERE a:{request.entity_type} OR b:{request.entity_type}"
            
            query += """
            RETURN a, r, b
            LIMIT $limit
            """
            
            results = graph_store.execute_query(query, {
                "limit": request.limit or 10
            })
            
        elif request.query_type == "cypher":
            results = graph_store.execute_query(request.query)
            
        else:
            logger.error(f"不支持的查询类型: {request.query_type}")
            raise HTTPException(status_code=400, detail="不支持的查询类型")
        
        logger.info(f"知识图谱查询成功 - results: {len(results)}")
        return GraphQueryResponse(
            success=True,
            message="查询成功",
            code=200,
            results=results,
            total=len(results)
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询知识图谱失败 - error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"查询知识图谱失败: {str(e)}"
        )


@router.get("/statistics", response_model=GraphStatisticsResponse)
async def get_graph_statistics():
    """获取知识图谱统计信息"""
    try:
        logger.info("获取知识图谱统计信息")
        
        stats = graph_store.get_statistics()
        
        logger.info(
            f"获取知识图谱统计信息成功 - "
            f"nodes: {stats.get('total_nodes', 0)}, "
            f"relationships: {stats.get('total_relationships', 0)}"
        )
        
        return GraphStatisticsResponse(
            success=True,
            message="获取统计信息成功",
            code=200,
            total_nodes=stats.get("total_nodes", 0),
            total_relationships=stats.get("total_relationships", 0),
            node_types=stats.get("node_types", []),
            relationship_types=stats.get("relationship_types", [])
        )
            
    except Exception as e:
        logger.error(f"获取知识图谱统计信息失败 - error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取知识图谱统计信息失败: {str(e)}"
        )


@router.delete("/clear")
async def clear_graph():
    """清空知识图谱（慎用）"""
    try:
        logger.warning("清空知识图谱")
        
        success = graph_store.clear_all()
        
        if success:
            logger.info("知识图谱清空成功")
            return {
                "success": True,
                "message": "知识图谱已清空",
                "code": 200
            }
        else:
            logger.error("知识图谱清空失败")
            raise HTTPException(
                status_code=500,
                detail="知识图谱清空失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清空知识图谱失败 - error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"清空知识图谱失败: {str(e)}"
        )
