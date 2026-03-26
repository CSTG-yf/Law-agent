from typing import Dict, List, Any, Optional
from langchain_openai import ChatOpenAI
from app.schema.form_filling import SlotExtractionResult
from app.core.config import settings
from app.core.logger import get_logger
import json
import re

logger = get_logger("slot_extractor")


class SlotExtractor:
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm or ChatOpenAI(
            base_url=settings.OPENAI_BASE_URL,
            api_key=settings.DASHSCOPE_API_KEY or settings.OPENAI_API_KEY,
            model=settings.MODEL_NAME,
            temperature=0.3
        )

    async def extract_slots(
        self,
        user_input: str,
        current_block: str,
        known_slots: Dict[str, Any],
        conversation_history: Optional[List[str]] = None
    ) -> SlotExtractionResult:
        """
        从用户输入中提取槽位信息
        """
        try:
            logger.info(f"开始槽位提取 - current_block: {current_block}, user_input: {user_input[:100]}")

            prompt = self._build_extraction_prompt(
                user_input=user_input,
                current_block=current_block,
                known_slots=known_slots,
                conversation_history=conversation_history
            )

            response = await self.llm.ainvoke(prompt)
            content = response.content

            result = self._parse_extraction_result(content)

            logger.info(f"槽位提取完成 - extracted: {len(result.extracted_slots)}, inferred: {len(result.inferred_slots)}, confidence: {result.confidence}")
            return result

        except Exception as e:
            logger.error(f"槽位提取失败 - error: {str(e)}")
            return SlotExtractionResult(
                extracted_slots={},
                inferred_slots={},
                confidence=0.0,
                needs_clarification=[],
                clarification_questions=["抱歉，我没有理解您的意思，请您重新表述。"]
            )

    def _build_extraction_prompt(
        self,
        user_input: str,
        current_block: str,
        known_slots: Dict[str, Any],
        conversation_history: Optional[List[str]] = None
    ) -> str:
        block_descriptions = {
            "plaintiff": """
当前业务块：原告信息
需要提取的槽位：
- plaintiff.name: 原告姓名
- plaintiff.gender: 性别（男/女）
- plaintiff.birthday: 出生日期（YYYY-MM-DD格式）
- plaintiff.ethnicity: 民族（如：汉族、回族等）
- plaintiff.work_unit: 工作单位
- plaintiff.job_title: 职位
- plaintiff.phone: 手机号码
- plaintiff.domicile: 户籍地址
- plaintiff.habitual_residence: 现住址
""",
            "agent": """
当前业务块：代理人信息
需要提取的槽位：
- agent.has_agent: 是否有委托代理人（true/false）
- agent.name: 代理人姓名
- agent.work_place: 代理人工作单位
- agent.job: 代理人职务
- agent.phone: 代理人电话
- agent.auth: 授权类型（一般/特别）
""",
            "service": """
当前业务块：送达地址
需要提取的槽位：
- service.address: 送达地址
- service.recipient: 收件人
- service.phone: 联系电话
- service.allow_electronic: 是否接受电子送达（true/false）
- service.wechat: 微信号
- service.mail: 电子邮箱
""",
            "defendant": """
当前业务块：被告信息
需要提取的槽位：
- defendant.name: 被告公司名称
- defendant.address: 公司地址
- defendant.Company_address: 公司注册地址
- defendant.legal_rep: 法定代表人
- defendant.job: 法定代表人职务
- defendant.phone: 法定代表人电话
- defendant.social_credit_code: 统一社会信用代码
- defendant.entity_type: 企业类型（如：有限责任公司、股份有限公司等）
- defendant.is_state_owned: 是否国有企业（true/false）
""",
            "claims": """
当前业务块：诉讼请求
需要提取的槽位：
- claims.salary.active: 是否主张工资（true/false）
- claims.salary.details: 工资详情描述
- claims.double_salary.active: 是否主张未签劳动合同双倍工资（true/false）
- claims.double_salary.details: 双倍工资详情描述
- claims.overtime.active: 是否主张加班费（true/false）
- claims.overtime.details: 加班费详情描述
- claims.annual_leave.active: 是否主张年休假工资（true/false）
- claims.annual_leave.details: 年休假工资详情描述
- claims.social_loss.active: 是否主张社保损失（true/false）
- claims.social_loss.details: 社保损失详情描述
- claims.termination_compensation.active: 是否主张经济补偿金（true/false）
- claims.termination_compensation.details: 经济补偿金详情描述
- claims.illegal_termination_damages.active: 是否主张违法解除劳动合同赔偿金（true/false）
- claims.illegal_termination_damages.details: 违法解除赔偿金详情描述
- claims.other_requests: 其他诉讼请求
- claims.litigation_cost_burden: 诉讼费用承担（默认：由被告承担）
""",
            "preservation": """
当前业务块：财产保全
需要提取的槽位：
- preservation.active: 是否申请财产保全（true/false）
- preservation.court: 保全法院
- preservation.document: 保全文书
""",
            "facts": """
当前业务块：事实与理由
需要提取的槽位：
- facts.contract_signing: 合同签订情况描述
- facts.performance_details: 劳动合同履行情况详情
- facts.termination_reason: 离职原因详情
- facts.work_injury: 工伤情况（如有）
- facts.arbitration_details: 劳动仲裁情况详情
- facts.is_migrant_worker: 是否农民工（true/false）
- facts.legal_basis: 法律依据
"""
        }

        known_slots_text = ""
        if known_slots:
            known_slots_text = "\n已知信息：\n"
            for key, value in known_slots.items():
                if value:
                    known_slots_text += f"- {key}: {value}\n"

        history_text = ""
        if conversation_history:
            history_text = "\n对话历史：\n"
            for i, msg in enumerate(conversation_history[-4:]):
                history_text += f"{i+1}. {msg}\n"

        prompt = f"""你是一个专业的法律文书信息提取专家。请从用户的自然语言中提取结构化信息。

{block_descriptions.get(current_block, "当前业务块：通用信息提取")}

{known_slots_text}

{history_text}

用户输入：{user_input}

## 提取任务
1. 识别用户输入中包含的所有槽位信息
2. 对于金额，提取数字和单位（元/月/年）
3. 对于日期，转换为标准格式（YYYY年MM月DD日）
4. 对于布尔值，使用true/false
5. 对于隐含信息，进行合理推断
6. 为每个提取的信息生成合理的置信度（0.0-1.0）

## 智能问题生成规则
- **重要**：首先检查"已知信息"，如果当前业务块的所有槽位都已填写，**不要**生成任何澄清问题
- 只有当确实缺失槽位时，才生成澄清问题
- **不要**为每个缺失槽位单独生成问题
- **要**将多个缺失槽位的信息合并成一个自然、友好的综合问题
- 使用口语化的表达，让用户感觉像是在对话
- 优先询问重要信息，次要信息可以后续补充
- 如果缺失的槽位较多，可以分成2-3个相关问题，但不要超过3个
- 问题的语气要自然，避免机械地列出"请告诉我A、B、C、D..."

## 智能问题示例

**示例0：所有槽位已填写**
- 已知信息：plaintiff.name=张三, plaintiff.gender=男, plaintiff.birthday=1990-01-01, ...
- ✅ 应该这样：clarification_questions = []（空数组，不要生成任何问题）

**示例1：原告信息缺失多个槽位**
- ❌ 不要这样：["请问您的性别是？", "请问您的出生日期是？", "请问您的民族是？", "请问您的工作单位是？", "请问您的职位是？"]
- ✅ 应该这样：["能介绍一下您的基本情况吗？比如您的性别、出生日期、民族，还有您的工作单位和职位。"]

**示例2：被告信息缺失**
- ❌ 不要这样：["请问被告公司的名称是？", "请问被告公司的地址是？", "请问被告公司的法定代表人是谁？"]
- ✅ 应该这样：["请告诉我被告公司的详细信息，包括公司名称、地址和法定代表人。"]

**示例3：诉讼请求缺失**
- ❌ 不要这样：["请问是否主张工资？", "请问是否主张加班费？", "请问是否主张经济补偿金？"]
- ✅ 应该这样：["关于您的诉讼请求，您希望主张哪些费用？比如工资、加班费、经济补偿金等。"]

**示例4：送达地址缺失**
- ❌ 不要这样：["请问法律文书的送达地址是？", "请问收件人是谁？", "请问收件人的联系电话是？"]
- ✅ 应该这样：["请提供法律文书的送达地址，包括地址、收件人和联系电话。"]

## 输出格式
请严格按照以下JSON格式输出，不要包含任何其他内容：

{{
  "extracted_slots": {{
    "plaintiff.name": "张三",
    "defendant.name": "XX科技有限公司"
  }},
  "inferred_slots": {{
    "facts.employment_duration": "3年2个月"
  }},
  "confidence": 0.85,
  "needs_clarification": ["性别"],
  "clarification_questions": ["请问您能告诉我一些关于您的基本信息吗？比如您的性别、出生日期、民族，还有您的工作单位和职位。"]
}}

**示例：所有槽位已填写**
{{
  "extracted_slots": {{}},
  "inferred_slots": {{}},
  "confidence": 1.0,
  "needs_clarification": [],
  "clarification_questions": []
}}

注意事项：
- 如果没有提取到任何信息，extracted_slots应为空对象 {{}}
- 如果没有推断信息，inferred_slots应为空对象 {{}}
- confidence应该是整体提取的置信度
- needs_clarification列出需要进一步确认的字段名
- clarification_questions只包含1-3个综合性的自然问题，不要为每个槽位单独生成问题
- 如果当前业务块的所有槽位都已填写，clarification_questions必须为空数组[]
"""

        return prompt

    def _parse_extraction_result(self, content: str) -> SlotExtractionResult:
        try:
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {
                    "extracted_slots": {},
                    "inferred_slots": {},
                    "confidence": 0.0,
                    "needs_clarification": [],
                    "clarification_questions": []
                }

            return SlotExtractionResult(
                extracted_slots=result.get("extracted_slots", {}),
                inferred_slots=result.get("inferred_slots", {}),
                confidence=result.get("confidence", 0.0),
                needs_clarification=result.get("needs_clarification", []),
                clarification_questions=result.get("clarification_questions", [])
            )
        except Exception as e:
            logger.error(f"解析提取结果失败 - error: {str(e)}")
            return SlotExtractionResult(
                extracted_slots={},
                inferred_slots={},
                confidence=0.0,
                needs_clarification=[],
                clarification_questions=[]
            )

    def _validate_slot_value(self, slot_name: str, value: Any) -> bool:
        """
        验证槽位值的有效性
        """
        if value is None or value == "":
            return False

        if "phone" in slot_name:
            phone_pattern = r'^1[3-9]\d{9}$'
            return bool(re.match(phone_pattern, str(value)))

        if "date" in slot_name or "birthday" in slot_name:
            date_pattern = r'^\d{4}-\d{2}-\d{2}$'
            return bool(re.match(date_pattern, str(value)))

        if "amount" in slot_name or "salary" in slot_name:
            try:
                float(str(value).replace(",", "").replace("元", ""))
                return True
            except ValueError:
                return False

        return True


_slot_extractor_instance = None


def get_slot_extractor() -> SlotExtractor:
    global _slot_extractor_instance
    if _slot_extractor_instance is None:
        _slot_extractor_instance = SlotExtractor()
    return _slot_extractor_instance
