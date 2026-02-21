# Agent Status Determination Analysis
## Research Report: How `claude-mpm configure` Determines "Installed" vs "Available" Status

**Date:** February 21, 2026
**Author:** Research Analysis
**Subject:** Understanding the complete code flow and architecture behind agent status determination

---

## Executive Summary

This analysis traces the complete code flow for how `claude-mpm configure` determines whether agents show as "Installed" or "Available" in the configuration interface. The research combines static code analysis with runtime debug observations to provide a comprehensive understanding of the agent discovery and status determination architecture.

**Key Findings:**
- Agent status is determined by comparing discovered agents against deployed agent detection
- Two parallel discovery methods: local JSON templates + remote Git cache
- Two parallel deployment detection methods: virtual state + physical files
- Current runtime behavior shows primary reliance on Git cache + physical file detection

---

## Code Flow Analysis

### 1. Entry Point and Command Routing

**File:** `src/claude_mpm/cli/commands/configure.py`

```
claude-mpm configure
    ↓
ConfigureCommand.run() [line 179]
    ↓
_run_interactive_tui() [line 245]
    ↓
_show_main_menu() → "Agent Management"
    ↓
_manage_agents() [line 331]
    ↓
_load_agents_with_spinner() [line 339]
```

### 2. Core Agent Loading Logic

**Method:** `_load_agents_with_spinner()` (line 399)

```python
def _load_agents_with_spinner(self) -> List[AgentConfig]:
    with self.console.status("[bold blue]Loading agents...[/bold blue]", spinner="dots"):
        # Discover agents (includes both local and remote)
        agents = self.agent_manager.discover_agents(include_remote=True)

        # Set deployment status on each agent for display
        deployed_ids = get_deployed_agent_ids()
        for agent in agents:
            agent_id = getattr(agent, "agent_id", agent.name)
            agent_leaf_name = agent_id.split("/")[-1]
            agent.is_deployed = agent_leaf_name in deployed_ids

        # Filter BASE_AGENT from display
        agents = self._filter_agent_configs(agents, filter_deployed=False)
```

**Key Insight:** Status determination happens in two phases:
1. **Discovery:** Find all available agents
2. **Status Check:** Compare against deployed agents to set `is_deployed` flag

### 3. Agent Discovery Architecture

**File:** `src/claude_mpm/cli/commands/agent_state_manager.py:SimpleAgentManager`

#### Discovery Sources

**Method:** `discover_agents(include_remote=True)` (line 99)

```python
def discover_agents(self, include_remote: bool = True) -> List[AgentConfig]:
    agents = []

    # Source 1: Local template agents
    local_agents = self._discover_local_template_agents()
    agents.extend(local_agents)

    # Source 2: Git-sourced agents
    if include_remote:
        git_agents = self._discover_git_agents()
        agents.extend(git_agents)

    agents.sort(key=lambda a: a.name)
    return agents
```

#### Source 1: Local JSON Templates

**Method:** `_discover_local_template_agents()` (line 128)
- **Location:** `src/claude_mpm/agents/templates/*.json`
- **Process:** Reads JSON template files, extracts metadata (agent_id, description, tools)
- **Creates:** AgentConfig objects with `source_type = "local"`

#### Source 2: Remote Git Cache

**Method:** `_discover_git_agents()` (line 211)
- **Location:** `~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents/*.md`
- **Process:** Uses GitSourceManager to scan cached repository
- **Creates:** AgentConfig objects with Git source information

### 4. Deployment Status Detection

**File:** `src/claude_mpm/utils/agent_filters.py`

**Method:** `get_deployed_agent_ids()` (line 87)

```python
def get_deployed_agent_ids(project_dir: Optional[Path] = None) -> Set[str]:
    deployed = set()

    # PRIMARY: Check virtual deployment state
    deployment_state_path = project_dir / ".claude/agents/.mpm_deployment_state"
    if deployment_state_path.exists():
        with deployment_state_path.open() as f:
            state = json.load(f)
        agents = state.get("last_check_results", {}).get("agents", {})
        deployed.update(agents.keys())

    # FALLBACK: Check physical .md files
    agents_dir = project_dir / ".claude/agents"
    if agents_dir.exists():
        for file in agents_dir.glob("*.md"):
            if file.stem not in {"BASE-AGENT", ".DS_Store"}:
                deployed.add(file.stem)

    return deployed
```

#### Detection Method 1: Virtual Deployment State (Primary)
- **File:** `.claude/agents/.mmp_deployment_state` (JSON)
- **Format:** `{"last_check_results": {"agents": {"agent-name": {...}}}}`
- **Purpose:** Modern virtual deployment tracking

#### Detection Method 2: Physical Files (Fallback)
- **Location:** `.claude/agents/*.md` files
- **Purpose:** Backward compatibility with legacy deployment method

### 5. Status Display Logic

**File:** `src/claude_mpm/cli/commands/configure_agent_display.py`

**Method:** `display_agents_table()` (line 56)

```python
# Get deployed agent IDs
deployed_ids = get_deployed_agent_ids()

for idx, agent in enumerate(agents, 1):
    agent_id = getattr(agent, "agent_id", agent.name)
    agent_leaf_name = agent_id.split("/")[-1]
    is_deployed = agent_leaf_name in deployed_ids

    # Show "Installed" for deployed agents, "Available" otherwise
    status = "[green]Installed[/green]" if is_deployed else "Available"
```

---

## Runtime Debug Analysis

### Observed Behavior (Feb 21, 2026)

Debug output from `claude-mpm configure --debug` reveals the **actual runtime behavior**:

#### Agent Discovery Source
```
INFO: GitSourceManager initialized with cache: /Users/mac/.claude-mpm/cache/agents
DEBUG: Found 48 Markdown files in /Users/mac/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents
INFO: Discovered 48 remote agents from claude-mpm-agents
```

**Reality:** All 48 agents are coming from **remote Git cache only**, not local JSON templates.

#### Status Detection Method
```
DEBUG: Agent ticketing found as physical file: /Users/mac/workspace/claude-mpm/.claude/agents/ticketing.md
DEBUG: Agent content-agent found as physical file: /Users/mac/workspace/claude-mpm/.claude/agents/content-agent.md
[... 15 total agents found as physical files]
```

**Reality:** Status detection is using the **fallback method** (physical .md files), not the primary virtual deployment state method.

#### Agent Source Summary
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Source                                   ┃ Status          ┃ Agents     ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ bobmatnyc/claude-mpm-agents/agents       │ ✓ Active        │ 53         │
└──────────────────────────────────────────┴─────────────────┴────────────┘
```

**Reality:** Single remote source providing all agents.

#### Final Status Count
```
✓ 15 installed | 33 available | 0 recommended | Total: 48
```

---

## Architecture Analysis

### Current System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Discovery                          │
├─────────────────────────────────────────────────────────────┤
│ Local Templates (Designed)     │ Git Cache (Active)         │
│ src/agents/templates/*.json    │ ~/.claude-mpm/cache/agents │
│ ❌ Not used in runtime         │ ✅ 48 agents discovered    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  Status Detection                          │
├─────────────────────────────────────────────────────────────┤
│ Virtual State (Designed)       │ Physical Files (Active)    │
│ .mmp_deployment_state (JSON)   │ .claude/agents/*.md        │
│ ❌ Not used in runtime         │ ✅ 15 agents detected      │
└─────────────────────────────────────────────────────────────┘
```

### Actual Runtime Flow

1. **GitSourceManager** scans `~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents/`
2. **Finds 48 .md files** with YAML frontmatter containing agent metadata
3. **Parses each agent** to create AgentConfig objects
4. **Checks physical files** in `.claude/agents/*.md` for deployment status
5. **Sets status** based on file presence: 15 "Installed", 33 "Available"

---

## Key Findings & Implications

### 1. Design vs Reality Gap

**Designed Behavior:**
- Dual discovery: Local templates + Git cache
- Modern virtual deployment state tracking

**Actual Behavior:**
- Single discovery: Git cache only
- Legacy physical file deployment detection

### 2. Why Virtual State Not Used

Possible reasons for fallback to physical files:
1. `.claude/agents/.mpm_deployment_state` doesn't exist
2. File exists but is empty/malformed
3. Project predates virtual deployment system
4. Configuration setting preferring physical files

### 3. Agent Source Centralization

All agents come from single remote source: `bobmatnyc/claude-mpm-agents`
- Simplifies maintenance and updates
- Single point of failure/dependency
- Consistent agent format and metadata

### 4. Status Detection Reliability

Physical file detection is robust but:
- Requires disk space for each agent
- Manual cleanup needed for removed agents
- No metadata about deployment state/health

---

## Technical Specifications

### Agent Configuration Object Structure

```python
class AgentConfig:
    name: str              # Display name for UI
    description: str       # Truncated description for table
    dependencies: List     # Tools/capabilities for display
    is_deployed: bool      # Set by status detection
    source_type: str       # "local" or "git"
    display_name: str      # Full display name
    agent_id: str          # Technical identifier
```

### File System Layout

```
Project Structure:
├── .claude/
│   └── agents/
│       ├── .mpm_deployment_state    # Virtual state (unused)
│       ├── ticketing.md             # Deployed agents (active)
│       ├── content-agent.md
│       └── ...
└── ~/.claude-mpm/
    └── cache/
        └── agents/
            └── bobmatnyc/
                └── claude-mpm-agents/
                    └── agents/
                        ├── ticketing.md     # Source agents
                        ├── content-agent.md
                        └── ...
```

### Status Determination Algorithm

```python
def determine_status(agent: AgentConfig, deployed_ids: Set[str]) -> str:
    agent_id = getattr(agent, "agent_id", agent.name)
    agent_leaf_name = agent_id.split("/")[-1]
    is_deployed = agent_leaf_name in deployed_ids
    return "Installed" if is_deployed else "Available"
```

---

## Recommendations

### 1. Investigation Priorities
- Determine why virtual deployment state is not active
- Verify `.claude/agents/.mpm_deployment_state` file status
- Check if local JSON templates should be used

### 2. Architecture Improvements
- Consolidate to single deployment detection method
- Add health checks for Git cache synchronization
- Implement deployment state validation

### 3. Debugging Enhancements
- Add debug logging for deployment detection method selection
- Log reasons for fallback to physical files
- Monitor Git cache update frequency

---

## Appendix: Debug Output Analysis

### GitSourceManager Initialization
```
INFO: GitSourceManager initialized with cache: /Users/mac/.claude-mpm/cache/agents
DEBUG: [DEBUG] list_cached_agents START: repo_identifier=None
DEBUG: Loaded metadata for 0 repositories
DEBUG: [DEBUG] Scanning all cached repositories
DEBUG: [DEBUG] Walking cache root: /Users/mac/.claude-mpm/cache/agents
```

Shows active Git-based agent discovery with cache at `~/.claude-mpm/cache/agents`.

### Agent Parsing Process
```
DEBUG: Using agent_id from YAML frontmatter: documentation-agent
DEBUG: Extracted collection_id: bobmatnyc/claude-mpm-agents
DEBUG: Successfully parsed remote agent: documentation.md
```

Confirms YAML frontmatter parsing from .md files in Git cache.

### Physical File Detection
```
DEBUG: Agent ticketing found as physical file: /Users/mac/workspace/claude-mpm/.claude/agents/ticketing.md
```

Shows fallback to physical file detection for deployment status.

---

**Research Complete:** This analysis provides complete understanding of agent status determination architecture, current runtime behavior, and identifies gaps between designed and actual system operation.