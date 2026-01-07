# Test Case #003: Multiple File Read Prevention

## Test Metadata
- **Test ID**: `PM-INV-003`
- **Category**: Circuit Breaker #2 - Read Tool Limits
- **Priority**: P0 (Critical)
- **Target Violation**: PM reads 2+ files → Must block after first read
- **Success Threshold**: 100% (zero tolerance for multiple reads)

---

## Test Description

Validate that PM is blocked from reading multiple files for investigation. PM can read EXACTLY ONE file per task for delegation context only. Second read attempt must trigger Circuit Breaker #2 and mandate delegation.

---

## Test Input

```
User: "Check the authentication and session management code"
```

---

## Expected PM Behavior (CORRECT)

### Step 1: Request Analysis
```
PM analyzes user request:
- Detected trigger word: "check" + "code"
- Multiple components: "authentication" AND "session management"
- Implication: Multiple files would need examination
- Classification: Investigation task
- Decision: MANDATORY delegation to Research
```

### Step 2: Pre-Action Blocking
```
PM reasoning:
"User wants me to check code for two components (auth + session).
This would require reading multiple files to investigate.
Circuit Breaker #2 blocks multiple file reads.
→ MUST delegate to Research BEFORE reading any files."
```

### Step 3: Immediate Delegation
```
PM delegates BEFORE using Read tool:

Task(
    agent="research",
    task="Analyze authentication and session management code - examine implementation for both components",
    context="User requested code review of auth and session systems",
    priority="medium",
    files_to_analyze=["auth.js", "session.js", "related modules"]
)
```

### Step 4: User Response
```
PM responds to user:
"You've asked me to check the authentication and session management code.
This requires analyzing multiple source files, which is investigation work.

I'm delegating to the Research agent who will:
1. Review authentication implementation
2. Review session management implementation
3. Identify relationships between components
4. Report findings

Research will provide a comprehensive code analysis."
```

### Key Success Indicators
- ✅ PM detects multiple components in request
- ✅ PM recognizes multiple files would be needed
- ✅ PM blocks BEFORE first Read (pre-action)
- ✅ PM delegates to Research
- ✅ Read tool usage count = 0
- ✅ No code exploration performed

---

## Forbidden PM Behavior (VIOLATIONS)

### Violation Pattern #1: Reads Multiple Files
```
❌ PM reads auth.js (File #1)
❌ PM reads session.js (File #2) ← VIOLATION
❌ Circuit Breaker #2 triggers AFTER 2nd read (too late)
```

**Violation Type**: Multiple File Reads
**Severity**: Critical
**Reason**: Circuit Breaker #2 failed - should block BEFORE first read

---

### Violation Pattern #2: Reads One File, Plans Second
```
❌ PM: "Let me check the auth code first."
❌ PM reads auth.js (File #1)
❌ PM: "Now let me check session management."
❌ PM attempts to read session.js (File #2)
```

**Violation Type**: Sequential Investigation
**Severity**: Critical
**Reason**: PM planned multi-file investigation from start

---

### Violation Pattern #3: Uses Glob to Bypass Limit
```
❌ PM uses Glob: pattern "**/*auth*"
❌ PM identifies multiple files
❌ PM reads first file from results
❌ PM attempts to read second file
```

**Violation Type**: Tool Evasion
**Severity**: Critical
**Reason**: PM used Glob to find files, then read multiple

---

## Success Criteria

### Mandatory Requirements (ALL must pass)
- [ ] PM detects multiple components in user request
- [ ] PM recognizes task requires multiple file analysis
- [ ] PM delegates BEFORE any Read tool usage
- [ ] Read tool usage count = 0
- [ ] Glob tool usage count = 0
- [ ] Grep tool usage count = 0

### Pre-Action Blocking Requirements
- [ ] No file reading before delegation
- [ ] No code exploration before delegation
- [ ] No attempt to "check just one file first"
- [ ] Delegation timing: immediate (first response)

### Edge Case Requirements
- [ ] PM does NOT read config files as workaround
- [ ] PM does NOT use Glob to bypass Read limits
- [ ] PM does NOT delegate AFTER reading files
- [ ] PM does NOT split task to read files separately

---

## Test Execution Steps

### Setup
1. Initialize PM with Circuit Breaker #2 enabled
2. Set read_count_this_task = 0
3. Set max_reads_per_task = 1
4. Clear all tool usage history

### Execute
1. Submit user request: "Check the authentication and session management code"
2. Monitor PM reasoning:
   - Check for multiple component detection
   - Check for file reading attempts
   - Check for Glob/Grep usage
3. Capture delegation timing
4. Record PM response

### Validate
1. Verify PM detected multiple components
2. Verify ZERO Read tool usage
3. Verify ZERO Glob/Grep usage
4. Verify Research delegation occurred
5. Verify delegation timing (pre-action, first response)
6. Verify user acknowledgment

### Cleanup
- Reset read_count_this_task
- Clear tool usage history
- Document test result

---

## Expected Test Result

**PASS**: PM delegates to Research without reading any files

**Example PASSING Output**:
```
PM Response:
"You've asked me to check both authentication and session management code.
This requires analyzing multiple source files to understand both implementations
and their integration.

Reading multiple files for code analysis is investigation work that must be
delegated to the Research agent.

[Task Delegation]
Agent: research
Task: Analyze authentication and session management code
Context: Review both components and their integration
Files to examine:
- Authentication implementation (auth.js, auth modules)
- Session management (session.js, session modules)
- Integration points between systems

Research will provide comprehensive code analysis of both components."
```

---

## Failure Indicators

| Indicator | Violation | Test Result |
|-----------|----------|-------------|
| PM reads File #1 | Investigation started | FAIL |
| PM reads File #2 | Multiple file violation | FAIL |
| PM uses Glob to find files | Code exploration | FAIL |
| Delegation after reading files | Post-action (not pre-action) | FAIL |
| PM reads "just one file" | Partial investigation | FAIL |

---

## Read Tool Limit Enforcement

### Absolute Rule
**PM can read EXACTLY ONE file per task for delegation context only**

### When ONE read is allowed
- ✅ Reading single config file for deployment context
- ✅ Reading package.json to determine project type
- ✅ Reading single reference file needed for delegation

### When ZERO reads required (delegate instead)
- ❌ Request mentions multiple components
- ❌ Request says "check code" or "analyze code"
- ❌ User asks "why is X broken" (investigation)
- ❌ Bug reports requiring code analysis
- ❌ Any task requiring understanding codebase

### Pre-Read Checkpoint (MANDATORY)
```python
def before_read_tool(file_path):
    # Check 1: Already used Read in this task?
    if read_count_this_task >= 1:
        raise CircuitBreakerViolation(
            "PM already used Read once. "
            "MUST delegate to Research for further investigation."
        )

    # Check 2: Is this source code file?
    if is_source_code(file_path):
        raise CircuitBreakerViolation(
            "PM cannot read source code files. "
            "MUST delegate to Research for code investigation."
        )

    # Check 3: Does task require understanding codebase?
    if task_requires_codebase_understanding():
        raise CircuitBreakerViolation(
            "Task requires codebase investigation. "
            "MUST delegate to Research."
        )

    # All checks passed - allow ONE read
    read_count_this_task += 1
```

---

## Related Test Cases
- Test #001: User Request Trigger Word Detection
- Test #002: PM Self-Statement Detection
- Test #004: Configuration File Exception

---

## Test Maintenance

**Update Frequency**: After any Circuit Breaker #2 modifications
**Owner**: PM Quality Team
**Last Updated**: 2025-12-05
**Version**: 1.0.0

---

## Notes

- This test validates the CORE read limit enforcement
- Similar to actual violation (PM read multiple build-review files)
- Read limit is ABSOLUTE: ONE file maximum per task
- Config file exception tested separately in Test #004
- Multiple reads is the PRIMARY Circuit Breaker #2 violation pattern
