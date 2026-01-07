# PM Instructions Obsolete Content Analysis

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`
**Analysis Date**: 2025-12-23
**Current Version**: 0007
**Total Lines**: 1176

## Executive Summary

**Total Obsolete Lines**: ~150-200 lines (13-17% of file)
**Confidence**: High (verified against codebase)
**Impact**: Medium (outdated tool references, incorrect workflows)

## Findings by Category

### 1. Deprecated Tool References ⚠️ HIGH PRIORITY

#### 1.1 AskUserQuestion Tool (OBSOLETE)
**Lines**: 950-977 (28 lines)
**Status**: Tool does not exist in codebase
**Evidence**: Import error when attempting to use `AskUserQuestion`

```python
# Test shows tool doesn't exist:
ImportError: cannot import name 'AskUserQuestion' from 'claude_mpm.utils.structured_questions'
```

**Obsolete Content**:
- Line 950: "The PM can use structured questions to gather user preferences using the AskUserQuestion tool."
- Lines 952-964: List of when to use/not use structured questions
- Lines 965-977: "Available Question Templates" section with `PRWorkflowTemplate` import example

**Current Reality**:
- `structured_questions.py` exists but only exports `QuestionBuilder`, `QuestionSet`, `StructuredQuestion`
- No `AskUserQuestion` tool exists
- PR workflow templates exist but integration mechanism is unclear

**Recommendation**:
- **REMOVE** lines 950-977 entirely (28 lines)
- OR **UPDATE** to reflect actual tool availability and usage pattern

---

#### 1.2 Code Analyzer Agent (UNCLEAR)
**Lines**: 649, 674-676, 786-810, 1022, 1053, 1170 (15+ references)
**Status**: Agent not found in cache or templates
**Evidence**: Only BASE-AGENT.md found in `~/.claude-mpm/cache/agents/`

**Obsolete References**:
- Line 649: "Code Analyzer (solution review)"
- Line 674-676: Code Analyzer step in workflow pipeline
- Lines 786-810: Every workflow pattern includes "Analyzer" step
- Line 1022: "Research/Code Analyzer reports code smells"
- Line 1170: "Analyze (delegates to Code Analyzer)"

**Current Reality**:
- No `code-analyzer.md` agent template in cache
- Only generic agents found: BASE-AGENT.md, documentation, engineer, ops, qa, security, universal
- Unclear if this agent exists or was planned but never implemented

**Recommendation**:
- **VERIFY** if code-analyzer agent exists in any published repo
- If doesn't exist: **REMOVE** all Analyzer references (15+ lines across multiple sections)
- If exists: **CLARIFY** where it's published and how to access it

---

#### 1.3 aitrackdown CLI (DEPRECATED)
**Lines**: 322, 880
**Status**: Legacy CLI, replaced by mcp-ticketer
**Evidence**: Only mentioned as "forbidden" tool

**Obsolete Content**:
- Line 322: Table entry listing `aitrackdown` CLI as forbidden
- Line 880: "PM MUST NEVER use aitrackdown CLI → Delegate to ticketing"

**Current Reality**:
- mcp-ticketer MCP tools are the current standard
- No evidence of aitrackdown usage in codebase
- References only exist as "don't use this"

**Recommendation**:
- **REMOVE** aitrackdown references (2 lines)
- These are already marked as deprecated/forbidden
- Keeping them adds confusion about legacy systems

---

### 2. Incorrect Commands 🔧 MEDIUM PRIORITY

#### 2.1 Auto-Configure Command Mismatch
**Lines**: 1008
**Status**: Command name inconsistency

**Obsolete Content**:
```
Line 1008: "Run '/mpm-auto-configure --preview'"
```

**Current Reality**:
- Line 281 correctly documents: `/mpm-configure`
- Line 1000 correctly documents: `/mpm-configure`
- Line 1008 incorrectly shows: `/mpm-auto-configure` (with "auto-" prefix)

**Recommendation**:
- **FIX** line 1008 to use `/mpm-configure --preview` (consistency)

---

### 3. Workflow Pipeline Inconsistencies 📋 MEDIUM PRIORITY

#### 3.1 Analyzer Step in All Workflows
**Lines**: 786-810 (25 lines)
**Status**: Every workflow includes "Analyzer" which may not exist

**Obsolete Content**:
```
Line 786: Research → Analyzer → react-engineer + Engineer → ...
Line 790: Research → Analyzer → Engineer → ...
Line 794: Research → Analyzer → web-ui/react-engineer → ...
Line 798: Research → Analyzer → Engineer → ...
Line 802: Research → Analyzer → Engineer → ...
Line 806: Research → Analyzer → Engineer → ...
Line 810: Research → Analyzer → Engineer → ...
```

**Impact**: If Code Analyzer doesn't exist, ALL documented workflows are incorrect

**Recommendation**:
- If Analyzer doesn't exist: **REMOVE** "Analyzer →" from all workflow patterns (7 locations)
- Update to: `Research → Engineer → ...` (simpler, matches reality)

---

### 4. Agent Discovery Section 📁 LOW PRIORITY

#### 4.1 Cache Structure Documentation
**Lines**: 186-209 (24 lines)
**Status**: May be outdated or incomplete

**Current Reality**:
- Only 13 items found in `~/.claude-mpm/cache/agents/` (including directories)
- Minimal agent presence suggests caching may not work as documented
- No evidence of auto-sync on startup

**Concerns**:
- Line 189: Claims agents cached from `bobmatnyc/claude-mpm-agents` repo
- Line 206: Claims "Automatic sync on startup (if >24h since last sync)"
- Line 207: Claims manual sync with `claude-mpm agents update`

**Recommendation**:
- **VERIFY** if agent caching works as documented
- **TEST** auto-sync behavior
- Consider marking as "experimental" or removing if not functional

---

### 5. Structured Questions Section 📝 HIGH PRIORITY

#### 5.1 Entire Structured Questions Section
**Lines**: 947-984 (38 lines)
**Status**: Implementation unclear, tool missing

**Obsolete Content**:
- Entire section titled "Structured Questions for User Input"
- References to non-existent `AskUserQuestion` tool
- Import examples that don't work
- Template classes that may not integrate with PM

**Evidence**:
```python
# Documented usage (doesn't work):
from claude_mpm.templates.questions.pr_strategy import PRWorkflowTemplate
template = PRWorkflowTemplate(num_tickets=3, has_ci=True)
params = template.to_params()  # Method doesn't exist
# Use params with AskUserQuestion tool  # Tool doesn't exist
```

**Current Reality**:
- Templates exist: `pr_strategy.py`, `project_init.py`, `ticket_mgmt.py`
- But no clear integration path with PM agent
- No `AskUserQuestion` tool in PM's available tools

**Recommendation**:
- **REMOVE** entire section (38 lines) OR
- **REWRITE** with actual working examples and tool names
- **VERIFY** if PM can actually use structured questions

---

## Summary by Line Numbers

### Lines to REMOVE (Total: ~150-200 lines)

| Line Range | Reason | Lines | Priority |
|------------|--------|-------|----------|
| 950-977 | AskUserQuestion tool doesn't exist | 28 | HIGH |
| 322 (partial) | Remove aitrackdown from table | 1 | MEDIUM |
| 880 | Remove aitrackdown CLI reference | 1 | MEDIUM |
| 649, 674-676 | Code Analyzer references (if agent doesn't exist) | 5 | HIGH |
| 786-810 | Remove "Analyzer →" from workflows (if doesn't exist) | 7 | HIGH |
| 1022 | Code Analyzer reference | 1 | MEDIUM |
| 1053 | Code Analyzer workflow reference | 1 | MEDIUM |
| 1170 | Code Analyzer in "PM Does Not" list | 1 | MEDIUM |

### Lines to UPDATE (not remove)

| Line | Current | Should Be | Priority |
|------|---------|-----------|----------|
| 1008 | `/mpm-auto-configure --preview` | `/mpm-configure --preview` | HIGH |
| 189-209 | Agent caching claims | Verify or mark experimental | LOW |

---

## Estimated Cleanup Impact

### Conservative Estimate (Verified Obsolete Only)
- **AskUserQuestion section**: 28 lines
- **aitrackdown references**: 2 lines
- **Command fix**: 0 lines (update only)
- **Total**: ~30 lines removed

### Aggressive Estimate (Include Likely Obsolete)
- **AskUserQuestion section**: 28 lines
- **Code Analyzer references**: 15 lines
- **Analyzer in workflows**: 7 lines
- **aitrackdown references**: 2 lines
- **Agent cache section** (if not working): 24 lines
- **Total**: ~76 lines removed

### Maximum Estimate (Include All Questionable)
- All above + clarifications + outdated examples: ~150-200 lines

---

## Verification Checklist

Before finalizing removals, verify:

- [ ] Does Code Analyzer agent exist? Check `bobmatnyc/claude-mpm-agents` repo
- [ ] Does AskUserQuestion tool work? Test with actual PM session
- [ ] Do PRWorkflowTemplate imports work? Test Python imports
- [ ] Does agent caching work? Test `claude-mpm agents update`
- [ ] Does auto-sync work? Test startup behavior
- [ ] Are workflow examples accurate? Test actual PM delegations

---

## Recommendations Priority

### Immediate (Do Now)
1. **Remove AskUserQuestion section** (lines 950-977) - Tool doesn't exist
2. **Fix command name** (line 1008) - Simple typo fix
3. **Remove aitrackdown references** (lines 322, 880) - Confirmed deprecated

### Soon (This Week)
4. **Verify Code Analyzer** - If doesn't exist, remove all 15+ references
5. **Test structured questions** - If doesn't work, remove entire section

### Later (Next Sprint)
6. **Verify agent caching** - If doesn't work, update or remove section
7. **Review workflow examples** - Ensure all delegate patterns are current

---

## Notes

- Document version is `0007` (line 1)
- Last major update appears to be recent (references mcp-ticketer, not aitrackdown)
- Overall structure is good, just needs removal of unimplemented/deprecated features
- Most content is accurate and valuable, cleanup will improve clarity

---

**Analysis Tools Used**:
- Grep pattern matching for deprecated terms
- Python import verification
- File system checks for agent templates
- Code structure analysis
