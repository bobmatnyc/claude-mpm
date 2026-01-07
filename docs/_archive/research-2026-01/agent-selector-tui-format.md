# Agent Selector TUI Format Analysis

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/agent_wizard.py`

**Date**: 2026-01-02

---

## Summary

The agent selector TUI uses Python's `questionary` library with a select component (arrow-key navigation). The format is consistent across all agent selection points, with variations depending on context (deploy vs. view vs. filter).

---

## Key Findings

### 1. Questionary Component Used

**Component**: `questionary.select()`

- Provides arrow-key navigation (up/down arrows to select, Enter to confirm, Esc to cancel)
- Not a checkbox component (single selection only)
- Uses the `MPM_STYLE` custom styling from `questionary_styles.py`
- Supports custom string formatting for each choice

### 2. Format String Patterns

There are **three distinct format patterns** used in the agent selector:

#### Pattern 1: Index + Agent ID + Description (Deploy Context)
**Location**: Lines 1183-1186

```python
agent_choices = [
    f"{i}. {agent['agent_id']} - {agent['description'][:60]}{'...' if len(agent['description']) > 60 else ''}"
    for i, agent in enumerate(deployable, 1)
]
```

**Example Output**:
```
1. engineer/backend/python-engineer - Python backend development with FastAPI and async patterns...
2. qa/test-automation/playwright-qa - Automated testing and QA with Playwright framework
3. docs/technical-writer - Technical documentation and API specification writing
```

**Components**:
- `{i}` = Sequential number starting at 1
- `.` = Literal period separator
- `{agent['agent_id']}` = Full agent ID (e.g., "engineer/backend/python-engineer")
- ` - ` = Literal separator
- `{agent['description'][:60]}` = First 60 characters of description
- `'...'` = Ellipsis shown only if description exceeds 60 characters

#### Pattern 2: Index + Agent ID (Minimal Context)
**Locations**: Lines 1507-1509 (filtered list deploy), Lines 1613-1615 (filtered list view)

```python
agent_choices = [
    f"{i}. {agent['agent_id']}" for i, agent in enumerate(agents, 1)
]
```

**Example Output**:
```
1. engineer/backend/python-engineer
2. qa/test-automation/playwright-qa
3. docs/technical-writer
```

**Components**:
- `{i}` = Sequential number starting at 1
- `.` = Literal period separator
- `{agent['agent_id']}` = Full agent ID

#### Pattern 3: Index + Label (Menu Actions)
**Locations**: Lines 349-372 (main management menu)

```python
# For agent viewing:
menu_choices.append(f"{i}. View agent: {agent['agent_id']}")

# For actions:
menu_choices.append(f"{len(all_agents) + 1}. Deploy agent")
menu_choices.append(f"{len(all_agents) + 2}. Create new agent")
menu_choices.append(f"{len(all_agents) + 3}. Delete agent(s)")
```

**Example Output**:
```
1. View agent: engineer/backend/python-engineer
2. View agent: qa/test-automation/playwright-qa
3. Deploy agent
4. Create new agent
5. Delete agent(s)
6. Import agents
```

**Components**:
- `{i}` = Sequential number (dynamically calculated)
- `.` = Literal period separator
- Descriptive text (varies by context)

#### Pattern 4: Index + Category (Filter Selection)
**Locations**: Lines 1327

```python
cat_choices = [f"{idx}. {cat}" for idx, cat in enumerate(categories, 1)]
```

**Example Output**:
```
1. engineer/backend
2. engineer/frontend
3. qa
4. ops
5. documentation
6. universal
```

### 3. Status Indicators

**Critical Finding**: The agent selector does NOT show "installed" vs "available" status in the questionary choices.

Status is shown in a separate **table view** above the questionary selection:
- **Location**: Lines 322-346
- Uses formatted print statements before the questionary select
- Status display: `"✓ Deployed"` or `"Available"`
- Uses dynamic column widths based on terminal size

**Table Format** (lines 312-346):
```python
print(f"{'#':<{widths['#']}} "
      f"{'Agent ID':<{widths['Agent ID']}} "
      f"{'Name':<{widths['Name']}} "
      f"{'Source':<{widths['Source']}} "
      f"{'Status':<{widths['Status']}}")
```

**Typical Output**:
```
#    Agent ID                         Name                 Source              Status
----------------------------------------------------------------------------------------------
1    engineer/backend/python-engineer Python Engineer      [project] local     ✓ Deployed
2    qa/test-automation/qa-expert     QA Expert            [system] official   Available
3    docs/technical-writer            Tech Writer          [system] official   Available
```

### 4. Data Structure for Choices

The choices parameter passed to questionary is a **Python list of strings**:

```python
agent_choices: List[str] = [
    "1. engineer/backend/python-engineer - Python backend development...",
    "2. qa/test-automation/qa-expert - Quality assurance and testing...",
    "3. docs/technical-writer - Technical documentation and writing..."
]

choice = questionary.select(
    "Select agent to deploy:",
    choices=agent_choices,
    style=MPM_STYLE
).ask()
```

**Return Value**: The exact string from the choices list (e.g., `"1. engineer/backend/python-engineer - Python backend..."`

**Parsing Pattern**:
```python
# Extract index from choice string
idx = int(choice.split(".")[0]) - 1  # "1. ..." -> 1 -> 0 (for list indexing)
selected_agent = agents[idx]
```

### 5. Style Configuration

- **Component**: `MPM_STYLE` custom style object
- **Location**: Imported from `claude_mpm.cli.interactive.questionary_styles`
- Uses consistent styling across all agent selection points
- No emojis or special characters in the choice strings themselves
- Status indicators (✓) appear only in the table display, not in questionary choices

---

## Summary Table: Format Variations

| Context | Component | Format Pattern | Example | Parses To |
|---------|-----------|---|---|---|
| Deploy menu | `questionary.select()` | `{i}. {id} - {desc[:60]}...` | `1. engineer/backend/python-engineer - Python backend development...` | `agents[0]` |
| Filtered list | `questionary.select()` | `{i}. {id}` | `1. engineer/backend/python-engineer` | `agents[0]` |
| Main menu | `questionary.select()` | `{i}. {label}: {id}` | `1. View agent: engineer/backend/python-engineer` | Manual parsing |
| Categories | `questionary.select()` | `{i}. {category}` | `1. engineer/backend` | `categories[0]` |
| Status display | Table (print) | `{i:<4} {id:<40} {name:<25} {status:<12}` | `1    engineer/backend/python-engineer ... ✓ Deployed` | N/A |

---

## Implementation for Skills Selector

To replicate this for skills with the same UX:

### 1. Three-Layer Display

```python
# Layer 1: Status table (printed above questionary)
# Shows: #, Skill ID, Name, Source, Status

# Layer 2: Questionary choices (arrow-key selection)
# Shows: {i}. {skill_id} - {description[:60]}...

# Layer 3: Return value parsing
# Extract index: idx = int(choice.split(".")[0]) - 1
```

### 2. Format String Implementation

**Primary format** (with description):
```python
skill_choices = [
    f"{i}. {skill['skill_id']} - {skill['description'][:60]}{'...' if len(skill['description']) > 60 else ''}"
    for i, skill in enumerate(skills, 1)
]
```

**Minimal format** (without description):
```python
skill_choices = [
    f"{i}. {skill['skill_id']}" for i, skill in enumerate(skills, 1)
]
```

### 3. Status Display

Do NOT include status in questionary choices. Instead:
- Display status in a table BEFORE questionary.select() is called
- Use format: `"✓ Installed"` or `"Available"`
- Use dynamic column widths for responsiveness

### 4. Key Characteristics

- **Single selection** (not multi-select/checkbox)
- **Arrow-key navigation** (up/down, Enter to confirm, Esc to cancel)
- **Simple string list** as choices (not objects or tuples)
- **Index-based parsing** from the returned string
- **No special characters/emojis** in choice strings (status shown separately)
- **Dynamic truncation** with ellipsis for long text

---

## Code References

**Agent Choices Construction**:
- Lines 1183-1186 (deploy with description)
- Lines 1507-1509 (minimal format)
- Lines 1327 (category format)

**Questionary Integration**:
- Lines 1188-1190 (deploy)
- Lines 1511-1513 (filtered list)
- Lines 1617-1619 (view)
- Lines 1329-1331 (categories)

**Status Table Display**:
- Lines 312-346 (format and render)
- Lines 300-309 (column width calculation)

**Parsing Return Value**:
- Line 1196 (deploy): `idx = int(choice.split(".")[0]) - 1`
- Line 1519 (filtered): `idx = int(choice_choice.split(".")[0]) - 1`
- Line 1625 (view): `idx = int(agent_choice.split(".")[0]) - 1`

---

## Style Reference

**Import**:
```python
from claude_mpm.cli.interactive.questionary_styles import (
    BANNER_WIDTH,
    MPM_STYLE,
    print_section_header,
)
```

**Usage**:
```python
questionary.select(
    "Select agent:",
    choices=agent_choices,
    style=MPM_STYLE
).ask()
```
