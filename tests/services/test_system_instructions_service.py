"""Tests for SystemInstructionsService.

Tests the extracted system instructions service to ensure it maintains
the same behavior as the original ClaudeRunner methods.
"""

from pathlib import Path
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

    def test_load_system_instructions_project_found(self, service):
        """Test loading system instructions via FrameworkLoader."""
        instructions_content = "# Project Instructions\nProject-specific instructions"

        # FrameworkLoader is a local import - patch at source module
        with patch(
            "claude_mpm.core.framework_loader.FrameworkLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_loader.get_framework_instructions.return_value = instructions_content
            mock_loader_class.return_value = mock_loader

            result = service.load_system_instructions()

        assert result is not None
        assert "Project Instructions" in result
        assert "Project-specific instructions" in result

    def test_load_system_instructions_framework_fallback(self, service):
        """Test fallback when FrameworkLoader returns empty string."""
        with patch(
            "claude_mpm.core.framework_loader.FrameworkLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_loader.get_framework_instructions.return_value = ""
            mock_loader_class.return_value = mock_loader

            result = service.load_system_instructions()

        assert result is not None
        # Returns the no-instructions fallback message
        assert "System Instructions" in result

    def test_load_system_instructions_base_pm_fallback(self, service):
        """Test that BASE_PM-based content is returned via FrameworkLoader."""
        base_pm_content = "# Base PM\nInstructions loaded from BASE_PM"

        with patch(
            "claude_mpm.core.framework_loader.FrameworkLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_loader.get_framework_instructions.return_value = base_pm_content
            mock_loader_class.return_value = mock_loader

            result = service.load_system_instructions()

        assert result is not None
        assert "Base PM" in result

    def test_load_system_instructions_not_found(self, service):
        """Test when FrameworkLoader raises an exception - returns fallback string."""
        with patch(
            "claude_mpm.core.framework_loader.FrameworkLoader"
        ) as mock_loader_class:
            mock_loader_class.side_effect = Exception("FrameworkLoader failed")

            result = service.load_system_instructions()

        # Returns error fallback string (not None) when loading fails
        assert result is not None
        assert len(result) > 0

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

    def test_process_base_pm_content_without_agent_service(self, service):
        """Test BASE_PM content processing without agent capabilities service."""
        base_pm_content = """
# Base PM
{{AGENT_CAPABILITIES}}
{{VERSION}}
{{CURRENT_DATE}}
"""

        result = service.process_base_pm_content(base_pm_content)

        # Agent capabilities remain unchanged (no service to replace it)
        assert "{{AGENT_CAPABILITIES}}" in result
        # Version and date are replaced
        assert "{{VERSION}}" not in result
        assert "{{CURRENT_DATE}}" not in result

    def test_strip_metadata_comments(self, service):
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

    def test_strip_metadata_comments_no_comments(self, service):
        """Test metadata stripping with no comments."""
        content = """
# Clean Content
No metadata comments here
Just regular content
"""

        result = service.strip_metadata_comments(content)

        # The method strips leading newlines
        expected = content.lstrip("\n")
        assert result == expected

    def test_create_system_prompt_with_instructions(self, service):
        """Test system prompt creation with provided instructions.

        The user-level override file is mocked away so this test passes
        regardless of whether ~/.claude-mpm/PM_INSTRUCTIONS.md exists on
        the host machine.
        """
        instructions = "Test system instructions"

        with patch.object(Path, "is_file", return_value=False):
            result = service.create_system_prompt(instructions)

        assert result == instructions

    def test_create_system_prompt_load_instructions(self, service):
        """Test system prompt creation loads via FrameworkLoader."""
        instructions_content = "# Loaded Instructions\nLoaded content"

        with (
            patch(
                "claude_mpm.core.framework_loader.FrameworkLoader"
            ) as mock_loader_class,
            patch.object(Path, "is_file", return_value=False),
        ):
            mock_loader = Mock()
            mock_loader.get_framework_instructions.return_value = instructions_content
            mock_loader_class.return_value = mock_loader

            result = service.create_system_prompt()

        assert result is not None
        assert "Loaded Instructions" in result

    def test_create_system_prompt_fallback(self, service):
        """Test system prompt creation delegates to load_system_instructions.

        The user-level override file is mocked away so the assertion
        ``result == "Fallback context"`` holds regardless of whether
        ~/.claude-mpm/PM_INSTRUCTIONS.md exists on the host machine.
        """
        with (
            patch.object(
                service, "load_system_instructions", return_value="Fallback context"
            ) as mock_load,
            patch.object(Path, "is_file", return_value=False),
        ):
            result = service.create_system_prompt()

        assert result == "Fallback context"
        mock_load.assert_called_once()

    def test_get_version_from_file(self, service, tmp_path):
        """Test version detection from VERSION file."""
        version_file = tmp_path / "VERSION"
        version_file.write_text("1.2.3")

        with patch(
            "claude_mpm.services.system_instructions_service.paths"
        ) as mock_paths:
            mock_paths.project_root = tmp_path
            version = service._get_version()

        assert version == "1.2.3"

    def test_get_version_from_package(self, service, tmp_path):
        """Test version detection falls back to installed package version."""
        import claude_mpm as _claude_mpm

        expected = getattr(_claude_mpm, "__version__", "unknown")

        with patch(
            "claude_mpm.services.system_instructions_service.paths"
        ) as mock_paths:
            # Point to directory with no VERSION file
            mock_paths.project_root = tmp_path / "no_version_here"
            version = service._get_version()

        # Should return the installed package version (or "unknown" if not set)
        assert version == expected

    def test_get_version_unknown(self, service):
        """Test version detection returns 'unknown' when paths raise exception."""
        with patch(
            "claude_mpm.services.system_instructions_service.paths"
        ) as mock_paths:
            # Make project_root raise an exception to force the outer except handler
            type(mock_paths).project_root = Mock(
                side_effect=Exception("no paths available")
            )
            version = service._get_version()

        assert version == "unknown"

    def test_error_handling_in_load_instructions(self, service):
        """Test error handling during instruction loading returns fallback."""
        with patch(
            "claude_mpm.core.framework_loader.FrameworkLoader"
        ) as mock_loader_class:
            mock_loader_class.side_effect = Exception("Test error")

            result = service.load_system_instructions()

        # Should return a non-None fallback string
        assert result is not None
        assert len(result) > 0

    def test_error_handling_in_process_base_pm(self, service):
        """Test error handling during BASE_PM processing."""
        # Unknown template vars are left unchanged (no processing error)
        result = service.process_base_pm_content("{{INVALID_TEMPLATE}}")

        assert result is not None
        assert "{{INVALID_TEMPLATE}}" in result

    def test_error_handling_in_strip_comments(self, service):
        """Test error handling during comment stripping."""
        result = service.strip_metadata_comments("Some content")

        assert result == "Some content"


class TestUserLevelPMOverride:
    """Tests for the user-level ~/.claude-mpm/PM_INSTRUCTIONS.md override.

    These tests exercise the override-application logic in
    ``SystemInstructionsService.create_system_prompt`` by redirecting the
    user config dir to a pytest ``tmp_path`` so they don't depend on (or
    pollute) the real ~/.claude-mpm directory.
    """

    @pytest.fixture
    def service(self):
        """Fresh service instance per test (clears prompt cache between tests)."""
        return SystemInstructionsService()

    @pytest.fixture
    def user_config_dir(self, tmp_path, monkeypatch):
        """Redirect get_user_config_dir() to a tmp directory.

        Patches the path manager used by ``create_system_prompt`` so each
        test gets an isolated user config directory that disappears with
        the tmp_path fixture.
        """
        fake_dir = tmp_path / ".claude-mpm"
        fake_dir.mkdir()

        # Patch the get_path_manager() call site inside the service module
        # to return a stub whose get_user_config_dir() points at fake_dir.
        mock_manager = Mock()
        mock_manager.get_user_config_dir.return_value = fake_dir
        monkeypatch.setattr(
            "claude_mpm.services.system_instructions_service.get_path_manager",
            lambda: mock_manager,
        )
        return fake_dir

    def test_override_applied_when_file_exists(self, service, user_config_dir):
        """Override content is appended when ~/.claude-mpm/PM_INSTRUCTIONS.md exists."""
        override_text = "Custom user PM directive: be extra concise."
        (user_config_dir / "PM_INSTRUCTIONS.md").write_text(
            override_text, encoding="utf-8"
        )

        base = "# Base PM Instructions\nDefault behavior."
        result = service.create_system_prompt(base)

        # Original base is preserved, override is appended with marker.
        assert base in result
        assert "# User-Level PM Override" in result
        assert override_text in result
        # Marker appears exactly once (sanity check).
        assert result.count("# User-Level PM Override") == 1

    def test_no_override_when_file_absent(self, service, user_config_dir):
        """Result equals base when the override file does not exist."""
        # user_config_dir fixture created the directory but no override file.
        assert not (user_config_dir / "PM_INSTRUCTIONS.md").exists()

        base = "# Base PM Instructions\nDefault behavior."
        result = service.create_system_prompt(base)

        assert result == base
        assert "# User-Level PM Override" not in result

    def test_override_appended_only_once_across_calls(self, service, user_config_dir):
        """Regression test for the double-append bug.

        ``create_system_prompt`` is called multiple times on the same
        service instance; the override marker must appear exactly once.
        Uses the no-arg path so the augmented-prompt cache is exercised.
        """
        (user_config_dir / "PM_INSTRUCTIONS.md").write_text(
            "Override body", encoding="utf-8"
        )

        with patch.object(
            service, "load_system_instructions", return_value="# Base\nstuff"
        ):
            first = service.create_system_prompt()
            second = service.create_system_prompt()
            third = service.create_system_prompt()

        # All calls return the same augmented prompt.
        assert first == second == third
        # The override marker appears exactly once, not three times.
        assert first.count("# User-Level PM Override") == 1
        assert first.count("Override body") == 1

    def test_override_skipped_on_read_error(self, service, user_config_dir, caplog):
        """When the override file raises OSError on read, fall back to base.

        The exception must be caught, a DEBUG-level message logged, and
        the un-augmented base instructions returned.
        """
        override_file = user_config_dir / "PM_INSTRUCTIONS.md"
        override_file.write_text("ignored", encoding="utf-8")

        base = "# Base instructions only"

        # Patch Path.read_text to raise OSError for any call. The
        # is_file() check still succeeds (the file exists), so we
        # exercise the read-error branch specifically.
        with patch.object(Path, "read_text", side_effect=OSError("permission denied")):
            import logging

            with caplog.at_level(logging.DEBUG):
                result = service.create_system_prompt(base)

        # Fell back to base content, no marker appended.
        assert result == base
        assert "# User-Level PM Override" not in result

        # The DEBUG log message was emitted (substring match — exact
        # format may evolve).
        debug_messages = [
            r.getMessage() for r in caplog.records if r.levelno == logging.DEBUG
        ]
        assert any(
            "User-level override exists but couldn't read" in msg
            for msg in debug_messages
        ), f"Expected debug log not found in: {debug_messages}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
