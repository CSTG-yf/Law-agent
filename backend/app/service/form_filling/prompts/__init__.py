from app.service.form_filling.prompts.block_descriptions import BLOCK_DESCRIPTIONS, get_block_description
from app.service.form_filling.prompts.extraction_prompt import EXTRACTION_SYSTEM_PROMPT, build_extraction_prompt
from app.service.form_filling.prompts.conversation_prompts import (
    BLOCK_GREETINGS, BLOCK_COMPLETION_MESSAGES, SLOT_QUESTIONS, SLOT_CONFIRMATIONS,
    ALL_COMPLETE_MESSAGE,
    get_greeting, get_completion, get_slot_question, get_slot_confirmation
)
