# backend/app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")
    
    # OpenAI/DashScope 配置
    OPENAI_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    OPENAI_API_KEY: str = ""
    DASHSCOPE_API_KEY: str = ""
    HF_TOKEN: str = ""
    MODEL_NAME: str = "qwen-max-latest"
    
    # RAG 检索配置（可动态配置）
    RAG_TOP_K: int = 5
    RAG_FETCH_K: int = 20
    MMR_MAX_FETCH_K: int = 20
    PRE_RETRIEVE_TOP_K: int = 5
    MAX_HISTORY_LENGTH: int = 10
    
    # Neo4j 配置（硬编码）
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "legal_password_2024"
    
    # Chroma 配置（硬编码）
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    
    # Ollama 配置（硬编码）
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "demonbyron/embeddinggemma-300m-lawvault"
    
    # Redis 配置（硬编码）
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # 知识图谱配置（可动态配置）
    GRAPH_MODEL_NAME: str = "qwen-max-latest"
    GRAPH_STRICT_MODE: bool = True
    GRAPH_MAX_CHUNK_SIZE: int = 10000


def reload_settings() -> Settings:
    """重新加载配置"""
    global settings
    settings = Settings()
    return settings


settings = Settings()