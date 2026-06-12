"""Tests for the trusty-search / trusty-memory autodetect migration.

These tests deliberately mock ``shutil.which``, the addr-file resolver, and
the HTTP health probe so they never depend on a real daemon being installed
on the test runner or on real ``~/.trusty-*/http_addr`` files existing.
"""

from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003 - used at runtime in fixtures & call sites
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from collections.abc import Callable

import pytest

from claude_mpm.migrations import migrate_trusty_autodetect as mod

# Capture the real palace helper BEFORE the autouse fixture stubs it, so the
# dedicated palace tests can re-install the genuine implementation.
_REAL_ENSURE_PALACE = mod._ensure_palace


@pytest.fixture(autouse=True)
def _isolate_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralize palace creation + hook injection for the .mcp.json tests.

    The autodetect migration now also creates a palace and injects Claude Code
    hooks once a daemon is healthy. The existing tests in this module only
    assert ``.mcp.json`` behavior, so we stub those two side effects out by
    default (dedicated tests below patch them back in to assert their behavior)
    and ensure no opt-out env var leaks in from the host environment.
    """
    from claude_mpm.services import trusty_hooks

    monkeypatch.delenv("CLAUDE_MPM_NO_TRUSTY_AUTO_LINK", raising=False)
    monkeypatch.setattr(mod, "_ensure_palace", lambda *a, **k: None)
    # inject_trusty_hooks is imported lazily inside run_migration, so patch it
    # on its source module rather than on ``mod``.
    monkeypatch.setattr(trusty_hooks, "inject_trusty_hooks", lambda *a, **k: False)


def _make_which(installed: set[str]) -> Callable[[str], str | None]:
    """Return a ``shutil.which`` stand-in matching the given binary set."""

    def fake_which(name: str) -> str | None:
        return f"/fake/bin/{name}" if name in installed else None

    return fake_which


def _fake_resolve_base_url(_: Path, fallback_addr: str) -> str:
    """Deterministic addr resolver: always returns the fallback.

    Avoids depending on real ``~/.trusty-*/http_addr`` files on the test
    runner.
    """
    return f"http://{fallback_addr}"


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Empty project directory (no pre-existing .mcp.json)."""
    return tmp_path


def test_writes_entries_when_both_daemons_healthy(project_dir: Path) -> None:
    """Both binaries on PATH + both daemons healthy → both entries written."""
    with (
        patch.object(
            mod.shutil,
            "which",
            side_effect=_make_which({"trusty-search", "trusty-memory"}),
        ),
        patch.object(mod, "_resolve_base_url", side_effect=_fake_resolve_base_url),
        patch.object(mod, "_http_health_check", return_value=True),
    ):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is True

    mcp_json = project_dir / ".mcp.json"
    assert mcp_json.exists()

    config = json.loads(mcp_json.read_text())
    servers = config["mcpServers"]

    assert servers["trusty-search"] == {
        "type": "stdio",
        "command": "trusty-search",
        "args": ["serve"],
    }
    assert servers["trusty-memory"] == {
        "type": "stdio",
        "command": "trusty-memory-mcp-bridge",
        "args": [],
    }


def test_no_op_when_daemons_not_running(project_dir: Path) -> None:
    """Binary present but health probe fails → no file written, no exception."""
    with (
        patch.object(
            mod.shutil,
            "which",
            side_effect=_make_which({"trusty-search", "trusty-memory"}),
        ),
        patch.object(mod, "_resolve_base_url", side_effect=_fake_resolve_base_url),
        patch.object(mod, "_http_health_check", return_value=False),
    ):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is False
    assert not (project_dir / ".mcp.json").exists()


def test_no_op_when_binaries_missing(project_dir: Path) -> None:
    """No binary on PATH → skip without probing HTTP or reading addr files."""
    probe_called: list[str] = []
    resolve_called: list[Path] = []

    def tracking_probe(url: str) -> bool:
        probe_called.append(url)
        return True

    def tracking_resolve(addr_file: Path, fallback_addr: str) -> str:
        resolve_called.append(addr_file)
        return f"http://{fallback_addr}"

    with (
        patch.object(mod.shutil, "which", side_effect=_make_which(set())),
        patch.object(mod, "_resolve_base_url", side_effect=tracking_resolve),
        patch.object(mod, "_http_health_check", side_effect=tracking_probe),
    ):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is False
    assert probe_called == [], "Health probe should be skipped when binary missing"
    assert resolve_called == [], "addr resolution should be skipped when binary missing"
    assert not (project_dir / ".mcp.json").exists()


def test_idempotent_when_entries_already_present(project_dir: Path) -> None:
    """Existing entries → migration is a no-op and returns False."""
    existing = {
        "mcpServers": {
            "trusty-search": {
                "type": "stdio",
                "command": "trusty-search",
                "args": ["serve"],
            },
            "trusty-memory": {
                "type": "stdio",
                "command": "trusty-memory-mcp-bridge",
                "args": [],
            },
        }
    }
    mcp_path = project_dir / ".mcp.json"
    mcp_path.write_text(json.dumps(existing, indent=2) + "\n")
    original_contents = mcp_path.read_text()

    with (
        patch.object(
            mod.shutil,
            "which",
            side_effect=_make_which({"trusty-search", "trusty-memory"}),
        ),
        patch.object(mod, "_resolve_base_url", side_effect=_fake_resolve_base_url),
        patch.object(mod, "_http_health_check", return_value=True),
    ):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is False
    # File untouched.
    assert mcp_path.read_text() == original_contents


def test_partial_injection_preserves_unrelated_entries(project_dir: Path) -> None:
    """Only the missing daemon is added; unrelated MCP servers stay intact."""
    existing = {
        "mcpServers": {
            "trusty-search": {
                "type": "stdio",
                "command": "trusty-search",
                "args": ["serve"],
            },
            "some-other-server": {"type": "stdio", "command": "whatever"},
        }
    }
    mcp_path = project_dir / ".mcp.json"
    mcp_path.write_text(json.dumps(existing, indent=2) + "\n")

    with (
        patch.object(
            mod.shutil,
            "which",
            side_effect=_make_which({"trusty-search", "trusty-memory"}),
        ),
        patch.object(mod, "_resolve_base_url", side_effect=_fake_resolve_base_url),
        patch.object(mod, "_http_health_check", return_value=True),
    ):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is True
    config = json.loads(mcp_path.read_text())
    servers = config["mcpServers"]
    assert "trusty-memory" in servers
    assert "trusty-search" in servers
    # Pre-existing unrelated entry must survive.
    assert servers["some-other-server"] == {"type": "stdio", "command": "whatever"}


# ---------------------------------------------------------------------------
# Palace auto-create
# ---------------------------------------------------------------------------


def _detect_only_memory() -> Callable[[str], str | None]:
    """which() that reports only trusty-memory installed."""
    return _make_which({"trusty-memory"})


def test_palace_created_when_absent(project_dir: Path) -> None:
    """Healthy trusty-memory + no matching palace → POST issued once."""
    calls: list[tuple[str, str]] = []

    class _Resp:
        status = 200

        def read(self) -> bytes:
            return b"[]"  # GET /palaces → empty list

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *a: object) -> None:
            return None

    def fake_urlopen(req, timeout=5):  # noqa: ANN001, ARG001
        calls.append((req.get_method(), req.full_url))
        return _Resp()

    with (
        patch.object(mod.shutil, "which", side_effect=_detect_only_memory()),
        patch.object(mod, "_resolve_base_url", side_effect=_fake_resolve_base_url),
        patch.object(mod, "_http_health_check", return_value=True),
        patch.object(mod, "_ensure_palace", wraps=_REAL_ENSURE_PALACE),
        patch.object(mod.urllib.request, "urlopen", side_effect=fake_urlopen),
    ):
        mod.run_migration(project_dir=project_dir)

    methods = [m for m, _ in calls]
    assert "GET" in methods, "must list palaces first"
    assert "POST" in methods, "must create palace when absent"


def test_palace_post_includes_cwd(project_dir: Path) -> None:
    """Palace POST body must include ``cwd`` so the daemon validates against the
    project directory, not its own process cwd (which is typically ``~`` or
    ``/`` and fails the daemon's project-root enforcement).
    """
    post_bodies: list[dict] = []

    class _Resp:
        status = 200

        def read(self) -> bytes:
            return b"[]"  # GET /palaces → empty list (not present)

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *a: object) -> None:
            return None

    def fake_urlopen(req, timeout=5):  # noqa: ANN001, ARG001
        if req.get_method() == "POST":
            post_bodies.append(json.loads(req.data))
        return _Resp()

    with (
        patch.object(mod.shutil, "which", side_effect=_detect_only_memory()),
        patch.object(mod, "_resolve_base_url", side_effect=_fake_resolve_base_url),
        patch.object(mod, "_http_health_check", return_value=True),
        patch.object(mod, "_ensure_palace", wraps=_REAL_ENSURE_PALACE),
        patch.object(mod.urllib.request, "urlopen", side_effect=fake_urlopen),
    ):
        mod.run_migration(project_dir=project_dir)

    assert len(post_bodies) == 1, f"expected one POST, got: {post_bodies}"
    body = post_bodies[0]
    assert "cwd" in body, (
        "POST body must include 'cwd' for daemon palace-name enforcement; "
        f"got keys: {list(body.keys())}"
    )
    assert body["cwd"] == str(project_dir), (
        f"cwd must be the project_dir path, got: {body['cwd']!r}"
    )


def test_palace_not_created_when_present(project_dir: Path) -> None:
    """Healthy trusty-memory + matching palace exists → no POST (idempotent)."""
    palace_name = project_dir.name
    payload = json.dumps([{"name": palace_name}]).encode("utf-8")
    calls: list[str] = []

    class _Resp:
        status = 200

        def __init__(self, body: bytes) -> None:
            self._body = body

        def read(self) -> bytes:
            return self._body

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *a: object) -> None:
            return None

    def fake_urlopen(req, timeout=5):  # noqa: ANN001, ARG001
        calls.append(req.get_method())
        return _Resp(payload)

    with (
        patch.object(mod.shutil, "which", side_effect=_detect_only_memory()),
        patch.object(mod, "_resolve_base_url", side_effect=_fake_resolve_base_url),
        patch.object(mod, "_http_health_check", return_value=True),
        patch.object(mod, "_ensure_palace", wraps=_REAL_ENSURE_PALACE),
        patch.object(mod.urllib.request, "urlopen", side_effect=fake_urlopen),
    ):
        mod.run_migration(project_dir=project_dir)

    assert "GET" in calls
    assert "POST" not in calls, "palace already present — must not re-create"


def test_palace_failure_is_non_fatal(project_dir: Path) -> None:
    """Palace HTTP errors never raise and never block the .mcp.json write."""

    def boom(req, timeout=5):  # noqa: ANN001, ARG001
        raise OSError("connection refused")

    with (
        patch.object(mod.shutil, "which", side_effect=_detect_only_memory()),
        patch.object(mod, "_resolve_base_url", side_effect=_fake_resolve_base_url),
        patch.object(mod, "_http_health_check", return_value=True),
        patch.object(mod, "_ensure_palace", wraps=_REAL_ENSURE_PALACE),
        patch.object(mod.urllib.request, "urlopen", side_effect=boom),
    ):
        changed = mod.run_migration(project_dir=project_dir)

    # .mcp.json still written despite palace failure.
    assert changed is True
    config = json.loads((project_dir / ".mcp.json").read_text())
    assert "trusty-memory" in config["mcpServers"]


# ---------------------------------------------------------------------------
# Opt-out
# ---------------------------------------------------------------------------


def test_opt_out_via_env_var(
    project_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLAUDE_MPM_NO_TRUSTY_AUTO_LINK truthy → full no-op, no detection."""
    monkeypatch.setenv("CLAUDE_MPM_NO_TRUSTY_AUTO_LINK", "1")
    which_calls: list[str] = []

    def tracking_which(name: str) -> str | None:
        which_calls.append(name)
        return f"/fake/bin/{name}"

    with patch.object(mod.shutil, "which", side_effect=tracking_which):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is False
    assert which_calls == [], "opt-out must short-circuit before detection"
    assert not (project_dir / ".mcp.json").exists()


def test_opt_out_via_config(project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """configuration.yaml trusty.auto_link: false → no-op."""
    monkeypatch.delenv("CLAUDE_MPM_NO_TRUSTY_AUTO_LINK", raising=False)
    cfg_dir = project_dir / ".claude-mpm"
    cfg_dir.mkdir()
    (cfg_dir / "configuration.yaml").write_text("trusty:\n  auto_link: false\n")

    with (
        patch.object(
            mod.shutil,
            "which",
            side_effect=_make_which({"trusty-memory", "trusty-search"}),
        ),
        patch.object(mod, "_resolve_base_url", side_effect=_fake_resolve_base_url),
        patch.object(mod, "_http_health_check", return_value=True),
    ):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is False
    assert not (project_dir / ".mcp.json").exists()


def test_config_auto_link_true_does_not_block(
    project_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """auto_link: true (explicit) still runs detection normally."""
    monkeypatch.delenv("CLAUDE_MPM_NO_TRUSTY_AUTO_LINK", raising=False)
    cfg_dir = project_dir / ".claude-mpm"
    cfg_dir.mkdir()
    (cfg_dir / "configuration.yaml").write_text("trusty:\n  auto_link: true\n")

    with (
        patch.object(mod.shutil, "which", side_effect=_make_which({"trusty-memory"})),
        patch.object(mod, "_resolve_base_url", side_effect=_fake_resolve_base_url),
        patch.object(mod, "_http_health_check", return_value=True),
    ):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is True
    assert (project_dir / ".mcp.json").exists()


# ---------------------------------------------------------------------------
# Hook injection wiring
# ---------------------------------------------------------------------------


def test_hooks_injected_for_detected_services(
    project_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The migration forwards detected service names to inject_trusty_hooks."""
    from claude_mpm.services import trusty_hooks

    captured: dict[str, object] = {}

    def fake_inject(services, project_dir=None, report=None):  # noqa: ANN001
        captured["services"] = list(services)
        captured["project_dir"] = project_dir
        return True

    monkeypatch.setattr(trusty_hooks, "inject_trusty_hooks", fake_inject)

    with (
        patch.object(
            mod.shutil,
            "which",
            side_effect=_make_which({"trusty-memory", "trusty-search"}),
        ),
        patch.object(mod, "_resolve_base_url", side_effect=_fake_resolve_base_url),
        patch.object(mod, "_http_health_check", return_value=True),
    ):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is True
    assert set(captured["services"]) == {"trusty-memory", "trusty-search"}
    assert captured["project_dir"] == project_dir


def test_no_hooks_or_palace_when_binaries_missing(
    project_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No binary on PATH → no palace HTTP, no hook injection, no settings."""
    from claude_mpm.services import trusty_hooks

    palace_calls: list[object] = []
    hook_calls: list[object] = []

    monkeypatch.setattr(mod, "_ensure_palace", lambda *a, **k: palace_calls.append(a))
    monkeypatch.setattr(
        trusty_hooks,
        "inject_trusty_hooks",
        lambda *a, **k: hook_calls.append(a) or False,
    )

    with patch.object(mod.shutil, "which", side_effect=_make_which(set())):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is False
    assert palace_calls == []
    assert hook_calls == []
    assert not (project_dir / ".mcp.json").exists()


# --------------------------------------------------------------------------
# trusty-review (review-on-demand): MCP entry only, no palace, no hooks.
# --------------------------------------------------------------------------


def _service_descriptor(name: str) -> dict[str, object]:
    """Return the _SERVICES descriptor with the given name (asserts presence)."""
    for svc in mod._SERVICES:
        if svc["name"] == name:
            return svc
    raise AssertionError(f"{name} not found in _SERVICES")


def test_trusty_review_registered_in_services() -> None:
    """trusty-review is a known autodetect service with jsonrpc detection mode."""
    svc = _service_descriptor("trusty-review")
    assert svc["binary"] == "trusty-review"
    # trusty-review is review-on-demand — no HTTP daemon, so no fallback_addr.
    assert "fallback_addr" not in svc
    assert svc.get("detect") == "jsonrpc"
    assert svc["mcp_entry"] == {
        "type": "stdio",
        "command": "trusty-review",
        "args": ["serve", "--stdio"],
        "env": {"TRUSTY_REVIEW_AUTH_MODE": "cli"},
    }


def test_trusty_review_env_holds_no_secrets() -> None:
    """The auto-wired env must NEVER carry AWS keys / GITHUB_TOKEN — those are
    inherited from the Claude Code process environment, not written to disk."""
    env = _service_descriptor("trusty-review")["mcp_entry"]["env"]
    forbidden = {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "GITHUB_TOKEN",
        "TRUSTY_SEARCH_INDEX",
    }
    assert forbidden.isdisjoint(env.keys())
    assert env == {"TRUSTY_REVIEW_AUTH_MODE": "cli"}


def test_trusty_review_wired_without_palace_or_hooks(
    project_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Healthy trusty-review → .mcp.json entry written via jsonrpc probe, but
    NO palace created and NO trusty-review hooks injected (it has no
    _TRUSTY_HOOK_SPECS entry)."""
    from claude_mpm.services import trusty_hooks

    palace_calls: list[object] = []
    hook_services: list[object] = []

    monkeypatch.setattr(mod, "_ensure_palace", lambda *a, **k: palace_calls.append(a))
    monkeypatch.setattr(
        trusty_hooks,
        "inject_trusty_hooks",
        lambda services, **k: hook_services.append(list(services)) or False,
    )

    with (
        patch.object(mod.shutil, "which", side_effect=_make_which({"trusty-review"})),
        # trusty-review uses jsonrpc detection — mock _probe_mcp_stdio, not
        # _http_health_check / _resolve_base_url.
        patch.object(mod, "_probe_mcp_stdio", return_value=True),
    ):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is True
    servers = json.loads((project_dir / ".mcp.json").read_text())["mcpServers"]
    assert servers["trusty-review"] == {
        "type": "stdio",
        "command": "trusty-review",
        "args": ["serve", "--stdio"],
        "env": {"TRUSTY_REVIEW_AUTH_MODE": "cli"},
    }
    # No palace was created for trusty-review (palace is memory-only).
    assert palace_calls == []
    # inject_trusty_hooks is called with trusty-review, but it has no hook spec
    # so nothing is actually injected for it.
    assert hook_services == [["trusty-review"]]


def test_trusty_review_not_wired_when_probe_fails(project_dir: Path) -> None:
    """Binary present but JSON-RPC probe returns False → entry NOT written."""
    with (
        patch.object(mod.shutil, "which", side_effect=_make_which({"trusty-review"})),
        patch.object(mod, "_probe_mcp_stdio", return_value=False),
    ):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is False
    assert not (project_dir / ".mcp.json").exists()


def test_trusty_review_idempotent_when_already_present(project_dir: Path) -> None:
    """trusty-review entry already in .mcp.json → probe not called, no-op."""
    existing = {
        "mcpServers": {
            "trusty-review": {
                "type": "stdio",
                "command": "trusty-review",
                "args": ["serve", "--stdio"],
                "env": {"TRUSTY_REVIEW_AUTH_MODE": "cli"},
            }
        }
    }
    mcp_path = project_dir / ".mcp.json"
    mcp_path.write_text(json.dumps(existing, indent=2) + "\n")
    original_contents = mcp_path.read_text()

    probe_called: list[list[str]] = []

    def tracking_probe(cmd: list[str], **kwargs: object) -> bool:
        probe_called.append(cmd)
        return True

    with (
        patch.object(mod.shutil, "which", side_effect=_make_which({"trusty-review"})),
        patch.object(mod, "_probe_mcp_stdio", side_effect=tracking_probe),
    ):
        changed = mod.run_migration(project_dir=project_dir)

    # The entry was already present so no probe subprocess should have been
    # spawned at all (Fix 1: skip probe when service already in .mcp.json).
    assert probe_called == [], (
        f"_probe_mcp_stdio must NOT be called when entry already present; "
        f"got calls: {probe_called}"
    )
    assert changed is False
    assert mcp_path.read_text() == original_contents


def test_http_services_unaffected_by_jsonrpc_mode(project_dir: Path) -> None:
    """http-mode services (trusty-search, trusty-memory) still work via the
    existing HTTP health-check path when trusty-review's jsonrpc probe fires."""
    http_probe_called: list[str] = []
    jsonrpc_probe_called: list[list[str]] = []

    def tracking_http(url: str, **kwargs: object) -> bool:
        http_probe_called.append(url)
        return True

    def tracking_jsonrpc(cmd: list[str], **kwargs: object) -> bool:
        jsonrpc_probe_called.append(cmd)
        return True

    with (
        patch.object(
            mod.shutil,
            "which",
            side_effect=_make_which(
                {"trusty-search", "trusty-memory", "trusty-review"}
            ),
        ),
        patch.object(mod, "_resolve_base_url", side_effect=_fake_resolve_base_url),
        patch.object(mod, "_http_health_check", side_effect=tracking_http),
        patch.object(mod, "_probe_mcp_stdio", side_effect=tracking_jsonrpc),
    ):
        changed = mod.run_migration(project_dir=project_dir)

    assert changed is True
    # HTTP probe called for search + memory, not review.
    assert len(http_probe_called) == 2
    assert all("/health" in url for url in http_probe_called)
    # JSON-RPC probe called only for trusty-review.
    assert len(jsonrpc_probe_called) == 1
    assert jsonrpc_probe_called[0] == ["trusty-review", "serve", "--stdio"]
    # All three entries wired.
    servers = json.loads((project_dir / ".mcp.json").read_text())["mcpServers"]
    assert set(servers.keys()) == {"trusty-search", "trusty-memory", "trusty-review"}


def test_trusty_review_has_no_hook_spec() -> None:
    """trusty-review must not declare any capture/index hooks."""
    from claude_mpm.services.trusty_hooks import _TRUSTY_HOOK_SPECS

    assert "trusty-review" not in _TRUSTY_HOOK_SPECS
