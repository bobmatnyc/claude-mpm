# Primary Breaking-Change Verification Analysis

**Date**: 2026-02-14
**Analyst**: Primary Researcher (Research Agent)
**Branch**: `ui-agents-skills-config`
**Scope**: Phases 1-3 plans for agents/skills dashboard UI enrichment

---

## Executive Summary

After thorough analysis of all 4 plan files, 6 research files, and deep-dive into the source code, I conclude that **the proposed changes across Phases 1-3 pose LOW risk of breaking regular (non-dashboard) claude-mpm operation**. The plans are predominantly additive in nature, targeting frontend-only changes (Phase 1), additive backend enrichment (Phase 2), and new frontend components (Phase 3). However, I identify **3 moderate-risk areas** and **5 low-risk areas** that require attention during implementation.

**Risk Summary**:
- **CRITICAL RISK**: 0 items
- **HIGH RISK**: 0 items
- **MODERATE RISK**: 3 items (Phase 2 Steps 1, 4, 5)
- **LOW RISK**: 5 items (Phase 2 Steps 2, 3, 6, 7, 8)
- **NO RISK**: All Phase 1 and Phase 3 changes

---

## 1. Architecture Overview: How claude-mpm Works Without the Dashboard

### 1.1 Core Operational Paths (Non-Dashboard)

The system operates through multiple independent paths:

1. **CLI Agent Management** (`cli/commands/agent_manager.py`):
   - Uses `AgentRegistry.list_agents()` (NOT `AgentManager.list_agents()`)
   - Returns list of `AgentMetadata` objects (different return type)
   - Path: CLI -> AgentListingService -> AgentRegistry -> filesystem

2. **Agent Deployment** (`services/agents/deployment/agent_lifecycle_manager.py`):
   - Uses `AgentRegistry.list_agents()` for discovery
   - Accesses `.name`, `.version` attributes on returned objects
   - Path: CLI -> AgentLifecycleManager -> AgentRegistry -> filesystem

3. **Agent Validation** (`services/cli/agent_validation_service.py`):
   - Uses `AgentRegistry.list_agents()` which returns dict or list
   - Handles both formats: `isinstance(agents, dict)` check exists
   - Path: CLI -> AgentValidationService -> AgentRegistry

4. **Skill Deployment** (`services/skills_deployer.py`, `services/skills/selective_skill_deployer.py`):
   - `SkillsDeployerService.deploy_skills()` - writes to `~/.claude/skills/`
   - `check_deployed_skills()` - scans directory for SKILL.md files
   - `load_deployment_index()` - reads `.mpm-deployed-skills.json`
   - Path: CLI -> SkillsDeployerService -> filesystem

5. **Version Service** (`services/version_service.py`):
   - Uses `AgentRegistry.list_agents()` (different from AgentManager)
   - Accesses `.name`, `.version` on returned agent objects

### 1.2 Dashboard-Specific Path (Isolated)

The dashboard operates through a completely separate path:

- **Dashboard API** (`services/monitor/config_routes.py`):
  - Uses `AgentManager.list_agents()` (DIFFERENT class from AgentRegistry)
  - Uses `GitSourceManager.list_cached_agents()` for available agents
  - Uses `SkillsDeployerService.check_deployed_skills()` for deployed skills
  - Uses `SkillsDeployerService.list_available_skills()` for available skills
  - Registered ONLY when dashboard server starts (lazy import in `_setup_http_routes`)

**Key Insight**: `AgentManager` (used by dashboard) and `AgentRegistry` (used by CLI) are **completely separate classes** with different `list_agents()` methods. Changes to `AgentManager.list_agents()` do NOT affect CLI operations.

### 1.3 Service Isolation Analysis

```
CLI Operations:
  AgentRegistry.list_agents() -> List[AgentMetadata]  # objects with .name, .version
  AgentLifecycleManager.list_agents() -> List[AgentLifecycleRecord]
  SkillsDeployerService.deploy_skills() -> Dict
  SkillsDeployerService.check_deployed_skills() -> Dict

Dashboard Operations (SEPARATE):
  AgentManager.list_agents() -> Dict[str, Dict[str, Any]]  # dict with "location", "path", etc.
  GitSourceManager.list_cached_agents() -> List[Dict[str, Any]]
  SkillsDeployerService.check_deployed_skills() -> Dict  (SHARED - same method)
  SkillsDeployerService.list_available_skills() -> Dict  (SHARED - same method)
```

The only shared service methods between dashboard and CLI are:
1. `SkillsDeployerService.check_deployed_skills()` - used by both dashboard and CLI
2. `SkillsDeployerService.list_available_skills()` - used by both dashboard and CLI
3. `load_deployment_index()` - used by dashboard's deployed skills handler

---

## 2. Phase-by-Phase Breaking Risk Analysis

### 2.1 Phase 1: Frontend-Only Quick Wins (11 Steps)

**Overall Risk: NONE**

Phase 1 exclusively modifies SvelteKit frontend files under `src/claude_mpm/dashboard-svelte/src/lib/`. These files are:
- TypeScript interfaces (`config.svelte.ts`)
- Svelte components (`.svelte` files)
- CSS/Tailwind styles

**Evidence**:
- No Python backend files are modified
- TypeScript interface changes only affect how the frontend interprets data already sent by the API
- The API already sends fields that the frontend currently ignores (12+ fields from available skills API, but only 5 in TypeScript interface)

| Step | Change | Files Modified | Breaking Risk |
|------|--------|---------------|---------------|
| 1 | Expand AvailableSkill TS interface 5->15 fields | `config.svelte.ts` | NONE - additive, optional fields |
| 2 | Add sort controls | `AgentsList.svelte`, `SkillsList.svelte` | NONE - UI only |
| 3 | Add toolchain grouping | `SkillsList.svelte` | NONE - UI only |
| 4 | Add category grouping | `AgentsList.svelte` | NONE - UI only |
| 5 | Display version badge | Skill components | NONE - UI only |
| 6 | Display tags | Skill components | NONE - UI only |
| 7 | Display token count | Skill components | NONE - UI only |
| 8 | Skill detail panel enrichment | Skill detail components | NONE - UI only |
| 9 | Agent list info density | Agent components | NONE - UI only |
| 10 | Consolidate Badge components | Badge components | NONE - UI only |
| 11 | Dark mode audit | Various components | NONE - UI only |

### 2.2 Phase 2: Backend API Enrichment (9 Steps)

**Overall Risk: LOW-MODERATE (3 moderate, 5 low, 1 no-risk)**

This is the only phase that modifies Python backend code. Careful analysis required.

#### Step 1: Enrich AgentManager.list_agents() with frontmatter fields
**Risk: MODERATE**

**Current implementation** (`agent_management_service.py:265-306`):
```python
def list_agents(self, location=None) -> Dict[str, Dict[str, Any]]:
    # Returns dict like:
    # {"agent-name": {"location": "project", "path": "...", "version": "...",
    #                  "type": "...", "specializations": [...]}}
```

**Proposed change**: Add additional fields (description, category, color, tags, model_preference) to the returned dict.

**Callers of AgentManager.list_agents()** (dashboard-specific path):

| Caller | File | Access Pattern | Impact |
|--------|------|---------------|--------|
| `handle_project_summary` | `config_routes.py:133` | `len(deployed_agents)` - count only | SAFE - additive fields ignored |
| `handle_agents_deployed` | `config_routes.py:197` | Spreads `**details` into list | SAFE - additive fields passed through |
| `handle_agents_available` | `config_routes.py:271` | `deployed.keys()` - name set only | SAFE - only uses keys |

**Why MODERATE not LOW**: The method `list_agents()` calls `self.read_agent()` for every agent file (line 282-283, 296-297). The proposed change would parse YAML frontmatter from `agent_def.raw_content` (which is already loaded in memory). However:
- **Performance concern**: `read_agent()` already parses the full file including frontmatter. The plan proposes accessing already-parsed `agent_def.metadata` fields (tags, model_preference) and extracting description from `agent_def.primary_role`. This is efficient since no additional I/O is needed.
- **Error handling concern**: If an agent file has malformed frontmatter that causes `frontmatter.loads()` to fail, `read_agent()` already handles this (returns None, logged as error). The current code safely skips such files (`if agent_def:` check on line 283/297). Adding new field extraction from the existing `agent_def` object won't change this behavior.
- **Backward compatibility**: All existing callers access KNOWN keys only. Adding new keys is backward-compatible.

**Verdict**: MODERATE risk due to the complexity of the change (adding 5+ new fields) but architecturally safe. No breaking risk to non-dashboard operations since `AgentManager` is NOT used by CLI.

#### Step 2: Add color/tags to available agents endpoint
**Risk: LOW**

**Current implementation** (`config_routes.py:245-298`):
The `handle_agents_available` handler calls `git_mgr.list_cached_agents()` which already returns extensive metadata from `RemoteAgentDiscoveryService._parse_markdown_agent()`. The returned dict already includes:
- `agent_id`, `name`, `description`, `version`, `category`, `source`, `routing`, etc.
- `metadata.name`, `metadata.description`, `metadata.version`, `metadata.category`, etc.

**Proposed change**: Frontend would consume additional fields already present in the API response.

**Why LOW**: The data is already being returned by the API. The change is to surface it in the frontend. No backend changes needed for this step (or minimal backend additions for new fields like `color` not currently in frontmatter).

**Non-dashboard impact**: `GitSourceManager.list_cached_agents()` is only called from dashboard API handlers. No CLI code uses this method.

#### Step 3: Enrich deployed skills with manifest data
**Risk: LOW**

**Current implementation** (`config_routes.py:307-367`):
The `handle_skills_deployed` handler already enriches skills with deployment index metadata (description, category, collection, deploy_date). The proposed change would add additional manifest fields.

**Proposed change**: Read `manifest.json` and/or `metadata.json` from each deployed skill directory for additional fields (author, version, toolchain, token_count, tags).

**Shared service concern**: `SkillsDeployerService.check_deployed_skills()` is shared between dashboard and CLI. However, the enrichment happens ONLY in the dashboard handler (`_list_deployed_skills` local function), not in the shared service method. The shared method returns basic `{name, path}` data only.

**Why LOW**: The enrichment code is in the dashboard handler, not in the shared service. CLI operations are unaffected.

#### Step 4: Agent detail endpoint (NEW)
**Risk: MODERATE**

**Proposed change**: Add new API endpoint `GET /api/config/agents/deployed/{name}` returning full agent detail.

**Implementation approach**: Would call `AgentManager.read_agent(name)` and return `agent_def.to_dict()`.

**Why MODERATE**:
1. New endpoint registration in `register_config_routes()` adds to the route table. This is safe (additive).
2. The endpoint would call `AgentManager.read_agent()` which reads a file from disk. This is the same operation already performed by `list_agents()`. No new I/O paths.
3. **Path traversal concern**: The `{name}` parameter must be validated to prevent directory traversal attacks. The existing `_find_agent_file()` method constructs paths as `project_dir / f"{name}.md"`. If `name` contains `../`, this could read files outside the agents directory. **However**, the existing codebase already has path traversal protection added (commit `45bc147c: fix: add path traversal protection to agent and skill deployment endpoints`). This should be verified for the new endpoint.

**Non-dashboard impact**: None. New endpoints are registered only in the dashboard server.

#### Step 5: Skill content preview endpoint (NEW)
**Risk: MODERATE**

**Proposed change**: Add new API endpoint `GET /api/config/skills/deployed/{name}/preview` returning truncated SKILL.md content.

**Why MODERATE**:
1. Similar path traversal concern as Step 4. Must validate `{name}` parameter.
2. Reads file content from disk - new I/O operation in dashboard API layer.
3. File size concern: SKILL.md files can be large. Plan specifies truncation to first N lines.

**Non-dashboard impact**: None. New endpoint is dashboard-only.

#### Step 6: Add agent_count to available skills endpoint
**Risk: LOW**

**Proposed change**: For each available skill, count how many deployed agents reference it.

**Implementation concern**: This requires cross-referencing skills with agents, potentially calling `AgentManager.list_agents()` or scanning agent files. The plan proposes doing this in the API handler.

**Why LOW**: The computation happens in the dashboard handler function. The only concern is performance (scanning agents for each skill could be O(n*m)), but this is bounded by the number of agents (~50-100) and skills (~150-200).

**Non-dashboard impact**: None.

#### Step 7: Frontend TypeScript interface updates (deployed agent)
**Risk: LOW**

**Current interface** (`config.svelte.ts:13-21`):
```typescript
export interface DeployedAgent {
  name: string;
  location: string;
  path: string;
  version: string;
  type: string;
  specializations?: string[];
  is_core: boolean;
}
```

**Proposed change**: Add optional fields (description, category, color, tags, model_preference).

**Why LOW**: Adding optional fields to TypeScript interfaces is fully backward-compatible. Existing components won't break if new fields are undefined.

#### Step 8: Frontend TypeScript interface updates (deployed skill)
**Risk: LOW**

Same analysis as Step 7. Adding optional fields to `DeployedSkill` interface.

#### Step 9: Frontend detail panel integration
**Risk: NO RISK**

Pure frontend component work consuming already-available API data.

### 2.3 Phase 3: Rich Detail Panels (7 Features)

**Overall Risk: NONE**

Phase 3 creates new Svelte components and integrates them with the existing frontend. All changes are:
- New `.svelte` component files (12 new components proposed)
- New TypeScript utility files
- Modifications to existing Svelte components to add progressive disclosure
- Feature flags for independent rollback

No backend modifications are proposed in Phase 3. All data comes from existing or Phase 2 enriched API endpoints.

| Feature | Change | Breaking Risk |
|---------|--------|---------------|
| 1 | Agent detail panel | NONE - new component |
| 2 | Skill detail panel | NONE - new component |
| 3 | Filter dropdowns | NONE - frontend state management |
| 4 | Version mismatch detection | NONE - frontend comparison logic |
| 5 | Agent collaboration links | NONE - new component |
| 6 | Merge skill links | NONE - component restructuring |
| 7 | Search enhancements | NONE - frontend text filtering |

---

## 3. Detailed Risk Evaluation by Dimension

### 3.1 Schema Changes

| Proposed Change | Schema Impact | Risk |
|----------------|--------------|------|
| Phase 1 Step 1: Expand AvailableSkill TS interface | Frontend-only type addition | NONE |
| Phase 2 Step 1: Enrich list_agents() return value | Additive dict keys in dashboard-only path | LOW |
| Phase 2 Step 3: Enrich deployed skills handler | Additive dict keys in dashboard-only handler | LOW |
| Phase 2 Step 7: DeployedAgent interface expansion | Frontend-only optional type fields | NONE |

**No breaking schema changes identified.**

### 3.2 New Required Fields

No proposed change introduces new REQUIRED fields. All additions are:
- Optional TypeScript fields (using `?:` syntax)
- Additional dict keys in Python (consumers use `.get()` or spread)
- New API response fields (additive to existing JSON)

**No breaking required field changes.**

### 3.3 Path Changes

| Proposed Change | Path Impact | Risk |
|----------------|-----------|------|
| Phase 2 Step 4: New `/api/config/agents/deployed/{name}` | New endpoint, no existing path modified | NONE |
| Phase 2 Step 5: New `/api/config/skills/deployed/{name}/preview` | New endpoint, no existing path modified | NONE |

**No existing paths are changed.** All modifications are additive (new routes only).

### 3.4 API Backward Compatibility

Existing API responses maintain full backward compatibility:

| Endpoint | Current Response Shape | After Changes | Compatible? |
|----------|----------------------|---------------|-------------|
| `GET /api/config/agents/deployed` | `{success, agents: [{name, location, path, version, type, specializations, is_core}], total}` | Same + additional optional fields per agent | YES |
| `GET /api/config/agents/available` | `{success, agents: [{agent_id, name, description, ...}], total, pagination}` | Same + possible additional fields | YES |
| `GET /api/config/skills/deployed` | `{success, skills: [{name, path, description, category, ...}], total}` | Same + additional optional fields per skill | YES |
| `GET /api/config/skills/available` | `{success, skills: [{name, description, category, collection, is_deployed}], total, pagination}` | Same + possible additional fields | YES |

**Full backward compatibility maintained.**

### 3.5 Import Side Effects

All Python imports in the dashboard path use **lazy loading**:

```python
# config_routes.py - ALL imports are lazy (inside function bodies)
def _get_agent_manager():
    global _agent_manager
    if _agent_manager is None:
        from claude_mpm.services.agents.management.agent_management_service import AgentManager
        _agent_manager = AgentManager(project_dir=agents_dir)
    return _agent_manager
```

**No import side effects.** The dashboard services are only instantiated when first accessed through API calls. CLI startup does NOT trigger dashboard imports.

### 3.6 Dependency Additions

**Phase 1**: No new Python dependencies. May add Svelte/TypeScript devDependencies (frontend-only).
**Phase 2**: No new Python dependencies proposed. Uses existing `frontmatter`, `yaml`, `mistune` libraries.
**Phase 3**: No new Python dependencies. Frontend-only changes.

**No new runtime dependencies.**

### 3.7 CLI Startup Impact

The dashboard server (`UnifiedMonitorServer`) is started via a separate CLI command (`mpm dashboard` or similar). It is NOT started during normal CLI operations like `mpm agents list` or `mpm skills deploy`.

**Key evidence** from `server.py:1432-1437`:
```python
# Config routes are registered ONLY inside _setup_http_routes()
# which is called ONLY when the dashboard server starts
from claude_mpm.services.monitor.config_routes import register_config_routes
register_config_routes(self.app, server_instance=self)
```

**No CLI startup impact.** Dashboard code is completely isolated from CLI startup path.

### 3.8 Configuration Changes

No proposed changes modify:
- `configuration.yaml` format or parsing
- `.claude-mpm/` directory structure
- `.claude/agents/` or `.claude/skills/` directory structure
- `.mpm-deployed-skills.json` schema
- Environment variables or system configuration

**No configuration changes.**

---

## 4. Cross-Cutting Concerns

### 4.1 Performance Impact on Shared Services

Two services are shared between dashboard and CLI:

1. **`SkillsDeployerService.check_deployed_skills()`**: Phase 2 Step 3 modifies the dashboard handler that CALLS this method, not the method itself. The shared method returns basic data; enrichment happens in the dashboard handler layer. **No performance impact on CLI.**

2. **`SkillsDeployerService.list_available_skills()`**: Phase 2 does not propose changes to this method. **No impact.**

### 4.2 Concurrent Access Safety

The dashboard runs in an async aiohttp server. All blocking calls are wrapped in `asyncio.to_thread()`. The plans don't change this pattern. Phase 2's new endpoints should follow the same `asyncio.to_thread()` pattern.

**No concurrency concerns if implementation follows existing patterns.**

### 4.3 Error Propagation

All dashboard API handlers follow a consistent error handling pattern:
```python
try:
    data = await asyncio.to_thread(_sync_function)
    return web.json_response({"success": True, "data": data})
except Exception as e:
    return web.json_response({"success": False, "error": str(e), "code": "SERVICE_ERROR"}, status=500)
```

Phase 2's new endpoints should follow this same pattern. If they do, errors in dashboard endpoints will NOT propagate to CLI operations.

### 4.4 Data Model Integrity

The `AgentDefinition` dataclass (`models/agent_definition.py`) is used by:
- `AgentManager` (dashboard path) - full read/write operations
- `AgentRegistry` (CLI path) - read-only, returns `AgentMetadata` not `AgentDefinition`

Phase 2 Step 1 accesses `AgentDefinition` fields that are ALREADY populated by `_parse_agent_markdown()`:
- `agent_def.metadata.tags` (line 355)
- `agent_def.metadata.model_preference` (line 351)
- `agent_def.metadata.specializations` (line 356)
- `agent_def.primary_role` (line 378)
- `agent_def.title` (line 370)

**No data model changes needed.** All accessed fields already exist in the dataclass.

---

## 5. Specific Recommendations

### 5.1 Implementation Safety Measures

1. **Phase 2 Step 1** (AgentManager.list_agents enrichment):
   - Use `.get()` access patterns for frontmatter fields to handle missing data
   - Add unit test verifying old callers still work with enriched response
   - Test with malformed agent files (missing frontmatter, empty content)

2. **Phase 2 Steps 4-5** (New endpoints):
   - Implement path traversal validation (verify existing protection from commit `45bc147c` applies)
   - Add input sanitization for `{name}` parameters
   - Follow existing `asyncio.to_thread()` pattern for blocking I/O
   - Add file size limits for skill content preview

3. **Phase 2 Step 6** (Agent count for skills):
   - Cache the agent-skill mapping to avoid O(n*m) computation on every request
   - Consider computing this once per request cycle, not per-skill

### 5.2 Testing Strategy

| Risk Area | Test Type | Priority |
|-----------|----------|----------|
| list_agents() enrichment | Unit test: verify old keys preserved | HIGH |
| list_agents() enrichment | Unit test: verify new keys present | HIGH |
| New endpoints path traversal | Security test: `../` injection | HIGH |
| New endpoints | Integration test: 404 for nonexistent agents/skills | MEDIUM |
| Frontend TS interfaces | TypeScript compile check (existing build) | LOW |
| Performance | Benchmark: list_agents() with enrichment vs without | LOW |

### 5.3 Rollback Strategy

- **Phase 1**: Pure frontend changes. Rollback by reverting Svelte/TS files. No data migration needed.
- **Phase 2**: Backend changes are additive. Rollback by reverting Python files. No schema migration needed since no database changes.
- **Phase 3**: Pure frontend changes with feature flags. Disable features via flags or revert components.

---

## 6. Conclusion

### 6.1 Overall Assessment

The proposed plans are well-designed with strong separation between dashboard and core claude-mpm operations. The architectural decision to use lazy-loaded singleton services for dashboard API routes, combined with the complete separation of `AgentManager` (dashboard) from `AgentRegistry` (CLI), provides excellent isolation.

### 6.2 Breaking Change Probability

| Category | Probability | Confidence |
|----------|------------|------------|
| Phase 1 breaks CLI | 0% | Very High |
| Phase 2 breaks CLI | <2% | High |
| Phase 3 breaks CLI | 0% | Very High |
| Phase 2 breaks dashboard | <5% | High |
| Any phase breaks agent deployment | <1% | Very High |
| Any phase breaks skill deployment | <1% | Very High |

### 6.3 Critical Path Dependencies

The plans correctly identify that Phase 2 must be completed before Phase 3 (detail panels need enriched API data). Phase 1 can proceed independently.

### 6.4 Final Verdict

**SAFE TO PROCEED** with the following conditions:
1. Phase 2 Steps 4-5 must include path traversal protection
2. Phase 2 Step 1 must use defensive `.get()` access patterns
3. All new endpoints must follow the existing `asyncio.to_thread()` + try/except pattern
4. Unit tests for `list_agents()` backward compatibility are recommended before deployment

---

## Appendix A: Source Files Examined

### Python Backend
- `src/claude_mpm/services/agents/management/agent_management_service.py` (648 lines) - AgentManager with list_agents()
- `src/claude_mpm/services/monitor/config_routes.py` (642 lines) - All dashboard API handlers
- `src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py` (866 lines) - Available agent parsing
- `src/claude_mpm/services/agents/git_source_manager.py` (partial) - list_cached_agents()
- `src/claude_mpm/services/skills_deployer.py` (partial) - check_deployed_skills(), deploy_skills()
- `src/claude_mpm/services/skills/selective_skill_deployer.py` (partial) - load_deployment_index()
- `src/claude_mpm/models/agent_definition.py` (214 lines) - AgentDefinition, AgentMetadata dataclasses
- `src/claude_mpm/services/monitor/server.py` (partial) - UnifiedMonitorServer._setup_http_routes()

### Frontend (TypeScript/Svelte)
- `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts` - All TypeScript interfaces

### list_agents() Caller Analysis (9 callers across codebase)
- `config_routes.py:133` (dashboard) - `len(deployed_agents)` - count only
- `config_routes.py:197` (dashboard) - `**details` spread into list
- `config_routes.py:271` (dashboard) - `deployed.keys()` - name set only
- `version_service.py:291` - Uses `AgentRegistry.list_agents()` (different class)
- `deployed_agent_discovery.py:54` - Uses `AgentRegistry.list_agents()` (different class)
- `agent_lifecycle_manager.py:287` - Uses `AgentRegistry.list_agents()` (different class)
- `agent_listing_service.py:283` - Uses `AgentRegistry.list_agents()` (different class)
- `agent_validation_service.py:96,138` - Uses `AgentRegistry.list_agents()` (different class)
- `debug.py:1036` - Performance benchmarking only

### Plan Files Analyzed
- `phase-1-frontend-quick-wins.md` (1130 lines, 11 steps)
- `phase-2-backend-api-enrichment.md` (1361 lines, 9 steps)
- `phase-3-rich-detail-panels.md` (1274 lines, 7 features)
- `devils-advocate-plan-review.md` (337 lines, 8 concerns)

### Research Files Analyzed
- `agents-skills-descriptions-info.md` (14 lines)
- `dashboard-ui-research.md` (653 lines)
- `agent-definitions-research.md` (808 lines)
- `skill-definitions-research.md` (599 lines)
- `devils-advocate-review.md` (563 lines)
- `SYNTHESIS-recommendations.md` (780 lines)

## Appendix B: Key Architecture Diagram

```
CLI Operations (UNAFFECTED by proposed changes)
================================================
mpm agents list  -->  AgentRegistry.list_agents()  -->  filesystem (.claude/agents/)
mpm skills deploy -->  SkillsDeployerService  -->  filesystem (.claude/skills/)
mpm skills list  -->  SkillsDeployerService  -->  filesystem (.claude/skills/)

Dashboard Operations (TARGET of proposed changes)
=================================================
GET /api/config/agents/deployed  -->  AgentManager.list_agents()  -->  filesystem (.claude/agents/)
GET /api/config/agents/available -->  GitSourceManager.list_cached_agents()  -->  cache (~/.claude-mpm/cache/agents/)
GET /api/config/skills/deployed  -->  SkillsDeployerService.check_deployed_skills()  -->  filesystem (.claude/skills/)
GET /api/config/skills/available -->  SkillsDeployerService.list_available_skills()  -->  skills repo cache

Key Isolation:
  AgentManager (dashboard)  !=  AgentRegistry (CLI)
  These are COMPLETELY SEPARATE classes with SEPARATE list_agents() methods
  Changes to AgentManager DO NOT affect AgentRegistry
```
