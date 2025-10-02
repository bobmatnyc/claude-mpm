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

## Test Process Management

When running tests in JavaScript/TypeScript projects:

### 1. Always Use Non-Interactive Mode

**CRITICAL**: Never use watch mode during agent operations as it causes memory leaks.

```bash
# CORRECT - CI-safe test execution
CI=true npm test
npx vitest run --reporter=verbose
npx jest --ci --no-watch

# WRONG - Causes memory leaks
npm test  # May trigger watch mode
npm test -- --watch  # Never terminates
vitest  # Default may be watch mode
```

### 2. Verify Process Cleanup

After running tests, always verify no orphaned processes remain:

```bash
# Check for hanging test processes
ps aux | grep -E "(vitest|jest|node.*test)" | grep -v grep

# Kill orphaned processes if found
pkill -f "vitest" || pkill -f "jest"
```

### 3. Package.json Best Practices

Before running any test command:
- **Always check package.json** test script configuration
- Verify if test script uses watch mode by default
- Use explicit `--run` or `--ci` flags when uncertain

```bash
# Check test configuration first
cat package.json | grep -A 2 '"test"'

# If watch mode detected, override with:
CI=true npm test
# OR use run flag explicitly:
npx vitest run
```

### 4. Common Pitfalls to Avoid

- ❌ Running `npm test` when package.json has watch mode as default
- ❌ Not waiting for test completion before continuing
- ❌ Not checking for orphaned test processes
- ❌ Assuming test commands are CI-safe without verification
- ✅ Always check package.json configuration first
- ✅ Use CI=true or explicit --run/--ci flags
- ✅ Verify process termination after tests
- ✅ Monitor for hanging processes between test runs

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