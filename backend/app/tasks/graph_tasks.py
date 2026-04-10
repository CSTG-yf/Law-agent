from celery import Task
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
import asyncio
import traceback
from app.celery_config import celery_app
from app.service.graph.graph_builder_v2 import KnowledgeGraphBuilderV2
from app.service.graph.graph_document_manager import graph_document_manager
from app.core.logger import get_logger

logger = get_logger("graph_tasks")


class GraphProcessingTask(Task):
    """知识图谱处理任务基类"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的回调"""
        logger.error(f"知识图谱任务失败 - task_id: {task_id}, error: {exc}")
        try:
            self.update_state(
                state='FAILURE',
                meta={
                    'error': str(exc),
                    'status': 'failed'
                }
            )
        except Exception as e:
            logger.error(f"更新任务状态失败 - error: {str(e)}")


@celery_app.task(
    base=GraphProcessingTask,
    bind=True,
    name='app.tasks.graph_tasks.build_graph_task'
)
def build_graph_task(
    self,
    file_path: str,
    file_name: str,
    document_type: str = "legal"
) -> Dict[str, Any]:
    """
    构建知识图谱的 Celery 任务
    
    Args:
        file_path: 文件路径
        file_name: 文件名
        document_type: 文档类型 (legal/case/general)
        
    Returns:
        构建结果
    """
    task_id = self.request.id
    
    logger.info(
        f"开始构建知识图谱任务 - "
        f"task_id: {task_id}, file: {file_name}, type: {document_type}"
    )
    
    file_hash = None
    
    try:
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 5,
                'message': '计算文件哈希'
            }
        )
        
        file_hash = graph_document_manager.calculate_file_hash(file_path)
        
        if file_hash is None:
            logger.error(f"计算文件哈希失败 - file: {file_name}")
            return {
                'task_id': task_id,
                'success': False,
                'message': '计算文件哈希失败',
                'error_type': 'hash_error'
            }
        
        if graph_document_manager.is_duplicate(file_hash):
            logger.warning(f"文件已存在 - file: {file_name}, hash: {file_hash[:8]}")
            return {
                'task_id': task_id,
                'success': False,
                'message': '文件已存在，请勿重复上传',
                'error_type': 'duplicate_file',
                'file_hash': file_hash
            }
        
        graph_document_manager.register_document(
            file_hash=file_hash,
            file_name=file_name,
            file_path=file_path,
            document_type=document_type,
            nodes_count=0,
            relationships_count=0
        )
        
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 10,
                'message': '初始化知识图谱构建器'
            }
        )
        
        graph_builder = KnowledgeGraphBuilderV2()
        
        logger.info(f"知识图谱构建器初始化完成 - task_id: {task_id}")
        
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 20,
                'message': '开始提取文档文本'
            }
        )
        
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 30,
                'message': '开始提取实体和关系'
            }
        )
        
        result = asyncio.run(graph_builder.build_from_document(
            file_path=file_path,
            document_type=document_type,
            file_hash=file_hash
        ))
        
        logger.info(
            f"知识图谱构建完成 - "
            f"task_id: {task_id}, success: {result.get('success')}"
        )
        
        if result.get("success"):
            nodes_count = result.get("nodes_count", 0)
            relationships_count = result.get("relationships_count", 0)
            
            doc_info = {
                "file_name": file_name,
                "file_path": file_path,
                "document_type": document_type,
                "nodes_count": nodes_count,
                "relationships_count": relationships_count,
                "uploaded_at": datetime.now().isoformat(),
                "status": "completed"
            }
            
            graph_document_manager.save_document(
                file_hash=file_hash,
                doc_info=doc_info
            )
            
            self.update_state(
                state='PROGRESS',
                meta={
                    'status': 'processing',
                    'progress': 90,
                    'message': '知识图谱构建完成'
                }
            )
            
            logger.info(
                f"知识图谱任务成功 - "
                f"task_id: {task_id}, nodes: {nodes_count}, relationships: {relationships_count}"
            )
            
            return {
                'task_id': task_id,
                'success': True,
                'message': '知识图谱构建成功',
                'file_name': file_name,
                'file_hash': file_hash,
                'document_type': document_type,
                'nodes_count': nodes_count,
                'relationships_count': relationships_count
            }
        else:
            error_msg = result.get('error', '未知错误')
            
            logger.error(
                f"知识图谱构建失败 - "
                f"task_id: {task_id}, error: {error_msg}"
            )
            
            return {
                'task_id': task_id,
                'success': False,
                'message': f'知识图谱构建失败: {error_msg}',
                'file_hash': file_hash,
                'error_type': 'processing_error'
            }
            
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        
        logger.error(
            f"知识图谱任务异常 - "
            f"task_id: {task_id}, error: {error_msg}\n{error_trace}"
        )
        
        return {
            'task_id': task_id,
            'success': False,
            'message': f'知识图谱构建异常: {error_msg}',
            'error_type': 'exception',
            'error_detail': error_trace
        }


@celery_app.task(
    base=GraphProcessingTask,
    bind=True,
    name='app.tasks.graph_tasks.delete_graph_document_task'
)
def delete_graph_document_task(self, file_hash: str) -> Dict[str, Any]:
    """
    删除知识图谱文档的 Celery 任务
    
    Args:
        file_hash: 文件哈希
        
    Returns:
        删除结果
    """
    task_id = self.request.id
    
    logger.info(f"开始删除知识图谱文档 - task_id: {task_id}, hash: {file_hash[:8]}")
    
    try:
        doc_info = graph_document_manager.get_document(file_hash)
        
        if doc_info is None:
            logger.warning(f"文档不存在 - hash: {file_hash[:8]}")
            return {
                'task_id': task_id,
                'success': False,
                'message': '文档不存在',
                'file_hash': file_hash
            }
        
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 30,
                'message': '正在删除Neo4j中的节点'
            }
        )
        
        from app.service.graph.graph_db import Neo4jGraphStore
        graph_store = Neo4jGraphStore()
        
        delete_result = graph_store.delete_nodes_by_property("file_hash", file_hash)
        
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 70,
                'message': '正在删除文档记录'
            }
        )
        
        graph_document_manager.delete_document(file_hash)
        
        logger.info(f"知识图谱文档删除成功 - task_id: {task_id}")
        
        return {
            'task_id': task_id,
            'success': True,
            'message': '文档删除成功',
            'file_hash': file_hash,
            'file_name': doc_info.get('file_name'),
            'deleted_nodes': delete_result.get('deleted_count', 0)
        }
            
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        
        logger.error(
            f"删除知识图谱文档异常 - "
            f"task_id: {task_id}, error: {error_msg}\n{error_trace}"
        )
        
        return {
            'task_id': task_id,
            'success': False,
            'message': f'删除文档异常: {error_msg}',
            'file_hash': file_hash,
            'error_type': 'exception'
        }


@celery_app.task(
    base=GraphProcessingTask,
    bind=True,
    name='app.tasks.graph_tasks.clear_graph_task'
)
def clear_graph_task(self) -> Dict[str, Any]:
    """
    清空知识图谱的 Celery 任务
        
    Returns:
        清空结果
    """
    task_id = self.request.id
    
    logger.info(f"开始清空知识图谱任务 - task_id: {task_id}")
    
    try:
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 30,
                'message': '正在清空Neo4j数据库'
            }
        )
        
        from app.service.graph.graph_db import Neo4jGraphStore
        graph_store = Neo4jGraphStore()
        
        success = graph_store.clear_all()
        
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 70,
                'message': '正在清空文档记录'
            }
        )
        
        if success:
            graph_document_manager.file_hashes.clear()
            graph_document_manager._save_hashes()
            
            logger.info(f"知识图谱清空成功 - task_id: {task_id}")
            
            return {
                'task_id': task_id,
                'success': True,
                'message': '知识图谱清空成功'
            }
        else:
            logger.error(f"知识图谱清空失败 - task_id: {task_id}")
            
            return {
                'task_id': task_id,
                'success': False,
                'message': '知识图谱清空失败'
            }
            
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        
        logger.error(
            f"清空知识图谱任务异常 - "
            f"task_id: {task_id}, error: {error_msg}\n{error_trace}"
        )
        
        return {
            'task_id': task_id,
            'success': False,
            'message': f'清空知识图谱异常: {error_msg}',
            'error_type': 'exception'
        }
