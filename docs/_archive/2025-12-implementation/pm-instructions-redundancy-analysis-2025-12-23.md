# PM Instructions Redundancy Analysis

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`
**Date**: 2025-12-23
**Current Stats**: 1,175 lines, 44,426 characters

---

## Executive Summary

The PM instructions file shows significant redundancy and verbosity issues:
- **Delegation concept** repeated 72 times
- **Verification requirements** explained in 5+ different sections
- **Example patterns** duplicated across multiple sections
- **Enforcement rules** restated 3-4 times each
- **Estimated reduction potential**: 30-40% (350-450 lines)

---

## Section Outline

### 1. Role and Core Principle (Lines 6-32)
- **Purpose**: Define PM role and delegation rationale
- **Length**: 26 lines
- **Assessment**: Core content, well-scoped

### 2. Core Workflow: Do the Work, Then Report (Lines 33-67)
- **Purpose**: Execution model and when to ask vs proceed
- **Length**: 35 lines
- **Assessment**: Good, but overlaps with "PM Responsibilities" (line 68)

### 3. PM Responsibilities (Lines 68-80)
- **Purpose**: List of PM responsibilities
- **Length**: 13 lines
- **Redundancy**: Repeats points from "Core Workflow" and "Summary" (line 1152)

### 4. Tool Usage Guide (Lines 82-315)
- **Purpose**: How to use Task, TodoWrite, Read, Bash, Vector Search
- **Length**: 233 lines (20% of file!)
- **Assessment**: VERBOSE - many examples repeat same patterns

#### 4a. Task Tool Examples (Lines 86-139)
- 3 delegation examples (implementation, verification, investigation)
- **Redundancy**: Same delegation pattern repeated 3 times
- **Recommendation**: Show ONE complete example, reference for others

#### 4b. Read Tool Usage (Lines 168-185)
- **Redundancy**: Repeats delegation-first thinking from section 1
- **Recommendation**: Consolidate into "Forbidden PM Actions" section

#### 4c. Bash Tool (Lines 220-272)
- **Redundancy**: Verification delegation explained again (already in Task examples)
- **Recommendation**: Remove duplicate verification example

### 5. Agent Deployment Architecture (Lines 186-218)
- **Purpose**: Cache structure, discovery priority, BASE_AGENT inheritance
- **Length**: 33 lines
- **Assessment**: Informational, low priority for PM execution
- **Recommendation**: MOVE to appendix or separate reference doc

### 6. FORBIDDEN MCP Tools (Lines 316-374)
- **Purpose**: MCP tools PM must never use
- **Length**: 59 lines
- **Redundancy**: Circuit breaker #6 mentioned but not defined here (defined later line 376)
- **Assessment**: Critical rules, but verbose

#### 6a. Browser State Verification (Lines 327-374)
- Chrome DevTools MCP tools list (12 lines)
- Example with ✅/❌ (28 lines)
- Circuit breaker enforcement (3 lines)
- **Redundancy**: Overlaps with Circuit Breaker #8 (QA Gate, line 504)
- **Recommendation**: Consolidate all browser verification into QA Gate section

### 7. Circuit Breaker #7 (Lines 376-413)
- **Purpose**: Verification command detection
- **Length**: 38 lines
- **Redundancy**: Repeats Bash tool forbidden uses (line 228-246)
- **Recommendation**: MERGE with Bash tool section or move all circuit breakers to one section

### 8. Ops Agent Routing (Lines 414-432)
- **Purpose**: Route to correct ops agent
- **Length**: 19 lines
- **Assessment**: Good, concise table format

### 9. When to Delegate to Each Agent (Lines 434-446)
- **Purpose**: Agent delegation matrix
- **Length**: 13 lines (table)
- **Assessment**: Excellent reference, keep as-is

### 10. Research Gate Protocol (Lines 447-502)
- **Purpose**: When/how to delegate to Research
- **Length**: 56 lines
- **Redundancy**: Overlaps with "Tool Usage Guide - Task Tool" examples
- **Recommendation**: Consolidate with Task examples or make this the ONLY place Research delegation is explained

### 11. QA Verification Gate Protocol (Lines 504-536)
- **Purpose**: MANDATORY QA before completion claims
- **Length**: 33 lines
- **Redundancy**: Repeats browser verification from lines 327-374
- **Recommendation**: THIS is the canonical QA gate section - remove duplicate browser sections

### 12. Verification Requirements (Lines 537-639)
- **Purpose**: Evidence requirements for Implementation, Deployment, Bug Fix
- **Length**: 103 lines (9% of file!)
- **Assessment**: VERBOSE - 3 separate examples with same "Good Evidence" pattern

#### Breakdown:
- Implementation Verification (lines 541-561): 21 lines
- Deployment Verification (lines 563-590): 28 lines
- Bug Fix Verification (lines 592-624): 33 lines
- Evidence Quality Standards (lines 626-639): 14 lines

**Redundancy**: Each section follows identical "Required Evidence" → "Example Good Evidence" pattern
**Recommendation**: Show ONE complete example, use table for other verification types

### 13. Workflow Pipeline (Lines 640-708)
- **Purpose**: Standard workflow steps
- **Length**: 69 lines
- **Redundancy**: Repeats verification requirements from section 12
- **Recommendation**: Reference verification section instead of re-explaining

### 14. Git File Tracking Protocol (Lines 710-781)
- **Purpose**: Track files immediately after agents create them
- **Length**: 72 lines
- **Assessment**: Important but repetitive examples
- **Recommendation**: Consolidate decision matrix, reduce example verbosity

### 15. Common Delegation Patterns (Lines 782-811)
- **Purpose**: Quick reference for delegation flows
- **Length**: 30 lines
- **Assessment**: EXCELLENT - concise, scannable
- **Recommendation**: KEEP as reference

### 16. Documentation Routing Protocol (Lines 812-864)
- **Purpose**: Where to save research/specs (with/without ticket context)
- **Length**: 53 lines
- **Assessment**: Useful, but could be more concise

### 17. Ticketing Integration (Lines 865-904)
- **Purpose**: Delegate ALL ticket operations to ticketing agent
- **Length**: 40 lines
- **Redundancy**: Repeats forbidden MCP tools (line 316-326)
- **Recommendation**: Consolidate with FORBIDDEN MCP Tools section

### 18. TICKET-DRIVEN DEVELOPMENT PROTOCOL (Lines 893-904)
- **Purpose**: Ticket lifecycle management
- **Length**: 12 lines
- **Redundancy**: Circuit Breaker #6 mentioned but not fully explained
- **Recommendation**: Link to circuit breaker section instead of inline enforcement

### 19. PR Workflow Delegation (Lines 905-946)
- **Purpose**: Branch protection and PR strategy
- **Length**: 42 lines
- **Assessment**: Good balance of rules and examples

### 20. Structured Questions (Lines 948-979)
- **Purpose**: When/how to use AskUserQuestion tool
- **Length**: 32 lines
- **Assessment**: Specific, actionable

### 21. Auto-Configuration Feature (Lines 986-1016)
- **Purpose**: Suggest auto-config to users
- **Length**: 31 lines
- **Assessment**: Useful, appropriate length

### 22. Proactive Architecture Improvement (Lines 1017-1055)
- **Purpose**: When to suggest architecture improvements
- **Length**: 39 lines
- **Assessment**: Clear examples, good format

### 23. Response Format (Lines 1057-1083)
- **Purpose**: How to format PM reports
- **Length**: 27 lines
- **Assessment**: Good example

### 24. Validation Rules (Lines 1085-1115)
- **Purpose**: PM validation rules
- **Length**: 31 lines
- **Redundancy**: Repeats concepts from sections 1, 4, 12
- **Recommendation**: REMOVE - redundant with earlier sections

### 25. Common User Request Patterns (Lines 1117-1135)
- **Purpose**: Quick pattern matching for user requests
- **Length**: 19 lines
- **Assessment**: Useful reference, keep

### 26. Session Resume Capability (Lines 1137-1150)
- **Purpose**: Git-based session continuity
- **Length**: 14 lines
- **Assessment**: Concise, useful

### 27. Summary: PM as Pure Coordinator (Lines 1152-1175)
- **Purpose**: Final summary of PM role
- **Length**: 24 lines
- **Redundancy**: COMPLETE REPETITION of sections 1, 3, and 4
- **Recommendation**: REMOVE or drastically shorten to 3-5 bullet points

---

## Redundancy Report

### Concept Repetition Analysis

| Concept | Times Explained | Line Numbers | Consolidation Target |
|---------|----------------|--------------|---------------------|
| **Delegation-first thinking** | 5+ times | 10-31, 86-139, 168-185, 1152-1175 | Keep ONLY in "Role and Core Principle" |
| **Verification requirements** | 5 times | 327-374, 504-536, 537-639, 640-708, 1085-1115 | Keep ONLY "QA Gate" and "Verification Requirements" |
| **Browser testing delegation** | 3 times | 327-374, 504-536, 1123 | Keep ONLY in QA Gate section |
| **Forbidden PM actions** | 4 times | 168-185, 228-272, 316-413, 1085-1115 | Create ONE "Forbidden PM Actions" section |
| **Git file tracking** | 3 times | 75, 640-708, 710-781 | Keep ONLY Git File Tracking Protocol section |
| **Task tool examples** | 6+ times | 86-139, 447-502, 782-811, 1117-1135 | Keep examples in Tool Usage, reference elsewhere |

### Example Pattern Duplication

**Pattern**: "❌ WRONG: PM does X directly" → "✅ CORRECT: PM delegates to Agent"

This exact pattern appears **8 times**:
1. Read tool example (line 183)
2. Bash tool example (line 233-246)
3. Browser verification (line 352-354)
4. Circuit breaker #7 (line 391-407)
5. Ticketing example (line 879-881)
6. Validation Rule 1 (line 1093-1094)
7. Validation Rule 2 (line 1100-1101)
8. Validation Rule 3 (line 1107-1108)

**Recommendation**: Show this pattern ONCE in a "Forbidden Actions" section, then reference it.

### Circuit Breaker Fragmentation

Circuit Breakers are scattered across the file:
- Circuit Breaker #6: Mentioned at lines 325, 535, 903 (never fully defined)
- Circuit Breaker #7: Lines 376-413 (full definition)
- Circuit Breaker #8: Lines 534-535 (partial definition)

**Recommendation**: Create ONE "Circuit Breakers" section with all enforcement rules consolidated.

---

## Verbosity Measurement

### Longest Sections (by line count)

| Section | Lines | % of File | Verbosity Assessment |
|---------|-------|-----------|---------------------|
| Tool Usage Guide | 233 | 20% | **HIGH** - repetitive examples |
| Verification Requirements | 103 | 9% | **HIGH** - 3 nearly identical examples |
| Git File Tracking | 72 | 6% | **MEDIUM** - decision matrix good, examples verbose |
| Workflow Pipeline | 69 | 6% | **MEDIUM** - references could replace re-explanations |
| FORBIDDEN MCP Tools | 59 | 5% | **MEDIUM** - critical rules, but repetitive |
| Research Gate Protocol | 56 | 5% | **MEDIUM** - overlaps with Task examples |

**Total "high verbosity" sections**: 336 lines (29% of file)

### Character Density Analysis

Average characters per line: 37.8 (44,426 chars / 1,175 lines)

**Sections above average density** (indicates verbosity):
- Tool Usage Guide: ~45 chars/line (lots of prose)
- Verification Requirements: ~52 chars/line (detailed examples)
- Workflow Pipeline: ~41 chars/line

**Sections below average** (concise):
- Common Delegation Patterns: ~28 chars/line (tables/lists)
- Agent Routing table: ~32 chars/line (structured data)

---

## Specific Redundancy Examples

### Example 1: Delegation Concept Repeated 5 Times

**Occurrence 1** (Lines 10-26):
```markdown
### Why Delegation Matters
The PM delegates all work to specialized agents for three key reasons:
1. Separation of Concerns
2. Agent Specialization
3. Verification Chain
```

**Occurrence 2** (Lines 28-31):
```markdown
### Delegation-First Thinking
When receiving a user request, the PM's first consideration is:
"Which specialized agent has the expertise and tools to handle this effectively?"
```

**Occurrence 3** (Lines 80):
```markdown
The PM does not investigate, implement, test, or deploy directly.
These activities are delegated to appropriate agents.
```

**Occurrence 4** (Lines 1164-1171):
```markdown
**PM Does Not**:
1. Investigate (delegates to Research)
2. Implement (delegates to Engineers)
3. Test (delegates to QA)
4. Deploy (delegates to Ops)
```

**Occurrence 5** (Lines 1175):
```markdown
A successful PM session has the PM using primarily the Task tool for delegation...
```

**Impact**: Same message repeated 5 times = 60+ lines of redundant content

---

### Example 2: Verification Evidence Pattern Repeated 3 Times

**Pattern**: "Required Evidence" checklist → "Example Good Evidence" code block

**Occurrence 1** (Lines 544-561): Implementation Verification
```markdown
**Required Evidence**:
- [ ] Engineer agent confirmation message
- [ ] List of files changed (specific paths)
...

**Example Good Evidence**:
```
Engineer Agent Report:
...
```
```

**Occurrence 2** (Lines 566-590): Deployment Verification
```markdown
**Required Evidence**:
- [ ] Ops agent deployment confirmation
- [ ] Live URL or endpoint (must be accessible)
...

**Example Good Evidence**:
```
Ops Agent Report:
...
```
```

**Occurrence 3** (Lines 595-623): Bug Fix Verification
```markdown
**Required Evidence**:
- [ ] QA reproduction of bug before fix
- [ ] Engineer fix confirmation
...

**Example Good Evidence**:
```
Bug Fix Workflow:
...
```
```

**Impact**: 80+ lines showing same evidence pattern 3 times

---

### Example 3: Browser Verification Explained Twice

**Occurrence 1** (Lines 327-374): "Browser State Verification (MANDATORY)"
- Chrome DevTools MCP tools list (12 lines)
- Required Evidence template (28 lines)
- Circuit breaker enforcement (3 lines)
- **Total**: 48 lines

**Occurrence 2** (Lines 504-536): "QA Verification Gate Protocol"
- Includes "Local Server UI" verification row (line 521)
- References web-qa agent with Chrome DevTools
- **Overlap**: 15+ lines of redundant browser verification

**Impact**: 60+ lines explaining browser verification, should be ~25 lines in ONE place

---

### Example 4: Forbidden PM Actions Stated 4 Times

**Occurrence 1** (Lines 168-185): Read Tool Usage
```markdown
**DEFAULT**: Zero reads - delegate to Research instead.
❌ Forbidden: Source code, multiple files, investigation keywords
```

**Occurrence 2** (Lines 228-246): Bash Tool
```markdown
**FORBIDDEN Uses** (MUST delegate instead):
❌ Verification commands (curl, lsof, ps, wget, nc)
❌ Browser testing tools
```

**Occurrence 3** (Lines 316-326): FORBIDDEN MCP Tools
```markdown
**PM MUST NEVER use these MCP tools directly - ALWAYS delegate instead:**
| Tool Category | Forbidden Patterns | Delegate To |
```

**Occurrence 4** (Lines 1085-1115): Validation Rules
```markdown
### Rule 1: Implementation Detection
When the PM attempts to use Edit, Write, or implementation Bash commands...
**Correct Action**: PM delegates to Engineer agent
```

**Impact**: 70+ lines explaining PM cannot perform implementation/investigation

---

## Proposed Consolidation Plan

### Phase 1: Merge Redundant Sections (Estimated Savings: 200 lines)

#### 1.1 Create "Forbidden PM Actions" Section (Consolidate 4 sections → 1)
**Merge**: Lines 168-185, 228-246, 316-413, 1085-1115
**Into**: New section "Forbidden PM Actions and Circuit Breakers"
**Current**: 140 lines
**Target**: 50 lines
**Savings**: 90 lines

**Structure**:
```markdown
## Forbidden PM Actions and Circuit Breakers

### Actions PM MUST Delegate (Never Execute)
| Forbidden Action | Delegate To | Circuit Breaker |
|------------------|-------------|-----------------|
| Code changes (Edit/Write) | engineer | #1 |
| Investigation (Read multiple files) | research | #2 |
| Verification commands (curl, lsof) | local-ops, QA | #7 |
| Browser tools (chrome-devtools) | web-qa | #6 |
| Ticket operations (mcp-ticketer) | ticketing | #6 |

### Circuit Breaker Enforcement
- Violation #1: ⚠️ WARNING
- Violation #2: 🚨 ESCALATION
- Violation #3: ❌ FAILURE
```

#### 1.2 Consolidate Verification Evidence (Merge 3 examples → 1 table)
**Merge**: Lines 541-624 (Implementation, Deployment, Bug Fix)
**Into**: Unified verification requirements table
**Current**: 84 lines
**Target**: 40 lines
**Savings**: 44 lines

**Structure**:
```markdown
## Verification Requirements

| Work Type | Agent | Required Evidence |
|-----------|-------|-------------------|
| Implementation | engineer | Confirmation message, files changed, git commit, summary |
| Deployment | ops | Confirmation, live URL, health check (HTTP status), logs excerpt, process verification |
| Bug Fix | qa, engineer | Bug reproduction (before), fix confirmation, verification (after), regression tests |

**Example Evidence Format**:
```
[Agent] Agent Report:
- [Specific action completed]
- [Measurable outcome with numbers/status codes]
- [Files/URLs/processes verified]
```
```

#### 1.3 Remove Duplicate Summary Section
**Remove**: Lines 1152-1175 (Summary: PM as Pure Coordinator)
**Reason**: Completely repeats lines 6-80 (Role and Core Principle, PM Responsibilities)
**Current**: 24 lines
**Target**: 0 lines (or 3-line reference to earlier section)
**Savings**: 21 lines

#### 1.4 Consolidate Task Tool Examples
**Merge**: Lines 94-133 (3 separate Task examples)
**Into**: ONE complete example + reference table for others
**Current**: 40 lines
**Target**: 20 lines
**Savings**: 20 lines

#### 1.5 Merge Workflow Pipeline References
**Modify**: Lines 640-708 (Workflow Pipeline)
**Change**: Replace re-explanations with references to Verification Requirements section
**Current**: 69 lines
**Target**: 45 lines
**Savings**: 24 lines

**Total Phase 1 Savings**: ~200 lines (17% reduction)

---

### Phase 2: Extract Reference Material (Estimated Savings: 50 lines)

#### 2.1 Move Agent Deployment Architecture to Appendix
**Move**: Lines 186-218 (Agent Deployment Architecture)
**To**: Separate file `AGENT_DEPLOYMENT.md` or appendix section
**Reason**: Informational, not critical for PM execution flow
**Current**: 33 lines
**Savings**: 33 lines (replaced with 2-line reference)

#### 2.2 Consolidate Circuit Breaker Mentions
**Current**: Circuit Breakers mentioned at lines 325, 376-413, 535, 903
**Target**: ONE section with all circuit breakers (#6, #7, #8) defined
**Savings**: 15 lines (eliminate duplicate mentions)

**Total Phase 2 Savings**: ~50 lines (4% reduction)

---

### Phase 3: Reduce Example Verbosity (Estimated Savings: 100 lines)

#### 3.1 Git File Tracking Examples
**Modify**: Lines 710-781 (Git File Tracking Protocol)
**Change**: Keep decision matrix (excellent), reduce example verbosity
**Current**: 72 lines
**Target**: 45 lines
**Savings**: 27 lines

#### 3.2 Browser Verification
**Merge**: Lines 327-374 (Browser State Verification) into QA Gate section (504-536)
**Current**: 48 + 33 = 81 lines
**Target**: 40 lines
**Savings**: 41 lines

#### 3.3 Research Gate Examples
**Modify**: Lines 447-502 (Research Gate Protocol)
**Change**: Reduce example verbosity, reference Task tool examples
**Current**: 56 lines
**Target**: 35 lines
**Savings**: 21 lines

#### 3.4 Documentation Routing
**Modify**: Lines 812-864 (Documentation Routing Protocol)
**Change**: Use table format instead of prose explanations
**Current**: 53 lines
**Target**: 35 lines
**Savings**: 18 lines

**Total Phase 3 Savings**: ~100 lines (9% reduction)

---

## Total Estimated Reduction

| Phase | Target | Savings | New Total |
|-------|--------|---------|-----------|
| **Current** | - | - | 1,175 lines |
| **Phase 1**: Merge redundant sections | Consolidate | 200 lines | 975 lines |
| **Phase 2**: Extract reference material | Relocate | 50 lines | 925 lines |
| **Phase 3**: Reduce example verbosity | Simplify | 100 lines | 825 lines |

**Final Estimate**: **825 lines** (30% reduction, 350 lines saved)

---

## Categorized Content Assessment

### Core Rules (ESSENTIAL - Keep)
- Role and Core Principle (lines 6-32): **26 lines**
- Core Workflow (lines 33-67): **35 lines**
- PM Responsibilities (lines 68-80): **13 lines** *(could merge with Role)*
- QA Verification Gate (lines 504-536): **33 lines**
- Git File Tracking Protocol (lines 710-781): **72 lines** *(reduce to 45)*
- **Total Core**: ~174 lines (target: 150 lines)

### Tool Usage Guide (ESSENTIAL - Simplify)
- Task Tool (lines 86-139): **54 lines** *(reduce to 30)*
- TodoWrite (lines 140-167): **28 lines** *(keep)*
- Read Tool (lines 168-185): **18 lines** *(merge into Forbidden)*
- Bash Tool (lines 220-272): **53 lines** *(reduce to 30)*
- Vector Search (lines 290-315): **26 lines** *(keep)*
- **Total Tools**: ~179 lines (target: 120 lines)

### Agent Routing (ESSENTIAL - Keep)
- Ops Agent Routing (lines 414-432): **19 lines**
- When to Delegate table (lines 434-446): **13 lines**
- Common Delegation Patterns (lines 782-811): **30 lines**
- **Total Routing**: ~62 lines (keep as-is)

### Verification Requirements (ESSENTIAL - Consolidate)
- Verification Requirements (lines 537-639): **103 lines** *(reduce to 40)*
- Workflow Pipeline (lines 640-708): **69 lines** *(reduce to 45)*
- **Total Verification**: ~172 lines (target: 85 lines)

### Enforcement Rules (ESSENTIAL - Consolidate)
- FORBIDDEN MCP Tools (lines 316-374): **59 lines**
- Circuit Breaker #7 (lines 376-413): **38 lines**
- Validation Rules (lines 1085-1115): **31 lines**
- **Total Enforcement**: ~128 lines (target: 50 lines via consolidation)

### Special Protocols (KEEP - Minor Edits)
- Research Gate (lines 447-502): **56 lines** *(reduce to 35)*
- Documentation Routing (lines 812-864): **53 lines** *(reduce to 35)*
- Ticketing Integration (lines 865-904): **40 lines** *(merge with Forbidden)*
- PR Workflow (lines 905-946): **42 lines** *(keep)*
- **Total Protocols**: ~191 lines (target: 130 lines)

### User Interaction Features (KEEP - As-Is)
- Structured Questions (lines 948-979): **32 lines**
- Auto-Configuration (lines 986-1016): **31 lines**
- Proactive Architecture (lines 1017-1055): **39 lines**
- Common User Patterns (lines 1117-1135): **19 lines**
- **Total User Features**: ~121 lines (keep as-is)

### Reference Material (RELOCATE or APPENDIX)
- Agent Deployment Architecture (lines 186-218): **33 lines** *(move to appendix)*
- Response Format (lines 1057-1083): **27 lines** *(keep)*
- Session Resume (lines 1137-1150): **14 lines** *(keep)*
- **Total Reference**: ~74 lines (target: 40 lines)

### Redundant Sections (REMOVE or DRASTICALLY REDUCE)
- Summary section (lines 1152-1175): **24 lines** *(remove, redundant)*
- Duplicate browser verification (lines 327-374): **48 lines** *(merge into QA Gate)*
- **Total Redundant**: ~72 lines (target: 0 lines)

---

## Recommendations Priority Matrix

### Priority 1: High-Impact Consolidations (Target: 200 line reduction)
1. **Merge "Forbidden PM Actions"** (4 sections → 1): Save 90 lines
2. **Consolidate Verification Evidence** (3 examples → 1 table): Save 44 lines
3. **Remove Summary Section** (duplicate content): Save 21 lines
4. **Consolidate Task Examples** (3 examples → 1 + table): Save 20 lines
5. **Merge Workflow Pipeline** (references instead of re-explanations): Save 24 lines

### Priority 2: Content Relocation (Target: 50 line reduction)
1. **Move Agent Deployment Architecture** to appendix: Save 31 lines
2. **Consolidate Circuit Breaker Mentions** (4 locations → 1 section): Save 15 lines

### Priority 3: Example Simplification (Target: 100 line reduction)
1. **Reduce Browser Verification** (merge 2 sections): Save 41 lines
2. **Simplify Git File Tracking** (keep matrix, reduce examples): Save 27 lines
3. **Streamline Research Gate** (reference Task examples): Save 21 lines
4. **Compact Documentation Routing** (table format): Save 18 lines

---

## Template for Consolidated Sections

### Example: Consolidated "Forbidden PM Actions" Section

**Before** (140 lines across 4 sections):
- Read Tool Usage (18 lines)
- Bash Tool forbidden uses (26 lines)
- FORBIDDEN MCP Tools (59 lines)
- Validation Rules (31 lines)

**After** (50 lines in ONE section):

```markdown
## Forbidden PM Actions and Circuit Breakers

### Rule: PM NEVER Executes, Always Delegates

| Forbidden Action | Why Forbidden | Delegate To | Circuit Breaker |
|------------------|---------------|-------------|-----------------|
| **Code Changes** (Edit, Write, implementation Bash) | Separation of concerns | engineer | #1 |
| **Multi-File Investigation** (Read >1 file, grep, find) | Research tools | research | #2 |
| **Verification Commands** (curl, lsof, ps, wget, nc) | Verification expertise | local-ops, QA | #7 |
| **Browser Tools** (mcp__chrome-devtools__*) | Playwright expertise | web-qa | #6 |
| **Ticket Operations** (mcp__mcp-ticketer__*, WebFetch tickets) | MCP-first routing | ticketing | #6 |

### ONE Exception: Read Tool for Delegation Context
✅ **Allowed**: ONE config file read (package.json, pyproject.toml, settings.json, .env.example)
❌ **Forbidden**: Source code, multiple files, investigation keywords ("check", "analyze", "debug")

**Pattern Recognition**:
```
❌ WRONG: PM executes forbidden action directly
PM: curl http://localhost:3000  # Verification command - VIOLATION

✅ CORRECT: PM delegates to appropriate agent
Task:
  agent: "local-ops"
  task: "Verify app is running on localhost:3000"
  acceptance_criteria:
    - Check port listening (lsof -i :3000)
    - Test HTTP endpoint (curl http://localhost:3000)
    - Check for errors in logs
```

### Circuit Breaker Enforcement
All forbidden actions trigger progressive enforcement:
- **Violation #1**: ⚠️ WARNING - PM must delegate to appropriate agent
- **Violation #2**: 🚨 ESCALATION - Session flagged for review
- **Violation #3**: ❌ FAILURE - Session non-compliant

### Circuit Breaker Definitions

**#1: Implementation Detection**
Trigger: PM uses Edit, Write, or implementation Bash commands

**#2: Investigation Detection**
Trigger: PM reads multiple files or uses search tools

**#6: MCP Tool Misuse**
Trigger: PM uses ticketing or browser MCP tools directly

**#7: Verification Command Detection**
Trigger: PM runs curl, lsof, ps, wget, nc, netcat

**#8: QA Gate Bypass**
Trigger: PM claims completion without QA delegation (see QA Verification Gate section)
```

**Reduction**: 140 lines → 50 lines (64% reduction, 90 lines saved)

---

## Next Steps

### Immediate Actions
1. **Review this analysis** with stakeholders
2. **Prioritize consolidations** based on impact vs effort
3. **Create backup** of current PM_INSTRUCTIONS.md (version 0007)
4. **Execute Phase 1** consolidations (highest impact)
5. **Test with PM agent** to ensure no functionality loss
6. **Iterate** based on testing results

### Testing Strategy
- Use PM agent with consolidated instructions
- Compare behavior against original instructions
- Verify circuit breakers still trigger correctly
- Ensure delegation patterns remain clear
- Check that tool usage guidance is sufficient

### Success Metrics
- **Target**: 825 lines (30% reduction from 1,175)
- **Readability**: Improved scannability (more tables, less prose)
- **Maintainability**: Fewer locations to update per concept
- **Consistency**: ONE canonical explanation per concept
- **Functionality**: No behavior changes for PM agent

---

## Conclusion

The PM instructions file suffers from significant redundancy primarily due to:
1. **Concept repetition**: Delegation explained 5+ times, verification 5+ times
2. **Example duplication**: Same ❌/✅ pattern used 8+ times
3. **Scattered enforcement**: Circuit breakers in 4+ locations
4. **Verbose evidence examples**: 3 nearly identical verification examples

**Primary recommendation**: Consolidate redundant sections using the Phase 1-3 plan to achieve **30% reduction (350 lines)** while improving readability and maintainability.

**Key insight**: The file contains excellent content, but each concept should have ONE canonical location with references from other sections rather than full re-explanations.
