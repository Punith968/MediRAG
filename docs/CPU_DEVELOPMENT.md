# CPU Development Profile

This profile is intended for contributors who do not have an NVIDIA GPU.

## Start

From the repository root:

```bash
docker compose -f docker-compose.cpu.yml up --build
```

The backend remains API-compatible with the normal development stack. GPU-specific model acceleration is not required for the development profile; PyTorch and the embedding libraries use their CPU fallback path.

## What this profile is for

- API development
- validation and unit tests
- retrieval/evaluation work
- frontend integration
- contributor onboarding

For GPU-heavy inference, use the standard `docker-compose.yml` profile.

## Limitations

CPU inference can be substantially slower for embedding, image, and audio workloads. The profile is intended for development and testing rather than performance benchmarking.
