import time
from typing import List, Optional
from langchain_core.documents import Document
from pydantic import BaseModel
from app.service.vector_db import ChromaVectorStore
from app.core.logger import get_logger

logger = get_logger("pre_retriever")


class PreRetrieveResult(BaseModel):
    query: str
    documents: List[dict] = []
    retrieval_time: float = 0.0
    documents_count: int = 0


class PreRetriever:
    def __init__(self, vector_store: ChromaVectorStore):
        self.vector_store = vector_store

    async def pre_retrieve(
        self,
        query: str,
        top_k: int = 5
    ) -> PreRetrieveResult:
        start_time = time.time()
        logger.info(f"预检索开始 - query: {query[:50]}, top_k: {top_k}")

        try:
            results = self.vector_store.query(
                query_text=query,
                n_results=top_k
            )

            documents = []
            if results.get("documents") and results["documents"][0]:
                for i, doc_text in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                    distance = results["distances"][0][i] if results.get("distances") else 0
                    documents.append({
                        "content": doc_text,
                        "metadata": metadata,
                        "distance": distance
                    })

            retrieval_time = time.time() - start_time
            logger.info(f"预检索完成 - documents: {len(documents)}, time: {retrieval_time:.3f}s")

            return PreRetrieveResult(
                query=query,
                documents=documents,
                retrieval_time=retrieval_time,
                documents_count=len(documents)
            )

        except Exception as e:
            logger.error(f"预检索失败 - error: {str(e)}")
            return PreRetrieveResult(
                query=query,
                documents=[],
                retrieval_time=time.time() - start_time,
                documents_count=0
            )

    def convert_to_documents(self, pre_result: PreRetrieveResult) -> List[Document]:
        documents = []
        for doc_dict in pre_result.documents:
            doc = Document(
                page_content=doc_dict["content"],
                metadata=doc_dict.get("metadata", {})
            )
            doc.metadata["distance"] = doc_dict.get("distance", 0)
            doc.metadata["source"] = "pre_retrieval"
            documents.append(doc)
        return documents
