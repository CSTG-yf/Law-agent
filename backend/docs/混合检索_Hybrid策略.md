# 混合检索 (Hybrid) 策略详解

## 1. 什么是混合检索？

**混合检索（Hybrid Search）** 结合了**向量检索**和**BM25 关键词检索**两种方法，取长补短，提高检索质量和召回率。

核心思想是：
> **向量检索擅长语义匹配，BM25 擅长精确关键词匹配，两者结合效果更好。**

---

## 2. 原理

### 2.1 整体流程

```
查询 → 向量检索 ─┐
              ├→ RRF 融合 → 排序 → 返回结果
查询 → BM25 检索 ─┘
```

### 2.2 向量检索

基于语义相似度检索，使用余弦距离计算：

```
优点：
- 理解语义关系
- 支持同义词检索
- 跨语言匹配

缺点：
- 对专业术语精确度低
- 可能遗漏关键词匹配
```

### 2.3 BM25 检索

基于关键词的统计语言模型检索：

```
优点：
- 精确匹配关键词
- 对专业术语效果好
- 解释性强

缺点：
- 无法理解语义
- 依赖词频统计
```

### 2.4 RRF 融合算法

**倒数排名融合（Reciprocal Rank Fusion）** 的核心思想是：

```
score(doc) = Σ (1 / (rank_i + k)) × weight_i
```

| 参数 | 说明 |
|------|------|
| `rank_i` | 文档在第 i 个检索方法中的排名 |
| `k` | 平滑常数（通常为 60），防止排名靠前时分数爆炸 |
| `weight_i` | 第 i 个检索方法的权重 |

---

## 3. 项目中的实现

### 3.1 HybridRetriever 类

项目实现在 `app/service/rag/hybrid_retriever.py`：

```python
class HybridRetriever:
    """混合检索器：结合向量检索和BM25关键词检索"""
    
    def __init__(
        self,
        vector_store: ChromaVectorStore,
        documents: List[Document] = None,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3
    ):
        """
        初始化混合检索器
        
        Args:
            vector_store: Chroma向量存储
            documents: 文档列表（用于BM25）
            vector_weight: 向量检索权重
            bm25_weight: BM25权重
        """
        self.vector_store = vector_store
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.bm25_retriever = None
        
        if documents:
            self._init_bm25(documents)
    
    def _init_bm25(self, documents: List[Document]):
        """初始化BM25检索器"""
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        self.bm25_retriever = BM25Retriever.from_documents(
            documents=[
                Document(page_content=text, metadata=meta)
                for text, meta in zip(texts, metadatas)
            ]
        )
        self.bm25_retriever.k = 10
```

### 3.2 混合检索执行

```python
def hybrid_search(
    self,
    query: str,
    k: int = 5,
    filters: Optional[Dict[str, Any]] = None
) -> List[Document]:
    """
    执行混合检索
    
    Args:
        query: 查询文本
        k: 返回结果数量
        filters: 过滤条件
    
    Returns:
        检索结果列表
    """
    # 1. 执行向量检索（获取更多候选）
    vector_results = []
    vector_result = self.vector_store.query(
        query,
        n_results=k * 2,  # 获取 2 倍数量的候选
        where=filters
    )
    
    if vector_result.get("documents") and vector_result["documents"][0]:
        for i, doc_text in enumerate(vector_result["documents"][0]):
            metadata = vector_result["metadatas"][0][i]
            distance = vector_result["distances"][0][i]
            doc = Document(
                page_content=doc_text,
                metadata={**metadata, "distance": distance, "source": "vector"}
            )
            vector_results.append(doc)
    
    # 2. 执行 BM25 关键词检索
    bm25_results = []
    if self.bm25_retriever:
        bm25_results = self.bm25_retriever.invoke(query)
        for doc in bm25_results:
            doc.metadata["source"] = "bm25"
    
    # 3. RRF 融合结果
    final_results = self._fusion_results(vector_results, bm25_results, k)
    
    return final_results
```

### 3.3 RRF 融合实现

```python
def _fusion_results(
    self,
    vector_results: List[Document],
    bm25_results: List[Document],
    k: int
) -> List[Document]:
    """使用倒数排名融合（RRF）合并结果"""
    doc_scores = {}
    doc_docs = {}
    
    # 处理向量检索结果
    for rank, doc in enumerate(vector_results):
        doc_id = doc.page_content[:100]  # 用文档前100字符作为ID
        score = (1.0 / (rank + 60)) * self.vector_weight
        doc_scores[doc_id] = doc_scores.get(doc_id, 0) + score
        doc_docs[doc_id] = doc
    
    # 处理 BM25 检索结果
    for rank, doc in enumerate(bm25_results):
        doc_id = doc.page_content[:100]
        score = (1.0 / (rank + 60)) * self.bm25_weight
        doc_scores[doc_id] = doc_scores.get(doc_id, 0) + score
        if doc_id not in doc_docs:
            doc_docs[doc_id] = doc
    
    # 按分数排序，返回 Top-K
    sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
    final_docs = []
    for doc_id, _ in sorted_docs[:k]:
        doc = doc_docs[doc_id]
        doc.metadata["source"] = "hybrid"
        final_docs.append(doc)
    
    return final_docs
```

---

## 4. 参数说明

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `vector_weight` | float | 向量检索权重 | 0.7 |
| `bm25_weight` | float | BM25 检索权重 | 0.3 |
| `k` | int | 返回结果数量 | 5 |
| `filters` | dict | 过滤条件 | None |

### 权重配置建议

| 场景 | vector_weight | bm25_weight | 说明 |
|------|---------------|--------------|------|
| 法律文档 | 0.6 | 0.4 | 关键词重要 |
| 通用场景 | 0.7 | 0.3 | 语义为主 |
| 客服问答 | 0.8 | 0.2 | 语义理解为主 |
| 技术文档 | 0.5 | 0.5 | 关键词为主 |

---

## 5. RRF 融合示例

假设向量权重 0.7，BM25 权重 0.3，k=60：

| 文档 | 向量排名 | BM25排名 | 向量得分 | BM25得分 | 总分 |
|------|---------|---------|----------|----------|------|
| 文档A | 1 | 3 | 1/61×0.7=0.0115 | 1/63×0.3=0.0048 | **0.0163** |
| 文档B | 2 | 1 | 1/62×0.7=0.0113 | 1/61×0.3=0.0049 | **0.0162** |
| 文档C | 3 | 2 | 1/63×0.7=0.0111 | 1/62×0.3=0.0048 | **0.0159** |

最终排序：文档A > 文档B > 文档C

---

## 6. 特点

### 优点

| 优点 | 说明 |
|------|------|
| **兼顾语义和关键词** | 同时考虑语义相似度和关键词匹配 |
| **提高召回率** | 两种方法互补，减少遗漏 |
| **适合专业领域** | 对法律、医学等术语密集领域效果好 |
| **可调权重** | 可以根据场景调整侧重点 |

### 缺点

| 缺点 | 说明 |
|------|------|
| **计算复杂度较高** | 需要同时执行两种检索 |
| **需要维护 BM25 索引** | 文档更新时需要重新索引 |
| **需要调优权重** | 不同场景权重不同 |

---

## 7. 适用场景

### 最佳场景

- **法律文档检索**：专业术语多，需要精确匹配
- **技术文档查询**：包含大量专业名词
- **产品搜索**：需要兼顾语义和属性匹配
- **客服对话**：需要理解用户意图同时匹配关键信息

### 不适合场景

- **简单概念查询**：如"什么是XX"
- **对响应速度要求极高**：混合检索比纯向量检索慢

---

## 8. 与其他策略对比

| 特性 | Basic | **Hybrid** | MMR | Multi-Query | +Rerank |
|------|-------|------------|-----|-------------|---------|
| **召回率** | 中 | ⭐⭐⭐⭐⭐ | 中 | ⭐⭐⭐⭐⭐ | - |
| **精确度** | 中 | ⭐⭐⭐⭐ | 中 | 中 | ⭐⭐⭐⭐⭐ |
| **速度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **多样性** | 低 | 中 | ⭐⭐⭐⭐⭐ | 中 | - |
| **复杂度** | 低 | 中 | 高 | 中 | 高 |

---

## 9. API 调用示例

### REST API

```bash
# 混合检索
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "劳动合同解除赔偿",
    "n_results": 5,
    "strategy": "hybrid"
  }'
```

### Python SDK

```python
from app.service.rag.hybrid_retriever import AdvancedRAGService
from app.service.vector_db import ChromaVectorStore

vector_store = ChromaVectorStore(collection_name="legal_documents")
documents = [...]  # 文档列表
rag_service = AdvancedRAGService(vector_store, documents)

# 混合检索
docs = rag_service.search(
    query="劳动合同解除赔偿",
    strategy="hybrid",
    k=5
)

for doc in docs:
    print(f"内容: {doc.page_content[:100]}...")
    print(f"来源: {doc.metadata.get('source')}")
```

### 直接使用 HybridRetriever

```python
from app.service.rag.hybrid_retriever import HybridRetriever

hybrid_retriever = HybridRetriever(
    vector_store=vector_store,
    documents=documents,
    vector_weight=0.7,
    bm25_weight=0.3
)

results = hybrid_retriever.hybrid_search(
    query="劳动合同法 经济补偿",
    k=5
)
```

---

## 10. 性能优化建议

### 10.1 异步执行

```python
import asyncio

async def hybrid_search_async(query, k=5):
    # 同时执行两种检索
    vector_task = asyncio.to_thread(vector_store.query, query, k * 2)
    bm25_task = asyncio.to_thread(bm25_retriever.invoke, query)
    
    vector_results, bm25_results = await asyncio.gather(vector_task, bm25_task)
    
    # 融合结果
    return fusion(vector_results, bm25_results, k)
```

### 10.2 缓存 BM25 索引

```python
import pickle

# 保存 BM25 索引
with open('bm25_index.pkl', 'wb') as f:
    pickle.dump(bm25_retriever, f)

# 加载 BM25 索引
with open('bm25_index.pkl', 'rb') as f:
    bm25_retriever = pickle.load(f)
```

### 10.3 调整检索数量

```python
# 如果候选文档较少，可以增加初始检索数量
vector_result = vector_store.query(query, n_results=k * 3)
bm25_results = bm25_retriever.invoke(query, k=k * 3)
```

---

## 11. 最佳实践

1. **从 0.7/0.3 开始**：这是大多数场景的合理默认值
2. **观察结果来源**：检查返回结果中 vector 和 bm25 的比例
3. **根据领域调整**：法律/技术领域增加 bm25_weight
4. **结合 Rerank**：Hybrid + Rerank 通常效果最佳
5. **监控检索时间**：确保响应时间在可接受范围内

---

## 12. 参考资料

- [BM25 Algorithm](https://en.wikipedia.org/wiki/Okapi_BM25)
- [RRF 论文](https://dl.acm.org/doi/10.1145/1645953.1646033)
- [LangChain Hybrid Search](https://python.langchain.com/docs/modules/data_connection/retrievers/