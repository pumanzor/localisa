"""Document routes — upload, search, list, delete."""

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel

from config import settings

router = APIRouter()
log = logging.getLogger("localisa.documents")


class SearchRequest(BaseModel):
    query: str
    collection: Optional[str] = None
    top_k: int = 5


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    collection: Optional[str] = Form(None),
):
    """Upload a document to RAG for indexing."""
    content = await file.read()
    collection = collection or "documents"

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{settings.rag_url}/ingest/file",
                files={"file": (file.filename, content, file.content_type)},
                data={"collection": collection},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "ok",
                    "filename": file.filename,
                    "chunks": data.get("chunks", 0),
                    "collection": collection,
                }
            return {"status": "error", "detail": resp.text}
    except Exception as e:
        log.error(f"Upload failed: {e}")
        return {"status": "error", "detail": str(e)}


@router.post("/documents/search")
async def search_documents(req: SearchRequest):
    """Search documents via RAG."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            payload = {"query": req.query, "top_k": req.top_k}
            if req.collection:
                payload["collection"] = req.collection
            resp = await client.post(f"{settings.rag_url}/search", json=payload)
            if resp.status_code == 200:
                return resp.json()
            return {"results": [], "error": resp.text}
    except Exception as e:
        return {"results": [], "error": str(e)}


@router.get("/documents/collections")
async def list_collections():
    """List available RAG collections."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.rag_url}/collections")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return {"collections": []}


@router.delete("/documents/{collection}")
async def delete_collection(collection: str):
    """Delete a RAG collection."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(f"{settings.rag_url}/collection/{collection}")
            if resp.status_code == 200:
                return {"status": "deleted", "collection": collection}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
