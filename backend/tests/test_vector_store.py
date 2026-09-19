from app.vector_store import PineconeVectorStore


class FakeIndex:
    def __init__(self):
        self.calls = []

    def upsert(self, **kwargs):
        self.calls.append(("upsert", kwargs))

    def query(self, **kwargs):
        self.calls.append(("query", kwargs))
        return "query-result"

    def fetch(self, **kwargs):
        self.calls.append(("fetch", kwargs))
        return "fetch-result"

    def describe_index_stats(self):
        return type("Stats", (), {"total_vector_count": 7})()


def test_pinecone_adapter_maps_operations():
    index = FakeIndex()
    store = PineconeVectorStore(index)

    store.upsert("id-1", [0.1, 0.2], {"type": "text"})
    assert index.calls[-1][0] == "upsert"

    assert store.query([0.1], 3, filter={"type": {"$in": ["text"]}}) == "query-result"
    assert index.calls[-1][1]["filter"]["type"]["$in"] == ["text"]

    assert store.fetch(["id-1"]) == "fetch-result"
    assert store.count() == 7
