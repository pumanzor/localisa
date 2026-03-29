"""Models route — list and switch LLM models."""

import logging
import httpx
from fastapi import APIRouter
from config import settings

router = APIRouter()
log = logging.getLogger("localisa.models")


@router.get("/models")
async def list_models():
    """List available models from the active backend."""
    models = []

    if settings.llm_backend == "ollama":
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{settings.ollama_host}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get("models", []):
                        models.append({
                            "name": m["name"],
                            "size_gb": round(m.get("size", 0) / (1024**3), 1),
                            "active": m["name"] == settings.ollama_model,
                        })
        except Exception:
            pass
    elif settings.llm_backend in ("vllm", "custom"):
        try:
            url = settings.llm_base_url.replace("/v1", "") + "/v1/models"
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    url, headers={"Authorization": f"Bearer {settings.llm_api_key}"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get("data", []):
                        models.append({
                            "name": m["id"],
                            "active": m["id"] == settings.llm_model_name,
                        })
        except Exception:
            pass

    return {
        "backend": settings.llm_backend,
        "active_model": settings.llm_model_name,
        "models": models,
    }
