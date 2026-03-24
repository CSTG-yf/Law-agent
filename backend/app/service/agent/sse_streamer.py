import json
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, List
from fastapi.responses import StreamingResponse
from langchain_core.messages import BaseMessage, AIMessage


class SSEStreamer:
    def __init__(self):
        pass

    @staticmethod
    async def stream_agent_response(
        graph,
        state: Dict[str, Any],
        config: Dict[str, Any],
        message_id: Optional[str] = None,
        session_id: Optional[str] = None,
        role: str = "assistant",
        sources: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[str, None]:
        if message_id:
            yield SSEStreamer._format_sse(
                type="metadata",
                data={
                    "message_id": message_id,
                    "session_id": session_id,
                    "role": role
                }
            )

        async for event in graph.astream_events(
            state,
            config=config,
            version="v2"
        ):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    yield SSEStreamer._format_sse(
                        type="token",
                        data={"content": chunk.content}
                    )

            elif event["event"] == "on_tool_start":
                yield SSEStreamer._format_sse(
                    type="tool_start",
                    data={
                        "tool": event["name"],
                        "input": event["data"].get("input", {})
                    }
                )

            elif event["event"] == "on_tool_end":
                yield SSEStreamer._format_sse(
                    type="tool_end",
                    data={
                        "tool": event["name"],
                        "output": str(event["data"].get("output", ""))[:500]
                    }
                )

            elif event["event"] == "on_chain_end":
                if "generate" in event.get("name", ""):
                    messages = event["data"].get("output", {}).get("messages", [])
                    if messages:
                        last_message = messages[-1]
                        if isinstance(last_message, AIMessage):
                            yield SSEStreamer._format_sse(
                                type="complete",
                                data={
                                    "content": last_message.content,
                                    "message_id": getattr(last_message, "id", "")
                                }
                            )

        if sources:
            yield SSEStreamer._format_sse(
                type="sources",
                data={"sources": sources}
            )

        yield SSEStreamer._format_sse(
            type="done",
            data={}
        )

    @staticmethod
    async def stream_simple_response(
        generator: AsyncGenerator[str, None]
    ) -> AsyncGenerator[str, None]:
        async for chunk in generator:
            yield SSEStreamer._format_sse(
                type="token",
                data={"content": chunk}
            )

        yield SSEStreamer._format_sse(
            type="done",
            data={}
        )

    @staticmethod
    def _format_sse(type: str, data: Dict[str, Any]) -> str:
        return f"event: {type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


    @staticmethod
    def create_streaming_response(
        generator: AsyncGenerator[str, None]
    ) -> StreamingResponse:
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )


class StreamingResponseBuilder:
    def __init__(self):
        self.streamer = SSEStreamer()

    async def build_conversation_stream(
        self,
        graph,
        state: Dict[str, Any],
        config: Dict[str, Any],
        message_id: Optional[str] = None,
        session_id: Optional[str] = None,
        role: str = "assistant",
        sources: Optional[List[Dict[str, Any]]] = None
    ) -> StreamingResponse:
        generator = self.streamer.stream_agent_response(
            graph,
            state,
            config,
            message_id,
            session_id,
            role,
            sources
        )
        return SSEStreamer.create_streaming_response(generator)

    async def build_simple_stream(
        self,
        text_generator: AsyncGenerator[str, None]
    ) -> StreamingResponse:
        generator = self.streamer.stream_simple_response(text_generator)
        return SSEStreamer.create_streaming_response(generator)


async def mock_stream_generator(text: str) -> AsyncGenerator[str, None]:
    words = text.split()
    for word in words:
        yield word + " "
        await asyncio.sleep(0.05)
