# Contributing to MediRAG

Thanks for contributing to MediRAG. This project is intended to become a modular, provider-agnostic multimodal RAG toolkit.

## Before you start

1. Check existing issues and pull requests.
2. For non-trivial changes, open an issue first so the design can be discussed.
3. Never commit API keys, credentials, patient data, or other sensitive information.
4. Keep changes focused and include tests where practical.

## Development

The current application contains a FastAPI backend and React frontend. See the README and integration guide for local setup.

## Pull requests

A good PR should:
- explain the problem and the proposed solution;
- include tests or a clear testing note;
- update documentation when behavior changes;
- avoid unrelated formatting or refactoring;
- pass the CI checks.

## Good first contributions

Documentation improvements, tests, ingestion adapters, retrieval backends, LLM/provider integrations, evaluation utilities, error handling, and developer tooling are all welcome.

## Medical-safety boundary

MediRAG is a software/research project, not a medical professional or diagnostic authority. Contributions must not present generated output as a diagnosis or treatment recommendation. Safety limitations should be explicit in user-facing features.
