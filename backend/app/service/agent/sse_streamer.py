import json
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, List
from fastapi.responses import StreamingResponse
from langchain_core.messages import BaseMessage, AIMessage


class SSEStreamer:
    GENERATE_NODE_NAMES = {"generate", "agent", "chat", "llm"}
    SKIP_NODE_NAMES = {
        "intent_classifier", "query_rewriter", "intent", "rewrite", "classify", 
        "retrieval_pipeline", "keyword_extraction", "graph_retriever", "entity_extractor",
        "pre_retriever", "reranker", "hybrid_retriever", "rag_retriever"
    }

    def __init__(self):
        pass

    @staticmethod
    def _should_stream_token(event: Dict[str, Any], in_generate_phase: bool) -> bool:
        if in_generate_phase:
            return True
        
        return False

    @staticmethod
    async def stream_agent_response(
        graph,
        state: Dict[str, Any],
        config: Dict[str, Any],
        message_id: Optional[str] = None,
        session_id: Optional[str] = None,
        role: str = "assistant",
        sources: Optional[List[Dict[str, Any]]] = None,
        retrieval_metadata: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None,
        user_message: Optional[str] = None,
        title_generator: Optional[callable] = None,
        completion_handler: Optional[callable] = None,
        agent: Optional[Any] = None
    ) -> AsyncGenerator[str, None]:
        if message_id:
            metadata_data = {
                "message_id": message_id,
                "session_id": session_id,
                "role": role
            }
            if title:
                metadata_data["title"] = title
            yield SSEStreamer._format_sse(
                type="metadata",
                data=metadata_data
            )

        assistant_content = ""
        final_ai_content = ""
        in_generate_phase = False
        collected_sources = []
        collected_metadata = None
        
        async for event in graph.astream_events(
            state,
            config=config,
            version="v2"
        ):
            if event["event"] == "on_chain_start":
                event_name = event.get("name", "").lower()
                if "generate" in event_name:
                    in_generate_phase = True
            
            elif event["event"] == "on_chain_end":
                event_name = event.get("name", "").lower()
                if "retrieve" in event_name:
                    output = event["data"].get("output", {})
                    if output and isinstance(output, dict):
                        context = output.get("context", [])
                        if context:
                            for doc in context:
                                if hasattr(doc, "page_content"):
                                    collected_sources.append({
                                        "content": doc.page_content[:200],
                                        "metadata": getattr(doc, "metadata", {})
                                    })
                        metadata = output.get("retrieval_metadata")
                        if metadata:
                            collected_metadata = metadata
                
                if "generate" in event_name:
                    in_generate_phase = False
                    messages = event["data"].get("output", {}).get("messages", [])
                    if messages:
                        last_message = messages[-1]
                        if isinstance(last_message, AIMessage):
                            final_ai_content = last_message.content or ""
                            yield SSEStreamer._format_sse(
                                type="complete",
                                data={
                                    "content": final_ai_content,
                                    "message_id": getattr(last_message, "id", "")
                                }
                            )

            elif event["event"] == "on_chat_model_stream":
                if not SSEStreamer._should_stream_token(event, in_generate_phase):
                    continue
                    
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    assistant_content += chunk.content
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

        if collected_sources:
            yield SSEStreamer._format_sse(
                type="sources",
                data={"sources": collected_sources}
            )

        if collected_metadata:
            yield SSEStreamer._format_sse(
                type="intent",
                data={
                    "intent": collected_metadata.get("intent"),
                    "rewritten_query": collected_metadata.get("rewritten_query"),
                    "original_query": collected_metadata.get("original_query"),
                    "rewrite_type": collected_metadata.get("rewrite_type"),
                    "intent_confidence": collected_metadata.get("intent_confidence")
                }
            )

        generated_title = title
        completed_content = assistant_content or final_ai_content

        if title_generator and user_message and completed_content and title is None:
            try:
                generated_title = await title_generator(user_message, completed_content)
                yield SSEStreamer._format_sse(
                    type="title",
                    data={"title": generated_title}
                )
            except Exception:
                generated_title = title

        if completion_handler and user_message and completed_content:
            await completion_handler(
                user_message=user_message,
                assistant_message=completed_content,
                collected_sources=collected_sources,
                retrieval_metadata=collected_metadata,
                title=generated_title
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
        sources: Optional[List[Dict[str, Any]]] = None,
        retrieval_metadata: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None,
        user_message: Optional[str] = None,
        title_generator: Optional[callable] = None,
        completion_handler: Optional[callable] = None,
        agent: Optional[Any] = None
    ) -> StreamingResponse:
        generator = self.streamer.stream_agent_response(
            graph,
            state,
            config,
            message_id,
            session_id,
            role,
            sources,
            retrieval_metadata,
            title,
            user_message,
            title_generator,
            completion_handler,
            agent
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
