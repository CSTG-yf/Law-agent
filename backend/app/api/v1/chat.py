import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage
from app.schema.chat import (
    ChatRequest,
    ChatResponse,
    ConversationHistory,
    SessionInfo,
    ErrorResponse
)
from app.service.agent.factory import AgentFactory
from app.service.agent.sse_streamer import StreamingResponseBuilder
from app.core.constants import HttpStatus
from app.core.config import settings
from app.core.logger import get_logger

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = get_logger("chat_api")

streaming_builder = StreamingResponseBuilder()

_sessions = {}


@router.post("/message", response_model=dict)
async def send_message(request: ChatRequest):
    try:
        logger.info(f"收到聊天消息请求 - session_id: {request.session_id}, user_id: {request.user_id}, message: {request.message[:100]}")
        
        agent = AgentFactory.get_conversation_agent(
            max_history=request.max_history or 10
        )

        session_id = request.session_id
        user_id = request.user_id

        if session_id is None:
            session_id = f"session-{uuid.uuid4().hex[:12]}"
            logger.info(f"自动生成session_id - session_id: {session_id}")

        if session_id not in _sessions:
            _sessions[session_id] = {
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "messages": [],
                "rag_enabled": request.use_rag
            }
            logger.info(f"创建新会话 - session_id: {session_id}")

        session = _sessions[session_id]

        config = {"configurable": {"thread_id": session_id}}

        new_message = HumanMessage(content=request.message)

        state_update = {
            "messages": [new_message],
            "use_rag": request.use_rag,
            "retrieval_strategy": request.retrieval_strategy or "vector",
        }

        if request.stream:
            logger.info(f"开始流式响应 - session_id: {session_id}")
            return await streaming_builder.build_conversation_stream(
                agent.get_compiled_graph(),
                state_update,
                config
            )
        else:
            logger.info(f"开始非流式响应 - session_id: {session_id}, use_rag: {request.use_rag}")
            result = await agent.ainvoke(state_update, config=config)

            assistant_message = result["messages"][-1]
            if isinstance(assistant_message, AIMessage):
                content = assistant_message.content
            else:
                content = str(assistant_message)

            sources = []
            if result.get("context"):
                for doc in result["context"]:
                    source_info = {
                        "content": doc.page_content[:200],
                        "metadata": doc.metadata
                    }
                    sources.append(source_info)

            session["messages"] = []
            for msg in result["messages"]:
                if isinstance(msg, HumanMessage):
                    session["messages"].append({
                        "role": "user",
                        "content": msg.content,
                        "timestamp": datetime.now().isoformat()
                    })
                elif isinstance(msg, AIMessage):
                    session["messages"].append({
                        "role": "assistant",
                        "content": msg.content,
                        "timestamp": datetime.now().isoformat()
                    })

            response = ChatResponse(
                message_id=str(uuid.uuid4()),
                session_id=session_id,
                role="assistant",
                content=content,
                timestamp=datetime.now().isoformat(),
                sources=sources if sources else None,
                rag_used=request.use_rag,
                retrieval_strategy=request.retrieval_strategy if request.use_rag else None
            )

            logger.info(f"聊天消息处理完成 - session_id: {session_id}, response_length: {len(content)}")
            return {
                "code": HttpStatus.OK,
                "status": "success",
                "message": "",
                "data": response.model_dump()
            }

    except Exception as e:
        logger.error(f"聊天消息处理失败 - session_id: {request.session_id}, error: {str(e)}")
        raise HTTPException(
            status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/sessions/{session_id}", response_model=dict)
async def get_session(session_id: str):
    logger.info(f"查询会话信息 - session_id: {session_id}")
    
    if session_id not in _sessions:
        logger.warning(f"会话不存在 - session_id: {session_id}")
        raise HTTPException(
            status_code=HttpStatus.NOT_FOUND,
            detail="Session not found"
        )

    session = _sessions[session_id]

    session_info = SessionInfo(
        session_id=session_id,
        user_id=session["user_id"],
        created_at=session["created_at"],
        message_count=len(session["messages"]),
        rag_enabled=session.get("rag_enabled", False)
    )

    logger.info(f"查询会话信息成功 - session_id: {session_id}, message_count: {len(session['messages'])}")
    return {
        "code": HttpStatus.OK,
        "status": "success",
        "message": "",
        "data": session_info.model_dump()
    }


@router.get("/sessions/{session_id}/history", response_model=dict)
async def get_conversation_history(session_id: str, limit: Optional[int] = None):
    logger.info(f"查询会话历史 - session_id: {session_id}, limit: {limit}")
    
    if session_id not in _sessions:
        logger.warning(f"会话不存在 - session_id: {session_id}")
        raise HTTPException(
            status_code=HttpStatus.NOT_FOUND,
            detail="Session not found"
        )

    session = _sessions[session_id]
    messages = session["messages"]

    if limit and limit > 0:
        messages = messages[-limit:]

    history = ConversationHistory(
        session_id=session_id,
        messages=messages,
        total_messages=len(session["messages"]),
        created_at=session["created_at"],
        updated_at=datetime.now().isoformat()
    )

    logger.info(f"查询会话历史成功 - session_id: {session_id}, returned_messages: {len(messages)}")
    return {
        "code": HttpStatus.OK,
        "status": "success",
        "message": "",
        "data": history.model_dump()
    }


@router.delete("/sessions/{session_id}", response_model=dict)
async def delete_session(session_id: str):
    logger.info(f"删除会话 - session_id: {session_id}")
    
    if session_id not in _sessions:
        logger.warning(f"会话不存在 - session_id: {session_id}")
        raise HTTPException(
            status_code=HttpStatus.NOT_FOUND,
            detail="Session not found"
        )

    del _sessions[session_id]

    logger.info(f"删除会话成功 - session_id: {session_id}")
    return {
        "code": HttpStatus.OK,
        "status": "success",
        "message": "Session deleted successfully",
        "data": None
    }


@router.get("/sessions", response_model=dict)
async def list_sessions(user_id: Optional[str] = None):
    logger.info(f"查询会话列表 - user_id: {user_id}")
    
    sessions = []

    for session_id, session_data in _sessions.items():
        if user_id is None or session_data["user_id"] == user_id:
            sessions.append(SessionInfo(
                session_id=session_id,
                user_id=session_data["user_id"],
                created_at=session_data["created_at"],
                message_count=len(session_data["messages"]),
                rag_enabled=session_data.get("rag_enabled", False)
            ))

    logger.info(f"查询会话列表成功 - total: {len(sessions)}")
    return {
        "code": HttpStatus.OK,
        "status": "success",
        "message": "",
        "data": {
            "sessions": [s.model_dump() for s in sessions],
            "total": len(sessions)
        }
    }


@router.post("/sessions/{session_id}/clear", response_model=dict)
async def clear_session_history(session_id: str):
    logger.info(f"清空会话历史 - session_id: {session_id}")
    
    if session_id not in _sessions:
        logger.warning(f"会话不存在 - session_id: {session_id}")
        raise HTTPException(
            status_code=HttpStatus.NOT_FOUND,
            detail="Session not found"
        )

    _sessions[session_id]["messages"] = []

    logger.info(f"清空会话历史成功 - session_id: {session_id}")
    return {
        "code": HttpStatus.OK,
        "status": "success",
        "message": "Session history cleared",
        "data": None
    }
