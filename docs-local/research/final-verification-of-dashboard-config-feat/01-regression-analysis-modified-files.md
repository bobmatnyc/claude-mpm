# Regression Analysis: Modified Files in `ui-agents-skills-config` Feature Branch

**Date**: 2026-02-19
**Branch**: `ui-agents-skills-config` (feature) vs `main` (baseline)
**Analyst**: Claude Opus 4.6 (research agent)
**Scope**: 6 modified Python files -- comparative analysis for CLI regression risk

---

## Executive Summary

This analysis compares 6 existing Python files modified in the `ui-agents-skills-config` feature branch against their counterparts in the `main` branch. The feature adds a dashboard UI for configuring agents and skills. The critical concern is whether the regular `claude-mpm` CLI command (non-dashboard mode) continues to work identically.

### Verdict: LOW-to-MEDIUM overall regression risk

- **5 of 6 files** are fully backward compatible with additive-only changes or safe refactors.
- **1 file** (`agent_management_service.py`) contains a **behavioral change** to the default `project_dir` path that is the single highest-risk item and requires verification.
- All existing public API signatures are preserved across all 6 files.
- No imports were removed; only additive imports were introduced.
- Error handling is preserved or improved in every case.

### Risk Summary Table

| File | Lines (Main -> Feature) | Risk Level | Change Type |
|------|------------------------|------------|-------------|
| `agent_sources.py` | 353 -> 362 | **LOW** | Safe refactor (atomic writes) |
| `auto_config_manager.py` | 798 -> 795 | **LOW** | Safe refactor (async -> sync bypass) |
| `remote_agent_discovery_service.py` | 866 -> 888 | **LOW** | Additive (UI enrichment fields) |
| `agent_management_service.py` | 648 -> 740 | **MEDIUM** | Behavioral change (project_dir path) + additive |
| `server.py` | 1662 -> 1736 | **LOW** | Additive (new routes, CORS, config infra) |
| `skills_deployer.py` | 1211 -> 1242 | **LOW** | Additive (optional `skills_dir` param) |

---

## Per-File Analysis

---

### 1. `agent_sources.py` -- Atomic Write Pattern

**Path**: `src/claude_mpm/config/agent_sources.py`
**Lines**: 353 (main) -> 362 (feature)
**Risk**: LOW

#### What Changed

The `save()` method was refactored to use an atomic write pattern (temp file + rename) instead of writing directly to the config file.

#### Main Branch (`save()` method, lines 146-191)

```python
try:
    with open(config_path, "w") as f:
        # Write header comments if requested
        if include_comments:
            f.write("# Claude MPM Agent Sources Configuration\n")
            # ... comments ...
            f.write("#\n\n")

        # Build YAML data structure
        data = {
            "disable_system_repo": self.disable_system_repo,
            "repositories": [
                {
                    "url": repo.url,
                    "subdirectory": repo.subdirectory,
                    "enabled": repo.enabled,
                    "priority": repo.priority,
                }
                for repo in self.repositories
            ],
        }

        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    logger.info(f"Configuration saved to {config_path}")

except Exception as e:
    logger.error(f"Failed to save configuration to {config_path}: {e}")
    raise
```

#### Feature Branch (`save()` method, lines 146-200)

```python
# Build YAML data structure
data = {
    "disable_system_repo": self.disable_system_repo,
    "repositories": [
        {
            "url": repo.url,
            "subdirectory": repo.subdirectory,
            "enabled": repo.enabled,
            "priority": repo.priority,
        }
        for repo in self.repositories
    ],
}

try:
    # Write atomically: write to temp file, then rename
    temp_path = config_path.with_suffix(".yaml.tmp")
    with open(temp_path, "w") as f:
        # Write header comments if requested
        if include_comments:
            f.write("# Claude MPM Agent Sources Configuration\n")
            # ... comments ...
            f.write("#\n\n")

        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    # Atomic rename
    temp_path.replace(config_path)

    logger.info(f"Configuration saved to {config_path}")

except Exception as e:
    logger.error(f"Failed to save configuration to {config_path}: {e}")
    # Clean up temp file if it exists
    temp_path = config_path.with_suffix(".yaml.tmp")
    if temp_path.exists():
        temp_path.unlink()
    raise
```

#### Analysis

| Aspect | Assessment |
|--------|-----------|
| **API Signature** | Unchanged -- `save(config_path, include_comments)` |
| **Return Type** | Unchanged -- `None` |
| **Behavioral Change** | Data structure built before try block (moved up); write targets temp file, then atomic rename |
| **Error Handling** | Improved -- adds temp file cleanup on exception |
| **Backward Compatibility** | Full -- callers see identical behavior; only internal write mechanics differ |
| **Regression Risk** | Negligible -- atomic writes are strictly safer than direct writes |

#### Critical Questions

- **Does this change affect CLI callers?** No. The `save()` method signature is identical. The YAML data written is identical. The only difference is the write-then-rename pattern, which prevents partial writes.
- **Can temp file cleanup fail?** The `temp_path.unlink()` is inside the exception handler and preceded by an `exists()` check. If cleanup itself fails, the exception from the original save is still re-raised. A stale `.yaml.tmp` file could remain, but this is a minor inconvenience, not a regression.

---

### 2. `auto_config_manager.py` -- Async-to-Sync Preview Refactor

**Path**: `src/claude_mpm/services/agents/auto_config_manager.py`
**Lines**: 798 (main) -> 795 (feature)
**Risk**: LOW

#### What Changed

The `preview_configuration()` method was refactored to call underlying synchronous services directly instead of using `asyncio.get_event_loop()` + `loop.run_until_complete()`. This fixes a real bug where the method would fail when called from a worker thread (via `asyncio.to_thread`) where no event loop is available.

#### Main Branch (`preview_configuration()`, lines 530-552)

```python
try:
    # Run analysis and recommendations synchronously for preview
    import asyncio

    loop = asyncio.get_event_loop()

    # Analyze toolchain
    if asyncio.iscoroutinefunction(self._analyze_toolchain):
        toolchain = loop.run_until_complete(
            self._analyze_toolchain(project_path)
        )
    else:
        toolchain = self._analyze_toolchain(project_path)

    # Generate recommendations
    if asyncio.iscoroutinefunction(self._generate_recommendations):
        recommendations = loop.run_until_complete(
            self._generate_recommendations(toolchain, min_confidence)
        )
    else:
        recommendations = self._generate_recommendations(
            toolchain, min_confidence
        )
```

#### Feature Branch (`preview_configuration()`, lines 530-549)

```python
try:
    # Call underlying synchronous services directly.
    # The async wrappers (_analyze_toolchain, _generate_recommendations)
    # just delegate to these synchronous methods, so we bypass them
    # to avoid needing an event loop. This method may be called from
    # a worker thread (via asyncio.to_thread) where no event loop
    # is available.

    # Analyze toolchain
    if self._toolchain_analyzer is None:
        raise RuntimeError("ToolchainAnalyzer not initialized")
    toolchain = self._toolchain_analyzer.analyze_toolchain(project_path)

    # Generate recommendations
    if self._agent_recommender is None:
        raise RuntimeError("AgentRecommender not initialized")
    constraints = {"min_confidence": min_confidence}
    recommendations = self._agent_recommender.recommend_agents(
        toolchain, constraints
    )
```

#### Analysis

| Aspect | Assessment |
|--------|-----------|
| **API Signature** | Unchanged -- `preview_configuration(project_path, min_confidence=0.5)` |
| **Return Type** | Unchanged -- `ConfigurationPreview` |
| **Behavioral Change** | Calls synchronous methods directly instead of through async wrappers |
| **Error Handling** | Improved -- adds explicit null checks with clear RuntimeError messages |
| **Backward Compatibility** | Full -- produces identical results; async wrappers were just delegating to these sync methods |
| **Regression Risk** | Negligible -- actually fixes a latent bug in the main branch |

#### Critical Questions

- **Does the CLI call `preview_configuration()`?** Yes, via `claude-mpm auto-config preview`. The refactor eliminates the `asyncio.get_event_loop()` call which can fail in certain threading contexts. This is a strict improvement.
- **Are the underlying sync methods stable?** Yes. `self._toolchain_analyzer.analyze_toolchain()` and `self._agent_recommender.recommend_agents()` are well-established synchronous methods. The async wrappers were thin shims.
- **What about the null checks?** The `RuntimeError("ToolchainAnalyzer not initialized")` and `RuntimeError("AgentRecommender not initialized")` are guards against calling preview before the manager is fully initialized. This is a defensive improvement -- the main branch would have raised an `AttributeError` on `None.analyze_toolchain()` anyway, just with a less clear error message.

---

### 3. `remote_agent_discovery_service.py` -- UI Enrichment Fields

**Path**: `src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py`
**Lines**: 866 (main) -> 888 (feature)
**Risk**: LOW

#### What Changed

The `_parse_markdown_agent()` method now extracts additional frontmatter fields for UI enrichment and includes them in the returned dictionary. All additions are purely additive -- no existing keys or values were modified.

#### Feature Branch Additions (within `_parse_markdown_agent()`)

New fields extracted from frontmatter and added to the returned dict:

```python
# In the metadata sub-dict:
"tags": tags,           # Phase 2: UI enrichment
"color": color,         # Phase 2: UI enrichment
"resource_tier": resource_tier,    # Phase 2: UI enrichment
"network_access": network_access,  # Phase 2: UI enrichment

# At root level (for filtering convenience):
"tags": tags,           # Phase 2: Also at root level for filtering
"color": color,         # Phase 2: Also at root level for UI
```

#### Comparison of Return Dict Keys

| Key | Main | Feature | Notes |
|-----|------|---------|-------|
| `agent_id` | Yes | Yes | Unchanged |
| `hierarchical_path` | Yes | Yes | Unchanged |
| `canonical_id` | Yes | Yes | Unchanged |
| `collection_id` | Yes | Yes | Unchanged |
| `source_path` | Yes | Yes | Unchanged |
| `metadata.name` | Yes | Yes | Unchanged |
| `metadata.description` | Yes | Yes | Unchanged |
| `metadata.version` | Yes | Yes | Unchanged |
| `metadata.author` | Yes | Yes | Unchanged |
| `metadata.category` | Yes | Yes | Unchanged |
| `metadata.hierarchical_path` | Yes | Yes | Unchanged |
| `metadata.collection_id` | Yes | Yes | Unchanged |
| `metadata.source_path` | Yes | Yes | Unchanged |
| `metadata.canonical_id` | Yes | Yes | Unchanged |
| `metadata.tags` | No | **Yes** | NEW -- additive |
| `metadata.color` | No | **Yes** | NEW -- additive |
| `metadata.resource_tier` | No | **Yes** | NEW -- additive |
| `metadata.network_access` | No | **Yes** | NEW -- additive |
| `model` | Yes | Yes | Unchanged |
| `source` | Yes | Yes | Unchanged |
| `source_file` | Yes | Yes | Unchanged |
| `path` | Yes | Yes | Unchanged |
| `file_path` | Yes | Yes | Unchanged |
| `version` | Yes | Yes | Unchanged |
| `category` | Yes | Yes | Unchanged |
| `tags` (root) | No | **Yes** | NEW -- additive |
| `color` (root) | No | **Yes** | NEW -- additive |
| `routing` | Yes | Yes | Unchanged |

#### Analysis

| Aspect | Assessment |
|--------|-----------|
| **API Signature** | Unchanged -- `_parse_markdown_agent(md_file)` (private method) |
| **Return Type** | Unchanged -- `Optional[Dict]` (with additional keys) |
| **Behavioral Change** | None -- existing return values identical; new keys added |
| **Error Handling** | Unchanged -- extraction uses `.get()` with safe defaults |
| **Backward Compatibility** | Full -- consumers using existing keys are unaffected |
| **Regression Risk** | Negligible -- purely additive to dict |

#### Critical Questions

- **Can additional dict keys break existing consumers?** No. Python dict access via `dict["key"]` or `dict.get("key")` is unaffected by the presence of additional keys. No existing consumer iterates over dict keys expecting a fixed set.
- **What if frontmatter lacks these new fields?** Safe defaults are used: `color="gray"`, `tags=[]`, `resource_tier=""`, `network_access=None`. These are extracted with `.get()` calls with explicit defaults.

---

### 4. `agent_management_service.py` -- Path Change + Enrichment (HIGHEST RISK)

**Path**: `src/claude_mpm/services/agents/management/agent_management_service.py`
**Lines**: 648 (main) -> 740 (feature)
**Risk**: **MEDIUM**

This file contains the **most significant behavioral change** in the entire feature branch.

#### Change 1: Default `project_dir` Path (BEHAVIORAL CHANGE)

##### Main Branch (line 68)

```python
if project_dir is None:
    project_root = get_path_manager().get_project_root()
    # Use direct agents directory without subdirectory to match deployment expectations
    self.project_dir = project_root / get_path_manager().CONFIG_DIR / "agents"
```

Where `get_path_manager().CONFIG_DIR` resolves to `CONFIG_DIR_NAME = ".claude-mpm"`, so the effective path is:
```
{project_root}/.claude-mpm/agents
```

##### Feature Branch (line 67-68)

```python
if project_dir is None:
    project_root = get_path_manager().get_project_root()
    # Deployed agents live in .claude/agents/ (Claude Code's native directory)
    self.project_dir = project_root / ".claude" / "agents"
```

Effective path:
```
{project_root}/.claude/agents
```

##### Impact Analysis

This changes where the `AgentManager` looks for project-level agents by default:

| Operation | Main Branch Path | Feature Branch Path | Risk |
|-----------|-----------------|--------------------|----|
| `list_agents(location="project")` | `.claude-mpm/agents/*.md` | `.claude/agents/*.md` | **Agents in `.claude-mpm/agents/` will no longer be found** |
| `create_agent(location="project")` | Creates in `.claude-mpm/agents/` | Creates in `.claude/agents/` | Different target directory |
| `read_agent()` (project search) | Searches `.claude-mpm/agents/` | Searches `.claude/agents/` | May miss agents in old location |
| `delete_agent()` | Deletes from `.claude-mpm/agents/` | Deletes from `.claude/agents/` | May fail to find agents |

**CRITICAL QUESTION**: Does the `claude-mpm` CLI rely on the default `project_dir`, or does it always pass an explicit `project_dir` argument?

If the CLI constructs `AgentManager()` without an explicit `project_dir`, and agents exist in `.claude-mpm/agents/`, they will **silently not be found** in the feature branch. The comment "Deployed agents live in .claude/agents/ (Claude Code's native directory)" suggests this aligns with where agents are actually deployed by the dashboard feature, but the CLI may still expect `.claude-mpm/agents/`.

**Mitigation**: The `__init__` signature still accepts `project_dir` as an optional parameter. Any caller that explicitly passes `project_dir` is unaffected. The risk is limited to callers that rely on the default.

#### Change 2: New `list_agent_names()` Method (ADDITIVE)

```python
def list_agent_names(self, location: Optional[str] = None) -> Set[str]:
    """Return set of agent names (filenames without .md) without parsing content.

    This is a lightweight alternative to list_agents() when only names are needed,
    e.g., for is_deployed cross-referencing. Avoids O(n * parse_time) when
    O(n * glob_time) suffices.
    """
    names: Set[str] = set()
    if location in (None, "framework"):
        if self.framework_dir.exists():
            names.update(
                f.stem
                for f in self.framework_dir.glob("*.md")
                if f.name != "base_agent.md"
            )
    if location in (None, "project"):
        if self.project_dir.exists():
            names.update(f.stem for f in self.project_dir.glob("*.md"))
    return names
```

This is a new method with no impact on existing functionality. It provides a lightweight alternative to `list_agents()` that only returns names without parsing content.

#### Change 3: `list_agents()` Refactored with `_build_agent_entry()` Helper

##### Main Branch (lines 265-306)

```python
def list_agents(self, location=None):
    agents = {}
    if location in [None, "framework"]:
        for agent_file in self.framework_dir.glob("*.md"):
            if agent_file.name != "base_agent.md":
                agent_name = agent_file.stem
                agent_def = self.read_agent(agent_name)
                if agent_def:
                    agents[agent_name] = {
                        "location": "framework",
                        "path": str(agent_file),
                        "version": agent_def.metadata.version,
                        "type": agent_def.metadata.type.value,
                        "specializations": agent_def.metadata.specializations,
                    }
    # ... similar for project agents ...
    return agents
```

##### Feature Branch (lines 291-340)

```python
def list_agents(self, location=None):
    agents = {}

    def _build_agent_entry(agent_file, agent_name, loc):
        agent_def = self.read_agent(agent_name)
        if not agent_def:
            return None
        enrichment = self._extract_enrichment_fields(agent_def.raw_content)
        return {
            "location": loc,
            "path": str(agent_file),
            "version": agent_def.metadata.version,
            "type": agent_def.metadata.type.value,
            "specializations": agent_def.metadata.specializations,
            **enrichment,  # NEW: adds description, category, color, tags, etc.
        }

    if location in [None, "framework"]:
        for agent_file in self.framework_dir.glob("*.md"):
            if agent_file.name != "base_agent.md":
                agent_name = agent_file.stem
                entry = _build_agent_entry(agent_file, agent_name, "framework")
                if entry:
                    agents[agent_name] = entry
    # ... similar for project agents ...
    return agents
```

The return dict now includes additional enrichment fields via `**enrichment`:

```python
# Enrichment fields added to each agent entry:
{
    "description": "",       # from frontmatter
    "category": "",          # from frontmatter
    "color": "gray",         # from frontmatter (default: gray)
    "tags": [],              # from frontmatter
    "resource_tier": "",     # from frontmatter
    "network_access": None,  # from capabilities.network_access
    "skills_count": 0,       # computed from skills field
}
```

#### Change 4: New `_extract_enrichment_fields()` Method (ADDITIVE)

```python
def _extract_enrichment_fields(self, raw_content: str) -> Dict[str, Any]:
    """Extract UI enrichment fields from agent raw content frontmatter."""
    defaults = {
        "description": "",
        "category": "",
        "color": "gray",
        "tags": [],
        "resource_tier": "",
        "network_access": None,
        "skills_count": 0,
    }
    try:
        post = frontmatter.loads(raw_content)
        fm = post.metadata
        # ... extraction logic with safe defaults ...
        return { ... }
    except Exception:
        logger.warning("Failed to parse frontmatter for enrichment, using defaults")
        return defaults
```

This method has robust error handling -- any parsing failure returns safe defaults.

#### Change 5: Import Addition

```python
# Main:
from typing import Any, Dict, List, Optional

# Feature:
from typing import Any, Dict, List, Optional, Set
```

`Set` is added for the new `list_agent_names()` return type. No existing imports removed.

#### Overall Analysis for `agent_management_service.py`

| Aspect | Assessment |
|--------|-----------|
| **API Signatures** | `list_agents()` unchanged; new `list_agent_names()` added |
| **Return Types** | `list_agents()` returns dict with additional keys (additive); `list_agent_names()` new |
| **Behavioral Change** | **YES** -- default `project_dir` changed from `.claude-mpm/agents` to `.claude/agents` |
| **Error Handling** | Improved -- `_extract_enrichment_fields()` has catch-all with defaults |
| **Backward Compatibility** | **PARTIAL** -- enrichment fields are backward-compatible; path change is NOT |
| **Regression Risk** | **MEDIUM** -- path change affects any caller relying on default `project_dir` |

#### Recommended Verification

1. **Search for all callers of `AgentManager()` that do NOT pass `project_dir`** -- these are affected.
2. **Verify where agents are actually deployed** -- if the deployment pipeline already puts agents in `.claude/agents/`, the path change is correct and the main branch was already broken.
3. **Check if `.claude-mpm/agents/` is still used anywhere** -- if it is, a migration strategy or dual-path lookup may be needed.

---

### 5. `server.py` -- Dashboard Route Additions + CORS + Config Infrastructure

**Path**: `src/claude_mpm/services/monitor/server.py`
**Lines**: 1662 (main) -> 1736 (feature)
**Risk**: LOW

#### What Changed

Four categories of changes, all additive:

##### 5a. New Instance Variables in `__init__` (lines 167-169)

```python
# Feature branch adds:
# Config event infrastructure (Phase 2)
self.config_event_handler = None
self.config_file_watcher = None
```

These are initialized to `None` alongside existing handler variables. No effect when dashboard mode is not used.

##### 5b. CORS Middleware in `_start_async_server()` (lines 312-328)

```python
# Feature branch adds CORS middleware:
@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        return web.Response(
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, If-None-Match",
            }
        )
    response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

# Main: self.app = web.Application()
# Feature: self.app = web.Application(middlewares=[cors_middleware])
```

##### 5c. Config Event Infrastructure in `_start_async_server()` (lines 347-356)

```python
# Feature branch adds:
from claude_mpm.services.monitor.handlers.config_handler import (
    ConfigEventHandler,
    ConfigFileWatcher,
)
self.config_event_handler = ConfigEventHandler(self.sio)
self.config_file_watcher = ConfigFileWatcher(self.config_event_handler)
self.config_file_watcher.start()
```

##### 5d. New Route Registrations in `_setup_http_routes()` (lines 1432-1467)

```python
# Phase 1: Read-only config routes
from claude_mpm.services.monitor.config_routes import register_config_routes
register_config_routes(self.app, server_instance=self)

# Phase 2: Mutation routes
from claude_mpm.services.monitor.routes.config_sources import register_source_routes
register_source_routes(self.app, self.config_event_handler, self.config_file_watcher)

# Phase 3: Deployment routes
from claude_mpm.services.config_api.agent_deployment_handler import register_agent_deployment_routes
from claude_mpm.services.config_api.autoconfig_handler import register_autoconfig_routes
from claude_mpm.services.config_api.skill_deployment_handler import register_skill_deployment_routes

register_agent_deployment_routes(self.app, self.config_event_handler, self.config_file_watcher)
register_skill_deployment_routes(self.app, self.config_event_handler, self.config_file_watcher)
register_autoconfig_routes(self.app, self.config_event_handler, self.config_file_watcher)
```

##### 5e. Graceful Shutdown Addition (lines 1721-1726)

```python
# Feature branch adds to _graceful_shutdown():
# Stop config file watcher
if self.config_file_watcher is not None:
    try:
        await self.config_file_watcher.stop()
    except Exception as e:
        self.logger.debug(f"Error stopping config file watcher: {e}")
```

#### Analysis

| Aspect | Assessment |
|--------|-----------|
| **API Signatures** | No public APIs changed |
| **Behavioral Change** | CORS headers added to all responses; config watcher thread started at server startup |
| **Error Handling** | Config watcher stop has its own try/except; route registration wrapped in existing try/except |
| **Backward Compatibility** | Full for CLI; CORS is transparent to existing dashboard consumers |
| **Regression Risk** | Low |

#### Critical Questions

- **Does the CLI use the monitor server?** The CLI starts the monitor server when running `claude-mpm monitor`. All existing routes and event handlers are preserved. The new routes are purely additive and use distinct URL paths (`/api/config/*`, `/api/sources/*`, `/api/deploy/*`).
- **Can CORS middleware break existing requests?** No. CORS headers are passthrough for non-OPTIONS requests -- they just add `Access-Control-Allow-Origin: *` to existing responses. For OPTIONS preflight requests, it returns a 200 with appropriate headers. This is standard CORS behavior and does not affect same-origin requests (which is what the CLI uses).
- **Can the config file watcher cause issues?** The watcher is initialized but only actively watches for config file changes. It runs in a background thread. If the config handler module fails to import, the exception would be caught by the outer try/except in `_start_async_server()`. The `None` check in shutdown prevents errors when the watcher was never started.

---

### 6. `skills_deployer.py` -- Optional `skills_dir` Parameter

**Path**: `src/claude_mpm/services/skills_deployer.py`
**Lines**: 1211 (main) -> 1242 (feature)
**Risk**: LOW

#### What Changed

Three methods gained a new optional `skills_dir: Optional[Path] = None` parameter, allowing callers to specify an alternative target directory for skill deployment. When `None` (the default), behavior is identical to the main branch.

##### 6a. `deploy_skills()` Signature Change

```python
# Main:
def deploy_skills(
    self,
    collection: Optional[str] = None,
    toolchain: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    force: bool = False,
    selective: bool = True,
    project_root: Optional[Path] = None,
    skill_names: Optional[List[str]] = None,
) -> Dict:

# Feature:
def deploy_skills(
    self,
    collection: Optional[str] = None,
    toolchain: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    force: bool = False,
    selective: bool = True,
    project_root: Optional[Path] = None,
    skill_names: Optional[List[str]] = None,
    skills_dir: Optional[Path] = None,   # NEW
) -> Dict:
```

Feature branch adds at the top of the method:
```python
# Use provided skills_dir or fall back to default
target_skills_dir = (
    skills_dir if skills_dir is not None else self.CLAUDE_SKILLS_DIR
)
```

And adds directory creation:
```python
target_skills_dir.mkdir(parents=True, exist_ok=True)
```

Throughout the method, `self.CLAUDE_SKILLS_DIR` references are replaced with `target_skills_dir`, including the `cleanup_orphan_skills()` call.

##### 6b. `check_deployed_skills()` Signature Change

```python
# Main:
def check_deployed_skills(self) -> Dict:
    deployed_skills = []
    if self.CLAUDE_SKILLS_DIR.exists():
        for skill_dir in self.CLAUDE_SKILLS_DIR.iterdir():
            # ...
    return {
        "claude_skills_dir": str(self.CLAUDE_SKILLS_DIR),
        # ...
    }

# Feature:
def check_deployed_skills(self, skills_dir: Optional[Path] = None) -> Dict:
    scan_dir = skills_dir if skills_dir is not None else self.CLAUDE_SKILLS_DIR
    deployed_skills = []
    if scan_dir.exists():
        for skill_dir in scan_dir.iterdir():
            # ...
    return {
        "claude_skills_dir": str(scan_dir),
        # ...
    }
```

##### 6c. Internal `_deploy_skill()` Also Gains `skills_dir` Parameter

The private `_deploy_skill()` method follows the same pattern -- adds `skills_dir: Optional[Path] = None` with the `target_skills_dir` fallback.

#### Analysis

| Aspect | Assessment |
|--------|-----------|
| **API Signatures** | New optional parameter `skills_dir=None` added to 3 methods |
| **Return Type** | Unchanged for all methods |
| **Behavioral Change** | None when called without `skills_dir` (defaults to `self.CLAUDE_SKILLS_DIR`) |
| **Error Handling** | Unchanged; `mkdir(parents=True, exist_ok=True)` added for custom dirs |
| **Backward Compatibility** | Full -- all existing callers pass no `skills_dir` argument |
| **Regression Risk** | Negligible |

#### Critical Questions

- **Does the CLI call `deploy_skills()` without `skills_dir`?** Yes. Every existing CLI call uses positional/keyword arguments that predate `skills_dir`. Since `skills_dir` defaults to `None`, and `None` triggers the fallback to `self.CLAUDE_SKILLS_DIR`, behavior is identical.
- **Could `target_skills_dir.mkdir()` cause issues?** No. `parents=True, exist_ok=True` is safe -- it creates the directory if missing and does nothing if it exists. For the default case, `self.CLAUDE_SKILLS_DIR` already exists (created in `__init__`).

---

## Risk Matrix

| Risk Level | Files | Count | Action Required |
|------------|-------|-------|----------------|
| **MEDIUM** | `agent_management_service.py` | 1 | Verify callers of `AgentManager()` without explicit `project_dir`; confirm `.claude/agents` is the correct deployment target |
| **LOW** | `agent_sources.py`, `auto_config_manager.py`, `remote_agent_discovery_service.py`, `server.py`, `skills_deployer.py` | 5 | No action required; changes are backward-compatible |

---

## Recommendations

### Priority 1: Verify `project_dir` Path Change (MEDIUM risk)

The change from `.claude-mpm/agents` to `.claude/agents` in `agent_management_service.py` is the single highest-risk item. To determine actual impact:

1. **Search for all callers** of `AgentManager()` or `AgentManager(project_dir=...)` across the codebase:
   - If all callers pass explicit `project_dir`, the default change has no effect.
   - If any caller relies on the default, verify where agents are actually stored on disk.

2. **Check if there is a migration path**: Do existing deployments have agents in `.claude-mpm/agents/`, `.claude/agents/`, or both?

3. **Consider a dual-lookup fallback**: If both paths might contain agents, the `__init__` could check `.claude/agents` first, then fall back to `.claude-mpm/agents`.

### Priority 2: No Action Required (LOW risk items)

The remaining 5 files are safe:

- `agent_sources.py`: Atomic write is strictly safer.
- `auto_config_manager.py`: Async-to-sync fix eliminates a latent bug.
- `remote_agent_discovery_service.py`: Additive dict keys with safe defaults.
- `server.py`: Additive routes, CORS, and config infrastructure.
- `skills_deployer.py`: Optional parameter with None default preserves existing behavior.

### Priority 3: Test Coverage

For comprehensive confidence, the following test scenarios should be verified:

1. **CLI smoke test**: Run `claude-mpm auto-config preview` on a project with agents deployed -- verify it produces the same output as the main branch.
2. **Agent listing**: Run `claude-mpm agents list` -- verify all agents are found (this exercises `AgentManager.list_agents()` and will reveal any `project_dir` issues).
3. **Skills deployment**: Run `claude-mpm skills deploy` -- verify skills deploy to `~/.claude/skills/` as expected.
4. **Monitor startup**: Run `claude-mpm monitor` -- verify the dashboard loads and existing Socket.IO events work.
5. **Config save**: Trigger a config save operation -- verify the atomic write produces a valid YAML file.

---

## Appendix: Import Changes Summary

| File | Imports Removed | Imports Added | Risk |
|------|----------------|---------------|------|
| `agent_sources.py` | None | None | None |
| `auto_config_manager.py` | `asyncio` (removed from `preview_configuration` body) | None at module level | Low |
| `remote_agent_discovery_service.py` | None | None | None |
| `agent_management_service.py` | None | `Set` (from typing) | None |
| `server.py` | None | `ConfigEventHandler`, `ConfigFileWatcher` (lazy), `register_config_routes`, `register_source_routes`, `register_agent_deployment_routes`, `register_skill_deployment_routes`, `register_autoconfig_routes` (all lazy imports inside methods) | None -- lazy imports only execute when server starts |
| `skills_deployer.py` | None | None | None |

All import changes are additive. No existing imports were removed.
