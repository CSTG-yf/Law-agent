from typing import Dict, List, Optional, Any
from app.schema.form_filling import (
    FormFillingState,
    BlockState,
    SlotStatus,
    BlockDefinition,
    TemplateDefinition
)
from app.core.logger import get_logger
import json

logger = get_logger("slot_manager")


class SlotManager:
    def __init__(self):
        self._sessions: Dict[str, FormFillingState] = {}
        self._templates: Dict[str, TemplateDefinition] = {}
        self._load_template_definitions()

    def _load_template_definitions(self):
        self._templates["labor_dispute"] = TemplateDefinition(
            template_type="labor_dispute",
            template_name="劳动争议起诉状",
            template_file="Labour_Litigation_Template.docx",
            blocks=[
                BlockDefinition(
                    block_id="plaintiff",
                    display_name="原告信息",
                    description="填写原告的基本信息",
                    slots=[
                        "plaintiff.name",
                        "plaintiff.gender",
                        "plaintiff.birthday",
                        "plaintiff.ethnicity",
                        "plaintiff.work_unit",
                        "plaintiff.job_title",
                        "plaintiff.phone",
                        "plaintiff.domicile",
                        "plaintiff.habitual_residence"
                    ],
                    required_slots=[
                        "plaintiff.name",
                        "plaintiff.phone",
                        "plaintiff.habitual_residence"
                    ],
                    order=1
                ),
                BlockDefinition(
                    block_id="agent",
                    display_name="代理人信息",
                    description="填写委托代理人的信息（如有）",
                    slots=[
                        "agent.has_agent",
                        "agent.name",
                        "agent.work_place",
                        "agent.job",
                        "agent.phone",
                        "agent.auth"
                    ],
                    required_slots=[],
                    order=2
                ),
                BlockDefinition(
                    block_id="service",
                    display_name="送达地址",
                    description="填写法律文书送达地址",
                    slots=[
                        "service.address",
                        "service.recipient",
                        "service.phone",
                        "service.allow_electronic",
                        "service.wechat",
                        "service.mail"
                    ],
                    required_slots=[
                        "service.address",
                        "service.recipient",
                        "service.phone"
                    ],
                    order=3
                ),
                BlockDefinition(
                    block_id="defendant",
                    display_name="被告信息",
                    description="填写被告的基本信息",
                    slots=[
                        "defendant.name",
                        "defendant.address",
                        "defendant.Company_address",
                        "defendant.legal_rep",
                        "defendant.job",
                        "defendant.phone",
                        "defendant.social_credit_code",
                        "defendant.entity_type",
                        "defendant.is_state_owned"
                    ],
                    required_slots=[
                        "defendant.name",
                        "defendant.address"
                    ],
                    order=4
                ),
                BlockDefinition(
                    block_id="claims",
                    display_name="诉讼请求",
                    description="填写诉讼请求和金额",
                    slots=[
                        "claims.salary.active",
                        "claims.salary.details",
                        "claims.double_salary.active",
                        "claims.double_salary.details",
                        "claims.overtime.active",
                        "claims.overtime.details",
                        "claims.annual_leave.active",
                        "claims.annual_leave.details",
                        "claims.social_loss.active",
                        "claims.social_loss.details",
                        "claims.termination_compensation.active",
                        "claims.termination_compensation.details",
                        "claims.illegal_termination_damages.active",
                        "claims.illegal_termination_damages.details",
                        "claims.other_requests",
                        "claims.litigation_cost_burden"
                    ],
                    required_slots=[],
                    order=5
                ),
                BlockDefinition(
                    block_id="preservation",
                    display_name="财产保全",
                    description="填写诉前财产保全信息（如有）",
                    slots=[
                        "preservation.active",
                        "preservation.court",
                        "preservation.document"
                    ],
                    required_slots=[],
                    order=6
                ),
                BlockDefinition(
                    block_id="facts",
                    display_name="事实与理由",
                    description="填写劳动关系相关事实",
                    slots=[
                        "facts.contract_signing",
                        "facts.performance_details",
                        "facts.termination_reason",
                        "facts.work_injury",
                        "facts.arbitration_details",
                        "facts.is_migrant_worker",
                        "facts.legal_basis"
                    ],
                    required_slots=[
                        "facts.performance_details",
                        "facts.termination_reason"
                    ],
                    order=7
                )
            ]
        )
        logger.info(f"模板定义加载完成 - total: {len(self._templates)}")

    def create_session(self, template_type: str = "labor_dispute") -> FormFillingState:
        session_id = f"filling-{template_type}-{self._generate_id()}"
        
        template = self._templates.get(template_type)
        if not template:
            raise ValueError(f"模板类型不存在: {template_type}")

        blocks = {}
        for block_def in template.blocks:
            slots = {}
            for slot_name in block_def.slots:
                parts = slot_name.split(".")
                slot_key = parts[1] if len(parts) > 1 else slot_name
                slots[slot_key] = SlotStatus(
                    value=None,
                    confirmed=False,
                    source="default",
                    confidence=0.0,
                    turn_filled=0
                )

            blocks[block_def.block_id] = BlockState(
                block_id=block_def.block_id,
                display_name=block_def.display_name,
                slots=slots,
                completion_rate=0.0,
                is_active=(block_def.block_id == template.blocks[0].block_id),
                is_complete=False
            )

        state = FormFillingState(
            session_id=session_id,
            template_type=template_type,
            blocks=blocks,
            current_block=template.blocks[0].block_id
        )

        self._sessions[session_id] = state
        logger.info(f"创建填充会话 - session_id: {session_id}, template: {template_type}")
        return state

    def get_session(self, session_id: str) -> Optional[FormFillingState]:
        return self._sessions.get(session_id)

    def update_slot(
        self,
        session_id: str,
        block_id: str,
        slot_name: str,
        value: Any,
        confirmed: bool = True,
        source: str = "user_input",
        confidence: float = 1.0
    ) -> bool:
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"会话不存在 - session_id: {session_id}")
            return False

        if block_id not in session.blocks:
            logger.warning(f"业务块不存在 - session_id: {session_id}, block_id: {block_id}")
            return False

        block = session.blocks[block_id]
        if slot_name not in block.slots:
            logger.warning(f"槽位不存在 - session_id: {session_id}, block_id: {block_id}, slot_name: {slot_name}")
            return False

        block.slots[slot_name] = SlotStatus(
            value=value,
            confirmed=confirmed,
            source=source,
            confidence=confidence,
            turn_filled=session.conversation_turn
        )

        self._update_block_completion(session, block_id)
        session.updated_at = self._get_current_timestamp()
        
        logger.info(f"更新槽位 - session_id: {session_id}, block_id: {block_id}, slot_name: {slot_name}, value: {value}")
        return True

    def _update_block_completion(self, session: FormFillingState, block_id: str):
        template = self._templates.get(session.template_type)
        if not template:
            return

        block_def = next((b for b in template.blocks if b.block_id == block_id), None)
        if not block_def:
            return

        block = session.blocks[block_id]
        
        filled_slots = sum(1 for slot in block.slots.values() if slot.value is not None and slot.value != "")
        total_slots = len(block.slots)
        block.completion_rate = filled_slots / total_slots if total_slots > 0 else 0.0

        required_filled = all(
            block.slots.get(
                slot_name.split(".")[1] if "." in slot_name else slot_name,
                SlotStatus()
            ).value is not None 
            and block.slots.get(
                slot_name.split(".")[1] if "." in slot_name else slot_name,
                SlotStatus()
            ).value != ""
            for slot_name in block_def.required_slots
        )
        
        if block_id == "agent":
            has_agent_slot = block.slots.get("has_agent")
            if has_agent_slot and has_agent_slot.value == False:
                block.is_complete = True
                block.completion_rate = 1.0
            else:
                block.is_complete = required_filled and block.completion_rate >= 0.8
        else:
            block.is_complete = required_filled and block.completion_rate >= 0.8

        logger.info(f"更新业务块完成度 - session_id: {session.session_id}, block_id: {block_id}, completion_rate: {block.completion_rate:.2f}, is_complete: {block.is_complete}")

    def get_missing_required_slots(self, session_id: str, block_id: str) -> List[str]:
        session = self.get_session(session_id)
        if not session:
            return []

        template = self._templates.get(session.template_type)
        if not template:
            return []

        block_def = next((b for b in template.blocks if b.block_id == block_id), None)
        if not block_def:
            return []

        block = session.blocks.get(block_id)
        if not block:
            return []

        missing = []
        for slot_name in block_def.required_slots:
            slot_key = slot_name.split(".")[1] if "." in slot_name else slot_name
            slot = block.slots.get(slot_key)
            if not slot or not slot.value or slot.value == "":
                missing.append(slot_name)

        return missing

    def get_low_confidence_slots(self, session_id: str, block_id: str, threshold: float = 0.7) -> List[str]:
        session = self.get_session(session_id)
        if not session:
            return []

        block = session.blocks.get(block_id)
        if not block:
            return []

        low_conf = []
        for slot_name, slot in block.slots.items():
            if slot.value and slot.confidence < threshold:
                low_conf.append(slot_name)

        return low_conf

    def switch_block(self, session_id: str, target_block_id: str) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False

        if target_block_id not in session.blocks:
            logger.warning(f"目标业务块不存在 - session_id: {session_id}, target_block_id: {target_block_id}")
            return False

        for block_id in session.blocks:
            session.blocks[block_id].is_active = (block_id == target_block_id)

        session.current_block = target_block_id
        session.updated_at = self._get_current_timestamp()
        
        logger.info(f"切换业务块 - session_id: {session_id}, target_block: {target_block_id}")
        return True

    def get_overall_completion_rate(self, session_id: str) -> float:
        session = self.get_session(session_id)
        if not session:
            return 0.0

        total_slots = 0
        filled_slots = 0

        for block in session.blocks.values():
            for slot in block.slots.values():
                total_slots += 1
                if slot.value and slot.value != "":
                    filled_slots += 1

        return filled_slots / total_slots if total_slots > 0 else 0.0

    def is_complete(self, session_id: str) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False

        template = self._templates.get(session.template_type)
        if not template:
            return False

        for block_def in template.blocks:
            block = session.blocks.get(block_def.block_id)
            if not block or not block.is_complete:
                return False

        return True

    def get_next_block(self, session_id: str) -> Optional[str]:
        session = self.get_session(session_id)
        if not session:
            return None

        template = self._templates.get(session.template_type)
        if not template:
            return None

        current_index = -1
        for i, block_def in enumerate(template.blocks):
            if block_def.block_id == session.current_block:
                current_index = i
                break

        if current_index >= 0 and current_index < len(template.blocks) - 1:
            return template.blocks[current_index + 1].block_id

        return None

    def get_template_definition(self, template_type: str) -> Optional[TemplateDefinition]:
        return self._templates.get(template_type)

    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"删除会话 - session_id: {session_id}")
            return True
        return False

    def _generate_id(self) -> str:
        import uuid
        return uuid.uuid4().hex[:12]

    def _get_current_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()


_slot_manager_instance = None


def get_slot_manager() -> SlotManager:
    global _slot_manager_instance
    if _slot_manager_instance is None:
        _slot_manager_instance = SlotManager()
    return _slot_manager_instance
