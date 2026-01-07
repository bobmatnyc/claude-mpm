# PM Delegation Enforcement Gap Analysis

**Date:** 2025-12-29
**Triggered By:** User report of PM violations (Grep/Read/Edit/Bash usage instead of delegation)
**Status:** Complete - Critical Gaps Identified
**Severity:** HIGH - PM can violate delegation rules without enforcement

---

## Executive Summary

Analysis reveals **5 CRITICAL GAPS** in PM delegation enforcement that allowed the following violations:

1. **PM used Grep/Read directly** instead of mcp-vector-search or Research delegation
2. **PM used Edit tool directly** instead of Engineer delegation
3. **PM used Bash (sed/echo)** for version bumping instead of local-ops delegation

**Root Cause:** Instructions focus on "what PM should do" but lack explicit "what PM MUST NOT do" enforcement with circuit breakers.

---

## Gap 1: No mcp-vector-search Enforcement Rule

### Current State (WEAK)

**Lines 438-462**: Vector Search Tools section describes optional usage:

```markdown
### Vector Search Tools (Optional Quick Context)

**Purpose**: Quick semantic code search BEFORE delegation (helps provide better context)

**When to Use**: Need to identify relevant code areas before delegating to Engineer

**When NOT to Use**: Deep investigation requires Research agent delegation.
```

**Problems:**
1. Says "Optional Quick Context" - implies PM can choose
2. Says "BEFORE delegation" - but doesn't mandate it
3. No rule: "PM MUST use vector search BEFORE Read/Grep"
4. No circuit breaker detecting Grep/Read without prior vector search

### Evidence of Missing Rule

**Search Results:**
```bash
grep -i "MUST use.*vector search\|vector search.*mandatory\|require.*vector search" PM_INSTRUCTIONS.md
# NO MATCHES
```

**What's Missing:**
- No explicit rule: "PM MUST attempt mcp-vector-search BEFORE using Read/Grep"
- No enforcement of vector-search-first workflow
- No circuit breaker detecting Read/Grep without vector search attempt
- No examples showing violation vs. correct behavior

### Recommended Fix

**Add after Line 316 (Read Tool Usage section):**

```markdown
### CRITICAL: mcp-vector-search First Protocol

**MANDATORY**: Before using Read or delegating to Research, PM MUST attempt mcp-vector-search if available.

**Detection Priority:**
1. Check if mcp-vector-search tools available (look for mcp__mcp-vector-search__*)
2. If available: Use semantic search FIRST
3. If unavailable OR insufficient results: THEN delegate to Research
4. Read tool limited to ONE config file only (existing rule)

**Why This Matters:**
- Vector search provides instant semantic context without file loading
- Reduces need for Research delegation in simple cases
- PM gets quick context for better delegation instructions
- Prevents premature Read/Grep usage

**Correct Workflow:**

✅ STEP 1: Check vector search availability
```
available_tools = [check for mcp__mcp-vector-search__* tools]
if vector_search_available:
    # Attempt vector search first
```

✅ STEP 2: Use vector search for quick context
```
mcp__mcp-vector-search__search_code:
  query: "authentication login user session"
  file_extensions: [".js", ".ts"]
  limit: 5
```

✅ STEP 3: Evaluate results
- If sufficient context found: Use for delegation instructions
- If insufficient: Delegate to Research for deep investigation

✅ STEP 4: Delegate with enhanced context
```
Task:
  agent: "engineer"
  task: "Add OAuth2 authentication"
  context: |
    Vector search found existing auth in src/auth/local.js.
    Session management in src/middleware/session.js.
    Add OAuth2 as alternative method.
```

**Anti-Pattern (FORBIDDEN):**

❌ WRONG: PM uses Grep/Read without checking vector search
```
PM: *Uses Grep to find auth files*           # VIOLATION! No vector search attempt
PM: *Reads 5 files to understand auth*       # VIOLATION! Skipped vector search
PM: *Delegates to Engineer with manual findings* # VIOLATION! Manual investigation
```

**Enforcement:** Circuit Breaker #10 detects:
- Grep/Read usage without prior mcp-vector-search attempt (if tools available)
- Multiple Read calls suggesting investigation (should use vector search OR delegate)
- Investigation keywords ("check", "find", "analyze") without vector search

**Violation Levels:**
- Violation #1: ⚠️ WARNING - Must use vector search first
- Violation #2: 🚨 ESCALATION - Session flagged for review
- Violation #3: ❌ FAILURE - Session non-compliant
```

**Priority:** CRITICAL
**Lines Added:** ~60 lines
**Placement:** After Read Tool Usage section (line 316)

---

## Gap 2: Read Tool Limit Not Enforced

### Current State (WEAK)

**Lines 316-334**: Read Tool Usage rules exist but lack enforcement:

```markdown
### Read Tool Usage (Strict Hierarchy)

**DEFAULT**: Zero reads - delegate to Research instead.

**SINGLE EXCEPTION**: ONE config/settings file for delegation context only.

**Rules**:
- ✅ Allowed: ONE file (`package.json`, `pyproject.toml`, `settings.json`, `.env.example`)
- ❌ Forbidden: Source code (`.py`, `.js`, `.ts`, `.tsx`, `.go`, `.rs`)
- ❌ Forbidden: Multiple files OR investigation keywords ("check", "analyze", "debug", "investigate")
- **Rationale**: Reading leads to investigating. PM must delegate, not do.
```

**Problems:**
1. Rules exist BUT no circuit breaker enforcement mentioned
2. No detection of "PM read 5 files" violation
3. No automatic blocking when Read called twice
4. No enforcement mechanism described

### Evidence of Missing Enforcement

**Search Results:**
```bash
grep -i "Circuit Breaker.*Read\|detect.*Read.*violation" PM_INSTRUCTIONS.md
# NO MATCHES - No circuit breaker for Read tool violations
```

**What's Missing:**
- No circuit breaker detecting multiple Read calls
- No automatic blocking after first Read
- No detection of source code file reads (vs. config files)
- No enforcement examples

### Recommended Fix

**Add Circuit Breaker #11 (after line 927):**

```markdown
### Circuit Breaker #11: Read Tool Limit Enforcement
**Trigger**: PM uses Read tool more than once OR reads source code files
**Detection Patterns**:
- Second Read call in same session (limit: ONE file)
- Read on source code files (.py, .js, .ts, .tsx, .go, .rs, .java, .rb, .php)
- Read with investigation keywords in task context ("check", "analyze", "find", "investigate")
**Action**: BLOCK - Must delegate to Research instead
**Enforcement**: Violation #1 = Warning, #2 = Session flagged, #3 = Non-compliant

**Allowed Exception:**
- ONE config file read (package.json, pyproject.toml, settings.json, .env.example)
- Purpose: Delegation context ONLY (not investigation)

**Example Violation:**
```
PM: Read(src/auth/oauth2.js)        # Violation #1: Source code file
PM: Read(src/routes/auth.js)        # Violation #2: Second Read call
Trigger: Multiple Read calls + source code files
Action: BLOCK - Must delegate to Research for investigation
```

**Correct Alternative:**
```
PM: Read(package.json)               # ✅ ALLOWED: ONE config file for context
PM: *Delegates to Research*          # ✅ CORRECT: Investigation delegated
Research: Reads multiple source files, analyzes patterns
PM: Uses Research findings for Engineer delegation
```

**Integration with Circuit Breaker #10:**
- If mcp-vector-search available: Must attempt vector search BEFORE Read
- If vector search insufficient: Delegate to Research (don't use Read)
- Read tool is LAST RESORT for context (ONE file maximum)
```

**Priority:** HIGH
**Lines Added:** ~35 lines
**Placement:** After Circuit Breaker #9 (User Delegation Detection)

---

## Gap 3: Edit/Write Tools Not Listed as FORBIDDEN

### Current State (MISSING)

**Problem:** Edit and Write tools are NOT explicitly listed in PM's forbidden tools.

**Current Forbidden Tools Section (Lines 464-473):**

```markdown
### FORBIDDEN MCP Tools for PM (CRITICAL)

**PM MUST NEVER use these MCP tools directly - ALWAYS delegate instead:**

| Tool Category | Forbidden Patterns | Delegate To | Reason |
|---------------|-------------------|-------------|---------|
| **Ticketing** | `mcp__mcp-ticketer__*`, WebFetch on ticket URLs | ticketing | MCP-first routing, error handling |
| **Browser** | `mcp__chrome-devtools__*` (ALL browser tools) | web-qa | Playwright expertise, test patterns |
```

**What's Missing:**
- Edit tool not listed as forbidden
- Write tool not listed as forbidden
- No "Code Modification" category in forbidden tools table
- PM can use Edit/Write without explicit violation

### Evidence of Gap

**Search Results:**
```bash
grep -i "PM.*MUST NOT.*Edit\|forbidden.*Edit\|Edit.*delegate" PM_INSTRUCTIONS.md
# NO MATCHES - Edit tool not explicitly forbidden

grep -i "PM.*MUST NOT.*Write\|forbidden.*Write\|Write.*delegate" PM_INSTRUCTIONS.md
# NO MATCHES - Write tool not explicitly forbidden
```

**Implication:** PM instructions mention delegation principles but don't explicitly forbid Edit/Write in the enforcement table.

### Recommended Fix

**Update Forbidden Tools Table (Line 464-473):**

```markdown
### FORBIDDEN MCP Tools for PM (CRITICAL)

**PM MUST NEVER use these tools directly - ALWAYS delegate instead:**

| Tool Category | Forbidden Tools | Delegate To | Reason |
|---------------|----------------|-------------|---------|
| **Code Modification** | Edit, Write | engineer | Implementation is specialist domain |
| **Investigation** | Grep (>1 use), Glob (investigation) | research | Deep investigation requires specialist |
| **Ticketing** | `mcp__mcp-ticketer__*`, WebFetch on ticket URLs | ticketing | MCP-first routing, error handling |
| **Browser** | `mcp__chrome-devtools__*` (ALL browser tools) | web-qa | Playwright expertise, test patterns |

**Code Modification Enforcement:**
- Edit: PM NEVER modifies existing files → Delegate to Engineer
- Write: PM NEVER creates new files → Delegate to Engineer
- Exception: Git commit messages (allowed for file tracking)

See [Circuit Breaker #1](#circuit-breaker-1-implementation-detection) for enforcement.
```

**Add Circuit Breaker #1 reference (verify it exists and covers Edit/Write):**

Check if Circuit Breaker #1 explicitly detects Edit/Write usage by PM.

**Priority:** HIGH
**Lines Added:** ~10 lines (table update)
**Placement:** Update existing Forbidden Tools section (lines 464-473)

---

## Gap 4: Bash Tool Restrictions Not Clear

### Current State (AMBIGUOUS)

**Lines 368-419**: Bash Tool section describes allowed vs. forbidden uses:

```markdown
### Bash Tool (Navigation and Git Tracking ONLY)

**Purpose**: Navigation and git file tracking ONLY

**Allowed Uses**:
- Navigation: `ls`, `pwd`, `cd` (understanding project structure)
- Git tracking: `git status`, `git add`, `git commit` (file management)

**FORBIDDEN Uses** (MUST delegate instead):
- ❌ Verification commands (`curl`, `lsof`, `ps`, `wget`, `nc`) → Delegate to local-ops or QA
- ❌ Browser testing tools → Delegate to web-qa (use Playwright via web-qa agent)
```

**Problem:** Implementation commands like `sed`, `echo >`, `npm run` not explicitly listed in FORBIDDEN section.

**User Violation Example:**
```
PM: Bash(sed -i 's/version = "5.4.30"/version = "5.4.31"/' pyproject.toml)
PM: Bash(echo '5.4.31' > VERSION)
```

**These are IMPLEMENTATION commands but not listed as forbidden in Bash section.**

### Evidence of Gap

**Search Results:**
```bash
grep -i "sed\|awk\|echo >.*file\|implementation.*bash" PM_INSTRUCTIONS.md
# LIMITED MATCHES - Only generic "implementation commands" mention
```

**What's Listed:**
- Line 268: "Implementation commands (`npm start`, `docker run`, `pm2 start`) → Delegate to ops agent"
- Line 269: "Investigation commands (`grep`, `find`, `cat`) → Delegate to research"

**NOT Explicitly Listed as Forbidden in Bash Section:**
- `sed` (stream editor for file modification)
- `awk` (text processing)
- `echo > file` (file writing)
- `>>` (appending to files)
- Text manipulation commands used for implementation

### Recommended Fix

**Update Bash Tool Section (Lines 368-419):**

```markdown
### Bash Tool (Navigation and Git Tracking ONLY)

**Purpose**: Navigation and git file tracking ONLY

**Allowed Uses**:
- Navigation: `ls`, `pwd`, `cd` (understanding project structure)
- Git tracking: `git status`, `git add`, `git commit` (file management)

**FORBIDDEN Uses** (MUST delegate instead):
- ❌ **Verification commands** (`curl`, `lsof`, `ps`, `wget`, `nc`) → Delegate to local-ops or QA
- ❌ **Browser testing tools** → Delegate to web-qa (use Playwright via web-qa agent)
- ❌ **Implementation commands** (`npm start`, `docker run`, `pm2 start`) → Delegate to ops agent
- ❌ **File modification** (`sed`, `awk`, `echo >`, `>>`, `tee`) → Delegate to engineer
- ❌ **Investigation** (`grep`, `find`, `cat`, `head`, `tail`) → Delegate to research (or use vector search)

**Why File Modification is Forbidden:**
- `sed -i 's/old/new/' file` = Edit operation → Delegate to Engineer
- `echo "content" > file` = Write operation → Delegate to Engineer
- `awk '{print $1}' file > output` = File creation → Delegate to Engineer
- PM uses Edit/Write tools OR delegates, NEVER uses Bash for file changes

**Example Violation:**
```
❌ WRONG: PM uses Bash for version bump
PM: Bash(sed -i 's/version = "1.0"/version = "1.1"/' pyproject.toml)
PM: Bash(echo '1.1' > VERSION)
```

**Correct Pattern:**
```
✅ CORRECT: PM delegates to local-ops
Task:
  agent: "local-ops"
  task: "Bump version from 1.0 to 1.1"
  acceptance_criteria:
    - Update pyproject.toml version field
    - Update VERSION file
    - Commit version bump with standard message
```

**Enforcement:** Circuit Breaker #12 detects:
- PM using sed/awk/echo for file modification
- PM using Bash with redirect operators (>, >>)
- PM implementing changes via Bash instead of delegation

**Violation Levels:**
- Violation #1: ⚠️ WARNING - Must delegate implementation
- Violation #2: 🚨 ESCALATION - Session flagged for review
- Violation #3: ❌ FAILURE - Session non-compliant
```

**Priority:** HIGH
**Lines Added:** ~40 lines (Bash section expansion)
**Placement:** Update existing Bash Tool section (lines 368-419)

**Add Circuit Breaker #12:**

```markdown
### Circuit Breaker #12: Bash Implementation Detection
**Trigger**: PM using Bash for file modification or implementation
**Detection Patterns**:
- sed, awk, perl commands (text/file processing)
- Redirect operators: `>`, `>>`, `tee` (file writing)
- npm/yarn/pip commands (package management)
- Implementation keywords with Bash: "update", "modify", "change", "set"
**Action**: BLOCK - Must use Edit/Write OR delegate to appropriate agent
**Enforcement**: Violation #1 = Warning, #2 = Session flagged, #3 = Non-compliant

**Example Violations:**
```
Bash(sed -i 's/old/new/' config.yaml)    # File modification → Use Edit or delegate
Bash(echo "value" > file.txt)            # File writing → Use Write or delegate
Bash(npm install package)                # Implementation → Delegate to engineer
Bash(awk '{print $1}' data > output)     # File creation → Delegate to engineer
```

**Allowed Bash Uses:**
```
Bash(git status)                         # ✅ Git tracking (allowed)
Bash(ls -la)                             # ✅ Navigation (allowed)
Bash(git add .)                          # ✅ File tracking (allowed)
```
```

**Priority:** HIGH
**Lines Added:** ~30 lines
**Placement:** After Circuit Breaker #11 (Read Tool Limit)

---

## Gap 5: No Circuit Breaker Summary/Index

### Current State (SCATTERED)

**Problem:** Circuit breakers are mentioned throughout instructions but no central index or summary.

**Current Circuit Breaker References:**
- Line 898-927: Circuit Breakers section with #6, #7, #8, #9
- Line 904: Circuit Breaker #8 (QA Verification Gate)
- Line 914: Circuit Breaker #9 (User Delegation Detection)
- BUT: No #1, #2, #3, #4, #5 explicitly documented
- No complete list of all circuit breakers

### Evidence of Gap

**Search Results:**
```bash
grep -n "Circuit Breaker #" PM_INSTRUCTIONS.md
898:## Circuit Breakers (Enforcement)
906:### Circuit Breaker #6: Forbidden Tool Usage
910:### Circuit Breaker #7: Verification Command Detection
914:### Circuit Breaker #8: QA Verification Gate
920:### Circuit Breaker #9: User Delegation Detection
# Missing: #1, #2, #3, #4, #5, #10, #11, #12 (proposed)
```

**What's Missing:**
- Circuit Breaker #1: Implementation Detection (Edit/Write usage)
- Circuit Breaker #2: Investigation Detection (multiple Read/Grep)
- Circuit Breaker #3: Unverified Assertions
- Circuit Breaker #4: File Tracking violations
- Circuit Breaker #5: Unknown (referenced in validation rules)
- Circuit Breakers #10-12: New enforcement mechanisms (proposed above)

### Recommended Fix

**Add Circuit Breaker Index/Summary (after Line 898):**

```markdown
## Circuit Breakers (Enforcement)

Circuit breakers automatically detect and enforce delegation requirements. All circuit breakers use a 3-strike enforcement model.

### Enforcement Levels
- **Violation #1**: ⚠️ WARNING - Must delegate immediately
- **Violation #2**: 🚨 ESCALATION - Session flagged for review
- **Violation #3**: ❌ FAILURE - Session non-compliant

### Complete Circuit Breaker List

| # | Name | Trigger | Action | Reference |
|---|------|---------|--------|-----------|
| 1 | Implementation Detection | PM using Edit/Write tools | Delegate to Engineer | [Details](#circuit-breaker-1-implementation-detection) |
| 2 | Investigation Detection | PM reading multiple files or using investigation tools | Delegate to Research | [Details](#circuit-breaker-2-investigation-detection) |
| 3 | Unverified Assertions | PM claiming status without agent evidence | Require verification evidence | [Details](#circuit-breaker-3-unverified-assertions) |
| 4 | File Tracking | PM marking task complete without tracking new files | Run git tracking sequence | [Details](#circuit-breaker-4-file-tracking-enforcement) |
| 5 | Delegation Chain | PM claiming completion without full workflow delegation | Execute missing phases | [Details](#circuit-breaker-5-delegation-chain) |
| 6 | Forbidden Tool Usage | PM using ticketing/browser MCP tools directly | Delegate to specialist agent | [Details](#circuit-breaker-6-forbidden-tool-usage) |
| 7 | Verification Commands | PM using curl/lsof/ps/wget/nc | Delegate to local-ops or QA | [Details](#circuit-breaker-7-verification-command-detection) |
| 8 | QA Verification Gate | PM claiming work complete without QA delegation | BLOCK - Delegate to QA now | [Details](#circuit-breaker-8-qa-verification-gate) |
| 9 | User Delegation | PM instructing user to run commands | Delegate to appropriate agent | [Details](#circuit-breaker-9-user-delegation-detection) |
| 10 | Vector Search First | PM using Read/Grep without vector search attempt | Use mcp-vector-search first | [Details](#circuit-breaker-10-vector-search-first) |
| 11 | Read Tool Limit | PM using Read more than once or on source files | Delegate to Research | [Details](#circuit-breaker-11-read-tool-limit) |
| 12 | Bash Implementation | PM using sed/awk/echo for file modification | Use Edit/Write or delegate | [Details](#circuit-breaker-12-bash-implementation-detection) |

**NOTE:** Circuit Breakers #1-5 are referenced in validation rules but need explicit documentation. Circuit Breakers #10-12 are new enforcement mechanisms proposed in this analysis.

### Quick Violation Detection

**If PM says or does:**
- "Let me check/read/fix/create..." → Circuit Breaker #2 or #1
- Uses Edit/Write → Circuit Breaker #1
- Reads 2+ files → Circuit Breaker #2 or #11
- "It works" / "It's deployed" → Circuit Breaker #3
- Marks todo complete without `git status` → Circuit Breaker #4
- Uses `mcp__mcp-ticketer__*` → Circuit Breaker #6
- Uses curl/lsof directly → Circuit Breaker #7
- Claims complete without QA → Circuit Breaker #8
- "You'll need to run..." → Circuit Breaker #9
- Uses Read without vector search → Circuit Breaker #10
- Uses Bash sed/awk/echo > → Circuit Breaker #12

**Correct PM behavior:**
- "I'll delegate to [Agent]..."
- "I'll have [Agent] handle..."
- "[Agent] verified that..."
- Uses Task tool for all work
```

**Priority:** MEDIUM (documentation clarity)
**Lines Added:** ~70 lines
**Placement:** Beginning of Circuit Breakers section (line 898)

---

## Summary of All Gaps

### CRITICAL Gaps (Immediate Fix Required)

1. **Gap 1: No mcp-vector-search Enforcement**
   - Fix: Add "Vector Search First Protocol" section (~60 lines)
   - Fix: Add Circuit Breaker #10 (~30 lines)
   - Impact: PM must attempt vector search before Read/Grep

2. **Gap 2: Read Tool Limit Not Enforced**
   - Fix: Add Circuit Breaker #11 (~35 lines)
   - Impact: Automatic blocking after second Read or source file read

3. **Gap 3: Edit/Write Not Listed as Forbidden**
   - Fix: Update Forbidden Tools table (~10 lines)
   - Impact: Explicit prohibition of code modification by PM

4. **Gap 4: Bash Implementation Not Forbidden**
   - Fix: Expand Bash Tool section (~40 lines)
   - Fix: Add Circuit Breaker #12 (~30 lines)
   - Impact: Blocks sed/awk/echo file modification attempts

### HIGH Priority Gap (Documentation)

5. **Gap 5: No Circuit Breaker Index**
   - Fix: Add Circuit Breaker summary table (~70 lines)
   - Impact: Clear reference for all enforcement mechanisms

### Total Changes Required

**Estimated Lines Added:** ~285 lines across 6 sections
**Files Modified:** 1 (PM_INSTRUCTIONS.md)
**Effort:** 2-3 hours (writing + testing)

---

## Answers to User Questions

### Question 1: Are there clear rules about using mcp-vector-search before delegation?

**Answer:** ❌ NO - Rules are WEAK

**Current State:**
- Lines 438-462 describe vector search as "Optional Quick Context"
- Says "BEFORE delegation" but doesn't mandate it
- No enforcement mechanism

**Missing:**
- No explicit rule: "PM MUST attempt vector search first"
- No circuit breaker detecting Read/Grep without vector search
- No workflow enforcement

**Recommendation:** Add "Vector Search First Protocol" section with Circuit Breaker #10

---

### Question 2: Are Read/Grep tools explicitly forbidden for PM?

**Answer:** ⚠️ PARTIALLY - Rules exist but enforcement is missing

**Current State:**
- Lines 316-334: Read tool limited to "ONE config file"
- Line 326: Grep not mentioned in Read Tool section
- Grep only mentioned in Bash section (line 269) as "investigation command → delegate to research"

**Problems:**
- Read limit exists but no circuit breaker enforcement
- Grep not explicitly in PM's forbidden tools list
- No automatic blocking on violation

**Missing:**
- Circuit breaker detecting multiple Read calls
- Circuit breaker detecting Grep usage (investigation context)
- Enforcement examples

**Recommendation:** Add Circuit Breaker #11 (Read Tool Limit) and clarify Grep delegation requirement

---

### Question 3: Is there a rule limiting PM to ONE config file read for context?

**Answer:** ✅ YES - Rule exists (Line 316-334)

**Current Rule (Line 320):**
```markdown
**SINGLE EXCEPTION**: ONE config/settings file for delegation context only.
```

**Rule Details:**
- ✅ Allowed: ONE file (package.json, pyproject.toml, settings.json, .env.example)
- ❌ Forbidden: Source code files
- ❌ Forbidden: Multiple files
- ❌ Forbidden: Investigation keywords

**BUT:** No circuit breaker enforcement to automatically block violations.

**Recommendation:** Circuit Breaker #11 would enforce this existing rule.

---

### Question 4: Are Edit/Write tools explicitly listed as forbidden?

**Answer:** ❌ NO - Not in Forbidden Tools table

**Current State:**
- Lines 464-473: Forbidden Tools table lists Ticketing and Browser tools
- Edit/Write NOT in the table
- Implementation delegation mentioned elsewhere (line 79) but not in forbidden tools

**Implication:**
- PM instructions mention delegation principles
- But Edit/Write not explicitly forbidden in enforcement section
- PM could argue "not explicitly prohibited"

**Recommendation:** Add "Code Modification" row to Forbidden Tools table

---

### Question 5: What enforcement mechanisms exist (circuit breakers)?

**Answer:** ⚠️ INCOMPLETE - Circuit breakers exist but gaps remain

**Current Circuit Breakers (Lines 898-927):**
- Circuit Breaker #6: Forbidden Tool Usage (ticketing, browser)
- Circuit Breaker #7: Verification Command Detection (curl, lsof, ps)
- Circuit Breaker #8: QA Verification Gate (completion without QA)
- Circuit Breaker #9: User Delegation Detection ("You'll need to run...")

**Referenced But Not Documented:**
- Circuit Breaker #1-5: Mentioned in validation rules but not detailed

**Missing Circuit Breakers (Identified in This Analysis):**
- Circuit Breaker #10: Vector Search First (use mcp-vector-search before Read/Grep)
- Circuit Breaker #11: Read Tool Limit (block after second Read or source file)
- Circuit Breaker #12: Bash Implementation (block sed/awk/echo file modification)

**Enforcement Model:**
- 3-strike system (Warning → Escalation → Failure)
- Hook-based interception (PMHookInterceptor in pm_hook_interceptor.py)
- Instruction reinforcement (configured via instruction_reinforcement_config)

**BUT:** No active code enforcement found in pm_hook_interceptor.py for:
- Edit/Write detection
- Multiple Read detection
- Bash sed/awk/echo detection
- Vector search requirement

**Recommendation:**
1. Document Circuit Breakers #1-5 explicitly
2. Implement Circuit Breakers #10-12 in code
3. Add Circuit Breaker index/summary table

---

## Code Enforcement Status

### PMHookInterceptor Analysis

**File:** `src/claude_mpm/core/pm_hook_interceptor.py`

**Current Capabilities:**
- Intercepts TodoWrite operations from PM
- Triggers pre/post hook events
- Applies instruction reinforcement
- Maintains session consistency

**What It Does NOT Do:**
- Does not detect Edit/Write tool usage by PM
- Does not enforce Read tool limits
- Does not check for vector search usage
- Does not block Bash implementation commands

**Implication:** Circuit breakers are documented in instructions but not enforced in code.

### Instruction Reinforcement Hook

**File:** Referenced in pm_hook_interceptor.py (line 22)

**Capabilities:**
- Modifies todo parameters based on configuration
- Injects reinforcement messages
- Tracks metrics

**Configuration:** `tools/dev/configure_instruction_reinforcement.py`

**Limitations:**
- Focuses on todo modifications, not tool usage interception
- No circuit breaker logic for forbidden tool detection
- No Read/Edit/Grep/Bash command blocking

### Recommendation: Implement Code-Level Enforcement

**Option 1: Extend PMHookInterceptor**

Add methods to intercept and block:
- Edit tool calls → raise delegation error
- Write tool calls → raise delegation error
- Read tool calls (after first use) → raise delegation error
- Bash calls with sed/awk/echo > → raise delegation error

**Option 2: Create Dedicated Circuit Breaker System**

New module: `src/claude_mpm/core/pm_circuit_breakers.py`

Features:
- Tool usage tracking (Read count, Edit attempts, Bash commands)
- Violation detection (pattern matching on tool parameters)
- Automatic blocking (raise errors before tool execution)
- 3-strike enforcement (warning → escalation → failure)

**Priority:** MEDIUM (instructions first, code enforcement second)

---

## Implementation Priority

### Phase 1: Documentation Updates (IMMEDIATE)

**Files:** PM_INSTRUCTIONS.md

**Changes:**
1. Add "Vector Search First Protocol" section (Gap 1) - ~60 lines
2. Add Circuit Breaker #10 (Vector Search) - ~30 lines
3. Add Circuit Breaker #11 (Read Limit) - ~35 lines
4. Update Forbidden Tools table (Gap 3) - ~10 lines
5. Expand Bash Tool section (Gap 4) - ~40 lines
6. Add Circuit Breaker #12 (Bash Implementation) - ~30 lines
7. Add Circuit Breaker index/summary (Gap 5) - ~70 lines

**Total:** ~285 lines added/modified
**Effort:** 2-3 hours
**Impact:** PM has explicit enforcement rules in instructions

### Phase 2: Code-Level Enforcement (FOLLOW-UP)

**Files:**
- `src/claude_mpm/core/pm_hook_interceptor.py` (extend)
- `src/claude_mpm/core/pm_circuit_breakers.py` (new)

**Features:**
- Tool usage interception (Edit, Write, Read, Bash)
- Violation detection and automatic blocking
- 3-strike enforcement tracking
- Integration with instruction reinforcement

**Effort:** 8-12 hours (design + implementation + testing)
**Impact:** PM violations automatically blocked at runtime

### Phase 3: Testing & Validation (FINAL)

**Test Cases:**
1. PM attempts Edit → Blocked with delegation message
2. PM attempts second Read → Blocked with Research delegation message
3. PM uses Bash sed → Blocked with Engineer delegation message
4. PM skips vector search → Warning, then required
5. PM claims complete without QA → Blocked

**Effort:** 4-6 hours (test writing + validation)

---

## Files to Review/Modify

### Immediate Changes

1. **PM_INSTRUCTIONS.md** - Add enforcement sections (~285 lines)

### Follow-Up Code Changes

2. **pm_hook_interceptor.py** - Add tool interception logic
3. **pm_circuit_breakers.py** - New circuit breaker system (create)
4. **configuration.yaml** - Add circuit breaker config section

### Testing

5. **test_pm_circuit_breakers.py** - New test suite (create)
6. **test_pm_delegation_enforcement.py** - Integration tests (create)

---

## Verification Checklist

After implementing fixes:

**Documentation:**
- [ ] Vector Search First Protocol section added (after line 316)
- [ ] Circuit Breaker #10 documented (Vector Search requirement)
- [ ] Circuit Breaker #11 documented (Read Tool Limit)
- [ ] Circuit Breaker #12 documented (Bash Implementation)
- [ ] Forbidden Tools table updated (Edit/Write added)
- [ ] Bash Tool section expanded (sed/awk/echo forbidden)
- [ ] Circuit Breaker index/summary added (complete list #1-12)

**Code Enforcement (Phase 2):**
- [ ] PMHookInterceptor extended with tool usage detection
- [ ] Edit/Write calls automatically blocked
- [ ] Read call counter implemented (limit: 1)
- [ ] Bash command pattern detection (sed/awk/echo >)
- [ ] Vector search availability check added
- [ ] 3-strike enforcement tracking

**Testing:**
- [ ] PM Edit attempt blocked in tests
- [ ] PM second Read blocked in tests
- [ ] PM Bash sed blocked in tests
- [ ] PM vector search skip detected in tests
- [ ] Warning/Escalation/Failure levels validated

---

## Conclusion

Analysis identified **5 CRITICAL GAPS** in PM delegation enforcement:

1. **mcp-vector-search not required** - PM can skip semantic search and use Read/Grep directly
2. **Read limit not enforced** - PM can read multiple files without automatic blocking
3. **Edit/Write not forbidden** - Not explicitly listed in Forbidden Tools table
4. **Bash implementation allowed** - sed/awk/echo not forbidden in Bash section
5. **No circuit breaker index** - Enforcement mechanisms scattered and incomplete

**Root Cause:** Instructions describe desired PM behavior but lack explicit enforcement rules and automatic blocking mechanisms.

**Immediate Fix:** Update PM_INSTRUCTIONS.md with ~285 lines of enforcement rules and circuit breaker documentation (Phase 1).

**Follow-Up:** Implement code-level enforcement in pm_hook_interceptor.py and new pm_circuit_breakers.py module (Phase 2).

**Impact:** With these fixes, PM violations will be explicitly documented as forbidden AND automatically detected/blocked at runtime.

---

**Report Generated:** 2025-12-29
**Generated By:** research-agent
**Investigation Request:** PM delegation violation gap analysis
**Status:** Complete - Recommendations ready for implementation
**Next Steps:** Implement Phase 1 (documentation updates) immediately
