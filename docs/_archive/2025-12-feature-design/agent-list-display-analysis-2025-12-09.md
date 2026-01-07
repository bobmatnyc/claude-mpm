# Agent List Display Analysis

**Research Date**: 2025-12-09
**Issue**: "This list is now not correct" - agent display inconsistency
**Researcher**: Research Agent

## Executive Summary

The agent list display shows **hierarchical agent IDs** (e.g., `engineer/backend/python-engineer`) but the deployed filenames use **flattened leaf names** (e.g., `python-engineer.md`). This creates a mismatch between what users see in the `agents discover` output and what they expect to find in `.claude/agents/`.

**Key Finding**: The issue is NOT in the display itself, but in understanding the relationship between:
1. **Agent ID** (hierarchical path for organization/discovery): `engineer/backend/python-engineer`
2. **Deployed Filename** (flattened for Claude Code): `python-engineer.md`
3. **Display Name** (human-readable): `Python Engineer`

## Current Behavior

### `agents discover` Command Output

**Table Format** (from `agents_discover.py`):
```
Engineering/Backend
  • engineer/backend/python-engineer
    Source: bobmatnyc/claude-mpm-agents (priority: 100)
```

**JSON Format**:
```json
{
  "agent_id": "engineer/backend/python-engineer",
  "source": "bobmatnyc/claude-mpm-agents",
  "priority": 100,
  "category": "engineer/backend",
  "version": "unknown",
  "description": "## Identity\nPython 3.12-3.13 specialist..."
}
```

### Hierarchical ID Generation

**Source**: `RemoteAgentDiscoveryService._generate_hierarchical_id()`
**Location**: `src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py:156-194`

```python
def _generate_hierarchical_id(self, file_path: Path) -> str:
    """Generate hierarchical agent ID from file path.

    Example:
        Input:  /cache/bobmatnyc/claude-mpm-agents/agents/engineer/backend/python-engineer.md
        Root:   /cache/bobmatnyc/claude-mpm-agents/agents
        Output: engineer/backend/python-engineer
    """
    agents_dir = self.remote_agents_dir / "agents"
    relative_path = file_path.relative_to(agents_dir)
    return str(relative_path.with_suffix("")).replace("\\", "/")
```

**Purpose**: Preserve directory hierarchy for category-based filtering and organization.

### Deployment Behavior

**Cache Location**:
```
~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/
├── engineer/
│   ├── backend/
│   │   ├── python-engineer.md    # Hierarchical storage
│   │   ├── golang-engineer.md
│   │   └── rust-engineer.md
│   └── frontend/
│       └── react-engineer.md
└── qa/
    └── qa.md
```

**Deployed Location** (expected):
```
.claude/agents/
├── python-engineer.md    # Flattened deployment
├── golang-engineer.md
├── react-engineer.md
└── qa.md
```

## Analysis of Display Components

### 1. Agent Listing Service

**File**: `src/claude_mpm/services/cli/agent_listing_service.py`

**AgentInfo Dataclass**:
```python
@dataclass
class AgentInfo:
    name: str           # Display name: "Python Engineer"
    type: str           # "agent"
    tier: str           # "system", "user", "project"
    path: str           # Full file path
    description: Optional[str] = None
    specializations: Optional[List[str]] = None
    version: Optional[str] = None
    deployed: bool = False
    active: bool = True
    overridden_by: Optional[List[str]] = None
```

**Key Methods**:
- `list_system_agents()`: Lists available agent templates from cache
- `list_deployed_agents()`: Lists agents actually deployed to `.claude/agents/`
- `list_agents_by_tier()`: Groups agents by project/user/system tiers

### 2. Agent Output Formatter

**File**: `src/claude_mpm/services/cli/agent_output_formatter.py`

**Table Format Headers** (lines 508-534):
```python
# Verbose mode:
headers = ["Name", "Version", "Tier", "Description", "Path"]

# Normal mode:
headers = ["Name", "Version", "Description"]

# Quiet mode:
headers = ["Name"]
```

**No "Agent ID" or "Status" columns in current implementation.**

### 3. Discover Command Display

**File**: `src/claude_mpm/cli/commands/agents_discover.py`

**Table Output** (lines 147-153):
```python
for agent in sorted(category_agents, key=lambda a: a.get("agent_id", "")):
    agent_id = agent.get("agent_id", "unknown")
    source = agent.get("source", agent.get("repository", "unknown"))
    priority = agent.get("priority", "unknown")

    # Agent ID line
    console.print(f"  • [bold]{agent_id}[/bold]")
```

**Displays**: Hierarchical agent_id (`engineer/backend/python-engineer`)

## What's "Not Correct"?

Based on the user's statement **"Agent ID: engineer/backend/python-engineer (hierarchical path), Name: Python Engineer, Source: MPM Agents, Status: Available"**, they're seeing a display with these columns:

1. **Agent ID** - Shows hierarchical path
2. **Name** - Shows human-readable name
3. **Source** - Shows repository source
4. **Status** - Shows deployment status

**This display format does NOT exist in current codebase.** Possible explanations:

### Hypothesis 1: User is Looking at Different Output

The user may be running a different command that produces this format. Let me check slash commands:

**Slash Command**: `/mpm-agents-list`
**Implementation**: `src/claude_mpm/commands/mpm-agents-list.md`
**CLI Mapping**: Runs `claude-mpm agents list --deployed`

### Hypothesis 2: Recent Code Changes

The user's git status shows recent commits about agent display:
```
c635ed92 • 40 minutes ago • fix(ui): show actual deployment state...
89e45938 • 49 minutes ago • fix(ui): show actual deployment state...
```

These commits may have introduced or changed the display format.

### Hypothesis 3: Display During Startup

The agent sync/deployment process shows progress:
```
Syncing agents 46/46 (100%) - universal/research.md
Deploying agents 41/41 (100%)
```

This may show agent IDs during deployment, creating confusion.

## The Real Issue

The core confusion stems from **three different identifier types**:

1. **Hierarchical Agent ID** (`engineer/backend/python-engineer`)
   - Used for: Discovery, filtering, organization
   - Shown in: `agents discover` output
   - Purpose: Semantic categorization

2. **Deployed Filename** (`python-engineer.md`)
   - Used for: Claude Code agent discovery
   - Location: `.claude/agents/`
   - Purpose: Flat namespace for runtime loading

3. **Display Name** (`Python Engineer`)
   - Used for: Human-readable identification
   - Shown in: Agent metadata
   - Purpose: User-friendly presentation

**The "incorrectness"** likely refers to showing hierarchical IDs when users expect to see either:
- Flattened leaf names (what's actually deployed)
- Display names (what's human-readable)

## Recommendations

### 1. Clarify Display Intent

**Current behavior** (CORRECT for discovery):
```
Engineering/Backend
  • engineer/backend/python-engineer
    Source: bobmatnyc/claude-mpm-agents (priority: 100)
```

**What users may expect** (deployed filename):
```
Engineering/Backend
  • python-engineer
    Source: bobmatnyc/claude-mpm-agents (priority: 100)
    Deployed: .claude/agents/python-engineer.md
```

### 2. Add Deployment Status Column

For `agents list --deployed`, show:
```
Agent ID               | Name            | Source       | Status   | Deployed File
---------------------- | --------------- | ------------ | -------- | ---------------------
engineer/backend/...   | Python Engineer | MPM Agents   | Active   | python-engineer.md
```

### 3. Distinguish Between Available vs Deployed

**Available Agents** (from cache):
- Show: Hierarchical agent_id for category understanding
- Include: "Deploy with: claude-mpm agents deploy python-engineer"

**Deployed Agents** (in .claude/agents/):
- Show: Deployed filename (leaf name)
- Include: Full path, deployment tier, active status

### 4. Update AgentInfo to Include Agent ID

```python
@dataclass
class AgentInfo:
    name: str                      # Display name: "Python Engineer"
    agent_id: str                  # NEW: Hierarchical ID
    deployed_filename: str         # NEW: Leaf filename
    type: str
    tier: str
    path: str
    # ... rest of fields
```

### 5. Improve Status Display

The "Status" column should show:
- **Available**: In cache, not deployed
- **Deployed**: Active in `.claude/agents/`
- **Overridden**: Deployed but shadowed by higher tier
- **Outdated**: Deployed version older than cache

## Files to Investigate/Modify

Based on user's context, check these recent commits:

1. **c635ed92** - "fix(ui): show actual deployment state"
2. **89e45938** - "fix(ui): show actual deployment state"

These likely modified agent display logic. Review changes in:
- `src/claude_mpm/services/cli/agent_output_formatter.py`
- `src/claude_mpm/cli/commands/agents.py`
- `src/claude_mpm/cli/commands/agents_discover.py`

## Verification Commands

```bash
# Check current list output
claude-mpm agents list --deployed

# Check system agents
claude-mpm agents list --system

# Check discover output
claude-mpm agents discover --category engineer/backend

# Check deployed files
ls -la .claude/agents/

# Check cache structure
find ~/.claude-mpm/cache/remote-agents -name "*.md" -type f | head -10
```

## Conclusion

After investigating the codebase, I found:

### Finding 1: No "Agent ID / Name / Source / Status" Table Format Exists

The display format described by the user (with columns "Agent ID", "Name", "Source", "Status") **does not exist in the current codebase**. Current formats are:

**Discover Command** (`agents_discover.py`):
```
Engineering/Backend
  • engineer/backend/python-engineer
    Source: bobmatnyc/claude-mpm-agents (priority: 100)
```

**List Command** (`agent_output_formatter.py`):
```
Name                | Version | Description
--------------------|---------|-------------
Python Engineer     | unknown | Python 3.12-3.13 specialist...
```

### Finding 2: Recent UI Commits Were About Configure, Not List

Commits c635ed92 and 89e45938 modified the **interactive agent configuration UI** (checkboxes), not the list display. They fixed deployment state indicators in `configure.py`.

### Finding 3: The Real Issue - Three Types of Identifiers

The confusion stems from three different identifier types:

1. **Hierarchical Agent ID** (`engineer/backend/python-engineer`)
   - Used in: Discovery, filtering, cache organization
   - Purpose: Semantic categorization

2. **Deployed Filename** (`python-engineer.md`)
   - Used in: `.claude/agents/` directory
   - Purpose: Flat namespace for Claude Code runtime

3. **Display Name** (`Python Engineer`)
   - Used in: Human-readable output
   - Purpose: User-friendly presentation

## The "Incorrectness"

The likely issue is that `agents discover` shows hierarchical IDs like `engineer/backend/python-engineer`, which:

1. **Is correct** for discovery and categorization
2. **May confuse users** who expect to see the deployed filename `python-engineer.md`
3. **Doesn't match** what users find in `.claude/agents/`

## Recommendations

### Immediate Fix: Add Context to Display

**Option 1**: Show both hierarchical ID and deployed filename
```
Engineering/Backend
  • engineer/backend/python-engineer
    Deploys as: python-engineer.md
    Source: bobmatnyc/claude-mpm-agents (priority: 100)
```

**Option 2**: Make hierarchical path clearer
```
Engineering/Backend
  • Python Engineer (python-engineer)
    Category: engineer/backend
    Source: bobmatnyc/claude-mpm-agents
    Deployed: ✓ .claude/agents/python-engineer.md
```

### Long-term Fix: Add Deployment Status to Discovery

Extend `agents discover` to show deployment state:
```python
# In agents_discover.py
for agent in agents:
    agent_id = agent.get("agent_id")
    leaf_name = agent_id.split("/")[-1]  # Extract leaf

    # Check if deployed
    deployed_path = Path(".claude/agents") / f"{leaf_name}.md"
    status = "Deployed" if deployed_path.exists() else "Available"

    console.print(f"  • [bold]{agent_id}[/bold] ({status})")
    console.print(f"    File: {leaf_name}.md")
```

## What to Ask User

1. **Which command are you running?**
   - `claude-mpm agents discover`?
   - `claude-mpm agents list --deployed`?
   - `/mpm-agents` slash command?
   - Something else?

2. **What output do you see?**
   - Can you paste the exact output or provide a screenshot?
   - What columns does the display have?

3. **What do you expect to see?**
   - Should it show `engineer/backend/python-engineer` or `python-engineer`?
   - Should it indicate deployment status?

4. **Where is the disconnect?**
   - Is the ID format wrong?
   - Is the status incorrect?
   - Is something missing?

## Verification Commands

```bash
# Check current list output
claude-mpm agents list --deployed

# Check discover output
claude-mpm agents discover --category engineer/backend

# Check deployed files
ls -la .claude/agents/ | grep python

# Check cache structure
find ~/.claude-mpm/cache/remote-agents -name "python-engineer.md"
```

## Next Steps for Implementation

If the issue is confirmed to be about hierarchical vs. leaf names:

1. **Update `agents_discover.py`** to show leaf filename alongside hierarchical ID
2. **Add deployment status check** to show if agent is actually deployed
3. **Update documentation** to clarify the difference between agent_id and filename
4. **Consider adding `--show-filenames` flag** to control display format
