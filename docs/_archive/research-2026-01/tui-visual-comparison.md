# TUI Visual Comparison: Side-by-Side Reference

## Overview
This document provides a visual comparison of how the two TUIs currently appear vs how they should appear after standardization.

---

## 1. QUESTIONARY STYLE - CURRENT vs UNIFIED

### Current Agent Wizard Style
```
Definition (lines 27-34):
QUESTIONARY_STYLE = Style([
    ("selected", "fg:cyan bold"),
    ("pointer", "fg:cyan bold"),
    ("highlighted", "fg:cyan"),
    ("question", "fg:cyan bold"),
])

Visual Result:
✓ Selected: [cyan bold text]
> Pointer:  [cyan bold text]
  Hovered:  [cyan text]
  Question: [cyan bold text]
```

### Current Skill Selector Style
```
Definition (lines 28-37):
QUESTIONARY_STYLE = Style([
    ("qmark", "fg:cyan bold"),
    ("question", "bold"),           <-- No cyan!
    ("answer", "fg:cyan"),
    ("pointer", "fg:cyan bold"),
    ("highlighted", "fg:cyan bold"),
    ("selected", "fg:cyan"),
])

Visual Result:
? [cyan bold qmark]
  [bold only question]             <-- INCONSISTENT
✓ [cyan answer]
> [cyan bold pointer]
  [cyan bold highlight]
✓ [cyan selected]
```

### UNIFIED STYLE (Proposed)
```python
QUESTIONARY_STYLE = Style([
    ("qmark", "fg:cyan bold"),
    ("question", "fg:cyan bold"),    <-- Consistent
    ("answer", "fg:cyan"),
    ("pointer", "fg:cyan bold"),
    ("highlighted", "fg:cyan bold"),
    ("selected", "fg:cyan"),
])

Visual Result:
? [cyan bold qmark]
  [cyan bold question]              <-- CONSISTENT
✓ [cyan answer]
> [cyan bold pointer]
  [cyan bold highlight]
✓ [cyan selected]
```

---

## 2. BANNER DISPLAY - CURRENT vs UNIFIED

### Current Agent Wizard Banner
```
Width: 60 chars
Style: Emoji + text + description

Output:
════════════════════════════════════════════════════════
🧙‍♂️  Agent Creation Wizard
════════════════════════════════════════════════════════

I'll guide you through creating a custom local agent.
Press Ctrl+C anytime to cancel.

Characteristics:
  ✓ Emoji-based branding
  ✓ Friendly tone
  ✓ Additional description below
  ✗ Inconsistent width
  ✗ Informal visual treatment
```

### Current Skill Selector Banner
```
Width: 70 chars
Style: Centered text, no emoji

Output:
══════════════════════════════════════════════════════════════════════════
                    SKILL CONFIGURATION
══════════════════════════════════════════════════════════════════════════

Characteristics:
  ✓ Professional centered layout
  ✗ No emoji branding
  ✗ Inconsistent width (70 vs 60)
  ✗ Formal, cold appearance
```

### UNIFIED BANNER (Proposed)
```
Width: 70 chars (standard)
Style: Emoji prefix + centered title (matches modern CLI UX)

Option 1 (Recommend - Best of both):
══════════════════════════════════════════════════════════════════════════
                    🧙 Agent Creation Wizard
══════════════════════════════════════════════════════════════════════════

Option 2 (Alternative - More formal):
══════════════════════════════════════════════════════════════════════════
                      AGENT CONFIGURATION
══════════════════════════════════════════════════════════════════════════

Usage:
  AGENT WIZARD: Use Option 1 with agent emoji (🧙)
  SKILL SELECTOR: Use Option 1 with skill emoji (📚)

Benefits:
  ✓ Consistent width across all wizards
  ✓ Consistent visual style
  ✓ Modern, professional appearance
  ✓ Branding maintained while staying consistent
```

---

## 3. MENU CHOICE FORMAT - CURRENT vs UNIFIED

### Current Agent Wizard Menu
```
Agent ID list: agent-1, agent-2, agent-3
Action: Deploy agent
Option: Export all agents

Code (lines 359-388):
menu_choices = []
for i, agent in enumerate(all_agents, 1):
    menu_choices.append(f"{i}. View agent: {agent['agent_id']}")

# Parsing (line 394):
choice_num = int(choice.split(".")[0])

Display:
┌─────────────────────────────────────────────────────────┐
│ Agent Management Menu:                                  │
│ ? [question with pointer]                               │
│   1. View agent: research-engineer                      │
│   2. View agent: backend-engineer                       │
│   3. View agent: qa-engineer                            │
│   6. Deploy agent                    <-- parsed from "6." │
│   7. Create new agent                <-- fragile parsing  │
│   ...                                                    │
└─────────────────────────────────────────────────────────┘

ISSUES:
  ✗ Manual parsing required
  ✗ Fragile string parsing (depends on exact "N. " format)
  ✗ Type conversion (string -> int)
  ✗ No separation of display vs value
  ✗ Cannot have "." in choice text safely
```

### Current Skill Selector Menu
```
Code (lines 187-188):
choice_text = f"{icon} {display_name} ({len(skills)} skills)"
choices.append(questionary.Choice(
    title=choice_text,
    value=toolchain
))

Display:
┌─────────────────────────────────────────────────────────┐
│ Select Topic Groups to Add Skills From:                 │
│ ✓ [pointer] 🌐 Universal (5 skills)                     │
│   ✓ 🐍 Python (12 skills)                               │
│   ✓ 📘 TypeScript (8 skills)                            │
│   ✓ ⚙️  Rust (3 skills)                                 │
└─────────────────────────────────────────────────────────┘

Selected value: "python" (directly, no parsing)

BENEFITS:
  ✓ questionary handles parsing
  ✓ Type-safe (value is the object, not a string)
  ✓ Display clearly separated from value
  ✓ No manual parsing code needed
  ✓ More maintainable
```

### UNIFIED MENU FORMAT (Proposed)
```python
# Apply Skill Selector's pattern to Agent Wizard

Code:
menu_choices = []

# For agent viewing
for i, agent in enumerate(all_agents, 1):
    menu_choices.append(
        questionary.Choice(
            title=f"{i}. View agent: {agent['agent_id']}",
            value=("view_agent", agent)
        )
    )

# For actions
menu_choices.append(
    questionary.Choice(
        title=f"{len(all_agents) + 1}. Deploy agent",
        value=("deploy", None)
    )
)

# Selection (no manual parsing!)
result = questionary.select(
    "Agent Management Menu:",
    choices=menu_choices,
    style=QUESTIONARY_STYLE,
).ask()

if result:
    action, data = result
    if action == "view_agent":
        # handle agent viewing
    elif action == "deploy":
        # handle deployment

Display:
┌─────────────────────────────────────────────────────────┐
│ Agent Management Menu:                                  │
│ ? [pointer] 1. View agent: research-engineer            │
│   2. View agent: backend-engineer                       │
│   3. View agent: qa-engineer                            │
│   6. Deploy agent                    <-- No parsing!    │
│   7. Create new agent                <-- Type-safe      │
│   ...                                                    │
└─────────────────────────────────────────────────────────┘

BENEFITS:
  ✓ No manual string parsing
  ✓ Type-safe value passing
  ✓ Cleaner code
  ✓ Matches skill_selector pattern
  ✓ Easier to maintain
```

---

## 4. EMOJI USAGE - CURRENT vs UNIFIED

### Current Agent Wizard Emoji Usage
```
Heavy emoji throughout:
  🧙‍♂️ Agent Creation Wizard (banner)
  🔧 Agent Management Menu
  📭 No agents found
  📋 Found N agents
  ✓ Deployed status
  📄 Agent Details
  📑 Agent Configuration Preview
  🗑️ Delete Agent
  ✏️ Editing Agent
  ✅ Success messages
  ❌ Error messages
  🚀 Deployment messages
  📦 Deploy Agent section
  🔍 Browse & Filter Agents
  🔗 Manage Agent Sources

Pattern: Very visual, emoji-heavy, modern style
Impact: Friendly, approachable, modern appearance
```

### Current Skill Selector Emoji Usage
```
Light emoji usage:
  📂 Select Topic Groups (section)
  📦 Agent-Required Skills (section)
  ✓ Checked items
  ⚠️ Warnings

Pattern: Minimal, functional emoji only
Impact: Professional, restrained, less visual
```

### UNIFIED EMOJI USAGE (Proposed - Option A: Heavy Emoji)
```
Both should use: emoji + text for major sections

Agent Wizard (current - keep):
  🧙‍♂️ Agent Creation Wizard
  🔧 Agent Management Menu
  ...all current emoji...

Skill Selector (update to match):
  📚 Skill Configuration (was: SKILL CONFIGURATION)
  📦 Agent-Required Skills (keep current)
  🐍 Python Skills (icon already shown)
  📘 TypeScript Skills
  ...etc

Benefits:
  ✓ Consistent visual language
  ✓ Modern, friendly appearance
  ✓ Better visual scannability
  ✓ Professional yet approachable
```

---

## 5. CHOICE PRE-SELECTION - COMPARISON

### Agent Wizard (Current)
```
Selection type: Single-select
Pre-selected items: N/A (single-select doesn't support)
Checkbox display: N/A

Code: questionary.select(...) only
```

### Skill Selector (Current)
```
Selection type: Multi-select
Pre-selected items: YES - shows "[auto]" prefix
Checkbox display: Shows checked boxes (✓)

Code (lines 228-234):
already_selected = skill.name in self.agent_skill_deps
prefix = "[auto] " if already_selected else ""
choice = questionary.Choice(
    title=f"{prefix}{skill.display_name}",
    value=skill.name,
    checked=already_selected,  <-- THIS IS KEY
)

Display:
┌─────────────────────────────────────────────────────────┐
│ Select Python skills to include:                        │
│ ✓ [auto] pytest (25K tokens)        <-- Pre-checked    │
│ ✓ [auto] black (15K tokens)         <-- Pre-checked    │
│ ☐ [  ] MyPy (8K tokens)             <-- Not checked    │
│ ✓ NumPy (20K tokens)                <-- User selected   │
└─────────────────────────────────────────────────────────┘

Benefits:
  ✓ Users see what's auto-included
  ✓ Clear dependency visualization
  ✓ Better understanding of choices
  ✓ Professional UX
```

### Agent Wizard Could Use Similar Pattern
```
If Agent Wizard used checkbox (multi-select deployments):
  ✓ [auto] research-agent      <-- Auto-required by preset
  ☐ [ ] backend-engineer
  ✓ qa-engineer                <-- User selected

But: Agent Wizard currently uses single-select, which is appropriate
for its use case (one action at a time).
```

---

## 6. CURRENT vs PROPOSED: Side-by-Side Terminal Output

### CURRENT AGENT WIZARD FLOW
```
════════════════════════════════════════════════════════
🧙‍♂️  Agent Creation Wizard
════════════════════════════════════════════════════════

I'll guide you through creating a custom local agent.
Press Ctrl+C anytime to cancel.

📋 Found 3 agent(s):

#   Agent ID         Name            Source        Status
─────────────────────────────────────────────────────────
1   research-agent   Research Agent  [project]     ✓ Deployed
2   backend-eng      Backend Eng     [system]      Available
3   qa-specialist    QA Specialist   [system]      Available

Agent Management Menu:
? [pointer] 1. View agent: research-agent
  2. View agent: backend-eng
  3. View agent: qa-specialist
  4. Deploy agent
  5. Create new agent
  ...

Issues visible:
  - Inconsistent emoji styling
  - Plain string choices
```

### CURRENT SKILL SELECTOR FLOW
```
══════════════════════════════════════════════════════════════════════════
                    SKILL CONFIGURATION
══════════════════════════════════════════════════════════════════════════

📦 Agent-Required Skills (auto-included):
  ✓ pytest
  ✓ black

📂 Select Topic Groups to Add Skills From:
✓ [pointer] 🌐 Universal (5 skills)
  ✓ 🐍 Python (12 skills)
  ✓ 📘 TypeScript (8 skills)

🐍 Python Skills:
✓ [auto] pytest (25K tokens)
☐ [ ] black (15K tokens)
☐ [ ] mypy (8K tokens)

Issues visible:
  - Different banner style from Agent Wizard
  - Different emoji usage pattern
```

### PROPOSED UNIFIED FLOW

#### Agent Wizard (After Changes)
```
══════════════════════════════════════════════════════════════════════════
                      🧙 Agent Creation Wizard
══════════════════════════════════════════════════════════════════════════

I'll guide you through creating a custom local agent.
Press Ctrl+C anytime to cancel.

📋 Found 3 agent(s):

#   Agent ID         Name            Source        Status
─────────────────────────────────────────────────────────
1   research-agent   Research Agent  [project]     ✓ Deployed
2   backend-eng      Backend Eng     [system]      Available
3   qa-specialist    QA Specialist   [system]      Available

Agent Management Menu:
? [pointer] 1. View agent: research-agent
  2. View agent: backend-eng
  3. View agent: qa-specialist
  ─────────────────────────────────
  4. Deploy agent
  5. Create new agent
  ...

Changes:
  + Banner now 70 chars wide
  + Consistent style with other wizards
  + Better choice format (internally)
  + Menu separator for organization
```

#### Skill Selector (After Changes)
```
══════════════════════════════════════════════════════════════════════════
                       📚 Skill Configuration
══════════════════════════════════════════════════════════════════════════

📦 Agent-Required Skills (auto-included):
  ✓ pytest
  ✓ black

📂 Select Topic Groups to Add Skills From:
✓ [pointer] 🌐 Universal (5 skills)
  ✓ 🐍 Python (12 skills)
  ✓ 📘 TypeScript (8 skills)

🐍 Python Skills:
✓ [auto] pytest (25K tokens)
☐ [ ] black (15K tokens)
☐ [ ] mypy (8K tokens)

Changes:
  + Added emoji to banner for consistency
  + Banner width already 70 (correct)
  + Everything else stays the same (already good)
```

---

## 7. Color Swatches - QUESTIONARY_STYLE Attributes

### Agent Wizard (Current 4 attrs)
```
selected      = fg:cyan bold       (bright cyan, bold)
pointer       = fg:cyan bold       (bright cyan, bold)
highlighted   = fg:cyan            (bright cyan)
question      = fg:cyan bold       (bright cyan, bold)

Visual representation:
┌────────────────────────────────────────────┐
│ Selected:     ██████  (cyan bold)          │
│ Pointer:      ██████  (cyan bold)          │
│ Highlighted:  ██████  (cyan)               │
│ Question:     ██████  (cyan bold)          │
└────────────────────────────────────────────┘

Consistency: Good (all cyan family)
Coverage: Minimal (only 4 states)
```

### Skill Selector (Current 6 attrs)
```
qmark         = fg:cyan bold       (bright cyan, bold)
question      = bold               (white bold, no cyan) ✗ INCONSISTENT
answer        = fg:cyan            (bright cyan)
pointer       = fg:cyan bold       (bright cyan, bold)
highlighted   = fg:cyan bold       (bright cyan, bold)
selected      = fg:cyan            (bright cyan)

Visual representation:
┌────────────────────────────────────────────┐
│ QMark:        ██████  (cyan bold)          │
│ Question:     ██████  (white bold) ✗ INCONSISTENT
│ Answer:       ██████  (cyan)               │
│ Pointer:      ██████  (cyan bold)          │
│ Highlighted:  ██████  (cyan bold)          │
│ Selected:     ██████  (cyan)               │
└────────────────────────────────────────────┘

Consistency: Poor (question is different color)
Coverage: Good (6 states)
```

### Unified (Proposed 7 attrs)
```
qmark         = fg:cyan bold       (bright cyan, bold)
question      = fg:cyan bold       (bright cyan, bold) ✓ FIXED
answer        = fg:cyan            (bright cyan)
pointer       = fg:cyan bold       (bright cyan, bold)
highlighted   = fg:cyan bold       (bright cyan, bold)
selected      = fg:cyan            (bright cyan)
checkbox      = fg:cyan            (bright cyan)

Visual representation:
┌────────────────────────────────────────────┐
│ QMark:        ██████  (cyan bold)          │
│ Question:     ██████  (cyan bold)  ✓ FIXED │
│ Answer:       ██████  (cyan)               │
│ Pointer:      ██████  (cyan bold)          │
│ Highlighted:  ██████  (cyan bold)          │
│ Selected:     ██████  (cyan)               │
│ Checkbox:     ██████  (cyan)               │
└────────────────────────────────────────────┘

Consistency: Excellent (all cyan family)
Coverage: Excellent (7 states + checkbox)
```

---

## Summary: What Users Will See

### Before Fixes
```
User switches between Agent Wizard and Skill Selector:

Agent Wizard:
  - Friendly emoji banners
  - 60-char wide headers
  - Cyan bold styling
  - Heavy emoji usage
  - Informal tone

Skill Selector:
  - Centered text banner (no emoji)
  - 70-char wide headers
  - Inconsistent cyan styling (question is white!)
  - Light emoji usage
  - Formal tone

User Experience:
  "Why do these look like different tools?"
  "The question text looks different..."
  "Inconsistent styling is jarring"
```

### After Fixes
```
User switches between Agent Wizard and Skill Selector:

Both wizards now have:
  - Consistent emoji branding (🧙 for agents, 📚 for skills)
  - Same 70-char wide headers
  - Unified cyan styling (consistent across all attributes)
  - Modern, clean appearance
  - Professional yet friendly tone
  - Same interaction patterns (questionary.Choice objects)

User Experience:
  "These are clearly part of the same tool"
  "Styling is clean and consistent"
  "Modern, professional appearance"
```

---

## Testing Visual Consistency

When implementing changes, verify:

1. **Colors match exactly** - Hold agent_wizard and skill_selector side-by-side
2. **Banner widths are same** - Both should be 70 chars
3. **Emoji display identically** - No rendering differences
4. **Question styling is identical** - Test with long questions to ensure no color difference
5. **Menu selections work smoothly** - No parsing errors, smooth navigation
6. **Checkboxes pre-select properly** - Agent deps show as checked
7. **Separated from actual functionality** - Visual changes don't affect behavior

---

## References

**Files Involved:**
- `src/claude_mpm/cli/interactive/agent_wizard.py` - Lines 27-34 (style), 116-120 (banner), 359-394 (menu)
- `src/claude_mpm/cli/interactive/skill_selector.py` - Lines 28-37 (style), 139-141 (banner), 175-248 (menu)
- `src/claude_mpm/cli/commands/configure.py` - Lines 53-65 (reference style)

**Related Issues:**
- Visual consistency across interactive wizards
- Code maintainability (manual parsing vs questionary native)
- User experience (confused by inconsistent styling)

