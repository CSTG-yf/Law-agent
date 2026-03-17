from typing import List, Optional, Dict, Any
import chromadb
from app.core.config import settings
from app.service.rag.ollama_embedding import OllamaEmbedding


class ChromaVectorStore:
    """ChromaDB向量存储服务"""
    
    def __init__(self, collection_name: str = "legal_documents"):
        """
        初始化ChromaDB向量存储
        
        Args:
            collection_name: 集合名称
        """
        self.client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT
        )
        self.collection_name = collection_name
        self.collection = self._get_or_create_collection()
        self.embedding_service = OllamaEmbedding()
    
    def _get_or_create_collection(self):
        """获取或创建集合"""
        try:
            collection = self.client.get_collection(name=self.collection_name)
        except:
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Legal documents collection"}
            )
        return collection
    
    def add_documents(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> bool:
        """
        添加文档到向量数据库
        
        Args:
            texts: 文本列表
            metadatas: 元数据列表
            ids: 文档ID列表
            
        Returns:
            是否成功
        """
        try:
            embeddings = self.embedding_service.embed_texts_sync(texts)
            
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            return True
        except Exception as e:
            print(f"添加文档失败: {e}")
            return False
    
    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        查询相似文档
        
        Args:
            query_text: 查询文本
            n_results: 返回结果数量
            where: 元数据过滤条件
            where_document: 文档内容过滤条件
            
        Returns:
            查询结果
        """
        try:
            query_embedding = self.embedding_service.embed_text_sync(query_text)
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document
            )
            return results
        except Exception as e:
            print(f"查询失败: {e}")
            return {"documents": [], "metadatas": [], "distances": [], "ids": []}
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取文档
        
        Args:
            doc_id: 文档ID
            
        Returns:
            文档信息
        """
        try:
            results = self.collection.get(ids=[doc_id])
            if results["ids"]:
                return {
                    "id": results["ids"][0],
                    "document": results["documents"][0] if results["documents"] else None,
                    "metadata": results["metadatas"][0] if results["metadatas"] else None
                }
            return None
        except Exception as e:
            print(f"获取文档失败: {e}")
            return None
    
    def delete_document(self, doc_id: str) -> bool:
        """
        删除文档
        
        Args:
            doc_id: 文档ID
            
        Returns:
            是否成功
        """
        try:
            self.collection.delete(ids=[doc_id])
            return True
        except Exception as e:
            print(f"删除文档失败: {e}")
            return False
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """
        获取所有文档
        
        Returns:
            所有文档列表
        """
        try:
            results = self.collection.get()
            documents = []
            for i, doc_id in enumerate(results["ids"]):
                documents.append({
                    "id": doc_id,
                    "document": results["documents"][i] if results["documents"] else None,
                    "metadata": results["metadatas"][i] if results["metadatas"] else None
                })
            return documents
        except Exception as e:
            print(f"获取所有文档失败: {e}")
            return []
    
    def count_documents(self) -> int:
        """
        统计文档数量
        
        Returns:
            文档数量
        """
        try:
            return self.collection.count()
        except Exception as e:
            print(f"统计文档数量失败: {e}")
            return 0