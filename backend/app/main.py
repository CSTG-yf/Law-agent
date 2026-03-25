import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import rag, chat, config
from app.core.config import settings
from app.core.logger import setup_logging, api_logger
import time
import json

setup_logging()

app = FastAPI(
    title="Legal AI Agent API",
    description="法律AI助手API - 基于RAG的智能法律咨询系统",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    method = request.method
    path = request.url.path
    
    try:
        body = await request.body()
        params = {}
        if body:
            try:
                params = json.loads(body.decode())
            except:
                params = {"raw_body": str(body)[:200]}
        
        headers = dict(request.headers)
        
        api_logger.log_request(method, path, params, headers)
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        api_logger.log_response(method, path, response.status_code, None, duration)
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        api_logger.log_error(method, path, e, duration)
        raise


app.include_router(rag.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(config.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "message": "Legal AI Agent API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "ollama": settings.OLLAMA_HOST,
            "chroma": f"{settings.CHROMA_HOST}:{settings.CHROMA_PORT}",
            "neo4j": settings.NEO4J_URI
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",  # 应用模块和函数名
        host="0.0.0.0",  # 监听所有IP地址
        port=8000,  # 监听端口
        reload=False   # 开启后会自动重启服务器，但会占用更多内存
    )