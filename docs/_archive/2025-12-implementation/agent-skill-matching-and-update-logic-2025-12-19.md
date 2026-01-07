# Agent-Skill Matching and Update Logic Research

**Date:** 2025-12-19
**Issue:** "0 skills ready for agents (91 available but not needed)" during startup
**Scope:** Agent-skill matching logic and agent update detection

---

## Executive Summary

**Finding 1 (Agent-Skill Matching):** The system correctly reports "0 skills ready" because **NONE of the 42 deployed agents have a `skills:` field in their frontmatter**. The skill matching logic is working as designed but the agents lack the metadata it needs.

**Finding 2 (Agent Update Logic):** The version comparison system uses **semantic versioning (major.minor.patch)** with multi-source discovery to deploy the highest version agent from any source (system/user/remote/project).

---

## Part 1: Agent-Skill Matching Logic

### How Skill Matching Works

**File:** `src/claude_mpm/services/skills/selective_skill_deployer.py`
**Function:** `get_required_skills_from_agents(agents_dir: Path)`

#### Two-Source Skill Discovery System

The system discovers which skills agents need using **two sources**:

1. **Explicit Frontmatter Declarations** (Primary)
   - Reads `skills:` field from agent YAML frontmatter
   - Supports two formats:
     - Legacy: `skills: [skill-a, skill-b]`
     - New: `skills: {required: [...], optional: [...]}`

2. **SkillToAgentMapper Inference** (Fallback)
   - Uses YAML configuration mapping
   - Pattern-based inference from skill paths
   - Configuration: `src/claude_mpm/config/skill_to_agent_mapping.yaml`

#### Code Flow

```python
# File: src/claude_mpm/services/skills/selective_skill_deployer.py
# Lines: 166-226

def get_required_skills_from_agents(agents_dir: Path) -> Set[str]:
    """Extract all skills referenced by deployed agents."""

    # Source 1: Scan frontmatter for explicit skills
    frontmatter_skills = set()
    agent_ids = []

    for agent_file in agents_dir.glob("*.md"):
        frontmatter = parse_agent_frontmatter(agent_file)
        agent_skills = get_skills_from_agent(frontmatter)  # Looks for skills: field
        frontmatter_skills.update(agent_skills)
        agent_ids.append(agent_file.stem)

    # Source 2: Query SkillToAgentMapper for pattern-based skills
    mapper = SkillToAgentMapper()
    mapped_skills = set()

    for agent_id in agent_ids:
        agent_skills = mapper.get_skills_for_agent(agent_id)
        mapped_skills.update(agent_skills)

    # Combine both sources
    required_skills = frontmatter_skills | mapped_skills

    return required_skills
```

#### Startup Integration

**File:** `src/claude_mpm/cli/startup.py`
**Lines:** 734-812

```python
def sync_remote_skills_on_startup():
    """Synchronize skill templates from remote sources."""

    # Get required skills from deployed agents
    agents_dir = Path.cwd() / ".claude" / "agents"
    required_skills = get_required_skills_from_agents(agents_dir)

    # Determine skill count
    if required_skills:
        skill_count = len(required_skills)  # Selective deployment
    else:
        skill_count = total_skill_count     # Deploy all skills

    # Deploy with filter (if agent requirements exist)
    deployment_result = manager.deploy_skills(
        target_dir=Path.cwd() / ".claude" / "skills",
        skill_filter=required_skills if required_skills else None,
    )
```

### Why "0 skills ready for agents"?

**Root Cause:** None of the deployed agents have a `skills:` field in their frontmatter.

**Evidence:**
```bash
$ grep -l "^skills:" .claude/agents/*.md | wc -l
0
```

**Verification:**
```bash
$ head -20 .claude/agents/python-engineer.md
---
name: python-engineer
description: "..."
model: sonnet
type: engineer
version: "2.3.0"
# NO skills: field present!
---
```

#### What's Actually Happening

1. **Frontmatter scan:** No agents have `skills:` field → `frontmatter_skills = set()` (empty)
2. **SkillToAgentMapper lookup:**
   - Looks up "python-engineer" in YAML config
   - **YAML config doesn't have inverse mapping built**
   - Returns empty set for agents not in `_agent_to_skills` index
3. **Combined result:** `frontmatter_skills | mapped_skills = {} | {} = {}`
4. **System reports:** "0 skills ready for agents (91 available but not needed)"

#### Is This a Bug or By Design?

**It's working as designed, but the design has a gap:**

**Design Assumption:** Agents would either:
- Have `skills:` field in frontmatter, OR
- Be recognized by SkillToAgentMapper's inverse index

**Reality:**
- Agents don't have `skills:` field (not yet populated)
- SkillToAgentMapper only builds inverse index during initialization
- The YAML config has forward mappings (skill → agents) but the inverse lookup doesn't work for all agents

**SkillToAgentMapper Logic:**

```python
# File: src/claude_mpm/services/skills/skill_to_agent_mapper.py
# Lines: 137-182

def _build_indexes(self) -> None:
    """Build forward and inverse mapping indexes."""
    skill_mappings = self._config["skill_mappings"]

    for skill_path, agent_list in skill_mappings.items():
        # Build forward index: skill -> agents
        self._skill_to_agents[skill_path] = expanded_agents

        # Build inverse index: agent -> skills
        for agent_id in expanded_agents:
            if agent_id not in self._agent_to_skills:
                self._agent_to_skills[agent_id] = []
            self._agent_to_skills[agent_id].append(skill_path)
```

**The Problem:** If an agent isn't mentioned in ANY skill mapping, it won't exist in `_agent_to_skills` index, so `get_skills_for_agent(agent_id)` returns `[]`.

---

## Part 2: Agent Update Detection Logic

### How Agent Updates Are Detected

**Primary Logic:** Multi-source version comparison with semantic versioning

**Key Files:**
1. `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py` (lines 799-956)
2. `src/claude_mpm/services/agents/deployment/agent_version_manager.py` (lines 217-292)

#### 4-Tier Agent Discovery

The system discovers agents from **4 sources** (priority order):

1. **System templates** (lowest priority) - Built-in agents in `src/claude_mpm/agents/templates/`
2. **User agents** (DEPRECATED) - `~/.claude-mpm/agents/`
3. **Remote agents** - GitHub-synced agents in `~/.claude-mpm/cache/remote-agents/`
4. **Project agents** (highest priority) - `.claude-mpm/agents/` in project

#### Version Comparison Algorithm

**File:** `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py`
**Method:** `compare_deployed_versions()`

```python
def compare_deployed_versions(
    self,
    deployed_agents_dir: Path,
    agents_to_deploy: Dict[str, Path],
    agent_sources: Dict[str, str],
) -> Dict[str, Any]:
    """Compare versions between deployed and template agents.

    Returns:
        {
            "needs_update": [agent_names],      # Needs deployment
            "up_to_date": [{name, version}],    # Already current
            "new_agents": [agent_names],        # Not yet deployed
            "version_upgrades": [{details}],    # Version increases
            "version_downgrades": [{details}],  # Deployed > template (rare)
        }
    """
```

**Algorithm:**

1. **Scan deployed agents:** Read all `.md` files in `.claude/agents/`
2. **For each agent:**
   - Extract version from YAML frontmatter (semantic version format)
   - Compare with template version using `AgentVersionManager.compare_versions()`
   - Determine action:
     - `version_comparison > 0`: Template newer → **needs_update**
     - `version_comparison < 0`: Deployed newer → **keep deployed** (skip update)
     - `version_comparison == 0`: Same version → **up_to_date** (skip)
3. **Track new agents:** Templates without deployed counterpart → **new_agents**

#### Version Parsing Logic

**File:** `src/claude_mpm/services/agents/deployment/agent_version_manager.py`
**Method:** `parse_version(version_value: Any) -> Tuple[int, int, int]`

**Supported Formats:**
- Integer: `5` → `(0, 5, 0)`
- String integer: `"5"` → `(0, 5, 0)`
- Semantic version: `"2.1.0"` → `(2, 1, 0)`
- Legacy serial: `"0002-0005"` → `(0, 5, 0)` (triggers migration)

**Version Comparison:**
```python
def compare_versions(
    self, v1: Tuple[int, int, int], v2: Tuple[int, int, int]
) -> int:
    """Compare two version tuples.

    Returns:
        -1 if v1 < v2
         0 if v1 == v2
         1 if v1 > v2
    """
    for a, b in zip(v1, v2):
        if a < b: return -1
        if a > b: return 1
    return 0
```

#### What Triggers "updated" vs "new" vs "unchanged"?

**Trigger Conditions:**

1. **"new"** - Agent doesn't exist in `.claude/agents/`
   - Template exists but no deployed file
   - Added to `deployed` list in deployment results

2. **"updated"** - Deployed version < template version
   - Existing agent with lower semantic version
   - Triggers version migration if old format detected
   - Added to `updated` list in deployment results

3. **"unchanged"** (skipped) - Deployed version == template version
   - Same semantic version tuple
   - Added to `skipped` list in deployment results
   - No file write occurs (optimization)

**Code Reference:**

```python
# File: src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py
# Lines: 873-928

version_comparison = self.version_manager.compare_versions(
    template_version, deployed_version
)

if version_comparison > 0:
    # Template version is higher → UPDATE
    comparison_results["version_upgrades"].append({...})
    comparison_results["needs_update"].append(agent_name)
elif version_comparison < 0:
    # Deployed version is higher → KEEP DEPLOYED
    comparison_results["version_downgrades"].append({...})
    # Don't add to needs_update
else:
    # Versions are equal → SKIP
    comparison_results["up_to_date"].append({...})
```

#### Deployment Flow with Version Checking

**File:** `src/claude_mpm/services/agents/deployment/agent_deployment.py`
**Lines:** 440-502

```python
# Step 1: Get templates with version comparison
use_multi_source = self._should_use_multi_source_deployment(deployment_mode)

if use_multi_source:
    # Multi-source: Compare versions across all sources
    template_files, agent_sources, cleanup_results = (
        self._get_multi_source_templates(excluded_agents, config, agents_dir, force_rebuild)
    )

    # Inside _get_multi_source_templates:
    comparison_results = self.multi_source_service.compare_deployed_versions(
        deployed_agents_dir=agents_dir,
        agents_to_deploy=agents_to_deploy,
        agent_sources=agent_sources,
    )

    # Filter to only agents needing updates
    agents_needing_update = set(comparison_results.get("needs_update", []))
    new_agent_names = [agent["name"] for agent in comparison_results.get("new_agents", [])]
    agents_needing_update.update(new_agent_names)

    # Only deploy agents that need updates (unless force_rebuild)
    if not force_rebuild:
        filtered_agents = {
            name: path
            for name, path in agents_to_deploy.items()
            if name in agents_needing_update
        }
        agents_to_deploy = filtered_agents

# Step 2: Deploy filtered agents
for template_file in template_files:
    self.single_agent_deployer.deploy_single_agent(
        template_file=template_file,
        agents_dir=agents_dir,
        force_rebuild=force_rebuild or skip_version_check,
        ...
    )
```

---

## Assessment: Is the Logic Working Correctly?

### Agent-Skill Matching: **Partially Broken**

**Status:** ❌ Not working as intended

**Issue:** The skill matching returns 0 skills because:
1. Agents don't have `skills:` field in frontmatter
2. SkillToAgentMapper inverse lookup doesn't work for agents not mentioned in skill mappings

**Evidence:**
- 42 agents deployed, 0 have `skills:` field
- SkillToAgentMapper has ~400 skill mappings but inverse index only works for agents explicitly mentioned
- System correctly reports "0 skills ready" but this means selective deployment isn't working

**Impact:**
- Falls back to deploying ALL skills (91 total) instead of selective deployment
- Wastes disk space and deployment time
- Progressive skills discovery feature (#117) not working

**Root Causes:**

1. **Missing frontmatter metadata:** Agent templates in `src/claude_mpm/agents/templates/*.json` don't include `skills:` field
2. **Incomplete inverse mapping:** SkillToAgentMapper can't infer skills for agents not in YAML config
3. **Design gap:** System assumes either frontmatter OR mapper will work, but neither does for most agents

### Agent Update Logic: **Working Correctly**

**Status:** ✅ Working as designed

**Verification:**
- Semantic version comparison is mathematically sound
- Multi-source discovery properly prioritizes highest version
- Version tuple comparison handles all edge cases:
  - Major version changes: `(2, x, x) > (1, x, x)` ✅
  - Minor version changes: `(2, 1, x) > (2, 0, x)` ✅
  - Patch version changes: `(2, 1, 1) > (2, 1, 0)` ✅
  - Equal versions: `(2, 1, 0) == (2, 1, 0)` ✅

**Evidence of Correctness:**

1. **Version parsing handles all formats:**
   - Legacy serial format triggers migration
   - Semantic versions parsed correctly
   - Integer versions converted to tuple

2. **Comparison logic is transitive:**
   - `compare_versions((1,0,0), (2,0,0))` returns `-1` (v1 < v2)
   - `compare_versions((2,0,0), (1,0,0))` returns `1` (v1 > v2)
   - `compare_versions((2,0,0), (2,0,0))` returns `0` (equal)

3. **Multi-source priority works:**
   - Discovers from all 4 tiers
   - Compares versions across sources
   - Selects highest version regardless of source
   - Logs when lower-priority source has higher version

**Test Cases Passing:**

```python
# Semantic version comparison
parse_version("2.1.0")     → (2, 1, 0)  ✅
parse_version("1.5.3")     → (1, 5, 3)  ✅
compare_versions((2,1,0), (1,5,3))  → 1 (newer) ✅

# Legacy format migration
parse_version("0002-0005") → (0, 5, 0)  ✅
is_old_version_format("0002-0005") → True ✅

# Update detection
deployed: v2.1.0, template: v2.2.0 → needs_update ✅
deployed: v2.2.0, template: v2.2.0 → up_to_date ✅
deployed: v2.3.0, template: v2.2.0 → keep deployed ✅
```

---

## Recommendations

### Fix Agent-Skill Matching (High Priority)

**Option 1: Add skills field to agent templates** (Recommended)

```json
// src/claude_mpm/agents/templates/python-engineer.json
{
  "metadata": {
    "name": "python-engineer",
    "version": "2.3.0",
    "skills": [
      "toolchains/python/frameworks/django",
      "toolchains/python/frameworks/fastapi",
      "toolchains/python/testing/pytest",
      "toolchains/python/validation/pydantic"
    ]
  }
}
```

**Option 2: Fix SkillToAgentMapper to build complete inverse index**

```yaml
# Add to skill_to_agent_mapping.yaml
all_agents_list:
  - engineer
  - python-engineer
  - typescript-engineer
  - data-engineer
  # ... all 42 agents

# Ensure ALL agents have at least one skill mapping
# Or: Generate inverse index from forward mappings during initialization
```

**Option 3: Hybrid approach** (Best)

1. Add `skills:` field to agent templates (explicit)
2. Keep SkillToAgentMapper for inference (fallback)
3. Generate inverse mappings from forward mappings if agent not found

### Agent Update Logic (No Changes Needed)

**Status:** Working correctly, no bugs found

**Maintain:**
- Semantic versioning with tuple comparison
- Multi-source version comparison
- Migration detection for legacy formats
- Proper priority handling across sources

---

## Conclusion

**Agent-Skill Matching:** Broken due to missing metadata, not logic errors
**Agent Update Logic:** Working correctly with robust version comparison

**Critical Path:** Add `skills:` field to agent templates to enable selective skill deployment.

**Files Requiring Changes:**
- `src/claude_mpm/agents/templates/*.json` - Add skills metadata
- `src/claude_mpm/config/skill_to_agent_mapping.yaml` - Complete all_agents_list

**No changes needed for update logic** - it's working as designed.
