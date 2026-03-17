import hashlib
from typing import Optional
from pathlib import Path


class FileHasher:
    """文件哈希计算器，用于文件去重"""
    
    @staticmethod
    def calculate_md5(file_path: str) -> Optional[str]:
        """
        计算文件的MD5哈希值
        
        Args:
            file_path: 文件路径
            
        Returns:
            MD5哈希值，如果计算失败返回None
        """
        try:
            md5_hash = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        except Exception as e:
            print(f"计算MD5失败: {e}")
            return None
    
    @staticmethod
    def calculate_md5_from_bytes(file_content: bytes) -> str:
        """
        从字节内容计算MD5哈希值
        
        Args:
            file_content: 文件字节内容
            
        Returns:
            MD5哈希值
        """
        md5_hash = hashlib.md5()
        md5_hash.update(file_content)
        return md5_hash.hexdigest()
    
    @staticmethod
    def is_file_duplicate(file_path: str, existing_hashes: set) -> tuple[bool, Optional[str]]:
        """
        检查文件是否重复
        
        Args:
            file_path: 文件路径
            existing_hashes: 已存在的哈希值集合
            
        Returns:
            (是否重复, MD5哈希值)
        """
        md5_hash = FileHasher.calculate_md5(file_path)
        if md5_hash is None:
            return False, None
        
        is_duplicate = md5_hash in existing_hashes
        return is_duplicate, md5_hash