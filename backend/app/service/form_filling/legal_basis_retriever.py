from typing import List, Optional, Dict, Any
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from app.service.vector_db import ChromaVectorStore
from app.service.rag.hybrid_retriever import AdvancedRAGService
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("legal_basis_retriever")


class LegalBasisRetriever:
    _instance = None
    _rag_service: Optional[AdvancedRAGService] = None
    _llm: Optional[ChatOpenAI] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def _get_rag_service(cls) -> AdvancedRAGService:
        if cls._rag_service is None:
            try:
                vector_store = ChromaVectorStore(collection_name="legal_documents")
                cls._rag_service = AdvancedRAGService(vector_store)
                logger.info("法律条文检索RAG服务初始化成功")
            except Exception as e:
                logger.error(f"法律条文检索RAG服务初始化失败: {e}")
                raise
        return cls._rag_service

    @classmethod
    def _get_llm(cls) -> ChatOpenAI:
        if cls._llm is None:
            cls._llm = ChatOpenAI(
                base_url=settings.OPENAI_BASE_URL,
                api_key=settings.OPENAI_API_KEY,
                model=settings.MODEL_NAME,
                temperature=0.3
            )
        return cls._llm

    @classmethod
    async def retrieve_and_generate(
        cls,
        facts_summary: str,
        claims_summary: str = ""
    ) -> Optional[str]:
        query_parts = []
        if claims_summary:
            query_parts.append(f"诉讼请求：{claims_summary}")
        if facts_summary:
            query_parts.append(f"事实情况：{facts_summary}")
        query = "；".join(query_parts)

        logger.info(f"开始检索法律条文 - query: {query[:200]}")

        try:
            rag_service = cls._get_rag_service()
            docs = rag_service.search(
                query=query,
                strategy="hybrid",
                k=8
            )

            logger.info(f"混合检索完成 - 检索到 {len(docs)} 条相关法律条文")

            if not docs:
                logger.warning("未检索到相关法律条文")
                return None

            context_parts = []
            for i, doc in enumerate(docs):
                source = doc.metadata.get("source", "unknown")
                file_name = doc.metadata.get("file_name", "未知")
                context_parts.append(f"[条文{i+1}] {doc.page_content}")
                logger.info(f"检索结果[{i+1}] - source: {source}, file: {file_name}, content: {doc.page_content[:100]}...")

            context = "\n\n".join(context_parts)

            legal_basis = await cls._generate_legal_basis(
                facts_summary=facts_summary,
                claims_summary=claims_summary,
                legal_context=context
            )

            logger.info(f"法律条文生成完成 - legal_basis: {legal_basis[:200]}...")
            return legal_basis

        except Exception as e:
            logger.error(f"检索法律条文失败: {e}")
            return None

    @classmethod
    async def _generate_legal_basis(
        cls,
        facts_summary: str,
        claims_summary: str,
        legal_context: str
    ) -> str:
        llm = cls._get_llm()

        prompt = f"""你是一名专业的劳动法律师。请根据以下案件事实和诉讼请求，从提供的法律条文中选择最相关的条文，生成专业的诉请依据。

要求：
1. 只引用与案件事实直接相关的法律条文
2. 必须写明具体的法律名称和条文编号（如《中华人民共和国劳动法》第四十四条）
3. 每条引用后简要说明该条文如何适用于本案
4. 语言要专业、简洁，符合法律文书规范
5. 按照逻辑顺序排列，先列实体法依据，再列程序法依据
6. 如果没有找到完全匹配的条文，选择最接近的条文并说明适用理由

案件事实：
{facts_summary}

诉讼请求：
{claims_summary}

相关法律条文：
{legal_context}

请直接输出诉请依据，不要输出其他内容。格式示例：
根据《中华人民共和国劳动合同法》第XX条规定，[条文内容摘要]。本案中，[适用理由]。
根据《中华人民共和国劳动法》第XX条规定，[条文内容摘要]。本案中，[适用理由]。"""

        try:
            response = await llm.ainvoke(prompt)
            return response.content.strip()
        except Exception as e:
            logger.error(f"生成法律依据失败: {e}")
            return ""


def get_legal_basis_retriever() -> LegalBasisRetriever:
    return LegalBasisRetriever()
