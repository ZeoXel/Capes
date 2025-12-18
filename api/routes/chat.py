"""
Chat Routes - Conversational interface with LangChain Agent.

支持上下文保持：
- 每个 session_id 对应一个 ConversationState
- 使用 PromptBuilder 按模型构建上下文增强的 Prompt
- 使用 StateUpdater 每轮更新状态（摘要、事实抽取）
"""

import asyncio
import json
import time
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.deps import get_settings, AVAILABLE_MODELS
from api.schemas import ChatRequest, ChatResponse, ChatMessage
from api.state import state_manager
from api.prompt_builder import PromptBuilder
from api.state_updater import StateUpdater

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


def extract_response_content(messages: list) -> tuple[str, Optional[str]]:
    """
    从 Agent 响应中提取最终内容和匹配的 Cape

    Returns:
        (final_content, matched_cape)
    """
    final_content = ""
    matched_cape = None

    for msg in messages:
        msg_type = type(msg).__name__

        if msg_type == "AIMessage":
            # Check for tool calls
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.get('name', '')
                    if tool_name.startswith('cape_'):
                        matched_cape = tool_name.replace('cape_', '').replace('_', '-')

            # Final response content (没有 tool_calls 的 AIMessage)
            if hasattr(msg, 'content') and msg.content and not getattr(msg, 'tool_calls', None):
                final_content = msg.content

    # If no final content, use tool output
    if not final_content:
        for msg in messages:
            if type(msg).__name__ == "ToolMessage" and hasattr(msg, 'content'):
                final_content = str(msg.content)
                break

    return final_content, matched_cape


async def generate_sse_events(
    message: str,
    model: str,
    session_id: Optional[str],
    enabled_capes: list[str] | None,
) -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events for streaming chat response.

    Event types:
    - session: Session ID (first event)
    - cape_match: Cape matching result (when agent selects a tool)
    - cape_start: Start executing a Cape
    - content: Content chunk
    - cape_end: Cape execution completed
    - error: Error occurred
    - done: Stream finished
    """
    start_time = time.time()

    # 1. 获取或创建会话状态
    state = state_manager.get_or_create(session_id)

    # 返回 session_id（前端首次请求时可能没有）
    yield f"event: session\ndata: {json.dumps({'session_id': state.session_id})}\n\n"

    try:
        # 2. 构建上下文增强的 Prompt
        context_prompt = PromptBuilder.build(state, message, model)

        # 3. 创建 LangChain agent
        agent = create_agent(model)

        # 4. 调用 agent（使用增强后的 prompt）
        exec_start = time.time()
        result = await asyncio.to_thread(
            agent.invoke,
            {"messages": [("user", context_prompt)]}
        )

        # 5. 解析响应
        messages = result.get("messages", [])

        # Track tool calls
        tool_calls = []
        final_content = ""
        matched_cape = None

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
                            matched_cape = cape_id
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
                    final_content = content  # 保存用于状态更新
                    chunk_size = 50
                    for i in range(0, len(content), chunk_size):
                        chunk = content[i:i + chunk_size]
                        yield f"event: content\ndata: {json.dumps({'text': chunk})}\n\n"
                        await asyncio.sleep(0.02)
                    break

        # 6. 更新状态（异步，不阻塞响应）
        try:
            StateUpdater.update_sync(
                state=state,
                user_input=message,  # 原始用户输入，非增强版
                assistant_response=final_content or "No response",
                cape_id=matched_cape
            )
            state_manager.update(state)
        except Exception as update_err:
            print(f"[Chat] State update error: {update_err}")

        # Done
        total_duration = int((time.time() - start_time) * 1000)
        yield f"event: done\ndata: {json.dumps({'total_duration_ms': total_duration, 'session_id': state.session_id})}\n\n"

    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        yield f"event: error\ndata: {json.dumps({'message': error_msg, 'code': 'internal_error'})}\n\n"
        yield f"event: done\ndata: {json.dumps({'total_duration_ms': 0, 'session_id': state.session_id})}\n\n"


@router.post("")
async def chat(request: ChatRequest):
    """
    Send a message and receive a streaming response from LangChain Agent.

    The agent has access to Cape tools and will automatically decide
    which capabilities to use based on the user's request.

    支持上下文保持：
    - 首次请求不传 session_id，服务端自动创建
    - 后续请求携带 session_id，保持对话上下文
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
                session_id=request.session_id,
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
            # 1. 获取或创建会话状态
            state = state_manager.get_or_create(request.session_id)

            # 2. 构建上下文增强的 Prompt
            context_prompt = PromptBuilder.build(state, request.message, request.model)

            # 3. 创建并调用 agent
            agent = create_agent(request.model)

            exec_start = time.time()
            result = await asyncio.to_thread(
                agent.invoke,
                {"messages": [("user", context_prompt)]}
            )
            exec_time = (time.time() - exec_start) * 1000

            # 4. 提取响应
            messages = result.get("messages", [])
            final_content, matched_cape = extract_response_content(messages)

            # 5. 更新状态
            StateUpdater.update_sync(
                state=state,
                user_input=request.message,
                assistant_response=final_content or "No response",
                cape_id=matched_cape
            )
            state_manager.update(state)

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
                execution_time_ms=exec_time,
                tokens_used=0,
                cost_usd=0,
                session_id=state.session_id,
            )

        except Exception as e:
            # 即使出错也返回 session_id
            state = state_manager.get_or_create(request.session_id)
            return ChatResponse(
                message=ChatMessage(
                    role="assistant",
                    content=f"Error: {str(e)}",
                ),
                matched_cape=None,
                session_id=state.session_id,
            )


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    success = state_manager.delete(session_id)
    if success:
        return {"status": "deleted", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """获取会话状态（用于 Debug）"""
    state = state_manager.get(session_id)
    if state:
        return {
            "session_id": state.session_id,
            "turn_count": len(state.turns),
            "summary_count": len(state.summaries),
            "facts": {f.key: f.value for f in state.facts},
            "active_tasks": [t.goal for t in state.get_active_tasks()],
            "recent_turns": [
                {"role": t.role, "content": t.content[:100], "cape_id": t.cape_id}
                for t in state.get_recent_turns(5)
            ],
            "latest_summary": state.get_latest_summary(),
        }
    else:
        raise HTTPException(status_code=404, detail="Session not found")


@router.get("/sessions")
async def list_sessions():
    """列出所有会话（用于 Debug）"""
    return {
        "total": state_manager.get_session_count(),
        "sessions": state_manager.list_sessions(),
    }
