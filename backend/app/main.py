from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis
import json
import hashlib
from .ingest import process_pdf, process_image, process_audio, get_audio_backend_status
from .embed import get_text_embedding, get_image_embedding, store_embedding, get_embedding_backend_status
from .retrieve import (
    describe_audio,
    describe_image,
    generate_diagnosis,
    query_system,
    get_generation_backend_status,
)
from .graph import get_graph_data
import logging
import os
import shutil
import uuid
from typing import List
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="MediRAG API")
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {
    "text": {".pdf", ".txt"},
    "image": {".png", ".jpg", ".jpeg"},
    "audio": {".mp3", ".wav", ".m4a"},
}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

def validate_file(filename: str, file_size: int) -> None:
    """Validate file extension and size."""
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is 20MB, got {file_size / (1024*1024):.1f}MB"
        )
    
    ext = os.path.splitext(filename or "")[1].lower() if filename else ""
    all_allowed = set().union(*ALLOWED_EXTENSIONS.values())
    
    if ext not in all_allowed:
        allowed_list = ", ".join(sorted(all_allowed))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {ext}. Allowed formats: {allowed_list}"
        )

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Maximum 10 queries per minute."}
    )

async def _process_single_file(file: UploadFile) -> dict:
    """Process a single uploaded file and return its result."""
    file_bytes = await file.read()
    
    # Validate file extension and size
    validate_file(file.filename, len(file_bytes))
    
    ext = os.path.splitext(file.filename or "")[1].lower()
    doc_id = str(uuid.uuid4())
    
    if ext == "pdf":
        text = await run_in_threadpool(process_pdf, file_bytes)
        emb = await run_in_threadpool(get_text_embedding, text)
        await run_in_threadpool(store_embedding, doc_id, emb, {"type": "text", "text": text[:1000], "filename": file.filename})
        return {"filename": file.filename, "status": "success", "message": "PDF ingested successfully", "id": doc_id}
        
    elif ext in ["png", "jpg", "jpeg"]:
        image = await run_in_threadpool(process_image, file_bytes)
        emb = await run_in_threadpool(get_image_embedding, image)
        image_analysis = await describe_image(file_bytes)
        await run_in_threadpool(
            store_embedding,
            doc_id,
            emb,
            {
                "type": "image",
                "filename": file.filename,
                "image_analysis": image_analysis,
                "text": image_analysis,
            }
        )
        text_emb = await run_in_threadpool(get_text_embedding, image_analysis)
        await run_in_threadpool(
            store_embedding,
            f"{doc_id}-analysis",
            text_emb,
            {
                "type": "image",
                "filename": file.filename,
                "image_analysis": image_analysis,
                "text": image_analysis,
            }
        )
        return {"filename": file.filename, "status": "success", "message": "Image ingested successfully", "id": doc_id}
        
    elif ext in ["mp3", "wav", "m4a"]:
        text = await run_in_threadpool(process_audio, file_bytes, file.filename)
        if not text:
            logger.warning("No transcript for audio file %s - storing anyway", file.filename)
            text = f"[Audio file: {file.filename} - no speech transcript available]"
        audio_analysis = await describe_audio(text)
        emb = await run_in_threadpool(get_text_embedding, text)
        await run_in_threadpool(
            store_embedding,
            doc_id,
            emb,
            {
                "type": "audio",
                "text": text,
                "transcript": text,
                "audio_analysis": audio_analysis,
                "filename": file.filename,
            }
        )
        return {
            "filename": file.filename,
            "status": "success",
            "message": "Audio ingested successfully",
            "id": doc_id,
            "transcription": text,
            "audio_analysis": audio_analysis,
        }
        
    else:
        return {"filename": file.filename, "status": "error", "message": f"Unsupported file format: .{ext}"}

# Keep the single-file endpoint for backward compatibility
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        result = await _process_single_file(file)
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-batch")
async def upload_batch(files: List[UploadFile] = File(...)):
    """Upload multiple files at once. Each file is processed independently."""
    from .embed import index
    if index is not None:
        try:
            index.delete(delete_all=True)
            logger.info("Cleared Pinecone index before new batch.")
        except Exception as e:
            logger.warning(f"Failed to clear Pinecone index: {e}")

    results = []
    for file in files:
        try:
            result = await _process_single_file(file)
            results.append(result)
        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "error",
                "message": str(e)
            })
    
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = sum(1 for r in results if r["status"] == "error")
    
    return {
        "summary": f"{success_count}/{len(results)} files ingested successfully",
        "success_count": success_count,
        "error_count": error_count,
        "total": len(results),
        "results": results
    }

@app.post("/query")
@limiter.limit("10/minute")
async def query(request: Request, query_text: str = Form(...), image: UploadFile | None = File(None)):
    ALLOWED_IMAGE_TYPES = {"png", "jpg", "jpeg"}
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

    if image is not None:
        ext = image.filename.split(".")[-1].lower() if image.filename and "." in image.filename else ""
        if ext not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported image format. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}")

        image.seek(0, 2)
        size = image.tell()
        image.seek(0)
        if size > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail=f"Image too large. Max size: 10MB")

    try:
        if not query_text or not query_text.strip():
            raise HTTPException(status_code=400, detail="Query text cannot be empty")

        image_analysis = ""
        if image is not None:
            logger.info("Processing attached image for query analysis")
            img_bytes = await image.read()
            image_analysis = await generate_diagnosis(query_text, image_bytes=img_bytes)
            logger.info("Image analysis completed, length: %d", len(image_analysis))

        result = query_system(query_text, image_analysis=image_analysis)
        hit_counts = result.get("hit_counts", {})
        logger.info(
            "Query hit counts: text/audio=%s image=%s graph=%s",
            hit_counts.get("text_audio", 0),
            hit_counts.get("image", 0),
            hit_counts.get("graph", 0),
        )

        if not result.get("response"):
            result["response"] = "No response generated. Please try again."

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error processing query")
        return {
            "error": True,
            "response": f"An error occurred during analysis: {str(e)}",
            "vector_context": "",
            "graph_context": "",
            "hit_counts": {"text_audio": 0, "image": 0, "graph": 0},
            "image_context_enabled": False,
        }


@app.get("/graph")
async def graph():
    return get_graph_data()


@app.get("/health")
async def health():
    from .retrieve import _vector_count
    
    cwd = os.getcwd()
    total, used, free = shutil.disk_usage(cwd)
    disk = {
        "path": cwd,
        "total_bytes": total,
        "used_bytes": used,
        "free_bytes": free,
        "free_gb": round(free / (1024 ** 3), 2),
        "low_space": free < 2 * 1024 * 1024 * 1024,  # 2GB threshold
    }

    embedding_status = get_embedding_backend_status()
    audio_status = get_audio_backend_status()
    generation_status = get_generation_backend_status()
    
    vector_count = _vector_count()
    
    models_status = {
        "text_embedder": embedding_status["models"]["text"] == "loaded",
        "image_embedder": embedding_status["models"]["image"] == "loaded",
        "whisper": audio_status["whisper_model"] == "loaded",
    }
    
    pinecone_connected = (
        embedding_status["pinecone"]["configured"] and 
        embedding_status["pinecone"]["index_connected"]
    )
    
    degraded = (
        disk["low_space"]
        or not pinecone_connected
        or not generation_status["openrouter"]["client_initialized"]
    )

    return {
        "status": "degraded" if degraded else "ok",
        "models": models_status,
        "pinecone": pinecone_connected,
        "vector_count": vector_count,
    }
