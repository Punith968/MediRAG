from app.retrieve import build_provenance, rerank


def test_build_provenance_deduplicates_sources():
    hits = [
        {
            "id": "a",
            "text": "one",
            "score": 0.8,
            "metadata": {"id": "a", "filename": "one.pdf", "type": "text"},
        },
        {
            "id": "a",
            "text": "duplicate",
            "score": 0.7,
            "metadata": {"id": "a", "filename": "one.pdf", "type": "text"},
        },
    ]

    sources = build_provenance(hits, [])

    assert len(sources) == 1
    assert sources[0]["filename"] == "one.pdf"
    assert sources[0]["modality"] == "TEXT"
    assert sources[0]["retrieval_score"] == 0.8


def test_rerank_orders_by_cosine_similarity():
    results = [
        {"id": "low", "embedding": [0.0, 1.0]},
        {"id": "high", "embedding": [1.0, 0.0]},
    ]

    ranked = rerank([1.0, 0.0], results)

    assert [item["id"] for item in ranked] == ["high", "low"]
    assert ranked[0]["rerank_score"] > ranked[1]["rerank_score"]


def test_rerank_ignores_missing_embeddings():
    results = [{"id": "missing"}, {"id": "valid", "embedding": [1.0, 0.0]}]

    ranked = rerank([1.0, 0.0], results)

    assert [item["id"] for item in ranked] == ["valid"]
