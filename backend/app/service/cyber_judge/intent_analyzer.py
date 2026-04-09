from typing import List, Optional, Literal
from langchain_core.messages import BaseMessage, HumanMessage
from pydantic import BaseModel
import json
import re
from app.core.logger import get_logger
from .state import IntentInfo, ExtractedFacts
from .prompts import CyberJudgePrompts

logger = get_logger("intent_analyzer")

IntentType = Literal[
    "legal_consultation",
    "case_analysis", 
    "law_inquiry",
    "document_analysis",
    "rights_protection",
    "compensation_calc",
    "procedure_guidance",
    "follow_up",
    "chitchat"
]


class IntentResult(BaseModel):
    intent_type: IntentType
    confidence: float
    sub_intents: List[str] = []
    reasoning: str = ""
    needs_case_search: bool = False
    needs_law_search: bool = False
    needs_law_detail: bool = False
    needs_file_analysis: bool = False


INTENT_PATTERNS = {
    "chitchat": [
        r"^(你好|您好|hi|hello|hey)[\s!！。.]*$",
        r"^(谢谢|感谢|多谢|thanks|thank you)[\s!！。.]*$",
        r"^(再见|拜拜|bye|goodbye)[\s!！。.]*$",
        r"^(你是谁|你叫什么|你的名字|介绍一下你自己)",
        r"^(早上好|下午好|晚上好|早安|晚安)",
    ],
    "case_analysis": [
        r"(类似|相似|相关).*(案例|判决|裁定)",
        r"(有没有|有没有).*(案例|判决)",
        r"(案例|判决).*(参考|借鉴)",
        r"(怎么判|判决结果|裁判结果)",
        r"(法院|法官).*(怎么|如何).*(认定|判决)",
    ],
    "law_inquiry": [
        r"(法律规定|法律条文|法条)",
        r"(根据|依据|按照).*(法律|法规)",
        r"(什么|哪些).*(法律|法规|规定)",
        r"(有没有|是否).*(法律|法规)",
        r"(合法|违法|违规)",
    ],
    "rights_protection": [
        r"(维权|维护权益|保护权益)",
        r"(怎么办|如何处理|怎么处理)",
        r"(投诉|举报|申诉)",
        r"(仲裁|诉讼|起诉)",
        r"(怎么维权|如何维权)",
    ],
    "compensation_calc": [
        r"(赔偿|补偿|赔付).*(多少|怎么算|如何计算)",
        r"(计算|算).*(赔偿|补偿|金额)",
        r"(能赔|可以赔|应该赔).*(多少)",
        r"(经济补偿|经济赔偿)",
        r"(违约金|损失赔偿)",
    ],
    "procedure_guidance": [
        r"(程序|流程|步骤)",
        r"(怎么走|如何走).*(程序|流程)",
        r"(需要|要).*(什么|哪些).*(材料|手续)",
        r"(起诉|立案|上诉).*(程序|流程)",
        r"(仲裁|调解).*(程序|流程)",
    ],
    "document_analysis": [
        r"(分析|解读|解释).*(合同|协议|文件|文书)",
        r"(这个|这份).*(合同|协议|文件)",
        r"(看|审查|审核).*(合同|协议)",
        r"(条款|约定).*(什么意思|如何理解)",
    ],
    "follow_up": [
        r"(再回答|重新回答|再说一遍|再解释)",
        r"(它|这|那个|这个)(具体)?(指|是|意思|含义)",
        r"(详细|具体|深入)(说说|解释|讲讲)",
        r"(有什么|会有)(后果|影响|结果)",
        r"(那如果|如果|假如|假设)",
        r"(呢|吗)[？?。.]*$",
        r"^(继续|接着|然后)",
    ],
}


class IntentAnalyzer:
    """赛博判官意图识别增强模块"""
    
    def __init__(self, llm):
        self.llm = llm
        self.patterns = INTENT_PATTERNS

    def _quick_classify(self, query: str, has_files: bool = False) -> Optional[IntentResult]:
        query_lower = query.lower().strip()
        
        for pattern in self.patterns.get("chitchat", []):
            if re.search(pattern, query_lower, re.IGNORECASE):
                return IntentResult(
                    intent_type="chitchat",
                    confidence=0.95,
                    reasoning="匹配闲聊模式",
                    needs_case_search=False,
                    needs_law_search=False,
                    needs_law_detail=False,
                    needs_file_analysis=False
                )
        
        if has_files:
            return IntentResult(
                intent_type="document_analysis",
                confidence=0.90,
                reasoning="用户上传了文件，判定为文书分析",
                needs_case_search=True,
                needs_law_search=True,
                needs_law_detail=True,
                needs_file_analysis=True
            )
        
        for intent_type, patterns in self.patterns.items():
            if intent_type == "chitchat":
                continue
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    needs_case = intent_type in ["case_analysis", "rights_protection", "compensation_calc"]
                    needs_law = intent_type in ["law_inquiry", "rights_protection", "compensation_calc", "procedure_guidance"]
                    needs_detail = intent_type in ["law_inquiry", "rights_protection", "compensation_calc"]
                    
                    return IntentResult(
                        intent_type=intent_type,
                        confidence=0.85,
                        reasoning=f"匹配{intent_type}模式",
                        needs_case_search=needs_case,
                        needs_law_search=needs_law,
                        needs_law_detail=needs_detail,
                        needs_file_analysis=False
                    )
        
        return None

    def _format_history(self, messages: List[BaseMessage], max_turns: int = 3) -> str:
        if not messages:
            return "（无历史记录）"
        
        recent = messages[-max_turns * 2:] if len(messages) > max_turns * 2 else messages
        formatted = []
        for msg in recent:
            role = "用户" if isinstance(msg, HumanMessage) else "助手"
            content = msg.content[:200] if len(msg.content) > 200 else msg.content
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)

    async def analyze(
        self,
        current_query: str,
        conversation_history: List[BaseMessage],
        extracted_facts: Optional[ExtractedFacts] = None,
        has_files: bool = False
    ) -> IntentResult:
        quick_result = self._quick_classify(current_query, has_files)
        if quick_result and quick_result.confidence >= 0.85:
            logger.info(f"快速意图识别 - intent: {quick_result.intent_type}, confidence: {quick_result.confidence}")
            return quick_result

        history_text = self._format_history(conversation_history)
        facts_text = CyberJudgePrompts.format_extracted_facts(extracted_facts)
        
        prompt = CyberJudgePrompts.INTENT_ANALYSIS_PROMPT.format(
            user_input=current_query,
            extracted_facts=facts_text,
            conversation_history=history_text
        )

        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content
            
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {
                    "intent_type": "legal_consultation",
                    "confidence": 0.5,
                    "reasoning": "无法解析LLM响应"
                }
        except Exception as e:
            logger.error(f"意图识别LLM调用失败: {str(e)}")
            result = {
                "intent_type": "legal_consultation",
                "confidence": 0.5,
                "reasoning": f"LLM调用异常: {str(e)}"
            }

        intent_type = result.get("intent_type", "legal_consultation")
        confidence = result.get("confidence", 0.5)
        
        default_needs = {
            "legal_consultation": (False, True, True, False),
            "case_analysis": (True, True, True, False),
            "law_inquiry": (False, True, True, False),
            "document_analysis": (True, True, True, True),
            "rights_protection": (True, True, True, False),
            "compensation_calc": (True, True, True, False),
            "procedure_guidance": (False, True, True, False),
            "follow_up": (True, True, True, False),
            "chitchat": (False, False, False, False),
        }
        
        needs = default_needs.get(intent_type, (False, True, True, False))

        logger.info(f"LLM意图识别完成 - intent: {intent_type}, confidence: {confidence}")

        return IntentResult(
            intent_type=intent_type,
            confidence=confidence,
            sub_intents=result.get("sub_intents", []),
            reasoning=result.get("reasoning", ""),
            needs_case_search=result.get("needs_case_search", needs[0]),
            needs_law_search=result.get("needs_law_search", needs[1]),
            needs_law_detail=result.get("needs_law_detail", needs[2]),
            needs_file_analysis=result.get("needs_file_analysis", needs[3])
        )

    def to_intent_info(self, result: IntentResult) -> IntentInfo:
        return IntentInfo(
            intent_type=result.intent_type,
            confidence=result.confidence,
            sub_intents=result.sub_intents,
            reasoning=result.reasoning,
            needs_case_search=result.needs_case_search,
            needs_law_search=result.needs_law_search,
            needs_law_detail=result.needs_law_detail,
            needs_file_analysis=result.needs_file_analysis
        )
