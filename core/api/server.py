"""Localisa API Gateway — connects all services."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routes import chat, documents, health, models, voice, vision, devices, settings as settings_route

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("localisa")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(f"Localisa API starting — LLM backend: {settings.llm_backend}")
    log.info(f"  Model: {settings.llm_model_name}")
    log.info(f"  Base URL: {settings.llm_base_url}")
    log.info(f"  Language: {settings.localisa_lang}")
    yield
    log.info("Localisa API shutting down")


app = FastAPI(
    title="Localisa",
    description="AI that lives in the real world",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes
app.include_router(chat.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(voice.router, prefix="/api")
app.include_router(vision.router, prefix="/api")
app.include_router(devices.router, prefix="/api")
app.include_router(settings_route.router, prefix="/api")


@app.get("/")
async def root():
    return {"name": "Localisa", "version": "0.1.0", "status": "running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5002)
