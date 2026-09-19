"""Deterministic helpers for lightweight RAG retrieval evaluation."""

from __future__ import annotations

from collections.abc import Iterable


def normalize_text(value: str) -> str:
    return " ".join((value or "").lower().split())


def reciprocal_rank(retrieved_ids: Iterable[str], relevant_ids: set[str]) -> float:
    """Return reciprocal rank of the first relevant retrieved item."""
    if not relevant_ids:
        return 0.0
    for rank, item_id in enumerate(retrieved_ids, start=1):
        if item_id in relevant_ids:
            return 1.0 / rank
    return 0.0


def recall_at_k(retrieved_ids: Iterable[str], relevant_ids: set[str], k: int) -> float:
    """Return the fraction of relevant items retrieved in the first k results."""
    if not relevant_ids or k <= 0:
        return 0.0
    retrieved = set(list(retrieved_ids)[:k])
    return len(retrieved & relevant_ids) / len(relevant_ids)


def precision_at_k(retrieved_ids: Iterable[str], relevant_ids: set[str], k: int) -> float:
    """Return the fraction of the first k results that are relevant."""
    if k <= 0:
        return 0.0
    top_k = list(retrieved_ids)[:k]
    if not top_k:
        return 0.0
    return len(set(top_k) & relevant_ids) / len(top_k)
