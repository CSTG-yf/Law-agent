import uuid
import os
from datetime import datetime
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

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
    FileInfoResponse
)
from app.service.cyber_judge.agent import CyberJudgeAgent
from app.service.cyber_judge.state import FileInfo
from app.service.cyber_judge.fact_extractor import FactExtractor
from app.service.session_service import get_session_service
from app.core.config import settings
from app.core.constants import HttpStatus
from app.core.logger import get_logger

router = APIRouter(prefix="/cyber-judge", tags=["CyberJudge"])
logger = get_logger("cyber_judge_api")

session_service = get_session_service()

UPLOAD_DIR = Path("uploads/cyber_judge")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_cyber_judge_agents = {}


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
async def upload_file(file: UploadFile = File(...)):
    try:
        logger.info(f"收到文件上传请求 - filename: {file.filename}")
        
        file_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix.lower() if file.filename else ""
        
        allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.md', '.xls', '.xlsx']
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=HttpStatus.BAD_REQUEST,
                detail=f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(allowed_extensions)}"
            )
        
        safe_filename = f"{file_id}{file_ext}"
        file_path = UPLOAD_DIR / safe_filename
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        file_size = len(content)
        
        response = FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            file_type=file_ext[1:] if file_ext else "unknown",
            file_path=str(file_path),
            file_size=file_size,
            upload_time=datetime.now().isoformat()
        )
        
        logger.info(f"文件上传成功 - file_id: {file_id}, filename: {file.filename}, size: {file_size}")
        
        return {
            "code": HttpStatus.OK,
            "status": "success",
            "message": "文件上传成功",
            "data": response.model_dump()
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
        
        session_id = request.session_id
        if session_id is None:
            session_id = f"cyber-judge-{uuid.uuid4().hex[:12]}"
            logger.info(f"自动生成session_id - session_id: {session_id}")
        
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
        
        if request.file_paths:
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
                    
                    if facts and facts.get("summary"):
                        if extracted_facts is None:
                            extracted_facts = facts
                        else:
                            extracted_facts["parties"].extend(facts.get("parties", []))
                            extracted_facts["events"].extend(facts.get("events", []))
                            extracted_facts["disputes"].extend(facts.get("disputes", []))
                            extracted_facts["claims"].extend(facts.get("claims", []))
                            extracted_facts["summary"] += "；" + facts.get("summary", "")
        
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
        
        logger.info(f"开始处理请求 - session_id: {session_id}, has_files: {bool(uploaded_files)}")
        
        result = await agent.ainvoke(state_update, config=config)
        
        assistant_message = result["messages"][-1]
        if isinstance(assistant_message, AIMessage):
            content = assistant_message.content
        else:
            content = str(assistant_message)
        
        intent_info = result.get("intent_info")
        intent_response = None
        if intent_info:
            intent_response = IntentInfoResponse(
                intent_type=intent_info.get("intent_type", "legal_consultation"),
                confidence=intent_info.get("confidence", 0.0),
                sub_intents=intent_info.get("sub_intents", [])
            )
        
        related_cases = result.get("related_cases", [])
        cases_response = [
            CaseInfoResponse(
                title=case.get("title", "未知标题"),
                case_number=case.get("case_number"),
                court=case.get("court"),
                judgement_date=case.get("judgement_date"),
                cause=case.get("cause"),
                content_preview=case.get("content", "")[:200] if case.get("content") else None,
                relevance_score=case.get("relevance_score", 0.0)
            )
            for case in related_cases
        ]
        
        related_laws = result.get("related_laws", [])
        laws_response = [
            LawInfoResponse(
                title=law.get("title", "未知标题"),
                publisher=law.get("publisher"),
                publish_date=law.get("publish_date"),
                timeliness=law.get("timeliness"),
                law_id=law.get("law_id"),
                content_preview=None,
                relevance_score=law.get("relevance_score", 0.0)
            )
            for law in related_laws
        ]
        
        law_details = result.get("law_details", [])
        details_response = [
            LawDetailResponse(
                title=detail.get("title", "未知标题"),
                content=detail.get("content")
            )
            for detail in law_details
        ]
        
        extracted_facts_result = result.get("extracted_facts")
        facts_response = None
        if extracted_facts_result:
            facts_response = ExtractedFactsResponse(
                parties=extracted_facts_result.get("parties", []),
                events=extracted_facts_result.get("events", []),
                disputes=extracted_facts_result.get("disputes", []),
                claims=extracted_facts_result.get("claims", []),
                key_dates=extracted_facts_result.get("key_dates", []),
                summary=extracted_facts_result.get("summary")
            )
        
        analysis_result = result.get("analysis_result")
        analysis_response = None
        if analysis_result:
            analysis_response = AnalysisResultResponse(
                legal_basis=analysis_result.get("legal_basis", []),
                risk_assessment=analysis_result.get("risk_assessment"),
                suggestions=analysis_result.get("suggestions", [])
            )
        
        files_response = [
            FileInfoResponse(
                filename=f.get("filename", "未知"),
                file_type=f.get("file_type", "unknown"),
                extracted_text_length=f.get("extracted_text_length", 0)
            )
            for f in uploaded_files
        ]
        
        await session_service.add_message(
            session_id=session_id,
            role="user",
            content=request.message,
            sources=[]
        )
        await session_service.add_message(
            session_id=session_id,
            role="assistant",
            content=content,
            sources=[]
        )
        
        title = session.get("title")
        if not title:
            title = request.message[:20]
            await session_service.update_session(session_id, title=title)
        
        response = CyberJudgeResponse(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            role="assistant",
            content=content,
            timestamp=datetime.now().isoformat(),
            intent=intent_response,
            related_cases=cases_response,
            related_laws=laws_response,
            law_details=details_response,
            extracted_facts=facts_response,
            analysis_result=analysis_response,
            files_processed=files_response,
            title=title
        )
        
        logger.info(f"请求处理完成 - session_id: {session_id}, response_length: {len(content)}, cases: {len(cases_response)}, laws: {len(laws_response)}")
        
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
