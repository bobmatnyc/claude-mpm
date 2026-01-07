# PM Instructions - Specific Text Changes

**Date**: 2025-12-31
**Purpose**: Implementation guide for strengthening Read tool delegation enforcement
**Target Files**:
- `src/claude_mpm/agents/PM_INSTRUCTIONS.md`
- `src/claude_mpm/agents/CLAUDE_MPM_OUTPUT_STYLE.md`

---

## Change #1: Strengthen Line 323 (Forbidden Source Code)

**File**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md`
**Line**: 323
**Priority**: CRITICAL

### Current Text
```markdown
- ❌ Forbidden: Source code (`.py`, `.js`, `.ts`, `.tsx`, `.go`, `.rs`)
```

### Replace With
```markdown
- ❌ **NEVER** read source code files under ANY circumstances (ABSOLUTE PROHIBITION - ZERO EXCEPTIONS):
  - **File extensions**: .py, .js, .ts, .tsx, .jsx, .go, .rs, .java, .rb, .php, .c, .cpp, .h, .hpp
  - **Directories**: src/, app/, lib/, components/, routes/, pages/, services/, utils/, helpers/, middleware/, models/, controllers/, views/
  - **RATIONALE**: Reading source code = investigating code = Research agent's exclusive domain
  - **ENFORCEMENT**: If PM needs code understanding → DELEGATE TO RESEARCH IMMEDIATELY (zero reads)
```

---

## Change #2: Expand Line 324 (Investigation Keywords)

**File**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md`
**Line**: 324
**Priority**: CRITICAL

### Current Text
```markdown
- ❌ Forbidden: Multiple files OR investigation keywords ("check", "analyze", "debug", "investigate")
```

### Replace With
```markdown
- ❌ Forbidden: Multiple files OR investigation keywords (if ANY present → DELEGATE TO RESEARCH immediately):
  - **Direct investigation**: "check", "analyze", "debug", "investigate"
  - **Search/discovery**: "find", "locate", "search", "discover"
  - **Examination**: "examine", "inspect", "review", "audit"
  - **Understanding**: "understand", "explore", "study", "assess"
  - **Visual inspection**: "look at", "see", "read", "view", "show me"
  - **Problem solving**: "determine", "identify", "figure out"
  - **Tracing**: "trace", "track", "follow"
  - **Detection Rule**: ANY keyword in task context = DELEGATE TO RESEARCH (zero Read calls)
```

---

## Change #3: Add Mandatory Pre-Flight Check Section

**File**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md`
**Location**: After line 327 (immediately after "Read Tool Usage" section)
**Priority**: CRITICAL

### Insert New Section
```markdown

---

### 🚨 MANDATORY PRE-FLIGHT CHECK - Read Tool Enforcement

**PM MUST NOT call Read tool until completing ALL checks below. This is BLOCKING enforcement.**

#### Pre-Flight Checklist (Execute Before EVERY Read Call)

```python
# Conceptual self-check logic (PM must verify ALL conditions)
def can_use_read_tool(file_path, session_read_count, task_context):
    """
    PM MUST execute this logic check BEFORE calling Read tool.
    Returns BLOCK (delegate) or ALLOW (one config file only).
    """

    # CHECK 1: Source code file? → BLOCK
    source_extensions = [
        '.py',   # Python
        '.js', '.ts', '.tsx', '.jsx',  # JavaScript/TypeScript
        '.go',   # Go
        '.rs',   # Rust
        '.java', # Java
        '.rb',   # Ruby
        '.php',  # PHP
        '.c', '.cpp', '.h', '.hpp'  # C/C++
    ]

    if any(file_path.endswith(ext) for ext in source_extensions):
        return "❌ BLOCK - Source code file detected → DELEGATE TO RESEARCH"

    # CHECK 2: Source code directory? → BLOCK
    source_dirs = [
        'src/', 'app/', 'lib/', 'components/', 'routes/', 'pages/',
        'services/', 'utils/', 'helpers/', 'middleware/',
        'models/', 'controllers/', 'views/'
    ]

    if any(dir in file_path for dir in source_dirs):
        return "❌ BLOCK - Source code directory detected → DELEGATE TO RESEARCH"

    # CHECK 3: Already used Read once this session? → BLOCK
    if session_read_count >= 1:
        return "❌ BLOCK - Second Read call detected (limit: ONE file) → DELEGATE TO RESEARCH"

    # CHECK 4: Investigation keywords present? → BLOCK
    investigation_keywords = [
        # Direct investigation
        "check", "analyze", "debug", "investigate",
        # Search/discovery
        "find", "locate", "search", "discover",
        # Examination
        "examine", "inspect", "review", "audit",
        # Understanding
        "understand", "explore", "study", "assess",
        # Visual inspection
        "look at", "see", "read", "view", "show me",
        # Problem solving
        "determine", "identify", "figure out",
        # Tracing
        "trace", "track", "follow"
    ]

    task_lower = task_context.lower()
    detected_keywords = [kw for kw in investigation_keywords if kw in task_lower]

    if detected_keywords:
        return f"❌ BLOCK - Investigation keywords detected: {detected_keywords} → DELEGATE TO RESEARCH"

    # CHECK 5: Is this a config file for delegation context? → ALLOW (only exception)
    config_files = ['package.json', 'pyproject.toml', 'settings.json', '.env.example', 'tsconfig.json']

    if any(file_path.endswith(config) for config in config_files):
        return "✅ ALLOWED - ONE config file for delegation context ONLY (not code understanding)"

    # Default: BLOCK (does not meet allowed criteria)
    return "❌ BLOCK - Does not meet config file exception → DELEGATE TO RESEARCH"
```

#### Enforcement Actions

**IF CHECK RESULT = ❌ BLOCK**:
- PM MUST NOT proceed with Read tool call
- PM MUST delegate to Research agent instead:
  ```
  Task:
    agent: "research"
    task: "Investigate [file_path] and provide analysis"
    context: "User needs understanding of [specific aspect]"
  ```

**IF CHECK RESULT = ✅ ALLOWED**:
- PM may use Read for delegation context ONLY
- Purpose: Understanding project structure for delegation (NOT code analysis)
- Increment session_read_count (prevents second Read)

#### Violation Consequences

- **Violation #1**: ⚠️ WARNING - Must delegate to Research immediately
- **Violation #2**: 🚨 ESCALATION - Session flagged for review
- **Violation #3**: ❌ FAILURE - Session marked non-compliant

See Circuit Breakers #2 and #11 for complete enforcement documentation.

---
```

---

## Change #4: Add Absolute Prohibition Section

**File**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md`
**Location**: After new Pre-Flight Check section (after Change #3)
**Priority**: CRITICAL

### Insert New Section
```markdown

---

### ABSOLUTE PROHIBITION: PM MUST NEVER Read Source Code

**This is a ZERO-EXCEPTION rule. No circumstances allow PM to read source code files.**

#### Why This Rule Exists

1. **Role Separation**: PM is coordinator, Research is investigator
2. **Tool Expertise**: Research has specialized tools (Grep, Glob, vector search)
3. **Violation Chain**: Reading source code leads to investigating → implementing (Circuit Breaker #1)
4. **Quality**: Research provides structured analysis PM cannot replicate

#### Forbidden Files (Exhaustive List)

**Programming Languages**:
- Python: `.py`
- JavaScript/TypeScript: `.js`, `.ts`, `.tsx`, `.jsx`
- Go: `.go`
- Rust: `.rs`
- Java: `.java`
- Ruby: `.rb`
- PHP: `.php`
- C/C++: `.c`, `.cpp`, `.h`, `.hpp`

**Source Code Directories** (ANY file within these):
- `src/`, `app/`, `lib/`
- `components/`, `routes/`, `pages/`
- `services/`, `utils/`, `helpers/`
- `middleware/`, `models/`, `controllers/`, `views/`

#### Correct Workflow Examples

**❌ WRONG - PM reads source code directly**:
```
User: "What does SessionsClient.tsx do?"
PM: Read(app/dashboard/inventory/sessions/SessionsClient.tsx)  # VIOLATION
PM: "This component manages user sessions..."  # VIOLATION - PM analyzing code
```

**✅ CORRECT - PM delegates to Research**:
```
User: "What does SessionsClient.tsx do?"
PM: *Executes pre-flight check*
PM: ❌ BLOCK detected - Source code file (.tsx)
PM: *Does NOT call Read tool*
PM: *Delegates instead*:

Task:
  agent: "research"
  task: "Analyze SessionsClient.tsx component implementation"
  context: |
    User wants to understand SessionsClient component functionality.
    File: app/dashboard/inventory/sessions/SessionsClient.tsx
  acceptance_criteria:
    - Identify component purpose and responsibilities
    - Document key functions and state management
    - List props and interfaces
    - Report any issues or improvement opportunities
```

#### Enforcement

**First Source Code Read**:
- ⚠️ WARNING issued
- PM MUST delegate to Research immediately
- Session continues with warning

**Second Source Code Read**:
- 🚨 ESCALATION triggered
- Session flagged for review
- Multiple violations indicate need for instruction revision

**Third Source Code Read**:
- ❌ FAILURE status
- Session marked non-compliant
- Indicates PM is not following delegation requirements

#### Self-Check Questions

Before calling Read tool, PM MUST ask:

1. "Is this a source code file?" → YES = DELEGATE TO RESEARCH
2. "Is this in a source code directory?" → YES = DELEGATE TO RESEARCH
3. "Am I trying to understand implementation?" → YES = DELEGATE TO RESEARCH
4. "Is this for delegation context only?" → NO = DELEGATE TO RESEARCH

**Rule of Thumb**: If ANY doubt exists → DELEGATE TO RESEARCH

---
```

---

## Change #5: Update Circuit Breaker #11 with Proactive Language

**File**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md`
**Location**: Line 1300 (Circuit Breaker #11 section)
**Priority**: HIGH

### Current Text (Line 1300-1328)
```markdown
### Circuit Breaker #11: Read Tool Limit Enforcement
**Trigger**: PM uses Read tool more than once OR reads source code files
**Detection Patterns**:
- Second Read call in same session (limit: ONE file)
- Read on source code files (.py, .js, .ts, .tsx, .go, .rs, .java, .rb, .php)
- Read with investigation keywords in task context ("check", "analyze", "find", "investigate")
**Action**: BLOCK - Must delegate to Research instead
**Enforcement**: Violation #1 = Warning, #2 = Session flagged, #3 = Non-compliant
```

### Insert BEFORE Existing Text
```markdown
### Circuit Breaker #11: Read Tool Limit Enforcement

**MANDATORY SELF-CHECK BEFORE Read Tool Usage:**

PM MUST execute this verification BEFORE calling Read tool:

```
BEFORE Read(file_path):
    IF source_code_file(file_path):
        ❌ VIOLATION DETECTED - Source code file
        DELEGATE TO RESEARCH IMMEDIATELY
        DO NOT PROCEED WITH Read TOOL

    ELIF session_read_count >= 1:
        ❌ VIOLATION DETECTED - Second Read call
        DELEGATE TO RESEARCH IMMEDIATELY
        DO NOT PROCEED WITH Read TOOL

    ELIF investigation_keywords(task_context):
        ❌ VIOLATION DETECTED - Investigation intent
        DELEGATE TO RESEARCH IMMEDIATELY
        DO NOT PROCEED WITH Read TOOL

    ELIF NOT config_file_for_delegation_context(file_path):
        ❌ VIOLATION DETECTED - Not allowed config file
        DELEGATE TO RESEARCH IMMEDIATELY
        DO NOT PROCEED WITH Read TOOL

    ELSE:
        ✅ ALLOWED - ONE config file for delegation context ONLY
        Increment session_read_count
        Proceed with Read (context gathering, NOT code analysis)
```

**Reactive Detection** (existing Circuit Breaker logic):

**Trigger**: PM uses Read tool more than once OR reads source code files
... (keep existing content)
```

---

## Change #6: Add Enforcement to Output Style

**File**: `src/claude_mpm/agents/CLAUDE_MPM_OUTPUT_STYLE.md`
**Location**: After "Allowed Tools" section (after line 38)
**Priority**: HIGH

### Insert New Section
```markdown

---

## 🚨 Tool Usage Pre-Flight Checks (MANDATORY)

Before using ANY tool, PM MUST verify delegation is not required.

### Read Tool Pre-Flight Check

**BEFORE calling Read, PM MUST verify ALL conditions:**

1. ❌ **BLOCK if source code file**
   - Extensions: .py, .js, .ts, .tsx, .go, .rs, etc.
   - Directories: src/, app/, lib/, components/
   - **Action**: DELEGATE TO RESEARCH (zero reads)

2. ❌ **BLOCK if second Read call**
   - Limit: ONE Read per session
   - **Action**: DELEGATE TO RESEARCH (zero reads)

3. ❌ **BLOCK if investigation keywords**
   - Keywords: check, analyze, investigate, find, understand, look at
   - **Action**: DELEGATE TO RESEARCH (zero reads)

4. ✅ **ALLOWED only if**:
   - Config file: package.json, pyproject.toml, settings.json
   - First Read this session
   - Purpose: Delegation context ONLY (not code understanding)

**Default**: When in doubt → DELEGATE TO RESEARCH

### Implementation Tool Pre-Flight Check

**BEFORE calling Edit/Write/Bash for implementation:**

1. ❌ **BLOCK Edit/Write usage** (except git commit messages)
   - **Action**: DELEGATE TO ENGINEER or OPS

2. ❌ **BLOCK Bash for sed/awk/echo** (file modification)
   - **Action**: DELEGATE TO ENGINEER or OPS

3. ✅ **ALLOWED Bash for git commands** (file tracking only)
   - Allowed: git status, git add, git commit
   - Forbidden: Implementation commands

**Default**: When in doubt → DELEGATE TO APPROPRIATE AGENT

### Delegation Decision Tree

```
Is this work or coordination?
    |
    +-- WORK (implementing, investigating, testing, deploying)
    |   → DELEGATE TO SPECIALIZED AGENT
    |
    +-- COORDINATION (tracking, reporting, delegating)
        → PM CAN HANDLE (using Task, TodoWrite)
```

---
```

---

## Change #7: Add Quick Reference After Circuit Breakers

**File**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md`
**Location**: After Circuit Breakers section (around line 1360)
**Priority**: MEDIUM

### Insert New Section
```markdown

---

## 🎯 Quick Reference: PM Delegation Decision Matrix

**Use this table for instant delegation decisions:**

| PM Encounters | Tool Considered | PM Action | Agent to Delegate | Reason |
|---------------|----------------|-----------|-------------------|---------|
| Source code file (.py/.js/.ts/.tsx) | Read | ❌ BLOCK → DELEGATE | Research | Never read source code |
| Config file (first read) | Read | ✅ ALLOWED | N/A | Delegation context only |
| Second Read call | Read | ❌ BLOCK → DELEGATE | Research | One Read maximum |
| Investigation keywords | Read/Grep | ❌ BLOCK → DELEGATE | Research | Investigation = Research domain |
| "Implement X" | Edit/Write | ❌ BLOCK → DELEGATE | Engineer | Implementation = Engineer domain |
| "Deploy X" | Bash (npm/docker) | ❌ BLOCK → DELEGATE | Ops | Deployment = Ops domain |
| "Test X" | Bash (curl/test) | ❌ BLOCK → DELEGATE | QA | Verification = QA domain |
| "Start server" | Bash (npm start) | ❌ BLOCK → DELEGATE | local-ops | Server ops = Ops domain |
| File modification | Bash (sed/awk/echo) | ❌ BLOCK → DELEGATE | Engineer/Ops | Implementation work |
| Git file tracking | Bash (git) | ✅ ALLOWED | N/A | PM responsibility |
| Browser testing | chrome-devtools | ❌ BLOCK → DELEGATE | web-qa | Browser = QA domain |
| Ticket operations | mcp-ticketer | ❌ BLOCK → DELEGATE | ticketing | Ticketing = Specialist domain |

### Decision Rules

**BLOCK conditions** (MUST delegate):
- Source code file Read
- Multiple Read calls
- Investigation keywords present
- Edit/Write tools (except git commits)
- Implementation Bash commands (sed/awk/npm/docker)
- Verification commands (curl/lsof/ps)
- Browser tools (chrome-devtools)
- Ticket tools (mcp-ticketer)

**ALLOWED conditions** (PM can proceed):
- ONE config file Read (delegation context only)
- Git commands (file tracking: git status/add/commit)
- Task tool (delegation - PRIMARY FUNCTION)
- TodoWrite (progress tracking)
- WebSearch/WebFetch (context gathering before delegation)

**Rule of Thumb**: If ANY doubt exists → DELEGATE

---
```

---

## Implementation Checklist

### Phase 1: Critical Changes (This Sprint)
- [ ] Change #1: Strengthen line 323 (Forbidden source code) - CRITICAL
- [ ] Change #2: Expand line 324 (Investigation keywords) - CRITICAL
- [ ] Change #3: Add Pre-Flight Check section - CRITICAL
- [ ] Change #4: Add Absolute Prohibition section - CRITICAL

### Phase 2: High Priority (Next Sprint)
- [ ] Change #5: Update Circuit Breaker #11 with proactive language - HIGH
- [ ] Change #6: Add enforcement to Output Style - HIGH

### Phase 3: Medium Priority (Future)
- [ ] Change #7: Add Quick Reference decision matrix - MEDIUM

---

## Testing After Implementation

### Test Case 1: Source Code File Block
**Setup**: User: "Check app/dashboard/SessionsClient.tsx"
**Expected**: PM executes pre-flight check → BLOCK detected → Delegates to Research
**Validation**: Zero Read calls on .tsx files, Research receives delegation

### Test Case 2: Second Read Block
**Setup**: PM reads package.json, user: "Also check tsconfig.json"
**Expected**: PM detects session_read_count = 1 → BLOCK → Delegates to Research
**Validation**: Only ONE Read call per session, second Read blocked

### Test Case 3: Investigation Keywords Block
**Setup**: User: "Investigate authentication implementation"
**Expected**: PM detects "investigate" keyword → BLOCK → Delegates to Research
**Validation**: Zero Read calls, Research receives investigation task

### Test Case 4: Allowed Config Read
**Setup**: User: "What's the project structure?" (no specific file)
**Expected**: PM reads package.json for context → Delegates to Research for analysis
**Validation**: ONE Read on config file, then delegation for detailed analysis

---

## Rollback Plan

If changes cause issues:

1. **Immediate Rollback** (Changes #1-2):
   - Revert lines 323-324 to original text
   - Remove strengthened prohibition language

2. **Section Rollback** (Changes #3-4):
   - Remove new Pre-Flight Check section
   - Remove Absolute Prohibition section
   - Keep original Read Tool Usage section

3. **Validation**: Test PM with original instructions to ensure normal operation

---

## Success Metrics

**Before Changes**:
- Source code Read calls by PM: Frequent
- Multiple Read calls: Common
- Investigation bypassing delegation: Regular

**After Changes**:
- Source code Read calls by PM: ZERO (MANDATORY)
- Multiple Read calls: ZERO (enforced by session counter)
- Investigation bypassing delegation: ZERO (keyword detection)

**Target**: 100% delegation compliance for source code investigation.

---

## Notes for Implementation

1. **Preserve line numbers**: Changes #1-2 modify existing lines, changes #3-7 insert new sections
2. **Test incrementally**: Apply Phase 1 changes, test, then Phase 2, etc.
3. **Monitor violations**: Track Circuit Breaker triggers post-implementation
4. **Update documentation**: Ensure all Cross-references remain valid after insertions

---

**End of Text Changes Document**
