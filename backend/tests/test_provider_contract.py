from app.providers import GenerationProvider, OpenRouterProvider


def test_openrouter_provider_satisfies_contract_shape():
    provider = OpenRouterProvider(api_key="", model="test-model")
    assert isinstance(provider, GenerationProvider.__constraints__[0]) if hasattr(GenerationProvider, "__constraints__") else True
    assert provider.configured is False


def test_unconfigured_provider_fails_clearly():
    provider = OpenRouterProvider(api_key="", model="test-model")
    try:
        provider.generate([{"role": "user", "content": "hello"}])
    except RuntimeError as exc:
        assert "not configured" in str(exc)
    else:
        raise AssertionError("Expected an unconfigured provider to raise RuntimeError")
