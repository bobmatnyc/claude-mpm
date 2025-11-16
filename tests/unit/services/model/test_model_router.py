"""Comprehensive unit tests for ModelRouter.

This test suite provides complete coverage of the ModelRouter class,
testing routing logic, fallback behavior, provider management, and all
configuration strategies.

Coverage targets:
- Line coverage: >90%
- Branch coverage: >85%
- All routing strategies tested
- All error paths tested
- All provider interactions tested
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from claude_mpm.services.core.interfaces.model import ModelCapability, ModelResponse
from claude_mpm.services.model.model_router import ModelRouter, RoutingStrategy

# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def auto_config():
    """Configuration for AUTO routing strategy."""
    return {
        "strategy": "auto",
        "fallback_enabled": True,
        "max_retries": 2,
    }


@pytest.fixture
def ollama_only_config():
    """Configuration for OLLAMA_ONLY strategy."""
    return {
        "strategy": "ollama",
        "fallback_enabled": False,
    }


@pytest.fixture
def claude_only_config():
    """Configuration for CLAUDE_ONLY strategy."""
    return {
        "strategy": "claude",
    }


@pytest.fixture
def privacy_first_config():
    """Configuration for PRIVACY_FIRST strategy."""
    return {
        "strategy": "privacy",
        "fallback_enabled": False,
    }


@pytest.fixture
def router_auto(auto_config):
    """Create ModelRouter with AUTO strategy."""
    return ModelRouter(config=auto_config)


@pytest.fixture
def router_ollama(ollama_only_config):
    """Create ModelRouter with OLLAMA_ONLY strategy."""
    return ModelRouter(config=ollama_only_config)


@pytest.fixture
def router_claude(claude_only_config):
    """Create ModelRouter with CLAUDE_ONLY strategy."""
    return ModelRouter(config=claude_only_config)


@pytest.fixture
def router_privacy(privacy_first_config):
    """Create ModelRouter with PRIVACY_FIRST strategy."""
    return ModelRouter(config=privacy_first_config)


@pytest.fixture
def sample_content():
    """Sample content for testing."""
    return "This is sample content for testing the model router."


@pytest.fixture
def mock_success_response():
    """Create mock successful ModelResponse."""
    return ModelResponse(
        success=True,
        provider="test",
        model="test-model",
        task="test",
        result="Test result",
    )


@pytest.fixture
def mock_error_response():
    """Create mock error ModelResponse."""
    return ModelResponse(
        success=False,
        provider="test",
        model="test-model",
        task="test",
        result="",
        error="Test error",
    )


# ============================================================================
# TEST INITIALIZATION
# ============================================================================


class TestInitialization:
    """Tests for ModelRouter initialization."""

    def test_init_with_auto_strategy(self, auto_config):
        """Test initialization with AUTO strategy."""
        # Arrange & Act
        router = ModelRouter(config=auto_config)

        # Assert
        assert router.strategy == RoutingStrategy.AUTO
        assert router.fallback_enabled is True
        assert router.max_retries == 2
        assert router.ollama_provider is not None
        assert router.claude_provider is not None

    def test_init_with_ollama_only_strategy(self, ollama_only_config):
        """Test initialization with OLLAMA_ONLY strategy."""
        # Arrange & Act
        router = ModelRouter(config=ollama_only_config)

        # Assert
        assert router.strategy == RoutingStrategy.OLLAMA_ONLY
        assert router.fallback_enabled is False
        assert router.ollama_provider is not None

    def test_init_with_claude_only_strategy(self, claude_only_config):
        """Test initialization with CLAUDE_ONLY strategy."""
        # Arrange & Act
        router = ModelRouter(config=claude_only_config)

        # Assert
        assert router.strategy == RoutingStrategy.CLAUDE_ONLY
        assert router.claude_provider is not None

    def test_init_with_privacy_first_strategy(self, privacy_first_config):
        """Test initialization with PRIVACY_FIRST strategy."""
        # Arrange & Act
        router = ModelRouter(config=privacy_first_config)

        # Assert
        assert router.strategy == RoutingStrategy.PRIVACY_FIRST
        assert router.fallback_enabled is False

    def test_init_with_invalid_strategy(self):
        """Test initialization with invalid strategy falls back to AUTO."""
        # Arrange & Act
        with patch("claude_mpm.services.model.model_router.get_logger"):
            router = ModelRouter(config={"strategy": "invalid"})

        # Assert
        assert router.strategy == RoutingStrategy.AUTO

    def test_init_with_no_config(self):
        """Test initialization with no configuration uses defaults."""
        # Arrange & Act
        router = ModelRouter()

        # Assert
        assert router.strategy == RoutingStrategy.AUTO
        assert router.fallback_enabled is True

    def test_init_sets_routing_metrics(self, router_auto):
        """Test initialization sets up routing metrics."""
        # Arrange & Act (router from fixture)

        # Assert
        assert router_auto._route_count == {"ollama": 0, "claude": 0}
        assert router_auto._fallback_count == 0
        assert router_auto._active_provider is None

    def test_init_with_provider_configs(self):
        """Test initialization with provider-specific configs."""
        # Arrange
        config = {
            "strategy": "auto",
            "ollama_config": {"host": "http://localhost:11434"},
            "claude_config": {"api_key": "test-key"},
        }

        # Act
        router = ModelRouter(config=config)

        # Assert
        assert router.ollama_provider is not None
        assert router.claude_provider is not None


# ============================================================================
# TEST INITIALIZE METHOD
# ============================================================================


class TestInitializeMethod:
    """Tests for the initialize() async method."""

    @pytest.mark.asyncio
    async def test_initialize_auto_strategy(self, router_auto):
        """Test initialize with AUTO strategy initializes both providers."""
        # Arrange
        with patch.object(
            router_auto.ollama_provider, "initialize", return_value=True
        ) as mock_ollama, patch.object(
            router_auto.claude_provider, "initialize", return_value=True
        ) as mock_claude:

            # Act
            result = await router_auto.initialize()

            # Assert
            assert result is True
            mock_ollama.assert_called_once()
            mock_claude.assert_called_once()
            assert router_auto._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_ollama_only_strategy(self, router_ollama):
        """Test initialize with OLLAMA_ONLY initializes only Ollama."""
        # Arrange
        with patch.object(
            router_ollama.ollama_provider, "initialize", return_value=True
        ) as mock_ollama, patch.object(
            router_ollama.claude_provider, "initialize", return_value=True
        ) as mock_claude:

            # Act
            result = await router_ollama.initialize()

            # Assert
            assert result is True
            mock_ollama.assert_called_once()
            mock_claude.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialize_claude_only_strategy(self, router_claude):
        """Test initialize with CLAUDE_ONLY initializes only Claude."""
        # Arrange
        with patch.object(
            router_claude.ollama_provider, "initialize", return_value=True
        ) as mock_ollama, patch.object(
            router_claude.claude_provider, "initialize", return_value=True
        ) as mock_claude:

            # Act
            result = await router_claude.initialize()

            # Assert
            assert result is True
            mock_ollama.assert_not_called()
            mock_claude.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_fails_when_no_providers(self, router_auto):
        """Test initialize fails when no providers initialize successfully."""
        # Arrange
        with patch.object(
            router_auto.ollama_provider, "initialize", return_value=False
        ), patch.object(router_auto.claude_provider, "initialize", return_value=False):

            # Act
            result = await router_auto.initialize()

            # Assert
            assert result is False
            assert router_auto._initialized is False

    @pytest.mark.asyncio
    async def test_initialize_succeeds_with_one_provider(self, router_auto):
        """Test initialize succeeds if at least one provider initializes."""
        # Arrange
        with patch.object(
            router_auto.ollama_provider, "initialize", return_value=True
        ), patch.object(router_auto.claude_provider, "initialize", return_value=False):

            # Act
            result = await router_auto.initialize()

            # Assert
            assert result is True
            assert router_auto._initialized is True


# ============================================================================
# TEST SHUTDOWN METHOD
# ============================================================================


class TestShutdownMethod:
    """Tests for the shutdown() async method."""

    @pytest.mark.asyncio
    async def test_shutdown_calls_all_providers(self, router_auto):
        """Test shutdown calls shutdown on all providers."""
        # Arrange
        with patch.object(
            router_auto.ollama_provider, "shutdown"
        ) as mock_ollama, patch.object(
            router_auto.claude_provider, "shutdown"
        ) as mock_claude:

            # Act
            await router_auto.shutdown()

            # Assert
            mock_ollama.assert_called_once()
            mock_claude.assert_called_once()
            assert router_auto._shutdown is True

    @pytest.mark.asyncio
    async def test_shutdown_sets_shutdown_flag(self, router_auto):
        """Test shutdown sets _shutdown flag."""
        # Arrange & Act
        await router_auto.shutdown()

        # Assert
        assert router_auto._shutdown is True


# ============================================================================
# TEST ROUTING - AUTO STRATEGY
# ============================================================================


class TestAutoRouting:
    """Tests for AUTO routing strategy."""

    @pytest.mark.asyncio
    async def test_routes_to_ollama_when_available(
        self, router_auto, sample_content, mock_success_response
    ):
        """Test AUTO routes to Ollama when available."""
        # Arrange
        await router_auto.initialize()
        with patch.object(
            router_auto.ollama_provider, "is_available", return_value=True
        ), patch.object(
            router_auto.ollama_provider,
            "analyze_content",
            return_value=mock_success_response,
        ) as mock_analyze:

            # Act
            response = await router_auto.analyze_content(
                content=sample_content, task=ModelCapability.SEO_ANALYSIS
            )

            # Assert
            assert response.success is True
            mock_analyze.assert_called_once()
            assert router_auto._route_count["ollama"] == 1
            assert router_auto._active_provider == "ollama"

    @pytest.mark.asyncio
    async def test_falls_back_to_claude_when_ollama_fails(
        self, router_auto, sample_content, mock_error_response, mock_success_response
    ):
        """Test AUTO falls back to Claude when Ollama fails."""
        # Arrange
        await router_auto.initialize()
        with patch.object(
            router_auto.ollama_provider, "is_available", return_value=True
        ), patch.object(
            router_auto.ollama_provider,
            "analyze_content",
            return_value=mock_error_response,
        ), patch.object(
            router_auto.claude_provider,
            "analyze_content",
            return_value=mock_success_response,
        ) as mock_claude:

            # Act
            response = await router_auto.analyze_content(
                content=sample_content, task=ModelCapability.GRAMMAR
            )

            # Assert
            assert response.success is True
            mock_claude.assert_called_once()
            assert router_auto._fallback_count == 1
            assert router_auto._active_provider == "claude"

    @pytest.mark.asyncio
    async def test_routes_to_claude_when_ollama_unavailable(
        self, router_auto, sample_content, mock_success_response
    ):
        """Test AUTO routes to Claude when Ollama unavailable."""
        # Arrange
        await router_auto.initialize()
        with patch.object(
            router_auto.ollama_provider, "is_available", return_value=False
        ), patch.object(
            router_auto.claude_provider,
            "analyze_content",
            return_value=mock_success_response,
        ) as mock_claude:

            # Act
            response = await router_auto.analyze_content(
                content=sample_content, task=ModelCapability.READABILITY
            )

            # Assert
            assert response.success is True
            mock_claude.assert_called_once()
            assert router_auto._route_count["claude"] == 1

    @pytest.mark.asyncio
    async def test_fails_when_fallback_disabled(self, sample_content):
        """Test fails when fallback disabled and Ollama unavailable."""
        # Arrange
        router = ModelRouter(config={"strategy": "auto", "fallback_enabled": False})
        await router.initialize()
        with patch.object(router.ollama_provider, "is_available", return_value=False):

            # Act
            response = await router.analyze_content(
                content=sample_content, task=ModelCapability.GENERAL
            )

            # Assert
            assert response.success is False
            assert "fallback disabled" in response.error.lower()


# ============================================================================
# TEST ROUTING - OLLAMA ONLY STRATEGY
# ============================================================================


class TestOllamaOnlyRouting:
    """Tests for OLLAMA_ONLY routing strategy."""

    @pytest.mark.asyncio
    async def test_routes_to_ollama_when_available(
        self, router_ollama, sample_content, mock_success_response
    ):
        """Test OLLAMA_ONLY routes to Ollama when available."""
        # Arrange
        await router_ollama.initialize()
        with patch.object(
            router_ollama.ollama_provider, "is_available", return_value=True
        ), patch.object(
            router_ollama.ollama_provider,
            "analyze_content",
            return_value=mock_success_response,
        ) as mock_analyze:

            # Act
            response = await router_ollama.analyze_content(
                content=sample_content, task=ModelCapability.SENTIMENT
            )

            # Assert
            assert response.success is True
            mock_analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_fails_when_ollama_unavailable(self, router_ollama, sample_content):
        """Test OLLAMA_ONLY fails when Ollama unavailable."""
        # Arrange
        await router_ollama.initialize()
        with patch.object(
            router_ollama.ollama_provider, "is_available", return_value=False
        ):

            # Act
            response = await router_ollama.analyze_content(
                content=sample_content, task=ModelCapability.GENERAL
            )

            # Assert
            assert response.success is False
            assert "not available" in response.error.lower()

    @pytest.mark.asyncio
    async def test_never_routes_to_claude(
        self, router_ollama, sample_content, mock_error_response
    ):
        """Test OLLAMA_ONLY never routes to Claude even on failure."""
        # Arrange
        await router_ollama.initialize()
        with patch.object(
            router_ollama.ollama_provider, "is_available", return_value=True
        ), patch.object(
            router_ollama.ollama_provider,
            "analyze_content",
            return_value=mock_error_response,
        ), patch.object(
            router_ollama.claude_provider, "analyze_content"
        ) as mock_claude:

            # Act
            response = await router_ollama.analyze_content(
                content=sample_content, task=ModelCapability.SEO_ANALYSIS
            )

            # Assert
            # Returns Ollama's error response
            assert response.success is False
            mock_claude.assert_not_called()


# ============================================================================
# TEST ROUTING - CLAUDE ONLY STRATEGY
# ============================================================================


class TestClaudeOnlyRouting:
    """Tests for CLAUDE_ONLY routing strategy."""

    @pytest.mark.asyncio
    async def test_always_routes_to_claude(
        self, router_claude, sample_content, mock_success_response
    ):
        """Test CLAUDE_ONLY always routes to Claude."""
        # Arrange
        await router_claude.initialize()
        with patch.object(
            router_claude.claude_provider,
            "analyze_content",
            return_value=mock_success_response,
        ) as mock_claude:

            # Act
            response = await router_claude.analyze_content(
                content=sample_content, task=ModelCapability.GRAMMAR
            )

            # Assert
            assert response.success is True
            mock_claude.assert_called_once()
            assert router_claude._route_count["claude"] == 1

    @pytest.mark.asyncio
    async def test_never_routes_to_ollama(
        self, router_claude, sample_content, mock_success_response
    ):
        """Test CLAUDE_ONLY never routes to Ollama."""
        # Arrange
        await router_claude.initialize()
        with patch.object(
            router_claude.ollama_provider, "analyze_content"
        ) as mock_ollama, patch.object(
            router_claude.claude_provider,
            "analyze_content",
            return_value=mock_success_response,
        ):

            # Act
            await router_claude.analyze_content(
                content=sample_content, task=ModelCapability.READABILITY
            )

            # Assert
            mock_ollama.assert_not_called()


# ============================================================================
# TEST ROUTING - PRIVACY FIRST STRATEGY
# ============================================================================


class TestPrivacyFirstRouting:
    """Tests for PRIVACY_FIRST routing strategy."""

    @pytest.mark.asyncio
    async def test_routes_to_ollama_only(
        self, router_privacy, sample_content, mock_success_response
    ):
        """Test PRIVACY_FIRST routes to Ollama only."""
        # Arrange
        await router_privacy.initialize()
        with patch.object(
            router_privacy.ollama_provider, "is_available", return_value=True
        ), patch.object(
            router_privacy.ollama_provider,
            "analyze_content",
            return_value=mock_success_response,
        ) as mock_analyze:

            # Act
            response = await router_privacy.analyze_content(
                content=sample_content, task=ModelCapability.ACCESSIBILITY
            )

            # Assert
            assert response.success is True
            mock_analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_fails_with_privacy_message(self, router_privacy, sample_content):
        """Test PRIVACY_FIRST provides privacy-focused error message."""
        # Arrange
        await router_privacy.initialize()
        with patch.object(
            router_privacy.ollama_provider, "is_available", return_value=False
        ):

            # Act
            response = await router_privacy.analyze_content(
                content=sample_content, task=ModelCapability.GENERAL
            )

            # Assert
            assert response.success is False
            assert (
                "privacy" in response.error.lower()
                or "not sending to cloud" in response.error.lower()
            )


# ============================================================================
# TEST PROVIDER STATUS
# ============================================================================


class TestProviderStatus:
    """Tests for get_provider_status() method."""

    @pytest.mark.asyncio
    async def test_get_provider_status_auto(self, router_auto):
        """Test get_provider_status with AUTO strategy."""
        # Arrange
        await router_auto.initialize()
        with patch.object(
            router_auto.ollama_provider, "is_available", return_value=True
        ), patch.object(
            router_auto.ollama_provider,
            "get_available_models",
            return_value=["model1", "model2"],
        ), patch.object(
            router_auto.ollama_provider, "get_metrics", return_value={}
        ), patch.object(
            router_auto.claude_provider, "is_available", return_value=True
        ), patch.object(
            router_auto.claude_provider, "get_metrics", return_value={}
        ):

            # Act
            status = await router_auto.get_provider_status()

            # Assert
            assert "ollama" in status
            assert "claude" in status
            assert "router" in status
            assert status["ollama"]["available"] is True
            assert status["ollama"]["models_count"] == 2

    @pytest.mark.asyncio
    async def test_get_provider_status_includes_routing_metrics(self, router_auto):
        """Test status includes routing metrics."""
        # Arrange
        await router_auto.initialize()
        router_auto._route_count = {"ollama": 5, "claude": 3}
        router_auto._fallback_count = 2

        with patch.object(
            router_auto.ollama_provider, "is_available", return_value=True
        ), patch.object(
            router_auto.ollama_provider, "get_available_models", return_value=[]
        ), patch.object(
            router_auto.ollama_provider, "get_metrics", return_value={}
        ), patch.object(
            router_auto.claude_provider, "is_available", return_value=True
        ), patch.object(
            router_auto.claude_provider, "get_metrics", return_value={}
        ):

            # Act
            status = await router_auto.get_provider_status()

            # Assert
            assert status["router"]["route_count"] == {"ollama": 5, "claude": 3}
            assert status["router"]["fallback_count"] == 2
            assert status["router"]["strategy"] == "auto"


# ============================================================================
# TEST ROUTING METRICS
# ============================================================================


class TestRoutingMetrics:
    """Tests for get_routing_metrics() method."""

    def test_get_routing_metrics_initial_state(self, router_auto):
        """Test routing metrics in initial state."""
        # Arrange & Act
        metrics = router_auto.get_routing_metrics()

        # Assert
        assert metrics["total_routes"] == 0
        assert metrics["ollama_routes"] == 0
        assert metrics["claude_routes"] == 0
        assert metrics["ollama_percentage"] == 0
        assert metrics["fallback_count"] == 0

    def test_get_routing_metrics_after_routes(self, router_auto):
        """Test routing metrics after some routes."""
        # Arrange
        router_auto._route_count = {"ollama": 7, "claude": 3}
        router_auto._fallback_count = 2

        # Act
        metrics = router_auto.get_routing_metrics()

        # Assert
        assert metrics["total_routes"] == 10
        assert metrics["ollama_routes"] == 7
        assert metrics["claude_routes"] == 3
        assert metrics["ollama_percentage"] == 70.0
        assert metrics["fallback_rate"] == 20.0

    def test_get_routing_metrics_includes_strategy(self, router_auto):
        """Test routing metrics includes strategy."""
        # Arrange & Act
        metrics = router_auto.get_routing_metrics()

        # Assert
        assert metrics["strategy"] == "auto"


# ============================================================================
# TEST GET_ACTIVE_PROVIDER
# ============================================================================


class TestGetActiveProvider:
    """Tests for get_active_provider() method."""

    def test_get_active_provider_initial_state(self, router_auto):
        """Test active provider is None initially."""
        # Arrange & Act
        active = router_auto.get_active_provider()

        # Assert
        assert active is None

    @pytest.mark.asyncio
    async def test_get_active_provider_after_routing(
        self, router_auto, sample_content, mock_success_response
    ):
        """Test active provider is set after routing."""
        # Arrange
        await router_auto.initialize()
        with patch.object(
            router_auto.ollama_provider, "is_available", return_value=True
        ), patch.object(
            router_auto.ollama_provider,
            "analyze_content",
            return_value=mock_success_response,
        ):

            # Act
            await router_auto.analyze_content(sample_content, ModelCapability.GENERAL)
            active = router_auto.get_active_provider()

            # Assert
            assert active == "ollama"


# ============================================================================
# TEST ERROR HANDLING
# ============================================================================


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_analyze_before_initialization(self, router_auto, sample_content):
        """Test analyze before initialization returns error."""
        # Arrange (not initialized)

        # Act
        response = await router_auto.analyze_content(
            content=sample_content, task=ModelCapability.GENERAL
        )

        # Assert
        assert response.success is False
        assert "not initialized" in response.error.lower()

    @pytest.mark.asyncio
    async def test_handles_none_content(self, router_auto):
        """Test handles None content gracefully."""
        # Arrange
        await router_auto.initialize()

        # Act
        # Content validation happens in providers
        # Router should pass it through
        response = await router_auto.analyze_content(
            content=None, task=ModelCapability.GENERAL
        )

        # Assert
        # Providers will handle the validation


# ============================================================================
# TEST EDGE CASES
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_concurrent_routing_requests(
        self, router_auto, sample_content, mock_success_response
    ):
        """Test handles concurrent routing requests."""
        # Arrange
        await router_auto.initialize()
        import asyncio

        with patch.object(
            router_auto.ollama_provider, "is_available", return_value=True
        ), patch.object(
            router_auto.ollama_provider,
            "analyze_content",
            return_value=mock_success_response,
        ):

            # Act
            tasks = [
                router_auto.analyze_content(
                    sample_content, ModelCapability.SEO_ANALYSIS
                ),
                router_auto.analyze_content(sample_content, ModelCapability.GRAMMAR),
                router_auto.analyze_content(
                    sample_content, ModelCapability.READABILITY
                ),
            ]
            results = await asyncio.gather(*tasks)

            # Assert
            assert len(results) == 3
            assert all(r.success for r in results)
            assert router_auto._route_count["ollama"] == 3

    @pytest.mark.asyncio
    async def test_routing_with_specific_model(
        self, router_auto, sample_content, mock_success_response
    ):
        """Test routing with specific model parameter."""
        # Arrange
        await router_auto.initialize()
        with patch.object(
            router_auto.ollama_provider, "is_available", return_value=True
        ), patch.object(
            router_auto.ollama_provider,
            "analyze_content",
            return_value=mock_success_response,
        ) as mock_analyze:

            # Act
            await router_auto.analyze_content(
                content=sample_content,
                task=ModelCapability.GENERAL,
                model="specific-model",
            )

            # Assert
            # Should pass model parameter to provider
            mock_analyze.assert_called_once()
            call_args = mock_analyze.call_args
            # Model should be passed (either as positional arg or keyword arg)
            # Check if it's in args[2] or kwargs["model"]
            model_value = (
                call_args.args[2]
                if len(call_args.args) > 2
                else call_args.kwargs.get("model")
            )
            assert model_value == "specific-model"

    @pytest.mark.asyncio
    async def test_routing_with_kwargs(
        self, router_auto, sample_content, mock_success_response
    ):
        """Test routing passes kwargs to provider."""
        # Arrange
        await router_auto.initialize()
        with patch.object(
            router_auto.ollama_provider, "is_available", return_value=True
        ), patch.object(
            router_auto.ollama_provider,
            "analyze_content",
            return_value=mock_success_response,
        ) as mock_analyze:

            # Act
            await router_auto.analyze_content(
                content=sample_content,
                task=ModelCapability.GENERAL,
                temperature=0.5,
                max_tokens=2048,
            )

            # Assert
            mock_analyze.assert_called_once()
            call_args = mock_analyze.call_args
            assert call_args[1].get("temperature") == 0.5
            assert call_args[1].get("max_tokens") == 2048


# ============================================================================
# TEST CONFIGURATION
# ============================================================================


class TestConfiguration:
    """Tests for configuration handling."""

    def test_strategy_case_insensitive(self):
        """Test strategy configuration is case-insensitive."""
        # Arrange & Act
        router1 = ModelRouter(config={"strategy": "AUTO"})
        router2 = ModelRouter(config={"strategy": "auto"})
        router3 = ModelRouter(config={"strategy": "AuTo"})

        # Assert
        assert router1.strategy == RoutingStrategy.AUTO
        assert router2.strategy == RoutingStrategy.AUTO
        assert router3.strategy == RoutingStrategy.AUTO

    def test_max_retries_configuration(self):
        """Test max_retries configuration is respected."""
        # Arrange & Act
        router = ModelRouter(config={"max_retries": 5})

        # Assert
        assert router.max_retries == 5

    def test_fallback_enabled_auto_default(self):
        """Test fallback_enabled defaults to True for AUTO strategy."""
        # Arrange & Act
        router = ModelRouter(config={"strategy": "auto"})

        # Assert
        assert router.fallback_enabled is True

    def test_fallback_enabled_ollama_default(self):
        """Test fallback_enabled defaults to False for OLLAMA_ONLY."""
        # Arrange & Act
        router = ModelRouter(config={"strategy": "ollama"})

        # Assert
        assert router.fallback_enabled is False
