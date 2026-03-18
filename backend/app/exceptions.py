class DocumentProcessingError(Exception):
    """文档处理异常"""
    pass


class DuplicateFileError(DocumentProcessingError):
    """重复文件异常"""
    pass


class FileProcessingError(DocumentProcessingError):
    """文件处理异常"""
    pass


class VectorDBError(DocumentProcessingError):
    """向量数据库异常"""
    pass