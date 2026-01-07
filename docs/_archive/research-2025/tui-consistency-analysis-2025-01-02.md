# TUI Consistency Analysis: Agent Selector vs Skill Selector

## Executive Summary

The **Agent Selector** (`agent_wizard.py`) and **Skill Selector** (`skill_selector.py`) have **SIGNIFICANT INCONSISTENCIES** in their TUI implementations. While both use `questionary`, they differ substantially in styling, UI patterns, and visual presentation.

---

## Critical Inconsistencies

### 1. QUESTIONARY STYLE DEFINITIONS

#### Agent Wizard (agent_wizard.py, lines 27-34)
```python
QUESTIONARY_STYLE = Style(
    [
        ("selected", "fg:cyan bold"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan"),
        ("question", "fg:cyan bold"),
    ]
)
```
**Characteristics:**
- Cyan theme (4 attributes)
- Simple, minimal styling
- No checkbox customization
- Same color for selected/pointer/question

#### Skill Selector (skill_selector.py, lines 28-37)
```python
QUESTIONARY_STYLE = Style(
    [
        ("qmark", "fg:cyan bold"),
        ("question", "bold"),
        ("answer", "fg:cyan"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan bold"),
        ("selected", "fg:cyan"),
    ]
)
```
**Characteristics:**
- 6 attributes (more comprehensive)
- Cyan with varying boldness
- Includes qmark and answer styling
- Slightly different highlighted styling
- `question` is bold without cyan (breaks pattern)

#### Configure.py (reference pattern, lines 53-65)
```python
QUESTIONARY_STYLE = Style(
    [
        ("selected", "fg:#e0e0e0 bold"),
        ("pointer", "fg:#ffd700 bold"),
        ("highlighted", "fg:#e0e0e0"),
        ("question", "fg:#e0e0e0 bold"),
        ("checkbox", "fg:#00ff00"),
        ("checkbox-selected", "fg:#00ff00 bold"),
    ]
)
```
**Characteristics:**
- Uses hex color codes (#e0e0e0, #ffd700, #00ff00)
- Has checkbox-specific styling
- More mature/polished appearance
- 6 attributes with checkbox specialization

### Key Difference
Agent wizard uses only 4 basic attributes, while Skill selector uses 6. The Skill selector's `question` attribute is `bold` without color, which may appear different than expected.

---

## 2. UI COMPONENTS & SELECTION PATTERNS

### Agent Selector
- **questionary.select()** - Single-select with arrow navigation (line 384)
- **questionary.select()** - For agent management menu (line 1314, 1345, etc.)
- Plain text menu choices (strings only)
- Example: `menu_choices.append(f"{i}. View agent: {agent['agent_id']}")`

### Skill Selector
- **questionary.checkbox()** - Multi-select for topic groups (line 195)
- **questionary.checkbox()** - Multi-select for skills within groups (line 238)
- questionary.Choice objects with explicit titles/values
- Pre-checks items (line 233: `checked=already_selected`)
- Example:
  ```python
  choices.append(questionary.Choice(
      title=f"{prefix}{skill.display_name}",
      value=skill.name,
      checked=already_selected,
  ))
  ```

### Key Differences
1. **Selection Type**: Agent uses single-select exclusively; Skill uses multi-select exclusively
2. **Choice Format**: Agent passes plain strings; Skill properly uses questionary.Choice() objects
3. **Choice Parsing**: Agent manually parses with `split(".")[0]`; Skill uses questionary's built-in value separation

**Impact**: The Choice object approach in Skill Selector is more robust and maintainable.

---

## 3. BANNER/HEADER STYLING

### Agent Wizard (lines 116-120)
```python
print("\n" + "=" * 60)
print("🧙‍♂️  Agent Creation Wizard")
print("=" * 60)
print("\nI'll guide you through creating a custom local agent.")
```
**Style:**
- ASCII separator (====)
- Emoji icon in title
- 60-character width
- Plain text description below
- Informal, friendly tone

### Skill Selector (lines 139-141)
```python
print("\n" + "=" * 70)
print("                    SKILL CONFIGURATION")
print("=" * 70)
```
**Style:**
- ASCII separator (====)
- Centered text using spaces
- 70-character width
- No emoji
- Formal, centered layout

### Key Differences
1. **Width**: 60 chars vs 70 chars (inconsistent)
2. **Visual Style**: Emoji icon vs centered text (different aesthetics)
3. **Tone**: Friendly vs formal (jarring contrast)

---

## 4. OUTPUT/PRESENTATION PATTERNS

### Agent Wizard
- Inline printing for progress/results
- Examples (lines 1481-1486):
  ```python
  print("  [d] Deploy agent from this list")
  print("  [v] View agent details")
  print("  [n] New filter")
  print("  [b] Back to main menu")
  ```
- Heavy emoji usage (✅, ❌, 🚀, 🧙‍♂️, 📦, 🔧, etc.)
- Rich markup in plain print (line 1304: `[bold]Filter by:[/bold]`)
- Inconsistent: Rich markup won't render in standard print

### Skill Selector
- Grouped output sections
- Examples (lines 170-173):
  ```python
  print("\n📦 Agent-Required Skills (auto-included):")
  for skill_name in sorted(self.agent_skill_deps):
      print(f"  ✓ {skill_name}")
  print()
  ```
- Light/minimal emoji (mainly 📦, ✓, ⚠️)
- Pure print statements, no Rich markup
- Consistent: All output is plain text

### Key Differences
1. **Emoji Usage**: Heavy (agent) vs light (skill) - inconsistent branding
2. **Rich Markup**: Agent uses `[bold]` in print statements, which won't render correctly
3. **Structure**: Agent is more varied; Skill is more structured/grouped

---

## 5. MENU CHOICE FORMATTING

### Agent Wizard (line 363)
```python
menu_choices.append(f"{i}. View agent: {agent['agent_id']}")
```
**Format:** `"1. View agent: agent-id"`
**Parsing:** `choice_num = int(choice.split(".")[0])`

**Issues:**
- Manual parsing required
- Fragile: depends on exact format with period
- No type safety (string -> int parsing)

### Skill Selector (lines 187-188)
```python
choice_text = f"{icon} {display_name} ({len(skills)} skills)"
choices.append(questionary.Choice(title=choice_text, value=toolchain))
```
**Format:** `"🐍 Python (15 skills)"`
**Parsing:** Handled by questionary - selected value is the toolchain directly

**Advantages:**
- questionary handles parsing
- Type-safe: value is directly the correct type
- Display (title) separated from value
- Icon + metadata + count provides better UX

---

## 6. CHOICE OBJECT USAGE

### Agent Wizard (PROBLEM)
Uses plain strings throughout:
```python
menu_choices.append(f"{i}. View agent: {agent['agent_id']}")
choice = questionary.select(
    "Agent Management Menu:",
    choices=menu_choices,
    style=QUESTIONARY_STYLE,
).ask()
```

**Problem**: questionary.select() can accept strings, but this doesn't separate title from value. It uses the string as both.

### Skill Selector (CORRECT)
Uses questionary.Choice objects:
```python
choices.append(questionary.Choice(title=choice_text, value=toolchain))
selected = questionary.checkbox(
    "📂 Select Topic Groups to Add Skills From:",
    choices=choices,
    style=QUESTIONARY_STYLE,
).ask()
```

**Benefit**: Clear separation of display text and return value. Selected values are the actual objects.

---

## 7. STATE MANAGEMENT

### Agent Wizard
- **Pre-checked items**: Not supported (uses select, not checkbox)
- **Agent dependencies**: Not tracked

### Skill Selector
- **Pre-checked items**: YES - marks auto-included skills as checked
- **Agent dependencies**: Tracks and shows which skills are required by deployed agents
- **Visual feedback**: "[auto] " prefix shows pre-selected items

---

## Summary Table

| Aspect | Agent Wizard | Skill Selector | Status |
|--------|--------------|----------------|--------|
| **Style Colors** | Simple cyan only | Cyan + variants | INCONSISTENT |
| **Style Attributes** | 4 attrs | 6 attrs | INCONSISTENT |
| **Color Format** | Named (fg:cyan) | Named (fg:cyan) | CONSISTENT |
| **Selection Type** | Single only (select) | Multi only (checkbox) | DIFFERENT (appropriate) |
| **Choice Format** | Plain strings | questionary.Choice | INCONSISTENT |
| **Choice Value Parsing** | Manual string split | questionary native | INCONSISTENT |
| **Banner Width** | 60 chars | 70 chars | INCONSISTENT |
| **Banner Style** | Emoji + text | Centered text | INCONSISTENT |
| **Banner Tone** | Friendly informal | Formal centered | INCONSISTENT |
| **Output Emoji** | Heavy usage (🧙, 🚀) | Light usage (📦, ✓) | INCONSISTENT |
| **Rich Markup** | Yes (broken - in print) | No (pure print) | INCONSISTENT |
| **Pre-checked Items** | N/A (single-select) | Yes (checked=...) | N/A |
| **Dependency Display** | Not shown | Shown with "[auto]" | INCONSISTENT |

---

## Recommended Changes

### Priority 1: Unified QUESTIONARY_STYLE Definition
**File**: Create `src/claude_mpm/cli/interactive/questionary_styles.py`

```python
"""Shared questionary styles for consistent CLI experience."""

from questionary import Style

# Main questionary style used across all interactive wizards
QUESTIONARY_STYLE = Style(
    [
        ("qmark", "fg:cyan bold"),
        ("question", "fg:cyan bold"),
        ("answer", "fg:cyan"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan bold"),
        ("selected", "fg:cyan"),
        ("checkbox", "fg:cyan"),
        ("checkbox-selected", "fg:cyan bold"),
    ]
)
```

**Update**:
- `agent_wizard.py`: Import from shared styles module
- `skill_selector.py`: Import from shared styles module
- Remove local definitions

### Priority 2: Standardize Banner Format
**Both files should use**:
```python
print("\n" + "=" * 70)
print("SECTION TITLE")
print("=" * 70)
```

**Specific changes**:
- Agent wizard: Change width from 60 to 70
- Skill selector: Add optional emoji prefix if desired
- Remove emoji from title text itself; use console output before banner instead

### Priority 3: Convert Agent Wizard to questionary.Choice
**Agent Wizard (lines 359-388)** - Menu selection:

```python
# BUILD: Change from plain strings to Choice objects
menu_choices_values = []
for i, agent in enumerate(all_agents, 1):
    title = f"{i}. View agent: {agent['agent_id']}"
    menu_choices_values.append(
        questionary.Choice(title=title, value=("agent", agent))
    )

# Add separator
menu_choices_values.append(questionary.Separator())

# Add actions (similarly converted)
menu_choices_values.append(
    questionary.Choice(
        title=f"{len(all_agents) + 1}. Deploy agent",
        value=("deploy", None),
    )
)

# ... rest of actions

# SELECT: Now we get back the actual object, not a string
choice_result = questionary.select(
    "Agent Management Menu:",
    choices=menu_choices_values,
    style=QUESTIONARY_STYLE,
).ask()

# PARSE: No manual parsing needed
if choice_result:
    action_type, agent_or_none = choice_result
    if action_type == "agent":
        selected_agent = agent_or_none
        # handle viewing agent
    elif action_type == "deploy":
        # handle deploy
```

**Benefits**:
- No manual string parsing
- Type-safe
- Cleaner code
- Matches skill_selector pattern

### Priority 4: Standardize Emoji Usage
**Option A: Heavy Emoji (Recommended)**
- Keep agent_wizard's current emoji usage
- Add emoji to skill_selector's output:
  - Replace `"📦 Agent-Required Skills"` prefix with section emoji
  - Use consistent icons across both

**Option B: Light Emoji**
- Reduce agent_wizard emoji usage
- Keep minimal emoji for visual breaks only

**Recommendation**: Option A (heavy) because:
- More modern, visually appealing
- Agent wizard already established this pattern
- Helps users quickly scan sections

### Priority 5: Remove Rich Markup from Print Statements
**Agent Wizard (line 1304)**
```python
# BAD (current):
print("[bold]Filter by:[/bold]")

# GOOD (fixed):
print("\nFilter by:")
```

**Reason**: Rich markup (`[bold]`, etc.) only works with Rich's Console.print(), not standard print(). The current code won't render the bold formatting.

### Priority 6: Add Separator Support to Agent Wizard
**Enhancement** (optional but improves UX):

```python
menu_choices_values = []

# Add agent viewing options
for i, agent in enumerate(all_agents, 1):
    menu_choices_values.append(
        questionary.Choice(title=f"{i}. View agent: {agent['agent_id']}", value=...)
    )

# Visual separator
menu_choices_values.append(questionary.Separator("--- Actions ---"))

# Add action options
menu_choices_values.append(questionary.Choice(title="1. Deploy agent", value=...))
```

**Benefits**: Improves menu organization, matches modern CLI patterns

---

## Implementation Plan

### Phase 1: Setup (Low Risk)
1. Create `questionary_styles.py` with shared style
2. Update imports in both files
3. Test visual consistency

### Phase 2: Banner Standardization (Low Risk)
1. Change agent_wizard banner width to 70
2. Ensure consistent formatting
3. Verify alignment

### Phase 3: Choice Object Migration (Medium Risk)
1. Update agent_wizard menus to use questionary.Choice
2. Remove manual parsing logic
3. Test all menu flows thoroughly
4. Verify backward compatibility

### Phase 4: Emoji & Markup Cleanup (Low Risk)
1. Remove Rich markup from print statements
2. Standardize emoji usage
3. Update documentation if needed

### Phase 5: Polish (Optional)
1. Add questionary.Separator() for menu organization
2. Consider skill_selector enhancements
3. Add preference for pre-selection display

---

## Testing Checklist

- [ ] Agent wizard banner displays correctly
- [ ] Skill selector banner displays correctly
- [ ] Agent menu selections work without parsing errors
- [ ] Skill multi-select checkbox displays correctly
- [ ] Pre-checked items show properly in skill selector
- [ ] Emoji render correctly in all outputs
- [ ] Rich markup removed from plain print statements
- [ ] Questionary style applies consistently
- [ ] Cyan colors are consistent across both UIs
- [ ] No visual jarring when switching between wizards

---

## File Locations

**Files to Modify:**
1. `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/agent_wizard.py` (lines 27-34)
2. `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/skill_selector.py` (lines 28-37)

**File to Create:**
1. `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/questionary_styles.py` (NEW)

---

## Key Takeaways

| Finding | Severity | Impact |
|---------|----------|--------|
| Different QUESTIONARY_STYLE definitions | High | Users see inconsistent colors/formatting |
| Plain strings vs questionary.Choice | High | Code is fragile, harder to maintain |
| Manual string parsing | Medium | Error-prone, unclear intent |
| Emoji usage inconsistency | Medium | Looks unprofessional, inconsistent branding |
| Rich markup in print() | Medium | Markup won't render correctly |
| Different banner styles | Low | Visual inconsistency |
| Different banner widths | Low | Alignment issues |

All issues are fixable without breaking changes.
