from typing import Dict, List, Optional
from app.schema.form_filling import FormFillingState, BlockState
from app.core.logger import get_logger

logger = get_logger("conversation_strategy")


class ConversationStrategy:
    def __init__(self):
        self.block_greetings = {
            "plaintiff": "好的，我们先来填写原告信息。请告诉我您的姓名、联系方式和住址。",
            "agent": "请问您有委托代理人吗？如果有，请告诉我代理人的相关信息。",
            "service": "接下来请填写法律文书送达地址，这是法院向您送达法律文书的重要信息。",
            "defendant": "现在请告诉我被告公司的信息，包括公司名称、地址等。",
            "claims": "现在请告诉我您的诉讼请求，包括您希望被告赔偿哪些费用。",
            "preservation": "请问您是否需要申请诉前财产保全？",
            "facts": "最后，请详细描述一下您和被告之间的劳动关系情况，包括入职时间、工作内容、离职原因等。"
        }

        self.block_completion_messages = {
            "plaintiff": "原告信息已填写完成。",
            "agent": "代理人信息已填写完成。",
            "service": "送达地址已填写完成。",
            "defendant": "被告信息已填写完成。",
            "claims": "诉讼请求已填写完成。",
            "preservation": "财产保全信息已填写完成。",
            "facts": "事实与理由已填写完成。"
        }

    def get_greeting_message(self, block_id: str) -> str:
        """
        获取业务块的引导语
        """
        return self.block_greetings.get(block_id, "请继续填写相关信息。")

    def get_completion_message(self, block_id: str) -> str:
        """
        获取业务块完成的消息
        """
        return self.block_completion_messages.get(block_id, "该部分信息已填写完成。")

    def generate_next_action(
        self,
        state: FormFillingState,
        extraction_result: Dict
    ) -> Dict[str, any]:
        """
        根据当前状态和提取结果，决定下一步行动
        """
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
            return {
                "message": f"{self.get_completion_message(state.current_block)} {self.get_greeting_message(next_block)}",
                "needs_clarification": False,
                "suggested_next_action": f"switch_to_{next_block}"
            }

        return {
            "message": "所有信息已填写完成！您可以点击生成文档按钮，生成法律文书。",
            "needs_clarification": False,
            "suggested_next_action": "generate_document"
        }

    def _get_missing_required_slots(self, state: FormFillingState, block_id: str) -> List[str]:
        """
        获取当前块中缺失的必填槽位
        """
        from app.service.form_filling.slot_manager import get_slot_manager
        slot_manager = get_slot_manager()
        return slot_manager.get_missing_required_slots(state.session_id, block_id)

    def _get_low_confidence_slots(self, state: FormFillingState, block_id: str, threshold: float = 0.7) -> List[str]:
        """
        获取当前块中低置信度的槽位
        """
        from app.service.form_filling.slot_manager import get_slot_manager
        slot_manager = get_slot_manager()
        return slot_manager.get_low_confidence_slots(state.session_id, block_id, threshold)

    def _generate_question_for_slot(self, slot_name: str) -> str:
        """
        为特定槽位生成问题
        """
        slot_questions = {
            "plaintiff.name": "请问您的姓名是什么？",
            "plaintiff.gender": "请问您的性别是？",
            "plaintiff.birthday": "请问您的出生日期是？（格式：YYYY-MM-DD）",
            "plaintiff.ethnicity": "请问您的民族是？",
            "plaintiff.work_unit": "请问您的工作单位是？",
            "plaintiff.job_title": "请问您的职位是？",
            "plaintiff.phone": "请问您的联系电话是？",
            "plaintiff.domicile": "请问您的户籍地址是？",
            "plaintiff.habitual_residence": "请问您的现住址是？",
            "agent.has_agent": "请问您是否有委托代理人？",
            "agent.name": "请问代理人的姓名是？",
            "agent.work_place": "请问代理人的工作单位是？",
            "agent.job": "请问代理人的职务是？",
            "agent.phone": "请问代理人的联系电话是？",
            "agent.auth": "请问代理人的授权类型是？（一般授权/特别授权）",
            "service.address": "请问法律文书的送达地址是？",
            "service.recipient": "请问收件人是谁？",
            "service.phone": "请问收件人的联系电话是？",
            "service.allow_electronic": "请问是否接受电子送达？",
            "service.wechat": "请问微信号是？",
            "service.mail": "请问电子邮箱是？",
            "defendant.name": "请问被告公司的名称是？",
            "defendant.address": "请问被告公司的地址是？",
            "defendant.Company_address": "请问被告公司的注册地址是？",
            "defendant.legal_rep": "请问被告公司的法定代表人是谁？",
            "defendant.job": "请问法定代表人的职务是？",
            "defendant.phone": "请问法定代表人的电话是？",
            "defendant.social_credit_code": "请问被告公司的统一社会信用代码是？",
            "defendant.entity_type": "请问被告公司的企业类型是？（如：有限责任公司、股份有限公司等）",
            "defendant.is_state_owned": "请问被告公司是否为国有企业？",
            "claims.salary.active": "请问是否主张工资？",
            "claims.salary.details": "请详细说明工资诉求。",
            "claims.double_salary.active": "请问是否主张未签劳动合同双倍工资？",
            "claims.double_salary.details": "请详细说明双倍工资诉求。",
            "claims.overtime.active": "请问是否主张加班费？",
            "claims.overtime.details": "请详细说明加班费诉求。",
            "claims.annual_leave.active": "请问是否主张年休假工资？",
            "claims.annual_leave.details": "请详细说明年休假工资诉求。",
            "claims.social_loss.active": "请问是否主张社保损失？",
            "claims.social_loss.details": "请详细说明社保损失诉求。",
            "claims.termination_compensation.active": "请问是否主张经济补偿金？",
            "claims.termination_compensation.details": "请详细说明经济补偿金诉求。",
            "claims.illegal_termination_damages.active": "请问是否主张违法解除劳动合同赔偿金？",
            "claims.illegal_termination_damages.details": "请详细说明违法解除赔偿金诉求。",
            "claims.other_requests": "请问还有其他诉讼请求吗？",
            "claims.litigation_cost_burden": "请问诉讼费用由谁承担？",
            "preservation.active": "请问是否申请诉前财产保全？",
            "preservation.court": "请问保全法院是？",
            "preservation.document": "请问保全文书是？",
            "facts.contract_signing": "请问劳动合同签订情况如何？",
            "facts.performance_details": "请详细描述劳动合同履行情况。",
            "facts.termination_reason": "请问离职原因是什么？",
            "facts.work_injury": "请问是否有工伤情况？",
            "facts.arbitration_details": "请问是否申请过劳动仲裁？如有，请说明仲裁情况。",
            "facts.is_migrant_worker": "请问您是否为农民工？",
            "facts.legal_basis": "请问法律依据是什么？"
        }
        return slot_questions.get(slot_name, f"请填写{slot_name}的信息")

    def _generate_confirmation_question(self, slot_name: str) -> str:
        """
        为低置信度槽位生成确认问题
        """
        slot_confirmations = {
            "plaintiff.name": "请确认一下，您的姓名是{value}吗？",
            "plaintiff.phone": "请确认一下，您的联系电话是{value}吗？",
            "defendant.name": "请确认一下，被告公司的名称是{value}吗？",
            "facts.performance_details": "请确认一下，劳动合同履行情况是否正确？",
            "facts.termination_reason": "请确认一下，离职原因是否正确？"
        }
        return slot_confirmations.get(slot_name, f"请确认一下，{slot_name}的信息是否正确？")

    def _get_next_block(self, state: FormFillingState) -> Optional[str]:
        """
        获取下一个业务块
        """
        from app.service.form_filling.slot_manager import get_slot_manager
        slot_manager = get_slot_manager()
        return slot_manager.get_next_block(state.session_id)

    def handle_user_intent(self, user_input: str, state: FormFillingState) -> Optional[str]:
        """
        处理用户的意图（如修改、跳转等）
        """
        user_input_lower = user_input.lower()

        if "没有" in user_input or "不" in user_input or "无" in user_input or "不需要" in user_input:
            next_block = self._get_next_block(state)
            if next_block:
                return f"switch_to_{next_block}"

        if "跳过" in user_input or "skip" in user_input_lower:
            next_block = self._get_next_block(state)
            if next_block:
                return f"switch_to_{next_block}"

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
