# Integration and Workflows

How verification-before-completion integrates with other skills and common workflows.

## Integration with Other Skills

### Systematic Debugging

**When debugging, verification prevents false confidence in fixes:**

```
1. Reproduce bug (systematic-debugging Phase 1)
2. Investigate root cause (systematic-debugging Phase 1)
3. Form hypothesis (systematic-debugging Phase 3)
4. Implement fix (systematic-debugging Phase 4)
5. ⚠️ GATE FUNCTION: Verify fix works (verification-before-completion)
   - Run reproduction case → Must pass
   - Run full test suite → Must pass
   - THEN claim "Bug fixed"
```

**Integration points:**
- After Phase 1 (Investigation): Verify you can reproduce consistently
- After Phase 4 (Implementation): Verify fix actually works
- Never claim fix without verification

**Common mistakes:**
- ❌ "Logic looks correct" → Verify it works
- ❌ "Should fix the bug" → Run reproduction test
- ❌ "Code changed" → Verify behavior changed

### Test-Driven Development (TDD)

**TDD red-green cycle requires verification at each step:**

```
1. Write test (TDD)
2. ⚠️ VERIFY: Test fails (RED) - proves it catches bug
3. Implement code (TDD)
4. ⚠️ VERIFY: Test passes (GREEN) - proves fix works
5. Revert code temporarily
6. ⚠️ VERIFY: Test fails again (RED) - proves test isn't false positive
7. Restore code
8. ⚠️ VERIFY: Test passes (GREEN) - final confirmation
```

**Integration points:**
- Every transition in red-green cycle needs verification
- Never assume test state, always verify
- Document verification evidence for each step

**Why critical:**
- Test passing immediately = test doesn't catch bug
- Skip verification = false confidence in test coverage

### Condition-Based Waiting

**When waiting for conditions, verify they're actually met:**

```
1. Identify condition to wait for (condition-based-waiting)
2. Implement wait logic
3. ⚠️ GATE FUNCTION: Verify condition actually met
   - Check condition state
   - Don't assume timeout = success
   - THEN proceed
```

**Integration points:**
- After wait completes: Verify condition met, not just timeout elapsed
- Replace "waited long enough" with "verified condition met"

**Common mistakes:**
- ❌ "Waited 5 seconds" → Verify condition met
- ❌ "Should be ready now" → Check actual state

### Root-Cause Tracing

**When tracing root causes, verify your understanding:**

```
1. Trace back through call stack (root-cause-tracing)
2. Identify suspected root cause
3. ⚠️ GATE FUNCTION: Verify root cause identified
   - Test hypothesis
   - Can you reproduce by triggering suspected cause?
   - THEN claim root cause found
```

**Integration points:**
- After identifying root cause: Verify it's truly the cause
- Test by removing suspected cause: Problem should disappear
- Never claim root cause without verification

## Workflow Examples

### Feature Development Workflow

```
1. Read requirements
2. Write tests (TDD)
3. ⚠️ VERIFY: Tests fail (red)
4. Implement feature
5. ⚠️ VERIFY: Tests pass (green)
6. ⚠️ VERIFY: All requirements met (checklist)
7. ⚠️ VERIFY: Full test suite passes
8. ⚠️ VERIFY: Linter clean
9. ⚠️ VERIFY: Build succeeds
10. THEN commit
```

**Verification points: 5 gates before commit**

### Bug Fix Workflow

```
1. Reproduce bug
2. ⚠️ VERIFY: Can reproduce consistently
3. Investigate root cause (systematic-debugging)
4. ⚠️ VERIFY: Root cause identified
5. Write regression test
6. ⚠️ VERIFY: Test fails (catches bug)
7. Implement fix
8. ⚠️ VERIFY: Regression test passes
9. ⚠️ VERIFY: Full test suite passes (no regressions)
10. THEN claim bug fixed
```

**Verification points: 5 gates before claiming fixed**

### Refactoring Workflow

```
1. Identify code to refactor
2. ⚠️ VERIFY: All tests pass (baseline)
3. Make refactoring changes
4. ⚠️ VERIFY: All tests still pass
5. ⚠️ VERIFY: Behavior unchanged
6. ⚠️ VERIFY: Performance not degraded
7. THEN claim refactoring complete
```

**Verification points: 4 gates ensuring safe refactoring**

### Code Review Workflow

**As reviewer:**
```
1. Read PR description and requirements
2. Review code changes (git diff)
3. ⚠️ VERIFY: Can't trust PR author verification
4. Checkout branch locally
5. ⚠️ VERIFY: Tests pass
6. ⚠️ VERIFY: Build succeeds
7. ⚠️ VERIFY: Requirements met
8. THEN approve PR
```

**As author:**
```
1. Complete feature/fix
2. ⚠️ VERIFY: All local checks pass
3. Push to branch
4. ⚠️ VERIFY: CI pipeline passes
5. Create PR with evidence
6. THEN request review
```

## Agent Delegation Workflows

### Delegating to AI Agent

**Before delegation:**
```
1. Define task clearly
2. Specify verification criteria
3. Delegate to agent
```

**After agent reports completion:**
```
4. ⚠️ NEVER trust agent report
5. Check git diff: What actually changed?
6. ⚠️ VERIFY: Run tests
7. ⚠️ VERIFY: Run build
8. ⚠️ VERIFY: Check requirements met
9. ⚠️ VERIFY: No unexpected changes
10. ⚠️ VERIFY: No secrets added
11. THEN accept or reject
```

**Critical rule: Agent success reports are NOT verification**

### Agent Verification Checklist

**For every agent task completion:**
```
[ ] Reviewed complete git diff
[ ] Ran full test suite
[ ] Checked build succeeds
[ ] Verified requirements met
[ ] No TODO/placeholder code
[ ] No commented-out code
[ ] No secrets in code
[ ] No unrelated changes
[ ] Dependencies appropriate
[ ] Code quality acceptable
```

**Only after ALL checks pass: Accept agent work**

### Multi-Agent Workflows

**When coordinating multiple agents:**
```
1. Agent A completes task
2. ⚠️ VERIFY: Agent A work correct
3. Agent B completes dependent task
4. ⚠️ VERIFY: Agent B work correct
5. ⚠️ VERIFY: Integration works (A + B together)
6. THEN proceed
```

**Each agent verified independently, then verify integration**

## CI/CD Pipeline Integration

### Pre-Commit Hook Verification

```bash
#!/bin/bash
# .git/hooks/pre-commit

# GATE FUNCTION: Verify before allowing commit

echo "Running pre-commit verification..."

# Test verification
pytest tests/ || exit 1
echo "✅ Tests pass"

# Linter verification
ruff check . || exit 1
echo "✅ Linter clean"

# Build verification
make build || exit 1
echo "✅ Build succeeds"

echo "✅ All verifications pass - commit allowed"
```

**Enforces gate function at commit time**

### CI Pipeline Stages

```yaml
# .github/workflows/ci.yml

name: CI Pipeline with Verification

on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      # Stage 1: Build
      - name: Build
        run: make build
      - name: Verify build artifacts
        run: ls dist/ && test -f dist/app

      # Stage 2: Test
      - name: Run tests
        run: pytest tests/
      - name: Verify test results
        run: |
          # Parse test output
          # Verify 0 failures

      # Stage 3: Lint
      - name: Run linter
        run: ruff check .
      - name: Verify linter output
        run: |
          # Verify 0 violations

      # Stage 4: Security
      - name: Security scan
        run: bandit -r .
      - name: Verify no critical issues
        run: |
          # Parse security output
          # Verify 0 high/critical
```

**Each stage has verification step**

### Deployment Pipeline Verification

```yaml
deploy:
  needs: verify
  steps:
    # Deploy
    - name: Deploy to staging
      run: ./deploy.sh staging

    # Verify deployment
    - name: Verify endpoint accessible
      run: curl -f https://staging.example.com/health

    - name: Verify application responding
      run: |
        response=$(curl -s https://staging.example.com/api/status)
        if [ "$response" != "OK" ]; then
          echo "Deployment verification failed"
          exit 1
        fi

    - name: Run smoke tests
      run: pytest tests/smoke/

    # Only proceed if all verifications pass
    - name: Deploy to production
      if: success()
      run: ./deploy.sh production
```

**Production deployment only after staging verification**

## Team Workflows

### Pull Request Template

```markdown
## Description
[What changed and why]

## Verification Evidence

### Tests
- [ ] All tests pass
- Command: `pytest tests/`
- Output: [paste output showing pass count]
- Exit code: 0

### Build
- [ ] Build succeeds
- Command: `make build`
- Output: [paste relevant output]
- Artifacts: [list created artifacts]

### Requirements
- [ ] Requirement 1: [evidence]
- [ ] Requirement 2: [evidence]
- [ ] Requirement 3: [evidence]

### Manual Testing
- [ ] Tested scenario 1: [result]
- [ ] Tested scenario 2: [result]

## CI Pipeline
- [ ] All CI checks pass
- Link: [CI run URL]
```

**Forces verification evidence collection**

### Code Review Checklist

**For reviewers:**
```
[ ] Author provided verification evidence
[ ] Checked out branch locally
[ ] Ran tests myself (don't trust author claim)
[ ] Verified build succeeds
[ ] Checked requirements met
[ ] Reviewed all changes in diff
[ ] No secrets added
[ ] Code quality acceptable
```

**Reviewer must independently verify**

## Emergency Workflows

### Production Hotfix Workflow

**Even under extreme time pressure:**

```
1. Reproduce production issue
2. ⚠️ VERIFY: Can reproduce locally
3. Implement minimal fix
4. ⚠️ VERIFY: Fix works locally
5. ⚠️ VERIFY: Tests pass
6. Deploy to staging
7. ⚠️ VERIFY: Fix works in staging
8. ⚠️ VERIFY: No new issues introduced
9. Deploy to production
10. ⚠️ VERIFY: Fix works in production
11. ⚠️ VERIFY: Monitor error rates
12. THEN claim hotfix complete
```

**Time pressure = MORE verification needed, not less**

### Rollback Verification

**When rolling back:**
```
1. Trigger rollback
2. ⚠️ VERIFY: Rollback completed
3. ⚠️ VERIFY: Application responding
4. ⚠️ VERIFY: Error rates normal
5. ⚠️ VERIFY: Key user flows work
6. THEN communicate "Rollback successful"
```

**Never assume rollback worked - verify it**

## Documentation Workflows

### Documentation Update Workflow

```
1. Update documentation
2. Have fresh user read it
3. ⚠️ VERIFY: User can follow steps successfully
4. ⚠️ VERIFY: All code examples work
5. ⚠️ VERIFY: All links valid
6. ⚠️ VERIFY: Screenshots current
7. THEN claim documentation complete
```

### API Documentation Workflow

```
1. Document API endpoints
2. Include request/response examples
3. ⚠️ VERIFY: Can run examples with curl
4. ⚠️ VERIFY: Response matches documentation
5. ⚠️ VERIFY: All error codes documented
6. ⚠️ VERIFY: All parameters documented
7. THEN publish API docs
```

## Metrics and Monitoring

### Tracking Verification Compliance

**Metrics to track:**
- % of commits with verification evidence
- % of PRs with verification evidence
- % of deployments with post-deployment verification
- False positive rate (unverified claims that failed)
- Time spent on verification vs debugging unverified work

**Goals:**
- 100% verification compliance
- < 5% false positive rate
- Verification time << debugging time saved

### Automation Opportunities

**What to automate:**
- Pre-commit hooks enforce verification
- CI pipelines enforce verification gates
- PR templates require verification evidence
- Deployment scripts include verification steps

**What NOT to automate:**
- Reading verification output (human must read)
- Making verification claims (human responsibility)
- Judging if verification is sufficient (requires judgment)

## The Bottom Line

Verification-before-completion is:
- **Non-negotiable** in every workflow
- **More critical** under time pressure, not less
- **Required** for agent work, never trust agent reports
- **Enforced** through automation where possible
- **Cultural** - team practice, not individual choice

**Integration principle:** Every workflow completion point needs a verification gate.

No shortcuts. No exceptions. No workflow bypasses verification.
