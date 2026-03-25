from typing import Optional
from langchain_openai import ChatOpenAI
from app.service.vector_db import ChromaVectorStore
from app.service.agent.legal_conversation_agent import LegalConversationAgent
from app.service.agent.rag_retriever import RAGRetriever
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("agent_factory")


class AgentFactory:
    _instance = None
    _agents = {}
    _llm = None
    _vector_db = None
    _rag_retriever = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_llm(cls) -> ChatOpenAI:
        if cls._llm is None:
            logger.info(f"初始化LLM - model: {settings.MODEL_NAME}")
            cls._llm = ChatOpenAI(
                base_url=settings.OPENAI_BASE_URL,
                api_key=settings.OPENAI_API_KEY,
                model=settings.MODEL_NAME,
                temperature=0.7,
                streaming=True
            )
        return cls._llm

    @classmethod
    def get_vector_db(cls) -> ChromaVectorStore:
        if cls._vector_db is None:
            logger.info("初始化向量数据库")
            cls._vector_db = ChromaVectorStore()
        return cls._vector_db

    @classmethod
    def get_rag_retriever(cls) -> Optional[RAGRetriever]:
        if cls._rag_retriever is None:
            try:
                vector_db = cls.get_vector_db()
                cls._rag_retriever = RAGRetriever(vector_db)
                logger.info("RAG检索器初始化成功")
            except Exception as e:
                logger.error(f"RAG检索器初始化失败: {e}")
                return None
        return cls._rag_retriever

    @classmethod
    def get_conversation_agent(
        cls,
        max_history: int = None,
        enable_parallel: bool = True,
        use_ner: bool = True
    ) -> LegalConversationAgent:
        max_history = max_history or settings.MAX_HISTORY_LENGTH
        key = f"conversation_{max_history}_{enable_parallel}_{use_ner}"

        if key not in cls._agents:
            llm = cls.get_llm()
            rag_retriever = cls.get_rag_retriever()
            vector_db = cls.get_vector_db()

            cls._agents[key] = LegalConversationAgent(
                llm=llm,
                rag_retriever=rag_retriever,
                vector_db=vector_db,
                max_history=max_history,
                enable_parallel=enable_parallel,
                use_ner=use_ner
            )

            logger.info(f"对话Agent初始化成功 - max_history: {max_history}, enable_parallel: {enable_parallel}, use_ner: {use_ner}")

        return cls._agents[key]

    @classmethod
    def reset(cls):
        cls._agents = {}
        cls._llm = None
        cls._vector_db = None
        cls._rag_retriever = None
        logger.info("Agent工厂已重置")
