# Critical Bugs - Agents CLI MVP

**Status:** 🔴 **BLOCKING RELEASE**
**Date Reported:** 2025-12-01
**Reporter:** QA Agent
**Affects:** Phase 1 (Discovery) + Phase 2 (Presets)

---

## Bug #1: Agent Category Detection Completely Broken

**Priority:** P0 - CRITICAL (Blocks MVP)
**Status:** 🔴 Open
**Component:** `RemoteAgentDiscoveryService`
**Assignee:** TBD

### Problem

All agents show category as "Unknown" instead of proper hierarchical categories (engineer/backend, qa, ops, etc.).

### Impact

- Makes `--category` filtering completely useless
- Discovery UI shows all 39 agents under "Unknown"
- Cannot browse agents by role/specialization
- Phase 1 (Discovery & Browsing) **non-functional**

### Root Cause

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py:94`

```python
# WRONG: Only searches immediate directory
md_files = list(self.remote_agents_dir.glob("*.md"))
```

This doesn't recursively search subdirectories. Agents are organized hierarchically:

```
agents/
  engineer/backend/python-engineer.md
  engineer/frontend/react-engineer.md
  qa/qa.md
  ops/ops.md
```

But discovery only finds `*.md` in immediate directory, losing hierarchy context.

### Reproduction

```bash
claude-mpm agents discover
# All agents show under "Unknown" category

claude-mpm agents discover --category engineer/backend
# Returns 0 results (should return 7+ agents)
```

### Expected Behavior

```
📚 Agents from configured sources (39 matching filters):

Engineering/Backend
  • engineer/backend/python-engineer
    Source: bobmatnyc/claude-mpm-agents (priority: 100)
  • engineer/backend/rust-engineer
    Source: bobmatnyc/claude-mpm-agents (priority: 100)

QA
  • qa/qa
    Source: bobmatnyc/claude-mpm-agents (priority: 100)
  • qa/web-qa
    Source: bobmatnyc/claude-mpm-agents (priority: 100)
```

### Actual Behavior

```
📚 Agents from configured sources (39 matching filters):

Unknown
  • agent-repository-reorganization-plan
    Source: remote (priority: unknown)
  • python-engineer
    Source: remote (priority: unknown)
  [... all 39 agents under "Unknown" ...]
```

### Suggested Fix

**Option A: Recursive Discovery (Recommended)**

```python
def discover_remote_agents(self) -> List[Dict[str, Any]]:
    """Discover all remote agents from cache directory."""
    agents = []

    if not self.remote_agents_dir.exists():
        return agents

    # CHANGE: Recursively find all Markdown files
    md_files = list(self.remote_agents_dir.rglob("*.md"))  # rglob instead of glob

    for md_file in md_files:
        try:
            # Extract category from path relative to agents root
            agent_dict = self._parse_markdown_agent(md_file)
            if agent_dict:
                # Add category from file path
                category = self._extract_category_from_path(md_file)
                agent_dict["category"] = category
                agents.append(agent_dict)
        except Exception as e:
            self.logger.warning(f"Failed to parse {md_file.name}: {e}")

    return agents

def _extract_category_from_path(self, md_file: Path) -> str:
    """Extract category from file path.

    Example:
        agents/engineer/backend/python-engineer.md → engineer/backend
        agents/qa/qa.md → qa
        agents/universal/research.md → universal
    """
    # Find 'agents/' in path
    parts = md_file.parts
    agents_index = None
    for i, part in enumerate(parts):
        if part == "agents":
            agents_index = i
            break

    if agents_index is None:
        return "unknown"

    # Get parts between 'agents/' and filename
    category_parts = parts[agents_index + 1:-1]

    if not category_parts:
        return "unknown"

    return "/".join(category_parts)
```

**Option B: Change Discovery Call Site**

Call discovery once from agents root, not from each subdirectory.

### Testing

After fix, verify:

```bash
# Should show categories
claude-mpm agents discover

# Should return 7+ agents
claude-mpm agents discover --category engineer/backend

# Should work with multiple filters
claude-mpm agents discover --language python --category engineer/backend
```

---

## Bug #2: Source Attribution Broken

**Priority:** P1 - HIGH (Blocks Phase 1)
**Status:** 🔴 Open
**Component:** `GitSourceManager`
**Assignee:** TBD

### Problem

All agents show:
- Source as "remote" instead of repository name ("bobmatnyc/claude-mpm-agents")
- Priority as "unknown" instead of configured value (100)

### Impact

- Users can't see which repository agents come from
- Priority information lost (needed for conflict resolution)
- Multi-source scenarios broken
- Discovery output looks unprofessional

### Root Cause

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/git_source_manager.py:294-318`

`_discover_agents_in_directory()` adds `repository` field but not `source` or `priority`:

```python
def _discover_agents_in_directory(
    self, directory: Path, repo_identifier: str
) -> List[Dict[str, Any]]:
    """Discover agents in a specific directory."""
    try:
        discovery_service = RemoteAgentDiscoveryService(directory)
        discovered = discovery_service.discover_remote_agents()

        # Add repository identifier to each agent
        for agent in discovered:
            agent["repository"] = repo_identifier  # ✅ Added
            # MISSING: agent["source"] = repo_identifier
            # MISSING: agent["priority"] = <from config>

        return discovered
```

### Reproduction

```bash
claude-mpm agents discover
# All agents show "Source: remote (priority: unknown)"
```

### Expected Behavior

```
• python-engineer
  Source: bobmatnyc/claude-mpm-agents (priority: 100)
```

### Actual Behavior

```
• python-engineer
  Source: remote (priority: unknown)
```

### Suggested Fix

```python
def _discover_agents_in_directory(
    self, directory: Path, repo_identifier: str
) -> List[Dict[str, Any]]:
    """Discover agents in a specific directory."""
    try:
        discovery_service = RemoteAgentDiscoveryService(directory)
        discovered = discovery_service.discover_remote_agents()

        # Load configuration to get priority
        from ...config.agent_sources import AgentSourceConfiguration
        sources_config = AgentSourceConfiguration()
        source_info = sources_config.get_source(repo_identifier)
        priority = source_info.get("priority", 100) if source_info else 100

        # Enrich agent metadata with source info
        for agent in discovered:
            agent["repository"] = repo_identifier
            agent["source"] = repo_identifier      # ADD THIS
            agent["priority"] = priority            # ADD THIS

        return discovered
```

### Testing

After fix, verify:

```bash
claude-mpm agents discover
# Should show: Source: bobmatnyc/claude-mpm-agents (priority: 100)

claude-mpm agents discover --format json
# Verify JSON has correct "source" and "priority" fields
```

---

## Bug #3: Agent IDs Missing Hierarchy

**Priority:** P0 - CRITICAL (Blocks Phase 1 + 2)
**Status:** 🔴 Open
**Component:** `RemoteAgentDiscoveryService`
**Assignee:** TBD

### Problem

Agent IDs generated from agent name only:
- Generated: `python-engineer`
- Expected: `engineer/backend/python-engineer`

Loses hierarchical structure needed for filtering and preset matching.

### Impact

- **Phase 2 completely broken:** Presets can't find agents (reference `engineer/backend/python-engineer`)
- AUTO-DEPLOY-INDEX.md matching fails (uses hierarchical IDs)
- Filter matching broken
- MVP **cannot ship** without this fix

### Root Cause

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py:190-198`

```python
# WRONG: Generates flat ID from name
agent_id = name.lower()
agent_id = agent_id.replace(" ", "-").replace("_", "-")
agent_id = re.sub(r"[^a-z0-9-]+", "", agent_id)
# Result: "python-engineer" ❌
```

Should use file path to preserve hierarchy:
- File: `agents/engineer/backend/python-engineer.md`
- ID: `engineer/backend/python-engineer` ✅

### Reproduction

```bash
claude-mpm agents discover --format json | jq '.agents[0].agent_id'
# Shows: "python-engineer"
# Expected: "engineer/backend/python-engineer"

claude-mpm agents deploy --preset python-dev --dry-run
# Will fail to find agents (preset references hierarchical IDs)
```

### Expected Behavior

```json
{
  "agent_id": "engineer/backend/python-engineer",
  "name": "Python Engineer",
  "category": "engineer/backend"
}
```

### Actual Behavior

```json
{
  "agent_id": "python-engineer",
  "name": "Python Engineer",
  "category": "unknown"
}
```

### Suggested Fix

```python
def _parse_markdown_agent(self, md_file: Path) -> Optional[Dict[str, Any]]:
    """Parse Markdown agent file and convert to JSON template format."""
    # ... existing code for name, description, etc. ...

    # CHANGE: Generate agent_id from file path, not name
    agent_id = self._generate_agent_id_from_path(md_file)

    # ... rest of code ...

def _generate_agent_id_from_path(self, md_file: Path) -> str:
    """Generate hierarchical agent_id from file path.

    Examples:
        agents/engineer/backend/python-engineer.md → engineer/backend/python-engineer
        agents/qa/qa.md → qa/qa
        agents/universal/research.md → universal/research

    Args:
        md_file: Path to agent markdown file

    Returns:
        Hierarchical agent ID
    """
    # Find 'agents/' in path
    path_parts = md_file.parts
    agents_index = None
    for i, part in enumerate(path_parts):
        if part == "agents":
            agents_index = i
            break

    if agents_index is None:
        # Fallback: use filename only
        return md_file.stem

    # Get path from agents/ onwards
    relative_parts = path_parts[agents_index + 1:-1]  # Skip 'agents/' and get dirs
    filename_base = md_file.stem  # Filename without .md

    # Build hierarchical ID
    if relative_parts:
        return "/".join(relative_parts) + "/" + filename_base
    else:
        return filename_base
```

### Testing

After fix, verify:

```bash
# Verify hierarchical IDs
claude-mpm agents discover --format json | jq '.agents[] | {id: .agent_id, cat: .category}'

# Should show:
# {"id": "engineer/backend/python-engineer", "cat": "engineer/backend"}
# {"id": "qa/qa", "cat": "qa"}
# {"id": "universal/research", "cat": "universal"}

# Test preset deployment
claude-mpm agents deploy --preset python-dev --dry-run
# Should successfully match agents
```

---

## Fix Priority & Timeline

| Bug | Priority | Estimated Fix Time | Blocks |
|-----|----------|-------------------|--------|
| #3: Agent IDs | P0 | 1-2 hours | Phase 1 + Phase 2 |
| #1: Categories | P0 | 2-3 hours | Phase 1 |
| #2: Source Info | P1 | 1 hour | Phase 1 UX |

**Total Estimated Fix Time:** 4-6 hours

**Suggested Fix Order:**
1. Fix Bug #3 first (enables preset testing)
2. Fix Bug #1 (enables category filtering)
3. Fix Bug #2 (improves UX)

---

## Testing After Fixes

**Smoke Test:**
```bash
# 1. Verify categories
claude-mpm agents discover
# Should show Engineering/Backend, QA, Ops, etc.

# 2. Verify agent IDs
claude-mpm agents discover --format json | jq '.agents[0]'
# Should show hierarchical agent_id and category

# 3. Verify source info
claude-mpm agents discover --verbose
# Should show: bobmatnyc/claude-mpm-agents (priority: 100)

# 4. Verify category filtering
claude-mpm agents discover --category engineer/backend
# Should return 7+ agents

# 5. Verify preset deployment
claude-mpm agents deploy --preset python-dev --dry-run
# Should find all agents in preset
```

**Full Test Plan:**
- Run complete TEST_EXECUTION_REPORT test plan
- Execute all 32 test cases
- Verify all success criteria met

---

## Dependencies

**Blocked Issues:**
- Phase 2 preset deployment completely blocked by Bug #3
- Phase 1 category filtering blocked by Bug #1
- All integration tests blocked until all bugs fixed

**Testing Blocked:**
- 31 of 32 test cases blocked by these 3 bugs
- Cannot proceed with full QA until fixed

---

## Notes

**Why These Bugs Exist:**

The codebase was originally designed for flat agent structure:
```
agents/
  python-engineer.md
  react-engineer.md
  qa.md
```

But the repository was reorganized to hierarchical structure:
```
agents/
  engineer/backend/python-engineer.md
  engineer/frontend/react-engineer.md
  qa/qa.md
```

Discovery code was never updated to handle hierarchy. Integration tests would have caught this.

**Lessons Learned:**
- Need integration tests for hierarchical agent structure
- Need validation that agent IDs match AUTO-DEPLOY-INDEX.md
- Need tests that verify discovery against actual repository structure
