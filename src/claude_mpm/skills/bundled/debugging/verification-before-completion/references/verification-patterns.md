# Verification Patterns

Complete patterns for verifying different types of claims before making them.

## Test Verification

**Correct Pattern:**
```
1. Run full test suite: pytest tests/
2. Read complete output
3. Count: 34 tests, 34 passed, 0 failed
4. Claim: "All 34 tests pass"
```

**Incorrect Patterns:**
- ❌ "Should pass now" (no evidence)
- ❌ "Looks correct" (subjective)
- ❌ "Tests were passing earlier" (stale)
- ❌ "I fixed the issue" (assumes, doesn't verify)

**Evidence Required:**
- Full test command executed
- Complete output visible
- Exact pass/fail counts
- Exit code confirmed (0 = success)

## Regression Test Verification (TDD Red-Green Cycle)

**Correct Pattern:**
```
1. Write regression test
2. Run test → MUST FAIL (RED)
3. Implement fix
4. Run test → MUST PASS (GREEN)
5. Revert fix temporarily
6. Run test → MUST FAIL AGAIN (confirms test works)
7. Restore fix
8. Run test → MUST PASS (final confirmation)
```

**Why Red-Green-Red-Green?**
- First RED: Confirms test catches the bug
- GREEN: Confirms fix works
- Second RED: Confirms test isn't passing by accident
- Final GREEN: Confirms fix is stable

**Incorrect Patterns:**
- ❌ "I've written a regression test" (didn't verify it fails)
- ❌ Test passes on first run (never confirmed it catches bug)
- ❌ Single pass without reverting (could be false positive)

## Build Verification

**Correct Pattern:**
```
1. Run full build: make build
2. Read complete output
3. Check exit code: echo $? → 0
4. Verify artifacts created: ls dist/
5. Claim: "Build succeeds, artifacts in dist/"
```

**Incorrect Patterns:**
- ❌ "Linter passed, so build should work" (linter ≠ compiler)
- ❌ "No errors in logs" (didn't actually build)
- ❌ "Build was working earlier" (stale verification)

**Common Gotchas:**
- Linter passing ≠ compilation passing
- TypeScript errors ≠ build errors
- Local build ≠ CI build
- Dev build ≠ production build

## Linter Verification

**Correct Pattern:**
```
1. Run linter: ruff check .
2. Read full output
3. Count violations: 0 errors, 0 warnings
4. Check exit code: 0
5. Claim: "Linter clean (0 violations)"
```

**Incorrect Patterns:**
- ❌ "Fixed the obvious issues" (partial check)
- ❌ "Linter passed on one file" (not comprehensive)
- ❌ "Should be clean now" (no verification)

## Bug Fix Verification

**Correct Pattern:**
```
1. Document original symptom
2. Create reproduction steps
3. Run reproduction → FAILS (confirms bug)
4. Implement fix
5. Run reproduction → PASSES
6. Run full test suite → PASSES (no regressions)
7. Claim: "Bug fixed, verified with reproduction and tests"
```

**Incorrect Patterns:**
- ❌ "Code changed, bug should be fixed" (assumes)
- ❌ "Logic looks correct" (theory, not evidence)
- ❌ "Can't reproduce anymore" (didn't verify with test)

## Requirements Verification

**Correct Pattern:**
```
1. Re-read original requirements
2. Create line-by-line checklist
3. Verify each requirement individually
4. Document evidence for each
5. Report: "5/5 requirements met" OR "4/5 met, missing X"
```

**Incorrect Patterns:**
- ❌ "Tests pass, so requirements met" (tests ≠ requirements)
- ❌ "I implemented what was asked" (subjective)
- ❌ "Phase complete" (vague, no checklist)

## Agent Delegation Verification

**Correct Pattern:**
```
1. Agent reports: "Task complete"
2. Check version control diff: git diff
3. Read all changes made
4. Verify changes match task requirements
5. Run verification commands (tests, build, etc.)
6. Report actual state: "Agent made changes to X, Y verified"
```

**Incorrect Patterns:**
- ❌ Trusting agent success report
- ❌ "Agent said success, moving on"
- ❌ Not checking actual changes made

## Deployment Verification

**Correct Pattern:**
```
1. Deploy to environment
2. Check deployment logs: SUCCESS
3. Verify endpoint accessible: curl https://...
4. Check application logs: No errors
5. Run smoke tests on deployed version
6. Claim: "Deployed successfully, endpoint responding"
```

**Incorrect Patterns:**
- ❌ "Deployment command succeeded" (didn't check endpoint)
- ❌ "Should be live now" (no verification)
- ❌ "Deployed to staging" (didn't verify it works)

## Performance Verification

**Correct Pattern:**
```
1. Run performance benchmark
2. Record baseline: 150ms average
3. Implement optimization
4. Run benchmark again
5. Record new measurement: 45ms average
6. Calculate improvement: 70% faster
7. Run multiple times to confirm consistency
8. Claim: "Performance improved 70% (150ms → 45ms, 10 runs)"
```

**Incorrect Patterns:**
- ❌ "Should be faster now" (no measurement)
- ❌ "Looks quicker" (subjective)
- ❌ Single measurement (could be outlier)

## Security Verification

**Correct Pattern:**
```
1. Run security scanner: bandit -r .
2. Read full report
3. Review each finding
4. Document: "3 high, 2 medium, 5 low"
5. Address critical issues
6. Re-run scanner
7. Claim: "Security scan: 0 high, 0 medium, 5 low (accepted)"
```

**Incorrect Patterns:**
- ❌ "Looks secure" (no scan)
- ❌ "No obvious vulnerabilities" (didn't scan)
- ❌ "Should be safe" (assumption)

## Documentation Verification

**Correct Pattern:**
```
1. Write documentation
2. Have someone else read it
3. Ask them to follow steps
4. Observe if they succeed without questions
5. Fix confusing parts
6. Repeat until successful
7. Claim: "Documentation verified with fresh user"
```

**Incorrect Patterns:**
- ❌ "Documentation complete" (not tested)
- ❌ "Clear to me" (author bias)
- ❌ "Should be understandable" (no verification)

## The Universal Pattern

All verification follows this structure:

```
1. IDENTIFY: What proves this claim?
2. RUN: Execute the full verification command
3. READ: Complete output, not just summary
4. ANALYZE: Does evidence support claim?
5. DECIDE:
   - If YES: Claim with evidence
   - If NO: Report actual state with evidence
```

**Never skip steps. Never assume. Always verify.**
