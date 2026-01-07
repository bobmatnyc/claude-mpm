# Agent Selection UI Grouping Research

**Date:** 2025-12-09
**Researcher:** Research Agent
**Objective:** Understand current agent selection UI to add grouping by collection with "Select All" per group

## Executive Summary

The agent selection UI is implemented in `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py` using the `questionary` library for interactive checkboxes. Agents are discovered from both local templates and remote Git sources, with metadata including repository/collection information already available in the `source_dict` attribute.

**Key Finding:** The infrastructure for collection-based grouping already exists. We can leverage:
1. `agent_config.source_dict['source']` to identify repository/collection
2. `questionary.Choice` objects with `checked` state for pre-selection
3. `questionary.Separator` for visual grouping headers

**Recommended Implementation:** Use questionary's Separator to create collection groups with "Select All [collection]" choices that programmatically toggle all agents in that group.

---

## 1. Selection UI Code Location

### Primary File
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py`
**Method:** `_deploy_agents_individual()`
**Lines:** 1147-1444

### Key Code Sections

#### Agent Discovery (Line 355)
```python
agents = self.agent_manager.discover_agents(include_remote=True)
```

#### Checkbox Creation (Lines 1196-1220)
```python
for agent in agents:
    display_name = getattr(agent, "display_name", agent.name)
    is_selected = agent.name in current_selection

    choice_text = f"{agent.name}"
    if display_name and display_name != agent.name:
        choice_text += f" - {display_name}"

    choice = questionary.Choice(
        title=choice_text, value=agent.name, checked=is_selected
    )
    agent_choices.append(choice)
```

#### Questionary Checkbox Invocation (Lines 1243-1245)
```python
selected_agent_ids = questionary.checkbox(
    "Agents:", choices=agent_choices, style=self.QUESTIONARY_STYLE
).ask()
```

---

## 2. Agent Data Structure

### AgentConfig Model
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure_models.py`
**Lines:** 10-19

```python
class AgentConfig:
    def __init__(
        self, name: str, description: str = "", dependencies: Optional[List[str]] = None
    ):
        self.name = name
        self.description = description
        self.dependencies = dependencies or []
```

### Metadata Attached During Discovery
**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/agent_state_manager.py`
**Method:** `_discover_remote_agents()`
**Lines:** 210-264

#### Available Metadata (Lines 237-253)
```python
agent_config = AgentConfig(
    name=agent_id,
    description=f"[{category}] {description[:60]}...",
    dependencies=[f"Source: {source}"]
)

# Attach additional metadata
agent_config.source_type = "remote"  # or "local"
agent_config.is_deployed = is_deployed
agent_config.display_name = name
agent_config.full_agent_id = agent_id
agent_config.source_dict = agent_dict  # Full dictionary with:
    # - agent_id
    # - metadata (name, description)
    # - category
    # - source (repository URL or identifier)
    # - repository (repo identifier)
    # - version
    # - source_file (path to .md file)
```

### Source Dictionary Contents
From `git_source_manager.py` and agent discovery:
```python
source_dict = {
    "agent_id": "engineer/backend/python-engineer",
    "metadata": {
        "name": "Python Backend Engineer",
        "description": "Specialized in Python backend development"
    },
    "category": "engineer/backend",
    "source": "https://github.com/bobmatnyc/claude-mpm-agents",
    "repository": "bobmatnyc/claude-mpm-agents",  # Key field for grouping
    "version": "abc123def456...",
    "source_file": "/path/to/agents/engineer/backend/python-engineer.md"
}
```

**Critical Field for Grouping:** `source_dict['repository']` or `source_dict['source']`

---

## 3. Questionary Capabilities

### Library Used
**Package:** `questionary>=2.0.0` (from `pyproject.toml` line 13)
**Import:** Lines 19-22 of `configure.py`

### Supported Features

#### Checkbox Selection
- ✅ Multi-select with space bar
- ✅ Pre-selection via `checked=True` on Choice objects
- ✅ Arrow key navigation
- ✅ Returns list of selected values

#### Visual Grouping
- ✅ `questionary.Separator()` for section headers
- ✅ Custom text for separators (e.g., `Separator("── Collection Name ──")`)
- ✅ Non-selectable items

#### Style Customization
**Current Style (Lines 51-63):**
```python
QUESTIONARY_STYLE = Style([
    ("selected", "fg:#e0e0e0 bold"),
    ("pointer", "fg:#ffd700 bold"),
    ("highlighted", "fg:#e0e0e0"),
    ("question", "fg:#e0e0e0 bold"),
    ("checkbox", "fg:#00ff00"),
    ("checkbox-selected", "fg:#00ff00 bold"),
])
```

#### Symbol Customization (Lines 1234-1235)
```python
questionary.prompts.common.INDICATOR_SELECTED = "[✓]"
questionary.prompts.common.INDICATOR_UNSELECTED = "[ ]"
```

---

## 4. Current Data Flow

### Discovery → Display → Selection

```
1. user_agent_manager.discover_agents(include_remote=True)
   ├─ _discover_local_template_agents() → AgentConfig with source_type="local"
   └─ _discover_remote_agents()
      ├─ GitSourceManager.list_cached_agents()
      └─ AgentConfig with source_type="remote", source_dict={...}

2. Filter agents (BASE_AGENT removal)
   └─ filter_base_agents()

3. Build agent_choices list
   ├─ questionary.Choice(title, value, checked=is_selected)
   └─ Append to agent_choices

4. Display checkbox
   └─ questionary.checkbox("Agents:", choices=agent_choices)

5. User selects agents (space/arrows/enter)

6. Return selected_agent_ids (list of agent.name values)
```

### Available at Selection Time
- ✅ `agent.source_type` ("local" or "remote")
- ✅ `agent.source_dict['repository']` (e.g., "bobmatnyc/claude-mpm-agents")
- ✅ `agent.is_deployed` (current installation status)
- ✅ `agent.display_name` (human-readable name)

---

## 5. Recommended Implementation Approach

### Strategy: Collection-Grouped Selection with "Select All" Options

#### A. Group Agents by Collection

```python
# Group agents by collection
collections = {}
for agent in agents:
    # Determine collection identifier
    if agent.source_type == "remote":
        collection = agent.source_dict.get('repository', 'unknown')
    else:
        collection = "local"

    if collection not in collections:
        collections[collection] = []
    collections[collection].append(agent)
```

#### B. Build Grouped Choices with "Select All" Options

```python
agent_choices = []

for collection_id, collection_agents in sorted(collections.items()):
    # Add separator header
    agent_choices.append(questionary.Separator(f"── {collection_id} ──"))

    # Add "Select All" option for this collection
    select_all_value = f"__SELECT_ALL__{collection_id}"
    agent_choices.append(questionary.Choice(
        title=f"[ Select All ({len(collection_agents)} agents) ]",
        value=select_all_value,
        checked=False  # Not pre-checked
    ))

    # Add individual agents in this collection
    for agent in collection_agents:
        choice_text = f"{agent.name}"
        if agent.display_name and agent.display_name != agent.name:
            choice_text += f" - {agent.display_name}"

        is_selected = agent.name in current_selection
        agent_choices.append(questionary.Choice(
            title=choice_text,
            value=agent.name,
            checked=is_selected
        ))
```

#### C. Handle "Select All" Post-Processing

```python
selected_agent_ids = questionary.checkbox(
    "Agents:", choices=agent_choices, style=self.QUESTIONARY_STYLE
).ask()

if selected_agent_ids is None:
    return  # User cancelled

# Process "Select All" selections
final_selection = set()
select_all_collections = set()

for selected_id in selected_agent_ids:
    if selected_id.startswith("__SELECT_ALL__"):
        collection_id = selected_id.replace("__SELECT_ALL__", "")
        select_all_collections.add(collection_id)
    else:
        final_selection.add(selected_id)

# Add all agents from "Select All" collections
for collection_id in select_all_collections:
    for agent in collections[collection_id]:
        final_selection.add(agent.name)

# Update current_selection for next iteration
current_selection = final_selection
```

---

## 6. Alternative Approaches Considered

### Option 1: Pre-Select All via Checked State
**Pros:** No post-processing needed
**Cons:** Cannot dynamically toggle group without re-rendering

### Option 2: Nested Menus
**Pros:** Cleaner UX for many collections
**Cons:** Requires multiple screens, more complex flow

### Option 3: Filter-First Approach
**Pros:** Reduces visual clutter
**Cons:** Extra step, less discoverable

**Recommendation:** Use Option 1 (from Section 5) with post-processing for maximum flexibility.

---

## 7. Expected UX with Grouped Selection

```
? Agents:

  ── bobmatnyc/claude-mpm-agents ───────────────
  [ ] [ Select All (8 agents) ]
  [✓] pm
  [✓] engineer
  [✓] research
  [ ] qa
  [ ] documentation
  [ ] ops
  [ ] ticketing
  [ ] tauri-engineer

  ── local ─────────────────────────────────────
  [ ] [ Select All (2 agents) ]
  [✓] my-custom-agent
  [ ] experimental-agent

  ↑↓ Navigate  Space: Toggle  Enter: Confirm
```

**Behavior:**
1. Arrow keys navigate all choices
2. Space toggles individual agents or "Select All" option
3. "Select All" checked → All agents in that collection auto-selected
4. Enter confirms final selection

---

## 8. Files to Modify

### Primary Changes

1. **`configure.py`** (Lines 1196-1245)
   - Modify `_deploy_agents_individual()` to group agents by collection
   - Add "Select All" Choice objects per group
   - Post-process selection to expand "Select All" choices

### Supporting Changes

2. **`agent_state_manager.py`** (Optional)
   - No changes needed; metadata already available

3. **`configure_models.py`** (Optional)
   - Consider adding `collection_id` property to AgentConfig for cleaner access

---

## 9. Implementation Risks & Mitigations

### Risk 1: "Select All" Conflicts with Individual Selections
**Scenario:** User checks "Select All" AND unchecks individual agent
**Mitigation:** "Select All" always overrides individual selections (document in UI hint)

### Risk 2: Empty Collections
**Scenario:** Collection with 0 agents after filtering
**Mitigation:** Skip empty collections in grouping loop

### Risk 3: Unknown Collection Identifiers
**Scenario:** Missing `repository` field in source_dict
**Mitigation:** Fallback to "unknown" or "other" collection

### Risk 4: Performance with Many Collections
**Scenario:** 50+ collections with 500+ agents
**Mitigation:** Group by top-level organization (e.g., "bobmatnyc/*" → "bobmatnyc")

---

## 10. Testing Recommendations

### Unit Tests
1. Test collection grouping logic with mixed local/remote agents
2. Test "Select All" expansion with various collection sizes
3. Test empty collection handling

### Integration Tests
1. Test full selection flow with grouped UI
2. Test cancel/adjust workflows with grouped selections
3. Test deployment/removal with collection-selected agents

### Manual Tests
1. Verify visual rendering with real agent cache
2. Test keyboard navigation across collection boundaries
3. Test "Select All" interaction with pre-selected agents

---

## 11. Memory Usage Analysis

- **Agent Discovery:** Lightweight (only metadata, not full agent files)
- **Grouping Logic:** O(n) where n = number of agents
- **Questionary Rendering:** Efficient (terminal-based, no DOM)
- **Estimated Memory:** <5MB for 100 agents across 10 collections

---

## 12. Future Enhancements

1. **Hierarchical Categories:** Group by category (engineer/backend, engineer/frontend)
2. **Search/Filter:** Add search box before checkbox selection
3. **Collection Metadata:** Show agent count, last update time per collection
4. **Preset Collections:** Save custom collection groups (e.g., "Python Stack")
5. **Multi-Level Select All:** "Select All Visible" across all collections

---

## 13. References

- **Questionary Docs:** https://github.com/tmbo/questionary
- **Configure Command:** `src/claude_mpm/cli/commands/configure.py`
- **Agent State Manager:** `src/claude_mpm/cli/commands/agent_state_manager.py`
- **Git Source Manager:** `src/claude_mpm/services/agents/git_source_manager.py`
- **Agent Models:** `src/claude_mpm/cli/commands/configure_models.py`

---

## Appendices

### Appendix A: Questionary Choice API

```python
from questionary import Choice, Separator

# Regular choice
Choice(title="Display Text", value="agent_id", checked=True)

# Separator (non-selectable)
Separator("── Header Text ──")

# Checkbox usage
selected = questionary.checkbox(
    "Select items:",
    choices=[
        Separator("Group 1"),
        Choice("Item 1", value="item1", checked=True),
        Choice("Item 2", value="item2", checked=False),
        Separator("Group 2"),
        Choice("Item 3", value="item3", checked=False),
    ]
).ask()  # Returns: ["item1"] if user doesn't change selection
```

### Appendix B: Agent Source Attribution Logic

From `agent_state_manager.py` line 230-232:
```python
category = agent_dict.get("category", "unknown")
source = agent_dict.get("source", "remote")
```

From `configure.py` line 1087-1107 (display logic):
```python
if source_type == "remote":
    source_dict = getattr(agent, "source_dict", {})
    repo_url = source_dict.get("source", "")

    if "bobmatnyc/claude-mpm" in repo_url or "claude-mpm" in repo_url.lower():
        source_label = "MPM Agents"
    elif "/" in repo_url:
        parts = repo_url.rstrip("/").split("/")
        if len(parts) >= 2:
            source_label = f"{parts[-2]}/{parts[-1]}"
        else:
            source_label = "Community"
    else:
        source_label = "Community"
else:
    source_label = "Local"
```

**Recommendation:** Reuse this logic for collection grouping key.

### Appendix C: Example Implementation Pseudocode

```python
def _deploy_agents_individual_grouped(self, agents: List[AgentConfig]) -> None:
    """Enhanced agent selection with collection grouping."""

    # Step 1: Group agents by collection
    collections = self._group_agents_by_collection(agents)

    # Step 2: Build choices with separators and "Select All" options
    agent_choices = []
    for collection_id in sorted(collections.keys()):
        collection_agents = collections[collection_id]

        # Collection header
        agent_choices.append(questionary.Separator(f"── {collection_id} ──"))

        # "Select All" for this collection
        select_all_key = f"__SELECT_ALL__{collection_id}"
        agent_choices.append(questionary.Choice(
            title=f"[ Select All ({len(collection_agents)} agents) ]",
            value=select_all_key,
            checked=False
        ))

        # Individual agents
        for agent in collection_agents:
            agent_choices.append(self._create_agent_choice(agent))

    # Step 3: Show checkbox
    selected_raw = questionary.checkbox(
        "Agents:", choices=agent_choices, style=self.QUESTIONARY_STYLE
    ).ask()

    # Step 4: Expand "Select All" selections
    final_selection = self._expand_select_all(selected_raw, collections)

    # Step 5: Continue with deployment logic...
    # (existing code from line 1295 onwards)

def _group_agents_by_collection(self, agents: List[AgentConfig]) -> Dict[str, List[AgentConfig]]:
    """Group agents by collection identifier."""
    collections = {}
    for agent in agents:
        collection_id = self._get_collection_id(agent)
        if collection_id not in collections:
            collections[collection_id] = []
        collections[collection_id].append(agent)
    return collections

def _get_collection_id(self, agent: AgentConfig) -> str:
    """Extract collection identifier from agent metadata."""
    if agent.source_type == "remote":
        source_dict = getattr(agent, "source_dict", {})
        repo = source_dict.get("repository", "")
        if repo:
            return repo

        # Fallback: parse from source URL
        source_url = source_dict.get("source", "")
        if "/" in source_url:
            parts = source_url.rstrip("/").split("/")
            if len(parts) >= 2:
                return f"{parts[-2]}/{parts[-1]}"
        return "Community"
    else:
        return "Local"

def _expand_select_all(self, selected_raw: List[str], collections: Dict[str, List[AgentConfig]]) -> Set[str]:
    """Expand 'Select All' selections to individual agent IDs."""
    final_selection = set()
    select_all_collections = set()

    for selected_id in selected_raw:
        if selected_id.startswith("__SELECT_ALL__"):
            collection_id = selected_id.replace("__SELECT_ALL__", "")
            select_all_collections.add(collection_id)
        else:
            final_selection.add(selected_id)

    # Add all agents from "Select All" collections
    for collection_id in select_all_collections:
        for agent in collections.get(collection_id, []):
            final_selection.add(agent.name)

    return final_selection
```

---

**End of Research Document**
