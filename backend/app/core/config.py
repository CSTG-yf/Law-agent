# backend/app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")
    
    # OpenAI/DashScope 配置
    OPENAI_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    OPENAI_API_KEY: str = ""
    DASHSCOPE_API_KEY: str = ""
    MODEL_NAME: str = "qwen-max-latest"
    
    # Neo4j 配置
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "legal_password_2024"
    
    # Chroma 配置
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    
    # Ollama 配置
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "demonbyron/embeddinggemma-300m-lawvault"
    
    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

settings = Settings()