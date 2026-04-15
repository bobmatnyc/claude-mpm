"""
Migration: Create .claude/commands/ directory with default templates (v6.3.0).

Creates .claude/commands/ if it does not exist and writes default slash command
templates (release.md, test.md, agent-list.md). Skips files that already exist
so the migration is idempotent.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default command templates keyed by filename
_COMMAND_TEMPLATES: dict[str, str] = {
    "release.md": """\
---
description: "Release a new version of claude-mpm (patch/minor/major)"
argument-hint: "[patch|minor|major]"
---

Release a new version of claude-mpm using the Makefile workflow.

The release type is: $ARGUMENTS

Steps to follow:

1. First, verify the correct GitHub account is active:
   ```
   claude-mpm gh switch
   ```
   This must be `bobmatnyc`, not `bob-duetto`.

2. Run the appropriate release target:
   ```
   make release-$ARGUMENTS
   ```
   This bumps the version, updates changelogs, and builds the package.

3. Publish to all platforms (PyPI, Homebrew, npm, GitHub Releases):
   ```
   make release-publish
   ```

If $ARGUMENTS is empty or not one of patch/minor/major, ask the user which type they want before proceeding.

**CRITICAL**: Never manually edit version files or call `./scripts/publish_to_pypi.sh` directly. Always use the Makefile targets.
""",
    "test.md": """\
---
description: "Run the test suite"
argument-hint: "[path or pytest flags]"
---

Run the claude-mpm test suite.

If $ARGUMENTS is provided, pass it as additional pytest arguments (e.g., a specific test file path or flags).

Run the tests:
```
uv run pytest -n auto $ARGUMENTS
```

**Tips**:
- Use `-n auto` (default) to parallelize across all CPU cores via pytest-xdist.
- Use `-p no:xdist` instead of `-n auto` when debugging flaky or order-dependent tests.
- Use `-x` to stop on first failure.
- Use `-k "test_name"` to run a specific test by name.
- Use `--cov=src/claude_mpm` to generate a coverage report.

After the run, summarize: total tests, passed, failed, skipped, and any errors.
""",
    "agent-list.md": """\
---
description: "List all available agents with their capabilities"
---

List all available agents in the claude-mpm project.

1. Find agent files in `.claude/agents/` (project-level) and `~/.claude/agents/` (user-level).

2. For each `.md` file found, read the YAML frontmatter and extract:
   - `name` — agent identifier
   - `description` — when/how to use it
   - `model` — which model it uses (if specified)
   - `tools` — allowed tools (if specified)
   - `skills` — preloaded skills (if specified)

3. Display a formatted table or list with columns: **Name**, **Model**, **Description** (truncated to ~80 chars), **Skills**.

4. Group results by location: project-level agents first, then user-level agents.

5. Report total counts: X project agents, Y user-level agents.
""",
}


def run_migration(installation_dir: Path | None = None) -> bool:
    """Create .claude/commands/ and populate with default command templates.

    Args:
        installation_dir: Root of the project (default: cwd)

    Returns:
        True on success
    """
    project_root = installation_dir or Path.cwd()
    commands_dir = project_root / ".claude" / "commands"

    created_dir = False
    if not commands_dir.exists():
        commands_dir.mkdir(parents=True)
        created_dir = True
        logger.info("Created directory: %s", commands_dir)

    written = 0
    skipped = 0

    for filename, content in _COMMAND_TEMPLATES.items():
        target = commands_dir / filename
        if target.exists():
            logger.debug("Skipping %s: already exists", filename)
            skipped += 1
            continue

        target.write_text(content, encoding="utf-8")
        logger.info("Created command template: %s", filename)
        written += 1

    logger.info(
        "Commands migration: dir=%s, written=%d, skipped=%d",
        "created" if created_dir else "existed",
        written,
        skipped,
    )

    return True
