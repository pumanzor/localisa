"""Chat route — streaming SSE responses from LLM."""

import json
import logging
import time
from typing import Optional

import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from config import settings

router = APIRouter()
log = logging.getLogger("localisa.chat")

# Redis for conversation history
_redis = None


async def get_redis():
    global _redis
    if _redis is None:
        _redis = aioredis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True,
        )
    return _redis


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = "default"
    system_prompt: Optional[str] = None
    stream: bool = True


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    model: str
    elapsed_ms: int


SYSTEM_PROMPTS = {
    "es": (
        "Eres Localisa, un asistente de IA local y privado. "
        "Respondes de forma concisa y util en espanol. "
        "Puedes ayudar con preguntas sobre documentos, controlar dispositivos del hogar, "
        "describir lo que ven las camaras, y mas. Todos los datos del usuario se procesan localmente."
    ),
    "en": (
        "You are Localisa, a local and private AI assistant. "
        "You respond concisely and helpfully in English. "
        "You can help with document questions, control smart home devices, "
        "describe camera feeds, and more. All user data is processed locally."
    ),
}


async def get_history(conversation_id: str, max_turns: int = 10) -> list:
    """Get conversation history from Redis."""
    try:
        r = await get_redis()
        key = f"localisa:conv:{conversation_id}"
        raw = await r.lrange(key, -max_turns * 2, -1)
        return [json.loads(m) for m in raw]
    except Exception:
        return []


async def save_message(conversation_id: str, role: str, content: str):
    """Save a message to conversation history."""
    try:
        r = await get_redis()
        key = f"localisa:conv:{conversation_id}"
        await r.rpush(key, json.dumps({"role": role, "content": content}))
        await r.ltrim(key, -20, -1)  # Keep last 20 messages
        await r.expire(key, 3600)  # 1 hour TTL
    except Exception:
        pass


def build_messages(
    user_message: str,
    history: list,
    system_prompt: Optional[str] = None,
    rag_context: Optional[str] = None,
) -> list:
    """Build the messages array for the LLM."""
    sys_prompt = system_prompt or SYSTEM_PROMPTS.get(settings.localisa_lang, SYSTEM_PROMPTS["en"])

    if rag_context:
        sys_prompt += f"\n\nRelevant context from documents:\n{rag_context}"

    messages = [{"role": "system", "content": sys_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages


async def query_rag(query: str) -> Optional[str]:
    """Search RAG for relevant document context."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.rag_url}/search",
                json={"query": query, "top_k": 3},
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    chunks = []
                    for r in results:
                        score = r.get("score", 0)
                        if score > 0.3:
                            text = r.get("text", r.get("document", ""))
                            source = r.get("metadata", {}).get("source", "unknown")
                            chunks.append(f"[{source}]: {text[:500]}")
                    if chunks:
                        return "\n\n".join(chunks)
    except Exception as e:
        log.debug(f"RAG query failed: {e}")
    return None


@router.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """Chat with LLM — returns full response or SSE stream."""
    t0 = time.time()

    # Get history
    history = await get_history(req.conversation_id)

    # Search RAG for context
    rag_context = await query_rag(req.message)

    # Build messages
    messages = build_messages(req.message, history, req.system_prompt, rag_context)

    # Save user message
    await save_message(req.conversation_id, "user", req.message)

    if req.stream:
        return EventSourceResponse(
            stream_chat(messages, req.conversation_id, rag_context is not None)
        )

    # Non-streaming response
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model_name,
                    "messages": messages,
                    "stream": False,
                    "max_tokens": 2048,
                },
            )
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            await save_message(req.conversation_id, "assistant", content)
            return ChatResponse(
                response=content,
                conversation_id=req.conversation_id,
                model=settings.llm_model_name,
                elapsed_ms=int((time.time() - t0) * 1000),
            )
    except Exception as e:
        log.error(f"LLM error: {e}")
        return ChatResponse(
            response=f"Error connecting to LLM: {e}",
            conversation_id=req.conversation_id,
            model=settings.llm_model_name,
            elapsed_ms=int((time.time() - t0) * 1000),
        )


async def stream_chat(messages: list, conversation_id: str, has_rag: bool):
    """Stream chat completions as SSE events."""
    full_response = ""

    # Send metadata event
    yield {
        "event": "metadata",
        "data": json.dumps({
            "model": settings.llm_model_name,
            "backend": settings.llm_backend,
            "has_rag_context": has_rag,
        }),
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model_name,
                    "messages": messages,
                    "stream": True,
                    "max_tokens": 2048,
                },
            ) as resp:
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_response += content
                            yield {"event": "token", "data": content}
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
    except Exception as e:
        log.error(f"Stream error: {e}")
        yield {"event": "error", "data": str(e)}

    # Save assistant response
    if full_response:
        await save_message(conversation_id, "assistant", full_response)

    yield {"event": "done", "data": json.dumps({"total_tokens": len(full_response.split())})}


@router.delete("/chat/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Clear conversation history."""
    try:
        r = await get_redis()
        await r.delete(f"localisa:conv:{conversation_id}")
    except Exception:
        pass
    return {"status": "cleared", "conversation_id": conversation_id}
