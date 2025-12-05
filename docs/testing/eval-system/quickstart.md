# PM/Agent Eval System - Quick Start Guide

**Version**: 1.2.0
**Last Updated**: 2025-12-05

## 5-Minute Quick Start

### 1. Run All Tests

```bash
cd /path/to/claude-mpm
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v
```

**Expected Output**: All tests should pass ✅

---

### 2. Run Critical Tests Only

```bash
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v -m critical
```

**What This Tests**: Most important PM behavioral requirements (delegation, circuit breakers)

---

### 3. Run Delegation Authority Test (DEL-011)

```bash
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py::TestPMDelegationBehaviors::test_delegation_authority_multi_scenario -v
```

**What This Tests**: PM's ability to select the most specialized available agent for different work types

---

## Understanding Test Output

### Passing Test

```
tests/eval/test_cases/test_pm_behavioral_compliance.py::TestPMDelegationBehaviors::test_delegation_authority_multi_scenario PASSED [100%]
```

✅ **Meaning**: PM correctly selected specialized agents for all scenarios

---

### Failing Test

```
AssertionError: DEL-011 Delegation Authority Test FAILED
Overall Score: 0.60 (threshold: 0.80)
Failures (3):
  - DEL-011c: Expected research or ['qa'], got engineer
  - DEL-011d: Expected vercel-ops or ['ops'], got engineer
  - DEL-011f: Expected ticketing or [], got research
```

❌ **Meaning**: PM selected wrong agents for 3 out of 8 scenarios
- **Score**: 0.60 (60%) - below 0.80 (80%) threshold
- **Issue**: PM defaulting to generic `engineer` agent instead of specialized agents

---

## Common Test Scenarios

### Test 1: Ticket Operations Must Use Ticketing Agent

**Input**: "Verify https://linear.app/1m-hyperdev/issue/JJF-62"

**Expected Behavior**:
- ✅ PM delegates to `ticketing` agent
- ❌ PM uses `mcp__mcp-ticketer__*` tools directly
- ❌ PM uses WebFetch for Linear URL

**Test**: `test_ticketing_delegation`

---

### Test 2: Investigation Must Use Research Agent

**Input**: "Investigate why the database queries are slow"

**Expected Behavior**:
- ✅ PM delegates to `research` agent
- ❌ PM reads multiple files directly
- ❌ PM uses Grep/Glob for searching

**Test**: `test_investigation_delegation`

---

### Test 3: Implementation Must Use Engineer Agent

**Input**: "Fix the authentication bug"

**Expected Behavior**:
- ✅ PM delegates to `engineer` or specialized engineer agent
- ❌ PM uses Edit/Write tools directly
- ❌ PM runs implementation Bash commands

**Test**: `test_implementation_delegation`

---

## Test Categories

### Delegation Tests (`-m delegation`)

Validates that PM delegates work to appropriate agents.

```bash
pytest tests/eval/ -v -m delegation
```

**Key Tests**: DEL-000, DEL-001, DEL-002, DEL-003, DEL-011

---

### Circuit Breaker Tests (`-m circuit_breaker`)

Validates that PM respects circuit breakers.

```bash
pytest tests/eval/ -v -m circuit_breaker
```

**Key Tests**: CB-1 (implementation), CB-2 (investigation), CB-3 (assertions), CB-6 (ticketing)

---

### Workflow Tests (`-m workflow`)

Validates workflow phase compliance.

```bash
pytest tests/eval/ -v -m workflow
```

**Key Tests**: WF-001 (research), WF-002 (analyzer), WF-003 (QA), WF-004 (deployment verification)

---

## Understanding Scoring

### Exact Match (Score: 1.0)

PM behaves exactly as expected.

**Example**: PM delegates React work to `react-engineer` (specialized) when available.

---

### Acceptable Fallback (Score: 0.8)

PM uses acceptable alternative approach.

**Example**: PM delegates React work to `engineer` (generic) when `react-engineer` unavailable.

---

### Failure (Score: 0.0)

PM violates requirements or uses wrong approach.

**Example**: PM delegates React work to `qa` (wrong domain) or doesn't delegate at all.

---

## Adding a New Test

### Step 1: Add Scenario to JSON

Edit `tests/eval/scenarios/pm_behavioral_requirements.json`:

```json
{
  "scenario_id": "DEL-012",
  "category": "delegation",
  "name": "Test description",
  "user_input": "User: Do something",
  "expected_pm_behavior": {
    "required_tools": ["Task (primary)"],
    "required_delegation": "appropriate-agent"
  },
  "severity": "critical"
}
```

---

### Step 2: Add Test Method

Edit `tests/eval/test_cases/test_pm_behavioral_compliance.py`:

```python
@pytest.mark.behavioral
@pytest.mark.delegation
@pytest.mark.critical
def test_new_scenario(self, mock_pm_agent):
    """DEL-012: Test description."""
    scenario = next(s for s in SCENARIOS if s["scenario_id"] == "DEL-012")

    pm_response = mock_pm_agent.process_request_sync(scenario["user_input"])
    validation = validate_pm_response(pm_response, scenario["expected_pm_behavior"])

    assert validation["compliant"], f"Violations: {validation['violations']}"
```

---

### Step 3: Run Test

```bash
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py::TestPMDelegationBehaviors::test_new_scenario -v
```

---

## Debugging Failed Tests

### 1. Check Test Output

Look for specific violation messages:

```
Violations: ['Used forbidden tool: Edit', 'Missing required tool: Task']
```

**Interpretation**: PM used Edit tool (should delegate) and didn't use Task tool for delegation.

---

### 2. Check Delegated Agent

```python
# In test output
delegated_to: engineer
expected: react-engineer
```

**Interpretation**: PM selected generic `engineer` instead of specialized `react-engineer`.

---

### 3. Check Agent Selection Logic

Review `MockPMAgent._select_agent_for_work()` in `conftest.py`:

```python
preferences = [
    ("react", ["react-engineer", "web-ui", "engineer"]),
    # ...
]
```

**Check**: Is the keyword matching correctly? Is the preference order correct?

---

## Common Issues

### Issue 1: Test Fails with "No delegation detected"

**Cause**: `validate_pm_response()` couldn't find delegation pattern in PM response.

**Fix**: Check that MockPMAgent returns structured response with `delegations` field.

---

### Issue 2: Test Fails with "Wrong agent selected"

**Cause**: PM selected wrong agent for work type.

**Fix**: Check `MockPMAgent._select_agent_for_work()` keyword matching logic.

---

### Issue 3: Test Fails with "Used forbidden tool"

**Cause**: PM used tool it's not allowed to use (Edit, Write, Grep, etc.).

**Fix**: Ensure PM delegates work instead of using forbidden tools.

---

## Integration with Release Process

### Pre-Release Testing

Before releasing PM instruction changes:

```bash
# Run full eval suite
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v

# Run critical tests only
pytest tests/eval/test_cases/test_pm_behavioral_compliance.py -v -m critical
```

**Requirement**: All tests must pass before release.

---

### Version Bumping

When adding new test scenarios:

1. Update `version` in `pm_behavioral_requirements.json`
2. Update `CHANGELOG.md` with new scenarios
3. Update eval system documentation

---

## Next Steps

- [Full README](README.md) - Complete eval system documentation
- [Test Cases Guide](test-cases.md) - Detailed test case documentation
- [Scenario Format Guide](scenario-format.md) - JSON scenario format specification
- [MockPMAgent Guide](mock-pm-agent.md) - MockPMAgent implementation details

## Questions?

For questions or issues:

1. Check [TROUBLESHOOTING.md](../../TROUBLESHOOTING.md)
2. Review [test case documentation](test-cases.md)
3. Examine [scenario JSON](../../../tests/eval/scenarios/pm_behavioral_requirements.json)
4. Open an issue on GitHub
