"""
Model Provider Interfaces for Claude MPM Framework
==================================================

WHY: This module defines the interfaces for content processing model providers,
enabling support for both local (Ollama) and cloud (Claude) models with
intelligent routing and auto-fallback capabilities.

DESIGN DECISION: Model providers implement a common interface (IModelProvider)
to enable polymorphic use and easy switching between providers. The abstraction
allows for provider-specific optimizations while maintaining a consistent API.

ARCHITECTURE:
- IModelProvider: Core provider interface for content analysis
- ModelCapability: Enum of supported content processing tasks
- ModelProvider: Enum of available provider types
- ModelResponse: Standardized response format across providers

USAGE:
    provider = OllamaProvider()
    if await provider.is_available():
        response = await provider.analyze_content(
            content="Your text here",
            task=ModelCapability.SEO_ANALYSIS
        )
        if response.success:
            print(f"Analysis from {response.model}: {response.result}")
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ModelCapability(Enum):
    """
    Content processing capabilities supported by model providers.

    WHY: Defines task-specific analysis types for content processing.
    Each capability may route to different models optimized for that task.
    """

    SEO_ANALYSIS = "seo_analysis"
    READABILITY = "readability"
    GRAMMAR = "grammar"
    SUMMARIZATION = "summarization"
    KEYWORD_EXTRACTION = "keyword_extraction"
    ACCESSIBILITY = "accessibility"
    SENTIMENT = "sentiment"
    GENERAL = "general"


class ModelProvider(Enum):
    """
    Available model provider backends.

    WHY: Enables configuration-based routing between providers.

    Values:
        CLAUDE: Cloud-based Claude API (always available)
        OLLAMA: Local Ollama installation (requires local setup)
        AUTO: Intelligent routing with Ollama-first, Claude fallback
    """

    CLAUDE = "claude"
    OLLAMA = "ollama"
    AUTO = "auto"


@dataclass
class ModelResponse:
    """
    Standardized response from model providers.

    WHY: Provides consistent response format across all providers,
    enabling transparent provider switching and unified error handling.

    Attributes:
        success: Whether the operation succeeded
        provider: Name of provider that handled request (e.g., "ollama", "claude")
        model: Specific model used (e.g., "llama3.3:70b", "claude-3-5-sonnet")
        task: Task that was performed
        result: Analysis result text
        metadata: Provider-specific metadata (tokens, timing, etc.)
        error: Error message if success=False
    """

    success: bool
    provider: str
    model: str
    task: str
    result: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary for serialization."""
        return {
            "success": self.success,
            "provider": self.provider,
            "model": self.model,
            "task": self.task,
            "result": self.result,
            "metadata": self.metadata,
            "error": self.error,
        }


class IModelProvider(ABC):
    """
    Interface for content processing model providers.

    WHY: Defines contract for all model providers (Claude, Ollama, future providers).
    Enables polymorphic use and easy provider switching without changing client code.

    DESIGN PATTERN: Strategy pattern - allows runtime selection of model provider
    based on availability, configuration, and task requirements.

    Implementations should:
    - Handle provider-specific connection management
    - Map capabilities to optimal models
    - Provide robust error handling
    - Return standardized ModelResponse objects
    """

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if provider is available and functional.

        WHY: Enables auto-fallback routing. Local providers may not always be
        available (Ollama not running), while cloud providers need API keys.

        Returns:
            True if provider is ready to handle requests
        """

    @abstractmethod
    async def analyze_content(
        self,
        content: str,
        task: ModelCapability,
        model: Optional[str] = None,
        **kwargs,
    ) -> ModelResponse:
        """
        Analyze content with specified task.

        WHY: Core content processing method. Handles all analysis types
        with task-specific prompting and model selection.

        Args:
            content: Text content to analyze
            task: Type of analysis to perform
            model: Optional specific model to use (overrides default)
            **kwargs: Provider-specific options (temperature, max_tokens, etc.)

        Returns:
            ModelResponse with analysis results or error

        Example:
            response = await provider.analyze_content(
                content="Your article text",
                task=ModelCapability.SEO_ANALYSIS,
                temperature=0.7
            )
        """

    @abstractmethod
    def get_supported_capabilities(self) -> List[ModelCapability]:
        """
        Return list of capabilities this provider supports.

        WHY: Enables capability-based routing. Some providers may not
        support all task types.

        Returns:
            List of supported ModelCapability values
        """

    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """
        List models available from this provider.

        WHY: Enables model validation and user selection. Local providers
        may have different models installed than expected.

        Returns:
            List of model names/identifiers

        Example:
            models = await provider.get_available_models()
            # ["llama3.3:70b", "gemma2:9b", "mistral:7b"]
        """

    @abstractmethod
    async def get_model_info(self, model: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific model.

        WHY: Provides model metadata for UI display and capability checking.

        Args:
            model: Model name/identifier

        Returns:
            Dictionary with model details (size, parameters, capabilities, etc.)
        """

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Shutdown provider and cleanup resources.

        WHY: Proper resource cleanup for connection pools, HTTP sessions, etc.
        """


class IModelRouter(ABC):
    """
    Interface for intelligent model routing with fallback.

    WHY: Manages provider selection and fallback logic. Routes requests
    to optimal provider based on availability and configuration.

    DESIGN PATTERN: Chain of Responsibility - tries providers in order
    until one succeeds or all fail.
    """

    @abstractmethod
    async def analyze_content(
        self,
        content: str,
        task: ModelCapability,
        model: Optional[str] = None,
        **kwargs,
    ) -> ModelResponse:
        """
        Route content analysis to optimal provider.

        WHY: Single entry point for all content analysis. Handles provider
        selection, fallback, and error recovery transparently.

        Args:
            content: Text content to analyze
            task: Type of analysis to perform
            model: Optional specific model to use
            **kwargs: Provider-specific options

        Returns:
            ModelResponse from successful provider
        """

    @abstractmethod
    def get_active_provider(self) -> Optional[str]:
        """
        Get name of currently active provider.

        Returns:
            Provider name or None if no provider active
        """

    @abstractmethod
    async def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all configured providers.

        Returns:
            Dictionary mapping provider names to status info
        """


__all__ = [
    "IModelProvider",
    "IModelRouter",
    "ModelCapability",
    "ModelProvider",
    "ModelResponse",
]
