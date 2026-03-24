from typing import Literal, Optional, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from pydantic import BaseModel
import json
import re
from app.core.logger import get_logger

logger = get_logger("intent_classifier")


class IntentResult(BaseModel):
    intent: Literal["chitchat", "follow_up", "new_question"]
    confidence: float
    needs_retrieval: bool
    needs_rewrite: bool
    original_query: str
    reasoning: Optional[str] = None


INTENT_CLASSIFICATION_PROMPT = """你是一个意图识别专家。分析用户的查询意图。

会话历史：
{conversation_history}

当前用户输入：{current_query}

请判断用户意图属于以下哪一类：

1. **chitchat（闲聊）**：打招呼、感谢、简单问候等，不需要检索知识库
   示例："你好"、"谢谢"、"再见"、"你叫什么名字"、"你是谁"

2. **follow_up（追问）**：基于上一轮对话的追问，需要结合历史上下文进行改写
   示例："再回答一下我上一个问题"、"它具体指什么？"、"能详细说说吗？"、"有什么后果？"、"那如果...呢？"

3. **new_question（新问题）**：全新的独立问题，需要检索知识库
   示例："劳动合同法第39条规定了什么？"、"经济补偿金怎么计算？"、"离婚财产如何分割？"

请以JSON格式返回，不要包含任何其他内容：
{{"intent": "意图类型", "confidence": 0.95, "reasoning": "判断理由"}}
"""


class IntentClassifier:
    CHITCHAT_PATTERNS = [
        r"^(你好|您好|hi|hello|hey)[\s!！。.]*$",
        r"^(谢谢|感谢|多谢|thanks|thank you)[\s!！。.]*$",
        r"^(再见|拜拜|bye|goodbye)[\s!！。.]*$",
        r"^(你是谁|你叫什么|你的名字|介绍一下你自己)",
        r"^(早上好|下午好|晚上好|早安|晚安)",
    ]

    FOLLOW_UP_PATTERNS = [
        r"(再回答|重新回答|再说一遍|再解释)",
        r"(它|这|那个|这个)(具体)?(指|是|意思|含义)",
        r"(详细|具体|深入)(说说|解释|讲讲)",
        r"(有什么|会有)(后果|影响|结果)",
        r"(那如果|如果|假如|假设)",
        r"(为什么|怎么会|怎么可以)",
        r"(呢|吗)[？?。.]*$",
        r"^(继续|接着|然后)",
    ]

    def __init__(self, llm):
        self.llm = llm

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

    def _quick_classify(self, query: str) -> Optional[IntentResult]:
        query_lower = query.lower().strip()
        
        for pattern in self.CHITCHAT_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return IntentResult(
                    intent="chitchat",
                    confidence=0.95,
                    needs_retrieval=False,
                    needs_rewrite=False,
                    original_query=query,
                    reasoning="匹配闲聊模式"
                )
        
        for pattern in self.FOLLOW_UP_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return IntentResult(
                    intent="follow_up",
                    confidence=0.85,
                    needs_retrieval=True,
                    needs_rewrite=True,
                    original_query=query,
                    reasoning="匹配追问模式"
                )
        
        return None

    async def classify(
        self,
        current_query: str,
        conversation_history: List[BaseMessage]
    ) -> IntentResult:
        quick_result = self._quick_classify(current_query)
        if quick_result and quick_result.confidence >= 0.85:
            logger.info(f"快速意图识别 - intent: {quick_result.intent}, confidence: {quick_result.confidence}")
            return quick_result

        if not conversation_history or len(conversation_history) == 0:
            logger.info(f"无历史记录，默认为新问题 - query: {current_query[:50]}")
            return IntentResult(
                intent="new_question",
                confidence=0.9,
                needs_retrieval=True,
                needs_rewrite=False,
                original_query=current_query,
                reasoning="无历史记录，判断为新问题"
            )

        history_text = self._format_history(conversation_history)
        
        prompt = INTENT_CLASSIFICATION_PROMPT.format(
            conversation_history=history_text,
            current_query=current_query
        )

        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content
            
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {
                    "intent": "new_question",
                    "confidence": 0.5,
                    "reasoning": "无法解析LLM响应"
                }
        except Exception as e:
            logger.error(f"意图识别LLM调用失败: {str(e)}")
            result = {
                "intent": "new_question",
                "confidence": 0.5,
                "reasoning": f"LLM调用异常: {str(e)}"
            }

        intent = result.get("intent", "new_question")
        confidence = result.get("confidence", 0.5)
        
        needs_retrieval = intent != "chitchat"
        needs_rewrite = intent == "follow_up"

        logger.info(f"LLM意图识别完成 - intent: {intent}, confidence: {confidence}, needs_rewrite: {needs_rewrite}")

        return IntentResult(
            intent=intent,
            confidence=confidence,
            needs_retrieval=needs_retrieval,
            needs_rewrite=needs_rewrite,
            original_query=current_query,
            reasoning=result.get("reasoning")
        )
