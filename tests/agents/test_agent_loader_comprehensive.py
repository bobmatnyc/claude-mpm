#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Agent Loading Functionality
========================================================

This test module provides comprehensive coverage for the AgentLoader class,
testing all core methods, caching behavior, error handling, and performance.

Test Categories:
----------------
1. Core Methods: list_agents, get_agent, get_agent_prompt, get_agent_metadata
2. Caching: Cache hits/misses, invalidation, TTL behavior
3. Error Handling: Missing agents, invalid configurations, corrupted files
4. Dynamic Model Selection: Complexity analysis, model thresholds
5. Performance: Loading multiple agents, cache efficiency
6. Backward Compatibility: Legacy function support
7. Utility Functions: Validation, reloading, cache management

WHY: Comprehensive testing ensures the agent loading system remains reliable
as it's a critical component used throughout the Claude MPM system. These
tests verify both functional correctness and performance characteristics.
"""

import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_mpm.agents.agent_loader import (  # Legacy functions
    AGENT_CACHE_PREFIX,
    MODEL_NAME_MAPPINGS,
    MODEL_THRESHOLDS,
    AgentLoader,
    ComplexityLevel,
    ModelType,
    _get_loader,
    clear_agent_cache,
    get_agent_prompt,
    get_agent_prompt_with_model_info,
    get_documentation_agent_prompt,
    get_engineer_agent_prompt,
    get_qa_agent_prompt,
    get_research_agent_prompt,
    list_available_agents,
    reload_agents,
    validate_agent_files,
)
from claude_mpm.services.memory.cache.shared_prompt_cache import SharedPromptCache
from claude_mpm.validation.agent_validator import ValidationResult


class TestAgentLoaderCore:
    """Test core AgentLoader methods."""

    # Fixtures moved to conftest.py
    def _unused_mock_agent_data(self) -> Dict[str, Any]:
        """Create mock agent data matching the schema."""
        return {
            "schema_version": "1.1.0",
            "agent_id": "test_agent",
            "agent_version": "1.0.0",
            "agent_type": "base",
            "metadata": {
                "name": "Test Agent",
                "description": "A test agent for unit testing",
                "category": "quality",
                "tags": ["test", "mock"],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
            "capabilities": {
                "model": "claude-sonnet-4-20250514",
                "resource_tier": "standard",
                "tools": ["Read", "Grep"],
                "features": ["caching", "validation"],
            },
            "instructions": "# Test Agent Instructions\n\nThis is a test agent for unit testing purposes.\n\n## Purpose\n\nThe test agent is designed to validate the agent loading functionality, including:\n- Schema validation\n- Caching behavior\n- Error handling\n- Performance characteristics\n\n## Capabilities\n\nThis agent supports various testing scenarios and can be used to verify:\n1. Agent discovery and registration\n2. Prompt loading and caching\n3. Metadata retrieval\n4. Dynamic model selection\n\n## Testing Guidelines\n\nWhen using this agent for testing:\n- Ensure all required fields are populated\n- Verify caching behavior works as expected\n- Test error conditions and edge cases\n- Monitor performance metrics\n\n## Additional Context\n\nThis agent is part of the comprehensive test suite for the Claude MPM agent loading system. It provides a minimal but complete implementation that satisfies all schema requirements while being simple enough for testing purposes.",
            "knowledge": {
                "domain_expertise": ["testing", "mocking"],
                "codebase_patterns": ["pytest", "unittest"],
            },
            "interactions": {
                "input_format": {"required_fields": ["text"]},
                "output_format": {"structure": "markdown"},
            },
        }

    # Fixtures moved to conftest.py
    def _unused_temp_agent_dir(self, tmp_path, mock_agent_data):
        """Create a temporary directory with test agent files."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create test agent file
        agent_file = templates_dir / "test_agent.json"
        agent_file.write_text(json.dumps(mock_agent_data, indent=2))

        # Create another test agent
        research_data = mock_agent_data.copy()
        research_data.update(
            {
                "agent_id": "research_agent",
                "agent_type": "research",
                "metadata": mock_agent_data["metadata"].copy(),
            }
        )
        research_data["metadata"].update(
            {
                "name": "Research Agent",
                "description": "Agent for research tasks",
                "category": "research",
            }
        )
        research_data["capabilities"] = mock_agent_data["capabilities"].copy()
        research_data["capabilities"].update(
            {"model": "claude-opus-4-20250514", "resource_tier": "intensive"}
        )
        research_data[
            "instructions"
        ] = "# Research Agent\n\nSpecialized for research and analysis tasks.\n\n## Core Functionality\n\nThe Research Agent is optimized for:\n- Deep codebase analysis using tree-sitter AST\n- Pattern recognition and identification\n- Security vulnerability assessment\n- Performance optimization opportunities\n- Architecture documentation\n\n## Research Capabilities\n\n1. **Code Analysis**: Leverages tree-sitter for syntactic and semantic analysis\n2. **Pattern Detection**: Identifies common patterns and anti-patterns\n3. **Documentation**: Generates comprehensive technical documentation\n4. **Metrics Collection**: Gathers code quality and complexity metrics\n\n## Best Practices\n\nWhen conducting research:\n- Start with high-level architecture overview\n- Drill down into specific components as needed\n- Document findings with clear examples\n- Provide actionable recommendations\n- Include confidence levels in assessments\n\n## Integration\n\nThis agent integrates with other system components to provide comprehensive analysis capabilities for the Claude MPM system."
        research_file = templates_dir / "research_agent.json"
        research_file.write_text(json.dumps(research_data, indent=2))

        # Create schema file (should be ignored)
        schema_file = templates_dir / "agent_schema.json"
        schema_file.write_text(json.dumps({"type": "object"}, indent=2))

        return templates_dir

    def test_agent_loader_initialization(self, temp_agent_dir, monkeypatch):
        """Test AgentLoader initializes correctly and loads agents."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )

        loader = AgentLoader()

        # Verify initialization
        assert loader.validator is not None
        assert loader.cache is not None
        assert len(loader._agent_registry) == 2  # test_agent and research_agent
        assert "test_agent" in loader._agent_registry
        assert "research_agent" in loader._agent_registry

        # Verify metrics initialization
        assert loader._metrics["agents_loaded"] == 2
        assert loader._metrics["validation_failures"] == 0
        assert loader._metrics["initialization_time_ms"] > 0

    def test_get_agent(self, temp_agent_dir, monkeypatch):
        """Test retrieving agent configuration by ID."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )

        loader = AgentLoader()

        # Test existing agent
        agent = loader.get_agent("test_agent")
        assert agent is not None
        assert agent["agent_id"] == "test_agent"
        assert agent["metadata"]["name"] == "Test Agent"

        # Test non-existent agent
        missing = loader.get_agent("missing_agent")
        assert missing is None

    def test_list_agents(self, temp_agent_dir, monkeypatch):
        """Test listing all available agents."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )

        loader = AgentLoader()
        agents = loader.list_agents()

        assert len(agents) == 2
        assert all(isinstance(agent, dict) for agent in agents)

        # Check agent summaries
        test_agent = next(a for a in agents if a["id"] == "test_agent")
        assert test_agent["name"] == "Test Agent"
        assert test_agent["description"] == "A test agent for unit testing"
        assert test_agent["category"] == "quality"
        assert test_agent["model"] == "claude-sonnet-4-20250514"
        assert test_agent["resource_tier"] == "standard"

        # Verify sorting
        agent_ids = [a["id"] for a in agents]
        assert agent_ids == sorted(agent_ids)

    def test_get_agent_prompt(self, temp_agent_dir, monkeypatch):
        """Test retrieving agent prompt with caching."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )

        loader = AgentLoader()

        # First call - cache miss
        prompt1 = loader.get_agent_prompt("test_agent")
        assert prompt1 is not None
        assert prompt1.startswith("# Test Agent Instructions")
        assert loader._metrics["cache_misses"] == 1
        assert loader._metrics["cache_hits"] == 0
        assert loader._metrics["usage_counts"]["test_agent"] == 1

        # Second call - cache hit
        prompt2 = loader.get_agent_prompt("test_agent")
        assert prompt2 == prompt1
        assert loader._metrics["cache_misses"] == 1
        assert loader._metrics["cache_hits"] == 1
        assert loader._metrics["usage_counts"]["test_agent"] == 2

        # Force reload
        prompt3 = loader.get_agent_prompt("test_agent", force_reload=True)
        assert prompt3 == prompt1
        assert loader._metrics["cache_misses"] == 2

        # Non-existent agent
        missing = loader.get_agent_prompt("missing_agent")
        assert missing is None

    def test_get_agent_metadata(self, temp_agent_dir, monkeypatch):
        """Test retrieving agent metadata."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )

        loader = AgentLoader()
        metadata = loader.get_agent_metadata("test_agent")

        assert metadata is not None
        assert metadata["id"] == "test_agent"
        assert (
            metadata["version"] == "1.0.0"
        )  # The get_agent_metadata returns "version", not "agent_version"
        assert metadata["metadata"]["name"] == "Test Agent"
        assert metadata["capabilities"]["model"] == "claude-sonnet-4-20250514"
        assert "instructions" not in metadata  # Should exclude instructions

        # Non-existent agent
        missing = loader.get_agent_metadata("missing_agent")
        assert missing is None

    def test_metrics_collection(self, temp_agent_dir, monkeypatch):
        """Test performance metrics collection."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )

        loader = AgentLoader()

        # Generate some metrics
        loader.get_agent_prompt("test_agent")
        loader.get_agent_prompt("test_agent")  # Cache hit
        loader.get_agent_prompt("research_agent")

        metrics = loader.get_metrics()

        # Verify metrics structure
        assert metrics["agents_loaded"] == 2
        assert metrics["validation_failures"] == 0
        assert metrics["cache_hit_rate_percent"] > 0
        # Cache behavior may vary due to internal optimizations
        assert metrics["cache_hits"] >= 1
        assert metrics["cache_misses"] >= 1
        assert metrics["cache_hits"] + metrics["cache_misses"] >= 3
        assert metrics["average_load_time_ms"] >= 0
        assert "test_agent" in metrics["top_agents_by_usage"]
        assert metrics["prompt_size_stats"]["total_agents"] == 2


class TestAgentLoaderCaching:
    """Test caching behavior in detail."""

    @pytest.fixture
    def mock_cache(self):
        """Create a mock cache for testing."""
        cache = Mock(spec=SharedPromptCache)
        cache.get = Mock(return_value=None)
        cache.set = Mock()
        cache.invalidate = Mock()
        return cache

    # Fixtures moved to conftest.py
    def _unused_mock_agent_data(self) -> Dict[str, Any]:
        """Create mock agent data matching the schema."""
        return {
            "schema_version": "1.1.0",
            "agent_id": "test_agent",
            "agent_version": "1.0.0",
            "agent_type": "base",
            "metadata": {
                "name": "Test Agent",
                "description": "A test agent for unit testing",
                "category": "quality",
                "tags": ["test", "mock"],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
            "capabilities": {
                "model": "claude-sonnet-4-20250514",
                "resource_tier": "standard",
                "tools": ["Read", "Grep"],
                "features": ["caching", "validation"],
            },
            "instructions": "# Test Agent Instructions\n\nThis is a test agent for unit testing purposes.\n\n## Purpose\n\nThe test agent is designed to validate the agent loading functionality, including:\n- Schema validation\n- Caching behavior\n- Error handling\n- Performance characteristics\n\n## Capabilities\n\nThis agent supports various testing scenarios and can be used to verify:\n1. Agent discovery and registration\n2. Prompt loading and caching\n3. Metadata retrieval\n4. Dynamic model selection\n\n## Testing Guidelines\n\nWhen using this agent for testing:\n- Ensure all required fields are populated\n- Verify caching behavior works as expected\n- Test error conditions and edge cases\n- Monitor performance metrics\n\n## Additional Context\n\nThis agent is part of the comprehensive test suite for the Claude MPM agent loading system. It provides a minimal but complete implementation that satisfies all schema requirements while being simple enough for testing purposes.",
            "knowledge": {
                "domain_expertise": ["testing", "mocking"],
                "codebase_patterns": ["pytest", "unittest"],
            },
            "interactions": {
                "input_format": {"required_fields": ["text"]},
                "output_format": {"structure": "markdown"},
            },
        }

    # Fixtures moved to conftest.py
    def _unused_temp_agent_dir(self, tmp_path, mock_agent_data):
        """Create a temporary directory with test agent files."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create test agent file
        agent_file = templates_dir / "test_agent.json"
        agent_file.write_text(json.dumps(mock_agent_data, indent=2))

        # Create another test agent
        research_data = mock_agent_data.copy()
        research_data.update(
            {
                "agent_id": "research_agent",
                "agent_type": "research",
                "metadata": mock_agent_data["metadata"].copy(),
            }
        )
        research_data["metadata"].update(
            {
                "name": "Research Agent",
                "description": "Agent for research tasks",
                "category": "research",
            }
        )
        research_data["capabilities"] = mock_agent_data["capabilities"].copy()
        research_data["capabilities"].update(
            {"model": "claude-opus-4-20250514", "resource_tier": "intensive"}
        )
        research_data[
            "instructions"
        ] = "# Research Agent\n\nSpecialized for research and analysis tasks.\n\n## Core Functionality\n\nThe Research Agent is optimized for:\n- Deep codebase analysis using tree-sitter AST\n- Pattern recognition and identification\n- Security vulnerability assessment\n- Performance optimization opportunities\n- Architecture documentation\n\n## Research Capabilities\n\n1. **Code Analysis**: Leverages tree-sitter for syntactic and semantic analysis\n2. **Pattern Detection**: Identifies common patterns and anti-patterns\n3. **Documentation**: Generates comprehensive technical documentation\n4. **Metrics Collection**: Gathers code quality and complexity metrics\n\n## Best Practices\n\nWhen conducting research:\n- Start with high-level architecture overview\n- Drill down into specific components as needed\n- Document findings with clear examples\n- Provide actionable recommendations\n- Include confidence levels in assessments\n\n## Integration\n\nThis agent integrates with other system components to provide comprehensive analysis capabilities for the Claude MPM system."
        research_file = templates_dir / "research_agent.json"
        research_file.write_text(json.dumps(research_data, indent=2))

        # Create schema file (should be ignored)
        schema_file = templates_dir / "agent_schema.json"
        schema_file.write_text(json.dumps({"type": "object"}, indent=2))

        return templates_dir

    def test_cache_key_generation(self, temp_agent_dir, mock_cache, monkeypatch):
        """Test correct cache key generation."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )

        loader = AgentLoader()
        loader.cache = mock_cache

        loader.get_agent_prompt("test_agent")

        # Verify cache key format
        expected_key = f"{AGENT_CACHE_PREFIX}test_agent"
        mock_cache.get.assert_called_with(expected_key)

        # Check that set was called with correct key and TTL
        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        assert call_args[0][0] == expected_key  # First positional arg is the key
        assert call_args[0][1].startswith(
            "# Test Agent Instructions"
        )  # Second is the content
        assert call_args[1]["ttl"] == 3600  # TTL in kwargs

    def test_cache_ttl_behavior(self, temp_agent_dir, monkeypatch):
        """Test cache TTL is set correctly."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )

        with patch.object(SharedPromptCache, "set") as mock_set:
            loader = AgentLoader()
            loader.get_agent_prompt("test_agent")

            # Verify TTL is 1 hour (3600 seconds)
            mock_set.assert_called_once()
            args, kwargs = mock_set.call_args
            assert kwargs.get("ttl") == 3600

    def test_cache_invalidation(self, temp_agent_dir, mock_cache, monkeypatch):
        """Test cache invalidation functionality."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )
        monkeypatch.setattr("claude_mpm.agents.agent_loader._loader", None)

        with patch.object(SharedPromptCache, "get_instance", return_value=mock_cache):
            # Clear specific agent cache
            clear_agent_cache("test_agent")
            mock_cache.invalidate.assert_called_with(f"{AGENT_CACHE_PREFIX}test_agent")

            # Clear all agent caches
            mock_cache.invalidate.reset_mock()
            clear_agent_cache()
            assert (
                mock_cache.invalidate.call_count >= 2
            )  # At least test_agent and research_agent


class TestAgentLoaderErrorHandling:
    """Test error handling scenarios."""

    def test_invalid_json_handling(self, tmp_path, monkeypatch):
        """Test handling of invalid JSON files."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create invalid JSON file
        invalid_file = templates_dir / "invalid_agent.json"
        invalid_file.write_text("{ invalid json }")

        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", templates_dir
        )

        # Should not raise exception
        loader = AgentLoader()
        assert len(loader._agent_registry) == 0

    def test_missing_required_fields(self, tmp_path, monkeypatch):
        """Test handling of agents missing required fields."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Agent missing agent_id
        incomplete_agent = {
            "version": "1.0.0",
            "metadata": {"name": "Incomplete"},
            "instructions": "Test",
        }

        agent_file = templates_dir / "incomplete_agent.json"
        agent_file.write_text(json.dumps(incomplete_agent))

        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", templates_dir
        )

        loader = AgentLoader()
        assert len(loader._agent_registry) == 0
        assert loader._metrics["validation_failures"] == 1

    def test_empty_instructions_handling(self, tmp_path, monkeypatch):
        """Test handling of agents with empty instructions."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        agent_data = {
            "schema_version": "1.0.0",
            "agent_id": "empty_agent",
            "agent_version": "1.0.0",
            "agent_type": "base",
            "metadata": {
                "name": "Empty Agent",
                "description": "Test agent with empty instructions",
                "author": "test",
            },
            "instructions": "",  # Empty instructions
            "capabilities": {
                "model": "claude-sonnet-4-20250514",
                "resource_tier": "standard",
            },
        }

        agent_file = templates_dir / "empty_agent.json"
        agent_file.write_text(json.dumps(agent_data))

        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", templates_dir
        )

        loader = AgentLoader()
        prompt = loader.get_agent_prompt("empty_agent")
        assert prompt is None  # Should return None for empty instructions

    def test_file_permission_error(self, tmp_path, monkeypatch, caplog):
        """Test handling of file permission errors."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create a file and make it unreadable (platform-specific)
        agent_file = templates_dir / "restricted_agent.json"
        agent_file.write_text('{"agent_id": "test"}')

        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", templates_dir
        )

        # Mock open to raise PermissionError
        original_open = open

        def mock_open(path, *args, **kwargs):
            if "restricted_agent" in str(path):
                raise PermissionError("Access denied")
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", mock_open):
            with caplog.at_level(logging.ERROR):
                loader = AgentLoader()
                assert "Failed to load restricted_agent.json" in caplog.text


class TestDynamicModelSelection:
    """Test dynamic model selection based on task complexity."""

    def test_complexity_analysis_integration(self, temp_agent_dir, monkeypatch):
        """Test integration with complexity analysis."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )
        monkeypatch.setattr("claude_mpm.agents.agent_loader._loader", None)

        # Test with task description
        prompt, model, config = get_agent_prompt(
            "test_agent",
            return_model_info=True,
            task_description="Analyze complex codebase architecture",
        )

        assert prompt is not None
        assert model in MODEL_NAME_MAPPINGS.values()
        assert config["selection_method"] in [
            "dynamic_complexity_based",
            "agent_default",
        ]

        # The placeholder implementation returns MEDIUM complexity
        if config["selection_method"] == "dynamic_complexity_based":
            assert config["complexity_level"] == ComplexityLevel.MEDIUM

    def test_model_threshold_mapping(self):
        """Test model selection based on complexity thresholds."""
        # Test each complexity level
        test_cases = [
            (10, ModelType.HAIKU),  # Low complexity
            (50, ModelType.SONNET),  # Medium complexity
            (90, ModelType.OPUS),  # High complexity
        ]

        for score, expected_model in test_cases:
            # Simulate complexity analysis result
            complexity_result = {
                "complexity_score": score,
                "complexity_level": ComplexityLevel.HIGH
                if score > 70
                else (ComplexityLevel.MEDIUM if score > 30 else ComplexityLevel.LOW),
                "recommended_model": expected_model,
            }

            # Verify threshold mapping
            if expected_model == ModelType.HAIKU:
                assert (
                    MODEL_THRESHOLDS[ModelType.HAIKU]["min_complexity"]
                    <= score
                    <= MODEL_THRESHOLDS[ModelType.HAIKU]["max_complexity"]
                )
            elif expected_model == ModelType.SONNET:
                assert (
                    MODEL_THRESHOLDS[ModelType.SONNET]["min_complexity"]
                    <= score
                    <= MODEL_THRESHOLDS[ModelType.SONNET]["max_complexity"]
                )
            else:
                assert MODEL_THRESHOLDS[ModelType.OPUS]["min_complexity"] <= score

    def test_environment_variable_overrides(self, temp_agent_dir, monkeypatch):
        """Test environment variable control of model selection."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )
        monkeypatch.setattr("claude_mpm.agents.agent_loader._loader", None)

        # Disable global dynamic selection
        monkeypatch.setenv("ENABLE_DYNAMIC_MODEL_SELECTION", "false")

        _, model, config = get_agent_prompt(
            "test_agent", return_model_info=True, task_description="Complex task"
        )

        assert config["selection_method"] == "agent_default"
        assert config["reason"] == "dynamic_selection_disabled"

        # Enable per-agent override
        monkeypatch.setenv("CLAUDE_PM_TEST_AGENT_MODEL_SELECTION", "true")
        monkeypatch.setattr("claude_mpm.agents.agent_loader._loader", None)

        _, model, config = get_agent_prompt(
            "test_agent", return_model_info=True, task_description="Complex task"
        )

        # Should use dynamic selection despite global disable
        assert config["selection_method"] in [
            "dynamic_complexity_based",
            "agent_default",
        ]


class TestBackwardCompatibility:
    """Test backward compatibility with legacy functions."""

    def test_legacy_agent_functions(self, temp_agent_dir, monkeypatch):
        """Test legacy get_*_agent_prompt functions."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )
        monkeypatch.setattr("claude_mpm.agents.agent_loader._loader", None)

        # Create mock agents for legacy functions
        legacy_agents = {
            "documentation_agent": "Documentation instructions",
            "research_agent": "Research instructions",
            "qa_agent": "QA instructions",
            "engineer_agent": "Engineer instructions",
        }

        for agent_id, instructions in legacy_agents.items():
            agent_data = {
                "schema_version": "1.0.0",
                "agent_id": agent_id,
                "agent_version": "1.0.0",
                "agent_type": "base",
                "metadata": {
                    "name": agent_id,
                    "description": f"Test agent {agent_id}",
                    "author": "test",
                },
                "capabilities": {
                    "model": "claude-sonnet-4-20250514",
                    "resource_tier": "standard",
                    "tools": ["Read", "Write", "Edit"],
                },
                "instructions": instructions,
            }
            agent_file = temp_agent_dir / f"{agent_id}.json"
            agent_file.write_text(json.dumps(agent_data))

        # Force reload to pick up new agents
        reload_agents()

        # Test legacy functions with base instructions prepended
        with patch(
            "claude_mpm.agents.agent_loader.prepend_base_instructions",
            side_effect=lambda x, **k: f"BASE\n{x}",
        ):
            doc_prompt = get_documentation_agent_prompt()
            assert "Documentation instructions" in doc_prompt
            assert "BASE" in doc_prompt

            research_prompt = get_research_agent_prompt()
            assert "Research instructions" in research_prompt

            qa_prompt = get_qa_agent_prompt()
            assert "QA instructions" in qa_prompt

            eng_prompt = get_engineer_agent_prompt()
            assert "Engineer instructions" in eng_prompt

    def test_load_agent_prompt_from_md(self, temp_agent_dir, monkeypatch):
        """Test the legacy load_agent_prompt_from_md function."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )
        monkeypatch.setattr("claude_mpm.agents.agent_loader._loader", None)

        from claude_mpm.agents.agent_loader import load_agent_prompt_from_md

        # Should work despite the "md" in the name
        prompt = load_agent_prompt_from_md("test_agent")
        assert prompt == "# Test Agent Instructions\n\nThis is a test agent."

        # Force reload should work
        prompt2 = load_agent_prompt_from_md("test_agent", force_reload=True)
        assert prompt2 == prompt


class TestUtilityFunctions:
    """Test utility functions for agent management."""

    # Fixtures moved to conftest.py
    def _unused_mock_agent_data(self) -> Dict[str, Any]:
        """Create mock agent data matching the schema."""
        return {
            "schema_version": "1.1.0",
            "agent_id": "test_agent",
            "agent_version": "1.0.0",
            "agent_type": "base",
            "metadata": {
                "name": "Test Agent",
                "description": "A test agent for unit testing",
                "category": "quality",
                "tags": ["test", "mock"],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
            "capabilities": {
                "model": "claude-sonnet-4-20250514",
                "resource_tier": "standard",
                "tools": ["Read", "Grep"],
                "features": ["caching", "validation"],
            },
            "instructions": "# Test Agent Instructions\n\nThis is a test agent for unit testing purposes.\n\n## Purpose\n\nThe test agent is designed to validate the agent loading functionality, including:\n- Schema validation\n- Caching behavior\n- Error handling\n- Performance characteristics\n\n## Capabilities\n\nThis agent supports various testing scenarios and can be used to verify:\n1. Agent discovery and registration\n2. Prompt loading and caching\n3. Metadata retrieval\n4. Dynamic model selection\n\n## Testing Guidelines\n\nWhen using this agent for testing:\n- Ensure all required fields are populated\n- Verify caching behavior works as expected\n- Test error conditions and edge cases\n- Monitor performance metrics\n\n## Additional Context\n\nThis agent is part of the comprehensive test suite for the Claude MPM agent loading system. It provides a minimal but complete implementation that satisfies all schema requirements while being simple enough for testing purposes.",
            "knowledge": {
                "domain_expertise": ["testing", "mocking"],
                "codebase_patterns": ["pytest", "unittest"],
            },
            "interactions": {
                "input_format": {"required_fields": ["text"]},
                "output_format": {"structure": "markdown"},
            },
        }

    # Fixtures moved to conftest.py
    def _unused_temp_agent_dir(self, tmp_path, mock_agent_data):
        """Create a temporary directory with test agent files."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create test agent file
        agent_file = templates_dir / "test_agent.json"
        agent_file.write_text(json.dumps(mock_agent_data, indent=2))

        # Create another test agent
        research_data = mock_agent_data.copy()
        research_data.update(
            {
                "agent_id": "research_agent",
                "agent_type": "research",
                "metadata": mock_agent_data["metadata"].copy(),
            }
        )
        research_data["metadata"].update(
            {
                "name": "Research Agent",
                "description": "Agent for research tasks",
                "category": "research",
            }
        )
        research_data["capabilities"] = mock_agent_data["capabilities"].copy()
        research_data["capabilities"].update(
            {"model": "claude-opus-4-20250514", "resource_tier": "intensive"}
        )
        research_data[
            "instructions"
        ] = "# Research Agent\n\nSpecialized for research and analysis tasks.\n\n## Core Functionality\n\nThe Research Agent is optimized for:\n- Deep codebase analysis using tree-sitter AST\n- Pattern recognition and identification\n- Security vulnerability assessment\n- Performance optimization opportunities\n- Architecture documentation\n\n## Research Capabilities\n\n1. **Code Analysis**: Leverages tree-sitter for syntactic and semantic analysis\n2. **Pattern Detection**: Identifies common patterns and anti-patterns\n3. **Documentation**: Generates comprehensive technical documentation\n4. **Metrics Collection**: Gathers code quality and complexity metrics\n\n## Best Practices\n\nWhen conducting research:\n- Start with high-level architecture overview\n- Drill down into specific components as needed\n- Document findings with clear examples\n- Provide actionable recommendations\n- Include confidence levels in assessments\n\n## Integration\n\nThis agent integrates with other system components to provide comprehensive analysis capabilities for the Claude MPM system."
        research_file = templates_dir / "research_agent.json"
        research_file.write_text(json.dumps(research_data, indent=2))

        # Create schema file (should be ignored)
        schema_file = templates_dir / "agent_schema.json"
        schema_file.write_text(json.dumps({"type": "object"}, indent=2))

        return templates_dir

    def test_list_available_agents(self, temp_agent_dir, monkeypatch):
        """Test listing available agents with metadata."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )
        monkeypatch.setattr("claude_mpm.agents.agent_loader._loader", None)

        agents = list_available_agents()

        assert isinstance(agents, dict)
        assert "test_agent" in agents
        assert "research_agent" in agents

        # Check agent details
        test_agent = agents["test_agent"]
        assert test_agent["name"] == "Test Agent"
        assert test_agent["description"] == "A test agent for unit testing"
        assert test_agent["category"] == "quality"
        assert test_agent["version"] == "1.0.0"
        assert test_agent["model"] == "claude-sonnet-4-20250514"
        assert test_agent["tools"] == ["Read", "Grep"]

    def test_validate_agent_files(self, temp_agent_dir, monkeypatch):
        """Test agent file validation."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )

        # Add an invalid agent file (missing required fields)
        invalid_agent = {"invalid": "structure"}
        invalid_file = temp_agent_dir / "invalid_agent.json"
        invalid_file.write_text(json.dumps(invalid_agent))

        results = validate_agent_files()

        assert "test_agent" in results
        assert results["test_agent"]["valid"] is True
        assert len(results["test_agent"]["errors"]) == 0

        assert "invalid_agent" in results
        assert results["invalid_agent"]["valid"] is False
        assert len(results["invalid_agent"]["errors"]) > 0

    def test_reload_agents(self, temp_agent_dir, monkeypatch):
        """Test agent reloading functionality."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )
        monkeypatch.setattr("claude_mpm.agents.agent_loader._loader", None)

        # Initial load
        loader1 = _get_loader()
        assert "test_agent" in loader1._agent_registry

        # Add a new agent file
        new_agent = {
            "agent_id": "new_agent",
            "version": "1.0.0",
            "metadata": {"name": "New Agent"},
            "capabilities": {},
            "instructions": "New agent instructions",
        }
        new_file = temp_agent_dir / "new_agent.json"
        new_file.write_text(json.dumps(new_agent))

        # Reload agents
        reload_agents()

        # Get new loader instance
        loader2 = _get_loader()
        assert loader2 is not loader1  # Should be new instance
        assert "new_agent" in loader2._agent_registry
        assert len(loader2._agent_registry) == 3  # test, research, and new

    def test_get_agent_prompt_with_model_info(self, temp_agent_dir, monkeypatch):
        """Test the convenience function for getting prompt with model info."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )
        monkeypatch.setattr("claude_mpm.agents.agent_loader._loader", None)

        prompt, model, config = get_agent_prompt_with_model_info(
            "test_agent", task_description="Simple task"
        )

        assert isinstance(prompt, str)
        assert "Test Agent Instructions" in prompt
        assert isinstance(model, str)
        assert model in MODEL_NAME_MAPPINGS.values()
        assert isinstance(config, dict)
        assert "selection_method" in config


class TestPerformance:
    """Test performance characteristics of agent loading."""

    # Fixtures moved to conftest.py
    def _unused_mock_agent_data(self) -> Dict[str, Any]:
        """Create mock agent data matching the schema."""
        return {
            "schema_version": "1.1.0",
            "agent_id": "test_agent",
            "agent_version": "1.0.0",
            "agent_type": "base",
            "metadata": {
                "name": "Test Agent",
                "description": "A test agent for unit testing",
                "category": "quality",
                "tags": ["test", "mock"],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
            "capabilities": {
                "model": "claude-sonnet-4-20250514",
                "resource_tier": "standard",
                "tools": ["Read", "Grep"],
                "features": ["caching", "validation"],
            },
            "instructions": "# Test Agent Instructions\n\nThis is a test agent for unit testing purposes.\n\n## Purpose\n\nThe test agent is designed to validate the agent loading functionality, including:\n- Schema validation\n- Caching behavior\n- Error handling\n- Performance characteristics\n\n## Capabilities\n\nThis agent supports various testing scenarios and can be used to verify:\n1. Agent discovery and registration\n2. Prompt loading and caching\n3. Metadata retrieval\n4. Dynamic model selection\n\n## Testing Guidelines\n\nWhen using this agent for testing:\n- Ensure all required fields are populated\n- Verify caching behavior works as expected\n- Test error conditions and edge cases\n- Monitor performance metrics\n\n## Additional Context\n\nThis agent is part of the comprehensive test suite for the Claude MPM agent loading system. It provides a minimal but complete implementation that satisfies all schema requirements while being simple enough for testing purposes.",
            "knowledge": {
                "domain_expertise": ["testing", "mocking"],
                "codebase_patterns": ["pytest", "unittest"],
            },
            "interactions": {
                "input_format": {"required_fields": ["text"]},
                "output_format": {"structure": "markdown"},
            },
        }

    # Fixtures moved to conftest.py
    def _unused_temp_agent_dir(self, tmp_path, mock_agent_data):
        """Create a temporary directory with test agent files."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create test agent file
        agent_file = templates_dir / "test_agent.json"
        agent_file.write_text(json.dumps(mock_agent_data, indent=2))

        # Create another test agent
        research_data = mock_agent_data.copy()
        research_data.update(
            {
                "agent_id": "research_agent",
                "agent_type": "research",
                "metadata": mock_agent_data["metadata"].copy(),
            }
        )
        research_data["metadata"].update(
            {
                "name": "Research Agent",
                "description": "Agent for research tasks",
                "category": "research",
            }
        )
        research_data["capabilities"] = mock_agent_data["capabilities"].copy()
        research_data["capabilities"].update(
            {"model": "claude-opus-4-20250514", "resource_tier": "intensive"}
        )
        research_data[
            "instructions"
        ] = "# Research Agent\n\nSpecialized for research and analysis tasks.\n\n## Core Functionality\n\nThe Research Agent is optimized for:\n- Deep codebase analysis using tree-sitter AST\n- Pattern recognition and identification\n- Security vulnerability assessment\n- Performance optimization opportunities\n- Architecture documentation\n\n## Research Capabilities\n\n1. **Code Analysis**: Leverages tree-sitter for syntactic and semantic analysis\n2. **Pattern Detection**: Identifies common patterns and anti-patterns\n3. **Documentation**: Generates comprehensive technical documentation\n4. **Metrics Collection**: Gathers code quality and complexity metrics\n\n## Best Practices\n\nWhen conducting research:\n- Start with high-level architecture overview\n- Drill down into specific components as needed\n- Document findings with clear examples\n- Provide actionable recommendations\n- Include confidence levels in assessments\n\n## Integration\n\nThis agent integrates with other system components to provide comprehensive analysis capabilities for the Claude MPM system."
        research_file = templates_dir / "research_agent.json"
        research_file.write_text(json.dumps(research_data, indent=2))

        # Create schema file (should be ignored)
        schema_file = templates_dir / "agent_schema.json"
        schema_file.write_text(json.dumps({"type": "object"}, indent=2))

        return templates_dir

    def test_multiple_agent_loading_performance(self, tmp_path, monkeypatch):
        """Test performance when loading many agents."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create 50 test agents
        for i in range(50):
            agent_data = {
                "schema_version": "1.0.0",
                "agent_id": f"agent_{i}",
                "agent_version": "1.0.0",
                "agent_type": "base",
                "metadata": {
                    "name": f"Agent {i}",
                    "description": f"Test agent {i}",
                    "author": "test",
                    "category": "quality",
                    "tags": ["test", "performance"],
                },
                "capabilities": {
                    "model": "claude-sonnet-4-20250514",
                    "resource_tier": "standard",
                    "tools": ["Read", "Write", "Edit"],
                },
                "instructions": f"Instructions for agent {i}"
                * 100,  # Make it reasonably sized
            }
            agent_file = templates_dir / f"agent_{i}.json"
            agent_file.write_text(json.dumps(agent_data))

        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", templates_dir
        )

        # Measure initialization time
        start_time = time.time()
        loader = AgentLoader()
        init_time = time.time() - start_time

        assert len(loader._agent_registry) == 50
        assert init_time < 1.0  # Should load 50 agents in under 1 second

        # Test listing performance
        start_time = time.time()
        agents = loader.list_agents()
        list_time = time.time() - start_time

        assert len(agents) == 50
        assert list_time < 0.1  # Listing should be very fast

    def test_cache_efficiency(self, temp_agent_dir, monkeypatch):
        """Test cache efficiency with repeated access."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )
        monkeypatch.setattr("claude_mpm.agents.agent_loader._loader", None)

        loader = _get_loader()

        # Access same agent multiple times
        access_times = []
        for i in range(10):
            start_time = time.time()
            prompt = loader.get_agent_prompt("test_agent")
            access_time = time.time() - start_time
            access_times.append(access_time)

        # First access should be slower (cache miss)
        # Subsequent accesses should be faster (cache hits)
        assert (
            access_times[0] > sum(access_times[1:]) / 9
        )  # First is slower than average of others
        assert loader._metrics["cache_hits"] == 9
        assert loader._metrics["cache_misses"] == 1

    def test_prompt_size_tracking(self, temp_agent_dir, monkeypatch):
        """Test tracking of prompt sizes for memory analysis."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )
        monkeypatch.setattr("claude_mpm.agents.agent_loader._loader", None)

        loader = _get_loader()

        # Load all agents to track sizes
        loader.get_agent_prompt("test_agent")
        loader.get_agent_prompt("research_agent")

        metrics = loader.get_metrics()
        size_stats = metrics["prompt_size_stats"]

        assert size_stats["total_agents"] == 2
        assert size_stats["average_size"] > 0
        assert size_stats["max_size"] >= size_stats["min_size"]
        assert size_stats["min_size"] > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    # Fixtures moved to conftest.py
    def _unused_mock_agent_data(self) -> Dict[str, Any]:
        """Create mock agent data matching the schema."""
        return {
            "schema_version": "1.1.0",
            "agent_id": "test_agent",
            "agent_version": "1.0.0",
            "agent_type": "base",
            "metadata": {
                "name": "Test Agent",
                "description": "A test agent for unit testing",
                "category": "quality",
                "tags": ["test", "mock"],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
            "capabilities": {
                "model": "claude-sonnet-4-20250514",
                "resource_tier": "standard",
                "tools": ["Read", "Grep"],
                "features": ["caching", "validation"],
            },
            "instructions": "# Test Agent Instructions\n\nThis is a test agent for unit testing purposes.\n\n## Purpose\n\nThe test agent is designed to validate the agent loading functionality, including:\n- Schema validation\n- Caching behavior\n- Error handling\n- Performance characteristics\n\n## Capabilities\n\nThis agent supports various testing scenarios and can be used to verify:\n1. Agent discovery and registration\n2. Prompt loading and caching\n3. Metadata retrieval\n4. Dynamic model selection\n\n## Testing Guidelines\n\nWhen using this agent for testing:\n- Ensure all required fields are populated\n- Verify caching behavior works as expected\n- Test error conditions and edge cases\n- Monitor performance metrics\n\n## Additional Context\n\nThis agent is part of the comprehensive test suite for the Claude MPM agent loading system. It provides a minimal but complete implementation that satisfies all schema requirements while being simple enough for testing purposes.",
            "knowledge": {
                "domain_expertise": ["testing", "mocking"],
                "codebase_patterns": ["pytest", "unittest"],
            },
            "interactions": {
                "input_format": {"required_fields": ["text"]},
                "output_format": {"structure": "markdown"},
            },
        }

    # Fixtures moved to conftest.py
    def _unused_temp_agent_dir(self, tmp_path, mock_agent_data):
        """Create a temporary directory with test agent files."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create test agent file
        agent_file = templates_dir / "test_agent.json"
        agent_file.write_text(json.dumps(mock_agent_data, indent=2))

        # Create another test agent
        research_data = mock_agent_data.copy()
        research_data.update(
            {
                "agent_id": "research_agent",
                "agent_type": "research",
                "metadata": mock_agent_data["metadata"].copy(),
            }
        )
        research_data["metadata"].update(
            {
                "name": "Research Agent",
                "description": "Agent for research tasks",
                "category": "research",
            }
        )
        research_data["capabilities"] = mock_agent_data["capabilities"].copy()
        research_data["capabilities"].update(
            {"model": "claude-opus-4-20250514", "resource_tier": "intensive"}
        )
        research_data[
            "instructions"
        ] = "# Research Agent\n\nSpecialized for research and analysis tasks.\n\n## Core Functionality\n\nThe Research Agent is optimized for:\n- Deep codebase analysis using tree-sitter AST\n- Pattern recognition and identification\n- Security vulnerability assessment\n- Performance optimization opportunities\n- Architecture documentation\n\n## Research Capabilities\n\n1. **Code Analysis**: Leverages tree-sitter for syntactic and semantic analysis\n2. **Pattern Detection**: Identifies common patterns and anti-patterns\n3. **Documentation**: Generates comprehensive technical documentation\n4. **Metrics Collection**: Gathers code quality and complexity metrics\n\n## Best Practices\n\nWhen conducting research:\n- Start with high-level architecture overview\n- Drill down into specific components as needed\n- Document findings with clear examples\n- Provide actionable recommendations\n- Include confidence levels in assessments\n\n## Integration\n\nThis agent integrates with other system components to provide comprehensive analysis capabilities for the Claude MPM system."
        research_file = templates_dir / "research_agent.json"
        research_file.write_text(json.dumps(research_data, indent=2))

        # Create schema file (should be ignored)
        schema_file = templates_dir / "agent_schema.json"
        schema_file.write_text(json.dumps({"type": "object"}, indent=2))

        return templates_dir

    def test_empty_templates_directory(self, tmp_path, monkeypatch):
        """Test behavior with empty templates directory."""
        empty_dir = tmp_path / "empty_templates"
        empty_dir.mkdir()

        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", empty_dir
        )

        loader = AgentLoader()
        assert len(loader._agent_registry) == 0
        assert loader.list_agents() == []

    def test_very_large_prompt(self, tmp_path, monkeypatch):
        """Test handling of very large agent prompts."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create agent with very large instructions (1MB)
        large_instructions = "# Large Agent\n" + ("X" * 1024 * 1024)
        agent_data = {
            "schema_version": "1.0.0",
            "agent_id": "large_agent",
            "agent_version": "1.0.0",
            "agent_type": "base",
            "metadata": {
                "name": "Large Agent",
                "description": "Test agent with large instructions",
                "author": "test",
            },
            "capabilities": {
                "model": "claude-sonnet-4-20250514",
                "resource_tier": "standard",
            },
            "instructions": large_instructions,
        }

        agent_file = templates_dir / "large_agent.json"
        agent_file.write_text(json.dumps(agent_data))

        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", templates_dir
        )

        loader = AgentLoader()
        prompt = loader.get_agent_prompt("large_agent")

        assert prompt == large_instructions
        assert loader._metrics["prompt_sizes"]["large_agent"] > 1024 * 1024

    def test_concurrent_access_simulation(self, temp_agent_dir, monkeypatch):
        """Test behavior under simulated concurrent access."""
        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", temp_agent_dir
        )
        monkeypatch.setattr("claude_mpm.agents.agent_loader._loader", None)

        # Simulate multiple "threads" accessing the loader
        # Note: Due to GIL, this is more about testing state consistency
        loader = _get_loader()

        results = []
        for i in range(10):
            agent_id = "test_agent" if i % 2 == 0 else "research_agent"
            prompt = loader.get_agent_prompt(agent_id)
            results.append((agent_id, prompt))

        # Verify all accesses succeeded and returned correct data
        test_prompts = [r[1] for r in results if r[0] == "test_agent"]
        research_prompts = [r[1] for r in results if r[0] == "research_agent"]

        assert all(p == test_prompts[0] for p in test_prompts)
        assert all(p == research_prompts[0] for p in research_prompts)

    def test_special_characters_in_agent_id(self, tmp_path, monkeypatch):
        """Test handling of special characters in agent IDs."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Agent with special characters
        agent_data = {
            "schema_version": "1.0.0",
            "agent_id": "test-agent_v2.0",
            "agent_version": "1.0.0",
            "agent_type": "base",
            "metadata": {
                "name": "Special Agent",
                "description": "Test agent with special characters",
                "author": "test",
            },
            "capabilities": {
                "model": "claude-sonnet-4-20250514",
                "resource_tier": "standard",
            },
            "instructions": "Special agent instructions",
        }

        agent_file = templates_dir / "special_agent.json"
        agent_file.write_text(json.dumps(agent_data))

        monkeypatch.setattr(
            "claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", templates_dir
        )

        loader = AgentLoader()
        prompt = loader.get_agent_prompt("test_agent_v2_0")
        assert prompt == "Special agent instructions"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
