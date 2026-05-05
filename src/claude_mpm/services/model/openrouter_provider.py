"""
OpenRouter Model Provider Implementation for Claude MPM Framework
=================================================================

WHY: Enables independent code review and analysis using non-Claude LLMs
(GPT-4, Gemini, Llama, Mistral, etc.) via OpenRouter's unified API. This
provides unbiased perspectives from different model families and avoids
single-vendor lock-in.

DESIGN DECISION: Uses OpenAI-compatible chat completions API exposed by
OpenRouter at https://openrouter.ai/api/v1. Mirrors the OllamaProvider
streaming pattern for SSE-style data lines so consumers experience a
consistent streaming surface across local and remote providers.

ARCHITECTURE:
- Authentication via OPENROUTER_API_KEY environment variable
- HTTP transport via aiohttp (already a project dependency)
- Streaming via Server-Sent Events ("data: {...}" lines, "[DONE]" sentinel)
- Configurable default model with safe fallback to a low-cost Anthropic model
- Graceful degradation: is_available() returns False when API key is missing

REQUIRED ENVIRONMENT:
- OPENROUTER_API_KEY: API key issued by openrouter.ai

REFERENCE: https://openrouter.ai/docs/api-reference/chat-completion
"""

import json
import os
from collections.abc import Callable
from typing import Any

import aiohttp

from claude_mpm.services.core.interfaces.model import ModelCapability, ModelResponse
from claude_mpm.services.model.base_provider import BaseModelProvider


class OpenRouterProvider(BaseModelProvider):
    """
    OpenRouter unified-LLM provider.

    WHY: Provides access to 200+ non-Claude models for independent code review
    and second-opinion analysis. Useful when bias-free evaluation against a
    different model family is required.

    Configuration (constructor `config` dict):
        api_base: API endpoint (default: "https://openrouter.ai/api/v1")
        timeout: Request timeout in seconds (default: 60)
        default_model: Default model identifier (default: "anthropic/claude-3-haiku")
        models: Dict mapping ModelCapability values to model identifiers
        http_referer: Optional HTTP-Referer header (OpenRouter app attribution)
        x_title: Optional X-Title header (OpenRouter app attribution)
        api_key: Override for OPENROUTER_API_KEY env var (testing only)

    Usage:
        provider = OpenRouterProvider(config={
            "default_model": "openai/gpt-4-turbo",
        })

        if await provider.is_available():
            response = await provider.analyze_content(
                content="def foo(): ...",
                task=ModelCapability.GENERAL,
            )
    """

    DEFAULT_API_BASE = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "anthropic/claude-3-haiku"
    SSE_DATA_PREFIX = b"data: "
    SSE_DONE_SENTINEL = "[DONE]"

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize OpenRouter provider.

        Args:
            config: Provider configuration (see class docstring).
        """
        super().__init__(provider_name="openrouter", config=config or {})

        self.api_base: str = self.get_config("api_base", self.DEFAULT_API_BASE).rstrip(
            "/"
        )
        self.timeout: int = int(self.get_config("timeout", 60))
        self.default_model: str = self.get_config("default_model", self.DEFAULT_MODEL)

        # Per-task model mapping. Empty by default — falls back to default_model.
        custom_models = self.get_config("models", {}) or {}
        self.model_mapping: dict[ModelCapability, str] = {}
        for key, value in custom_models.items():
            if isinstance(key, str):
                try:
                    self.model_mapping[ModelCapability(key)] = value
                except ValueError:
                    self.log_warning(
                        f"Unknown ModelCapability in OpenRouter config: {key}"
                    )
            else:
                self.model_mapping[key] = value

        # Optional OpenRouter app attribution headers
        self.http_referer: str | None = self.get_config("http_referer", None)
        self.x_title: str | None = self.get_config("x_title", None)

        # Allow API key override via config for unit tests; otherwise read env.
        self._api_key: str | None = self.get_config(
            "api_key", os.environ.get("OPENROUTER_API_KEY")
        )

        self._session: aiohttp.ClientSession | None = None
        self._available_models: list[str] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> bool:
        """
        Initialize the OpenRouter provider.

        WHY: Establishes the HTTP session and validates that the service is
        reachable with a valid API key. Returns False on missing key so the
        router can gracefully skip this provider.
        """
        self.log_info(f"Initializing OpenRouter provider at {self.api_base}")

        if not self._api_key:
            self.log_warning(
                "OPENROUTER_API_KEY not set; OpenRouter provider unavailable"
            )
            self._initialized = False
            return False

        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self._session = aiohttp.ClientSession(timeout=timeout)

        if not await self.is_available():
            self.log_warning("OpenRouter service not reachable")
            self._initialized = False
            return False

        # Best-effort model discovery; failures are non-fatal.
        self._available_models = await self.get_available_models()
        self.log_info(
            f"OpenRouter ready ({len(self._available_models)} models discovered)"
        )

        self._initialized = True
        return True

    async def shutdown(self) -> None:
        """Close the HTTP session."""
        self.log_info("Shutting down OpenRouter provider")
        if self._session and not self._session.closed:
            await self._session.close()
        self._shutdown = True

    # ------------------------------------------------------------------
    # Capability discovery
    # ------------------------------------------------------------------

    async def is_available(self) -> bool:
        """
        Check whether the OpenRouter API is reachable.

        WHY: Used by the router for fallback decisions. Returns False if the
        API key is missing so callers can short-circuit cleanly.
        """
        if not self._api_key:
            return False

        try:
            session = await self._ensure_session()
            async with session.get(
                f"{self.api_base}/models",
                headers=self._build_headers(),
            ) as response:
                if response.status == 200:
                    return True
                self.log_warning(
                    f"OpenRouter availability check returned {response.status}"
                )
                return False
        except aiohttp.ClientError as e:
            self.log_debug(f"OpenRouter not available: {e}")
            return False
        except Exception as e:
            self.log_warning(f"Error checking OpenRouter availability: {e}")
            return False

    async def get_available_models(self) -> list[str]:
        """
        List models exposed by the configured OpenRouter account.

        Returns:
            List of model identifiers (e.g., ["anthropic/claude-3-haiku",
            "openai/gpt-4-turbo"]). Returns [] on error or when unauthorized.
        """
        if not self._api_key:
            return []

        try:
            session = await self._ensure_session()
            async with session.get(
                f"{self.api_base}/models",
                headers=self._build_headers(),
            ) as response:
                if response.status != 200:
                    self.log_error(
                        f"Failed to list OpenRouter models: status {response.status}"
                    )
                    return []
                data = await response.json()
                models = data.get("data", [])
                return [m["id"] for m in models if isinstance(m, dict) and "id" in m]
        except Exception as e:
            self.log_error(f"Error fetching OpenRouter models: {e}")
            return []

    def get_supported_capabilities(self) -> list[ModelCapability]:
        """OpenRouter supports all capabilities via prompt routing."""
        return list(ModelCapability)

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    async def analyze_content(
        self,
        content: str,
        task: ModelCapability,
        model: str | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """
        Analyze content using an OpenRouter-hosted model.

        Args:
            content: Text content to analyze.
            task: Capability driving prompt selection.
            model: Optional explicit model identifier (overrides mapping).
            **kwargs: Additional options:
                - temperature: Sampling temperature (0.0-2.0)
                - max_tokens: Maximum response tokens
                - stream: Enable SSE streaming (default: True)
                - stream_callback: callable(token: str) -> None invoked per token

        Returns:
            ModelResponse with accumulated text and provider metadata.
        """
        if not self._api_key:
            return self.create_response(
                success=False,
                model=model or self.default_model,
                task=task,
                error=("OpenRouter provider unavailable: OPENROUTER_API_KEY not set"),
            )

        if not self.validate_content(content, max_length=200_000):
            return self.create_response(
                success=False,
                model=model or self.default_model,
                task=task,
                error="Invalid content provided",
            )

        if not self._initialized:
            await self.initialize()

        if not self._initialized:
            return self.create_response(
                success=False,
                model=model or self.default_model,
                task=task,
                error="OpenRouter provider not initialized",
            )

        selected_model = model or self._get_model_for_task(task)
        prompt = self.get_task_prompt(task, content)

        return await self.analyze_with_retry(
            self._call_openrouter,
            prompt,
            task,
            selected_model,
            **kwargs,
        )

    async def _call_openrouter(
        self,
        prompt: str,
        task: ModelCapability,
        model: str,
        **kwargs: Any,
    ) -> ModelResponse:
        """Issue the chat-completions request and dispatch to streaming/non-streaming."""
        try:
            stream_callback: Callable[[str], None] | None = kwargs.get(
                "stream_callback"
            )
            stream_enabled = bool(kwargs.get("stream", True)) or (
                stream_callback is not None
            )

            payload: dict[str, Any] = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": stream_enabled,
            }
            if "temperature" in kwargs:
                payload["temperature"] = kwargs["temperature"]
            if "max_tokens" in kwargs:
                payload["max_tokens"] = kwargs["max_tokens"]

            session = await self._ensure_session()

            async with session.post(
                f"{self.api_base}/chat/completions",
                json=payload,
                headers=self._build_headers(),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return self.create_response(
                        success=False,
                        model=model,
                        task=task,
                        error=(f"OpenRouter API error {response.status}: {error_text}"),
                    )

                if stream_enabled:
                    return await self._consume_stream(
                        response, model, task, stream_callback
                    )

                data = await response.json()
                return self._build_response_from_completion(data, model, task)

        except TimeoutError:
            return self.create_response(
                success=False,
                model=model,
                task=task,
                error=f"Request timeout after {self.timeout}s",
            )
        except Exception as e:
            return self.create_response(
                success=False,
                model=model,
                task=task,
                error=f"Request failed: {e!s}",
            )

    async def _consume_stream(
        self,
        response: aiohttp.ClientResponse,
        model: str,
        task: ModelCapability,
        stream_callback: Callable[[str], None] | None = None,
    ) -> ModelResponse:
        """
        Consume OpenRouter's Server-Sent Events stream.

        WHY: OpenRouter (OpenAI-compatible) streams chat completions as
        ``data: {...}`` lines terminated by ``data: [DONE]``. Each chunk's
        ``choices[0].delta.content`` carries an incremental token. We
        accumulate tokens into a single ModelResponse and optionally invoke
        ``stream_callback`` per token for live consumers.

        Args:
            response: Open aiohttp response (status 200 verified by caller).
            model: Model identifier used for the request.
            task: Capability for response metadata.
            stream_callback: Optional per-token callback.
        """
        accumulated: list[str] = []
        finish_reason: str | None = None
        usage: dict[str, Any] = {}
        chunk_count = 0

        async for raw_line in response.content:
            if not raw_line:
                continue
            line = raw_line.strip()
            if not line:
                continue

            # OpenRouter emits SSE keep-alive comments as ": ...". Skip them.
            if line.startswith(b":"):
                continue
            if not line.startswith(self.SSE_DATA_PREFIX):
                continue

            payload = line[len(self.SSE_DATA_PREFIX) :].decode("utf-8").strip()
            if payload == self.SSE_DONE_SENTINEL:
                break

            try:
                chunk = json.loads(payload)
            except json.JSONDecodeError as e:
                self.log_warning(f"Skipping invalid SSE chunk: {e}")
                continue

            if "error" in chunk:
                err = chunk["error"]
                err_msg = err.get("message") if isinstance(err, dict) else str(err)
                return self.create_response(
                    success=False,
                    model=model,
                    task=task,
                    error=f"OpenRouter stream error: {err_msg}",
                )

            choices = chunk.get("choices") or []
            if choices:
                choice = choices[0]
                delta = choice.get("delta") or {}
                token = delta.get("content") or ""
                if token:
                    accumulated.append(token)
                    chunk_count += 1
                    if stream_callback is not None:
                        try:
                            stream_callback(token)
                        except Exception as cb_err:
                            self.log_warning(f"stream_callback raised: {cb_err}")
                if choice.get("finish_reason"):
                    finish_reason = choice["finish_reason"]

            if "usage" in chunk and isinstance(chunk["usage"], dict):
                usage = chunk["usage"]

        result_text = "".join(accumulated)
        metadata: dict[str, Any] = {
            "model": model,
            "streamed": True,
            "stream_chunks": chunk_count,
            "finish_reason": finish_reason,
        }
        if usage:
            metadata["prompt_tokens"] = usage.get("prompt_tokens", 0)
            metadata["completion_tokens"] = usage.get("completion_tokens", 0)
            metadata["total_tokens"] = usage.get("total_tokens", 0)

        return self.create_response(
            success=True,
            model=model,
            task=task,
            result=result_text,
            metadata=metadata,
        )

    def _build_response_from_completion(
        self,
        data: dict[str, Any],
        model: str,
        task: ModelCapability,
    ) -> ModelResponse:
        """Convert a non-streaming chat-completion JSON body into a ModelResponse."""
        choices = data.get("choices") or []
        if not choices:
            return self.create_response(
                success=False,
                model=model,
                task=task,
                error="OpenRouter returned no choices",
            )

        choice = choices[0]
        message = choice.get("message") or {}
        result_text = message.get("content", "") or ""

        usage = data.get("usage") or {}
        metadata: dict[str, Any] = {
            "model": data.get("model", model),
            "streamed": False,
            "finish_reason": choice.get("finish_reason"),
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }

        return self.create_response(
            success=True,
            model=model,
            task=task,
            result=result_text,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    async def get_model_info(self, model: str) -> dict[str, Any]:
        """
        Fetch metadata for a specific model from OpenRouter.

        WHY: OpenRouter does not expose a per-model `show` endpoint, so we
        fetch the catalogue and filter. Result includes pricing, context
        length, and provider details when available.
        """
        try:
            session = await self._ensure_session()
            async with session.get(
                f"{self.api_base}/models",
                headers=self._build_headers(),
            ) as response:
                if response.status != 200:
                    return {"name": model, "error": f"Status {response.status}"}
                data = await response.json()
                for entry in data.get("data", []):
                    if isinstance(entry, dict) and entry.get("id") == model:
                        return {"name": model, **entry}
                return {
                    "name": model,
                    "error": "Model not found in OpenRouter catalogue",
                }
        except Exception as e:
            return {"name": model, "error": str(e)}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_model_for_task(self, task: ModelCapability) -> str:
        """Resolve the configured model for a task, falling back to the default."""
        return self.model_mapping.get(task, self.default_model)

    def _build_headers(self) -> dict[str, str]:
        """Build headers including auth and OpenRouter app-attribution."""
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self.http_referer:
            headers["HTTP-Referer"] = self.http_referer
        if self.x_title:
            headers["X-Title"] = self.x_title
        return headers

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Create the HTTP session lazily if the lifecycle hasn't done so."""
        if not self._session or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session


__all__ = ["OpenRouterProvider"]
