# Visual Pattern Reference - Row Selection with Spacebar

**Quick visual guide** for understanding the questionary checkbox pattern

---

## What the User Sees

### Before Selection

```
Select items (spacebar to toggle):
  ☐ 1. Item A - Description here
  ☐ 2. Item B - Description here
  ☐ 3. Item C - Description here
  ☐ 4. Item D - Description here

[Navigation: arrow keys ↑↓ | spacebar to toggle | enter to confirm]
```

### User Presses Spacebar on Item 1

```
Select items (spacebar to toggle):
  ☑ 1. Item A - Description here      ← Checked!
  ☐ 2. Item B - Description here
  ☐ 3. Item C - Description here
  ☐ 4. Item D - Description here
```

### User Navigates Down and Toggles Item 3

```
Select items (spacebar to toggle):
  ☑ 1. Item A - Description here
  ☐ 2. Item B - Description here
  ☑ 3. Item C - Description here      ← Checked!
  ☐ 4. Item D - Description here
```

### User Presses Enter to Confirm

```
Selected: ['item-a', 'item-c']
```

---

## The Code Behind It

### What the Developer Writes

```python
# 1. Import (once)
import questionary
from questionary import Choice
from claude_mpm.cli.interactive.questionary_styles import MPM_STYLE

# 2. Data preparation
items = [
    {"id": "a", "name": "Item A", "desc": "Description here"},
    {"id": "b", "name": "Item B", "desc": "Description here"},
    {"id": "c", "name": "Item C", "desc": "Description here"},
    {"id": "d", "name": "Item D", "desc": "Description here"},
]

# 3. Create choices (this is what the user sees formatted)
choices = [
    Choice(
        title=f"{i}. {item['name']} - {item['desc']}",
        value=item['id']
    )
    for i, item in enumerate(items, 1)
]

# 4. Show selection
selected = questionary.checkbox(
    "Select items (spacebar to toggle):",
    choices=choices,
    style=MPM_STYLE
).ask()

# 5. Handle result
if selected is None:
    print("User cancelled")
else:
    print(f"Selected: {selected}")
```

### What Questionary Does

```
questionary.checkbox() → Shows UI with checkboxes
                      → Handles keyboard input (arrow, spacebar, enter, esc)
                      → Returns list of selected values OR None
                      → All built-in, no custom code needed!
```

---

## Pattern Visualization

### Simple Pattern (Pattern A)

```
┌─ Your Code ─────────────────────────┐
│ choices = [Choice(...), ...]        │
│ selected = questionary.checkbox()   │
│ .ask()                              │
└─────────────────────────────────────┘
         ↓
┌─ Questionary ───────────────────────┐
│ Shows checkbox UI                   │
│ Handles all keyboard input          │
│ User presses spacebar to toggle     │
└─────────────────────────────────────┘
         ↓
┌─ Result ────────────────────────────┐
│ Returns: ['item1', 'item3']         │
│ Or None if cancelled                │
└─────────────────────────────────────┘
```

### Pre-Selected Pattern (Pattern B)

```
┌─ Your Code ─────────────────────────────────┐
│ mandatory = {'item2', 'item3'}              │
│ choices = [                                 │
│   Choice(..., checked=id in mandatory)      │
│   ...                                       │
│ ]                                           │
└─────────────────────────────────────────────┘
         ↓
┌─ Questionary ───────────────────────────────┐
│ Shows checkboxes                            │
│ Items in 'mandatory' start CHECKED          │
│ User can toggle (including pre-checked)     │
│ Handles keyboard input                      │
└─────────────────────────────────────────────┘
         ↓
┌─ Result ────────────────────────────────────┐
│ Returns selected (may include/exclude       │
│ originally checked items)                   │
└─────────────────────────────────────────────┘
```

### Two-Tier Pattern (Pattern C)

```
TIER 1: Select Categories
┌─────────────────────────┐
│ ☐ Category A (5 items)  │
│ ☑ Category B (3 items)  │
│ ☐ Category C (2 items)  │
└─────────────────────────┘
         ↓ (User selected B)

TIER 2: Select Items from B
┌─────────────────────────┐
│ ☑ Item B1 (required)    │
│ ☐ Item B2               │
│ ☑ Item B3               │
└─────────────────────────┘
         ↓ (User toggled B2)

RESULT: ['b1', 'b2', 'b3']
```

---

## Keyboard Reference (Visual)

```
Current Row: ┌──────────────────────────┐
             │ ☐ 3. Item C - Description │
             └──────────────────────────┘

Key         Action
────────────────────────────────────────
↑ Arrow Up  Move to previous row
            ┌──────────────────────────┐
            │ ☐ 2. Item B - Description │
            └──────────────────────────┘

↓ Arrow Dn  Move to next row
            ┌──────────────────────────┐
            │ ☑ 4. Item D - Description │
            └──────────────────────────┘

SPACEBAR    Toggle current row
            ☐ → ☑ or ☑ → ☐

ENTER       Confirm selection
            Return list of checked items

ESC         Cancel selection
            Return None
```

---

## Component Breakdown

### questionary.Choice()

```
What the developer creates:
┌────────────────────────────────────┐
│ Choice(                            │
│   title="Display text shown",      │
│   value="returned_value",          │
│   checked=False                    │
│ )                                  │
└────────────────────────────────────┘

What the user sees:
┌────────────────────────┐
│ ☐ Display text shown   │
└────────────────────────┘

What questionary returns:
"returned_value"
```

### questionary.checkbox()

```
What the developer creates:
┌──────────────────────────────┐
│ questionary.checkbox(         │
│   "Prompt text:",            │
│   choices=[...],             │
│   style=MPM_STYLE            │
│ ).ask()                       │
└──────────────────────────────┘

What the user sees:
┌─────────────────────┐
│ ? Prompt text:      │
│   ☐ Choice 1        │
│   ☑ Choice 2        │
│   ☐ Choice 3        │
└─────────────────────┘

What questionary returns:
['choice_2_value']
or
None  (if cancelled)
```

---

## Data Flow Diagram

```
┌──────────────────────────┐
│ Your Items Data          │
│ [                        │
│   {"id": "a", ...},      │
│   {"id": "b", ...},      │
│ ]                        │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ Create Choice objects    │
│ Choice(title="...",      │
│        value=item['id']) │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ Pass to checkbox()       │
│ questionary.checkbox(    │
│   choices=[...],         │
│   style=MPM_STYLE        │
│ ).ask()                  │
└──────────┬───────────────┘
           │ (User interacts)
           ▼
┌──────────────────────────┐
│ questionary returns      │
│ ['a', 'b']  or  None     │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ Your code handles result │
│ if result is None: ...   │
│ else: process result     │
└──────────────────────────┘
```

---

## Side-by-Side: Checkbox vs Select

### checkbox() - Multi-Select

```
questionary.checkbox("Choose:", choices=[...])
                                  ↓
┌─────────────────────────────────┐
│ ☐ Option 1                      │
│ ☑ Option 2                      │
│ ☑ Option 3                      │
│ ☐ Option 4                      │
└─────────────────────────────────┘
Spacebar toggles checkboxes
Returns: ['option_2', 'option_3']
```

### select() - Single Select

```
questionary.select("Choose:", choices=[...])
                                  ↓
┌─────────────────────────────────┐
│ ◉ Option 1                      │
│ ○ Option 2                      │
│ ○ Option 3                      │
│ ○ Option 4                      │
└─────────────────────────────────┘
Arrow keys move selection
Returns: 'option_1'
```

---

## Real Example: Skills Selector

### Tier 1: Select Categories

```python
choices = [
    Choice(title=f"🐍 Python ({count} skills)", value="python"),
    Choice(title=f"📘 TypeScript ({count} skills)", value="typescript"),
    Choice(title=f"⚙️  Rust ({count} skills)", value="rust"),
]

selected = questionary.checkbox(
    "📂 Select Topic Groups:",
    choices=choices,
    style=MPM_STYLE
).ask()
```

What user sees:
```
📂 Select Topic Groups:
  ☐ 🐍 Python (5 skills)
  ☑ 📘 TypeScript (3 skills)
  ☐ ⚙️  Rust (2 skills)
```

User presses spacebar on Python, Python becomes checked:
```
  ☑ 🐍 Python (5 skills)
  ☑ 📘 TypeScript (3 skills)
  ☐ ⚙️  Rust (2 skills)
```

Result: `['python', 'typescript']`

---

### Tier 2: Select Skills from Category

```python
skills = [...]  # From selected category

choices = [
    Choice(
        title=f"1. tdd - Test-driven development (15K tokens)",
        value="tdd",
        checked="tdd" in mandatory_skills  # Pre-select required
    ),
    Choice(
        title=f"2. debug - Systematic debugging (20K tokens)",
        value="debug",
        checked="debug" in mandatory_skills
    ),
]

selected = questionary.checkbox(
    "Select TypeScript skills:",
    choices=choices,
    style=MPM_STYLE
).ask()
```

What user sees:
```
Select TypeScript skills:
  ☑ 1. tdd - Test-driven development (15K tokens)
  ☐ 2. debug - Systematic debugging (20K tokens)
```

Pre-checked items come from mandatory skills.
User can toggle any item (including pre-checked).

Result: `['tdd', 'debug']`

---

## Styling (MPM_STYLE)

### What gets styled

```
┌─────────────────────────────────────────┐
│ ? Prompt text here                      │ ← qmark + question
│   ☐ ✓ Option 1 - Description           │ ← pointer + highlighted
│   ☑ ✓ Option 2 - Description           │ ← selected
│   ☐ ✓ Option 3 - Description           │ ← pointer + highlighted
└─────────────────────────────────────────┘
```

### MPM_STYLE colors

```python
("qmark", "fg:cyan bold")       # Question mark: cyan + bold
("question", "bold")            # Question text: bold
("answer", "fg:cyan")           # Answer display: cyan
("pointer", "fg:cyan bold")     # Arrow pointer: cyan + bold
("highlighted", "fg:cyan bold") # Current row: cyan + bold
("selected", "fg:cyan")         # Selected item: cyan
```

Result: Consistent cyan theme across all questionary components

---

## Error Handling Visual

### User Presses Esc

```
Select items:
  ☐ Item 1
  ☐ Item 2
[User presses Esc]
                    ↓
result = None
                    ↓
if result is None:
    print("Selection cancelled")
```

### User Presses Enter with No Selection

```
Select items:
  ☐ Item 1
  ☐ Item 2
[User presses Enter]
                    ↓
result = []
                    ↓
if not result:
    print("No items selected")
```

### User Selects Items and Presses Enter

```
Select items:
  ☑ Item 1
  ☐ Item 2
  ☑ Item 3
[User presses Enter]
                    ↓
result = ['item1', 'item3']
                    ↓
print(f"Selected: {result}")
```

---

## Integration Checklist (Visual)

```
┌─ Step 1: Import ──────────────────────┐
│ import questionary                     │
│ from questionary import Choice         │
│ from ...questionary_styles MPM_STYLE   │
└────────────────────────────────────────┘
              ↓
┌─ Step 2: Prepare Data ────────────────┐
│ items = [...]                          │
│ pre_selected = {...}                   │
└────────────────────────────────────────┘
              ↓
┌─ Step 3: Create Choices ──────────────┐
│ choices = [                            │
│   Choice(title=..., value=...,         │
│   checked=id in pre_selected)          │
│   for item in items                    │
│ ]                                      │
└────────────────────────────────────────┘
              ↓
┌─ Step 4: Show Selection ──────────────┐
│ selected = questionary.checkbox(       │
│   "Prompt:",                           │
│   choices=choices,                     │
│   style=MPM_STYLE                      │
│ ).ask()                                │
└────────────────────────────────────────┘
              ↓
┌─ Step 5: Handle Result ───────────────┐
│ if selected is None:                   │
│     # User cancelled                   │
│ else:                                  │
│     # Process selected items           │
└────────────────────────────────────────┘

DONE! Spacebar toggling works automatically.
```

---

## Summary Diagram

```
                questionary.checkbox()
                         │
        ┌────────────────┼────────────────┐
        │                │                │
    Receives:        Shows:            Returns:
    - Choices       - Prompt text      - List of values
    - Style         - Checkboxes         or
    - Prompt        - Description      - None

                User interacts:
                - Arrow keys navigate
                - Spacebar toggles
                - Enter confirms
                - Esc cancels
```

That's the pattern! Simple, powerful, and built-in to questionary.
