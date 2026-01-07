# Spacebar Toggle Implementation - Quick Reference

**For**: Replicating the row selection with spacebar toggling pattern used in Claude MPM skills selector

---

## The Exact Answer

Claude MPM uses **`questionary.checkbox()`** component with **`questionary.Choice()` objects**.

Spacebar toggling is **built-in behavior** of questionary's checkbox component - no custom code needed.

---

## Minimal Example

```python
import questionary

# Create choice objects with title and value
choices = []
for i, item in enumerate(items, 1):
    choice = questionary.Choice(
        title=f"{i}. {item['name']}",
        value=item['id']
    )
    choices.append(choice)

# Use checkbox for multi-select with spacebar
selected = questionary.checkbox(
    "Select items (use spacebar to toggle):",
    choices=choices
).ask()

# Handle cancellation
if selected is None:
    print("Cancelled")
else:
    print(f"Selected: {selected}")
```

**That's it!** Spacebar toggling works automatically.

---

## With Pre-Selection

```python
# Pre-select items using checked parameter
choices = []
for i, item in enumerate(items, 1):
    is_required = item['id'] in required_ids

    choice = questionary.Choice(
        title=f"{i}. {item['name']}",
        value=item['id'],
        checked=is_required  # Pre-select this item
    )
    choices.append(choice)

selected = questionary.checkbox(
    "Select items:",
    choices=choices
).ask()
```

---

## With Styling (Claude MPM Pattern)

```python
from questionary import Style
import questionary

# Define style (from questionary_styles.py)
MPM_STYLE = Style([
    ("qmark", "fg:cyan bold"),
    ("question", "bold"),
    ("pointer", "fg:cyan bold"),
    ("highlighted", "fg:cyan bold"),
])

# Build choices
choices = [
    questionary.Choice(
        title=f"{i}. {item['name']} - {item['description'][:40]}",
        value=item['id'],
        checked=item['id'] in pre_selected
    )
    for i, item in enumerate(items, 1)
]

# Use with style
selected = questionary.checkbox(
    "Select items:",
    choices=choices,
    style=MPM_STYLE
).ask()
```

---

## Keyboard Controls

| Key | Action |
|-----|--------|
| **Spacebar** | Toggle checkbox on/off for current row |
| **Arrow ↑/↓** | Move to previous/next row |
| **Enter** | Confirm selection and return list |
| **Esc** | Cancel (returns None) |

---

## Two-Tier Pattern (Like Skills Selector)

```python
# Tier 1: Select categories
categories = questionary.checkbox(
    "📂 Select categories:",
    choices=[
        questionary.Choice(title=cat, value=cat)
        for cat in all_categories
    ],
    style=MPM_STYLE
).ask()

if not categories:
    return []

# Tier 2: Select items from each category
selected = set()
for category in categories:
    items = questionary.checkbox(
        f"Select {category} items:",
        choices=[
            questionary.Choice(
                title=f"{i}. {item['name']}",
                value=item['id'],
                checked=item['id'] in mandatory_ids
            )
            for i, item in enumerate(items_in_category, 1)
        ],
        style=MPM_STYLE
    ).ask()

    if items:
        selected.update(items)

return list(selected)
```

---

## Real Example from Code

From `/src/claude_mpm/cli/interactive/skill_selector.py` (lines 319-365):

```python
def _select_skills_from_group(self, toolchain: str) -> List[str]:
    skills = self.skills_by_toolchain.get(toolchain, [])

    choices = []
    for i, skill in enumerate(skills, 1):
        already_selected = skill.name in self.agent_skill_deps
        tokens_k = skill.full_tokens // 1000
        desc = skill.description[:50] if skill.description else skill.name
        choice_text = f"{i}. {skill.name} - {desc}... ({tokens_k}K tokens)"

        choice = questionary.Choice(
            title=choice_text,
            value=skill.name,
            checked=already_selected,  # Pre-selected items
        )
        choices.append(choice)

    # SPACEBAR TOGGLING IS HERE - built-in to checkbox!
    selected = questionary.checkbox(
        f"Select {toolchain} skills to include:",
        choices=choices,
        style=MPM_STYLE,
    ).ask()

    if selected is None:
        return []

    return selected
```

---

## Return Value

- **Multi-select**: Returns **list of selected values**
  ```python
  selected = ['skill-1', 'skill-2', 'skill-3']
  ```

- **Cancelled**: Returns **None**
  ```python
  if selected is None:
      print("User pressed Esc")
  ```

---

## Dependencies

```bash
pip install questionary
```

From `requirements.txt` or `pyproject.toml` in Claude MPM.

---

## Key Points

1. **questionary.checkbox()** - not select() - enables spacebar toggling
2. **questionary.Choice()** - creates formatted options with title/value
3. **checked=True** - pre-selects items
4. **Spacebar is built-in** - no custom code needed
5. **Handle None return** - for cancellation
6. **Use style parameter** - for consistent visual appearance

---

## Don't Forget

```python
# Import at top of file
import questionary
from questionary import Choice, Style

# Define or import style
from claude_mpm.cli.interactive.questionary_styles import MPM_STYLE
```

---

## Next Steps

To replicate this pattern for your use case:

1. Create `questionary.Choice` objects with `title`, `value`, and optional `checked`
2. Pass to `questionary.checkbox()` with your style
3. Call `.ask()` to show the prompt
4. Check if result is `None` (cancelled) or a list (selected items)
5. Spacebar toggling works automatically!
