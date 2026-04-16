from typing import Dict, List, Optional, Any
from app.schema.form_filling import (
    FormFillingState,
    BlockState,
    SlotStatus,
    BlockDefinition,
    TemplateDefinition
)
from app.core.config import settings
from app.core.logger import get_logger
import json

logger = get_logger("slot_manager")

SESSION_KEY_PREFIX = "form_filling:session:"
HISTORY_KEY_PREFIX = "form_filling:history:"
SESSION_INDEX_KEY = "form_filling:sessions"


class SlotManager:
    def __init__(self):
        self._templates: Dict[str, TemplateDefinition] = {}
        self._load_template_definitions()
        self._redis = None

    def _get_redis(self):
        if self._redis is None:
            import redis
            self._redis = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=False
            )
            try:
                self._redis.ping()
                logger.info(f"Redis连接成功 - {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            except Exception as e:
                logger.error(f"Redis连接失败 - {e}")
                raise
        return self._redis

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

    def _save_session(self, state: FormFillingState):
        try:
            redis_client = self._get_redis()
            key = f"{SESSION_KEY_PREFIX}{state.session_id}"
            data = state.model_dump()
            json_str = json.dumps(data, ensure_ascii=False)
            redis_client.set(key, json_str)
            logger.info(f"会话已保存到Redis - session_id: {state.session_id}, data_size: {len(json_str)}")
        except Exception as e:
            logger.error(f"保存会话到Redis失败 - session_id: {state.session_id}, error: {e}")
            raise

    def _load_session_from_redis(self, session_id: str) -> Optional[FormFillingState]:
        redis_client = self._get_redis()
        key = f"{SESSION_KEY_PREFIX}{session_id}"
        data = redis_client.get(key)
        if data is None:
            return None
        try:
            state_dict = json.loads(data)
            return FormFillingState(**state_dict)
        except Exception as e:
            logger.error(f"从Redis加载会话失败 - session_id: {session_id}, error: {e}")
            return None

    def _delete_session_from_redis(self, session_id: str) -> bool:
        redis_client = self._get_redis()
        key = f"{SESSION_KEY_PREFIX}{session_id}"
        result = redis_client.delete(key)
        return result > 0

    def create_session(self, template_type: str = "labor_dispute") -> FormFillingState:
        session_id = f"filling-{template_type}-{self._generate_id()}"
        
        template = self._templates.get(template_type)
        if not template:
            raise ValueError(f"模板类型不存在: {template_type}")

        blocks = {}
        for block_def in template.blocks:
            slots = {}
            for slot_name in block_def.slots:
                parts = slot_name.split(".", 1)
                slot_key = parts[1] if len(parts) == 2 else slot_name
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

        self._save_session(state)
        logger.info(f"创建填充会话 - session_id: {session_id}, template: {template_type}")
        return state

    def get_session(self, session_id: str) -> Optional[FormFillingState]:
        return self._load_session_from_redis(session_id)

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

        old_value = block.slots[slot_name].value
        
        if block_id == "claims" and slot_name.endswith(".active"):
            prefix = slot_name.rsplit(".", 1)[0]
            details_slot_name = f"{prefix}.details"
            
            if old_value != value:
                if details_slot_name in block.slots:
                    if value == False:
                        block.slots[details_slot_name] = SlotStatus(
                            value=None,
                            confirmed=True,
                            source="cleared",
                            confidence=1.0,
                            turn_filled=session.conversation_turn
                        )
                        logger.info(f"清空明细槽位（已确认）- session_id: {session_id}, block_id: {block_id}, slot_name: {details_slot_name}, reason: active_false")
                    else:
                        block.slots[details_slot_name] = SlotStatus(
                            value=None,
                            confirmed=False,
                            source="cleared",
                            confidence=0.0,
                            turn_filled=session.conversation_turn
                        )
                        logger.info(f"清空明细槽位（待填写）- session_id: {session_id}, block_id: {block_id}, slot_name: {details_slot_name}, reason: active_true")

        elif block_id == "agent" and slot_name == "has_agent":
            if old_value != value:
                agent_slots_to_clear = ["name", "work_place", "job", "phone", "auth"]
                for slot_to_clear in agent_slots_to_clear:
                    if slot_to_clear in block.slots:
                        block.slots[slot_to_clear] = SlotStatus(
                            value=None,
                            confirmed=False,
                            source="cleared",
                            confidence=0.0,
                            turn_filled=session.conversation_turn
                        )
                logger.info(f"清空代理人信息槽位 - session_id: {session_id}, block_id: {block_id}, reason: has_agent_changed")

        elif block_id == "service" and slot_name == "allow_electronic":
            if old_value != value:
                service_slots_to_clear = ["wechat", "mail"]
                for slot_to_clear in service_slots_to_clear:
                    if slot_to_clear in block.slots:
                        block.slots[slot_to_clear] = SlotStatus(
                            value=None,
                            confirmed=False,
                            source="cleared",
                            confidence=0.0,
                            turn_filled=session.conversation_turn
                        )
                logger.info(f"清空电子送达槽位 - session_id: {session_id}, block_id: {block_id}, reason: allow_electronic_changed")

        elif block_id == "preservation" and slot_name == "active":
            if old_value != value:
                preservation_slots_to_clear = ["court", "document"]
                for slot_to_clear in preservation_slots_to_clear:
                    if slot_to_clear in block.slots:
                        block.slots[slot_to_clear] = SlotStatus(
                            value=None,
                            confirmed=False,
                            source="cleared",
                            confidence=0.0,
                            turn_filled=session.conversation_turn
                        )
                logger.info(f"清空财产保全槽位 - session_id: {session_id}, block_id: {block_id}, reason: active_changed")

        block.slots[slot_name] = SlotStatus(
            value=value,
            confirmed=confirmed,
            source=source,
            confidence=confidence,
            turn_filled=session.conversation_turn
        )

        self._update_block_completion(session, block_id)
        session.updated_at = self._get_current_timestamp()
        
        self._save_session(session)
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

        if block_id == "agent":
            has_agent_slot = block.slots.get("has_agent")
            if has_agent_slot and has_agent_slot.value == False:
                block.is_complete = True
                block.completion_rate = 1.0
                logger.info(f"更新业务块完成度 - session_id: {session.session_id}, block_id: {block_id}, completion_rate: {block.completion_rate:.2f}, is_complete: {block.is_complete}")
                return
            else:
                effective_slots = {k: v for k, v in block.slots.items() if k != "has_agent"}
        elif block_id == "claims":
            claims_pairs = [
                ("salary", "active", "details"),
                ("double_salary", "active", "details"),
                ("overtime", "active", "details"),
                ("annual_leave", "active", "details"),
                ("social_loss", "active", "details"),
                ("termination_compensation", "active", "details"),
                ("illegal_termination_damages", "active", "details"),
            ]

            def _has_meaningful_value(slot: Optional[SlotStatus]) -> bool:
                return slot is not None and slot.value is not None and slot.value != ""

            total_slots = 0
            filled_slots = 0
            all_claims_answered = True
            active_claim_details_complete = True

            for prefix, active_key, details_key in claims_pairs:
                active_slot = block.slots.get(f"{prefix}.{active_key}")
                details_slot = block.slots.get(f"{prefix}.{details_key}")

                total_slots += 1
                if active_slot and active_slot.value is not None:
                    filled_slots += 1
                else:
                    all_claims_answered = False

                if active_slot and active_slot.value is True:
                    total_slots += 1
                    if _has_meaningful_value(details_slot):
                        filled_slots += 1
                    else:
                        active_claim_details_complete = False

            other_requests_slot = block.slots.get("other_requests")
            litigation_slot = block.slots.get("litigation_cost_burden")
            other_requests_filled = _has_meaningful_value(other_requests_slot)
            litigation_filled = _has_meaningful_value(litigation_slot)

            total_slots += 2
            if other_requests_filled:
                filled_slots += 1
            if litigation_filled:
                filled_slots += 1

            block.completion_rate = filled_slots / total_slots if total_slots > 0 else 0.0
            block.is_complete = (
                all_claims_answered
                and active_claim_details_complete
                and other_requests_filled
                and litigation_filled
            )
            logger.info(f"更新业务块完成度 - session_id: {session.session_id}, block_id: {block_id}, completion_rate: {block.completion_rate:.2f}, is_complete: {block.is_complete}")
            return
        else:
            effective_slots = block.slots

        if block_id == "service":
            allow_electronic_slot = block.slots.get("allow_electronic")
            if allow_electronic_slot and allow_electronic_slot.value == False:
                for skip_key in ["wechat", "mail"]:
                    skip_slot = block.slots.get(skip_key)
                    if skip_slot and (not skip_slot.confirmed or skip_slot.value is None):
                        block.slots[skip_key] = SlotStatus(
                            value=None,
                            confirmed=True,
                            source="inferred",
                            confidence=1.0,
                            turn_filled=session.conversation_turn
                        )
                effective_slots = {k: v for k, v in block.slots.items() if k not in ["wechat", "mail"]}

        if block_id == "preservation":
            active_slot = block.slots.get("active")
            if active_slot and active_slot.value == False:
                for skip_key in ["court", "document"]:
                    skip_slot = block.slots.get(skip_key)
                    if skip_slot and (not skip_slot.confirmed or skip_slot.value is None):
                        block.slots[skip_key] = SlotStatus(
                            value=None,
                            confirmed=True,
                            source="inferred",
                            confidence=1.0,
                            turn_filled=session.conversation_turn
                        )
                effective_slots = {k: v for k, v in block.slots.items() if k not in ["court", "document"]}

        filled_slots = sum(1 for slot in effective_slots.values() if (slot.value is not None and slot.value != "") or slot.confirmed)
        total_slots = len(effective_slots)
        block.completion_rate = filled_slots / total_slots if total_slots > 0 else 0.0

        required_filled = all(
            block.slots.get(
                slot_name.split(".", 1)[1] if "." in slot_name else slot_name,
                SlotStatus()
            ).value is not None 
            and block.slots.get(
                slot_name.split(".", 1)[1] if "." in slot_name else slot_name,
                SlotStatus()
            ).value != ""
            for slot_name in block_def.required_slots
        )
        
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
            slot_key = slot_name.split(".", 1)[1] if "." in slot_name else slot_name
            slot = block.slots.get(slot_key)
            if not slot or slot.value is None or slot.value == "":
                missing.append(slot_name)

        return missing

    def finalize_block(self, session_id: str, block_id: str) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False

        block = session.blocks.get(block_id)
        if not block:
            return False

        if block_id == "agent":
            has_agent_slot = block.slots.get("has_agent")
            if has_agent_slot and has_agent_slot.value == False:
                for skip_key in ["name", "work_place", "job", "phone", "auth"]:
                    skip_slot = block.slots.get(skip_key)
                    if skip_slot and (not skip_slot.confirmed or skip_slot.value is None):
                        block.slots[skip_key] = SlotStatus(
                            value=None,
                            confirmed=True,
                            source="inferred",
                            confidence=1.0,
                            turn_filled=session.conversation_turn
                        )

        elif block_id == "service":
            allow_electronic_slot = block.slots.get("allow_electronic")
            if allow_electronic_slot and allow_electronic_slot.value == False:
                for skip_key in ["wechat", "mail"]:
                    skip_slot = block.slots.get(skip_key)
                    if skip_slot and (not skip_slot.confirmed or skip_slot.value is None):
                        block.slots[skip_key] = SlotStatus(
                            value=None,
                            confirmed=True,
                            source="inferred",
                            confidence=1.0,
                            turn_filled=session.conversation_turn
                        )

        elif block_id == "preservation":
            active_slot = block.slots.get("active")
            if active_slot and active_slot.value == False:
                for skip_key in ["court", "document"]:
                    skip_slot = block.slots.get(skip_key)
                    if skip_slot and (not skip_slot.confirmed or skip_slot.value is None):
                        block.slots[skip_key] = SlotStatus(
                            value=None,
                            confirmed=True,
                            source="inferred",
                            confidence=1.0,
                            turn_filled=session.conversation_turn
                        )

        elif block_id == "claims":
            claims_pairs = [
                ("salary", "active", "details"),
                ("double_salary", "active", "details"),
                ("overtime", "active", "details"),
                ("annual_leave", "active", "details"),
                ("social_loss", "active", "details"),
                ("termination_compensation", "active", "details"),
                ("illegal_termination_damages", "active", "details"),
            ]
            for prefix, active_key, details_key in claims_pairs:
                active_slot = block.slots.get(f"{prefix}.{active_key}")
                details_slot = block.slots.get(f"{prefix}.{details_key}")
                if active_slot and active_slot.value is None:
                    block.slots[f"{prefix}.{active_key}"] = SlotStatus(
                        value=False,
                        confirmed=True,
                        source="inferred",
                        confidence=1.0,
                        turn_filled=session.conversation_turn
                    )
                if details_slot and details_slot.value is None:
                    block.slots[f"{prefix}.{details_key}"] = SlotStatus(
                        value=None,
                        confirmed=True,
                        source="inferred",
                        confidence=1.0,
                        turn_filled=session.conversation_turn
                    )

        block.is_complete = True
        block.completion_rate = 1.0
        self._save_session(session)
        logger.info(f"完成业务块 - session_id: {session_id}, block_id: {block_id}")
        return True

    def get_low_confidence_slots(self, session_id: str, block_id: str, threshold: float = 0.7) -> List[str]:
        session = self.get_session(session_id)
        if not session:
            return []

        block = session.blocks.get(block_id)
        if not block:
            return []

        low_conf = []
        for slot_name, slot in block.slots.items():
            if slot.value is not None and slot.value != "" and slot.confidence < threshold:
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
        
        self._save_session(session)
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
                if (slot.value is not None and slot.value != "") or slot.confirmed:
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

    def save_conversation_history(self, session_id: str, role: str, message: str):
        redis_client = self._get_redis()
        key = f"{HISTORY_KEY_PREFIX}{session_id}"
        entry = json.dumps({"role": role, "message": message, "timestamp": self._get_current_timestamp()}, ensure_ascii=False)
        redis_client.rpush(key, entry)
        history_count = redis_client.llen(key)
        logger.info(f"保存对话历史 - session_id: {session_id}, role: {role}, redis_history_count: {history_count}")

    def get_conversation_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict]:
        redis_client = self._get_redis()
        key = f"{HISTORY_KEY_PREFIX}{session_id}"
        history_count = redis_client.llen(key)
        if limit and limit > 0:
            raw_entries = redis_client.lrange(key, -limit, -1)
        else:
            raw_entries = redis_client.lrange(key, 0, -1)
        history = []
        for entry in raw_entries:
            try:
                history.append(json.loads(entry))
            except Exception:
                continue
        logger.info(
            f"获取对话历史成功 - session_id: {session_id}, limit: {limit}, "
            f"redis_history_count: {history_count}, returned_count: {len(history)}"
        )
        return history

    def get_session_list(self) -> List[Dict]:
        redis_client = self._get_redis()
        session_keys = redis_client.keys(f"{SESSION_KEY_PREFIX}*")
        sessions = []
        for key in session_keys:
            try:
                data = redis_client.get(key)
                if data:
                    state_dict = json.loads(data)
                    sessions.append({
                        "session_id": state_dict.get("session_id", ""),
                        "template_type": state_dict.get("template_type", ""),
                        "current_block": state_dict.get("current_block", ""),
                        "conversation_turn": state_dict.get("conversation_turn", 0),
                        "created_at": state_dict.get("created_at", ""),
                        "updated_at": state_dict.get("updated_at", ""),
                    })
            except Exception:
                continue
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return sessions

    def delete_session(self, session_id: str) -> bool:
        result = self._delete_session_from_redis(session_id)
        if result:
            redis_client = self._get_redis()
            redis_client.delete(f"{HISTORY_KEY_PREFIX}{session_id}")
            logger.info(f"删除会话 - session_id: {session_id}")
        return result

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
