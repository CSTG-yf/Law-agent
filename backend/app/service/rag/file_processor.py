from typing import List, Optional
from pathlib import Path
import pypdf
import docx2txt
from langchain_text_splitters import RecursiveCharacterTextSplitter


class FileProcessor:
    """文件处理器，支持多种文件格式"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        初始化文件处理器
        
        Args:
            chunk_size: 文本分块大小
            chunk_overlap: 文本分块重叠大小
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
        )
    
    def extract_text(self, file_path: str) -> str:
        """
        从文件中提取文本
        
        Args:
            file_path: 文件路径
            
        Returns:
            提取的文本内容
        """
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            return self._extract_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            return self._extract_docx(file_path)
        elif file_ext in ['.txt', '.md']:
            return self._extract_text_file(file_path)
        elif file_ext in ['.xlsx', '.xls']:
            return self._extract_excel(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_ext}")
    
    def _extract_pdf(self, file_path: str) -> str:
        """提取PDF文件文本"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"提取PDF文本失败: {e}")
            return ""
        return text
    
    def _extract_docx(self, file_path: str) -> str:
        """提取DOCX文件文本"""
        try:
            text = docx2txt.process(file_path)
            return text
        except Exception as e:
            print(f"提取DOCX文本失败: {e}")
            return ""
    
    def _extract_text_file(self, file_path: str) -> str:
        """提取文本文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='gbk') as file:
                    return file.read()
            except Exception as e:
                print(f"提取文本文件失败: {e}")
                return ""
        except Exception as e:
            print(f"提取文本文件失败: {e}")
            return ""
    
    def _extract_excel(self, file_path: str) -> str:
        """提取Excel文件文本"""
        try:
            from openpyxl import load_workbook
            workbook = load_workbook(file_path, read_only=True)
            text = ""
            for sheet in workbook:
                for row in sheet.iter_rows(values_only=True):
                    row_text = " ".join([str(cell) if cell is not None else "" for cell in row])
                    text += row_text + "\n"
            return text
        except Exception as e:
            print(f"提取Excel文本失败: {e}")
            return ""
    
    def split_text(self, text: str) -> List[str]:
        """
        将文本分割成块
        
        Args:
            text: 待分割的文本
            
        Returns:
            文本块列表
        """
        if not text or len(text.strip()) == 0:
            return []
        
        chunks = self.text_splitter.split_text(text)
        return chunks
    
    def process_file(self, file_path: str, metadata: dict = None) -> tuple[List[str], List[dict]]:
        """
        处理文件：提取文本并分割成块
        
        Args:
            file_path: 文件路径
            metadata: 基础元数据
            
        Returns:
            (文本块列表, 元数据列表)
        """
        text = self.extract_text(file_path)
        if not text:
            return [], []
        
        chunks = self.split_text(text)
        
        if metadata is None:
            metadata = {}
        
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunk_size": len(chunk)
            })
            metadatas.append(chunk_metadata)
        
        return chunks, metadatas