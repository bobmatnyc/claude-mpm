# Agent and Skill Selection UI Patterns in Claude MPM

**Research Date:** 2026-01-02
**Topic:** Row selection with spacebar toggling in questionary components

## Overview

This document details how Claude MPM implements interactive selection UIs using the questionary library. The patterns show two complementary approaches:

1. **Agent Selection**: Uses `questionary.select()` with arrow key navigation (single selection)
2. **Skill Selection**: Uses `questionary.checkbox()` with spacebar toggling (multi-select)

Both leverage the `questionary.Choice` object for flexible formatting and the `MPM_STYLE` for consistent visual styling.

---

## Table of Contents

1. [Component Overview](#component-overview)
2. [Questionary Components Used](#questionary-components-used)
3. [Skill Selection Pattern (Multi-Select with Spacebar)](#skill-selection-pattern)
4. [Agent Selection Pattern (Single Selection)](#agent-selection-pattern)
5. [Styling System](#styling-system)
6. [Code Patterns to Replicate](#code-patterns-to-replicate)

---

## Component Overview

### Core Files Involved

| File | Purpose | Component |
|------|---------|-----------|
| `src/claude_mpm/cli/interactive/skill_selector.py` | Multi-tier skill selection wizard | Checkbox (spacebar toggle) |
| `src/claude_mpm/cli/interactive/agent_wizard.py` | Agent management and deployment | Select (arrow keys) |
| `src/claude_mpm/cli/interactive/questionary_styles.py` | Shared styling and utilities | Style definition |

### Questionary Library

- **Library**: `questionary` (prompt library for Python CLI)
- **Key Components**: `select`, `checkbox`, `Choice`
- **Styling**: Custom `Style` objects for consistent theming

---

## Questionary Components Used

### 1. questionary.select() - Single Selection

**Purpose**: Single-choice selection with arrow key navigation
**Keyboard Controls**:
- Arrow keys (↑/↓) to navigate options
- Enter to confirm selection
- Esc to cancel

**Usage in Agent Wizard** (line 1188-1190, agent_wizard.py):
```python
choice = questionary.select(
    "Select agent to deploy:",
    choices=agent_choices,
    style=MPM_STYLE
).ask()
```

**Returns**: Selected choice string or `None` if cancelled

### 2. questionary.checkbox() - Multi-Select with Spacebar

**Purpose**: Multi-choice selection with spacebar toggling
**Keyboard Controls**:
- Arrow keys (↑/↓) to navigate options
- **Spacebar to toggle checkbox** (this is the key pattern)
- Enter to confirm selection
- Esc to cancel

**Usage in Skill Selector** (line 308-312, skill_selector.py):
```python
selected = questionary.checkbox(
    "📂 Select Topic Groups to Add Skills From:",
    choices=choices,
    style=MPM_STYLE,
).ask()
```

**Returns**: List of selected values or `None` if cancelled

### 3. questionary.Choice() - Formatted Options

**Purpose**: Create choice objects with custom display text and underlying values

**Two-tier approach in skills_wizard**:

#### Tier 1: Checkbox for topic/toolchain groups
```python
choices = []
for toolchain in sorted(self.skills_by_toolchain.keys()):
    skills = self.skills_by_toolchain[toolchain]
    icon = TOPIC_ICONS.get(toolchain, "📦")
    display_name = toolchain.capitalize() if toolchain else "Universal"
    choice_text = f"{icon} {display_name} ({len(skills)} skills)"
    choices.append(questionary.Choice(title=choice_text, value=toolchain))
```

#### Tier 2: Checkbox with pre-checked items
```python
choices = []
for i, skill in enumerate(skills, 1):
    already_selected = skill.name in self.agent_skill_deps
    tokens_k = skill.full_tokens // 1000
    desc = skill.description[:50] if skill.description else skill.name
    choice_text = f"{i}. {skill.name} - {desc}... ({tokens_k}K tokens)"

    choice = questionary.Choice(
        title=choice_text,
        value=skill.name,
        checked=already_selected,  # Pre-select items from agent deps
    )
    choices.append(choice)
```

**Key Parameters**:
- `title`: Display text shown to user
- `value`: Actual value returned when selected
- `checked`: (Checkbox only) Whether item is pre-selected

---

## Skill Selection Pattern

### Complete Implementation Pattern

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/skill_selector.py`

### Two-Tier Selection Architecture

#### Tier 1: Select Topic Groups (Multi-select with Spacebar)

```python
def _select_topic_groups(self) -> List[str]:
    """First tier: Select which toolchain groups to browse.

    Returns:
        List of selected toolchain keys
    """
    # Build choices with counts
    choices = []
    for toolchain in sorted(self.skills_by_toolchain.keys()):
        skills = self.skills_by_toolchain[toolchain]
        icon = TOPIC_ICONS.get(toolchain, "📦")
        display_name = toolchain.capitalize() if toolchain else "Universal"
        choice_text = f"{icon} {display_name} ({len(skills)} skills)"
        choices.append(questionary.Choice(title=choice_text, value=toolchain))

    if not choices:
        print("\n⚠️  No skills available in manifest.")
        return []

    # Multi-select groups using CHECKBOX (supports spacebar)
    selected = questionary.checkbox(
        "📂 Select Topic Groups to Add Skills From:",
        choices=choices,
        style=MPM_STYLE,
    ).ask()

    if selected is None:  # User cancelled
        return []

    return selected
```

**Pattern Details**:
- Uses `questionary.checkbox()` for multi-selection
- Each choice has `title` (display) and `value` (return value)
- **Spacebar toggles checkboxes** on/off
- Arrow keys navigate between items
- Returns list of selected values

#### Tier 2: Multi-Select Skills from Group (Multi-select with Pre-checked Items)

```python
def _select_skills_from_group(self, toolchain: str) -> List[str]:
    """Second tier: Multi-select skills within a toolchain group.

    Args:
        toolchain: Toolchain key to select from

    Returns:
        List of selected skill names
    """
    skills = self.skills_by_toolchain.get(toolchain, [])
    if not skills:
        return []

    icon = TOPIC_ICONS.get(toolchain, "📦")
    display_name = toolchain.capitalize() if toolchain else "Universal"

    print(f"\n{icon} {display_name} Skills:")

    # Build choices with numbered format
    choices = []
    for i, skill in enumerate(skills, 1):
        # Mark if already selected (from agent deps)
        already_selected = skill.name in self.agent_skill_deps

        # Format: "1. skill-name - description (XK tokens)"
        tokens_k = skill.full_tokens // 1000
        desc = skill.description[:50] if skill.description else skill.name
        choice_text = f"{i}. {skill.name} - {desc}... ({tokens_k}K tokens)"

        choice = questionary.Choice(
            title=choice_text,
            value=skill.name,
            checked=already_selected,  # Pre-select agent dependencies
        )
        choices.append(choice)

    # Multi-select skills
    selected = questionary.checkbox(
        f"Select {display_name} skills to include:",
        choices=choices,
        style=MPM_STYLE,
    ).ask()

    if selected is None:  # User cancelled
        return []

    return selected
```

**Pattern Details**:
- Uses `checked=True` parameter to pre-select items from agent dependencies
- Items already selected remain checked but can be unchecked with spacebar
- Arrow keys navigate, spacebar toggles each item
- Supports deselection of pre-checked items

### Key Features of Skill Selection

1. **Two-tier navigation**: First select categories, then items within category
2. **Pre-selection support**: Items can be pre-checked (from agent deps)
3. **Rich formatting**: Displays tokens, descriptions, and status
4. **Spacebar toggling**: Standard questionary checkbox behavior
5. **User-friendly icons**: Toolchain icons (🐍, 📘, etc.) for visual clarity

---

## Agent Selection Pattern

### Single Selection with Arrow Keys

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/agent_wizard.py`

```python
def _deploy_agent_interactive(self, available_agents: List[Dict[str, Any]]):
    """Interactive agent deployment."""
    # ... filtering code ...

    print_section_header("📦", "Deploy Agent", width=BANNER_WIDTH)
    print(f"\n{len(deployable)} agent(s) available to deploy:\n")

    # Build agent selection choices with arrow-key navigation
    agent_choices = [
        f"{i}. {agent['agent_id']} - {agent['description'][:60]}{'...' if len(agent['description']) > 60 else ''}"
        for i, agent in enumerate(deployable, 1)
    ]

    # Use questionary.select() for single selection
    choice = questionary.select(
        "Select agent to deploy:",
        choices=agent_choices,
        style=MPM_STYLE
    ).ask()

    if not choice:  # User pressed Esc
        return

    # Parse agent index from "N. agent_id - description" format
    idx = int(choice.split(".")[0]) - 1
    agent = deployable[idx]
```

**Pattern Details**:
- Uses `questionary.select()` for single selection
- Simple list of string choices (not Choice objects needed here)
- Arrow keys navigate, Enter selects
- Returns the selected choice string
- Parse index from formatted string to access array

### Navigation Menu Pattern (With Agent Details)

```python
def run_interactive_manage(self) -> Tuple[bool, str]:
    """Run interactive agent management menu."""
    # ... setup code ...

    # Build menu choices
    menu_choices = []

    # Add agent viewing options
    for i, agent in enumerate(all_agents, 1):
        menu_choices.append(f"{i}. View agent: {agent['agent_id']}")

    # Add action options
    menu_choices.append(f"{len(all_agents) + 1}. Deploy agent")
    menu_choices.append(f"{len(all_agents) + 2}. Create new agent")
    # ... more options ...

    choice = questionary.select(
        "Agent Management Menu:",
        choices=menu_choices,
        style=MPM_STYLE,
    ).ask()

    if not choice:  # User pressed Esc
        return True, "Management menu exited"

    # Parse choice number from "N. Description" format
    choice_num = int(choice.split(".")[0])
```

---

## Styling System

### MPM_STYLE Definition

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/questionary_styles.py`

```python
from questionary import Style

# Standard cyan-themed style for all selectors
MPM_STYLE = Style(
    [
        ("qmark", "fg:cyan bold"),           # Question mark color
        ("question", "bold"),                # Question text
        ("answer", "fg:cyan"),               # Selected answer color
        ("pointer", "fg:cyan bold"),         # Arrow pointer color
        ("highlighted", "fg:cyan bold"),     # Highlighted row color
        ("selected", "fg:cyan"),             # Selected item color
    ]
)

BANNER_WIDTH = 60
BANNER_CHAR = "="
```

### Usage in Components

Both agents and skills selectors use the same style:

```python
# In agent_wizard.py
choice = questionary.select(
    "...",
    choices=agent_choices,
    style=MPM_STYLE  # Consistent styling
).ask()

# In skill_selector.py
selected = questionary.checkbox(
    "...",
    choices=choices,
    style=MPM_STYLE  # Same style applied
).ask()
```

### Visual Elements

- **Cyan color scheme** (`fg:cyan`) for consistency with brand
- **Bold highlighting** for interactive elements
- **Unified pointer styling** across all selectors

---

## Code Patterns to Replicate

### Pattern 1: Multi-Select with Spacebar Toggling

**For implementing row selection with spacebar**:

```python
# Step 1: Create Choice objects with title and value
choices = []
for i, item in enumerate(items, 1):
    is_pre_selected = item.id in pre_selected_ids
    choice_text = f"{i}. {item.name} - {item.description}"

    choice = questionary.Choice(
        title=choice_text,
        value=item.id,
        checked=is_pre_selected,  # KEY: Pre-select items
    )
    choices.append(choice)

# Step 2: Use questionary.checkbox() for multi-select
selected = questionary.checkbox(
    "Select items (spacebar to toggle):",
    choices=choices,
    style=MPM_STYLE,
).ask()

# Step 3: Handle cancellation
if selected is None:
    return []

return selected
```

**Keyboard Behavior**:
- Arrow ↑/↓: Navigate between rows
- Spacebar: Toggle checkbox on current row
- Enter: Confirm selection
- Esc: Cancel (returns None)

### Pattern 2: Single Selection with Arrow Keys

**For implementing simple navigation**:

```python
# Step 1: Create formatted choice strings
choices = [
    f"{i}. {item['name']} - {item['description']}"
    for i, item in enumerate(items, 1)
]

# Step 2: Use questionary.select() for single selection
selected = questionary.select(
    "Choose an item:",
    choices=choices,
    style=MPM_STYLE,
).ask()

# Step 3: Parse the selection
if not selected:
    return None

# Extract index from "N. name - description" format
idx = int(selected.split(".")[0]) - 1
return items[idx]
```

**Keyboard Behavior**:
- Arrow ↑/↓: Navigate between rows
- Enter: Select current row
- Esc: Cancel (returns None)

### Pattern 3: Two-Tier Selection Flow

**For complex selection scenarios**:

```python
# Tier 1: Select categories (multi-select)
categories = questionary.checkbox(
    "Select categories:",
    choices=[questionary.Choice(title=cat, value=cat) for cat in all_categories],
    style=MPM_STYLE,
).ask()

if not categories:
    return []

# Tier 2: For each category, select items (multi-select)
selected_items = set()
for category in categories:
    items_in_category = get_items_for_category(category)

    items = questionary.checkbox(
        f"Select {category} items:",
        choices=[
            questionary.Choice(
                title=f"{i}. {item.name}",
                value=item.id,
                checked=item.id in mandatory_ids,
            )
            for i, item in enumerate(items_in_category, 1)
        ],
        style=MPM_STYLE,
    ).ask()

    if items is not None:
        selected_items.update(items)

return list(selected_items)
```

---

## Usage Summary

| Use Case | Component | Keyboard | Return Type |
|----------|-----------|----------|------------|
| **Single row selection** | `select()` | Arrow + Enter | String |
| **Multi-select with spacebar** | `checkbox()` | Arrow + Space + Enter | List |
| **Menu navigation** | `select()` | Arrow + Enter | String |
| **Dependent selection** | `checkbox()` then `select()` | Mixed | List |

---

## Key Implementation Notes

1. **Spacebar is built-in**: Questionary's `checkbox()` component natively supports spacebar toggling - no custom implementation needed

2. **Pre-selection**: Use `checked=True` in `questionary.Choice()` to mark items as pre-selected

3. **Cancellation handling**: Always check if return value is `None` (user pressed Esc)

4. **Choice formatting**: The `title` parameter is what users see; the `value` parameter is what's returned

5. **Consistent styling**: Always import and use `MPM_STYLE` from `questionary_styles.py`

6. **Icon support**: Use emoji icons in choice text for visual clarity (e.g., `"🐍 Python (5 skills)"`)

7. **Dynamic widths**: For table display alongside selections, use the column width calculation pattern from `skill_selector.py` and `agent_wizard.py`

---

## File References

- **Skill Selector**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/skill_selector.py` (Lines 238-365)
- **Agent Wizard**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/agent_wizard.py` (Lines 1162-1276, 1629-1886)
- **Styles**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/questionary_styles.py`
