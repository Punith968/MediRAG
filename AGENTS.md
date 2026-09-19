# MediRAG Development Guide

## Architecture
- **Frontend**: React 18 + Vite + Tailwind, served via nginx
- **Backend**: FastAPI + uvicorn
- **Reverse Proxy**: Nginx routes frontend traffic and `/api/` to the backend
- **Vector Store**: Pinecone (current integration)
- **Cache**: Redis
- **ML Models**: Sentence-transformers (MiniLM), CLIP, OpenAI Whisper
- **LLM**: OpenRouter

## Running the project

### Full stack
```bash
docker compose up --build
```

The default deployment exposes the application through nginx at `http://localhost`.

### Frontend development
```bash
cd frontend
npm install
npm run dev
```

### Backend development
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Environment

Configure a local `.env` with the credentials required by the active integrations:

- `PINECONE_API_KEY`
- `PINECONE_ENV`
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `CORS_ORIGINS`
- `REDIS_URL`

Never commit secrets or real patient/clinical data.

## API

- `POST /api/upload` — single file upload
- `POST /api/upload-batch` — multiple file upload
- `POST /api/query` — RAG query with optional image
- `GET /api/graph` — knowledge graph data
- `GET /api/health` — service health

Supported uploads currently include PDF, TXT, PNG, JPG/JPEG, MP3, WAV, and M4A. The upload limit is 20 MB.

## Testing

Backend tests live under `backend/tests/`.

Run them with:

```bash
cd backend
pip install pytest
pytest -q
```

The GitHub Actions quality workflow also runs the backend test suite.

## Implementation notes

1. Do not add a second Torch installation to the GPU Docker image; the image provides the intended PyTorch build.
2. Whisper is installed before the main requirements in the GPU Dockerfile so its Torch dependency resolves against the image's Torch build.
3. The current Pinecone integration uses a 512-dimensional index; the embedding pipeline adapts model output to that dimension.
4. Audio processing requires ffmpeg; the project includes a Python fallback dependency.
5. The health endpoint reports model, vector-store, and runtime status.

## Contribution workflow

1. Pick an open issue or propose a focused change.
2. Create a feature branch.
3. Add or update tests for behavioral changes.
4. Update documentation when public behavior changes.
5. Open a pull request using the repository template.

Keep changes small and independently reviewable.
