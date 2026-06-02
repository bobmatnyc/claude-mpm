"""
tests/test_manifest_merger.py — Unit tests for the manifest deep-merge module.

WHAT: Exercises all merge rules defined in SPEC-MANIFEST-02~1: scalar override,
nested object merge, ``setup.services`` union+dedup+order, other-array
replacement, and edge cases (empty preset, empty repo, deep conflicts).

WHY: The merger is the most test-critical module in the manifest subsystem
because incorrect merge semantics silently produce wrong effective configs that
are hard to diagnose in production.  Exhaustive unit tests provide the safety
net that makes future changes safe.

References
----------
SPEC-MANIFEST-02~1 : docs/specs/manifest.md#SPEC-MANIFEST-02~1
"""

from __future__ import annotations

import copy

import pytest

from claude_mpm.manifest.merger import _union_merge, deep_merge

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def merge(preset: dict, repo: dict) -> dict:
    """Thin wrapper so tests read as ``merge(preset, repo)``."""
    return deep_merge(preset, repo)


# ===========================================================================
# Scalar override
# ===========================================================================


class TestScalarOverride:
    """repo wins for scalar values; absent keys fall back to preset."""

    def test_repo_scalar_wins_over_preset(self) -> None:
        result = merge({"version": "1.0"}, {"version": "2.0"})
        assert result["version"] == "2.0"

    def test_preset_scalar_used_when_repo_absent(self) -> None:
        result = merge({"version": "1.0"}, {})
        assert result["version"] == "1.0"

    def test_repo_adds_new_scalar_key(self) -> None:
        result = merge({}, {"extra": "value"})
        assert result["extra"] == "value"

    def test_repo_none_wins_over_preset_string(self) -> None:
        # None is a valid scalar — repo wins.
        result = merge({"key": "value"}, {"key": None})
        assert result["key"] is None

    def test_preset_not_mutated(self) -> None:
        preset = {"x": 1}
        repo = {"x": 2}
        original_preset = copy.deepcopy(preset)
        merge(preset, repo)
        assert preset == original_preset

    def test_repo_not_mutated(self) -> None:
        preset = {"x": 1}
        repo = {"x": 2}
        original_repo = copy.deepcopy(repo)
        merge(preset, repo)
        assert repo == original_repo


# ===========================================================================
# Nested object merge
# ===========================================================================


class TestNestedObjectMerge:
    """Objects are recursively deep-merged; repo wins at the leaf level."""

    def test_nested_key_merge(self) -> None:
        preset = {"agents": {"engineer": {"model": "haiku", "color": "green"}}}
        repo = {"agents": {"engineer": {"model": "sonnet"}}}
        result = merge(preset, repo)
        assert result["agents"]["engineer"]["model"] == "sonnet"
        assert result["agents"]["engineer"]["color"] == "green"

    def test_repo_adds_new_agent(self) -> None:
        preset = {"agents": {"engineer": {"model": "haiku"}}}
        repo = {"agents": {"reviewer": {"model": "opus"}}}
        result = merge(preset, repo)
        assert "engineer" in result["agents"]
        assert result["agents"]["reviewer"]["model"] == "opus"

    def test_deeply_nested_conflict(self) -> None:
        preset = {"settings": {"permissions": {"additionalDirectories": ["~/shared"]}}}
        repo = {"settings": {"permissions": {"mode": "strict"}}}
        result = merge(preset, repo)
        perms = result["settings"]["permissions"]
        assert perms["additionalDirectories"] == ["~/shared"]
        assert perms["mode"] == "strict"

    def test_three_level_nesting(self) -> None:
        preset = {"a": {"b": {"c": 1, "d": 2}}}
        repo = {"a": {"b": {"c": 99}}}
        result = merge(preset, repo)
        assert result["a"]["b"]["c"] == 99
        assert result["a"]["b"]["d"] == 2

    def test_object_vs_scalar_type_mismatch_repo_wins(self) -> None:
        """When preset has dict and repo has scalar, repo wins."""
        preset = {"key": {"nested": "value"}}
        repo = {"key": "flat_value"}
        result = merge(preset, repo)
        assert result["key"] == "flat_value"

    def test_scalar_vs_object_type_mismatch_repo_wins(self) -> None:
        """When preset has scalar and repo has dict, repo wins."""
        preset = {"key": "flat_value"}
        repo = {"key": {"nested": "value"}}
        result = merge(preset, repo)
        assert result["key"] == {"nested": "value"}


# ===========================================================================
# setup.services union merge
# ===========================================================================


class TestSetupServicesUnion:
    """setup.services is union-merged: preset first, then repo-only extras."""

    def test_union_merges_disjoint_lists(self) -> None:
        preset = {"setup": {"services": ["kuzu-memory"]}}
        repo = {"setup": {"services": ["mcp-ticketer"]}}
        result = merge(preset, repo)
        assert result["setup"]["services"] == ["kuzu-memory", "mcp-ticketer"]

    def test_union_deduplicates_shared_entries(self) -> None:
        preset = {"setup": {"services": ["kuzu-memory", "shared-svc"]}}
        repo = {"setup": {"services": ["shared-svc", "mcp-ticketer"]}}
        result = merge(preset, repo)
        services = result["setup"]["services"]
        assert services == ["kuzu-memory", "shared-svc", "mcp-ticketer"]

    def test_union_preserves_preset_first_order(self) -> None:
        preset = {"setup": {"services": ["a", "b"]}}
        repo = {"setup": {"services": ["c", "a"]}}
        result = merge(preset, repo)
        assert result["setup"]["services"] == ["a", "b", "c"]

    def test_empty_preset_services_uses_repo_only(self) -> None:
        preset = {"setup": {"services": []}}
        repo = {"setup": {"services": ["svc-x"]}}
        result = merge(preset, repo)
        assert result["setup"]["services"] == ["svc-x"]

    def test_empty_repo_services_uses_preset_only(self) -> None:
        preset = {"setup": {"services": ["svc-x"]}}
        repo = {"setup": {"services": []}}
        result = merge(preset, repo)
        assert result["setup"]["services"] == ["svc-x"]

    def test_preset_services_absent_uses_repo(self) -> None:
        preset = {"setup": {}}
        repo = {"setup": {"services": ["svc-x"]}}
        result = merge(preset, repo)
        assert result["setup"]["services"] == ["svc-x"]

    def test_repo_services_absent_uses_preset(self) -> None:
        preset = {"setup": {"services": ["svc-x"]}}
        repo = {"setup": {}}
        result = merge(preset, repo)
        assert result["setup"]["services"] == ["svc-x"]

    def test_no_setup_key_in_either(self) -> None:
        preset = {"version": "1.0"}
        repo = {"version": "1.0"}
        result = merge(preset, repo)
        assert "setup" not in result

    def test_design_doc_example(self) -> None:
        """Verbatim example from docs/design/manifest-config-system.md."""
        preset = {
            "agents": {"engineer": {"model": "haiku", "color": "green"}},
            "setup": {"services": ["kuzu-memory"]},
        }
        repo = {
            "extends": "acme",
            "agents": {"engineer": {"model": "sonnet"}},
            "setup": {"services": ["mcp-ticketer"]},
        }
        result = merge(preset, repo)
        assert result["agents"]["engineer"]["model"] == "sonnet"
        assert result["agents"]["engineer"]["color"] == "green"
        assert result["setup"]["services"] == ["kuzu-memory", "mcp-ticketer"]


# ===========================================================================
# Other-array replacement
# ===========================================================================


class TestOtherArrayReplacement:
    """All arrays except setup.services are replaced by repo when repo sets them."""

    def test_hooks_array_replaced_not_merged(self) -> None:
        preset = {"hooks": {"PreToolUse": ["./preset-hook.sh"]}}
        repo = {"hooks": {"PreToolUse": ["./my-hook.sh"]}}
        result = merge(preset, repo)
        assert result["hooks"]["PreToolUse"] == ["./my-hook.sh"]

    def test_hooks_absent_in_repo_uses_preset(self) -> None:
        preset = {"hooks": {"Stop": ["./cleanup.sh"]}}
        repo = {}
        result = merge(preset, repo)
        assert result["hooks"]["Stop"] == ["./cleanup.sh"]

    def test_hooks_repo_adds_new_event(self) -> None:
        preset = {"hooks": {"PreToolUse": ["./preset.sh"]}}
        repo = {"hooks": {"Stop": ["./stop.sh"]}}
        result = merge(preset, repo)
        assert result["hooks"]["PreToolUse"] == ["./preset.sh"]
        assert result["hooks"]["Stop"] == ["./stop.sh"]

    def test_arbitrary_nested_array_replaced(self) -> None:
        preset = {"settings": {"allowed": ["x", "y"]}}
        repo = {"settings": {"allowed": ["z"]}}
        result = merge(preset, repo)
        assert result["settings"]["allowed"] == ["z"]


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdgeCases:
    """Empty inputs, single-side inputs, type errors."""

    def test_empty_preset_returns_repo(self) -> None:
        repo = {"version": "1.0", "extends": "default"}
        result = merge({}, repo)
        assert result == repo

    def test_empty_repo_returns_preset(self) -> None:
        preset = {"version": "1.0", "agents": {"eng": {"model": "haiku"}}}
        result = merge(preset, {})
        assert result == preset

    def test_both_empty(self) -> None:
        assert merge({}, {}) == {}

    def test_non_dict_preset_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="preset must be a dict"):
            deep_merge("not-a-dict", {})  # type: ignore[arg-type]

    def test_non_dict_repo_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="repo must be a dict"):
            deep_merge({}, ["not", "a", "dict"])  # type: ignore[arg-type]

    def test_result_is_independent_copy(self) -> None:
        """Mutating the result must not affect preset or repo."""
        preset = {"agents": {"eng": {"model": "haiku"}}}
        repo = {"agents": {"eng": {"color": "blue"}}}
        result = merge(preset, repo)
        result["agents"]["eng"]["model"] = "MUTATED"
        assert preset["agents"]["eng"]["model"] == "haiku"

    def test_large_nested_config(self) -> None:
        """Realistic full-manifest merge."""
        preset = {
            "version": "1.0",
            "agents": {
                "engineer": {"model": "haiku", "color": "green", "max_tokens": 4096},
                "reviewer": {"model": "haiku"},
            },
            "hooks": {
                "PreToolUse": ["./preset-pre.sh"],
                "Stop": ["./preset-stop.sh"],
            },
            "settings": {
                "permissions": {"additionalDirectories": ["~/shared"]},
                "model": "claude-haiku-4-5",
            },
            "setup": {"services": ["kuzu-memory", "mcp-ticketer"]},
        }
        repo = {
            "version": "1.0",
            "extends": "acme",
            "agents": {
                "engineer": {"model": "sonnet", "color": "blue"},
                "data-analyst": {"model": "sonnet"},
            },
            "hooks": {
                "PreToolUse": ["./repo-pre.sh"],
            },
            "settings": {
                "permissions": {"mode": "strict"},
            },
            "setup": {"services": ["duetto-mcp"]},
        }
        result = merge(preset, repo)

        # version: repo wins
        assert result["version"] == "1.0"

        # agents: deep merge
        assert result["agents"]["engineer"]["model"] == "sonnet"
        assert result["agents"]["engineer"]["color"] == "blue"
        assert result["agents"]["engineer"]["max_tokens"] == 4096
        assert result["agents"]["reviewer"]["model"] == "haiku"
        assert result["agents"]["data-analyst"]["model"] == "sonnet"

        # hooks: PreToolUse replaced, Stop kept from preset
        assert result["hooks"]["PreToolUse"] == ["./repo-pre.sh"]
        assert result["hooks"]["Stop"] == ["./preset-stop.sh"]

        # settings: deep merge
        assert result["settings"]["permissions"]["additionalDirectories"] == [
            "~/shared"
        ]
        assert result["settings"]["permissions"]["mode"] == "strict"
        assert result["settings"]["model"] == "claude-haiku-4-5"

        # setup.services: union
        assert result["setup"]["services"] == [
            "kuzu-memory",
            "mcp-ticketer",
            "duetto-mcp",
        ]


# ===========================================================================
# _union_merge unit tests
# ===========================================================================


class TestUnionMerge:
    """Direct tests for the _union_merge helper."""

    def test_disjoint_lists(self) -> None:
        assert _union_merge(["a", "b"], ["c", "d"]) == ["a", "b", "c", "d"]

    def test_overlapping_lists(self) -> None:
        assert _union_merge(["a", "b"], ["b", "c"]) == ["a", "b", "c"]

    def test_preset_first_order(self) -> None:
        assert _union_merge(["x"], ["y", "x"]) == ["x", "y"]

    def test_both_empty(self) -> None:
        assert _union_merge([], []) == []

    def test_empty_preset(self) -> None:
        assert _union_merge([], ["a", "b"]) == ["a", "b"]

    def test_empty_repo(self) -> None:
        assert _union_merge(["a", "b"], []) == ["a", "b"]

    def test_all_duplicates(self) -> None:
        assert _union_merge(["x", "y"], ["x", "y"]) == ["x", "y"]
