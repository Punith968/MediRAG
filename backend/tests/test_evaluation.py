from app.evaluation import precision_at_k, recall_at_k, reciprocal_rank


def test_reciprocal_rank_returns_first_relevant_position():
    assert reciprocal_rank(["a", "b", "target"], {"target"}) == 1 / 3


def test_reciprocal_rank_returns_zero_when_not_found():
    assert reciprocal_rank(["a", "b"], {"target"}) == 0.0


def test_recall_at_k_counts_relevant_items():
    assert recall_at_k(["a", "target", "b"], {"target", "other"}, 2) == 0.5


def test_precision_at_k_counts_relevant_results():
    assert precision_at_k(["target", "noise", "other"], {"target", "other"}, 2) == 0.5
