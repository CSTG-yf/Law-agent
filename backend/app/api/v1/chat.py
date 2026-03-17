from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/")
async def chat_root():
    return {"message": "Chat API"}