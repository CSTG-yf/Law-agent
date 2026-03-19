from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class EnvConfigUpdate(BaseModel):
    OPENAI_BASE_URL: Optional[str] = Field(None, description="OpenAI API base URL")
    OPENAI_API_KEY: Optional[str] = Field(None, description="OpenAI API key")
    DASHSCOPE_API_KEY: Optional[str] = Field(None, description="DashScope API key")
    HF_TOKEN: Optional[str] = Field(None, description="Hugging Face token")


class EnvConfigResponse(BaseModel):
    status: str
    message: str
    config: Optional[Dict[str, Any]] = None
