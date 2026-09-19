from app.core.retrieval import cosine_similarity, rerank


def test_cosine_similarity_handles_identical_vectors():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_cosine_similarity_handles_zero_vector():
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_rerank_orders_candidates_by_similarity():
    ranked = rerank(
        [1.0, 0.0],
        [
            {"id": "low", "embedding": [0.0, 1.0]},
            {"id": "high", "embedding": [1.0, 0.0]},
        ],
    )
    assert [item["id"] for item in ranked] == ["high", "low"]
