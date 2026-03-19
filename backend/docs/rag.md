---------------------------------------------------------------------------------------------------
RAG文档管理功能

功能特性：
- 文件上传与向量化存储
- MD5哈希去重机制
- 支持多种文件格式（PDF、Word、Excel、TXT、Markdown）
- 智能文本分割与嵌入
- 向量相似度检索
- 文档管理（查询、删除、统计）

高级检索特性：
- 混合检索（向量检索 + BM25关键词检索）
- MMR多样性检索
- 多查询检索
- Cross-Encoder重排序

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
   - strategy: 检索策略（可选，默认"basic"）
     - "basic": 基础向量检索
     - "hybrid": 混合检索（向量 + BM25）
     - "mmr": MMR多样性检索
     - "multi_query": 多查询检索
   - enable_rerank: 是否启用重排序（可选，默认false）
   - fetch_k: MMR初始获取数量（可选，默认20）
   - lambda_mult: MMR多样性因子（可选，默认0.5，范围0-1）
   
   示例：
   ```bash
   # 基础查询
   curl -X POST "http://localhost:8000/api/v1/rag/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "合同纠纷处理", "n_results": 5}'
   
   # 混合检索 + 重排序
   curl -X POST "http://localhost:8000/api/v1/rag/query" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "劳动合同法第39条",
       "n_results": 5,
       "strategy": "hybrid",
       "enable_rerank": true
     }'
   
   # MMR多样性检索
   curl -X POST "http://localhost:8000/api/v1/rag/query" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "知识产权侵权赔偿",
       "n_results": 5,
       "strategy": "mmr",
       "fetch_k": 20,
       "lambda_mult": 0.5
     }'
   
   # 多查询检索
   curl -X POST "http://localhost:8000/api/v1/rag/query" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "房屋租赁合同违约",
       "n_results": 5,
       "strategy": "multi_query"
     }'
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

7. 查询任务状态
   GET /api/v1/rag/task/{task_id}
   
   示例：
   ```bash
   curl -X GET "http://localhost:8000/api/v1/rag/task/abc123-task-id"
   ```

8. 获取任务结果
   GET /api/v1/rag/task/{task_id}/result
   
   示例：
   ```bash
   curl -X GET "http://localhost:8000/api/v1/rag/task/abc123-task-id/result"
   ```

---------------------------------------------------------------------------------------------------
检索策略说明

1. basic - 基础向量检索
   - 使用嵌入模型将查询转换为向量
   - 计算与文档向量的相似度
   - 返回最相似的文档
   - 适用场景：语义理解、同义词匹配

2. hybrid - 混合检索
   - 结合向量检索和BM25关键词检索
   - 使用倒数排名融合（RRF）合并结果
   - 权重：70%向量 + 30%BM25
   - 适用场景：法律条文、专有名词、精确匹配

3. mmr - MMR多样性检索
   - 平衡相关性和多样性
   - lambda_mult参数控制：
     - 0: 最大多样性
     - 1: 最大相关性
     - 0.5: 平衡（默认）
   - 适用场景：需要多样化结果的场景

4. multi_query - 多查询检索
   - 自动生成查询变体
   - 合并多个查询结果
   - 提高召回率
   - 适用场景：需要全面覆盖的场景

---------------------------------------------------------------------------------------------------
重排序说明

启用重排序后，会对检索结果进行二次排序：
- 使用Cross-Encoder模型（ms-marco-MiniLM）
- 对查询和文档进行精细匹配打分
- 提升检索精度

适用场景：
- 对检索精度要求高的场景
- 法律条文精确匹配
- 案例相关性判断

---------------------------------------------------------------------------------------------------
响应格式

查询响应示例：
```json
{
  "success": true,
  "message": "查询成功",
  "code": 200,
  "query": "劳动合同法第39条",
  "results": [
    {
      "document": "劳动合同法第三十九条规定...",
      "metadata": {
        "file_name": "劳动法.pdf",
        "chunk_index": 0,
        "distance": 0.15,
        "rerank_score": 0.92
      },
      "id": "abc123_chunk_0"
    }
  ],
  "total": 5
}
```

任务状态响应示例：
```json
{
  "task_id": "abc123-task-id",
  "status": "completed",
  "progress": 100,
  "message": "处理完成"
}
```

状态值：
- pending: 等待中
- processing: 处理中
- completed: 已完成
- failed: 失败
