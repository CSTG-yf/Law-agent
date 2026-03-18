from celery import Task
from typing import Dict, Any
import json
from pathlib import Path
from app.celery_config import celery_app
from app.service.rag.text_embedding import RAGDocumentService
from app.exceptions import DuplicateFileError, FileProcessingError, VectorDBError


class DocumentProcessingTask(Task):
    """文档处理任务基类"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的回调"""
        print(f"任务 {task_id} 失败: {exc}")
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(exc),
                'status': 'failed'
            }
        )
    
    def on_success(self, retval, task_id, args, kwargs):
        """任务成功时的回调"""
        print(f"任务 {task_id} 成功完成")
        self.update_state(
            state='SUCCESS',
            meta={
                'result': retval,
                'status': 'completed'
            }
        )


@celery_app.task(
    base=DocumentProcessingTask,
    bind=True,
    name='app.tasks.document_tasks.process_document_task'
)
def process_document_task(self, task_id: str, file_path: str, file_name: str, metadata: Dict[str, Any] = None):
    """
    处理文档的Celery任务
    
    Args:
        task_id: 任务ID
        file_path: 文件路径
        file_name: 文件名
        metadata: 额外的元数据
        
    Returns:
        处理结果
    """
    try:
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 10,
                'message': '开始处理文档'
            }
        )
        
        rag_service = RAGDocumentService()
        
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 30,
                'message': '计算文件哈希'
            }
        )
        
        result = rag_service.process_and_store_document(
            file_path=file_path,
            file_name=file_name,
            metadata=metadata
        )
        
        if result["success"]:
            self.update_state(
                state='PROGRESS',
                meta={
                    'status': 'processing',
                    'progress': 80,
                    'message': '文档处理完成'
                }
            )
            
            return {
                'task_id': task_id,
                'success': True,
                'message': result['message'],
                'file_name': result.get('file_name'),
                'file_hash': result.get('file_hash'),
                'chunks_count': result.get('chunks_count'),
                'document_ids': result.get('document_ids')
            }
        else:
            error_msg = result.get('message', '未知错误')
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
                'message': error_msg,
                'error_type': 'business_error'
            }
            
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'failed',
                'error': str(e)
            }
        )
        raise e


@celery_app.task(
    base=DocumentProcessingTask,
    bind=True,
    name='app.tasks.document_tasks.delete_document_task'
)
def delete_document_task(self, task_id: str, file_hash: str):
    """
    删除文档的Celery任务
    
    Args:
        task_id: 任务ID
        file_hash: 文件哈希
        
    Returns:
        删除结果
    """
    try:
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 50,
                'message': '正在删除文档'
            }
        )
        
        rag_service = RAGDocumentService()
        result = rag_service.delete_document(file_hash)
        
        if result["success"]:
            return {
                'task_id': task_id,
                'success': True,
                'message': result['message'],
                'file_hash': result.get('file_hash'),
                'deleted_chunks': result.get('deleted_chunks')
            }
        else:
            error_msg = result.get('message', '未知错误')
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
                'message': error_msg,
                'error_type': 'business_error'
            }
            
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'failed',
                'error': str(e)
            }
        )
        raise e