from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class EnvConfigUpdate(BaseModel):
    OPENAI_BASE_URL: Optional[str] = Field(None, description="OpenAI API base URL")
    OPENAI_API_KEY: Optional[str] = Field(None, description="OpenAI API key")
    DASHSCOPE_API_KEY: Optional[str] = Field(None, description="DashScope API key")
    HF_TOKEN: Optional[str] = Field(None, description="Hugging Face token")
    MODEL_NAME: Optional[str] = Field(None, description="LLM model name")
    
    RAG_TOP_K: Optional[int] = Field(None, ge=1, le=50, description="RAG检索返回文档数量")
    RAG_FETCH_K: Optional[int] = Field(None, ge=5, le=100, description="MMR检索初始获取文档数量")
    PRE_RETRIEVE_TOP_K: Optional[int] = Field(None, ge=1, le=20, description="预检索返回文档数量")
    MAX_HISTORY_LENGTH: Optional[int] = Field(None, ge=1, le=50, description="对话上下文最大长度")


class EnvConfigData(BaseModel):
    config: Optional[Dict[str, Any]] = None


class EnvConfigResponse(BaseModel):
    code: int
    status: str
    message: str
    data: Optional[EnvConfigData] = None
