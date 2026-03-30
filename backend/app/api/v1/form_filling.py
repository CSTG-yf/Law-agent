from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from app.schema.form_filling import (
    StartFillingRequest,
    StartFillingResponse,
    SendMessageRequest,
    SendMessageResponse,
    GetStateRequest,
    GetStateResponse,
    UpdateSlotRequest,
    UpdateSlotResponse,
    GenerateDocumentRequest,
    GenerateDocumentResponse,
    ErrorResponse
)
from app.service.form_filling.slot_manager import get_slot_manager
from app.service.form_filling.slot_extractor import get_slot_extractor
from app.service.form_filling.doc_renderer import get_doc_renderer
from app.service.form_filling.conversation_strategy import get_conversation_strategy
from app.core.constants import HttpStatus
from app.core.logger import get_logger
from pathlib import Path

router = APIRouter(prefix="/form-filling", tags=["Form Filling"])
logger = get_logger("form_filling_api")


@router.post("/start", response_model=dict)
async def start_filling(request: StartFillingRequest):
    """
    开始新的文书填写会话
    """
    try:
        logger.info(f"开始文书填写 - template_type: {request.template_type}, user_id: {request.user_id}")

        slot_manager = get_slot_manager()
        state = slot_manager.create_session(request.template_type)

        template_def = slot_manager.get_template_definition(request.template_type)
        if not template_def:
            raise HTTPException(
                status_code=HttpStatus.BAD_REQUEST,
                detail=f"模板类型不存在: {request.template_type}"
            )

        conversation_strategy = get_conversation_strategy()
        greeting_message = conversation_strategy.get_greeting_message(state.current_block)

        response = StartFillingResponse(
            session_id=state.session_id,
            template_type=request.template_type,
            current_block=state.current_block,
            blocks=template_def.blocks,
            message=f"欢迎使用正确车队法律文书智能填写系统！{greeting_message}"
        )

        logger.info(f"文书填写会话创建成功 - session_id: {state.session_id}")
        return {
            "code": HttpStatus.OK,
            "status": "success",
            "message": "",
            "data": response.model_dump()
        }

    except Exception as e:
        logger.error(f"开始文书填写失败 - error: {str(e)}")
        raise HTTPException(
            status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/message", response_model=dict)
async def send_message(request: SendMessageRequest):
    """
    发送消息，进行对话式填写
    """
    try:
        logger.info(f"收到填写消息 - session_id: {request.session_id}, message: {request.message[:100]}")

        slot_manager = get_slot_manager()
        state = slot_manager.get_session(request.session_id)

        if not state:
            raise HTTPException(
                status_code=HttpStatus.NOT_FOUND,
                detail="会话不存在，请先开始新的填写会话"
            )

        conversation_strategy = get_conversation_strategy()
        user_intent = conversation_strategy.handle_user_intent(request.message, state)

        manually_set_slots = {}
        if user_intent:
            if user_intent == "skip_agent":
                slot_manager.update_slot(
                    session_id=request.session_id,
                    block_id="agent",
                    slot_name="has_agent",
                    value=False,
                    confirmed=True,
                    source="user_input",
                    confidence=1.0
                )
                manually_set_slots["agent.has_agent"] = False
                
                next_block = conversation_strategy._get_next_block(state)
                if next_block:
                    success = slot_manager.switch_block(request.session_id, next_block)
                    if success:
                        greeting = conversation_strategy.get_greeting_message(next_block)
                        state = slot_manager.get_session(request.session_id)
                        all_extracted_slots = {}
                        for block_id, block_data in state.blocks.items():
                            for slot_name, slot_status in block_data.slots.items():
                                if slot_status.value is not None:
                                    full_slot_name = f"{block_id}.{slot_name}"
                                    all_extracted_slots[full_slot_name] = slot_status.value
                        
                        current_block_data = state.blocks.get(next_block)
                        current_block_completion_rate = current_block_data.completion_rate if current_block_data else 0.0
                        
                        return {
                            "code": HttpStatus.OK,
                            "status": "success",
                            "message": "",
                            "data": SendMessageResponse(
                                session_id=request.session_id,
                                message=greeting,
                                current_block=next_block,
                                completion_rate=current_block_completion_rate,
                                extracted_slots=all_extracted_slots,
                                needs_clarification=False,
                                suggested_next_action=None
                            ).model_dump()
                        }
            
            if user_intent == "skip_preservation":
                slot_manager.update_slot(
                    session_id=request.session_id,
                    block_id="preservation",
                    slot_name="active",
                    value=False,
                    confirmed=True,
                    source="user_input",
                    confidence=1.0
                )
                manually_set_slots["preservation.active"] = False
                
                next_block = conversation_strategy._get_next_block(state)
                if next_block:
                    success = slot_manager.switch_block(request.session_id, next_block)
                    if success:
                        greeting = conversation_strategy.get_greeting_message(next_block)
                        state = slot_manager.get_session(request.session_id)
                        all_extracted_slots = {}
                        for block_id, block_data in state.blocks.items():
                            for slot_name, slot_status in block_data.slots.items():
                                if slot_status.value is not None:
                                    full_slot_name = f"{block_id}.{slot_name}"
                                    all_extracted_slots[full_slot_name] = slot_status.value
                        
                        current_block_data = state.blocks.get(next_block)
                        current_block_completion_rate = current_block_data.completion_rate if current_block_data else 0.0
                        
                        return {
                            "code": HttpStatus.OK,
                            "status": "success",
                            "message": "",
                            "data": SendMessageResponse(
                                session_id=request.session_id,
                                message=greeting,
                                current_block=next_block,
                                completion_rate=current_block_completion_rate,
                                extracted_slots=all_extracted_slots,
                                needs_clarification=False,
                                suggested_next_action=None
                            ).model_dump()
                        }
            
            if user_intent.startswith("switch_to_"):
                target_block = user_intent.replace("switch_to_", "")
                
                if "没有" in request.message or "不" in request.message or "无" in request.message or "不需要" in request.message:
                    if target_block == "agent":
                        slot_manager.update_slot(
                            session_id=request.session_id,
                            block_id="agent",
                            slot_name="has_agent",
                            value=False,
                            confirmed=True,
                            source="user_input",
                            confidence=1.0
                        )
                        manually_set_slots["agent.has_agent"] = False
                    elif target_block == "preservation":
                        slot_manager.update_slot(
                            session_id=request.session_id,
                            block_id="preservation",
                            slot_name="active",
                            value=False,
                            confirmed=True,
                            source="user_input",
                            confidence=1.0
                        )
                        manually_set_slots["preservation.active"] = False
                
                success = slot_manager.switch_block(request.session_id, target_block)
                if success:
                    greeting = conversation_strategy.get_greeting_message(target_block)
                    
                    state = slot_manager.get_session(request.session_id)
                    all_extracted_slots = {}
                    for block_id, block_data in state.blocks.items():
                        for slot_name, slot_status in block_data.slots.items():
                            if slot_status.value is not None:
                                full_slot_name = f"{block_id}.{slot_name}"
                                all_extracted_slots[full_slot_name] = slot_status.value
                    
                    current_block_data = state.blocks.get(target_block)
                    current_block_completion_rate = current_block_data.completion_rate if current_block_data else 0.0
                    
                    return {
                        "code": HttpStatus.OK,
                        "status": "success",
                        "message": "",
                        "data": SendMessageResponse(
                            session_id=request.session_id,
                            message=greeting,
                            current_block=target_block,
                            completion_rate=current_block_completion_rate,
                            extracted_slots=all_extracted_slots,
                            needs_clarification=False,
                            suggested_next_action=None
                        ).model_dump()
                    }
            elif user_intent == "generate_document":
                return await generate_document_impl(request.session_id)

        state.conversation_turn += 1

        known_slots = {}
        for block_id, block_data in state.blocks.items():
            for slot_name, slot_status in block_data.slots.items():
                if slot_status.value is not None:
                    full_slot_name = f"{block_id}.{slot_name}"
                    known_slots[full_slot_name] = slot_status.value

        slot_extractor = get_slot_extractor()
        extraction_result = await slot_extractor.extract_slots(
            user_input=request.message,
            current_block=state.current_block,
            known_slots=known_slots
        )

        for slot_name, value in extraction_result.extracted_slots.items():
            if slot_name in manually_set_slots:
                logger.info(f"跳过手动设置的槽位 - slot_name: {slot_name}, value: {manually_set_slots[slot_name]}")
                continue
            parts = slot_name.split(".")
            if len(parts) >= 2:
                block_id = parts[0]
                slot_name_full = ".".join(parts[1:]) if len(parts) > 2 else parts[1]
                
                slot_confidence = extraction_result.confidence
                slot_confirmed = True
                
                if slot_name_full == "has_agent" and isinstance(value, bool):
                    slot_confidence = 1.0
                    slot_confirmed = True
                    logger.info(f"has_agent 槽位强制设置为高置信度 - value: {value}")
                
                slot_manager.update_slot(
                    session_id=request.session_id,
                    block_id=block_id,
                    slot_name=slot_name_full,
                    value=value,
                    confirmed=slot_confirmed,
                    source="user_input",
                    confidence=slot_confidence
                )

        next_action = conversation_strategy.generate_next_action(
            state,
            extraction_result.model_dump()
        )

        state = slot_manager.get_session(request.session_id)

        all_extracted_slots = {}
        for block_id, block_data in state.blocks.items():
            for slot_name, slot_status in block_data.slots.items():
                if slot_status.value is not None:
                    full_slot_name = f"{block_id}.{slot_name}"
                    all_extracted_slots[full_slot_name] = slot_status.value

        current_block_data = state.blocks.get(state.current_block)
        current_block_completion_rate = current_block_data.completion_rate if current_block_data else 0.0

        suggested_next_action = next_action.get("suggested_next_action")
        
        if suggested_next_action and suggested_next_action.startswith("switch_to_"):
            target_block = suggested_next_action.replace("switch_to_", "")
            success = slot_manager.switch_block(request.session_id, target_block)
            if success:
                state = slot_manager.get_session(request.session_id)
                current_block_data = state.blocks.get(state.current_block)
                current_block_completion_rate = current_block_data.completion_rate if current_block_data else 0.0

        response = SendMessageResponse(
            session_id=request.session_id,
            message=next_action["message"],
            current_block=state.current_block,
            completion_rate=current_block_completion_rate,
            extracted_slots=all_extracted_slots,
            needs_clarification=next_action["needs_clarification"],
            clarification_questions=extraction_result.clarification_questions,
            suggested_next_action=suggested_next_action
        )

        logger.info(f"填写消息处理完成 - session_id: {request.session_id}, completion_rate: {response.completion_rate:.2f}")
        return {
            "code": HttpStatus.OK,
            "status": "success",
            "message": "",
            "data": response.model_dump()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"填写消息处理失败 - session_id: {request.session_id}, error: {str(e)}")
        raise HTTPException(
            status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/state", response_model=dict)
async def get_state(request: GetStateRequest):
    """
    获取当前填写状态
    """
    try:
        logger.info(f"查询填写状态 - session_id: {request.session_id}")

        slot_manager = get_slot_manager()
        state = slot_manager.get_session(request.session_id)

        if not state:
            raise HTTPException(
                status_code=HttpStatus.NOT_FOUND,
                detail="会话不存在"
            )

        response = GetStateResponse(
            session_id=state.session_id,
            template_type=state.template_type,
            current_block=state.current_block,
            blocks={bid: bdata.model_dump() for bid, bdata in state.blocks.items()},
            overall_completion_rate=slot_manager.get_overall_completion_rate(request.session_id),
            conversation_turn=state.conversation_turn,
            is_complete=slot_manager.is_complete(request.session_id)
        )

        logger.info(f"查询填写状态成功 - session_id: {request.session_id}, completion_rate: {response.overall_completion_rate:.2f}")
        return {
            "code": HttpStatus.OK,
            "status": "success",
            "message": "",
            "data": response.model_dump()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询填写状态失败 - session_id: {request.session_id}, error: {str(e)}")
        raise HTTPException(
            status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/update-slot", response_model=dict)
async def update_slot(request: UpdateSlotRequest):
    """
    手动更新槽位值
    """
    try:
        logger.info(f"更新槽位 - session_id: {request.session_id}, block_id: {request.block_id}, slot_name: {request.slot_name}, value: {request.value}")

        slot_manager = get_slot_manager()
        success = slot_manager.update_slot(
            session_id=request.session_id,
            block_id=request.block_id,
            slot_name=request.slot_name,
            value=request.value,
            confirmed=request.confirmed,
            source="user_input",
            confidence=1.0
        )

        if not success:
            raise HTTPException(
                status_code=HttpStatus.BAD_REQUEST,
                detail="更新槽位失败"
            )

        response = UpdateSlotResponse(
            session_id=request.session_id,
            block_id=request.block_id,
            slot_name=request.slot_name,
            success=True,
            message="槽位更新成功"
        )

        logger.info(f"槽位更新成功 - session_id: {request.session_id}")
        return {
            "code": HttpStatus.OK,
            "status": "success",
            "message": "",
            "data": response.model_dump()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新槽位失败 - session_id: {request.session_id}, error: {str(e)}")
        raise HTTPException(
            status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/generate", response_model=dict)
async def generate_document(request: GenerateDocumentRequest):
    """
    生成最终文档
    """
    try:
        return await generate_document_impl(request.session_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成文档失败 - session_id: {request.session_id}, error: {str(e)}")
        raise HTTPException(
            status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


async def generate_document_impl(session_id: str) -> dict:
    """
    生成文档的实现
    """
    logger.info(f"开始生成文档 - session_id: {session_id}")

    slot_manager = get_slot_manager()
    state = slot_manager.get_session(session_id)

    if not state:
        raise HTTPException(
            status_code=HttpStatus.NOT_FOUND,
            detail="会话不存在"
        )

    if not slot_manager.is_complete(session_id):
        missing_fields = []
        template_def = slot_manager.get_template_definition(state.template_type)
        if template_def:
            for block_def in template_def.blocks:
                block = state.blocks.get(block_def.block_id)
                if block:
                    for slot_name in block_def.required_slots:
                        slot = block.slots.get(slot_name)
                        if not slot or not slot.value:
                            missing_fields.append(f"{block_def.display_name}.{slot_name}")

        logger.warning(f"文档不完整 - session_id: {session_id}, missing: {missing_fields}")
        return {
            "code": HttpStatus.BAD_REQUEST,
            "status": "error",
            "message": "文档信息不完整，无法生成",
            "data": GenerateDocumentResponse(
                success=False,
                document_url=None,
                message="请先填写所有必填信息",
                missing_fields=missing_fields
            ).model_dump()
        }

    doc_renderer = get_doc_renderer()
    template_file = doc_renderer.get_template_file(state.template_type)

    if not template_file:
        raise HTTPException(
            status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            detail=f"找不到模板文件: {state.template_type}"
        )

    slot_data = doc_renderer.extract_slots_from_session(state.model_dump())

    try:
        output_path = doc_renderer.render_document(
            template_file=template_file,
            slot_data=slot_data
        )

        document_url = f"/api/v1/form-filling/download/{Path(output_path).name}"

        response = GenerateDocumentResponse(
            success=True,
            document_url=document_url,
            message="文档生成成功",
            missing_fields=[]
        )

        logger.info(f"文档生成成功 - session_id: {session_id}, output: {output_path}")
        return {
            "code": HttpStatus.OK,
            "status": "success",
            "message": "",
            "data": response.model_dump()
        }

    except Exception as e:
        logger.error(f"文档渲染失败 - session_id: {session_id}, error: {str(e)}")
        raise HTTPException(
            status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            detail=f"文档渲染失败: {str(e)}"
        )


@router.get("/download/{filename}")
async def download_document(filename: str):
    """
    下载生成的文档
    """
    try:
        logger.info(f"下载文档 - filename: {filename}")

        doc_renderer = get_doc_renderer()
        file_path = doc_renderer.output_dir / filename

        if not file_path.exists():
            raise HTTPException(
                status_code=HttpStatus.NOT_FOUND,
                detail="文件不存在"
            )

        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载文档失败 - filename: {filename}, error: {str(e)}")
        raise HTTPException(
            status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/session/{session_id}", response_model=dict)
async def delete_session(session_id: str):
    """
    删除填写会话
    """
    try:
        logger.info(f"删除填写会话 - session_id: {session_id}")

        slot_manager = get_slot_manager()
        success = slot_manager.delete_session(session_id)

        if not success:
            raise HTTPException(
                status_code=HttpStatus.NOT_FOUND,
                detail="会话不存在"
            )

        logger.info(f"删除填写会话成功 - session_id: {session_id}")
        return {
            "code": HttpStatus.OK,
            "status": "success",
            "message": "会话删除成功",
            "data": None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除填写会话失败 - session_id: {session_id}, error: {str(e)}")
        raise HTTPException(
            status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/templates", response_model=dict)
async def list_templates():
    """
    获取可用的模板列表
    """
    try:
        logger.info("查询模板列表")

        slot_manager = get_slot_manager()
        templates = []

        for template_type, template_def in slot_manager._templates.items():
            templates.append({
                "template_type": template_def.template_type,
                "template_name": template_def.template_name,
                "template_file": template_def.template_file,
                "block_count": len(template_def.blocks)
            })

        logger.info(f"查询模板列表成功 - total: {len(templates)}")
        return {
            "code": HttpStatus.OK,
            "status": "success",
            "message": "",
            "data": {
                "templates": templates,
                "total": len(templates)
            }
        }

    except Exception as e:
        logger.error(f"查询模板列表失败 - error: {str(e)}")
        raise HTTPException(
            status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
