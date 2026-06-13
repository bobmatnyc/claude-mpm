"""Tests for FrameworkLoader trusty-search index freshness wiring (#649).

Why: When trusty-search is ON, a missing/empty/stale index silently degrades
code search. The loader must (a) check the daemon's OWN index status, (b) fire a
BACKGROUND reindex when not fresh, and (c) annotate the trusty-search row — all
fail-open so framework assembly never breaks and startup is never blocked.

What: Exercises ``_trusty_search_index_note`` and the integration through
``_generate_tool_status_section`` against mocked freshness helpers, asserting the
note text and whether the reindex trigger fired for fresh / missing / stale /
error cases.

Test: ``uv run pytest tests/test_framework_loader_index_freshness.py``.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.services import trusty_status


def _stub_loader():
    """Minimal stand-in exposing what the freshness methods touch: ``logger`` and
    the real ``_resolve_reindex_id`` (a staticmethod ``_trusty_search_index_note``
    calls via ``self``)."""
    return SimpleNamespace(
        logger=logging.getLogger("test_index_freshness"),
        _resolve_reindex_id=FrameworkLoader._resolve_reindex_id,
    )


def _patch_freshness(monkeypatch, *, status, missing, stale):
    """Patch the four trusty_status symbols the loader imports, and record any
    reindex trigger calls. Returns the list that captures triggered index IDs."""
    triggered: list[str] = []

    monkeypatch.setattr(
        trusty_status, "get_trusty_search_index_status", lambda cwd=None: status
    )
    monkeypatch.setattr(trusty_status, "is_index_missing_or_empty", lambda s: missing)
    monkeypatch.setattr(trusty_status, "is_index_stale", lambda s: stale)
    monkeypatch.setattr(
        trusty_status,
        "trigger_trusty_search_reindex",
        lambda index_id, cwd=None: triggered.append(index_id) or True,
    )
    return triggered


class TestIndexNote:
    def test_fresh_no_note_no_reindex(self, monkeypatch):
        """Fresh index → empty note and NO reindex fired."""
        triggered = _patch_freshness(
            monkeypatch,
            status={"index_id": "claude-mpm", "chunk_count": 100},
            missing=False,
            stale=False,
        )
        note = FrameworkLoader._trusty_search_index_note(_stub_loader())
        assert note == ""
        assert triggered == []

    def test_missing_empty_note_and_reindex(self, monkeypatch):
        """Missing/empty index → note + reindex fired with the resolved ID."""
        triggered = _patch_freshness(
            monkeypatch,
            status={"index_id": "claude-mpm", "chunk_count": 0},
            missing=True,
            stale=False,
        )
        note = FrameworkLoader._trusty_search_index_note(_stub_loader())
        assert note == "Index not found/empty — background indexing started."
        assert triggered == ["claude-mpm"]

    def test_status_none_resolves_cwd_candidate(self, monkeypatch):
        """Wholly-missing index (status None) → reindex uses the cwd candidate."""
        # Patch only the reference used by the code under test so we do not
        # intercept unrelated Path.cwd() calls made by pytest or other code.
        import claude_mpm.core.framework_loader as _fl_mod

        monkeypatch.setattr(
            _fl_mod.Path, "cwd", lambda: Path("/Volumes/SSD1/Projects/foo")
        )
        monkeypatch.setattr(trusty_status, "_load_config", dict)
        triggered = _patch_freshness(
            monkeypatch, status=None, missing=True, stale=False
        )
        note = FrameworkLoader._trusty_search_index_note(_stub_loader())
        assert "background indexing started" in note
        assert triggered == ["foo"]  # cwd basename candidate

    def test_stale_note_and_reindex(self, monkeypatch):
        """Daemon-stale index → stale note + reindex fired."""
        triggered = _patch_freshness(
            monkeypatch,
            status={"index_id": "claude-mpm", "chunk_count": 5, "status": "error"},
            missing=False,
            stale=True,
        )
        note = FrameworkLoader._trusty_search_index_note(_stub_loader())
        assert note == "Index may be stale — background reindex started."
        assert triggered == ["claude-mpm"]

    def test_error_fails_open(self, monkeypatch):
        """Any exception in the freshness path → empty note, no reindex, no raise."""

        def boom(cwd=None):
            raise OSError("daemon unreachable")

        monkeypatch.setattr(trusty_status, "get_trusty_search_index_status", boom)
        note = FrameworkLoader._trusty_search_index_note(_stub_loader())
        assert note == ""


class TestResolveReindexId:
    def test_prefers_status_index_id(self):
        rid = FrameworkLoader._resolve_reindex_id({"index_id": "my-index"})
        assert rid == "my-index"

    def test_none_status_falls_back_to_cwd_candidate(self, monkeypatch):
        # Patch only the reference used by the code under test so we do not
        # intercept unrelated Path.cwd() calls made by pytest or other code.
        import claude_mpm.core.framework_loader as _fl_mod

        monkeypatch.setattr(
            _fl_mod.Path, "cwd", lambda: Path("/Volumes/SSD1/Projects/bar")
        )
        monkeypatch.setattr(trusty_status, "_load_config", dict)
        assert FrameworkLoader._resolve_reindex_id(None) == "bar"


class TestSectionIntegration:
    """The note must appear ON the trusty-search row in the rendered block."""

    def _render(self, monkeypatch, *, note):
        _caps = {
            "trusty-memory": "absent",
            "trusty-search": "on",
            "trusty-analyze": "absent",
            "trusty-review": "absent",
        }
        # Patch both the live-probe variant (tried first) AND the config-only
        # fallback so _generate_tool_status_section sees trusty-search as "on"
        # regardless of whether an ambient daemon is running in CI.
        monkeypatch.setattr(
            trusty_status,
            "get_trusty_capabilities_live",
            lambda: _caps,
        )
        monkeypatch.setattr(
            trusty_status,
            "get_trusty_capabilities",
            lambda: _caps,
        )
        stub = _stub_loader()
        # _generate_tool_status_section calls self._trusty_search_index_note();
        # bind a fixed return on the stub so we test only the row-rendering wiring.
        stub._trusty_search_index_note = lambda: note
        return FrameworkLoader._generate_tool_status_section(stub)

    def test_note_appended_to_search_row(self, monkeypatch):
        block = self._render(
            monkeypatch, note="Index not found/empty — background indexing started."
        )
        search_row = next(
            line for line in block.splitlines() if "| trusty-search |" in line
        )
        assert "background indexing started" in search_row
        assert "| ON |" in search_row

    def test_no_note_leaves_row_clean(self, monkeypatch):
        block = self._render(monkeypatch, note="")
        search_row = next(
            line for line in block.splitlines() if "| trusty-search |" in line
        )
        assert "background" not in search_row
        assert "stale" not in search_row
