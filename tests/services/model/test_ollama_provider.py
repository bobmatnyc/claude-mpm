"""
Tests for Ollama Model Provider
================================

WHY: Ensures Ollama provider correctly integrates with Ollama API,
handles errors gracefully, and provides proper response formatting.

COVERAGE:
- Provider initialization
- Availability checking
- Model listing
- Content analysis
- Error handling
- Retry logic
- Metrics tracking
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.services.core.interfaces.model import ModelCapability, ModelResponse
from claude_mpm.services.model.ollama_provider import OllamaProvider


@pytest.fixture
def ollama_config():
    """Ollama provider configuration."""
    return {
        "host": "http://localhost:11434",
        "timeout": 30,
        "models": {
            "seo_analysis": "llama3.3:70b",
            "readability": "gemma2:9b",
        },
    }


@pytest.fixture
def ollama_provider(ollama_config):
    """Create Ollama provider instance."""
    return OllamaProvider(config=ollama_config)


@pytest.fixture
def mock_session():
    """Mock aiohttp session."""
    session = MagicMock()
    session.closed = False
    return session


# Initialization Tests


@pytest.mark.asyncio
async def test_ollama_provider_init(ollama_provider):
    """Test provider initialization."""
    assert ollama_provider.provider_name == "ollama"
    assert ollama_provider.host == "http://localhost:11434"
    assert ollama_provider.timeout == 30
    assert not ollama_provider.is_initialized


@pytest.mark.asyncio
async def test_ollama_provider_initialize_success(ollama_provider, mock_session):
    """Test successful initialization."""
    with patch("aiohttp.ClientSession", return_value=mock_session):
        # Mock availability check
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"models": [{"name": "llama3.3:70b"}]}
        )

        # Properly mock async context manager
        mock_get_context = AsyncMock()
        mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_get_context)

        result = await ollama_provider.initialize()

        assert result is True
        assert ollama_provider.is_initialized


@pytest.mark.asyncio
async def test_ollama_provider_initialize_failure(ollama_provider):
    """Test initialization when Ollama unavailable."""
    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = AsyncMock()
        mock_session_class.return_value = mock_session

        # Mock failed availability check
        mock_session.get.side_effect = Exception("Connection refused")

        result = await ollama_provider.initialize()

        assert result is False
        assert not ollama_provider.is_initialized


# Availability Tests


@pytest.mark.asyncio
async def test_is_available_success(ollama_provider, mock_session):
    """Test availability check when Ollama is running."""
    ollama_provider._session = mock_session

    mock_response = MagicMock()
    mock_response.status = 200

    # Properly mock async context manager
    mock_get_context = AsyncMock()
    mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_get_context.__aexit__ = AsyncMock(return_value=None)
    mock_session.get = MagicMock(return_value=mock_get_context)

    result = await ollama_provider.is_available()

    assert result is True


@pytest.mark.asyncio
async def test_is_available_failure(ollama_provider, mock_session):
    """Test availability check when Ollama is not running."""
    ollama_provider._session = mock_session

    mock_session.get.side_effect = Exception("Connection refused")

    result = await ollama_provider.is_available()

    assert result is False


# Model Listing Tests


@pytest.mark.asyncio
async def test_get_available_models(ollama_provider, mock_session):
    """Test fetching available models."""
    ollama_provider._session = mock_session

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "models": [
                {"name": "llama3.3:70b"},
                {"name": "gemma2:9b"},
                {"name": "mistral:7b"},
            ]
        }
    )

    # Properly mock async context manager
    mock_get_context = AsyncMock()
    mock_get_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_get_context.__aexit__ = AsyncMock(return_value=None)
    mock_session.get = MagicMock(return_value=mock_get_context)

    models = await ollama_provider.get_available_models()

    assert len(models) == 3
    assert "llama3.3:70b" in models
    assert "gemma2:9b" in models


@pytest.mark.asyncio
async def test_get_available_models_error(ollama_provider, mock_session):
    """Test model listing when API fails."""
    ollama_provider._session = mock_session
    mock_session.get.side_effect = Exception("API error")

    models = await ollama_provider.get_available_models()

    assert models == []


# Capability Tests


def test_get_supported_capabilities(ollama_provider):
    """Test getting supported capabilities."""
    capabilities = ollama_provider.get_supported_capabilities()

    assert ModelCapability.SEO_ANALYSIS in capabilities
    assert ModelCapability.READABILITY in capabilities
    assert ModelCapability.GRAMMAR in capabilities
    assert len(capabilities) == len(ModelCapability)


# Content Analysis Tests


@pytest.mark.asyncio
async def test_analyze_content_success(ollama_provider, mock_session):
    """Test successful content analysis (non-streaming for legacy coverage)."""
    ollama_provider._initialized = True
    ollama_provider._session = mock_session
    ollama_provider._available_models = ["llama3.3:70b"]

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "response": "SEO analysis result",
            "total_duration": 1000000000,  # 1 second in ns
            "prompt_eval_count": 100,
            "eval_count": 50,
        }
    )

    # Properly mock async context manager
    mock_post_context = AsyncMock()
    mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_context.__aexit__ = AsyncMock(return_value=None)
    mock_session.post = MagicMock(return_value=mock_post_context)

    response = await ollama_provider.analyze_content(
        content="Test content for SEO analysis",
        task=ModelCapability.SEO_ANALYSIS,
        stream=False,  # Use legacy single-JSON path for this test
    )

    assert response.success is True
    assert response.provider == "ollama"
    assert response.model == "llama3.3:70b"
    assert "SEO analysis result" in response.result


@pytest.mark.asyncio
async def test_analyze_content_invalid_content(ollama_provider):
    """Test analysis with invalid content."""
    ollama_provider._initialized = True

    response = await ollama_provider.analyze_content(
        content="",
        task=ModelCapability.SEO_ANALYSIS,
    )

    assert response.success is False
    assert "Invalid content" in response.error


@pytest.mark.asyncio
async def test_analyze_content_model_not_available(ollama_provider):
    """Test analysis when model not available."""
    ollama_provider._initialized = True
    ollama_provider._available_models = ["gemma2:9b"]  # Different model

    response = await ollama_provider.analyze_content(
        content="Test content",
        task=ModelCapability.SEO_ANALYSIS,  # Requires llama3.3:70b
    )

    assert response.success is False
    assert "not available" in response.error


@pytest.mark.asyncio
async def test_analyze_content_api_error(ollama_provider, mock_session):
    """Test analysis when API returns error."""
    ollama_provider._initialized = True
    ollama_provider._session = mock_session
    ollama_provider._available_models = ["llama3.3:70b"]

    mock_response = MagicMock()
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value="Internal server error")

    # Properly mock async context manager
    mock_post_context = AsyncMock()
    mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_context.__aexit__ = AsyncMock(return_value=None)
    mock_session.post = MagicMock(return_value=mock_post_context)

    response = await ollama_provider.analyze_content(
        content="Test content",
        task=ModelCapability.SEO_ANALYSIS,
    )

    assert response.success is False
    assert "500" in response.error


# Model Info Tests


@pytest.mark.asyncio
async def test_get_model_info(ollama_provider, mock_session):
    """Test getting model information."""
    ollama_provider._session = mock_session

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "modelfile": "FROM llama3.3",
            "parameters": "stop [INST]",
            "template": "{{ .Prompt }}",
            "details": {"format": "gguf", "family": "llama"},
        }
    )

    # Properly mock async context manager
    mock_post_context = AsyncMock()
    mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_context.__aexit__ = AsyncMock(return_value=None)
    mock_session.post = MagicMock(return_value=mock_post_context)

    info = await ollama_provider.get_model_info("llama3.3:70b")

    assert info["name"] == "llama3.3:70b"
    assert "modelfile" in info
    assert "details" in info


# Shutdown Tests


@pytest.mark.asyncio
async def test_shutdown(ollama_provider, mock_session):
    """Test provider shutdown."""
    ollama_provider._session = mock_session
    mock_session.close = AsyncMock()

    await ollama_provider.shutdown()

    assert ollama_provider.is_shutdown
    mock_session.close.assert_called_once()


# Metrics Tests


def test_get_metrics(ollama_provider):
    """Test getting provider metrics."""
    ollama_provider._request_count = 10
    ollama_provider._error_count = 2
    ollama_provider._total_latency = 15.5

    metrics = ollama_provider.get_metrics()

    assert metrics["provider"] == "ollama"
    assert metrics["request_count"] == 10
    assert metrics["error_count"] == 2
    assert metrics["error_rate"] == 0.2
    assert metrics["avg_latency_seconds"] == 1.55


# Streaming Tests


class _FakeStreamContent:
    """Async iterable yielding raw NDJSON lines like aiohttp's response.content."""

    def __init__(self, lines: list[bytes]):
        self._lines = lines

    def __aiter__(self):
        self._iter = iter(self._lines)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration as exc:  # noqa: PERF203
            raise StopAsyncIteration from exc


def _make_ndjson_response(chunks: list[dict]) -> MagicMock:
    """Build a mock aiohttp response that streams NDJSON chunks."""
    import json as _json

    response = MagicMock()
    response.status = 200
    response.content = _FakeStreamContent(
        [(_json.dumps(c) + "\n").encode("utf-8") for c in chunks]
    )
    return response


@pytest.mark.asyncio
async def test_analyze_content_streaming_accumulates_tokens(
    ollama_provider, mock_session
):
    """Streaming path must accumulate NDJSON tokens into final ModelResponse."""
    ollama_provider._initialized = True
    ollama_provider._session = mock_session
    ollama_provider._available_models = ["llama3.3:70b"]

    chunks = [
        {"response": "Hello", "done": False},
        {"response": ", ", "done": False},
        {"response": "world", "done": False},
        {
            "response": "!",
            "done": True,
            "total_duration": 2_000_000_000,
            "load_duration": 500_000_000,
            "prompt_eval_count": 12,
            "eval_count": 4,
        },
    ]
    mock_response = _make_ndjson_response(chunks)

    mock_post_context = AsyncMock()
    mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_context.__aexit__ = AsyncMock(return_value=None)
    mock_session.post = MagicMock(return_value=mock_post_context)

    response = await ollama_provider.analyze_content(
        content="Test content for streaming",
        task=ModelCapability.SEO_ANALYSIS,
    )

    assert response.success is True
    assert response.result == "Hello, world!"
    assert response.metadata["streamed"] is True
    assert response.metadata["stream_chunks"] == 4
    assert response.metadata["eval_count"] == 4
    assert response.metadata["total_duration"] == pytest.approx(2.0)

    # Verify request was made with stream=True
    call_kwargs = mock_session.post.call_args.kwargs
    assert call_kwargs["json"]["stream"] is True


@pytest.mark.asyncio
async def test_analyze_content_streaming_invokes_callback(
    ollama_provider, mock_session
):
    """stream_callback should be invoked once per token in order."""
    ollama_provider._initialized = True
    ollama_provider._session = mock_session
    ollama_provider._available_models = ["llama3.3:70b"]

    chunks = [
        {"response": "foo", "done": False},
        {"response": "bar", "done": False},
        {"response": "baz", "done": True},
    ]
    mock_response = _make_ndjson_response(chunks)

    mock_post_context = AsyncMock()
    mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_context.__aexit__ = AsyncMock(return_value=None)
    mock_session.post = MagicMock(return_value=mock_post_context)

    received: list[str] = []

    response = await ollama_provider.analyze_content(
        content="Stream me",
        task=ModelCapability.SEO_ANALYSIS,
        stream_callback=received.append,
    )

    assert response.success is True
    assert received == ["foo", "bar", "baz"]
    assert response.result == "foobarbaz"


@pytest.mark.asyncio
async def test_analyze_content_non_streaming_backward_compat(
    ollama_provider, mock_session
):
    """Passing stream=False must use the legacy single-JSON response path."""
    ollama_provider._initialized = True
    ollama_provider._session = mock_session
    ollama_provider._available_models = ["llama3.3:70b"]

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "response": "non-streamed result",
            "total_duration": 1_000_000_000,
            "prompt_eval_count": 8,
            "eval_count": 3,
        }
    )

    mock_post_context = AsyncMock()
    mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_context.__aexit__ = AsyncMock(return_value=None)
    mock_session.post = MagicMock(return_value=mock_post_context)

    response = await ollama_provider.analyze_content(
        content="Test content",
        task=ModelCapability.SEO_ANALYSIS,
        stream=False,
    )

    assert response.success is True
    assert response.result == "non-streamed result"
    assert response.metadata["streamed"] is False

    # Verify request was made with stream=False
    call_kwargs = mock_session.post.call_args.kwargs
    assert call_kwargs["json"]["stream"] is False


@pytest.mark.asyncio
async def test_analyze_content_streaming_handles_error_chunk(
    ollama_provider, mock_session
):
    """An error payload mid-stream should yield a failed ModelResponse."""
    ollama_provider._initialized = True
    ollama_provider._session = mock_session
    ollama_provider._available_models = ["llama3.3:70b"]

    chunks = [
        {"response": "partial", "done": False},
        {"error": "model exploded"},
    ]
    mock_response = _make_ndjson_response(chunks)

    mock_post_context = AsyncMock()
    mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_context.__aexit__ = AsyncMock(return_value=None)
    mock_session.post = MagicMock(return_value=mock_post_context)

    response = await ollama_provider.analyze_content(
        content="Test content",
        task=ModelCapability.SEO_ANALYSIS,
    )

    assert response.success is False
    assert "model exploded" in response.error


@pytest.mark.asyncio
async def test_analyze_content_streaming_skips_invalid_json(
    ollama_provider, mock_session
):
    """Malformed NDJSON lines must be skipped without aborting the stream."""
    ollama_provider._initialized = True
    ollama_provider._session = mock_session
    ollama_provider._available_models = ["llama3.3:70b"]

    response_obj = MagicMock()
    response_obj.status = 200
    response_obj.content = _FakeStreamContent(
        [
            b'{"response": "good", "done": false}\n',
            b"this is not json\n",
            b"\n",  # empty line
            b'{"response": "end", "done": true, "eval_count": 2}\n',
        ]
    )

    mock_post_context = AsyncMock()
    mock_post_context.__aenter__ = AsyncMock(return_value=response_obj)
    mock_post_context.__aexit__ = AsyncMock(return_value=None)
    mock_session.post = MagicMock(return_value=mock_post_context)

    response = await ollama_provider.analyze_content(
        content="Test content",
        task=ModelCapability.SEO_ANALYSIS,
    )

    assert response.success is True
    assert response.result == "goodend"
    assert response.metadata["stream_chunks"] == 2
