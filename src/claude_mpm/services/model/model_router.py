"""
Model Router Implementation for Claude MPM Framework
====================================================

WHY: Provides intelligent routing between local (Ollama) and cloud (Claude)
models with automatic fallback, enabling hybrid operation that balances
privacy, cost, and reliability.

DESIGN DECISION: Chain of Responsibility pattern - tries providers in priority
order until one succeeds. Configuration controls routing strategy (auto, local-only,
cloud-only, privacy-first).

ROUTING STRATEGIES:
- AUTO: Try Ollama first, fallback to Claude on error (default)
- OLLAMA: Local-only, fail if unavailable (privacy mode)
- CLAUDE: Cloud-only, always use Claude
- PRIVACY: Like OLLAMA but with better error messages

ARCHITECTURE:
- Manages provider lifecycle (initialization, shutdown)
- Routes requests based on strategy and availability
- Tracks routing decisions and fallbacks for monitoring
- Provides unified interface hiding provider complexity
"""

from enum import Enum
from typing import Any, Dict, Optional

from claude_mpm.core.logger import get_logger
from claude_mpm.services.core.base import BaseService
from claude_mpm.services.core.interfaces.model import (
    IModelRouter,
    ModelCapability,
    ModelResponse,
)
from claude_mpm.services.model.claude_provider import ClaudeProvider
from claude_mpm.services.model.ollama_provider import OllamaProvider


class RoutingStrategy(Enum):
    """
    Routing strategies for model selection.

    WHY: Provides different operational modes based on user preferences
    for privacy, cost, and reliability.
    """

    AUTO = "auto"  # Try Ollama first, fallback to Claude
    OLLAMA_ONLY = "ollama"  # Local only, fail if unavailable
    CLAUDE_ONLY = "claude"  # Cloud only, always use Claude
    PRIVACY_FIRST = "privacy"  # Like OLLAMA_ONLY but explicit about privacy


class ModelRouter(BaseService, IModelRouter):
    """
    Intelligent model router with automatic fallback.

    WHY: Provides seamless switching between local and cloud models based on
    availability and configuration. Enables privacy-preserving operation with
    cloud fallback when needed.

    Configuration:
        strategy: Routing strategy (auto/ollama/claude/privacy)
        ollama_config: Configuration for Ollama provider
        claude_config: Configuration for Claude provider
        fallback_enabled: Allow fallback to cloud (default: True for AUTO)
        max_retries: Maximum retry attempts per provider (default: 2)

    Usage:
        router = ModelRouter(config={
            "strategy": "auto",
            "ollama_config": {"host": "http://localhost:11434"}
        })

        await router.initialize()

        response = await router.analyze_content(
            content="Your content",
            task=ModelCapability.SEO_ANALYSIS
        )

    Routing Logic:
        AUTO: Ollama available? → Use Ollama → On error → Try Claude
        OLLAMA_ONLY: Ollama available? → Use Ollama → On error → Fail
        CLAUDE_ONLY: Always use Claude
        PRIVACY_FIRST: Like OLLAMA_ONLY but with privacy-focused messages
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize model router.

        Args:
            config: Router configuration
        """
        super().__init__(service_name="model_router", config=config or {})

        self.logger = get_logger("model.router")

        # Parse strategy
        strategy_str = self.get_config("strategy", "auto")
        try:
            self.strategy = RoutingStrategy(strategy_str.lower())
        except ValueError:
            self.log_warning(f"Invalid strategy '{strategy_str}', defaulting to AUTO")
            self.strategy = RoutingStrategy.AUTO

        # Fallback configuration
        self.fallback_enabled = self.get_config(
            "fallback_enabled",
            self.strategy == RoutingStrategy.AUTO,
        )
        self.max_retries = self.get_config("max_retries", 2)

        # Initialize providers
        ollama_config = self.get_config("ollama_config", {})
        claude_config = self.get_config("claude_config", {})

        self.ollama_provider = OllamaProvider(config=ollama_config)
        self.claude_provider = ClaudeProvider(config=claude_config)

        # Routing metrics
        self._route_count: Dict[str, int] = {"ollama": 0, "claude": 0}
        self._fallback_count = 0
        self._active_provider: Optional[str] = None

    async def initialize(self) -> bool:
        """
        Initialize router and providers.

        Returns:
            True if at least one provider initialized successfully
        """
        self.log_info(f"Initializing model router with strategy: {self.strategy.value}")

        success = False

        # Initialize providers based on strategy
        if self.strategy in (
            RoutingStrategy.AUTO,
            RoutingStrategy.OLLAMA_ONLY,
            RoutingStrategy.PRIVACY_FIRST,
        ):
            self.log_info("Initializing Ollama provider...")
            if await self.ollama_provider.initialize():
                self.log_info("Ollama provider initialized successfully")
                success = True
            else:
                self.log_warning("Ollama provider initialization failed")

        if self.strategy in (RoutingStrategy.AUTO, RoutingStrategy.CLAUDE_ONLY):
            self.log_info("Initializing Claude provider...")
            if await self.claude_provider.initialize():
                self.log_info("Claude provider initialized successfully")
                success = True
            else:
                self.log_warning("Claude provider initialization failed")

        if not success:
            self.log_error("No providers initialized successfully")
            return False

        self._initialized = True
        return True

    async def shutdown(self) -> None:
        """Shutdown router and all providers."""
        self.log_info("Shutting down model router")

        # Shutdown providers
        if self.ollama_provider:
            await self.ollama_provider.shutdown()

        if self.claude_provider:
            await self.claude_provider.shutdown()

        self._shutdown = True

    def get_active_provider(self) -> Optional[str]:
        """
        Get name of currently active provider.

        Returns:
            Provider name or None
        """
        return self._active_provider

    async def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all configured providers.

        Returns:
            Dictionary mapping provider names to status info
        """
        status = {}

        # Check Ollama
        if self.strategy in (
            RoutingStrategy.AUTO,
            RoutingStrategy.OLLAMA_ONLY,
            RoutingStrategy.PRIVACY_FIRST,
        ):
            ollama_available = await self.ollama_provider.is_available()
            ollama_models = (
                await self.ollama_provider.get_available_models()
                if ollama_available
                else []
            )

            status["ollama"] = {
                "available": ollama_available,
                "initialized": self.ollama_provider.is_initialized,
                "models_count": len(ollama_models),
                "metrics": self.ollama_provider.get_metrics(),
            }

        # Check Claude
        if self.strategy in (RoutingStrategy.AUTO, RoutingStrategy.CLAUDE_ONLY):
            claude_available = await self.claude_provider.is_available()

            status["claude"] = {
                "available": claude_available,
                "initialized": self.claude_provider.is_initialized,
                "metrics": self.claude_provider.get_metrics(),
            }

        # Add routing metrics
        status["router"] = {
            "strategy": self.strategy.value,
            "fallback_enabled": self.fallback_enabled,
            "route_count": self._route_count.copy(),
            "fallback_count": self._fallback_count,
            "active_provider": self._active_provider,
        }

        return status

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
            task: Type of analysis
            model: Optional specific model
            **kwargs: Provider-specific options

        Returns:
            ModelResponse from successful provider
        """
        if not self._initialized:
            return self._create_error_response(
                task,
                model,
                "Router not initialized",
            )

        # Route based on strategy
        if self.strategy == RoutingStrategy.CLAUDE_ONLY:
            return await self._route_to_claude(content, task, model=model, **kwargs)

        if self.strategy in (
            RoutingStrategy.OLLAMA_ONLY,
            RoutingStrategy.PRIVACY_FIRST,
        ):
            return await self._route_to_ollama(
                content,
                task,
                model=model,
                require_success=True,
                **kwargs,
            )

        # AUTO strategy
        return await self._route_auto(content, task, model=model, **kwargs)

    async def _route_auto(
        self,
        content: str,
        task: ModelCapability,
        model: Optional[str],
        **kwargs,
    ) -> ModelResponse:
        """
        Auto routing: Try Ollama first, fallback to Claude.

        Args:
            content: Content to analyze
            task: Task to perform
            model: Optional model
            **kwargs: Additional options

        Returns:
            ModelResponse from successful provider
        """
        # Try Ollama first
        if await self.ollama_provider.is_available():
            self.log_debug("Routing to Ollama (primary)")
            response = await self._route_to_ollama(
                content,
                task,
                model=model,
                require_success=False,
                **kwargs,
            )

            if response.success:
                return response

            # Ollama failed, try fallback
            self.log_warning(
                f"Ollama analysis failed: {response.error}, trying Claude fallback"
            )
            self._fallback_count += 1

        # Ollama unavailable or failed - fallback to Claude
        if self.fallback_enabled:
            self.log_info("Falling back to Claude")
            return await self._route_to_claude(content, task, model=model, **kwargs)
        return self._create_error_response(
            task,
            model,
            "Ollama unavailable and fallback disabled",
        )

    async def _route_to_ollama(
        self,
        content: str,
        task: ModelCapability,
        model: Optional[str],
        require_success: bool = False,
        **kwargs,
    ) -> ModelResponse:
        """
        Route to Ollama provider.

        Args:
            content: Content to analyze
            task: Task to perform
            model: Optional model
            require_success: If True, check availability first
            **kwargs: Additional options

        Returns:
            ModelResponse
        """
        if require_success and not await self.ollama_provider.is_available():
            if self.strategy == RoutingStrategy.PRIVACY_FIRST:
                error_msg = (
                    "Ollama not available. Privacy mode enabled - not sending to cloud."
                )
            else:
                error_msg = "Ollama not available and required by configuration"

            return self._create_error_response(task, model, error_msg)

        self._active_provider = "ollama"
        self._route_count["ollama"] += 1

        return await self.ollama_provider.analyze_content(
            content, task, model=model, **kwargs
        )

    async def _route_to_claude(
        self,
        content: str,
        task: ModelCapability,
        model: Optional[str],
        **kwargs,
    ) -> ModelResponse:
        """
        Route to Claude provider.

        Args:
            content: Content to analyze
            task: Task to perform
            model: Optional model
            **kwargs: Additional options

        Returns:
            ModelResponse
        """
        self._active_provider = "claude"
        self._route_count["claude"] += 1

        return await self.claude_provider.analyze_content(
            content, task, model=model, **kwargs
        )

    def _create_error_response(
        self,
        task: ModelCapability,
        model: Optional[str],
        error: str,
    ) -> ModelResponse:
        """
        Create error response.

        Args:
            task: Task that was attempted
            model: Model that was requested
            error: Error message

        Returns:
            ModelResponse with error
        """
        return ModelResponse(
            success=False,
            provider="router",
            model=model or "unknown",
            task=task.value,
            result="",
            error=error,
        )

    def get_routing_metrics(self) -> Dict[str, Any]:
        """
        Get routing performance metrics.

        Returns:
            Dictionary of routing metrics
        """
        total_routes = sum(self._route_count.values())
        ollama_percentage = (
            (self._route_count["ollama"] / total_routes * 100)
            if total_routes > 0
            else 0
        )

        return {
            "strategy": self.strategy.value,
            "total_routes": total_routes,
            "ollama_routes": self._route_count["ollama"],
            "claude_routes": self._route_count["claude"],
            "ollama_percentage": ollama_percentage,
            "fallback_count": self._fallback_count,
            "fallback_rate": (
                (self._fallback_count / total_routes * 100) if total_routes > 0 else 0
            ),
        }


__all__ = ["ModelRouter", "RoutingStrategy"]
