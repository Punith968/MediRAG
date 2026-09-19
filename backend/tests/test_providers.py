from app.providers import OpenRouterProvider


def test_provider_is_unconfigured_without_key():
    provider = OpenRouterProvider(api_key="", model="test-model")
    assert provider.configured is False


def test_provider_reports_configuration_with_key():
    provider = OpenRouterProvider(api_key="test-key", model="test-model")
    assert provider.configured is True


def test_provider_interface_uses_openrouter_client(monkeypatch):
    calls = {}

    class FakeCompletions:
        def create(self, **kwargs):
            calls.update(kwargs)
            return type("Response", (), {
                "choices": [type("Choice", (), {
                    "message": type("Message", (), {"content": "ok"})()
                })()]
            })()

    class FakeClient:
        def __init__(self):
            self.chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr("app.providers.OpenAI", lambda **kwargs: FakeClient())
    provider = OpenRouterProvider(api_key="test-key", model="test-model")
    result = provider.generate([{"role": "user", "content": "hello"}])

    assert result == "ok"
    assert calls["model"] == "test-model"
