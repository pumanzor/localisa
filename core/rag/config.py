"""RAG server configuration."""

from pydantic_settings import BaseSettings


class RAGSettings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 5001
    embed_url: str = "http://embeddings:8101"
    embed_model: str = "BAAI/bge-m3"
    embedding_dims: int = 1024
    chromadb_dir: str = "/data/chromadb"
    chunk_size: int = 800
    chunk_overlap: int = 150
    semantic_weight: float = 0.4
    keyword_weight: float = 0.6

    class Config:
        env_prefix = "RAG_"
        env_file = ".env"
        extra = "ignore"


settings = RAGSettings()
