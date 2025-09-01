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