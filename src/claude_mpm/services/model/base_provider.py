"""
Base Model Provider Implementation for Claude MPM Framework
===========================================================

WHY: Provides common functionality for all model providers, reducing
duplication and ensuring consistent behavior across implementations.

DESIGN DECISION: Abstract base class extends both BaseService and IModelProvider,
providing service lifecycle management plus model-specific utilities.

RESPONSIBILITIES:
- Common error handling and logging
- Task-specific prompt generation
- Response formatting and validation
- Performance metrics tracking
- Retry logic for transient failures
"""

import asyncio
import time
from abc import abstractmethod
from typing import Any, Dict, Optional

from claude_mpm.core.logger import get_logger
from claude_mpm.services.core.base import BaseService
from claude_mpm.services.core.interfaces.model import (
    IModelProvider,
    ModelCapability,
    ModelResponse,
)


class BaseModelProvider(BaseService, IModelProvider):
    """
    Abstract base class for model providers.

    WHY: Centralizes common provider functionality like prompt generation,
    error handling, and response formatting.

    Usage:
        class MyProvider(BaseModelProvider):
            async def analyze_content(self, content, task, model=None, **kwargs):
                prompt = self.get_task_prompt(task, content)
                # Call provider API
                return self.create_response(...)
    """

    # Task-specific prompt templates
    TASK_PROMPTS: Dict[ModelCapability, str] = {
        ModelCapability.SEO_ANALYSIS: """Analyze the following content for SEO effectiveness. Provide:
1. Primary and secondary keywords identified
2. Keyword density analysis
3. Meta description recommendation
4. Title tag optimization suggestions
5. Content structure analysis (H1, H2, etc.)
6. SEO score (0-100) with justification

Content to analyze:
{content}

Provide your analysis in a structured format.""",
        ModelCapability.READABILITY: """Analyze the readability of the following content. Provide:
1. Readability score (Flesch-Kincaid or similar)
2. Average sentence length
3. Complex word count
4. Grade level assessment
5. Suggestions for improvement
6. Overall readability rating (Easy/Medium/Hard)

Content to analyze:
{content}

Provide your analysis in a structured format.""",
        ModelCapability.GRAMMAR: """Perform a grammar and style check on the following content. Identify:
1. Grammatical errors with corrections
2. Spelling mistakes
3. Punctuation issues
4. Style inconsistencies
5. Clarity improvements
6. Overall quality score (0-100)

Content to analyze:
{content}

Provide your analysis in a structured format.""",
        ModelCapability.SUMMARIZATION: """Provide a comprehensive summary of the following content:
1. Main topic and key points (3-5 bullet points)
2. Supporting details
3. Conclusions or recommendations
4. One-sentence TL;DR

Content to summarize:
{content}

Provide your summary in a structured format.""",
        ModelCapability.KEYWORD_EXTRACTION: """Extract and analyze keywords from the following content:
1. Primary keywords (top 5-10)
2. Long-tail keyword phrases
3. Semantic relationships between keywords
4. Keyword relevance scores
5. Suggested additional keywords

Content to analyze:
{content}

Provide your keyword analysis in a structured format.""",
        ModelCapability.ACCESSIBILITY: """Analyze the accessibility of the following content:
1. Language complexity level
2. Inclusivity assessment
3. Plain language recommendations
4. Potential barriers for readers with disabilities
5. WCAG compliance suggestions
6. Accessibility score (0-100)

Content to analyze:
{content}

Provide your analysis in a structured format.""",
        ModelCapability.SENTIMENT: """Analyze the sentiment and tone of the following content:
1. Overall sentiment (Positive/Negative/Neutral)
2. Sentiment score (-1 to +1)
3. Emotional tone detected
4. Audience perception analysis
5. Tone consistency evaluation

Content to analyze:
{content}

Provide your analysis in a structured format.""",
        ModelCapability.GENERAL: """Analyze the following content and provide:
1. Overview and main themes
2. Quality assessment
3. Structural analysis
4. Improvement suggestions
5. Overall effectiveness rating

Content to analyze:
{content}

Provide your analysis in a structured format.""",
    }

    def __init__(
        self,
        provider_name: str,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize base model provider.

        Args:
            provider_name: Name of the provider (e.g., "ollama", "claude")
            config: Provider-specific configuration
        """
        super().__init__(service_name=f"{provider_name}_provider", config=config)
        self.provider_name = provider_name
        self.logger = get_logger(f"model.{provider_name}")
        self._request_count = 0
        self._error_count = 0
        self._total_latency = 0.0

    def get_task_prompt(self, task: ModelCapability, content: str) -> str:
        """
        Generate task-specific prompt.

        WHY: Centralizes prompt engineering. Tasks require different analysis
        approaches and output formats.

        Args:
            task: Type of analysis to perform
            content: Content to analyze

        Returns:
            Formatted prompt string
        """
        template = self.TASK_PROMPTS.get(
            task, self.TASK_PROMPTS[ModelCapability.GENERAL]
        )
        return template.format(content=content)

    def create_response(
        self,
        success: bool,
        model: str,
        task: ModelCapability,
        result: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> ModelResponse:
        """
        Create standardized model response.

        WHY: Ensures consistent response format across all providers.

        Args:
            success: Whether operation succeeded
            model: Model used
            task: Task performed
            result: Analysis result
            metadata: Additional metadata
            error: Error message if failed

        Returns:
            ModelResponse object
        """
        return ModelResponse(
            success=success,
            provider=self.provider_name,
            model=model,
            task=task.value,
            result=result,
            metadata=metadata or {},
            error=error,
        )

    async def analyze_with_retry(
        self,
        analyze_func,
        content: str,
        task: ModelCapability,
        model: Optional[str] = None,
        max_retries: int = 3,
        **kwargs,
    ) -> ModelResponse:
        """
        Execute analysis with retry logic.

        WHY: Handles transient failures (network issues, rate limits, etc.)
        without requiring retry logic in each provider implementation.

        Args:
            analyze_func: Async function to call for analysis
            content: Content to analyze
            task: Task to perform
            model: Optional model to use
            max_retries: Maximum retry attempts
            **kwargs: Additional arguments for analyze_func

        Returns:
            ModelResponse from successful attempt or final error
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                start_time = time.time()
                response = await analyze_func(content, task, model, **kwargs)
                latency = time.time() - start_time

                # Track metrics
                self._request_count += 1
                self._total_latency += latency

                if response.success:
                    response.metadata["latency_seconds"] = latency
                    response.metadata["attempt"] = attempt + 1
                    self.log_debug(
                        f"Analysis completed in {latency:.2f}s (attempt {attempt + 1})"
                    )
                    return response
                last_error = response.error
                self._error_count += 1

            except Exception as e:
                last_error = str(e)
                self._error_count += 1
                self.log_warning(
                    f"Analysis attempt {attempt + 1} failed: {e}",
                    exc_info=True,
                )

            # Wait before retry (exponential backoff)
            if attempt < max_retries - 1:
                wait_time = 2**attempt  # 1s, 2s, 4s
                self.log_info(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

        # All retries failed
        self.log_error(f"All {max_retries} attempts failed. Last error: {last_error}")
        return self.create_response(
            success=False,
            model=model or "unknown",
            task=task,
            error=f"Failed after {max_retries} attempts: {last_error}",
        )

    def validate_content(self, content: str, max_length: Optional[int] = None) -> bool:
        """
        Validate content before analysis.

        WHY: Prevents invalid requests and provides early error detection.

        Args:
            content: Content to validate
            max_length: Optional maximum length in characters

        Returns:
            True if valid, False otherwise
        """
        if not content or not content.strip():
            self.log_warning("Empty content provided for analysis")
            return False

        if max_length and len(content) > max_length:
            self.log_warning(
                f"Content length {len(content)} exceeds maximum {max_length}"
            )
            return False

        return True

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get provider performance metrics.

        Returns:
            Dictionary of metrics (request count, error rate, avg latency)
        """
        avg_latency = (
            self._total_latency / self._request_count if self._request_count > 0 else 0
        )
        error_rate = (
            self._error_count / self._request_count if self._request_count > 0 else 0
        )

        return {
            "provider": self.provider_name,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "error_rate": error_rate,
            "avg_latency_seconds": avg_latency,
        }

    async def initialize(self) -> bool:
        """
        Initialize provider.

        Subclasses should override to perform provider-specific setup.

        Returns:
            True if initialization successful
        """
        self.log_info(f"Initializing {self.provider_name} provider")
        self._initialized = True
        return True

    async def shutdown(self) -> None:
        """
        Shutdown provider and cleanup resources.

        Subclasses should override to perform provider-specific cleanup.
        """
        self.log_info(f"Shutting down {self.provider_name} provider")
        self._shutdown = True

    @abstractmethod
    async def get_model_info(self, model: str) -> Dict[str, Any]:
        """
        Get model information.

        Must be implemented by subclasses.
        """


__all__ = ["BaseModelProvider"]
