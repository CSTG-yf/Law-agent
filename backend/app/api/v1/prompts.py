import re
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.schema.prompt_config import (
    PromptDetailItem, PromptListItem, PromptListData, PromptListResponse, PromptDetailResponse
)
from app.core.constants import HttpStatus
from app.core.logger import get_logger

router = APIRouter(prefix="/prompts", tags=["Prompts"])
logger = get_logger("prompts_api")


def _is_template(content: str) -> bool:
    return bool(re.search(r'\{[a-zA-Z_][a-zA-Z0-9_]*\}', content))


def _collect_all_prompts() -> list:
    from app.service.prompts.conversation_prompts import (
        ConversationPrompts, ConversationSummaryPrompts,
        ConversationAnalysisPrompts, ConversationResponsePrompts
    )
    from app.service.agent.intent_classifier import INTENT_CLASSIFICATION_PROMPT
    from app.service.agent.query_rewriter import QUERY_REWRITE_PROMPT
    from app.service.form_filling.prompts.extraction_prompt import EXTRACTION_SYSTEM_PROMPT
    from app.service.form_filling.prompts.block_descriptions import BLOCK_DESCRIPTIONS
    from app.service.form_filling.prompts.conversation_prompts import (
        BLOCK_GREETINGS, BLOCK_COMPLETION_MESSAGES, SLOT_QUESTIONS,
        SLOT_CONFIRMATIONS, ALL_COMPLETE_MESSAGE,
        DEFAULT_GREETING, DEFAULT_COMPLETION, DEFAULT_SLOT_QUESTION, DEFAULT_SLOT_CONFIRMATION
    )

    items = []

    items.append(PromptDetailItem(
        id="conversation.system_prompt",
        label="通用对话系统提示词",
        content=ConversationPrompts.SYSTEM_PROMPT,
        description="法律AI助手的基础系统提示词，定义助手角色和职责范围",
        tags=["系统提示词", "对话", "法律咨询"],
        category="conversation",
        is_template=False,
        source_file="backend/app/service/prompts/conversation_prompts.py"
    ))

    items.append(PromptDetailItem(
        id="conversation.rag_system_prompt",
        label="RAG对话系统提示词",
        content=ConversationPrompts.RAG_SYSTEM_PROMPT,
        description="基于知识库文档回答问题的系统提示词，约束模型严格基于文档回答",
        tags=["系统提示词", "RAG", "知识库", "对话"],
        category="conversation",
        is_template=False,
        source_file="backend/app/service/prompts/conversation_prompts.py"
    ))

    items.append(PromptDetailItem(
        id="conversation.rag_user_prompt",
        label="RAG用户提示词模板",
        content=ConversationPrompts.get_rag_user_prompt("{query}", "{context}"),
        description="RAG检索后组装用户问题的提示词模板，包含query和context占位符",
        tags=["用户提示词", "RAG", "知识库", "模板"],
        category="conversation",
        is_template=True,
        source_file="backend/app/service/prompts/conversation_prompts.py"
    ))

    items.append(PromptDetailItem(
        id="conversation.summary_prompt",
        label="对话摘要提示词模板",
        content=ConversationSummaryPrompts.SUMMARY_PROMPT,
        description="将对话历史压缩为简洁摘要的提示词模板，包含history和max_tokens占位符",
        tags=["摘要", "对话管理", "模板"],
        category="conversation",
        is_template=True,
        source_file="backend/app/service/prompts/conversation_prompts.py"
    ))

    items.append(PromptDetailItem(
        id="conversation.intent_analysis",
        label="意图分析提示词模板",
        content=ConversationAnalysisPrompts.INTENT_ANALYSIS,
        description="分析用户消息意图的提示词模板，支持chitchat/follow_up/new_question分类",
        tags=["意图识别", "对话管理", "模板"],
        category="conversation",
        is_template=True,
        source_file="backend/app/service/prompts/conversation_prompts.py"
    ))

    items.append(PromptDetailItem(
        id="conversation.error_response",
        label="错误响应文案",
        content=ConversationResponsePrompts.ERROR_RESPONSE,
        description="对话出错时的默认响应文案",
        tags=["响应文案", "错误处理"],
        category="conversation",
        is_template=False,
        source_file="backend/app/service/prompts/conversation_prompts.py"
    ))

    items.append(PromptDetailItem(
        id="conversation.no_rag_response",
        label="无RAG结果响应文案",
        content=ConversationResponsePrompts.NO_RAG_RESPONSE,
        description="知识库未检索到相关文档时的响应文案",
        tags=["响应文案", "RAG", "知识库"],
        category="conversation",
        is_template=False,
        source_file="backend/app/service/prompts/conversation_prompts.py"
    ))

    items.append(PromptDetailItem(
        id="conversation.fallback_response",
        label="兜底响应文案",
        content=ConversationResponsePrompts.FALLBACK_RESPONSE,
        description="无法回答时的兜底响应文案",
        tags=["响应文案", "兜底"],
        category="conversation",
        is_template=False,
        source_file="backend/app/service/prompts/conversation_prompts.py"
    ))

    items.append(PromptDetailItem(
        id="agent.intent_classification",
        label="意图分类提示词",
        content=INTENT_CLASSIFICATION_PROMPT,
        description="Agent意图分类核心提示词，分析用户查询属于闲聊/追问/新问题",
        tags=["意图识别", "Agent", "分类"],
        category="agent",
        is_template=True,
        source_file="backend/app/service/agent/intent_classifier.py"
    ))

    items.append(PromptDetailItem(
        id="agent.query_rewrite",
        label="查询改写提示词",
        content=QUERY_REWRITE_PROMPT,
        description="查询改写核心提示词，支持指代消解、省略补全、追问重述、意图提取",
        tags=["查询改写", "Agent", "RAG"],
        category="agent",
        is_template=True,
        source_file="backend/app/service/agent/query_rewriter.py"
    ))

    items.append(PromptDetailItem(
        id="form_filling.extraction_system_prompt",
        label="信息提取系统提示词",
        content=EXTRACTION_SYSTEM_PROMPT,
        description="表单填写核心提示词，从用户自然语言中提取结构化信息并生成智能追问",
        tags=["系统提示词", "表单填写", "信息提取", "模板"],
        category="form_filling",
        is_template=True,
        source_file="backend/app/service/form_filling/prompts/extraction_prompt.py"
    ))

    block_label_map = {
        "plaintiff": "原告信息",
        "agent": "代理人信息",
        "service": "送达地址",
        "defendant": "被告信息",
        "claims": "诉讼请求",
        "preservation": "财产保全",
        "facts": "事实与理由"
    }

    for block_id, desc in BLOCK_DESCRIPTIONS.items():
        items.append(PromptDetailItem(
            id=f"form_filling.block_description.{block_id}",
            label=f"业务块描述 - {block_label_map.get(block_id, block_id)}",
            content=desc.strip(),
            description=f"{block_label_map.get(block_id, block_id)}业务块的槽位定义和提取规则描述",
            tags=["表单填写", "业务块描述", block_label_map.get(block_id, block_id)],
            category="form_filling",
            is_template=False,
            source_file="backend/app/service/form_filling/prompts/block_descriptions.py"
        ))

    items.append(PromptDetailItem(
        id="form_filling.block_greetings",
        label="业务块引导语",
        content="\n".join(f"- {k}: {v}" for k, v in BLOCK_GREETINGS.items()),
        description="每个业务块开始时的引导语，用于引导用户填写对应信息",
        tags=["表单填写", "引导语", "对话"],
        category="form_filling",
        is_template=False,
        source_file="backend/app/service/form_filling/prompts/conversation_prompts.py"
    ))

    items.append(PromptDetailItem(
        id="form_filling.block_completion_messages",
        label="业务块完成提示语",
        content="\n".join(f"- {k}: {v}" for k, v in BLOCK_COMPLETION_MESSAGES.items()),
        description="每个业务块填写完成后的确认提示语",
        tags=["表单填写", "完成提示", "对话"],
        category="form_filling",
        is_template=False,
        source_file="backend/app/service/form_filling/prompts/conversation_prompts.py"
    ))

    items.append(PromptDetailItem(
        id="form_filling.slot_questions",
        label="槽位追问问题",
        content="\n".join(f"- {k}: {v}" for k, v in SLOT_QUESTIONS.items()),
        description="每个槽位对应的追问问题，用于引导用户补充缺失信息",
        tags=["表单填写", "槽位追问", "对话"],
        category="form_filling",
        is_template=False,
        source_file="backend/app/service/form_filling/prompts/conversation_prompts.py"
    ))

    items.append(PromptDetailItem(
        id="form_filling.slot_confirmations",
        label="槽位确认问题",
        content="\n".join(f"- {k}: {v}" for k, v in SLOT_CONFIRMATIONS.items()),
        description="关键槽位的确认问题模板，包含{value}占位符",
        tags=["表单填写", "槽位确认", "对话", "模板"],
        category="form_filling",
        is_template=True,
        source_file="backend/app/service/form_filling/prompts/conversation_prompts.py"
    ))

    items.append(PromptDetailItem(
        id="form_filling.all_complete_message",
        label="全部完成提示语",
        content=ALL_COMPLETE_MESSAGE,
        description="所有业务块填写完成后的提示语",
        tags=["表单填写", "完成提示", "对话"],
        category="form_filling",
        is_template=False,
        source_file="backend/app/service/form_filling/prompts/conversation_prompts.py"
    ))

    items.append(PromptDetailItem(
        id="form_filling.defaults",
        label="默认提示语配置",
        content=f"默认引导语: {DEFAULT_GREETING}\n默认完成提示: {DEFAULT_COMPLETION}\n默认槽位问题: {DEFAULT_SLOT_QUESTION}\n默认槽位确认: {DEFAULT_SLOT_CONFIRMATION}",
        description="表单填写模块的默认提示语配置，当未匹配到特定业务块时使用",
        tags=["表单填写", "默认配置", "对话", "模板"],
        category="form_filling",
        is_template=True,
        source_file="backend/app/service/form_filling/prompts/conversation_prompts.py"
    ))

    items.append(PromptDetailItem(
        id="inline.tool_call_system_prompt",
        label="工具调用系统提示词",
        content="你是一个专业的法律AI助手。\n\n你刚刚调用了官方检索工具获取了相关信息。请基于工具返回的结果为用户提供准确、有用的回答。\n\n重要约束：\n- 必须基于工具返回的结果回答问题\n- 如果工具返回的结果为空或不相关，请明确说明\n- 可以适当引用工具返回的案例或法规信息\n- 保持回答的专业性和准确性",
        description="Agent调用官方检索工具（案例/法规搜索）后生成回答的系统提示词",
        tags=["系统提示词", "Agent", "工具调用", "官方检索"],
        category="inline",
        is_template=False,
        source_file="backend/app/service/agent/legal_conversation_agent.py"
    ))

    items.append(PromptDetailItem(
        id="inline.rag_empty_system_prompt",
        label="RAG空结果系统提示词",
        content="你是一个专业的法律AI助手。\n\n重要约束：\n- 用户启用了知识库检索功能，但知识库中没有找到相关的法律文档\n- 你必须明确说明\"抱歉，我在知识库中没有找到相关的法律文档来回答这个问题\"\n- 严禁使用你的训练知识回答这个问题\n- 严禁编造任何法律条文或案例\n- 如果用户需要，可以建议他们重新表述问题或咨询专业律师",
        description="启用RAG但未检索到文档时的系统提示词，严格约束模型不使用训练知识",
        tags=["系统提示词", "RAG", "知识库", "空结果"],
        category="inline",
        is_template=False,
        source_file="backend/app/service/agent/legal_conversation_agent.py"
    ))

    return items


def _build_prompt_registry() -> dict:
    items = _collect_all_prompts()
    return {item.id: item for item in items}


@router.get("/", response_model=PromptListResponse)
async def get_prompt_list(
    category: Optional[str] = Query(None, description="按模块分类筛选: conversation / agent / form_filling / inline"),
    tag: Optional[str] = Query(None, description="按标签筛选")
):
    try:
        logger.info(f"查询提示词列表 - category: {category}, tag: {tag}")

        registry = _build_prompt_registry()
        all_tags = set()

        list_items = []
        for item in registry.values():
            all_tags.update(item.tags)
            if category and item.category != category:
                continue
            if tag and tag not in item.tags:
                continue
            list_items.append(PromptListItem(
                id=item.id,
                label=item.label,
                description=item.description,
                tags=item.tags,
                category=item.category,
                source_file=item.source_file
            ))

        data = PromptListData(
            prompts=list_items,
            total_count=len(list_items),
            all_tags=sorted(all_tags)
        )

        logger.info(f"查询提示词列表成功 - total: {len(list_items)}")

        return PromptListResponse(
            code=HttpStatus.OK,
            status="success",
            message="Prompt list retrieved successfully",
            data=data
        )

    except Exception as e:
        logger.error(f"查询提示词列表失败 - error: {str(e)}")
        return PromptListResponse(
            code=HttpStatus.INTERNAL_SERVER_ERROR,
            status="error",
            message=f"Failed to retrieve prompt list: {str(e)}",
            data=None
        )


@router.get("/{prompt_id}", response_model=PromptDetailResponse)
async def get_prompt_detail(prompt_id: str):
    try:
        logger.info(f"查询提示词详情 - prompt_id: {prompt_id}")

        registry = _build_prompt_registry()

        if prompt_id not in registry:
            logger.warning(f"提示词不存在 - prompt_id: {prompt_id}")
            return PromptDetailResponse(
                code=HttpStatus.NOT_FOUND,
                status="error",
                message=f"Prompt not found: {prompt_id}",
                data=None
            )

        item = registry[prompt_id]

        logger.info(f"查询提示词详情成功 - prompt_id: {prompt_id}, label: {item.label}")

        return PromptDetailResponse(
            code=HttpStatus.OK,
            status="success",
            message="Prompt detail retrieved successfully",
            data=item
        )

    except Exception as e:
        logger.error(f"查询提示词详情失败 - error: {str(e)}")
        return PromptDetailResponse(
            code=HttpStatus.INTERNAL_SERVER_ERROR,
            status="error",
            message=f"Failed to retrieve prompt detail: {str(e)}",
            data=None
        )
