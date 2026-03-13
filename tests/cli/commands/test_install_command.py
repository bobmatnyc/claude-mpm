"""
Tests for the 'install' CLI command.

Covers:
- Language detection logic (unit tests with temp dirs)
- --language override
- settings.json update logic
- manage_install dispatch
"""

import json
import types
from pathlib import Path

import pytest

from claude_mpm.cli.commands.install import (
    LANGUAGE_CONFIGS,
    _config_for,
    _set_lsp_enabled_in_settings,
    detect_languages,
    manage_install,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_args(**kwargs) -> types.SimpleNamespace:
    """Build a minimal args namespace for testing."""
    defaults = {
        "install_command": None,
        "language": None,
        "force": False,
    }
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# detect_languages
# ---------------------------------------------------------------------------


class TestDetectLanguages:
    def test_rust_detected(self, tmp_path: Path) -> None:
        (tmp_path / "Cargo.toml").touch()
        assert detect_languages(tmp_path) == ["rust"]

    def test_go_detected(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").touch()
        assert detect_languages(tmp_path) == ["go"]

    def test_java_pom_detected(self, tmp_path: Path) -> None:
        (tmp_path / "pom.xml").touch()
        assert detect_languages(tmp_path) == ["java"]

    def test_java_gradle_detected(self, tmp_path: Path) -> None:
        (tmp_path / "build.gradle").touch()
        assert detect_languages(tmp_path) == ["java"]

    def test_typescript_detected(self, tmp_path: Path) -> None:
        (tmp_path / "tsconfig.json").touch()
        (tmp_path / "package.json").touch()
        assert detect_languages(tmp_path) == ["typescript"]

    def test_typescript_requires_package_json(self, tmp_path: Path) -> None:
        # tsconfig.json alone is NOT enough for TypeScript
        (tmp_path / "tsconfig.json").touch()
        assert "typescript" not in detect_languages(tmp_path)

    def test_javascript_detected(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").touch()
        assert detect_languages(tmp_path) == ["javascript"]

    def test_javascript_excluded_when_tsconfig_present(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").touch()
        (tmp_path / "tsconfig.json").touch()
        assert "javascript" not in detect_languages(tmp_path)

    def test_python_pyproject_detected(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        assert detect_languages(tmp_path) == ["python"]

    def test_python_setup_py_detected(self, tmp_path: Path) -> None:
        (tmp_path / "setup.py").touch()
        assert detect_languages(tmp_path) == ["python"]

    def test_python_py_glob_detected(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").touch()
        assert detect_languages(tmp_path) == ["python"]

    def test_empty_dir_no_detection(self, tmp_path: Path) -> None:
        assert detect_languages(tmp_path) == []

    def test_multiple_languages_detected(self, tmp_path: Path) -> None:
        # A project can have both Go and Python files (e.g. a polyglot repo)
        (tmp_path / "go.mod").touch()
        (tmp_path / "pyproject.toml").touch()
        langs = detect_languages(tmp_path)
        assert "go" in langs
        assert "python" in langs

    def test_detection_priority_rust_before_python(self, tmp_path: Path) -> None:
        # Rust is first in priority order
        (tmp_path / "Cargo.toml").touch()
        (tmp_path / "pyproject.toml").touch()
        langs = detect_languages(tmp_path)
        assert langs.index("rust") < langs.index("python")


# ---------------------------------------------------------------------------
# _config_for
# ---------------------------------------------------------------------------


class TestConfigFor:
    def test_known_language_returns_dict(self) -> None:
        cfg = _config_for("python")
        assert cfg is not None
        assert cfg["name"] == "python"
        assert "install_cmd" in cfg
        assert "plugin" in cfg

    def test_unknown_language_returns_none(self) -> None:
        assert _config_for("cobol") is None

    def test_all_language_configs_reachable(self) -> None:
        for lang_cfg in LANGUAGE_CONFIGS:
            result = _config_for(lang_cfg["name"])
            assert result is not None
            assert result["name"] == lang_cfg["name"]


# ---------------------------------------------------------------------------
# _set_lsp_enabled_in_settings
# ---------------------------------------------------------------------------


class TestSetLspEnabledInSettings:
    def test_creates_settings_file_if_missing(self, tmp_path: Path) -> None:
        settings_path = tmp_path / "settings.json"
        assert not settings_path.exists()

        result = _set_lsp_enabled_in_settings(settings_path)

        assert result is True
        assert settings_path.exists()
        data = json.loads(settings_path.read_text())
        assert data["env"]["ENABLE_LSP_TOOL"] == "1"

    def test_merges_with_existing_settings(self, tmp_path: Path) -> None:
        settings_path = tmp_path / "settings.json"
        existing = {"someKey": "someValue", "env": {"OTHER": "val"}}
        settings_path.write_text(json.dumps(existing))

        result = _set_lsp_enabled_in_settings(settings_path)

        assert result is True
        data = json.loads(settings_path.read_text())
        # Existing keys preserved
        assert data["someKey"] == "someValue"
        assert data["env"]["OTHER"] == "val"
        # New key added
        assert data["env"]["ENABLE_LSP_TOOL"] == "1"

    def test_overwrites_lsp_flag_if_already_set(self, tmp_path: Path) -> None:
        settings_path = tmp_path / "settings.json"
        settings_path.write_text(json.dumps({"env": {"ENABLE_LSP_TOOL": "0"}}))

        result = _set_lsp_enabled_in_settings(settings_path)

        assert result is True
        data = json.loads(settings_path.read_text())
        assert data["env"]["ENABLE_LSP_TOOL"] == "1"

    def test_recovers_from_malformed_json(self, tmp_path: Path) -> None:
        settings_path = tmp_path / "settings.json"
        settings_path.write_text("not valid json {{{{")

        result = _set_lsp_enabled_in_settings(settings_path)

        assert result is True
        data = json.loads(settings_path.read_text())
        assert data["env"]["ENABLE_LSP_TOOL"] == "1"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        settings_path = tmp_path / "deep" / "nested" / "settings.json"
        assert not settings_path.parent.exists()

        result = _set_lsp_enabled_in_settings(settings_path)

        assert result is True
        assert settings_path.exists()

    def test_handles_env_non_dict(self, tmp_path: Path) -> None:
        # If "env" is not a dict, it should be replaced
        settings_path = tmp_path / "settings.json"
        settings_path.write_text(json.dumps({"env": "bad_value"}))

        result = _set_lsp_enabled_in_settings(settings_path)

        assert result is True
        data = json.loads(settings_path.read_text())
        assert isinstance(data["env"], dict)
        assert data["env"]["ENABLE_LSP_TOOL"] == "1"


# ---------------------------------------------------------------------------
# manage_install dispatch
# ---------------------------------------------------------------------------


class TestManageInstall:
    def test_no_subcommand_returns_1(self, capsys) -> None:
        args = _make_args(install_command=None)
        result = manage_install(args)
        assert result == 1

    def test_unknown_subcommand_returns_1(self, capsys) -> None:
        args = _make_args(install_command="nonexistent")
        result = manage_install(args)
        assert result == 1
