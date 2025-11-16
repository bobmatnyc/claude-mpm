"""Comprehensive unit tests for ClaudeProvider.

This test suite provides complete coverage of the ClaudeProvider class,
testing all methods, edge cases, error handling, and configuration scenarios.

Coverage targets:
- Line coverage: >90%
- Branch coverage: >85%
- All error paths tested
- All configuration options covered
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from claude_mpm.services.core.interfaces.model import ModelCapability, ModelResponse
from claude_mpm.services.model.claude_provider import ClaudeProvider

# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def default_config():
    """Default configuration for ClaudeProvider."""
    return {
        "api_key": "test-api-key",
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4096,
    }


@pytest.fixture
def minimal_config():
    """Minimal configuration for ClaudeProvider."""
    return {}


@pytest.fixture
def custom_config():
    """Custom configuration for testing overrides."""
    return {
        "api_key": "custom-key",
        "model": "claude-3-opus-20240229",
        "max_tokens": 8192,
    }


@pytest.fixture
def provider(default_config):
    """Create ClaudeProvider instance with default config."""
    return ClaudeProvider(config=default_config)


@pytest.fixture
def provider_minimal():
    """Create ClaudeProvider instance with minimal config."""
    return ClaudeProvider(config={})


@pytest.fixture
def sample_content():
    """Sample content for testing analysis."""
    return """
    This is sample content for testing the Claude provider.
    It contains multiple sentences and provides enough text
    for meaningful analysis across different capabilities.
    """


# ============================================================================
# TEST INITIALIZATION
# ============================================================================


class TestInitialization:
    """Tests for ClaudeProvider initialization and configuration."""

    def test_init_with_default_config(self, default_config):
        """Test initialization with complete configuration."""
        # Arrange & Act
        provider = ClaudeProvider(config=default_config)

        # Assert
        assert provider.api_key == "test-api-key"
        assert provider.default_model == "claude-3-5-sonnet-20241022"
        assert provider.max_tokens == 4096
        assert provider._client is None  # Not initialized yet

    def test_init_with_minimal_config(self):
        """Test initialization with minimal/empty configuration."""
        # Arrange & Act
        provider = ClaudeProvider(config={})

        # Assert
        assert provider.api_key is None
        assert provider.default_model == "claude-3-5-sonnet-20241022"  # Default
        assert provider.max_tokens == 4096  # Default
        assert provider._client is None

    def test_init_with_custom_config(self, custom_config):
        """Test initialization with custom configuration."""
        # Arrange & Act
        provider = ClaudeProvider(config=custom_config)

        # Assert
        assert provider.api_key == "custom-key"
        assert provider.default_model == "claude-3-opus-20240229"
        assert provider.max_tokens == 8192

    def test_init_sets_provider_name(self, provider):
        """Test initialization sets correct provider name."""
        # Arrange & Act (provider from fixture)

        # Assert
        assert hasattr(provider, "provider_name")
        # The provider name is set in BaseModelProvider.__init__

    def test_init_with_none_config(self):
        """Test initialization handles None config."""
        # Arrange & Act
        provider = ClaudeProvider(config=None)

        # Assert
        assert provider.api_key is None
        assert provider.default_model == "claude-3-5-sonnet-20241022"
        assert provider._client is None

    def test_available_models_constant(self):
        """Test AVAILABLE_MODELS constant is defined correctly."""
        # Arrange & Act
        models = ClaudeProvider.AVAILABLE_MODELS

        # Assert
        assert isinstance(models, list)
        assert len(models) > 0
        assert "claude-3-5-sonnet-20241022" in models
        assert "claude-3-5-haiku-20241022" in models
        assert "claude-3-opus-20240229" in models


# ============================================================================
# TEST INITIALIZE METHOD
# ============================================================================


class TestInitializeMethod:
    """Tests for the initialize() async method."""

    @pytest.mark.asyncio
    async def test_initialize_success(self, provider):
        """Test successful initialization."""
        # Arrange (provider from fixture)

        # Act
        result = await provider.initialize()

        # Assert
        assert result is True
        assert provider._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_without_api_key(self, provider_minimal):
        """Test initialization succeeds in Phase 1 mock mode without API key."""
        # Arrange (provider with no API key)

        # Act
        result = await provider_minimal.initialize()

        # Assert
        # Phase 1: Should succeed (mock mode)
        assert result is True
        assert provider_minimal._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_logs_info(self, provider):
        """Test initialization logs appropriate messages."""
        # Arrange
        with patch.object(provider, "log_info") as mock_log:
            # Act
            await provider.initialize()

            # Assert
            assert mock_log.call_count >= 1
            # Should log initialization message

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, provider):
        """Test calling initialize multiple times is safe."""
        # Arrange & Act
        result1 = await provider.initialize()
        result2 = await provider.initialize()

        # Assert
        assert result1 is True
        assert result2 is True
        assert provider._initialized is True


# ============================================================================
# TEST SHUTDOWN METHOD
# ============================================================================


class TestShutdownMethod:
    """Tests for the shutdown() async method."""

    @pytest.mark.asyncio
    async def test_shutdown_success(self, provider):
        """Test successful shutdown."""
        # Arrange
        await provider.initialize()

        # Act
        await provider.shutdown()

        # Assert
        assert provider._shutdown is True

    @pytest.mark.asyncio
    async def test_shutdown_without_initialization(self, provider):
        """Test shutdown works without prior initialization."""
        # Arrange (provider not initialized)

        # Act
        await provider.shutdown()

        # Assert
        assert provider._shutdown is True

    @pytest.mark.asyncio
    async def test_shutdown_cleans_up_client(self, provider):
        """Test shutdown cleans up client if present."""
        # Arrange
        await provider.initialize()
        provider._client = Mock()  # Simulate client

        # Act
        await provider.shutdown()

        # Assert
        assert provider._shutdown is True
        # Phase 1: Client cleanup not implemented yet

    @pytest.mark.asyncio
    async def test_shutdown_logs_info(self, provider):
        """Test shutdown logs appropriate messages."""
        # Arrange
        with patch.object(provider, "log_info") as mock_log:
            # Act
            await provider.shutdown()

            # Assert
            mock_log.assert_called_once()


# ============================================================================
# TEST IS_AVAILABLE METHOD
# ============================================================================


class TestIsAvailableMethod:
    """Tests for the is_available() async method."""

    @pytest.mark.asyncio
    async def test_is_available_returns_true_in_phase1(self, provider):
        """Test is_available returns True in Phase 1 mock mode."""
        # Arrange & Act
        result = await provider.is_available()

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_is_available_without_api_key(self, provider_minimal):
        """Test is_available returns True even without API key in Phase 1."""
        # Arrange & Act
        result = await provider_minimal.is_available()

        # Assert
        # Phase 1: Returns True for testing
        assert result is True

    @pytest.mark.asyncio
    async def test_is_available_after_shutdown(self, provider):
        """Test is_available after shutdown."""
        # Arrange
        await provider.shutdown()

        # Act
        result = await provider.is_available()

        # Assert
        # Phase 1: Still returns True
        assert result is True


# ============================================================================
# TEST GET_AVAILABLE_MODELS METHOD
# ============================================================================


class TestGetAvailableModels:
    """Tests for the get_available_models() async method."""

    @pytest.mark.asyncio
    async def test_returns_available_models_list(self, provider):
        """Test returns list of available models."""
        # Arrange & Act
        models = await provider.get_available_models()

        # Assert
        assert isinstance(models, list)
        assert len(models) > 0
        assert "claude-3-5-sonnet-20241022" in models

    @pytest.mark.asyncio
    async def test_returns_same_as_constant(self, provider):
        """Test returns same models as AVAILABLE_MODELS constant."""
        # Arrange & Act
        models = await provider.get_available_models()

        # Assert
        assert models == ClaudeProvider.AVAILABLE_MODELS

    @pytest.mark.asyncio
    async def test_returns_models_without_initialization(self, provider):
        """Test can get available models without initialization."""
        # Arrange (not initialized)

        # Act
        models = await provider.get_available_models()

        # Assert
        assert isinstance(models, list)
        assert len(models) > 0


# ============================================================================
# TEST GET_SUPPORTED_CAPABILITIES METHOD
# ============================================================================


class TestGetSupportedCapabilities:
    """Tests for the get_supported_capabilities() method."""

    def test_returns_all_capabilities(self, provider):
        """Test returns all ModelCapability values."""
        # Arrange & Act
        capabilities = provider.get_supported_capabilities()

        # Assert
        assert isinstance(capabilities, list)
        assert len(capabilities) == len(ModelCapability)
        assert ModelCapability.SEO_ANALYSIS in capabilities
        assert ModelCapability.READABILITY in capabilities
        assert ModelCapability.GRAMMAR in capabilities
        assert ModelCapability.SUMMARIZATION in capabilities

    def test_returns_list_of_capabilities(self, provider):
        """Test returns list type."""
        # Arrange & Act
        capabilities = provider.get_supported_capabilities()

        # Assert
        assert isinstance(capabilities, list)
        for cap in capabilities:
            assert isinstance(cap, ModelCapability)

    def test_capabilities_includes_all_types(self, provider):
        """Test all capability types are included."""
        # Arrange
        all_caps = set(ModelCapability)

        # Act
        supported = set(provider.get_supported_capabilities())

        # Assert
        assert supported == all_caps


# ============================================================================
# TEST ANALYZE_CONTENT METHOD
# ============================================================================


class TestAnalyzeContent:
    """Tests for the analyze_content() async method."""

    @pytest.mark.asyncio
    async def test_analyze_content_success(self, provider, sample_content):
        """Test successful content analysis."""
        # Arrange
        await provider.initialize()

        # Act
        response = await provider.analyze_content(
            content=sample_content, task=ModelCapability.SEO_ANALYSIS
        )

        # Assert
        assert isinstance(response, ModelResponse)
        assert response.success is True
        assert response.task == ModelCapability.SEO_ANALYSIS.value
        assert response.result is not None
        assert len(response.result) > 0

    @pytest.mark.asyncio
    async def test_analyze_content_with_specific_model(self, provider, sample_content):
        """Test analysis with specific model selection."""
        # Arrange
        await provider.initialize()
        specific_model = "claude-3-opus-20240229"

        # Act
        response = await provider.analyze_content(
            content=sample_content, task=ModelCapability.GRAMMAR, model=specific_model
        )

        # Assert
        assert response.success is True
        assert response.model == specific_model

    @pytest.mark.asyncio
    async def test_analyze_content_uses_default_model(self, provider, sample_content):
        """Test analysis uses default model when not specified."""
        # Arrange
        await provider.initialize()

        # Act
        response = await provider.analyze_content(
            content=sample_content, task=ModelCapability.READABILITY
        )

        # Assert
        assert response.success is True
        assert response.model == provider.default_model

    @pytest.mark.asyncio
    async def test_analyze_content_all_capabilities(self, provider, sample_content):
        """Test analysis works for all capability types."""
        # Arrange
        await provider.initialize()
        capabilities = [
            ModelCapability.SEO_ANALYSIS,
            ModelCapability.READABILITY,
            ModelCapability.GRAMMAR,
            ModelCapability.SUMMARIZATION,
            ModelCapability.KEYWORD_EXTRACTION,
            ModelCapability.ACCESSIBILITY,
            ModelCapability.SENTIMENT,
            ModelCapability.GENERAL,
        ]

        # Act & Assert
        for capability in capabilities:
            response = await provider.analyze_content(
                content=sample_content, task=capability
            )
            assert response.success is True
            assert response.task == capability.value

    @pytest.mark.asyncio
    async def test_analyze_content_invalid_content(self, provider):
        """Test analysis rejects invalid content."""
        # Arrange
        await provider.initialize()

        # Act
        response = await provider.analyze_content(
            content="", task=ModelCapability.SEO_ANALYSIS  # Empty content
        )

        # Assert
        assert response.success is False
        assert response.error is not None

    @pytest.mark.asyncio
    async def test_analyze_content_very_long_content(self, provider):
        """Test analysis handles very long content."""
        # Arrange
        await provider.initialize()
        long_content = "word " * 10000  # Very long content

        # Act
        response = await provider.analyze_content(
            content=long_content, task=ModelCapability.SUMMARIZATION
        )

        # Assert
        # Phase 1: Should succeed with mock
        assert response.success is True

    @pytest.mark.asyncio
    async def test_analyze_content_without_initialization(
        self, provider, sample_content
    ):
        """Test analysis auto-initializes if not initialized."""
        # Arrange (not initialized)

        # Act
        response = await provider.analyze_content(
            content=sample_content, task=ModelCapability.GENERAL
        )

        # Assert
        assert response.success is True
        assert provider._initialized is True

    @pytest.mark.asyncio
    async def test_analyze_content_with_kwargs(self, provider, sample_content):
        """Test analysis accepts additional kwargs."""
        # Arrange
        await provider.initialize()

        # Act
        response = await provider.analyze_content(
            content=sample_content,
            task=ModelCapability.SEO_ANALYSIS,
            temperature=0.5,
            max_tokens=2048,
        )

        # Assert
        assert response.success is True

    @pytest.mark.asyncio
    async def test_analyze_content_returns_metadata(self, provider, sample_content):
        """Test analysis response includes metadata."""
        # Arrange
        await provider.initialize()

        # Act
        response = await provider.analyze_content(
            content=sample_content, task=ModelCapability.SENTIMENT
        )

        # Assert
        assert response.metadata is not None
        assert isinstance(response.metadata, dict)
        assert "phase" in response.metadata


# ============================================================================
# TEST MOCK ANALYSIS GENERATION
# ============================================================================


class TestMockAnalysisGeneration:
    """Tests for _generate_mock_analysis() method."""

    def test_generates_seo_analysis(self, provider):
        """Test generates mock SEO analysis."""
        # Arrange & Act
        result = provider._generate_mock_analysis(ModelCapability.SEO_ANALYSIS)

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0
        assert "SEO" in result
        assert "keyword" in result.lower()

    def test_generates_readability_analysis(self, provider):
        """Test generates mock readability analysis."""
        # Arrange & Act
        result = provider._generate_mock_analysis(ModelCapability.READABILITY)

        # Assert
        assert isinstance(result, str)
        assert "Readability" in result
        assert "Flesch" in result

    def test_generates_grammar_check(self, provider):
        """Test generates mock grammar check."""
        # Arrange & Act
        result = provider._generate_mock_analysis(ModelCapability.GRAMMAR)

        # Assert
        assert isinstance(result, str)
        assert "Grammar" in result

    def test_generates_summary(self, provider):
        """Test generates mock summary."""
        # Arrange & Act
        result = provider._generate_mock_analysis(ModelCapability.SUMMARIZATION)

        # Assert
        assert isinstance(result, str)
        assert "Summary" in result or "Main Points" in result

    def test_generates_keyword_extraction(self, provider):
        """Test generates mock keyword extraction."""
        # Arrange & Act
        result = provider._generate_mock_analysis(ModelCapability.KEYWORD_EXTRACTION)

        # Assert
        assert isinstance(result, str)
        assert "Keyword" in result

    def test_generates_accessibility_analysis(self, provider):
        """Test generates mock accessibility analysis."""
        # Arrange & Act
        result = provider._generate_mock_analysis(ModelCapability.ACCESSIBILITY)

        # Assert
        assert isinstance(result, str)
        assert "Accessibility" in result

    def test_generates_sentiment_analysis(self, provider):
        """Test generates mock sentiment analysis."""
        # Arrange & Act
        result = provider._generate_mock_analysis(ModelCapability.SENTIMENT)

        # Assert
        assert isinstance(result, str)
        assert "Sentiment" in result

    def test_generates_general_analysis(self, provider):
        """Test generates mock general analysis."""
        # Arrange & Act
        result = provider._generate_mock_analysis(ModelCapability.GENERAL)

        # Assert
        assert isinstance(result, str)
        assert "Analysis" in result


# ============================================================================
# TEST GET_MODEL_INFO METHOD
# ============================================================================


class TestGetModelInfo:
    """Tests for the get_model_info() async method."""

    @pytest.mark.asyncio
    async def test_get_model_info_for_sonnet(self, provider):
        """Test retrieves info for Claude 3.5 Sonnet."""
        # Arrange & Act
        info = await provider.get_model_info("claude-3-5-sonnet-20241022")

        # Assert
        assert isinstance(info, dict)
        assert info["name"] == "Claude 3.5 Sonnet"
        assert info["context_window"] == 200000
        assert "capabilities" in info

    @pytest.mark.asyncio
    async def test_get_model_info_for_haiku(self, provider):
        """Test retrieves info for Claude 3.5 Haiku."""
        # Arrange & Act
        info = await provider.get_model_info("claude-3-5-haiku-20241022")

        # Assert
        assert isinstance(info, dict)
        assert info["name"] == "Claude 3.5 Haiku"
        assert info["speed"] == "fastest"

    @pytest.mark.asyncio
    async def test_get_model_info_for_opus(self, provider):
        """Test retrieves info for Claude 3 Opus."""
        # Arrange & Act
        info = await provider.get_model_info("claude-3-opus-20240229")

        # Assert
        assert isinstance(info, dict)
        assert info["name"] == "Claude 3 Opus"
        assert info["cost"] == "high"

    @pytest.mark.asyncio
    async def test_get_model_info_for_unknown_model(self, provider):
        """Test handles unknown model gracefully."""
        # Arrange & Act
        info = await provider.get_model_info("unknown-model")

        # Assert
        assert isinstance(info, dict)
        assert "error" in info
        assert info["name"] == "unknown-model"

    @pytest.mark.asyncio
    async def test_get_model_info_includes_version(self, provider):
        """Test model info includes version information."""
        # Arrange & Act
        info = await provider.get_model_info("claude-3-5-sonnet-20241022")

        # Assert
        assert "version" in info
        assert info["version"] == "20241022"


# ============================================================================
# TEST EDGE CASES
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_handles_special_characters_in_content(self, provider):
        """Test handles special characters in content."""
        # Arrange
        await provider.initialize()
        special_content = "Test content with 🔐 emojis and 日本語 characters"

        # Act
        response = await provider.analyze_content(
            content=special_content, task=ModelCapability.GENERAL
        )

        # Assert
        assert response.success is True

    @pytest.mark.asyncio
    async def test_handles_multiline_content(self, provider):
        """Test handles multiline content."""
        # Arrange
        await provider.initialize()
        multiline = """Line 1
        Line 2
        Line 3
        Line 4"""

        # Act
        response = await provider.analyze_content(
            content=multiline, task=ModelCapability.READABILITY
        )

        # Assert
        assert response.success is True

    @pytest.mark.asyncio
    async def test_handles_whitespace_only_content(self, provider):
        """Test handles whitespace-only content."""
        # Arrange
        await provider.initialize()

        # Act
        response = await provider.analyze_content(
            content="   \n  \t  ", task=ModelCapability.GENERAL
        )

        # Assert
        # Should fail validation
        assert response.success is False

    @pytest.mark.asyncio
    async def test_handles_very_short_content(self, provider):
        """Test handles very short content."""
        # Arrange
        await provider.initialize()

        # Act
        response = await provider.analyze_content(
            content="Hi", task=ModelCapability.SENTIMENT
        )

        # Assert
        assert response.success is True

    @pytest.mark.asyncio
    async def test_concurrent_analyses(self, provider, sample_content):
        """Test handles concurrent analysis requests."""
        # Arrange
        await provider.initialize()
        import asyncio

        # Act
        tasks = [
            provider.analyze_content(sample_content, ModelCapability.SEO_ANALYSIS),
            provider.analyze_content(sample_content, ModelCapability.GRAMMAR),
            provider.analyze_content(sample_content, ModelCapability.READABILITY),
        ]
        results = await asyncio.gather(*tasks)

        # Assert
        assert len(results) == 3
        assert all(r.success for r in results)


# ============================================================================
# TEST ERROR HANDLING
# ============================================================================


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_handles_none_content(self, provider):
        """Test handles None content gracefully."""
        # Arrange
        await provider.initialize()

        # Act
        response = await provider.analyze_content(
            content=None, task=ModelCapability.GENERAL
        )

        # Assert
        assert response.success is False
        assert response.error is not None

    @pytest.mark.asyncio
    async def test_handles_initialization_failure(self):
        """Test handles initialization failure gracefully."""
        # Arrange
        provider = ClaudeProvider()

        # Mock initialization to fail
        with patch.object(provider, "log_error"):
            # Phase 1: Initialize always succeeds
            # This test is for future Phase 2 implementation
            pass

    @pytest.mark.asyncio
    async def test_analyze_before_successful_init(self, sample_content):
        """Test analyze auto-initializes if needed."""
        # Arrange
        provider = ClaudeProvider()
        provider._initialized = False

        # Act
        response = await provider.analyze_content(
            content=sample_content, task=ModelCapability.GENERAL
        )

        # Assert
        # Should auto-initialize and succeed
        assert response.success is True


# ============================================================================
# TEST CONFIGURATION
# ============================================================================


class TestConfiguration:
    """Tests for configuration handling."""

    def test_get_config_returns_value(self, provider):
        """Test get_config returns configured values."""
        # Arrange & Act
        api_key = provider.get_config("api_key")
        model = provider.get_config("model")

        # Assert
        assert api_key == "test-api-key"
        assert model == "claude-3-5-sonnet-20241022"

    def test_get_config_returns_default(self, provider_minimal):
        """Test get_config returns default for missing keys."""
        # Arrange & Act
        value = provider_minimal.get_config("missing_key", "default_value")

        # Assert
        assert value == "default_value"

    def test_config_isolation(self):
        """Test configuration is isolated between instances."""
        # Arrange
        provider1 = ClaudeProvider(config={"api_key": "key1"})
        provider2 = ClaudeProvider(config={"api_key": "key2"})

        # Act & Assert
        assert provider1.api_key == "key1"
        assert provider2.api_key == "key2"
        assert provider1.api_key != provider2.api_key
