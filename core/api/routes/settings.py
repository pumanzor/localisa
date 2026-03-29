"""Settings route — configure LLM backend, API keys, Telegram, plugins."""

import json
import logging
from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter
from pydantic import BaseModel

from config import settings as app_settings

router = APIRouter()
log = logging.getLogger("localisa.settings")

SETTINGS_KEY = "localisa:settings"
_redis = None


async def get_redis():
    global _redis
    if _redis is None:
        _redis = aioredis.Redis(
            host=app_settings.redis_host,
            port=app_settings.redis_port,
            decode_responses=True,
        )
    return _redis


# --- Default settings ---
DEFAULTS = {
    "llm_backend": "ollama",
    "ollama_host": "http://host.docker.internal:11434",
    "ollama_model": "qwen3:4b",
    "cloud_provider": "deepseek",
    "cloud_api_key": "",
    "cloud_model": "deepseek-chat",
    "cloud_fallback": False,
    "custom_url": "",
    "custom_api_key": "",
    "custom_model": "",
    "telegram_bot_token": "",
    "telegram_allowed_users": "",
    "language": "es",
    "plugins": ["search", "weather"],
    "whisper_model": "base",
    "whisper_language": "es",
    "tts_model": "es_MX-claude-high",
}

# Cloud provider configs
CLOUD_PROVIDERS = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "cost": "$0.14/M tokens",
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
        "cost": "Free tier",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-nano"],
        "cost": "$0.15-2.50/M tokens",
    },
    "claude": {
        "name": "Anthropic Claude",
        "base_url": "https://api.anthropic.com/v1",
        "models": ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"],
        "cost": "$0.80-3/M tokens",
    },
    "kimi": {
        "name": "Kimi (Moonshot)",
        "base_url": "https://api.moonshot.cn/v1",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k"],
        "cost": "$0.12/M tokens",
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "models": ["auto"],
        "cost": "Varies",
    },
}

AVAILABLE_PLUGINS = [
    {"id": "search", "name": "Web Search", "description": "Search the internet (DuckDuckGo)"},
    {"id": "weather", "name": "Weather", "description": "Weather forecasts (Open-Meteo, free)"},
    {"id": "home", "name": "Home Automation", "description": "Control IoT devices via MQTT"},
    {"id": "network", "name": "Network", "description": "Router intelligence, Pi-hole, firewall"},
    {"id": "energy", "name": "Energy", "description": "Solar + grid monitoring"},
    {"id": "audio", "name": "Audio", "description": "Music playback (Spotify, YouTube, Radio)"},
    {"id": "medical", "name": "Medical", "description": "Clinical guidelines RAG, triage"},
    {"id": "vehicle", "name": "Vehicle", "description": "Car diagnostics via OBD-II/CAN"},
    {"id": "elder", "name": "Elder Care", "description": "Fall detection, routine monitoring"},
    {"id": "finance", "name": "Finance", "description": "Bank integration, expense analysis"},
    {"id": "calendar", "name": "Calendar", "description": "Google Calendar, reminders"},
    {"id": "notify", "name": "Notifications", "description": "Push notifications (Ntfy, Gotify)"},
]


async def load_settings() -> dict:
    """Load settings from Redis, falling back to env vars then defaults."""
    try:
        r = await get_redis()
        raw = await r.get(SETTINGS_KEY)
        if raw:
            saved = json.loads(raw)
            # Merge with defaults (in case new settings were added)
            merged = {**DEFAULTS, **saved}
            return merged
    except Exception as e:
        log.warning(f"Failed to load settings from Redis: {e}")

    # Fall back to env vars
    return {
        "llm_backend": app_settings.llm_backend,
        "ollama_host": app_settings.ollama_host,
        "ollama_model": app_settings.ollama_model,
        "cloud_provider": app_settings.llm_cloud_provider,
        "cloud_api_key": app_settings.llm_cloud_api_key,
        "cloud_model": app_settings.llm_cloud_model,
        "cloud_fallback": app_settings.llm_cloud_fallback,
        "custom_url": app_settings.llm_custom_url,
        "custom_api_key": app_settings.llm_custom_api_key,
        "custom_model": "",
        "telegram_bot_token": app_settings.telegram_bot_token,
        "telegram_allowed_users": app_settings.telegram_allowed_users,
        "language": app_settings.localisa_lang,
        "plugins": app_settings.plugins.split(",") if app_settings.plugins else [],
        "whisper_model": "base",
        "whisper_language": "es",
        "tts_model": "es_MX-claude-high",
    }


async def save_settings(data: dict):
    """Save settings to Redis."""
    try:
        r = await get_redis()
        await r.set(SETTINGS_KEY, json.dumps(data))
        log.info("Settings saved to Redis")
    except Exception as e:
        log.error(f"Failed to save settings: {e}")


def mask_key(key: str) -> str:
    """Mask API key for display: show first 4 and last 4 chars."""
    if not key or len(key) < 12:
        return "****" if key else ""
    return f"{key[:4]}...{key[-4:]}"


# --- Endpoints ---

@router.get("/settings")
async def get_settings():
    """Get current settings (API keys masked)."""
    data = await load_settings()
    # Mask sensitive fields for display
    display = {**data}
    display["cloud_api_key_masked"] = mask_key(data.get("cloud_api_key", ""))
    display["custom_api_key_masked"] = mask_key(data.get("custom_api_key", ""))
    display["telegram_bot_token_masked"] = mask_key(data.get("telegram_bot_token", ""))
    # Don't send raw keys to frontend
    display.pop("cloud_api_key", None)
    display.pop("custom_api_key", None)
    display.pop("telegram_bot_token", None)
    return {
        "settings": display,
        "cloud_providers": CLOUD_PROVIDERS,
        "available_plugins": AVAILABLE_PLUGINS,
    }


class SettingsUpdate(BaseModel):
    llm_backend: Optional[str] = None
    ollama_host: Optional[str] = None
    ollama_model: Optional[str] = None
    cloud_provider: Optional[str] = None
    cloud_api_key: Optional[str] = None
    cloud_model: Optional[str] = None
    cloud_fallback: Optional[bool] = None
    custom_url: Optional[str] = None
    custom_api_key: Optional[str] = None
    custom_model: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_allowed_users: Optional[str] = None
    language: Optional[str] = None
    plugins: Optional[list] = None
    whisper_model: Optional[str] = None
    whisper_language: Optional[str] = None
    tts_model: Optional[str] = None


@router.post("/settings")
async def update_settings(update: SettingsUpdate):
    """Update settings. Only provided fields are changed."""
    current = await load_settings()

    # Apply updates (only non-None fields)
    changes = {k: v for k, v in update.dict().items() if v is not None}
    current.update(changes)

    await save_settings(current)

    # Update runtime config
    _apply_runtime_settings(current)

    return {"status": "ok", "changes": list(changes.keys())}


@router.post("/settings/test-llm")
async def test_llm_connection(update: SettingsUpdate):
    """Test LLM connection with provided settings (without saving)."""
    import httpx

    backend = update.llm_backend or "ollama"
    try:
        if backend == "ollama":
            host = update.ollama_host or "http://host.docker.internal:11434"
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{host}/api/tags")
                if resp.status_code == 200:
                    models = [m["name"] for m in resp.json().get("models", [])]
                    return {"status": "ok", "message": f"Connected. Models: {', '.join(models)}"}
                return {"status": "error", "message": f"HTTP {resp.status_code}"}

        elif backend == "cloud":
            provider = update.cloud_provider or "deepseek"
            api_key = update.cloud_api_key or ""
            if not api_key:
                return {"status": "error", "message": "API key required"}

            provider_cfg = CLOUD_PROVIDERS.get(provider, {})
            base_url = provider_cfg.get("base_url", "")

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 200:
                    return {"status": "ok", "message": f"Connected to {provider_cfg.get('name', provider)}"}
                return {"status": "error", "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}

        elif backend == "custom":
            url = update.custom_url or ""
            if not url:
                return {"status": "error", "message": "URL required"}
            async with httpx.AsyncClient(timeout=5) as client:
                headers = {}
                if update.custom_api_key:
                    headers["Authorization"] = f"Bearer {update.custom_api_key}"
                resp = await client.get(f"{url}/models", headers=headers)
                if resp.status_code == 200:
                    return {"status": "ok", "message": "Connected"}
                return {"status": "error", "message": f"HTTP {resp.status_code}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

    return {"status": "error", "message": "Unknown backend"}


def _apply_runtime_settings(data: dict):
    """Apply settings to the running config (hot reload)."""
    app_settings.llm_backend = data.get("llm_backend", app_settings.llm_backend)
    app_settings.ollama_host = data.get("ollama_host", app_settings.ollama_host)
    app_settings.ollama_model = data.get("ollama_model", app_settings.ollama_model)
    app_settings.llm_cloud_provider = data.get("cloud_provider", app_settings.llm_cloud_provider)
    app_settings.llm_cloud_api_key = data.get("cloud_api_key", app_settings.llm_cloud_api_key)
    app_settings.llm_cloud_model = data.get("cloud_model", app_settings.llm_cloud_model)
    app_settings.llm_cloud_fallback = data.get("cloud_fallback", app_settings.llm_cloud_fallback)
    app_settings.llm_custom_url = data.get("custom_url", app_settings.llm_custom_url)
    app_settings.llm_custom_api_key = data.get("custom_api_key", app_settings.llm_custom_api_key)
    app_settings.localisa_lang = data.get("language", app_settings.localisa_lang)
    app_settings.telegram_bot_token = data.get("telegram_bot_token", app_settings.telegram_bot_token)
    app_settings.telegram_allowed_users = data.get("telegram_allowed_users", app_settings.telegram_allowed_users)
    log.info(f"Runtime config updated: backend={app_settings.llm_backend}, model={app_settings.llm_model_name}")
