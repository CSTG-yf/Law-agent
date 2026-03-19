from typing import List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.documents import Document
from app.service.agent.conversation_state import ConversationState


class ConversationManager:
    def __init__(self, max_history: int = 10):
        self.max_history = max_history

    def trim_history(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        if len(messages) <= self.max_history:
            return messages

        keep_system_messages = [msg for msg in messages if isinstance(msg, SystemMessage)]
        other_messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]

        trimmed_other = other_messages[-self.max_history:]
        return keep_system_messages + trimmed_other

    def add_message(self, state: ConversationState, message: BaseMessage) -> ConversationState:
        messages = state["messages"] + [message]
        trimmed_messages = self.trim_history(messages)

        return {
            **state,
            "messages": trimmed_messages
        }

    def get_conversation_summary(self, messages: List[BaseMessage], max_tokens: int = 500) -> str:
        if len(messages) == 0:
            return ""

        conversation_text = "\n".join([
            f"{msg.__class__.__name__}: {msg.content}"
            for msg in messages[-6:]
        ])

        if len(conversation_text) <= max_tokens:
            return conversation_text

        return conversation_text[:max_tokens] + "..."

    def should_summarize(self, messages: List[BaseMessage]) -> bool:
        return len(messages) > self.max_history * 2

    def create_summary_message(self, messages: List[BaseMessage]) -> SystemMessage:
        summary = self.get_conversation_summary(messages)
        return SystemMessage(content=f"对话历史摘要:\n{summary}")

    def compress_history(self, state: ConversationState) -> ConversationState:
        if not self.should_summarize(state["messages"]):
            return state

        summary_message = self.create_summary_message(state["messages"])

        recent_messages = state["messages"][-self.max_history:]
        compressed_messages = [summary_message] + recent_messages

        return {
            **state,
            "messages": compressed_messages
        }
