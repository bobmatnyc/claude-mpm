# Phase 0: Scope Abstraction

## Objective

Extract the scope-based path resolution pattern already present in the CLI (`configure_paths.py`) into a shared module (`core/config_scope.py`) that both CLI and API layers can import. Extend it to cover Claude Code deployment directories (`.claude/agents/`, `~/.claude/skills/`, `.claude/agents/unused/`) in addition to MPM configuration directories.

This is the foundation for Phases 2-4. Without a shared scope resolver, the API handlers will continue to hardcode paths like `Path.cwd() / ".claude" / "agents"`, making future scope expansion (user-level agent deployment) require a rewrite.

## Prerequisites

None. This is the first phase and has no dependencies.

## Scope

**IN SCOPE:**
- New `ConfigScope(str, Enum)` with `PROJECT` and `USER` values
- Four pure resolver functions: `resolve_agents_dir`, `resolve_skills_dir`, `resolve_archive_dir`, `resolve_config_dir`
- New file at `src/claude_mpm/core/config_scope.py`
- Update API handlers to use resolvers instead of hardcoded paths

**NOT IN SCOPE:**
- Modifying `configure_paths.py` in `cli/commands/` -- it stays untouched
- Refactoring the CLI to use the new enum -- existing string comparisons continue working
- Adding user-scope support to the API -- only `PROJECT` scope is active for now
- Modifying `UnifiedPathManager` -- it serves a different purpose (MPM internal paths)

## Current State

The codebase has **no single, reusable scope abstraction**. Instead, scope-related patterns are scattered across multiple files:

### 1. CLI Raw String Scope
**File:** `src/claude_mpm/cli/commands/configure.py` line 182
```python
self.current_scope = getattr(args, "scope", "project")
```
The scope is a plain `str` propagated via constructor parameters to child components.

### 2. configure_paths.py -- Right Pattern, Wrong Location
**File:** `src/claude_mpm/cli/commands/configure_paths.py` lines 60-104

Three pure functions that resolve MPM config directories based on scope:
- `get_config_directory(scope: str, project_dir: Path)` -- resolves `.claude-mpm/`
- `get_agents_directory(scope: str, project_dir: Path)` -- resolves `.claude-mpm/agents/`
- `get_behaviors_directory(scope: str, project_dir: Path)` -- resolves `.claude-mpm/behaviors/`

These live in `cli/commands/`, so the API layer (`services/config_api/`) cannot import them without creating a circular dependency. They also resolve MPM config directories, not Claude Code deployment directories.

### 3. UnifiedPathManager -- Scope-Parameterized but MPM-Only
**File:** `src/claude_mpm/core/unified_paths.py` lines 446-547

Has methods like `get_config_dir(scope="project")` and `get_agents_dir(scope="framework")` but these resolve MPM internal paths (`.claude-mpm/`), not Claude Code directories (`.claude/agents/`, `~/.claude/skills/`).

### 4. AgentTier -- Wrong Concept
**File:** `src/claude_mpm/core/unified_agent_registry.py` line 44
```python
class AgentTier(Enum):
    PROJECT = "project"
    USER = "user"
    SYSTEM = "system"
```
This models **agent loading precedence** (which agent wins when names collide across tiers), NOT storage scope. It includes `SYSTEM` which has no equivalent in the configure scope concept.

### 5. ContextScope -- Wrong Abstraction Level
**File:** `src/claude_mpm/services/unified/config_strategies/context_strategy.py` line 22
```python
class ContextScope(Enum):
    GLOBAL = "global"
    SESSION = "session"
    PROJECT = "project"
    # ... 6 more values
```
This is a runtime lifecycle enum for configuration strategy dispatch. It has 9 values, most irrelevant to file system scope.

### 6. API Handlers -- Hardcoded Paths (the problem)
**File:** `src/claude_mpm/services/config_api/autoconfig_handler.py` line 497
```python
agents_dir = Path.cwd() / ".claude" / "agents"
```
**File:** `src/claude_mpm/services/config_api/agent_deployment_handler.py` line 139
```python
Path.cwd() / ".claude" / "agents"
```
**File:** `src/claude_mpm/services/config_api/deployment_verifier.py` lines 58-59
```python
agents_dir = Path.cwd() / ".claude" / "agents"
skills_dir = Path.home() / ".claude" / "skills"
```

## Target State

A single module at `src/claude_mpm/core/config_scope.py` provides:

1. **`ConfigScope(str, Enum)`** with `PROJECT` and `USER` values
   - The `str` base class ensures `ConfigScope.PROJECT == "project"` evaluates to `True`, maintaining backward compatibility with all existing CLI string comparisons
   - Serializes cleanly to/from JSON for API payloads

2. **Four pure resolver functions:**
   - `resolve_agents_dir(scope, project_path)` -- returns `.claude/agents/` path for the given scope
   - `resolve_skills_dir(scope)` -- returns `~/.claude/skills/` (always user-scoped for now)
   - `resolve_archive_dir(scope, project_path)` -- returns `.claude/agents/unused/` for the given scope
   - `resolve_config_dir(scope, project_path)` -- returns `.claude-mpm/` for the given scope

3. API handlers use resolver calls instead of hardcoded `Path.cwd()` / `Path.home()` constructions.

4. The existing `configure_paths.py` in `cli/commands/` remains untouched.

## Implementation Steps

### Step 1: Create `core/config_scope.py`

**Create:** `src/claude_mpm/core/config_scope.py`

```python
"""Scope-based path resolution for Claude Code deployment directories.

WHY: Centralizes the mapping from configuration scope (project vs user)
to file system paths for agents, skills, and archives. Replaces hardcoded
paths scattered across API handlers.

DESIGN: Pure functions + str-based enum for backward compatibility.
The str base on ConfigScope ensures existing CLI code that compares
against raw "project"/"user" strings continues working unchanged.

NOTE: This module resolves CLAUDE CODE deployment directories (.claude/agents/,
~/.claude/skills/). For MPM configuration directories (.claude-mpm/agents/,
.claude-mpm/behaviors/), see cli/commands/configure_paths.py.
"""

from enum import Enum
from pathlib import Path


class ConfigScope(str, Enum):
    """Storage scope for configuration and deployment paths.

    The str base class ensures backward compatibility with existing
    CLI string comparisons (e.g., scope == "project" still works).
    """

    PROJECT = "project"
    USER = "user"


def resolve_agents_dir(scope: ConfigScope, project_path: Path) -> Path:
    """Resolve the Claude Code agents deployment directory.

    Args:
        scope: PROJECT deploys to <project>/.claude/agents/,
               USER deploys to ~/.claude/agents/
        project_path: Root directory of the project (used for PROJECT scope)

    Returns:
        Path to the agents directory
    """
    if scope == ConfigScope.PROJECT:
        return project_path / ".claude" / "agents"
    return Path.home() / ".claude" / "agents"


def resolve_skills_dir(scope: ConfigScope = ConfigScope.USER) -> Path:
    """Resolve the Claude Code skills directory.

    Currently always returns ~/.claude/skills/ regardless of scope,
    because Claude Code loads skills from the user home directory at
    startup. The scope parameter exists for future extensibility.

    Args:
        scope: Currently ignored (skills are always user-scoped)

    Returns:
        Path to the skills directory (~/.claude/skills/)
    """
    return Path.home() / ".claude" / "skills"


def resolve_archive_dir(scope: ConfigScope, project_path: Path) -> Path:
    """Resolve the agent archive directory.

    Archived agents are moved to an 'unused/' subdirectory within the
    agents directory for the given scope.

    Args:
        scope: PROJECT archives to <project>/.claude/agents/unused/,
               USER archives to ~/.claude/agents/unused/
        project_path: Root directory of the project (used for PROJECT scope)

    Returns:
        Path to the archive directory
    """
    return resolve_agents_dir(scope, project_path) / "unused"


def resolve_config_dir(scope: ConfigScope, project_path: Path) -> Path:
    """Resolve the MPM configuration directory.

    Args:
        scope: PROJECT resolves to <project>/.claude-mpm/,
               USER resolves to ~/.claude-mpm/
        project_path: Root directory of the project (used for PROJECT scope)

    Returns:
        Path to the MPM configuration directory
    """
    if scope == ConfigScope.PROJECT:
        return project_path / ".claude-mpm"
    return Path.home() / ".claude-mpm"
```

### Step 2: Update `autoconfig_handler.py` to use resolvers

**Modify:** `src/claude_mpm/services/config_api/autoconfig_handler.py`

At the top of the file, add import:
```python
from claude_mpm.core.config_scope import ConfigScope, resolve_agents_dir
```

At line 497, replace:
```python
agents_dir = Path.cwd() / ".claude" / "agents"
```
with:
```python
agents_dir = resolve_agents_dir(ConfigScope.PROJECT, project_path)
```

Note: `project_path` is already available in the `_run_auto_configure` function as a parameter (line 355).

### Step 3: Update `agent_deployment_handler.py` to use resolvers

**Modify:** `src/claude_mpm/services/config_api/agent_deployment_handler.py`

Replace the hardcoded `Path.cwd() / ".claude" / "agents"` at line 139 with:
```python
from claude_mpm.core.config_scope import ConfigScope, resolve_agents_dir
agents_dir = resolve_agents_dir(ConfigScope.PROJECT, project_path)
```

### Step 4: Update `deployment_verifier.py` constructor defaults

**Modify:** `src/claude_mpm/services/config_api/deployment_verifier.py`

At lines 58-59, replace the hardcoded constructor defaults:
```python
# Before
agents_dir = Path.cwd() / ".claude" / "agents"
skills_dir = Path.home() / ".claude" / "skills"

# After
from claude_mpm.core.config_scope import ConfigScope, resolve_agents_dir, resolve_skills_dir
agents_dir = resolve_agents_dir(ConfigScope.PROJECT, Path.cwd())
skills_dir = resolve_skills_dir()
```

### Step 5: Update `backup_manager.py` constructor defaults

**Modify:** `src/claude_mpm/services/config_api/backup_manager.py`

At lines 88-90, replace hardcoded paths with resolver calls (same pattern as Step 4).

### Step 6: Add unit tests

**Create:** `tests/core/test_config_scope.py`

Test cases:
- `ConfigScope.PROJECT == "project"` (backward compatibility)
- `ConfigScope.USER == "user"` (backward compatibility)
- `resolve_agents_dir(PROJECT, Path("/project"))` returns `/project/.claude/agents`
- `resolve_agents_dir(USER, Path("/project"))` returns `~/.claude/agents`
- `resolve_skills_dir()` returns `~/.claude/skills`
- `resolve_archive_dir(PROJECT, Path("/project"))` returns `/project/.claude/agents/unused`
- `resolve_config_dir(PROJECT, Path("/project"))` returns `/project/.claude-mpm`
- `resolve_config_dir(USER, Path("/project"))` returns `~/.claude-mpm`

## Devil's Advocate Analysis

### "Is a new enum actually needed, or could we just move the existing functions?"

The existing `configure_paths.py` functions could theoretically be moved to `core/` and extended. However:
- They take `scope: str` with no type safety -- any string is accepted, including `"global"` or `"session"` which are meaningless here
- They resolve MPM config directories (`.claude-mpm/`), not Claude Code directories (`.claude/agents/`). Extending them to do both would conflate two concerns
- A `str` enum gives us both type safety AND backward compatibility in one construct

**Verdict:** The enum is warranted. The cost is ~80 lines of new code. The benefit is type safety, IDE autocompletion, and clear documentation of valid scope values.

### "Could we just use AgentTier since it already has PROJECT and USER?"

No. `AgentTier` includes `SYSTEM` (a third tier for framework-bundled agents) and its semantics are about loading precedence, not deployment targets. Reusing it would mean:
- Adding scope-resolution logic to an enum designed for precedence ordering
- Confusing future developers about what `SYSTEM` means in a deployment context
- Creating a semantic mismatch that makes the code harder to understand

### "What if the new ConfigScope breaks existing CLI code?"

The `str` base class on `ConfigScope(str, Enum)` ensures that all existing comparisons like `if scope == "project":` continue working. The Python `str` enum evaluates `ConfigScope.PROJECT == "project"` as `True`. No CLI code changes are needed.

### "Should we refactor configure_paths.py to delegate to the new resolver?"

Not in this phase. The existing `configure_paths.py` functions work correctly and have zero test failures. Refactoring them to delegate to `config_scope.py` would be a nice-to-have but risks introducing regressions in the CLI configure command for no immediate benefit. It can be done in a future cleanup pass.

### "Is putting this in core/ the right location?"

Yes. `core/` is the shared foundation layer that both `cli/` and `services/` can import. The `core/` package already contains `logging_config.py`, `unified_paths.py`, `types.py`, and other shared utilities. A scope resolver fits this pattern.

## Acceptance Criteria

1. `src/claude_mpm/core/config_scope.py` exists with `ConfigScope` enum and four resolver functions
2. `autoconfig_handler.py` uses `resolve_agents_dir()` instead of `Path.cwd() / ".claude" / "agents"` at line 497
3. `agent_deployment_handler.py` uses resolver instead of hardcoded path at line 139
4. `deployment_verifier.py` uses resolvers for its constructor defaults
5. All existing tests pass without modification (including CLI tests)
6. Unit tests for `ConfigScope` and all four resolver functions exist and pass
7. `ConfigScope.PROJECT == "project"` evaluates to `True` (backward compatibility verified)

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| CLI regression from new enum | `str` base class ensures backward compatibility; run full CLI test suite |
| Import cycle between `core/` and `services/` | Resolver functions are pure (no imports from other project modules) |
| `Path.cwd()` change breaks API behavior | `project_path` already passed as parameter in all API handlers; use it instead of `Path.cwd()` |

## Estimated Effort

**S (1-2 hours)**

- 30 minutes to write `config_scope.py` (80 lines, all pure functions)
- 30 minutes to update 4 handler files (replacing hardcoded paths with resolver calls)
- 30 minutes to write and run unit tests
- Buffer for any unexpected import issues
