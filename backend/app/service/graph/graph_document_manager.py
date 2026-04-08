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
        self.file_hasher = FileHasher()
        
        logger.info("知识图谱文档管理器初始化完成")
    
    def _load_hashes_from_file(self) -> Dict[str, Dict[str, Any]]:
        """直接从文件加载文件哈希"""
        try:
            if self.hash_file.exists():
                with open(self.hash_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"加载知识图谱文档hash表失败 - error: {str(e)}")
            return {}
    
    def _save_hashes_to_file(self, file_hashes: Dict[str, Dict[str, Any]]):
        """保存文件哈希到文件"""
        try:
            with open(self.hash_file, 'w', encoding='utf-8') as f:
                json.dump(file_hashes, f, ensure_ascii=False, indent=2)
            logger.debug("保存知识图谱文档hash表成功")
        except Exception as e:
            logger.error(f"保存知识图谱文档hash表失败 - error: {str(e)}")
    
    def calculate_file_hash(self, file_path: str) -> Optional[str]:
        """计算文件MD5哈希"""
        return self.file_hasher.calculate_md5(file_path)
    
    def is_duplicate(self, file_hash: str) -> bool:
        """检查文件是否已存在"""
        file_hashes = self._load_hashes_from_file()
        return file_hash in file_hashes
    
    def register_document(
        self,
        file_hash: str,
        file_name: str,
        file_path: str,
        document_type: str,
        nodes_count: int = 0,
        relationships_count: int = 0
    ) -> Dict[str, Any]:
        """准备新文档数据（仅在内存中，不保存到文件）"""
        doc_info = {
            "file_name": file_name,
            "file_path": file_path,
            "document_type": document_type,
            "nodes_count": nodes_count,
            "relationships_count": relationships_count,
            "uploaded_at": datetime.now().isoformat(),
            "status": "processing"
        }
        
        logger.info(
            f"准备知识图谱文档数据 - "
            f"file: {file_name}, hash: {file_hash[:8]}..."
        )
        
        return {
            "success": True,
            "message": "文档数据准备完成",
            "file_hash": file_hash,
            "doc_info": doc_info
        }
    
    def update_document_status(
        self,
        file_hash: str,
        status: str,
        error_message: str = None
    ):
        """更新文档状态"""
        file_hashes = self._load_hashes_from_file()
        if file_hash in file_hashes:
            file_hashes[file_hash]["status"] = status
            if error_message:
                file_hashes[file_hash]["error_message"] = error_message
            self._save_hashes_to_file(file_hashes)
    
    def save_document(
        self,
        file_hash: str,
        doc_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """保存文档到文件（在构建成功后调用）"""
        try:
            file_hashes = self._load_hashes_from_file()
            file_hashes[file_hash] = doc_info
            self._save_hashes_to_file(file_hashes)
            
            logger.info(
                f"保存知识图谱文档 - "
                f"file: {doc_info.get('file_name')}, hash: {file_hash[:8]}..."
            )
            
            return {
                "success": True,
                "message": "文档保存成功"
            }
        except Exception as e:
            logger.error(f"保存文档失败 - error: {str(e)}")
            return {
                "success": False,
                "message": f"保存文档失败: {str(e)}"
            }
    
    def update_document_stats(
        self,
        file_hash: str,
        nodes_count: int,
        relationships_count: int
    ):
        """更新文档统计信息"""
        file_hashes = self._load_hashes_from_file()
        if file_hash in file_hashes:
            file_hashes[file_hash]["nodes_count"] = nodes_count
            file_hashes[file_hash]["relationships_count"] = relationships_count
            file_hashes[file_hash]["status"] = "completed"
            self._save_hashes_to_file(file_hashes)
    
    def get_document(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """获取文档信息"""
        file_hashes = self._load_hashes_from_file()
        return file_hashes.get(file_hash)
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """获取所有文档列表"""
        file_hashes = self._load_hashes_from_file()
        return [
            {
                "file_hash": file_hash,
                **info
            }
            for file_hash, info in file_hashes.items()
        ]
    
    def delete_document(self, file_hash: str) -> Dict[str, Any]:
        """删除文档记录"""
        file_hashes = self._load_hashes_from_file()
        if file_hash not in file_hashes:
            return {
                "success": False,
                "message": "文档不存在"
            }
        
        doc_info = file_hashes[file_hash]
        del file_hashes[file_hash]
        self._save_hashes_to_file(file_hashes)
        
        logger.info(f"删除知识图谱文档记录 - file: {doc_info.get('file_name')}")
        
        return {
            "success": True,
            "message": "文档记录删除成功",
            "file_name": doc_info.get("file_name")
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        file_hashes = self._load_hashes_from_file()
        total_documents = len(file_hashes)
        total_nodes = sum(
            info.get("nodes_count", 0) 
            for info in file_hashes.values()
        )
        total_relationships = sum(
            info.get("relationships_count", 0) 
            for info in file_hashes.values()
        )
        
        by_type = {}
        for info in file_hashes.values():
            doc_type = info.get("document_type", "unknown")
            by_type[doc_type] = by_type.get(doc_type, 0) + 1
        
        return {
            "total_documents": total_documents,
            "total_nodes": total_nodes,
            "total_relationships": total_relationships,
            "by_type": by_type
        }


graph_document_manager = GraphDocumentManager()
