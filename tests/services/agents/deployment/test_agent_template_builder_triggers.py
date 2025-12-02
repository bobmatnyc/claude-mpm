#!/usr/bin/env python3
"""
Unit tests for agent_template_builder trigger handling.
Tests both string and dict trigger formats for backward compatibility.
"""

from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.agents.deployment.agent_template_builder import (
    AgentTemplateBuilder,
)


class TestAgentTemplateBuilderTriggers:
    """Test trigger handling in AgentTemplateBuilder"""

    def setup_method(self):
        """Set up test fixtures"""
        self.builder = AgentTemplateBuilder()

    def test_dict_trigger_format(self):
        """Test handling of new dict trigger format with pattern and confidence"""
        template_data = {
            "agent_type": "imagemagick",
            "interactions": {
                "triggers": [
                    {"pattern": "optimize.*image", "confidence": 0.9},
                    {"pattern": "convert.*format", "confidence": 0.8},
                ]
            },
        }

        examples = self.builder._extract_examples_from_template(
            template_data, "imagemagick"
        )

        # Should generate examples without error
        assert len(examples) > 0
        assert "<example>" in examples
        assert "</example>" in examples

        # Should extract pattern text correctly
        example_text = " ".join(examples)
        assert "optimize.*image" in example_text
        assert "imagemagick agent" in example_text.lower()

    def test_string_trigger_format(self):
        """Test handling of legacy string trigger format"""
        template_data = {
            "agent_type": "general",
            "interactions": {
                "triggers": ["agent creation request", "PM customization needed"]
            },
        }

        examples = self.builder._extract_examples_from_template(
            template_data, "test-agent"
        )

        # Should generate examples without error
        assert len(examples) > 0
        assert "<example>" in examples
        assert "</example>" in examples

        # Should use string trigger directly
        example_text = " ".join(examples)
        assert "agent creation request" in example_text
        assert "test-agent" in example_text

    def test_empty_triggers(self):
        """Test handling of empty triggers array"""
        template_data = {"agent_type": "general", "interactions": {"triggers": []}}

        examples = self.builder._extract_examples_from_template(
            template_data, "test-agent"
        )

        # Should return empty list for empty triggers
        assert examples == []

    def test_missing_interactions(self):
        """Test handling when interactions section is missing"""
        template_data = {"agent_type": "general"}

        examples = self.builder._extract_examples_from_template(
            template_data, "test-agent"
        )

        # Should return empty list when no interactions
        assert examples == []

    def test_dict_trigger_missing_pattern(self):
        """Test handling of dict trigger with missing pattern field"""
        template_data = {
            "agent_type": "general",
            "interactions": {
                "triggers": [
                    {"confidence": 0.9},  # Missing pattern field
                ]
            },
        }

        examples = self.builder._extract_examples_from_template(
            template_data, "test-agent"
        )

        # Should handle gracefully and return empty list
        assert examples == []

    def test_mixed_trigger_formats(self):
        """Test that only first trigger is used regardless of format"""
        # Test with dict first
        template_data = {
            "agent_type": "general",
            "interactions": {
                "triggers": [
                    {"pattern": "first_pattern", "confidence": 0.9},
                    "second_string_trigger",
                ]
            },
        }

        examples = self.builder._extract_examples_from_template(
            template_data, "test-agent"
        )

        example_text = " ".join(examples)
        assert "first_pattern" in example_text
        assert "second_string_trigger" not in example_text

    def test_trigger_text_lowercase_handling(self):
        """Test that trigger text can be safely converted to lowercase"""
        template_data = {
            "agent_type": "general",
            "interactions": {
                "triggers": [{"pattern": "UPPERCASE_PATTERN", "confidence": 0.9}]
            },
        }

        examples = self.builder._extract_examples_from_template(
            template_data, "test-agent"
        )

        # Should handle .lower() without error
        example_text = " ".join(examples)
        assert "uppercase_pattern" in example_text.lower()

    def test_special_characters_in_triggers(self):
        """Test handling of special characters in trigger patterns"""
        template_data = {
            "agent_type": "general",
            "interactions": {
                "triggers": [
                    {"pattern": "optimize.*\\.(jpg|png|webp)$", "confidence": 0.9}
                ]
            },
        }

        examples = self.builder._extract_examples_from_template(
            template_data, "test-agent"
        )

        # Should handle regex patterns without error
        assert len(examples) > 0
        example_text = " ".join(examples)
        assert "optimize" in example_text

    def test_with_existing_examples(self):
        """Test that triggers are not used when examples already exist"""
        template_data = {
            "agent_type": "general",
            "knowledge": {
                "examples": [
                    {
                        "scenario": "Existing example",
                        "approach": "Existing approach",
                        "commentary": "Existing commentary",
                    }
                ]
            },
            "interactions": {
                "triggers": [{"pattern": "should_not_appear", "confidence": 0.9}]
            },
        }

        examples = self.builder._extract_examples_from_template(
            template_data, "test-agent"
        )

        # Should use knowledge examples instead of triggers
        example_text = " ".join(examples)
        assert "Existing example" in example_text
        assert "should_not_appear" not in example_text
