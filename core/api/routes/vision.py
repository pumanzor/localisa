"""Vision routes — camera snapshots and AI description."""

import logging
import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from config import settings

router = APIRouter()
log = logging.getLogger("localisa.vision")


class DescribeRequest(BaseModel):
    camera_id: Optional[str] = None
    prompt: str = "Describe what you see in this image."


@router.get("/vision/cameras")
async def list_cameras():
    """List configured cameras."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.vision_url}/cameras")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return {"cameras": []}


@router.get("/vision/snapshot/{camera_id}")
async def get_snapshot(camera_id: str):
    """Get a snapshot from a camera."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.vision_url}/snapshot/{camera_id}")
            if resp.status_code == 200:
                from fastapi.responses import Response
                return Response(
                    content=resp.content,
                    media_type="image/jpeg",
                )
    except Exception as e:
        return {"error": str(e)}


@router.post("/vision/describe")
async def describe_camera(req: DescribeRequest):
    """Get AI description of what a camera sees."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.vision_url}/describe",
                json={"camera_id": req.camera_id, "prompt": req.prompt},
            )
            if resp.status_code == 200:
                return resp.json()
            return {"description": "", "error": resp.text}
    except Exception as e:
        return {"description": "", "error": str(e)}
