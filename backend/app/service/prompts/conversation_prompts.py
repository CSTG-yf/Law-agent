"""
多轮对话提示词模板
集中管理法律助手多轮对话的所有提示词
"""


class ConversationPrompts:
    """对话提示词模板"""

    SYSTEM_PROMPT = """你是一个专业的法律AI助手，擅长回答各类法律问题。

你的职责：
1. 提供准确、专业的法律咨询
2. 解释相关法律条文和法规
3. 分析案例和法律风险
4. 给出合理的法律建议

注意事项：
- 对于复杂的法律问题，建议咨询专业律师
- 保持客观、中立的立场
- 不提供具体的法律诉讼指导
- 遵守法律法规和职业道德"""

    RAG_SYSTEM_PROMPT = """你是一个专业的法律AI助手，基于提供的法律文档回答问题。

你的职责：
1. 仔细阅读提供的参考文档
2. 基于文档内容回答问题
3. 引用相关的法律条文和案例

重要约束：
- 必须严格基于提供的文档回答问题
- 如果提供的参考文档为空或文档中没有相关信息，你必须明确说明"抱歉，我在知识库中没有找到相关的法律文档来回答这个问题"
- 严禁使用文档外的任何信息回答问题
- 严禁编造法律条文或案例
- 如果文档内容不足以回答问题，请明确说明文档内容的局限性

注意事项：
- 引用文档时要标注来源
- 保持客观、专业的态度"""

    @staticmethod
    def get_rag_user_prompt(query: str, context: str) -> str:
        """获取RAG用户提示词"""
        return f"""问题: {query}

参考文档:
{context}

请基于以上参考文档回答问题。"""

    @staticmethod
    def get_user_prompt(query: str) -> str:
        """获取普通用户提示词"""
        return query

    @staticmethod
    def format_context(documents: list) -> str:
        """格式化文档上下文"""
        context_parts = []
        for i, doc in enumerate(documents, 1):
            context_parts.append(f"文档{i}: {doc.page_content}")
        return "\n\n".join(context_parts)

    @staticmethod
    def get_context_with_sources(documents: list) -> str:
        """获取带来源的上下文"""
        context_parts = []
        for i, doc in enumerate(documents, 1):
            metadata = doc.metadata or {}
            source = metadata.get("source", "unknown")
            distance = metadata.get("distance", 0)
            context_parts.append(
                f"文档{i} (来源: {source}, 相似度: {distance:.3f}):\n{doc.page_content}"
            )
        return "\n\n".join(context_parts)


class ConversationSummaryPrompts:
    """对话摘要提示词"""

    SUMMARY_PROMPT = """请将以下对话历史压缩成一个简洁的摘要，保留关键信息：

对话历史：
{history}

摘要要求：
1. 提取关键问题和回答
2. 保留重要的上下文信息
3. 控制在{max_tokens}个token以内
4. 使用简洁的语言"""

    @staticmethod
    def get_summary_prompt(history: str, max_tokens: int = 500) -> str:
        """获取摘要提示词"""
        return ConversationSummaryPrompts.SUMMARY_PROMPT.format(
            history=history,
            max_tokens=max_tokens
        )


class ConversationAnalysisPrompts:
    """对话分析提示词"""

    INTENT_ANALYSIS = """分析以下用户消息的意图：

用户消息：{message}

可能的意图类型：
- 法律咨询：询问法律条文、法规、案例等
- 案例分析：要求分析具体案例
- 风险评估：询问法律风险
- 程序指导：询问法律程序
- 其他：其他类型的询问

请判断最可能的意图类型。"""

    @staticmethod
    def get_intent_prompt(message: str) -> str:
        """获取意图分析提示词"""
        return ConversationAnalysisPrompts.INTENT_ANALYSIS.format(message=message)


class ConversationResponsePrompts:
    """对话响应提示词"""

    ERROR_RESPONSE = "抱歉，我遇到了一些问题，请稍后再试。"
    NO_RAG_RESPONSE = "抱歉，我没有找到相关的法律文档来回答这个问题。"
    FALLBACK_RESPONSE = "这个问题比较复杂，建议您咨询专业律师获取更准确的建议。"

    @staticmethod
    def get_uncertainty_response(topic: str) -> str:
        """获取不确定性响应"""
        return f"关于{topic}，我建议您咨询专业律师以获取更准确的法律建议。"
