from typing import List, Optional
from .state import ExtractedFacts, CaseInfo, LawInfo, LawDetail


class CyberJudgePrompts:
    """赛博判官专业提示词模板"""
    
    SYSTEM_PROMPT = """你是"赛博判官"，一个专业的法律AI助手，具有以下能力：

## 核心职责
1. **法律咨询**：解答各类法律问题，提供专业的法律意见
2. **案例分析**：分析相关案例，提取裁判要点和法律适用
3. **法规解读**：解读法律法规条文，解释法律含义和适用范围
4. **维权指导**：提供维权路径、程序和策略建议
5. **风险评估**：评估法律风险，给出预防建议

## 专业要求
- 严格遵守法律法规，维护法律尊严
- 保持客观、公正、中立的立场
- 引用法律条文时注明出处
- 对于复杂案件，建议咨询专业律师
- 不提供虚假信息或误导性建议
- 保护用户隐私和商业秘密

## 回答规范
1. 先分析问题核心，再给出解答
2. 引用相关法律条文作为依据
3. 结合案例说明法律适用
4. 给出明确的建议和操作指引
5. 提示可能存在的风险和注意事项

## 禁止行为
- 禁止编造法律条文或案例
- 禁止提供违法建议
- 禁止代替律师提供具体诉讼指导
- 禁止泄露用户隐私信息"""

    INTENT_ANALYSIS_PROMPT = """分析用户输入的意图，判断需要哪种法律服务。

## 用户输入
{user_input}

## 已提取的事实信息
{extracted_facts}

## 会话历史
{conversation_history}

## 意图类型说明
1. **legal_consultation**：一般法律咨询，询问法律条文、概念解释等
2. **case_analysis**：案例分析，需要检索相关案例进行参考
3. **law_inquiry**：法规查询，需要检索具体法律法规
4. **document_analysis**：文书分析，基于上传的文件进行分析
5. **rights_protection**：维权指导，需要综合分析并提供维权建议
6. **compensation_calc**：赔偿计算，需要计算赔偿金额
7. **procedure_guidance**：程序指导，说明法律程序和流程
8. **follow_up**：追问，需要结合上下文回答
9. **chitchat**：闲聊，不需要法律专业知识

请以JSON格式返回分析结果：
{{
    "intent_type": "意图类型",
    "confidence": 0.95,
    "sub_intents": ["次要意图"],
    "reasoning": "判断理由",
    "needs_case_search": true/false,
    "needs_law_search": true/false,
    "needs_law_detail": true/false,
    "needs_file_analysis": true/false
}}"""

    FACT_EXTRACTION_PROMPT = """从以下文本中提取关键法律事实。

## 文本内容
{text_content}

## 提取要求
请提取以下信息（如果存在）：
1. 当事人信息（原告、被告、第三人等）
2. 关键事件（事件经过、争议起因等）
3. 争议焦点（双方争议的核心问题）
4. 诉求主张（原告的诉讼请求或主张）
5. 关键日期（合同签订日、违约日、起诉日等）
6. 涉及金额（争议金额、赔偿金额等）
7. 相关地点（合同履行地、侵权地等）

请以JSON格式返回：
{{
    "parties": ["当事人列表"],
    "events": ["事件列表"],
    "disputes": ["争议焦点"],
    "claims": ["诉求列表"],
    "key_dates": ["关键日期"],
    "amounts": ["涉及金额"],
    "locations": ["相关地点"],
    "summary": "事实摘要（100字以内）"
}}"""

    KEYWORD_GENERATION_PROMPT = """根据用户问题和提取的事实，生成用于检索的关键词。

## 用户问题
{user_question}

## 提取的事实
{extracted_facts}

## 要求
1. 生成3-5个关键词或短语
2. 关键词应准确反映法律问题核心
3. 包含法律专业术语
4. 考虑同义词和相关概念

请以JSON格式返回：
{{
    "case_keywords": ["案例检索关键词"],
    "law_keywords": ["法规检索关键词"],
    "reasoning": "关键词生成理由"
}}"""

    CASE_ANALYSIS_PROMPT = """基于检索到的案例，分析用户问题并提供专业解答。

## 用户问题
{user_question}

## 提取的事实
{extracted_facts}

## 相关案例
{related_cases}

## 分析要求
1. 总结案例的裁判要点
2. 分析案例与用户问题的关联性
3. 提取可参考的法律适用规则
4. 给出专业建议

请提供详细的分析报告。"""

    LAW_ANALYSIS_PROMPT = """基于检索到的法律法规，解答用户问题。

## 用户问题
{user_question}

## 相关法律法规
{related_laws}

## 法规详情
{law_details}

## 解答要求
1. 引用相关法律条文
2. 解释法律含义和适用条件
3. 结合用户情况说明法律后果
4. 给出合规建议

请提供专业的法律解答。"""

    COMPREHENSIVE_ANALYSIS_PROMPT = """综合分析用户问题，提供全面的法律意见。

## 用户问题
{user_question}

## 提取的事实
{extracted_facts}

## 相关案例
{related_cases}

## 相关法律法规
{related_laws}

## 法规详情
{law_details}

## 分析要求
请提供一份综合法律分析报告，包括：

### 一、问题分析
分析用户面临的法律问题核心

### 二、法律依据
引用相关法律条文，说明法律适用

### 三、案例分析
参考相关案例，说明裁判规则

### 四、风险评估
评估可能的法律风险和后果

### 五、建议措施
给出具体的建议和操作指引

### 六、注意事项
提示需要注意的重要事项"""

    RIGHTS_PROTECTION_PROMPT = """基于用户情况，提供维权指导。

## 用户问题
{user_question}

## 提取的事实
{extracted_facts}

## 法律依据
{legal_basis}

## 维权指导要求
1. 明确维权路径（协商、调解、仲裁、诉讼等）
2. 说明维权程序和时限
3. 列举需要的证据材料
4. 提供维权策略建议
5. 提示可能的风险和成本

请提供详细的维权指导方案。"""

    COMPENSATION_CALC_PROMPT = """根据法律规定和事实情况，计算赔偿金额。

## 用户问题
{user_question}

## 提取的事实
{extracted_facts}

## 相关法律规定
{legal_basis}

## 计算要求
1. 列明计算依据和标准
2. 分项计算各项损失
3. 说明计算方法和公式
4. 给出计算结果范围
5. 提示影响赔偿的因素

请提供详细的赔偿计算分析。"""

    PROCEDURE_GUIDANCE_PROMPT = """提供法律程序指导。

## 用户问题
{user_question}

## 相关法律程序
{procedure_info}

## 指导要求
1. 说明程序流程和步骤
2. 列举需要的材料和文件
3. 提示时限和期限
4. 说明注意事项
5. 提供相关法律依据

请提供详细的程序指导。"""

    @staticmethod
    def format_extracted_facts(facts: Optional[ExtractedFacts]) -> str:
        if not facts:
            return "（未提取到事实信息）"
        
        parts = []
        if facts.get("summary"):
            parts.append(f"摘要：{facts['summary']}")
        if facts.get("parties"):
            parts.append(f"当事人：{', '.join(facts['parties'])}")
        if facts.get("events"):
            parts.append(f"事件：{'; '.join(facts['events'])}")
        if facts.get("disputes"):
            parts.append(f"争议焦点：{'; '.join(facts['disputes'])}")
        if facts.get("claims"):
            parts.append(f"诉求：{'; '.join(facts['claims'])}")
        if facts.get("key_dates"):
            parts.append(f"关键日期：{', '.join(facts['key_dates'])}")
        if facts.get("amounts"):
            parts.append(f"涉及金额：{', '.join(facts['amounts'])}")
        
        return "\n".join(parts) if parts else "（未提取到事实信息）"

    @staticmethod
    def format_cases(cases: List[CaseInfo]) -> str:
        if not cases:
            return "（未找到相关案例）"
        
        parts = []
        for i, case in enumerate(cases, 1):
            parts.append(f"案例{i}：{case.get('title', '未知标题')}")
            parts.append(f"  案号：{case.get('case_number', '未知')}")
            parts.append(f"  法院：{case.get('court', '未知')}")
            parts.append(f"  案由：{case.get('cause', '未知')}")
            parts.append(f"  裁判日期：{case.get('judgement_date', '未知')}")
            if case.get('content'):
                content = case['content'][:200] + "..." if len(case['content']) > 200 else case['content']
                parts.append(f"  内容摘要：{content}")
            parts.append("")
        
        return "\n".join(parts)

    @staticmethod
    def format_laws(laws: List[LawInfo]) -> str:
        if not laws:
            return "（未找到相关法规）"
        
        parts = []
        for i, law in enumerate(laws, 1):
            parts.append(f"法规{i}：{law.get('title', '未知标题')}")
            parts.append(f"  发布机关：{law.get('publisher', '未知')}")
            parts.append(f"  发布日期：{law.get('publish_date', '未知')}")
            parts.append(f"  时效性：{law.get('timeliness', '未知')}")
            parts.append(f"  法规ID：{law.get('law_id', '未知')}")
            parts.append("")
        
        return "\n".join(parts)

    @staticmethod
    def format_law_details(details: List[LawDetail]) -> str:
        if not details:
            return "（未获取法规详情）"
        
        parts = []
        for i, detail in enumerate(details, 1):
            parts.append(f"【{detail.get('title', '未知标题')}】")
            parts.append(f"发布机关：{detail.get('publisher', '未知')}")
            parts.append(f"时效性：{detail.get('timeliness', '未知')}")
            parts.append("")
            if detail.get('content'):
                parts.append(detail['content'])
            parts.append("")
            parts.append("-" * 50)
            parts.append("")
        
        return "\n".join(parts)
