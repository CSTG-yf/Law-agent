import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.service.rag.file_hasher import FileHasher
from app.core.logger import get_logger

logger = get_logger("graph_document_manager")


class GraphDocumentManager:
    """知识图谱文档管理器，维护文档hash表"""
    
    def __init__(self, data_dir: str = "graph_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.hash_file = self.data_dir / "graph_documents.json"
        self.file_hashes: Dict[str, Dict[str, Any]] = {}
        self.file_hasher = FileHasher()
        
        self._load_hashes()
    
    def _load_hashes(self):
        """加载已存在的文件哈希"""
        try:
            if self.hash_file.exists():
                with open(self.hash_file, 'r', encoding='utf-8') as f:
                    self.file_hashes = json.load(f)
                logger.info(f"加载知识图谱文档hash表 - count: {len(self.file_hashes)}")
        except Exception as e:
            logger.error(f"加载知识图谱文档hash表失败 - error: {str(e)}")
            self.file_hashes = {}
    
    def _save_hashes(self):
        """保存文件哈希到文件"""
        try:
            with open(self.hash_file, 'w', encoding='utf-8') as f:
                json.dump(self.file_hashes, f, ensure_ascii=False, indent=2)
            logger.debug("保存知识图谱文档hash表成功")
        except Exception as e:
            logger.error(f"保存知识图谱文档hash表失败 - error: {str(e)}")
    
    def calculate_file_hash(self, file_path: str) -> Optional[str]:
        """计算文件MD5哈希"""
        return self.file_hasher.calculate_md5(file_path)
    
    def is_duplicate(self, file_hash: str) -> bool:
        """检查文件是否已存在"""
        return file_hash in self.file_hashes
    
    def register_document(
        self,
        file_hash: str,
        file_name: str,
        file_path: str,
        document_type: str,
        nodes_count: int = 0,
        relationships_count: int = 0
    ) -> Dict[str, Any]:
        """注册新文档"""
        try:
            self.file_hashes[file_hash] = {
                "file_name": file_name,
                "file_path": file_path,
                "document_type": document_type,
                "nodes_count": nodes_count,
                "relationships_count": relationships_count,
                "uploaded_at": datetime.now().isoformat(),
                "status": "completed"
            }
            self._save_hashes()
            
            logger.info(
                f"注册知识图谱文档 - "
                f"file: {file_name}, hash: {file_hash[:8]}..., "
                f"nodes: {nodes_count}, relationships: {relationships_count}"
            )
            
            return {
                "success": True,
                "message": "文档注册成功",
                "file_hash": file_hash
            }
        except Exception as e:
            logger.error(f"注册文档失败 - error: {str(e)}")
            return {
                "success": False,
                "message": f"注册文档失败: {str(e)}"
            }
    
    def update_document_status(
        self,
        file_hash: str,
        status: str,
        error_message: str = None
    ):
        """更新文档状态"""
        if file_hash in self.file_hashes:
            self.file_hashes[file_hash]["status"] = status
            if error_message:
                self.file_hashes[file_hash]["error_message"] = error_message
            self._save_hashes()
    
    def update_document_stats(
        self,
        file_hash: str,
        nodes_count: int,
        relationships_count: int
    ):
        """更新文档统计信息"""
        if file_hash in self.file_hashes:
            self.file_hashes[file_hash]["nodes_count"] = nodes_count
            self.file_hashes[file_hash]["relationships_count"] = relationships_count
            self.file_hashes[file_hash]["status"] = "completed"
            self._save_hashes()
    
    def get_document(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """获取文档信息"""
        return self.file_hashes.get(file_hash)
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """获取所有文档列表"""
        return [
            {
                "file_hash": file_hash,
                **info
            }
            for file_hash, info in self.file_hashes.items()
        ]
    
    def delete_document(self, file_hash: str) -> Dict[str, Any]:
        """删除文档记录"""
        if file_hash not in self.file_hashes:
            return {
                "success": False,
                "message": "文档不存在"
            }
        
        doc_info = self.file_hashes[file_hash]
        del self.file_hashes[file_hash]
        self._save_hashes()
        
        logger.info(f"删除知识图谱文档记录 - file: {doc_info.get('file_name')}")
        
        return {
            "success": True,
            "message": "文档记录删除成功",
            "file_name": doc_info.get("file_name")
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_documents = len(self.file_hashes)
        total_nodes = sum(
            info.get("nodes_count", 0) 
            for info in self.file_hashes.values()
        )
        total_relationships = sum(
            info.get("relationships_count", 0) 
            for info in self.file_hashes.values()
        )
        
        by_type = {}
        for info in self.file_hashes.values():
            doc_type = info.get("document_type", "unknown")
            by_type[doc_type] = by_type.get(doc_type, 0) + 1
        
        return {
            "total_documents": total_documents,
            "total_nodes": total_nodes,
            "total_relationships": total_relationships,
            "by_type": by_type
        }


graph_document_manager = GraphDocumentManager()
