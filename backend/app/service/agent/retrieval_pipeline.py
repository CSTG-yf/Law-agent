import asyncio
import time
from typing import List, Optional, Tuple, Dict, Any
from langchain_core.messages import BaseMessage
from langchain_core.documents import Document
from pydantic import BaseModel
from app.service.agent.intent_classifier import IntentClassifier, IntentResult
from app.service.agent.query_rewriter import QueryRewriter, RewrittenQuery
from app.service.agent.rag_retriever import RAGRetriever
from app.service.agent.pre_retriever import PreRetriever, PreRetrieveResult
from app.service.agent.entity_extractor import EntityExtractor, EntityResult
from app.service.vector_db import ChromaVectorStore
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("retrieval_pipeline")


class RetrievalMetadata(BaseModel):
    original_query: str
    rewritten_query: str
    intent: str
    intent_confidence: float
    rewrite_type: str
    retrieval_skipped: bool
    skip_reason: Optional[str] = None
    documents_count: int = 0
    retrieval_strategy: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    pre_retrieval_hint: Optional[str] = None
    parallel_execution: bool = False
    total_time: float = 0.0


class SmartRetrievalPipeline:
    def __init__(
        self,
        llm,
        rag_retriever: RAGRetriever,
        vector_store: Optional[ChromaVectorStore] = None,
        enable_parallel: bool = True,
        use_ner: bool = True
    ):
        self.llm = llm
        self.intent_classifier = IntentClassifier(llm)
        self.query_rewriter = QueryRewriter(llm)
        self.rag_retriever = rag_retriever
        self.enable_parallel = enable_parallel

        if vector_store:
            self.pre_retriever = PreRetriever(vector_store)
            logger.info("预检索服务初始化成功")
        else:
            self.pre_retriever = None
            logger.warning("向量数据库未传入，预检索服务不可用")

        try:
            self.entity_extractor = EntityExtractor(use_ner=use_ner)
            logger.info(f"实体识别模块初始化成功 - use_ner: {use_ner}")
        except Exception as e:
            logger.error(f"实体识别模块初始化失败: {str(e)}")
            self.entity_extractor = None

    async def process(
        self,
        query: str,
        conversation_history: List[BaseMessage],
        use_rag: bool,
        retrieval_strategy: str = "vector",
        enable_rerank: bool = False,
        top_k: int = None
    ) -> Tuple[List[Document], RetrievalMetadata]:
        top_k = top_k or settings.RAG_TOP_K
        
        if self.enable_parallel and self.pre_retriever:
            return await self._process_parallel(
                query=query,
                conversation_history=conversation_history,
                use_rag=use_rag,
                retrieval_strategy=retrieval_strategy,
                enable_rerank=enable_rerank,
                top_k=top_k
            )
        else:
            return await self._process_serial(
                query=query,
                conversation_history=conversation_history,
                use_rag=use_rag,
                retrieval_strategy=retrieval_strategy,
                enable_rerank=enable_rerank,
                top_k=top_k
            )

    async def _process_parallel(
        self,
        query: str,
        conversation_history: List[BaseMessage],
        use_rag: bool,
        retrieval_strategy: str,
        enable_rerank: bool,
        top_k: int
    ) -> Tuple[List[Document], RetrievalMetadata]:
        start_time = time.time()
        logger.info(f"并行检索流程开始 - query: {query[:50]}, use_rag: {use_rag}")

        metadata = RetrievalMetadata(
            original_query=query,
            rewritten_query=query,
            intent="new_question",
            intent_confidence=0.0,
            rewrite_type="无需改写",
            retrieval_skipped=False,
            retrieval_strategy=retrieval_strategy if use_rag else None,
            parallel_execution=True
        )

        tasks = []
        task_names = []

        tasks.append(self.intent_classifier.classify(query, conversation_history))
        task_names.append("intent")

        if self.entity_extractor:
            tasks.append(self.entity_extractor.extract(query))
            task_names.append("entity")

        if use_rag and self.pre_retriever:
            tasks.append(self.pre_retriever.pre_retrieve(query, top_k))
            task_names.append("pre_retrieve")

        logger.info(f"并行执行任务: {task_names}")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        result_map = {}
        for i, name in enumerate(task_names):
            result = results[i]
            if isinstance(result, Exception):
                logger.error(f"任务 {name} 执行失败: {str(result)}")
                result_map[name] = None
            else:
                result_map[name] = result

        intent_result = result_map.get("intent")
        entity_result = result_map.get("entity")
        pre_retrieve_result = result_map.get("pre_retrieve")

        if intent_result:
            metadata.intent = intent_result.intent
            metadata.intent_confidence = intent_result.confidence
            logger.info(f"意图识别结果 - intent: {intent_result.intent}, confidence: {intent_result.confidence}")

        if entity_result:
            metadata.entities = entity_result.entities
            logger.info(f"实体识别结果 - entities: {entity_result.entities}")

        if intent_result and intent_result.intent == "chitchat":
            metadata.retrieval_skipped = True
            metadata.skip_reason = "chitchat_intent"
            metadata.total_time = time.time() - start_time
            logger.info(f"闲聊意图，跳过检索")
            return [], metadata

        if not use_rag:
            metadata.retrieval_skipped = True
            metadata.skip_reason = "rag_disabled"
            metadata.total_time = time.time() - start_time
            logger.info(f"RAG未启用，跳过检索")
            return [], metadata

        if pre_retrieve_result:
            if pre_retrieve_result.documents_count == 0:
                metadata.pre_retrieval_hint = "no_results"
                logger.info(f"预检索无结果，继续执行RAG检索")
            else:
                avg_distance = sum(d.get("distance", 1) for d in pre_retrieve_result.documents) / max(len(pre_retrieve_result.documents), 1)
                min_distance = min(d.get("distance", 1) for d in pre_retrieve_result.documents)
                max_distance = max(d.get("distance", 1) for d in pre_retrieve_result.documents)
                distance_span = max_distance - min_distance

                if distance_span <= 1e-9:
                    normalized_avg_distance = 0.0
                else:
                    normalized_avg_distance = sum(
                        (d.get("distance", 1) - min_distance) / distance_span
                        for d in pre_retrieve_result.documents
                    ) / max(len(pre_retrieve_result.documents), 1)

                if normalized_avg_distance < 0.3:
                    metadata.pre_retrieval_hint = "high_quality"
                    logger.info(
                        f"预检索质量较高 - avg_distance: {avg_distance:.3f}, "
                        f"normalized_avg_distance: {normalized_avg_distance:.3f}"
                    )
                else:
                    metadata.pre_retrieval_hint = "low_quality"
                    logger.info(
                        f"预检索质量一般 - avg_distance: {avg_distance:.3f}, "
                        f"normalized_avg_distance: {normalized_avg_distance:.3f}"
                    )

        if intent_result and intent_result.needs_rewrite:
            rewritten = await self.query_rewriter.rewrite(query, conversation_history)
            metadata.rewritten_query = rewritten.rewritten_query
            metadata.rewrite_type = rewritten.rewrite_type
            logger.info(f"Query改写完成 - type: {rewritten.rewrite_type}")
        elif entity_result:
            enhanced_query = self.entity_extractor.enhance_query(query, entity_result)
            if enhanced_query != query:
                metadata.rewritten_query = enhanced_query
                metadata.rewrite_type = "实体增强"

        query_to_use = metadata.rewritten_query
        logger.info(f"执行RAG检索 - query: {query_to_use[:50]}, strategy: {retrieval_strategy}")

        documents = await self.rag_retriever.retrieve(
            query=query_to_use,
            strategy=retrieval_strategy,
            top_k=top_k,
            enable_rerank=enable_rerank
        )

        metadata.documents_count = len(documents)
        metadata.total_time = time.time() - start_time
        logger.info(f"RAG检索完成 - documents: {len(documents)}, total_time: {metadata.total_time:.3f}s")

        return documents, metadata

    async def _process_serial(
        self,
        query: str,
        conversation_history: List[BaseMessage],
        use_rag: bool,
        retrieval_strategy: str,
        enable_rerank: bool,
        top_k: int
    ) -> Tuple[List[Document], RetrievalMetadata]:
        start_time = time.time()
        logger.info(f"串行检索流程开始 - query: {query[:50]}, use_rag: {use_rag}")

        metadata = RetrievalMetadata(
            original_query=query,
            rewritten_query=query,
            intent="new_question",
            intent_confidence=0.0,
            rewrite_type="无需改写",
            retrieval_skipped=False,
            retrieval_strategy=retrieval_strategy if use_rag else None,
            parallel_execution=False
        )

        intent_result = await self.intent_classifier.classify(query, conversation_history)
        metadata.intent = intent_result.intent
        metadata.intent_confidence = intent_result.confidence

        logger.info(f"意图识别结果 - intent: {intent_result.intent}, confidence: {intent_result.confidence}")

        if intent_result.intent == "chitchat":
            metadata.retrieval_skipped = True
            metadata.skip_reason = "chitchat_intent"
            metadata.total_time = time.time() - start_time
            logger.info(f"闲聊意图，跳过检索")
            return [], metadata

        if not use_rag:
            metadata.retrieval_skipped = True
            metadata.skip_reason = "rag_disabled"
            metadata.total_time = time.time() - start_time
            logger.info(f"RAG未启用，跳过检索")
            return [], metadata

        if intent_result.needs_rewrite:
            rewritten = await self.query_rewriter.rewrite(query, conversation_history)
            metadata.rewritten_query = rewritten.rewritten_query
            metadata.rewrite_type = rewritten.rewrite_type
            logger.info(f"Query改写完成 - type: {rewritten.rewrite_type}")
        else:
            rewritten = await self.query_rewriter.optimize(query)
            if rewritten.rewritten_query != query:
                metadata.rewritten_query = rewritten.rewritten_query
                metadata.rewrite_type = rewritten.rewrite_type
                logger.info(f"Query优化完成")

        query_to_use = metadata.rewritten_query
        logger.info(f"开始检索 - query: {query_to_use[:50]}, strategy: {retrieval_strategy}")

        documents = await self.rag_retriever.retrieve(
            query=query_to_use,
            strategy=retrieval_strategy,
            top_k=top_k,
            enable_rerank=enable_rerank
        )

        metadata.documents_count = len(documents)
        metadata.total_time = time.time() - start_time
        logger.info(f"检索完成 - documents: {len(documents)}, total_time: {metadata.total_time:.3f}s")

        return documents, metadata

    async def classify_intent_only(
        self,
        query: str,
        conversation_history: List[BaseMessage]
    ) -> IntentResult:
        return await self.intent_classifier.classify(query, conversation_history)

    async def rewrite_query_only(
        self,
        query: str,
        conversation_history: List[BaseMessage]
    ) -> RewrittenQuery:
        return await self.query_rewriter.rewrite(query, conversation_history)

    async def extract_entities_only(self, query: str) -> EntityResult:
        if self.entity_extractor:
            return await self.entity_extractor.extract(query)
        return EntityResult()
