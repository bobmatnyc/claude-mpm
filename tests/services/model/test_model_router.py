"""
Tests for Model Router
======================

WHY: Ensures model router correctly handles provider selection, fallback
logic, and routing strategies.

COVERAGE:
- Router initialization
- Auto routing (Ollama → Claude fallback)
- OLLAMA_ONLY strategy
- CLAUDE_ONLY strategy
- PRIVACY_FIRST strategy
- Fallback logic
- Provider status tracking
- Routing metrics
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.services.core.interfaces.model import ModelCapability, ModelResponse
from claude_mpm.services.model.model_router import ModelRouter, RoutingStrategy


@pytest.fixture
def router_config_auto():
    """Auto routing configuration."""
    return {
        "strategy": "auto",
        "fallback_enabled": True,
    }


@pytest.fixture
def router_config_ollama_only():
    """Ollama-only configuration."""
    return {
        "strategy": "ollama",
        "fallback_enabled": False,
    }


@pytest.fixture
def router_config_claude_only():
    """Claude-only configuration."""
    return {
        "strategy": "claude",
    }


@pytest.fixture
def mock_ollama_provider():
    """Mock Ollama provider."""
    provider = AsyncMock()
    provider.is_initialized = True
    provider.is_available = AsyncMock(return_value=True)
    provider.initialize = AsyncMock(return_value=True)
    provider.shutdown = AsyncMock()
    provider.get_metrics = MagicMock(
        return_value={
            "provider": "ollama",
            "request_count": 0,
            "error_count": 0,
        }
    )
    provider.get_available_models = AsyncMock(return_value=["llama3.3:70b"])
    return provider


@pytest.fixture
def mock_claude_provider():
    """Mock Claude provider."""
    provider = AsyncMock()
    provider.is_initialized = True
    provider.is_available = AsyncMock(return_value=True)
    provider.initialize = AsyncMock(return_value=True)
    provider.shutdown = AsyncMock()
    provider.get_metrics = MagicMock(
        return_value={
            "provider": "claude",
            "request_count": 0,
            "error_count": 0,
        }
    )
    return provider


# Initialization Tests


@pytest.mark.asyncio
async def test_router_init_auto(router_config_auto):
    """Test router initialization with AUTO strategy."""
    router = ModelRouter(config=router_config_auto)

    assert router.strategy == RoutingStrategy.AUTO
    assert router.fallback_enabled is True


@pytest.mark.asyncio
async def test_router_init_ollama_only(router_config_ollama_only):
    """Test router initialization with OLLAMA_ONLY strategy."""
    router = ModelRouter(config=router_config_ollama_only)

    assert router.strategy == RoutingStrategy.OLLAMA_ONLY
    assert router.fallback_enabled is False


@pytest.mark.asyncio
async def test_router_init_claude_only(router_config_claude_only):
    """Test router initialization with CLAUDE_ONLY strategy."""
    router = ModelRouter(config=router_config_claude_only)

    assert router.strategy == RoutingStrategy.CLAUDE_ONLY


@pytest.mark.asyncio
async def test_router_init_invalid_strategy():
    """Test router with invalid strategy defaults to AUTO."""
    router = ModelRouter(config={"strategy": "invalid"})

    assert router.strategy == RoutingStrategy.AUTO


@pytest.mark.asyncio
async def test_router_initialize_success(
    router_config_auto, mock_ollama_provider, mock_claude_provider
):
    """Test successful router initialization."""
    router = ModelRouter(config=router_config_auto)

    with patch.object(router, "ollama_provider", mock_ollama_provider), patch.object(
        router, "claude_provider", mock_claude_provider
    ):
        result = await router.initialize()

        assert result is True
        assert router.is_initialized
        mock_ollama_provider.initialize.assert_called_once()
        mock_claude_provider.initialize.assert_called_once()


# Auto Routing Tests


@pytest.mark.asyncio
async def test_auto_route_ollama_success(
    router_config_auto, mock_ollama_provider, mock_claude_provider
):
    """Test AUTO routing uses Ollama when available."""
    router = ModelRouter(config=router_config_auto)
    router._initialized = True

    # Mock successful Ollama response
    mock_response = ModelResponse(
        success=True,
        provider="ollama",
        model="llama3.3:70b",
        task="seo_analysis",
        result="Analysis complete",
    )
    mock_ollama_provider.analyze_content = AsyncMock(return_value=mock_response)

    with patch.object(router, "ollama_provider", mock_ollama_provider), patch.object(
        router, "claude_provider", mock_claude_provider
    ):
        response = await router.analyze_content(
            content="Test content",
            task=ModelCapability.SEO_ANALYSIS,
        )

        assert response.success is True
        assert response.provider == "ollama"
        mock_ollama_provider.analyze_content.assert_called_once()
        mock_claude_provider.analyze_content.assert_not_called()


@pytest.mark.asyncio
async def test_auto_route_fallback_to_claude(
    router_config_auto, mock_ollama_provider, mock_claude_provider
):
    """Test AUTO routing falls back to Claude on Ollama failure."""
    router = ModelRouter(config=router_config_auto)
    router._initialized = True

    # Mock Ollama failure
    mock_ollama_response = ModelResponse(
        success=False,
        provider="ollama",
        model="llama3.3:70b",
        task="seo_analysis",
        result="",
        error="Ollama error",
    )
    mock_ollama_provider.analyze_content = AsyncMock(return_value=mock_ollama_response)

    # Mock Claude success
    mock_claude_response = ModelResponse(
        success=True,
        provider="claude",
        model="claude-3-5-sonnet-20241022",
        task="seo_analysis",
        result="Analysis complete",
    )
    mock_claude_provider.analyze_content = AsyncMock(return_value=mock_claude_response)

    with patch.object(router, "ollama_provider", mock_ollama_provider), patch.object(
        router, "claude_provider", mock_claude_provider
    ):
        response = await router.analyze_content(
            content="Test content",
            task=ModelCapability.SEO_ANALYSIS,
        )

        assert response.success is True
        assert response.provider == "claude"
        assert router._fallback_count == 1


@pytest.mark.asyncio
async def test_auto_route_ollama_unavailable(
    router_config_auto, mock_ollama_provider, mock_claude_provider
):
    """Test AUTO routing uses Claude when Ollama unavailable."""
    router = ModelRouter(config=router_config_auto)
    router._initialized = True

    # Mock Ollama unavailable
    mock_ollama_provider.is_available = AsyncMock(return_value=False)

    # Mock Claude success
    mock_claude_response = ModelResponse(
        success=True,
        provider="claude",
        model="claude-3-5-sonnet-20241022",
        task="seo_analysis",
        result="Analysis complete",
    )
    mock_claude_provider.analyze_content = AsyncMock(return_value=mock_claude_response)

    with patch.object(router, "ollama_provider", mock_ollama_provider), patch.object(
        router, "claude_provider", mock_claude_provider
    ):
        response = await router.analyze_content(
            content="Test content",
            task=ModelCapability.SEO_ANALYSIS,
        )

        assert response.success is True
        assert response.provider == "claude"


# OLLAMA_ONLY Strategy Tests


@pytest.mark.asyncio
async def test_ollama_only_success(
    router_config_ollama_only, mock_ollama_provider, mock_claude_provider
):
    """Test OLLAMA_ONLY strategy with successful Ollama."""
    router = ModelRouter(config=router_config_ollama_only)
    router._initialized = True

    mock_response = ModelResponse(
        success=True,
        provider="ollama",
        model="llama3.3:70b",
        task="seo_analysis",
        result="Analysis complete",
    )
    mock_ollama_provider.analyze_content = AsyncMock(return_value=mock_response)

    with patch.object(router, "ollama_provider", mock_ollama_provider), patch.object(
        router, "claude_provider", mock_claude_provider
    ):
        response = await router.analyze_content(
            content="Test content",
            task=ModelCapability.SEO_ANALYSIS,
        )

        assert response.success is True
        assert response.provider == "ollama"
        mock_claude_provider.analyze_content.assert_not_called()


@pytest.mark.asyncio
async def test_ollama_only_unavailable(
    router_config_ollama_only, mock_ollama_provider, mock_claude_provider
):
    """Test OLLAMA_ONLY strategy fails when Ollama unavailable."""
    router = ModelRouter(config=router_config_ollama_only)
    router._initialized = True

    mock_ollama_provider.is_available = AsyncMock(return_value=False)

    with patch.object(router, "ollama_provider", mock_ollama_provider), patch.object(
        router, "claude_provider", mock_claude_provider
    ):
        response = await router.analyze_content(
            content="Test content",
            task=ModelCapability.SEO_ANALYSIS,
        )

        assert response.success is False
        assert "not available" in response.error


# CLAUDE_ONLY Strategy Tests


@pytest.mark.asyncio
async def test_claude_only(
    router_config_claude_only, mock_ollama_provider, mock_claude_provider
):
    """Test CLAUDE_ONLY strategy always uses Claude."""
    router = ModelRouter(config=router_config_claude_only)
    router._initialized = True

    mock_response = ModelResponse(
        success=True,
        provider="claude",
        model="claude-3-5-sonnet-20241022",
        task="seo_analysis",
        result="Analysis complete",
    )
    mock_claude_provider.analyze_content = AsyncMock(return_value=mock_response)

    with patch.object(router, "ollama_provider", mock_ollama_provider), patch.object(
        router, "claude_provider", mock_claude_provider
    ):
        response = await router.analyze_content(
            content="Test content",
            task=ModelCapability.SEO_ANALYSIS,
        )

        assert response.success is True
        assert response.provider == "claude"
        mock_ollama_provider.analyze_content.assert_not_called()


# PRIVACY_FIRST Strategy Tests


@pytest.mark.asyncio
async def test_privacy_first_unavailable(mock_ollama_provider, mock_claude_provider):
    """Test PRIVACY_FIRST strategy with privacy-focused error message."""
    router = ModelRouter(config={"strategy": "privacy"})
    router._initialized = True

    mock_ollama_provider.is_available = AsyncMock(return_value=False)

    with patch.object(router, "ollama_provider", mock_ollama_provider), patch.object(
        router, "claude_provider", mock_claude_provider
    ):
        response = await router.analyze_content(
            content="Test content",
            task=ModelCapability.SEO_ANALYSIS,
        )

        assert response.success is False
        assert "Privacy mode" in response.error
        mock_claude_provider.analyze_content.assert_not_called()


# Provider Status Tests


@pytest.mark.asyncio
async def test_get_provider_status(
    router_config_auto, mock_ollama_provider, mock_claude_provider
):
    """Test getting provider status."""
    router = ModelRouter(config=router_config_auto)
    router._initialized = True

    with patch.object(router, "ollama_provider", mock_ollama_provider), patch.object(
        router, "claude_provider", mock_claude_provider
    ):
        status = await router.get_provider_status()

        assert "ollama" in status
        assert "claude" in status
        assert "router" in status
        assert status["router"]["strategy"] == "auto"


@pytest.mark.asyncio
async def test_get_active_provider(
    router_config_auto, mock_ollama_provider, mock_claude_provider
):
    """Test getting active provider."""
    router = ModelRouter(config=router_config_auto)
    router._initialized = True

    mock_response = ModelResponse(
        success=True,
        provider="ollama",
        model="llama3.3:70b",
        task="seo_analysis",
        result="Analysis complete",
    )
    mock_ollama_provider.analyze_content = AsyncMock(return_value=mock_response)

    with patch.object(router, "ollama_provider", mock_ollama_provider), patch.object(
        router, "claude_provider", mock_claude_provider
    ):
        await router.analyze_content(
            content="Test content",
            task=ModelCapability.SEO_ANALYSIS,
        )

        assert router.get_active_provider() == "ollama"


# Metrics Tests


def test_get_routing_metrics(router_config_auto):
    """Test getting routing metrics."""
    router = ModelRouter(config=router_config_auto)

    router._route_count = {"ollama": 7, "claude": 3}
    router._fallback_count = 2

    metrics = router.get_routing_metrics()

    assert metrics["total_routes"] == 10
    assert metrics["ollama_routes"] == 7
    assert metrics["claude_routes"] == 3
    assert metrics["ollama_percentage"] == 70.0
    assert metrics["fallback_count"] == 2
    assert metrics["fallback_rate"] == 20.0


# Shutdown Tests


@pytest.mark.asyncio
async def test_router_shutdown(
    router_config_auto, mock_ollama_provider, mock_claude_provider
):
    """Test router shutdown."""
    router = ModelRouter(config=router_config_auto)

    with patch.object(router, "ollama_provider", mock_ollama_provider), patch.object(
        router, "claude_provider", mock_claude_provider
    ):
        await router.shutdown()

        assert router.is_shutdown
        mock_ollama_provider.shutdown.assert_called_once()
        mock_claude_provider.shutdown.assert_called_once()


# Error Handling Tests


@pytest.mark.asyncio
async def test_analyze_not_initialized(router_config_auto):
    """Test analysis when router not initialized."""
    router = ModelRouter(config=router_config_auto)

    response = await router.analyze_content(
        content="Test content",
        task=ModelCapability.SEO_ANALYSIS,
    )

    assert response.success is False
    assert "not initialized" in response.error
