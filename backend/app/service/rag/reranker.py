import os
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from langchain_core.documents import Document
from app.core.logger import get_logger

logger = get_logger("reranker")

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    logger.warning("sentence-transformers库未安装，Cross-Encoder不可用")

from app.service.rag.ollama_embedding import OllamaEmbedding
import numpy as np

MODELS_DIR = Path(__file__).parent.parent.parent.parent / "huggingface_models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

RERANKER_MODEL_DIR = MODELS_DIR / "reranker_model"


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
        self.local_model_path = RERANKER_MODEL_DIR
        self._load_model()
    
    def _load_model(self):
        """加载Cross-Encoder模型"""
        if not CROSS_ENCODER_AVAILABLE:
            logger.warning("Cross-Encoder不可用，将使用基于嵌入相似度的后备排序方法")
            return
            
        try:
            start_time = time.time()
            
            if self._is_model_cached():
                logger.info(f"从本地缓存加载Cross-Encoder模型: {self.local_model_path}")
                self.model = CrossEncoder(str(self.local_model_path))
            else:
                logger.info(f"首次运行，从Hugging Face下载Cross-Encoder模型到: {self.local_model_path}")
                self._download_and_cache_model()
                self.model = CrossEncoder(str(self.local_model_path))
            
            load_time = time.time() - start_time
            logger.info(f"Cross-Encoder模型加载完成 - time: {load_time:.2f}s")
            
        except Exception as e:
            logger.error(f"加载Cross-Encoder模型失败: {e}")
            logger.warning("将使用基于嵌入相似度的后备排序方法")
    
    def _is_model_cached(self) -> bool:
        config_file = self.local_model_path / "config.json"
        model_file = self.local_model_path / "pytorch_model.bin"
        tokenizer_file = self.local_model_path / "tokenizer.json"
        
        return config_file.exists() and (model_file.exists() or (self.local_model_path / "model.safetensors").exists()) and tokenizer_file.exists()
    
    def _download_and_cache_model(self):
        try:
            self.local_model_path.mkdir(parents=True, exist_ok=True)
            
            model = CrossEncoder(self.model_name)
            model.save(str(self.local_model_path))
            
            logger.info(f"Cross-Encoder模型已保存到本地: {self.local_model_path}")
            
        except Exception as e:
            logger.error(f"下载Cross-Encoder模型失败: {str(e)}")
            raise
    
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = None
    ) -> List[Document]:
        """
        对文档进行重排序
        
        Args:
            query: 查询文本
            documents: 待排序的文档列表
            top_k: 返回前k个结果（None表示返回全部）
            
        Returns:
            重排序后的文档列表
        """
        if not documents:
            return []
        
        if self.model is not None:
            return self._rerank_with_cross_encoder(query, documents, top_k)
        else:
            return self._rerank_with_embeddings(query, documents, top_k)
    
    def _rerank_with_cross_encoder(
        self,
        query: str,
        documents: List[Document],
        top_k: int = None
    ) -> List[Document]:
        """使用Cross-Encoder进行重排序"""
        pairs = [[query, doc.page_content] for doc in documents]
        
        scores = self.model.predict(pairs)
        
        doc_scores = list(zip(documents, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        if top_k is not None:
            doc_scores = doc_scores[:top_k]
        
        reranked = []
        for doc, score in doc_scores:
            doc.metadata["rerank_score"] = float(score)
            reranked.append(doc)
        
        return reranked
    
    def _rerank_with_embeddings(
        self,
        query: str,
        documents: List[Document],
        top_k: int = None
    ) -> List[Document]:
        """使用嵌入相似度进行后备排序"""
        embedding_service = OllamaEmbedding()
        
        try:
            query_embedding = embedding_service.embed_text_sync(query)
        except Exception as e:
            logger.error(f"生成查询嵌入失败: {e}")
            return documents[:top_k] if top_k else documents
        
        doc_scores = []
        for doc in documents:
            try:
                doc_embedding = embedding_service.embed_text_sync(doc.page_content)
                similarity = self._cosine_similarity(query_embedding, doc_embedding)
                doc_scores.append((doc, similarity))
            except Exception as e:
                logger.error(f"生成文档嵌入失败: {e}")
                doc_scores.append((doc, 0))
        
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        if top_k is not None:
            doc_scores = doc_scores[:top_k]
        
        reranked = []
        for doc, score in doc_scores:
            doc.metadata["rerank_score"] = float(score)
            reranked.append(doc)
        
        return reranked
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0
        return dot_product / (norm1 * norm2)


class MMRReranker:
    """基于最大边际相关性的重排序器"""
    
    def __init__(self, lambda_mult: float = 0.5):
        """
        初始化MMR重排序器
        
        Args:
            lambda_mult: 多样性因子 (0=最大多样性, 1=最大相关性)
        """
        self.lambda_mult = lambda_mult
        self.embedding_service = OllamaEmbedding()
    
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = None
    ) -> List[Document]:
        """
        使用MMR进行重排序
        
        Args:
            query: 查询文本
            documents: 待排序的文档列表
            top_k: 返回前k个结果
            
        Returns:
            重排序后的文档列表
        """
        if not documents:
            return []
        
        if top_k is None:
            top_k = len(documents)
        
        try:
            query_embedding = self.embedding_service.embed_text_sync(query)
        except Exception as e:
            logger.error(f"生成查询嵌入失败: {e}")
            return documents[:top_k]
        
        doc_embeddings = []
        for doc in documents:
            try:
                emb = self.embedding_service.embed_text_sync(doc.page_content)
                doc_embeddings.append(emb)
            except Exception as e:
                logger.error(f"生成文档嵌入失败: {e}")
                doc_embeddings.append([0] * 384)
        
        similarities = []
        for emb in doc_embeddings:
            sim = self._cosine_similarity(query_embedding, emb)
            similarities.append(sim)
        
        for i, doc in enumerate(documents):
            doc.metadata["relevance_score"] = similarities[i]
        
        selected = []
        remaining = list(range(len(documents)))
        
        while len(selected) < top_k and remaining:
            best_score = -float("inf")
            best_idx = None
            
            for idx in remaining:
                relevance = similarities[idx]
                
                if selected:
                    max_sim = -float("inf")
                    for sel_idx in selected:
                        sim = self._cosine_similarity(doc_embeddings[idx], doc_embeddings[sel_idx])
                        max_sim = max(max_sim, sim)
                    diversity = 1 - max_sim
                else:
                    diversity = 1
                
                mmr_score = self.lambda_mult * relevance + (1 - self.lambda_mult) * diversity
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            if best_idx is not None:
                selected.append(best_idx)
                remaining.remove(best_idx)
        
        return [documents[i] for i in selected]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0
        return dot_product / (norm1 * norm2)


class EnsembleReranker:
    """集成重排序器 - 结合多种排序策略"""
    
    def __init__(self, rerankers: List[Any] = None, weights: List[float] = None):
        """
        初始化集成重排序器
        
        Args:
            rerankers: 重排序器列表
            weights: 各重排序器的权重
        """
        self.rerankers = rerankers or []
        self.weights = weights or [1.0] * len(self.rerankers)
        
        if len(self.weights) != len(self.rerankers):
            self.weights = [1.0] * len(self.rerankers)
    
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = None
    ) -> List[Document]:
        """
        使用集成策略进行重排序
        
        Args:
            query: 查询文本
            documents: 待排序的文档列表
            top_k: 返回前k个结果
            
        Returns:
            重排序后的文档列表
        """
        if not documents:
            return []
        
        if not self.rerankers:
            return documents[:top_k] if top_k else documents
        
        doc_scores = {doc.page_content[:100]: 0.0 for doc in documents}
        
        total_weight = sum(self.weights)
        
        for reranker, weight in zip(self.rerankers, self.weights):
            try:
                reranked = reranker.rerank(query, documents)
                
                for rank, doc in enumerate(reranked):
                    doc_id = doc.page_content[:100]
                    score = (len(reranked) - rank) / len(reranked)
                    
                    if doc_id in doc_scores:
                        doc_scores[doc_id] += (weight / total_weight) * score
            except Exception as e:
                logger.error(f"重排序器执行失败: {e}")
                continue
        
        doc_with_scores = []
        for doc in documents:
            doc_id = doc.page_content[:100]
            score = doc_scores.get(doc_id, 0)
            doc_with_scores.append((doc, score))
        
        doc_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        if top_k is not None:
            doc_with_scores = doc_with_scores[:top_k]
        
        return [doc for doc, _ in doc_with_scores]


class ContextualCompressionReranker:
    """上下文压缩重排序器 - 提取与查询最相关的部分"""
    
    def __init__(self, llm = None):
        """
        初始化上下文压缩重排序器
        
        Args:
            llm: LLM实例（用于提取相关部分）
        """
        self.llm = llm
    
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = None
    ) -> List[Document]:
        """
        压缩文档内容，保留与查询最相关的部分
        
        Args:
            query: 查询文本
            documents: 待压缩的文档列表
            top_k: 返回前k个结果
            
        Returns:
            压缩后的文档列表
        """
        if not documents:
            return []
        
        if top_k is None:
            top_k = len(documents)
        
        if self.llm is None:
            return documents[:top_k]
        
        compressed_docs = []
        
        for doc in documents:
            try:
                compressed_content = self._compress_document(query, doc.page_content)
                
                compressed_doc = Document(
                    page_content=compressed_content,
                    metadata=doc.metadata.copy()
                )
                compressed_docs.append(compressed_doc)
            except Exception as e:
                logger.error(f"压缩文档失败: {e}")
                compressed_docs.append(doc)
        
        return compressed_docs[:top_k]
    
    def _compress_document(self, query: str, content: str) -> str:
        """使用LLM压缩文档内容"""
        prompt = f"""从以下文档中提取与问题"{query}"最相关的部分。
        
文档内容：
{content}

相关部分："""
        
        try:
            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"LLM压缩失败: {e}")
            return content
