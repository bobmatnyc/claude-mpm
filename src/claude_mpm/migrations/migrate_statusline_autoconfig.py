"""
Migration: Auto-configure MPM statusline at the USER level (v6.2.35, updated v6.3.2).

Operates at ``~/.claude/`` (user-global), NOT ``<project>/.claude/`` (project-scoped).

Ensures that:
1. The statusline script is present at ``~/.claude/hooks/scripts/statusline.sh``
   (creates it if missing; makes it executable; respects user customisation).
2. A ``statusLine`` entry pointing to that script (absolute path) is present in
   ``~/.claude/settings.json`` (adds it if missing; updates an existing
   MPM-owned entry to the new absolute path; leaves user-owned entries alone).
3. A Stop hook entry that calls ``statusline.sh --clear`` is present in
   ``~/.claude/settings.json`` so the bar disappears when Claude Code exits.

Ownership detection for the ``statusLine`` entry is an explicit recorded fact,
not an inference from the command string: every entry we write carries
``"_mpm": True`` (the same authoritative marker convention used for MPM hook
command entries — see ``v6_3_19_hooks_to_project_level``).  An entry is
MPM-owned if it carries that marker OR — purely as a backward-compatibility
fallback for entries written by MPM versions predating the marker — its
command contains ``statusline.sh``.  Anything else is user-authored and is
left strictly alone.

This distinction matters because "MPM wrote this entry" and "this entry points
at MPM's bundled script" are different facts that diverge under the CUSTOM
policy, where MPM writes the *user's* command into the entry.  Inferring
ownership from the command alone made MPM fail to recognise its own CUSTOM
entry on the next run, permanently freezing it (a later change to
``CLAUDE_MPM_STATUSLINE`` was silently ignored).

Project-level ``.claude/settings.json`` and ``.claude/hooks/scripts/statusline.sh``
are NEVER written by this migration.  Legacy project-level installs are left
in place — Claude Code's project-overrides-user precedence handles that
correctly — and are cleaned up by the dedicated
``migrate_statusline_user_level`` migration.

Idempotent: safe to run multiple times.

Note (v6.2.36 fix): The script was rewritten to print plain text to stdout
instead of painting via /dev/tty escape sequences.  Claude Code's statusLine
hook renders whatever the script prints to stdout in its built-in status bar;
no cursor positioning is needed or desired.
"""

import json
import logging
import os
import stat
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Opt-out / override knob
#
# WHY: Injecting a statusLine entry on every ``claude-mpm run`` is convenient
# for users who want the MPM statusline, but it silently overrides a user's
# own global or custom statusLine configuration the first time claude-mpm
# runs in a brand-new project, with no supported way to say "don't touch my
# statusline". This section adds three ways (env var, user config, project
# config; env wins, then user/project config, then default) to either
# disable management entirely or point it at a custom command instead of the
# bundled script.
# ---------------------------------------------------------------------------

# Environment variable that overrides the config-file based policy below.
# Highest precedence: if set and non-empty, it wins over configuration.yaml.
STATUSLINE_ENV_VAR = "CLAUDE_MPM_STATUSLINE"

# Case-insensitive values (after stripping whitespace) that mean "do not
# manage the statusline at all" when found in CLAUDE_MPM_STATUSLINE.
_DISABLE_ENV_VALUES = {"off", "false", "0", "disabled", "none"}


class StatuslinePolicyKind(Enum):
    """The three ways ``run_migration`` can be told to behave."""

    #: Default behavior: manage the bundled script + settings entry as before.
    MANAGED = "managed"
    #: User opted out entirely: touch nothing (script or settings).
    DISABLED = "disabled"
    #: User supplied a custom command to write into ``statusLine.command``
    #: instead of the bundled script path.
    CUSTOM = "custom"


@dataclass(frozen=True)
class StatuslinePolicy:
    """Resolved statusline management policy for a single ``run_migration`` call.

    Why: Centralizes the env-var / config-file precedence logic in one small,
    unit-testable value object instead of scattering conditionals across
    ``run_migration`` and its call sites (``cli/commands/run.py``'s direct
    call and ``update-statusline``'s force=True call both go through
    ``run_migration``, so resolving the policy in one place keeps behavior
    consistent everywhere).
    What: Holds the resolved ``kind`` plus, for ``CUSTOM``, the command string
    to write. ``source`` records where the policy came from (for debug logs).
    Test: Assert ``_resolve_statusline_policy`` returns the expected kind and
    command for each combination of env var / config file inputs.
    """

    kind: StatuslinePolicyKind
    command: str | None = None
    source: str = "default"


def _load_yaml_statusline_section(path: Path) -> dict:
    """Read the ``statusline`` mapping from a ``configuration.yaml`` file.

    Why: Reuses claude-mpm's existing YAML config file convention
    (``~/.claude-mpm/config/configuration.yaml`` and project-level
    ``<cwd>/.claude-mpm/configuration.yaml`` — see ``hooks/model_tier_hook.py``
    for the sibling per-agent-model overlay that established this pattern)
    rather than inventing a new bespoke config format for this one knob.
    What: Returns ``{}`` if the file is missing, unreadable, not a mapping, or
    has no ``statusline`` section; otherwise returns that section's dict.
    Test: Point at a YAML file with a ``statusline: {enabled: false}`` block
    and assert the returned dict is ``{"enabled": False}``.
    """
    if not path.is_file():
        return {}
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    section = data.get("statusline")
    if not isinstance(section, dict):
        return {}
    return section


def _load_statusline_config(project_dir: Path | None) -> dict:
    """Merge user-level and project-level ``statusline`` config sections.

    Why: Mirrors the overlay pattern already used for per-agent model config:
    user config first, project config overlaid on top so project-level
    settings win for duplicate keys.
    What: Returns the merged dict (e.g. ``{"enabled": False}`` or
    ``{"command": "..."}``).
    Test: Seed a user config with ``enabled: false`` and a project config with
    ``command: "foo"``; assert the merged dict has both keys.
    """
    merged: dict = {}
    user_config = Path.home() / ".claude-mpm" / "config" / "configuration.yaml"
    merged.update(_load_yaml_statusline_section(user_config))
    if project_dir is not None:
        project_config = Path(project_dir) / ".claude-mpm" / "configuration.yaml"
        merged.update(_load_yaml_statusline_section(project_config))
    return merged


def _resolve_statusline_policy(project_dir: Path | None = None) -> StatuslinePolicy:
    """Resolve the effective statusline policy from env var then config file.

    Why: Single source of truth for the opt-out/override knob, used
    consistently by ``run_migration`` (and therefore by every call site,
    since both ``cli/commands/run.py``'s direct call and ``update-statusline``
    go through it) so behavior is unit-testable in isolation and can't drift
    between call sites.
    What: Checks ``CLAUDE_MPM_STATUSLINE`` first (highest precedence): values
    in {off, false, 0, disabled, none} (case-insensitive) resolve to
    DISABLED; any other non-empty value resolves to CUSTOM with that value as
    the command. If the env var is unset/empty, falls back to the merged
    ``statusline`` section of ``configuration.yaml`` (user then project
    overlay): ``enabled: false`` resolves to DISABLED, else a non-empty
    ``command`` string resolves to CUSTOM. Otherwise resolves to MANAGED
    (today's default, unchanged behavior).
    Test: Set ``CLAUDE_MPM_STATUSLINE=off`` and assert DISABLED; set it to a
    command string and assert CUSTOM with that command; clear it and set
    config ``enabled: false`` and assert DISABLED; assert env value wins over
    a conflicting config value; assert MANAGED when nothing is set.
    """
    env_value = os.environ.get(STATUSLINE_ENV_VAR, "").strip()
    if env_value:
        if env_value.lower() in _DISABLE_ENV_VALUES:
            return StatuslinePolicy(StatuslinePolicyKind.DISABLED, source="env")
        return StatuslinePolicy(
            StatuslinePolicyKind.CUSTOM, command=env_value, source="env"
        )

    config = _load_statusline_config(project_dir)
    if config.get("enabled") is False:
        return StatuslinePolicy(StatuslinePolicyKind.DISABLED, source="config")

    command = config.get("command")
    if isinstance(command, str) and command.strip():
        return StatuslinePolicy(
            StatuslinePolicyKind.CUSTOM, command=command.strip(), source="config"
        )

    return StatuslinePolicy(StatuslinePolicyKind.MANAGED, source="default")


# Marker line that identifies an MPM-managed statusline.sh.
# Any file containing this string will be treated as an official MPM-owned
# copy and will be overwritten when the template has been updated (force mode).
_MPM_MARKER = "# claude-mpm-managed:"

# Absolute path to the user-level statusline script.  Computed once at import
# time so all defaults reference the same canonical location.
_USER_SCRIPT_PATH = Path.home() / ".claude" / "hooks" / "scripts" / "statusline.sh"

# Command string used in the Stop hook (absolute user-level path).  Matched
# substring-wise via ``_STOP_HOOK_MATCH`` so legacy project-relative
# invocations are still detected as "MPM-owned".
_STOP_HOOK_COMMAND = f"{_USER_SCRIPT_PATH} --clear"
_STOP_HOOK_MATCH = "statusline.sh --clear"

# LEGACY ownership signal only.  Substring used to identify a statusLine.command
# written by an MPM version that predates ``_MPM_OWNED_KEY``, regardless of
# whether the path is relative (``.claude/hooks/scripts/statusline.sh`` — legacy
# project-level installs) or absolute (``~/.claude/hooks/scripts/statusline.sh``).
# New entries are identified by the explicit marker instead; see
# ``_is_mpm_owned_statusline``.
_STATUSLINE_COMMAND_MATCH = "statusline.sh"

# Authoritative ownership marker stamped into every ``statusLine`` entry this
# migration writes.  Mirrors the ``"_mpm": True`` convention already used for
# MPM hook command entries (``v6_3_19_hooks_to_project_level``,
# ``migrate_dedup_hook_registrations``), so there is one project-wide way to
# say "claude-mpm wrote this settings entry".
_MPM_OWNED_KEY = "_mpm"


class StatuslineDisposition(Enum):
    """What a removal path may safely do with an existing ``statusLine`` entry.

    WHY: Every claude-mpm removal path (legacy project cleanup, global uninstall,
    the issue #924 global self-heal) needs to know more than *who owns* an entry —
    it needs to know whether the entry is MPM's to delete.  Those diverge under
    the CUSTOM policy, where MPM stamps its ownership marker onto an entry whose
    ``command`` is the *user's*, so a single boolean "is it ours?" is not enough
    to decide safely (issue #939).
    WHAT: Three mutually exclusive dispositions returned by
    ``classify_statusline_entry`` and consumed by every removal path.
    """

    #: Not MPM-owned at all — leave the entry strictly untouched.
    LEAVE = "leave"
    #: MPM's own artifact (``command`` points at the bundled ``statusline.sh``)
    #: — remove the whole entry.
    REMOVE = "remove"
    #: MPM-owned via the marker, but ``command`` is the user's (CUSTOM policy)
    #: — strip only the marker and keep the command.
    DISOWN = "disown"


def classify_statusline_entry(entry: object) -> StatuslineDisposition:
    """Decide what a removal path may do with a ``statusLine`` settings entry.

    Why: "claude-mpm owns this entry" and "this entry is claude-mpm's to delete"
    are different facts, and removal paths need the second one.  Under the CUSTOM
    policy MPM writes the *user's* command into the entry and stamps
    ``_MPM_OWNED_KEY`` on it, so treating ownership as licence to delete would
    destroy the user's own statusline configuration on uninstall (issue #939).
    What: Returns ``REMOVE`` when ``command`` points at the bundled
    ``statusline.sh`` — MPM's own artifact, true for marker-bearing MANAGED
    entries and for legacy pre-marker ones alike, which is what preserves the
    substring fallback.  Returns ``DISOWN`` when the entry carries the marker but
    its command is not ours.  Returns ``LEAVE`` for everything else, including
    non-dict values and genuinely user-authored entries.
    Test: Assert ``REMOVE`` for a bundled-script command with and without the
    marker, ``DISOWN`` for a marker-bearing custom command, and ``LEAVE`` for a
    marker-less non-bundled command and for a non-dict value.
    """
    if not isinstance(entry, dict):
        return StatuslineDisposition.LEAVE

    # Checked before the marker: a command pointing at our bundled script is
    # MPM's own artifact whether or not the entry was ever stamped, which is
    # also the backward-compatibility fallback for pre-marker entries.
    cmd = entry.get("command", "")
    if isinstance(cmd, str) and _STATUSLINE_COMMAND_MATCH in cmd:
        return StatuslineDisposition.REMOVE

    # Marker present but the command is not ours → a CUSTOM-policy entry.
    if entry.get(_MPM_OWNED_KEY) is True:
        return StatuslineDisposition.DISOWN

    return StatuslineDisposition.LEAVE


def strip_statusline_marker(entry: dict) -> bool:
    """Remove claude-mpm's ownership marker from ``entry``, leaving the rest.

    Why: The ``DISOWN`` disposition needs MPM to relinquish ownership of an entry
    whose ``command`` belongs to the user (issue #939), and every removal path
    must do that identically without reaching for the private marker constant.
    What: Deletes ``_MPM_OWNED_KEY`` from ``entry`` in place and returns True if
    it was present; returns False without mutating anything otherwise.  No other
    key — ``command`` above all — is touched.
    Test: Assert True and a marker-free dict with an intact ``command`` for a
    marker-bearing entry, and False plus an unchanged dict for one without.
    """
    if _MPM_OWNED_KEY not in entry:
        return False
    del entry[_MPM_OWNED_KEY]
    return True


def _is_mpm_owned_statusline(entry: object) -> bool:
    """Return True if a ``statusLine`` settings entry was written by claude-mpm.

    Why: Ownership must be a fact we RECORDED, not a fact we infer from the
    command string.  Under the CUSTOM policy MPM writes the user's own command
    into the entry, so "the command points at our bundled script" is false for
    entries we nonetheless own — inferring ownership from the command made MPM
    disown its own CUSTOM entry on the next run and freeze it forever.
    What: Returns True when the entry carries the explicit ``_MPM_OWNED_KEY``
    marker, or — as a backward-compatibility fallback for entries written
    before the marker existed — when its ``command`` contains
    ``_STATUSLINE_COMMAND_MATCH``.  Delegates to
    ``classify_statusline_entry`` so the ownership question and the removability
    question can never drift apart: "owned" is exactly "not ``LEAVE``".  A
    genuinely user-authored entry (no marker, non-bundled command) returns False
    and must be left untouched.
    Test: Assert True for a marker-bearing entry with an arbitrary command,
    True for a marker-less entry pointing at ``statusline.sh`` (legacy), and
    False for a marker-less entry pointing anywhere else.
    """
    return classify_statusline_entry(entry) is not StatuslineDisposition.LEAVE


# Statusline script content (byte-identical to .claude/hooks/scripts/statusline.sh
# in this repo so fresh projects receive the same canonical version).
_SCRIPT_CONTENT = r"""#!/bin/bash
# claude-mpm-managed: do not remove this line (used for auto-upgrades)
# claude-mpm status line
#
# Claude Code calls this script periodically via the statusLine hook and
# renders whatever this script prints to stdout in its own built-in status
# bar area at the bottom of the UI.  The script must NOT do any cursor
# positioning or /dev/tty painting — Claude Code owns that rendering.
#
# Usage:
#   statusline.sh           — print status string to stdout
#   statusline.sh --clear   — print empty string (Stop hook, bar goes blank)
#
# JSON context is provided on stdin when Claude Code invokes the script.
#
# Layout:
#   ◆ <user> │ <model> │ <ctx%> ctx │ <cwd> │ <branch> [↑N][↓N] │ style:<outputStyle>

set -u

# --clear mode: output an empty string so Claude Code blanks its status bar.
if [ "${1:-}" = "--clear" ]; then
    printf ''
    exit 0
fi

# ---------------------------------------------------------------------------
# Parse JSON payload from stdin (if any).
# ---------------------------------------------------------------------------
input=""
if [ ! -t 0 ]; then
    input=$(cat)
fi

USER_NAME=$(whoami 2>/dev/null || echo "user")

if [ -n "$input" ] && command -v jq >/dev/null 2>&1; then
    MODEL=$(printf '%s' "$input" | jq -r '.model.display_name // .model.id // "unknown"' 2>/dev/null || echo "unknown")
    # Use // empty so missing fields yield an empty string (not "0"). Claude Code
    # only sends context_window once a session has warmed up, so at session
    # start this field is absent and we want to omit the segment entirely
    # rather than display a misleading "0% ctx".
    REMAINING=$(printf '%s' "$input" | jq -r '.context_window.remaining_percentage // empty' 2>/dev/null | cut -d. -f1)
    CWD=$(printf '%s' "$input" | jq -r '.workspace.current_dir // .workspace.path // .cwd // .session_dir // .project_root // ""' 2>/dev/null)
else
    MODEL="unknown"
    REMAINING=""
    CWD=""
fi

# If JSON didn't provide a CWD, fall back to $PWD env var then pwd command.
if [ -z "$CWD" ]; then
    CWD="${PWD:-$(pwd 2>/dev/null || echo "")}"
fi

# Normalise REMAINING: must be a non-empty, non-negative integer to be shown.
# Empty/null/non-numeric values mean "context info not available" — we'll
# omit the segment entirely below.
case "$REMAINING" in
    ''|*[!0-9]*) REMAINING="" ;;
esac

# ---------------------------------------------------------------------------
# Read outputStyle from ~/.claude/settings.json (requires jq).
# ---------------------------------------------------------------------------
OUTPUT_STYLE=""
if command -v jq >/dev/null 2>&1; then
    OUTPUT_STYLE=$(jq -r '.outputStyle // "default"' "$HOME/.claude/settings.json" 2>/dev/null || echo "default")
    [ "$OUTPUT_STYLE" = "null" ] && OUTPUT_STYLE="default"
fi

# ---------------------------------------------------------------------------
# Claude brand palette (ANSI — Claude Code passes these through).
# ---------------------------------------------------------------------------
ORANGE="\033[38;5;174m"      # accent     #CC785C
AMBER="\033[38;5;223m"       # amber      #f3d5a3
RED="\033[38;5;196m"         # low-context warning
RESET="\033[0m"
DIM="\033[2m"

# Context remaining colour: amber above 20%, red below.
# Only used when REMAINING is a numeric value (segment is otherwise omitted).
CTX_COLOR="$AMBER"
if [ -n "$REMAINING" ] && [ "$REMAINING" -lt 20 ] 2>/dev/null; then
    CTX_COLOR="$RED"
fi

# Separator: orange vertical bar with surrounding spaces.
SEP=" ${ORANGE}│${RESET} "

# ---------------------------------------------------------------------------
# Git info (branch + ahead/behind) if we're inside a repo.
# ---------------------------------------------------------------------------
GIT_SEGMENT=""
if [ -n "$CWD" ] && command -v git >/dev/null 2>&1 \
   && git -C "$CWD" rev-parse --git-dir >/dev/null 2>&1; then
    BRANCH=$(git -C "$CWD" rev-parse --abbrev-ref HEAD 2>/dev/null)
    if [ -n "$BRANCH" ]; then
        AHEAD_BEHIND=$(git -C "$CWD" rev-list --left-right --count @{upstream}...HEAD 2>/dev/null)
        AHEAD_STR=""
        BEHIND_STR=""
        if [ -n "$AHEAD_BEHIND" ]; then
            BEHIND=$(echo "$AHEAD_BEHIND" | awk '{print $1}')
            AHEAD=$(echo "$AHEAD_BEHIND"  | awk '{print $2}')
            [ "${AHEAD:-0}"  -gt 0 ] 2>/dev/null && AHEAD_STR=" ↑${AHEAD}"
            [ "${BEHIND:-0}" -gt 0 ] 2>/dev/null && BEHIND_STR=" ↓${BEHIND}"
        fi
        GIT_SEGMENT="${AMBER}${BRANCH}${AHEAD_STR}${BEHIND_STR}${RESET}"
    fi
fi

# ---------------------------------------------------------------------------
# CWD segment: shorten path, colour amber.
# ---------------------------------------------------------------------------
CWD_SEGMENT=""
RAW_CWD="${CWD:-$(pwd 2>/dev/null || echo "")}"
case "$RAW_CWD" in
    "$HOME"*) SHORT_CWD="~${RAW_CWD#"$HOME"}" ;;
    *)        SHORT_CWD="$RAW_CWD" ;;
esac
if [ "${#SHORT_CWD}" -gt 40 ]; then
    SHORT_CWD="…$(printf '%s' "$SHORT_CWD" | awk '{ print substr($0, length($0)-38) }')"
fi
if [ -n "$SHORT_CWD" ]; then
    CWD_SEGMENT="${SEP}${AMBER}${SHORT_CWD}${RESET}"
fi

# ---------------------------------------------------------------------------
# outputStyle segment (dimmed). Omitted when jq unavailable.
# ---------------------------------------------------------------------------
STYLE_SEGMENT=""
if [ -n "$OUTPUT_STYLE" ]; then
    STYLE_SEGMENT="${SEP}${DIM}style:${OUTPUT_STYLE}${RESET}"
fi

# ---------------------------------------------------------------------------
# Compose and print the status string to stdout.
# Claude Code renders this in its built-in status bar — no cursor escapes.
# ---------------------------------------------------------------------------
# Base: ◆ <user> │ <model>
STATUS=$(printf "◆ %s%b%b%s%b" \
    "${USER_NAME}" \
    "${SEP}" \
    "${ORANGE}" "${MODEL}" "${RESET}")

# Context segment: only included when we have an actual numeric value.
# At session start Claude Code doesn't send context_window info, so we omit
# the segment rather than rendering a misleading "0% ctx".
if [ -n "$REMAINING" ]; then
    CTX_SEGMENT=$(printf "%b%b%s%%%b ctx" \
        "${SEP}" "${CTX_COLOR}" "${REMAINING}" "${RESET}")
    STATUS="${STATUS}${CTX_SEGMENT}"
fi

STATUS="${STATUS}${CWD_SEGMENT}"

if [ -n "$GIT_SEGMENT" ]; then
    STATUS="${STATUS}${SEP}${GIT_SEGMENT}"
fi

STATUS="${STATUS}${STYLE_SEGMENT}"

printf '%b\n' "$STATUS"
exit 0
"""

# Default statusLine settings block to add when missing.  Uses the absolute
# user-level script path because this entry now lives in ``~/.claude/settings.json``
# and is not project-relative.
#
# Carries ``_MPM_OWNED_KEY`` so that an entry MPM writes today is recognisable
# as MPM-owned tomorrow.  The CUSTOM policy builds its entry by overriding only
# ``command`` on this dict, so it inherits the marker too — which is exactly
# what keeps a custom command updatable across runs.
_DEFAULT_STATUS_LINE: dict = {
    "type": "command",
    "command": str(_USER_SCRIPT_PATH),
    "padding": 1,
    "refreshInterval": 10,
    _MPM_OWNED_KEY: True,
}

# Default Stop hook group (matcher "*") with the --clear command.
_DEFAULT_STOP_HOOK_ENTRY: dict = {
    "type": "command",
    "command": _STOP_HOOK_COMMAND,
    "timeout": 5,
}


def _ensure_script(script_path: Path, force: bool = False) -> bool:
    """Ensure the statusline script exists at ``script_path`` and is executable.

    Args:
        script_path: Absolute path to the desired statusline.sh location
            (typically ``~/.claude/hooks/scripts/statusline.sh``).
        force: If True, overwrite the existing script with the bundled
            canonical version regardless of whether it carries the
            ``_MPM_MARKER`` line.  This is the semantic of an explicit user
            action like ``claude-mpm update-statusline``: the user has asked
            for the official version, so we give them the official version.
            (Pre-marker installs and user-customised variants alike are
            overwritten.)  When False, we update if the file has the MPM
            marker, otherwise leave it alone.

    Returns:
        True on success, False on error.
    """
    if script_path.exists():
        try:
            existing = script_path.read_text(encoding="utf-8")
        except Exception:
            logger.exception("Failed to read existing statusline.sh at %s", script_path)
            return False

        is_mpm_owned = _MPM_MARKER in existing
        # Update if: (a) we own it and content differs, or (b) force is set.
        should_update = (is_mpm_owned and existing != _SCRIPT_CONTENT) or (
            force and existing != _SCRIPT_CONTENT
        )

        if should_update:
            try:
                script_path.write_text(_SCRIPT_CONTENT, encoding="utf-8")
                if is_mpm_owned:
                    logger.info("Upgraded MPM-managed statusline.sh at %s", script_path)
                else:
                    logger.info(
                        "Replaced statusline.sh at %s with canonical MPM version "
                        "(force mode; previous file lacked the MPM marker)",
                        script_path,
                    )
            except Exception:
                logger.exception("Failed to overwrite statusline.sh at %s", script_path)
                return False
        elif is_mpm_owned:
            logger.debug(
                "MPM-managed statusline.sh at %s is already up to date", script_path
            )
        else:
            logger.debug(
                "statusline.sh at %s lacks MPM marker — leaving user copy alone",
                script_path,
            )
        # Always re-chmod to ensure executable bit is set.
        try:
            current_mode = script_path.stat().st_mode
            script_path.chmod(
                current_mode
                | stat.S_IRWXU
                | stat.S_IRGRP
                | stat.S_IXGRP
                | stat.S_IROTH
                | stat.S_IXOTH
            )
        except Exception:
            logger.exception("Failed to chmod statusline.sh at %s", script_path)
            return False
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


def _ensure_settings_entry(
    settings_path: Path, desired_entry: dict | None = None
) -> bool:
    """Ensure the statusLine entry is present and current in settings.json.

    Ownership rules (see ``_is_mpm_owned_statusline``):
    - File absent → create with the desired statusLine entry.
    - No ``statusLine`` key → add the desired entry.
    - Existing entry carries the ``_MPM_OWNED_KEY`` marker, or (legacy
      fallback) its ``command`` contains ``statusline.sh`` → MPM-owned, so
      update the entry to the desired one.  Adopting a legacy marker-less
      entry also stamps the marker, so the next run recognises it directly.
    - Anything else is user-authored → leave it alone.

    Args:
        settings_path: Path to the ``settings.json`` to update.
        desired_entry: The statusLine block to write when we own the entry.
            Defaults to ``_DEFAULT_STATUS_LINE`` (the bundled script path).
            Callers under a CUSTOM statusline policy pass a block pointing at
            the user's custom command instead.

    Returns:
        True on success, False on error.
    """
    desired_entry = desired_entry if desired_entry is not None else _DEFAULT_STATUS_LINE

    if not settings_path.exists():
        # Create a minimal settings.json with the statusLine entry.
        try:
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings_path.write_text(
                json.dumps({"statusLine": desired_entry}, indent=2, ensure_ascii=False)
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

    if not isinstance(settings, dict):
        logger.warning(
            "settings.json at %s is not a JSON object — refusing to modify",
            settings_path,
        )
        return False

    existing = settings.get("statusLine")
    if existing is None:
        # No statusLine entry at all → add ours.
        settings["statusLine"] = desired_entry
        action = "Added statusLine entry to %s"
    # Ownership is read off the entry itself (explicit marker, with the
    # legacy command substring as a compatibility fallback) rather than
    # inferred from where the command happens to point.
    elif _is_mpm_owned_statusline(existing):
        if existing == desired_entry:
            logger.debug(
                "statusLine in %s already matches desired entry — skipping",
                settings_path,
            )
            return True
        settings["statusLine"] = desired_entry
        action = "Updated MPM-managed statusLine entry in %s"
    else:
        logger.debug(
            "statusLine in %s points elsewhere (user-customised) — leaving alone",
            settings_path,
        )
        return True

    try:
        settings_path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info(action, settings_path)
    except Exception:
        logger.exception("Failed to write settings.json at %s", settings_path)
        return False

    return True


def _find_mpm_stop_hook(settings: dict) -> dict | None:
    """Return the MPM-owned Stop hook entry if present, else None.

    Matches substring-wise so both relative and absolute invocations of
    ``statusline.sh --clear`` count as "MPM-owned".  Returns the hook dict
    itself (mutable reference) so callers can update it in place.
    """
    stop_groups = settings.get("hooks", {}).get("Stop", [])
    if not isinstance(stop_groups, list):
        return None

    for group in stop_groups:
        if not isinstance(group, dict):
            continue
        for hook in group.get("hooks", []) or []:
            if not isinstance(hook, dict):
                continue
            cmd = hook.get("command", "")
            if isinstance(cmd, str) and _STOP_HOOK_MATCH in cmd:
                return hook
    return None


def _ensure_stop_hook(settings_path: Path) -> bool:
    """Ensure a Stop hook calling statusline.sh --clear is present and current.

    Ownership rules:
    - If an existing Stop hook command contains ``statusline.sh --clear``
      (substring match — covers legacy relative paths and current absolute
      path), update its ``command`` to the absolute user-level path.
    - Otherwise, append a new MPM-owned hook to the existing matcher="*"
      group (or create one).
    - Stop hooks owned by the user (no ``statusline.sh --clear`` substring)
      are left in place.

    Args:
        settings_path: Path to ``~/.claude/settings.json``.

    Returns:
        True on success, False on error.
    """
    # Starting state: read existing settings, or start with {}.
    if settings_path.exists():
        try:
            raw = json.loads(settings_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                logger.warning(
                    "settings.json at %s is not a JSON object — overwriting",
                    settings_path,
                )
                raw = {}
            settings: dict = raw
        except Exception:
            logger.exception("Failed to parse settings.json at %s", settings_path)
            return False
    else:
        settings = {}

    existing_hook = _find_mpm_stop_hook(settings)
    if existing_hook is not None:
        if existing_hook.get("command") == _STOP_HOOK_COMMAND:
            logger.debug(
                "MPM-owned Stop hook in %s already uses absolute path — skipping",
                settings_path,
            )
            return True
        # Update in place to the absolute user-level path.
        existing_hook["command"] = _STOP_HOOK_COMMAND
        action = "Updated MPM-owned Stop hook command in %s to absolute user-level path"
    else:
        # Ensure nested structure: settings["hooks"]["Stop"] is a list of groups.
        hooks = settings.setdefault("hooks", {})
        if not isinstance(hooks, dict):
            hooks = {}
            settings["hooks"] = hooks
        stop_groups = hooks.setdefault("Stop", [])
        if not isinstance(stop_groups, list):
            stop_groups = []
            hooks["Stop"] = stop_groups

        # Prefer to append to an existing matcher="*" group so we don't
        # fragment the Stop configuration.
        wildcard_group: dict | None = None
        for group in stop_groups:
            if isinstance(group, dict) and group.get("matcher") == "*":
                wildcard_group = group
                break

        if wildcard_group is not None:
            group_hooks = wildcard_group.setdefault("hooks", [])
            if not isinstance(group_hooks, list):
                group_hooks = []
                wildcard_group["hooks"] = group_hooks
            group_hooks.append(_DEFAULT_STOP_HOOK_ENTRY)
        else:
            stop_groups.append(
                {
                    "matcher": "*",
                    "hooks": [_DEFAULT_STOP_HOOK_ENTRY],
                }
            )
        action = "Added Stop hook for statusline --clear to %s"

    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info(action, settings_path)
    except Exception:
        logger.exception("Failed to write settings.json at %s", settings_path)
        return False

    return True


def _strip_mpm_stop_hooks(settings: dict) -> bool:
    """Remove MPM-owned ``statusline.sh --clear`` Stop hooks from ``settings``.

    Why: Two callers need exactly this removal — the global-settings self-heal
    (``_cleanup_global_statusline_settings``, issue #924) and the CUSTOM-policy
    staleness fix (``_remove_mpm_stop_hook``) — so the group-pruning logic lives
    in one place instead of being duplicated.
    What: Mutates ``settings`` in place, dropping every Stop hook whose
    ``command`` contains ``_STOP_HOOK_MATCH`` and pruning hook groups (and the
    ``hooks`` dict) left empty by the removal.  Stop hooks that do not match are
    preserved untouched.  Returns True if anything was changed.
    Test: Seed a settings dict with one MPM ``--clear`` hook and one user hook
    in the same group; assert True is returned, the MPM hook is gone and the
    user hook remains.
    """
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return False
    stop_groups = hooks.get("Stop")
    if not isinstance(stop_groups, list):
        return False

    changed = False
    surviving_groups: list = []
    for group in stop_groups:
        if not isinstance(group, dict):
            surviving_groups.append(group)
            continue
        group_hooks = group.get("hooks")
        if isinstance(group_hooks, list):
            kept = [
                hook
                for hook in group_hooks
                if not (
                    isinstance(hook, dict)
                    and isinstance(hook.get("command"), str)
                    and _STOP_HOOK_MATCH in hook["command"]
                )
            ]
            if len(kept) != len(group_hooks):
                changed = True
                group["hooks"] = kept
            # Drop groups that are now empty.
            if not kept:
                continue
        surviving_groups.append(group)

    if len(surviving_groups) != len(stop_groups):
        changed = True
    if surviving_groups:
        hooks["Stop"] = surviving_groups
    else:
        del hooks["Stop"]
        changed = True
    # Remove an emptied hooks dict entirely.
    if not hooks:
        del settings["hooks"]

    return changed


def _remove_mpm_stop_hook(settings_path: Path) -> bool:
    """Remove a stale MPM-owned ``--clear`` Stop hook from ``settings_path``.

    Why: The Stop hook exists solely to blank the bar painted by the *bundled*
    ``statusline.sh``.  Under the CUSTOM policy ``statusLine.command`` points at
    the user's own command instead, so a hook installed by an earlier MANAGED
    run is firing ``--clear`` against a script that is no longer the active
    statusline.  We must not *install* a ``--clear`` hook for a custom command
    (it is not guaranteed to support the flag), but we do have to retract the
    one we previously installed.
    What: Reads ``settings_path``, strips MPM-owned Stop hooks via
    ``_strip_mpm_stop_hooks``, and rewrites the file only if something changed.
    A missing file, or a file with no MPM-owned Stop hook, is a successful
    no-op.  User-owned Stop hooks are never removed.
    Test: Run MANAGED then CUSTOM against the same project and assert the
    ``statusline.sh --clear`` hook is gone while an unrelated user Stop hook
    seeded alongside it survives.

    Returns:
        True on success (including no-op), False on error.
    """
    if not settings_path.exists():
        return True

    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to parse settings.json at %s", settings_path)
        return False

    if not isinstance(settings, dict):
        # Not something we can safely reason about; leave it to
        # _ensure_settings_entry to report the problem.
        return True

    if not _strip_mpm_stop_hooks(settings):
        return True

    try:
        settings_path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info(
            "Removed stale MPM-owned statusline --clear Stop hook from %s "
            "(statusLine now points at a custom command)",
            settings_path,
        )
    except Exception:
        logger.exception("Failed to write settings.json at %s", settings_path)
        return False

    return True


def _cleanup_global_statusline_settings(settings_path: Path) -> bool:
    """Strip MPM-owned statusLine and Stop-hook entries from global settings.

    WHAT: Reads the global ``~/.claude/settings.json`` and removes the MPM-owned
    ``statusLine`` entry and any ``statusline.sh --clear`` Stop hooks (pruning
    emptied hook groups), leaving user-authored entries intact.

    WHY: claude-mpm used to write ``statusLine`` and a ``statusline.sh --clear`` Stop
    hook into the shared ``~/.claude/settings.json`` (issue #924), so the bar
    appeared in every Claude Code session on the machine. Those entries now live
    in the project-local ``.claude/settings.json``; this helper removes the
    stale global copies so existing installs self-heal.

    Only MPM-owned entries are touched, and ownership alone does not authorise
    deletion (issue #939 — see ``classify_statusline_entry``):
    - ``statusLine`` is removed outright only when its ``command`` points at the
      bundled ``statusline.sh`` (explicitly marked or legacy pre-marker alike).
    - A marker-bearing entry holding the user's own command loses only the
      marker; its ``command`` is preserved.
    - Stop-hook entries are removed only when their ``command`` contains
      ``statusline.sh --clear``; empty hook groups left behind are pruned.

    Returns True on success (including no-op), False on error.
    """
    if not settings_path.exists():
        return True

    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to parse global settings.json at %s", settings_path)
        return False

    if not isinstance(settings, dict):
        return True

    changed = False

    # #939: ownership is not removability — a marker-bearing CUSTOM entry holds
    # the user's own command, so relinquish ownership instead of deleting it.
    existing = settings.get("statusLine")
    disposition = classify_statusline_entry(existing)
    if disposition is StatuslineDisposition.REMOVE:
        del settings["statusLine"]
        changed = True
    elif disposition is StatuslineDisposition.DISOWN and strip_statusline_marker(
        existing
    ):
        changed = True

    # Remove MPM-owned Stop hooks (and prune emptied groups).
    if _strip_mpm_stop_hooks(settings):
        changed = True

    if not changed:
        return True

    try:
        settings_path.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        logger.info(
            "Removed MPM-owned statusLine/Stop-hook entries from global %s (issue #924)",
            settings_path,
        )
    except Exception:
        logger.exception("Failed to write global settings.json at %s", settings_path)
        return False

    return True


def run_migration(installation_dir: Path | None = None, force: bool = False) -> bool:
    """Auto-configure the MPM statusline at the user level (~/.claude/).

    WHAT: Resolves the statusline policy for ``project_dir``, then branches three
    ways.  DISABLED returns immediately, touching nothing at all.  CUSTOM writes
    the user's command into the project-local ``statusLine`` entry and retracts
    any ``--clear`` Stop hook a previous MANAGED run installed, without ever
    installing one for the custom command.  MANAGED (the default) ensures the
    bundled script exists, writes the ``statusLine`` entry pointing at it, and
    installs the matching ``--clear`` Stop hook.  Every entry written carries
    ``_MPM_OWNED_KEY`` so later runs can recognise it as ours.

    WHY: This is the single entry point every caller reaches — ``claude-mpm run``
    calls it directly and ``update-statusline --force`` routes through it — so the
    policy branch has to live here for the opt-out to be honoured consistently
    (an explicit opt-out must beat ``force``).  Keeping the three policies in one
    function also makes their asymmetries reviewable side by side: only DISABLED
    skips the global-settings self-heal, and only MANAGED installs a Stop hook.

    Args:
        installation_dir: Accepted for backwards compatibility but ignored for
            the purpose of *where the script/settings live* — this migration
            always targets ``~/.claude/`` regardless of the project from which
            it is invoked (the user-level statusline is shared across all
            projects). It IS still consulted, alongside ``Path.cwd()``, as the
            project directory when resolving a project-level ``statusline``
            override in ``.claude-mpm/configuration.yaml`` (see
            ``_resolve_statusline_policy``).
        force: If True, overwrite an existing ``statusline.sh`` even when it
            lacks the MPM marker (i.e. user-customised).  When False (default),
            user-customised scripts are preserved; MPM-managed scripts are
            still upgraded if the bundled content has changed.  Ignored
            entirely when the resolved policy is DISABLED or CUSTOM — an
            explicit user opt-out or override always wins over ``force``,
            including when invoked via ``claude-mpm update-statusline --force``.

    Returns:
        True if migration completed successfully (including no-op, and
        including the DISABLED early-return below), False on error.
    """
    project_dir = installation_dir if installation_dir is not None else Path.cwd()
    policy = _resolve_statusline_policy(project_dir)

    if policy.kind is StatuslinePolicyKind.DISABLED:
        # Pure no-op: do not create/upgrade the managed script, do not
        # add/modify any statusLine or Stop-hook entry, and do not run the
        # global-settings self-heal cleanup below (which itself mutates
        # ~/.claude/settings.json). We also must NOT delete a user's existing
        # statusLine entry — simply doing nothing satisfies that too.
        logger.debug(
            "Statusline management disabled via %s (CLAUDE_MPM_STATUSLINE or "
            "statusline.enabled: false) — skipping autoconfig entirely",
            policy.source,
        )
        return True

    user_claude_dir = Path.home() / ".claude"
    # The statusline script itself stays at the user level so a single copy is
    # shared across projects; only the settings.json *entries* move project-local.
    script_path = user_claude_dir / "hooks" / "scripts" / "statusline.sh"

    # Write statusLine and Stop-hook entries into the PROJECT-LOCAL
    # .claude/settings.json instead of the shared ~/.claude/settings.json, which
    # previously caused the statusline to appear in every Claude Code session on
    # the machine (issue #924).
    settings_path = project_dir / ".claude" / "settings.json"

    # Self-heal existing installs: strip MPM-owned statusLine / Stop-hook entries
    # from the global ~/.claude/settings.json.
    _cleanup_global_statusline_settings(user_claude_dir / "settings.json")

    if policy.kind is StatuslinePolicyKind.CUSTOM:
        # Write the user's custom command instead of the bundled script path and
        # never *install* a --clear Stop hook for it (a custom command is not
        # guaranteed to support the flag).  The entry inherits _MPM_OWNED_KEY
        # from _DEFAULT_STATUS_LINE, which is what lets a later run recognise it
        # as ours and update it when the configured command changes.
        #
        # We do, however, have to retract a --clear Stop hook installed by an
        # earlier MANAGED run: statusLine.command no longer points at the
        # bundled script, so that hook is stale.
        #
        # The "leave user-authored entries alone" ownership check inside
        # _ensure_settings_entry still applies: an entry we never wrote (no
        # marker, non-bundled command) is left untouched.
        logger.debug(
            "Statusline command overridden via %s to: %s", policy.source, policy.command
        )
        desired_entry = {**_DEFAULT_STATUS_LINE, "command": policy.command}
        settings_ok = _ensure_settings_entry(settings_path, desired_entry=desired_entry)
        stop_hook_ok = _remove_mpm_stop_hook(settings_path)
        return settings_ok and stop_hook_ok

    script_ok = _ensure_script(script_path, force=force)
    settings_ok = _ensure_settings_entry(settings_path)
    stop_hook_ok = _ensure_stop_hook(settings_path) if settings_ok else False

    return script_ok and settings_ok and stop_hook_ok
