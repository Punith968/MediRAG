"""Compatibility wrapper for the reusable evaluation primitives."""

from .core.evaluation import precision_at_k, recall_at_k, reciprocal_rank

__all__ = ["precision_at_k", "recall_at_k", "reciprocal_rank"]
