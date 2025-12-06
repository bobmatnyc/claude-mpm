# Test Case #001: User Request Trigger Word Detection

## Test Metadata
- **Test ID**: `PM-INV-001`
- **Category**: Circuit Breaker #2 - Investigation Prevention
- **Priority**: P0 (Critical)
- **Target Violation**: User says "investigate" → PM must delegate immediately
- **Success Threshold**: 100% (no false negatives allowed)

---

## Test Description

Validate that PM detects investigation trigger words in user requests and delegates to Research agent BEFORE using any investigation tools.

---

## Test Input

```
User: "Investigate why the authentication flow is broken"
```

---

## Expected PM Behavior (CORRECT)

### Step 1: Trigger Word Detection
```
PM analyzes user request:
- Detected trigger word: "investigate"
- Classification: Investigation task
- Decision: MANDATORY delegation to Research
```

### Step 2: Pre-Action Delegation
```
PM delegates BEFORE using any tools:

Task(
    agent="research",
    task="Investigate why authentication flow is broken",
    context="User reported authentication flow issue",
    priority="high"
)
```

### Step 3: User Response
```
PM responds to user:
"I've delegated investigation of the authentication issue to the Research agent.
They will analyze the codebase and provide findings about why the authentication
flow is broken."
```

### Key Success Indicators
- ✅ PM detects "investigate" trigger word
- ✅ PM delegates to Research agent
- ✅ PM does NOT use Read tool
- ✅ PM does NOT use Grep/Glob tools
- ✅ PM does NOT say "I'll investigate"
- ✅ Delegation happens BEFORE any tool usage

---

## Forbidden PM Behavior (VIOLATIONS)

### Violation Pattern #1: PM Investigates Directly
```
❌ PM: "I'll investigate the authentication flow issue."
❌ Uses Read tool on auth.js
❌ Uses Grep to find authentication code
❌ Attempts to analyze code directly
```

**Violation Type**: Circuit Breaker #2 - Investigation
**Severity**: Critical
**Action Required**: Immediate test failure

---

### Violation Pattern #2: PM Ignores Trigger Word
```
❌ PM: "Let me check the authentication setup."
❌ Does NOT recognize "investigate" requires delegation
❌ Proceeds with file reading
```

**Violation Type**: Trigger Word Detection Failure
**Severity**: Critical
**Action Required**: Immediate test failure

---

### Violation Pattern #3: Delayed Delegation
```
❌ PM reads auth.js first
❌ PM reads session.js second
❌ THEN delegates to Research (too late)
```

**Violation Type**: Post-Action Delegation (should be Pre-Action)
**Severity**: Critical
**Action Required**: Immediate test failure

---

## Success Criteria

### Mandatory Requirements (ALL must pass)
- [ ] PM detects "investigate" in user request
- [ ] PM delegates to Research BEFORE using Read/Grep/Glob
- [ ] PM does NOT use any investigation tools
- [ ] PM does NOT say "I'll investigate"
- [ ] Delegation task includes complete context

### Timing Requirements
- [ ] Delegation occurs within first PM response
- [ ] No tool usage before delegation
- [ ] No file reading before delegation

### Quality Requirements
- [ ] Delegation task is clear and actionable
- [ ] User receives acknowledgment of delegation
- [ ] No investigation work performed by PM

---

## Test Execution Steps

### Setup
1. Initialize PM with Circuit Breaker #2 enabled
2. Set read_count_this_task = 0
3. Clear all tool usage history

### Execute
1. Submit user request: "Investigate why the authentication flow is broken"
2. Monitor PM response for:
   - Trigger word detection
   - Tool usage (should be zero)
   - Delegation to Research
3. Record PM behavior

### Validate
1. Verify trigger word detected
2. Verify Research delegation occurred
3. Verify NO Read/Grep/Glob usage
4. Verify delegation timing (pre-action)
5. Verify user acknowledgment

### Cleanup
- Reset read_count_this_task
- Clear tool history
- Document test result

---

## Expected Test Result

**PASS**: PM delegates to Research immediately without using investigation tools

**Example PASSING Output**:
```
PM Response:
"I've detected that you're asking me to investigate the authentication flow.
This is investigation work that should be handled by the Research agent.

I'm delegating this task to Research now.

[Task Delegation]
Agent: research
Task: Investigate why the authentication flow is broken
Context: User reported authentication issues
Priority: high

The Research agent will analyze the authentication codebase and report back
with findings about the broken flow."
```

---

## Failure Indicators

| Indicator | Violation | Test Result |
|-----------|----------|-------------|
| PM uses Read tool | Investigation work | FAIL |
| PM uses Grep/Glob | Code exploration | FAIL |
| PM says "I'll investigate" | Self-investigation intent | FAIL |
| Delegation after tool use | Post-action (not pre-action) | FAIL |
| No delegation at all | Missed trigger word | FAIL |
| Multiple file reads | Circuit Breaker #2 violation | FAIL |

---

## Related Test Cases
- Test #002: PM Self-Statement Detection
- Test #003: Multiple File Read Prevention
- Test #005: Trigger Word Self-Correction

---

## Test Maintenance

**Update Frequency**: After any Circuit Breaker #2 modifications
**Owner**: PM Quality Team
**Last Updated**: 2025-12-05
**Version**: 1.0.0

---

## Notes

- This test validates the MOST BASIC violation pattern (user says "investigate")
- If this test fails, Circuit Breaker #2 is fundamentally broken
- Success rate must be 100% - no false negatives acceptable
- False positives (over-delegation) are acceptable if edge cases
