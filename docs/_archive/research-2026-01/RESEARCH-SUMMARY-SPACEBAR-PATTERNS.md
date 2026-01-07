# Research Summary: Spacebar Toggle Row Selection Patterns

**Research Completed**: 2026-01-02
**Topic**: How Claude MPM implements row selection with spacebar toggling
**Output Files**: 3 detailed documents created

---

## Research Objective

Find the exact pattern for implementing row selection with spacebar toggling that can be replicated for skills selection UI, following the same pattern used for agent selection.

---

## Key Findings

### 1. The Core Answer

Claude MPM uses **`questionary.checkbox()`** component with **`questionary.Choice()` objects**.

**Spacebar toggling is built-in** - no custom implementation needed.

---

### 2. Where It's Used

| Component | File | Lines | Pattern |
|-----------|------|-------|---------|
| **Skills Selector** | `skill_selector.py` | 308-365 | Multi-select with checkbox |
| **Agent Wizard** | `agent_wizard.py` | 1188-1190 | Single-select with select |
| **Agent Management** | `agent_wizard.py` | 374-378 | Menu navigation with select |
| **Styling** | `questionary_styles.py` | 11-20 | MPM_STYLE definition |

---

### 3. The Exact Pattern

#### For Multi-Select with Spacebar (Skills)

```python
import questionary
from questionary import Choice

# Create Choice objects
choices = []
for i, item in enumerate(items, 1):
    choice = Choice(
        title=f"{i}. {item.name}",
        value=item.id,
        checked=item.id in pre_selected_ids  # Optional pre-selection
    )
    choices.append(choice)

# Use checkbox for spacebar toggling
selected = questionary.checkbox(
    "Select items (spacebar to toggle):",
    choices=choices,
    style=MPM_STYLE
).ask()

if selected is None:
    return []  # User cancelled

return selected  # Returns list of selected IDs
```

**Keyboard Behavior**:
- **Spacebar**: Toggle checkbox on/off for current row
- **Arrow ↑/↓**: Navigate between rows
- **Enter**: Confirm selection
- **Esc**: Cancel (returns None)

#### For Single-Selection (Agents)

```python
# Use select() for single selection
choices = [f"{i}. {item.name}" for i, item in enumerate(items, 1)]

selected = questionary.select(
    "Select an item:",
    choices=choices,
    style=MPM_STYLE
).ask()

if not selected:
    return None  # User cancelled

# Parse the selection
idx = int(selected.split(".")[0]) - 1
return items[idx]
```

---

### 4. Two-Tier Pattern (Like Skills Selector)

The skills selector uses a two-tier approach:

**Tier 1** (lines 288-317): Select toolchain groups
```python
selected = questionary.checkbox(
    "📂 Select Topic Groups to Add Skills From:",
    choices=[...],
    style=MPM_STYLE,
).ask()
```

**Tier 2** (lines 319-365): Select skills within each group
```python
selected = questionary.checkbox(
    f"Select {toolchain} skills to include:",
    choices=[...],  # With checked=True for pre-selected items
    style=MPM_STYLE,
).ask()
```

---

### 5. Choice Object Parameters

```python
questionary.Choice(
    title="Display text shown to user",
    value="Actual value returned when selected",
    checked=False  # Optional, for checkbox only
)
```

**Examples**:
```python
# Simple choice
Choice(title="Option 1", value="opt1")

# With pre-selection
Choice(title="Auth Module", value="auth", checked=True)

# Rich formatting
Choice(
    title="🐍 Python (5 skills) - token count",
    value="python",
    checked=False
)
```

---

### 6. Styling System

All selectors use unified `MPM_STYLE` from `questionary_styles.py`:

```python
MPM_STYLE = Style([
    ("qmark", "fg:cyan bold"),        # Question mark color
    ("question", "bold"),              # Question text
    ("answer", "fg:cyan"),             # Answer color
    ("pointer", "fg:cyan bold"),       # Arrow pointer
    ("highlighted", "fg:cyan bold"),   # Highlighted row
    ("selected", "fg:cyan"),           # Selected item
])
```

Import and use:
```python
from claude_mpm.cli.interactive.questionary_styles import MPM_STYLE

selected = questionary.checkbox(
    "Choose items:",
    choices=choices,
    style=MPM_STYLE
).ask()
```

---

## Implementation Steps

### To Implement Spacebar-Toggling Row Selection

1. **Import questionary components**:
   ```python
   import questionary
   from questionary import Choice
   from claude_mpm.cli.interactive.questionary_styles import MPM_STYLE
   ```

2. **Create Choice objects**:
   ```python
   choices = [
       Choice(
           title=f"{i}. {item['name']} - {item['description']}",
           value=item['id'],
           checked=item['id'] in pre_selected
       )
       for i, item in enumerate(items, 1)
   ]
   ```

3. **Call questionary.checkbox()**:
   ```python
   selected = questionary.checkbox(
       "Select items (spacebar to toggle):",
       choices=choices,
       style=MPM_STYLE
   ).ask()
   ```

4. **Handle the result**:
   ```python
   if selected is None:
       # User cancelled
       return []
   else:
       # Process selected items
       return selected  # List of selected values
   ```

5. **That's it!** Spacebar toggling works automatically.

---

## Key Implementation Notes

1. **Use `questionary.checkbox()`** - not `select()` - for spacebar toggling
2. **Spacebar is built-in** - no custom keyboard handling needed
3. **Pre-selection with `checked=True`** - items start selected but user can toggle
4. **Handle `None` return** - user pressed Esc to cancel
5. **Use consistent styling** - always apply `MPM_STYLE` parameter
6. **Rich formatting** - use emojis, icons, token counts in title parameter
7. **Two-tier works well** - for complex selections (topics → items)

---

## Return Values

### Multi-Select (checkbox)
- **Success**: List of selected values - `['item1', 'item2']`
- **Cancelled**: `None`
- **Empty**: `[]`

### Single-Select (select)
- **Success**: String value - `'item1'`
- **Cancelled**: `None`
- **Empty**: `None`

---

## Files Referenced

All code from `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/`:

1. **skill_selector.py**
   - `_select_topic_groups()` - Tier 1 multi-select (lines 288-317)
   - `_select_skills_from_group()` - Tier 2 multi-select with pre-selection (lines 319-365)
   - `select_skills()` - Orchestrates two-tier flow (lines 238-279)

2. **agent_wizard.py**
   - `_deploy_agent_interactive()` - Single selection (lines 1162-1276)
   - `run_interactive_manage()` - Menu navigation (lines 265-435)

3. **questionary_styles.py**
   - `MPM_STYLE` - Style definition (lines 11-20)
   - `print_banner()` - Banner utilities (lines 27-44)
   - `print_section_header()` - Section headers (lines 47-65)

---

## Real-World Examples from Code

### Example 1: Pre-Selected Items (from skills selector)

```python
# Line 348-352 in skill_selector.py
choice = questionary.Choice(
    title=choice_text,
    value=skill.name,
    checked=already_selected,  # Pre-select if in agent_skill_deps
)
```

### Example 2: Two-Tier Navigation (from skills selector)

```python
# Lines 260-272 in skill_selector.py
selected_groups = self._select_topic_groups()  # Tier 1
if not selected_groups:
    return list(self.agent_skill_deps)

selected_skills = set(self.agent_skill_deps)
for group in selected_groups:  # Tier 2
    group_skills = self._select_skills_from_group(group)
    selected_skills.update(group_skills)
```

### Example 3: Single Selection (from agent wizard)

```python
# Lines 1188-1196 in agent_wizard.py
choice = questionary.select(
    "Select agent to deploy:",
    choices=agent_choices,
    style=MPM_STYLE
).ask()

if not choice:
    return  # Cancelled
```

---

## Dependencies

```bash
pip install questionary
```

Already in project's requirements - verified in codebase.

---

## What NOT to Do

Don't manually implement:
- ❌ Keyboard event handling for spacebar
- ❌ Checkbox toggle logic
- ❌ Custom cursor navigation
- ❌ Arrow key bindings

**Do this instead**:
- ✅ Use `questionary.checkbox()` - it has everything
- ✅ Use `questionary.Choice()` for formatted options
- ✅ Use `MPM_STYLE` for consistent appearance
- ✅ Handle `None` return for cancellation

---

## Testing the Pattern

Quick test script:

```python
import questionary
from questionary import Choice, Style

style = Style([("pointer", "fg:cyan bold")])

items = [
    {"id": "a", "name": "Item A"},
    {"id": "b", "name": "Item B"},
    {"id": "c", "name": "Item C"},
]

choices = [
    Choice(title=f"{i}. {item['name']}", value=item['id'])
    for i, item in enumerate(items, 1)
]

selected = questionary.checkbox(
    "Select items (spacebar to toggle):",
    choices=choices,
    style=style
).ask()

print(f"Selected: {selected}")
```

Run and use spacebar - it just works!

---

## Summary

The exact pattern for row selection with spacebar toggling in Claude MPM is:

1. **Create `questionary.Choice` objects** with title/value/optional checked
2. **Call `questionary.checkbox()`** with list of choices
3. **Add `style=MPM_STYLE`** for consistent appearance
4. **Handle `None` return** for cancellation
5. **Spacebar automatically works** - built-in to questionary

No custom implementation needed!

---

## Output Documents

Three detailed research documents created:

1. **`agent-skill-selection-ui-patterns.md`** (15K)
   - Comprehensive analysis of both agent and skill patterns
   - Component overview and styling system
   - Complete code patterns for implementation
   - Key implementation notes and examples

2. **`spacebar-toggle-quick-reference.md`** (5.4K)
   - Quick reference for spacebar implementation
   - Minimal examples and keyboard controls
   - Two-tier pattern example
   - Real code from codebase

3. **`exact-code-patterns.md`** (11K)
   - Three essential patterns in detail
   - Pattern A: Simple multi-select
   - Pattern B: Multi-select with pre-selection
   - Pattern C: Two-tier selection flow
   - Complete working example and imports

**All saved to**: `/Users/masa/Projects/claude-mpm/docs/research/`
