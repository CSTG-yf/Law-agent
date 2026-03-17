---------------------------------------------------------------------------------------------------
RAG文档管理功能

功能特性：
- 文件上传与向量化存储
- MD5哈希去重机制
- 支持多种文件格式（PDF、Word、Excel、TXT、Markdown）
- 智能文本分割与嵌入
- 向量相似度检索
- 文档管理（查询、删除、统计）

支持的文件格式：
- PDF (.pdf)
- Word文档 (.docx, .doc)
- 文本文件 (.txt, .md)
- Excel文件 (.xlsx, .xls)

API接口：

1. 上传文档
   POST /api/v1/rag/upload
   参数：
   - file: 上传的文件（必需）
   - metadata: 额外的元数据（可选，JSON格式）
   
   示例：
   ```bash
   curl -X POST "http://localhost:8000/api/v1/rag/upload" \
     -F "file=@legal_document.pdf"
   ```

2. 查询相似文档
   POST /api/v1/rag/query
   参数：
   - query: 查询文本（必需）
   - n_results: 返回结果数量（默认5，最大20）
   - filters: 过滤条件（可选）
   
   示例：
   ```bash
   curl -X POST "http://localhost:8000/api/v1/rag/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "合同纠纷处理", "n_results": 5}'
   ```

3. 获取所有文档列表
   GET /api/v1/rag/documents
   
   示例：
   ```bash
   curl -X GET "http://localhost:8000/api/v1/rag/documents"
   ```

4. 获取文档详情
   GET /api/v1/rag/document/{file_hash}
   
   示例：
   ```bash
   curl -X GET "http://localhost:8000/api/v1/rag/document/abc123def456"
   ```

5. 删除文档
   DELETE /api/v1/rag/document
   参数：
   - file_hash: 文件哈希值（必需）
   
   示例：
   ```bash
   curl -X DELETE "http://localhost:8000/api/v1/rag/document" \
     -H "Content-Type: application/json" \
     -d '{"file_hash": "abc123def456"}'
   ```

6. 获取统计信息
   GET /api/v1/rag/statistics
   
   示例：
   ```bash
   curl -X GET "http://localhost:8000/api/v1/rag/statistics"
   ```

