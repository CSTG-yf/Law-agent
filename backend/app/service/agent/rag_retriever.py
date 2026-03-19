from typing import List, Optional
from langchain_core.documents import Document
from app.service.vector_db import ChromaVectorStore
from app.service.rag.hybrid_retriever import AdvancedRAGService


class RAGRetriever:
    def __init__(self, vector_store: ChromaVectorStore):
        self.vector_store = vector_store
        self.rag_service = AdvancedRAGService(vector_store)

    async def retrieve(
        self,
        query: str,
        strategy: str = "vector",
        top_k: int = 5,
        score_threshold: float = 0.7
    ) -> List[Document]:
        if strategy == "vector":
            return await self._vector_search(query, top_k, score_threshold)
        elif strategy == "hybrid":
            return await self._hybrid_search(query, top_k)
        elif strategy == "mmr":
            return await self._mmr_search(query, top_k)
        elif strategy == "multi_query":
            return await self._multi_query_search(query, top_k)
        else:
            return []

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
            fetch_k=20,
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
