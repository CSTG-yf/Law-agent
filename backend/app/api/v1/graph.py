from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import Optional, List
from pathlib import Path
import shutil
from app.service.graph.graph_db import Neo4jGraphStore
from app.service.graph.graph_document_manager import graph_document_manager
from app.schema.graph import (
    GraphUploadResponse,
    GraphQueryRequest,
    GraphQueryResponse,
    GraphStatisticsResponse,
    VisualizationRequest,
    VisualizationResponse,
    VisualizationNode,
    VisualizationRelationship
)
from app.tasks.graph_tasks import build_graph_task, delete_graph_document_task, clear_graph_task
from app.core.logger import get_logger
from app.core.constants import HttpStatus

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])
logger = get_logger("graph_api")

graph_store = Neo4jGraphStore()


@router.post("/upload", response_model=GraphUploadResponse)
async def upload_to_graph(
    file: UploadFile = File(..., description="上传的文件"),
    document_type: str = Form("legal", description="文档类型: legal/case/general")
):
    """
    上传文档并异步构建知识图谱
    
    特点：
    - 异步处理：使用 Celery 任务队列异步处理
    - Schema 约束：只提取预定义的实体类型和关系类型
    - 任务追踪：返回任务 ID，可查询处理进度
    - 重复检测：自动检测重复文件
    
    支持的文档类型：
    - legal: 法律文档（法条、法规等）
    - case: 案例文档（判决书、案例等）
    - general: 通用文档
    
    返回：
    - task_id: 任务 ID，用于查询处理进度
    """
    try:
        logger.info(
            f"上传文档构建知识图谱 - "
            f"filename: {file.filename}, type: {document_type}"
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
        
        file_hash = graph_document_manager.calculate_file_hash(str(file_path))
        
        if file_hash and graph_document_manager.is_duplicate(file_hash):
            logger.warning(f"文件已存在 - file: {file.filename}, hash: {file_hash[:8]}")
            return GraphUploadResponse(
                success=False,
                message="文件已存在，请勿重复上传",
                code=400,
                file_name=file.filename,
                document_type=document_type,
                nodes_count=0,
                relationships_count=0,
                task_id=None,
                file_hash=file_hash
            )
        
        task = build_graph_task.delay(
            file_path=str(file_path),
            file_name=file.filename,
            document_type=document_type
        )
        
        task_id = task.id
        
        logger.info(f"知识图谱构建任务已提交 - task_id: {task_id}")
        
        return GraphUploadResponse(
            success=True,
            message="知识图谱构建任务已提交，请使用 task_id 查询处理进度",
            code=200,
            file_name=file.filename,
            document_type=document_type,
            nodes_count=0,
            relationships_count=0,
            task_id=task_id
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


@router.get("/documents")
async def get_documents():
    """
    获取知识图谱文档列表
    
    Returns:
        文档列表
    """
    try:
        logger.info("获取知识图谱文档列表")
        
        documents = graph_document_manager.get_all_documents()
        
        logger.info(f"获取知识图谱文档列表成功 - count: {len(documents)}")
        
        return {
            "code": 200,
            "status": "success",
            "message": "获取文档列表成功",
            "data": {
                "documents": documents,
                "total": len(documents)
            }
        }
        
    except Exception as e:
        logger.error(f"获取文档列表失败 - error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取文档列表失败: {str(e)}"
        )


@router.get("/documents/{file_hash}")
async def get_document(file_hash: str):
    """
    获取单个文档信息
    
    Args:
        file_hash: 文件哈希
        
    Returns:
        文档信息
    """
    try:
        logger.info(f"获取文档信息 - hash: {file_hash[:8]}")
        
        doc_info = graph_document_manager.get_document(file_hash)
        
        if doc_info is None:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        logger.info(f"获取文档信息成功 - file: {doc_info.get('file_name')}")
        
        return {
            "code": 200,
            "status": "success",
            "message": "获取文档信息成功",
            "data": {
                "file_hash": file_hash,
                **doc_info
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档信息失败 - hash: {file_hash[:8]}, error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取文档信息失败: {str(e)}"
        )


@router.delete("/documents/{file_hash}")
async def delete_document(file_hash: str):
    """
    删除文档（异步任务）
    
    Args:
        file_hash: 文件哈希
        
    Returns:
        任务信息
    """
    try:
        logger.info(f"删除文档 - hash: {file_hash[:8]}")
        
        doc_info = graph_document_manager.get_document(file_hash)
        
        if doc_info is None:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        task = delete_graph_document_task.delay(file_hash=file_hash)
        
        logger.info(f"删除文档任务已提交 - task_id: {task.id}")
        
        return {
            "code": 200,
            "status": "success",
            "message": "删除文档任务已提交",
            "data": {
                "task_id": task.id,
                "file_hash": file_hash,
                "file_name": doc_info.get("file_name")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败 - hash: {file_hash[:8]}, error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"删除文档失败: {str(e)}"
        )


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    查询知识图谱构建任务状态
    
    Args:
        task_id: 任务 ID
        
    Returns:
        任务状态信息
    """
    try:
        logger.info(f"查询任务状态 - task_id: {task_id}")
        
        from app.celery_config import celery_app
        
        task_result = celery_app.AsyncResult(task_id)
        
        if task_result.state == 'PENDING':
            response = {
                'task_id': task_id,
                'status': 'pending',
                'message': '任务等待中'
            }
        elif task_result.state == 'PROGRESS':
            response = {
                'task_id': task_id,
                'status': 'processing',
                'progress': task_result.info.get('progress', 0),
                'message': task_result.info.get('message', '处理中')
            }
        elif task_result.state == 'SUCCESS':
            result = task_result.result
            response = {
                'task_id': task_id,
                'status': 'completed',
                'success': result.get('success', False),
                'message': result.get('message', '任务完成'),
                'file_name': result.get('file_name'),
                'file_hash': result.get('file_hash'),
                'document_type': result.get('document_type'),
                'nodes_count': result.get('nodes_count', 0),
                'relationships_count': result.get('relationships_count', 0),
                'error_type': result.get('error_type')
            }
        elif task_result.state == 'FAILURE':
            response = {
                'task_id': task_id,
                'status': 'failed',
                'error': str(task_result.info)
            }
        else:
            response = {
                'task_id': task_id,
                'status': task_result.state.lower(),
                'info': str(task_result.info)
            }
        
        logger.info(f"查询任务状态成功 - task_id: {task_id}, status: {response['status']}")
        
        return {
            'code': 200,
            'status': 'success',
            'message': '任务状态查询成功',
            'data': response
        }
        
    except Exception as e:
        logger.error(f"查询任务状态失败 - task_id: {task_id}, error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"查询任务状态失败: {str(e)}"
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
        
        graph_stats = graph_store.get_statistics()
        doc_stats = graph_document_manager.get_statistics()
        
        logger.info(
            f"获取知识图谱统计信息成功 - "
            f"nodes: {graph_stats.get('total_nodes', 0)}, "
            f"relationships: {graph_stats.get('total_relationships', 0)}"
        )
        
        return GraphStatisticsResponse(
            success=True,
            message="获取统计信息成功",
            code=200,
            total_nodes=graph_stats.get("total_nodes", 0),
            total_relationships=graph_stats.get("total_relationships", 0),
            node_types=graph_stats.get("node_types", []),
            relationship_types=graph_stats.get("relationship_types", []),
            document_stats=doc_stats
        )
            
    except Exception as e:
        logger.error(f"获取知识图谱统计信息失败 - error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取知识图谱统计信息失败: {str(e)}"
        )


@router.delete("/clear")
async def clear_graph():
    """清空知识图谱（慎用）- 异步任务"""
    try:
        logger.warning("清空知识图谱")
        
        task = clear_graph_task.delay()
        task_id = task.id
        
        logger.info(f"清空知识图谱任务已提交 - task_id: {task_id}")
        
        return {
            "success": True,
            "message": "清空知识图谱任务已提交",
            "code": 200,
            "task_id": task_id
        }
            
    except Exception as e:
        logger.error(f"清空知识图谱失败 - error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"清空知识图谱失败: {str(e)}"
        )


@router.post("/visualization", response_model=dict)
async def get_visualization_data(request: VisualizationRequest):
    """
    获取知识图谱可视化数据

    返回 NVL (Neo4j Visualization Library) 兼容的数据格式：
    - nodes: 节点列表，包含 id, labels, properties
    - relationships: 关系列表，包含 id, type, startNode, endNode, properties

    支持的参数：
    - node_types: 过滤节点类型（如 ["LawArticle", "LegalCase"]）
    - relation_types: 过滤关系类型（如 ["APPLIES_LAW", "INVOLVES"]）
    - node_limit: 节点数量限制（默认 100，最大 1000）
    - depth: 关系深度（默认 2，范围 1-3）
    - search_term: 搜索关键词，匹配节点名称
    - file_hash: 文档哈希值，根据source_documents属性过滤特定文档的节点
    """
    try:
        logger.info(
            f"获取可视化数据 - "
            f"node_types: {request.node_types}, "
            f"relation_types: {request.relation_types}, "
            f"node_limit: {request.node_limit}, "
            f"depth: {request.depth}, "
            f"search_term: {request.search_term}"
        )
        
        data = graph_store.get_visualization_data(
            node_types=request.node_types,
            relation_types=request.relation_types,
            node_limit=request.node_limit,
            depth=request.depth,
            search_term=request.search_term,
            file_hash=request.file_hash
        )
        
        nodes = [VisualizationNode(**n) for n in data.get("nodes", [])]
        relationships = [VisualizationRelationship(**r) for r in data.get("relationships", [])]
        
        logger.info(
            f"获取可视化数据成功 - "
            f"nodes: {len(nodes)}, relationships: {len(relationships)}"
        )
        
        return {
            "code": HttpStatus.OK,
            "status": "success",
            "message": "获取可视化数据成功",
            "data": VisualizationResponse(
                success=True,
                message="获取可视化数据成功",
                code=HttpStatus.OK,
                nodes=nodes,
                relationships=relationships,
                total_nodes=len(nodes),
                total_relationships=len(relationships)
            ).model_dump()
        }
            
    except Exception as e:
        logger.error(f"获取可视化数据失败 - error: {str(e)}")
        raise HTTPException(
            status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            detail=f"获取可视化数据失败: {str(e)}"
        )


@router.get("/visualization", response_model=dict)
async def get_visualization_data_get(
    node_types: Optional[str] = Query(None, description="节点类型，多个用逗号分隔"),
    relation_types: Optional[str] = Query(None, description="关系类型，多个用逗号分隔"),
    node_limit: int = Query(100, description="节点数量限制", ge=1, le=1000),
    depth: int = Query(2, description="关系深度", ge=1, le=3),
    search_term: Optional[str] = Query(None, description="搜索关键词"),
    file_hash: Optional[str] = Query(None, description="文档哈希值，根据source_documents属性过滤特定文档的节点")
):
    """
    获取知识图谱可视化数据（GET 方式）

    返回 NVL (Neo4j Visualization Library) 兼容的数据格式

    支持的参数：
    - node_types: 过滤节点类型（如 "LawArticle,LegalCase"）
    - relation_types: 过滤关系类型（如 "APPLIES_LAW,INVOLVES"）
    - node_limit: 节点数量限制（默认 100，最大 1000）
    - depth: 关系深度（默认 2，范围 1-3）
    - search_term: 搜索关键词，匹配节点名称
    - file_hash: 文档哈希值，根据source_documents属性过滤特定文档的节点
    """
    try:
        node_types_list = node_types.split(",") if node_types else None
        relation_types_list = relation_types.split(",") if relation_types else None

        logger.info(
            f"获取可视化数据(GET) - "
            f"node_types: {node_types_list}, "
            f"relation_types: {relation_types_list}, "
            f"node_limit: {node_limit}, "
            f"depth: {depth}, "
            f"search_term: {search_term}, "
            f"file_hash: {file_hash[:8] if file_hash else None}"
        )

        data = graph_store.get_visualization_data(
            node_types=node_types_list,
            relation_types=relation_types_list,
            node_limit=node_limit,
            depth=depth,
            search_term=search_term,
            file_hash=file_hash
        )
        
        nodes = [VisualizationNode(**n) for n in data.get("nodes", [])]
        relationships = [VisualizationRelationship(**r) for r in data.get("relationships", [])]
        
        logger.info(
            f"获取可视化数据成功 - "
            f"nodes: {len(nodes)}, relationships: {len(relationships)}"
        )
        
        return {
            "code": HttpStatus.OK,
            "status": "success",
            "message": "获取可视化数据成功",
            "data": VisualizationResponse(
                success=True,
                message="获取可视化数据成功",
                code=HttpStatus.OK,
                nodes=nodes,
                relationships=relationships,
                total_nodes=len(nodes),
                total_relationships=len(relationships)
            ).model_dump()
        }
            
    except Exception as e:
        logger.error(f"获取可视化数据失败 - error: {str(e)}")
        raise HTTPException(
            status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            detail=f"获取可视化数据失败: {str(e)}"
        )
