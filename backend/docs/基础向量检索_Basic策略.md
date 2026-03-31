# 基础向量检索 (Basic) 策略详解

## 1. 什么是基础向量检索？

**基础向量检索（Basic Vector Retrieval）** 是最简单也是最常用的 RAG 检索策略。它基于**向量相似度**进行语义检索，将查询文本和文档都转换为向量，然后在向量空间中查找最相似的文档。

---

## 2. 原理

### 2.1 核心流程

```
查询文本 → 向量化 → 向量数据库检索 → 余弦相似度计算 → 返回 Top-K 结果
```

### 2.2 向量化过程

1. **文本预处理**：分词、去停用词、标准化
2. **向量化**：使用预训练模型（如 BERT、Sentence-Transformer）将文本转换为稠密向量
3. **向量存储**：将向量存入向量数据库（如 Chroma、Milvus、FAISS）

### 2.3 相似度计算

最常用的是**余弦相似度**：

```
cosine_similarity(A, B) = (A · B) / (||A|| × ||B||)
```

其中：
- `A · B` 是向量点积
- `||A||` 和 `||B||` 是向量的 L2 范数

### 2.4 检索过程

1. 将查询文本向量化得到查询向量 `q`
2. 在向量数据库中计算 `q` 与所有文档向量的相似度
3. 按相似度降序排列，返回前 K 个文档

---

## 3. 项目中的实现

项目中基础向量检索在 `app/service/rag/hybrid_retriever.py` 的 `AdvancedRAGService.search()` 方法中实现：

```python
def search(
    self,
    query: str,
    strategy: str = "basic",  # 默认策略
    k: int = 5,
    filters: Optional[Dict[str, Any]] = None,
    ...
) -> List[Document]:
    # 其他策略分支...
    else:
        # 基础向量检索
        result = self.vector_store.query(query, n_results=k, where=filters)
        docs = []
        if result.get("documents") and result["documents"][0]:
            for i, doc_text in enumerate(result["documents"][0]):
                metadata = result["metadatas"][0][i] if result.get("metadatas") else {}
                distance = result["distances"][0][i] if result.get("distances") else 0
                doc = Document(
                    page_content=doc_text,
                    metadata={**metadata, "distance": distance}
                )
                docs.append(doc)
        return docs
```

### 向量存储查询

核心调用 `ChromaVectorStore.query()`：

```python
def query(self, query_text: str, n_results: int = 5, where: dict = None):
    """
    查询向量数据库
    
    Args:
        query_text: 查询文本
        n_results: 返回结果数量
        where: 过滤条件
    
    Returns:
        包含 documents, metadatas, distances 的结果
    """
    query_embedding = self.embedding_service.embed_text_sync(query_text)
    
    results = self.collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where
    )
    
    return results
```

---

## 4. 参数说明

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `query` | str | 查询文本 | - |
| `k` / `n_results` | int | 返回结果数量 | 5 |
| `filters` | dict | 过滤条件（如元数据筛选） | None |
| `distance_threshold` | float | 距离阈值过滤 | None |

### 距离度量

项目使用 Chroma 默认的**余弦距离**：

| 距离值 | 相似度 |
|--------|--------|
| 0 | 完全相同 |
| 0-0.5 | 高相似 |
| 0.5-1.0 | 低相似 |
| 1.0 | 完全不相关 |

---

## 5. 特点

### 优点

| 优点 | 说明 |
|------|------|
| **理解语义关系** | 能够理解查询的语义，不只是关键词匹配 |
| **跨语言检索** | 支持跨语言语义匹配 |
| **实现简单** | 逻辑清晰，易于理解和维护 |
| **检索速度快** | 适合大规模文档库 |

### 缺点

| 缺点 | 说明 |
|------|------|
| **无法精确匹配关键词** | 语义相似但关键词不同的文档可能被遗漏 |
| **计算成本较高** | 需要为每个查询计算向量相似度 |
| **对专业术语敏感度低** | 特定领域的术语可能无法准确理解 |
| **长文本信息丢失** | 长文档压缩成向量可能丢失细节 |

---

## 6. 适用场景

### 适合的场景

- **概念性查询**：如 "什么是劳动仲裁？"
- **语义相似查询**：如 "员工离职补偿" 与 "劳动合同解除经济补偿"
- **跨语言检索**：如用中文查询英文文档
- **快速原型验证**：需要快速搭建 RAG 系统时

### 不适合的场景

- **精确关键词匹配**：如法律条款编号查询
- **需要高召回**：如需要找到所有相关文档
- **专业术语密集**：如特定领域的专业文档

---

## 7. 与其他策略对比

| 特性 | Basic | Hybrid | MMR | Multi-Query | +Rerank |
|------|-------|--------|-----|-------------|---------|
| **召回率** | 中 | 高 | 中 | ⭐⭐⭐⭐⭐ | - |
| **精确度** | 中 | 高 | 中 | 中 | ⭐⭐⭐⭐⭐ |
| **速度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **多样性** | 低 | 中 | ⭐⭐⭐⭐⭐ | 中 | - |
| **复杂度** | 低 | 中 | 高 | 中 | 高 |

---

## 8. API 调用示例

### REST API

```bash
# 基础向量检索
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "劳动合同解除赔偿",
    "n_results": 5,
    "strategy": "basic"
  }'
```

### Python SDK

```python
from app.service.rag.hybrid_retriever import AdvancedRAGService
from app.service.vector_db import ChromaVectorStore

vector_store = ChromaVectorStore(collection_name="legal_documents")
rag_service = AdvancedRAGService(vector_store)

# 基础向量检索
docs = rag_service.search(
    query="劳动合同解除赔偿",
    strategy="basic",
    k=5
)

for doc in docs:
    print(f"内容: {doc.page_content[:100]}...")
    print(f"距离: {doc.metadata.get('distance')}")
```

### 返回结果示例

```json
{
  "code": 200,
  "status": "success",
  "data": {
    "results": [
      {
        "page_content": "根据《劳动合同法》第四十七条...",
        "metadata": {
          "source": "file_1.pdf",
          "distance": 0.234
        }
      }
    ]
  }
}
```

---

## 9. 性能优化建议

### 9.1 向量维度选择

| 维度 | 特点 | 适用场景 |
|------|------|----------|
| 768 | 标准 BERT 维度 | 通用场景 |
| 384 | 较小维度 | 内存受限场景 |
| 1024 | 较大维度 | 高精度场景 |

### 9.2 索引优化

```python
# 使用 HNSW 索引（默认）
collection = client.create_collection(
    name="legal_documents",
    metadata={"hnsw:space": "cosine"}
)

# HNSW 参数调优
collection = client.create_collection(
    name="legal_documents",
    metadata={
        "hnsw:space": "cosine",
        "hnsw:construction_ef": 200,  # 索引构建时的探索因子
        "hnsw:search_ef": 100          # 搜索时的探索因子
    }
)
```

### 9.3 批量查询

```python
# 批量向量化
queries = ["查询1", "查询2", "查询3"]
embeddings = embedding_service.embed_texts_sync(queries)

# 批量检索
results = collection.query(
    query_embeddings=embeddings,
    n_results=5
)
```

---

## 10. 最佳实践

1. **从 Basic 开始**：先使用基础检索验证流程，再根据需要升级
2. **监控距离分布**：观察返回结果的 distance 值，调整 n_results
3. **结合过滤条件**：使用 filters 缩小检索范围，提高精度
4. **评估召回率**：检查返回结果是否覆盖了预期的相关文档

---

## 11. 参考资料

- [Chroma Vector Store](https://docs.trychroma.com/)
- [Sentence-Transformers](https://sbert.net/)
- [向量检索综述](https://arxiv.org/abs/2103.10023)