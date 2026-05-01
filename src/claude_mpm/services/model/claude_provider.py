"""
Claude Model Provider Implementation for Claude MPM Framework
=============================================================

WHY: Provides cloud-based content analysis via Claude API as fallback
when local models are unavailable or for tasks requiring higher quality.

DESIGN DECISION: Uses the official Anthropic AsyncAnthropic SDK client to
issue messages.create requests. The provider supports configuration via
the constructor or the ANTHROPIC_API_KEY environment variable, and degrades
gracefully when the SDK is not installed or no API key is available.
"""

import os
from typing import Any

from claude_mpm.services.core.interfaces.model import ModelCapability, ModelResponse
from claude_mpm.services.model.base_provider import BaseModelProvider

try:
    import anthropic  # type: ignore[import-not-found]

    HAS_ANTHROPIC = True
except ImportError:
    anthropic = None  # type: ignore[assignment]
    HAS_ANTHROPIC = False


class ClaudeProvider(BaseModelProvider):
    """
    Claude API model provider (cloud-based).

    WHY: Provides high-quality cloud-based content analysis with guaranteed
    availability as fallback from local models.

    Configuration:
        api_key: Anthropic API key (optional, can use env var)
        model: Default model to use (default: claude-3-5-sonnet-20241022)
        max_tokens: Maximum response tokens (default: 4096)

    Usage:
        provider = ClaudeProvider(config={
            "api_key": "sk-ant-...",
            "model": "claude-3-5-sonnet-20241022"
        })

        response = await provider.analyze_content(
            content="Your content",
            task=ModelCapability.SEO_ANALYSIS
        )

    Note: Phase 1 implementation provides interface. Phase 2 will add
    actual Claude API integration.
    """

    # Available Claude models
    AVAILABLE_MODELS = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize Claude provider.

        Args:
            config: Configuration dict with:
                - api_key: Anthropic API key
                - model: Default model
                - max_tokens: Maximum response tokens
        """
        super().__init__(provider_name="claude", config=config or {})

        self.api_key = self.get_config("api_key", None) or os.getenv(
            "ANTHROPIC_API_KEY"
        )
        self.default_model = self.get_config("model", "claude-3-5-sonnet-20241022")
        self.max_tokens = self.get_config("max_tokens", 4096)

        # Anthropic AsyncAnthropic client; initialized lazily in initialize()
        self._client: Any = None

    async def initialize(self) -> bool:
        """
        Initialize Claude provider.

        Resolves the API key (constructor config or ANTHROPIC_API_KEY env var)
        and instantiates an AsyncAnthropic client.

        Returns:
            True if initialization successful, False otherwise
        """
        self.log_info("Initializing Claude provider")

        if not self.api_key:
            self.api_key = os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            self.log_error(
                "No Claude API key available "
                "(set ANTHROPIC_API_KEY or pass api_key in config)"
            )
            return False

        if not HAS_ANTHROPIC or anthropic is None:
            self.log_error(
                "anthropic package not installed; install with `pip install anthropic`"
            )
            return False

        try:
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
        except Exception as e:
            self.log_error(f"Failed to initialize Anthropic client: {e}")
            return False

        self.log_info("Claude provider initialized with Anthropic SDK")
        self._initialized = True
        return True

    async def shutdown(self) -> None:
        """Shutdown provider and cleanup resources."""
        self.log_info("Shutting down Claude provider")

        if self._client is not None:
            # AsyncAnthropic exposes an async close() method to release HTTP
            # connections. Older SDK versions may not have it; guard with getattr.
            close = getattr(self._client, "close", None)
            if close is not None:
                try:
                    await close()
                except Exception as e:  # pragma: no cover - defensive
                    self.log_warning(f"Error closing Anthropic client: {e}")
            self._client = None

        self._shutdown = True

    async def is_available(self) -> bool:
        """
        Check if Claude API is available.

        WHY: Cloud APIs are generally always available if API key is valid.
        We treat the provider as available when an API key is configured (or
        present in the environment) and the SDK is importable.

        Returns:
            True if the provider can plausibly issue requests, False otherwise
        """
        if not self.api_key and not os.getenv("ANTHROPIC_API_KEY"):
            return False

        if not HAS_ANTHROPIC:
            return False

        return True

    async def get_available_models(self) -> list[str]:
        """
        List available Claude models.

        Returns:
            List of model identifiers
        """
        return self.AVAILABLE_MODELS

    def get_supported_capabilities(self) -> list[ModelCapability]:
        """
        Return all supported capabilities.

        WHY: Claude supports all content analysis capabilities.

        Returns:
            List of all ModelCapability values
        """
        return list(ModelCapability)

    async def analyze_content(
        self,
        content: str,
        task: ModelCapability,
        model: str | None = None,
        **kwargs,
    ) -> ModelResponse:
        """
        Analyze content using Claude API.

        Args:
            content: Text content to analyze
            task: Type of analysis
            model: Optional specific model
            **kwargs: Additional options:
                - temperature: Sampling temperature
                - max_tokens: Maximum response tokens

        Returns:
            ModelResponse with analysis results
        """
        # Validate content
        if not self.validate_content(content, max_length=200000):
            return self.create_response(
                success=False,
                model=model or self.default_model,
                task=task,
                error="Invalid content provided",
            )

        # Check if initialized
        if not self._initialized:
            await self.initialize()

        if not self._initialized:
            return self.create_response(
                success=False,
                model=model or self.default_model,
                task=task,
                error="Claude provider not initialized",
            )

        # Select model
        selected_model = model or self.default_model

        # Generate prompt
        prompt = self.get_task_prompt(task, content)

        # Call Claude API with retry logic
        return await self.analyze_with_retry(
            self._call_claude_api,
            prompt,
            task,
            selected_model,
            **kwargs,
        )

    async def _call_claude_api(
        self,
        prompt: str,
        task: ModelCapability,
        model: str,
        **kwargs,
    ) -> ModelResponse:
        """
        Internal method to call the Claude Messages API.

        Args:
            prompt: Generated prompt (already includes content)
            task: Task capability being performed
            model: Model identifier to invoke
            **kwargs: Additional options:
                - temperature: Sampling temperature (default 0.7)
                - max_tokens: Maximum response tokens (default self.max_tokens)
                - system: Optional system prompt

        Returns:
            ModelResponse with the assistant's text and token usage metadata.
        """
        if self._client is None:
            return self.create_response(
                success=False,
                model=model,
                task=task,
                error="Claude provider client is not initialized",
            )

        if not HAS_ANTHROPIC or anthropic is None:
            return self.create_response(
                success=False,
                model=model,
                task=task,
                error="anthropic package not installed",
            )

        request_kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", 0.7),
            "messages": [{"role": "user", "content": prompt}],
        }
        system_prompt = kwargs.get("system")
        if system_prompt:
            request_kwargs["system"] = system_prompt

        try:
            message = await self._client.messages.create(**request_kwargs)
        except anthropic.AuthenticationError as e:
            self.log_error(f"Claude authentication error: {e}")
            return self.create_response(
                success=False,
                model=model,
                task=task,
                error=f"Authentication error: {e}",
            )
        except anthropic.RateLimitError as e:
            self.log_warning(f"Claude rate limit exceeded: {e}")
            return self.create_response(
                success=False,
                model=model,
                task=task,
                error=f"Rate limit exceeded: {e}",
            )
        except anthropic.APIError as e:
            self.log_error(f"Claude API error: {e}")
            return self.create_response(
                success=False,
                model=model,
                task=task,
                error=f"Claude API error: {e}",
            )
        except Exception as e:  # pragma: no cover - defensive catch-all
            self.log_error(f"Unexpected error calling Claude API: {e}")
            return self.create_response(
                success=False,
                model=model,
                task=task,
                error=f"Unexpected error: {e}",
            )

        # Extract text from content blocks. The Messages API returns a list of
        # content blocks; we concatenate text blocks for a flat string result.
        result_text = ""
        for block in getattr(message, "content", []) or []:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                result_text += getattr(block, "text", "") or ""

        usage = getattr(message, "usage", None)
        metadata: dict[str, Any] = {
            "model": getattr(message, "model", model),
            "stop_reason": getattr(message, "stop_reason", None),
        }
        if usage is not None:
            metadata["usage"] = {
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
            }

        return self.create_response(
            success=True,
            model=model,
            task=task,
            result=result_text,
            metadata=metadata,
        )

    def _generate_mock_analysis(self, task: ModelCapability) -> str:
        """
        Generate mock analysis for Phase 1 testing.

        Args:
            task: Task capability

        Returns:
            Mock analysis text
        """
        mock_responses = {
            ModelCapability.SEO_ANALYSIS: """SEO Analysis (Mock):
1. Primary keywords: content, analysis, optimization
2. Keyword density: Moderate (2-3%)
3. Meta description: Well-structured content with clear focus
4. Title optimization: Consider adding target keywords
5. Content structure: Good use of headers
6. SEO Score: 75/100 - Good foundation, room for improvement""",
            ModelCapability.READABILITY: """Readability Analysis (Mock):
1. Flesch Reading Ease: 65 (Standard)
2. Average sentence length: 15 words
3. Complex words: 12% of total
4. Grade level: 10th grade
5. Suggestions: Consider simplifying complex sentences
6. Overall rating: Medium readability""",
            ModelCapability.GRAMMAR: """Grammar Check (Mock):
1. Grammatical errors: None detected
2. Spelling: All correct
3. Punctuation: Appropriate usage
4. Style: Consistent and clear
5. Clarity: Well-expressed ideas
6. Quality score: 95/100 - Excellent""",
            ModelCapability.SUMMARIZATION: """Summary (Mock):
Main Points:
- Content provides valuable information
- Structure is logical and well-organized
- Key concepts are clearly explained

TL;DR: Well-structured content with clear messaging and good organization.""",
            ModelCapability.KEYWORD_EXTRACTION: """Keyword Extraction (Mock):
Primary Keywords:
1. content (relevance: 0.95)
2. analysis (relevance: 0.88)
3. quality (relevance: 0.82)
4. structure (relevance: 0.75)
5. optimization (relevance: 0.70)

Long-tail phrases:
- "content analysis"
- "quality optimization"
- "structured content"

Suggested additions: performance, effectiveness, improvement""",
            ModelCapability.ACCESSIBILITY: """Accessibility Analysis (Mock):
1. Language complexity: Moderate (10th grade level)
2. Inclusivity: Good, neutral language used
3. Plain language: Some jargon, consider simplification
4. Potential barriers: Technical terminology may challenge some readers
5. WCAG compliance: Meets basic guidelines
6. Accessibility score: 80/100 - Good with room for improvement""",
            ModelCapability.SENTIMENT: """Sentiment Analysis (Mock):
1. Overall sentiment: Positive
2. Sentiment score: +0.6 (Moderately positive)
3. Emotional tone: Professional, informative
4. Audience perception: Likely to be well-received
5. Tone consistency: Maintained throughout""",
            ModelCapability.GENERAL: """General Analysis (Mock):
1. Overview: Well-structured content with clear objectives
2. Quality: High-quality writing with good organization
3. Structure: Logical flow with appropriate sections
4. Improvements: Consider adding more examples
5. Effectiveness: 80/100 - Strong overall performance""",
        }

        return mock_responses.get(
            task,
            "Mock analysis completed. Phase 2 will provide detailed results.",
        )

    async def get_model_info(self, model: str) -> dict[str, Any]:
        """
        Get detailed information about a Claude model.

        Args:
            model: Model identifier

        Returns:
            Dictionary with model information
        """
        # Model information based on public documentation
        model_info = {
            "claude-3-5-sonnet-20241022": {
                "name": "Claude 3.5 Sonnet",
                "version": "20241022",
                "context_window": 200000,
                "max_output": 8192,
                "capabilities": ["analysis", "reasoning", "coding", "writing"],
                "speed": "fast",
                "cost": "medium",
            },
            "claude-3-5-haiku-20241022": {
                "name": "Claude 3.5 Haiku",
                "version": "20241022",
                "context_window": 200000,
                "max_output": 8192,
                "capabilities": ["quick_analysis", "summarization"],
                "speed": "fastest",
                "cost": "low",
            },
            "claude-3-opus-20240229": {
                "name": "Claude 3 Opus",
                "version": "20240229",
                "context_window": 200000,
                "max_output": 4096,
                "capabilities": ["complex_reasoning", "detailed_analysis"],
                "speed": "slower",
                "cost": "high",
            },
        }

        return model_info.get(
            model,
            {
                "name": model,
                "error": "Model information not available",
            },
        )


__all__ = ["ClaudeProvider"]
