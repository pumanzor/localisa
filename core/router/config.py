"""Router configuration."""

from pydantic_settings import BaseSettings


class RouterSettings(BaseSettings):
    rag_url: str = "http://rag:5001"
    llm_base_url: str = "http://host.docker.internal:11434/v1"
    llm_api_key: str = "not-needed"
    llm_model: str = "qwen2.5:3b"
    plugins_dir: str = "/app/plugins"

    class Config:
        env_prefix = "ROUTER_"
        extra = "ignore"


settings = RouterSettings()
