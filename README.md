# MediRAG

[![Quality](https://github.com/Punith968/MediRAG/actions/workflows/quality.yml/badge.svg)](https://github.com/Punith968/MediRAG/actions/workflows/quality.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Python 3.11](https://img.shields.io/badge/python-3.11-blue)
![React 18](https://img.shields.io/badge/react-18-61dafb)

**Multimodal Graph-Based RAG for medical-research and clinical-information workflows.**

MediRAG is an open-source reference implementation for combining multimodal document ingestion, vector retrieval, knowledge graphs, and LLM-assisted synthesis. It is intended for research, prototyping, and developer experimentation—not autonomous medical diagnosis.

## Why MediRAG?

Traditional RAG systems often treat documents as isolated text chunks. MediRAG explores a richer pipeline:

**documents + images + audio → multimodal representations → vector retrieval + graph context → LLM synthesis**

The project is designed so retrieval backends, model providers, and ingestion components can evolve independently.

## Current capabilities

- PDF/TXT document ingestion
- PNG/JPG image ingestion
- MP3/WAV/M4A audio ingestion
- Semantic vector search with Pinecone
- NetworkX-based knowledge graph
- Text embeddings with MiniLM
- Image embeddings with CLIP
- Audio processing with Whisper
- LLM integration through OpenRouter
- Redis response caching
- API rate limiting
- FastAPI backend
- React/Vite frontend
- Docker Compose deployment
- Nginx reverse proxy

## Architecture

```
                    ┌─────────────────────┐
                    │  Documents / Media  │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Multimodal Ingestor │
                    └───────┬─────┬───────┘
                            │     │
                 ┌──────────▼─┐ ┌─▼─────────────┐
                 │ Embeddings │ │ Knowledge     │
                 │ text/image │ │ Graph         │
                 │ /audio     │ │ NetworkX      │
                 └──────┬─────┘ └──────┬────────┘
                        │               │
                        └───────┬───────┘
                                ▼
                     ┌────────────────────┐
                     │ Retrieval + Graph  │
                     │ Context Assembly   │
                     └─────────┬──────────┘
                               ▼
                     ┌────────────────────┐
                     │ LLM Synthesis      │
                     └─────────┬──────────┘
                               ▼
                     ┌────────────────────┐
                     │ FastAPI / React UI │
                     └────────────────────┘
```

## Tech stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI, uvicorn, slowapi (rate limiting) |
| Text embeddings | sentence-transformers (MiniLM) |
| Image embeddings | CLIP |
| Audio transcription | OpenAI Whisper |
| Vector store | Pinecone (behind a `VectorStore` protocol) |
| Knowledge graph | NetworkX |
| LLM | OpenRouter (behind a `GenerationProvider` protocol) |
| Cache | Redis |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS |
| Deployment | Docker Compose (GPU and CPU profiles), Nginx |

## Quick start

### Prerequisites

- Docker and Docker Compose
- NVIDIA GPU is currently recommended for the full multimodal stack
- API credentials for the configured vector database and LLM provider

Copy the example environment file and configure credentials:

```bash
cp .env.example .env
docker compose up --build
```

The application exposes the frontend at `http://localhost` and the API under `/api`.

### Local development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

No GPU? Use the CPU profile: `docker compose -f docker-compose.cpu.yml up --build` (see [docs/CPU_DEVELOPMENT.md](docs/CPU_DEVELOPMENT.md)).

See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for additional setup information.

### Running tests

```bash
cd backend
pip install -r requirements.txt pytest
PYTHONPATH=. pytest -q
```

The suite covers retrieval helpers, retrieval evaluation metrics (recall@k, precision@k), input validation, the provider and vector-store contracts, and the health endpoint. It runs on every push and pull request through GitHub Actions, alongside a production build of the frontend.

### Utility scripts

- `scripts/clear_pinecone.py` deletes every vector in the `medirag` Pinecone index. It is destructive, so use it only on a development index.
- `samples/test-tone.wav` is a short audio clip for manually testing audio ingestion.

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/upload` | POST | Upload one file |
| `/api/upload-batch` | POST | Upload multiple files |
| `/api/query` | POST | Run a RAG query |
| `/api/graph` | GET | Retrieve graph data |
| `/api/health` | GET | Service health check |

Supported file types currently include PDF, TXT, PNG, JPG/JPEG, MP3, WAV, and M4A. The current upload limit is 20 MB.

## Roadmap

- [x] Provider-agnostic LLM interface (`GenerationProvider` protocol)
- [x] Pluggable vector-store interface (`VectorStore` protocol)
- [x] CPU-only development profile
- [x] Retrieval evaluation metrics (recall@k, precision@k)
- [x] Automated tests for retrieval, validation and provider contracts in CI
- [ ] Local/offline LLM inference profile
- [ ] End-to-end RAG benchmark suite on a public dataset
- [ ] Automated test coverage for multimodal ingestion
- [ ] Better citation/provenance tracking
- [ ] Streaming responses
- [ ] Multilingual document support
- [ ] CLI for indexing and querying
- [ ] Python package for reusable core components

## Contributing

Contributions are welcome. Start with the [contribution guide](CONTRIBUTING.md), check existing issues, and open an issue before substantial architectural changes.

Good areas for contribution include ingestion adapters, retrieval backends, provider integrations, evaluation, testing, documentation, and developer tooling.

## Security

Never commit API keys, credentials, private certificates, or real patient/clinical data. See [SECURITY.md](SECURITY.md) for reporting guidance.

## Medical-safety disclaimer

MediRAG is a research and software-engineering project. Generated output can be incorrect, incomplete, or misleading. It must not be treated as a medical diagnosis or as a substitute for a qualified healthcare professional. Do not use real patient data unless you have an appropriate lawful and secure workflow.

## License

MIT
