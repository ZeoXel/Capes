"""
Chat Routes - Conversational interface with LangChain Agent.
"""

import asyncio
import json
import os
import time
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.deps import get_registry, get_settings, AVAILABLE_MODELS
from api.schemas import ChatRequest, ChatResponse, ChatMessage

router = APIRouter(prefix="/api/chat", tags=["chat"])


def create_agent(model: str):
    """Create LangChain agent with specified model."""
    from langchain_openai import ChatOpenAI
    from cape.agent.langchain import create_langchain_agent
    from pathlib import Path

    settings = get_settings()

    llm = ChatOpenAI(
        model=model,
        temperature=0,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    base_dir = Path(__file__).parent.parent.parent
    agent = create_langchain_agent(
        capes_dir=base_dir / "capes",
        skills_dir=base_dir / "skills",
        llm=llm,
    )

    return agent


async def generate_sse_events(
    message: str,
    model: str,
    enabled_capes: list[str] | None,
) -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events for streaming chat response.

    Event types:
    - cape_match: Cape matching result (when agent selects a tool)
    - cape_start: Start executing a Cape
    - content: Content chunk
    - cape_end: Cape execution completed
    - error: Error occurred
    - done: Stream finished
    """
    start_time = time.time()

    try:
        # Create LangChain agent
        agent = create_agent(model)

        # Invoke agent
        exec_start = time.time()
        result = await asyncio.to_thread(
            agent.invoke,
            {"messages": [("user", message)]}
        )

        # Parse response
        messages = result.get("messages", [])

        # Track tool calls
        tool_calls = []
        final_content = ""

        for msg in messages:
            msg_type = type(msg).__name__

            if msg_type == "AIMessage":
                # Check for tool calls
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_name = tc.get('name', '')
                        # Emit cape_start for tool calls
                        if tool_name.startswith('cape_'):
                            cape_id = tool_name.replace('cape_', '').replace('_', '-')
                            yield f"event: cape_start\ndata: {json.dumps({'cape_id': cape_id, 'cape_name': tool_name})}\n\n"
                            tool_calls.append({
                                'cape_id': cape_id,
                                'cape_name': tool_name,
                                'start_time': time.time()
                            })

                # Final response content
                if hasattr(msg, 'content') and msg.content and not msg.tool_calls:
                    final_content = msg.content

            elif msg_type == "ToolMessage":
                # Tool completed
                if tool_calls:
                    tc = tool_calls[-1]
                    duration = int((time.time() - tc['start_time']) * 1000)
                    yield f"event: cape_end\ndata: {json.dumps({'cape_id': tc['cape_id'], 'duration_ms': duration, 'tokens_used': 0, 'cost_usd': 0})}\n\n"

        # Stream final content
        if final_content:
            chunk_size = 50
            for i in range(0, len(final_content), chunk_size):
                chunk = final_content[i:i + chunk_size]
                yield f"event: content\ndata: {json.dumps({'text': chunk})}\n\n"
                await asyncio.sleep(0.02)
        else:
            # No final content - might be direct tool output
            for msg in messages:
                if type(msg).__name__ == "ToolMessage" and hasattr(msg, 'content'):
                    content = str(msg.content)
                    chunk_size = 50
                    for i in range(0, len(content), chunk_size):
                        chunk = content[i:i + chunk_size]
                        yield f"event: content\ndata: {json.dumps({'text': chunk})}\n\n"
                        await asyncio.sleep(0.02)
                    break

        # Done
        total_duration = int((time.time() - start_time) * 1000)
        yield f"event: done\ndata: {json.dumps({'total_duration_ms': total_duration})}\n\n"

    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        yield f"event: error\ndata: {json.dumps({'message': error_msg, 'code': 'internal_error'})}\n\n"
        yield f"event: done\ndata: {json.dumps({'total_duration_ms': 0})}\n\n"


@router.post("")
async def chat(request: ChatRequest):
    """
    Send a message and receive a streaming response from LangChain Agent.

    The agent has access to Cape tools and will automatically decide
    which capabilities to use based on the user's request.
    """
    # Validate model
    valid_models = [m["id"] for m in AVAILABLE_MODELS]
    if request.model not in valid_models:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model: {request.model}. Valid models: {valid_models}"
        )

    if request.stream:
        return StreamingResponse(
            generate_sse_events(
                message=request.message,
                model=request.model,
                enabled_capes=request.enabled_capes,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        # Non-streaming response using agent
        try:
            agent = create_agent(request.model)

            result = await asyncio.to_thread(
                agent.invoke,
                {"messages": [("user", request.message)]}
            )

            # Extract final response
            messages = result.get("messages", [])
            final_content = ""
            matched_cape = None

            for msg in messages:
                msg_type = type(msg).__name__

                if msg_type == "AIMessage":
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tc in msg.tool_calls:
                            tool_name = tc.get('name', '')
                            if tool_name.startswith('cape_'):
                                matched_cape = tool_name.replace('cape_', '').replace('_', '-')

                    if hasattr(msg, 'content') and msg.content and not getattr(msg, 'tool_calls', None):
                        final_content = msg.content

            # If no final content, use tool output
            if not final_content:
                for msg in messages:
                    if type(msg).__name__ == "ToolMessage" and hasattr(msg, 'content'):
                        final_content = str(msg.content)
                        break

            return ChatResponse(
                message=ChatMessage(
                    role="assistant",
                    content=final_content or "No response generated",
                    cape_execution={
                        "cape_id": matched_cape,
                        "cape_name": matched_cape,
                        "status": "completed",
                    } if matched_cape else None,
                ),
                matched_cape=matched_cape,
                execution_time_ms=0,
                tokens_used=0,
                cost_usd=0,
            )

        except Exception as e:
            return ChatResponse(
                message=ChatMessage(
                    role="assistant",
                    content=f"Error: {str(e)}",
                ),
                matched_cape=None,
            )
