# MediRAG

Multi-Modal Graph-Based RAG for Medical Diagnostics

## Features

- **Multi-modal ingestion**: PDF, images (PNG/JPG), and audio (MP3/WAV/M4A)
- **Vector search**: Pinecone for semantic similarity search
- **Knowledge graph**: NetworkX-based medical symptom relationships
- **LLM-powered analysis**: Gemini 2.0 Flash via OpenRouter
- **Rate limiting**: 10 requests/minute on /query endpoint
- **Redis caching**: Query response caching with 1hr expiry
- **Nginx reverse proxy**: Single entry point for all services

## Quick Start

### Prerequisites

- Docker with GPU support (NVIDIA GPU)
- Docker Compose
- API keys in `.env` file

### Environment Variables

Create a `.env` file:

```env
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENV=us-east-1
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=google/gemini-2.0-flash-001
CORS_ORIGINS=http://localhost
REDIS_URL=redis://redis:6379
```

### Run with Docker

```bash
docker-compose up --build
```

Access the application at **http://localhost**

- Frontend: `/` (all paths except `/api/*`)
- Backend API: `/api/*` (proxied to backend:8000)
- Health check: `/api/health`

### Development

**Frontend only:**
```bash
cd frontend && npm run dev
```

**Backend only:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload single file |
| `/api/upload-batch` | POST | Upload multiple files |
| `/api/query` | POST | RAG query with optional image |
| `/api/graph` | GET | Knowledge graph data |
| `/api/health` | GET | System status |

## Supported File Types

- **Documents**: PDF, TXT
- **Images**: PNG, JPG, JPEG
- **Audio**: MP3, WAV, M4A

File size limit: 20MB

## Tech Stack

- **Backend**: FastAPI, Python, SlowAPI (rate limiting), Redis (caching)
- **Frontend**: React 18, Vite, Tailwind, D3.js
- **Reverse Proxy**: Nginx
- **Vector DB**: Pinecone (512-dim)
- **Cache**: Redis
- **ML Models**: MiniLM (text), CLIP (image), Whisper (audio)
- **LLM**: Gemini 2.0 Flash via OpenRouter
- **Graph**: NetworkX

## Branching Strategy

- `main` — stable production builds  
- `feature/multimodal-ingestion` — ingestion pipeline  
- `feature/graph-rag` — knowledge graph layer  
- `feature/frontend-ui` — React frontend