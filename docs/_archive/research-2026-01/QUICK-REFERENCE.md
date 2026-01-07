# TUI Consistency: Quick Reference Guide

## The Problem in One Sentence
Agent Wizard and Skill Selector have **significantly different** TUI styling, making them feel like separate tools.

## Key Differences at a Glance

| Issue | Agent Wizard | Skill Selector | Fix |
|-------|--------------|----------------|-----|
| questionary style | 4 attrs | 6 attrs (question is white!) | Create shared module |
| Banner width | 60 chars | 70 chars | Standardize to 70 |
| Banner style | Emoji + text | Centered text | Add emoji to both |
| Choice format | Plain strings | questionary.Choice | Convert wizard to Choice |
| Choice parsing | Manual split | questionary native | Remove manual parsing |
| Emoji usage | Heavy (10+) | Light (3-4) | Standardize (recommend heavy) |
| Rich markup | Line 1304 broken | None | Remove broken markup |

## Severity Ratings

🔴 **HIGH** - Users see different colors and broken styling
- questionary.Style inconsistency (skill_selector's question is white, not cyan)
- Question text appears wrong color in skill_selector

🟡 **MEDIUM** - Code quality and maintainability issues
- Manual string parsing in agent_wizard
- Rich markup broken in agent_wizard
- Different banner widths and styles

🟢 **LOW** - Professional appearance
- Emoji usage inconsistency
- Should be standardized for cohesive branding

## Quick Fixes

### Fix #1: Create Shared questionary_styles.py (30 min)
```python
# NEW FILE: src/claude_mpm/cli/interactive/questionary_styles.py
from questionary import Style

QUESTIONARY_STYLE = Style([
    ("qmark", "fg:cyan bold"),
    ("question", "fg:cyan bold"),    # <-- Fixes skill_selector issue
    ("answer", "fg:cyan"),
    ("pointer", "fg:cyan bold"),
    ("highlighted", "fg:cyan bold"),
    ("selected", "fg:cyan"),
    ("checkbox", "fg:cyan"),
])
```

Then in both files:
```python
from .questionary_styles import QUESTIONARY_STYLE
# Remove local QUESTIONARY_STYLE definition
```

### Fix #2: Standardize Banners (15 min)
Both files should use:
```python
print("\n" + "=" * 70)
print("              BANNER TITLE HERE")
print("=" * 70)
```

### Fix #3: Fix Rich Markup (15 min)
Agent Wizard line 1304:
```python
# BAD:
print("[bold]Filter by:[/bold]")

# GOOD:
print("\nFilter by:")
```

### Fix #4: Convert Choices to questionary.Choice (1-2 hours)
Agent Wizard lines 359-394:
```python
# Use questionary.Choice objects instead of plain strings
# Remove manual parsing with split(".")[0]
```

### Fix #5: Standardize Emoji (30 min)
Pick one approach and apply to both:
- Option A: Keep agent_wizard's heavy emoji, add to skill_selector
- Option B: Reduce both to minimal emoji

Recommendation: **Option A (heavy emoji)** - modern and friendly

## Files to Change

```
CHANGE:
  src/claude_mpm/cli/interactive/agent_wizard.py
    Lines 27-34:   QUESTIONARY_STYLE (remove, import instead)
    Lines 116-120: Banner (width 60 → 70)
    Lines 359-394: Menu choices (convert to questionary.Choice)
    Line 1304:     "[bold]...[/bold]" (remove markup)

  src/claude_mpm/cli/interactive/skill_selector.py
    Lines 28-37:   QUESTIONARY_STYLE (remove, import instead)
    Lines 139-141: Banner (add emoji prefix)

CREATE:
  src/claude_mpm/cli/interactive/questionary_styles.py (NEW)
```

## Implementation Order

1. ✓ Create questionary_styles.py
2. ✓ Update imports in both files
3. ✓ Standardize banners (width + emoji)
4. ✓ Fix Rich markup
5. ✓ Convert agent_wizard to questionary.Choice
6. ✓ Test everything
7. ✓ Commit

**Total time: 3-4 hours including thorough testing**

## Testing

Quick visual test after changes:
```bash
# Run agent wizard
python -m claude_mpm.cli interactive agent-wizard

# Run skill selector (if accessible)
python -m claude_mpm.cli skill-selector

# Compare:
# - Banner widths should be identical
# - Colors should match exactly (both cyan)
# - No broken Rich markup
# - Smooth menu navigation
```

## Before vs After

### BEFORE (Inconsistent)
```
Agent Wizard:                    Skill Selector:
════════════════════════════     ══════════════════════════════════════════════
🧙‍♂️  Agent Creation Wizard       SKILL CONFIGURATION
════════════════════════════     ══════════════════════════════════════════════
(60 chars, emoji, informal)      (70 chars, centered, formal)

[cyan bold pointer]             [cyan pointer] (question is WHITE!)
```

### AFTER (Consistent)
```
Agent Wizard:                    Skill Selector:
══════════════════════════════════════════════════════════════════════════
          🧙 Agent Creation Wizard        📚 Skill Configuration
══════════════════════════════════════════════════════════════════════════
(70 chars, emoji centered)       (70 chars, emoji centered)

[cyan bold pointer]              [cyan bold pointer] (question is CYAN!)
```

## Key References

- **Detailed Analysis**: docs/research/tui-consistency-analysis-2025-01-02.md
- **Visual Comparison**: docs/research/tui-visual-comparison.md
- **Full Summary**: docs/research/TUI-CONSISTENCY-SUMMARY.txt

## Why This Matters

Users should feel like they're using the same tool when they switch between Agent Wizard and Skill Selector. Currently:
- Different styling makes them feel separate
- Inconsistent questionary style breaks visual harmony
- Fragile code in agent_wizard is hard to maintain

After fixes:
- Professional, unified appearance
- Code is more maintainable
- Better user experience

## Risk Assessment

🟢 **LOW RISK**
- No breaking changes
- No functional changes
- All changes are visual or code quality
- Fully reversible if needed
