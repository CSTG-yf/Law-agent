from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import rag, chat, config
from app.core.config import settings

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
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )