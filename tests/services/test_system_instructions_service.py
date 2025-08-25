"""Tests for SystemInstructionsService.

Tests the extracted system instructions service to ensure it maintains
the same behavior as the original ClaudeRunner methods.
"""

from unittest.mock import Mock, patch

import pytest

from claude_mpm.services.system_instructions_service import SystemInstructionsService


class TestSystemInstructionsService:
    """Test the SystemInstructionsService class."""

    @pytest.fixture
    def service(self):
        """Create a SystemInstructionsService instance for testing."""
        return SystemInstructionsService()

    @pytest.fixture
    def service_with_agent_capabilities(self):
        """Create a SystemInstructionsService with mock agent capabilities service."""
        mock_agent_service = Mock()
        mock_agent_service.generate_deployed_agent_capabilities.return_value = (
            "Mock agent capabilities"
        )
        return SystemInstructionsService(agent_capabilities_service=mock_agent_service)

    def test_load_system_instructions_project_found(service, tmp_path):
        """Test loading system instructions from project directory."""
        # Create project instructions
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        instructions_dir = project_dir / ".claude-mpm" / "agents"
        instructions_dir.mkdir(parents=True)

        instructions_file = instructions_dir / "INSTRUCTIONS.md"
        instructions_content = "# Project Instructions\nProject-specific instructions"
        instructions_file.write_text(instructions_content)

        with patch("pathlib.Path.cwd", return_value=project_dir):
            result = service.load_system_instructions()

        assert result is not None
        assert "Project Instructions" in result
        assert "Project-specific instructions" in result

    def test_load_system_instructions_framework_fallback(service, tmp_path):
        """Test fallback to framework instructions when project not found."""
        # Mock framework path
        framework_dir = tmp_path / "framework"
        framework_dir.mkdir()
        framework_instructions = (
            framework_dir / "src" / "claude_mpm" / "agents" / "INSTRUCTIONS.md"
        )
        framework_instructions.parent.mkdir(parents=True)

        instructions_content = "# Framework Instructions\nFramework instructions"
        framework_instructions.write_text(instructions_content)

        with patch("claude_mpm.config.paths.paths.project_root", framework_dir), patch(
            "pathlib.Path.cwd", return_value=tmp_path / "empty_project"
        ):
            result = service.load_system_instructions()

        assert result is not None
        assert "Framework Instructions" in result

    def test_load_system_instructions_base_pm_fallback(service, tmp_path):
        """Test fallback to BASE_PM.md when INSTRUCTIONS.md not found."""
        # Mock framework path with BASE_PM.md
        framework_dir = tmp_path / "framework"
        framework_dir.mkdir()
        base_pm_file = framework_dir / "src" / "claude_mpm" / "agents" / "BASE_PM.md"
        base_pm_file.parent.mkdir(parents=True)

        base_pm_content = "# Base PM\n{{VERSION}} instructions"
        base_pm_file.write_text(base_pm_content)

        with patch("claude_mpm.config.paths.paths.project_root", framework_dir), patch(
            "pathlib.Path.cwd", return_value=tmp_path / "empty_project"
        ):
            result = service.load_system_instructions()

        assert result is not None
        assert "Base PM" in result
        # Version should be replaced
        assert "{{VERSION}}" not in result

    def test_load_system_instructions_not_found(service, tmp_path):
        """Test when no system instructions are found."""
        with patch(
            "claude_mpm.config.paths.paths.project_root", tmp_path / "nonexistent"
        ), patch("pathlib.Path.cwd", return_value=tmp_path / "empty_project"):
            result = service.load_system_instructions()

        assert result is None

    def test_process_base_pm_content_with_agent_capabilities(
        self, service_with_agent_capabilities
    ):
        """Test BASE_PM content processing with agent capabilities."""
        base_pm_content = """
# Base PM
{{AGENT_CAPABILITIES}}
{{VERSION}}
{{CURRENT_DATE}}
"""

        result = service_with_agent_capabilities.process_base_pm_content(
            base_pm_content
        )

        assert "{{AGENT_CAPABILITIES}}" not in result
        assert "Mock agent capabilities" in result
        assert "{{VERSION}}" not in result
        assert "{{CURRENT_DATE}}" not in result

    def test_process_base_pm_content_without_agent_service(service):
        """Test BASE_PM content processing without agent capabilities service."""
        base_pm_content = """
# Base PM
{{AGENT_CAPABILITIES}}
{{VERSION}}
{{CURRENT_DATE}}
"""

        result = service.process_base_pm_content(base_pm_content)

        # Agent capabilities should remain unchanged
        assert "{{AGENT_CAPABILITIES}}" in result
        # But version and date should be replaced
        assert "{{VERSION}}" not in result
        assert "{{CURRENT_DATE}}" not in result

    def test_strip_metadata_comments(service):
        """Test HTML metadata comment stripping."""
        content_with_comments = """
<!-- FRAMEWORK_VERSION: 0010 -->
# Real Content
Some instructions
<!-- LAST_MODIFIED: 2025-08-10T00:00:00Z -->
More content
<!-- metadata: test -->
Final content
"""

        result = service.strip_metadata_comments(content_with_comments)

        assert "<!-- FRAMEWORK_VERSION: 0010 -->" not in result
        assert "<!-- LAST_MODIFIED: 2025-08-10T00:00:00Z -->" not in result
        assert "<!-- metadata: test -->" not in result
        assert "# Real Content" in result
        assert "Some instructions" in result
        assert "More content" in result
        assert "Final content" in result

    def test_strip_metadata_comments_no_comments(service):
        """Test metadata stripping with no comments."""
        content = """
# Clean Content
No metadata comments here
Just regular content
"""

        result = service.strip_metadata_comments(content)

        # The method strips leading newlines, so we expect that behavior
        expected = content.lstrip("\n")
        assert result == expected

    def test_create_system_prompt_with_instructions(service):
        """Test system prompt creation with provided instructions."""
        instructions = "Test system instructions"

        result = service.create_system_prompt(instructions)

        assert result == instructions

    def test_create_system_prompt_load_instructions(service, tmp_path):
        """Test system prompt creation that loads instructions."""
        # Create project instructions
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        instructions_dir = project_dir / ".claude-mpm" / "agents"
        instructions_dir.mkdir(parents=True)

        instructions_file = instructions_dir / "INSTRUCTIONS.md"
        instructions_content = "# Loaded Instructions\nLoaded content"
        instructions_file.write_text(instructions_content)

        with patch("pathlib.Path.cwd", return_value=project_dir):
            result = service.create_system_prompt()

        assert result is not None
        assert "Loaded Instructions" in result

    def test_create_system_prompt_fallback(service, tmp_path):
        """Test system prompt creation with fallback."""
        with patch(
            "claude_mpm.config.paths.paths.project_root", tmp_path / "nonexistent"
        ), patch("pathlib.Path.cwd", return_value=tmp_path / "empty_project"), patch(
            "claude_mpm.core.claude_runner.create_simple_context",
            return_value="Simple context",
        ):
            result = service.create_system_prompt()

        assert result == "Simple context"

    def test_get_version_from_file(service, tmp_path):
        """Test version detection from VERSION file."""
        version_file = tmp_path / "VERSION"
        version_file.write_text("1.2.3")

        with patch("claude_mpm.config.paths.paths.project_root", tmp_path):
            version = service._get_version()

        assert version == "1.2.3"

    def test_get_version_from_package(service, tmp_path):
        """Test version detection from package."""
        with patch(
            "claude_mpm.config.paths.paths.project_root", tmp_path / "nonexistent"
        ), patch(
            "claude_mpm.services.system_instructions_service.claude_mpm"
        ) as mock_module:
            mock_module.__version__ = "2.0.0"
            version = service._get_version()

        assert version == "2.0.0"

    def test_get_version_unknown(service, tmp_path):
        """Test version detection when unknown."""
        with patch(
            "claude_mpm.config.paths.paths.project_root", tmp_path / "nonexistent"
        ):
            version = service._get_version()

        assert version == "unknown"

    def test_error_handling_in_load_instructions(service):
        """Test error handling during instruction loading."""
        with patch("pathlib.Path.cwd", side_effect=Exception("Test error")):
            result = service.load_system_instructions()

        assert result is None

    def test_error_handling_in_process_base_pm(service):
        """Test error handling during BASE_PM processing."""
        # This should not crash even with invalid content
        result = service.process_base_pm_content("{{INVALID_TEMPLATE}}")

        assert result is not None
        assert "{{INVALID_TEMPLATE}}" in result

    def test_error_handling_in_strip_comments(service):
        """Test error handling during comment stripping."""
        # This should not crash even with invalid regex patterns
        result = service.strip_metadata_comments("Some content")

        assert result == "Some content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
