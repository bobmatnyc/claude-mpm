#!/usr/bin/env python3
"""
Unit Tests for Agent Instruction Loading (Simplified Version)
=============================================================

This module provides comprehensive tests for the instruction loading functionality
in the agent system, with a focus on simplicity and robustness.

WHY: These tests ensure that agent instructions are loaded correctly, cached
efficiently, and combined properly with base instructions. This is critical
for agent behavior consistency and performance.
"""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

# Test imports
from claude_mpm.agents.agent_loader import (
    AGENT_CACHE_PREFIX,
    MODEL_NAME_MAPPINGS,
    AgentLoader,
    ComplexityLevel,
    ModelType,
    _get_model_config,
    clear_agent_cache,
    get_agent_prompt,
)
from claude_mpm.agents.base_agent_loader import (
    PromptTemplate,
    _remove_test_mode_instructions,
    clear_base_agent_cache,
    prepend_base_instructions,
)
from claude_mpm.services.memory.cache.shared_prompt_cache import SharedPromptCache


class TestInstructionLoadingCore(unittest.TestCase):
    """Core tests for instruction loading functionality."""

    def setUp(self):
        """Set up test environment."""
        clear_agent_cache()
        clear_base_agent_cache()

        # Reset environment
        for key in list(os.environ.keys()):
            if key.startswith("CLAUDE_PM_"):
                del os.environ[key]

    def tearDown(self):
        """Clean up after tests."""
        clear_agent_cache()
        clear_base_agent_cache()

    def test_basic_agent_prompt_loading():
        """Test basic loading of agent prompts."""
        mock_agent = {
            "agent_id": "test_agent",
            "instructions": "Test agent instructions.",
            "capabilities": {"model": "claude-sonnet-4-20250514"},
        }

        # Mock the loader to return our test agent
        with patch.object(AgentLoader, "get_agent", return_value=mock_agent):
            # Mock base instructions to avoid file system dependencies
            with patch(
                "claude_mpm.agents.agent_loader.prepend_base_instructions",
                side_effect=lambda prompt, **kw: f"[BASE]\n{prompt}",
            ):
                result = get_agent_prompt("test_agent")

                self.assertIn("[BASE]", result)
                self.assertIn("Test agent instructions", result)

    def test_missing_agent_error():
        """Test error handling for missing agents."""
        with patch.object(AgentLoader, "get_agent", return_value=None):
            with self.assertRaises(ValueError) as ctx:
                get_agent_prompt("missing_agent")

            self.assertIn("No agent found", str(ctx.exception))

    def test_instruction_caching_behavior():
        """Test that instructions are cached properly."""
        mock_agent = {
            "agent_id": "cache_test",
            "instructions": "Cached instructions",
            "capabilities": {"model": "claude-sonnet-4-20250514"},
        }

        # Track cache operations
        cache_sets = []
        cache = SharedPromptCache.get_instance()
        original_set = cache.set

        def track_set(key, value, ttl=None):
            cache_sets.append((key, ttl))
            return original_set(key, value, ttl=ttl)

        cache.set = track_set

        try:
            with patch.object(AgentLoader, "get_agent", return_value=mock_agent):
                loader = AgentLoader()

                # First call should cache
                prompt1 = loader.get_agent_prompt("cache_test")

                # Verify cache was set with correct TTL
                cache_key = f"{AGENT_CACHE_PREFIX}cache_test"
                self.assertTrue(
                    any(k == cache_key and ttl == 3600 for k, ttl in cache_sets)
                )

                # Second call should use cache (no new set)
                cache_sets.clear()
                prompt2 = loader.get_agent_prompt("cache_test")

                self.assertEqual(prompt1, prompt2)
                self.assertFalse(any(k == cache_key for k, _ in cache_sets))

        finally:
            cache.set = original_set

    def test_force_reload_functionality():
        """Test that force_reload bypasses cache."""
        mock_agent = {
            "agent_id": "reload_test",
            "instructions": "Original",
            "capabilities": {"model": "claude-sonnet-4-20250514"},
        }

        loader = AgentLoader()

        with patch.object(loader, "get_agent", return_value=mock_agent):
            # Initial load
            prompt1 = loader.get_agent_prompt("reload_test")
            self.assertIn("Original", prompt1)

            # Update mock
            mock_agent["instructions"] = "Updated"

            # Without force_reload - should get cached
            prompt2 = loader.get_agent_prompt("reload_test")
            self.assertIn("Original", prompt2)

            # With force_reload - should get updated
            prompt3 = loader.get_agent_prompt("reload_test", force_reload=True)
            self.assertIn("Updated", prompt3)

    def test_special_characters_handling():
        """Test handling of Unicode and special characters."""
        test_cases = [
            "Unicode: 你好 🌍 Привет",
            "Newlines:\nand\ttabs",
            "Quotes: 'single' and \"double\"",
            "Math: ∑ ∞ ≤ ≥",
            "Symbols: $ € £ → ←",
        ]

        for idx, instructions in enumerate(test_cases):
            mock_agent = {
                "agent_id": f"special_{idx}",
                "instructions": instructions,
                "capabilities": {"model": "claude-sonnet-4-20250514"},
            }

            with patch.object(AgentLoader, "get_agent", return_value=mock_agent):
                with patch(
                    "claude_mpm.agents.agent_loader.prepend_base_instructions",
                    side_effect=lambda p, **kw: p,
                ):
                    prompt = get_agent_prompt(f"special_{idx}")
                    self.assertEqual(instructions, prompt)

    def test_empty_instructions_handling():
        """Test handling of empty or missing instructions."""
        test_cases = [
            ({}, None),  # Missing instructions
            ({"instructions": ""}, None),  # Empty string
            ({"instructions": "   "}, "   "),  # Whitespace only - returns as-is
        ]

        loader = AgentLoader()

        for agent_data, expected in test_cases:
            agent_data.update(
                {
                    "agent_id": "empty_test",
                    "capabilities": {"model": "claude-sonnet-4-20250514"},
                }
            )

            with patch.object(loader, "get_agent", return_value=agent_data):
                result = loader.get_agent_prompt("empty_test")
                self.assertEqual(result, expected)

    def test_model_selection_basic():
        """Test basic model selection functionality."""
        mock_agent = {
            "agent_id": "model_test",
            "instructions": "Test",
            "capabilities": {"model": "claude-opus-4-20250514"},
        }

        with patch.object(AgentLoader, "get_agent", return_value=mock_agent):
            # Without complexity analysis - should use agent default
            model, config = _get_model_config("model_test")

            self.assertEqual(model, "claude-opus-4-20250514")
            self.assertEqual(config["selection_method"], "agent_default")

    def test_model_selection_with_complexity():
        """Test dynamic model selection based on complexity."""
        mock_agent = {
            "agent_id": "complex_test",
            "instructions": "Test",
            "capabilities": {"model": "claude-sonnet-4-20250514"},
        }

        complexity_analysis = {
            "complexity_score": 85,
            "complexity_level": ComplexityLevel.HIGH,
            "recommended_model": ModelType.OPUS,
        }

        with patch.object(AgentLoader, "get_agent", return_value=mock_agent):
            model, config = _get_model_config("complex_test", complexity_analysis)

            self.assertEqual(model, MODEL_NAME_MAPPINGS[ModelType.OPUS])
            self.assertEqual(config["selection_method"], "dynamic_complexity_based")
            self.assertEqual(config["complexity_score"], 85)

    def test_environment_variable_overrides():
        """Test environment variable model selection overrides."""
        mock_agent = {
            "agent_id": "env_test",
            "instructions": "Test",
            "capabilities": {"model": "claude-sonnet-4-20250514"},
        }

        complexity = {"recommended_model": ModelType.OPUS, "complexity_score": 90}

        # Test global disable
        os.environ["ENABLE_DYNAMIC_MODEL_SELECTION"] = "false"

        with patch.object(AgentLoader, "get_agent", return_value=mock_agent):
            model, config = _get_model_config("env_test", complexity)

            self.assertEqual(model, "claude-sonnet-4-20250514")
            self.assertEqual(config["reason"], "dynamic_selection_disabled")

        # Test per-agent override
        del os.environ["ENABLE_DYNAMIC_MODEL_SELECTION"]
        os.environ["CLAUDE_PM_ENV_TEST_MODEL_SELECTION"] = "false"

        with patch.object(AgentLoader, "get_agent", return_value=mock_agent):
            model, config = _get_model_config("env_test", complexity)

            self.assertEqual(model, "claude-sonnet-4-20250514")
            self.assertEqual(config["selection_method"], "agent_default")

    def test_template_selection_by_complexity():
        """Test automatic template selection based on complexity."""
        test_cases = [
            (10, PromptTemplate.MINIMAL),
            (50, PromptTemplate.STANDARD),
            (90, PromptTemplate.FULL),
        ]

        for score, expected_template in test_cases:
            # Mock to verify template selection
            with patch(
                "claude_mpm.agents.base_agent_loader._build_dynamic_prompt"
            ) as mock_build:
                mock_build.return_value = f"Template: {expected_template.value}"

                with patch(
                    "claude_mpm.agents.base_agent_loader.load_base_agent_instructions",
                    return_value="Base content",
                ):
                    prepend_base_instructions("Agent prompt", complexity_score=score)

                    # Verify the right template was selected
                    args = mock_build.call_args[0]
                    self.assertEqual(args[1], expected_template)

    def test_test_mode_instruction_removal():
        """Test removal of test-specific instructions."""
        content = """# Instructions

## Core Content
Always included.

## Standard Test Response Protocol
Remove this section.
And this line too.

### Test Subsection
Also remove this.

## Regular Content
Keep this."""

        result = _remove_test_mode_instructions(content)

        # Test protocol should be removed
        self.assertNotIn("Standard Test Response Protocol", result)
        self.assertNotIn("Remove this section", result)

        # Regular content should remain
        self.assertIn("Core Content", result)
        self.assertIn("Regular Content", result)

    def test_legacy_function_compatibility():
        """Test backward compatibility functions."""
        # NOTE: Legacy functions were removed, using get_agent_prompt instead
        from claude_mpm.agents.agent_loader import get_agent_prompt

        # Mock the missing legacy functions
        def get_documentation_agent_prompt(*args, **kwargs):
            return get_agent_prompt("documentation", *args, **kwargs)

        def get_qa_agent_prompt(*args, **kwargs):
            return get_agent_prompt("qa", *args, **kwargs)

        agents = {
            "documentation_agent": "Doc instructions",
            "qa_agent": "QA instructions",
        }

        for agent_id, instructions in agents.items():
            mock_agent = {
                "agent_id": agent_id,
                "instructions": instructions,
                "capabilities": {"model": "claude-sonnet-4-20250514"},
            }

            with patch.object(AgentLoader, "get_agent", return_value=mock_agent):
                with patch(
                    "claude_mpm.agents.agent_loader.prepend_base_instructions",
                    side_effect=lambda p, **kw: f"[BASE] {p}",
                ):
                    if agent_id == "documentation_agent":
                        result = get_agent_prompt("documentation")
                    else:
                        result = get_agent_prompt("qa")

                    self.assertIn(instructions, result)
                    self.assertIn("[BASE]", result)

    def test_cache_invalidation():
        """Test cache clearing functionality."""
        mock_agent = {
            "agent_id": "clear_test",
            "instructions": "Original",
            "capabilities": {"model": "claude-sonnet-4-20250514"},
        }

        loader = AgentLoader()

        with patch.object(loader, "get_agent", return_value=mock_agent):
            # Load and cache
            prompt1 = loader.get_agent_prompt("clear_test")

            # Update content
            mock_agent["instructions"] = "Updated"

            # Clear cache
            clear_agent_cache("clear_test")

            # Should get updated content
            prompt2 = loader.get_agent_prompt("clear_test")

            self.assertNotEqual(prompt1, prompt2)
            self.assertIn("Updated", prompt2)

    def test_agent_file_validation():
        """Test handling of invalid agent files."""
        with tmp_path as tmpdir:
            tmp_path = Path(tmpdir)

            # Create invalid JSON
            bad_file = tmp_path / "bad_agent.json"
            bad_file.write_text('{"agent_id": "test"')  # Missing closing brace

            # Create schema file to avoid warnings
            (tmp_path / "agent_schema.json").write_text("{}")

            with patch("claude_mpm.agents.agent_loader.AGENT_TEMPLATES_DIR", tmp_path):
                # Should not crash
                loader = AgentLoader()

                # Bad agent should not be loaded
                self.assertIsNone(loader.get_agent("test"))

    def test_return_model_info_format():
        """Test the return_model_info parameter."""
        mock_agent = {
            "agent_id": "format_test",
            "instructions": "Test",
            "capabilities": {"model": "claude-sonnet-4-20250514"},
        }

        with patch.object(AgentLoader, "get_agent", return_value=mock_agent):
            with patch(
                "claude_mpm.agents.agent_loader.prepend_base_instructions",
                side_effect=lambda p, **kw: f"[BASE] {p}",
            ):
                # Without model info
                result1 = get_agent_prompt("format_test", return_model_info=False)
                self.assertIsInstance(result1, str)

                # With model info
                result2 = get_agent_prompt("format_test", return_model_info=True)
                self.assertIsInstance(result2, tuple)
                self.assertEqual(len(result2), 3)

                prompt, model, config = result2
                self.assertIsInstance(prompt, str)
                self.assertIsInstance(model, str)
                self.assertIsInstance(config, dict)


if __name__ == "__main__":
    unittest.main()
