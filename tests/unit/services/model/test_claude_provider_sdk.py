"""Tests for Anthropic SDK-backed methods in ClaudeProvider (issue #475).

Covers the four Phase 2 operations now implemented against the
``anthropic.AsyncAnthropic`` client:

1. Completion / chat (analyze_content -> messages.create)
2. Streaming completion (stream_content -> messages.stream)
3. Token counting (count_tokens -> messages.count_tokens)
4. Model listing (list_models_from_api -> models.list)

All tests mock the Anthropic client to avoid real network calls.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.services.core.interfaces.model import ModelCapability
from claude_mpm.services.model.claude_provider import ClaudeProvider


@pytest.fixture
def provider_config():
    return {
        "api_key": "test-key",  # pragma: allowlist secret
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 1024,
    }


@pytest.fixture
def provider(provider_config):
    return ClaudeProvider(config=provider_config)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_message_response(text: str, model: str) -> SimpleNamespace:
    """Build a fake messages.create response with one text content block."""
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        model=model,
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=42, output_tokens=7),
    )


def _build_stream_context(chunks: list[str]):
    """Build an async-context-manager mimicking AsyncAnthropic.messages.stream()."""

    class _FakeStream:
        @property
        def text_stream(self):
            async def _gen():
                for chunk in chunks:
                    yield chunk

            return _gen()

    @asynccontextmanager
    async def _ctx(**_kwargs):
        yield _FakeStream()

    return _ctx


def _attach_mock_client(provider: ClaudeProvider, client) -> None:
    """Force the provider into an initialized state with the supplied client."""
    provider._client = client
    provider._initialized = True


# ---------------------------------------------------------------------------
# 1. Completion / chat -- analyze_content
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_content_calls_messages_create(provider):
    """analyze_content invokes AsyncAnthropic.messages.create and returns text."""
    fake_client = MagicMock()
    fake_client.messages = MagicMock()
    fake_client.messages.create = AsyncMock(
        return_value=_build_message_response("ok", "claude-3-5-sonnet-20241022")
    )
    _attach_mock_client(provider, fake_client)

    response = await provider.analyze_content(
        content="some text",
        task=ModelCapability.GENERAL,
    )

    assert response.success is True
    assert response.result == "ok"
    assert response.model == "claude-3-5-sonnet-20241022"
    fake_client.messages.create.assert_awaited_once()
    call_args = fake_client.messages.create.await_args
    assert call_args is not None
    call_kwargs = call_args.kwargs
    assert call_kwargs["model"] == "claude-3-5-sonnet-20241022"
    assert call_kwargs["messages"][0]["role"] == "user"


@pytest.mark.asyncio
async def test_analyze_content_uses_override_model(provider):
    fake_client = MagicMock()
    fake_client.messages = MagicMock()
    fake_client.messages.create = AsyncMock(
        return_value=_build_message_response("hi", "claude-3-opus-20240229")
    )
    _attach_mock_client(provider, fake_client)

    response = await provider.analyze_content(
        content="some text",
        task=ModelCapability.GENERAL,
        model="claude-3-opus-20240229",
    )

    assert response.success is True
    assert response.model == "claude-3-opus-20240229"
    call_args = fake_client.messages.create.await_args
    assert call_args is not None
    assert call_args.kwargs["model"] == "claude-3-opus-20240229"


# ---------------------------------------------------------------------------
# 2. Streaming completion -- stream_content
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_content_yields_text_chunks(provider):
    fake_client = MagicMock()
    fake_client.messages = MagicMock()
    fake_client.messages.stream = _build_stream_context(["hel", "lo", " world"])
    _attach_mock_client(provider, fake_client)

    chunks: list[str] = []
    async for piece in provider.stream_content(
        content="anything", task=ModelCapability.GENERAL
    ):
        chunks.append(piece)

    assert chunks == ["hel", "lo", " world"]


@pytest.mark.asyncio
async def test_stream_content_requires_initialization(provider):
    """If initialize() fails (no key), stream_content must raise."""
    # No API key on a fresh provider with the env unset.
    provider.api_key = None
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="not initialized"):
            agen = provider.stream_content(content="text", task=ModelCapability.GENERAL)
            await agen.__anext__()


@pytest.mark.asyncio
async def test_stream_content_rejects_empty_content(provider):
    fake_client = MagicMock()
    fake_client.messages = MagicMock()
    fake_client.messages.stream = _build_stream_context(["x"])
    _attach_mock_client(provider, fake_client)

    with pytest.raises(ValueError, match="Invalid content"):
        agen = provider.stream_content(content="", task=ModelCapability.GENERAL)
        await agen.__anext__()


# ---------------------------------------------------------------------------
# 3. Token counting -- count_tokens
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_count_tokens_returns_input_tokens(provider):
    fake_client = MagicMock()
    fake_client.messages = MagicMock()
    fake_client.messages.count_tokens = AsyncMock(
        return_value=SimpleNamespace(input_tokens=123)
    )
    _attach_mock_client(provider, fake_client)

    count = await provider.count_tokens("hello world")

    assert count == 123
    fake_client.messages.count_tokens.assert_awaited_once()
    call_args = fake_client.messages.count_tokens.await_args
    assert call_args is not None
    kwargs = call_args.kwargs
    assert kwargs["model"] == "claude-3-5-sonnet-20241022"
    assert kwargs["messages"] == [{"role": "user", "content": "hello world"}]


@pytest.mark.asyncio
async def test_count_tokens_passes_system_prompt(provider):
    fake_client = MagicMock()
    fake_client.messages = MagicMock()
    fake_client.messages.count_tokens = AsyncMock(
        return_value=SimpleNamespace(input_tokens=99)
    )
    _attach_mock_client(provider, fake_client)

    count = await provider.count_tokens(
        "hi", model="claude-3-5-haiku-20241022", system="You are a helpful bot."
    )

    assert count == 99
    call_args = fake_client.messages.count_tokens.await_args
    assert call_args is not None
    kwargs = call_args.kwargs
    assert kwargs["model"] == "claude-3-5-haiku-20241022"
    assert kwargs["system"] == "You are a helpful bot."


@pytest.mark.asyncio
async def test_count_tokens_handles_missing_attr(provider):
    """If the response lacks input_tokens, count_tokens must return 0."""
    fake_client = MagicMock()
    fake_client.messages = MagicMock()
    fake_client.messages.count_tokens = AsyncMock(return_value=SimpleNamespace())
    _attach_mock_client(provider, fake_client)

    assert await provider.count_tokens("text") == 0


# ---------------------------------------------------------------------------
# 4. Model listing -- list_models_from_api
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_models_from_api_returns_ids(provider):
    fake_client = MagicMock()
    fake_client.models = MagicMock()
    fake_client.models.list = AsyncMock(
        return_value=SimpleNamespace(
            data=[
                SimpleNamespace(id="claude-3-5-sonnet-20241022"),
                SimpleNamespace(id="claude-3-5-haiku-20241022"),
            ]
        )
    )
    _attach_mock_client(provider, fake_client)

    models = await provider.list_models_from_api()

    assert models == [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
    ]


@pytest.mark.asyncio
async def test_list_models_from_api_falls_back_when_unavailable(provider):
    """If the SDK does not expose models.list, fall back to curated list."""
    fake_client = MagicMock(spec=[])  # No `models` attribute
    _attach_mock_client(provider, fake_client)

    models = await provider.list_models_from_api()

    assert models == list(ClaudeProvider.AVAILABLE_MODELS)


@pytest.mark.asyncio
async def test_list_models_from_api_falls_back_on_exception(provider):
    fake_client = MagicMock()
    fake_client.models = MagicMock()
    fake_client.models.list = AsyncMock(side_effect=RuntimeError("boom"))
    _attach_mock_client(provider, fake_client)

    models = await provider.list_models_from_api()

    assert models == list(ClaudeProvider.AVAILABLE_MODELS)


@pytest.mark.asyncio
async def test_get_available_models_returns_curated_list(provider):
    """The curated, sync-friendly list remains the routing source of truth."""
    models = await provider.get_available_models()
    assert models == list(ClaudeProvider.AVAILABLE_MODELS)
