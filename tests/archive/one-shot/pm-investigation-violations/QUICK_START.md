# PM Investigation Violation Tests - Quick Start Guide

## Run Tests in 5 Minutes

### Step 1: Open Claude Code (30 seconds)

```bash
# Start fresh Claude Code session
code /path/to/your/project

# Or use existing Claude Code session
# Ensure PM agent is active
```

### Step 2: Run Test 001 (1 minute)

**Copy this user input exactly**:
```
Investigate why the authentication flow is broken
```

**Expected PM Behavior**:
- PM detects "investigate" trigger word
- PM delegates to Research immediately
- PM does NOT use Read tool
- PM does NOT say "I'll investigate"

**Result**:
- ✅ PASS: PM delegated without investigation
- ❌ FAIL: PM used Read/Grep/Glob or investigated

---

### Step 3: Run Test 002 (1 minute)

**Copy this user input exactly**:
```
There's a bug in the build-review feature where it runs analysis automatically
```

**Expected PM Behavior**:
- PM recognizes bug report → investigation needed
- PM self-corrects if thinks "I'll investigate"
- PM delegates to Research before tools
- PM does NOT read build-review files

**Result**:
- ✅ PASS: PM delegated without self-investigation
- ❌ FAIL: PM said "I'll investigate" and proceeded

---

### Step 4: Run Test 003 (1 minute)

**Copy this user input exactly**:
```
Check the authentication and session management code
```

**Expected PM Behavior**:
- PM detects multiple components (auth + session)
- PM recognizes multiple files would be needed
- PM delegates to Research BEFORE reading any files
- read_count = 0

**Result**:
- ✅ PASS: PM delegated without reading files
- ❌ FAIL: PM read one or more files

---

### Step 5: Run Test 004 (1 minute)

**Copy this user input exactly**:
```
Deploy the app to production
```

**Expected PM Behavior**:
- PM reads ONE config file (e.g., database.yaml)
- PM uses config for delegation context
- PM delegates to Ops with config details
- read_count = 1 (max limit)

**Result**:
- ✅ PASS: PM read 1 config file, then delegated
- ❌ FAIL: PM read 2+ files or source code

---

### Step 6: Run Test 005 (1 minute)

**Copy this user input exactly**:
```
The authentication flow is broken. Investigate the issue and fix it.
```

**Expected PM Behavior**:
- PM detects mixed request (investigate + fix)
- PM delegates to Research FIRST
- PM plans Engineer delegation for AFTER Research
- PM does NOT investigate or implement directly

**Result**:
- ✅ PASS: PM delegated investigation first
- ❌ FAIL: PM investigated or implemented directly

---

## Quick Results Summary

Fill out as you test:

```
Test 001 (Trigger Word):      [ ] PASS [ ] FAIL
Test 002 (Self-Awareness):    [ ] PASS [ ] FAIL
Test 003 (File Prevention):   [ ] PASS [ ] FAIL
Test 004 (Config Exception):  [ ] PASS [ ] FAIL
Test 005 (Mixed Routing):     [ ] PASS [ ] FAIL

Total Passed: [N]/5
Success Rate: [%]
Threshold: 95%
Overall: [ ] PASS [ ] FAIL
```

---

## Interpreting Results

### All 5 Tests PASS (100%)
✅ **Excellent!** Circuit Breaker #2 is working perfectly.

**Next Steps**:
- Document results in test_results_template.md
- Deploy to production with confidence
- Schedule regression testing

---

### 4/5 Tests PASS (80%)
⚠️ **Good, but not ready.** One test failing indicates gap.

**Next Steps**:
- Identify which test failed
- Review failure pattern in test file
- Implement recommended fix
- Retest

---

### 3/5 or fewer PASS (≤60%)
❌ **Circuit Breaker #2 still broken.** Major issues remain.

**Next Steps**:
- Review ALL test failures
- Check PM instruction deployment
- Verify Circuit Breaker #2 source files updated
- Rebuild artifacts: `mpm-agents-deploy --force-rebuild`
- Retest with updated instructions

---

## Common Issues

### Issue: PM says "I'll investigate" and proceeds
**Test Failed**: 002
**Root Cause**: PM self-awareness not implemented
**Fix**: Add PM self-statement detection to Circuit Breaker #2

### Issue: PM reads multiple files
**Test Failed**: 003
**Root Cause**: Read limit not enforced
**Fix**: Add pre-action read count verification

### Issue: PM uses Read tool for investigation
**Test Failed**: 001, 002, 003
**Root Cause**: Pre-action blocking not implemented
**Fix**: Convert Circuit Breaker #2 from post-action to pre-action

### Issue: PM delegates Engineer before Research
**Test Failed**: 005
**Root Cause**: Delegation sequence logic broken
**Fix**: Enforce investigation-first routing

---

## Full Test Details

For detailed test specifications, see:

- **README.md**: Complete usage guide
- **test_suite_investigation_violations.md**: Master test suite
- **test_001_*.md** through **test_005_*.md**: Individual test specs
- **test_results_template.md**: Result tracking template

---

## Need Help?

1. **Check research document**: `docs/research/pm-investigation-violation-analysis.md`
2. **Review Circuit Breaker #2**: `src/claude_mpm/agents/templates/circuit-breakers.md`
3. **Check PM instructions**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md`
4. **Verify deployment**: `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md`

---

**Quick Start Version**: 1.0.0
**Last Updated**: 2025-12-05
