from typing import List, Dict, Any, Optional
from pathlib import Path
import shutil
from app.service.rag.file_hasher import FileHasher
from app.service.rag.file_processor import FileProcessor
from app.service.rag.ollama_embedding import OllamaEmbedding
from app.service.vector_db import ChromaVectorStore


class RAGDocumentService:
    """RAG文档处理服务"""
    
    def __init__(self, upload_dir: str = "uploads"):
        """
        初始化RAG文档服务
        
        Args:
            upload_dir: 文件上传目录
        """
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        
        self.file_hasher = FileHasher()
        self.file_processor = FileProcessor()
        self.embedding_service = OllamaEmbedding()
        self.vector_store = ChromaVectorStore(collection_name="legal_documents")
        
        self.file_hashes_db = {}
        self._load_file_hashes()
    
    def _load_file_hashes(self):
        """加载已存在的文件哈希"""
        try:
            hash_file = self.upload_dir / "file_hashes.json"
            if hash_file.exists():
                import json
                with open(hash_file, 'r', encoding='utf-8') as f:
                    self.file_hashes_db = json.load(f)
        except Exception as e:
            print(f"加载文件哈希数据库失败: {e}")
            self.file_hashes_db = {}
    
    def _save_file_hashes(self):
        """保存文件哈希到数据库"""
        try:
            hash_file = self.upload_dir / "file_hashes.json"
            import json
            with open(hash_file, 'w', encoding='utf-8') as f:
                json.dump(self.file_hashes_db, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存文件哈希数据库失败: {e}")
    
    def _get_file_id(self, file_hash: str, chunk_index: int) -> str:
        """生成文档ID"""
        return f"{file_hash}_chunk_{chunk_index}"
    
    def process_and_store_document(
        self,
        file_path: str,
        file_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理并存储文档到向量数据库
        
        Args:
            file_path: 文件路径
            file_name: 文件名
            metadata: 额外的元数据
            
        Returns:
            处理结果
        """
        try:
            file_hash = self.file_hasher.calculate_md5(file_path)
            if file_hash is None:
                return {
                    "success": False,
                    "message": "计算文件哈希失败",
                    "file_name": file_name
                }
            
            if file_hash in self.file_hashes_db:
                return {
                    "success": False,
                    "message": "文件已存在（重复文件）",
                    "file_name": file_name,
                    "file_hash": file_hash
                }
            
            chunks, chunk_metadatas = self.file_processor.process_file(file_path, metadata)
            
            if not chunks:
                return {
                    "success": False,
                    "message": "文件内容为空或无法提取文本",
                    "file_name": file_name
                }
            
            base_metadata = {
                "file_name": file_name,
                "file_hash": file_hash,
                "file_type": Path(file_name).suffix.lower()
            }
            
            final_metadatas = []
            for chunk_metadata in chunk_metadatas:
                final_metadata = base_metadata.copy()
                final_metadata.update(chunk_metadata)
                if metadata:
                    final_metadata.update(metadata)
                final_metadatas.append(final_metadata)
            
            ids = [self._get_file_id(file_hash, i) for i in range(len(chunks))]
            
            success = self.vector_store.add_documents(
                texts=chunks,
                metadatas=final_metadatas,
                ids=ids
            )
            
            if success:
                self.file_hashes_db[file_hash] = {
                    "file_name": file_name,
                    "file_path": file_path,
                    "chunks_count": len(chunks),
                    "uploaded_at": str(Path(file_path).stat().st_ctime)
                }
                self._save_file_hashes()
                
                return {
                    "success": True,
                    "message": "文档处理并存储成功",
                    "file_name": file_name,
                    "file_hash": file_hash,
                    "chunks_count": len(chunks),
                    "document_ids": ids
                }
            else:
                return {
                    "success": False,
                    "message": "文档存储到向量数据库失败",
                    "file_name": file_name
                }
                
        except Exception as e:
            print(f"处理文档失败: {e}")
            return {
                "success": False,
                "message": f"处理文档时发生错误: {str(e)}",
                "file_name": file_name
            }
    
    def query_documents(
        self,
        query_text: str,
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        查询相似文档
        
        Args:
            query_text: 查询文本
            n_results: 返回结果数量
            filters: 过滤条件
            
        Returns:
            查询结果
        """
        try:
            results = self.vector_store.query(
                query_text=query_text,
                n_results=n_results,
                where=filters
            )
            
            formatted_results = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    formatted_results.append({
                        "document": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] and results["metadatas"][0] else {},
                        "distance": results["distances"][0][i] if results["distances"] and results["distances"][0] else None,
                        "id": results["ids"][0][i] if results["ids"] and results["ids"][0] else None
                    })
            
            return {
                "success": True,
                "query": query_text,
                "results": formatted_results,
                "total": len(formatted_results)
            }
        except Exception as e:
            print(f"查询文档失败: {e}")
            return {
                "success": False,
                "message": f"查询文档时发生错误: {str(e)}",
                "results": []
            }
    
    def delete_document(self, file_hash: str) -> Dict[str, Any]:
        """
        删除文档
        
        Args:
            file_hash: 文件哈希
            
        Returns:
            删除结果
        """
        try:
            if file_hash not in self.file_hashes_db:
                return {
                    "success": False,
                    "message": "文件不存在",
                    "file_hash": file_hash
                }
            
            file_info = self.file_hashes_db[file_hash]
            chunks_count = file_info["chunks_count"]
            
            deleted_count = 0
            for i in range(chunks_count):
                doc_id = self._get_file_id(file_hash, i)
                if self.vector_store.delete_document(doc_id):
                    deleted_count += 1
            
            del self.file_hashes_db[file_hash]
            self._save_file_hashes()
            
            return {
                "success": True,
                "message": f"成功删除文档，共删除 {deleted_count} 个文本块",
                "file_hash": file_hash,
                "deleted_chunks": deleted_count
            }
        except Exception as e:
            print(f"删除文档失败: {e}")
            return {
                "success": False,
                "message": f"删除文档时发生错误: {str(e)}",
                "file_hash": file_hash
            }
    
    def get_document_info(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """
        获取文档信息
        
        Args:
            file_hash: 文件哈希
            
        Returns:
            文档信息
        """
        return self.file_hashes_db.get(file_hash)
    
    def get_full_document_content(self, file_hash: str) -> Dict[str, Any]:
        """
        获取文档完整内容（合并所有分片）
        
        Args:
            file_hash: 文件哈希
            
        Returns:
            包含基本信息和完整内容的字典
        """
        doc_info = self.file_hashes_db.get(file_hash)
        if doc_info is None:
            return None
        
        chunks = self.vector_store.get_documents_by_file_hash(file_hash)
        
        full_content = "\n\n".join([chunk["document"] for chunk in chunks if chunk["document"]])
        
        return {
            "file_hash": file_hash,
            "file_name": doc_info.get("file_name"),
            "chunks_count": doc_info.get("chunks_count"),
            "uploaded_at": doc_info.get("uploaded_at"),
            "full_content": full_content,
            "chunks": [
                {
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["document"],
                    "metadata": chunk["metadata"]
                }
                for chunk in chunks
            ]
        }
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """
        获取所有文档信息
        
        Returns:
            所有文档信息列表
        """
        return [
            {
                "file_hash": file_hash,
                "file_name": info["file_name"],
                "chunks_count": info["chunks_count"],
                "uploaded_at": info.get("uploaded_at")
            }
            for file_hash, info in self.file_hashes_db.items()
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息
        """
        total_documents = len(self.file_hashes_db)
        total_chunks = sum(info["chunks_count"] for info in self.file_hashes_db.values())
        
        return {
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "vector_db_count": self.vector_store.count_documents()
        }