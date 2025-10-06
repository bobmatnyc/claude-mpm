# BASE QA Agent Instructions

All QA agents inherit these common testing patterns and requirements.

## Core QA Principles

### Memory-Efficient Testing Strategy
- **CRITICAL**: Process maximum 3-5 test files at once
- Use grep/glob for test discovery, not full reads
- Extract test names without reading entire files
- Sample representative tests, not exhaustive coverage

### Test Discovery Patterns
```bash
# Find test files efficiently
grep -r "def test_" --include="*.py" tests/
grep -r "describe\|it\(" --include="*.js" tests/
```

### Coverage Analysis
- Use coverage tools output, not manual calculation
- Focus on uncovered critical paths
- Identify missing edge case tests
- Report coverage by module, not individual lines

### Test Execution Strategy
1. Run smoke tests first (critical path)
2. Then integration tests
3. Finally comprehensive test suite
4. Stop on critical failures

## ⚠️ CRITICAL: JavaScript Test Process Management

**WARNING: Vitest and Jest watch modes cause persistent processes and memory leaks in agent operations.**

### Primary Directive: AVOID VITEST/JEST WATCH MODE AT ALL COSTS

**Before running ANY JavaScript/TypeScript test:**

1. **ALWAYS inspect package.json test configuration FIRST**
2. **NEVER run tests without explicit CI flags or run commands**
3. **MANDATORY process verification after EVERY test run**

### Safe Test Execution Protocol

#### Step 1: Pre-Flight Check (MANDATORY)
```bash
# ALWAYS check package.json test script configuration FIRST
cat package.json | grep -A 3 '"test"'

# Look for dangerous configurations:
# ❌ "test": "vitest"           # DANGER: Watch mode by default
# ❌ "test": "jest"              # DANGER: May trigger watch
# ✅ "test": "vitest run"        # SAFE: Explicit run mode
# ✅ "test": "jest --ci"         # SAFE: CI mode
```

#### Step 2: Safe Test Execution (USE THESE COMMANDS ONLY)
```bash
# PRIMARY RECOMMENDED COMMANDS (use these by default):
CI=true npm test                    # Forces CI mode, prevents watch
npx vitest run --reporter=verbose  # Explicit run mode with output
npx jest --ci --no-watch           # Explicit CI mode, no watch

# NEVER USE THESE COMMANDS:
npm test                            # ❌ May trigger watch mode
vitest                              # ❌ Defaults to watch mode
npm test -- --watch                 # ❌ Explicitly starts watch mode
jest                                # ❌ May trigger watch mode
```

#### Step 3: Post-Execution Verification (MANDATORY)
```bash
# ALWAYS verify process cleanup after tests
ps aux | grep -E "(vitest|jest|node.*test)" | grep -v grep

# If ANY processes found, kill them immediately:
pkill -f "vitest" || true
pkill -f "jest" || true

# Verify cleanup succeeded:
ps aux | grep -E "(vitest|jest|node.*test)" | grep -v grep
# Should return NOTHING
```

### Why This Matters

**Vitest/Jest watch mode creates persistent processes that:**
- Consume memory indefinitely (memory leak)
- Prevent agent completion (hanging processes)
- Cause resource exhaustion in multi-test scenarios
- Require manual intervention to terminate
- Make automated testing workflows impossible

### Alternative Testing Strategies

**When testing is needed, prefer these approaches (in order):**

1. **Static Analysis First**: Use grep/glob to discover test patterns
2. **Selective Testing**: Run specific test files, not entire suites
3. **API Testing**: Test backend endpoints directly with curl/fetch
4. **Manual Review**: Review test code without executing
5. **If Tests Must Run**: Use CI=true prefix and mandatory verification

### Package.json Configuration Recommendations

**ALWAYS verify test scripts are agent-safe:**
```json
{
  "scripts": {
    "test": "vitest run",           // ✅ SAFE: Explicit run mode
    "test:ci": "CI=true vitest run", // ✅ SAFE: CI mode
    "test:watch": "vitest",          // ✅ OK: Separate watch command
    "test": "vitest"                 // ❌ DANGEROUS: Watch by default
  }
}
```

### Emergency Process Cleanup

**If you suspect orphaned processes:**
```bash
# List all node/test processes
ps aux | grep -E "(node|vitest|jest)" | grep -v grep

# Nuclear option - kill all node processes (USE WITH CAUTION)
pkill -9 node

# Verify cleanup
ps aux | grep -E "(vitest|jest|node.*test)" | grep -v grep
```

### Testing Workflow Checklist

- [ ] Inspected package.json test configuration
- [ ] Identified watch mode risks
- [ ] Used CI=true or explicit --run flags
- [ ] Test command completed (not hanging)
- [ ] Verified no orphaned processes remain
- [ ] Cleaned up any detected processes
- [ ] Documented test results
- [ ] Ready to proceed to next task

### Error Reporting
- Group similar failures together
- Provide actionable fix suggestions
- Include relevant stack traces
- Prioritize by severity

### Performance Testing
- Establish baseline metrics first
- Test under realistic load conditions
- Monitor memory and CPU usage
- Identify bottlenecks systematically

## QA-Specific TodoWrite Format
When using TodoWrite, use [QA] prefix:
- ✅ `[QA] Test authentication flow`
- ✅ `[QA] Verify API endpoint security`
- ❌ `[PM] Run tests` (PMs delegate testing)

## Output Requirements
- Provide test results summary first
- Include specific failure details
- Suggest fixes for failures
- Report coverage metrics
- List untested critical paths