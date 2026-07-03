"""Per-project agent manifest persistence.

WHAT: Provides ``write_agent_manifest``/``read_agent_manifest`` helpers that
persist and load a small JSON file (``.claude-mpm/agent_manifest.json``)
recording which agent IDs the auto-configure workflow recommended/deployed
for a given project.

WHY: Without this manifest, the PM's "Available Agent Capabilities" system
prompt section (built in ``core/framework_loader.py``) has no way to know
which of the ~50 possible agent templates are actually relevant to a given
project, so it always exposes the full catalog. Persisting the
recommendation output here lets capability generation filter down to what
auto-configure already determined is relevant, while remaining fully
backward compatible: projects that never ran auto-configure simply have no
manifest file, and callers fall back to today's "show everything" behavior.

References
----------
GitHub issue: https://github.com/bobmatnyc/claude-mpm/issues/923
LINK: none
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from claude_mpm.core.logging_utils import get_logger

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

logger = get_logger(__name__)

#: Directory (relative to project root) that holds claude-mpm project state.
MANIFEST_DIRNAME = ".claude-mpm"
#: Manifest file name within MANIFEST_DIRNAME.
MANIFEST_FILENAME = "agent_manifest.json"
#: Bump when the on-disk schema changes in an incompatible way.
MANIFEST_SCHEMA_VERSION = 1


def get_manifest_path(project_path: Path) -> Path:
    """Return the manifest path for ``project_path`` (existence not checked)."""
    return project_path / MANIFEST_DIRNAME / MANIFEST_FILENAME


def write_agent_manifest(
    project_path: Path,
    agent_ids: Iterable[str],
    *,
    toolchain_summary: dict[str, Any] | None = None,
) -> Path:
    """Persist the recommended/deployed agent-id list for ``project_path``.

    Args:
        project_path: Project root directory.
        agent_ids: Agent IDs (``.claude/agents/*.md`` stems) to record.
        toolchain_summary: Optional debugging context (e.g. detected
            language/frameworks) stored alongside the agent list.

    Returns:
        The path the manifest was written to (whether or not the write
        succeeded -- callers that need to confirm success should check
        ``.exists()`` themselves).
    """
    manifest_path = get_manifest_path(project_path)

    data: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "agent_ids": sorted({str(agent_id) for agent_id in agent_ids}),
    }
    if toolchain_summary is not None:
        data["toolchain_summary"] = toolchain_summary

    try:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with manifest_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=False)
            f.write("\n")
        logger.debug(f"Wrote agent manifest to {manifest_path}")
    except OSError as e:
        logger.warning(f"Failed to write agent manifest to {manifest_path}: {e}")

    return manifest_path


def read_agent_manifest(project_path: Path) -> list[str] | None:
    """Read the agent-id allow-list for ``project_path``.

    Returns ``None`` when the manifest is absent, unreadable, or malformed
    (missing/invalid ``agent_ids``) so callers can distinguish "no manifest,
    use the full catalog" from "manifest present but empty" (an empty list is
    returned as ``[]``, not ``None``).
    """
    manifest_path = get_manifest_path(project_path)
    if not manifest_path.exists():
        return None

    try:
        with manifest_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        logger.warning(f"Could not read agent manifest at {manifest_path}: {e}")
        return None

    agent_ids = data.get("agent_ids") if isinstance(data, dict) else None
    if not isinstance(agent_ids, list):
        logger.warning(
            f"Agent manifest at {manifest_path} is missing a valid 'agent_ids' "
            "list; ignoring and falling back to the full catalog"
        )
        return None

    return [str(agent_id) for agent_id in agent_ids if isinstance(agent_id, str)]
