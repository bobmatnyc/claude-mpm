# The Gate Function

The gate function is the mandatory checkpoint before ANY completion claim.

## The Complete Gate Function

```
BEFORE claiming any status or expressing satisfaction:

1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL command (fresh, complete)
3. READ: Full output, check exit code, count failures
4. VERIFY: Does output confirm the claim?
   - If NO: State actual status with evidence
   - If YES: State claim WITH evidence
5. ONLY THEN: Make the claim

Skip any step = lying, not verifying
```

## Step-by-Step Breakdown

### Step 1: IDENTIFY

**What to identify:**
- The exact command that proves your claim
- Not a related command
- Not a partial command
- The FULL verification command

**Examples:**

| Claim | Verification Command |
|-------|---------------------|
| "Tests pass" | `pytest tests/` (full suite) |
| "Build succeeds" | `make build` (complete build) |
| "Linter clean" | `ruff check .` (all files) |
| "Bug fixed" | Reproduce original bug (full reproduction) |
| "Requirements met" | Line-by-line checklist (all requirements) |

**Common Mistakes:**
- ❌ Identifying related but insufficient command
- ❌ Identifying partial verification
- ❌ Identifying old verification results
- ❌ Can't identify verification → Claim invalid

### Step 2: RUN

**How to run:**
- Execute the COMPLETE command
- Fresh execution (not cached results)
- Full scope (not subset)
- Right here, right now (not "I ran it earlier")

**Requirements:**
- Use exact command identified in Step 1
- Run in correct environment
- Include all parameters/flags
- Wait for complete execution

**Common Mistakes:**
- ❌ Running partial command
- ❌ Using cached/previous results
- ❌ Running related but different command
- ❌ Assuming results without running

**Examples:**

✅ **Correct:**
```bash
# Full test suite, right now
pytest tests/
```

❌ **Incorrect:**
```bash
# Only one test file
pytest tests/test_auth.py

# Previous run (stale)
"I ran tests 10 minutes ago"

# Related but not sufficient
ruff check .  # This is linter, not tests
```

### Step 3: READ

**What to read:**
- COMPLETE output, not just summary
- Exit code (0 = success, non-zero = failure)
- Count of passes/failures
- Error messages if any
- Warnings if any

**How to read:**
- Scroll through entire output
- Don't skip "boring" parts
- Check final status line
- Verify exit code
- Count specific numbers

**Common Mistakes:**
- ❌ Reading only summary
- ❌ Skipping error details
- ❌ Ignoring warnings
- ❌ Not checking exit code
- ❌ Assuming from first few lines

**Examples:**

✅ **Correct Reading:**
```
pytest tests/
...
[complete output]
...
====== 34 passed in 2.45s ======
Exit code: 0

Conclusion: 34 tests, ALL passed, 0 failed
```

❌ **Incorrect Reading:**
```
pytest tests/
[output appears...]
"Looks like tests are passing"  ← Didn't read to end
```

### Step 4: VERIFY

**Verification questions:**
1. Does output match claim exactly?
2. Are there any failures/errors?
3. Is exit code 0 (success)?
4. Are counts what expected?
5. Are there warnings to address?

**Decision tree:**
```
Output confirms claim?
├─ YES → Proceed to Step 5 (claim with evidence)
└─ NO  → Report actual status with evidence
    - Don't claim success
    - Report what actually happened
    - Include evidence of actual state
```

**Examples:**

✅ **Output Confirms Claim:**
```
Claim: "All tests pass"
Output: "34 passed, 0 failed"
Exit Code: 0
Verification: YES → Safe to claim
```

❌ **Output Contradicts Claim:**
```
Claim: "All tests pass"
Output: "31 passed, 3 failed"
Exit Code: 1
Verification: NO → Cannot claim
Correct response: "31/34 tests pass, 3 failing: test_auth, test_db, test_api"
```

### Step 5: CLAIM

**Only reach this step if:**
- ✅ Identified correct verification
- ✅ Ran complete command
- ✅ Read full output
- ✅ Output confirms claim

**How to claim:**
```
[Evidence] + [Claim]

Example: "All 34 tests pass (pytest output: 34/34 passed, exit 0)"
```

**Structure:**
1. State the evidence first
2. Then make the claim
3. Include specific numbers
4. Reference verification command

**Examples:**

✅ **Correct Claims:**
```
"pytest output: 34/34 passed → All tests pass"
"make build: exit 0, dist/ created → Build succeeds"
"ruff check: 0 errors, 0 warnings → Linter clean"
"curl https://api.example.com: 200 OK → Endpoint accessible"
```

❌ **Incorrect Claims:**
```
"Should pass now" ← No evidence
"Tests pass" ← No evidence shown
"Looks good" ← Subjective, no evidence
"Fixed!" ← No verification
```

## Common Gate Function Violations

### Violation 1: Skipping IDENTIFY
**Symptom:** Can't name verification command
**Fix:** If you can't identify verification, claim is invalid

### Violation 2: Skipping RUN
**Symptom:** Using old results, assuming outcomes
**Fix:** Fresh execution required, every time

### Violation 3: Skipping READ
**Symptom:** Making claims without reading output
**Fix:** Read COMPLETE output before claiming

### Violation 4: Skipping VERIFY
**Symptom:** Claiming success despite failures in output
**Fix:** Match output to claim, report reality

### Violation 5: Claiming Despite Failure
**Symptom:** Tests fail but claim "mostly works"
**Fix:** Report actual state: "31/34 pass, 3 failing"

## Gate Function for Different Contexts

### Before Committing

```
GATE CHECK:
1. IDENTIFY: git diff, test suite, linter
2. RUN: git diff && pytest && ruff check .
3. READ: Full output of all three
4. VERIFY: No uncommitted junk, all tests pass, linter clean
5. CLAIM: "Ready to commit" OR report issues found
```

### Before Creating PR

```
GATE CHECK:
1. IDENTIFY: Full test suite, requirements checklist, diff review
2. RUN: pytest && git diff main...HEAD
3. READ: Test results + all changes made
4. VERIFY: Tests pass, changes match requirements
5. CLAIM: "Ready for PR" OR report gaps
```

### Before Marking Task Complete

```
GATE CHECK:
1. IDENTIFY: Requirements list, verification commands
2. RUN: Check each requirement individually
3. READ: Results of each verification
4. VERIFY: All requirements met
5. CLAIM: "Task complete: 5/5 requirements met" OR "4/5 met, missing X"
```

### Before Delegating to Agent

```
GATE CHECK:
1. IDENTIFY: What agent should accomplish
2. RUN: Agent execution
3. READ: Agent report AND git diff
4. VERIFY: Changes match task, no surprises
5. CLAIM: "Agent completed X, verified by diff" OR "Agent attempted but Y issue found"
```

### Before Deployment

```
GATE CHECK:
1. IDENTIFY: Build, tests, smoke tests, health checks
2. RUN: Full build + test suite
3. READ: All outputs
4. VERIFY: All pass, ready to deploy
5. CLAIM: "Ready for deployment" OR report blockers
```

## The Iron Law Explained

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

**"No completion claims"** = ANY variation:
- "Done", "Complete", "Finished", "Success"
- "Fixed", "Working", "Passing", "Clean"
- "Ready", "Good to go", "All set"
- ANY paraphrase or synonym

**"Without fresh verification"** = Must have:
- Run command in this session
- Read complete output
- Verified results match claim
- Evidence is current (not stale)

**"Evidence"** = Must include:
- Specific command run
- Specific output received
- Specific numbers/counts
- Exit codes where applicable

## Why Every Step Matters

**Skip IDENTIFY:** Don't know what to verify → Can't verify → Can't claim
**Skip RUN:** No current evidence → Claiming based on hope → Lying
**Skip READ:** Don't know actual results → Assuming → Lying
**Skip VERIFY:** Results might contradict claim → Claiming anyway → Lying
**Skip any step:** Broke verification process → Cannot be trusted

## The Bottom Line

The gate function is non-negotiable. Every completion claim must pass through it.

No shortcuts. No exceptions. No assumptions.

Run the command. Read the output. Verify the result. Then claim.
