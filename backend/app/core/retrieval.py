"""Dependency-light retrieval helpers."""

from __future__ import annotations

from math import sqrt
from typing import Any


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left or not right:
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = sqrt(sum(a * a for a in left))
    right_norm = sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


def rerank(query_embedding: list[float], results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = []
    for item in results:
        embedding = item.get("embedding")
        if not embedding:
            continue
        candidate = dict(item)
        candidate["rerank_score"] = cosine_similarity(query_embedding, embedding)
        ranked.append(candidate)
    return sorted(ranked, key=lambda item: item["rerank_score"], reverse=True)
