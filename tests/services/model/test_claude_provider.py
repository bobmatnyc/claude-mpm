"""
Tests for Claude Model Provider
================================

WHY: Ensures Claude provider provides proper interface implementation
and generates expected responses (Phase 1: mock mode).

COVERAGE:
- Provider initialization
- Availability checking
- Model listing
- Content analysis (mock responses)
- Error handling
- Configuration management
"""

import pytest

from claude_mpm.services.core.interfaces.model import ModelCapability
from claude_mpm.services.model.claude_provider import ClaudeProvider


@pytest.fixture
def claude_config():
    """Claude provider configuration."""
    return {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4096,
        "temperature": 0.7,
    }


@pytest.fixture
def claude_provider(claude_config):
    """Create Claude provider instance."""
    return ClaudeProvider(config=claude_config)


# Initialization Tests


@pytest.mark.asyncio
async def test_claude_provider_init(claude_provider):
    """Test provider initialization."""
    assert claude_provider.provider_name == "claude"
    assert claude_provider.default_model == "claude-3-5-sonnet-20241022"
    assert claude_provider.max_tokens == 4096
    assert not claude_provider.is_initialized


@pytest.mark.asyncio
async def test_claude_provider_initialize(claude_provider):
    """Test initialization (Phase 1 mock mode)."""
    result = await claude_provider.initialize()

    assert result is True
    assert claude_provider.is_initialized


# Availability Tests


@pytest.mark.asyncio
async def test_is_available(claude_provider):
    """Test availability check (Phase 1: always True)."""
    result = await claude_provider.is_available()

    assert result is True


# Model Listing Tests


@pytest.mark.asyncio
async def test_get_available_models(claude_provider):
    """Test fetching available models."""
    models = await claude_provider.get_available_models()

    assert len(models) > 0
    assert "claude-3-5-sonnet-20241022" in models
    assert "claude-3-5-haiku-20241022" in models
    assert "claude-3-opus-20240229" in models


# Capability Tests


def test_get_supported_capabilities(claude_provider):
    """Test getting supported capabilities."""
    capabilities = claude_provider.get_supported_capabilities()

    assert ModelCapability.SEO_ANALYSIS in capabilities
    assert ModelCapability.READABILITY in capabilities
    assert ModelCapability.GRAMMAR in capabilities
    assert len(capabilities) == len(ModelCapability)


# Content Analysis Tests (Phase 1 Mock Mode)


@pytest.mark.asyncio
async def test_analyze_content_seo_analysis(claude_provider):
    """Test SEO analysis (Phase 1 mock)."""
    await claude_provider.initialize()

    response = await claude_provider.analyze_content(
        content="Test content for SEO analysis",
        task=ModelCapability.SEO_ANALYSIS,
    )

    assert response.success is True
    assert response.provider == "claude"
    assert response.model == "claude-3-5-sonnet-20241022"
    assert response.task == "seo_analysis"
    assert "SEO" in response.result
    assert "keywords" in response.result.lower()


@pytest.mark.asyncio
async def test_analyze_content_readability(claude_provider):
    """Test readability analysis (Phase 1 mock)."""
    await claude_provider.initialize()

    response = await claude_provider.analyze_content(
        content="Test content for readability check",
        task=ModelCapability.READABILITY,
    )

    assert response.success is True
    assert "Readability" in response.result
    assert "Flesch" in response.result


@pytest.mark.asyncio
async def test_analyze_content_grammar(claude_provider):
    """Test grammar check (Phase 1 mock)."""
    await claude_provider.initialize()

    response = await claude_provider.analyze_content(
        content="Test content for grammar check",
        task=ModelCapability.GRAMMAR,
    )

    assert response.success is True
    assert "Grammar" in response.result


@pytest.mark.asyncio
async def test_analyze_content_summarization(claude_provider):
    """Test summarization (Phase 1 mock)."""
    await claude_provider.initialize()

    response = await claude_provider.analyze_content(
        content="Long content that needs to be summarized",
        task=ModelCapability.SUMMARIZATION,
    )

    assert response.success is True
    assert "Summary" in response.result or "TL;DR" in response.result


@pytest.mark.asyncio
async def test_analyze_content_keyword_extraction(claude_provider):
    """Test keyword extraction (Phase 1 mock)."""
    await claude_provider.initialize()

    response = await claude_provider.analyze_content(
        content="Content with important keywords",
        task=ModelCapability.KEYWORD_EXTRACTION,
    )

    assert response.success is True
    assert "Keyword" in response.result


@pytest.mark.asyncio
async def test_analyze_content_accessibility(claude_provider):
    """Test accessibility analysis (Phase 1 mock)."""
    await claude_provider.initialize()

    response = await claude_provider.analyze_content(
        content="Content to check for accessibility",
        task=ModelCapability.ACCESSIBILITY,
    )

    assert response.success is True
    assert "Accessibility" in response.result


@pytest.mark.asyncio
async def test_analyze_content_sentiment(claude_provider):
    """Test sentiment analysis (Phase 1 mock)."""
    await claude_provider.initialize()

    response = await claude_provider.analyze_content(
        content="Content with positive sentiment",
        task=ModelCapability.SENTIMENT,
    )

    assert response.success is True
    assert "Sentiment" in response.result


@pytest.mark.asyncio
async def test_analyze_content_general(claude_provider):
    """Test general analysis (Phase 1 mock)."""
    await claude_provider.initialize()

    response = await claude_provider.analyze_content(
        content="General content for analysis",
        task=ModelCapability.GENERAL,
    )

    assert response.success is True
    assert "Analysis" in response.result


@pytest.mark.asyncio
async def test_analyze_content_with_custom_model(claude_provider):
    """Test analysis with custom model."""
    await claude_provider.initialize()

    response = await claude_provider.analyze_content(
        content="Test content",
        task=ModelCapability.GENERAL,
        model="claude-3-opus-20240229",
    )

    assert response.success is True
    assert response.model == "claude-3-opus-20240229"


@pytest.mark.asyncio
async def test_analyze_content_invalid_content(claude_provider):
    """Test analysis with invalid content."""
    await claude_provider.initialize()

    response = await claude_provider.analyze_content(
        content="",
        task=ModelCapability.SEO_ANALYSIS,
    )

    assert response.success is False
    assert "Invalid content" in response.error


# Model Info Tests


@pytest.mark.asyncio
async def test_get_model_info_sonnet(claude_provider):
    """Test getting model info for Sonnet."""
    info = await claude_provider.get_model_info("claude-3-5-sonnet-20241022")

    assert info["name"] == "Claude 3.5 Sonnet"
    assert info["context_window"] == 200000
    assert "analysis" in info["capabilities"]


@pytest.mark.asyncio
async def test_get_model_info_haiku(claude_provider):
    """Test getting model info for Haiku."""
    info = await claude_provider.get_model_info("claude-3-5-haiku-20241022")

    assert info["name"] == "Claude 3.5 Haiku"
    assert info["speed"] == "fastest"


@pytest.mark.asyncio
async def test_get_model_info_unknown(claude_provider):
    """Test getting model info for unknown model."""
    info = await claude_provider.get_model_info("unknown-model")

    assert "error" in info


# Shutdown Tests


@pytest.mark.asyncio
async def test_shutdown(claude_provider):
    """Test provider shutdown."""
    await claude_provider.shutdown()

    assert claude_provider.is_shutdown


# Metrics Tests


def test_get_metrics(claude_provider):
    """Test getting provider metrics."""
    claude_provider._request_count = 5
    claude_provider._error_count = 1
    claude_provider._total_latency = 2.5

    metrics = claude_provider.get_metrics()

    assert metrics["provider"] == "claude"
    assert metrics["request_count"] == 5
    assert metrics["error_count"] == 1
    assert metrics["error_rate"] == 0.2
    assert metrics["avg_latency_seconds"] == 0.5
