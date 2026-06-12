"""
Migration registry for version-based migrations.

Migrations are registered by version and run automatically on first startup
of that version. Each migration runs once and is tracked in state file.

References
----------
SPEC-INTEGRATIONS-09~1 : docs/specs/integrations.md#SPEC-INTEGRATIONS-09~1
"""

from collections.abc import Callable
from typing import NamedTuple


class Migration(NamedTuple):
    """A migration definition.

    Set ``run_always=True`` for migrations that should re-run on every startup
    (e.g., environment auto-detection probes). Run-always migrations are NOT
    persisted to the ``completed`` state file and must therefore be cheap and
    idempotent — see :mod:`migrate_trusty_autodetect` for the canonical
    example.
    """

    id: str  # Unique identifier (e.g., "5.6.91_async_hooks")
    version: str  # Version this migration applies to
    description: str  # Human-readable description
    run: Callable[[], bool]  # Function that returns True on success
    run_always: bool = False  # If True, run every startup (skip completion gate)


def _run_async_hooks_migration() -> bool:
    """Run the async hooks migration."""
    from .migrate_async_hooks import migrate_all_settings

    return migrate_all_settings()


def _run_coauthor_email_migration() -> bool:
    """Run the co-author email migration."""
    from .migrate_coauthor_email import migrate_coauthor_email

    return migrate_coauthor_email()


def _run_remove_unsupported_hooks_migration() -> bool:
    """Remove v2.1.47+ hook events from settings on older Claude Code installs."""
    from .migrate_remove_unsupported_hooks import migrate_all_settings

    return migrate_all_settings()


def _run_binary_consolidation_migration() -> bool:
    """Migrate .mcp.json to consolidated 'claude-mpm mcp serve' format."""
    from .migrate_binary_consolidation import run_migration

    return run_migration()


def _run_core_skills_to_user_level_migration() -> bool:
    """Move CORE mpm-* skills to user level, remove project-level duplicates."""
    from .migrate_core_skills_to_user_level import run_migration

    return run_migration()


def _run_core_agents_to_user_level_migration() -> bool:
    """Move CORE agents to user level, remove project-level duplicates."""
    from .migrate_core_agents_to_user_level import run_migration

    return run_migration()


def _run_overlap_cleanup_migration() -> bool:
    """Clean up agent/skill overlap between user-level and project-level."""
    from pathlib import Path

    from .cleanup_overlap import run_overlap_cleanup

    result = run_overlap_cleanup(project_dir=Path.cwd())
    # Consider it successful if there are no errors
    total_errors = (
        len(result["agents"]["errors"])
        + len(result["skills"]["errors"])
        + len(result["stale_agents"]["errors"])
    )
    return total_errors == 0


def _run_native_agent_fields_migration() -> bool:  # pyright: ignore[unused-function]
    """Add Claude Code native frontmatter fields to project agent files."""
    from pathlib import Path

    from .v6_3_0_native_agent_fields import run_migration

    return run_migration(installation_dir=Path.cwd())


def _run_create_commands_dir_migration() -> bool:  # pyright: ignore[unused-function]
    """Create .claude/commands/ with default slash command templates."""
    from pathlib import Path

    from .v6_3_0_create_commands_dir import run_migration

    return run_migration(installation_dir=Path.cwd())


def _run_deploy_claude_assets_migration() -> bool:  # pyright: ignore[unused-function]
    """Deploy statusline.sh and settings.json from package templates into .claude/."""
    from pathlib import Path

    from .v6_3_1_deploy_claude_assets import run_migration

    return run_migration(installation_dir=Path.cwd())


def _run_agent_color_prompt_migration() -> bool:  # pyright: ignore[unused-function]
    """Inject color field into project agent frontmatter."""
    from pathlib import Path

    from .v6_3_2_agent_color_prompt import (
        run_migration,  # type: ignore[import-untyped]  # fmt: skip
    )

    return run_migration(installation_dir=Path.cwd())


def _run_additional_directories_migration() -> bool:  # pyright: ignore[unused-function]
    """Add permissions.additionalDirectories to .claude/settings.json."""
    from pathlib import Path

    from .v6_3_2_additional_directories import (
        run_migration,  # type: ignore[import-untyped]  # fmt: skip
    )

    return run_migration(installation_dir=Path.cwd())


def _run_permission_request_hook_migration() -> bool:  # pyright: ignore[unused-function]
    """Add PermissionRequest hook to .claude/settings.json."""
    from pathlib import Path

    from .v6_3_2_permission_request_hook import (
        run_migration,  # type: ignore[import-untyped]  # fmt: skip
    )

    return run_migration(installation_dir=Path.cwd())


def _run_statusline_autoconfig_migration() -> bool:
    """Auto-configure the MPM statusline script and settings entry."""
    from pathlib import Path

    from .migrate_statusline_autoconfig import run_migration

    return run_migration(installation_dir=Path.cwd())


def _run_statusline_user_level_migration() -> bool:
    """Move legacy project-level statusline assets to ~/.claude/."""
    from pathlib import Path

    from .migrate_statusline_user_level import run_migration

    return run_migration(installation_dir=Path.cwd())


def _run_trusty_autodetect_migration() -> bool:
    """Detect running trusty-search / trusty-memory daemons and wire into .mcp.json."""
    from .migrate_trusty_autodetect import run_migration

    return run_migration()


def _run_check_migration_skills_migration() -> bool:
    """Detect pending migration skill wizards and refresh the notification file."""
    from .migrate_check_migration_skills import run_migration

    return run_migration()


def _run_fix_mcp_command_args_migration() -> bool:
    """Fix .mcp.json entries where ``command`` contains spaces (split into command + args)."""
    from .migrate_fix_mcp_command_args import run_migration

    return run_migration()


def _run_remove_memory_capture_hook_migration() -> bool:
    """Remove stale memory_capture hook entries (moved to trusty-memory, issue #555)."""
    from .migrate_remove_memory_capture_hook import run_migration

    return run_migration()


def _run_fix_trusty_memory_bridge_migration() -> bool:
    """Repair broken trusty-memory MCP entries to use the bridge binary (issue #567)."""
    from .migrate_fix_trusty_memory_bridge import run_migration

    return run_migration()


def _run_remove_deployed_base_templates_migration() -> bool:
    """Remove BASE-*.md / BASE_*.md files incorrectly deployed as agents."""
    from .migrate_remove_deployed_base_templates import run_migration

    return run_migration()


def _run_dedup_hook_registrations_migration() -> bool:
    """Collapse duplicate MPM claude-hook entries that differ only in timeout (issue #677)."""
    from .migrate_dedup_hook_registrations import run_migration

    return run_migration()


def _run_clean_global_settings_metadata_migration() -> bool:
    """Remove stale _mpm_managed/_mpm_version metadata from global ~/.claude/settings.json (issue #676)."""
    from .migrate_clean_global_settings_metadata import run_migration

    return run_migration()


def _run_rename_trusty_analyzer_migration() -> bool:
    """Rename stale trusty-analyzer MCP entry to trusty-analyze and clean up launchd plist (issue #782)."""
    from .v6_5_34_rename_trusty_analyzer import run_migration

    return run_migration()


def _run_trusty_memory_stdio_migration() -> bool:
    """Rewrite stale trusty-memory-mcp-bridge entries to the canonical trusty-memory serve --stdio form."""
    from .v6_5_36_trusty_memory_stdio import run_migration

    return run_migration()


def _run_remove_absolute_hook_paths_migration() -> bool:
    """Replace absolute MPM hook paths with the portable 'claude-hook' entry point (issue #563)."""
    from pathlib import Path

    from .v6_4_18_remove_absolute_hook_paths import run_migration

    return run_migration(installation_dir=Path.cwd())


def _run_hooks_to_project_level_migration() -> bool:  # pyright: ignore[unused-function]
    """Move MPM hooks from settings.local.json (and ~/.claude/settings.json) into project settings.json."""
    from pathlib import Path

    from .v6_3_19_hooks_to_project_level import (
        run_migration,  # type: ignore[import-untyped]  # fmt: skip
    )

    return run_migration(installation_dir=Path.cwd())


# Registry of all migrations, ordered by version
MIGRATIONS: list[Migration] = [
    Migration(
        id="5.6.91_async_hooks",
        version="5.6.91",
        description="Migrate hooks to async execution mode",
        run=_run_async_hooks_migration,
    ),
    Migration(
        id="5.6.95_coauthor_email",
        version="5.6.95",
        description="Update Co-Authored-By to Claude MPM <https://github.com/bobmatnyc/claude-mpm>",
        run=_run_coauthor_email_migration,
    ),
    Migration(
        id="5.9.48_remove_unsupported_hooks",
        version="5.9.48",
        description="Remove unsupported v2.1.47+ hook events (WorktreeCreate, WorktreeRemove, TeammateIdle, TaskCompleted, ConfigChange) from Claude settings on older Claude Code installations",
        run=_run_remove_unsupported_hooks_migration,
    ),
    Migration(
        id="5.12.0_binary_consolidation",
        version="5.12.0",
        description="Migrate .mcp.json to consolidated 'claude-mpm mcp serve' format",
        run=_run_binary_consolidation_migration,
    ),
    Migration(
        id="6.1.0_core_skills_to_user_level",
        version="6.1.0",
        description="Move CORE mpm-* skills to user level, remove project-level duplicates",
        run=_run_core_skills_to_user_level_migration,
        # run_always=True is intentional: this migration is idempotent and must
        # run per-project on every startup to dedup skills in each project, not
        # just once globally.
        run_always=True,
    ),
    Migration(
        id="6.2.0_core_agents_to_user_level",
        version="6.2.0",
        description="Move CORE agents to user level, remove project-level duplicates",
        run=_run_core_agents_to_user_level_migration,
    ),
    Migration(
        id="6.2.1_overlap_cleanup",
        version="6.2.1",
        description="Archive project-level duplicates of user-level agents/skills and stale -agent suffixed names",
        run=_run_overlap_cleanup_migration,
    ),
    Migration(
        id="6.3.0_native_agent_fields",
        version="6.3.0",
        description="Add Claude Code native frontmatter fields (permissionMode, maxTurns, memory) to project agent files",
        run=_run_native_agent_fields_migration,
    ),
    Migration(
        id="6.3.0_create_commands_dir",
        version="6.3.0",
        description="Create .claude/commands/ directory with default slash command templates",
        run=_run_create_commands_dir_migration,
    ),
    Migration(
        id="v6_3_1_deploy_claude_assets",
        version="6.3.1",
        description="Deploy statusline.sh and settings.json from package templates into .claude/",
        run=_run_deploy_claude_assets_migration,
    ),
    Migration(
        id="v6_3_2_agent_color_prompt",
        version="6.3.2",
        description="Inject color field into project agent frontmatter based on agent name patterns",
        run=_run_agent_color_prompt_migration,
    ),
    Migration(
        id="v6_3_2_additional_directories",
        version="6.3.2",
        description="Add permissions.additionalDirectories: [] to .claude/settings.json if missing",
        run=_run_additional_directories_migration,
    ),
    Migration(
        id="v6_3_2_permission_request_hook",
        version="6.3.2",
        description="Add PermissionRequest hook entry to .claude/settings.json hooks section",
        run=_run_permission_request_hook_migration,
    ),
    Migration(
        id="v6_2_35_statusline_autoconfig",
        version="6.2.35",
        description="Auto-configure MPM statusline script and statusLine entry in .claude/settings.json",
        run=_run_statusline_autoconfig_migration,
    ),
    Migration(
        id="v6_3_2_statusline_user_level",
        version="6.3.2",
        description="Move legacy project-level statusline.sh and settings entries to ~/.claude/",
        run=_run_statusline_user_level_migration,
    ),
    Migration(
        id="trusty_autodetect",
        version="6.3.10",
        description="Auto-detect and configure trusty-search/trusty-memory MCP servers",
        run=_run_trusty_autodetect_migration,
        run_always=True,
    ),
    Migration(
        id="v6_3_19_hooks_to_project_level",
        version="6.3.19",
        description="Move MPM hooks from settings.local.json to project-level settings.json for team-shared hook configuration",
        run=_run_hooks_to_project_level_migration,
    ),
    Migration(
        id="check_migration_skills",
        version="6.4.1",
        description="Detect pending migration skill wizards",
        run=_run_check_migration_skills_migration,
        run_always=True,
    ),
    Migration(
        id="fix_mcp_command_args",
        version="6.4.2",
        description="Fix MCP server configs where command contains spaces (split into command + args)",
        run=_run_fix_mcp_command_args_migration,
    ),
    Migration(
        id="remove_memory_capture_hook",
        version="6.4.9",
        description="Remove stale memory_capture hook entries from .claude/settings.json (module moved to trusty-memory, issue #555)",
        run=_run_remove_memory_capture_hook_migration,
    ),
    Migration(
        id="v6_4_18_remove_absolute_hook_paths",
        version="6.4.18",
        description="Replace absolute MPM hook script paths with portable 'claude-hook' entry point in .claude/settings.json (issue #563)",
        run=_run_remove_absolute_hook_paths_migration,
    ),
    Migration(
        id="fix_trusty_memory_bridge",
        version="6.5.0",
        description="Repair broken trusty-memory MCP entries (command=trusty-memory args=[serve,--mcp]) to use the trusty-memory-mcp-bridge binary (issue #567)",
        run=_run_fix_trusty_memory_bridge_migration,
    ),
    Migration(
        id="remove_deployed_base_templates",
        version="6.5.8",
        description="Remove BASE-*.md / BASE_*.md composition templates incorrectly deployed to ~/.claude/agents/ and .claude/agents/ — they fail Claude Code parsing with 'Missing required description field'",
        run=_run_remove_deployed_base_templates_migration,
    ),
    Migration(
        id="dedup_hook_registrations",
        version="6.5.20",
        description="Collapse duplicate MPM claude-hook entries that differ only in timeout into a single canonical entry per event (issue #677)",
        run=_run_dedup_hook_registrations_migration,
        run_always=True,
    ),
    Migration(
        id="clean_global_settings_metadata",
        version="6.5.21",
        description="Remove stale _mpm_managed/_mpm_version metadata and leftover MPM hook entries from global ~/.claude/settings.json (issue #676)",
        run=_run_clean_global_settings_metadata_migration,
    ),
    Migration(
        id="v6_5_34_rename_trusty_analyzer",
        version="6.5.34",
        description="Rename stale trusty-analyzer MCP server entry to trusty-analyze and remove old com.bobmatnyc.trusty-analyzer launchd plist (issue #782)",
        run=_run_rename_trusty_analyzer_migration,
    ),
    Migration(
        id="v6_5_36_trusty_memory_stdio",
        version="6.5.36",
        description="Rewrite stale trusty-memory-mcp-bridge MCP entries to the canonical direct-stdio form (trusty-memory serve --stdio) — the bridge is broken in v0.15.2+",
        run=_run_trusty_memory_stdio_migration,
    ),
]


def get_migrations_for_version(version: str) -> list[Migration]:
    """Get all migrations that should run for a given version.

    Args:
        version: The target version (e.g., "5.6.91")

    Returns:
        List of migrations for that version
    """
    return [m for m in MIGRATIONS if m.version == version]


def get_all_migrations() -> list[Migration]:
    """Get all registered migrations."""
    return MIGRATIONS.copy()
