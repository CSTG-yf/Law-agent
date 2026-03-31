# MMR 检索策略详解

## 1. 什么是 MMR？

**MMR（Maximal Marginal Relevance，最大边际相关性）** 是一种**平衡相关性和多样性**的检索策略。它的核心思想是：

> **不要只返回最相关的文档，而是要返回既相关又互相不同的文档。**

---

## 2. 原理

MMR 通过**贪心迭代算法**选择文档，每一轮都计算一个综合分数：

```
MMR分数 = λ × 相关性 - (1 - λ) × 多样性
```

- **相关性**：候选文档与查询的相似程度
- **多样性**：候选文档与已选中文档的最大相似度（越低越好，避免重复）
- **λ 参数**：控制倾向（λ=1 纯相关，λ=0 纯多样）

### MMR 评分公式

```
MMR(D) = λ × Sim(D, Q) - (1 - λ) × max(Sim(D, Di))
```

| 参数 | 说明 |
|------|------|
| `D` | 候选文档 |
| `Q` | 查询 |
| `Di` | 已选中的文档 |
| `λ` | 多样性因子 (0-1) |
| `Sim()` | 相似度函数 |

### 迭代选择过程

MMR 通过贪心算法迭代选择文档：

```
步骤1: 初始检索 fetch_k 个文档
步骤2: 计算每个候选文档的 MMR 分数
步骤3: 选择 MMR 分数最高的文档
步骤4: 从候选集中移除该文档
步骤5: 重复步骤2-4，直到选出 k 个文档
```

**示例**：

假设查询"劳动合同"，初始检索到 5 个文档，λ=0.5：

| 轮次 | 候选文档 | 相关性 | 多样性 | MMR 分数 | 选择 |
|------|----------|--------|--------|----------|------|
| 1 | 文档A | 0.9 | 1.0 | 0.5×0.9+0.5×1.0=0.95 | ✓ |
| 1 | 文档B | 0.85 | 1.0 | 0.5×0.85+0.5×1.0=0.925 | - |
| 2 | 文档B | 0.85 | 0.3 | 0.5×0.85+0.5×0.3=0.575 | ✓ |
| 2 | 文档C | 0.8 | 0.7 | 0.5×0.8+0.5×0.7=0.75 | - |

最终选择：文档A、文档B

---

## 3. 项目中的实现

项目中 MMR 实现在 `app/service/rag/hybrid_retriever.py`：

```python
class MMRRetriever:
    """最大边际相关性检索器 - 平衡相关性和多样性"""
    
    def __init__(self, vector_store: ChromaVectorStore):
        self.vector_store = vector_store
        self.embedding_service = OllamaEmbedding()
    
    def search(
        self,
        query: str,
        k: int = 5,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        执行MMR检索
        
        Args:
            query: 查询文本
            k: 返回结果数量
            fetch_k: 初始获取数量
            lambda_mult: 多样性因子 (0=最大多样性, 1=最大相关性)
            filters: 过滤条件
            
        Returns:
            检索结果列表
        """
        # 1. 初始检索 fetch_k 个候选文档
        initial_results = self.vector_store.query(
            query,
            n_results=fetch_k,
            where=filters
        )
        
        # 2. 预计算查询和所有文档的 embedding
        query_embedding = self.embedding_service.embed_text_sync(query)
        
        doc_embeddings = []
        for doc in docs:
            emb = self.embedding_service.embed_text_sync(doc.page_content)
            doc_embeddings.append(emb)
        
        # 3. 迭代选择 k 个文档
        selected = []
        selected_embeddings = []
        remaining = list(range(len(docs)))
        
        while len(selected) < k and remaining:
            best_score = -float("inf")
            best_idx = None
            
            for idx in remaining:
                doc_embedding = doc_embeddings[idx]
                
                # 相关性 (1 - distance)
                relevance = 1 - docs[idx].metadata.get("distance", 0)
                
                # 多样性 (与已选文档的最大相似度)
                if selected_embeddings:
                    similarities = [
                        self._cosine_similarity(doc_embedding, sel_emb)
                        for sel_emb in selected_embeddings
                    ]
                    max_similarity = max(similarities) if similarities else 0
                    diversity = 1 - max_similarity
                else:
                    diversity = 1
                
                # MMR 综合分数
                mmr_score = lambda_mult * relevance + (1 - lambda_mult) * diversity
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            if best_idx is not None:
                selected.append(docs[best_idx])
                selected_embeddings.append(doc_embeddings[best_idx])
                remaining.remove(best_idx)
        
        for doc in selected:
            doc.metadata["source"] = "mmr"
        
        return selected
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0
        return dot_product / (norm1 * norm2)
```

---

## 4. 参数说明

| 参数 | 范围 | 作用 | 默认值 |
|------|------|------|--------|
| `k` | >0 | 最终返回结果数 | 5 |
| `fetch_k` | >k | 初始候选文档数 | 20 |
| `lambda_mult` | 0-1 | 多样性因子 | 0.5 |
| `filters` | dict | 过滤条件 | None |

### λ 值效果对比

| λ 值 | 效果 | 适用场景 |
|------|------|----------|
| 1.0 | 纯相关性 | 精确查询 |
| 0.7 | 偏向相关 | 大部分场景 |
| **0.5** | **平衡（推荐）** | **通用场景** |
| 0.3 | 偏向多样 | 探索性查询 |
| 0.0 | 纯多样 | 发现新角度 |

---

## 5. 适用场景

- **法律条款检索**：避免返回内容重复的条款
- **多角度分析**：需要覆盖不同方面的答案
- **探索性查询**：用户想全面了解某个主题
- **推荐系统**：需要结果多样性

---

## 6. 与其他策略对比

| 策略 | 召回率 | 精确度 | 速度 | 多样性 | 复杂度 |
|------|--------|--------|------|--------|--------|
| Basic | 中 | 中 | ⭐⭐⭐⭐⭐ | 低 | 低 |
| Hybrid | 高 | 高 | ⭐⭐⭐⭐ | 中 | 中 |
| **MMR** | 中 | 中 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 高 |
| Multi-Query | ⭐⭐⭐⭐⭐ | 中 | ⭐⭐ | 中 | 中 |
| +Rerank | - | ⭐⭐⭐⭐⭐ | ⭐⭐ | - | 高 |

### 各策略特点

| 策略 | 特点 |
|------|------|
| **Basic** | 只看相关性，速度最快，基于向量相似度 |
| **Hybrid** | 结合向量+关键词检索，使用 RRF 融合 |
| **MMR** | 兼顾相关性和多样性，避免结果重复 |
| **Multi-Query** | 生成多个查询变体，提高召回率 |
| **+Rerank** | 在初步结果上使用 Cross-Encoder 精排 |

---

## 7. API 调用示例

### REST API

```bash
# MMR 检索
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "劳动合同解除赔偿",
    "n_results": 5,
    "strategy": "mmr",
    "fetch_k": 30,
    "lambda_mult": 0.5
  }'
```

### Python SDK

```python
from app.service.rag.hybrid_retriever import AdvancedRAGService
from app.service.vector_db import ChromaVectorStore

vector_store = ChromaVectorStore(collection_name="legal_documents")
rag_service = AdvancedRAGService(vector_store)

# MMR 检索
docs = rag_service.search(
    query="劳动合同解除赔偿",
    strategy="mmr",
    k=5,
    fetch_k=30,
    lambda_mult=0.5
)
```

---

## 8. 使用建议

1. **从 λ=0.5 开始**：这是平衡点，适合大多数场景
2. **精确查询用高 λ**：如 λ=0.7 或 0.8
3. **探索性查询用低 λ**：如 λ=0.3 或 0.4
4. **fetch_k 要足够大**：建议 20-50，确保有足够候选

### 参数调优示例

```python
# 精确查询
lambda_mult = 0.7
fetch_k = 20

# 平衡查询（推荐）
lambda_mult = 0.5
fetch_k = 30

# 探索性查询
lambda_mult = 0.3
fetch_k = 50
```

---

## 9. 参考资料

- [MMR Paper](https://dl.acm.org/doi/10.1145/276646.276788)
- [LangChain MMR Retriever](https://python.langchain.com/docs/modules/data_connection/retrievers/contextual_compression/)
- [Maximum Marginal Relevance - Wiki](https://en.wikipedia.org/wiki/Maximum_marginal_relevance)
