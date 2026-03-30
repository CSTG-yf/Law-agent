from typing import Dict, Any, Optional, List
from app.service.form_filling.prompts.block_descriptions import get_block_description


EXTRACTION_SYSTEM_PROMPT = """你是一个专业的法律文书信息提取专家。请从用户的自然语言中提取结构化信息。

{block_description}

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


def build_extraction_prompt(
    user_input: str,
    current_block: str,
    known_slots: Dict[str, Any],
    conversation_history: Optional[List[str]] = None
) -> str:
    block_description = get_block_description(current_block)

    known_slots_text = ""
    if known_slots:
        known_slots_text = "\n已知信息：\n"
        for key, value in known_slots.items():
            if value is not None:
                known_slots_text += f"- {key}: {value}\n"

    history_text = ""
    if conversation_history:
        history_text = "\n对话历史：\n"
        for i, msg in enumerate(conversation_history[-4:]):
            history_text += f"{i+1}. {msg}\n"

    return EXTRACTION_SYSTEM_PROMPT.format(
        block_description=block_description,
        known_slots_text=known_slots_text,
        history_text=history_text,
        user_input=user_input
    )
