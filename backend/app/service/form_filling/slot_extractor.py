from typing import Dict, List, Any, Optional
from langchain_openai import ChatOpenAI
from app.schema.form_filling import SlotExtractionResult
from app.core.config import settings
from app.core.logger import get_logger
from app.service.form_filling.prompts.extraction_prompt import build_extraction_prompt
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
        try:
            logger.info(f"开始槽位提取 - current_block: {current_block}, user_input: {user_input[:100]}")

            prompt = build_extraction_prompt(
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
