"""
Migration: Auto-configure MPM statusline in .claude/settings.json (v6.2.35).

Ensures that:
1. The statusline script is present at .claude/hooks/scripts/statusline.sh
   (creates it if missing; makes it executable).
2. A `statusLine` entry pointing to that script is present in
   .claude/settings.json (adds it if missing; leaves existing config
   untouched).

Idempotent: safe to run multiple times.  If both the script and the
settings entry already exist the migration is a no-op and returns True.
"""

import json
import logging
import stat
from pathlib import Path

logger = logging.getLogger(__name__)

# Relative path of the script inside .claude/
_SCRIPT_REL = Path("hooks") / "scripts" / "statusline.sh"

# Statusline script content (identical to the project's existing script so
# that projects that don't yet have it receive the same canonical version).
_SCRIPT_CONTENT = """\
#!/bin/bash
# claude-mpm status line
# Format: claude-mpm: <user> | <model> | <context_remaining>% | [git-info]
# Receives JSON on stdin from Claude Code

input=$(cat)

USER=$(whoami)
MODEL=$(echo "$input" | jq -r '.model.display_name // .model.id // "unknown"' 2>/dev/null || echo "unknown")
REMAINING=$(echo "$input" | jq -r '.context_window.remaining_percentage // 0' 2>/dev/null | cut -d. -f1 || echo "0")
USED=$(echo "$input" | jq -r '.context_window.used_percentage // 0' 2>/dev/null | cut -d. -f1 || echo "0")
CWD=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // ""' 2>/dev/null)

# Color context based on remaining %
if [ "$REMAINING" -lt 20 ] 2>/dev/null; then
    CTX_COLOR="\\033[31m"   # red — critical
elif [ "$REMAINING" -lt 40 ] 2>/dev/null; then
    CTX_COLOR="\\033[33m"   # yellow — warning
else
    CTX_COLOR="\\033[32m"   # green — healthy
fi
RESET="\\033[0m"

# Get git branch and ahead/behind info if in a git repo
GIT_INFO=""
if [ -n "$CWD" ] && git -C "$CWD" rev-parse --git-dir >/dev/null 2>&1; then
    BRANCH=$(git -C "$CWD" rev-parse --abbrev-ref HEAD 2>/dev/null)

    # Get ahead/behind counts relative to upstream
    AHEAD_BEHIND=$(git -C "$CWD" rev-list --left-right --count @{upstream}...HEAD 2>/dev/null)
    if [ -n "$AHEAD_BEHIND" ]; then
        BEHIND=$(echo "$AHEAD_BEHIND" | awk '{print $1}')
        AHEAD=$(echo "$AHEAD_BEHIND" | awk '{print $2}')

        AHEAD_STR=""
        BEHIND_STR=""
        [ "$AHEAD" -gt 0 ] && AHEAD_STR="↑${AHEAD}"
        [ "$BEHIND" -gt 0 ] && BEHIND_STR="↓${BEHIND}"

        if [ -n "$AHEAD_STR" ] || [ -n "$BEHIND_STR" ]; then
            GIT_INFO=" | \\033[36m${BRANCH}\\033[0m ${AHEAD_STR}${BEHIND_STR:+ }${BEHIND_STR}"
        else
            GIT_INFO=" | \\033[36m${BRANCH}\\033[0m"
        fi
    else
        GIT_INFO=" | \\033[36m${BRANCH}\\033[0m"
    fi
fi

printf "claude-mpm: %s | %s | ${CTX_COLOR}%s%% remaining${RESET}${GIT_INFO}\\n" "$USER" "$MODEL" "$REMAINING"
"""

# Default statusLine settings block to add when missing.
_DEFAULT_STATUS_LINE: dict = {
    "type": "command",
    "command": ".claude/hooks/scripts/statusline.sh",
    "padding": 1,
    "refreshInterval": 10,
}


def _ensure_script(claude_dir: Path) -> bool:
    """Ensure the statusline script exists and is executable.

    Args:
        claude_dir: Path to the .claude/ directory.

    Returns:
        True on success, False on error.
    """
    script_path = claude_dir / _SCRIPT_REL

    if script_path.exists():
        logger.debug(
            "statusline.sh already exists at %s — skipping script deploy", script_path
        )
        return True

    try:
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(_SCRIPT_CONTENT, encoding="utf-8")
        # chmod 755
        current_mode = script_path.stat().st_mode
        script_path.chmod(
            current_mode
            | stat.S_IRWXU
            | stat.S_IRGRP
            | stat.S_IXGRP
            | stat.S_IROTH
            | stat.S_IXOTH
        )
        logger.info("Created statusline.sh at %s (executable)", script_path)
    except Exception:
        logger.exception("Failed to create statusline.sh at %s", script_path)
        return False

    return True


def _ensure_settings_entry(settings_path: Path) -> bool:
    """Ensure the statusLine entry is present in settings.json.

    If the file doesn't exist it is created with just the statusLine entry.
    If it already contains a `statusLine` key the file is left unchanged.

    Args:
        settings_path: Path to .claude/settings.json.

    Returns:
        True on success, False on error.
    """
    if not settings_path.exists():
        # Create a minimal settings.json with the statusLine entry.
        try:
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings_path.write_text(
                json.dumps(
                    {"statusLine": _DEFAULT_STATUS_LINE}, indent=2, ensure_ascii=False
                )
                + "\n",
                encoding="utf-8",
            )
            logger.info(
                "Created settings.json with statusLine entry at %s", settings_path
            )
        except Exception:
            logger.exception("Failed to create settings.json at %s", settings_path)
            return False
        return True

    # File exists — read, check, maybe update.
    try:
        settings: dict = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to parse settings.json at %s", settings_path)
        return False

    if "statusLine" in settings:
        logger.debug("statusLine already present in %s — skipping", settings_path)
        return True

    settings["statusLine"] = _DEFAULT_STATUS_LINE

    try:
        settings_path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info("Added statusLine entry to %s", settings_path)
    except Exception:
        logger.exception("Failed to write settings.json at %s", settings_path)
        return False

    return True


def run_migration(installation_dir: Path | None = None) -> bool:
    """Auto-configure the MPM statusline for the current project.

    Args:
        installation_dir: Root of the project (default: cwd).

    Returns:
        True if migration completed successfully (including no-op), False on error.
    """
    project_root = installation_dir or Path.cwd()
    claude_dir = project_root / ".claude"
    settings_path = claude_dir / "settings.json"

    script_ok = _ensure_script(claude_dir)
    settings_ok = _ensure_settings_entry(settings_path)

    return script_ok and settings_ok
