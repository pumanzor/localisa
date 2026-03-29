"""Localisa RAG Server — hybrid search (semantic + keyword) with ChromaDB."""

import hashlib
import logging
import re
import gc
from datetime import datetime
from typing import List, Dict, Any, Optional

import httpx
import chromadb
from chromadb.config import Settings as ChromaSettings
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from config import settings
from chunker import chunk_text, extract_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("localisa.rag")

app = FastAPI(title="Localisa RAG")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- ChromaDB ---
_chroma = None


def get_chroma():
    global _chroma
    if _chroma is None:
        _chroma = chromadb.PersistentClient(
            path=settings.chromadb_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        log.info(f"ChromaDB initialized at {settings.chromadb_dir}")
    return _chroma


def get_collection(name: str):
    return get_chroma().get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


# --- Pydantic Models ---

class IngestTextRequest(BaseModel):
    text: str
    collection: str = "documents"
    metadata: dict = {}


class SearchRequest(BaseModel):
    query: str
    collection: Optional[str] = None
    collections: Optional[List[str]] = None
    top_k: int = 5
    threshold: float = 0.0


# --- Embeddings ---

def get_embedding(text: str) -> List[float]:
    """Get embedding from the embeddings service."""
    try:
        resp = httpx.post(
            f"{settings.embed_url}/api/embeddings",
            json={"prompt": text[:8000]},
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json().get("embedding", [])
    except Exception as e:
        log.error(f"Embedding error: {e}")
    return []


# --- Keyword Extraction ---

SPANISH_STOPWORDS = {
    'de', 'la', 'el', 'en', 'y', 'a', 'los', 'del', 'las', 'un', 'por', 'con',
    'una', 'su', 'para', 'es', 'al', 'lo', 'como', 'mas', 'o', 'pero', 'sus',
    'le', 'ya', 'fue', 'este', 'ha', 'si', 'porque', 'esta', 'son', 'entre',
    'cuando', 'muy', 'sin', 'sobre', 'ser', 'tambien', 'me', 'hasta', 'hay',
    'donde', 'quien', 'desde', 'nos', 'durante', 'todo', 'ni', 'que', 'se', 'no',
    'the', 'is', 'in', 'it', 'of', 'and', 'to', 'a', 'for', 'on', 'with', 'was',
    'are', 'be', 'at', 'by', 'an', 'or', 'not', 'from', 'but', 'have', 'had',
}


def extract_keywords(query: str) -> List[str]:
    """Extract meaningful keywords from a query."""
    # Acronyms and technical terms
    acronyms = re.findall(r'\b[A-Z][A-Z0-9]{1,10}\b', query)

    # IP addresses
    ips = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', query)

    # Regular words (3+ chars, not stopwords)
    words = re.findall(r'\b\w{3,}\b', query.lower())
    keywords = [w for w in words if w not in SPANISH_STOPWORDS]

    return list(set(acronyms + ips + keywords))


# --- Keyword Search ---

def keyword_search(collection, keywords: List[str], limit: int = 30) -> List[Dict]:
    """Search by keywords in document text."""
    if not keywords:
        return []

    try:
        all_docs = collection.get(include=["documents", "metadatas"])
    except Exception:
        return []

    results = []
    for i, doc in enumerate(all_docs["documents"] or []):
        if not doc:
            continue
        doc_lower = doc.lower()
        matched = []
        score = 0

        for kw in keywords:
            kw_lower = kw.lower()
            count = doc_lower.count(kw_lower)
            if count > 0:
                matched.append(kw)
                score += min(count, 5) * 0.1  # Cap at 0.5 per keyword

                # Bonus for match in metadata (source, filename)
                meta = (all_docs["metadatas"] or [{}])[i] if all_docs.get("metadatas") else {}
                source = str(meta.get("source", "")).lower()
                if kw_lower in source:
                    score += 0.3

        if matched:
            meta = (all_docs["metadatas"] or [{}])[i] if all_docs.get("metadatas") else {}
            results.append({
                "id": all_docs["ids"][i],
                "document": doc,
                "metadata": meta,
                "keyword_score": min(score, 1.0),
                "matched_keywords": matched,
            })

    results.sort(key=lambda x: x["keyword_score"], reverse=True)
    return results[:limit]


# --- Hybrid Search ---

def hybrid_search(
    query: str,
    collections: List[str],
    top_k: int = 5,
    threshold: float = 0.0,
) -> List[Dict]:
    """Hybrid search: semantic + keyword, with score fusion."""
    sem_w = settings.semantic_weight
    kw_w = settings.keyword_weight

    keywords = extract_keywords(query)
    has_keywords = len(keywords) > 0
    log.info(f"Search: keywords={keywords}, sem_w={sem_w}, kw_w={kw_w}")

    query_emb = get_embedding(query)
    if not query_emb:
        log.error("Failed to generate embedding")
        return []

    all_results = {}

    for col_name in collections:
        try:
            col = get_collection(col_name)
            count = col.count()
            if count == 0:
                continue

            # Keyword search
            if keywords:
                for kw_result in keyword_search(col, keywords, limit=top_k * 3):
                    doc_id = kw_result["id"]
                    all_results[doc_id] = {
                        "id": doc_id,
                        "collection": col_name,
                        "text": kw_result["document"],
                        "metadata": kw_result["metadata"],
                        "semantic_score": 0.0,
                        "keyword_score": kw_result["keyword_score"],
                        "score": 0.5 + kw_result["keyword_score"] * 0.2,
                    }

            # Semantic search
            n_results = min(max(top_k * 5, 50), count)
            sem_results = col.query(
                query_embeddings=[query_emb],
                n_results=n_results,
            )

            if sem_results and sem_results["documents"] and sem_results["documents"][0]:
                for i, doc in enumerate(sem_results["documents"][0]):
                    doc_id = sem_results["ids"][0][i]
                    sem_score = 1 - (sem_results["distances"][0][i] / 2)
                    meta = sem_results["metadatas"][0][i] if sem_results.get("metadatas") else {}

                    if doc_id in all_results:
                        # Dual match (keyword + semantic) — most relevant
                        all_results[doc_id]["semantic_score"] = sem_score
                        kw = all_results[doc_id]["keyword_score"]
                        all_results[doc_id]["score"] = kw_w * kw + sem_w * sem_score + 0.15
                    else:
                        penalty = 0.05 if has_keywords else 0
                        all_results[doc_id] = {
                            "id": doc_id,
                            "collection": col_name,
                            "text": doc,
                            "metadata": meta,
                            "semantic_score": sem_score,
                            "keyword_score": 0,
                            "score": sem_score - penalty,
                        }

        except Exception as e:
            log.error(f"Error searching {col_name}: {e}")

    # Sort by score
    results = sorted(all_results.values(), key=lambda x: x["score"], reverse=True)

    # Apply threshold
    if threshold > 0:
        results = [r for r in results if r["score"] >= threshold]

    return results[:top_k]


# --- Endpoints ---

@app.get("/")
def root():
    return {"name": "Localisa RAG", "status": "running"}


@app.get("/health")
def health():
    try:
        client = get_chroma()
        cols = client.list_collections()
        total = sum(c.count() for c in cols)
        return {
            "status": "ok",
            "collections": len(cols),
            "total_documents": total,
            "chromadb_dir": settings.chromadb_dir,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/collections")
def list_collections():
    """List all collections with document counts."""
    try:
        cols = get_chroma().list_collections()
        return {
            "collections": [
                {"name": c.name, "count": c.count()} for c in cols
            ]
        }
    except Exception as e:
        return {"collections": [], "error": str(e)}


@app.post("/ingest/text")
def ingest_text(req: IngestTextRequest):
    """Ingest raw text into a collection."""
    col = get_collection(req.collection)

    chunks = chunk_text(req.text, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        return {"status": "error", "detail": "No chunks generated"}

    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for chunk in chunks:
        chunk_hash = hashlib.md5(chunk.encode()).hexdigest()[:12]
        doc_id = f"{req.collection}_{chunk_hash}"

        emb = get_embedding(chunk)
        if not emb:
            continue

        meta = {
            "source": req.metadata.get("source", "text_input"),
            "collection": req.collection,
            "ingested_at": datetime.now().isoformat(),
            **{k: v for k, v in req.metadata.items() if isinstance(v, (str, int, float, bool))},
        }

        ids.append(doc_id)
        embeddings.append(emb)
        documents.append(chunk)
        metadatas.append(meta)

    if ids:
        col.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        log.info(f"Ingested {len(ids)} chunks into '{req.collection}'")

    gc.collect()
    return {"status": "ok", "chunks": len(ids), "collection": req.collection}


@app.post("/ingest/file")
def ingest_file(file: UploadFile = File(...), collection: str = "documents"):
    """Upload and ingest a file (PDF, DOCX, TXT, XLSX)."""
    content = file.file.read()
    filename = file.filename or "unknown"

    log.info(f"Ingesting file: {filename} ({len(content)} bytes) into '{collection}'")

    text = extract_text(filename, content)
    if not text or len(text.strip()) < 50:
        return {"status": "error", "detail": f"Could not extract text from {filename}"}

    chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        return {"status": "error", "detail": "No chunks generated"}

    col = get_collection(collection)
    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        chunk_hash = hashlib.md5(chunk.encode()).hexdigest()[:12]
        doc_id = f"{collection}_{filename}_{chunk_hash}"

        emb = get_embedding(chunk)
        if not emb:
            continue

        meta = {
            "source": filename,
            "collection": collection,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "ingested_at": datetime.now().isoformat(),
        }

        ids.append(doc_id)
        embeddings.append(emb)
        documents.append(chunk)
        metadatas.append(meta)

    if ids:
        col.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        log.info(f"Ingested {len(ids)}/{len(chunks)} chunks from '{filename}'")

    gc.collect()
    return {"status": "ok", "filename": filename, "chunks": len(ids), "collection": collection}


@app.post("/search")
def search(req: SearchRequest):
    """Hybrid search across collections."""
    # Determine which collections to search
    if req.collection:
        cols = [req.collection]
    elif req.collections:
        cols = req.collections
    else:
        # Search all collections
        try:
            all_cols = get_chroma().list_collections()
            cols = [c.name for c in all_cols if c.count() > 0]
        except Exception:
            cols = ["documents"]

    log.info(f"Searching: '{req.query}' in {cols} (top_k={req.top_k})")
    results = hybrid_search(req.query, cols, req.top_k, req.threshold)
    log.info(f"Found {len(results)} results")

    return {"query": req.query, "results": results, "collections_searched": cols}


@app.delete("/collection/{name}")
def delete_collection(name: str):
    """Delete a collection."""
    try:
        get_chroma().delete_collection(name)
        log.info(f"Deleted collection: {name}")
        return {"status": "deleted", "collection": name}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host=settings.host, port=settings.port)
