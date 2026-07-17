"""Tests for the global ``~/.claude/`` artifact cleanup (issue #924).

Coverage:
1. MPM-owned agent files (frontmatter marker) are removed; user files kept.
2. ``claude-mpm*`` output-styles are removed; other styles kept.
3. MPM-managed statusline.sh (marker) is removed; unmarked script kept.
4. MPM-owned settings.json keys are stripped; unrelated keys and user Stop
   hooks preserved.
5. ``dry_run=True`` reports without touching the filesystem.
6. Empty ``~/.claude/`` is a clean no-op.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from claude_mpm.cli.commands.uninstall_global import run_global_cleanup

if TYPE_CHECKING:
    from pathlib import Path


def _seed(claude_dir: Path) -> None:
    """Populate a fake ~/.claude/ with a mix of MPM and non-MPM artifacts."""
    (claude_dir / "agents").mkdir(parents=True)
    (claude_dir / "output-styles").mkdir(parents=True)
    (claude_dir / "hooks" / "scripts").mkdir(parents=True)

    # MPM-owned agents (each marker variant) + one user-authored agent.
    (claude_dir / "agents" / "ops.md").write_text(
        "---\nname: ops\nauthor: claude-mpm\n---\nbody"
    )
    (claude_dir / "agents" / "cat.md").write_text(
        "---\nname: cat\ncategory: claude-mpm\n---\nbody"
    )
    (claude_dir / "agents" / "ext.md").write_text("---\nsource: external\n---\nx")
    (claude_dir / "agents" / "mine.md").write_text(
        "---\nname: mine\nauthor: someone-else\n---\nbody"
    )

    # Output styles.
    (claude_dir / "output-styles" / "claude-mpm.md").write_text("x")
    (claude_dir / "output-styles" / "other.md").write_text("x")

    # Statusline script (MPM-managed marker).
    (claude_dir / "hooks" / "scripts" / "statusline.sh").write_text(
        "#!/bin/bash\n# claude-mpm-managed: yes\n"
    )

    # Settings with MPM-owned keys + user-owned entries to preserve.
    settings = {
        "outputStyle": "claude_mpm",
        "statusLine": {"command": "/x/statusline.sh"},
        "spinnerVerbs": {"mode": "replace"},
        "_mpm_spinner_version": "1.0",
        "keepme": True,
        "hooks": {
            "Stop": [
                {
                    "matcher": "*",
                    "hooks": [
                        {"command": "statusline.sh --clear"},
                        {"command": "user-hook"},
                    ],
                }
            ],
            "PreToolUse": [{"matcher": "Edit", "hooks": [{"command": "keep"}]}],
        },
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings))


def test_dry_run_reports_without_deleting(tmp_path: Path) -> None:
    claude_dir = tmp_path / ".claude"
    _seed(claude_dir)

    summary = run_global_cleanup(claude_dir=claude_dir, dry_run=True)

    assert summary.dry_run is True
    assert summary.total > 0
    # Nothing actually removed.
    assert (claude_dir / "agents" / "ops.md").exists()
    assert (claude_dir / "output-styles" / "claude-mpm.md").exists()
    assert (claude_dir / "hooks" / "scripts" / "statusline.sh").exists()
    settings = json.loads((claude_dir / "settings.json").read_text())
    assert settings["outputStyle"] == "claude_mpm"


def test_removes_only_mpm_agents(tmp_path: Path) -> None:
    claude_dir = tmp_path / ".claude"
    _seed(claude_dir)

    run_global_cleanup(claude_dir=claude_dir, dry_run=False)

    assert not (claude_dir / "agents" / "ops.md").exists()
    assert not (claude_dir / "agents" / "cat.md").exists()
    assert not (claude_dir / "agents" / "ext.md").exists()
    # User-authored agent is preserved.
    assert (claude_dir / "agents" / "mine.md").exists()


def test_removes_only_mpm_output_styles(tmp_path: Path) -> None:
    claude_dir = tmp_path / ".claude"
    _seed(claude_dir)

    run_global_cleanup(claude_dir=claude_dir, dry_run=False)

    assert not (claude_dir / "output-styles" / "claude-mpm.md").exists()
    assert (claude_dir / "output-styles" / "other.md").exists()


def test_removes_marked_statusline_script(tmp_path: Path) -> None:
    claude_dir = tmp_path / ".claude"
    _seed(claude_dir)

    run_global_cleanup(claude_dir=claude_dir, dry_run=False)
    assert not (claude_dir / "hooks" / "scripts" / "statusline.sh").exists()


def test_unmarked_statusline_script_preserved(tmp_path: Path) -> None:
    claude_dir = tmp_path / ".claude"
    (claude_dir / "hooks" / "scripts").mkdir(parents=True)
    script = claude_dir / "hooks" / "scripts" / "statusline.sh"
    script.write_text("#!/bin/bash\necho user-owned\n")

    run_global_cleanup(claude_dir=claude_dir, dry_run=False)
    assert script.exists()


def test_strips_mpm_settings_keys_preserves_user(tmp_path: Path) -> None:
    claude_dir = tmp_path / ".claude"
    _seed(claude_dir)

    run_global_cleanup(claude_dir=claude_dir, dry_run=False)

    settings = json.loads((claude_dir / "settings.json").read_text())
    assert "outputStyle" not in settings
    assert "statusLine" not in settings
    assert "spinnerVerbs" not in settings
    assert "_mpm_spinner_version" not in settings
    # Unrelated keys preserved.
    assert settings["keepme"] is True
    # PreToolUse untouched; Stop keeps only the user hook (statusline hook pruned).
    assert settings["hooks"]["PreToolUse"] == [
        {"matcher": "Edit", "hooks": [{"command": "keep"}]}
    ]
    stop_hooks = settings["hooks"]["Stop"][0]["hooks"]
    assert stop_hooks == [{"command": "user-hook"}]


def test_preserves_user_only_outputstyle(tmp_path: Path) -> None:
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / "settings.json").write_text(json.dumps({"outputStyle": "my_style"}))

    run_global_cleanup(claude_dir=claude_dir, dry_run=False)

    settings = json.loads((claude_dir / "settings.json").read_text())
    assert settings["outputStyle"] == "my_style"


def test_empty_claude_dir_is_noop(tmp_path: Path) -> None:
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    summary = run_global_cleanup(claude_dir=claude_dir, dry_run=False)
    assert summary.total == 0
