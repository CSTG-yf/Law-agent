from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from pathlib import Path
import shutil
import uuid
from app.service.graph.graph_db import Neo4jGraphStore
from app.schema.graph import (
    GraphUploadResponse,
    GraphQueryRequest,
    GraphQueryResponse,
    GraphStatisticsResponse
)
from app.tasks.graph_tasks import build_graph_task, clear_graph_task
from app.core.logger import get_logger

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
        
        task_id = str(uuid.uuid4())
        
        logger.info(f"创建知识图谱构建任务 - task_id: {task_id}")
        
        task = build_graph_task.delay(
            task_id=task_id,
            file_path=str(file_path),
            file_name=file.filename,
            document_type=document_type
        )
        
        logger.info(f"知识图谱构建任务已提交 - task_id: {task_id}, celery_id: {task.id}")
        
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
                'document_type': result.get('document_type'),
                'nodes_count': result.get('nodes_count', 0),
                'relationships_count': result.get('relationships_count', 0)
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
    """清空知识图谱（慎用）- 异步任务"""
    try:
        logger.warning("清空知识图谱")
        
        task_id = str(uuid.uuid4())
        
        task = clear_graph_task.delay(task_id=task_id)
        
        logger.info(f"清空知识图谱任务已提交 - task_id: {task_id}, celery_id: {task.id}")
        
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
