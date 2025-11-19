"""
Unit tests for startup display banner.
"""

import os
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.claude_mpm.cli.startup_display import (
    _create_two_column_layout,
    _format_logging_status,
    _get_alien_art,
    _get_cwd_display,
    _get_terminal_width,
    _get_username,
    _parse_changelog_highlights,
    display_startup_banner,
    should_show_banner,
)


class TestUsernameDetection:
    """Tests for username detection."""

    def test_get_username_from_user_env(self):
        """Test username detection from USER environment variable."""
        with patch.dict(os.environ, {"USER": "testuser"}, clear=True):
            assert _get_username() == "testuser"

    def test_get_username_from_username_env(self):
        """Test username detection from USERNAME environment variable."""
        with patch.dict(os.environ, {"USERNAME": "winuser"}, clear=True):
            assert _get_username() == "winuser"

    def test_get_username_default(self):
        """Test default username when no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            assert _get_username() == "User"


class TestTerminalWidth:
    """Tests for terminal width detection."""

    def test_get_terminal_width_default(self):
        """Test terminal width returns reasonable value."""
        width = _get_terminal_width()
        assert width >= 80  # Reasonable minimum
        assert isinstance(width, int)

    def test_get_terminal_width_fallback(self):
        """Test terminal width fallback on error."""
        with patch("shutil.get_terminal_size", side_effect=Exception("Test error")):
            assert _get_terminal_width() == 100


class TestChangelogParsing:
    """Tests for changelog parsing."""

    def test_parse_changelog_missing_file(self, tmp_path):
        """Test changelog parsing when file doesn't exist."""
        with patch.object(Path, "__truediv__", return_value=tmp_path / "missing.md"):
            highlights = _parse_changelog_highlights()
            assert highlights == ["• No changelog available"]

    def test_parse_changelog_valid_content(self, tmp_path):
        """Test changelog parsing with valid content."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            """## [Unreleased]

### Added

## [1.0.0] - 2025-01-01

### Added
- **New Feature**: Amazing functionality
- **Another Feature**: More improvements
- **Third Feature**: Even more stuff

## [0.9.0] - 2024-12-01

### Added
- Old feature
"""
        )

        with patch.object(Path, "__truediv__", return_value=changelog) as mock_path:
            # Need to make sure the path resolution works correctly
            mock_instance = MagicMock()
            mock_instance.exists.return_value = True
            mock_instance.__truediv__.return_value = changelog
            mock_path.return_value = mock_instance

            # Patch the actual file path properly
            with patch(
                "src.claude_mpm.cli.startup_display.Path.__truediv__",
                return_value=changelog,
            ):
                # Mock the exists check
                with patch.object(Path, "exists", return_value=True):
                    # The function constructs path dynamically, so we patch the file open directly
                    original_open = open

                    def mock_open(*args, **kwargs):
                        if "CHANGELOG.md" in str(args[0]):
                            return original_open(changelog, *args[1:], **kwargs)
                        return original_open(*args, **kwargs)

                    with patch("builtins.open", side_effect=mock_open):
                        highlights = _parse_changelog_highlights(max_items=3)
                        assert len(highlights) >= 1
                        assert (
                            "New Feature" in highlights[0]
                            or "Amazing functionality" in highlights[0]
                        )

    def test_parse_changelog_empty_added_section(self, tmp_path):
        """Test changelog parsing with empty Added section."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            """## [1.0.0] - 2025-01-01

### Added

### Changed
- Some changes

## [0.9.0] - 2024-12-01
"""
        )

        with patch(
            "src.claude_mpm.cli.startup_display.Path.__truediv__",
            return_value=changelog,
        ):
            with patch.object(Path, "exists", return_value=True):
                original_open = open

                def mock_open(*args, **kwargs):
                    if "CHANGELOG.md" in str(args[0]):
                        return original_open(changelog, *args[1:], **kwargs)
                    return original_open(*args, **kwargs)

                with patch("builtins.open", side_effect=mock_open):
                    highlights = _parse_changelog_highlights()
                    # Should find the Changed item
                    assert len(highlights) >= 1


class TestAlienArt:
    """Tests for alien ASCII art."""

    def test_get_alien_art_returns_list(self):
        """Test alien art returns list of strings."""
        art = _get_alien_art()
        assert isinstance(art, list)
        assert len(art) > 0
        assert all(isinstance(line, str) for line in art)

    def test_get_alien_art_has_emojis(self):
        """Test alien art contains emojis."""
        art = _get_alien_art()
        art_text = "".join(art)
        # Check for some alien-related emojis
        assert any(emoji in art_text for emoji in ["👽", "🛸", "👾", "🚀"])


class TestLoggingStatus:
    """Tests for logging status formatting."""

    def test_format_logging_status_off(self):
        """Test OFF logging status formatting."""
        assert _format_logging_status("OFF") == "Logging: OFF (default)"

    def test_format_logging_status_debug(self):
        """Test DEBUG logging status formatting."""
        assert _format_logging_status("DEBUG") == "Logging: DEBUG (verbose)"

    def test_format_logging_status_info(self):
        """Test INFO logging status formatting."""
        assert _format_logging_status("INFO") == "Logging: INFO"

    def test_format_logging_status_custom(self):
        """Test custom logging status formatting."""
        assert _format_logging_status("CUSTOM") == "Logging: CUSTOM"


class TestCwdDisplay:
    """Tests for current working directory display."""

    def test_get_cwd_display_short_path(self):
        """Test CWD display with short path."""
        with patch.object(Path, "cwd", return_value=Path("/short/path")):
            result = _get_cwd_display(max_width=50)
            assert result == "/short/path"

    def test_get_cwd_display_long_path_truncation(self):
        """Test CWD display truncates long paths."""
        long_path = "/very/long/path/that/exceeds/the/maximum/width/limit/here"
        with patch.object(Path, "cwd", return_value=Path(long_path)):
            result = _get_cwd_display(max_width=20)
            assert result.startswith("...")
            assert len(result) == 20
            assert result.endswith(long_path[-(20 - 3) :])


class TestTwoColumnLayout:
    """Tests for two-column layout creation."""

    def test_create_two_column_layout_equal_height(self):
        """Test two-column layout with equal height content."""
        left = ["Line 1", "Line 2"]
        right = ["Right 1", "Right 2"]
        result = _create_two_column_layout(left, right, total_width=89, left_width=40)

        assert len(result) == 2
        assert all(line.startswith("│") and line.endswith("│") for line in result)

    def test_create_two_column_layout_unequal_height(self):
        """Test two-column layout with different height content."""
        left = ["Line 1", "Line 2", "Line 3"]
        right = ["Right 1"]
        result = _create_two_column_layout(left, right, total_width=89, left_width=40)

        assert len(result) == 3  # Should match taller column
        assert all(line.startswith("│") and line.endswith("│") for line in result)

    def test_create_two_column_layout_empty_content(self):
        """Test two-column layout with empty content."""
        left = []
        right = []
        result = _create_two_column_layout(left, right, total_width=89, left_width=40)

        assert len(result) == 0


class TestShouldShowBanner:
    """Tests for banner display logic."""

    def test_should_show_banner_run_command(self):
        """Test banner shows for run command."""
        args = Namespace(command="run", help=False, version=False)
        assert should_show_banner(args) is True

    def test_should_show_banner_tickets_command(self):
        """Test banner shows for tickets command."""
        args = Namespace(command="tickets", help=False, version=False)
        assert should_show_banner(args) is True

    def test_should_show_banner_info_command(self):
        """Test banner doesn't show for info command."""
        args = Namespace(command="info", help=False, version=False)
        assert should_show_banner(args) is False

    def test_should_show_banner_doctor_command(self):
        """Test banner doesn't show for doctor command."""
        args = Namespace(command="doctor", help=False, version=False)
        assert should_show_banner(args) is False

    def test_should_show_banner_config_command(self):
        """Test banner doesn't show for config command."""
        args = Namespace(command="config", help=False, version=False)
        assert should_show_banner(args) is False

    def test_should_show_banner_configure_command(self):
        """Test banner doesn't show for configure command."""
        args = Namespace(command="configure", help=False, version=False)
        assert should_show_banner(args) is False

    def test_should_show_banner_help_flag(self):
        """Test banner doesn't show with help flag."""
        args = Namespace(command="run", help=True, version=False)
        assert should_show_banner(args) is False

    def test_should_show_banner_version_flag(self):
        """Test banner doesn't show with version flag."""
        args = Namespace(command="run", help=False, version=True)
        assert should_show_banner(args) is False

    def test_should_show_banner_no_command(self):
        """Test banner shows when no command specified."""
        args = Namespace(help=False, version=False)
        # No command attribute means it should show
        assert should_show_banner(args) is True


class TestDisplayStartupBanner:
    """Tests for full banner display."""

    def test_display_startup_banner_output(self, capsys):
        """Test banner displays output."""
        display_startup_banner("4.24.0", "OFF")
        captured = capsys.readouterr()

        assert "Claude MPM v4.24.0" in captured.out
        assert "Welcome back" in captured.out
        assert "Sonnet 4.5" in captured.out
        assert "Logging: OFF (default)" in captured.out
        assert "💡 Tip" in captured.out

    def test_display_startup_banner_info_logging(self, capsys):
        """Test banner with INFO logging level."""
        display_startup_banner("4.24.0", "INFO")
        captured = capsys.readouterr()

        assert "Logging: INFO" in captured.out
        assert "(default)" not in captured.out

    def test_display_startup_banner_debug_logging(self, capsys):
        """Test banner with DEBUG logging level."""
        display_startup_banner("4.24.0", "DEBUG")
        captured = capsys.readouterr()

        assert "Logging: DEBUG (verbose)" in captured.out

    def test_display_startup_banner_includes_aliens(self, capsys):
        """Test banner includes alien art."""
        display_startup_banner("4.24.0", "OFF")
        captured = capsys.readouterr()

        # Check for alien emojis
        assert any(emoji in captured.out for emoji in ["👽", "🛸", "👾", "🚀"])

    def test_display_startup_banner_includes_whats_new(self, capsys):
        """Test banner includes what's new section."""
        display_startup_banner("4.24.0", "OFF")
        captured = capsys.readouterr()

        assert "What's new in 4.24.0" in captured.out

    def test_display_startup_banner_includes_cwd(self, capsys):
        """Test banner includes current working directory."""
        display_startup_banner("4.24.0", "OFF")
        captured = capsys.readouterr()

        # Should contain some path
        assert "/" in captured.out or "\\" in captured.out  # Unix or Windows path
