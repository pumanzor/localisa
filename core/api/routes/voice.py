"""Voice routes — transcribe audio and synthesize speech."""

import logging
import httpx
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from config import settings

router = APIRouter()
log = logging.getLogger("localisa.voice")


class SynthesizeRequest(BaseModel):
    text: str
    language: str = "es"


@router.post("/voice/transcribe")
async def transcribe(file: UploadFile = File(...)):
    """Transcribe audio file using Whisper."""
    content = await file.read()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.whisper_url}/transcribe",
                content=content,
                headers={"Content-Type": "audio/wav"},
            )
            if resp.status_code == 200:
                return resp.json()
            return {"text": "", "error": resp.text}
    except Exception as e:
        return {"text": "", "error": str(e)}


@router.post("/voice/synthesize")
async def synthesize(req: SynthesizeRequest):
    """Synthesize text to speech using Piper TTS."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.tts_url}/synthesize",
                json={"text": req.text, "language": req.language},
            )
            if resp.status_code == 200:
                from fastapi.responses import Response
                return Response(
                    content=resp.content,
                    media_type="audio/wav",
                    headers={"Content-Disposition": "inline; filename=speech.wav"},
                )
            return {"error": resp.text}
    except Exception as e:
        return {"error": str(e)}
