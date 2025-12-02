#!/usr/bin/env python3
"""Test agent_loader handles both old and new JSON formats."""

import json

from claude_mpm.agents.agent_loader import load_agent_prompt_from_md


class TestAgentLoaderFormats:
    """Test agent_loader handles different JSON formats correctly."""

    def test_narrative_fields_format(self):
        """Test loading from new narrative_fields.instructions format."""
        # Create a test agent with new format
        test_agent = {
            "version": 3,
            "agent_type": "test",
            "narrative_fields": {
                "instructions": "# Test Agent\n\nThis is a test agent with narrative_fields format."
            },
            "configuration_fields": {
                "model": "claude-4-sonnet-20250514",
                "description": "Test agent",
            },
        }

        # Write to temp file
        agent_file = self / "test_agent.json"
        agent_file.write_text(json.dumps(test_agent, indent=2))

        # Mock the AGENT_MAPPINGS and AGENT_TEMPLATES_DIR
        import claude_mpm.agents.agent_loader as loader

        original_mappings = loader.AGENT_MAPPINGS
        original_dir = loader.AGENT_TEMPLATES_DIR

        try:
            loader.AGENT_MAPPINGS = {"test": "test_agent.json"}
            loader.AGENT_TEMPLATES_DIR = self

            # Load the agent
            content = load_agent_prompt_from_md("test", force_reload=True)

            assert content is not None
            assert "Test Agent" in content
            assert "narrative_fields format" in content

        finally:
            loader.AGENT_MAPPINGS = original_mappings
            loader.AGENT_TEMPLATES_DIR = original_dir

    def test_old_content_format(self):
        """Test loading from old content field format (backward compatibility)."""
        # Create a test agent with old format
        test_agent = {
            "version": 1,
            "agent_type": "test_old",
            "content": "# Test Old Agent\n\nThis is a test agent with old content format.",
            "configuration_fields": {
                "model": "claude-3-sonnet",
                "description": "Test old agent",
            },
        }

        # Write to temp file
        agent_file = self / "test_old_agent.json"
        agent_file.write_text(json.dumps(test_agent, indent=2))

        # Mock the AGENT_MAPPINGS and AGENT_TEMPLATES_DIR
        import claude_mpm.agents.agent_loader as loader

        original_mappings = loader.AGENT_MAPPINGS
        original_dir = loader.AGENT_TEMPLATES_DIR

        try:
            loader.AGENT_MAPPINGS = {"test_old": "test_old_agent.json"}
            loader.AGENT_TEMPLATES_DIR = self

            # Load the agent
            content = load_agent_prompt_from_md("test_old", force_reload=True)

            assert content is not None
            assert "Test Old Agent" in content
            assert "old content format" in content

        finally:
            loader.AGENT_MAPPINGS = original_mappings
            loader.AGENT_TEMPLATES_DIR = original_dir

    def test_instructions_field_format(self):
        """Test loading from instructions field at root level."""
        # Create a test agent with instructions at root
        test_agent = {
            "version": 2,
            "agent_type": "test_instructions",
            "instructions": "# Test Instructions Agent\n\nThis is a test agent with instructions at root.",
            "configuration_fields": {
                "model": "claude-4-sonnet",
                "description": "Test instructions agent",
            },
        }

        # Write to temp file
        agent_file = self / "test_instructions_agent.json"
        agent_file.write_text(json.dumps(test_agent, indent=2))

        # Mock the AGENT_MAPPINGS and AGENT_TEMPLATES_DIR
        import claude_mpm.agents.agent_loader as loader

        original_mappings = loader.AGENT_MAPPINGS
        original_dir = loader.AGENT_TEMPLATES_DIR

        try:
            loader.AGENT_MAPPINGS = {
                "test_instructions": "test_instructions_agent.json"
            }
            loader.AGENT_TEMPLATES_DIR = self

            # Load the agent
            content = load_agent_prompt_from_md("test_instructions", force_reload=True)

            assert content is not None
            assert "Test Instructions Agent" in content
            assert "instructions at root" in content

        finally:
            loader.AGENT_MAPPINGS = original_mappings
            loader.AGENT_TEMPLATES_DIR = original_dir

    def test_missing_content_returns_none(self):
        """Test that missing content/instructions returns None."""
        # Create a test agent with no content
        test_agent = {
            "version": 1,
            "agent_type": "test_empty",
            "configuration_fields": {
                "model": "claude-3-sonnet",
                "description": "Test empty agent",
            },
        }

        # Write to temp file
        agent_file = self / "test_empty_agent.json"
        agent_file.write_text(json.dumps(test_agent, indent=2))

        # Mock the AGENT_MAPPINGS and AGENT_TEMPLATES_DIR
        import claude_mpm.agents.agent_loader as loader

        original_mappings = loader.AGENT_MAPPINGS
        original_dir = loader.AGENT_TEMPLATES_DIR

        try:
            loader.AGENT_MAPPINGS = {"test_empty": "test_empty_agent.json"}
            loader.AGENT_TEMPLATES_DIR = self

            # Load the agent
            content = load_agent_prompt_from_md("test_empty", force_reload=True)

            assert content is None

        finally:
            loader.AGENT_MAPPINGS = original_mappings
            loader.AGENT_TEMPLATES_DIR = original_dir

    def test_real_agent_templates_load():
        """Test that all real agent templates load successfully."""
        from claude_mpm.agents.agent_loader import (
            AGENT_MAPPINGS,
            load_agent_prompt_from_md,
        )

        # Test each real agent
        for agent_name in AGENT_MAPPINGS:
            content = load_agent_prompt_from_md(agent_name, force_reload=True)
            assert content is not None, f"Failed to load {agent_name} agent"
            assert len(content) > 0, f"Empty content for {agent_name} agent"
            # Check that it's markdown content
            assert "#" in content, f"No markdown headers in {agent_name} agent content"
