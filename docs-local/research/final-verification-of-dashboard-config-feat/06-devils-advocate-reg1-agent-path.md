# Devil's Advocate: REG-1 AgentManager Default Path Change

**Date**: 2026-02-19
**Investigator**: Research Agent (Devil's Advocate mode)
**Branch**: `ui-agents-skills-config`
**Claim**: The default `project_dir` changed from `{root}/.claude-mpm/agents` to `{root}/.claude/agents`, causing agents to silently not be found.

---

## Executive Verdict

**The path change is a BUG FIX, not a regression.** The main branch's default was already broken at runtime, and the feature branch corrects it to match where agents are actually deployed.

**Risk level**: NONE (downgraded from MEDIUM)
**Recommended action**: KEEP the change as-is. No revert, no dual-path fallback needed.

---

## 1. Complete List of AgentManager() Callers

### 1.1 Production Code Callers (src/)

| File | Line | Constructor Call | Passes explicit project_dir? | Affected by default change? |
|------|------|-----------------|-----------------------------|-----------------------------|
| `agents/agent_loader_integration.py` | 26 | `AgentManager()` | NO | YES -- uses default |
| `services/agents/deployment/agent_lifecycle_manager.py` | 212 | `AgentManager()` | NO | YES -- uses default |
| `services/monitor/config_routes.py` | 44 | `AgentManager(project_dir=agents_dir)` | YES (`Path.cwd() / ".claude" / "agents"`) | NO -- already passes `.claude/agents` |
| `cli/commands/configure.py` | 191 | `SimpleAgentManager(config_dir)` | YES (different class entirely) | NO -- different class |

### 1.2 Test Code Callers (tests/)

| File | Line | Constructor Call | Passes explicit project_dir? |
|------|------|-----------------|------------------------------|
| `tests/test_phase2_agent_manager.py` | 39 | `AgentManager(framework_dir=..., project_dir=...)` | YES |
| All `SimpleAgentManager` calls in tests | various | `SimpleAgentManager(temp_dir)` | YES (different class) |

### 1.3 Tool/Dev Code

| File | Line | Constructor Call | Context |
|------|------|-----------------|---------|
| `tools/dev/verify_import_fixes.py` | 60 | `AgentManager()` | Dev utility only |

**Summary**: Only 2 production callers use the default path: `agent_loader_integration.py` and `agent_lifecycle_manager.py`. One caller (`config_routes.py`) explicitly passes `.claude/agents`. All test callers pass explicit paths.

---

## 2. The Main Branch Default Was ALREADY BROKEN

### Critical Finding: `CONFIG_DIR` Attribute Does Not Exist

The main branch's default path code at line 68 is:

```python
self.project_dir = project_root / get_path_manager().CONFIG_DIR / "agents"
```

However, `UnifiedPathManager` (the class returned by `get_path_manager()`) does NOT have a `CONFIG_DIR` attribute. It has:
- `CONFIG_DIR_NAME = ".claude-mpm"` (a class-level string constant)
- Various methods like `get_config_dir(scope)`, `get_project_config_dir()`, etc.

**Verified by direct Python execution on the main branch:**

```python
>>> from claude_mpm.core.unified_paths import get_path_manager
>>> pm = get_path_manager()
>>> pm.CONFIG_DIR
AttributeError: 'UnifiedPathManager' object has no attribute 'CONFIG_DIR'
```

This means **any code path on main that uses the default `project_dir` would crash with an `AttributeError` at runtime**. The default path `{root}/.claude-mpm/agents` was never actually reachable.

### Same Bug Exists in Other Files on Main

The broken `CONFIG_DIR` reference also appears in:
- `src/claude_mpm/agents/async_agent_loader.py:113` (`get_path_manager().CONFIG_DIR`)
- `src/claude_mpm/services/agents/loading/framework_agent_loader.py:70,91,129` (`get_path_manager().CONFIG_DIR`)
- `src/claude_mpm/config/agent_config.py:242,261` (`get_path_manager().CONFIG_DIR`)
- `src/claude_mpm/services/version_control/branch_strategy.py:313` (`get_path_manager().CONFIG_DIR`)

These all would crash if reached. The callers that work in practice all pass explicit paths, bypassing the broken default.

---

## 3. Where Agents Actually Exist on Disk

### Feature Branch (`claude-mpm-fork`)

| Directory | Contents |
|-----------|----------|
| `.claude/agents/` | **48 agent .md files** + deployment state + dependency cache |
| `.claude-mpm/agents/` | **EMPTY** (only `.` and `..`) |

### Main Branch (`claude-mpm`)

| Directory | Contents |
|-----------|----------|
| `.claude/agents/` | **42+ agent .md files** + deployment state + dependency cache |
| `.claude-mpm/agents/` | **EMPTY** (only `.` and `..`) |

**Conclusion**: No agents have EVER been deployed to `.claude-mpm/agents/`. All agents live in `.claude/agents/`.

---

## 4. The Deployment System Confirms `.claude/agents/`

### `AgentsDirectoryResolver` (authoritative deployment target)

File: `src/claude_mpm/services/agents/deployment/agents_directory_resolver.py`

The resolver's documentation and code are unambiguous:

```python
# Line 26: "ALL AGENTS DEPLOY TO: <project_root>/.claude/agents/"
# Line 84: "Deploy to: <working_directory>/.claude/agents"

def determine_agents_directory(self, target_dir):
    if not target_dir:
        return self.working_directory / ".claude" / "agents"  # Line 122
```

### `config_scope.py` (new centralized path resolver)

File: `src/claude_mpm/core/config_scope.py`

```python
def resolve_agents_dir(scope, project_path):
    if scope == ConfigScope.PROJECT:
        return project_path / ".claude" / "agents"   # Line 43
    return Path.home() / ".claude" / "agents"         # Line 44
```

### `config_routes.py` (dashboard API)

```python
agents_dir = project_dir or (Path.cwd() / ".claude" / "agents")  # Line 43
```

### CLI `agents deploy` command

```python
deployment_dir = Path.home() / ".claude" / "agents"  # Lines 718, 2000, 2086
```

**Every single deployment-related component uses `.claude/agents/`.**

---

## 5. Path Convention Analysis

The codebase maintains a clear two-directory convention:

| Purpose | Directory | Used By |
|---------|-----------|---------|
| **MPM configuration** (agent states, behaviors, config) | `.claude-mpm/` | CLI configure command, `SimpleAgentManager` |
| **Claude Code runtime** (deployed agents, skills) | `.claude/` | Deployment system, Claude Code agent discovery |

The feature branch's change aligns the `AgentManager` default with where agents actually live at runtime (`.claude/agents/`), which is where Claude Code discovers them.

The `.claude-mpm/agents/` path in the main branch was the result of a confused reference to `CONFIG_DIR` (which doesn't even exist as an attribute). It was never a deliberate choice -- it was a bug that happened to be unreachable because all active callers pass explicit paths.

---

## 6. Is There a Migration Concern?

**No.** `.claude-mpm/agents/` is empty on both the main and feature branches. No user has ever had agents deployed there because:

1. The deployment system (`AgentsDirectoryResolver`) has always targeted `.claude/agents/`
2. The CLI deploy command targets `.claude/agents/`
3. The broken `CONFIG_DIR` reference meant the default was never actually used

The `.claude-mpm/` directory is used for MPM's own configuration (agent states, behaviors, settings), NOT for deployed agent files that Claude Code reads.

---

## 7. Remaining Pre-Existing Bug: `CONFIG_DIR` References

While the feature branch fixes the `AgentManager` default, several OTHER files still reference the non-existent `get_path_manager().CONFIG_DIR`:

| File | Line | Code |
|------|------|------|
| `agents/async_agent_loader.py` | 113 | `Path.cwd() / get_path_manager().CONFIG_DIR / "agents"` |
| `services/agents/loading/framework_agent_loader.py` | 70 | `project_dir / get_path_manager().CONFIG_DIR / "agents"` |
| `services/agents/loading/framework_agent_loader.py` | 91 | `framework_dir / get_path_manager().CONFIG_DIR / "agents"` |
| `services/agents/loading/framework_agent_loader.py` | 129 | `path / get_path_manager().CONFIG_DIR` |
| `config/agent_config.py` | 242 | `Path.cwd() / get_path_manager().CONFIG_DIR / "agent_config.yaml"` |
| `config/agent_config.py` | 261 | `Path.cwd() / get_path_manager().CONFIG_DIR / "agents"` |
| `services/version_control/branch_strategy.py` | 313 | `get_path_manager().CONFIG_DIR` |

These are all pre-existing bugs on main, not introduced by the feature branch. They would raise `AttributeError` if their code paths are reached. The likely intended attribute was `CONFIG_DIR_NAME` (which equals `".claude-mpm"`).

**This is a separate issue from REG-1 and should be tracked independently.**

---

## 8. Final Assessment

### The Claim: "Changed default from `.claude-mpm/agents` to `.claude/agents`, causing agents to silently not be found"

**Verdict: FALSE on all counts.**

1. **The "old" default was never reachable.** `get_path_manager().CONFIG_DIR` raises `AttributeError`. No caller ever reached this path in production.

2. **No agents exist in `.claude-mpm/agents/`.** Both branches have empty directories there. There is nothing to "not find."

3. **The new default matches reality.** All 48 deployed agents live in `.claude/agents/`. The deployment system has always targeted `.claude/agents/`.

4. **Only 2 production callers use the default**, and both would have crashed on main if they ever ran without explicit paths. On the feature branch, they now correctly resolve to where agents actually are.

### Classification

| Attribute | Value |
|-----------|-------|
| Risk Level | **NONE** (was MEDIUM) |
| Type | **BUG FIX** (not regression) |
| Behavior Change | The default path now works instead of crashing |
| Data Loss Risk | Zero (no data exists at old path) |
| Backward Compatibility | Improved (was broken, now works) |

### Recommended Action: KEEP

**Keep the change as-is. No revert needed. No dual-path fallback needed.**

The feature branch correctly hardcodes `.claude/agents/` as the default, which:
- Matches where the deployment system puts agents
- Matches where Claude Code discovers agents
- Matches what `config_scope.py` resolves
- Matches what the dashboard API (`config_routes.py`) uses
- Actually works (unlike the main branch's broken `CONFIG_DIR` reference)

### Optional Follow-Up (Separate Issue)

Fix the remaining `get_path_manager().CONFIG_DIR` references in other files (listed in Section 7) to use either:
- `get_path_manager().CONFIG_DIR_NAME` (if `.claude-mpm` is intended)
- Hardcoded `".claude"` (if Claude Code's directory is intended)
- `config_scope.resolve_*()` functions (preferred for new code)

This is a pre-existing bug on main, not related to this feature branch.

---

## Evidence Chain

1. **Main branch `agent_management_service.py:68`**: `get_path_manager().CONFIG_DIR` -- attribute does not exist, raises `AttributeError`
2. **Feature branch `agent_management_service.py:68`**: `project_root / ".claude" / "agents"` -- works, matches deployment target
3. **`UnifiedPathManager`**: Only has `CONFIG_DIR_NAME = ".claude-mpm"`, not `CONFIG_DIR`
4. **Disk state**: `.claude/agents/` has 48 agents; `.claude-mpm/agents/` is empty (both branches)
5. **`AgentsDirectoryResolver:122`**: Default deployment target is `working_directory / ".claude" / "agents"`
6. **`config_scope.py:43`**: `project_path / ".claude" / "agents"`
7. **CLI agents.py**: All deployment targets use `.claude/agents/`
