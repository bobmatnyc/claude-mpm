# Exact Code Patterns for Row Selection with Spacebar

**From**: Claude MPM codebase analysis
**Focus**: Agent selection and skill selection UI patterns

---

## The Three Essential Patterns

### Pattern A: Simple Multi-Select with Spacebar

**Component**: `questionary.checkbox()`
**Location**: Used throughout Claude MPM for multi-selection

```python
import questionary

choices = [
    questionary.Choice(title=f"{i}. {name}", value=name)
    for i, name in enumerate(items, 1)
]

selected = questionary.checkbox(
    "Choose items (spacebar to toggle):",
    choices=choices
).ask()

if selected is None:
    return  # User cancelled
```

**Spacebar Behavior**:
- User presses spacebar to toggle checkbox on/off
- No custom code needed - built-in to questionary

---

### Pattern B: Multi-Select with Pre-Checked Items

**Component**: `questionary.checkbox()` + `questionary.Choice(checked=...)`
**Real-World Example**: Skills selector with agent dependencies

**From `skill_selector.py` lines 319-365**:

```python
def _select_skills_from_group(self, toolchain: str) -> List[str]:
    """Multi-select skills with pre-selection of agent-required skills."""

    skills = self.skills_by_toolchain.get(toolchain, [])
    if not skills:
        return []

    choices = []
    for i, skill in enumerate(skills, 1):
        # Determine if this skill should be pre-selected
        already_selected = skill.name in self.agent_skill_deps

        # Format the display text
        tokens_k = skill.full_tokens // 1000
        desc = skill.description[:50] if skill.description else skill.name
        choice_text = f"{i}. {skill.name} - {desc}... ({tokens_k}K tokens)"

        # Create Choice with checked parameter
        choice = questionary.Choice(
            title=choice_text,
            value=skill.name,
            checked=already_selected,  # THIS ENABLES PRE-SELECTION
        )
        choices.append(choice)

    # Multi-select using checkbox - SPACEBAR WORKS HERE
    selected = questionary.checkbox(
        f"Select {toolchain} skills to include:",
        choices=choices,
        style=MPM_STYLE,
    ).ask()

    if selected is None:  # User pressed Esc
        return []

    return selected
```

**Key Elements**:
- `questionary.Choice(title=..., value=..., checked=...)`
- `checked=True` - item starts as selected
- User can toggle with spacebar to select/deselect
- Returns list of `value` attributes

---

### Pattern C: Two-Tier Selection Flow

**Components**: Nested `questionary.checkbox()` calls
**Real-World Example**: Skills wizard - first select topics, then items

**From `skill_selector.py` lines 288-365**:

```python
def select_skills(self) -> List[str]:
    """Two-tier selection: first topics, then items within topics."""

    # TIER 1: Select topic groups
    selected_groups = self._select_topic_groups()
    if not selected_groups:
        return list(self.agent_skill_deps)

    # TIER 2: For each selected group, select skills
    selected_skills = set(self.agent_skill_deps)  # Start with mandatory
    for group in selected_groups:
        group_skills = self._select_skills_from_group(group)
        selected_skills.update(group_skills)

    return list(selected_skills)

# --- Tier 1 Implementation ---
def _select_topic_groups(self) -> List[str]:
    """First tier: Select which toolchain groups to explore."""

    choices = []
    for toolchain in sorted(self.skills_by_toolchain.keys()):
        skills = self.skills_by_toolchain[toolchain]
        icon = TOPIC_ICONS.get(toolchain, "📦")
        display_name = toolchain.capitalize() if toolchain else "Universal"
        choice_text = f"{icon} {display_name} ({len(skills)} skills)"

        choices.append(questionary.Choice(
            title=choice_text,
            value=toolchain
        ))

    if not choices:
        return []

    # Multi-select groups
    selected = questionary.checkbox(
        "📂 Select Topic Groups to Add Skills From:",
        choices=choices,
        style=MPM_STYLE,
    ).ask()

    if selected is None:
        return []

    return selected

# --- Tier 2 Implementation ---
def _select_skills_from_group(self, toolchain: str) -> List[str]:
    """Second tier: Multi-select skills within a group."""
    # (See Pattern B above - same implementation)
```

**Flow**:
1. Show checkbox to select categories (spacebar toggles each)
2. For each selected category, show checkbox to select items (spacebar toggles each)
3. Accumulate all selected items
4. Return final list

---

## Agent Selection Pattern (Single Selection)

**Component**: `questionary.select()` (not checkbox)
**Real-World Example**: Deploy agent interactive menu

**From `agent_wizard.py` lines 1162-1197**:

```python
def _deploy_agent_interactive(self, available_agents: List[Dict[str, Any]]):
    """Interactive agent deployment - single selection."""

    deployable = apply_all_filters(
        available_agents, filter_base=True, filter_deployed=True
    )

    if not deployable:
        print("\n✅ All agents are already deployed!")
        return

    print_section_header("📦", "Deploy Agent", width=BANNER_WIDTH)

    # Build agent choices (simple string list for single selection)
    agent_choices = [
        f"{i}. {agent['agent_id']} - {agent['description'][:60]}"
        for i, agent in enumerate(deployable, 1)
    ]

    # Single-select using select() - NOT checkbox
    choice = questionary.select(
        "Select agent to deploy:",
        choices=agent_choices,
        style=MPM_STYLE
    ).ask()

    if not choice:  # User pressed Esc
        return

    # Parse the selection
    idx = int(choice.split(".")[0]) - 1
    agent = deployable[idx]

    # ... deployment logic ...
```

**Key Differences from Multi-Select**:
- Uses `questionary.select()` not `questionary.checkbox()`
- Returns single selected string, not list
- Arrow keys navigate, Enter confirms (no spacebar needed)
- For single selection, simple string list works fine

---

## Styling Pattern

**File**: `questionary_styles.py`

```python
from questionary import Style

# Unified style for all selectors
MPM_STYLE = Style([
    ("qmark", "fg:cyan bold"),        # Question mark
    ("question", "bold"),              # Question text
    ("answer", "fg:cyan"),             # Selected answer
    ("pointer", "fg:cyan bold"),       # Arrow pointer
    ("highlighted", "fg:cyan bold"),   # Highlighted row
    ("selected", "fg:cyan"),           # Selected item
])

BANNER_WIDTH = 60
BANNER_CHAR = "="
```

**Usage**:
```python
# Import and use in any selector
from claude_mpm.cli.interactive.questionary_styles import MPM_STYLE

selected = questionary.checkbox(
    "Choose items:",
    choices=choices,
    style=MPM_STYLE  # Apply consistent styling
).ask()
```

---

## Choice Object Format

The `questionary.Choice` object has three parameters:

```python
questionary.Choice(
    title="Display text shown to user",
    value="Actual value returned when selected",
    checked=False  # Optional, for checkbox only
)
```

**Examples**:

```python
# Minimal - for select()
Choice(title="Option 1", value="opt1")

# With pre-selection - for checkbox()
Choice(title="Skill: TDD", value="tdd", checked=True)

# Rich formatting
Choice(
    title=f"🐍 Python ({5} skills)",
    value="python",
    checked=False
)

# With metadata
Choice(
    title=f"1. auth-agent - Handles OAuth2 (32K tokens)",
    value="auth-agent"
)
```

---

## Return Value Handling

### For checkbox() - Multi-Select

```python
selected = questionary.checkbox(...).ask()

if selected is None:
    # User pressed Esc - cancelled
    print("Selection cancelled")
    return
elif selected == []:
    # User pressed Enter with nothing selected
    print("No items selected")
else:
    # User selected one or more items
    print(f"Selected {len(selected)} items: {selected}")
    # selected is a list: ['item1', 'item2', ...]
```

### For select() - Single Selection

```python
selected = questionary.select(...).ask()

if not selected:
    # User pressed Esc - cancelled or no selection
    print("Selection cancelled")
    return
else:
    # User selected an item
    print(f"Selected: {selected}")
    # selected is a string: 'item1'
```

---

## Complete Working Example

```python
import questionary
from questionary import Choice, Style

# Define style
style = Style([
    ("qmark", "fg:cyan bold"),
    ("question", "bold"),
    ("pointer", "fg:cyan bold"),
    ("highlighted", "fg:cyan bold"),
])

# Sample data
all_items = [
    {"id": "item1", "name": "First Item"},
    {"id": "item2", "name": "Second Item"},
    {"id": "item3", "name": "Third Item"},
]

pre_selected = {"item2"}  # Pre-select item2

# Build choices
choices = []
for i, item in enumerate(all_items, 1):
    choice = Choice(
        title=f"{i}. {item['name']}",
        value=item['id'],
        checked=item['id'] in pre_selected
    )
    choices.append(choice)

# Show selection
selected = questionary.checkbox(
    "Select items (spacebar to toggle):",
    choices=choices,
    style=style
).ask()

# Handle result
if selected is None:
    print("Cancelled")
else:
    print(f"You selected: {selected}")
    # Output might be: ['item2', 'item3']
```

**To run**:
```bash
pip install questionary
python script.py
```

**Keyboard**:
- Press spacebar on item 1, item 3
- Press Enter to confirm
- Result: `['item1', 'item2', 'item3']` (item2 was pre-selected, items 1 and 3 toggled on)

---

## Import Requirements

```python
# For the selector itself
import questionary
from questionary import Choice, Style

# For Claude MPM specific imports
from claude_mpm.cli.interactive.questionary_styles import (
    MPM_STYLE,
    BANNER_WIDTH,
    print_section_header,
)
```

---

## Summary Table

| Pattern | Component | Keyboard | Return | Use Case |
|---------|-----------|----------|--------|----------|
| A | `checkbox()` | Arrow + Space + Enter | List | Multi-select |
| B | `checkbox()` + `checked=` | Arrow + Space + Enter | List | Multi-select with pre-selection |
| C | Nested `checkbox()` | Arrow + Space + Enter | List | Two-tier selection |
| Agent | `select()` | Arrow + Enter | String | Single selection |

---

## Files in Claude MPM Using These Patterns

- **`/src/claude_mpm/cli/interactive/skill_selector.py`** - Patterns A, B, C (lines 238-365)
- **`/src/claude_mpm/cli/interactive/agent_wizard.py`** - Pattern: Agent selection (lines 1162-1197)
- **`/src/claude_mpm/cli/interactive/questionary_styles.py`** - Styling pattern
- **`/src/claude_mpm/cli/commands/skills.py`** - Uses skill_selector

---

## The Key Point

**Spacebar toggling for row selection is built-in to `questionary.checkbox()`. You don't need to implement it yourself - just use the right component:**

```python
# This gives you spacebar toggling automatically:
questionary.checkbox(
    "Choose items:",
    choices=[...],
).ask()
```

Done!
