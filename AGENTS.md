# MediRAG Agent Guide

## Architecture
- **Frontend**: React 18 + Vite + Tailwind, served via nginx on port 80
- **Backend**: FastAPI + uvicorn on port 8000 (internal)
- **Reverse Proxy**: Nginx routes `/api/` → backend, `/` → frontend
- **Vector Store**: Pinecone (index: `medirag`, dimension: 512)
- **Cache**: Redis (port 6379)
- **ML Models**: Sentence-transformers (MiniLM), CLIP, OpenAI Whisper
- **LLM**: OpenRouter (google/gemini-2.0-flash-001)

## Running the Project

### Full stack (requires GPU)
```bash
docker-compose up --build
```
- Access: **http://localhost** (single entry point via nginx)
- API: `/api/*` (proxied to backend:8000)
- Health: `/api/health`

### Frontend only (development)
```bash
cd frontend && npm run dev
```
Dev server runs on port **5173**.

### Backend only (requires PINECONE_API_KEY in .env)
```bash
cd backend && source venv/bin/activate && uvicorn app.main:app --reload
```

## Environment Variables
Required in `.env`:
- `PINECONE_API_KEY` — vector database
- `PINECONE_ENV` — region (default: us-east-1)
- `OPENROUTER_API_KEY` — LLM access
- `OPENROUTER_MODEL` — model ID (default: `google/gemini-2.0-flash-001`)
- `CORS_ORIGINS` — comma-separated (default: `http://localhost`)
- `REDIS_URL` — Redis URL (default: `redis://redis:6379`)

## Features

- **Rate limiting**: 10 requests/minute on `/api/query` (SlowAPI)
- **Redis caching**: Query responses cached for 1 hour
- **File validation**: Max 20MB, allowed: pdf/txt/png/jpg/jpeg/mp3/wav/m4a
- **D3.js knowledge graph**: Force-directed visualization at page load

## Utility Scripts
- `clear_pinecone.py` — reset the vector index
- `list_models.py` — list available Whisper/CLIP models

## Critical Quirks

1. **Do NOT add torch/torchvision/torchaudio to requirements.txt** — they are pre-installed in the base image (`pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime`). Adding them will overwrite the CUDA build with a CPU build.

2. **Whisper must be installed before requirements.txt** — the Dockerfile installs `openai-whisper` first so its torch dependency resolves against the pre-installed CUDA build.

3. **Embedding dimension is 512** — MiniLM produces 384-d vectors, zero-padded to 512 for Pinecone compatibility.

4. **Audio processing requires ffmpeg** — the code falls back to `imageio-ffmpeg` if system ffmpeg is unavailable.

5. **Health endpoint returns detailed status** — `/api/health` reports disk space, Pinecone connectivity, Whisper/CLIP model states, and OpenRouter client status.

## API Endpoints (via /api/)
- `POST /api/upload` — single file upload
- `POST /api/upload-batch` — multiple files, clears Pinecone index first
- `POST /api/query` — RAG query with optional image
- `GET /api/graph` — knowledge graph data
- `GET /api/health` — system status

## No Formal Tests
No test framework is configured. Test via manual API calls or curl.