# Contributor Onboarding

Welcome to MediRAG. This guide is for contributors who want to fix bugs, improve tests, add integrations, or work on retrieval.

## Development

### CPU development

If you do not have an NVIDIA GPU:

```bash
docker compose -f docker-compose.cpu.yml up --build
```

See `docs/CPU_DEVELOPMENT.md` for limitations.

### Local Python development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

Focused unit tests are designed to run without external API credentials.

## Repository structure

```text
backend/
  app/
    main.py          FastAPI routes and orchestration
    embed.py         embedding/model and vector-store wiring
    retrieve.py      retrieval, reranking, provenance, generation
    graph.py         knowledge-graph context
    providers.py     LLM provider abstraction
    vector_store.py  vector-store abstraction
    evaluation.py    deterministic retrieval metrics
  tests/             backend unit tests
frontend/             React/Vite client
docs/                 contributor and development documentation
```

## Configuration

Copy `.env.example` to `.env`. Never commit `.env` or real credentials.

## Testing

Before opening a pull request:

```bash
cd backend
pytest -q
python -m compileall -q .
```

Add focused tests when changing validation, retrieval, providers, vector stores, or evaluation logic.

## Pull requests

A useful PR should explain the problem, describe the implementation, include tests, avoid unrelated changes, document configuration changes, and call out limitations.

## Architecture principles

MediRAG favors small interfaces around external dependencies. New providers, vector stores, and evaluation components should be independently testable and should not require frontend changes.

## Safety

Do not add real patient information, private clinical records, credentials, or sensitive data to the repository or test fixtures.
