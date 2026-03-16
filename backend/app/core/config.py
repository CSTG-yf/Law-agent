# backend/app/core/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 现有配置...
    
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
    
    class Config:
        env_file = ".env"

settings = Settings()