"""Tests for OpenRouter client."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from claude_mpm.commander.llm import OpenRouterClient, OpenRouterConfig


class TestOpenRouterConfig:
    """Test OpenRouterConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = OpenRouterConfig()
        assert config.api_key is None
        assert config.model == "anthropic/claude-3.5-sonnet"
        assert config.base_url == "https://openrouter.ai/api/v1"
        assert config.max_tokens == 4096
        assert config.temperature == 0.7

    def test_custom_values(self):
        """Test custom configuration values."""
        config = OpenRouterConfig(
            api_key="test-key",  # pragma: allowlist secret
            model="custom-model",
            base_url="https://custom.api",
            max_tokens=2048,
            temperature=0.5,
        )
        assert config.api_key == "test-key"  # pragma: allowlist secret
        assert config.model == "custom-model"
        assert config.base_url == "https://custom.api"
        assert config.max_tokens == 2048
        assert config.temperature == 0.5


class TestOpenRouterClient:
    """Test OpenRouter Client."""

    def test_init_with_api_key_in_config(self):
        """Test initialization with API key in config."""
        config = OpenRouterConfig(api_key="test-key")  # pragma: allowlist secret
        client = OpenRouterClient(config)
        assert client._api_key == "test-key"  # pragma: allowlist secret

    def test_init_with_api_key_in_env(self):
        """Test initialization with API key from environment."""
        with patch.dict(
            os.environ,
            {"OPENROUTER_API_KEY": "env-key"},  # pragma: allowlist secret
        ):
            client = OpenRouterClient()
            assert client._api_key == "env-key"  # pragma: allowlist secret

    def test_init_without_api_key_raises_error(self):
        """Test initialization without API key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENROUTER_API_KEY not set"):
                OpenRouterClient()

    def test_config_api_key_takes_precedence_over_env(self):
        """Test that config API key takes precedence over environment."""
        with patch.dict(
            os.environ,
            {"OPENROUTER_API_KEY": "env-key"},  # pragma: allowlist secret
        ):
            config = OpenRouterConfig(api_key="config-key")  # pragma: allowlist secret
            client = OpenRouterClient(config)
            assert client._api_key == "config-key"  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_chat_success(self):
        """Test successful chat completion."""
        config = OpenRouterConfig(api_key="test-key")  # pragma: allowlist secret
        client = OpenRouterClient(config)

        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello, world!"}}]
        }
        mock_response.raise_for_status = MagicMock()

        # Mock httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            messages = [{"role": "user", "content": "Hello"}]
            result = await client.chat(messages)

            assert result == "Hello, world!"

            # Verify request
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://openrouter.ai/api/v1/chat/completions"
            assert (
                call_args[1]["headers"]["Authorization"] == "Bearer test-key"
            )  # pragma: allowlist secret
            assert call_args[1]["json"]["model"] == "anthropic/claude-3.5-sonnet"
            assert call_args[1]["json"]["messages"] == messages

    @pytest.mark.asyncio
    async def test_chat_with_system_prompt(self):
        """Test chat with system prompt."""
        config = OpenRouterConfig(api_key="test-key")  # pragma: allowlist secret
        client = OpenRouterClient(config)

        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}]
        }
        mock_response.raise_for_status = MagicMock()

        # Mock httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            messages = [{"role": "user", "content": "Hello"}]
            system = "You are a helpful assistant"
            result = await client.chat(messages, system=system)

            assert result == "Response"

            # Verify system prompt in payload
            call_args = mock_client.post.call_args
            assert call_args[1]["json"]["system"] == system

    @pytest.mark.asyncio
    async def test_chat_handles_http_error(self):
        """Test chat handles HTTP errors."""
        config = OpenRouterConfig(api_key="test-key")  # pragma: allowlist secret
        client = OpenRouterClient(config)

        # Mock error response
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=MagicMock(), response=MagicMock()
        )

        # Mock httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            messages = [{"role": "user", "content": "Hello"}]

            with pytest.raises(httpx.HTTPStatusError):
                await client.chat(messages)

    @pytest.mark.asyncio
    async def test_chat_stream_success(self):
        """Test successful streaming chat completion."""
        config = OpenRouterConfig(api_key="test-key")  # pragma: allowlist secret
        client = OpenRouterClient(config)

        # Mock SSE stream
        async def mock_aiter_lines():
            yield "data: " + '{"choices": [{"delta": {"content": "Hello"}}]}'
            yield "data: " + '{"choices": [{"delta": {"content": " world"}}]}'
            yield "data: " + '{"choices": [{"delta": {"content": "!"}}]}'
            yield "data: [DONE]"

        # Mock response
        mock_response = AsyncMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None

        # Mock httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.stream = MagicMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            messages = [{"role": "user", "content": "Hello"}]
            chunks = []
            async for chunk in client.chat_stream(messages):
                chunks.append(chunk)

            assert chunks == ["Hello", " world", "!"]

            # Verify request
            mock_client.stream.assert_called_once()
            call_args = mock_client.stream.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "https://openrouter.ai/api/v1/chat/completions"
            assert call_args[1]["json"]["stream"] is True

    @pytest.mark.asyncio
    async def test_chat_stream_skips_malformed_chunks(self):
        """Test streaming skips malformed JSON chunks."""
        config = OpenRouterConfig(api_key="test-key")  # pragma: allowlist secret
        client = OpenRouterClient(config)

        # Mock SSE stream with malformed data
        async def mock_aiter_lines():
            yield "data: " + '{"choices": [{"delta": {"content": "Hello"}}]}'
            yield "data: invalid-json"
            yield "data: " + '{"malformed": "no choices"}'
            yield ""  # Empty line
            yield "data: " + '{"choices": [{"delta": {"content": " world"}}]}'
            yield "data: [DONE]"

        # Mock response
        mock_response = AsyncMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None

        # Mock httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.stream = MagicMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            messages = [{"role": "user", "content": "Hello"}]
            chunks = []
            async for chunk in client.chat_stream(messages):
                chunks.append(chunk)

            # Should only get valid chunks
            assert chunks == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_summarize_success(self):
        """Test successful summarization."""
        config = OpenRouterConfig(api_key="test-key")  # pragma: allowlist secret
        client = OpenRouterClient(config)

        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Summary of text"}}]
        }
        mock_response.raise_for_status = MagicMock()

        # Mock httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            text = "Long text to summarize" * 100
            result = await client.summarize(text, max_length=200)

            assert result == "Summary of text"

            # Verify summarization prompt
            call_args = mock_client.post.call_args
            messages = call_args[1]["json"]["messages"]
            assert len(messages) == 1
            assert "Summarize" in messages[0]["content"]
            assert "200 characters" in messages[0]["content"]
            assert text in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_summarize_custom_config(self):
        """Test summarization respects custom config."""
        config = OpenRouterConfig(
            api_key="test-key",  # pragma: allowlist secret
            model="custom-model",
            temperature=0.3,
        )
        client = OpenRouterClient(config)

        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Summary"}}]
        }
        mock_response.raise_for_status = MagicMock()

        # Mock httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            await client.summarize("Text to summarize")

            # Verify custom config used
            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert payload["model"] == "custom-model"
            assert payload["temperature"] == 0.3
