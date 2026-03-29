"""Embeddings server — BGE-M3 via sentence-transformers."""

import os
import logging
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("localisa.embeddings")

app = FastAPI(title="Localisa Embeddings")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Globals
model = None
MODEL_PATH = os.environ.get("EMBED_MODEL", "BAAI/bge-m3")
DEVICE = os.environ.get("EMBED_DEVICE", "cpu")
PORT = int(os.environ.get("EMBED_PORT", "8101"))


class EmbedRequest(BaseModel):
    prompt: str
    model: str = ""


class EmbedBatchRequest(BaseModel):
    prompts: List[str]
    model: str = ""


def load_model():
    global model
    if model is not None:
        return
    log.info(f"Loading embedding model: {MODEL_PATH} on {DEVICE}")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_PATH, device=DEVICE)
    log.info(f"Model loaded. Dimensions: {model.get_sentence_embedding_dimension()}")


@app.on_event("startup")
def startup():
    load_model()


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_PATH, "device": DEVICE, "loaded": model is not None}


@app.post("/api/embeddings")
def embed_single(req: EmbedRequest):
    """Embed a single text. Compatible with Ollama API format."""
    load_model()
    text = req.prompt[:8000]
    embedding = model.encode(text, normalize_embeddings=True).tolist()
    return {"embedding": embedding}


@app.post("/api/embeddings/batch")
def embed_batch(req: EmbedBatchRequest):
    """Embed multiple texts."""
    load_model()
    texts = [t[:8000] for t in req.prompts]
    embeddings = model.encode(texts, normalize_embeddings=True).tolist()
    return {"embeddings": embeddings}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
