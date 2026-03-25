from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Optional
from pathlib import Path
import shutil
import json
import uuid
import zipfile
import os
from app.service.rag.text_embedding import RAGDocumentService
from app.service.rag.hybrid_retriever import AdvancedRAGService
from app.service.rag.reranker import Reranker
from app.service.vector_db import ChromaVectorStore
from app.schema.rag import (
    UploadResponse,
    QueryRequest,
    QueryResponse,
    QueryResult,
    DeleteRequest,
    DeleteResponse,
    DocumentsListResponse,
    DocumentInfo,
    DocumentDetailResponse,
    StatisticsResponse,
    TaskSubmitResponse,
    TaskStatusResponse,
    TaskResultResponse,
    BatchUploadTaskInfo,
    BatchUploadResponse
)
from app.tasks.document_tasks import process_document_task, delete_document_task
from app.core.logger import get_logger

router = APIRouter(prefix="/rag", tags=["RAG"])
logger = get_logger("rag_api")

rag_service = RAGDocumentService(upload_dir="uploads")

vector_store = ChromaVectorStore(collection_name="legal_documents")
advanced_rag_service = AdvancedRAGService(vector_store)
reranker = Reranker()


@router.post("/upload", response_model=TaskSubmitResponse)
async def upload_document(
    file: UploadFile = File(..., description="上传的文件"),
    metadata: Optional[str] = Form(None, description="额外的元数据（JSON格式）")
):
    """
    上传文档并异步处理存储到向量数据库
    
    支持的文件格式：
    - PDF (.pdf)
    - Word文档 (.docx, .doc)
    - 文本文件 (.txt, .md)
    - Excel文件 (.xlsx, .xls)
    
    返回任务ID，可通过 /task/{task_id} 查询处理状态
    """
    try:
        logger.info(f"上传文档 - filename: {file.filename}, metadata: {metadata}")
        
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        file_path = upload_dir / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        extra_metadata = None
        if metadata:
            try:
                extra_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                pass
        
        task_id = str(uuid.uuid4())
        
        task = process_document_task.delay(
            task_id=task_id,
            file_path=str(file_path),
            file_name=file.filename,
            metadata=extra_metadata
        )
        
        logger.info(f"文档上传成功 - filename: {file.filename}, task_id: {task.id}")
        return TaskSubmitResponse(
            success=True,
            message="文档上传成功，正在后台处理",
            code=202,
            task_id=task.id
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文档失败 - filename: {file.filename}, error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传文档失败: {str(e)}")


@router.post("/upload/batch", response_model=BatchUploadResponse)
async def upload_batch_documents(
    file: UploadFile = File(..., description="上传的ZIP压缩包"),
    metadata: Optional[str] = Form(None, description="额外的元数据（JSON格式）")
):
    """
    批量上传文档（ZIP压缩包）
    
    支持的文件格式：
    - PDF (.pdf)
    - Word文档 (.docx, .doc)
    - 文本文件 (.txt, .md)
    - Excel文件 (.xlsx, .xls)
    
    上传ZIP压缩包，系统会自动解压并批量处理其中的文档
    返回批量任务ID和每个文件的任务ID列表
    """
    try:
        logger.info(f"批量上传文档 - filename: {file.filename}, metadata: {metadata}")
        
        if not file.filename.lower().endswith('.zip'):
            logger.error(f"文件格式错误 - 只支持ZIP文件: {file.filename}")
            raise HTTPException(status_code=400, detail="只支持ZIP压缩包格式")
        
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        zip_path = upload_dir / file.filename
        
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"ZIP文件已保存 - path: {zip_path}")
        
        extra_metadata = None
        if metadata:
            try:
                extra_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                logger.warning(f"元数据格式错误，忽略: {metadata}")
        
        extract_dir = upload_dir / f"extract_{file.filename[:-4]}"
        extract_dir.mkdir(exist_ok=True)
        
        logger.info(f"开始解压ZIP文件 - extract_dir: {extract_dir}")
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            logger.info(f"ZIP文件解压成功")
        except zipfile.BadZipFile:
            logger.error(f"ZIP文件损坏: {file.filename}")
            raise HTTPException(status_code=400, detail="ZIP文件损坏，无法解压")
        
        supported_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md', '.xlsx', '.xls'}
        extracted_files = []
        
        for root, dirs, files in os.walk(extract_dir):
            for filename in files:
                file_path = Path(root) / filename
                if file_path.suffix.lower() in supported_extensions:
                    extracted_files.append(file_path)
                else:
                    logger.info(f"跳过不支持的文件格式: {filename}")
        
        logger.info(f"找到 {len(extracted_files)} 个支持的文件")
        
        if not extracted_files:
            logger.warning(f"ZIP文件中没有找到支持的文档格式")
            os.remove(zip_path)
            shutil.rmtree(extract_dir)
            raise HTTPException(status_code=400, detail="ZIP文件中没有找到支持的文档格式")
        
        batch_id = str(uuid.uuid4())
        tasks = []
        
        for file_path in extracted_files:
            try:
                file_name = file_path.name
                task_id = str(uuid.uuid4())
                
                logger.info(f"创建处理任务 - file: {file_name}, task_id: {task_id}")
                
                task = process_document_task.delay(
                    task_id=task_id,
                    file_path=str(file_path),
                    file_name=file_name,
                    metadata=extra_metadata
                )
                
                tasks.append(BatchUploadTaskInfo(
                    file_name=file_name,
                    task_id=task.id,
                    status="pending"
                ))
                
                logger.info(f"任务创建成功 - file: {file_name}, task_id: {task.id}")
                
            except Exception as e:
                logger.error(f"创建任务失败 - file: {file_path.name}, error: {str(e)}")
                tasks.append(BatchUploadTaskInfo(
                    file_name=file_path.name,
                    task_id="",
                    status="failed"
                ))
        
        logger.info(f"批量上传完成 - batch_id: {batch_id}, total_files: {len(extracted_files)}, success_tasks: {len([t for t in tasks if t.status == 'pending'])}")
        
        return BatchUploadResponse(
            success=True,
            message=f"批量上传成功，共 {len(extracted_files)} 个文件，正在后台处理",
            code=202,
            batch_id=batch_id,
            total_files=len(extracted_files),
            tasks=tasks
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量上传失败 - filename: {file.filename}, error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量上传失败: {str(e)}")


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    查询任务状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态信息
    """
    try:
        logger.info(f"查询任务状态 - task_id: {task_id}")
        from app.celery_config import celery_app
        task_result = celery_app.AsyncResult(task_id)
        
        if task_result.state == 'PENDING':
            logger.info(f"任务状态: PENDING - task_id: {task_id}")
            return TaskStatusResponse(
                task_id=task_id,
                status='pending',
                message='任务等待中'
            )
        elif task_result.state == 'PROGRESS':
            meta = task_result.info or {}
            logger.info(f"任务状态: PROGRESS - task_id: {task_id}, progress: {meta.get('progress', 0)}")
            return TaskStatusResponse(
                task_id=task_id,
                status='processing',
                progress=meta.get('progress', 0),
                message=meta.get('message', '处理中')
            )
        elif task_result.state == 'SUCCESS':
            logger.info(f"任务状态: SUCCESS - task_id: {task_id}")
            return TaskStatusResponse(
                task_id=task_id,
                status='completed',
                progress=100,
                message='处理完成'
            )
        elif task_result.state == 'FAILURE':
            meta = task_result.info or {}
            logger.error(f"任务状态: FAILURE - task_id: {task_id}, error: {meta.get('error', '任务失败')}")
            return TaskStatusResponse(
                task_id=task_id,
                status='failed',
                error=meta.get('error', '任务失败')
            )
        else:
            logger.info(f"任务状态: {task_result.state} - task_id: {task_id}")
            return TaskStatusResponse(
                task_id=task_id,
                status=task_result.state,
                message=f'任务状态: {task_result.state}'
            )
            
    except Exception as e:
        logger.error(f"查询任务状态失败 - task_id: {task_id}, error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询任务状态失败: {str(e)}")


@router.get("/task/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(task_id: str):
    """
    获取任务结果
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务处理结果
    """
    try:
        logger.info(f"获取任务结果 - task_id: {task_id}")
        from app.celery_config import celery_app
        task_result = celery_app.AsyncResult(task_id)
        
        if task_result.state != 'SUCCESS':
            logger.warning(f"任务尚未完成 - task_id: {task_id}, current_state: {task_result.state}")
            return TaskResultResponse(
                success=False,
                message=f"任务尚未完成，当前状态: {task_result.state}",
                code=400,
                task_id=task_id
            )
        
        result = task_result.result
        
        logger.info(f"获取任务结果成功 - task_id: {task_id}, file_name: {result.get('file_name')}")
        return TaskResultResponse(
            success=result.get('success', False),
            message=result.get('message', ''),
            code=200,
            task_id=task_id,
            file_name=result.get('file_name'),
            file_hash=result.get('file_hash'),
            chunks_count=result.get('chunks_count'),
            document_ids=result.get('document_ids')
        )
            
    except Exception as e:
        logger.error(f"获取任务结果失败 - task_id: {task_id}, error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取任务结果失败: {str(e)}")


@router.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    查询相似文档
    
    Args:
        query: 查询文本
        n_results: 返回结果数量（默认5，最大20）
        filters: 过滤条件（可选）
        strategy: 检索策略 (basic/hybrid/mmr/multi_query)
        enable_rerank: 是否启用重排序
        fetch_k: MMR初始获取数量
        lambda_mult: MMR多样性因子(0-1)
    """
    try:
        logger.info(f"查询文档 - query: {request.query[:100]}, n_results: {request.n_results}, strategy: {getattr(request, 'strategy', 'basic')}")
        
        if not request.query or not request.query.strip():
            logger.warning("查询文本为空")
            raise HTTPException(status_code=400, detail="查询文本不能为空")
        
        if request.n_results < 1 or request.n_results > 20:
            logger.warning(f"返回结果数量超出范围 - n_results: {request.n_results}")
            raise HTTPException(status_code=400, detail="返回结果数量必须在1-20之间")
        
        strategy = request.strategy if hasattr(request, 'strategy') else "basic"
        enable_rerank = request.enable_rerank if hasattr(request, 'enable_rerank') else False
        
        if strategy != "basic" and hasattr(request, 'strategy'):
            logger.info(f"使用高级检索策略 - strategy: {strategy}")
            documents = advanced_rag_service.search(
                query=request.query,
                strategy=strategy,
                k=request.n_results,
                filters=request.filters,
                fetch_k=request.fetch_k if hasattr(request, 'fetch_k') else 20,
                lambda_mult=request.lambda_mult if hasattr(request, 'lambda_mult') else 0.5
            )
            
            if enable_rerank and hasattr(request, 'enable_rerank') and request.enable_rerank:
                logger.info("启用重排序")
                documents = reranker.rerank(
                    query=request.query,
                    documents=documents,
                    top_k=request.n_results
                )
            
            query_results = []
            for doc in documents:
                query_results.append(QueryResult(
                    document=doc.page_content,
                    metadata=doc.metadata,
                    distance=doc.metadata.get("distance"),
                    id=doc.metadata.get("chunk_index")
                ))
            
            logger.info(f"查询成功 - results: {len(query_results)}")
            return QueryResponse(
                success=True,
                message="查询成功",
                code=200,
                query=request.query,
                results=query_results,
                total=len(query_results)
            )
        else:
            logger.info("使用基础检索策略")
            result = rag_service.query_documents(
                query_text=request.query,
                n_results=request.n_results,
                filters=request.filters
            )
            
            if result["success"]:
                if enable_rerank and hasattr(request, 'enable_rerank') and request.enable_rerank:
                    logger.info("启用重排序")
                    from langchain_core.documents import Document
                    docs = []
                    for r in result["results"]:
                        docs.append(Document(
                            page_content=r["document"],
                            metadata=r.get("metadata", {})
                        ))
                    docs = reranker.rerank(
                        query=request.query,
                        documents=docs,
                        top_k=request.n_results
                    )
                    result["results"] = [
                        {
                            "document": doc.page_content,
                            "metadata": doc.metadata,
                            "distance": doc.metadata.get("distance"),
                            "id": doc.metadata.get("chunk_index")
                        }
                        for doc in docs
                    ]
                
                query_results = [
                    QueryResult(**r) for r in result["results"]
                ]
                logger.info(f"查询成功 - results: {len(query_results)}")
                return QueryResponse(
                    success=True,
                    message="查询成功",
                    code=200,
                    query=result["query"],
                    results=query_results,
                    total=result["total"]
                )
            else:
                logger.error(f"查询失败 - message: {result.get('message', '查询失败')}")
                return QueryResponse(
                    success=False,
                    message=result.get("message", "查询失败"),
                    code=500,
                    query=request.query,
                    results=[],
                    total=0
                )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询文档失败 - query: {request.query[:100]}, error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询文档失败: {str(e)}")


@router.delete("/document", response_model=TaskSubmitResponse)
async def delete_document(request: DeleteRequest):
    """
    删除文档（异步任务）
    
    Args:
        file_hash: 文件哈希值
        
    返回任务ID，可通过 /task/{task_id} 查询处理状态
    """
    try:
        logger.info(f"删除文档 - file_hash: {request.file_hash}")
        
        if not request.file_hash or not request.file_hash.strip():
            logger.warning("文件哈希为空")
            raise HTTPException(status_code=400, detail="文件哈希不能为空")
        
        task_id = str(uuid.uuid4())
        
        task = delete_document_task.delay(
            task_id=task_id,
            file_hash=request.file_hash
        )
        
        logger.info(f"删除文档任务已提交 - file_hash: {request.file_hash}, task_id: {task.id}")
        return TaskSubmitResponse(
            success=True,
            message="删除任务已提交，正在后台处理",
            code=202,
            task_id=task.id
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败 - file_hash: {request.file_hash}, error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")


@router.get("/documents", response_model=DocumentsListResponse)
async def list_documents():
    """
    获取所有文档列表
    """
    try:
        logger.info("获取文档列表")
        documents = rag_service.get_all_documents()
        document_infos = [DocumentInfo(**doc) for doc in documents]
        
        logger.info(f"获取文档列表成功 - total: {len(document_infos)}")
        return DocumentsListResponse(
            documents=document_infos,
            total=len(document_infos)
        )
    except Exception as e:
        logger.error(f"获取文档列表失败 - error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics():
    """
    获取系统统计信息
    """
    try:
        logger.info("获取系统统计信息")
        stats = rag_service.get_statistics()
        logger.info(f"获取系统统计信息成功 - documents: {stats.get('total_documents', 0)}, chunks: {stats.get('total_chunks', 0)}")
        return StatisticsResponse(**stats)
    except Exception as e:
        logger.error(f"获取统计信息失败 - error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/document/{file_hash}", response_model=DocumentDetailResponse)
async def get_document_info(file_hash: str):
    """
    获取指定文档的详细信息（包含完整内容）
    
    Args:
        file_hash: 文件哈希值
        
    Returns:
        文档详细信息，包含：
        - file_hash: 文件哈希
        - file_name: 文件名
        - chunks_count: 分片数量
        - uploaded_at: 上传时间
        - full_content: 完整文档内容（所有分片合并）
        - chunks: 分片列表（每个分片包含chunk_index、content、metadata）
    """
    try:
        logger.info(f"获取文档信息 - file_hash: {file_hash}")
        
        if not file_hash or not file_hash.strip():
            logger.warning("文件哈希为空")
            raise HTTPException(status_code=400, detail="文件哈希不能为空")
        
        doc_detail = rag_service.get_full_document_content(file_hash)
        if doc_detail is None:
            logger.warning(f"文档不存在 - file_hash: {file_hash}")
            raise HTTPException(status_code=404, detail="文档不存在")
        
        logger.info(f"获取文档信息成功 - file_hash: {file_hash}, chunks_count: {doc_detail.get('chunks_count')}")
        return DocumentDetailResponse(
            code=200,
            status="success",
            message="获取文档信息成功",
            data=doc_detail
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档信息失败 - file_hash: {file_hash}, error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档信息失败: {str(e)}")