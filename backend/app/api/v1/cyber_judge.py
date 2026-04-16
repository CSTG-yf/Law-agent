import uuid
import os
import json
from datetime import datetime
from typing import Annotated, Any, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI

from app.schema.cyber_judge import (
    CyberJudgeRequest,
    CyberJudgeResponse,
    CyberJudgeSessionInfo,
    CyberJudgeSessionHistory,
    FileUploadResponse,
    IntentInfoResponse,
    CaseInfoResponse,
    LawInfoResponse,
    LawDetailResponse,
    ExtractedFactsResponse,
    AnalysisResultResponse,
    FileInfoResponse,
    build_cyber_judge_response
)
from app.service.cyber_judge.agent import CyberJudgeAgent, CyberJudgeStreamPayload
from app.service.cyber_judge.state import FileInfo
from app.service.cyber_judge.fact_extractor import FactExtractor
from app.service.session_service import get_session_service
from app.core.config import settings
from app.core.constants import HttpStatus
from app.core.logger import get_logger

router = APIRouter(prefix="/cyber-judge", tags=["CyberJudge"])
logger = get_logger("cyber_judge_api")

client = OpenAI(
    base_url=settings.OPENAI_BASE_URL,
    api_key=settings.DASHSCOPE_API_KEY or settings.OPENAI_API_KEY
)

session_service = get_session_service()

UPLOAD_DIR = Path("uploads/cyber_judge")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_cyber_judge_agents = {}
ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.txt', '.md', '.xls', '.xlsx']
CYBER_JUDGE_SESSION_PREFIX = "cyber-judge-"


def _is_cyber_judge_session(session_id: str) -> bool:
    return session_id.startswith(CYBER_JUDGE_SESSION_PREFIX)


def _ensure_cyber_judge_session(session_id: str) -> None:
    if not _is_cyber_judge_session(session_id):
        logger.warning(f"非法赛博判官会话访问 - session_id: {session_id}")
        raise HTTPException(
            status_code=HttpStatus.NOT_FOUND,
            detail="Session not found"
        )


def _build_uploaded_file_source(file_info: dict[str, Any]) -> dict[str, Any]:
    extracted_text = file_info.get("extracted_text") or ""
    return {
        "content": extracted_text[:300] if extracted_text else None,
        "metadata": {
            "source_type": "file",
            "filename": file_info.get("filename", "未知"),
            "file_type": file_info.get("file_type", "unknown"),
            "file_path": file_info.get("file_path"),
            "extracted_text_length": file_info.get("extracted_text_length", 0)
        }
    }


def _build_case_source(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": case.get("content", "")[:300] if case.get("content") else None,
        "metadata": {
            "source_type": "case",
            "title": case.get("title", "未知标题"),
            "case_number": case.get("case_number"),
            "court": case.get("court"),
            "judgement_date": case.get("judgement_date"),
            "cause": case.get("cause"),
            "relevance_score": case.get("relevance_score", 0.0)
        }
    }


def _build_law_source(law: dict[str, Any], law_detail_map: dict[str, str]) -> dict[str, Any]:
    detail_content = law_detail_map.get(law.get("title", ""))
    return {
        "content": detail_content[:500] if detail_content else None,
        "metadata": {
            "source_type": "law",
            "title": law.get("title", "未知标题"),
            "publisher": law.get("publisher"),
            "publish_date": law.get("publish_date"),
            "timeliness": law.get("timeliness"),
            "law_id": law.get("law_id"),
            "relevance_score": law.get("relevance_score", 0.0)
        }
    }


def _build_assistant_sources(
    uploaded_files: list[dict[str, Any]],
    related_cases: list[dict[str, Any]],
    related_laws: list[dict[str, Any]],
    law_details: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    law_detail_map = {
        detail.get("title", ""): detail.get("content", "")
        for detail in law_details
        if detail.get("title")
    }

    sources.extend(_build_uploaded_file_source(file_info) for file_info in uploaded_files)
    sources.extend(_build_case_source(case) for case in related_cases)
    sources.extend(_build_law_source(law, law_detail_map) for law in related_laws)
    return sources


async def _stream_cyber_judge_response(
    request: CyberJudgeRequest,
    session_id: str,
    session: dict[str, Any],
    uploaded_files: list[dict[str, Any]],
    state_update: dict[str, Any],
    config: dict[str, Any],
    agent: CyberJudgeAgent
) -> StreamingResponse:
    logger.info(f"开始赛博判官流式响应 - session_id: {session_id}")
    message_id = str(uuid.uuid4())
    existing_title = session.get("title")

    async def event_generator():
        payload: Optional[CyberJudgeStreamPayload] = None
        final_content = ""
        stream_uploaded_files = list(uploaded_files)
        stream_state_update = dict(state_update)

        try:
            yield f"event: metadata\ndata: {json.dumps({'message_id': message_id, 'session_id': session_id, 'role': 'assistant', 'title': existing_title}, ensure_ascii=False)}\n\n"

            if request.file_paths:
                yield f"event: progress\ndata: {json.dumps({'stage': 'extract_facts', 'message': '正在提取文档事实，请稍候...'}, ensure_ascii=False)}\n\n"

            if request.file_paths and not stream_uploaded_files:
                llm = ChatOpenAI(
                    model=settings.MODEL_NAME,
                    temperature=0.7,
                    base_url=settings.OPENAI_BASE_URL,
                    api_key=settings.DASHSCOPE_API_KEY or settings.OPENAI_API_KEY
                )
                fact_extractor = FactExtractor(llm)
                extracted_facts = None

                total_files = len(request.file_paths)
                for index, file_path in enumerate(request.file_paths, 1):
                    if os.path.exists(file_path):
                        filename = Path(file_path).name
                        yield f"event: progress\ndata: {json.dumps({'stage': 'extract_facts', 'message': f'正在提取第{index}/{total_files}个文件的事实信息：{filename}'}, ensure_ascii=False)}\n\n"
                        file_info, facts = await fact_extractor.extract_from_file(file_path, filename)
                        stream_uploaded_files.append(file_info)

                        if facts:
                            if extracted_facts is None:
                                extracted_facts = facts
                            else:
                                for field in ["parties", "events", "disputes", "claims", "key_dates", "amounts", "locations"]:
                                    normalized_values = [str(item).strip() for item in facts.get(field, []) if str(item).strip()]
                                    extracted_facts[field].extend(normalized_values)
                                    extracted_facts[field] = list(dict.fromkeys(extracted_facts[field]))

                                summaries = [item for item in [extracted_facts.get("summary", ""), facts.get("summary", "")] if item]
                                extracted_facts["summary"] = "；".join(dict.fromkeys(summaries))

                            logger.info(
                                f"流式文件事实已载入 - filename: {filename}, summary_length: {len(facts.get('summary', ''))}, text_length: {file_info.get('extracted_text_length', 0)}"
                            )

                stream_state_update["uploaded_files"] = stream_uploaded_files
                stream_state_update["extracted_facts"] = extracted_facts

            extracted_facts = stream_state_update.get("extracted_facts")
            facts_summary = extracted_facts.get("summary", "").strip() if extracted_facts else ""
            if facts_summary:
                yield f"event: facts_summary\ndata: {json.dumps({'title': '已识别文件事实', 'summary': facts_summary}, ensure_ascii=False)}\n\n"

            yield f"event: progress\ndata: {json.dumps({'stage': 'analyze', 'message': '正在检索相关案例与法规并生成分析结论...'}, ensure_ascii=False)}\n\n"

            user_sources = [_build_uploaded_file_source(file_info) for file_info in stream_uploaded_files]

            async for chunk in agent.astream_final_response(stream_state_update, config=config):
                if isinstance(chunk, str):
                    final_content += chunk
                    yield f"event: token\ndata: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
                else:
                    payload = chunk

            if payload is None:
                raise RuntimeError("流式响应未生成最终结果")

            assistant_sources = _build_assistant_sources(
                uploaded_files=stream_uploaded_files,
                related_cases=payload["related_cases"],
                related_laws=payload["related_laws"],
                law_details=payload["law_details"]
            )

            await session_service.add_message(
                session_id=session_id,
                role="user",
                content=request.message,
                sources=user_sources
            )
            await session_service.add_message(
                session_id=session_id,
                role="assistant",
                content=final_content,
                sources=assistant_sources,
                related_laws=payload["related_laws"],
                related_cases=payload["related_cases"]
            )

            title = existing_title
            if not title:
                title = await generate_session_title(request.message, final_content)
                await session_service.update_session(session_id, title=title)
                logger.info(f"赛博判官流式标题生成成功 - session_id: {session_id}, title: {title}")
                yield f"event: title\ndata: {json.dumps({'title': title}, ensure_ascii=False)}\n\n"

            response = build_cyber_judge_response(
                message_id=message_id,
                session_id=session_id,
                content=final_content,
                timestamp=datetime.now().isoformat(),
                title=title,
                intent_info=payload["intent_info"],
                related_cases=payload["related_cases"],
                related_laws=payload["related_laws"],
                law_details=payload["law_details"],
                extracted_facts=payload["extracted_facts"],
                analysis_result=payload["analysis_result"],
                uploaded_files=payload["files_processed"]
            )

            yield f"event: complete\ndata: {json.dumps(response.model_dump(), ensure_ascii=False)}\n\n"
            yield "event: done\ndata: {}\n\n"
            logger.info(
                f"赛博判官流式响应完成 - session_id: {session_id}, response_length: {len(final_content)}, cases: {len(payload['related_cases'])}, laws: {len(payload['related_laws'])}"
            )
        except Exception as e:
            logger.error(f"赛博判官流式响应失败 - session_id: {session_id}, error: {str(e)}")
            error_payload = {
                'code': HttpStatus.INTERNAL_SERVER_ERROR,
                'status': 'error',
                'message': str(e),
                'data': None
            }
            yield f"event: error\ndata: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
            yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


async def _save_uploaded_file(upload: UploadFile) -> FileUploadResponse:
    file_id = str(uuid.uuid4())
    file_ext = Path(upload.filename).suffix.lower() if upload.filename else ""

    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=HttpStatus.BAD_REQUEST,
            detail=f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    safe_filename = f"{file_id}{file_ext}"
    file_path = UPLOAD_DIR / safe_filename

    content = await upload.read()
    with open(file_path, "wb") as f:
        f.write(content)

    file_size = len(content)

    logger.info(f"文件上传成功 - file_id: {file_id}, filename: {upload.filename}, size: {file_size}")
    return FileUploadResponse(
        file_id=file_id,
        filename=upload.filename,
        file_type=file_ext[1:] if file_ext else "unknown",
        file_path=str(file_path),
        file_size=file_size,
        upload_time=datetime.now().isoformat()
    )


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


def get_cyber_judge_agent(max_history: int = None) -> CyberJudgeAgent:
    key = f"agent_{max_history or settings.MAX_HISTORY_LENGTH}"
    if key not in _cyber_judge_agents:
        llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            temperature=0.7,
            base_url=settings.OPENAI_BASE_URL,
            api_key=settings.DASHSCOPE_API_KEY or settings.OPENAI_API_KEY
        )
        _cyber_judge_agents[key] = CyberJudgeAgent(llm=llm, max_history=max_history)
    return _cyber_judge_agents[key]


@router.post("/upload", response_model=dict)
async def upload_file(
    files: Annotated[list[UploadFile] | None, File(description="上传文件列表")] = None,
    file: Annotated[UploadFile | None, File(description="上传单个文件")] = None
):
    try:
        upload_files = files or ([file] if file else [])
        if not upload_files:
            raise HTTPException(
                status_code=HttpStatus.BAD_REQUEST,
                detail="请至少上传一个文件"
            )

        logger.info(f"收到文件上传请求 - total_files: {len(upload_files)}")
        responses = [await _save_uploaded_file(upload) for upload in upload_files]

        if len(responses) == 1:
            response = responses[0].model_dump()
            response["files"] = [response.copy()]
            response["total"] = 1
            return {
                "code": HttpStatus.OK,
                "status": "success",
                "message": "文件上传成功",
                "data": response
            }

        return {
            "code": HttpStatus.OK,
            "status": "success",
            "message": f"成功上传{len(responses)}个文件",
            "data": {
                "files": [item.model_dump() for item in responses],
                "total": len(responses)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败 - error: {str(e)}")
        raise HTTPException(
            status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            detail=f"文件上传失败: {str(e)}"
        )


@router.post("/analyze", response_model=dict)
async def analyze_case(request: CyberJudgeRequest):
    try:
        logger.info(f"收到赛博判官请求 - session_id: {request.session_id}, user_id: {request.user_id}, message: {request.message[:100]}")
        
        agent = get_cyber_judge_agent(max_history=request.max_history)
        
        session_id = request.session_id.strip() if request.session_id else None
        if not session_id:
            session_id = f"{CYBER_JUDGE_SESSION_PREFIX}{uuid.uuid4().hex[:12]}"
            logger.info(f"自动生成session_id - session_id: {session_id}")
        else:
            _ensure_cyber_judge_session(session_id)

        session_exists = await session_service.session_exists(session_id)
        if not session_exists:
            await session_service.create_session(
                session_id=session_id,
                user_id=request.user_id,
                rag_enabled=False
            )
            logger.info(f"创建新会话 - session_id: {session_id}")
        
        session = await session_service.get_session(session_id)
        
        uploaded_files = []
        extracted_facts = None

        if request.file_paths and not request.stream:
            llm = ChatOpenAI(
                model=settings.MODEL_NAME,
                temperature=0.7,
                base_url=settings.OPENAI_BASE_URL,
                api_key=settings.DASHSCOPE_API_KEY or settings.OPENAI_API_KEY
            )
            fact_extractor = FactExtractor(llm)

            for file_path in request.file_paths:
                if os.path.exists(file_path):
                    filename = Path(file_path).name
                    file_info, facts = await fact_extractor.extract_from_file(file_path, filename)
                    uploaded_files.append(file_info)

                    if facts:
                        if extracted_facts is None:
                            extracted_facts = facts
                        else:
                            for field in ["parties", "events", "disputes", "claims", "key_dates", "amounts", "locations"]:
                                normalized_values = [str(item).strip() for item in facts.get(field, []) if str(item).strip()]
                                extracted_facts[field].extend(normalized_values)
                                extracted_facts[field] = list(dict.fromkeys(extracted_facts[field]))

                            summaries = [item for item in [extracted_facts.get("summary", ""), facts.get("summary", "")] if item]
                            extracted_facts["summary"] = "；".join(dict.fromkeys(summaries))

                        logger.info(
                            f"文件事实已载入 - filename: {filename}, summary_length: {len(facts.get('summary', ''))}, text_length: {file_info.get('extracted_text_length', 0)}"
                        )
        
        config = {"configurable": {"thread_id": session_id}}
        
        new_message = HumanMessage(content=request.message)
        
        state_update = {
            "messages": [new_message],
            "session_id": session_id,
            "user_id": request.user_id,
            "intent_info": None,
            "uploaded_files": uploaded_files,
            "extracted_facts": extracted_facts,
            "related_cases": [],
            "related_laws": [],
            "law_details": [],
            "analysis_result": None,
            "tool_calls": [],
            "tool_results": {},
            "enable_tools": True,
            "max_history": request.max_history or settings.MAX_HISTORY_LENGTH
        }
        
        logger.info(f"开始处理请求 - session_id: {session_id}, has_files: {bool(uploaded_files)}, stream: {request.stream}")

        if request.stream:
            return await _stream_cyber_judge_response(
                request=request,
                session_id=session_id,
                session=session,
                uploaded_files=uploaded_files,
                state_update=state_update,
                config=config,
                agent=agent
            )

        result = await agent.ainvoke(state_update, config=config)

        assistant_message = result["messages"][-1]
        if isinstance(assistant_message, AIMessage):
            content = assistant_message.content
        else:
            content = str(assistant_message)
        
        related_cases = result.get("related_cases", [])
        related_laws = result.get("related_laws", [])
        law_details = result.get("law_details", [])

        user_sources = [_build_uploaded_file_source(file_info) for file_info in uploaded_files]
        assistant_sources = _build_assistant_sources(
            uploaded_files=uploaded_files,
            related_cases=related_cases,
            related_laws=related_laws,
            law_details=law_details
        )

        await session_service.add_message(
            session_id=session_id,
            role="user",
            content=request.message,
            sources=user_sources
        )
        await session_service.add_message(
            session_id=session_id,
            role="assistant",
            content=content,
            sources=assistant_sources,
            related_laws=related_laws,
            related_cases=related_cases
        )

        title = session.get("title")
        if not title:
            title = await generate_session_title(request.message, content)
            await session_service.update_session(session_id, title=title)

        response = build_cyber_judge_response(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            content=content,
            timestamp=datetime.now().isoformat(),
            title=title,
            intent_info=result.get("intent_info"),
            related_cases=related_cases,
            related_laws=related_laws,
            law_details=law_details,
            extracted_facts=result.get("extracted_facts"),
            analysis_result=result.get("analysis_result"),
            uploaded_files=uploaded_files
        )
        
        logger.info(f"请求处理完成 - session_id: {session_id}, response_length: {len(content)}, cases: {len(related_cases)}, laws: {len(related_laws)}")
        
        return {
            "code": HttpStatus.OK,
            "status": "success",
            "message": "",
            "data": response.model_dump()
        }
        
    except Exception as e:
        logger.error(f"赛博判官请求处理失败 - session_id: {request.session_id}, error: {str(e)}")
        raise HTTPException(
            status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/sessions/{session_id}", response_model=dict)
async def get_session(session_id: str):
    logger.info(f"查询会话信息 - session_id: {session_id}")
    _ensure_cyber_judge_session(session_id)

    session = await session_service.get_session(session_id)
    
    if not session:
        logger.warning(f"会话不存在 - session_id: {session_id}")
        raise HTTPException(
            status_code=HttpStatus.NOT_FOUND,
            detail="Session not found"
        )
    
    session_info = CyberJudgeSessionInfo(
        session_id=session_id,
        user_id=session["user_id"],
        created_at=session["created_at"],
        message_count=session.get("message_count", 0),
        title=session.get("title")
    )
    
    logger.info(f"查询会话信息成功 - session_id: {session_id}")
    return {
        "code": HttpStatus.OK,
        "status": "success",
        "message": "",
        "data": session_info.model_dump()
    }


@router.get("/sessions/{session_id}/history", response_model=dict)
async def get_session_history(session_id: str, limit: Optional[int] = None):
    logger.info(f"查询会话历史 - session_id: {session_id}, limit: {limit}")
    _ensure_cyber_judge_session(session_id)

    session = await session_service.get_session(session_id)
    
    if not session:
        logger.warning(f"会话不存在 - session_id: {session_id}")
        raise HTTPException(
            status_code=HttpStatus.NOT_FOUND,
            detail="Session not found"
        )
    
    messages = await session_service.get_messages(session_id, limit)
    
    history = CyberJudgeSessionHistory(
        session_id=session_id,
        messages=messages,
        total_messages=session.get("message_count", 0),
        created_at=session["created_at"],
        updated_at=session.get("updated_at", datetime.now().isoformat())
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
    _ensure_cyber_judge_session(session_id)

    success = await session_service.delete_session(session_id)
    
    if not success:
        logger.warning(f"会话不存在 - session_id: {session_id}")
        raise HTTPException(
            status_code=HttpStatus.NOT_FOUND,
            detail="Session not found"
        )
    
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

    sessions_data = await session_service.list_sessions(user_id=user_id)
    sessions_data = [s for s in sessions_data if _is_cyber_judge_session(s["session_id"])]

    sessions = [
        CyberJudgeSessionInfo(
            session_id=s["session_id"],
            user_id=s["user_id"],
            created_at=s["created_at"],
            message_count=s.get("message_count", 0),
            title=s.get("title")
        )
        for s in sessions_data
    ]
    
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
    _ensure_cyber_judge_session(session_id)

    success = await session_service.clear_messages(session_id)
    
    if not success:
        logger.warning(f"会话不存在 - session_id: {session_id}")
        raise HTTPException(
            status_code=HttpStatus.NOT_FOUND,
            detail="Session not found"
        )
    
    logger.info(f"清空会话历史成功 - session_id: {session_id}")
    return {
        "code": HttpStatus.OK,
        "status": "success",
        "message": "Session history cleared",
        "data": None
    }
