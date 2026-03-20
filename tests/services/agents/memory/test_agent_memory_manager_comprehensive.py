#!/usr/bin/env python3

"""
Comprehensive unit tests for AgentMemoryManager.

This test suite ensures safe refactoring by testing all methods and edge cases
in the AgentMemoryManager class.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestAgentMemoryManager:
    """Comprehensive test suite for AgentMemoryManager."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock Config object."""
        config = MagicMock()
        config.get.side_effect = lambda key, default=None: {
            "memory.enabled": True,
            "memory.auto_learning": True,
            "memory.limits": {
                "default_size_kb": 80,
                "max_items": 100,
                "max_line_length": 120,
            },
            "memory.agent_overrides": {
                "research": {"size_kb": 160, "auto_learning": False},
                "pm": {"auto_learning": True},
            },
        }.get(key, default)
        return config

    @pytest.fixture
    def mock_path_manager(self):
        """Create a mock PathManager."""
        with patch(
            "claude_mpm.services.agents.memory.agent_memory_manager.get_path_manager"
        ) as mock:
            mock_pm = MagicMock()
            mock_pm.project_root = Path("/project/root")
            mock.return_value = mock_pm
            yield mock

    @pytest.fixture
    def mock_content_manager(self):
        """Create a mock MemoryContentManager."""
        with patch(
            "claude_mpm.services.agents.memory.agent_memory_manager.MemoryContentManager"
        ) as mock:
            instance = MagicMock()
            instance.exceeds_limits.return_value = False
            instance.validate_and_repair.side_effect = lambda content, agent_id: content
            instance.truncate_simple_list.side_effect = lambda content, limits: content
            instance.validate_memory_size.return_value = (True, None)
            mock.return_value = instance
            yield instance

    @pytest.fixture
    def mock_template_generator(self):
        """Create a mock MemoryTemplateGenerator."""
        with patch(
            "claude_mpm.services.agents.memory.agent_memory_manager.MemoryTemplateGenerator"
        ) as mock:
            instance = MagicMock()
            instance.create_default_memory.return_value = "# Default Memory Template"
            mock.return_value = instance
            yield instance

    @pytest.fixture
    def manager(
        self,
        mock_config,
        mock_path_manager,
        mock_content_manager,
        mock_template_generator,
    ):
        """Create an AgentMemoryManager instance with mocked dependencies."""
        from claude_mpm.services.agents.memory.agent_memory_manager import (
            AgentMemoryManager,
        )

        working_dir = Path("/test/working")
        return AgentMemoryManager(config=mock_config, working_directory=working_dir)

    # ================================================================================
    # Memory File Operations Tests
    # ================================================================================

    def test_get_memory_file_with_migration_no_existing_files(self, manager):
        """Test getting memory file path when no files exist.

        normalize_agent_id("test_agent") -> "test" because:
        test_agent -> test-agent (underscores to dashes) -> test (strip -agent suffix)
        So the canonical filename is test_memories.md.
        """
        directory = Path("/test/memories")
        agent_id = "test_agent"

        with patch.object(Path, "exists", return_value=False):
            result = manager.file_service.get_memory_file_with_migration(
                directory, agent_id
            )

        # normalize_agent_id("test_agent") = "test" (underscore->dash then strip -agent)
        assert result == directory / "test_memories.md"

    def test_get_memory_file_with_migration_from_old_agent_format(self, manager):
        """Test migrating from old underscore format to canonical kebab-case.

        normalize_agent_id("test_agent") = "test" so canonical = test_memories.md.
        The legacy file test_agent_memories.md should be migrated to test_memories.md.
        """
        directory = Path("/test/memories")
        agent_id = "test_agent"

        canonical_file = directory / "test_memories.md"

        # Sequence: canonical.exists()=False (skip early return),
        #           legacy_underscore.exists()=True (triggers migration)
        with patch("pathlib.Path.exists", side_effect=[False, True]):
            with patch("pathlib.Path.rename") as mock_rename:
                result = manager.file_service.get_memory_file_with_migration(
                    directory, agent_id
                )

        mock_rename.assert_called_once_with(canonical_file)
        assert result == canonical_file

    def test_get_memory_file_with_migration_from_simple_format(self, manager):
        """Test migration when underscore rename fails falls back to old file.

        normalize_agent_id("test_agent") = "test", canonical = test_memories.md.
        Legacy underscore file = test_agent_memories.md.
        When canonical doesn't exist and legacy exists but rename fails,
        should fall back to the legacy file.
        """
        directory = Path("/test/memories")
        agent_id = "test_agent"

        legacy_file = directory / "test_agent_memories.md"

        # Sequence: canonical.exists()=False, legacy_underscore.exists()=True
        # Then rename raises OSError -> falls back to legacy file
        with patch("pathlib.Path.exists", side_effect=[False, True]):
            with patch("pathlib.Path.rename", side_effect=OSError("Cannot rename")):
                result = manager.file_service.get_memory_file_with_migration(
                    directory, agent_id
                )

        # Falls back to legacy file when rename fails
        assert result == legacy_file

    def test_get_memory_file_migration_error_handling(self, manager):
        """Test getting memory file when no old format exists.

        normalize_agent_id("test_agent") = "test", so canonical = test_memories.md.
        When nothing exists, returns the canonical path.
        """
        directory = Path("/test/memories")
        agent_id = "test_agent"

        canonical_file = directory / "test_memories.md"

        with patch.object(Path, "exists", return_value=False):
            result = manager.file_service.get_memory_file_with_migration(
                directory, agent_id
            )

        # Returns canonical path when no old format found
        assert result == canonical_file

    def test_save_memory_file_success(self, manager):
        """Test successful memory file save via file_service."""
        content = "Test memory content"
        file_path = Path("/test/memories/test_agent_memories.md")

        with patch.object(Path, "mkdir") as mock_mkdir:
            with patch.object(Path, "write_text") as mock_write:
                result = manager.file_service.save_memory_file(file_path, content)

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_write.assert_called_once_with(content)
        assert result is True

    def test_save_memory_file_error(self, manager):
        """Test error handling during save via file_service."""
        content = "Test memory content"
        file_path = Path("/test/memories/test_agent_memories.md")

        with patch.object(Path, "mkdir"):
            with patch.object(Path, "write_text", side_effect=OSError("Write error")):
                result = manager.file_service.save_memory_file(file_path, content)

        assert result is False

    def test_ensure_memories_directory_creates_readme(self, manager):
        """Test that README is created in memories directory."""
        with patch.object(Path, "mkdir") as mock_mkdir:
            with patch.object(Path, "exists", return_value=False):
                with patch.object(Path, "write_text") as mock_write:
                    manager.file_service.ensure_memories_directory()

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_write.assert_called_once()

        # Check README content (new format)
        call_args = mock_write.call_args[0][0]
        assert "# Agent Memories Directory" in call_args
        assert "## File Format" in call_args

    def test_ensure_memories_directory_existing_readme(self, manager):
        """Test that README is not recreated if it exists."""
        with patch.object(Path, "mkdir"):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "write_text") as mock_write:
                    manager.file_service.ensure_memories_directory()

        mock_write.assert_not_called()

    # ================================================================================
    # Memory Response Processing Tests
    # ================================================================================

    def test_extract_and_update_memory_with_remember_field(self, manager):
        """Test extracting memories from JSON with 'remember' field."""
        agent_id = "test_agent"
        response = """
        Some response text
        ```json
        {
            "remember": ["Learning 1", "Learning 2", "Learning 3"]
        }
        ```
        """

        with patch.object(
            manager, "_add_learnings_to_memory", return_value=True
        ) as mock_add:
            result = manager.extract_and_update_memory(agent_id, response)

        mock_add.assert_called_once_with(
            agent_id, ["Learning 1", "Learning 2", "Learning 3"]
        )
        assert result is True

    def test_extract_and_update_memory_with_Remember_field(self, manager):
        """Test extracting memories from JSON with 'Remember' field."""
        agent_id = "test_agent"
        response = """
        ```json
        {
            "Remember": ["Memory A", "Memory B"]
        }
        ```
        """

        with patch.object(
            manager, "_add_learnings_to_memory", return_value=True
        ) as mock_add:
            result = manager.extract_and_update_memory(agent_id, response)

        mock_add.assert_called_once_with(agent_id, ["Memory A", "Memory B"])
        assert result is True

    def test_extract_and_update_memory_with_MEMORIES_field(self, manager):
        """Test replacing all memories with 'MEMORIES' field."""
        agent_id = "test_agent"
        response = """
        ```json
        {
            "MEMORIES": ["- New memory 1", "New memory 2", "- New memory 3"]
        }
        ```
        """

        with patch.object(
            manager, "replace_agent_memory", return_value=True
        ) as mock_replace:
            result = manager.extract_and_update_memory(agent_id, response)

        expected_memories = ["- New memory 1", "- New memory 2", "- New memory 3"]
        mock_replace.assert_called_once_with(agent_id, expected_memories)
        assert result is True

    def test_extract_and_update_memory_malformed_json(self, manager):
        """Test handling malformed JSON in response."""
        agent_id = "test_agent"
        response = """
        ```json
        {
            "remember": ["Memory 1",
            invalid json here
        }
        ```
        """

        with patch.object(manager, "_add_learnings_to_memory") as mock_add:
            result = manager.extract_and_update_memory(agent_id, response)

        mock_add.assert_not_called()
        assert result is False

    def test_extract_and_update_memory_no_json_block(self, manager):
        """Test when response has no JSON block."""
        agent_id = "test_agent"
        response = "Just plain text response without JSON"

        result = manager.extract_and_update_memory(agent_id, response)
        assert result is False

    def test_extract_and_update_memory_empty_remember_list(self, manager):
        """Test handling empty remember list."""
        agent_id = "test_agent"
        response = """
        ```json
        {
            "remember": []
        }
        ```
        """

        with patch.object(manager, "_add_learnings_to_memory") as mock_add:
            result = manager.extract_and_update_memory(agent_id, response)

        mock_add.assert_not_called()
        assert result is False

    def test_extract_and_update_memory_null_remember(self, manager):
        """Test handling null remember field."""
        agent_id = "test_agent"
        response = """
        ```json
        {
            "remember": null
        }
        ```
        """

        with patch.object(manager, "_add_learnings_to_memory") as mock_add:
            result = manager.extract_and_update_memory(agent_id, response)

        mock_add.assert_not_called()
        assert result is False

    def test_extract_and_update_memory_filters_empty_strings(self, manager):
        """Test that empty strings and None values are filtered out."""
        agent_id = "test_agent"
        response = """
        ```json
        {
            "remember": ["Valid memory", "", "   ", "Another valid", null]
        }
        ```
        """

        with patch.object(
            manager, "_add_learnings_to_memory", return_value=True
        ) as mock_add:
            result = manager.extract_and_update_memory(agent_id, response)

        mock_add.assert_called_once_with(agent_id, ["Valid memory", "Another valid"])
        assert result is True

    # ================================================================================
    # Memory Categorization Tests
    # ================================================================================

    def test_categorize_learning_architecture_keywords(self, manager):
        """Test categorization for architecture-related learnings."""
        learnings = [
            "The system uses microservices architecture",
            "Module structure follows MVC pattern",
            "Service-oriented design is implemented",
        ]

        for learning in learnings:
            category = manager.categorization_service.categorize_learning(learning)
            assert category == "Project Architecture"

    def test_categorize_learning_integration_keywords(self, manager):
        """Test categorization for context/integration-related learnings."""
        learnings = [
            "Current environment configuration needs updating",
            "Library dependency version is 3.2.0",
            "Deployment infrastructure uses Kubernetes",
        ]

        for learning in learnings:
            category = manager.categorization_service.categorize_learning(learning)
            assert category == "Current Technical Context"

    def test_categorize_learning_mistake_keywords(self, manager):
        """Test categorization for mistake-related learnings."""
        learnings = [
            "Never skip error handling in async calls",
            "Avoid the bug by validating inputs",
            "Don't ignore caution about wrong assumptions",
        ]

        for learning in learnings:
            category = manager.categorization_service.categorize_learning(learning)
            assert category == "Common Mistakes to Avoid"

    def test_categorize_learning_guideline_keywords(self, manager):
        """Test categorization for guideline-related learnings."""
        learnings = [
            "Each function requires proper error handling",
            "Code review follows these conventions",
            "Class implementation uses standard practice",
        ]

        for learning in learnings:
            category = manager.categorization_service.categorize_learning(learning)
            assert category == "Implementation Guidelines"

    def test_categorize_learning_default_category(self, manager):
        """Test default categorization for unmatched learnings."""
        learning = "Something that does not match any specific keyword xyz"
        category = manager.categorization_service.categorize_learning(learning)
        assert category == "Current Technical Context"

    # ================================================================================
    # Memory Limits Tests
    # ================================================================================

    def test_init_memory_limits_from_config(self, manager):
        """Test memory limits initialization from configuration."""
        # memory_limits is delegated from limits_service
        assert manager.memory_limits["max_file_size_kb"] == 80
        assert manager.memory_limits["max_items"] == 100
        assert manager.memory_limits["max_line_length"] == 120

    def test_get_agent_limits_with_overrides(self, manager):
        """Test getting agent-specific limits with overrides via limits_service."""
        # Test agent without overrides (overrides require config.agents attribute)
        limits = manager.limits_service.get_agent_limits("engineer")
        assert limits["max_file_size_kb"] == 80  # Default
        assert limits["max_items"] == 100  # Default

        # Limits service uses self.memory_limits as base
        limits = manager.limits_service.get_agent_limits("research")
        assert limits["max_file_size_kb"] == 80  # Default (no config.agents override)
        assert limits["max_items"] == 100  # Default

    def test_get_agent_auto_learning_with_override(self, manager):
        """Test getting agent-specific auto-learning settings via limits_service."""
        # Set agent_auto_learning on the mock config so limits_service can read it
        manager.limits_service.config.agent_auto_learning = True
        assert manager.limits_service.get_agent_auto_learning("engineer") is True
        assert manager.limits_service.get_agent_auto_learning("pm") is True
        assert manager.limits_service.get_agent_auto_learning("research") is True

    # ================================================================================
    # Memory Formatting Tests
    # ================================================================================

    def test_build_simple_memory_content(self, manager):
        """Test building simple memory content."""
        agent_id = "test_agent"
        items = [
            "- Learning 1",
            "- Learning 2",
            "Learning 3",
        ]  # Mix with and without bullet

        content = manager.format_service.build_simple_memory_content(agent_id, items)

        # New format: "# {Title} Agent Memory\n\nLast Updated: ..."
        assert "Agent Memory" in content
        assert "Last Updated:" in content
        assert "## Learnings" in content
        assert "Learning 1" in content
        assert "Learning 2" in content
        assert "Learning 3" in content

    def test_parse_memory_list(self, manager):
        """Test parsing memory content into list."""
        memory_content = """
        # Agent Memory: test_agent
        <!-- Last Updated: 2024-01-01T10:00:00Z -->

        - Item 1
        - Item 2
        Item 3
        ## Some Section
        - Item 4
        """

        items = manager.format_service.parse_memory_list(memory_content)
        # Items returned without bullet prefix
        assert "Item 1" in items
        assert "Item 2" in items
        assert "Item 3" in items
        assert "Item 4" in items

    def test_parse_memory_sections(self, manager):
        """Test parsing memory content into sections."""
        memory_content = """# Agent Memory: test_agent
<!-- Last Updated: 2024-01-01T10:00:00Z -->

## Project Architecture
- Architecture item 1
- Architecture item 2

## Implementation Guidelines
- Guideline 1
- Guideline 2

## Recent Learnings
- Recent item 1"""

        sections = manager.format_service.parse_memory_sections(memory_content)

        assert "Project Architecture" in sections
        assert len(sections["Project Architecture"]) == 2
        assert (
            "Architecture item 1" in sections["Project Architecture"]
        )  # No bullet prefix

        assert "Implementation Guidelines" in sections
        assert len(sections["Implementation Guidelines"]) == 2

        assert "Recent Learnings" in sections
        assert len(sections["Recent Learnings"]) == 1

    def test_clean_template_placeholders(self, manager):
        """Test clean_template_placeholders_list returns items unchanged."""
        items = [
            "- Real learning 1",
            "- Real learning 2",
        ]

        cleaned = manager.format_service.clean_template_placeholders_list(items)

        assert len(cleaned) == 2
        assert "- Real learning 1" in cleaned
        assert "- Real learning 2" in cleaned

    # ================================================================================
    # Core Operations Tests
    # ================================================================================

    def test_load_memory_existing_file(self, manager):
        """Test loading existing memory file."""
        agent_id = "test_agent"
        memory_content = "# Existing memory content"

        with patch.object(
            manager.file_service, "get_memory_file_with_migration"
        ) as mock_get_file:
            mock_file = MagicMock()
            mock_file.exists.return_value = True
            mock_file.read_text.return_value = memory_content
            mock_get_file.return_value = mock_file

            result = manager.load_agent_memory(agent_id)

        assert result == memory_content

    def test_load_memory_create_default(self, manager):
        """Test creating default memory when file doesn't exist."""
        agent_id = "test_agent"
        default_content = "# Default Memory Template"

        with patch.object(
            manager.file_service, "get_memory_file_with_migration"
        ) as mock_get_file:
            mock_file = MagicMock()
            mock_file.exists.return_value = False
            mock_get_file.return_value = mock_file

            with patch.object(
                manager, "_create_default_memory", return_value=default_content
            ):
                result = manager.load_agent_memory(agent_id)

        assert result == default_content

    def test_save_memory_interface_method(self, manager):
        """Test save_memory interface adapter method."""
        agent_id = "test_agent"
        content = "Test content"

        with patch.object(Path, "write_text") as mock_write:
            result = manager.save_memory(agent_id, content)

        mock_write.assert_called_once_with(content, encoding="utf-8")
        assert result is True

    def test_add_learning_with_deduplication(self, manager):
        """Test adding learning with duplicate detection."""
        agent_id = "test_agent"
        existing_memory = """
        # Agent Memory: test_agent
        <!-- Last Updated: 2024-01-01T10:00:00Z -->

        - Existing learning 1
        - Existing learning 2
        """

        with patch.object(manager, "load_agent_memory", return_value=existing_memory):
            with patch.object(
                manager, "_save_memory_file_wrapper", return_value=True
            ) as mock_save:
                # Try to add duplicate (case-insensitive)
                result = manager.add_learning(agent_id, "EXISTING LEARNING 1")

                # Should not save since it's a duplicate
                mock_save.assert_not_called()
                assert result is True  # Not an error, just nothing to add

                # Add new learning
                result = manager.add_learning(agent_id, "New learning")
                mock_save.assert_called_once()
                assert result is True

    def test_clear_memory(self, manager):
        """Test clearing memory (through replace with empty list)."""
        agent_id = "test_agent"

        with patch.object(
            manager, "_save_memory_file_wrapper", return_value=True
        ) as mock_save:
            manager.replace_agent_memory(agent_id, [])

        mock_save.assert_called_once()
        # Check that empty list generates minimal content (new format)
        saved_content = mock_save.call_args[0][1]
        assert "Agent Memory" in saved_content
        assert "Last Updated:" in saved_content

    # ================================================================================
    # Metrics & Status Tests
    # ================================================================================

    def test_get_memory_status(self, manager):
        """Test getting memory system status."""
        # Create mock memory files
        mock_files = [
            MagicMock(name="pm_memories.md", stem="pm_memories"),
            MagicMock(name="research_memories.md", stem="research_memories"),
        ]

        for i, mock_file in enumerate(mock_files):
            mock_file.stat.return_value.st_size = (i + 1) * 1024  # 1KB, 2KB

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "glob", return_value=mock_files):
                status = manager.get_memory_status()

        assert status["system_enabled"] is True
        assert status["auto_learning"] is True
        assert status["total_agents"] == 2
        assert status["total_size_kb"] == 3.0  # 1KB + 2KB
        assert "pm" in status["agents"]
        assert "research" in status["agents"]

    def test_get_memory_metrics_all_agents(self, manager):
        """Test getting metrics for all agents."""
        mock_files = [
            MagicMock(name="pm_memories.md", stem="pm_memories"),
            MagicMock(name="research_memories.md", stem="research_memories"),
        ]

        mock_files[0].stat.return_value.st_size = 40 * 1024  # 40KB
        mock_files[1].stat.return_value.st_size = 80 * 1024  # 80KB

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "glob", return_value=mock_files):
                metrics = manager.get_memory_metrics()

        assert metrics["agent_count"] == 2
        assert metrics["total_memory_kb"] == 120.0
        assert metrics["agents"]["pm"]["size_kb"] == 40.0
        assert (
            metrics["agents"]["pm"]["usage_percent"] == 50.0
        )  # 40KB of 80KB default limit
        assert metrics["agents"]["research"]["size_kb"] == 80.0
        assert (
            metrics["agents"]["research"]["usage_percent"] == 100.0
        )  # 80KB of 80KB default limit (no override via config.agents)

    def test_get_memory_metrics_specific_agent(self, manager):
        """Test getting metrics for specific agent."""
        agent_id = "pm"

        # Replace memories_dir with a MagicMock to allow / operator mocking
        mock_memories_dir = MagicMock()
        mock_file = MagicMock()
        mock_file.stat.return_value.st_size = 40 * 1024  # 40KB
        mock_file.exists.return_value = True
        mock_file.name = "pm_memories.md"
        mock_memories_dir.exists.return_value = True
        mock_memories_dir.__truediv__ = MagicMock(return_value=mock_file)

        manager.memories_dir = mock_memories_dir
        metrics = manager.get_memory_metrics(agent_id)

        assert metrics["agent_count"] == 1
        assert metrics["total_memory_kb"] == 40.0
        assert metrics["agents"]["pm"]["size_kb"] == 40.0
        assert metrics["agents"]["pm"]["limit_kb"] == 80
        assert metrics["agents"]["pm"]["usage_percent"] == 50.0

    # ================================================================================
    # Error Handling Tests
    # ================================================================================

    def test_load_memory_read_error(self, manager):
        """Test error handling when reading memory file fails."""
        agent_id = "test_agent"

        with patch.object(
            manager.file_service, "get_memory_file_with_migration"
        ) as mock_get_file:
            mock_file = MagicMock()
            mock_file.exists.return_value = True
            mock_file.read_text.side_effect = OSError("Read error")
            mock_get_file.return_value = mock_file

            with patch.object(
                manager, "_create_default_memory", return_value="Default"
            ) as mock_create:
                result = manager.load_agent_memory(agent_id)

        mock_create.assert_called_once()
        assert result == "Default"

    def test_save_memory_permission_error(self, manager):
        """Test handling permission errors during save via file_service."""
        content = "Test content"
        file_path = Path("/test/memories/test_agent_memories.md")

        with (
            patch.object(Path, "mkdir"),
            patch.object(
                Path, "write_text", side_effect=PermissionError("No permission")
            ),
        ):
            result = manager.file_service.save_memory_file(file_path, content)

        assert result is False

    def test_extract_memory_exception_handling(self, manager):
        """Test exception handling in extract_and_update_memory."""
        agent_id = "test_agent"
        response = "Some response"

        # Patch re module at the import level
        import re

        with patch.object(re, "findall", side_effect=Exception("Regex error")):
            result = manager.extract_and_update_memory(agent_id, response)

        assert result is False

    def test_ensure_directory_error_handling(self, manager):
        """Test error handling in ensure_memories_directory."""
        with patch.object(
            Path, "mkdir", side_effect=OSError("Cannot create directory")
        ):
            # Should not raise, just log error
            manager.file_service.ensure_memories_directory()

    def test_invalid_json_in_response(self, manager):
        """Test handling various invalid JSON formats."""
        agent_id = "test_agent"

        invalid_responses = [
            '```json\n{"remember": }\n```',  # Invalid syntax
            '```json\n{"remember": [1, 2, 3]}\n```',  # Non-string items
            '```json\n{"remember": "not a list"}\n```',  # Wrong type
        ]

        for response in invalid_responses:
            with patch.object(manager, "_add_learnings_to_memory") as mock_add:
                manager.extract_and_update_memory(agent_id, response)
                mock_add.assert_not_called()

    # ================================================================================
    # Configuration Error Tests
    # ================================================================================

    def test_config_missing_values(self):
        """Test handling missing configuration values."""
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key, default=None: (
            default
        )  # Return default for all config keys

        with patch(
            "claude_mpm.services.agents.memory.agent_memory_manager.get_path_manager"
        ):
            with patch(
                "claude_mpm.services.agents.memory.agent_memory_manager.MemoryContentManager"
            ):
                with patch(
                    "claude_mpm.services.agents.memory.agent_memory_manager.MemoryTemplateGenerator"
                ):
                    from claude_mpm.services.agents.memory.agent_memory_manager import (
                        AgentMemoryManager,
                    )

                    manager = AgentMemoryManager(config=mock_config)

                    # Should use defaults
                    assert manager.memory_limits["max_file_size_kb"] == 80
                    assert manager.memory_limits["max_items"] == 100
                    assert manager.memory_limits["max_line_length"] == 120

    # ================================================================================
    # Integration with Content Manager Tests
    # ================================================================================

    def test_memory_truncation_when_exceeds_limits(self, manager):
        """Test that memory is truncated when it exceeds limits."""
        agent_id = "test_agent"
        truncated_content = "truncated content"

        # Mock content manager to trigger truncation
        manager.content_manager.exceeds_limits.return_value = True
        manager.content_manager.truncate_simple_list.side_effect = (
            lambda content, limits: truncated_content
        )

        with patch.object(
            manager, "_save_memory_file_wrapper", return_value=True
        ) as mock_save:
            manager.replace_agent_memory(agent_id, ["Item 1", "Item 2"])

        # Should save truncated content
        saved_content = mock_save.call_args[0][1]
        assert saved_content == truncated_content

    def test_memory_validation_and_repair(self, manager):
        """Test that loaded memory is validated and repaired."""
        agent_id = "test_agent"
        corrupted_memory = "Corrupted memory content"
        repaired_memory = "Repaired memory content"

        # Configure the mock to return repaired memory
        manager.content_manager.validate_and_repair.side_effect = (
            lambda content, agent: repaired_memory
        )

        with patch.object(
            manager.file_service, "get_memory_file_with_migration"
        ) as mock_get_file:
            mock_file = MagicMock()
            mock_file.exists.return_value = True
            mock_file.read_text.return_value = corrupted_memory
            mock_get_file.return_value = mock_file

            result = manager.load_agent_memory(agent_id)

        manager.content_manager.validate_and_repair.assert_called_once_with(
            corrupted_memory, agent_id
        )
        assert result == repaired_memory

    # ================================================================================
    # Additional Edge Cases
    # ================================================================================

    def test_update_memory_with_none_items(self, manager):
        """Test handling None values in memory items."""
        agent_id = "test_agent"
        items = ["Valid item", None, "", "Another valid"]

        with patch.object(manager, "load_agent_memory", return_value="# Memory"):
            with patch.object(
                manager, "_save_memory_file_wrapper", return_value=True
            ) as mock_save:
                result = manager.update_agent_memory(agent_id, items)

        # Check that only valid items are saved
        saved_content = mock_save.call_args[0][1]
        assert "Valid item" in saved_content
        assert "Another valid" in saved_content
        assert result is True

    def test_logger_property_initialization(self, manager):
        """Test logger property lazy initialization."""
        # First access should create logger
        logger1 = manager.logger
        assert logger1 is not None

        # Second access should return same instance
        logger2 = manager.logger
        assert logger1 is logger2

    def test_singleton_get_memory_manager(self):
        """Test that get_memory_manager returns singleton."""
        from claude_mpm.services.agents.memory.agent_memory_manager import (
            get_memory_manager,
        )

        # Clear any existing instance
        if hasattr(get_memory_manager, "_instance"):
            delattr(get_memory_manager, "_instance")

        with patch(
            "claude_mpm.services.agents.memory.agent_memory_manager.AgentMemoryManager"
        ) as MockManager:
            mock_instance = MagicMock()
            MockManager.return_value = mock_instance

            # First call creates instance
            manager1 = get_memory_manager()
            assert manager1 == mock_instance
            MockManager.assert_called_once()

            # Second call returns same instance
            manager2 = get_memory_manager()
            assert manager2 == mock_instance
            MockManager.assert_called_once()  # Still only called once
