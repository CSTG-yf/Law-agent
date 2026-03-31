# 多查询检索 (Multi-Query) 策略详解

## 1. 什么是多查询检索？

**多查询检索（Multi-Query Retrieval）** 通过**生成多个查询变体**来提高检索召回率。其核心思想是：

> **用户的查询表达可能不完整或不准确，生成多个语义相近的查询可以覆盖更多相关文档。**

---

## 2. 原理

### 2.1 整体流程

```
原始查询 → 查询变体生成 → 多路检索 → 结果合并 → 去重排序 → 返回
```

### 2.2 查询变体生成策略

项目实现了以下几种变体生成方法：

#### 方法一：关键词提取

使用 jieba 中文分词提取关键词，重新组合形成新查询：

```
原始: "劳动合同解除赔偿"
↓ 关键词提取
["劳动合同", "解除", "赔偿"]
↓ 重组变体
变体1: "劳动合同 解除 赔偿"
变体2: "劳动合同 解除"
变体3: "劳动合同 赔偿"
```

#### 方法二：简化查询

去除疑问词，生成更简洁的查询：

```
原始: "如何申请劳动仲裁？"
↓ 去除疑问词
变体: "申请劳动仲裁"

原始: "什么情况下可以解除劳动合同？"
↓ 去除疑问词
变体: "情况下可以解除劳动合同"
```

#### 方法三：同义词扩展（预留）

```python
def _get_synonyms(self, query: str) -> List[str]:
    """获取同义词查询变体"""
    # 可以接入同义词词典或 LLM 生成
    return []
```

### 2.3 结果合并策略

项目使用**累加分数法**：

```
score(doc) = Σ (1 / (distance + ε)) × weight
```

| 参数 | 说明 |
|------|------|
| `distance` | 文档与查询的距离 |
| `ε` | 平滑常数（0.01），避免除零 |
| `weight` | 查询权重（默认1.0） |

同时记录每个文档被多少个查询命中（multi_query_count），命中次数越多排名越靠前。

---

## 3. 项目中的实现

### 3.1 MultiQueryRetriever 类

实现在 `app/service/rag/hybrid_retriever.py`：

```python
class MultiQueryRetriever:
    """多查询检索器 - 生成多个查询变体以提高召回率"""
    
    def __init__(self, vector_store: ChromaVectorStore, llm=None):
        self.vector_store = vector_store
        self.llm = llm
    
    def generate_queries(self, query: str) -> List[str]:
        """生成查询变体"""
        variations = [query]
        
        # 方法1: 关键词提取
        try:
            from jieba.analyse import extract_tags
            keywords = extract_tags(query, topK=5)
            if keywords:
                variations.append(" ".join(keywords))
                if len(keywords) >= 2:
                    variations.append(" ".join(keywords[:2]))
        except Exception as e:
            logger.warning(f"jieba关键词提取失败: {str(e)}")
        
        # 方法2: 简化查询
        question_words = ["什么", "怎么", "如何", "为什么", "哪些", "怎样"]
        for word in question_words:
            if word in query:
                simplified = query.replace(word, "")
                if simplified.strip() and simplified != query:
                    variations.append(simplified.strip())
                break
        
        # 去重，返回最多5个变体
        unique_variations = list(set(variations))[:5]
        
        return unique_variations
```

### 3.2 多查询检索执行

```python
def search(
    self,
    query: str,
    k: int = 5,
    filters: Optional[Dict[str, Any]] = None
) -> List[Document]:
    """
    执行多查询检索
    
    Args:
        query: 原始查询
        k: 每查询返回结果数
        filters: 过滤条件
    
    Returns:
        合并后的检索结果
    """
    # 1. 生成查询变体
    queries = self.generate_queries(query)
    logger.info(f"执行 {len(queries)} 个查询变体检索")
    
    # 2. 多路检索并合并分数
    all_docs = []
    doc_scores = {}
    
    for i, q in enumerate(queries):
        # 执行检索，获取更多候选
        results = self.vector_store.query(q, n_results=k * 2, where=filters)
        
        if results.get("documents") and results["documents"][0]:
            for j, doc_text in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][j]
                distance = results["distances"][0][j]
                
                doc_id = doc_text[:100]  # 用文档前100字符作为ID
                
                # 累加分数
                score = 1 / (distance + 0.01)
                
                if doc_id in doc_scores:
                    doc_scores[doc_id]["score"] += score
                    doc_scores[doc_id]["count"] += 1
                else:
                    doc_scores[doc_id] = {
                        "score": score,
                        "count": 1,
                        "document": Document(
                            page_content=doc_text,
                            metadata=metadata
                        )
                    }
    
    # 3. 按分数排序，返回 Top-K
    sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1]["score"], reverse=True)
    final_docs = []
    for doc_id, doc_info in sorted_docs[:k]:
        doc = doc_info["document"]
        doc.metadata["source"] = "multi_query"
        doc.metadata["multi_query_count"] = doc_info["count"]
        final_docs.append(doc)
    
    return final_docs
```

---

## 4. 查询变体示例

| 原始查询 | 变体1 | 变体2 | 变体3 | 变体4 |
|----------|--------|--------|--------|--------|
| "劳动合同解除赔偿" | "劳动合同 解除 赔偿" | "劳动合同 解除" | "劳动合同 赔偿" | "解除 赔偿" |
| "劳动仲裁流程" | "劳动仲裁 流程" | "仲裁流程" | "劳动仲裁" | - |
| "如何申请工伤认定" | "申请工伤认定" | "工伤认定" | "申请 工伤" | - |
| "什么情况下不签劳动合同" | "情况下不签劳动合同" | "不签劳动合同" | "什么 情况 劳动合同" | - |

---

## 5. 参数说明

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `k` | int | 每个查询返回的结果数 | 5 |
| `max_queries` | int | 最大变体数量 | 5 |
| `filters` | dict | 过滤条件 | None |

---

## 6. 特点

### 优点

| 优点 | 说明 |
|------|------|
| **提高召回率** | 多个查询变体覆盖更多相关文档 |
| **覆盖多种表达** | 适配不同的查询表达方式 |
| **适合探索性查询** | 用户想全面了解某个主题时效果好 |
| **实现简单** | 不需要额外的模型或复杂逻辑 |

### 缺点

| 缺点 | 说明 |
|------|------|
| **检索时间增加** | 需要执行多个查询 |
| **可能引入噪音** | 变体查询可能检索到不相关结果 |
| **变体质量依赖** | 关键词提取的准确性影响效果 |

---

## 7. 适用场景

### 最佳场景

- **用户查询表达不明确**：如口语化、碎片化的查询
- **需要全面了解主题**：如"关于XX的所有信息"
- **同义词多的领域**：如咨询、问答类
- **探索性查询**：用户没有明确目标

### 不适合场景

- **精确查询**：如已知具体关键词
- **对响应速度要求极高**：多查询会增加延迟

---

## 8. 与其他策略对比

| 特性 | Basic | Hybrid | MMR | **Multi-Query** | +Rerank |
|------|-------|--------|-----|----------------|---------|
| **召回率** | 中 | 高 | 中 | ⭐⭐⭐⭐⭐ | - |
| **精确度** | 中 | 高 | 中 | 中 | ⭐⭐⭐⭐⭐ |
| **速度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **多样性** | 低 | 中 | ⭐⭐⭐⭐⭐ | 中 | - |
| **复杂度** | 低 | 中 | 高 | 中 | 高 |

---

## 9. API 调用示例

### REST API

```bash
# 多查询检索
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "劳动合同解除赔偿",
    "n_results": 5,
    "strategy": "multi_query"
  }'
```

### Python SDK

```python
from app.service.rag.hybrid_retriever import AdvancedRAGService

rag_service = AdvancedRAGService(vector_store)

# 多查询检索
docs = rag_service.search(
    query="劳动合同解除赔偿",
    strategy="multi_query",
    k=5
)

for doc in docs:
    print(f"内容: {doc.page_content[:100]}...")
    print(f"命中次数: {doc.metadata.get('multi_query_count')}")
```

### 直接使用 MultiQueryRetriever

```python
from app.service.rag.hybrid_retriever import MultiQueryRetriever

mq_retriever = MultiQueryRetriever(vector_store)

# 生成查询变体
queries = mq_retriever.generate_queries("如何申请劳动仲裁")
print(f"生成的变体: {queries}")

# 执行检索
results = mq_retriever.search("如何申请劳动仲裁", k=5)
```

---

## 10. 进阶扩展

### 10.1 使用 LLM 生成变体

```python
def generate_queries_with_llm(self, query: str) -> List[str]:
    """使用 LLM 生成查询变体"""
    if not self.llm:
        return [query]
    
    prompt = f"""请为以下查询生成3-5个语义相近的查询变体：
原始查询: {query}
要求：变体应该覆盖不同的表达方式和关键词组合"""
    
    response = self.llm.invoke(prompt)
    # 解析 response 获取变体列表
    return variations
```

### 10.2 使用同义词库

```python
def _expand_with_synonyms(self, query: str) -> List[str]:
    """使用同义词库扩展查询"""
    synonyms_map = {
        "赔偿": ["补偿", "赔偿金", "补偿金"],
        "解除": ["终止", "结束"],
        "劳动": ["劳工", "职工"]
    }
    
    variations = [query]
    for word, syns in synonyms_map.items():
        if word in query:
            for syn in syns:
                variations.append(query.replace(word, syn))
    
    return variations
```

---

## 11. 最佳实践

1. **监控变体数量**：通常 3-5 个变体效果最好
2. **观察命中次数**：multi_query_count 高的文档更可靠
3. **调整检索数量**：每个变体检索 k*2 个，确保有足够候选
4. **结合 Rerank**：Multi-Query + Rerank 可以过滤噪音
5. **根据场景选择**：探索性查询适合，精确查询用 Basic 或 Hybrid

---

## 12. 参考资料

- [LangChain MultiQueryRetriever](https://python.langchain.com/docs/modules/data_connection/retrievers/multiquery)
- [Query Expansion Techniques](https://arxiv.org/abs/2104.09420)