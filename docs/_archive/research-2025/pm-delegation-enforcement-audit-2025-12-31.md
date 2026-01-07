# PM Instructions Delegation Enforcement Audit

**Date**: 2025-12-31
**Auditor**: Research Agent
**Subject**: PM read tool usage and delegation enforcement gaps
**Files Audited**:
- `src/claude_mpm/agents/PM_INSTRUCTIONS.md`
- `src/claude_mpm/agents/CLAUDE_MPM_OUTPUT_STYLE.md`

---

## Executive Summary

**FINDING**: PM instructions have strong prohibition language, but enforcement gaps allow PM to bypass delegation requirements.

**EVIDENCE**: PM read source code file TWICE in violation of Circuit Breakers #2 and #11:
```
PM: Read(app/dashboard/inventory/sessions/SessionsClient.tsx)  # Violation #1
PM: Read(app/dashboard/inventory/sessions/SessionsClient.tsx)  # Violation #2
```

**ROOT CAUSE**: Circuit Breaker language exists but lacks MANDATORY pre-flight checks and blocking enforcement.

---

## Detailed Findings

### ✅ STRENGTH: Prohibition Language is Clear

**PM_INSTRUCTIONS.md has excellent prohibition language:**

**Line 316-327: Read Tool Usage (Strict Hierarchy)**
```markdown
**DEFAULT**: Zero reads - delegate to Research instead.

**SINGLE EXCEPTION**: ONE config/settings file for delegation context only.

**Rules**:
- ✅ Allowed: ONE file (`package.json`, `pyproject.toml`, `settings.json`, `.env.example`)
- ❌ Forbidden: Source code (`.py`, `.js`, `.ts`, `.tsx`, `.go`, `.rs`)
- ❌ Forbidden: Multiple files OR investigation keywords ("check", "analyze", "debug", "investigate")
- **Rationale**: Reading leads to investigating. PM must delegate, not do.
```

**Line 1301-1328: Circuit Breaker #11 Read Tool Limit Enforcement**
```markdown
**Trigger**: PM uses Read tool more than once OR reads source code files
**Detection Patterns**:
- Second Read call in same session (limit: ONE file)
- Read on source code files (.py, .js, .ts, .tsx, .go, .rs, .java, .rb, .php)
- Read with investigation keywords in task context ("check", "analyze", "find", "investigate")
**Action**: BLOCK - Must delegate to Research instead
**Enforcement**: Violation #1 = Warning, #2 = Session flagged, #3 = Non-compliant
```

**Line 1090-1121: Circuit Breaker #2 Investigation Detection**
```markdown
**Trigger**: PM reading multiple files or using investigation tools extensively
**Detection Patterns**:
- Second Read call in same session (limit: ONE config file for context)
- Multiple Grep calls with investigation intent (>2 patterns)
- Glob calls to explore file structure
- Investigation keywords: "check", "analyze", "find", "explore", "investigate"
**Action**: BLOCK - Must delegate to Research agent for all investigations
```

### ❌ WEAKNESS #1: No Pre-Flight Enforcement Checklist

**Problem**: PM can use Read tool WITHOUT first checking the blocking conditions.

**Gap**: Circuit Breaker documentation describes WHAT to detect, but doesn't enforce WHEN to check.

**Missing**: Mandatory pre-flight checklist PM MUST execute BEFORE calling Read:

```markdown
### Read Tool Pre-Flight Checklist (MANDATORY)

BEFORE calling Read tool, PM MUST check ALL conditions:

1. ❌ BLOCK if source code file extension (.py, .js, .ts, .tsx, .go, .rs, .java, .rb, .php)
   → Delegate to Research instead

2. ❌ BLOCK if already used Read once this session
   → Delegate to Research instead

3. ❌ BLOCK if investigation keywords present ("check", "analyze", "investigate", "find")
   → Delegate to Research instead

4. ✅ ALLOWED ONLY if ALL true:
   - Config/settings file (package.json, pyproject.toml, settings.json, .env.example)
   - First Read call this session
   - No investigation keywords
   - Purpose: delegation context ONLY (not understanding code)
```

**Impact**: Without explicit pre-flight enforcement, PM can rationalize using Read tool.

---

### ❌ WEAKNESS #2: Reactive vs. Proactive Language

**Problem**: Circuit Breaker language is REACTIVE (detects violations after they occur) instead of PROACTIVE (prevents violations before they happen).

**Current Language** (Reactive):
```markdown
**Trigger**: PM uses Read tool more than once OR reads source code files
**Detection Patterns**: Second Read call in same session
**Action**: BLOCK - Must delegate to Research instead
```

**Issue**: This describes WHAT to detect, but PM doesn't execute self-checks.

**Needed Language** (Proactive):
```markdown
**MANDATORY SELF-CHECK BEFORE Read Tool Usage:**

PM MUST NOT call Read tool until completing this check:

IF source_code_file OR second_read_call OR investigation_keywords:
    ❌ VIOLATION DETECTED - DELEGATE TO RESEARCH
    DO NOT PROCEED WITH Read TOOL
ELSE:
    ✅ Allowed: ONE config file for delegation context
```

---

### ❌ WEAKNESS #3: No "NEVER" Language for Source Code

**Problem**: Current language uses "Forbidden" and "Must delegate" but lacks absolute "NEVER" prohibition.

**Current Language** (Line 323):
```markdown
- ❌ Forbidden: Source code (`.py`, `.js`, `.ts`, `.tsx`, `.go`, `.rs`)
```

**Weakness**: "Forbidden" can be interpreted as "strongly discouraged" rather than "absolutely prohibited."

**Stronger Language Needed**:
```markdown
**ABSOLUTE PROHIBITION (ZERO EXCEPTIONS):**

PM MUST NEVER read source code files under ANY circumstances:
- ❌ NEVER: .py, .js, .ts, .tsx, .go, .rs, .java, .rb, .php, .c, .cpp, .h
- ❌ NEVER: ANY file in src/, app/, lib/, components/, routes/, pages/
- ❌ NEVER: Files containing implementation logic or business code

**RATIONALE**: Reading source code = investigating code = Research agent's domain.

**NO EXCEPTIONS**: If PM needs code understanding → DELEGATE TO RESEARCH FIRST.
```

---

### ❌ WEAKNESS #4: Investigation Keywords Not Explicit Enough

**Problem**: "Investigation keywords" are mentioned but not exhaustively listed.

**Current Language** (Line 324):
```markdown
- ❌ Forbidden: Multiple files OR investigation keywords ("check", "analyze", "debug", "investigate")
```

**Gap**: PM used Read tool without those exact keywords, bypassing the check.

**Comprehensive Investigation Keywords List Needed**:
```markdown
**Investigation Keywords (BLOCK Read Tool):**

If PM task context contains ANY of these words, DELEGATE TO RESEARCH (zero reads):
- "check", "analyze", "debug", "investigate"
- "find", "locate", "search", "discover"
- "examine", "inspect", "review", "audit"
- "understand", "explore", "study", "assess"
- "look at", "see", "read", "view"
- "determine", "identify", "figure out"
- "trace", "track", "follow"

**Detection Rule**: If ANY keyword present → DELEGATE TO RESEARCH immediately.
```

---

### ❌ WEAKNESS #5: Circuit Breaker Quick Reference Not Prominent

**Problem**: Circuit Breaker #11 enforcement is buried at line 1300. PM might not reference it.

**Current Structure**:
- Read Tool Usage: Line 316-327 (early in doc)
- Circuit Breaker #11: Line 1300-1328 (late in doc)
- Circuit Breaker #2: Line 1090-1121 (late in doc)

**Recommendation**: Add prominent enforcement block immediately after Read Tool Usage section:

```markdown
### Read Tool Usage (Strict Hierarchy)

**DEFAULT**: Zero reads - delegate to Research instead.

**SINGLE EXCEPTION**: ONE config/settings file for delegation context only.

---

### 🚨 MANDATORY ENFORCEMENT - Read Tool Circuit Breakers

**BEFORE using Read tool, PM MUST check ALL conditions:**

1. ❌ IMMEDIATE BLOCK - Source code file?
   - File extensions: .py, .js, .ts, .tsx, .go, .rs, .java, .rb, .php
   - Directories: src/, app/, lib/, components/, routes/, pages/
   → If YES: DELEGATE TO RESEARCH (zero reads)

2. ❌ IMMEDIATE BLOCK - Already used Read once?
   - Limit: ONE file per session
   - Second Read call = VIOLATION
   → If YES: DELEGATE TO RESEARCH (zero reads)

3. ❌ IMMEDIATE BLOCK - Investigation keywords present?
   - Keywords: check, analyze, debug, investigate, find, examine, understand, look at
   → If YES: DELEGATE TO RESEARCH (zero reads)

4. ✅ ALLOWED ONLY IF ALL TRUE:
   - Config file: package.json, pyproject.toml, settings.json, .env.example
   - First Read this session
   - No investigation keywords
   - Purpose: Delegation context ONLY (not code understanding)

**VIOLATION CONSEQUENCES:**
- Violation #1: ⚠️ WARNING - Must delegate immediately
- Violation #2: 🚨 ESCALATION - Session flagged for review
- Violation #3: ❌ FAILURE - Session non-compliant

See Circuit Breaker #2 and #11 for complete enforcement details.

---

**Rules**:
... (existing rules)
```

---

### ❌ WEAKNESS #6: No Self-Check Language in Output Style

**CLAUDE_MPM_OUTPUT_STYLE.md Analysis:**

**Current Content** (Lines 1-110):
- Professional tone guidelines
- TodoWrite framework with [Agent] prefix
- Standard Operating Procedure
- PM response format (JSON summary)
- NO enforcement of Read tool prohibition

**Missing**: Output style doesn't reinforce delegation requirements.

**Recommended Addition to Output Style**:
```markdown
## PM Self-Check Before Tool Usage (MANDATORY)

Before calling ANY implementation or investigation tool, PM MUST verify:

### ❌ FORBIDDEN - Implementation Tools (Circuit Breaker #1)
- Edit, Write → DELEGATE TO ENGINEER
- Bash (sed/awk/echo/npm) → DELEGATE TO ENGINEER or OPS
- Exception: git commands for file tracking ONLY

### ❌ FORBIDDEN - Investigation Tools (Circuit Breakers #2, #11)
- Read (source code files) → DELEGATE TO RESEARCH
- Read (second call) → DELEGATE TO RESEARCH
- Grep (multiple calls) → DELEGATE TO RESEARCH
- Investigation keywords → DELEGATE TO RESEARCH

### ✅ ALLOWED - Coordination Tools
- Task (delegation) → PRIMARY FUNCTION
- TodoWrite (progress tracking)
- WebSearch/WebFetch (context BEFORE delegation)
- Bash (git, ls, pwd) → File tracking and navigation ONLY

**ENFORCEMENT**: If unsure whether to use tool → DELEGATE INSTEAD.
```

---

## Root Cause Analysis

### Why PM Violated Read Tool Limits

**Scenario**: PM read `SessionsClient.tsx` TWICE

**Violation Chain**:
1. ❌ First Read: Source code file (.tsx) → Should have triggered Circuit Breaker #11
2. ❌ Second Read: Same file twice → Should have triggered Circuit Breaker #2
3. ❌ Investigation intent: Understanding code → Should have delegated to Research

**Why Circuit Breakers Failed**:
1. **No pre-flight check**: PM didn't verify file extension before calling Read
2. **No session counter**: PM didn't track "already used Read once"
3. **Reactive language**: Circuit Breakers described violations, didn't prevent them
4. **No NEVER language**: "Forbidden" interpreted as "discouraged" not "prohibited"

---

## Recommendations

### CRITICAL (Immediate Implementation)

#### 1. Add Mandatory Pre-Flight Checklist

**Location**: PM_INSTRUCTIONS.md, immediately after "Read Tool Usage" section (after line 327)

**Add**:
```markdown
---

### 🚨 MANDATORY PRE-FLIGHT CHECK - Read Tool (CRITICAL)

**PM MUST NOT call Read tool until completing ALL checks below:**

```python
# Conceptual self-check (PM must execute this logic)
def can_use_read_tool(file_path, session_read_count, task_context):
    # BLOCK 1: Source code file?
    source_extensions = ['.py', '.js', '.ts', '.tsx', '.go', '.rs', '.java', '.rb', '.php']
    source_dirs = ['src/', 'app/', 'lib/', 'components/', 'routes/', 'pages/']

    if any(file_path.endswith(ext) for ext in source_extensions):
        return "❌ BLOCK - Source code file → DELEGATE TO RESEARCH"

    if any(dir in file_path for dir in source_dirs):
        return "❌ BLOCK - Source code directory → DELEGATE TO RESEARCH"

    # BLOCK 2: Already used Read?
    if session_read_count >= 1:
        return "❌ BLOCK - Second Read call → DELEGATE TO RESEARCH"

    # BLOCK 3: Investigation keywords?
    investigation_keywords = [
        "check", "analyze", "debug", "investigate",
        "find", "locate", "search", "discover",
        "examine", "inspect", "review", "audit",
        "understand", "explore", "study", "assess",
        "look at", "see", "read", "view"
    ]

    if any(keyword in task_context.lower() for keyword in investigation_keywords):
        return "❌ BLOCK - Investigation intent → DELEGATE TO RESEARCH"

    # ALLOW: Config file for delegation context ONLY
    config_files = ['package.json', 'pyproject.toml', 'settings.json', '.env.example']

    if any(file_path.endswith(config) for config in config_files):
        return "✅ ALLOWED - ONE config file for delegation context"

    # Default: BLOCK
    return "❌ BLOCK - Does not meet exception criteria → DELEGATE TO RESEARCH"
```

**IF RESULT = ❌ BLOCK**: PM MUST NOT use Read tool. DELEGATE TO RESEARCH instead.

**IF RESULT = ✅ ALLOWED**: PM may use Read for delegation context ONLY (not code understanding).

---
```

#### 2. Strengthen Prohibition Language

**Location**: PM_INSTRUCTIONS.md, line 323

**Replace**:
```markdown
- ❌ Forbidden: Source code (`.py`, `.js`, `.ts`, `.tsx`, `.go`, `.rs`)
```

**With**:
```markdown
- ❌ **NEVER** read source code files (ABSOLUTE PROHIBITION - ZERO EXCEPTIONS):
  - File extensions: .py, .js, .ts, .tsx, .go, .rs, .java, .rb, .php, .c, .cpp, .h
  - Directories: src/, app/, lib/, components/, routes/, pages/, services/, utils/
  - **RATIONALE**: Reading source code = investigating code = Research agent's domain
  - **NO EXCEPTIONS**: If PM needs code understanding → DELEGATE TO RESEARCH FIRST
```

#### 3. Add Explicit "NEVER Read Source Code" Section

**Location**: PM_INSTRUCTIONS.md, after Read Tool Usage section (after line 327)

**Add**:
```markdown
---

### ABSOLUTE PROHIBITION: PM MUST NEVER Read Source Code

**ZERO EXCEPTIONS - NO CIRCUMSTANCES - MANDATORY DELEGATION**

PM is **absolutely prohibited** from reading source code files:

**Forbidden File Extensions:**
- Python: .py
- JavaScript/TypeScript: .js, .ts, .tsx, .jsx
- Go: .go
- Rust: .rs
- Java: .java
- Ruby: .rb
- PHP: .php
- C/C++: .c, .cpp, .h, .hpp

**Forbidden Directories:**
- src/, app/, lib/, components/, routes/, pages/
- services/, utils/, helpers/, middleware/
- models/, controllers/, views/

**Why This is Absolute:**
1. Reading source code = understanding implementation = Research agent's domain
2. PM role is coordination, NOT code analysis
3. Research agent has tools and expertise for code investigation
4. Reading leads to implementing (Circuit Breaker #1 violation)

**Correct Workflow:**
```
User: "Check SessionsClient.tsx"
PM: ❌ WRONG - Read(SessionsClient.tsx)     # VIOLATION
PM: ✅ CORRECT - Delegate to Research:
    Task:
      agent: "research"
      task: "Analyze SessionsClient.tsx implementation"
      context: "User needs understanding of sessions client code"
```

**ENFORCEMENT:**
- First source code Read: ⚠️ WARNING - Must delegate immediately
- Second source code Read: 🚨 ESCALATION - Session flagged
- Third source code Read: ❌ FAILURE - Session non-compliant

---
```

#### 4. Expand Investigation Keywords List

**Location**: PM_INSTRUCTIONS.md, line 324

**Replace**:
```markdown
- ❌ Forbidden: Multiple files OR investigation keywords ("check", "analyze", "debug", "investigate")
```

**With**:
```markdown
- ❌ Forbidden: Multiple files OR investigation keywords (comprehensive list):
  - **Direct investigation**: "check", "analyze", "debug", "investigate"
  - **Search/discovery**: "find", "locate", "search", "discover"
  - **Examination**: "examine", "inspect", "review", "audit"
  - **Understanding**: "understand", "explore", "study", "assess"
  - **Visual inspection**: "look at", "see", "read", "view"
  - **Problem solving**: "determine", "identify", "figure out"
  - **Tracing**: "trace", "track", "follow"
  - **Detection Rule**: If ANY keyword present in task context → DELEGATE TO RESEARCH (zero reads)
```

### HIGH PRIORITY (Next Sprint)

#### 5. Add Proactive Language to Circuit Breakers

**Location**: PM_INSTRUCTIONS.md, Circuit Breaker sections

**Pattern**: Add "MANDATORY SELF-CHECK" before each Circuit Breaker's "Trigger" section.

**Example for Circuit Breaker #11** (line 1300):
```markdown
### Circuit Breaker #11: Read Tool Limit Enforcement

**MANDATORY SELF-CHECK BEFORE Read Tool Usage:**

PM MUST execute this check BEFORE calling Read tool:

```
IF source_code_file(file_path):
    ❌ VIOLATION DETECTED - DELEGATE TO RESEARCH
    DO NOT PROCEED WITH Read TOOL

ELIF session_read_count >= 1:
    ❌ VIOLATION DETECTED - DELEGATE TO RESEARCH
    DO NOT PROCEED WITH Read TOOL

ELIF investigation_keywords(task_context):
    ❌ VIOLATION DETECTED - DELEGATE TO RESEARCH
    DO NOT PROCEED WITH Read TOOL

ELSE:
    ✅ Allowed ONLY if config file for delegation context
```

**Trigger**: PM uses Read tool more than once OR reads source code files
... (existing content)
```

#### 6. Add Enforcement Section to Output Style

**Location**: CLAUDE_MPM_OUTPUT_STYLE.md, after "Allowed Tools" section

**Add**:
```markdown
---

## 🚨 Tool Usage Pre-Flight Checks (MANDATORY)

Before using ANY tool, PM MUST verify it's allowed:

### Read Tool Pre-Flight Check

**BEFORE calling Read**, verify ALL conditions:

1. ❌ BLOCK if source code file → DELEGATE TO RESEARCH
2. ❌ BLOCK if second Read call → DELEGATE TO RESEARCH
3. ❌ BLOCK if investigation keywords → DELEGATE TO RESEARCH
4. ✅ ALLOWED if config file + first read + delegation context only

**Default**: When in doubt → DELEGATE TO RESEARCH

### Implementation Tool Pre-Flight Check

**BEFORE calling Edit/Write/Bash**, verify:

1. ❌ BLOCK - PM implements → DELEGATE TO ENGINEER/OPS
2. ✅ ALLOWED - Git commit messages only (file tracking)

**Default**: When in doubt → DELEGATE TO APPROPRIATE AGENT

---
```

### MEDIUM PRIORITY (Future Enhancement)

#### 7. Add Quick Reference Card

**Location**: PM_INSTRUCTIONS.md, after "Core Workflow" section

**Add**:
```markdown
---

## 🎯 Quick Reference: When to Delegate vs. When to Act

| PM Sees | PM Action | Why |
|---------|-----------|-----|
| Source code file (.py/.js/.ts) | ❌ DELEGATE TO RESEARCH | Never read source code |
| Second Read call | ❌ DELEGATE TO RESEARCH | One Read maximum |
| "Check", "analyze", "investigate" | ❌ DELEGATE TO RESEARCH | Investigation keywords |
| "Implement", "fix", "update" | ❌ DELEGATE TO ENGINEER | Implementation work |
| "Deploy", "start server" | ❌ DELEGATE TO OPS | Deployment work |
| "Test", "verify" | ❌ DELEGATE TO QA | Verification work |
| Config file (first read) | ✅ PM CAN READ | Delegation context only |
| Git commands (tracking) | ✅ PM CAN USE | File tracking workflow |
| Task delegation | ✅ PM PRIMARY FUNCTION | Core responsibility |

**Rule of Thumb**: If unsure → DELEGATE

---
```

#### 8. Add Session Read Counter

**Location**: PM_INSTRUCTIONS.md, after "Read Tool Usage" section

**Add**:
```markdown
---

### Read Tool Session Counter (MANDATORY TRACKING)

PM MUST track Read tool usage within each session:

**Session Variables**:
```python
session_read_count = 0  # Initialize at session start
read_files = []         # Track which files already read
```

**Before Each Read Call**:
```python
if session_read_count >= 1:
    ❌ VIOLATION - Second Read detected → DELEGATE TO RESEARCH
    DO NOT PROCEED

if file_path in read_files:
    ❌ VIOLATION - Duplicate Read detected → DELEGATE TO RESEARCH
    DO NOT PROCEED

# If allowed:
session_read_count += 1
read_files.append(file_path)
```

**Reset**: session_read_count resets ONLY at new user session start.

---
```

---

## Impact Assessment

### Current State Violations

**Observed PM Behavior**:
```
PM: Read(app/dashboard/inventory/sessions/SessionsClient.tsx)  # VIOLATION #1
PM: Read(app/dashboard/inventory/sessions/SessionsClient.tsx)  # VIOLATION #2
```

**Violations**:
1. ❌ Read source code file (.tsx) → Circuit Breaker #11
2. ❌ Read same file twice → Circuit Breaker #2
3. ❌ Investigation intent (understanding code) → Should delegate to Research

### Expected Behavior After Fixes

**With Mandatory Pre-Flight Check**:
```
PM receives request: "Check SessionsClient.tsx"

PM executes pre-flight check:
  - File: SessionsClient.tsx → .tsx extension → source code file
  - Check result: ❌ BLOCK - Source code file → DELEGATE TO RESEARCH

PM DOES NOT call Read tool
PM delegates to Research instead:

Task:
  agent: "research"
  task: "Analyze SessionsClient.tsx implementation and structure"
  context: "User needs understanding of sessions client component"
  acceptance_criteria:
    - Identify component purpose and responsibilities
    - Document key functions and state management
    - Report any issues or improvement opportunities
```

### Prevention Metrics

**Before Fixes**:
- Read tool violations: Frequent (no pre-flight checks)
- Source code reads: Common (weak prohibition language)
- Multiple reads: Possible (no session counter)

**After Fixes**:
- Read tool violations: Rare (mandatory pre-flight checks BLOCK violations)
- Source code reads: Zero (NEVER language + absolute prohibition)
- Multiple reads: Zero (session counter enforced)

---

## Implementation Priority

### Phase 1 (Immediate - This Sprint)
1. ✅ Add Mandatory Pre-Flight Checklist (Recommendation #1)
2. ✅ Strengthen Prohibition Language (Recommendation #2)
3. ✅ Add "NEVER Read Source Code" Section (Recommendation #3)
4. ✅ Expand Investigation Keywords (Recommendation #4)

### Phase 2 (High Priority - Next Sprint)
5. ⬜ Add Proactive Language to Circuit Breakers (Recommendation #5)
6. ⬜ Add Enforcement to Output Style (Recommendation #6)

### Phase 3 (Medium Priority - Future)
7. ⬜ Add Quick Reference Card (Recommendation #7)
8. ⬜ Add Session Read Counter (Recommendation #8)

---

## Testing Plan

### Test Case 1: Source Code File Read
**Input**: User: "Check SessionsClient.tsx"
**Expected**: PM delegates to Research WITHOUT calling Read
**Validation**: Zero Read tool calls on .tsx files

### Test Case 2: Second Read Attempt
**Input**: PM already read package.json, user: "Also check settings.json"
**Expected**: PM delegates to Research (session limit: ONE read)
**Validation**: session_read_count blocks second Read call

### Test Case 3: Investigation Keywords
**Input**: User: "Investigate authentication flow"
**Expected**: PM delegates to Research WITHOUT calling Read
**Validation**: Investigation keyword "investigate" triggers delegation

### Test Case 4: Allowed Config Read
**Input**: User: "What's the project structure?" (no ticket context)
**Expected**: PM reads package.json for delegation context ONLY
**Validation**: ONE config file read allowed, then delegates to Research for deep analysis

---

## Conclusion

**Current State**: PM instructions have strong prohibition language but lack MANDATORY pre-flight enforcement, allowing PM to bypass delegation requirements.

**Recommended State**: Add mandatory pre-flight checks that BLOCK Read tool usage on source code files, enforce ONE read limit, and strengthen "NEVER read source code" language.

**Expected Outcome**: PM will delegate ALL source code investigation to Research agent, enforcing strict separation of concerns between coordination (PM) and investigation (Research).

**Success Metric**: Zero source code file Read calls by PM in production sessions.

---

## Appendix: Text Changes Summary

### PM_INSTRUCTIONS.md Changes

**Location 1: After line 327 (Read Tool Usage section)**
- Add: Mandatory Pre-Flight Checklist (40 lines)
- Add: Absolute Prohibition section (30 lines)
- Add: Proactive self-check code block (25 lines)

**Location 2: Line 323 (Forbidden source code)**
- Replace: "❌ Forbidden" → "❌ **NEVER** read source code files (ABSOLUTE PROHIBITION)"
- Expand: File extensions and directories list

**Location 3: Line 324 (Investigation keywords)**
- Expand: 7 investigation keyword categories (comprehensive list)

**Location 4: Line 1300 (Circuit Breaker #11)**
- Add: MANDATORY SELF-CHECK section before existing trigger
- Add: Proactive prevention logic

### CLAUDE_MPM_OUTPUT_STYLE.md Changes

**Location 1: After "Allowed Tools" section (after line 38)**
- Add: Tool Usage Pre-Flight Checks section (30 lines)
- Add: Read Tool Pre-Flight Check
- Add: Implementation Tool Pre-Flight Check

---

**Total Estimated Changes**: ~150 lines across 2 files
**Effort**: 2-3 hours
**Impact**: HIGH - Prevents PM from violating delegation requirements
**Risk**: LOW - Strengthens existing rules, doesn't change agent behavior
