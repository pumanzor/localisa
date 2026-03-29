"""Health route — check all services."""

import logging
import httpx
from fastapi import APIRouter
from config import settings

router = APIRouter()
log = logging.getLogger("localisa.health")


async def check_service(name: str, url: str, timeout: float = 3.0) -> dict:
    """Check if a service is reachable."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            return {"name": name, "status": "ok", "code": resp.status_code}
    except Exception as e:
        return {"name": name, "status": "error", "error": str(e)}


@router.get("/health")
async def health():
    """Health check for all services."""
    checks = [
        check_service("rag", f"{settings.rag_url}/health"),
        check_service("embeddings", f"{settings.embed_url}/health"),
    ]

    # LLM backend check
    if settings.llm_backend == "ollama":
        checks.append(check_service("llm", f"{settings.ollama_host}/api/tags"))
    elif settings.llm_backend == "vllm":
        checks.append(check_service("llm", f"{settings.vllm_host}/v1/models"))

    # Optional services
    checks.append(check_service("whisper", f"{settings.whisper_url}/health"))
    checks.append(check_service("tts", f"{settings.tts_url}/health"))
    checks.append(check_service("vision", f"{settings.vision_url}/health"))

    import asyncio
    results = await asyncio.gather(*checks)

    all_ok = all(r["status"] == "ok" for r in results if r["name"] in ("rag", "embeddings"))

    return {
        "status": "ok" if all_ok else "degraded",
        "backend": settings.llm_backend,
        "model": settings.llm_model_name,
        "language": settings.localisa_lang,
        "services": results,
    }
