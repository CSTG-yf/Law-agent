from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Optional
from pathlib import Path
import shutil
from app.service.rag.text_embedding import RAGDocumentService
from app.schema.rag import (
    UploadResponse,
    QueryRequest,
    QueryResponse,
    QueryResult,
    DeleteRequest,
    DeleteResponse,
    DocumentsListResponse,
    DocumentInfo,
    StatisticsResponse
)

router = APIRouter(prefix="/rag", tags=["RAG"])

rag_service = RAGDocumentService(upload_dir="uploads")


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(..., description="上传的文件"),
    metadata: Optional[str] = Form(None, description="额外的元数据（JSON格式）")
):
    """
    上传文档并处理存储到向量数据库
    
    支持的文件格式：
    - PDF (.pdf)
    - Word文档 (.docx, .doc)
    - 文本文件 (.txt, .md)
    - Excel文件 (.xlsx, .xls)
    """
    try:
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        file_path = upload_dir / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        extra_metadata = None
        if metadata:
            import json
            try:
                extra_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                pass
        
        result = rag_service.process_and_store_document(
            file_path=str(file_path),
            file_name=file.filename,
            metadata=extra_metadata
        )
        
        if result["success"]:
            return UploadResponse(
                success=True,
                message=result["message"],
                code=200,
                file_name=result.get("file_name"),
                file_hash=result.get("file_hash"),
                chunks_count=result.get("chunks_count"),
                document_ids=result.get("document_ids")
            )
        else:
            message = result.get("message", "未知错误")
            
            if "文件已存在" in message or "重复文件" in message:
                return UploadResponse(
                    success=False,
                    message=message,
                    code=409
                )
            elif "文件内容为空" in message or "无法提取文本" in message:
                return UploadResponse(
                    success=False,
                    message=message,
                    code=400
                )
            elif "计算文件哈希失败" in message:
                return UploadResponse(
                    success=False,
                    message=message,
                    code=500
                )
            else:
                return UploadResponse(
                    success=False,
                    message=message,
                    code=500
                )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传文件失败: {str(e)}")


@router.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    查询相似文档
    
    Args:
        query: 查询文本
        n_results: 返回结果数量（默认5，最大20）
        filters: 过滤条件（可选）
    """
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="查询文本不能为空")
        
        if request.n_results < 1 or request.n_results > 20:
            raise HTTPException(status_code=400, detail="返回结果数量必须在1-20之间")
        
        result = rag_service.query_documents(
            query_text=request.query,
            n_results=request.n_results,
            filters=request.filters
        )
        
        if result["success"]:
            query_results = [
                QueryResult(**r) for r in result["results"]
            ]
            return QueryResponse(
                success=True,
                message="查询成功",
                code=200,
                query=result["query"],
                results=query_results,
                total=result["total"]
            )
        else:
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
        raise HTTPException(status_code=500, detail=f"查询文档失败: {str(e)}")


@router.delete("/document", response_model=DeleteResponse)
async def delete_document(request: DeleteRequest):
    """
    删除文档
    
    Args:
        file_hash: 文件哈希值
    """
    try:
        if not request.file_hash or not request.file_hash.strip():
            raise HTTPException(status_code=400, detail="文件哈希不能为空")
        
        result = rag_service.delete_document(request.file_hash)
        
        if result["success"]:
            return DeleteResponse(
                success=True,
                message=result["message"],
                code=200,
                file_hash=result.get("file_hash"),
                deleted_chunks=result.get("deleted_chunks")
            )
        else:
            message = result.get("message", "删除失败")
            
            if "文件不存在" in message:
                return DeleteResponse(
                    success=False,
                    message=message,
                    code=404,
                    file_hash=request.file_hash
                )
            else:
                return DeleteResponse(
                    success=False,
                    message=message,
                    code=500,
                    file_hash=request.file_hash
                )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")


@router.get("/documents", response_model=DocumentsListResponse)
async def list_documents():
    """
    获取所有文档列表
    """
    try:
        documents = rag_service.get_all_documents()
        document_infos = [DocumentInfo(**doc) for doc in documents]
        
        return DocumentsListResponse(
            documents=document_infos,
            total=len(document_infos)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics():
    """
    获取系统统计信息
    """
    try:
        stats = rag_service.get_statistics()
        return StatisticsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/document/{file_hash}")
async def get_document_info(file_hash: str):
    """
    获取指定文档的详细信息
    
    Args:
        file_hash: 文件哈希值
    """
    try:
        if not file_hash or not file_hash.strip():
            raise HTTPException(status_code=400, detail="文件哈希不能为空")
        
        doc_info = rag_service.get_document_info(file_hash)
        if doc_info is None:
            raise HTTPException(status_code=404, detail="文档不存在")
        return doc_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档信息失败: {str(e)}")