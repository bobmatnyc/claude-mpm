# Phase 2: Backend API Enrichment + Frontend Integration

## Revision History
- **v1 (2026-02-14)**: Initial draft
- **v2 (2026-02-14)**: Revised based on devil's advocate review. Key changes: (1) Fixed Step 1 — use `agent_def.raw_content` frontmatter re-parse with clear justification instead of claiming `agent_def.metadata` has fields it doesn't (R4); (2) Fixed deployment index naming to `.mpm-deployed-skills.json` throughout (R2); (3) Added caller audit for `list_agents()` changes (R3); (4) Added error handling spec for missing/malformed metadata (R8); (5) Clarified no agent deployment index is needed — agents use filesystem presence check instead (R1); (6) Added default color spec for agents missing `color` field (R10).
- **v3 (2026-02-14)**: Amended with Verification Pass 1 findings. Key changes: (1) **HIGH**: Added mandatory `validate_safe_name()` path traversal protection to Steps 4 and 5 (VP-1-SEC); (2) Added Step 0 — lightweight `list_agent_names()` to fix `handle_agents_available` performance cascade (VP-1-PERF); (3) Amended Step 1 with alternative approaches to avoid double frontmatter parsing (VP-1-PERF); (4) Added concurrent access handling requirement (VP-1-CONC); (5) Added integration testing requirement with real service instances (VP-1-TEST); (6) Added deployment ordering — Phase 2 MUST complete before Phase 3 (VP-1-DEPLOY).

**Date**: 2026-02-14
**Status**: Implementation-Ready
**Phase**: 2 of 3
**Depends on**: Phase 1 (Frontend-only quick wins)
**Estimated Effort**: Medium-Large (1-2 sprint cycles)

---

## Verification Amendments (Cross-Cutting)

> The following amendments were added after Verification Pass 1 (VP-1) identified HIGH and MODERATE severity issues across the Phase 1-3 plan set. See `docs/research/.../verification-pass-1/` for the full analysis.

### VP-1-DEPLOY: Deployment Ordering

Phase 2 **MUST** complete deployment before Phase 3 begins. Phase 3 detail panels call `GET /api/config/agents/{name}/detail` and `GET /api/config/skills/{name}/detail` which are created in Phase 2 Steps 4 and 5. Deploying Phase 3 without Phase 2 would produce 404 errors for all detail views.

Phase 2 backend changes should be deployed before Phase 2 frontend changes (Steps 7-9). The frontend uses optional (`?:`) types for all new fields, so it gracefully degrades if deployed ahead of the backend, but the intended user experience requires the backend enrichment to be live first.

### VP-1-SEC: Path Traversal Validation (Applies to Steps 4 and 5)

> **HIGH SEVERITY**: The existing `validate_safe_name()` function from `services/config_api/validation.py` is NOT imported by `config_routes.py`. The commit `45bc147c` that added path traversal protection only covers `agent_deployment_handler.py` and `skill_deployment_handler.py`. The new detail endpoints in Steps 4 and 5 construct filesystem paths from user-supplied `{name}` parameters and MUST apply the same validation.

All new endpoints that accept a `{name}` path parameter and use it to construct filesystem paths **MUST** import and call `validate_safe_name()` before any file-system operation. See Steps 4 and 5 for the specific code amendment.

### VP-1-PERF: Lightweight Agent Name Listing (New Pre-Requisite)

> **MODERATE SEVERITY**: `handle_agents_available()` at `config_routes.py:270-272` calls `list_agents(location="project")` which reads and frontmatter-parses ALL 49 agent files just to produce a set of agent names for the `is_deployed` cross-reference. Phase 2 enrichment of `list_agents()` makes this worse by adding more data extraction per agent.

Before implementing Step 1, create a lightweight `list_agent_names()` method on `AgentManager` that globs `*.md` filenames without parsing file contents. Update `handle_agents_available()` to use this method instead of `list_agents()` for the `is_deployed` cross-reference. See the new "Step 0" below.

### VP-1-CONC: Concurrent CLI/Dashboard File Access

> **MODERATE SEVERITY**: Dashboard READ operations in `config_routes.py` do not use any file locking. The CLI can simultaneously deploy/update agents, writing to the same `.claude/agents/` directory. `read_agent()` could encounter half-written files; the current `try/except` silently skips them, causing missing agents in the list view.

All Phase 2 implementation should:
1. Accept "eventual consistency" as the operating model for dashboard reads during CLI deployments.
2. Add a brief note in API error responses when agent/skill reads fail, rather than silently dropping items.
3. Recommend atomic writes (write to temp file, then `os.rename()`) in any future CLI deploy refactoring. This is NOT a Phase 2 blocker, but should be documented as a known limitation.
4. Consider adding `Cache-Control: private, max-age=5` headers to list endpoints so rapid refreshes during deployments do not repeatedly hit partially-written files.

### VP-1-TEST: Integration Testing Requirement

> **MODERATE SEVERITY**: `tests/test_config_routes.py` uses `unittest.mock.MagicMock` for ALL services. Tests cannot catch type mismatches, enrichment errors, or data flow bugs between the actual `AgentManager`/`SkillsDeployerService` and the API response format.

Every step in Phase 2 must include:
1. **Unit tests** (existing pattern): Mocked services for fast CI feedback.
2. **Integration tests** (NEW requirement): At least one test per step that instantiates a real `AgentManager` (or `SkillsDeployerService`) with fixture agent/skill files in a temp directory, calls the actual enrichment code, and verifies the API response contains the expected fields with correct types and values. This catches data flow bugs that mocked tests cannot.

Test fixture files should include:
- An agent with full frontmatter (all fields populated)
- An agent with minimal frontmatter (missing `color`, `resource_tier`, `network_access`)
- An agent with malformed frontmatter (invalid YAML)
- A deployed skill with matching manifest entry
- A deployed skill with no manifest match (custom/local skill)

---

## Prerequisites and Assumptions

### Must Be Complete Before Phase 2

1. **Phase 1 deployed** - Frontend TypeScript interfaces updated, existing API data surfaced
2. **Svelte build pipeline** working (already confirmed in `dashboard-svelte/`)
3. **Backend aiohttp server** running (`services/monitor/config_routes.py`)
4. **Agent and skill deployment** working (`.claude/agents/`, `.claude/skills/`)

### Key Assumptions

- Python backend uses **aiohttp** (not Flask/FastAPI despite CLAUDE.md)
- Agent definitions are Markdown with YAML frontmatter (confirmed)
- Skills deployment index exists at **`.mpm-deployed-skills.json`** (confirmed at `selective_skill_deployer.py:51`)
- No agent deployment index exists (agents are raw `.md` files — deployment status is determined by filesystem presence check)
- `AgentManager.read_agent()` already parses full frontmatter but `list_agents()` only returns 5 fields
- `AgentMetadata` dataclass has: `type`, `model_preference`, `version`, `last_updated`, `author`, `tags`, `specializations`, `collection_id`, `source_path`, `canonical_id`
- `AgentMetadata` does **NOT** have: `description`, `category`, `color`, `resource_tier`, `network_access`, `skills` — these are in the YAML frontmatter but not stored in the dataclass
- `RemoteAgentDiscoveryService._parse_markdown_agent()` already parses frontmatter for available agents but does not extract `color`, `skills`, `tags`, `resource_tier`, or `network_access`

### Caller Audit for `list_agents()`

> **[REVISED]** Added caller audit per R3 to assess backward compatibility impact.

The following callers consume `list_agents()` return values. All changes to the return dict are **additive** (new fields alongside existing ones), so no existing callers will break:

| Caller | File | Fields Used | Impact |
|--------|------|-------------|--------|
| `handle_agents_deployed()` | `config_routes.py:197` | Spreads all fields into response | **Safe** — new fields pass through to API response |
| `agent_listing_service` | `agent_listing_service.py:283` | `location`, `version`, `type` | **Safe** — doesn't destructure; ignores unknown fields |
| `agent_validation_service` | `agent_validation_service.py:138,273,486` | `keys()`, `location`, `version`, `type` | **Safe** — reads specific fields only |
| `agent_lifecycle_manager` | `agent_lifecycle_manager.py:287` | `keys()`, iteration | **Safe** — iterates agent names |
| `framework_loader` | `framework_loader.py:526` | Presence check | **Safe** — checks if agents exist |
| `deployed_agent_discovery` | `deployed_agent_discovery.py:54` | Full dict | **Safe** — new fields are additive |
| `agent_loader` | `agent_loader.py:210,335,371,426` | Various | **Safe** — passes through or reads known fields |
| `version_service` | `version_service.py:291` | Iteration | **Safe** — iterates entries |
| `debug.py` | `debug.py:1036` | Smoke test | **Safe** — just verifies no crash |

**Conclusion**: Adding new fields to `list_agents()` return values is fully backward compatible. No caller destructures with exact field expectations.

### Current Data Pipeline

```
Deployed Agents:
  .claude/agents/*.md → AgentManager.list_agents() → config_routes.handle_agents_deployed()
  Returns: {name, location, path, version, type, specializations} + enriched {is_core}

Available Agents:
  ~/.claude-mpm/cache/agents/ → RemoteAgentDiscoveryService → GitSourceManager → config_routes
  Returns: {agent_id, metadata:{name, description, version, category}, source, priority, ...}
  Handler promotes metadata.name + metadata.description to root, adds is_deployed

Deployed Skills:
  .claude/skills/ → SkillsDeployerService.check_deployed_skills() + load_deployment_index()
  Deployment index file: .mpm-deployed-skills.json (NOT .deployment_index.json)
  Returns: {name, path, description, category, collection, is_user_requested, deploy_mode, deploy_date}

Available Skills:
  GitHub manifest.json → SkillsDeployerService.list_available_skills()
  Returns: {name, version, category, toolchain, framework, tags, entry_point_tokens, full_tokens, ...}
```

---

## Step 0: Create Lightweight `list_agent_names()` Method

> **Verification Amendment (VP-1-PERF)**: This step was added to address the performance cascade in `handle_agents_available()`, which currently reads and parses ALL 49 agent files just to produce a set of deployed agent names for the `is_deployed` cross-reference.

### What
Add a lightweight `list_agent_names()` method to `AgentManager` that returns a `Set[str]` of deployed agent filenames WITHOUT reading or parsing file contents.

### Where
- **Primary file**: `src/claude_mpm/services/agents/management/agent_management_service.py`
- **Consumer**: `src/claude_mpm/services/monitor/config_routes.py` — `handle_agents_available()` (lines 270-272)

### How

1. Add method to `AgentManager`:

```python
def list_agent_names(self, location: str = "project") -> Set[str]:
    """Return set of agent names (filenames without .md) without parsing content.

    This is a lightweight alternative to list_agents() when only names are needed,
    e.g., for is_deployed cross-referencing. Avoids O(n * parse_time) when O(n * glob_time) suffices.
    """
    names = set()
    if location in ("project", None):
        project_agents = self.project_dir.glob("*.md")
        names.update(f.stem for f in project_agents)
    if location in ("framework", None):
        for fw_dir in self.framework_dirs:
            if fw_dir.exists():
                names.update(f.stem for f in fw_dir.glob("*.md"))
    return names
```

2. Update `handle_agents_available()` in `config_routes.py`:

```python
# BEFORE (reads and parses ALL agent files):
# deployed = agent_mgr.list_agents(location="project")
# deployed_names = set(deployed.keys())

# AFTER (globs filenames only — microseconds instead of milliseconds):
deployed_names = agent_mgr.list_agent_names(location="project")
```

### Why
- `list_agents(location="project")` reads and parses ALL 49 agent files (~1ms per file = ~50ms) just to get `deployed.keys()` — a set of filenames.
- `list_agent_names()` achieves the same result with a single `glob()` call (~0.1ms total).
- Phase 2 Step 1 makes `list_agents()` heavier (more field extraction), amplifying this waste.
- Both `GET /api/config/agents/deployed` AND `GET /api/config/agents/available` call `list_agents()`, so the performance improvement benefits both endpoints.

### Acceptance Criteria
- [ ] `list_agent_names()` returns the same set of names as `set(list_agents().keys())`
- [ ] `handle_agents_available()` uses `list_agent_names()` instead of `list_agents()`
- [ ] No functional regression in the `is_deployed` cross-reference
- [ ] Response time improvement measurable (expected: ~50ms reduction on available agents endpoint)

### Dependencies
- None (self-contained, should be implemented BEFORE Step 1)

### Estimated Complexity
**Small** — One new method (5 lines) + one consumer update (2 lines)

---

## Step 1: Enrich `AgentManager.list_agents()` to Return Frontmatter Fields

### What
Extend `AgentManager.list_agents()` to return `description`, `category`, `color`, `tags`, `resource_tier`, `network_access`, and `skills_count` alongside existing fields.

> **[REVISED v2]** Previously proposed accessing `agent_def.metadata.color`, `agent_def.metadata.category`, etc. However, the `AgentMetadata` dataclass does NOT have these fields. The `AgentMetadata` dataclass only has: `type`, `model_preference`, `version`, `last_updated`, `author`, `tags`, `specializations`, `collection_id`, `source_path`, `canonical_id`. Fields like `description`, `category`, `color`, `resource_tier`, `network_access` exist in the YAML frontmatter but are never stored in `AgentMetadata`.
>
> The revised approach: Parse frontmatter from `agent_def.raw_content` (which is an in-memory string — no additional I/O). While this is technically a "re-parse" of data that `_parse_agent_markdown()` already parsed, it's the correct approach because modifying the `AgentMetadata` dataclass would be invasive and affect many consumers. The frontmatter parse of an in-memory string is < 1ms per agent.
>
> **Verification Amendment (VP-1 — Double Frontmatter Parsing)**: The devil's advocate review identified that `list_agents()` already calls `read_agent()` which calls `_parse_agent_markdown()` which calls `frontmatter.loads()` for EVERY agent file. Adding a second `fm_lib.loads(agent_def.raw_content)` call doubles the parsing work (49 agents = 98 frontmatter parses per `list_agents()` call).
>
> **Recommended approach (choose one)**:
>
> **(a) Preferred — Reuse already-parsed fields + `frontmatter_extras` dict**: Modify `_parse_agent_markdown()` to store not-yet-captured frontmatter fields in a `frontmatter_extras` dict on `AgentDefinition`. This avoids both a second parse AND invasive changes to `AgentMetadata`. In `list_agents()`, access fields from `agent_def.metadata` (for `tags`, `author`, `version`) and `agent_def.frontmatter_extras` (for `description`, `category`, `color`, `resource_tier`, `network_access`). This is a single-parse solution.
>
> **(b) Acceptable — Re-parse `raw_content` (current plan)**: If the `frontmatter_extras` approach is too invasive for this phase, the re-parse approach from `agent_def.raw_content` is acceptable. The cost is ~1ms per agent in-memory (no file I/O), and 98 total parses for 49 agents is still under 50ms. Document this as technical debt to address in a future refactor.
>
> **(c) Alternative — Use `get_agent_api()` for detail endpoints**: Note that `AgentManager.get_agent_api()` (lines 308-322 in `agent_management_service.py`) already exists and returns `agent_def.to_dict()`, which includes ALL parsed data. Consider using this for the detail endpoint (Step 4) instead of building new enrichment code. However, `get_agent_api()` returns the full agent definition and may need field selection to match the detail API contract.
>
> **Decision**: Implementer should choose (a) or (b) based on complexity assessment. If (b) is chosen, do NOT use the import alias `fm_lib` — use the existing `import frontmatter` convention already established in the file.

### Where
- **Primary file**: `src/claude_mpm/services/agents/management/agent_management_service.py`
  - Method: `list_agents()` (lines 265-306)

### How

In `list_agents()`, after calling `self.read_agent(agent_name)`, parse the frontmatter from `agent_def.raw_content` to extract enrichment fields:

```python
import frontmatter as fm_lib

def list_agents(self, location=None):
    agents = {}
    # ... existing glob logic ...
    for agent_file in ...:
        agent_name = agent_file.stem
        agent_def = self.read_agent(agent_name)
        if agent_def:
            # Extract enrichment fields from frontmatter
            # raw_content is already in memory (no additional I/O)
            enrichment = {}
            try:
                post = fm_lib.loads(agent_def.raw_content)
                fm = post.metadata
                capabilities = fm.get("capabilities", {})
                if not isinstance(capabilities, dict):
                    capabilities = {}

                skills_field = fm.get("skills", [])
                if isinstance(skills_field, dict):
                    skills_count = len(skills_field.get("required", [])) + len(skills_field.get("optional", []))
                elif isinstance(skills_field, list):
                    skills_count = len(skills_field)
                else:
                    skills_count = 0

                enrichment = {
                    "description": fm.get("description", ""),
                    "category": fm.get("category", ""),
                    "color": fm.get("color", "gray"),  # Default gray for 3 agents missing color
                    "tags": fm.get("tags", []),
                    "resource_tier": fm.get("resource_tier", ""),
                    "network_access": capabilities.get("network_access"),
                    "skills_count": skills_count,
                }
            except Exception:
                # Malformed frontmatter — use defaults
                enrichment = {
                    "description": "",
                    "category": "",
                    "color": "gray",
                    "tags": [],
                    "resource_tier": "",
                    "network_access": None,
                    "skills_count": 0,
                }

            agents[agent_name] = {
                "location": "project",  # or "framework"
                "path": str(agent_file),
                "version": agent_def.metadata.version,
                "type": agent_def.metadata.type.value,
                "specializations": agent_def.metadata.specializations,
                **enrichment,
            }
    return agents
```

### Why
- `list_agents()` already calls `read_agent()` which reads the file into `raw_content`
- The frontmatter parse is an in-memory operation (< 1ms per agent) — no additional file I/O
- No changes to `AgentMetadata` dataclass (which has many consumers)
- Backward compatible — adds new fields alongside existing ones (see caller audit above)

### Error Handling

> **[REVISED]** Added explicit error handling spec per R8.

| Error Condition | Handling | Default Value |
|----------------|---------|---------------|
| Malformed YAML frontmatter | `try/except` catches parse error | All fields get defaults |
| Missing `description` key | `fm.get("description", "")` | `""` |
| Missing `category` key | `fm.get("category", "")` | `""` |
| Missing `color` key (3 agents: code-analyzer, local-ops, nestjs-engineer) | `fm.get("color", "gray")` | `"gray"` |
| Missing `tags` key | `fm.get("tags", [])` | `[]` |
| Missing `capabilities` block | `fm.get("capabilities", {})` | `{}` → `network_access: None` |
| `capabilities` is not a dict | `isinstance` check | `network_access: None` |
| `skills` is neither list nor dict | `isinstance` check | `skills_count: 0` |
| Agent file without frontmatter | `frontmatter.loads()` returns empty metadata | All fields get defaults |

### Edge Cases
- Agent file without YAML frontmatter: `frontmatter.loads()` returns empty metadata → all new fields get defaults
- Agent without `color` field (3 agents: `code-analyzer`, `local-ops-agent`, `nestjs-engineer`): returns `"gray"`, frontend renders gray dot
- Agent without `capabilities` block: `capabilities.get("network_access")` returns `None`
- Agent with dict-format `skills:` (new format): handled by isinstance check
- Agent with list-format `skills:` (legacy format): handled by isinstance check

### Acceptance Criteria
- [ ] `GET /api/config/agents/deployed` returns `description`, `category`, `color`, `tags`, `resource_tier`, `network_access`, `skills_count` for each agent
- [ ] All existing fields unchanged (backward compatible)
- [ ] `color` defaults to `"gray"` for agents without a `color` field
- [ ] Python tests: verify enriched response for an agent with full frontmatter
- [ ] Python tests: verify graceful defaults for agent without optional fields
- [ ] No performance regression (frontmatter parse is in-memory, < 1ms per agent)

### Dependencies
- None (self-contained change)

### Estimated Complexity
**Small** — Modifying an existing method to extract data from content it already loads

### API Contract

**Before** (current):
```json
{
  "name": "engineer",
  "location": "project",
  "path": "/path/.claude/agents/engineer.md",
  "version": "2.5.0",
  "type": "core",
  "specializations": [],
  "is_core": true
}
```

**After** (enriched):
```json
{
  "name": "engineer",
  "location": "project",
  "path": "/path/.claude/agents/engineer.md",
  "version": "2.5.0",
  "type": "core",
  "specializations": [],
  "is_core": true,
  "description": "Base engineer agent for general-purpose development",
  "category": "engineering",
  "color": "green",
  "tags": ["engineering", "general-purpose"],
  "resource_tier": "standard",
  "network_access": true,
  "skills_count": 18
}
```

---

## Step 2: Add `color` and `tags` to Available Agents Endpoint

### What
The `RemoteAgentDiscoveryService._parse_markdown_agent()` already parses YAML frontmatter but does NOT extract `color`, `tags`, `resource_tier`, or `network_access`. Add these fields to the discovery output.

### Where
- **Primary file**: `src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py`
  - Method: `_parse_markdown_agent()` (lines 551-713)

### How

In `_parse_markdown_agent()`, after the existing frontmatter extraction block (line 598-698), add extraction for the new fields:

```python
# After existing frontmatter extractions (line ~668):
# NEW: Extract additional frontmatter fields for UI enrichment
color = ""
tags = []
resource_tier = ""
network_access = None

if frontmatter:
    color = frontmatter.get("color", "")
    tags = frontmatter.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    resource_tier = frontmatter.get("resource_tier", "")
    capabilities = frontmatter.get("capabilities", {})
    if isinstance(capabilities, dict):
        network_access = capabilities.get("network_access")

# Then in the return dict (line ~686):
return {
    "agent_id": agent_id,
    # ... existing fields ...
    "metadata": {
        "name": name,
        "description": description,
        "version": version,
        "author": "remote",
        "category": category,
        "tags": tags,               # NEW
        "color": color,             # NEW
        "resource_tier": resource_tier,  # NEW
        "network_access": network_access,  # NEW
        # ... existing metadata fields ...
    },
    # ... rest of existing fields ...
    "tags": tags,                    # Also at root level
    "color": color,                  # Also at root level
}
```

### Why
- The frontmatter is already being parsed (line 598); we just need to extract more fields
- No additional file I/O
- Enables the frontend to show color dots and tags for available agents without a separate API call
- Research showed `color` is the #1 missing field for visual differentiation

### Error Handling

| Error Condition | Handling | Default Value |
|----------------|---------|---------------|
| No frontmatter parsed (regex fallback path) | Fields get defaults | `color=""`, `tags=[]`, etc. |
| `tags` is not a list | `isinstance` check | `[]` |
| `capabilities` is not a dict | `isinstance` check | `network_access: None` |
| Agent missing `color` | `frontmatter.get("color", "")` | `""` → frontend defaults to gray |

### Edge Cases
- Agent without `color`: returns `""`, frontend defaults to gray
- Agent without `tags`: returns `[]`, frontend hides tag section
- Agent with malformed frontmatter (fallback regex parsing): new fields won't be extracted → get defaults
- Non-list `tags` value: explicit isinstance check falls back to `[]`

### Acceptance Criteria
- [ ] `GET /api/config/agents/available` returns `color`, `tags`, `resource_tier`, `network_access` for each agent
- [ ] `color` field present in `metadata` and at root level
- [ ] `tags` field present in `metadata` and at root level
- [ ] All existing fields unchanged
- [ ] Python tests: verify new fields from a well-formed agent definition

### Dependencies
- None (self-contained)

### Estimated Complexity
**Small** — Adding field extraction to existing frontmatter parsing

### API Contract

**Before** (current available agent):
```json
{
  "agent_id": "python-engineer",
  "metadata": {
    "name": "Python Engineer",
    "description": "Python 3.12+ specialist...",
    "version": "2.3.0",
    "author": "remote",
    "category": "engineer/backend"
  },
  "source": "bobmatnyc/claude-mpm-agents",
  "priority": 100,
  "source_url": "https://github.com/bobmatnyc/claude-mpm-agents",
  "version": "2.3.0",
  "category": "engineer/backend",
  "is_deployed": false
}
```

**After** (enriched):
```json
{
  "agent_id": "python-engineer",
  "metadata": {
    "name": "Python Engineer",
    "description": "Python 3.12+ specialist...",
    "version": "2.3.0",
    "author": "remote",
    "category": "engineer/backend",
    "tags": ["python", "async", "SOA"],
    "color": "green",
    "resource_tier": "standard",
    "network_access": true
  },
  "source": "bobmatnyc/claude-mpm-agents",
  "priority": 100,
  "source_url": "https://github.com/bobmatnyc/claude-mpm-agents",
  "version": "2.3.0",
  "category": "engineer/backend",
  "tags": ["python", "async", "SOA"],
  "color": "green",
  "is_deployed": false
}
```

---

## Step 3: Enrich Deployed Skills with Manifest Data

### What
Cross-reference deployed skills against the cached manifest to fill in `version`, `toolchain`, `tags`, `full_tokens`, `entry_point_tokens`, and `framework`. Currently, deployed skills return sparse data from the deployment index (`name`, `path`, `description` [often empty], `category`, `collection`, `deploy_mode`, `deploy_date`). The manifest has rich metadata for every skill.

> **[REVISED]** Corrected deployment index file name reference. The actual file is **`.mpm-deployed-skills.json`** (confirmed at `selective_skill_deployer.py:51`), NOT `.deployment_index.json` as previously referenced in some plan documents.

### Where
- **Primary file**: `src/claude_mpm/services/monitor/config_routes.py`
  - Function: `handle_skills_deployed()` (lines 307-367)
  - Specifically the `_list_deployed_skills()` inner function

### How

After building the `skills_list` from the deployment index (line 334-349), cross-reference with manifest data:

```python
def _list_deployed_skills():
    skills_svc = _get_skills_deployer()
    project_skills_dir = Path.cwd() / ".claude" / "skills"
    deployed = skills_svc.check_deployed_skills(skills_dir=project_skills_dir)

    # ... existing deployment index loading (reads .mpm-deployed-skills.json) ...

    # NEW: Cross-reference with manifest for enrichment
    manifest_lookup = {}
    try:
        available = skills_svc.list_available_skills()
        available_skills = available.get("skills", [])
        # Build lookup: support both flat list and dict structures
        if isinstance(available_skills, list):
            for skill in available_skills:
                if isinstance(skill, dict):
                    manifest_lookup[skill.get("name", "")] = skill
        elif isinstance(available_skills, dict):
            for category, cat_skills in available_skills.items():
                if isinstance(cat_skills, list):
                    for skill in cat_skills:
                        if isinstance(skill, dict):
                            manifest_lookup[skill.get("name", "")] = skill
    except Exception as e:
        logger.warning(f"Could not load manifest for skill enrichment: {e}")

    # Enrich each deployed skill with manifest data
    for skill_item in skills_list:
        skill_name = skill_item.get("name", "")
        # Try exact match first, then suffix match
        manifest_entry = manifest_lookup.get(skill_name)
        if not manifest_entry:
            # Deployed names are path-normalized (e.g., "universal-testing-tdd")
            # Manifest names are short (e.g., "test-driven-development")
            for m_name, m_data in manifest_lookup.items():
                if skill_name.endswith(f"-{m_name}"):
                    manifest_entry = m_data
                    break

        if manifest_entry:
            skill_item["version"] = manifest_entry.get("version", "")
            skill_item["toolchain"] = manifest_entry.get("toolchain")
            skill_item["framework"] = manifest_entry.get("framework")
            skill_item["tags"] = manifest_entry.get("tags", [])
            skill_item["full_tokens"] = manifest_entry.get("full_tokens", 0)
            skill_item["entry_point_tokens"] = manifest_entry.get("entry_point_tokens", 0)
            # Enrich description from manifest if deployment index has empty description
            if not skill_item.get("description") and manifest_entry.get("description"):
                skill_item["description"] = manifest_entry.get("description", "")

    return {
        "skills": skills_list,
        "total": len(skills_list),
        "claude_skills_dir": str(deployed.get("claude_skills_dir", "")),
    }
```

### Why
- Deployed skills lose all manifest metadata — users see less info about deployed skills than available ones
- The manifest data is already cached by `SkillsDeployerService` (no additional GitHub calls)
- Cross-referencing is an in-memory join — fast and reliable
- Suffix matching handles the name normalization gap (deployed: `universal-testing-tdd`, manifest: `test-driven-development`)

### Edge Cases
- Manifest unavailable (network error, cache miss): graceful degradation to existing sparse data
- Deployed skill not in manifest (custom/local skill): no enrichment, fields missing → frontend handles gracefully
- Name mismatch between deployed and manifest names: suffix matching covers the common case; unmatched skills keep sparse data
- Empty manifest (first-time setup before sync): manifest_lookup is empty, no enrichment
- `list_available_skills()` returns dict vs list: both structures handled

### Acceptance Criteria
- [ ] `GET /api/config/skills/deployed` returns `version`, `toolchain`, `framework`, `tags`, `full_tokens`, `entry_point_tokens` when manifest data is available
- [ ] Sparse data returned when manifest unavailable (graceful degradation)
- [ ] All existing fields unchanged
- [ ] Response time: < 500ms additional latency for manifest cross-reference
- [ ] Python tests: verify enrichment with mock manifest data
- [ ] Python tests: verify graceful degradation when manifest unavailable

### Dependencies
- `SkillsDeployerService.list_available_skills()` must work (requires cached manifest or network)

### Estimated Complexity
**Medium** — In-memory join with name normalization

### API Contract

**Before** (current deployed skill):
```json
{
  "name": "universal-testing-test-driven-development",
  "path": "/path/.claude/skills/universal-testing-test-driven-development",
  "description": "",
  "category": "unknown",
  "collection": "claude-mpm-skills",
  "is_user_requested": false,
  "deploy_mode": "agent_referenced",
  "deploy_date": "2026-01-15T10:30:00Z"
}
```

**After** (enriched):
```json
{
  "name": "universal-testing-test-driven-development",
  "path": "/path/.claude/skills/universal-testing-test-driven-development",
  "description": "Comprehensive TDD patterns and practices for all programming languages",
  "category": "unknown",
  "collection": "claude-mpm-skills",
  "is_user_requested": false,
  "deploy_mode": "agent_referenced",
  "deploy_date": "2026-01-15T10:30:00Z",
  "version": "1.0.0",
  "toolchain": null,
  "framework": null,
  "tags": ["testing", "tdd", "quality"],
  "full_tokens": 3200,
  "entry_point_tokens": 85
}
```

---

## Step 4: Agent Detail Endpoint (Lazy-Loaded Rich Metadata)

### What
Create a new endpoint `GET /api/config/agents/{name}/detail` that returns the full frontmatter for a single deployed agent. This powers the detail panel's expandable sections (expertise, skills list, dependencies, handoff agents, constraints) without loading all this data for every agent in the list view.

### Where
- **Primary file**: `src/claude_mpm/services/monitor/config_routes.py`
  - New function: `handle_agent_detail()`
  - New route registration in `register_config_routes()`

### How

1. Register new route:
```python
# In register_config_routes():
app.router.add_get("/api/config/agents/{name}/detail", handle_agent_detail)
```

2. Implement handler:

> **Verification Amendment (VP-1-SEC — PATH TRAVERSAL VALIDATION, HIGH SEVERITY)**: The `{name}` path parameter is user-supplied and passed to `AgentManager.read_agent()`, which calls `_find_agent_file()` to construct filesystem paths like `self.project_dir / f"{name}.md"`. Without validation, a request to `GET /api/config/agents/../../etc/passwd/detail` could traverse the directory. The existing `validate_safe_name()` from `services/config_api/validation.py` MUST be imported and called before any file-system operation.

```python
async def handle_agent_detail(request: web.Request) -> web.Response:
    """GET /api/config/agents/{name}/detail - Full agent metadata for detail panel."""
    try:
        agent_name = request.match_info["name"]

        # MANDATORY: Path traversal protection (VP-1-SEC)
        from claude_mpm.services.config_api.validation import validate_safe_name
        if not validate_safe_name(agent_name):
            return web.json_response(
                {"success": False, "error": f"Invalid agent name: '{agent_name}'", "code": "INVALID_NAME"},
                status=400,
            )

        def _get_detail():
            import frontmatter as fm_lib

            agent_mgr = _get_agent_manager()
            agent_def = agent_mgr.read_agent(agent_name)
            if not agent_def:
                return None

            # Parse full frontmatter from raw content
            post = fm_lib.loads(agent_def.raw_content)
            fmdata = post.metadata

            capabilities = fmdata.get("capabilities", {})
            if not isinstance(capabilities, dict):
                capabilities = {}

            knowledge = fmdata.get("knowledge", {})
            if not isinstance(knowledge, dict):
                knowledge = {}

            interactions = fmdata.get("interactions", {})
            if not isinstance(interactions, dict):
                interactions = {}

            # Normalize skills field
            skills_field = fmdata.get("skills", [])
            if isinstance(skills_field, dict):
                skills_list = list(set(
                    (skills_field.get("required") or []) +
                    (skills_field.get("optional") or [])
                ))
            elif isinstance(skills_field, list):
                skills_list = skills_field
            else:
                skills_list = []

            # Normalize dependencies
            dependencies = fmdata.get("dependencies", {})
            if not isinstance(dependencies, dict):
                dependencies = {}

            return {
                "name": fmdata.get("name", agent_name),
                "agent_id": fmdata.get("agent_id", agent_name),
                "description": fmdata.get("description", ""),
                "version": fmdata.get("version", agent_def.metadata.version),
                "category": fmdata.get("category", ""),
                "color": fmdata.get("color", "gray"),
                "tags": fmdata.get("tags", []),
                "resource_tier": fmdata.get("resource_tier", ""),
                "agent_type": fmdata.get("agent_type", ""),
                "temperature": fmdata.get("temperature"),
                "timeout": fmdata.get("timeout"),
                "network_access": capabilities.get("network_access"),
                "skills": skills_list,
                "dependencies": dependencies,
                "knowledge": {
                    "domain_expertise": knowledge.get("domain_expertise", []),
                    "constraints": knowledge.get("constraints", []),
                    "best_practices": knowledge.get("best_practices", []),
                },
                "handoff_agents": interactions.get("handoff_agents", []),
                "author": fmdata.get("author", ""),
                "schema_version": fmdata.get("schema_version", ""),
            }

        data = await asyncio.to_thread(_get_detail)

        if data is None:
            return web.json_response(
                {"success": False, "error": f"Agent '{agent_name}' not found", "code": "NOT_FOUND"},
                status=404,
            )

        return web.json_response({"success": True, "data": data})
    except Exception as e:
        logger.error(f"Error fetching agent detail for {request.match_info.get('name', '?')}: {e}")
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )
```

### Why
- Detail panel needs 15+ fields (expertise, skills list, dependencies, handoff agents, constraints)
- Loading all this data for every agent in the list view would be wasteful
- Single-agent frontmatter parsing is fast (~1-5ms per file) — acceptable for on-click latency
- Follows the progressive disclosure pattern recommended in research

### Edge Cases
- Agent not found: 404 response with clear error message
- Agent without knowledge block: empty arrays for expertise/constraints/best_practices
- Agent without interactions block: empty array for handoff_agents
- Agent without skills field: empty array
- Malformed YAML nested structures: `isinstance` checks prevent crashes
- Available (not deployed) agent requested: returns 404 (only searches project agents)

### Acceptance Criteria
- [ ] `GET /api/config/agents/engineer/detail` returns full metadata including knowledge, skills, dependencies, handoff_agents
- [ ] Returns 404 with `{"success": false, "error": "...", "code": "NOT_FOUND"}` for non-existent agents
- [ ] **VP-1-SEC**: Returns 400 with `{"success": false, "error": "Invalid agent name: '...'", "code": "INVALID_NAME"}` for names containing path traversal characters (`../`, `/`, etc.)
- [ ] **VP-1-SEC**: `validate_safe_name()` is called BEFORE `read_agent()` — names like `../../etc/passwd` are rejected without any filesystem access
- [ ] Response time: < 50ms for single file parse
- [ ] All optional fields gracefully default to empty arrays/dicts when missing
- [ ] `color` defaults to `"gray"` when not in frontmatter
- [ ] Python tests: verify full response for complex agent (e.g., research agent)
- [ ] Python tests: verify minimal response for simple agent (e.g., local-ops)
- [ ] Python tests: verify 404 for non-existent agent
- [ ] **VP-1-SEC**: Security test: verify 400 for path traversal attempts (`../secret`, `foo/../../bar`, `/etc/passwd`)
- [ ] **VP-1-TEST**: Integration test with real `AgentManager` and fixture agent file (not mocked)

### Dependencies
- None (uses existing `AgentManager.read_agent()`)

### Estimated Complexity
**Small-Medium** — New endpoint, but uses existing parsing infrastructure

### API Contract

**Request**: `GET /api/config/agents/python-engineer/detail`

**Response**:
```json
{
  "success": true,
  "data": {
    "name": "Python Engineer",
    "agent_id": "python-engineer",
    "description": "Python 3.12+ development specialist: type-safe, async-first...",
    "version": "2.3.0",
    "category": "engineering",
    "color": "green",
    "tags": ["python", "async", "SOA", "DI"],
    "resource_tier": "standard",
    "agent_type": "engineer",
    "temperature": 0.2,
    "timeout": 900,
    "network_access": true,
    "skills": ["dspy", "langchain", "mcp", "pytest", "mypy", "pydantic", "git-workflow", "test-driven-development"],
    "dependencies": {
      "python": ["black>=24.0.0", "isort>=5.13.0", "mypy>=1.8.0", "pytest>=8.0.0"],
      "system": ["python3.12+", "git"]
    },
    "knowledge": {
      "domain_expertise": ["Python 3.12-3.13 features (JIT, TypeForm)", "Service-oriented architecture with ABC"],
      "constraints": ["Maximum 5-10 test files for sampling per session"],
      "best_practices": ["100% type coverage with mypy --strict"]
    },
    "handoff_agents": ["qa", "security", "data_engineer"],
    "author": "Claude MPM Team",
    "schema_version": "1.3.0"
  }
}
```

---

## Step 5: Skill Content Preview Endpoint

### What
Create a new endpoint `GET /api/config/skills/{name}/detail` that returns enriched skill metadata from the SKILL.md frontmatter (particularly `when_to_use` and `progressive_disclosure.entry_point.summary`) and, if available, metadata.json fields (key_features, use_cases, related_skills, prerequisites).

### Where
- **Primary file**: `src/claude_mpm/services/monitor/config_routes.py`
  - New function: `handle_skill_detail()`
  - New route registration in `register_config_routes()`

### How

1. Register new route:
```python
# In register_config_routes():
app.router.add_get("/api/config/skills/{name}/detail", handle_skill_detail)
```

2. Implement handler:

> **Verification Amendment (VP-1-SEC — PATH TRAVERSAL VALIDATION, HIGH SEVERITY)**: Same as Step 4. The `{name}` parameter is used to construct a filesystem path (`project_skills_dir / skill_name`). Without validation, a crafted name like `../../etc` could traverse directories. The existing `validate_safe_name()` MUST be applied.

```python
async def handle_skill_detail(request: web.Request) -> web.Response:
    """GET /api/config/skills/{name}/detail - Enriched skill metadata for detail panel."""
    try:
        skill_name = request.match_info["name"]

        # MANDATORY: Path traversal protection (VP-1-SEC)
        from claude_mpm.services.config_api.validation import validate_safe_name
        if not validate_safe_name(skill_name):
            return web.json_response(
                {"success": False, "error": f"Invalid skill name: '{skill_name}'", "code": "INVALID_NAME"},
                status=400,
            )

        def _get_skill_detail():
            # Look for the skill in the deployed skills directory
            project_skills_dir = Path.cwd() / ".claude" / "skills"
            skill_dir = project_skills_dir / skill_name
            skill_md = skill_dir / "SKILL.md"

            result = {"name": skill_name}

            # Parse SKILL.md frontmatter if deployed
            if skill_md.exists():
                try:
                    content = skill_md.read_text(encoding="utf-8")
                    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
                    if match:
                        fm = yaml.safe_load(match.group(1)) or {}
                        result["when_to_use"] = fm.get("when_to_use", "")
                        result["languages"] = fm.get("languages", "")
                        pd = fm.get("progressive_disclosure", {})
                        if isinstance(pd, dict):
                            entry = pd.get("entry_point", {})
                            if isinstance(entry, dict):
                                result["summary"] = entry.get("summary", "")
                                result["quick_start"] = entry.get("quick_start", "")
                            refs = pd.get("references", [])
                            if isinstance(refs, list):
                                result["references"] = [
                                    {"path": r.get("path", ""), "purpose": r.get("purpose", "")}
                                    for r in refs if isinstance(r, dict)
                                ]
                        # Frontmatter description/name override
                        result["description"] = fm.get("description", result.get("description", ""))
                        result["frontmatter_name"] = fm.get("name", "")
                        result["frontmatter_tags"] = fm.get("tags", [])
                except Exception as e:
                    logger.warning(f"Failed to parse SKILL.md for {skill_name}: {e}")

            # Cross-reference with manifest data for baseline fields
            try:
                skills_svc = _get_skills_deployer()
                available = skills_svc.list_available_skills()
                available_skills = available.get("skills", [])
                manifest_entry = None

                if isinstance(available_skills, list):
                    for s in available_skills:
                        if isinstance(s, dict) and (
                            s.get("name") == skill_name or
                            skill_name.endswith(f"-{s.get('name', '')}")
                        ):
                            manifest_entry = s
                            break
                elif isinstance(available_skills, dict):
                    for cat, cat_skills in available_skills.items():
                        if isinstance(cat_skills, list):
                            for s in cat_skills:
                                if isinstance(s, dict) and (
                                    s.get("name") == skill_name or
                                    skill_name.endswith(f"-{s.get('name', '')}")
                                ):
                                    manifest_entry = s
                                    break
                            if manifest_entry:
                                break

                if manifest_entry:
                    result["version"] = manifest_entry.get("version", "")
                    result["toolchain"] = manifest_entry.get("toolchain")
                    result["framework"] = manifest_entry.get("framework")
                    result["tags"] = manifest_entry.get("tags", [])
                    result["full_tokens"] = manifest_entry.get("full_tokens", 0)
                    result["entry_point_tokens"] = manifest_entry.get("entry_point_tokens", 0)
                    result["requires"] = manifest_entry.get("requires", [])
                    result["author"] = manifest_entry.get("author", "")
                    result["updated"] = manifest_entry.get("updated", "")
                    result["source_path"] = manifest_entry.get("source_path", "")
                    if not result.get("description"):
                        result["description"] = manifest_entry.get("description", "")
            except Exception as e:
                logger.warning(f"Could not load manifest for skill detail: {e}")

            # Get agent usage from skill-links
            try:
                mapper = _get_skill_to_agent_mapper()
                links = mapper.get_all_links()
                by_skill = links.get("by_skill", {})
                # Try exact match, then suffix match
                skill_agents = by_skill.get(skill_name, {})
                if not skill_agents:
                    for s_name, s_data in by_skill.items():
                        if skill_name.endswith(f"-{s_name}") or s_name.endswith(f"-{skill_name}"):
                            skill_agents = s_data
                            break
                result["used_by_agents"] = skill_agents.get("agents", []) if isinstance(skill_agents, dict) else []
                result["agent_count"] = len(result["used_by_agents"])
            except Exception as e:
                logger.warning(f"Could not load skill-links for {skill_name}: {e}")
                result["used_by_agents"] = []
                result["agent_count"] = 0

            return result

        data = await asyncio.to_thread(_get_skill_detail)
        return web.json_response({"success": True, "data": data})
    except Exception as e:
        logger.error(f"Error fetching skill detail for {request.match_info.get('name', '?')}: {e}")
        return web.json_response(
            {"success": False, "error": str(e), "code": "SERVICE_ERROR"},
            status=500,
        )
```

### Why
- Skill detail panel needs `when_to_use`, agent usage, and progressive disclosure data
- Loading this for all 156 skills in the list view would be expensive
- Lazy loading on click is the right pattern for detail data
- Combines three data sources: SKILL.md frontmatter, manifest, and skill-links

### Edge Cases
- Skill not deployed (no SKILL.md): returns manifest data only
- Skill not in manifest (custom/local): returns SKILL.md data only
- Neither deployed nor in manifest: returns minimal `{name}` response
- SKILL.md without frontmatter: frontmatter parsing skipped
- Skill-links unavailable: `used_by_agents` defaults to empty array
- Name normalization mismatch: suffix matching handles deployed vs manifest names

### Acceptance Criteria
- [ ] `GET /api/config/skills/{name}/detail` returns `when_to_use`, `summary`, `used_by_agents`, `agent_count` plus manifest fields
- [ ] **VP-1-SEC**: Returns 400 with `{"success": false, "error": "Invalid skill name: '...'", "code": "INVALID_NAME"}` for names containing path traversal characters (`../`, `/`, etc.)
- [ ] **VP-1-SEC**: `validate_safe_name()` is called BEFORE any filesystem path construction
- [ ] Graceful degradation when any data source is unavailable
- [ ] Response time: < 100ms
- [ ] Python tests: verify combined response from all three sources
- [ ] Python tests: verify degraded response when SKILL.md missing
- [ ] Python tests: verify degraded response when manifest unavailable
- [ ] **VP-1-SEC**: Security test: verify 400 for path traversal attempts (`../secret`, `foo/../../bar`)
- [ ] **VP-1-TEST**: Integration test with real deployed skill directory and fixture files (not mocked)

### Dependencies
- Step 3 (same manifest cross-reference pattern, but can be implemented independently)

### Estimated Complexity
**Medium** — New endpoint combining three data sources with name normalization

### API Contract

**Request**: `GET /api/config/skills/universal-testing-test-driven-development/detail`

**Response**:
```json
{
  "success": true,
  "data": {
    "name": "universal-testing-test-driven-development",
    "description": "Comprehensive TDD patterns and practices for all programming languages",
    "version": "1.0.0",
    "toolchain": null,
    "framework": null,
    "tags": ["testing", "tdd", "quality"],
    "full_tokens": 3200,
    "entry_point_tokens": 85,
    "requires": [],
    "author": "claude-mpm-skills",
    "updated": "2025-12-15",
    "source_path": "universal/testing/test-driven-development/SKILL.md",
    "when_to_use": "When writing tests, implementing test-first methodology, or establishing testing patterns",
    "languages": "all",
    "summary": "Brief TDD pattern summary",
    "quick_start": "Step-by-step quick start guide",
    "frontmatter_name": "Test-Driven Development",
    "frontmatter_tags": ["testing", "tdd"],
    "references": [
      {"path": "references/patterns-and-implementation.md", "purpose": "Detailed implementation guide"}
    ],
    "used_by_agents": ["python-engineer", "java-engineer", "rust-engineer", "qa", "web-qa"],
    "agent_count": 5
  }
}
```

---

## Step 6: Add Agent Count to Available Skills Endpoint

### What
Enrich the available skills endpoint to include `agent_count` — how many agents reference each skill. This is derived from the skill-links data that the `SkillToAgentMapper` already computes.

### Where
- **Primary file**: `src/claude_mpm/services/monitor/config_routes.py`
  - Function: `handle_skills_available()` (lines 370-451)

### How

In `_list_available_skills()`, after building the flat skills list and before returning:

```python
def _list_available_skills():
    # ... existing code to build flat_skills ...

    # NEW: Enrich with agent count from skill-links
    try:
        mapper = _get_skill_to_agent_mapper()
        links = mapper.get_all_links()
        by_skill = links.get("by_skill", {})

        for skill in flat_skills:
            skill_name = skill.get("name", "")
            skill_data = by_skill.get(skill_name, {})
            if not skill_data:
                # Try suffix matching for normalized names
                for s_name, s_data in by_skill.items():
                    if s_name.endswith(f"-{skill_name}") or skill_name.endswith(f"-{s_name}"):
                        skill_data = s_data
                        break
            agents = skill_data.get("agents", []) if isinstance(skill_data, dict) else []
            skill["agent_count"] = len(agents)
    except Exception as e:
        logger.warning(f"Could not load skill-links for agent counts: {e}")
        # Don't fail - just skip enrichment

    return flat_skills
```

### Why
- Shows "N agents" badge in skill list cards without requiring a separate API call
- The skill-links data is already computed by `SkillToAgentMapper`
- In-memory lookup — no additional I/O
- Helps users assess skill importance at a glance

### Edge Cases
- Skill-links unavailable: skip enrichment, `agent_count` field won't be present
- Skill not referenced by any agent: `agent_count = 0`
- Name mismatch: suffix matching handles normalized vs short names

### Acceptance Criteria
- [ ] `GET /api/config/skills/available` returns `agent_count` for each skill
- [ ] `agent_count` accurately reflects the number of agents referencing each skill
- [ ] Graceful degradation if skill-links unavailable
- [ ] No performance regression (skill-links data is cached)

### Dependencies
- `SkillToAgentMapper` must be working (Phase 4A feature, already implemented)

### Estimated Complexity
**Small** — In-memory lookup added to existing endpoint

### API Contract

**Enrichment added to each available skill**:
```json
{
  "name": "test-driven-development",
  "version": "1.0.0",
  "agent_count": 30,
  ...
}
```

---

## Step 7: Frontend TypeScript Interface Updates (Deployed Agent)

### What
Update the `DeployedAgent` TypeScript interface and the `AgentsList.svelte` component to render the new fields from Step 1.

### Where
- **Primary file**: `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts` (interface)
- **Primary file**: `src/claude_mpm/dashboard-svelte/src/lib/components/config/AgentsList.svelte` (rendering)

### How

1. Update `DeployedAgent` interface:
```typescript
interface DeployedAgent {
    name: string;
    location: string;
    path: string;
    version: string;
    type: string;
    specializations?: string[];
    is_core: boolean;
    // NEW Phase 2 fields:
    description?: string;
    category?: string;
    color?: string;
    tags?: string[];
    resource_tier?: string;
    network_access?: boolean;
    skills_count?: number;
}
```

2. In `AgentsList.svelte` deployed section, render:
   - Color dot (small circle with agent's color, default gray)
   - Description (truncated to ~80 chars, 1 line)
   - Tags (max 3, small badge chips)
   - Network access icon (globe/lock)
   - Resource tier label

### Why
- Backend now provides these fields (Step 1)
- Deployed agents need description visibility (the most critical gap identified)
- Color dots provide visual differentiation between agent categories
- Progressive disclosure: list shows summary, detail panel shows full data

### Edge Cases
- Fields not present (backend not yet upgraded): all new fields are optional with `?`
- Empty description: show "No description available" in muted text
- Missing color: default to `gray` CSS class
- Empty tags array: hide tags section

### Acceptance Criteria
- [ ] Deployed agents show description, color dot, tags, and network icon in list view
- [ ] All new fields are optional — backward compatible with old backend responses
- [ ] Visual styling matches existing design conventions (Tailwind, slate/cyan theme)
- [ ] Color dot defaults to gray when `color` field is missing or empty

### Dependencies
- Step 1 (backend enrichment)
- Phase 1 completed (badge consolidation, shared components)

### Estimated Complexity
**Medium** — Interface update + component rendering changes

---

## Step 8: Frontend TypeScript Interface Updates (Deployed Skill)

### What
Update the `DeployedSkill` TypeScript interface and `SkillsList.svelte` component to render the new fields from Step 3.

### Where
- **Primary file**: `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts` (interface)
- **Primary file**: `src/claude_mpm/dashboard-svelte/src/lib/components/config/SkillsList.svelte` (rendering)

### How

1. Update `DeployedSkill` interface:
```typescript
interface DeployedSkill {
    name: string;
    path: string;
    description: string;
    category: string;
    collection: string;
    is_user_requested: boolean;
    deploy_mode: 'agent_referenced' | 'user_defined';
    deploy_date: string;
    // NEW Phase 2 fields:
    version?: string;
    toolchain?: string | null;
    framework?: string | null;
    tags?: string[];
    full_tokens?: number;
    entry_point_tokens?: number;
}
```

2. In `SkillsList.svelte` deployed section, render:
   - Version badge
   - Toolchain badge (for grouping)
   - Tags (max 3)
   - Token count indicator

### Why
- Backend now provides these fields (Step 3)
- Deployed skills need version and toolchain visibility
- Enables toolchain-based grouping in the skills list (Phase 1 prerequisite)

### Edge Cases
- Fields not present: all optional with `?`
- `toolchain` is `null` for universal skills: show "Universal" label
- `full_tokens` is 0 or missing: hide token indicator

### Acceptance Criteria
- [ ] Deployed skills show version, toolchain, tags, and token count
- [ ] Backward compatible with old backend responses
- [ ] Matches Phase 1 available skills rendering conventions

### Dependencies
- Step 3 (backend enrichment)
- Phase 1 completed

### Estimated Complexity
**Small-Medium** — Interface update + component rendering

---

## Step 9: Frontend Detail Panel Integration

### What
Update the ConfigView right panel to fetch and display the rich detail data from the new agent and skill detail endpoints (Steps 4 and 5). Implement expandable/collapsible sections for progressive disclosure.

### Where
- **Primary file**: `src/claude_mpm/dashboard-svelte/src/lib/components/config/ConfigView.svelte` (right panel)
- **May require**: New `AgentDetailPanel.svelte` and `SkillDetailPanel.svelte` components

### How

1. When a deployed agent or available agent is selected in the list:
   - Fetch `GET /api/config/agents/{name}/detail`
   - Render the enriched data with collapsible sections

2. When a skill is selected:
   - Fetch `GET /api/config/skills/{name}/detail`
   - Render with collapsible sections

3. Collapsible sections pattern:
```svelte
<details class="group">
  <summary class="cursor-pointer font-medium text-slate-700 dark:text-slate-300">
    Expertise ({data.knowledge.domain_expertise.length} items)
  </summary>
  <ul class="mt-2 pl-4 text-sm text-slate-600 dark:text-slate-400">
    {#each data.knowledge.domain_expertise as item}
      <li class="mt-1">{item}</li>
    {/each}
  </ul>
</details>
```

4. Skills chips in agent detail:
```svelte
<div class="flex flex-wrap gap-1.5">
  {#each data.skills as skill}
    <span class="px-2 py-0.5 text-xs rounded-full bg-slate-100 dark:bg-slate-800">
      {skill}
    </span>
  {/each}
</div>
```

### Why
- Progressive disclosure reduces information overload in the detail panel
- Lazy loading detail data keeps list view fast
- Collapsible sections let users expand only what they need
- Skills chips with deployment indicators help users assess readiness

### Edge Cases
- Detail endpoint returns error: show "Could not load details" message
- Slow network: show loading spinner in detail panel
- Agent/skill not found (404): show appropriate empty state
- Very long expertise lists (23 items for research agent): collapsible section handles this naturally

### Acceptance Criteria
- [ ] Agent detail panel shows: description, category/tier/network grid, collapsible expertise, skills chips, dependencies, handoff agents, constraints, footer with source/temperature/timeout
- [ ] Skill detail panel shows: description, toolchain/tokens/updated grid, when_to_use, used_by agents, requires, related_skills
- [ ] All sections gracefully handle missing data
- [ ] Loading states shown during fetch
- [ ] Svelte 5 Runes API used (not Svelte 4 stores)

### Dependencies
- Steps 4, 5 (backend detail endpoints)
- Phase 1 completed
- Steps 7, 8 (interface updates)

### Estimated Complexity
**Large** — New components with multiple data sources and interaction patterns

---

## Agent Deployment Status Strategy

> **[REVISED]** Added this section to address R1 (cross-phase dependency gap). Phase 3 originally required an agent deployment index file (`.claude/agents/.deployment_index.json`) that Phase 2 never creates. Resolution: agents don't need a deployment index — use filesystem presence check instead.

**Problem**: Phase 3's AgentDetailPanel originally listed "Agent deployment index (`.claude/agents/.deployment_index.json`) — from Phase 2" as a prerequisite. But no such file exists or is created.

**Resolution**: Agent deployment status is determined by **filesystem presence check**, not a deployment index:
- A deployed agent is one whose `.md` file exists in `.claude/agents/` (the project directory)
- `list_agents(location="project")` already returns only project-deployed agents
- The `is_deployed` flag on available agents is already set by `handle_agents_available()` which cross-references cached agents against project agents

**No new deployment index file is needed for agents.** Skills use `.mpm-deployed-skills.json` because skill deployment is more complex (selective deployment, user-requested vs agent-referenced). Agent deployment is simple (file exists = deployed).

Phase 3 should remove the agent deployment index prerequisite and instead rely on the existing `is_deployed` cross-reference that `handle_agents_available()` already performs.

---

## Performance Considerations

### Current Baseline
- Deployed agents endpoint: ~50-100ms (15-20 file reads with YAML parsing)
- Available agents endpoint: ~20-50ms (in-memory from cache)
- Deployed skills endpoint: ~10-30ms (directory scan + JSON read)
- Available skills endpoint: ~100-200ms (manifest download or cache read)

### Expected Impact

| Change | Impact | Mitigation |
|--------|--------|------------|
| Step 1: Frontmatter re-parse from raw_content | ~1ms per agent (in-memory string parse) | No file I/O; 20 agents × 1ms = 20ms total |
| Step 2: Extract 4 more fields from already-parsed frontmatter | ~0ms additional | Same file read, more regex |
| Step 3: Cross-reference deployed skills with manifest | ~50-100ms first call | Manifest cached after first call |
| Step 4: Agent detail endpoint (single file) | ~5-10ms per request | Only on user click, not list load |
| Step 5: Skill detail endpoint (file + manifest + links) | ~20-50ms per request | Only on user click |
| Step 6: Add agent count to available skills | ~10-20ms | In-memory lookup from cached data |

### Caching Strategy
- Steps 1, 2: No additional caching needed (in-memory operations on already-loaded data)
- Step 3: Manifest data cached in-memory by `SkillsDeployerService` (already implemented)
- Steps 4, 5: Consider adding `Cache-Control: private, max-age=60` to detail responses
- Step 6: Skill-links data cached in-memory by `SkillToAgentMapper`

### Response Size Management
- List endpoints: New fields add ~200 bytes per agent/skill (negligible)
- Detail endpoints: Full response ~2-5KB per item (acceptable for single-item requests)
- No pagination changes needed (already implemented for list endpoints)

---

## Migration Strategy for Existing Deployments

### Backward Compatibility
All changes are **additive** — new fields are added alongside existing ones:
- No existing fields are removed or renamed
- No existing response structure changes
- Frontend interfaces use optional (`?`) types for all new fields
- Frontend gracefully handles missing new fields with defaults

### Progressive Rollout
1. Deploy backend changes (Steps 1-6) first
2. Deploy frontend changes (Steps 7-9) after backend is stable
3. Frontend works with both old and new backend responses

### No Database/Storage Schema Changes
- No new index files required for Phase 2
- Skill deployment index (`.mpm-deployed-skills.json`) unchanged
- Agent deployment status uses filesystem presence (no index needed)
- All enrichment comes from existing data sources (frontmatter, manifest, skill-links)

---

## Testing Strategy

> **Verification Amendment (VP-1-TEST)**: The existing test suite uses `unittest.mock.MagicMock` for ALL backend services. Mocked tests cannot catch type mismatches, missing fields, or data flow bugs. Phase 2 testing must include both mocked unit tests (for speed) AND integration tests with real service instances (for correctness).

### Unit Tests (Mocked — existing pattern)

| Component | Test File | Tests |
|-----------|-----------|-------|
| `AgentManager.list_agents()` enrichment | `tests/services/agents/test_agent_management_service.py` | Verify new fields returned, defaults for missing fields, graceful handling of malformed frontmatter |
| `AgentManager.list_agent_names()` | `tests/services/agents/test_agent_management_service.py` | Verify returns same name set as `list_agents().keys()` |
| `_parse_markdown_agent()` new fields | `tests/services/agents/deployment/test_remote_agent_discovery.py` | Verify color/tags/tier extraction |
| Deployed skills enrichment | `tests/services/monitor/test_config_routes.py` | Verify manifest cross-reference, suffix matching |
| Agent detail endpoint | `tests/services/monitor/test_config_routes.py` | Verify full response, 404 handling, default values for missing fields |
| Skill detail endpoint | `tests/services/monitor/test_config_routes.py` | Verify combined data sources |
| Agent count enrichment | `tests/services/monitor/test_config_routes.py` | Verify skill-links integration |
| **Path traversal validation** | `tests/services/monitor/test_config_routes.py` | **VP-1-SEC**: Verify 400 response for `../`, `/etc/passwd`, `foo/../../bar` in agent/skill detail endpoints |

### Integration Tests (Real services — NEW requirement per VP-1-TEST)

> These tests instantiate real `AgentManager` and `SkillsDeployerService` instances with fixture files in a temporary directory. They verify end-to-end data flow from filesystem to API response format.

| Scenario | Description | Fixture Files |
|----------|-------------|---------------|
| Full pipeline: agent deploy → API response | Deploy a fixture agent, call `list_agents()`, verify enriched response has all expected fields with correct types | `fixture-agent-full.md` (all frontmatter fields), `fixture-agent-minimal.md` (missing color/tier) |
| Malformed agent handling | Agent with invalid YAML frontmatter, verify graceful defaults | `fixture-agent-malformed.md` |
| Agent detail endpoint → real parse | Call detail endpoint with real `AgentManager`, verify response matches `agent_def.to_dict()` structure | `fixture-agent-full.md` |
| Manifest cache → skill enrichment | With cached manifest, verify deployed skills enrichment | Fixture manifest + deployed skill directory |
| Detail endpoint → skill-links integration | Verify agent detail includes skills, skill detail includes agents | Fixture agent with skills references |
| Graceful degradation | Verify response when manifest/skill-links unavailable | Missing/empty fixture directories |
| `list_agent_names()` consistency | Verify `list_agent_names()` returns same names as `set(list_agents().keys())` | Multiple fixture agents |

### Integration Tests (Existing)

| Scenario | Description |
|----------|-------------|
| Full pipeline: agent deploy → API response | Deploy an agent, verify enriched response |
| Manifest cache → skill enrichment | With cached manifest, verify deployed skills enrichment |
| Detail endpoint → skill-links integration | Verify agent detail includes skills, skill detail includes agents |
| Graceful degradation | Verify response when manifest/skill-links unavailable |

### Frontend Tests
- TypeScript compile check: new interfaces type-check correctly
- Component rendering: verify new fields render in list and detail views
- Loading states: verify skeleton/spinner during detail fetch
- Edge cases: verify defaults when optional fields are missing

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **VP-1-SEC: Path traversal in detail endpoints** | **Certain without mitigation** | **HIGH** | **Import and call `validate_safe_name()` before any filesystem operation in Steps 4 and 5** |
| **VP-1-PERF: Double-parsing in list_agents()** | Certain if approach (b) chosen | Medium | Use approach (a) — reuse already-parsed fields; or accept (b) with documented tech debt |
| **VP-1-PERF: handle_agents_available cascade** | Certain | Medium | Step 0: Create `list_agent_names()` for lightweight name-only lookup |
| **VP-1-CONC: Concurrent CLI/dashboard file access** | Medium | Medium | Accept eventual consistency; add error logging for partial reads; document known limitation |
| **VP-1-TEST: Mocked tests hide data flow bugs** | High | Medium | Add integration tests with real `AgentManager` instances per VP-1-TEST section |
| Frontmatter re-parse performance | Low | Low | In-memory string parse < 1ms per agent; no file I/O |
| Manifest cross-reference stale data | Medium | Low | Manifest cached; stale data is better than no data |
| Name normalization mismatch (deployed vs manifest) | Medium | Medium | Suffix matching handles common cases; log warnings for mismatches |
| Breaking existing API consumers | Very Low | High | Caller audit confirms all changes are additive (see audit table) |
| Frontend type errors from missing fields | Low | Low | All new fields optional with `?` types |
| Detail endpoint latency | Low | Low | Single-file parse is fast; add cache headers |
| 3 agents missing color field | Certain | Low | Default to "gray" in backend and frontend |

---

## Rollback Plan

Each step can be independently reverted:

1. **Backend changes** (Steps 1-6): Revert the Python file changes; API returns to previous response format
2. **Frontend changes** (Steps 7-9): Frontend gracefully handles missing fields (optional types with defaults)
3. **New endpoints** (Steps 4-5): Simply remove route registrations; frontend falls back to existing data

No data migration or schema changes means rollback is a simple code revert.

---

## Step Execution Order

> **Verification Amendment (VP-1-PERF)**: Step 0 added as a prerequisite for Step 1 to prevent performance degradation.

```
Step 0: Create list_agent_names()                ← FIRST — prevents performance cascade (VP-1-PERF)
  │
Step 1: Enrich AgentManager.list_agents()        ← After Step 0; highest impact
Step 2: Add color/tags to available agents       ← No dependencies
Step 3: Enrich deployed skills with manifest     ← No dependencies
Step 6: Add agent count to available skills      ← No dependencies
  │
  ├── Steps 1-3, 6 can be implemented in parallel (independent)
  │
Step 4: Agent detail endpoint                    ← After Step 1 (same frontmatter approach)
Step 5: Skill detail endpoint                    ← After Step 3 (same manifest approach)
  │                                                 MUST include validate_safe_name() (VP-1-SEC)
  ├── Steps 4-5 can be implemented in parallel (independent)
  │
Step 7: Frontend deployed agent interface        ← After Step 1
Step 8: Frontend deployed skill interface        ← After Step 3
Step 9: Frontend detail panel integration        ← After Steps 4, 5, 7, 8
```

**Critical path**: Steps 0 → 1 → 7 → 9 (performance fix → agent enrichment → detail panel)

> **VP-1-DEPLOY**: Phase 2 MUST be fully deployed before Phase 3 implementation begins. Phase 3 detail panels depend on the endpoints created in Steps 4 and 5.

---

## Phase 2 → Phase 3 Contract

> **[REVISED]** Added explicit contract to ensure Phase 3 knows exactly what Phase 2 provides.

### What Phase 2 Provides to Phase 3

| Deliverable | Type | Endpoint / Location | Fields |
|-------------|------|---------------------|--------|
| Enriched deployed agents | API response | `GET /api/config/agents/deployed` | description, category, color, tags, resource_tier, network_access, skills_count |
| Enriched available agents | API response | `GET /api/config/agents/available` | color, tags, resource_tier, network_access (in metadata + root) |
| Enriched deployed skills | API response | `GET /api/config/skills/deployed` | version, toolchain, framework, tags, full_tokens, entry_point_tokens |
| Agent detail data | New endpoint | `GET /api/config/agents/{name}/detail` | Full frontmatter: knowledge, skills, dependencies, handoff_agents, constraints |
| Skill detail data | New endpoint | `GET /api/config/skills/{name}/detail` | when_to_use, summary, used_by_agents, agent_count, references |
| Agent count per skill | API response | `GET /api/config/skills/available` | agent_count |
| Agent deployment status | Filesystem check | `.claude/agents/{name}.md` existence | Boolean: file exists = deployed |

### What Phase 2 Does NOT Provide (Phase 3 Must Not Depend On)

| Item | Reason |
|------|--------|
| Agent deployment index file (`.claude/agents/.deployment_index.json`) | Agents use filesystem presence check instead |
| Graph/relationship endpoint | Phase 3 builds graph from cached agent detail data client-side |
| Skill deployment index changes | Existing `.mpm-deployed-skills.json` is unchanged |

---

## Summary

Phase 2 addresses the most impactful data gaps identified in research:

0. **Lightweight agent name listing** (Step 0) — performance pre-requisite (VP-1-PERF)
1. **Deployed agents get description, category, color, tags** (Step 1) — the #1 issue
2. **Available agents get color, tags, resource_tier** (Step 2) — visual differentiation
3. **Deployed skills get manifest data** (Step 3) — version, toolchain, tags
4. **Detail endpoints for lazy-loaded rich metadata** (Steps 4-5) — progressive disclosure, with mandatory path traversal validation (VP-1-SEC)
5. **Agent count on skills** (Step 6) — importance indicator
6. **Frontend rendering of all new data** (Steps 7-9) — user-facing value

Total: 1 pre-requisite + 6 backend changes + 3 frontend changes = 10 implementation steps.
All changes are additive and backward compatible.

### Verification Amendment Summary

| ID | Severity | Issue | Resolution |
|----|----------|-------|------------|
| VP-1-SEC | HIGH | Path traversal in Steps 4/5 detail endpoints | Import `validate_safe_name()` before filesystem ops |
| VP-1-PERF (parsing) | MODERATE | Double frontmatter parsing in Step 1 | Use approach (a) or accept (b) with documented debt |
| VP-1-PERF (cascade) | MODERATE | `handle_agents_available` parses all agents for name set | Step 0: `list_agent_names()` method |
| VP-1-CONC | MODERATE | Concurrent CLI/dashboard file access | Accept eventual consistency; add error logging |
| VP-1-TEST | MODERATE | Mocked tests hide real data flow bugs | Integration tests with real service instances |
| VP-1-DEPLOY | MODERATE | Phase deployment ordering | Phase 2 MUST complete before Phase 3 |
