import uuid
from datetime import datetime
from typing import Optional
from openai import OpenAI
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage
from app.schema.chat import (
    ChatRequest,
    ChatResponse,
    ConversationHistory,
    SessionInfo,
    ErrorResponse,
    ToolsListResponse
)
from app.service.agent.factory import AgentFactory
from app.service.agent.sse_streamer import StreamingResponseBuilder
from app.service.agent.official_tools import get_available_tools
from app.core.constants import HttpStatus
from app.core.config import settings
from app.core.logger import get_logger

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = get_logger("chat_api")

streaming_builder = StreamingResponseBuilder()

client = OpenAI(
    base_url=settings.OPENAI_BASE_URL,
    api_key=settings.DASHSCOPE_API_KEY or settings.OPENAI_API_KEY
)

_sessions = {}


async def generate_session_title(user_message: str, assistant_message: str) -> str:
    try:
        logger.info(f"开始生成会话标题 - user_message: {user_message[:50]}..., assistant_message: {assistant_message[:50]}...")
        
        response = client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": """你是一个专业的会话标题生成助手。请根据用户的提问和AI的回答，生成一个简洁、准确、有概括性的会话标题。

标题生成要求：
1. 长度控制在8-20个字之间
2. 准确概括对话的核心主题和内容
3. 使用简洁、专业的语言
4. 突出问题的类型或领域（如：劳动纠纷、合同纠纷、交通事故等）
5. 不包含标点符号（除了必要的问号或感叹号）
6. 避免使用"关于"、"关于什么"等冗余词汇
7. 优先使用法律专业术语

示例：
- 用户问"劳动合同解除需要什么条件？"，回答涉及劳动合同法第39条 → 标题："劳动合同解除条件"
- 用户问"交通事故如何赔偿？"，回答涉及赔偿标准和计算方法 → 标题："交通事故赔偿标准"
- 用户问"租房合同违约怎么办？"，回答涉及违约责任和维权途径 → 标题："租房合同违约处理"
"""
                },
                {
                    "role": "user",
                    "content": f"""请为以下对话生成一个标题：

用户提问：{user_message}

AI回答：{assistant_message[:200]}

请直接输出标题，不要包含任何解释。"""
                }
            ],
            temperature=0.5,
            max_tokens=30
        )
        
        title = response.choices[0].message.content.strip()
        
        if len(title) > 20:
            title = title[:20]
        
        logger.info(f"会话标题生成成功 - title: {title}")
        return title
    except Exception as e:
        logger.error(f"会话标题生成失败 - error: {str(e)}")
        return user_message[:20]


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
                "rag_enabled": request.use_rag,
                "title": None
            }
            logger.info(f"创建新会话 - session_id: {session_id}")

        session = _sessions[session_id]

        config = {"configurable": {"thread_id": session_id}}

        new_message = HumanMessage(content=request.message)

        state_update = {
            "messages": [new_message],
            "use_rag": request.use_rag,
            "retrieval_strategy": request.retrieval_strategy or "vector",
            "enable_rerank": request.enable_rerank,
            "enable_tools": request.enable_tools,
            "tool_calls": [],
            "tool_results": {}
        }

        logger.info(f"请求参数 - use_rag: {request.use_rag}, retrieval_strategy: {request.retrieval_strategy}, enable_rerank: {request.enable_rerank}, enable_tools: {request.enable_tools}")
        if not request.use_rag and request.enable_rerank:
            logger.warning(f"enable_rerank=true 但 use_rag=false，重排序将被忽略")

        if request.stream:
            logger.info(f"开始流式响应 - session_id: {session_id}, use_rag: {request.use_rag}")
            
            message_id = str(uuid.uuid4())
            sources = []
            retrieval_metadata = None
            title = session.get("title") if session_id in _sessions else None
            
            async def title_generator_wrapper(user_msg: str, assistant_msg: str) -> str:
                generated_title = await generate_session_title(user_msg, assistant_msg)
                if session_id in _sessions:
                    _sessions[session_id]["title"] = generated_title
                    logger.info(f"更新会话标题 - session_id: {session_id}, title: {generated_title}")
                return generated_title
            
            title_generator = None
            if title is None:
                title_generator = title_generator_wrapper
            
            if request.use_rag:
                temp_result = await agent.ainvoke(state_update, config=config)
                if temp_result.get("context"):
                    for doc in temp_result["context"]:
                        source_info = {
                            "content": doc.page_content[:200],
                            "metadata": doc.metadata
                        }
                        sources.append(source_info)
                retrieval_metadata = temp_result.get("retrieval_metadata")
                logger.info(f"获取到 {len(sources)} 个引用来源")
            
            return await streaming_builder.build_conversation_stream(
                agent.get_compiled_graph(),
                state_update,
                config,
                message_id=message_id,
                session_id=session_id,
                role="assistant",
                sources=sources if sources else None,
                retrieval_metadata=retrieval_metadata,
                title=title,
                user_message=request.message,
                title_generator=title_generator
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

            tools_used = []
            tool_results = {}
            if result.get("tool_calls"):
                for tool_call in result["tool_calls"]:
                    tools_used.append(tool_call["name"])
            if result.get("tool_results"):
                tool_results = result["tool_results"]

            retrieval_metadata = result.get("retrieval_metadata")
            intent = None
            rewritten_query = None
            original_query = None
            entities = None
            pre_retrieval_used = False
            parallel_execution = False
            total_time = 0.0
            if retrieval_metadata:
                intent = retrieval_metadata.get("intent")
                rewritten_query = retrieval_metadata.get("rewritten_query")
                original_query = retrieval_metadata.get("original_query")
                entities = retrieval_metadata.get("entities")
                pre_retrieval_used = retrieval_metadata.get("pre_retrieval_used", False)
                parallel_execution = retrieval_metadata.get("parallel_execution", False)
                total_time = retrieval_metadata.get("total_time", 0.0)
                if retrieval_metadata.get("retrieval_skipped"):
                    logger.info(f"检索被跳过 - reason: {retrieval_metadata.get('skip_reason')}")

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

            if session.get("title") is None:
                session["title"] = await generate_session_title(request.message, content)
                logger.info(f"生成会话标题 - session_id: {session_id}, title: {session['title']}")

            response = ChatResponse(
                message_id=str(uuid.uuid4()),
                session_id=session_id,
                role="assistant",
                content=content,
                timestamp=datetime.now().isoformat(),
                sources=sources if sources else None,
                rag_used=request.use_rag,
                retrieval_strategy=request.retrieval_strategy if request.use_rag else None,
                tools_used=tools_used if tools_used else None,
                tool_results=tool_results if tool_results else None,
                intent=intent,
                rewritten_query=rewritten_query,
                original_query=original_query,
                entities=entities,
                pre_retrieval_used=pre_retrieval_used,
                parallel_execution=parallel_execution,
                total_time=total_time,
                title=session.get("title")
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
        rag_enabled=session.get("rag_enabled", False),
        title=session.get("title")
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
                rag_enabled=session_data.get("rag_enabled", False),
                title=session_data.get("title")
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


@router.get("/tools", response_model=dict)
async def list_tools():
    logger.info(f"查询工具列表")
    
    tools = get_available_tools()
    
    logger.info(f"查询工具列表成功 - total: {len(tools)}")
    return {
        "code": HttpStatus.OK,
        "status": "success",
        "message": "",
        "data": {
            "tools": tools,
            "total": len(tools)
        }
    }
