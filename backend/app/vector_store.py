"""Vector-store interfaces used by the retrieval layer."""

from __future__ import annotations

from typing import Any, Protocol


class VectorStore(Protocol):
    """Minimal vector-store contract for ingestion and retrieval."""

    def upsert(self, doc_id: str, embedding: list[float], metadata: dict[str, Any]) -> None: ...
    def query(self, vector: list[float], top_k: int, *, filter: dict | None = None) -> Any: ...
    def fetch(self, ids: list[str]) -> Any: ...
    def count(self) -> int: ...


class PineconeVectorStore:
    """Adapter around a Pinecone index implementing the VectorStore contract."""

    def __init__(self, index: Any):
        self.index = index

    def upsert(self, doc_id: str, embedding: list[float], metadata: dict[str, Any]) -> None:
        self.index.upsert(vectors=[{"id": doc_id, "values": embedding, "metadata": metadata}])

    def query(self, vector: list[float], top_k: int, *, filter: dict | None = None) -> Any:
        kwargs = {"vector": vector, "top_k": top_k, "include_metadata": True}
        if filter:
            kwargs["filter"] = filter
        return self.index.query(**kwargs)

    def fetch(self, ids: list[str]) -> Any:
        return self.index.fetch(ids=ids)

    def count(self) -> int:
        stats = self.index.describe_index_stats()
        return int(getattr(stats, "total_vector_count", 0) or 0)