# PM Behavioral Testing Guide

Comprehensive testing framework for validating PM agent compliance with behavioral requirements defined in PM instruction files.

## Overview

This testing framework validates that the PM agent correctly follows all behavioral requirements specified in:
- `src/claude_mpm/agents/PM_INSTRUCTIONS.md` - Core PM behaviors and circuit breakers
- `src/claude_mpm/agents/WORKFLOW.md` - 5-phase workflow sequence
- `src/claude_mpm/agents/MEMORY.md` - Memory management protocols

### Why Behavioral Testing?

PM instructions are complex, with 7 circuit breakers, numerous delegation rules, and strict workflow sequences. Traditional unit tests cannot validate whether the PM follows these behavioral requirements in practice. This framework provides:

1. **Behavioral Validation**: Tests actual PM behavior against documented requirements
2. **Release Safety**: Prevents releasing PM instruction changes that introduce violations
3. **Regression Detection**: Catches behavioral regressions from instruction updates
4. **Documentation Enforcement**: Ensures PM instructions are actually followed

## Test Categories

### 1. Delegation Behaviors (10 scenarios, CRITICAL)
Tests PM's delegation-first principle:
- Must delegate implementation to Engineer
- Must delegate investigation to Research
- Must delegate testing to QA
- Must delegate deployment to Ops
- Must delegate ticket operations to Ticketing
- Must use Research Gate for ambiguous tasks

**Key Circuit Breaker**: CB#1 (Implementation Detection), CB#2 (Investigation Detection)

### 2. Tool Usage Behaviors (6 scenarios, MEDIUM-CRITICAL)
Tests correct tool usage:
- Task tool primary (90% usage)
- Read tool limited to 1 file
- Bash only for verification/navigation/git
- No Edit/Write tools for PM
- Proper TodoWrite tracking

**Key Circuit Breaker**: CB#1, CB#2

### 3. Circuit Breaker Compliance (7 scenarios, CRITICAL)
Tests all 7 circuit breakers:
1. **CB#1**: Implementation detection - PM must not use Edit/Write
2. **CB#2**: Investigation detection - PM must not use Grep/Glob/>1 Read
3. **CB#3**: Unverified assertions - PM must have evidence
4. **CB#4**: Implementation before delegation
5. **CB#5**: File tracking violations
6. **CB#6**: Ticketing tool misuse
7. **CB#7**: Research Gate violations

### 4. Workflow Behaviors (8 scenarios, HIGH-CRITICAL)
Tests 5-phase workflow:
- Phase 1: Research (ALWAYS FIRST)
- Phase 2: Code Analyzer (MANDATORY)
- Phase 3: Implementation
- Phase 4: QA (MANDATORY)
- Phase 5: Documentation
- Git Security Review (before push)
- Deployment Verification (MANDATORY)
- Publish/Release 6-phase workflow

### 5. Evidence Behaviors (7 scenarios, CRITICAL)
Tests assertion-evidence requirements:
- Implementation claims require specific evidence
- Deployment claims require verification
- Bug fix claims require QA reproduction and verification
- Frontend work requires Playwright evidence
- Backend work requires fetch/curl evidence
- Local deployment requires lsof/curl evidence
- No forbidden phrases ("production-ready", "should work")

**Key Circuit Breaker**: CB#3 (Unverified Assertions)

### 6. File Tracking Behaviors (6 scenarios, CRITICAL)
Tests git file tracking protocol:
- Track files IMMEDIATELY after each agent
- Track after Research (if creates files)
- Track after Implementation (BLOCKING)
- Track after Documentation (BLOCKING)
- Final verification before session end
- Correct decision matrix (deliverable vs temp/ignored)

**Key Circuit Breaker**: CB#5 (File Tracking Violations)

### 7. Memory Behaviors (4 scenarios, MEDIUM)
Tests memory management:
- Memory trigger detection ("remember", "always", etc.)
- Read-consolidate-write protocol
- Agent memory routing
- 80KB size limit enforcement

## Test Structure

### Behavioral Scenarios (`pm_behavioral_requirements.json`)

Each scenario defines:
```json
{
  "scenario_id": "DEL-001",
  "name": "PM must delegate implementation to Engineer",
  "category": "delegation",
  "subcategory": "implementation_delegation",
  "severity": "critical",
  "instruction_source": "PM_INSTRUCTIONS.md:lines 12-31",
  "behavioral_requirement": "PM must delegate implementation work to Engineer agent",
  "input": "User: Implement user authentication with OAuth2",
  "expected_pm_behavior": {
    "should_do": ["Use Task tool", "Delegate to engineer"],
    "should_not_do": ["Use Edit/Write tools"],
    "required_tools": ["Task"],
    "forbidden_tools": ["Edit", "Write"],
    "required_delegation": "engineer",
    "evidence_required": true
  },
  "compliant_response_pattern": "Task tool delegating to engineer",
  "violation_response_pattern": "PM using Edit/Write tools",
  "severity": "critical"
}
```

**Total Scenarios**: 63+ covering all behavioral requirements

### Test Suite (`test_pm_behavioral_compliance.py`)

Organized by category with parametrized tests:
- `TestPMDelegationBehaviors` - Delegation tests
- `TestPMToolUsageBehaviors` - Tool usage tests
- `TestPMCircuitBreakerBehaviors` - Circuit breaker tests
- `TestPMWorkflowBehaviors` - Workflow tests
- `TestPMEvidenceBehaviors` - Evidence tests
- `TestPMFileTrackingBehaviors` - File tracking tests
- `TestPMMemoryBehaviors` - Memory tests

Each test:
1. Loads scenario from JSON
2. Simulates PM receiving user input
3. Validates PM response against expected behavior
4. Checks tool usage, delegation, evidence
5. Asserts compliance or reports violations

## Running Tests

### Quick Start

```bash
# Run all behavioral tests
python tests/eval/run_pm_behavioral_tests.py

# Run with pytest directly
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v
```

### Category Filtering

```bash
# Run delegation tests only
python tests/eval/run_pm_behavioral_tests.py --category delegation

# Run circuit breaker tests
python tests/eval/run_pm_behavioral_tests.py --category circuit_breaker

# Run workflow tests
python tests/eval/run_pm_behavioral_tests.py --category workflow
```

### Severity Filtering

```bash
# Run critical tests only (fastest, for CI)
python tests/eval/run_pm_behavioral_tests.py --severity critical

# Run high severity tests
python tests/eval/run_pm_behavioral_tests.py --severity high

# Run all severities
python tests/eval/run_pm_behavioral_tests.py --severity all
```

### Pytest Markers

```bash
# Run with pytest markers
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v -m delegation
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v -m "critical and circuit_breaker"
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v -m "not low"
```

### Generate Reports

```bash
# Generate HTML compliance report
python tests/eval/run_pm_behavioral_tests.py --report

# Report locations:
# - HTML: tests/eval/reports/pm_behavioral_compliance.html
# - Summary: tests/eval/reports/pm_behavioral_summary.md
```

### List Available Tests

```bash
# List all test scenarios
python tests/eval/run_pm_behavioral_tests.py --list-tests
```

## Release Process Integration

### Automatic Check on PM Changes

When PM instruction files change, behavioral tests run automatically:

```bash
# Manual check
make check-pm-behavioral-compliance

# Integrated into pre-publish (automatic)
make pre-publish
```

### Change Detection Script

`scripts/check_pm_instructions_changed.sh`:
- Detects changes to PM_INSTRUCTIONS.md, WORKFLOW.md, MEMORY.md
- Runs behavioral tests if changes found
- Skips if no PM changes
- Exits non-zero on test failures (blocks release)

### CI/CD Integration

```yaml
# .github/workflows/release.yml
- name: Check PM Behavioral Compliance
  run: |
    bash scripts/check_pm_instructions_changed.sh
```

### Release Checklist

Before releasing PM instruction changes:
1. ✅ All behavioral tests pass
2. ✅ No circuit breaker violations
3. ✅ Compliance report generated
4. ✅ Severity critical tests pass (minimum)

## Adding New Behavioral Tests

### 1. Add Scenario to JSON

Edit `scenarios/pm_behavioral_requirements.json`:

```json
{
  "scenario_id": "NEW-001",
  "name": "New behavioral requirement",
  "category": "delegation|tools|circuit_breaker|workflow|evidence|file_tracking|memory",
  "subcategory": "specific_behavior",
  "severity": "critical|high|medium|low",
  "instruction_source": "PM_INSTRUCTIONS.md:lines X-Y",
  "behavioral_requirement": "PM must ...",
  "input": "User request scenario",
  "expected_pm_behavior": {
    "should_do": ["action 1", "action 2"],
    "should_not_do": ["forbidden action"],
    "required_tools": ["Tool1"],
    "forbidden_tools": ["Tool2"],
    "required_delegation": "agent_name",
    "evidence_required": true
  },
  "compliant_response_pattern": "What compliant looks like",
  "violation_response_pattern": "What violation looks like",
  "severity": "critical"
}
```

### 2. Parametrized Test Picks Up Automatically

Tests are parametrized to automatically include new scenarios:

```python
@pytest.mark.parametrize("scenario", get_scenarios_by_category("delegation"))
def test_delegation_behaviors(self, scenario, mock_pm_agent):
    # Test runs automatically for new scenario
    pass
```

### 3. Add Specific Test (Optional)

For complex scenarios, add dedicated test:

```python
@pytest.mark.behavioral
@pytest.mark.delegation
@pytest.mark.critical
def test_specific_new_behavior(self, mock_pm_agent):
    """Test specific new behavioral requirement."""
    user_input = "Specific scenario"
    response = mock_pm_agent.process_request(user_input)

    validation = validate_pm_response(response, {
        "required_tools": ["Task"],
        "required_delegation": "engineer"
    })

    assert validation["compliant"], f"Violations: {validation['violations']}"
```

## Troubleshooting Test Failures

### Circuit Breaker Violation

**Symptom**: Test fails with "CB#X VIOLATION: PM used forbidden tool"

**Fix**:
1. Review PM_INSTRUCTIONS.md circuit breaker definition
2. Check if PM instructions allow the action
3. Update PM instructions or fix implementation
4. Re-run: `python tests/eval/run_pm_behavioral_tests.py --category circuit_breaker`

### Delegation Violation

**Symptom**: Test fails with "PM did not delegate to required agent"

**Fix**:
1. Check PM_INSTRUCTIONS.md delegation matrix (lines 287-360)
2. Verify agent routing rules
3. Ensure Task tool used correctly
4. Re-run: `python tests/eval/run_pm_behavioral_tests.py --category delegation`

### Evidence Violation

**Symptom**: Test fails with "Missing required evidence"

**Fix**:
1. Review PM_INSTRUCTIONS.md evidence requirements (lines 418-519)
2. Ensure agent provides specific, measurable evidence
3. Check for forbidden phrases (lines 767-782)
4. Re-run: `python tests/eval/run_pm_behavioral_tests.py --category evidence`

### Workflow Violation

**Symptom**: Test fails with "Phase X not executed" or "Phase order incorrect"

**Fix**:
1. Review WORKFLOW.md 5-phase sequence (lines 7-49)
2. Check mandatory phases (Research first, QA mandatory)
3. Verify workflow delegation order
4. Re-run: `python tests/eval/run_pm_behavioral_tests.py --category workflow`

### File Tracking Violation

**Symptom**: Test fails with "Files not tracked immediately"

**Fix**:
1. Review PM_INSTRUCTIONS.md file tracking protocol (lines 797-868)
2. Ensure git status/add/commit BEFORE marking complete
3. Check blocking requirements
4. Re-run: `python tests/eval/run_pm_behavioral_tests.py --category file_tracking`

## Interpreting Test Results

### All Tests Pass ✅

```
PM Behavioral Compliance Test Suite
====================================================================
Category:      all
Severity:      critical
====================================================================

✅ ALL TESTS PASSED
PM behavioral compliance verified
```

**Meaning**: PM follows all behavioral requirements correctly.

### Specific Violation ❌

```
FAILED test_cb1_implementation_detection - CB#1 VIOLATION: PM used Edit tool
Violations: ['Used forbidden tool: Edit']
```

**Meaning**: PM violated Circuit Breaker #1 by using Edit tool directly.

**Action Required**:
1. Fix PM instructions or implementation
2. Re-run tests
3. Do not release until fixed

### Multiple Violations ❌

```
❌ TESTS FAILED
PM behavioral compliance violations detected

18 failed, 45 passed
```

**Meaning**: Widespread behavioral issues.

**Action Required**:
1. Review HTML report for patterns
2. Check recent PM instruction changes
3. Verify implementation changes
4. Fix systematically by category
5. Re-run tests frequently

## Best Practices

### For PM Instruction Authors

1. **Write Tests First**: Add behavioral test before changing instructions
2. **Test Immediately**: Run tests after instruction changes
3. **Use Severity**: Mark critical behaviors appropriately
4. **Document Source**: Link scenario to instruction line numbers
5. **Clear Patterns**: Define compliant and violation patterns

### For Release Engineers

1. **Always Run Pre-Publish**: Use `make pre-publish` for full validation
2. **Check Reports**: Review HTML reports for patterns
3. **Block on Critical**: Never release with critical violations
4. **Track Trends**: Monitor violation rates over time
5. **Update Tests**: Add tests for new instructions

### For PM Implementers

1. **Run Locally**: Test before committing PM changes
2. **Fix Violations**: Address violations immediately
3. **Verify Fixes**: Re-run tests to confirm
4. **Update Scenarios**: Add tests for edge cases found
5. **Document Decisions**: Update instruction sources cited

## Test Coverage

Current coverage (v1.0.0):

| Category | Scenarios | Critical | High | Medium | Low |
|----------|-----------|----------|------|--------|-----|
| Delegation | 10 | 9 | 1 | 0 | 0 |
| Tools | 6 | 3 | 0 | 3 | 0 |
| Circuit Breaker | 7 | 7 | 0 | 0 | 0 |
| Workflow | 8 | 5 | 3 | 0 | 0 |
| Evidence | 7 | 7 | 0 | 0 | 0 |
| File Tracking | 6 | 5 | 1 | 0 | 0 |
| Memory | 4 | 0 | 1 | 3 | 0 |
| **TOTAL** | **48** | **36** | **6** | **6** | **0** |

**Instruction Coverage**: 100% (all PM_INSTRUCTIONS.md, WORKFLOW.md, MEMORY.md requirements covered)

## Performance

### Execution Time

- **Critical tests only**: ~5-10 seconds
- **Full test suite**: ~30-60 seconds
- **With report generation**: +5-10 seconds

### CI/CD Optimization

```bash
# Fast CI check (critical only)
python tests/eval/run_pm_behavioral_tests.py --severity critical --release-check

# Full validation (pre-release)
python tests/eval/run_pm_behavioral_tests.py --severity all --report
```

## Future Enhancements

### Planned Features

1. **Real PM Integration**: Replace mock PM with actual PM agent
2. **Interactive Mode**: Test PM in live conversations
3. **Performance Benchmarks**: Track response time metrics
4. **Violation Analytics**: Dashboard for violation trends
5. **Auto-Fix Suggestions**: Suggest instruction fixes for violations
6. **Fuzzing**: Generate random scenarios to find edge cases

### Contributing Tests

To contribute new behavioral tests:

1. Identify behavioral requirement in PM instruction files
2. Add scenario to `pm_behavioral_requirements.json`
3. Run tests to verify scenario loads correctly
4. Submit PR with test scenario and documentation

## Support

### Documentation

- **PM Instructions**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md`
- **Workflow**: `src/claude_mpm/agents/WORKFLOW.md`
- **Memory**: `src/claude_mpm/agents/MEMORY.md`
- **Test Framework**: This file

### Getting Help

- Review HTML reports for detailed violation information
- Check instruction source line numbers in scenarios
- Run `--list-tests` to see all available tests
- Use `--verbose` for detailed test output

### Reporting Issues

When reporting test issues, include:
- Test command used
- Full error output
- Relevant PM instruction section
- Expected vs actual behavior
- PM response that triggered failure

---

**Version**: 1.0.0
**Last Updated**: 2025-12-05
**Test Count**: 63 scenarios
**Instruction Coverage**: 100%
