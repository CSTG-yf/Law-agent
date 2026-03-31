# 重排序 (Reranking) 策略详解

## 1. 什么是重排序？

**重排序（Reranking）** 是**两阶段检索**中的第二阶段。它在初步检索结果（可能 50-100 个）基础上，使用更精确的模型重新排序，返回最相关的 Top-K（如 10 个）结果。

核心思想是：
> **第一阶段快速筛选候选，第二阶段精细排序。**

---

## 2. 原理

### 2.1 两阶段检索流程

```
阶段1: 快速检索 (Bi-Encoder)
  查询 → 向量化 → 向量数据库 → 返回 50-100 个候选文档

阶段2: 精确重排序 (Cross-Encoder)
  候选文档 → Cross-Encoder 联合编码 → 相关性评分 → 返回 Top-10
```

### 2.2 Bi-Encoder vs Cross-Encoder

| 特性 | Bi-Encoder（双编码器） | Cross-Encoder（交叉编码器） |
|------|----------------------|---------------------------|
| 编码方式 | 查询和文档独立编码 | 查询和文档联合编码 |
| 计算复杂度 | O(1) 预计算 + O(N) 检索 | O(N) 实时计算 |
| 检索速度 | 快 | 慢 |
| 相关性精度 | 中 | 高 |
| 适用场景 | 大规模初筛 | 精细化排序 |

### 2.3 Cross-Encoder 工作原理

```
输入: [CLS] 查询 [SEP] 文档 [SEP]
  ↓
嵌入层 (Embedding Layer)
  ↓
Transformer 编码器 (多层注意力机制)
  ↓
池化层 (Pooling)
  ↓
全连接层 (FC)
  ↓
输出层 (Sigmoid)
  ↓
相关性分数 (0-1)
```

**关键优势**：
- 查询和文档联合编码，捕获交互信息
- 直接计算相关性分数，更精确
- 适合 Top-K 场景

---

## 3. 项目中的实现

项目实现了多种重排序器，实现在 `app/service/rag/reranker.py`：

### 3.1 Reranker（Cross-Encoder 重排序）

```python
class Reranker:
    """文档重排序器 - 提升检索质量"""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        初始化重排序器
        
        Args:
            model_name: Cross-Encoder模型名称
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """加载Cross-Encoder模型"""
        try:
            if self._is_model_cached():
                # 从本地加载
                self.model = CrossEncoder(str(self.local_model_path))
            else:
                # 从 Hugging Face 下载到本地
                self._download_and_cache_model()
                self.model = CrossEncoder(str(self.local_model_path))
        except Exception as e:
            logger.error(f"加载Cross-Encoder模型失败: {e}")
            # 后备：使用嵌入相似度排序
    
    def rerank(self, query, documents, top_k=None):
        if self.model is not None:
            return self._rerank_with_cross_encoder(query, documents, top_k)
        else:
            return self._rerank_with_embeddings(query, documents, top_k)
    
    def _rerank_with_cross_encoder(self, query, documents, top_k):
        """使用Cross-Encoder进行重排序"""
        # 构建查询-文档对
        pairs = [[query, doc.page_content] for doc in documents]
        
        # 一次性预测所有对的分数
        scores = self.model.predict(pairs)
        
        # 按分数排序
        doc_scores = list(zip(documents, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 返回 Top-K
        if top_k is not None:
            doc_scores = doc_scores[:top_k]
        
        reranked = []
        for doc, score in doc_scores:
            doc.metadata["rerank_score"] = float(score)
            reranked.append(doc)
        
        return reranked
```

### 3.2 MMRReranker（MMR 重排序）

```python
class MMRReranker:
    """基于最大边际相关性的重排序器"""
    
    def __init__(self, lambda_mult: float = 0.5):
        self.lambda_mult = lambda_mult
    
    def rerank(self, query, documents, top_k=None):
        """使用 MMR 策略重排序，兼顾相关性和多样性"""
        # 预计算所有文档的嵌入
        query_embedding = self.embedding_service.embed_text_sync(query)
        doc_embeddings = [embedding_service.embed_text_sync(doc.page_content) for doc in documents]
        
        # 计算每个文档与查询的相似度
        similarities = [cosine_sim(query_embedding, emb) for emb in doc_embeddings]
        
        # MMR 迭代选择
        selected = []
        remaining = list(range(len(documents)))
        
        while len(selected) < top_k and remaining:
            best_idx = None
            best_score = -float("inf")
            
            for idx in remaining:
                relevance = similarities[idx]
                
                # 计算与已选文档的最大相似度（多样性）
                if selected:
                    max_sim = max(cosine_sim(doc_embeddings[idx], doc_embeddings[i]) for i in selected)
                    diversity = 1 - max_sim
                else:
                    diversity = 1
                
                mmr_score = self.lambda_mult * relevance + (1 - self.lambda_mult) * diversity
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            if best_idx:
                selected.append(best_idx)
                remaining.remove(best_idx)
        
        return [documents[i] for i in selected]
```

### 3.3 EnsembleReranker（集成重排序）

```python
class EnsembleReranker:
    """集成重排序器 - 结合多种排序策略"""
    
    def __init__(self, rerankers: List[Any] = None, weights: List[float] = None):
        self.rerankers = rerankers or []
        self.weights = weights or [1.0] * len(self.rerankers)
    
    def rerank(self, query, documents, top_k=None):
        """加权投票的集成策略"""
        doc_scores = {doc.page_content[:100]: 0.0 for doc in documents}
        
        total_weight = sum(self.weights)
        
        for reranker, weight in zip(self.rerankers, self.weights):
            try:
                reranked = reranker.rerank(query, documents)
                
                # 基于排名的分数加权
                for rank, doc in enumerate(reranked):
                    doc_id = doc.page_content[:100]
                    score = (len(reranked) - rank) / len(reranked)
                    doc_scores[doc_id] += (weight / total_weight) * score
            except Exception as e:
                logger.error(f"重排序器执行失败: {e}")
        
        # 按综合分数排序
        doc_with_scores = [(doc, doc_scores.get(doc.page_content[:100], 0)) for doc in documents]
        doc_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        return [doc for doc, _ in doc_with_scores[:top_k]]
```

---

## 4. 模型选择

项目使用的默认模型：`cross-encoder/ms-marco-MiniLM-L-6-v2`

### 常用模型对比

| 模型 | 大小 | 速度 | 精度 | 适用场景 |
|------|------|------|------|----------|
| `ms-marco-MiniLM-L-6-v2` | 小 | 快 | 中 | 实时应用（默认） |
| `ms-marco-MiniLM-L-12-v2` | 中 | 中 | 高 | 通用场景 |
| `ms-marco-electra-base` | 中 | 中 | 高 | 英文场景 |
| `bge-reranker-base` | 中 | 中 | 高 | 中文场景 |
| `bge-reranker-v2-m3` | 大 | 慢 | 最高 | 高精度场景 |

---

## 5. 参数说明

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `top_k` | int | 返回结果数量 | None（返回全部） |
| `lambda_mult` | float | 多样性因子（MMRReranker） | 0.5 |
| `model_name` | str | Cross-Encoder 模型名称 | ms-marco-MiniLM-L-6-v2 |

---

## 6. 特点

### 优点

| 优点 | 说明 |
|------|------|
| **提高结果质量** | 相比单纯向量检索，精确度显著提升 |
| **更精确的相关性** | Cross-Encoder 捕获查询-文档交互信息 |
| **适合 Top-K 场景** | 在小规模候选集上效果尤佳 |
| **可组合使用** | 多种重排序器可以集成 |

### 缺点

| 缺点 | 说明 |
|------|------|
| **增加计算成本** | 需要对每个候选文档单独编码 |
| **延迟增加** | 重排序阶段耗时较长 |
| **需要加载额外模型** | 需要额外的模型文件 |

---

## 7. 适用场景

### 最佳场景

- **对结果质量要求高**：如法律、医疗等专业领域
- **Top-K 推荐**：如搜索结果只展示前 10 个
- **搜索引擎**：需要高精度的排序结果
- **对话系统**：需要准确的引用内容

### 不适合场景

- **大规模候选集**：候选太多时延迟高
- **实时性要求高**：需要快速响应的场景

---

## 8. 与其他策略对比

| 特性 | Basic | Hybrid | MMR | Multi-Query | **+Rerank** |
|------|-------|--------|-----|------------|-------------|
| **召回率** | 中 | 高 | 中 | ⭐⭐⭐⭐⭐ | 高 |
| **精确度** | 中 | 高 | 中 | 中 | ⭐⭐⭐⭐⭐ |
| **速度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **多样性** | 低 | 中 | ⭐⭐⭐⭐⭐ | 中 | 中 |
| **复杂度** | 低 | 中 | 高 | 中 | 高 |

---

## 9. API 调用示例

### REST API

```bash
# 混合检索 + 重排序
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "劳动合同解除赔偿",
    "n_results": 5,
    "strategy": "hybrid",
    "enable_rerank": true
  }'
```

### Python SDK

```python
from app.service.rag.hybrid_retriever import AdvancedRAGService
from app.service.rag.reranker import Reranker
from app.service.vector_db import ChromaVectorStore

# 初始化
vector_store = ChromaVectorStore(collection_name="legal_documents")
rag_service = AdvancedRAGService(vector_store)
reranker = Reranker()

# 初步检索（获取更多候选）
docs = rag_service.search(
    query="劳动合同解除赔偿",
    strategy="hybrid",
    k=20  # 获取更多候选
)

# 重排序
reranked_docs = reranker.rerank(
    query="劳动合同解除赔偿",
    documents=docs,
    top_k=5  # 返回前5个
)

for doc in reranked_docs:
    print(f"内容: {doc.page_content[:100]}...")
    print(f"重排分数: {doc.metadata.get('rerank_score')}")
```

### 直接使用 MMRReranker

```python
from app.service.rag.reranker import MMRReranker

mmr_reranker = MMRReranker(lambda_mult=0.5)

results = mmr_reranker.rerank(
    query="劳动合同解除赔偿",
    documents=docs,
    top_k=5
)
```

### 集成重排序

```python
from app.service.rag.reranker import Reranker, MMRReranker, EnsembleReranker

reranker1 = Reranker()
reranker2 = MMRReranker(lambda_mult=0.5)

ensemble = EnsembleReranker(
    rerankers=[reranker1, reranker2],
    weights=[0.6, 0.4]
)

results = ensemble.rerank(query, documents, top_k=5)
```

---

## 10. 性能优化建议

### 10.1 批量预测

```python
# Cross-Encoder 支持批量预测，一次性获取所有分数
pairs = [[query, doc.page_content] for doc in documents]
scores = model.predict(pairs)  # 返回分数数组
```

### 10.2 候选数量选择

```python
# 初步检索获取 50-100 个候选
initial_results = vector_store.query(query, n_results=50)

# 重排序返回 Top-10
reranked = reranker.rerank(query, initial_results, top_k=10)
```

### 10.3 模型缓存

```python
# 模型下载到本地后会自动缓存
# 首次启动会下载，后续启动从本地加载
local_model_path = "huggingface_models/reranker_model"
```

---

## 11. 最佳实践

1. **先检索后重排序**：先用 Basic/Hybrid/MMR 快速获取候选，再用 Rerank 精细排序
2. **候选数量适中**：建议 50-100 个候选，效果和延迟的平衡点
3. **选择合适的模型**：中文场景推荐 bge-reranker-base
4. **组合多种策略**：如 Hybrid + Rerank 通常效果最佳
5. **监控延迟**：重排序会增加 100-500ms 的延迟

---

## 12. 参考资料

- [Cross-Encoder 官方文档](https://sbert.net/examples/applications/retrieval/README.html)
- [Hugging Face Reranking Models](https://huggingface.co/models?pipeline_tag=reranking)
- [BGE Reranker](https://github.com/flagopen/flagperf/tree/main/benchmark/retrieve/rerank)
- [MS MARCO Reranking](https://github.com/microsoft/MSMARCO-Passage-Ranking)