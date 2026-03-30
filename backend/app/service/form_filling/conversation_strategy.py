from typing import Dict, List, Optional
from app.schema.form_filling import FormFillingState, BlockState
from app.core.logger import get_logger
from app.service.form_filling.prompts.conversation_prompts import (
    get_greeting, get_completion, get_slot_question, get_slot_confirmation,
    ALL_COMPLETE_MESSAGE
)

logger = get_logger("conversation_strategy")


class ConversationStrategy:

    def get_greeting_message(self, block_id: str) -> str:
        return get_greeting(block_id)

    def get_completion_message(self, block_id: str) -> str:
        return get_completion(block_id)

    def generate_next_action(
        self,
        state: FormFillingState,
        extraction_result: Dict
    ) -> Dict[str, any]:
        current_block = state.blocks.get(state.current_block)
        if not current_block:
            return {
                "message": "系统错误：找不到当前业务块",
                "needs_clarification": False,
                "suggested_next_action": None
            }

        missing_required = self._get_missing_required_slots(state, state.current_block)
        low_confidence = self._get_low_confidence_slots(state, state.current_block)

        if extraction_result.get("clarification_questions"):
            return {
                "message": extraction_result["clarification_questions"][0],
                "needs_clarification": True,
                "clarification_questions": extraction_result["clarification_questions"],
                "suggested_next_action": None
            }

        if low_confidence:
            slot_name = low_confidence[0]
            question = self._generate_confirmation_question(slot_name)
            return {
                "message": question,
                "needs_clarification": True,
                "suggested_next_action": None
            }

        if missing_required:
            slot_name = missing_required[0]
            question = self._generate_question_for_slot(slot_name)
            return {
                "message": question,
                "needs_clarification": False,
                "suggested_next_action": None
            }

        if current_block.completion_rate < 0.8:
            return {
                "message": f"{self.get_completion_message(state.current_block)} 还有其他信息需要补充吗？",
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

    def _get_missing_required_slots(self, state: FormFillingState, block_id: str) -> List[str]:
        from app.service.form_filling.slot_manager import get_slot_manager
        slot_manager = get_slot_manager()
        return slot_manager.get_missing_required_slots(state.session_id, block_id)

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

        skip_patterns = ["没有代理人", "没有代理", "无代理人", "无代理", "不需要代理人", "不需要代理", "没有", "不需要", "无"]
        is_skip = False
        for pattern in skip_patterns:
            if pattern in user_input:
                is_skip = True
                break
        if not is_skip:
            input_stripped = user_input.strip()
            if input_stripped.startswith("没有") or input_stripped.startswith("无") or input_stripped.startswith("不需要"):
                is_skip = True

        if is_skip:
            if state.current_block == "agent":
                return "skip_agent"
            if state.current_block == "preservation":
                return "skip_preservation"

        if "跳过" in user_input or "skip" in user_input_lower:
            if state.current_block == "agent":
                return "skip_agent"
            if state.current_block == "preservation":
                return "skip_preservation"

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
            return "generate_document"

        return None


_conversation_strategy_instance = None


def get_conversation_strategy() -> ConversationStrategy:
    global _conversation_strategy_instance
    if _conversation_strategy_instance is None:
        _conversation_strategy_instance = ConversationStrategy()
    return _conversation_strategy_instance
