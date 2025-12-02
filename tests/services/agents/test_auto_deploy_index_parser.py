"""Tests for AutoDeployIndexParser service.

WHY: This module tests the AUTO-DEPLOY-INDEX.md parsing functionality,
ensuring category mappings, language/framework detection, and filtering
logic work correctly.

DESIGN DECISION: Test with real AUTO-DEPLOY-INDEX.md file

Rationale: Since AUTO-DEPLOY-INDEX.md is the source of truth and we expect
it to exist in production, testing with the real file ensures our parser
handles the actual format correctly. This is more reliable than mocking.

Trade-offs:
- Reliability: Tests break if file format changes (good - we want to know!)
- Maintenance: Tests coupled to file structure (acceptable for core feature)
- Performance: File I/O in tests is fast enough (~1ms per test)
"""

from pathlib import Path

import pytest

from claude_mpm.services.agents.auto_deploy_index_parser import AutoDeployIndexParser


# Find AUTO-DEPLOY-INDEX.md in test fixtures or use real file
@pytest.fixture
def index_file_path():
    """Get path to AUTO-DEPLOY-INDEX.md for testing.

    Tries to find the file in:
    1. Test fixtures directory
    2. Real agent cache (if available)

    Returns:
        Path to AUTO-DEPLOY-INDEX.md
    """
    # Try test fixtures first
    fixtures_path = (
        Path(__file__).parent.parent.parent / "fixtures" / "AUTO-DEPLOY-INDEX.md"
    )

    if fixtures_path.exists():
        return fixtures_path

    # Fall back to real cache
    cache_path = (
        Path.home()
        / ".claude-mpm"
        / "cache"
        / "remote-agents"
        / "bobmatnyc"
        / "claude-mpm-agents"
        / "AUTO-DEPLOY-INDEX.md"
    )

    if cache_path.exists():
        return cache_path

    pytest.skip("AUTO-DEPLOY-INDEX.md not found in fixtures or cache")


@pytest.fixture
def parser(index_file_path):
    """Create AutoDeployIndexParser instance with test file."""
    return AutoDeployIndexParser(index_file_path)


class TestAutoDeployIndexParserInit:
    """Test parser initialization."""

    def test_init_with_valid_path(self, index_file_path):
        """Test parser initializes with valid path."""
        parser = AutoDeployIndexParser(index_file_path)

        assert parser.index_file_path == Path(index_file_path)
        assert parser._cache is None
        assert parser._content is None

    def test_init_with_nonexistent_path(self):
        """Test parser initializes with nonexistent path (doesn't fail until parse)."""
        parser = AutoDeployIndexParser(Path("/nonexistent/file.md"))

        assert parser.index_file_path == Path("/nonexistent/file.md")
        # Shouldn't raise error until parse() is called


class TestAutoDeployIndexParserParse:
    """Test parsing AUTO-DEPLOY-INDEX.md."""

    def test_parse_returns_structure(self, parser):
        """Test parse returns expected data structure."""
        result = parser.parse()

        assert isinstance(result, dict)
        assert "universal_agents" in result
        assert "language_mappings" in result
        assert "framework_mappings" in result
        assert "platform_mappings" in result
        assert "specialization_mappings" in result

    def test_parse_caches_results(self, parser):
        """Test parse caches results for performance."""
        result1 = parser.parse()
        result2 = parser.parse()

        assert result1 is result2  # Same object (cached)

    def test_parse_universal_agents(self, parser):
        """Test parsing universal agents section."""
        result = parser.parse()
        universal_agents = result["universal_agents"]

        assert isinstance(universal_agents, list)
        assert len(universal_agents) > 0

        # Check for expected universal agents
        expected_agents = [
            "universal/memory-manager",
            "universal/research",
            "universal/code-analyzer",
            "documentation/documentation",
            "documentation/ticketing",
        ]

        for agent in expected_agents:
            assert (
                agent in universal_agents
            ), f"Expected agent '{agent}' not found in universal agents"

    def test_parse_language_mappings(self, parser):
        """Test parsing language-specific mappings."""
        result = parser.parse()
        language_mappings = result["language_mappings"]

        assert isinstance(language_mappings, dict)
        assert len(language_mappings) > 0

        # Check Python language mapping
        assert "python" in language_mappings

        python_mapping = language_mappings["python"]
        assert "core" in python_mapping
        assert "optional" in python_mapping

        assert isinstance(python_mapping["core"], list)
        assert isinstance(python_mapping["optional"], list)

        # Verify expected Python agents
        assert "engineer/backend/python-engineer" in python_mapping["core"]
        assert "qa/qa" in python_mapping["core"]
        assert "ops/core/ops" in python_mapping["core"]

    def test_parse_framework_mappings(self, parser):
        """Test parsing framework-specific mappings."""
        result = parser.parse()
        framework_mappings = result["framework_mappings"]

        assert isinstance(framework_mappings, dict)
        assert len(framework_mappings) > 0

        # Check React framework mapping
        assert "react" in framework_mappings or "react-projects" in framework_mappings

        # Get the actual key used
        react_key = next(k for k in framework_mappings if "react" in k.lower())
        react_agents = framework_mappings[react_key]

        assert isinstance(react_agents, list)
        assert len(react_agents) > 0

    def test_parse_platform_mappings(self, parser):
        """Test parsing platform-specific mappings."""
        result = parser.parse()
        platform_mappings = result["platform_mappings"]

        assert isinstance(platform_mappings, dict)
        assert len(platform_mappings) > 0

        # Check for common platforms
        platform_keys = [k.lower() for k in platform_mappings]
        assert any("vercel" in k for k in platform_keys), "Vercel platform not found"

    def test_parse_with_nonexistent_file(self):
        """Test parse with nonexistent file returns empty result."""
        parser = AutoDeployIndexParser(Path("/nonexistent/file.md"))
        result = parser.parse()

        assert result == {
            "universal_agents": [],
            "language_mappings": {},
            "framework_mappings": {},
            "platform_mappings": {},
            "specialization_mappings": {},
        }


class TestAutoDeployIndexParserGetters:
    """Test getter methods for filtered results."""

    def test_get_categories(self, parser):
        """Test getting all categories."""
        categories = parser.get_categories()

        assert isinstance(categories, list)
        assert len(categories) > 0

        # Check for expected categories
        expected_categories = [
            "universal",
            "documentation",
            "engineer/backend",
            "qa",
            "ops",
        ]

        for category in expected_categories:
            assert any(
                category in c for c in categories
            ), f"Expected category '{category}' not found"

    def test_get_agents_by_category(self, parser):
        """Test filtering agents by category."""
        # Test engineer/backend category
        agents = parser.get_agents_by_category("engineer/backend")

        assert isinstance(agents, list)
        assert len(agents) > 0

        # All agents should start with 'engineer/backend/'
        for agent in agents:
            assert agent.startswith(
                "engineer/backend/"
            ), f"Agent '{agent}' doesn't match category"

    def test_get_agents_by_category_nonexistent(self, parser):
        """Test filtering by nonexistent category returns empty list."""
        agents = parser.get_agents_by_category("nonexistent/category")

        assert isinstance(agents, list)
        assert len(agents) == 0

    def test_get_agents_by_language(self, parser):
        """Test getting agents by language."""
        # Test Python language
        result = parser.get_agents_by_language("python")

        assert isinstance(result, dict)
        assert "core" in result
        assert "optional" in result

        assert isinstance(result["core"], list)
        assert isinstance(result["optional"], list)

        # Should have core agents
        assert len(result["core"]) > 0

        # Verify expected agents
        assert "engineer/backend/python-engineer" in result["core"]

    def test_get_agents_by_language_case_insensitive(self, parser):
        """Test language lookup is case-insensitive."""
        result_lower = parser.get_agents_by_language("python")
        result_upper = parser.get_agents_by_language("Python")
        result_mixed = parser.get_agents_by_language("PYTHON")

        assert result_lower == result_upper == result_mixed

    def test_get_agents_by_language_nonexistent(self, parser):
        """Test nonexistent language returns empty dict."""
        result = parser.get_agents_by_language("nonexistent")

        assert result == {"core": [], "optional": []}

    def test_get_agents_by_framework(self, parser):
        """Test getting agents by framework."""
        # Parse first to ensure data loaded
        parser.parse()

        # Try to find a React framework key
        data = parser.parse()
        framework_keys = list(data["framework_mappings"].keys())

        if not framework_keys:
            pytest.skip("No framework mappings found")

        # Use first available framework
        framework_key = framework_keys[0]
        agents = parser.get_agents_by_framework(framework_key)

        assert isinstance(agents, list)

    def test_get_agents_by_platform(self, parser):
        """Test getting agents by platform."""
        # Parse first to ensure data loaded
        parser.parse()

        # Try to find a platform key
        data = parser.parse()
        platform_keys = list(data["platform_mappings"].keys())

        if not platform_keys:
            pytest.skip("No platform mappings found")

        # Use first available platform
        platform_key = platform_keys[0]
        agents = parser.get_agents_by_platform(platform_key)

        assert isinstance(agents, list)

    def test_get_agents_by_specialization(self, parser):
        """Test getting agents by specialization."""
        # Parse first to ensure data loaded
        parser.parse()

        # Try to find a specialization key
        data = parser.parse()
        spec_keys = list(data["specialization_mappings"].keys())

        if not spec_keys:
            pytest.skip("No specialization mappings found")

        # Use first available specialization
        spec_key = spec_keys[0]
        agents = parser.get_agents_by_specialization(spec_key)

        assert isinstance(agents, list)


class TestAutoDeployIndexParserEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_file(self, tmp_path):
        """Test parsing empty file returns empty result."""
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("")

        parser = AutoDeployIndexParser(empty_file)
        result = parser.parse()

        assert result["universal_agents"] == []
        assert result["language_mappings"] == {}

    def test_malformed_markdown(self, tmp_path):
        """Test parsing malformed markdown returns partial results."""
        malformed_file = tmp_path / "malformed.md"
        malformed_file.write_text(
            """
# Some Header

This is not a valid AUTO-DEPLOY-INDEX.md file.

## Universal Agents (Always Deployed)

- `universal/memory-manager` - Memory management

Random text without proper structure.
"""
        )

        parser = AutoDeployIndexParser(malformed_file)
        result = parser.parse()

        # Should parse what it can
        assert isinstance(result, dict)

        # Universal agents should be found
        assert "universal/memory-manager" in result["universal_agents"]

    def test_file_with_unicode(self, tmp_path):
        """Test parsing file with unicode characters."""
        unicode_file = tmp_path / "unicode.md"
        unicode_file.write_text(
            """
## Universal Agents (Always Deployed)

- `universal/memory-manager` - Mémoire management 🚀
- `universal/research` - Recherche avec émojis ✨

## Project Type Detection

### Python Projects

**Auto-Deploy Agents**:
- `engineer/backend/python-engineer` - Python développement
""",
            encoding="utf-8",
        )

        parser = AutoDeployIndexParser(unicode_file)
        result = parser.parse()

        # Should handle unicode without errors
        assert "universal/memory-manager" in result["universal_agents"]
        assert "universal/research" in result["universal_agents"]


class TestAutoDeployIndexParserPerformance:
    """Test performance characteristics."""

    def test_parse_performance(self, parser, benchmark):
        """Test parsing performance (should be < 100ms)."""
        # First parse to load file
        parser.parse()

        # Reset cache to test parse from scratch
        parser._cache = None

        # Benchmark parsing
        result = benchmark(parser.parse)

        assert result is not None

    def test_cached_parse_performance(self, parser, benchmark):
        """Test cached parsing performance (should be < 1ms)."""
        # Pre-parse to populate cache
        parser.parse()

        # Benchmark cached access
        result = benchmark(parser.parse)

        assert result is not None
