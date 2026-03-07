"""
Unit tests for startup display banner.
"""

import os
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.claude_mpm.cli.startup_display import (
    _collect_scope_names,
    _count_scope_assets,
    _format_logging_status,
    _format_scope_counts,
    _format_two_column_line,
    _get_active_model_display_name,
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
            assert _get_terminal_width() == 120  # 75% of DEFAULT_WIDTH (160)


class TestChangelogParsing:
    """Tests for changelog parsing."""

    def test_parse_changelog_missing_file(self, tmp_path):
        """Test changelog parsing when file doesn't exist."""
        with patch.object(Path, "__truediv__", return_value=tmp_path / "missing.md"):
            highlights = _parse_changelog_highlights()
            assert highlights == ["No changelog available"]

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
        """Test alien art contains ASCII characters."""
        art = _get_alien_art()
        art_text = "".join(art)
        # Check for ASCII alien art characters
        assert any(char in art_text for char in ["▐", "▛", "█", "▜", "▌", "▝", "▘"])


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


class TestGetActiveModelDisplayName:
    """Tests for _get_active_model_display_name()."""

    def test_env_var_exact_alias(self, monkeypatch):
        """ANTHROPIC_MODEL env var with exact alias returns display name."""
        monkeypatch.setenv("ANTHROPIC_MODEL", "sonnet")
        assert _get_active_model_display_name() == "Sonnet"

    def test_env_var_versioned_model(self, monkeypatch):
        """ANTHROPIC_MODEL env var with versioned model returns display name."""
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-4-6")
        assert _get_active_model_display_name() == "Opus 4.6"

    def test_env_var_dated_variant_prefix_match(self, monkeypatch):
        """ANTHROPIC_MODEL env var with dated variant uses prefix match."""
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-4-6-20260101")
        assert _get_active_model_display_name() == "Opus 4.6"

    def test_env_var_unknown_model_returns_raw(self, monkeypatch):
        """ANTHROPIC_MODEL env var with unknown model returns raw value."""
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-unknown-9999")
        result = _get_active_model_display_name()
        assert result == "claude-unknown-9999"

    def test_env_var_unknown_model_truncated(self, monkeypatch):
        """ANTHROPIC_MODEL env var with very long unknown model is truncated."""
        long_model = "claude-unknown-model-very-long-name-exceeds-thirty-chars"
        monkeypatch.setenv("ANTHROPIC_MODEL", long_model)
        result = _get_active_model_display_name()
        assert len(result) <= 30

    def test_fallback_to_default_when_no_config(self, monkeypatch, tmp_path):
        """Returns 'Default' when no env var and no settings files exist."""
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        # Point cwd and home to empty tmp dirs so no settings files are found
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert _get_active_model_display_name() == "Default"

    def test_project_local_settings_takes_precedence(self, monkeypatch, tmp_path):
        """Project .claude/settings.local.json is preferred over other settings."""
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)

        # Create settings files with different model values
        local_settings = tmp_path / ".claude" / "settings.local.json"
        local_settings.parent.mkdir(parents=True)
        local_settings.write_text('{"model": "claude-opus-4-6"}')

        project_settings = tmp_path / ".claude" / "settings.json"
        project_settings.write_text('{"model": "claude-sonnet-4-6"}')

        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        assert _get_active_model_display_name() == "Opus 4.6"

    def test_project_settings_used_when_no_local(self, monkeypatch, tmp_path):
        """Project .claude/settings.json is used when no local settings exist."""
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)

        project_settings = tmp_path / ".claude" / "settings.json"
        project_settings.parent.mkdir(parents=True)
        project_settings.write_text('{"model": "sonnet"}')

        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        # home is a separate dir with no settings
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home_dir)

        assert _get_active_model_display_name() == "Sonnet"

    def test_global_settings_used_as_fallback(self, monkeypatch, tmp_path):
        """Global ~/.claude/settings.json is used when no project settings exist."""
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)

        cwd_dir = tmp_path / "project"
        cwd_dir.mkdir()
        monkeypatch.setattr(Path, "cwd", lambda: cwd_dir)

        global_settings = tmp_path / ".claude" / "settings.json"
        global_settings.parent.mkdir(parents=True)
        global_settings.write_text('{"model": "haiku"}')
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        assert _get_active_model_display_name() == "Haiku"

    def test_malformed_json_does_not_crash(self, monkeypatch, tmp_path):
        """Malformed JSON in settings file is silently skipped."""
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)

        local_settings = tmp_path / ".claude" / "settings.local.json"
        local_settings.parent.mkdir(parents=True)
        local_settings.write_text("{ this is not valid json }")

        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Should not raise; falls back to "Default"
        result = _get_active_model_display_name()
        assert result == "Default"

    def test_settings_file_with_no_model_key_skipped(self, monkeypatch, tmp_path):
        """Settings file without a 'model' key does not cause crash or bad value."""
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)

        local_settings = tmp_path / ".claude" / "settings.local.json"
        local_settings.parent.mkdir(parents=True)
        local_settings.write_text('{"theme": "dark"}')

        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        assert _get_active_model_display_name() == "Default"

    def test_env_var_takes_precedence_over_settings(self, monkeypatch, tmp_path):
        """ANTHROPIC_MODEL env var overrides any settings file."""
        monkeypatch.setenv("ANTHROPIC_MODEL", "opus")

        local_settings = tmp_path / ".claude" / "settings.local.json"
        local_settings.parent.mkdir(parents=True)
        local_settings.write_text('{"model": "haiku"}')

        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        assert _get_active_model_display_name() == "Opus"


class TestTwoColumnLayout:
    """Tests for two-column line formatting."""

    def test_format_two_column_line_basic(self):
        """Test two-column line formatting with basic content."""
        result = _format_two_column_line(
            "Left", "Right", left_panel_width=20, right_panel_width=40
        )

        assert result.startswith("│")
        assert result.endswith("│")
        assert "Left" in result
        assert "Right" in result

    def test_format_two_column_line_empty_left(self):
        """Test two-column line formatting with empty left panel."""
        result = _format_two_column_line(
            "", "Right content", left_panel_width=20, right_panel_width=40
        )

        assert result.startswith("│")
        assert result.endswith("│")
        assert "Right content" in result

    def test_format_two_column_line_empty_both(self):
        """Test two-column line formatting with both panels empty."""
        result = _format_two_column_line(
            "", "", left_panel_width=20, right_panel_width=40
        )

        assert result.startswith("│")
        assert result.endswith("│")
        # Should still have proper structure with pipes and spaces
        assert result.count("│") >= 3  # Start, middle, end


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


class TestCollectScopeNames:
    """Tests for _collect_scope_names() function."""

    def test_returns_lowercased_agent_stems(self, tmp_path, monkeypatch):
        """Test agent names are lowercased for cross-platform dedup."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "Engineer.md").write_text("agent")
        (agents_dir / "QA.md").write_text("agent")

        agent_names, _ = _collect_scope_names("project")
        assert agent_names == {"engineer", "qa"}

    def test_returns_lowercased_skill_names(self, tmp_path, monkeypatch):
        """Test skill directory names are lowercased for cross-platform dedup."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        skills_dir = tmp_path / ".claude" / "skills"
        d = skills_dir / "My-Skill"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("skill")

        _, skill_names = _collect_scope_names("project")
        assert skill_names == {"my-skill"}

    def test_excludes_git_repos(self, tmp_path, monkeypatch):
        """Test git source repos excluded from skill names."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        skills_dir = tmp_path / ".claude" / "skills"
        normal = skills_dir / "real-skill"
        normal.mkdir(parents=True)
        (normal / "SKILL.md").write_text("skill")
        repo = skills_dir / "source-repo"
        repo.mkdir(parents=True)
        (repo / "SKILL.md").write_text("skill")
        (repo / ".git").mkdir()

        _, skill_names = _collect_scope_names("project")
        assert skill_names == {"real-skill"}

    def test_empty_when_no_claude_dir(self, tmp_path, monkeypatch):
        """Test returns empty sets when .claude/ doesn't exist."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        agent_names, skill_names = _collect_scope_names("project")
        assert agent_names == set()
        assert skill_names == set()


class TestCountScopeAssets:
    """Tests for _count_scope_assets() function."""

    def test_project_scope_counts_agents(self, tmp_path, monkeypatch):
        """Test counting agents in project scope."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "engineer.md").write_text("agent")
        (agents_dir / "qa.md").write_text("agent")
        (agents_dir / "README.md").write_text("readme")  # excluded
        (agents_dir / "INSTRUCTIONS.md").write_text("instructions")  # excluded
        (agents_dir / ".hidden.md").write_text("hidden")  # excluded

        agents, skills = _count_scope_assets("project")
        assert agents == 2
        assert skills == 0

    def test_project_scope_counts_skills(self, tmp_path, monkeypatch):
        """Test counting skills in project scope."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        skills_dir = tmp_path / ".claude" / "skills"
        for name in ["skill-a", "skill-b", "skill-c"]:
            d = skills_dir / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text("skill")

        agents, skills = _count_scope_assets("project")
        assert agents == 0
        assert skills == 3

    def test_user_scope_uses_home(self, tmp_path, monkeypatch):
        """Test user scope reads from home directory."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "ops.md").write_text("agent")

        agents, _skills = _count_scope_assets("user")
        assert agents == 1

    def test_git_repo_excluded(self, tmp_path, monkeypatch):
        """Test git source repos are excluded from skill count."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        skills_dir = tmp_path / ".claude" / "skills"
        # Normal skill
        normal = skills_dir / "my-skill"
        normal.mkdir(parents=True)
        (normal / "SKILL.md").write_text("skill")
        # Git repo (should be excluded)
        repo = skills_dir / "claude-mpm"
        repo.mkdir(parents=True)
        (repo / "SKILL.md").write_text("skill")
        (repo / ".git").mkdir()

        _agents, skills = _count_scope_assets("project")
        assert skills == 1

    def test_lowercase_skill_md(self, tmp_path, monkeypatch):
        """Test lowercase skill.md is counted (Linux portability)."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        skills_dir = tmp_path / ".claude" / "skills"
        d = skills_dir / "my-skill"
        d.mkdir(parents=True)
        (d / "skill.md").write_text("skill")

        _agents, skills = _count_scope_assets("project")
        assert skills == 1

    def test_missing_directories(self, tmp_path, monkeypatch):
        """Test returns (0, 0) when .claude/ doesn't exist."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        agents, skills = _count_scope_assets("project")
        assert agents == 0
        assert skills == 0

    def test_both_counts_together(self, tmp_path, monkeypatch):
        """Test counting both agents and skills in same scope."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "engineer.md").write_text("agent")
        (agents_dir / "qa.md").write_text("agent")

        skills_dir = tmp_path / ".claude" / "skills"
        for name in ["skill-a", "skill-b"]:
            d = skills_dir / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text("skill")

        agents, skills = _count_scope_assets("project")
        assert agents == 2
        assert skills == 2


class TestFormatScopeCounts:
    """Tests for _format_scope_counts() function."""

    def test_full_format(self):
        """Test full format with wide panel."""
        result = _format_scope_counts("proj", 48, 189, 40)
        assert result == "proj: 48 agents, 189 skills"

    def test_abbreviated_format(self):
        """Test abbreviated format with narrow panel."""
        result = _format_scope_counts("proj", 48, 189, 20)
        assert result == "proj: 48a, 189s"

    def test_none_when_zero(self):
        """Test displays 'none' when both counts are zero."""
        result = _format_scope_counts("proj", 0, 0, 40)
        assert result == "proj: none"

    def test_agents_only(self):
        """Test displays only agents when skills are zero."""
        result = _format_scope_counts("user", 7, 0, 40)
        assert result == "user: 7 agents"

    def test_skills_only(self):
        """Test displays only skills when agents are zero."""
        result = _format_scope_counts("user", 0, 62, 40)
        assert result == "user: 62 skills"

    def test_singular(self):
        """Test singular form for single items."""
        result = _format_scope_counts("proj", 1, 1, 40)
        assert result == "proj: 1 agent, 1 skill"


class TestDisplayStartupBanner:
    """Tests for full banner display."""

    def test_display_startup_banner_output(self, capsys, monkeypatch):
        """Test banner displays output."""
        # Pin the model display name so the assertion is environment-independent
        monkeypatch.setattr(
            "src.claude_mpm.cli.startup_display._get_active_model_display_name",
            lambda: "Sonnet",
        )
        display_startup_banner("4.24.0", "OFF")
        captured = capsys.readouterr()

        # Banner was redesigned from text to visual box layout; "Launching..." text removed
        assert "Claude MPM v4.24.0" in captured.out
        assert "Welcome back" in captured.out
        # Banner shows the mocked model name
        assert "Sonnet" in captured.out

    def test_display_startup_banner_info_logging(self, capsys):
        """Test banner with INFO logging level."""
        display_startup_banner("4.24.0", "INFO")
        captured = capsys.readouterr()

        # Banner was redesigned from text to visual box layout; "Launching..." text removed
        assert "Claude MPM v4.24.0" in captured.out

    def test_display_startup_banner_debug_logging(self, capsys):
        """Test banner with DEBUG logging level."""
        display_startup_banner("4.24.0", "DEBUG")
        captured = capsys.readouterr()

        # Banner was redesigned from text to visual box layout; "Launching..." text removed
        assert "Claude MPM v4.24.0" in captured.out

    def test_display_startup_banner_includes_aliens(self, capsys):
        """Test banner includes alien art."""
        display_startup_banner("4.24.0", "OFF")
        captured = capsys.readouterr()

        # Check for alien ASCII art characters
        assert "▐▛███▜▌" in captured.out or "▝▜█████▛▘" in captured.out

    def test_display_startup_banner_includes_whats_new(self, capsys):
        """Test banner includes what's new section."""
        display_startup_banner("4.24.0", "OFF")
        captured = capsys.readouterr()

        assert "What's new" in captured.out

    def test_display_startup_banner_includes_cwd(self, capsys):
        """Test banner includes current working directory."""
        display_startup_banner("4.24.0", "OFF")
        captured = capsys.readouterr()

        # Should contain some path
        assert "/" in captured.out or "\\" in captured.out  # Unix or Windows path

    def test_display_startup_banner_scope_counts(self, capsys, monkeypatch):
        """Test banner shows project and user scope counts."""
        monkeypatch.setattr(
            "src.claude_mpm.cli.startup_display._get_active_model_display_name",
            lambda: "Sonnet",
        )
        monkeypatch.setattr(
            "src.claude_mpm.cli.startup_display._collect_scope_names",
            lambda scope: (
                (
                    {f"a{i}" for i in range(48)},
                    {f"s{i}" for i in range(189)},
                )
                if scope == "project"
                else (
                    {f"a{i}" for i in range(7)},
                    {f"s{i}" for i in range(62)},
                )
            ),
        )
        display_startup_banner("4.24.0", "OFF")
        captured = capsys.readouterr()

        assert "proj:" in captured.out
        assert "user:" in captured.out
        assert "total:" in captured.out
        assert "Sonnet" in captured.out

    def test_display_startup_banner_total_counts(self, capsys, monkeypatch):
        """Test banner shows total deduplicated counts."""
        monkeypatch.setattr(
            "src.claude_mpm.cli.startup_display._get_active_model_display_name",
            lambda: "Sonnet",
        )
        # Project has 48 agents, user has 7 (all overlap) + 3 unique = 10
        # Project has 189 skills, user has 62 (all overlap) + 5 unique = 67
        proj_agents = {f"agent-{i}" for i in range(48)}
        user_agents = {f"agent-{i}" for i in range(7)} | {
            "personal-a",
            "personal-b",
            "personal-c",
        }
        proj_skills = {f"skill-{i}" for i in range(189)}
        user_skills = {f"skill-{i}" for i in range(62)} | {
            "my-skill-1",
            "my-skill-2",
            "my-skill-3",
            "my-skill-4",
            "my-skill-5",
        }

        def mock_collect(scope):
            if scope == "project":
                return (proj_agents, proj_skills)
            return (user_agents, user_skills)

        monkeypatch.setattr(
            "src.claude_mpm.cli.startup_display._collect_scope_names",
            mock_collect,
        )
        display_startup_banner("4.24.0", "OFF")
        captured = capsys.readouterr()

        assert "proj:" in captured.out
        assert "user:" in captured.out
        assert "total:" in captured.out
        assert "Sonnet" in captured.out
