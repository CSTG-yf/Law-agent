from typing import List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from pydantic import BaseModel
import json
import re
from app.core.logger import get_logger

logger = get_logger("query_rewriter")


class RewrittenQuery(BaseModel):
    original_query: str
    rewritten_query: str
    rewrite_type: str
    context_used: List[str] = []


QUERY_REWRITE_PROMPT = """你是一个查询改写专家。根据对话历史，改写用户的当前查询，使其成为一个完整、独立的问题。

对话历史：
{conversation_history}

当前用户查询：{current_query}

改写规则：
1. **指代消解**：将代词（它、这、那个、这个等）替换为具体实体
   示例："它是什么？" → "劳动合同法第39条是什么？"

2. **省略补全**：补全省略的主语、宾语
   示例："有什么后果？" → "违反劳动合同法第39条有什么后果？"

3. **追问重述**：将追问转换为完整问题
   示例："再回答一下我上一个问题" → 提取上一轮的完整问题

4. **意图提取**：从历史中提取"待解决意图"
   如果上一轮回答不完整或用户不满意，提取用户真正想问的问题

重要约束：
- 改写后的问题必须是完整、独立、可理解的
- 不要添加原问题中没有的信息
- 如果当前问题已经是完整的，可以保持不变

请以JSON格式返回，不要包含任何其他内容：
{{"rewritten_query": "改写后的完整查询", "rewrite_type": "指代消解/省略补全/追问重述/意图提取/无需改写", "context_used": ["使用的历史上下文片段"]}}
"""


class QueryRewriter:
    FOLLOW_UP_KEYWORDS = [
        "再回答", "重新回答", "再说一遍", "再解释",
        "继续", "接着", "详细", "具体", "深入"
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
            content = msg.content[:300] if len(msg.content) > 300 else msg.content
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)

    def _extract_last_question(self, messages: List[BaseMessage]) -> Optional[str]:
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return msg.content
        return None

    def _extract_topic_from_response(self, messages: List[BaseMessage]) -> Optional[str]:
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                content = msg.content
                patterns = [
                    r"第[一二三四五六七八九十百]+条",
                    r"第\d+条",
                    r"[《][^》]+[》]",
                    r"[^，。！？]{2,20}(法|条例|规定|办法)",
                ]
                for pattern in patterns:
                    match = re.search(pattern, content)
                    if match:
                        return match.group()
        return None

    async def rewrite(
        self,
        current_query: str,
        conversation_history: List[BaseMessage]
    ) -> RewrittenQuery:
        if not conversation_history or len(conversation_history) == 0:
            logger.info(f"无历史记录，无需改写 - query: {current_query[:50]}")
            return RewrittenQuery(
                original_query=current_query,
                rewritten_query=current_query,
                rewrite_type="无需改写",
                context_used=[]
            )

        if any(kw in current_query for kw in self.FOLLOW_UP_KEYWORDS):
            last_question = self._extract_last_question(conversation_history)
            if last_question:
                logger.info(f"追问重述 - 提取上一轮问题: {last_question[:50]}")
                return RewrittenQuery(
                    original_query=current_query,
                    rewritten_query=last_question,
                    rewrite_type="追问重述",
                    context_used=[last_question]
                )

        history_text = self._format_history(conversation_history)
        
        prompt = QUERY_REWRITE_PROMPT.format(
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
                    "rewritten_query": current_query,
                    "rewrite_type": "无需改写",
                    "context_used": []
                }
        except Exception as e:
            logger.error(f"Query改写LLM调用失败: {str(e)}")
            result = {
                "rewritten_query": current_query,
                "rewrite_type": "无需改写",
                "context_used": []
            }

        rewritten_query = result.get("rewritten_query", current_query)
        rewrite_type = result.get("rewrite_type", "无需改写")
        context_used = result.get("context_used", [])

        if rewritten_query == current_query:
            rewrite_type = "无需改写"

        logger.info(f"Query改写完成 - type: {rewrite_type}, original: {current_query[:30]}, rewritten: {rewritten_query[:30]}")

        return RewrittenQuery(
            original_query=current_query,
            rewritten_query=rewritten_query,
            rewrite_type=rewrite_type,
            context_used=context_used if isinstance(context_used, list) else []
        )

    async def optimize(self, query: str) -> RewrittenQuery:
        query = query.strip()
        
        if len(query) < 5:
            return RewrittenQuery(
                original_query=query,
                rewritten_query=query,
                rewrite_type="无需改写",
                context_used=[]
            )

        optimized = query
        
        if not optimized.endswith("？") and not optimized.endswith("?"):
            if any(kw in optimized for kw in ["什么", "怎么", "如何", "为什么", "哪些", "是否", "能否", "可以"]):
                optimized = optimized + "？"

        if optimized == query:
            logger.info(f"Query优化完成 - 无需优化: {query[:50]}")
            return RewrittenQuery(
                original_query=query,
                rewritten_query=query,
                rewrite_type="无需改写",
                context_used=[]
            )

        logger.info(f"Query优化完成 - original: {query[:30]}, optimized: {optimized[:30]}")
        return RewrittenQuery(
            original_query=query,
            rewritten_query=optimized,
            rewrite_type="简单优化",
            context_used=[]
        )
