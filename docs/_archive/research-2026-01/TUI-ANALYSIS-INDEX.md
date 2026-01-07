# TUI Consistency Analysis - Research Index

## Project
Claude MPM - Multi-Agent Project Manager

## Analysis Date
January 2, 2025

## Objective
Compare the Agent Selector TUI (`agent_wizard.py`) and Skill Selector TUI (`skill_selector.py`) to identify inconsistencies and provide implementation recommendations.

---

## Research Documents

### 1. **QUICK-REFERENCE.md** (Start Here)
**Best for**: Quick overview, executive summary
- One-sentence problem statement
- Quick differences table with severity ratings
- Five key fixes with time estimates
- Before/after visual examples
- Key references and risk assessment

**When to use**: First thing to read when reviewing the analysis

---

### 2. **COMPARISON-SUMMARY.txt** (Detailed Overview)
**Best for**: Complete understanding of all inconsistencies
- Answers all 5 specific questions you asked
- Key inconsistencies listing with severity
- Comprehensive comparison table
- Detailed findings with code examples
- What needs to change and time estimates

**When to use**: Understanding the full scope of issues

---

### 3. **TUI-CONSISTENCY-ANALYSIS-2025-01-02.md** (Deep Dive)
**Best for**: Implementation planning and detailed code review
- Executive summary and critical inconsistencies
- 7 detailed comparison sections
- Code examples and line-by-line analysis
- Summary table (20+ rows)
- Recommended changes by priority (1-6)
- Detailed implementation plan (5 phases)
- Testing checklist
- File locations and line numbers

**When to use**: Planning actual implementation work

---

### 4. **tui-visual-comparison.md** (Visual Reference)
**Best for**: Understanding visual appearance and user experience impact
- Side-by-side visual comparisons
- questionary.Style color swatches
- Terminal output examples
- Before/after mockups
- UI component patterns
- Visual consistency testing guide

**When to use**: Understanding the visual impact, designing UI changes

---

### 5. **TUI-CONSISTENCY-SUMMARY.txt** (Implementation Reference)
**Best for**: During implementation, as a checklist
- Quick answer to "do they match?" (NO - 7 ways)
- Key findings with severity ratings
- Detailed comparison by aspect
- Fixes required (by priority)
- Files affected with line numbers
- Impact assessment
- Testing checklist
- References and next steps

**When to use**: During implementation as a reference guide

---

## Quick Navigation

### If you want to...

**...understand the problem quickly**
→ Read: QUICK-REFERENCE.md (5 min)

**...get all the details**
→ Read: COMPARISON-SUMMARY.txt (15 min)

**...plan the implementation**
→ Read: TUI-CONSISTENCY-ANALYSIS-2025-01-02.md (30 min)

**...see visual examples**
→ Read: tui-visual-comparison.md (20 min)

**...implement the fixes**
→ Use: TUI-CONSISTENCY-SUMMARY.txt as checklist

---

## Key Findings Summary

### The Problem
Agent Selector and Skill Selector have **SIGNIFICANTLY DIFFERENT** TUI styling, making them feel like separate tools.

### Critical Issues (HIGH SEVERITY)
1. **questionary.Style mismatch** - Skill Selector's question text is white instead of cyan
2. **Banner width inconsistency** - 60 vs 70 characters
3. **questionary implementation differs** - Manual parsing vs native questionary
4. **Rich markup broken** - Markup renders as literal text

### Medium Issues (MEDIUM SEVERITY)
5. Emoji usage inconsistent (heavy vs light)
6. Tone differs (friendly vs formal)
7. Code maintainability issues

### Low Issues (LOW SEVERITY)
8. Professional appearance needs polish

---

## Recommended Fixes (In Order)

| Priority | Issue | Time | Impact | Risk |
|----------|-------|------|--------|------|
| 1 | Create shared questionary_styles.py | 30 min | HIGH (fixes colors) | LOW |
| 2 | Standardize banners (70 char width) | 15 min | MEDIUM (appearance) | LOW |
| 3 | Fix Rich markup (remove from print) | 15 min | MEDIUM (rendering) | LOW |
| 4 | Convert to questionary.Choice objects | 1-2 hrs | MEDIUM (code quality) | LOW |
| 5 | Standardize emoji usage | 30 min | LOW (branding) | LOW |

**Total Time**: 3-4 hours (including testing)
**Total Risk**: LOW (no breaking changes, fully reversible)

---

## Files to Modify

```
CHANGE:
  src/claude_mpm/cli/interactive/agent_wizard.py
    Lines 27-34:   QUESTIONARY_STYLE
    Lines 116-120: Banner
    Lines 359-394: Menu choices
    Line 1304:     Rich markup

  src/claude_mpm/cli/interactive/skill_selector.py
    Lines 28-37:   QUESTIONARY_STYLE
    Lines 139-141: Banner

CREATE:
  src/claude_mpm/cli/interactive/questionary_styles.py (NEW)
```

---

## Your Specific Questions - Answered

### 1. "Does the agent selector use checkbox multi-select or single select?"
**Answer**: SINGLE SELECT
- Uses `questionary.select()`
- Plain string choices: `"1. View agent: agent-id"`
- Single selection at a time

### 2. "Does the skill selector match that pattern?"
**Answer**: NO - Uses MULTI SELECT
- Uses `questionary.checkbox()`
- questionary.Choice objects
- Multiple selections allowed

### 3. "Are the console banners/headers styled the same way?"
**Answer**: NO
- Agent: 60 chars, emoji + text, informal
- Skill: 70 chars, centered text, formal
- Inconsistent widths and visual style

### 4. "Do both use Rich console for output?"
**Answer**: NO (with broken markup)
- Agent: Mixes Rich markup with plain print (broken)
- Skill: Pure print statements only
- Agent's `[bold]` markup won't render

### 5. "Is the selection flow similar?"
**Answer**: SOMEWHAT (but different)
- Both use questionary
- Different components (select vs checkbox)
- Different parsing (manual vs native)
- Appropriate for use cases but inconsistent

---

## Comparison Table at a Glance

| Aspect | Agent Wizard | Skill Selector | Status |
|--------|--------------|----------------|--------|
| questionary style attributes | 4 | 6 | INCONSISTENT |
| Question text color | cyan bold | bold (white!) | BROKEN |
| Selection type | single-select | multi-select | BY DESIGN |
| Choice implementation | plain strings | questionary.Choice | CODE QUALITY |
| Banner width | 60 chars | 70 chars | INCONSISTENT |
| Banner style | emoji + text | centered text | INCONSISTENT |
| Rich markup | yes (broken) | no | INCONSISTENT |
| Emoji usage | heavy (10+) | light (3-4) | INCONSISTENT |

---

## Implementation Phases

### Phase 1: Setup (Low Risk) - 30 min
- Create questionary_styles.py
- Update imports
- Visual tests

### Phase 2: Appearance (Low Risk) - 15 min
- Standardize banner width to 70
- Ensure consistent formatting

### Phase 3: Code Quality (Medium Risk) - 1-2 hours
- Convert agent_wizard menus to questionary.Choice
- Remove manual parsing
- Test all flows

### Phase 4: Cleanup (Low Risk) - 45 min
- Fix Rich markup
- Standardize emoji
- Final polish

---

## Testing Checklist

- [ ] Banner widths identical (70 chars)
- [ ] Cyan colors identical across both
- [ ] No broken Rich markup
- [ ] Menu navigation smooth
- [ ] Checkbox pre-selection works
- [ ] No parsing errors
- [ ] Professional appearance
- [ ] User confusion eliminated

---

## Success Criteria

After implementation:
- Both wizards feel like they're part of the same tool
- Consistent visual style across all interactive components
- More maintainable code (fewer manual parsing hacks)
- Professional, modern appearance
- No breaking changes to functionality

---

## References

**Source Files**:
- `src/claude_mpm/cli/interactive/agent_wizard.py`
- `src/claude_mpm/cli/interactive/skill_selector.py`
- `src/claude_mpm/cli/commands/configure.py` (reference style)

**Research Documents** (in this directory):
1. QUICK-REFERENCE.md
2. COMPARISON-SUMMARY.txt
3. TUI-CONSISTENCY-ANALYSIS-2025-01-02.md
4. tui-visual-comparison.md
5. TUI-CONSISTENCY-SUMMARY.txt
6. TUI-ANALYSIS-INDEX.md (this file)

---

## Document Overview

```
TUI-ANALYSIS-INDEX.md (this file)
├── QUICK-REFERENCE.md ..................... 2 min read
├── COMPARISON-SUMMARY.txt ................. 10 min read
├── TUI-CONSISTENCY-ANALYSIS-2025-01-02.md. 30 min read
├── tui-visual-comparison.md ............... 20 min read
└── TUI-CONSISTENCY-SUMMARY.txt ............ 15 min read
```

---

## Getting Started

1. **Read QUICK-REFERENCE.md** (5 minutes) - Get the overview
2. **Review COMPARISON-SUMMARY.txt** (15 minutes) - Understand all issues
3. **Check tui-visual-comparison.md** (optional) - See visual examples
4. **Use TUI-CONSISTENCY-ANALYSIS-2025-01-02.md** - Reference during implementation

---

## Key Takeaway

The two TUIs have **7 major inconsistencies** that make them feel like different tools. However, **all issues are LOW RISK to fix** and can be resolved in **3-4 hours** with **no breaking changes**.

The largest issue is questionary.Style inconsistency (question text is white in skill_selector when it should be cyan). This can be fixed by creating a shared style module.

---

**Analysis Complete**: January 2, 2025
**Status**: Ready for Implementation
**Estimated Effort**: 3-4 hours total
**Risk Level**: LOW
**Impact**: HIGH (improved user experience and code quality)
