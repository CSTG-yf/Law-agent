from typing import Dict, List, Optional, Tuple
from app.schema.form_filling import FormFillingState, BlockState
from app.core.logger import get_logger
from app.service.form_filling.prompts.conversation_prompts import (
    get_greeting, get_completion, get_slot_question, get_slot_confirmation,
    ALL_COMPLETE_MESSAGE
)

logger = get_logger("conversation_strategy")

CLAIMS_TYPES = [
    ("salary", "工资支付"),
    ("double_salary", "未签订劳动合同双倍工资"),
    ("overtime", "加班费"),
    ("annual_leave", "年休假工资"),
    ("social_loss", "社保损失"),
    ("termination_compensation", "经济补偿金"),
    ("illegal_termination_damages", "违法解除劳动合同赔偿金"),
]


class ConversationStrategy:

    def get_greeting_message(self, block_id: str) -> str:
        return get_greeting(block_id)

    def get_completion_message(self, block_id: str) -> str:
        return get_completion(block_id)

    def generate_next_action(
        self,
        state: FormFillingState,
        extraction_result: Dict,
        user_input: str = ""
    ) -> Dict[str, any]:
        current_block = state.blocks.get(state.current_block)
        if not current_block:
            return {
                "message": "系统错误：找不到当前业务块",
                "needs_clarification": False,
                "suggested_next_action": None
            }

        user_wants_skip = self._is_user_skipping(user_input)

        missing_required = self._get_missing_required_slots(state, state.current_block)
        low_confidence = self._get_low_confidence_slots(state, state.current_block)

        if extraction_result.get("clarification_questions") and not user_wants_skip:
            return {
                "message": extraction_result["clarification_questions"][0],
                "needs_clarification": True,
                "clarification_questions": extraction_result["clarification_questions"],
                "suggested_next_action": None
            }

        if low_confidence and not user_wants_skip:
            slot_name = low_confidence[0]
            question = self._generate_confirmation_question(slot_name)
            return {
                "message": question,
                "needs_clarification": True,
                "suggested_next_action": None
            }

        if missing_required and not user_wants_skip:
            slot_name = missing_required[0]
            question = self._generate_question_for_slot(slot_name)
            return {
                "message": question,
                "needs_clarification": False,
                "suggested_next_action": None
            }

        if state.current_block == "claims":
            claims_action = self._handle_claims_block(state, user_wants_skip)
            if claims_action:
                return claims_action

        if state.current_block == "facts":
            facts_block = state.blocks.get("facts")
            if facts_block:
                legal_basis_slot = facts_block.slots.get("legal_basis")
                if current_block.completion_rate >= 0.8 and (not legal_basis_slot or not legal_basis_slot.value):
                    return {
                        "message": "事实与理由部分已填写完成。是否需要我为您自动生成法律条文依据？您可以回复\"生成法律条文\"或\"不需要\"。",
                        "needs_clarification": False,
                        "suggested_next_action": None
                    }

        missing_optional = self._get_missing_optional_slots(state, state.current_block)
        if state.current_block == "facts":
            missing_optional = [slot_name for slot_name in missing_optional if slot_name != "facts.legal_basis"]
        if missing_optional and not user_wants_skip:
            slot_name = missing_optional[0]
            question = self._generate_question_for_slot(slot_name)
            return {
                "message": question,
                "needs_clarification": False,
                "suggested_next_action": None
            }

        if current_block.completion_rate < 0.8 and not user_wants_skip:
            return {
                "message": f"{self.get_completion_message(state.current_block)} 还有其他信息需要补充吗？",
                "needs_clarification": False,
                "suggested_next_action": None
            }

        if state.current_block == "facts":
            facts_block = state.blocks.get("facts")
            if facts_block:
                legal_basis_slot = facts_block.slots.get("legal_basis")
                if not legal_basis_slot or not legal_basis_slot.value:
                    return {
                        "message": "事实与理由部分已填写完成。是否需要我为您自动生成法律条文依据？您可以回复\"生成法律条文\"或\"不需要\"。",
                        "needs_clarification": False,
                        "suggested_next_action": None
                    }

        next_block = self._get_next_block(state)
        if next_block:
            completion_msg = self.get_completion_message(state.current_block)
            greeting_msg = self.get_greeting_message(next_block)
            return {
                "message": f"{completion_msg} {greeting_msg}",
                "needs_clarification": False,
                "suggested_next_action": f"switch_to_{next_block}"
            }

        return {
            "message": ALL_COMPLETE_MESSAGE,
            "needs_clarification": False,
            "suggested_next_action": "generate_document"
        }

    def _is_user_skipping(self, user_input: str) -> bool:
        if not user_input:
            return False
        skip_patterns = [
            "没有了", "没有其他", "没有更多信息", "没有要补充",
            "不需要补充", "就这些", "就这些了", "没了",
            "没有别的", "没有别的了", "没有其他信息", "不需要了",
            "没有了", "补充完了", "填完了", "好了", "可以了",
            "暂时没有", "目前没有", "先这样", "就这样"
        ]
        user_input_stripped = user_input.strip()
        for pattern in skip_patterns:
            if pattern in user_input_stripped:
                return True
        if user_input_stripped.startswith("没有") or user_input_stripped.startswith("无") or user_input_stripped.startswith("不需要"):
            return True
        return False

    def _get_missing_required_slots(self, state: FormFillingState, block_id: str) -> List[str]:
        from app.service.form_filling.slot_manager import get_slot_manager
        slot_manager = get_slot_manager()
        return slot_manager.get_missing_required_slots(state.session_id, block_id)

    def _get_missing_optional_slots(self, state: FormFillingState, block_id: str) -> List[str]:
        from app.service.form_filling.slot_manager import get_slot_manager
        slot_manager = get_slot_manager()
        template_def = slot_manager.get_template_definition(state.template_type)
        if not template_def:
            return []

        block_def = next((b for b in template_def.blocks if b.block_id == block_id), None)
        if not block_def:
            return []

        block = state.blocks.get(block_id)
        if not block:
            return []

        required_set = set(block_def.required_slots)
        missing = []
        for slot_name in block_def.slots:
            if slot_name in required_set:
                continue
            slot_key = slot_name.split(".", 1)[1] if "." in slot_name else slot_name
            slot = block.slots.get(slot_key)
            if not slot:
                continue
            if slot.confirmed and slot.source == "inferred" and slot.value is None:
                continue
            if slot.value is None or slot.value == "":
                missing.append(slot_name)
        return missing

    def _get_claims_status(self, state: FormFillingState) -> Tuple[List[str], List[str]]:
        block = state.blocks.get("claims")
        if not block:
            return [], []

        confirmed_claims = []
        unconfirmed_claims = []

        for claim_key, claim_name in CLAIMS_TYPES:
            active_slot = block.slots.get(f"{claim_key}.active")
            if active_slot and active_slot.value is not None and active_slot.confirmed:
                if active_slot.value == True:
                    confirmed_claims.append(claim_name)
            else:
                unconfirmed_claims.append(claim_name)

        return confirmed_claims, unconfirmed_claims

    def _handle_claims_block(self, state: FormFillingState, user_wants_skip: bool) -> Optional[Dict]:
        block = state.blocks.get("claims")
        if not block:
            return None

        confirmed_claims, unconfirmed_claims = self._get_claims_status(state)

        litigation_slot = block.slots.get("litigation_cost_burden")
        litigation_filled = litigation_slot and litigation_slot.value is not None

        if user_wants_skip:
            if not litigation_filled:
                return {
                    "message": "请问诉讼费用由谁承担？",
                    "needs_clarification": False,
                    "suggested_next_action": None
                }
            return None

        if unconfirmed_claims:
            examples = "、".join(unconfirmed_claims[:3])
            if len(unconfirmed_claims) > 3:
                examples += "等"
            return {
                "message": f"好的，已记录您的诉求。请问是否还有其他诉讼请求？例如：{examples}？",
                "needs_clarification": False,
                "suggested_next_action": None
            }

        if not litigation_filled:
            return {
                "message": "请问诉讼费用由谁承担？",
                "needs_clarification": False,
                "suggested_next_action": None
            }

        return None

    def _get_low_confidence_slots(self, state: FormFillingState, block_id: str, threshold: float = 0.7) -> List[str]:
        from app.service.form_filling.slot_manager import get_slot_manager
        slot_manager = get_slot_manager()
        return slot_manager.get_low_confidence_slots(state.session_id, block_id, threshold)

    def _generate_question_for_slot(self, slot_name: str) -> str:
        return get_slot_question(slot_name)

    def _generate_confirmation_question(self, slot_name: str) -> str:
        return get_slot_confirmation(slot_name)

    def _get_next_block(self, state: FormFillingState) -> Optional[str]:
        from app.service.form_filling.slot_manager import get_slot_manager
        slot_manager = get_slot_manager()
        return slot_manager.get_next_block(state.session_id)

    def handle_user_intent(self, user_input: str, state: FormFillingState) -> Optional[str]:
        user_input_lower = user_input.lower()

        negative_reply_patterns = ["没有代理人", "没有代理", "无代理人", "无代理", "不需要代理人", "不需要代理", "没有", "不需要", "无"]
        is_negative_reply = False
        for pattern in negative_reply_patterns:
            if pattern in user_input:
                is_negative_reply = True
                break
        if not is_negative_reply:
            input_stripped = user_input.strip()
            if input_stripped.startswith("没有") or input_stripped.startswith("无") or input_stripped.startswith("不需要"):
                is_negative_reply = True

        if is_negative_reply:
            if state.current_block == "agent":
                return "skip_agent"
            if state.current_block == "preservation":
                return "skip_preservation"
            if state.current_block == "claims":
                return "confirm_remaining_claims"

        if "跳过" in user_input or "skip" in user_input_lower:
            if state.current_block == "agent":
                return "skip_agent"
            if state.current_block == "preservation":
                return "skip_preservation"
            if state.current_block == "claims":
                return "confirm_remaining_claims"
            return "skip_current_block"

        if "修改" in user_input or "改" in user_input:
            if "原告" in user_input or "plaintiff" in user_input_lower:
                return "switch_to_plaintiff"
            elif "被告" in user_input or "defendant" in user_input_lower:
                return "switch_to_defendant"
            elif "事实" in user_input or "facts" in user_input_lower:
                return "switch_to_facts"
            elif "诉讼" in user_input or "claims" in user_input_lower:
                return "switch_to_claims"
            elif "代理" in user_input or "agent" in user_input_lower:
                return "switch_to_agent"
            elif "送达" in user_input or "service" in user_input_lower:
                return "switch_to_service"
            elif "保全" in user_input or "preservation" in user_input_lower:
                return "switch_to_preservation"

        if "完成" in user_input or "finish" in user_input_lower or "生成" in user_input:
            if "法律条文" in user_input or "法律依据" in user_input or "legal_basis" in user_input_lower:
                return "generate_legal_basis"
            return "generate_document"

        return None


_conversation_strategy_instance = None


def get_conversation_strategy() -> ConversationStrategy:
    global _conversation_strategy_instance
    if _conversation_strategy_instance is None:
        _conversation_strategy_instance = ConversationStrategy()
    return _conversation_strategy_instance
