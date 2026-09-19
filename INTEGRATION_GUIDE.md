# MediRAG Development & Integration Guide

MediRAG is a research-oriented multimodal RAG application. This guide covers the supported development path and the project's current architecture.

## Architecture

```
Documents / Images / Audio
          │
          ▼
   Multimodal ingestion
          │
          ├── text / image embeddings
          ├── audio transcription
          └── knowledge graph
          │
          ▼
 Vector retrieval + graph context
          │
          ▼
      LLM synthesis
          │
          ▼
      FastAPI API
          │
          ▼
       React UI
```

## Local development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Full stack

```bash
cp .env.example .env
docker compose up --build
```

The full multimodal stack currently targets a CUDA-enabled environment. Local CPU development is being tracked as an open roadmap item.

## Required configuration

The active integrations may require:

- `PINECONE_API_KEY`
- `PINECONE_ENV`
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `REDIS_URL`
- `CORS_ORIGINS`

Do not commit credentials or real clinical/patient information.

## API

| Endpoint | Method | Description |
|---|---|---|
| `/api/upload` | POST | Ingest one supported file |
| `/api/upload-batch` | POST | Ingest multiple supported files |
| `/api/query` | POST | Run a RAG query, optionally with an image |
| `/api/graph` | GET | Return knowledge-graph data |
| `/api/health` | GET | Return service health information |

Supported uploads: PDF, TXT, PNG, JPG/JPEG, MP3, WAV, and M4A. Maximum upload size is currently 20 MB.

## Testing

Backend tests are located in `backend/tests/`.

```bash
cd backend
pip install pytest
pytest -q
```

GitHub Actions also runs the backend tests as part of the quality workflow.

## Open-source development priorities

The project is intentionally moving from an application-first architecture toward reusable open-source components.

Planned areas include:

1. Provider interfaces for LLMs.
2. Vector-store abstraction.
3. RAG evaluation and benchmark tooling.
4. More isolated ingestion/retrieval tests.
5. Provenance and citation tracking.
6. CPU-friendly development profile.
7. Reusable Python package and CLI.

See the repository issues for focused contribution opportunities.

## Safety

MediRAG is not a medical device or diagnostic system. Generated answers may be wrong or incomplete and must not replace qualified medical advice. Use only lawful, appropriately protected data in any real-world deployment.

