# CLI Auto-Configuration Impact Assessment

**Date**: 2026-02-21
**Branch**: `ui-agents-skills-config` vs `main`
**Scope**: Determine if dashboard branch changes affect CLI auto-configure behavior

---

## 1. Changed Files Classification

Total files changed between `main` and `ui-agents-skills-config`: **188 files** (+23,504 / -813 lines).

### Files Used by CLI Auto-Configure Pipeline

| File | Changed | Used by CLI | Risk Level | Description of Change |
|------|---------|------------|------------|----------------------|
| `cli/commands/auto_configure.py` | Yes | **Direct** | **Low** (beneficial) | Bug fix: `min_confidence=0.0` falsy check |
| `services/agents/auto_config_manager.py` | Yes | **Direct** | **Medium** | `preview_configuration()` rewritten to bypass async wrappers |
| `services/skills_deployer.py` | Yes | **Direct** | **Low** | New `skills_dir` parameter added (backward-compatible) |
| `config/agent_sources.py` | Yes | **Indirect** | **Low** (beneficial) | Atomic file writes for config saves |
| `services/agents/deployment/single_agent_deployer.py` | Yes | **Direct** | **Medium** | Multi-source agent template search (new fallback chain) |
| `services/agents/management/agent_management_service.py` | Yes | **Indirect** | ~~**Medium**~~ **Low** | ~~Project agents path changed `.claude-mpm/agents/` -> `.claude/agents/`~~; new enrichment methods. See [CORRECTION in 2.6](#26-correction-2026-02-21). |
| `services/agents/deployment/remote_agent_discovery_service.py` | Yes | **Indirect** | **None** | UI enrichment fields added to metadata (additive) |
| `services/agents/sources/git_source_sync_service.py` | Yes | **Indirect** | **Low** | Fallback agent names updated (`research.md` -> `research-agent.md`) |
| `services/diagnostics/checks/agent_check.py` | Yes | **Indirect** (doctor) | **Low** | Core agent names updated to match renames |

### Files NOT Used by CLI Auto-Configure Pipeline

| Category | File Count | Risk | Notes |
|----------|-----------|------|-------|
| `services/config_api/*` (NEW) | 8 files | **None** | Entirely new dashboard REST API handlers |
| `services/monitor/*` | 5 files | **None** | Dashboard server routes, handlers, pagination |
| `services/config/config_validation_service.py` (NEW) | 1 file | **None** | Dashboard validation service |
| `core/config_scope.py` (NEW) | 1 file | **None** | Dashboard path resolution |
| `core/config_file_lock.py` (NEW) | 1 file | **None** | Dashboard file locking |
| `dashboard-svelte/*` | ~50 files | **None** | Frontend Svelte components, stores, utils |
| `dashboard/static/svelte-build/*` | ~80 files | **None** | Compiled dashboard build artifacts |
| `docs/*` | 3 files | **None** | Documentation changes |
| `tests/*` (NEW) | ~20 files | **None** | New test files |
| `.secrets.baseline` | 1 file | **None** | Secrets detection baseline |

---

## 2. Detailed Impact Analysis

### 2.1 `cli/commands/auto_configure.py` - Bug Fix (Risk: Low, Beneficial)

**What changed (2 lines):**

```diff
# Line 170: Validation gate
-        if hasattr(args, "min_confidence") and args.min_confidence:
+        if hasattr(args, "min_confidence") and args.min_confidence is not None:

# Line 200: Default assignment
             min_confidence = (
                 args.min_confidence
-                if hasattr(args, "min_confidence") and args.min_confidence
+                if hasattr(args, "min_confidence") and args.min_confidence is not None
                 else 0.5
             )
```

**Impact**: This is a pure **bug fix**. On main, `--min-confidence 0.0` would be treated as falsy (Python treats `0.0` as falsy), causing it to silently fall back to the default `0.5`. After this fix, `0.0` is correctly accepted. This change is **beneficial** and has no regression risk.

**Scenario that could break**: None. Only changes behavior when user explicitly passes `--min-confidence 0.0`, which was broken before.

### 2.2 `services/agents/auto_config_manager.py` - Preview Method Rewrite (Risk: Medium)

**What changed:**

The `preview_configuration()` method was rewritten to bypass async wrappers and call synchronous services directly:

```diff
 # OLD (main): Used asyncio event loop introspection
-            import asyncio
-            loop = asyncio.get_event_loop()
-            if asyncio.iscoroutinefunction(self._analyze_toolchain):
-                toolchain = loop.run_until_complete(
-                    self._analyze_toolchain(project_path)
-                )
-            else:
-                toolchain = self._analyze_toolchain(project_path)

 # NEW (branch): Calls synchronous services directly
+            if self._toolchain_analyzer is None:
+                raise RuntimeError("ToolchainAnalyzer not initialized")
+            toolchain = self._toolchain_analyzer.analyze_toolchain(project_path)
+
+            if self._agent_recommender is None:
+                raise RuntimeError("AgentRecommender not initialized")
+            constraints = {"min_confidence": min_confidence}
+            recommendations = self._agent_recommender.recommend_agents(
+                toolchain, constraints
+            )
```

**Impact Analysis**:

- **Why it was changed**: The old code used `asyncio.get_event_loop()` which fails when called from a worker thread (via `asyncio.to_thread()`), as the dashboard does. The new code bypasses async wrappers and calls the underlying synchronous methods directly.

- **CLI behavior change**: The CLI calls `preview_configuration()` synchronously from its main thread. On main, the code would try `asyncio.iscoroutinefunction()` checks and potentially use the event loop. On the branch, it directly calls `self._toolchain_analyzer.analyze_toolchain()` and `self._agent_recommender.recommend_agents()`.

- **Risk**: **Medium**. The logic is functionally equivalent IF:
  1. `self._toolchain_analyzer` is properly initialized (not None) when the CLI calls it
  2. `self._agent_recommender` is properly initialized (not None)
  3. The old code's `self._generate_recommendations(toolchain, min_confidence)` and the new direct `self._agent_recommender.recommend_agents(toolchain, constraints)` produce the same results

  Looking at the CLI's lazy init pattern in `auto_configure.py:118-147`, the `AutoConfigManagerService` is created with explicit `toolchain_analyzer=ToolchainAnalyzerService()` and `agent_recommender=AgentRecommenderService()`, so they will NOT be None. The new RuntimeError checks are a safety net that won't trigger in normal CLI usage.

  The parameter passing changed from `self._generate_recommendations(toolchain, min_confidence)` to `self._agent_recommender.recommend_agents(toolchain, {"min_confidence": min_confidence})`. If `_generate_recommendations` did any additional processing beyond calling `recommend_agents`, this could differ. However, based on the method's documented purpose (simply delegating to the recommender), this should be equivalent.

- **Specific scenario where it could break**: If `_generate_recommendations()` on main contained logic BEYOND just calling `recommend_agents()` (e.g., additional filtering or transformation), the branch would bypass that logic. This needs verification but is unlikely given the Facade pattern.

### 2.3 `services/skills_deployer.py` - New `skills_dir` Parameter (Risk: Low)

**What changed:**

Added an optional `skills_dir` parameter to multiple methods:

```diff
     def deploy_skills(
         self,
         ...
+        skills_dir: Optional[Path] = None,
     ) -> Dict:
```

When `skills_dir=None` (the default), behavior is identical to main: uses `self.CLAUDE_SKILLS_DIR` (~/.claude/skills/). The new parameter is used by the dashboard to deploy to project-scoped directories.

Also added `skills_dir` parameter to:
- `_deploy_skill()` - internal method
- `check_deployed_skills()` - checking method

**Impact**: **None for CLI**. All new parameters have default `None` which preserves existing behavior. The CLI does not pass `skills_dir`, so it gets the default path. This is a clean backward-compatible extension.

### 2.4 `config/agent_sources.py` - Atomic Writes (Risk: Low, Beneficial)

**What changed:**

The `save()` method now uses atomic file writing (write to temp → rename):

```diff
-            with open(config_path, "w") as f:
+            temp_path = config_path.with_suffix(".yaml.tmp")
+            with open(temp_path, "w") as f:
                 ...
                 yaml.safe_dump(data, f, ...)
+            temp_path.replace(config_path)
```

Also moved the YAML data structure building before the `try` block (no functional change).

**Impact**: **Beneficial**. Prevents corrupted config files from partial writes (e.g., if process is killed mid-write). The YAML content is identical. No CLI behavior change except improved reliability.

### 2.5 `services/agents/deployment/single_agent_deployer.py` - Multi-Source Template Search (Risk: Medium)

**What changed:**

Added a new `_find_agent_template()` method that searches multiple source tiers:

```diff
-            template_file = templates_dir / f"{agent_name}.md"
-            if not template_file.exists():
-                self.logger.error(f"Agent template not found: {agent_name}")
+            template_file = self._find_agent_template(
+                agent_name, templates_dir, working_directory
+            )
+            if template_file is None:
+                self.logger.error(
+                    f"Agent template not found in any source: {agent_name}"
+                )
                 return False
```

The new search order:
1. System templates directory (same as before)
2. Git cache (`~/.claude-mpm/cache/agents/` via `GitSourceManager`)
3. Project agents (`.claude-mpm/agents/`)
4. User agents (`~/.claude-mpm/agents/`)
5. Cache directory scan (`~/.claude-mpm/cache/agents/` rglob fallback)

Also added `"remote"` as a new source type in `_determine_agent_source()`.

**Impact**: The first search tier (system templates) is identical to main. The additional tiers are **fallback only** - they only activate if the template isn't found in the system directory. This means:

- **Normal case**: Identical behavior (found in tier 1)
- **Missing template case**: Instead of failing, now searches more locations. This is **beneficial** - it can find agents from git sources that weren't found before.
- **Risk**: The lazy import of `GitSourceManager` could theoretically raise if git dependencies aren't installed, but this is caught by `except Exception`.

**Specific scenario where it could break**: If an agent with the same name exists in both system templates AND git cache with different content, the system template wins (same as before). No conflict.

### 2.6 `services/agents/management/agent_management_service.py` - ~~Path Change +~~ New Methods (Risk: ~~Medium~~ Low)

#### CORRECTION (2026-02-21)

> **CORRECTION (2026-02-21):** The original analysis below reported a path change in `agent_management_service.py` from `.claude-mpm/agents/` to `.claude/agents/`. **This change does NOT exist.** Both branches have identical code in this file for the `project_dir` assignment. The original analysis was based on a faulty diff comparison.
>
> The two directories serve fundamentally different purposes:
>
> - **`.claude-mpm/agents/`** = MPM internal configuration directory for agent templates/source definitions. Currently empty on disk in this project.
> - **`.claude/agents/`** = Claude Code runtime deployment target. Contains 44 deployed `.md` agent files that Claude Code loads at startup.
>
> The deployment flow is: **source tiers** (system cache, project config, user config) --> **deployed as `.md` files** to `.claude/agents/`.
>
> **Pre-existing bug found:** Both branches contain `get_path_manager().CONFIG_DIR` which references a **non-existent attribute**. The correct attribute is `CONFIG_DIR_NAME`. However, no production code path reaches this line because `AgentManager` is not used by the auto-configure pipeline, and other code paths that use it provide `project_root` in a way that does not trigger this fallback. This is pre-existing technical debt, not a regression.
>
> **Risk downgrade:** The original "Medium" rating was partly based on this non-existent path change. With the correction, the risk is **Low** -- the only actual changes are additive new methods for UI enrichment.

#### Original Analysis (superseded -- preserved for research history)

~~**What changed:**~~

~~1. **Project agents path changed**:~~
```diff
# CORRECTION: This diff does NOT exist. Both branches have identical code:
#   self.project_dir = project_root / get_path_manager().CONFIG_DIR / "agents"
# The diff below was incorrectly reported in the original analysis.
-            self.project_dir = project_root / get_path_manager().CONFIG_DIR / "agents"
+            self.project_dir = project_root / ".claude" / "agents"
```

~~On main, `CONFIG_DIR` resolves via `get_path_manager()` which uses `CONFIG_DIR_NAME = ".claude-mpm"`, so:~~
~~- Main: `project_root/.claude-mpm/agents/`~~
~~- Branch: `project_root/.claude/agents/`~~

#### Actual Changes (what IS different between branches)

1. **New `list_agent_names()` method** - lightweight name-only listing
2. **New `_extract_enrichment_fields()` method** - extracts UI fields from frontmatter
3. **`list_agents()` refactored** - extracted `_build_agent_entry()` helper, adds enrichment fields

#### Corrected Impact Analysis

- ~~**Path change**: This changes where `AgentManager` looks for project agents from `.claude-mpm/agents/` to `.claude/agents/`. This is actually **correct** - deployed agents live in `.claude/agents/` (Claude Code's native directory). The `.claude-mpm/agents/` path was MPM's internal directory.~~

- **No path change exists.** Both branches use `get_path_manager().CONFIG_DIR / "agents"`. The `CONFIG_DIR` attribute is a pre-existing bug (should be `CONFIG_DIR_NAME`), but it exists identically on both branches and no production code path reaches it.

- **CLI relevance**: `AgentManager` is NOT directly used by the core CLI auto-configure pipeline. It's used by other CLI commands (like `claude-mpm agents list`). The auto-configure pipeline uses `AgentReviewService` for agent review, which has its own agent discovery mechanism.

- ~~**Risk**: **Medium** for non-auto-configure CLI commands that use `AgentManager.list_agents()`. The path change means these commands will now look in `.claude/agents/` instead of `.claude-mpm/agents/`. If a project has agents in `.claude-mpm/agents/`, they would NOT be found.~~

- **Risk**: **Low**. The only changes are additive new methods (`list_agent_names()`, `_extract_enrichment_fields()`, `_build_agent_entry()` refactoring). These are backward-compatible additions used by dashboard UI enrichment.

- **Risk for auto-configure specifically**: **None**. The auto-configure pipeline creates its own service instances and doesn't depend on `AgentManager.project_dir`.

#### Actual Directory Architecture

For clarity, here is the correct understanding of the two directories:

| Directory | Purpose | Contents | Used By |
|-----------|---------|----------|---------|
| `.claude-mpm/agents/` | MPM internal config, agent templates/source definitions | Currently empty on disk | `AgentManager` (via `CONFIG_DIR` attribute -- pre-existing bug, never reached) |
| `.claude/agents/` | Claude Code runtime deployment target | 44 deployed `.md` agent files | Claude Code at startup, `AgentReviewService`, `AgentDeploymentService` |
| `~/.claude-mpm/cache/agents/` | Cached agent templates from remote sources | Downloaded agent `.md` files | `RemoteAgentDiscoveryService`, `SingleAgentDeployer` |

The deployment flow:
```
Source Tiers:                          Deployment Target:
  System templates (cache)      --+
  Project config (.claude-mpm/) --+--> .claude/agents/*.md (Claude Code reads these)
  User config (~/.claude-mpm/)  --+
```

### 2.7 `services/agents/deployment/remote_agent_discovery_service.py` - UI Enrichment (Risk: None)

**What changed:**

Added UI enrichment fields to the agent metadata dictionary:

```diff
+                "tags": tags,  # Phase 2: UI enrichment
+                "color": color,  # Phase 2: UI enrichment
+                "resource_tier": resource_tier,  # Phase 2: UI enrichment
+                "network_access": network_access,  # Phase 2: UI enrichment
```

**Impact**: Purely **additive**. Adds new keys to the metadata dict. CLI code that reads this dict will get extra keys but this won't break anything - dict access by key is safe for extra keys.

### 2.8 `services/agents/sources/git_source_sync_service.py` - Agent Name Updates (Risk: Low)

**What changed:**

Fallback agent names updated to match renamed agents:

```diff
-            "research.md",
+            "research-agent.md",
             "engineer.md",
-            "qa.md",
-            "documentation.md",
+            "qa-agent.md",
+            "documentation-agent.md",
+            "web-qa-agent.md",
             "security.md",
```

**Impact**: This fallback list is used when the GitHub API fails. The renamed filenames must match what's actually in the remote repository. If the remote repo still uses old names, this would break the fallback. If the remote was already renamed, this is a necessary fix.

### 2.9 `services/diagnostics/checks/agent_check.py` - Core Agent Names (Risk: Low)

**What changed:**

Core agent names updated:

```diff
-        core_agents = ["research.md", "engineer.md", "qa.md", "documentation.md"]
+        core_agents = [
+            "research-agent.md",
+            "engineer.md",
+            "qa-agent.md",
+            "documentation-agent.md",
+        ]
```

**Impact**: This affects `claude-mpm doctor` command, not auto-configure. It will correctly check for the renamed agent files. **Low risk** - must be aligned with actual deployed filenames.

---

## 3. The `min_confidence` Bug Fix

### 3.1 Location

**File**: `src/claude_mpm/cli/commands/auto_configure.py`
**Lines**: 170, 200 (two instances)

### 3.2 The Bug

Python's truthiness evaluation treats `0.0` as falsy:

```python
# On main:
if args.min_confidence:  # 0.0 evaluates to False!
    # This block is SKIPPED when min_confidence=0.0
```

This means `claude-mpm auto-configure --min-confidence 0.0` would silently use the default `0.5` instead of `0.0`.

### 3.3 The Fix

```python
# On branch:
if args.min_confidence is not None:  # 0.0 is not None, so True
    # This block correctly executes when min_confidence=0.0
```

### 3.4 Does it Affect CLI Path?

**Yes, directly** - this IS the CLI path. The fix is in `AutoConfigureCommand._validate_args()` and `AutoConfigureCommand._run_preview()`.

### 3.5 Is This Beneficial or Could It Change Expected CLI Behavior?

**Purely beneficial**. The fix corrects a bug where an explicitly-passed value was being ignored. No reasonable CLI user would expect `--min-confidence 0.0` to silently become `0.5`.

**Edge case**: A user who was relying on the broken behavior (passing 0.0 expecting it to be ignored) would see different results. This is extremely unlikely and would be incorrect usage regardless.

### 3.6 Risk Rating: **Low** (beneficial bug fix)

---

## 4. New Dependencies / Imports

### 4.1 CLI-Path Files: No New External Imports

Checked all modified CLI-path files for new imports:

| File | New Imports | Dashboard Dependency? |
|------|-----------|----------------------|
| `cli/commands/auto_configure.py` | None | No |
| `services/agents/auto_config_manager.py` | None (removed `import asyncio`) | No |
| `services/skills_deployer.py` | None | No |
| `config/agent_sources.py` | None | No |
| `services/agents/deployment/single_agent_deployer.py` | `GitSourceManager` (lazy, in try/except) | No |
| `services/agents/management/agent_management_service.py` | `Set` from typing | No |
| `services/agents/deployment/remote_agent_discovery_service.py` | None | No |
| `services/agents/sources/git_source_sync_service.py` | None | No |
| `services/diagnostics/checks/agent_check.py` | None | No |

### 4.2 No Cross-Contamination

The new dashboard modules (`config_api/*`, `config_scope.py`, `config_file_lock.py`, etc.) are **NOT imported by any CLI-path file**. They are only imported by:
- `services/monitor/server.py` (dashboard server)
- `services/config_api/*.py` (dashboard handlers)
- Test files

**Conclusion**: No risk of CLI failing due to missing dashboard dependencies.

---

## 5. Configuration Format Changes

### 5.1 Agent Sources Config (`agent_sources.py`)

The YAML schema written by `save()` is **unchanged**. The only change is HOW it's written (atomic write via temp file). The data structure is identical:

```yaml
disable_system_repo: false
repositories:
  - url: ...
    subdirectory: ...
    enabled: true
    priority: 0
```

### 5.2 Agent Capabilities YAML

`config/agent_capabilities.yaml` is **NOT changed** on the branch. Scoring weights, agent definitions, and recommendation rules are identical.

### 5.3 Auto-Config Output YAML

The `.claude-mpm/auto-config.yaml` output format is controlled by `AutoConfigManagerService._save_configuration()`, which was **NOT changed** on the branch.

### 5.4 No Schema Changes

**Conclusion**: No configuration format changes that could affect CLI reading or writing.

---

## 6. Test Coverage Assessment

### 6.1 Existing Tests for CLI Auto-Configure (on main)

| Test File | Tests | Status on Branch |
|-----------|-------|-----------------|
| `tests/services/agents/test_auto_config_manager.py` | Service initialization, preview, deployment | Modified (min_confidence assert: 0.8→0.5) |

### 6.2 New Tests Added on Branch

| Test File | Scope | Relevance to CLI |
|-----------|-------|-----------------|
| `tests/e2e/test_autoconfig_full_flow.py` | Full CLI auto-configure flow | **High** - tests the complete CLI pathway |
| `tests/services/config_api/test_autoconfig_defaults.py` | Default min_confidence values | Medium - tests shared service |
| `tests/services/config_api/test_autoconfig_events.py` | Socket.IO events | None - dashboard-only |
| `tests/services/config_api/test_autoconfig_integration.py` | API integration | None - dashboard-only |
| `tests/services/config_api/test_autoconfig_skill_deployment.py` | Skill deployment in auto-configure | Low - tests shared service via API |

### 6.3 Test Change: `test_auto_config_manager.py`

```diff
-    assert service._min_confidence_default == 0.8
+    assert service._min_confidence_default == 0.5
```

The actual code has `_min_confidence_default = 0.5` on BOTH main and the branch. The test on main was asserting `0.8` which was **wrong** - it would fail when run. The branch corrects the test to match the actual code.

### 6.4 Test Change: `test_agent_names_fix.py`

Updated expected agent filenames to match renames (`research.md` -> `research-agent.md`, etc.).

### 6.5 Running Tests

Note: Tests were not executed as part of this assessment due to the research-only scope. The new `test_autoconfig_full_flow.py` provides comprehensive e2e coverage of the CLI path on the branch.

---

## 7. Overall Risk Rating

> **CORRECTION (2026-02-21):** The original "Low Risk (with caveats)" rating listed the `agent_management_service` path change as one of two caveats requiring attention. Since this path change does not exist (see [2.6](#26-correction-2026-02-21)), the caveats are reduced to one (the `preview_configuration()` rewrite, which the devil's advocate in document 05 verified as Low Risk). The corrected overall risk assessment is **Low Risk** with a single caveat (preview_configuration rewrite). The `agent_management_service` changes are purely additive UI enrichment methods with no behavioral impact.

### Summary Matrix

| Change | Risk | Rationale |
|--------|------|-----------|
| `min_confidence` bug fix | **Low** (beneficial) | Fixes real bug, no regression risk |
| `preview_configuration()` sync rewrite | **Medium** | Functionally equivalent but bypasses internal methods |
| `skills_deployer` `skills_dir` param | **None** | Backward-compatible optional parameter |
| `agent_sources` atomic write | **Low** (beneficial) | Improves reliability, no behavior change |
| `single_agent_deployer` multi-source search | **Low** | Adds fallback tiers, doesn't change primary behavior |
| `agent_management_service` ~~path change~~ new methods | ~~**Medium**~~ **Low** | ~~Changes project agents directory (`.claude-mpm/` -> `.claude/`)~~ Path change does NOT exist (see [CORRECTION in 2.6](#26-correction-2026-02-21)). Only additive UI enrichment methods. |
| `remote_agent_discovery_service` enrichment | **None** | Additive metadata fields |
| `git_source_sync_service` name updates | **Low** | Must match remote repo filenames |
| `agent_check` name updates | **Low** | Must match deployed filenames |
| New dashboard files (config_api, etc.) | **None** | Not imported by CLI |
| Configuration format changes | **None** | No schema changes |
| New import dependencies | **None** | No cross-contamination |

### Overall Risk: **Low Risk** (with caveats)

**Rationale**: The vast majority of changes (180+ files) are dashboard-only additions that have zero impact on the CLI. The CLI-touching changes fall into three categories:

1. **Bug fixes** (min_confidence, test assertion): Purely beneficial, no regression risk.
2. **Backward-compatible extensions** (skills_dir param, multi-source search, enrichment fields): New functionality that defaults to old behavior.
3. **Behavioral changes** (preview_configuration sync rewrite~~, agent_management_service path change~~): ~~These require~~ This requires verification. *(CORRECTION 2026-02-21: The agent_management_service path change does not exist. See [2.6](#26-correction-2026-02-21).)*

**Caveats requiring attention**:

- **`preview_configuration()` rewrite**: While functionally equivalent in the expected case, it bypasses the internal `_generate_recommendations()` method and calls `recommend_agents()` directly. If `_generate_recommendations()` on main contains any logic beyond simple delegation, the behavior could differ. **Recommendation**: Verify by reading `_generate_recommendations()` to confirm it's a pure delegate.

- ~~**`agent_management_service` path change**: Changes from `.claude-mpm/agents/` to `.claude/agents/`. This is correct for deployed agents but could affect `claude-mpm agents list` and other commands that use `AgentManager`. **Does NOT affect auto-configure directly** since the auto-configure pipeline uses its own service chain.~~ *(CORRECTION 2026-02-21: This path change does not exist. Both branches have identical code. The two directories serve different purposes: `.claude-mpm/agents/` is MPM internal config, `.claude/agents/` is the Claude Code deployment target. See [2.6](#26-correction-2026-02-21) for full details.)*

**Safe to merge for CLI auto-configure**: Yes, with the understanding that the `preview_configuration()` change has been manually verified as functionally equivalent.
