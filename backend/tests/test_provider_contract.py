from app.providers import GenerationProvider, OpenRouterProvider


def test_openrouter_provider_exposes_generation_contract():
    provider = OpenRouterProvider(api_key="", model="test-model")
    assert hasattr(provider, "configured")
    assert hasattr(provider, "generate")
    assert provider.configured is False


def test_unconfigured_provider_fails_clearly():
    provider = OpenRouterProvider(api_key="", model="test-model")
    try:
        provider.generate([{"role": "user", "content": "hello"}])
    except RuntimeError as exc:
        assert str(exc) == "Generation provider is not configured."
    else:
        raise AssertionError("Expected an unconfigured provider to raise RuntimeError")


def test_fake_provider_matches_protocol():
    class FakeProvider:
        configured = True

        def generate(self, messages: list[dict], timeout: float = 30.0) -> str:
            return "ok"

    provider: GenerationProvider = FakeProvider()
    assert provider.configured is True
    assert provider.generate([{"role": "user", "content": "hello"}]) == "ok"
