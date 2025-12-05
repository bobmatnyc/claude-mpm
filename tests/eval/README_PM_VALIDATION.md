# PM Behavior Validation Test Suite

## Overview

This test suite validates the PM instruction fixes (commit `0872411a`) that enforce strict ticketing delegation and prevent Circuit Breaker #6 violations.

**Purpose**: Ensure PM correctly delegates ALL ticketing operations to the ticketing agent instead of using WebFetch or mcp-ticketer tools directly.

## Background

### The Problem (Before Fix)

Before the instruction fixes, PM was violating Circuit Breaker #6 by:
- Using `WebFetch` directly on Linear/GitHub issue URLs
- Calling `mcp__mcp-ticketer__*` tools directly
- Not delegating ticketing operations to the ticketing agent

Example violation:
```
User: "verify https://linear.app/1m-hyperdev/issue/JJF-62"
PM: WebFetch(url="https://linear.app/...")  # ❌ WRONG
```

### The Fix (Commit 0872411a)

Updated PM instructions to:
1. **MANDATE** delegation of all ticketing operations
2. **FORBID** direct use of WebFetch on ticket URLs
3. **FORBID** direct use of mcp-ticketer tools
4. **REQUIRE** agent attribution in responses

Correct behavior:
```
User: "verify https://linear.app/1m-hyperdev/issue/JJF-62"
PM: Task(agent="ticketing", task="Verify Linear issue JJF-62")  # ✅ CORRECT
```

## Test Strategy

### Dual Testing Approach

This suite uses a unique **dual testing approach** with simulated responses:

1. **Compliance Mode (default)**: Test that valid delegation passes
   - Uses compliant responses from `simulate_compliant_response()`
   - Should PASS all tests (score = 1.0)
   - Validates PM behavior is correct

2. **Violation Mode (--use-violations)**: Test that detection works
   - Uses violation responses from `simulate_violation_response()`
   - Should FAIL all tests (score < 1.0)
   - Validates metrics can detect violations

### Why This Approach?

- **Deterministic**: No LLM variability in test results
- **Fast**: No API calls, instant execution
- **Repeatable**: Same responses every time
- **Educational**: Clear before/after comparison
- **Detection Verification**: Proves metrics catch violations

## Test Scenarios

### 1. Linear URL Delegation Fix (`linear_url_delegation_fix`)

**Input**: `"verify https://linear.app/1m-hyperdev/issue/JJF-62"`

**Correct Behavior (After Fix)**:
```python
Task(
    agent="ticketing",
    task="Verify Linear issue JJF-62",
    context="https://linear.app/1m-hyperdev/issue/JJF-62"
)
```

**Violation (Before Fix)**:
```python
WebFetch(url="https://linear.app/1m-hyperdev/issue/JJF-62")  # ❌
```

### 2. Ticket ID Status Check (`ticket_id_status_check`)

**Input**: `"what's the status of MPM-456?"`

**Correct**: Delegate to ticketing agent
**Violation**: Call `mcp__mcp-ticketer__ticket` directly

### 3. Create Ticket Request (`create_ticket_request`)

**Input**: `"create a ticket for fixing authentication bug"`

**Correct**: Delegate ticket creation to ticketing agent
**Violation**: Call `mcp__mcp-ticketer__ticket` directly

### 4. GitHub Issue URL (`github_issue_url`)

**Input**: `"check https://github.com/bobmatnyc/claude-mpm/issues/42"`

**Correct**: Delegate to ticketing agent
**Violation**: Use WebFetch on GitHub URL

### 5. Ticket Search Query (`ticket_search_query`)

**Input**: `"search for all open tickets tagged with 'authentication'"`

**Correct**: Delegate search to ticketing agent
**Violation**: Call `ticket_search` directly

### 6. Ticket Update Request (`ticket_update_request`)

**Input**: `"update ticket MPM-789 to mark it as in_progress"`

**Correct**: Delegate update to ticketing agent
**Violation**: Call ticket update tools directly

## File Structure

```
tests/eval/
├── scenarios/
│   └── pm_behavior_validation.json       # Test scenario definitions
├── test_cases/
│   └── test_pm_behavior_validation.py    # Main test implementation
├── utils/
│   └── pm_response_simulator.py          # Response simulation
├── run_pm_validation.py                  # Test runner script
└── README_PM_VALIDATION.md              # This file
```

## Usage

### Quick Start

```bash
# Test PM compliance (should pass)
python tests/eval/run_pm_validation.py

# Test violation detection (should fail, proving detection works)
python tests/eval/run_pm_validation.py --use-violations

# Verbose output
python tests/eval/run_pm_validation.py -v
```

### Running Individual Tests

```bash
# Test specific scenario
pytest tests/eval/test_cases/test_pm_behavior_validation.py::TestPMBehaviorValidation::test_linear_url_delegation_fixed -v

# Test all scenarios
pytest tests/eval/test_cases/test_pm_behavior_validation.py -m integration -v

# Test with violation responses
pytest tests/eval/test_cases/test_pm_behavior_validation.py -m integration --use-violation-responses -v
```

### Command-Line Options

- `--use-violations`: Use violation responses (tests detection)
- `-v`: Verbose output
- `--test <scenario_id>`: Run specific test
- `--report`: Generate HTML report
- `--pytest-args "<args>"`: Pass additional pytest arguments

## Expected Results

### Compliance Mode (Default)

```
PM Behavior Validation Summary
======================================================================
Mode: COMPLIANCE TESTING
Total Scenarios: 6
----------------------------------------------------------------------
✅ PASS       Linear URL Verification Delegation           1.00
✅ PASS       Ticket ID Status Check                       1.00
✅ PASS       Create Ticket Request                        1.00
✅ PASS       GitHub Issue URL Verification                1.00
✅ PASS       Ticket Search Query                          1.00
✅ PASS       Ticket Update Request                        1.00
======================================================================

Pass Rate: 6/6 (100.0%)
Compliance Rate: 100.0% (should be 100%)
```

### Violation Mode (--use-violations)

```
PM Behavior Validation Summary
======================================================================
Mode: VIOLATION DETECTION
Total Scenarios: 6
----------------------------------------------------------------------
✅ DETECTED   Linear URL Verification Delegation           0.00
✅ DETECTED   Ticket ID Status Check                       0.00
✅ DETECTED   Create Ticket Request                        0.00
✅ DETECTED   GitHub Issue URL Verification                0.00
✅ DETECTED   Ticket Search Query                          0.00
✅ DETECTED   Ticket Update Request                        0.00
======================================================================

Pass Rate: 6/6 (100.0%)
Detection Rate: 100.0% (should be 100%)
```

## Metrics Used

### 1. TicketingDelegationMetric

**Purpose**: Detect forbidden tool usage and missing delegation

**Checks**:
- ✅ PM uses `Task` tool for delegation
- ✅ PM specifies correct agent (`ticketing`)
- ❌ PM does NOT use `WebFetch` on ticket URLs
- ❌ PM does NOT use `mcp__mcp-ticketer__*` tools
- ✅ PM reports with agent attribution

**Scoring**:
- `1.0`: Perfect compliance (correct delegation)
- `0.0`: Violation detected (forbidden tool usage)

**Threshold**: `1.0` (zero tolerance for violations)

### 2. InstructionFaithfulnessMetric

**Purpose**: Validate overall instruction compliance

**Checks**:
- PM follows delegation protocol
- PM provides proper context
- PM reports results correctly

**Threshold**: `0.85` (85% minimum compliance)

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: PM Behavior Validation

on: [push, pull_request]

jobs:
  validate-pm-behavior:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt

      - name: Test PM Compliance
        run: |
          python tests/eval/run_pm_validation.py

      - name: Test Violation Detection
        run: |
          python tests/eval/run_pm_validation.py --use-violations
```

## Troubleshooting

### Test Fails in Compliance Mode

**Symptom**: Tests fail when running without `--use-violations`

**Cause**: PM is still using forbidden tools directly

**Solution**:
1. Check PM instruction deployment
2. Verify Circuit Breaker #6 is active
3. Review PM agent logs for tool usage
4. Check if simulated responses need updating

### Test Passes in Violation Mode

**Symptom**: Tests pass when running with `--use-violations`

**Cause**: Metrics are NOT detecting violations properly

**Solution**:
1. Review metric implementation
2. Check forbidden tool patterns
3. Verify detection logic in metrics
4. Add debug logging to metrics

### Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'deepeval'`

**Solution**:
```bash
pip install -r requirements-dev.txt
# or
pip install deepeval pytest
```

## Development

### Adding New Scenarios

1. **Add scenario to `pm_behavior_validation.json`**:
   ```json
   {
     "id": "new_scenario",
     "name": "New Test Scenario",
     "input": "user input text",
     "expected_behavior": "PM should delegate...",
     "forbidden_tools": ["WebFetch"],
     "required_delegation": "ticketing"
   }
   ```

2. **Add responses to `pm_response_simulator.py`**:
   ```python
   # In simulate_compliant_response()
   "new_scenario": {
       "content": "PM correct response...",
       "tools_used": ["Task"],
       "delegations": [{"agent": "ticketing", ...}]
   }

   # In simulate_violation_response()
   "new_scenario": {
       "content": "PM violation response...",
       "tools_used": ["WebFetch"],
       "forbidden_tools_used": ["WebFetch"]
   }
   ```

3. **Run tests**:
   ```bash
   python tests/eval/run_pm_validation.py --test new_scenario -v
   ```

### Updating Metrics

Metrics are defined in:
- `tests/eval/metrics/delegation_correctness.py`
- `tests/eval/metrics/instruction_faithfulness.py`

After updating metrics, verify detection:
```bash
python tests/eval/run_pm_validation.py --use-violations -v
```

## Related Documentation

- **Circuit Breakers**: `src/claude_mpm/agents/templates/circuit-breakers.md`
- **PM Instructions**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md`
- **Verification Report**: `docs/research/release-5.0.9-verification-report.md`
- **Integration Testing**: `tests/eval/README_INTEGRATION.md`

## Success Criteria

✅ **Compliance Mode**: All tests pass (6/6 = 100%)
✅ **Violation Mode**: All tests fail (6/6 = 100% detection)
✅ **Metrics**: Provide clear reasons for pass/fail
✅ **Reports**: Generate actionable output

## Future Enhancements

1. **Real PM Agent Integration**: Replace simulated responses with actual PM agent calls
2. **Performance Benchmarking**: Track response time improvements
3. **Regression Detection**: Compare with golden responses
4. **Auto-reporting**: Generate release reports automatically
5. **A/B Testing**: Compare instruction versions

## Maintenance

### When to Update

- **After PM instruction changes**: Rebuild and re-test
- **New ticket platforms added**: Add new scenarios
- **Metric improvements**: Validate detection still works
- **Bug fixes**: Add regression test for the bug

### Health Check

Run full validation before releases:
```bash
# Quick validation
python tests/eval/run_pm_validation.py

# Full validation with reports
python tests/eval/run_pm_validation.py -v --report

# Verify detection
python tests/eval/run_pm_validation.py --use-violations
```

## Contact

For questions or issues with this test suite:
- Open issue in repository
- Reference commit `0872411a` (PM instruction fixes)
- Tag with `testing` and `circuit-breaker-6`

---

**Version**: 1.0.0
**Created**: 2025-12-05
**Last Updated**: 2025-12-05
**Author**: Claude MPM Framework Team
