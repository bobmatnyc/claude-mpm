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

**Edge Cases:**
- Flaky tests: Run multiple times, document flakiness
- Timeout tests: Verify timeout values appropriate
- Skipped tests: Count and document why skipped
- Warnings in output: Document and address

**Troubleshooting:**
- **Tests hang**: Check for infinite loops, deadlocks
- **Random failures**: Run 10x, identify flaky tests
- **Environment issues**: Verify dependencies, config
- **Coverage gaps**: Check coverage report for holes

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

**Edge Cases:**
- Test passes immediately: Test doesn't catch bug, rewrite
- Test fails differently: Fix changed behavior, investigate
- Can't revert cleanly: Use version control, stash changes

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

**Build Types to Verify:**
- Development build: Fast iteration
- Production build: Minification, optimization
- Test build: Coverage instrumentation
- Distribution build: Platform-specific artifacts

**Troubleshooting:**
- **Build succeeds but artifacts missing**: Check output directory
- **Incremental build issues**: Clean build, verify again
- **Platform-specific failures**: Test on target platform
- **Resource exhaustion**: Check memory, disk space

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

**Multiple Linters Pattern:**
```
1. Run each linter separately
2. Verify each independently
3. Document results for each
4. Only claim clean if ALL pass
```

**Edge Cases:**
- Warnings vs errors: Document acceptable warnings
- Auto-fix available: Run auto-fix, verify results
- Custom rules: Verify custom rules active
- Ignored files: Document why files ignored

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

**Bug Types:**
- **Logic bugs**: Unit test verifies correct behavior
- **Race conditions**: Stress test, run 100x
- **Edge cases**: Test boundary conditions
- **Integration bugs**: End-to-end test verifies
- **Performance bugs**: Benchmark before/after

**Troubleshooting:**
- **Can't reproduce**: Document steps, environment
- **Intermittent bug**: Increase test iterations
- **Different in production**: Test in production-like environment
- **Fix causes regression**: Test full suite, not just bug test

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

**Requirement Types:**
- **Functional**: Feature works as specified
- **Non-functional**: Performance, scalability, security
- **User experience**: UI/UX matches design
- **Integration**: Works with other systems
- **Documentation**: Docs complete and accurate

**Checklist Format:**
```
[ ] Requirement 1: [Evidence: test_feature_x passes]
[ ] Requirement 2: [Evidence: benchmark shows 50ms response]
[ ] Requirement 3: [Evidence: manual testing confirms behavior]
[X] Requirement 4: MISSING - not yet implemented
[ ] Requirement 5: [Evidence: integration test passes]
```

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

**Agent Verification Checklist:**
```
1. Review git diff: What changed?
2. Run tests: Do tests still pass?
3. Check task requirements: All met?
4. Look for unexpected changes: Any surprises?
5. Verify no secrets added: .env, keys, tokens?
6. Check for commented code: Any TODOs added?
7. Verify imports/dependencies: Any new ones?
```

**Common Agent Failures:**
- Agent adds TODO instead of implementing
- Agent introduces syntax errors
- Agent misunderstands requirements
- Agent makes unrelated changes
- Agent adds secrets to version control
- Agent breaks existing functionality

**Troubleshooting:**
- **Agent claims success but tests fail**: Review diff, find issue
- **Agent made unexpected changes**: Revert, clarify task
- **Agent added placeholder code**: Complete implementation
- **Agent broke unrelated code**: Partial revert, fix issue

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

**Environment-Specific Verification:**

**Staging:**
```
1. Deploy to staging
2. Run full test suite against staging
3. Check all endpoints
4. Verify database migrations
5. Test with production-like data
```

**Production:**
```
1. Deploy to production
2. Verify zero-downtime deployment
3. Check health endpoints
4. Monitor error rates
5. Verify key user flows
6. Keep rollback ready
```

**Deployment Types:**
- **Blue-green**: Verify both environments
- **Canary**: Monitor canary metrics
- **Rolling**: Verify each batch
- **Feature flags**: Verify flag state

**Troubleshooting:**
- **Deployment succeeds but service down**: Check logs, restart
- **Configuration mismatch**: Verify environment variables
- **Database migration failed**: Rollback, investigate
- **Partial deployment**: Complete or rollback fully

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

**Benchmark Requirements:**
- **Sample size**: Minimum 10 runs
- **Statistical significance**: Calculate standard deviation
- **Cold vs warm**: Test both scenarios
- **Load levels**: Test under different loads
- **Environment**: Same environment for before/after

**Metrics to Measure:**
- **Response time**: p50, p95, p99 latency
- **Throughput**: Requests per second
- **Resource usage**: CPU, memory, disk I/O
- **Database queries**: Query count, duration
- **Network**: Bandwidth, connection count

**Edge Cases:**
- Performance regression: Identify cause, revert if needed
- Inconsistent results: Check for external factors
- Different under load: Load test before claiming
- Memory leaks: Profile memory over time

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

**Security Layers to Verify:**

**Static Analysis:**
```
1. Code scanning: bandit, semgrep
2. Dependency scanning: safety check
3. Secret scanning: git secrets
4. License compliance: license checker
```

**Dynamic Analysis:**
```
1. Penetration testing: OWASP ZAP
2. Fuzzing: Input validation
3. Load testing: DoS resistance
4. Authentication testing: Auth flows
```

**Security Checklist:**
- [ ] Input validation implemented
- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] CSRF protection
- [ ] Authentication secure
- [ ] Authorization checks
- [ ] Secrets not in code
- [ ] HTTPS enforced
- [ ] Headers configured
- [ ] Dependencies updated

**Troubleshooting:**
- **False positives**: Document and suppress with justification
- **Critical findings**: Fix immediately, don't suppress
- **Dependency vulnerabilities**: Update or replace
- **Configuration issues**: Fix in deployment configs

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

**Documentation Types:**

**API Documentation:**
```
1. Document all endpoints
2. Include request/response examples
3. Document error codes
4. Test with curl/Postman
5. Verify examples work
```

**User Documentation:**
```
1. Write step-by-step guide
2. Include screenshots
3. Test with fresh user
4. Record where they get stuck
5. Improve those sections
```

**Developer Documentation:**
```
1. Document setup steps
2. Fresh clone, follow steps
3. Verify can build and run
4. Document all prerequisites
5. Test on clean machine
```

**Troubleshooting:**
- **User gets stuck**: Add more detail, screenshots
- **Prerequisites missing**: Document all dependencies
- **Examples don't work**: Verify and fix examples
- **Outdated documentation**: Regular review and updates

## CI/CD Pipeline Verification

**Correct Pattern:**
```
1. Push to branch
2. Watch CI pipeline run
3. Verify all stages pass: build, test, lint, security
4. Check pipeline logs for warnings
5. Verify artifacts created
6. Claim: "CI pipeline passes, all stages green"
```

**Pipeline Stages to Verify:**
- **Build**: Code compiles, artifacts created
- **Test**: All tests pass, coverage threshold met
- **Lint**: Code style compliance
- **Security**: No vulnerabilities found
- **Deploy**: Successful deployment to target

**Edge Cases:**
- Flaky pipeline: Investigate root cause, fix
- Timeout issues: Optimize slow stages
- Cache issues: Clear cache, rebuild
- Secrets missing: Verify environment variables

## Database Migration Verification

**Correct Pattern:**
```
1. Backup database
2. Run migration on backup
3. Verify data integrity
4. Test rollback
5. Run on staging
6. Verify application works
7. Document any data changes
8. Claim: "Migration tested, rollback verified"
```

**Critical Checks:**
- **Data loss prevention**: Verify no data dropped
- **Rollback tested**: Must be able to undo
- **Application compatibility**: App works during migration
- **Performance impact**: Migration doesn't lock tables long

**Edge Cases:**
- Large tables: Use online migration tools
- Zero-downtime: Test deployment order
- Data transformation: Verify transformation logic
- Foreign key constraints: Check constraint violations

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
