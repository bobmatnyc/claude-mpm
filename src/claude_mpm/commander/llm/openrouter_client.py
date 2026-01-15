"""OpenRouter LLM client for Commander chat interface."""

import os
from dataclasses import dataclass
from typing import AsyncIterator

import httpx


@dataclass
class OpenRouterConfig:
    """Configuration for OpenRouter API client."""

    api_key: str | None = None  # Falls back to OPENROUTER_API_KEY env
    model: str = "anthropic/claude-3.5-sonnet"
    base_url: str = "https://openrouter.ai/api/v1"
    max_tokens: int = 4096
    temperature: float = 0.7


class OpenRouterClient:
    """Async client for OpenRouter API."""

    def __init__(self, config: OpenRouterConfig | None = None):
        """Initialize client with config.

        Args:
            config: OpenRouter configuration. Defaults to OpenRouterConfig().

        Raises:
            ValueError: If OPENROUTER_API_KEY is not set.
        """
        self.config = config or OpenRouterConfig()
        self._api_key = self.config.api_key or os.getenv("OPENROUTER_API_KEY")
        if not self._api_key:
            raise ValueError("OPENROUTER_API_KEY not set")

    async def chat(self, messages: list[dict], system: str | None = None) -> str:
        """Send chat completion request, return response content.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            system: Optional system prompt.

        Returns:
            Response content from the model.

        Raises:
            httpx.HTTPStatusError: If API request fails.
        """
        async with httpx.AsyncClient() as client:
            # Build request payload
            payload = {
                "model": self.config.model,
                "messages": messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
            }

            if system:
                payload["system"] = system

            # Send request
            response = await client.post(
                f"{self.config.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()

            # Extract content from response
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def chat_stream(
        self, messages: list[dict], system: str | None = None
    ) -> AsyncIterator[str]:
        """Stream chat completion, yield chunks.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            system: Optional system prompt.

        Yields:
            Content chunks from the streaming response.

        Raises:
            httpx.HTTPStatusError: If API request fails.
        """
        async with httpx.AsyncClient() as client:
            # Build request payload
            payload = {
                "model": self.config.model,
                "messages": messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "stream": True,
            }

            if system:
                payload["system"] = system

            # Send streaming request
            async with client.stream(
                "POST",
                f"{self.config.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            ) as response:
                response.raise_for_status()

                # Parse SSE stream
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    # SSE format: "data: {json}"
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix

                        # Check for stream end
                        if data_str == "[DONE]":
                            break

                        # Parse JSON chunk
                        import json

                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError, IndexError):
                            # Skip malformed chunks
                            continue

    async def summarize(self, text: str, max_length: int = 500) -> str:
        """Summarize text to max_length characters.

        Args:
            text: Text to summarize.
            max_length: Maximum length of summary in characters.

        Returns:
            Summarized text.
        """
        messages = [
            {
                "role": "user",
                "content": f"Summarize the following text in approximately {max_length} characters or less:\n\n{text}",
            }
        ]

        system = (
            "You are a concise summarization assistant. "
            "Provide clear, accurate summaries that capture the key points."
        )

        return await self.chat(messages, system=system)
