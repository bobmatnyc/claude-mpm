"""
tests/test_manifest_loader.py — Unit tests for the detection-gated manifest loader.

WHAT: Exercises ``find_manifest``, ``load_manifest``, ``ManifestResult``, and
``ManifestLoadError`` across four key scenarios: (1) dormant path (no file),
(2) valid file loaded and validated, (3) malformed JSON raises ManifestLoadError,
(4) injectable preset_resolver is called when ``extends`` is present.

WHY: The loader is the entry point for all manifest-aware code.  Correct
dormant behaviour (returning None with no side effects) is the most critical
property to test because a regression here would silently change the behaviour
of all projects that have not opted in to the manifest system.

References
----------
SPEC-MANIFEST-01~1 : docs/specs/manifest.md#SPEC-MANIFEST-01~1
"""

from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003 — used as a value at runtime in _write_manifest
from typing import Any

import pytest

from claude_mpm.manifest.loader import (
    ManifestLoadError,
    ManifestResult,
    find_manifest,
    load_manifest,
)
from claude_mpm.manifest.schema import ManifestValidationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_manifest(directory: Path, content: Any) -> Path:
    """Write a manifest file (as JSON string or raw string) into *directory*."""
    manifest_dir = directory / ".claude-mpm"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "manifest.json"
    if isinstance(content, dict):
        manifest_path.write_text(json.dumps(content), encoding="utf-8")
    else:
        # Allow raw invalid strings for error-path tests.
        manifest_path.write_text(str(content), encoding="utf-8")
    return manifest_path


# ===========================================================================
# find_manifest
# ===========================================================================


class TestFindManifest:
    """``find_manifest`` locates the manifest by walking upward."""

    def test_returns_none_when_no_manifest(self, tmp_path: Path) -> None:
        assert find_manifest(tmp_path) is None

    def test_finds_manifest_in_same_directory(self, tmp_path: Path) -> None:
        expected = _write_manifest(tmp_path, {"version": "1.0"})
        result = find_manifest(tmp_path)
        assert result == expected

    def test_finds_manifest_in_parent_directory(self, tmp_path: Path) -> None:
        expected = _write_manifest(tmp_path, {"version": "1.0"})
        subdir = tmp_path / "src" / "mymodule"
        subdir.mkdir(parents=True)
        result = find_manifest(subdir)
        assert result == expected

    def test_finds_nearest_manifest(self, tmp_path: Path) -> None:
        """When manifests exist at multiple levels, the nearest one wins."""
        parent_manifest = _write_manifest(tmp_path, {"version": "1.0"})
        child_dir = tmp_path / "child"
        child_dir.mkdir()
        child_manifest = _write_manifest(child_dir, {"version": "1.0"})
        result = find_manifest(child_dir)
        assert result == child_manifest
        assert result != parent_manifest

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, {"version": "1.0"})
        result = find_manifest(str(tmp_path))
        assert result is not None

    def test_returns_absolute_path(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, {"version": "1.0"})
        result = find_manifest(tmp_path)
        assert result is not None
        assert result.is_absolute()


# ===========================================================================
# Dormant path (no manifest file)
# ===========================================================================


class TestDormantPath:
    """When no manifest file exists, load_manifest must return None silently."""

    def test_returns_none_when_no_file(self, tmp_path: Path) -> None:
        result = load_manifest(tmp_path)
        assert result is None

    def test_no_exception_when_no_file(self, tmp_path: Path) -> None:
        """Must not raise any exception for the absent case."""
        try:
            load_manifest(tmp_path)
        except Exception as exc:
            pytest.fail(f"load_manifest raised unexpectedly: {exc}")

    def test_returns_none_from_subdirectory_with_no_manifest(
        self, tmp_path: Path
    ) -> None:
        subdir = tmp_path / "deep" / "nested"
        subdir.mkdir(parents=True)
        result = load_manifest(subdir)
        assert result is None


# ===========================================================================
# Valid manifest loaded and validated
# ===========================================================================


class TestValidManifestLoaded:
    """When a valid manifest is found, a ManifestResult is returned."""

    def test_returns_manifest_result(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, {"version": "1.0"})
        result = load_manifest(tmp_path)
        assert isinstance(result, ManifestResult)

    def test_repo_contains_parsed_manifest(self, tmp_path: Path) -> None:
        manifest = {"version": "1.0", "setup": {"services": ["svc-a"]}}
        _write_manifest(tmp_path, manifest)
        result = load_manifest(tmp_path)
        assert result is not None
        assert result.repo["version"] == "1.0"
        assert result.repo["setup"]["services"] == ["svc-a"]

    def test_effective_equals_repo_when_no_resolver(self, tmp_path: Path) -> None:
        manifest = {"version": "1.0"}
        _write_manifest(tmp_path, manifest)
        result = load_manifest(tmp_path)
        assert result is not None
        assert result.effective == result.repo

    def test_preset_merged_is_false_when_no_extends(self, tmp_path: Path) -> None:
        """When extends is absent, no preset is merged and preset_merged is False."""
        _write_manifest(tmp_path, {"version": "1.0"})
        result = load_manifest(tmp_path)
        assert result is not None
        assert result.preset_merged is False

    def test_path_attribute_points_to_file(self, tmp_path: Path) -> None:
        manifest_path = _write_manifest(tmp_path, {"version": "1.0"})
        result = load_manifest(tmp_path)
        assert result is not None
        assert result.path == manifest_path

    def test_loads_from_subdirectory(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, {"version": "1.0"})
        subdir = tmp_path / "src"
        subdir.mkdir()
        result = load_manifest(subdir)
        assert result is not None
        assert result.repo["version"] == "1.0"


# ===========================================================================
# Error paths
# ===========================================================================


class TestErrorPaths:
    """Clear errors raised for malformed files and schema violations."""

    def test_malformed_json_raises_manifest_load_error(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, "{not valid json")
        with pytest.raises(ManifestLoadError) as exc_info:
            load_manifest(tmp_path)
        err = exc_info.value
        assert hasattr(err, "path")
        assert hasattr(err, "message")

    def test_manifest_load_error_message_is_human_readable(
        self, tmp_path: Path
    ) -> None:
        _write_manifest(tmp_path, "{bad json")
        with pytest.raises(ManifestLoadError) as exc_info:
            load_manifest(tmp_path)
        assert len(str(exc_info.value)) > 10

    def test_schema_violation_raises_manifest_validation_error(
        self, tmp_path: Path
    ) -> None:
        # Missing required "version" field.
        _write_manifest(tmp_path, {"extends": "default"})
        with pytest.raises(ManifestValidationError):
            load_manifest(tmp_path)

    def test_wrong_version_raises_manifest_validation_error(
        self, tmp_path: Path
    ) -> None:
        _write_manifest(tmp_path, {"version": "99.0"})
        with pytest.raises(ManifestValidationError):
            load_manifest(tmp_path)

    def test_manifest_root_not_object_raises_load_error(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, '["not", "an", "object"]')
        with pytest.raises(ManifestLoadError):
            load_manifest(tmp_path)


# ===========================================================================
# Injectable preset resolver
# ===========================================================================


class TestInjectablePresetResolver:
    """preset_resolver is called when extends is present and resolver provided."""

    def test_resolver_called_with_extends_value(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, {"version": "1.0", "extends": "mypreset"})
        calls: list[str] = []

        def resolver(name: str) -> dict:
            calls.append(name)
            return {}

        load_manifest(tmp_path, preset_resolver=resolver)
        assert calls == ["mypreset"]

    def test_resolver_result_merged_into_effective(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            {
                "version": "1.0",
                "extends": "preset-x",
                "agents": {"eng": {"model": "sonnet"}},
            },
        )
        preset_data = {
            "agents": {"eng": {"model": "haiku", "color": "green"}},
            "setup": {"services": ["preset-svc"]},
        }

        result = load_manifest(tmp_path, preset_resolver=lambda _: preset_data)
        assert result is not None
        assert result.preset_merged is True
        # repo wins for model
        assert result.effective["agents"]["eng"]["model"] == "sonnet"
        # preset fills color
        assert result.effective["agents"]["eng"]["color"] == "green"
        # setup.services from preset appears in effective
        assert "preset-svc" in result.effective["setup"]["services"]

    def test_preset_merged_true_when_resolver_provided(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, {"version": "1.0", "extends": "any"})
        result = load_manifest(tmp_path, preset_resolver=lambda _: {})
        assert result is not None
        assert result.preset_merged is True

    def test_repo_unchanged_when_resolver_provided(self, tmp_path: Path) -> None:
        """result.repo must always be the raw file content, never the merged dict."""
        _write_manifest(
            tmp_path, {"version": "1.0", "extends": "p", "agents": {"x": {}}}
        )
        preset_data = {"agents": {"y": {"model": "haiku"}}}
        result = load_manifest(tmp_path, preset_resolver=lambda _: preset_data)
        assert result is not None
        # repo should not have been mutated by the merge
        assert "y" not in result.repo.get("agents", {})
        # effective should have merged data
        assert "y" in result.effective.get("agents", {})

    def test_no_custom_resolver_uses_builtin_resolver(self, tmp_path: Path) -> None:
        """When preset_resolver=None and extends is set, the built-in resolver is used.

        PR2 changed the behavior from PR1: passing preset_resolver=None no longer
        skips preset resolution; instead the built-in four-step resolver is invoked
        automatically.  Tests that need to skip resolution should use a stub that
        returns an empty dict or raises, rather than relying on preset_resolver=None.
        """
        from claude_mpm.manifest.resolver import PresetResolutionError

        # A known built-in preset: resolution should succeed and merge the preset.
        _write_manifest(
            tmp_path / "with_builtin", {"version": "1.0", "extends": "minimal"}
        )
        (tmp_path / "with_builtin").mkdir(exist_ok=True)
        import json

        preset_dir = tmp_path / "with_builtin" / ".claude-mpm"
        preset_dir.mkdir(parents=True, exist_ok=True)
        (preset_dir / "manifest.json").write_text(
            json.dumps({"version": "1.0", "extends": "minimal"}), encoding="utf-8"
        )
        result = load_manifest(tmp_path / "with_builtin", preset_resolver=None)
        assert result is not None
        assert result.preset_merged is True

        # An unknown preset name: should raise PresetResolutionError.
        unknown_dir = tmp_path / "with_unknown"
        unknown_dir.mkdir()
        preset_dir2 = unknown_dir / ".claude-mpm"
        preset_dir2.mkdir()
        (preset_dir2 / "manifest.json").write_text(
            json.dumps({"version": "1.0", "extends": "totally-unknown-preset-xyz"}),
            encoding="utf-8",
        )
        with pytest.raises(PresetResolutionError):
            load_manifest(unknown_dir, preset_resolver=None)

    def test_resolver_not_called_when_extends_absent(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, {"version": "1.0"})
        calls: list[str] = []

        def resolver(name: str) -> dict:
            calls.append(name)
            return {}

        load_manifest(tmp_path, preset_resolver=resolver)
        assert calls == []

    def test_resolver_exception_propagates(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path, {"version": "1.0", "extends": "bad-preset"})

        def failing_resolver(name: str) -> dict:
            raise RuntimeError("preset not found")

        with pytest.raises(RuntimeError, match="preset not found"):
            load_manifest(tmp_path, preset_resolver=failing_resolver)
