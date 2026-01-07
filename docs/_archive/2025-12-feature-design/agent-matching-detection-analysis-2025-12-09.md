# Agent Matching and Detection Implementation Analysis

**Research Date**: 2025-12-09
**Researcher**: Research Agent (Claude MPM)
**Scope**: Agent matching logic, file structure, collection organization, deployment flow

---

## Executive Summary

The Claude MPM agent system currently uses **filename-based matching** for agent detection and version comparison across multiple sources (system, user, remote, project). While functional, this approach has limitations when agents from different collections share similar names or when agents are reorganized within collections.

**Key Findings**:
1. ✅ **No frontmatter-based matching currently exists** - pure filename matching
2. ✅ **Frontmatter infrastructure is present** - agents already have `agent_id` field
3. ✅ **Remote agents use hierarchical paths** - but matching still relies on filename
4. ⚠️ **Collection identifier gap** - no explicit collection tracking in agent metadata
5. ⚠️ **Version comparison vulnerable** - relies on filename match to detect same agent

**Recommendation**: Implement frontmatter-based matching using `agent_id` + `collection_id` composite key for robust agent identification across sources.

---

## 1. Current Agent Matching Logic

### 1.1 Primary Matching Mechanism

**Location**: `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py`

**Current Algorithm**:
```python
# Line 376-401: Agent name extraction and matching
for agent_name, agent_info in selected_agents.items():
    # Defensive: Try multiple path fields for backward compatibility (ticket 1M-480)
    # Priority: 'path' -> 'file_path' -> 'source_file'
    path_str = (
        agent_info.get("path")
        or agent_info.get("file_path")
        or agent_info.get("source_file")
    )

    template_path = Path(path_str)
    if template_path.exists():
        # Use the file stem as the key for consistency
        file_stem = template_path.stem
        agents_to_deploy[file_stem] = template_path
        agent_sources[file_stem] = agent_info["source"]
```

**Key Observation**: Agent matching is **purely filename-based** using `template_path.stem` (filename without extension).

### 1.2 Version Comparison Logic

**Location**: `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py`

**Current Algorithm**:
```python
# Line 709-821: Version comparison
for agent_name, template_path in agents_to_deploy.items():
    deployed_file = deployed_agents_dir / f"{agent_name}.md"

    if not deployed_file.exists():
        comparison_results["new_agents"].append({
            "name": agent_name,
            "source": agent_sources[agent_name],
            "template": str(template_path),
        })
```

**Key Observation**: Comparison logic assumes `agent_name` (derived from filename) uniquely identifies agents across all sources.

### 1.3 Multi-Source Selection

**Location**: `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py`

**Current Algorithm**:
```python
# Line 192-293: Highest version selection
def select_highest_version_agents(
    self, agents_by_name: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Dict[str, Any]]:
    selected_agents = {}

    for agent_name, agent_versions in agents_by_name.items():
        # Compare versions to find the highest
        highest_version_agent = None
        highest_version_tuple = (0, 0, 0)

        for agent_info in agent_versions:
            version_str = agent_info.get("version", "0.0.0")
            version_tuple = self.version_manager.parse_version(version_str)

            if (
                self.version_manager.compare_versions(
                    version_tuple, highest_version_tuple
                )
                > 0
            ):
                highest_version_agent = agent_info
                highest_version_tuple = version_tuple
```

**Key Observation**: Version comparison groups agents by `agent_name` (from frontmatter `name` field), then selects highest version.

### 1.4 Identifier Extraction

**Location**: `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py`

**Current Algorithm**:
```python
# Line 147-163: Agent name extraction from different sources
for agent_info in agents:
    agent_name = agent_info.get("name") or agent_info.get(
        "metadata", {}
    ).get("name")
    if not agent_name:
        continue

    # Add source information
    agent_info["source"] = source_name
    agent_info["source_dir"] = str(source_dir)

    # Initialize list if this is the first occurrence of this agent
    if agent_name not in agents_by_name:
        agents_by_name[agent_name] = []

    agents_by_name[agent_name].append(agent_info)
```

**Key Observation**: Primary identifier is the `name` field from frontmatter, NOT `agent_id`.

---

## 2. Agent File Structure

### 2.1 Remote Agent Markdown Format

**Example**: `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/universal/code-analyzer.md`

```yaml
---
name: code_analysis_agent
description: Multi-language code analysis with AST parsing and Mermaid diagram visualization
version: 2.6.2
schema_version: 1.2.0
agent_id: code-analyzer  # ✅ ALREADY EXISTS - can be used for matching
agent_type: research
model: sonnet
resource_tier: standard
tags:
- code-analysis
- ast-analysis
category: research
temperature: 0.15
---
```

**Key Fields for Matching**:
- ✅ `name`: Currently used for grouping (e.g., `code_analysis_agent`)
- ✅ `agent_id`: Human-readable identifier (e.g., `code-analyzer`)
- ✅ `version`: Used for version comparison (e.g., `2.6.2`)
- ❌ `collection_id`: **MISSING** - no field tracking which collection agent belongs to

### 2.2 System Agent JSON Format

**Location**: `src/claude_mpm/agents/templates/*.json`

**Expected Format** (based on `AgentDiscoveryService`):
```json
{
  "agent_id": "hierarchical-agent-id",
  "metadata": {
    "name": "Agent Display Name",
    "description": "...",
    "version": "1.0.0",
    "author": "claude-mpm",
    "category": "research"
  },
  "model": "sonnet",
  "routing": {
    "keywords": ["keyword1"],
    "paths": ["/path/"],
    "priority": 100
  }
}
```

**Key Observation**: System templates use JSON format, while remote agents use Markdown with YAML frontmatter. Both formats support `agent_id` field.

### 2.3 Deployed Agent Format

**Location**: `.claude/agents/*.md`

**Format**: Markdown with YAML frontmatter (deployed format)

```yaml
---
name: research_agent
agent_id: research-agent
version: 4.9.0
---
```

**Key Observation**: Deployed agents preserve frontmatter fields from source, including `agent_id`.

---

## 3. Collection/Repository Structure

### 3.1 Remote Agents Cache Organization

**Structure**:
```
~/.claude-mpm/cache/remote-agents/
├── bobmatnyc/
│   └── claude-mpm-agents/
│       └── agents/
│           ├── documentation/
│           │   ├── documentation.md
│           │   └── ticketing.md
│           ├── engineer/
│           │   └── backend/
│           │       └── python-engineer.md
│           └── universal/
│               ├── code-analyzer.md
│               ├── content-agent.md
│               ├── memory-manager.md
│               └── research.md
├── claude-mpm/
├── documentation/
├── engineer/
├── ops/
├── qa/
├── security/
└── universal/
```

**Key Observations**:
1. ✅ **Repository-level organization**: `bobmatnyc/claude-mpm-agents/` identifies collection
2. ✅ **Hierarchical agent paths**: `engineer/backend/python-engineer.md`
3. ❌ **No collection ID in frontmatter**: Repository path not stored in agent metadata
4. ⚠️ **Multiple collection sources**: Could have `bobmatnyc/claude-mpm-agents/` AND `acme/custom-agents/`

### 3.2 Hierarchical ID Generation

**Location**: `src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py`

**Algorithm**:
```python
# Line 68-106: Hierarchical ID generation
def _generate_hierarchical_id(self, file_path: Path) -> str:
    """Generate hierarchical agent ID from file path.

    Example:
        Input:  /cache/bobmatnyc/claude-mpm-agents/agents/engineer/backend/python-engineer.md
        Root:   /cache/bobmatnyc/claude-mpm-agents/agents
        Output: engineer/backend/python-engineer
    """
    try:
        # Calculate relative to /agents/ subdirectory (Bug #4 fix)
        agents_dir = self.remote_agents_dir / "agents"
        relative_path = file_path.relative_to(agents_dir)

        # Remove .md extension and convert to forward slashes
        return str(relative_path.with_suffix("")).replace("\\", "/")
    except ValueError:
        # File is not under agents subdirectory, fall back to filename
        return file_path.stem
```

**Key Observations**:
1. ✅ **Hierarchical IDs generated**: `engineer/backend/python-engineer`
2. ⚠️ **Not stored in frontmatter**: Calculated at runtime, not persisted
3. ⚠️ **No collection prefix**: `engineer/backend/python-engineer` (no `bobmatnyc/` prefix)

### 3.3 Category Detection

**Location**: `src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py`

**Algorithm**:
```python
# Line 108-135: Category detection from path
def _detect_category_from_path(self, file_path: Path) -> str:
    """Detect category from file path hierarchy.

    Example:
        Input:  /cache/bobmatnyc/claude-mpm-agents/agents/engineer/backend/python-engineer.md
        Root:   /cache/bobmatnyc/claude-mpm-agents/agents
        Output: engineer/backend
    """
    try:
        agents_dir = self.remote_agents_dir / "agents"
        relative_path = file_path.relative_to(agents_dir)
        parts = relative_path.parts[:-1]  # Exclude filename
        return "/".join(parts) if parts else "universal"
    except ValueError:
        return "universal"
```

**Key Observation**: Category is derived from directory structure, stored in frontmatter `category` field.

---

## 4. Deployment Flow

### 4.1 Agent Discovery Process

**4-Tier Discovery Hierarchy** (lowest to highest priority):

1. **System Templates** (Tier 1)
   - Location: `src/claude_mpm/agents/templates/*.json`
   - Format: JSON
   - Discovery: `AgentDiscoveryService.list_available_agents()`
   - Priority: Lowest

2. **User Agents** (Tier 2) - DEPRECATED
   - Location: `~/.claude-mpm/agents/*.md`
   - Format: Markdown with YAML frontmatter
   - Discovery: `AgentDiscoveryService.list_available_agents()`
   - Priority: Low (deprecated, removal planned v5.0.0)

3. **Remote Agents** (Tier 3)
   - Location: `~/.claude-mpm/cache/remote-agents/{owner}/{repo}/agents/**/*.md`
   - Format: Markdown with YAML frontmatter
   - Discovery: `RemoteAgentDiscoveryService.discover_remote_agents()`
   - Priority: High

4. **Project Agents** (Tier 4)
   - Location: `.claude-mpm/agents/*.md`
   - Format: Markdown with YAML frontmatter
   - Discovery: `AgentDiscoveryService.list_available_agents()`
   - Priority: Highest

**Code Reference**:
```python
# src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py
# Line 112-169: Discovery from all sources

sources = [
    ("system", system_templates_dir),
    ("user", user_agents_dir),
    ("remote", remote_agents_dir),
    ("project", project_agents_dir),
]

for source_name, source_dir in sources:
    if source_dir and source_dir.exists():
        # Use appropriate discovery service based on source type
        if source_name == "remote":
            remote_service = RemoteAgentDiscoveryService(source_dir)
            agents = remote_service.discover_remote_agents()
        else:
            discovery_service = AgentDiscoveryService(source_dir)
            agents = discovery_service.list_available_agents(log_discovery=False)
```

### 4.2 Version Selection Algorithm

**Process**:
1. Group agents by `name` field from frontmatter
2. Compare versions within each group
3. Select highest version agent
4. Track source tier for logging

**Code Reference**:
```python
# Line 192-293: select_highest_version_agents()

for agent_name, agent_versions in agents_by_name.items():
    highest_version_agent = None
    highest_version_tuple = (0, 0, 0)

    for agent_info in agent_versions:
        version_str = agent_info.get("version", "0.0.0")
        version_tuple = self.version_manager.parse_version(version_str)

        if (
            self.version_manager.compare_versions(
                version_tuple, highest_version_tuple
            )
            > 0
        ):
            highest_version_agent = agent_info
            highest_version_tuple = version_tuple
```

**Warning Scenario**:
```python
# Line 263-282: Version override warnings
if version_comparison < 0:
    if (
        other_agent["source"] == "project"
        and highest_version_agent["source"] == "system"
    ):
        self.logger.warning(
            f"Project agent '{agent_name}' v{other_agent['version']} "
            f"overridden by higher system version v{highest_version_agent['version']}"
        )
```

### 4.3 Deployment Process

**Steps**:
1. **Sync remote sources**: `AgentDeploymentService._sync_remote_agent_sources()`
2. **Discover agents**: Multi-source discovery from all 4 tiers
3. **Select highest versions**: `select_highest_version_agents()`
4. **Compare with deployed**: `compare_deployed_versions()`
5. **Deploy updated agents**: Copy to `.claude/agents/`

**Metadata Preserved**:
- ✅ `name`, `agent_id`, `version`, `description`
- ✅ `category`, `tags`, `model`, `capabilities`
- ❌ `source` field (added during discovery, not in original frontmatter)
- ❌ `collection_id` (not tracked)

**Code Reference**:
```python
# Line 294-413: get_agents_for_deployment()

# Discover all available agents from 4 tiers
agents_by_name = self.discover_agents_from_all_sources(...)

# Select highest version for each agent
selected_agents = self.select_highest_version_agents(agents_by_name)

# Create deployment mappings
agents_to_deploy = {}
agent_sources = {}

for agent_name, agent_info in selected_agents.items():
    path_str = agent_info.get("path") or agent_info.get("file_path")
    template_path = Path(path_str)

    if template_path.exists():
        file_stem = template_path.stem
        agents_to_deploy[file_stem] = template_path
        agent_sources[file_stem] = agent_info["source"]
```

### 4.4 Source Origin Tracking

**Current Implementation**:
- ✅ Source tier tracked: `agent_info["source"]` = `"system"` | `"user"` | `"remote"` | `"project"`
- ✅ Source directory tracked: `agent_info["source_dir"]` = path to source directory
- ❌ Collection identity NOT tracked (no repository/owner information)

**Example**:
```python
# Line 155-157: Source annotation
agent_info["source"] = source_name  # e.g., "remote"
agent_info["source_dir"] = str(source_dir)  # e.g., "/Users/masa/.claude-mpm/cache/remote-agents"
```

**Gap**: If two collections (`bobmatnyc/claude-mpm-agents` and `acme/custom-agents`) both have `research.md` agents, the system cannot distinguish them beyond filename matching.

---

## 5. Current Implementation Gaps

### 5.1 Filename-Based Matching Limitations

**Problem**: Two agents with same filename from different collections are treated as same agent.

**Example Scenario**:
```
Collection A (bobmatnyc/claude-mpm-agents):
  agents/research/research.md
    name: research_agent
    agent_id: research-agent
    version: 4.9.0

Collection B (acme/custom-agents):
  agents/research/custom-research.md  # Different filename
    name: research_agent              # Same name
    agent_id: acme-research-agent     # Different agent_id
    version: 2.0.0
```

**Current Behavior**: Both agents would be grouped by `name: research_agent`, and v4.9.0 would win (correct).

**Edge Case Problem**:
```
Collection A (bobmatnyc/claude-mpm-agents):
  agents/research/research.md
    name: research_agent
    agent_id: research-agent
    version: 4.9.0

Collection B (acme/custom-agents):
  agents/analysis/research.md  # SAME filename
    name: custom_research_agent  # Different name (safe)
    agent_id: acme-research       # Different agent_id
    version: 5.0.0
```

**Current Behavior**: Both agents would be deployed because `name` fields differ. However, both would try to deploy to `.claude/agents/research.md`, causing a conflict.

### 5.2 Collection Identifier Absence

**Problem**: No way to explicitly identify which collection an agent belongs to.

**Missing Metadata**:
- ❌ `collection_id`: Unique identifier for agent collection (e.g., `bobmatnyc/claude-mpm-agents`)
- ❌ `collection_version`: Version of the collection itself
- ❌ `collection_url`: Source URL for tracking updates

**Impact**:
- Cannot distinguish agents from different collections with same `agent_id`
- Cannot track which collection provided the deployed agent
- Cannot implement collection-level updates or rollbacks

### 5.3 Agent Identity Ambiguity

**Current Identifier Priority**:
1. `name` field (used for grouping in multi-source selection)
2. `file_stem` (filename without extension, used for deployment)
3. `agent_id` field (exists but NOT used for matching)

**Problem**: Inconsistent identifier usage across deployment pipeline.

**Example**:
```yaml
# Agent A
name: research_agent        # Used for version comparison grouping
agent_id: research-agent    # NOT used for matching
filename: research.md       # Used for deployment filename
```

If another agent has:
```yaml
# Agent B
name: analysis_agent        # Different name (no conflict)
agent_id: research-agent    # SAME agent_id (should conflict, but doesn't)
filename: research.md       # SAME filename (WILL conflict on deployment)
```

**Current System**: Would allow both agents to be selected (different `name`), but deployment would fail (same `filename`).

### 5.4 Hierarchical ID Not Persisted

**Problem**: Hierarchical IDs are calculated at runtime but not stored in frontmatter.

**Current Flow**:
1. `RemoteAgentDiscoveryService._generate_hierarchical_id()` calculates `engineer/backend/python-engineer`
2. ID is stored in `agent_info["agent_id"]` during discovery
3. **BUT**: Original frontmatter `agent_id` (e.g., `python-engineer`) is NOT updated
4. Deployed agent retains original `agent_id`, losing hierarchy information

**Impact**:
- Hierarchy information lost after deployment
- Cannot reconstruct source path from deployed agent
- Cannot implement hierarchical filtering or routing

---

## 6. Recommended Approach for Frontmatter-Based Matching

### 6.1 Composite Key Design

**Proposed Primary Identifier**:
```
{collection_id}:{agent_id}
```

**Example**:
```yaml
# bobmatnyc/claude-mpm-agents/agents/research/research.md
collection_id: bobmatnyc/claude-mpm-agents
agent_id: research-agent
canonical_id: bobmatnyc/claude-mpm-agents:research-agent  # Auto-generated
version: 4.9.0
```

**Benefits**:
- ✅ Globally unique agent identification
- ✅ Collection-level version management
- ✅ Clear source attribution
- ✅ Supports multiple collections with overlapping agent names

### 6.2 Frontmatter Schema Enhancement

**Proposed Additions to YAML Frontmatter**:

```yaml
---
# Core Identity (REQUIRED)
name: research_agent
agent_id: research-agent
version: 4.9.0

# Collection Metadata (NEW - REQUIRED for remote agents)
collection_id: bobmatnyc/claude-mpm-agents
collection_version: 1.2.0
collection_url: https://github.com/bobmatnyc/claude-mpm-agents

# Hierarchical Organization (NEW - OPTIONAL)
hierarchical_id: research/advanced/research-agent  # Full path within collection

# Source Tracking (NEW - AUTO-POPULATED during deployment)
source_tier: remote  # system | user | remote | project
deployed_from: /Users/masa/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents
deployed_at: 2025-12-09T10:30:00Z

# Existing Fields (UNCHANGED)
description: Memory-efficient codebase analysis
category: research
tags: [research, memory-efficient]
---
```

### 6.3 Matching Algorithm Changes

**Current Algorithm** (filename-based):
```python
# Current: Match by filename stem
file_stem = template_path.stem
agents_to_deploy[file_stem] = template_path
```

**Proposed Algorithm** (frontmatter-based):
```python
# Proposed: Match by canonical_id (collection_id:agent_id)
canonical_id = f"{agent_info['collection_id']}:{agent_info['agent_id']}"
agents_to_deploy[canonical_id] = template_path

# Fallback for backward compatibility
if not agent_info.get('collection_id'):
    # Legacy agents without collection_id
    canonical_id = f"legacy:{template_path.stem}"
```

**Version Comparison Enhancement**:
```python
# Group by canonical_id instead of name
for canonical_id, agent_versions in agents_by_canonical_id.items():
    # Select highest version within same canonical_id
    highest_version_agent = max(
        agent_versions,
        key=lambda a: parse_version(a.get("version", "0.0.0"))
    )
```

### 6.4 Deployment Filename Strategy

**Problem**: Multiple collections could have agents with same `agent_id` but different `collection_id`.

**Proposed Solution**:
```
.claude/agents/{collection_slug}_{agent_id}.md
```

**Example**:
```
bobmatnyc/claude-mpm-agents:research-agent
  → .claude/agents/bobmatnyc-claude-mpm-agents_research-agent.md

acme/custom-agents:research-agent
  → .claude/agents/acme-custom-agents_research-agent.md
```

**Alternative** (shorter, hash-based):
```
.claude/agents/{agent_id}_{collection_hash}.md
```

**Example**:
```
research-agent (from bobmatnyc/claude-mpm-agents)
  → .claude/agents/research-agent_a1b2c3d4.md
```

### 6.5 Migration Path

**Phase 1: Backward Compatible Addition** (v5.1.0)
- Add `collection_id`, `collection_version`, `collection_url` to remote agent frontmatter
- Auto-populate from repository path during discovery
- Continue using filename-based matching (no breaking changes)

**Phase 2: Dual Matching** (v5.2.0)
- Implement canonical_id-based matching
- Prefer canonical_id when available, fallback to filename
- Add migration warnings for agents without collection metadata

**Phase 3: Full Transition** (v6.0.0)
- Require `collection_id` for all remote agents
- Use canonical_id as primary identifier
- Remove filename-based fallback

### 6.6 Implementation Checklist

**Step 1: Frontmatter Parsing Enhancement**
- [ ] Update `RemoteAgentDiscoveryService._parse_markdown_agent()` to extract `collection_id`
- [ ] Auto-populate `collection_id` from repository path if missing
- [ ] Generate `canonical_id` during discovery
- [ ] Store in `agent_info` dictionary

**Step 2: Matching Logic Update**
- [ ] Add `canonical_id` generation in `get_agents_for_deployment()`
- [ ] Update `select_highest_version_agents()` to group by `canonical_id`
- [ ] Implement fallback for legacy agents without `collection_id`

**Step 3: Deployment Filename Handling**
- [ ] Decide on filename strategy (prefix vs hash)
- [ ] Update `SingleAgentDeployer.deploy_single_agent()` to use new filenames
- [ ] Handle migration of existing deployed agents

**Step 4: Version Comparison Enhancement**
- [ ] Update `compare_deployed_versions()` to use `canonical_id` matching
- [ ] Add collection-level version tracking
- [ ] Implement collection update detection

**Step 5: Testing & Validation**
- [ ] Unit tests for canonical_id generation
- [ ] Integration tests for multi-collection scenarios
- [ ] Migration tests for legacy agents
- [ ] Deployment filename conflict detection

---

## 7. Code Examples

### 7.1 Current Matching Code (Filename-Based)

**Location**: `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py:376-401`

```python
for agent_name, agent_info in selected_agents.items():
    # Defensive: Try multiple path fields for backward compatibility
    path_str = (
        agent_info.get("path")
        or agent_info.get("file_path")
        or agent_info.get("source_file")
    )

    template_path = Path(path_str)
    if template_path.exists():
        # CURRENT: Use the file stem as the key for consistency
        file_stem = template_path.stem  # ⚠️ Filename-based matching
        agents_to_deploy[file_stem] = template_path
        agent_sources[file_stem] = agent_info["source"]
```

### 7.2 Proposed Matching Code (Frontmatter-Based)

```python
for agent_name, agent_info in selected_agents.items():
    # Extract canonical identifier
    collection_id = agent_info.get("collection_id")
    agent_id = agent_info.get("agent_id") or agent_info.get("name")

    # Generate canonical_id
    if collection_id:
        canonical_id = f"{collection_id}:{agent_id}"
    else:
        # Legacy fallback: use filename
        canonical_id = f"legacy:{template_path.stem}"
        logger.warning(
            f"Agent '{agent_name}' missing collection_id, using legacy matching"
        )

    # Use canonical_id as deployment key
    agents_to_deploy[canonical_id] = template_path
    agent_sources[canonical_id] = {
        "source": agent_info["source"],
        "collection_id": collection_id,
        "agent_id": agent_id,
    }

    # Store canonical_id in agent_info for deployment
    agent_info["canonical_id"] = canonical_id
```

### 7.3 Collection ID Auto-Population

**Location**: `src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py`

**Current Code** (lines 200-300):
```python
def _parse_markdown_agent(self, md_file: Path) -> Optional[Dict[str, Any]]:
    content = md_file.read_text(encoding="utf-8")

    # Extract frontmatter
    frontmatter = extract_yaml_frontmatter(content)

    # Current: No collection_id extraction
    return {
        "agent_id": agent_id,
        "metadata": {...},
        "version": version,
    }
```

**Proposed Enhancement**:
```python
def _parse_markdown_agent(self, md_file: Path) -> Optional[Dict[str, Any]]:
    content = md_file.read_text(encoding="utf-8")
    frontmatter = extract_yaml_frontmatter(content)

    # NEW: Extract or generate collection_id
    collection_id = frontmatter.get("collection_id")

    if not collection_id:
        # Auto-populate from repository path
        # Example: /cache/remote-agents/bobmatnyc/claude-mpm-agents/...
        # Extract: bobmatnyc/claude-mpm-agents
        collection_id = self._extract_collection_id_from_path(md_file)

    # Generate canonical_id
    agent_id = frontmatter.get("agent_id", md_file.stem)
    canonical_id = f"{collection_id}:{agent_id}"

    return {
        "agent_id": agent_id,
        "collection_id": collection_id,  # NEW
        "canonical_id": canonical_id,    # NEW
        "metadata": {...},
        "version": version,
    }

def _extract_collection_id_from_path(self, md_file: Path) -> str:
    """Extract collection identifier from file path.

    Example:
        /Users/masa/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/...
        → bobmatnyc/claude-mpm-agents
    """
    try:
        # Find "remote-agents" in path
        parts = md_file.parts
        remote_idx = parts.index("remote-agents")

        # Collection ID is next two parts (owner/repo)
        owner = parts[remote_idx + 1]
        repo = parts[remote_idx + 2]

        return f"{owner}/{repo}"
    except (ValueError, IndexError):
        # Fallback: use "unknown" collection
        return "unknown"
```

---

## 8. Testing Scenarios

### 8.1 Single Collection, Multiple Versions

**Scenario**: Same agent, different versions, same collection

```yaml
# bobmatnyc/claude-mpm-agents (system templates)
name: research_agent
agent_id: research-agent
collection_id: bobmatnyc/claude-mpm-agents
version: 4.0.0

# bobmatnyc/claude-mpm-agents (remote cached)
name: research_agent
agent_id: research-agent
collection_id: bobmatnyc/claude-mpm-agents
version: 4.9.0  # Higher version
```

**Expected Behavior**: Deploy v4.9.0 from remote cache.

**Matching Key**: `bobmatnyc/claude-mpm-agents:research-agent`

### 8.2 Multiple Collections, Same Agent ID

**Scenario**: Same `agent_id`, different collections

```yaml
# Collection A
name: research_agent
agent_id: research-agent
collection_id: bobmatnyc/claude-mpm-agents
version: 4.9.0

# Collection B
name: research_agent
agent_id: research-agent  # SAME agent_id
collection_id: acme/custom-agents
version: 5.0.0
```

**Expected Behavior**: Deploy BOTH agents (different canonical_ids).

**Matching Keys**:
- `bobmatnyc/claude-mpm-agents:research-agent`
- `acme/custom-agents:research-agent`

**Deployed Files**:
- `.claude/agents/bobmatnyc-claude-mpm-agents_research-agent.md`
- `.claude/agents/acme-custom-agents_research-agent.md`

### 8.3 Legacy Agent Migration

**Scenario**: Legacy agent without `collection_id`

```yaml
# Legacy agent (no collection_id)
name: custom_agent
agent_id: custom-agent
version: 1.0.0
# collection_id: <missing>
```

**Expected Behavior**: Use fallback matching with warning.

**Matching Key**: `legacy:custom-agent`

**Deployed File**: `.claude/agents/custom-agent.md` (backward compatible)

### 8.4 Collection Reorganization

**Scenario**: Agent moved within collection

```yaml
# Old location: research/research.md
hierarchical_id: research/research-agent
agent_id: research-agent
collection_id: bobmatnyc/claude-mpm-agents

# New location: analysis/advanced-research.md
hierarchical_id: analysis/advanced-research-agent
agent_id: research-agent  # SAME agent_id
collection_id: bobmatnyc/claude-mpm-agents
```

**Expected Behavior**: Recognize as same agent, update deployment.

**Matching Key**: `bobmatnyc/claude-mpm-agents:research-agent` (unchanged)

---

## 9. Performance Considerations

### 9.1 Frontmatter Parsing Overhead

**Current**: Frontmatter already parsed for `name`, `version`, `description`.

**Impact of Addition**: Minimal - extracting 3 additional fields (`collection_id`, `agent_id`, `canonical_id`).

**Mitigation**: Cache parsed frontmatter during discovery phase.

### 9.2 Canonical ID Generation

**Cost**: String concatenation + path parsing for auto-population.

**Frequency**: Once per agent during discovery (not per deployment).

**Optimization**: Pre-compute during discovery, store in `agent_info` dictionary.

### 9.3 Version Comparison Complexity

**Current**: O(n × m) where n = number of agents, m = average versions per agent.

**Proposed**: Same complexity, just different grouping key.

**No degradation expected**.

---

## 10. Related Files and Components

### 10.1 Core Discovery Services

1. **`AgentDiscoveryService`** (`src/claude_mpm/services/agents/deployment/agent_discovery_service.py`)
   - Discovers JSON templates and user/project Markdown agents
   - Extracts YAML frontmatter
   - **Modification needed**: Extract `collection_id`, generate `canonical_id`

2. **`RemoteAgentDiscoveryService`** (`src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py`)
   - Discovers remote Markdown agents from cache
   - Parses frontmatter with regex
   - **Modification needed**: Auto-populate `collection_id` from path

3. **`MultiSourceAgentDeploymentService`** (`src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py`)
   - Coordinates multi-tier discovery
   - Selects highest version agents
   - **Modification needed**: Use `canonical_id` for matching and version comparison

### 10.2 Deployment Components

1. **`AgentDeploymentService`** (`src/claude_mpm/services/agents/deployment/agent_deployment.py`)
   - Main deployment orchestrator
   - Handles deployment flow
   - **Modification needed**: Pass `canonical_id` to deployment pipeline

2. **`SingleAgentDeployer`** (`src/claude_mpm/services/agents/deployment/single_agent_deployer.py`)
   - Deploys individual agents
   - Generates deployment filenames
   - **Modification needed**: Use `canonical_id`-based filenames

### 10.3 Version Management

1. **`AgentVersionManager`** (`src/claude_mpm/services/agents/deployment/agent_version_manager.py`)
   - Parses and compares semantic versions
   - Extracts version from frontmatter
   - **No modification needed** (version parsing unchanged)

---

## 11. Conclusion

The current agent matching system is **functional but filename-dependent**, which creates potential conflicts when multiple collections contain agents with similar names. The infrastructure for frontmatter-based matching already exists (agents have `agent_id` fields), but the matching logic doesn't utilize it.

**Next Steps**:
1. ✅ **Add collection metadata** to agent frontmatter (`collection_id`, `collection_version`)
2. ✅ **Implement canonical_id generation** during agent discovery
3. ✅ **Update matching logic** to prefer canonical_id over filename
4. ✅ **Design deployment filename strategy** to prevent conflicts
5. ✅ **Test with multiple collection scenarios**

This research provides the foundation for implementing robust, collection-aware agent matching in Claude MPM v5.1.0+.

---

## Appendix A: File Inventory

**Files Analyzed**:
- ✅ `src/claude_mpm/services/agents/deployment/agent_discovery_service.py` (546 lines)
- ✅ `src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py` (364 lines)
- ✅ `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py` (900+ lines)
- ✅ `src/claude_mpm/services/agents/deployment/agent_deployment.py` (1016 lines)
- ✅ Example agent: `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/universal/research.md`

**Total Lines Analyzed**: ~3000+ lines of code

**Memory Management**: Used strategic sampling and grep-based discovery to avoid loading entire codebase.
