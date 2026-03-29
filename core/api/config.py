"""Localisa API configuration — all from environment variables."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # LLM Backend
    llm_backend: str = "ollama"  # ollama | cloud | vllm | llamacpp | custom

    # Ollama
    ollama_host: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen2.5:3b"

    # Cloud API
    llm_cloud_provider: str = "deepseek"
    llm_cloud_api_key: str = ""
    llm_cloud_model: str = "deepseek-chat"
    llm_cloud_fallback: bool = False

    # vLLM
    vllm_host: str = "http://llm-vllm:8100"
    vllm_model: str = "Qwen/Qwen2.5-7B-Instruct-AWQ"

    # Custom
    llm_custom_url: str = ""
    llm_custom_api_key: str = ""

    # Internal services
    redis_host: str = "redis"
    redis_port: int = 6379
    rag_url: str = "http://rag:5001"
    embed_url: str = "http://embeddings:8101"
    whisper_url: str = "http://whisper:5012"
    tts_url: str = "http://tts:5050"
    vision_url: str = "http://vision:8060"

    # General
    localisa_lang: str = "es"
    web_port: int = 8080
    plugins: str = "search,weather"

    # Telegram
    telegram_bot_token: str = ""
    telegram_allowed_users: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def llm_base_url(self) -> str:
        """Return the OpenAI-compatible base URL for the active LLM backend."""
        if self.llm_backend == "ollama":
            return f"{self.ollama_host}/v1"
        elif self.llm_backend == "cloud":
            providers = {
                "deepseek": "https://api.deepseek.com/v1",
                "kimi": "https://api.moonshot.cn/v1",
                "groq": "https://api.groq.com/openai/v1",
                "claude": "https://api.anthropic.com/v1",
                "openai": "https://api.openai.com/v1",
            }
            return providers.get(self.llm_cloud_provider, "https://api.openai.com/v1")
        elif self.llm_backend == "vllm":
            return f"{self.vllm_host}/v1"
        elif self.llm_backend == "custom":
            return self.llm_custom_url
        return f"{self.ollama_host}/v1"

    @property
    def llm_api_key(self) -> str:
        """Return the API key for the active backend."""
        if self.llm_backend == "cloud":
            return self.llm_cloud_api_key
        elif self.llm_backend == "custom":
            return self.llm_custom_api_key
        return "not-needed"

    @property
    def llm_model_name(self) -> str:
        """Return the model name for the active backend."""
        if self.llm_backend == "ollama":
            return self.ollama_model
        elif self.llm_backend == "cloud":
            return self.llm_cloud_model
        elif self.llm_backend == "vllm":
            return self.vllm_model
        return self.ollama_model


settings = Settings()
