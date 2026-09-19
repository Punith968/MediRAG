import os
import io
import logging
import base64

from dotenv import load_dotenv
from PIL import Image

from .embed import get_text_embedding, index
from .graph import get_context
from .core.retrieval import rerank as core_rerank
from .providers import OpenRouterProvider

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

generation_provider = OpenRouterProvider(
    api_key=OPENROUTER_API_KEY,
    model=OPENROUTER_MODEL,
)
_ai_ready = generation_provider.configured

logger = logging.getLogger(__name__)
MEDICAL_DISCLAIMER = (
    "This is an AI-generated analysis and is not a substitute for professional "
    "medical advice, diagnosis, or treatment. Please consult a qualified clinician."
)
UNUSABLE_TRANSCRIPT_PREFIXES = (
    "Audio transcription is currently unavailable",
    "Error: OpenRouter API Key not configured",
)


# ---------------------------------------------------------------------------
# Pinecone query helpers
# ---------------------------------------------------------------------------

def _vector_count() -> int:
    if index is None:
        return 0
    try:
        return int(index.count() or 0)
    except Exception as exc:
        logger.warning("Unable to read Pinecone vector count: %s", exc)
        return 0


def _ensure_disclaimer(response_text: str) -> str:
    response_text = response_text.strip()
    if response_text.endswith(MEDICAL_DISCLAIMER):
        return response_text
    return f"{response_text}\n\n{MEDICAL_DISCLAIMER}"


# ---------------------------------------------------------------------------
# OpenRouter Generation
# ---------------------------------------------------------------------------

def _generate_content(parts):
    """Generate content via OpenRouter (OpenAI SDK format).
    parts can be a string, or a list containing strings and PIL Images.
    """
    if not _ai_ready:
        return None

    if not isinstance(parts, list):
        parts = [parts]

    messages_content = []
    for part in parts:
        if isinstance(part, str):
            messages_content.append({"type": "text", "text": part})
        elif isinstance(part, Image.Image):
            # Convert PIL image to base64
            buffered = io.BytesIO()
            # Convert to RGB to ensure JPEG compatibility if needed, but PNG is safe
            img = part.convert("RGB") if part.mode != "RGB" else part
            img.save(buffered, format="PNG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            messages_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_b64}"
                }
            })

    try:
        generated_text = generation_provider.generate(
            messages=[{"role": "user", "content": messages_content}],
            timeout=30.0,
        )
        class _MockResponse:
            def __init__(self, text):
                self.text = text
        return _MockResponse(generated_text)
    except Exception as exc:
        logger.warning("OpenRouter generation failed: %s", exc)
        error_msg = str(exc).lower()
        if "timeout" in error_msg:
            raise Exception("The LLM API request timed out. Please try again later.") from exc
        elif "404" in error_msg or "not found" in error_msg:
            raise Exception("The configured LLM model was not found. Please check your model settings.") from exc
        elif "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg:
            raise Exception("The LLM API rate limit or quota has been exceeded.") from exc
        else:
            raise Exception(f"The LLM API encountered an error: {exc}") from exc


# ---------------------------------------------------------------------------
# Pinecone retrieval helpers
# ---------------------------------------------------------------------------

def _metadata_type(metadata: dict) -> str:
    return str(metadata.get("type") or metadata.get("modality") or "").lower()


def _normalize_text(text: str) -> str:
    return " ".join((text or "").split()).strip().lower()


def rerank(query_embedding, results):
    return core_rerank(query_embedding, results)

def _fetch_embeddings_for_results(hits: list[dict]) -> list[dict]:
    """Fetch embeddings from Pinecone for results that don't have them."""
    if index is None or not hits:
        return hits
    
    doc_ids = [h.get("metadata", {}).get("id") or h.get("id", "") for h in hits]
    doc_ids = [did for did in doc_ids if did]
    
    if not doc_ids:
        return hits
    
    try:
        fetch_response = index.fetch(doc_ids)
        fetched_vectors = fetch_response.get("vectors", {})
    except Exception as exc:
        logger.warning("Failed to fetch embeddings from Pinecone: %s", exc)
        return hits
    
    result_with_embeddings = []
    for hit in hits:
        doc_id = hit.get("metadata", {}).get("id") or hit.get("id", "")
        if doc_id and doc_id in fetched_vectors:
            emb = fetched_vectors[doc_id].get("values")
            if emb:
                result_with_embeddings.append({**hit, "embedding": emb})
                continue
        result_with_embeddings.append(hit)
    
    return result_with_embeddings


def _search(query_vector: list[float], top_k: int, allowed_types: set[str]) -> list[dict]:
    """Query Pinecone and return filtered, de-duplicated hits as plain dicts."""
    if index is None:
        return []

    count = _vector_count()
    if count == 0:
        return []

    # Query a larger candidate pool so one modality cannot starve another.
    n_results = min(max(top_k * 20, top_k), count)
    if n_results <= 0:
        return []

    allowed_types_list = sorted(allowed_types)
    try:
        results = index.query(
            vector=query_vector,
            top_k=n_results,
            include_metadata=True,
            filter={"type": {"$in": allowed_types_list}},
        )
    except Exception as exc:
        logger.warning(
            "Filtered Pinecone query failed, falling back to unfiltered: %s", exc
        )
        try:
            results = index.query(
                vector=query_vector,
                top_k=n_results,
                include_metadata=True,
            )
        except Exception as exc2:
            logger.error("Pinecone query failed entirely: %s", exc2)
            return []

    hits = []
    # pinecone>=3 returns QueryResponse with .matches (list of ScoredVector)
    for match in results.matches:
        # match is a ScoredVector: .id, .score, .metadata
        metadata: dict = match.metadata or {}
        modality = _metadata_type(metadata)
        if allowed_types and modality not in allowed_types:
            continue

        text = (
            metadata.get("text")
            or metadata.get("transcript")
            or metadata.get("image_analysis")
            or ""
        )
        if not text.strip():
            logger.info(
                "Skipping empty %s hit from %s",
                modality or "unknown",
                metadata.get("filename", "Unknown"),
            )
            continue
        if any(text.strip().startswith(p) for p in UNUSABLE_TRANSCRIPT_PREFIXES):
            logger.info(
                "Skipping unusable %s hit from %s",
                modality or "unknown",
                metadata.get("filename", "Unknown"),
            )
            continue

        logger.info(
            "Retrieved %s hit (score=%.4f) from %s: %s",
            modality or "unknown",
            match.score or 0.0,
            metadata.get("filename", "Unknown"),
            text[:100],
        )

        hits.append(
            {
                "id": match.id,
                "text": text,
                "metadata": {**metadata, "id": match.id},
                "score": match.score,
            }
        )

    return hits


def search_text(query_vector: list[float], top_k: int = 3) -> list[dict]:
    hits = _search(query_vector, top_k, {"text", "audio"})
    return _fetch_embeddings_for_results(hits)


def search_images(query_vector: list[float], top_k: int = 3) -> list[dict]:
    hits = _search(query_vector, top_k, {"image"})
    return _fetch_embeddings_for_results(hits)


# ---------------------------------------------------------------------------
# Gemini-powered analysis helpers (public API consumed by main.py)
# ---------------------------------------------------------------------------

async def generate_diagnosis(query_text: str, image_bytes: bytes | None = None) -> str:
    prompt = f"""
Analyze the clinical information below.

User Query:
{query_text}

If an attached medical image is provided, analyze the visible findings in the image.
Provide:
1. Visible medical image findings, when an image is attached
2. Top 3 differential diagnoses
3. Recommended next steps
4. Confidence level

Always end with this medical disclaimer:
{MEDICAL_DISCLAIMER}
"""

    if not _ai_ready:
        return "Error: OpenRouter API Key not configured. Please set OPENROUTER_API_KEY."

    try:
        if image_bytes:
            image = Image.open(io.BytesIO(image_bytes))
            response = _generate_content([image, prompt])
        else:
            response = _generate_content(prompt)
    except Exception as exc:
        logger.exception("Diagnosis generation failed")
        return _ensure_disclaimer(
            f"AI could not generate an analysis for this request. Technical detail: {exc}"
        )

    if response is None:
        return "Error: OpenRouter API Key not configured. Please set OPENROUTER_API_KEY."
    return _ensure_disclaimer(response.text)


async def describe_image(image_bytes: bytes) -> str:
    return await generate_diagnosis(
        "Analyze this uploaded medical image and summarize the visible findings for later retrieval.",
        image_bytes=image_bytes,
    )


async def describe_audio(transcript: str) -> str:
    cleaned = (transcript or "").strip()
    if not cleaned:
        return "No clear spoken transcript detected in this audio file."
    if any(cleaned.startswith(p) for p in UNUSABLE_TRANSCRIPT_PREFIXES):
        return cleaned
    if not _ai_ready:
        return "Error: OpenRouter API Key not configured. Please set OPENROUTER_API_KEY."

    prompt = f"""
You are an expert medical AI assistant.
Analyze the following transcript from an uploaded audio note and summarize medically relevant findings.

Audio Transcript:
{cleaned}

Provide:
1. Key reported symptoms/signs from the transcript
2. Top 3 differential diagnoses (based only on transcript content)
3. Recommended next steps
4. Confidence level

Always end with this medical disclaimer:
{MEDICAL_DISCLAIMER}
"""
    try:
        response = _generate_content(prompt)
    except Exception as exc:
        logger.exception("Audio analysis generation failed")
        return _ensure_disclaimer(
            f"AI could not generate an audio analysis. Technical detail: {exc}"
        )

    if response is None:
        return "Error: OpenRouter API Key not configured. Please set OPENROUTER_API_KEY."
    return _ensure_disclaimer(response.text)


def _describe_audio_sync(transcript: str) -> str:
    """Synchronous variant used inside query_system for already-stored audio hits."""
    cleaned = (transcript or "").strip()
    if not cleaned or any(cleaned.startswith(p) for p in UNUSABLE_TRANSCRIPT_PREFIXES):
        return ""
    if not _ai_ready:
        return ""

    prompt = f"""
You are an expert medical AI assistant.
Analyze the following transcript from an uploaded audio note and summarize medically relevant findings.

Audio Transcript:
{cleaned}

Provide:
1. Key reported symptoms/signs from the transcript
2. Top 3 differential diagnoses (based only on transcript content)
3. Recommended next steps
4. Confidence level

Always end with this medical disclaimer:
{MEDICAL_DISCLAIMER}
"""
    try:
        response = _generate_content(prompt)
        if response is None:
            return ""
        return _ensure_disclaimer(response.text)
    except Exception as exc:
        logger.exception("Sync audio analysis generation failed")
        return ""


# ---------------------------------------------------------------------------
# Provenance helpers
# ---------------------------------------------------------------------------

def build_provenance(text_hits: list[dict], image_hits: list[dict]) -> list[dict]:
    """Return compact source metadata for clients that need answer provenance."""
    sources = []
    seen_ids: set[str] = set()

    for hit in [*text_hits, *image_hits]:
        metadata = hit.get("metadata") or {}
        source_id = str(metadata.get("id") or hit.get("id") or "")
        if not source_id or source_id in seen_ids:
            continue
        seen_ids.add(source_id)

        modality = _metadata_type(metadata).upper() or "UNKNOWN"
        source = {
            "id": source_id,
            "filename": metadata.get("filename", "Unknown source"),
            "modality": modality,
        }
        if hit.get("score") is not None:
            source["retrieval_score"] = float(hit["score"])
        if hit.get("rerank_score") is not None:
            source["rerank_score"] = float(hit["rerank_score"])
        sources.append(source)

    return sources

# ---------------------------------------------------------------------------
# Main query pipeline
# ---------------------------------------------------------------------------

def query_system(query_text: str, top_k: int = 3, image_analysis: str | None = None) -> dict:
    query_vector = get_text_embedding(query_text)

    text_hits = search_text(query_vector, top_k)
    image_hits = search_images(query_vector, top_k)

    text_hits = rerank(query_vector, text_hits)
    image_hits = rerank(query_vector, image_hits)

    logger.info(
        "Query retrieved %d text/audio hits and %d image hits (reranked).",
        len(text_hits),
        len(image_hits),
    )

    context_blocks: list[str] = []
    seen_context_keys: set[str] = set()

    def _append_context(header: str, body: str) -> None:

        normalized_body = _normalize_text(body)
        if not normalized_body:
            return
        context_key = f"{header}|{normalized_body}"
        if context_key in seen_context_keys:
            return
        seen_context_keys.add(context_key)
        context_blocks.append(f"{header}\n{body.strip()}")

    if image_analysis:
        _append_context("[AI IMAGE ANALYSIS]", image_analysis)

    seen_image_filenames: set[str] = set()
    for hit in image_hits:
        filename = hit.get("metadata", {}).get("filename", "Unknown")
        if filename in seen_image_filenames:
            continue
        seen_image_filenames.add(filename)
        text = hit.get("text", "")
        if text:
            _append_context("[AI IMAGE ANALYSIS]", text)

    seen_filenames: set[str] = set()

    for hit in text_hits:
        metadata = hit.get("metadata", {})
        modality = _metadata_type(metadata).upper() or "TEXT"
        filename = metadata.get("filename", "Unknown source")
        filename_key = f"{modality}|{filename}"

        if filename_key in seen_filenames:
            continue
        seen_filenames.add(filename_key)

        if modality == "AUDIO":
            audio_analysis = metadata.get("audio_analysis", "")
            if not audio_analysis:
                audio_analysis = _describe_audio_sync(hit.get("text", ""))
            if audio_analysis:
                _append_context(f"[AI AUDIO ANALYSIS — {filename}]", str(audio_analysis))
        elif modality == "IMAGE":
            _append_context(f"[IMAGE — {filename}]", hit.get("text", ""))
        else:
            _append_context(f"[{modality} — {filename}]", hit.get("text", ""))

    # Fuse graph context with vector context ONLY for prompt
    pure_vector_context_str = "\n\n".join(context_blocks) if context_blocks else ""

    graph_result = get_context(query_text)
    graph_context_str = graph_result["context"]

    prompt_context_blocks = context_blocks.copy()
    if graph_result["has_matches"]:
        prompt_context_blocks.insert(0, f"[MEDICAL KNOWLEDGE GRAPH - PRIORITY SYMPTOM MATCH]\n{graph_context_str}")
    else:
        prompt_context_blocks.append(f"[MEDICAL KNOWLEDGE GRAPH]\n{graph_context_str}")
        
    prompt_context_str = "\n\n".join(prompt_context_blocks) if prompt_context_blocks else ""

    prompt = f"""
You are an expert medical AI assistant. Analyze the user's query based on the retrieved context.

User Query: {query_text}

Retrieved Multimodal Context:
{prompt_context_str if prompt_context_str else "None"}

Provide a comprehensive, medically coherent diagnostic response based strictly on the provided context.
If the context does not contain enough information, state so clearly.
IMPORTANT: Conclude with this disclaimer: {MEDICAL_DISCLAIMER}
"""

    if _ai_ready:
        try:
            response = _generate_content(prompt)
            if response is None:
                response_text = "Error: OpenRouter API Key not configured. Please set OPENROUTER_API_KEY."
            else:
                response_text = _ensure_disclaimer(response.text)
        except Exception as exc:
            logger.exception("Query generation failed")
            response_text = _ensure_disclaimer(
                f"I could not generate a response for this query. Technical detail: {exc}"
            )
    else:
        response_text = "Error: OpenRouter API Key not configured. Please set OPENROUTER_API_KEY."

    provenance = build_provenance(text_hits, image_hits)

    return {
        "query": query_text,
        "vector_context": pure_vector_context_str,
        "sources": provenance,
        "graph_context": graph_context_str,
        "image_analysis": image_analysis or "",
        "image_context_enabled": True,
        "hit_counts": {
            "text_audio": len(text_hits),
            "image": len(image_hits),
            "graph": 1 if graph_result["has_matches"] else 0,
        },
        "response": response_text,
    }


# ---------------------------------------------------------------------------
# Status helper
# ---------------------------------------------------------------------------

def get_generation_backend_status() -> dict:
    return {
        "openrouter": {
            "configured": bool(OPENROUTER_API_KEY),
            "model": OPENROUTER_MODEL,
            "client_initialized": _ai_ready,
        },
    }
