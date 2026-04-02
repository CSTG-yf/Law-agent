from celery import Task
from typing import Dict, Any
from pathlib import Path
from app.celery_config import celery_app
from app.service.graph.graph_builder_v2 import KnowledgeGraphBuilderV2
from app.core.logger import get_logger

logger = get_logger("graph_tasks")


class GraphProcessingTask(Task):
    """知识图谱处理任务基类"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的回调"""
        logger.error(f"知识图谱任务失败 - task_id: {task_id}, error: {exc}")
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(exc),
                'status': 'failed'
            }
        )
    
    def on_success(self, retval, task_id, args, kwargs):
        """任务成功时的回调"""
        logger.info(f"知识图谱任务成功完成 - task_id: {task_id}")
        self.update_state(
            state='SUCCESS',
            meta={
                'result': retval,
                'status': 'completed'
            }
        )


@celery_app.task(
    base=GraphProcessingTask,
    bind=True,
    name='app.tasks.graph_tasks.build_graph_task'
)
def build_graph_task(
    self,
    task_id: str,
    file_path: str,
    file_name: str,
    document_type: str = "legal"
) -> Dict[str, Any]:
    """
    构建知识图谱的 Celery 任务
    
    Args:
        task_id: 任务 ID
        file_path: 文件路径
        file_name: 文件名
        document_type: 文档类型 (legal/case/general)
        
    Returns:
        构建结果
    """
    logger.info(
        f"开始构建知识图谱任务 - "
        f"task_id: {task_id}, file: {file_name}, type: {document_type}"
    )
    
    try:
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
        
        result = graph_builder.build_from_document(
            file_path=file_path,
            document_type=document_type
        )
        
        logger.info(
            f"知识图谱构建完成 - "
            f"task_id: {task_id}, success: {result.get('success')}"
        )
        
        if result.get("success"):
            self.update_state(
                state='PROGRESS',
                meta={
                    'status': 'processing',
                    'progress': 90,
                    'message': '知识图谱构建完成'
                }
            )
            
            nodes_count = result.get("nodes_count", 0)
            relationships_count = result.get("relationships_count", 0)
            
            logger.info(
                f"知识图谱任务成功 - "
                f"task_id: {task_id}, nodes: {nodes_count}, relationships: {relationships_count}"
            )
            
            return {
                'task_id': task_id,
                'success': True,
                'message': '知识图谱构建成功',
                'file_name': file_name,
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
            
            self.update_state(
                state='SUCCESS',
                meta={
                    'status': 'completed',
                    'error': error_msg
                }
            )
            
            return {
                'task_id': task_id,
                'success': False,
                'message': f'知识图谱构建失败: {error_msg}',
                'error_type': 'processing_error'
            }
            
    except Exception as e:
        logger.error(
            f"知识图谱任务异常 - "
            f"task_id: {task_id}, error: {str(e)}",
            exc_info=True
        )
        
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'failed',
                'error': str(e)
            }
        )
        raise


@celery_app.task(
    base=GraphProcessingTask,
    bind=True,
    name='app.tasks.graph_tasks.clear_graph_task'
)
def clear_graph_task(self, task_id: str) -> Dict[str, Any]:
    """
    清空知识图谱的 Celery 任务
    
    Args:
        task_id: 任务 ID
        
    Returns:
        清空结果
    """
    logger.info(f"开始清空知识图谱任务 - task_id: {task_id}")
    
    try:
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 50,
                'message': '正在清空知识图谱'
            }
        )
        
        from app.service.graph.graph_db import Neo4jGraphStore
        graph_store = Neo4jGraphStore()
        
        success = graph_store.clear_graph()
        
        if success:
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
        logger.error(
            f"清空知识图谱任务异常 - "
            f"task_id: {task_id}, error: {str(e)}",
            exc_info=True
        )
        
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'failed',
                'error': str(e)
            }
        )
        raise
