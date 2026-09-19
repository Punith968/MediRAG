"""Dependency-light retrieval helpers."""


def cosine_similarity(query_embedding: list[float], result_embedding: list[float]) -> float:
    if not query_embedding or not result_embedding or len(query_embedding) != len(result_embedding):
        return 0.0

    query_norm = sum(value * value for value in query_embedding) ** 0.5
    result_norm = sum(value * value for value in result_embedding) ** 0.5
    if query_norm == 0 or result_norm == 0:
        return 0.0

    dot = sum(q * r for q, r in zip(query_embedding, result_embedding))
    return float(dot / (query_norm * result_norm))


def rerank(query_embedding: list[float], results: list[dict]) -> list[dict]:
    if not results or not query_embedding:
        return results

    reranked = []
    for result in results:
        embedding = result.get("embedding")
        if embedding is None:
            continue
        reranked.append({
            **result,
            "rerank_score": cosine_similarity(query_embedding, embedding),
        })

    reranked.sort(key=lambda item: item.get("rerank_score", 0), reverse=True)
    return reranked
