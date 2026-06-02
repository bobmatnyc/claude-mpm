"""
tests/test_manifest_resolver.py — Unit and integration tests for the preset resolver.

WHAT: Exercises ``resolve_preset``, ``PresetResolutionError``,
``load_builtin_preset``, and the end-to-end integration of
``load_manifest`` with real preset resolution.

WHY: Preset resolution is the primary new behaviour in PR2.  Correct
resolution ORDER (local > user > entry-point > built-in) and correct
error messages when nothing matches are the most important properties to
verify.  Integration tests confirm the loader + resolver data path works
end-to-end.

References
----------
SPEC-MANIFEST-04~1 : docs/specs/manifest.md#SPEC-MANIFEST-04~1
SPEC-MANIFEST-01~1 : docs/specs/manifest.md#SPEC-MANIFEST-01~1
"""

from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.manifest.loader import load_manifest
from claude_mpm.manifest.presets import BUILTIN_PRESET_NAMES, load_builtin_preset
from claude_mpm.manifest.resolver import PresetResolutionError, resolve_preset
from claude_mpm.manifest.schema import ManifestValidationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_manifest(directory: Path, content: Any) -> Path:
    """Write a manifest file into *directory*/.claude-mpm/manifest.json."""
    manifest_dir = directory / ".claude-mpm"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "manifest.json"
    if isinstance(content, dict):
        manifest_path.write_text(json.dumps(content), encoding="utf-8")
    else:
        manifest_path.write_text(str(content), encoding="utf-8")
    return manifest_path


def _write_preset_file(path: Path, content: dict) -> None:
    """Write a preset JSON file at *path* (creates parent dirs)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content), encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests: load_builtin_preset
# ---------------------------------------------------------------------------


class TestLoadBuiltinPreset:
    """Tests for the built-in preset accessor module."""

    def test_default_returns_dict(self) -> None:
        result = load_builtin_preset("default")
        assert isinstance(result, dict)

    def test_minimal_returns_dict(self) -> None:
        result = load_builtin_preset("minimal")
        assert isinstance(result, dict)

    def test_enterprise_returns_dict(self) -> None:
        result = load_builtin_preset("enterprise")
        assert isinstance(result, dict)

    def test_unknown_returns_none(self) -> None:
        assert load_builtin_preset("does-not-exist") is None
        assert load_builtin_preset("") is None
        assert load_builtin_preset("DEFAULT") is None  # case-sensitive

    def test_each_builtin_has_version(self) -> None:
        for name in BUILTIN_PRESET_NAMES:
            preset = load_builtin_preset(name)
            assert preset is not None
            assert preset.get("version") == "1.0", f"{name} missing version"

    def test_builtin_preset_names_coverage(self) -> None:
        """Sanity-check the frozenset covers all three expected names."""
        assert "default" in BUILTIN_PRESET_NAMES
        assert "minimal" in BUILTIN_PRESET_NAMES
        assert "enterprise" in BUILTIN_PRESET_NAMES

    def test_importlib_resources_path(self) -> None:
        """Verify load_builtin_preset works via importlib.resources (wheel-safe)."""
        # This test verifies the correct loading mechanism is used by checking
        # the result is valid JSON with the expected structure.
        result = load_builtin_preset("default")
        assert result is not None
        assert isinstance(result, dict)
        assert result["version"] == "1.0"

    def test_default_has_agents(self) -> None:
        result = load_builtin_preset("default")
        assert result is not None
        assert "agents" in result
        assert isinstance(result["agents"], dict)

    def test_enterprise_has_hooks(self) -> None:
        result = load_builtin_preset("enterprise")
        assert result is not None
        assert "hooks" in result
        hooks = result["hooks"]
        assert "PreToolUse" in hooks
        assert "Stop" in hooks

    def test_minimal_is_minimal(self) -> None:
        """Minimal preset should have only version and (optionally) settings."""
        result = load_builtin_preset("minimal")
        assert result is not None
        assert "version" in result
        # Should NOT have agents or hooks
        assert "agents" not in result
        assert "hooks" not in result


# ---------------------------------------------------------------------------
# Tests: each built-in preset schema-validates
# ---------------------------------------------------------------------------


class TestBuiltinPresetSchemaValidation:
    """Verifies each built-in preset passes the manifest schema."""

    @pytest.mark.parametrize("name", list(BUILTIN_PRESET_NAMES))
    def test_builtin_validates(self, name: str) -> None:
        from claude_mpm.manifest.schema import validate_manifest

        preset = load_builtin_preset(name)
        assert preset is not None
        # Should NOT raise
        validate_manifest(preset)


# ---------------------------------------------------------------------------
# Tests: PresetResolutionError
# ---------------------------------------------------------------------------


class TestPresetResolutionError:
    """Tests for the PresetResolutionError exception."""

    def test_has_extends_and_tried(self) -> None:
        err = PresetResolutionError("my-preset", ["source1", "source2"])
        assert err.extends == "my-preset"
        assert err.tried == ["source1", "source2"]

    def test_message_includes_sources(self) -> None:
        err = PresetResolutionError("my-preset", ["source1", "source2"])
        msg = str(err)
        assert "my-preset" in msg
        assert "source1" in msg
        assert "source2" in msg

    def test_is_lookup_error(self) -> None:
        err = PresetResolutionError("x", [])
        assert isinstance(err, LookupError)


# ---------------------------------------------------------------------------
# Tests: resolve_preset — resolution ORDER
# ---------------------------------------------------------------------------


class TestResolvePresetOrder:
    """Verify FIRST MATCH WINS in the four-step resolution order."""

    # ------------------------------------------------------------------
    # Step 4: built-in wins when nothing else matches
    # ------------------------------------------------------------------

    def test_builtin_default_resolves(self) -> None:
        result = resolve_preset("default")
        assert isinstance(result, dict)
        assert result.get("version") == "1.0"

    def test_builtin_minimal_resolves(self) -> None:
        result = resolve_preset("minimal")
        assert isinstance(result, dict)

    def test_builtin_enterprise_resolves(self) -> None:
        result = resolve_preset("enterprise")
        assert isinstance(result, dict)

    def test_unknown_raises_preset_resolution_error(self) -> None:
        with pytest.raises(PresetResolutionError) as exc_info:
            resolve_preset("no-such-preset-xyz-123")
        err = exc_info.value
        assert "no-such-preset-xyz-123" in str(err)
        # All four sources should be listed
        assert len(err.tried) >= 3  # user-dir, entry-point, built-in

    def test_error_lists_all_sources_tried(self) -> None:
        with pytest.raises(PresetResolutionError) as exc_info:
            resolve_preset("totally-unknown-preset")
        tried_text = "\n".join(exc_info.value.tried)
        assert "user preset directory" in tried_text
        assert "entry point" in tried_text
        assert "built-in" in tried_text

    # ------------------------------------------------------------------
    # Step 1: local path beats everything
    # ------------------------------------------------------------------

    def test_local_absolute_path_wins(self, tmp_path: Path) -> None:
        preset_file = tmp_path / "my-preset.json"
        _write_preset_file(
            preset_file, {"version": "1.0", "settings": {"key": "local"}}
        )
        result = resolve_preset(str(preset_file))
        assert result["settings"]["key"] == "local"

    def test_local_relative_path_wins_over_builtin(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        preset_file = tmp_path / "my-preset.json"
        _write_preset_file(
            preset_file, {"version": "1.0", "settings": {"key": "local-rel"}}
        )
        monkeypatch.chdir(tmp_path)
        result = resolve_preset("./my-preset.json")
        assert result["settings"]["key"] == "local-rel"

    def test_local_path_not_found_raises_immediately(self, tmp_path: Path) -> None:
        """When a local path is explicit, fail immediately if file missing."""
        with pytest.raises(PresetResolutionError) as exc_info:
            resolve_preset(str(tmp_path / "nonexistent.json"))
        assert "local path" in " ".join(exc_info.value.tried)

    def test_local_relative_path_not_found_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        with pytest.raises(PresetResolutionError):
            resolve_preset("./no-such-file.json")

    # ------------------------------------------------------------------
    # Step 2: user preset dir beats entry-point and built-in
    # ------------------------------------------------------------------

    def test_user_preset_dir_beats_builtin(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        user_preset_dir = tmp_path / ".claude-mpm" / "presets"
        user_preset_dir.mkdir(parents=True)
        preset_file = user_preset_dir / "default.json"
        # Override the built-in "default" with a custom one
        preset_file.write_text(
            json.dumps({"version": "1.0", "settings": {"override": "from-user-dir"}}),
            encoding="utf-8",
        )
        # Patch Path.home() to point to tmp_path
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        result = resolve_preset("default")
        assert result["settings"]["override"] == "from-user-dir"

    def test_user_preset_dir_beats_entry_point(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """User dir is checked before entry points."""
        user_preset_dir = tmp_path / ".claude-mpm" / "presets"
        user_preset_dir.mkdir(parents=True)
        preset_file = user_preset_dir / "acme.json"
        preset_file.write_text(
            json.dumps({"version": "1.0", "settings": {"src": "user-dir"}}),
            encoding="utf-8",
        )
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

        # Register a mock entry point for "acme" that would return different data
        mock_ep = MagicMock()
        mock_ep.name = "acme"
        mock_ep.load.return_value = lambda: {
            "version": "1.0",
            "settings": {"src": "entry-point"},
        }

        with patch.object(importlib.metadata, "entry_points", return_value=[mock_ep]):
            result = resolve_preset("acme")

        # User dir should win
        assert result["settings"]["src"] == "user-dir"

    # ------------------------------------------------------------------
    # Step 3: entry point beats built-in
    # ------------------------------------------------------------------

    def test_entry_point_beats_builtin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Entry points are checked before built-in presets."""
        # Patch home so no user preset dir file exists for "default"
        monkeypatch.setattr(
            Path, "home", classmethod(lambda cls: Path("/nonexistent-tmp-home"))
        )

        mock_ep = MagicMock()
        mock_ep.name = "default"
        mock_ep.load.return_value = lambda: {
            "version": "1.0",
            "settings": {"src": "entry-point"},
        }

        with patch.object(importlib.metadata, "entry_points", return_value=[mock_ep]):
            result = resolve_preset("default")

        assert result["settings"]["src"] == "entry-point"

    def test_entry_point_for_unknown_builtin(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An entry point for a non-built-in name is found before failing."""
        monkeypatch.setattr(
            Path, "home", classmethod(lambda cls: Path("/nonexistent-tmp-home"))
        )

        mock_ep = MagicMock()
        mock_ep.name = "acme-corp"
        mock_ep.load.return_value = lambda: {
            "version": "1.0",
            "settings": {"company": "acme"},
        }

        with patch.object(importlib.metadata, "entry_points", return_value=[mock_ep]):
            result = resolve_preset("acme-corp")

        assert result["settings"]["company"] == "acme"


# ---------------------------------------------------------------------------
# Tests: resolve_preset — validation
# ---------------------------------------------------------------------------


class TestResolvePresetValidation:
    """Ensure resolved presets are schema-validated."""

    def test_invalid_local_preset_raises_validation_error(self, tmp_path: Path) -> None:
        """A local preset with an invalid shape raises ManifestValidationError."""
        preset_file = tmp_path / "bad.json"
        # Missing required "version" key → schema violation
        preset_file.write_text(json.dumps({"agents": {}}), encoding="utf-8")
        with pytest.raises(ManifestValidationError):
            resolve_preset(str(preset_file))

    def test_invalid_entry_point_preset_raises_validation_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            Path, "home", classmethod(lambda cls: Path("/nonexistent-tmp-home"))
        )
        mock_ep = MagicMock()
        mock_ep.name = "bad-preset"
        mock_ep.load.return_value = lambda: {"no_version": True}

        with patch.object(importlib.metadata, "entry_points", return_value=[mock_ep]):
            with pytest.raises(ManifestValidationError):
                resolve_preset("bad-preset")


# ---------------------------------------------------------------------------
# Tests: multi-level extends chains (deferred, O1)
# ---------------------------------------------------------------------------


class TestMultiLevelExtendsDeferral:
    """Confirm that a preset's own extends key is ignored (O1 deferred)."""

    def test_preset_with_extends_key_is_returned_without_recursion(
        self, tmp_path: Path
    ) -> None:
        """A preset that itself has 'extends' should be returned as-is (no recursion)."""
        preset_file = tmp_path / "chained.json"
        preset_file.write_text(
            json.dumps({"version": "1.0", "extends": "default", "settings": {"x": 1}}),
            encoding="utf-8",
        )
        # Should not raise, should not recurse
        result = resolve_preset(str(preset_file))
        assert result["settings"]["x"] == 1
        assert result["extends"] == "default"  # key preserved but not resolved


# ---------------------------------------------------------------------------
# Integration tests: load_manifest + real resolver
# ---------------------------------------------------------------------------


class TestLoadManifestIntegration:
    """End-to-end tests: load_manifest with the built-in resolver."""

    def test_extends_minimal_merges_correctly(self, tmp_path: Path) -> None:
        """A manifest with extends=minimal resolves and merges correctly."""
        _write_manifest(
            tmp_path,
            {
                "version": "1.0",
                "extends": "minimal",
                "settings": {"project": "my-proj"},
            },
        )
        result = load_manifest(tmp_path)
        assert result is not None
        assert result.preset_merged is True
        assert result.effective["settings"]["project"] == "my-proj"
        assert result.effective["version"] == "1.0"

    def test_extends_default_merges_preset_agents(self, tmp_path: Path) -> None:
        """Extending 'default' pulls in the preset's agent definitions."""
        _write_manifest(
            tmp_path,
            {
                "version": "1.0",
                "extends": "default",
            },
        )
        result = load_manifest(tmp_path)
        assert result is not None
        assert result.preset_merged is True
        # The default preset defines agents
        assert "agents" in result.effective
        assert "engineer" in result.effective["agents"]

    def test_repo_wins_over_preset_on_scalar(self, tmp_path: Path) -> None:
        """Repo manifest scalar values override the preset's values."""
        _write_manifest(
            tmp_path,
            {
                "version": "1.0",
                "extends": "default",
                "agents": {"engineer": {"model": "custom-model"}},
            },
        )
        result = load_manifest(tmp_path)
        assert result is not None
        assert result.effective["agents"]["engineer"]["model"] == "custom-model"

    def test_preset_resolver_override_still_works(self, tmp_path: Path) -> None:
        """Injectable preset_resolver param still overrides the built-in resolver."""
        stub_preset = {"version": "1.0", "settings": {"from": "stub"}}
        _write_manifest(
            tmp_path,
            {"version": "1.0", "extends": "anything"},
        )
        result = load_manifest(tmp_path, preset_resolver=lambda _: stub_preset)
        assert result is not None
        assert result.effective["settings"]["from"] == "stub"

    def test_no_extends_no_preset_merged(self, tmp_path: Path) -> None:
        """Without extends, preset_merged is False and effective == repo."""
        _write_manifest(tmp_path, {"version": "1.0", "settings": {"k": "v"}})
        result = load_manifest(tmp_path)
        assert result is not None
        assert result.preset_merged is False
        assert result.effective == result.repo

    def test_unknown_preset_raises(self, tmp_path: Path) -> None:
        """load_manifest with an unknown extends raises PresetResolutionError."""
        _write_manifest(tmp_path, {"version": "1.0", "extends": "no-such-preset-xyz"})
        with pytest.raises(PresetResolutionError):
            load_manifest(tmp_path)

    def test_extends_enterprise_has_hooks(self, tmp_path: Path) -> None:
        """Extending enterprise preset provides audit hooks."""
        _write_manifest(tmp_path, {"version": "1.0", "extends": "enterprise"})
        result = load_manifest(tmp_path)
        assert result is not None
        assert result.preset_merged is True
        assert "hooks" in result.effective
        assert "PreToolUse" in result.effective["hooks"]
