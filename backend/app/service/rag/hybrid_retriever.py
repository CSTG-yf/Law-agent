from typing import List, Optional, Dict, Any, Callable
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from app.service.vector_db import ChromaVectorStore
from app.service.rag.ollama_embedding import OllamaEmbedding
import jieba
from app.core.logger import get_logger

logger = get_logger("hybrid_retriever")


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
        logger.info(f"开始初始化BM25检索器 - 文档数量: {len(documents)}")
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        self.bm25_retriever = BM25Retriever.from_documents(
            documents=[
                Document(page_content=text, metadata=meta)
                for text, meta in zip(texts, metadatas)
            ]
        )
        self.bm25_retriever.k = 10
        logger.info(f"BM25检索器初始化完成 - 返回结果数: {self.bm25_retriever.k}")
    
    def _create_chroma_retriever(self, k: int = 5):
        """创建Chroma向量检索器"""
        def search_fn(query: str):
            result = self.vector_store.query(query, n_results=k)
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
        
        return search_fn
    
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
        logger.info(f"开始混合检索 - query: {query[:100]}, k: {k}, filters: {filters}")
        
        vector_results = []
        bm25_results = []
        
        logger.info(f"执行向量检索 - 获取 {k * 2} 个结果")
        vector_result = self.vector_store.query(
            query,
            n_results=k * 2,
            where=filters
        )
        
        if vector_result.get("documents") and vector_result["documents"][0]:
            for i, doc_text in enumerate(vector_result["documents"][0]):
                metadata = vector_result["metadatas"][0][i] if vector_result.get("metadatas") else {}
                distance = vector_result["distances"][0][i] if vector_result.get("distances") else 0
                doc = Document(
                    page_content=doc_text,
                    metadata={**metadata, "distance": distance, "source": "vector"}
                )
                vector_results.append(doc)
            logger.info(f"向量检索完成 - 检索到 {len(vector_results)} 个文档")
        else:
            logger.warning(f"向量检索未找到结果")
        
        if self.bm25_retriever:
            logger.info(f"执行BM25关键词检索 - 查询: {query[:100]}")
            try:
                bm25_results = self.bm25_retriever.invoke(query)
                for doc in bm25_results:
                    doc.metadata["source"] = "bm25"
                logger.info(f"BM25关键词检索完成 - 检索到 {len(bm25_results)} 个文档")
                
                if len(bm25_results) > 0:
                    logger.info(f"BM25检索结果示例 - 文档1: {bm25_results[0].page_content[:100]}...")
            except Exception as e:
                logger.error(f"BM25关键词检索失败 - error: {str(e)}")
                bm25_results = []
        else:
            logger.warning(f"BM25检索器未初始化，跳过BM25检索")
        
        logger.info(f"开始融合结果 - 向量结果: {len(vector_results)}, BM25结果: {len(bm25_results)}")
        final_results = self._fusion_results(vector_results, bm25_results, k)
        logger.info(f"混合检索完成 - 返回 {len(final_results)} 个文档")
        
        return final_results
    
    def _fusion_results(
        self,
        vector_results: List[Document],
        bm25_results: List[Document],
        k: int
    ) -> List[Document]:
        """使用倒数排名融合（RRF）合并结果"""
        logger.info(f"开始RRF融合 - 向量权重: {self.vector_weight}, BM25权重: {self.bm25_weight}")
        doc_scores = {}
        doc_docs = {}
        
        logger.info(f"处理向量检索结果 - 数量: {len(vector_results)}")
        for rank, doc in enumerate(vector_results):
            doc_id = doc.page_content[:100]
            score = (1.0 / (rank + 60)) * self.vector_weight
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + score
            doc_docs[doc_id] = doc
            logger.debug(f"向量结果 - rank: {rank}, doc_id: {doc_id[:50]}..., score: {score:.4f}")
        
        logger.info(f"处理BM25检索结果 - 数量: {len(bm25_results)}")
        for rank, doc in enumerate(bm25_results):
            doc_id = doc.page_content[:100]
            score = (1.0 / (rank + 60)) * self.bm25_weight
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + score
            if doc_id not in doc_docs:
                doc_docs[doc_id] = doc
            logger.debug(f"BM25结果 - rank: {rank}, doc_id: {doc_id[:50]}..., score: {score:.4f}")
        
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        final_docs = [doc_docs[doc_id] for doc_id, _ in sorted_docs[:k]]
        
        logger.info(f"RRF融合完成 - 合并后文档数: {len(doc_scores)}, 返回前{k}个")
        for i, (doc_id, score) in enumerate(sorted_docs[:k]):
            logger.debug(f"最终结果 - rank: {i}, score: {score:.4f}, doc: {doc_id[:50]}...")
        
        return final_docs


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
        initial_results = self.vector_store.query(
            query,
            n_results=fetch_k,
            where=filters
        )
        
        if not initial_results.get("documents") or not initial_results["documents"][0]:
            return []
        
        docs = []
        for i, doc_text in enumerate(initial_results["documents"][0]):
            metadata = initial_results["metadatas"][0][i] if initial_results.get("metadatas") else {}
            distance = initial_results["distances"][0][i] if initial_results.get("distances") else 0
            doc = Document(
                page_content=doc_text,
                metadata={**metadata, "distance": distance}
            )
            docs.append(doc)
        
        query_embedding = self.embedding_service.embed_text_sync(query)
        
        selected = []
        selected_embeddings = []
        remaining = list(range(len(docs)))
        
        while len(selected) < k and remaining:
            best_score = -float("inf")
            best_idx = None
            
            for idx in remaining:
                doc = docs[idx]
                doc_embedding = self.embedding_service.embed_text_sync(doc.page_content)
                
                relevance = 1 - docs[idx].metadata.get("distance", 0)
                
                if selected_embeddings:
                    similarities = [
                        self._cosine_similarity(doc_embedding, sel_emb)
                        for sel_emb in selected_embeddings
                    ]
                    max_similarity = max(similarities) if similarities else 0
                    diversity = 1 - max_similarity
                else:
                    diversity = 1
                
                mmr_score = lambda_mult * relevance + (1 - lambda_mult) * diversity
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            if best_idx is not None:
                selected.append(docs[best_idx])
                selected_embeddings.append(self.embedding_service.embed_text_sync(docs[best_idx].page_content))
                remaining.remove(best_idx)
        
        return selected
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0
        return dot_product / (norm1 * norm2)


class MultiQueryRetriever:
    """多查询检索器 - 生成多个查询变体以提高召回率"""
    
    def __init__(self, vector_store: ChromaVectorStore, llm=None):
        self.vector_store = vector_store
        self.llm = llm
    
    def generate_queries(self, query: str) -> List[str]:
        """生成查询变体"""
        variations = [query]
        
        try:
            from jieba.analyse import extract_tags
            keywords = extract_tags(query, topK=5)
            if keywords:
                variations.append(" ".join(keywords))
        except:
            pass
        
        synonyms = self._get_synonyms(query)
        variations.extend(synonyms)
        
        return list(set(variations))[:5]
    
    def _get_synonyms(self, query: str) -> List[str]:
        """获取同义词查询变体"""
        return []
    
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
        queries = self.generate_queries(query)
        
        all_docs = []
        doc_scores = {}
        
        for q in queries:
            results = self.vector_store.query(q, n_results=k * 2, where=filters)
            
            if results.get("documents") and results["documents"][0]:
                for i, doc_text in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                    distance = results["distances"][0][i] if results.get("distances") else 0
                    
                    doc_id = doc_text[:100]
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
        
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1]["score"], reverse=True)
        return [v["document"] for _, v in sorted_docs[:k]]


class AdvancedRAGService:
    """高级RAG服务 - 整合多种检索策略"""
    
    def __init__(self, vector_store: ChromaVectorStore, documents: List[Document] = None):
        self.vector_store = vector_store
        
        if documents is None:
            logger.info("未传入documents参数，从向量数据库加载文档")
            documents = self._load_documents_from_vector_store(vector_store)
            logger.info(f"从向量数据库加载了 {len(documents)} 个文档用于BM25")
        else:
            logger.info(f"使用传入的 {len(documents)} 个文档用于BM25")
        
        self.hybrid_retriever = HybridRetriever(vector_store, documents)
        self.mmr_retriever = MMRRetriever(vector_store)
        self.multi_query_retriever = MultiQueryRetriever(vector_store)
    
    @staticmethod
    def _load_documents_from_vector_store(vector_store: ChromaVectorStore) -> List[Document]:
        """从向量数据库加载文档用于BM25"""
        all_docs = vector_store.get_all_documents()
        documents = []
        for doc_data in all_docs:
            documents.append(Document(
                page_content=doc_data["document"],
                metadata=doc_data["metadata"]
            ))
        return documents
    
    def search(
        self,
        query: str,
        strategy: str = "hybrid",
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        fetch_k: int = 20,
        lambda_mult: float = 0.5
    ) -> List[Document]:
        """
        执行检索
        
        Args:
            query: 查询文本
            strategy: 检索策略 (hybrid/mmr/multi_query/basic)
            k: 返回结果数量
            filters: 过滤条件
            fetch_k: 初始获取数量（仅MMR有效）
            lambda_mult: 多样性因子（仅MMR有效）
            
        Returns:
            检索结果列表
        """
        if strategy == "hybrid":
            return self.hybrid_retriever.hybrid_search(query, k, filters)
        elif strategy == "mmr":
            return self.mmr_retriever.search(query, k, fetch_k, lambda_mult, filters)
        elif strategy == "multi_query":
            return self.multi_query_retriever.search(query, k, filters)
        else:
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
