import hashlib
import logging
import os
import threading

import numpy as np
import torch
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from .vector_store import PineconeVectorStore
from sentence_transformers import SentenceTransformer
from transformers import CLIPModel, CLIPProcessor

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_ENV = os.getenv("PINECONE_ENV", "us-east-1")
INDEX_NAME = "medirag"
# All embeddings are stored at 512 dimensions:
#   - CLIP (openai/clip-vit-base-patch32) natively produces 512-d vectors.
#   - MiniLM (all-MiniLM-L6-v2) produces 384-d vectors, zero-padded then
#     re-normalised to 512-d so cosine similarity remains well-defined.
INDEX_DIMENSION = 512

device = "cuda" if torch.cuda.is_available() else "cpu"
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pinecone initialisation
# ---------------------------------------------------------------------------
_pc: Pinecone | None = None
index = None

if PINECONE_API_KEY:
    try:
        _pc = Pinecone(api_key=PINECONE_API_KEY)
        existing_indexes = [idx.name for idx in _pc.list_indexes()]
        if INDEX_NAME not in existing_indexes:
            _pc.create_index(
                name=INDEX_NAME,
                dimension=INDEX_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region=PINECONE_ENV),
            )
        index = PineconeVectorStore(_pc.Index(INDEX_NAME))
        logger.info("Pinecone index '%s' connected (dim=%d).", INDEX_NAME, INDEX_DIMENSION)
    except Exception as e:
        logger.warning("Pinecone initialisation failed: %s", e)
        index = None
else:
    logger.warning("PINECONE_API_KEY not set — vector store disabled.")

_model_lock = threading.Lock()
_text_model = None
_clip_model = None
_clip_processor = None


# ---------------------------------------------------------------------------
# Fallback embedding (deterministic, reproducible)
# ---------------------------------------------------------------------------

def _deterministic_fallback_embedding(seed_text: str) -> np.ndarray:
    seed = hashlib.sha256(seed_text.encode("utf-8", errors="ignore")).digest()
    values = np.frombuffer(seed * (INDEX_DIMENSION // len(seed) + 1), dtype=np.uint8)[
        :INDEX_DIMENSION
    ].astype(np.float32)
    values = (values / 255.0) - 0.5
    norm = np.linalg.norm(values)
    if norm > 0:
        values = values / norm
    return values


# ---------------------------------------------------------------------------
# Model lazy-loaders
# ---------------------------------------------------------------------------

def _get_text_model():
    global _text_model
    if _text_model is not None:
        return _text_model if _text_model is not False else None
    with _model_lock:
        if _text_model is not None:
            return _text_model if _text_model is not False else None
        try:
            _text_model = SentenceTransformer(
                "sentence-transformers/all-MiniLM-L6-v2", device=device
            )
            logger.info("Text embedding model loaded on %s.", device)
        except Exception as exc:
            logger.warning(
                "Text model unavailable, using deterministic fallback embeddings: %s", exc
            )
            _text_model = False
    return _text_model if _text_model is not False else None


def _get_clip_components():
    global _clip_model, _clip_processor
    if _clip_model is not None and _clip_processor is not None:
        return (
            (_clip_model, _clip_processor)
            if _clip_model is not False
            else (None, None)
        )
    with _model_lock:
        if _clip_model is not None and _clip_processor is not None:
            return (
                (_clip_model, _clip_processor)
                if _clip_model is not False
                else (None, None)
            )
        try:
            _clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(
                device
            )
            _clip_processor = CLIPProcessor.from_pretrained(
                "openai/clip-vit-base-patch32"
            )
            logger.info("CLIP model loaded on %s.", device)
        except Exception as exc:
            logger.warning(
                "CLIP model unavailable, using image-stat fallback embeddings: %s", exc
            )
            _clip_model = False
            _clip_processor = False
    if _clip_model is False or _clip_processor is False:
        return None, None
    return _clip_model, _clip_processor


# ---------------------------------------------------------------------------
# Public embedding functions
# ---------------------------------------------------------------------------

def get_text_embedding(text: str) -> list[float]:
    """Embed text using MiniLM-L6-v2, padded & normalised to INDEX_DIMENSION."""
    text_model = _get_text_model()
    if text_model is None:
        return _deterministic_fallback_embedding(text).tolist()

    try:
        emb = text_model.encode(text, convert_to_numpy=True)  # shape (384,)
        # Zero-pad to INDEX_DIMENSION then re-normalise so cosine sim is valid.
        padded = np.zeros(INDEX_DIMENSION, dtype=np.float32)
        padded[: len(emb)] = emb
        norm = np.linalg.norm(padded)
        if norm > 0:
            padded /= norm
        return padded.tolist()
    except Exception as exc:
        logger.warning(
            "Text embedding failed, falling back to deterministic embedding: %s", exc
        )
        return _deterministic_fallback_embedding(text).tolist()


def get_image_embedding(image) -> list[float]:
    """Embed a PIL Image using CLIP (512-d, already matches INDEX_DIMENSION)."""
    clip_model, clip_processor = _get_clip_components()

    if clip_model is None or clip_processor is None:
        # Fallback: statistical summary of pixel values, tiled to INDEX_DIMENSION.
        image_array = np.asarray(image, dtype=np.float32) / 255.0
        stats = np.array(
            [
                image_array.mean(),
                image_array.std(),
                image_array.min(),
                image_array.max(),
                float(image_array.shape[0]),
                float(image_array.shape[1]),
            ],
            dtype=np.float32,
        )
        repeated = np.resize(stats, INDEX_DIMENSION)
        norm = np.linalg.norm(repeated)
        if norm > 0:
            repeated /= norm
        return repeated.tolist()

    try:
        inputs = clip_processor(images=image, return_tensors="pt").to(device)
        with torch.no_grad():
            image_features = clip_model.get_image_features(**inputs)

        # L2-normalise (standard CLIP practice)
        image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        return image_features.squeeze(0).cpu().numpy().tolist()
    except Exception as exc:
        logger.warning(
            "Image embedding failed, falling back to image-stats embedding: %s", exc
        )
        image_array = np.asarray(image, dtype=np.float32) / 255.0
        stats = np.array(
            [
                image_array.mean(),
                image_array.std(),
                image_array.min(),
                image_array.max(),
                float(image_array.shape[0]),
                float(image_array.shape[1]),
            ],
            dtype=np.float32,
        )
        repeated = np.resize(stats, INDEX_DIMENSION)
        norm = np.linalg.norm(repeated)
        if norm > 0:
            repeated /= norm
        return repeated.tolist()


def store_embedding(doc_id: str, embedding: list[float], metadata: dict) -> None:
    """Upsert a single vector into Pinecone using the v3+ dict format."""
    if index is None:
        logger.info("Pinecone not initialised — skipping upsert for '%s'.", doc_id)
        return

    # Truncate metadata string values so they stay within Pinecone's 40 KB limit.
    safe_metadata: dict = {}
    for k, v in metadata.items():
        if isinstance(v, str) and len(v) > 4000:
            safe_metadata[k] = v[:4000]
        else:
            safe_metadata[k] = v

    try:
        index.upsert(doc_id, embedding, safe_metadata)
        logger.info("Upserted vector '%s' into Pinecone.", doc_id)
    except Exception as exc:
        logger.warning("Pinecone upsert failed for '%s': %s", doc_id, exc)


# ---------------------------------------------------------------------------
# Status helper
# ---------------------------------------------------------------------------

def _model_state(value) -> str:
    if value is False:
        return "failed"
    if value is None:
        return "not_loaded"
    return "loaded"


def get_embedding_backend_status() -> dict:
    return {
        "device": device,
        "pinecone": {
            "configured": bool(PINECONE_API_KEY),
            "index_connected": index is not None,
            "index_name": INDEX_NAME,
            "dimension": INDEX_DIMENSION,
            "region": PINECONE_ENV,
        },
        "models": {
            "text": _model_state(_text_model),
            "image": _model_state(_clip_model),
        },
    }
