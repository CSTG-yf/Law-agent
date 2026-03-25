from typing import List, Optional
from langchain_core.documents import Document
from app.service.vector_db import ChromaVectorStore
from app.service.rag.hybrid_retriever import AdvancedRAGService
from app.service.rag.reranker import Reranker
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("rag_retriever")


class RAGRetriever:
    def __init__(self, vector_store: ChromaVectorStore):
        self.vector_store = vector_store
        self.rag_service = AdvancedRAGService(vector_store)
        self.reranker = Reranker()

    async def retrieve(
        self,
        query: str,
        strategy: str = "vector",
        top_k: int = None,
        score_threshold: float = 0.7,
        enable_rerank: bool = False
    ) -> List[Document]:
        top_k = top_k or settings.RAG_TOP_K
        logger.info(f"开始RAG检索 - query: {query[:100]}, strategy: {strategy}, top_k: {top_k}, enable_rerank: {enable_rerank}")

        if strategy == "vector":
            documents = await self._vector_search(query, top_k, score_threshold)
        elif strategy == "hybrid":
            documents = await self._hybrid_search(query, top_k)
        elif strategy == "mmr":
            documents = await self._mmr_search(query, top_k)
        elif strategy == "multi_query":
            documents = await self._multi_query_search(query, top_k)
        else:
            documents = []

        logger.info(f"检索完成 - 检索到 {len(documents)} 个文档")

        if enable_rerank and documents:
            logger.info(f"启用重排序 - 对 {len(documents)} 个文档进行重排序")
            documents = self.reranker.rerank(
                query=query,
                documents=documents,
                top_k=top_k
            )
            logger.info(f"重排序完成 - 返回 {len(documents)} 个文档")
        elif enable_rerank:
            logger.warning(f"enable_rerank=true 但没有检索到文档，跳过重排序")
        else:
            logger.info(f"未启用重排序 - 直接返回检索结果")

        return documents

    async def _vector_search(
        self,
        query: str,
        top_k: int,
        score_threshold: float
    ) -> List[Document]:
        results = self.vector_store.query(
            query,
            n_results=top_k
        )

        filtered_results = []
        if results.get("documents") and results["documents"][0]:
            for i, doc_text in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results.get("distances") else 0
                if distance <= (1 - score_threshold):
                    metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                    doc = Document(
                        page_content=doc_text,
                        metadata={**metadata, "distance": distance, "source": "vector"}
                    )
                    filtered_results.append(doc)

        return filtered_results

    async def _hybrid_search(self, query: str, top_k: int) -> List[Document]:
        return self.rag_service.search(
            query=query,
            strategy="hybrid",
            k=top_k
        )

    async def _mmr_search(self, query: str, top_k: int) -> List[Document]:
        return self.rag_service.search(
            query=query,
            strategy="mmr",
            k=top_k,
            fetch_k=settings.RAG_FETCH_K,
            lambda_mult=0.5
        )

    async def _multi_query_search(self, query: str, top_k: int) -> List[Document]:
        return self.rag_service.search(
            query=query,
            strategy="multi_query",
            k=top_k
        )

    async def retrieve_with_metadata(
        self,
        query: str,
        strategy: str = "vector",
        filters: Optional[dict] = None,
        top_k: int = 5
    ) -> List[Document]:
        if filters:
            results = self.vector_store.query(
                query,
                n_results=top_k,
                where=filters
            )
            docs = []
            if results.get("documents") and results["documents"][0]:
                for i, doc_text in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                    distance = results["distances"][0][i] if results.get("distances") else 0
                    doc = Document(
                        page_content=doc_text,
                        metadata={**metadata, "distance": distance}
                    )
                    docs.append(doc)
            return docs

        return await self.retrieve(query, strategy, top_k)
