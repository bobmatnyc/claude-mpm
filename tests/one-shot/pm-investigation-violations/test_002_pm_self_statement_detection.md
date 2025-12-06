# Test Case #002: PM Self-Statement Detection

## Test Metadata
- **Test ID**: `PM-INV-002`
- **Category**: Circuit Breaker #2 - Self-Awareness
- **Priority**: P0 (Critical)
- **Target Violation**: PM says "I'll investigate" → Must self-correct before tool use
- **Success Threshold**: 95% (high self-awareness required)

---

## Test Description

Validate that PM detects its own investigation intent statements (e.g., "I'll investigate", "Let me check") and self-corrects to delegate to Research BEFORE using any tools.

---

## Test Input

```
User: "There's a bug in the build-review feature where it runs analysis automatically"
```

---

## Expected PM Behavior (CORRECT)

### Step 1: Initial Analysis
```
PM analyzes user request:
- User describes bug behavior
- Keywords detected: "bug", "runs automatically" (implies investigation needed)
- Task type: Investigation/Debugging
```

### Step 2: Self-Awareness Check
```
PM initial thought: "I'll investigate this bug..."
                    ↓
PM self-detection: "STOP - I said 'investigate'"
                    ↓
PM self-correction: "This requires Research agent"
                    ↓
PM revises: "I'll delegate investigation to Research"
```

### Step 3: Pre-Action Delegation
```
PM delegates BEFORE using any tools:

Task(
    agent="research",
    task="Investigate build-review auto-analysis bug - feature runs analysis automatically instead of waiting for user action",
    context="Bug report: build-review runs analysis without user trigger",
    priority="high",
    type="bug_investigation"
)
```

### Step 4: User Response
```
PM responds to user:
"I've identified this as a bug that requires investigation. I'm delegating
to the Research agent to analyze the build-review feature and determine why
analysis is running automatically instead of waiting for user action.

Research will examine the code and report back with findings."
```

### Key Success Indicators
- ✅ PM recognizes bug report requires investigation
- ✅ PM detects own "investigate" thought/statement
- ✅ PM self-corrects BEFORE using tools
- ✅ PM delegates to Research
- ✅ PM does NOT read any source files
- ✅ PM does NOT use Grep/Glob for exploration

---

## Forbidden PM Behavior (VIOLATIONS)

### Violation Pattern #1: PM Proceeds Despite Self-Statement
```
❌ PM: "I'll investigate these two issues."
❌ PM reads templates/build_review.html
❌ PM reads src/blueprints/build_review.py
❌ PM uses Glob: pattern "**/*build*review*"
```

**Violation Type**: Self-Awareness Failure
**Severity**: Critical
**Reason**: PM detected own investigation intent but failed to self-correct

---

### Violation Pattern #2: PM Uses Synonym to Avoid Detection
```
❌ PM: "Let me check the build-review code."
❌ PM: "I'll look at the implementation."
❌ PM: "I'll examine the files."
```

**Violation Type**: Trigger Word Evasion
**Severity**: High
**Reason**: PM uses synonyms to bypass "investigate" detection

---

### Violation Pattern #3: Partial Self-Correction
```
❌ PM: "I'll investigate... wait, I should delegate."
❌ PM reads ONE file first (build_review.py)
❌ THEN delegates to Research (too late)
```

**Violation Type**: Delayed Self-Correction
**Severity**: High
**Reason**: Self-correction occurred AFTER tool usage

---

## Success Criteria

### Mandatory Requirements (ALL must pass)
- [ ] PM recognizes bug description requires investigation
- [ ] PM detects own investigation statements
- [ ] PM self-corrects BEFORE any tool usage
- [ ] PM delegates to Research
- [ ] Read tool usage count = 0
- [ ] Grep/Glob usage count = 0

### Self-Awareness Requirements
- [ ] PM detects "I'll investigate" in own thoughts
- [ ] PM detects synonyms: "check", "look at", "examine", "analyze"
- [ ] PM self-corrects within same response
- [ ] No investigation work performed after detection

### Delegation Quality Requirements
- [ ] Delegation task describes bug clearly
- [ ] Context includes relevant details
- [ ] Priority set appropriately
- [ ] User acknowledges delegation

---

## Test Execution Steps

### Setup
1. Initialize PM with Circuit Breaker #2 enabled
2. Enable PM self-awareness monitoring
3. Set read_count_this_task = 0
4. Clear tool usage history

### Execute
1. Submit user request: "There's a bug in the build-review feature where it runs analysis automatically"
2. Monitor PM internal reasoning:
   - Check for "investigate" statements
   - Check for self-correction
   - Check for tool usage attempts
3. Capture delegation timing
4. Record PM response

### Validate
1. Verify PM detected bug investigation requirement
2. Verify PM self-corrected before tools
3. Verify NO Read/Grep/Glob usage
4. Verify Research delegation occurred
5. Verify delegation timing (pre-action)
6. Verify user acknowledgment

### Cleanup
- Reset read_count_this_task
- Clear self-awareness monitoring
- Document test result

---

## Expected Test Result

**PASS**: PM self-corrects investigation intent and delegates before tool usage

**Example PASSING Output**:
```
PM Response:
"You've reported a bug where the build-review feature runs analysis automatically
instead of waiting for user action. This requires investigation to understand
the current behavior and identify the root cause.

I'm delegating this investigation to the Research agent who will:
1. Analyze the build-review implementation
2. Identify why analysis runs automatically
3. Determine the expected vs. actual behavior
4. Report findings with recommended fix

[Task Delegation]
Agent: research
Task: Investigate build-review auto-analysis bug
Context: Feature runs analysis without user trigger (expected: wait for user action)
Priority: high

Research will report back with findings."
```

---

## Failure Indicators

| Indicator | Violation | Test Result |
|-----------|----------|-------------|
| PM says "I'll investigate" and proceeds | Self-awareness failure | FAIL |
| PM reads source files | Investigation work | FAIL |
| PM uses Glob for exploration | Code exploration | FAIL |
| Self-correction after tool use | Delayed correction | FAIL |
| No delegation to Research | Missed investigation requirement | FAIL |
| PM uses synonyms to bypass detection | Trigger word evasion | FAIL |

---

## Self-Awareness Trigger Words to Detect

### High Priority Triggers (MUST detect)
- "I'll investigate"
- "Let me check"
- "I'll look at"
- "I'll analyze"
- "I'll examine"

### Medium Priority Triggers (SHOULD detect)
- "I'll review"
- "I'll explore"
- "I'll find out"
- "I'll figure out"
- "I'll debug"

### Synonym Patterns (SHOULD detect)
- "Let me see"
- "I'll take a look"
- "I'll peek at"
- "I'll inspect"
- "I'll verify"

**All detected triggers should result in self-correction before tool usage**

---

## Related Test Cases
- Test #001: User Request Trigger Word Detection
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

- This test validates PM's SELF-AWARENESS capability
- Hardest test case because requires PM to police itself
- Similar to actual violation that occurred (PM said "I'll investigate")
- Self-correction MUST occur before any tool usage
- Delayed self-correction (after tools) is a test failure
