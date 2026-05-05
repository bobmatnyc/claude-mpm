"""Unit tests for OpenRouterProvider.

WHY: Verifies the OpenRouter-backed provider correctly integrates with the
OpenAI-compatible chat-completions API exposed at https://openrouter.ai,
handles streaming SSE, surfaces auth errors, and degrades gracefully when
the OPENROUTER_API_KEY is not set.

COVERAGE:
- is_available(): True when key is set, False when missing
- analyze_content() success on a non-streaming response
- analyze_content() streaming accumulates tokens correctly
- Error response (HTTP 401/500) surfaces error text
- get_available_models() parses the model catalogue
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_mpm.services.core.interfaces.model import ModelCapability
from claude_mpm.services.model.openrouter_provider import OpenRouterProvider

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def provider_with_key() -> OpenRouterProvider:
    """Provider with API key supplied via config (bypassing env)."""
    return OpenRouterProvider(
        config={
            "api_key": "test-or-key",  # pragma: allowlist secret
            "default_model": "openai/gpt-4-turbo",
            "timeout": 5,
        }
    )


@pytest.fixture
def provider_no_key(monkeypatch) -> OpenRouterProvider:
    """Provider with NO API key (env unset, no config override)."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    return OpenRouterProvider(config={"timeout": 5})


@pytest.fixture
def mock_session() -> MagicMock:
    """Mock aiohttp.ClientSession."""
    session = MagicMock()
    session.closed = False
    return session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeStreamContent:
    """Async iterable yielding raw SSE lines like aiohttp's response.content."""

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


def _sse_lines(events: list[dict | str]) -> list[bytes]:
    """Build SSE-formatted byte lines.

    Strings are passed through verbatim (used for the "[DONE]" sentinel);
    dicts are JSON-encoded with the ``data: `` prefix.
    """
    import json as _json

    out: list[bytes] = []
    for evt in events:
        if isinstance(evt, str):
            out.append(f"data: {evt}\n".encode())
        else:
            out.append(f"data: {_json.dumps(evt)}\n".encode())
    return out


def _attach_get_response(session: MagicMock, response: MagicMock) -> None:
    """Attach an async-context-manager GET response to the mock session."""
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=response)
    ctx.__aexit__ = AsyncMock(return_value=None)
    session.get = MagicMock(return_value=ctx)


def _attach_post_response(session: MagicMock, response: MagicMock) -> None:
    """Attach an async-context-manager POST response to the mock session."""
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=response)
    ctx.__aexit__ = AsyncMock(return_value=None)
    session.post = MagicMock(return_value=ctx)


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_is_available_true_when_key_set_and_endpoint_ok(
    provider_with_key, mock_session
):
    """is_available returns True when key set and /models returns 200."""
    provider_with_key._session = mock_session

    response = MagicMock()
    response.status = 200
    _attach_get_response(mock_session, response)

    assert await provider_with_key.is_available() is True


@pytest.mark.asyncio
async def test_is_available_false_when_key_missing(provider_no_key):
    """is_available short-circuits to False when API key is not set."""
    assert await provider_no_key.is_available() is False


@pytest.mark.asyncio
async def test_is_available_false_when_endpoint_returns_error(
    provider_with_key, mock_session
):
    """is_available returns False when /models returns non-200."""
    provider_with_key._session = mock_session

    response = MagicMock()
    response.status = 401
    _attach_get_response(mock_session, response)

    assert await provider_with_key.is_available() is False


# ---------------------------------------------------------------------------
# analyze_content (non-streaming) success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_content_non_streaming_success(provider_with_key, mock_session):
    """Non-streaming path returns the assistant message and usage metadata."""
    provider_with_key._initialized = True
    provider_with_key._session = mock_session

    response = MagicMock()
    response.status = 200
    response.json = AsyncMock(
        return_value={
            "id": "chatcmpl-1",
            "model": "openai/gpt-4-turbo",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Reviewed: looks good with minor nits.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 42,
                "completion_tokens": 17,
                "total_tokens": 59,
            },
        }
    )
    _attach_post_response(mock_session, response)

    result = await provider_with_key.analyze_content(
        content="def add(a, b): return a + b",
        task=ModelCapability.GENERAL,
        stream=False,
    )

    assert result.success is True
    assert result.provider == "openrouter"
    assert result.model == "openai/gpt-4-turbo"
    assert "Reviewed" in result.result
    assert result.metadata["streamed"] is False
    assert result.metadata["total_tokens"] == 59
    assert result.metadata["finish_reason"] == "stop"

    # Verify request payload
    call_kwargs = mock_session.post.call_args.kwargs
    assert call_kwargs["json"]["stream"] is False
    assert call_kwargs["json"]["model"] == "openai/gpt-4-turbo"
    # Auth header included
    assert call_kwargs["headers"]["Authorization"] == "Bearer test-or-key"


# ---------------------------------------------------------------------------
# analyze_content (streaming) accumulates tokens
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_content_streaming_accumulates_tokens(
    provider_with_key, mock_session
):
    """Streaming path accumulates SSE delta.content tokens into one result."""
    provider_with_key._initialized = True
    provider_with_key._session = mock_session

    chunks = [
        {"choices": [{"delta": {"content": "Hello"}, "finish_reason": None}]},
        {"choices": [{"delta": {"content": ", "}, "finish_reason": None}]},
        {
            "choices": [{"delta": {"content": "world!"}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 3,
                "total_tokens": 13,
            },
        },
    ]
    sse_events: list[dict | str] = [*chunks, "[DONE]"]

    response = MagicMock()
    response.status = 200
    response.content = _FakeStreamContent(_sse_lines(sse_events))
    _attach_post_response(mock_session, response)

    callback_tokens: list[str] = []

    result = await provider_with_key.analyze_content(
        content="Stream this",
        task=ModelCapability.GENERAL,
        stream_callback=callback_tokens.append,
    )

    assert result.success is True
    assert result.result == "Hello, world!"
    assert callback_tokens == ["Hello", ", ", "world!"]
    assert result.metadata["streamed"] is True
    assert result.metadata["stream_chunks"] == 3
    assert result.metadata["finish_reason"] == "stop"
    assert result.metadata["total_tokens"] == 13

    # Verify request asked for streaming
    call_kwargs = mock_session.post.call_args.kwargs
    assert call_kwargs["json"]["stream"] is True


# ---------------------------------------------------------------------------
# Error response handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_content_api_error_returns_failed_response(
    provider_with_key, mock_session
):
    """Non-200 response is converted into a failed ModelResponse with detail."""
    provider_with_key._initialized = True
    provider_with_key._session = mock_session

    response = MagicMock()
    response.status = 500
    response.text = AsyncMock(return_value="Upstream model overloaded")
    _attach_post_response(mock_session, response)

    result = await provider_with_key.analyze_content(
        content="def foo(): pass",
        task=ModelCapability.GENERAL,
        stream=False,
    )

    assert result.success is False
    assert "500" in result.error
    assert "overloaded" in result.error


@pytest.mark.asyncio
async def test_analyze_content_without_key_returns_clear_error(provider_no_key):
    """Missing API key yields a descriptive error rather than crashing."""
    result = await provider_no_key.analyze_content(
        content="def foo(): pass",
        task=ModelCapability.GENERAL,
    )

    assert result.success is False
    assert "OPENROUTER_API_KEY" in result.error


# ---------------------------------------------------------------------------
# get_available_models
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_available_models_parses_catalogue(provider_with_key, mock_session):
    """get_available_models extracts model ids from /models response."""
    provider_with_key._session = mock_session

    response = MagicMock()
    response.status = 200
    response.json = AsyncMock(
        return_value={
            "data": [
                {"id": "openai/gpt-4-turbo", "context_length": 128000},
                {"id": "google/gemini-pro-1.5", "context_length": 1000000},
                {"id": "meta-llama/llama-3.1-70b-instruct"},
                {"not_id": "should_be_skipped"},
            ]
        }
    )
    _attach_get_response(mock_session, response)

    models = await provider_with_key.get_available_models()

    assert models == [
        "openai/gpt-4-turbo",
        "google/gemini-pro-1.5",
        "meta-llama/llama-3.1-70b-instruct",
    ]


@pytest.mark.asyncio
async def test_get_available_models_empty_when_no_key(provider_no_key):
    """get_available_models returns [] when API key is unset."""
    assert await provider_no_key.get_available_models() == []
