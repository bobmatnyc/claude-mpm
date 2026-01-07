# Web-QA Agent MCP Tool Prioritization Tests

Comprehensive DeepEval test suite validating the web-qa agent's compliance with Playwright MCP prioritization guidelines.

## Overview

These tests ensure the web-qa agent correctly prioritizes browser automation tools according to the guidelines documented in `web-qa-mcp-browser-integration-2025-12-18.md`:

1. **Playwright MCP** (highest priority) - Use when available
2. **Chrome DevTools MCP** (fallback) - Use when Playwright unavailable
3. **Bash commands** (last resort) - Use only when no MCP tools available

Additionally, the tests validate:
- `browser_snapshot` is preferred over `browser_take_screenshot` for structural inspection
- Proper evidence collection from tool outputs
- Correct tool availability detection and fallback behavior

## Test Files

### Test Scenarios
**File**: `tests/eval/scenarios/web_qa_mcp_prioritization.json`

Contains 10 test scenarios covering:
- ✅ Playwright MCP prioritization (4 scenarios)
- ✅ Chrome DevTools fallback (1 scenario)
- ✅ Bash command fallback (1 scenario)
- ✅ Tool selection correctness (4 scenarios)

### Custom Metrics
**File**: `tests/eval/metrics/mcp_tool_prioritization.py`

Two custom DeepEval metrics:

#### `MCPToolPrioritizationMetric`
Validates MCP tool prioritization compliance.

**Scoring**:
- `1.0` - Perfect prioritization (Playwright when available)
- `0.8` - Good (Chrome DevTools, Playwright unavailable)
- `0.6` - Acceptable (Bash, no MCP available)
- `0.4` - Poor (Chrome DevTools when Playwright available)
- `0.2` - Bad (Bash when MCP available)
- `0.0` - Failed (wrong tools or no evidence)

**Checks**:
- Required tools used (must_use_tools)
- Forbidden tools avoided (must_not_use_tools)
- Playwright prioritized over Chrome DevTools
- Snapshot preferred over screenshot for inspection
- Bash avoided when MCP available
- Concrete evidence provided

#### `MCPToolAvailabilityMetric`
Validates tool availability detection and adaptation.

**Scoring**:
- `1.0` - Correctly identifies and adapts to available tools
- `0.5` - Partially correct
- `0.0` - Fails to detect tool availability

### Test Cases
**File**: `tests/eval/test_cases/test_web_qa_mcp_prioritization.py`

Contains 11 individual test methods plus parametrized tests.

## Running the Tests

### Install Dependencies

```bash
# Install eval dependencies
pip install -e ".[eval]"

# Or with uv
uv pip install -e ".[eval]"
```

### Run All Tests

```bash
# Run all web-qa MCP prioritization tests
pytest tests/eval/test_cases/test_web_qa_mcp_prioritization.py -v

# Run with detailed output
pytest tests/eval/test_cases/test_web_qa_mcp_prioritization.py -v -s
```

### Run by Severity

```bash
# Critical tests only (must be 100% compliant)
pytest tests/eval/test_cases/test_web_qa_mcp_prioritization.py -v -m critical

# High priority tests (80%+ compliance)
pytest tests/eval/test_cases/test_web_qa_mcp_prioritization.py -v -m high

# Medium priority tests (70%+ compliance)
pytest tests/eval/test_cases/test_web_qa_mcp_prioritization.py -v -m medium
```

### Run Specific Test

```bash
# Run single test method
pytest tests/eval/test_cases/test_web_qa_mcp_prioritization.py::TestWebQAMCPPrioritization::test_playwright_navigation_and_snapshot -v

# Run specific scenario by ID
pytest tests/eval/test_cases/test_web_qa_mcp_prioritization.py::test_all_scenarios[playwright_navigation_and_snapshot] -v
```

### Run Parametrized Tests

```bash
# Run all scenarios as parametrized tests
pytest tests/eval/test_cases/test_web_qa_mcp_prioritization.py::test_all_scenarios -v

# Run specific parametrized scenario
pytest tests/eval/test_cases/test_web_qa_mcp_prioritization.py::test_all_scenarios[snapshot_over_screenshot_priority] -v
```

## Test Scenarios

### Critical Scenarios (Must Pass)

These scenarios require **100% compliance** (score = 1.0):

1. **playwright_navigation_and_snapshot**
   - User input: "Test the login page at http://localhost:3000/login"
   - Must use: `browser_navigate`, `browser_snapshot`
   - Must avoid: Chrome DevTools, Bash

2. **snapshot_over_screenshot_priority**
   - User input: "Inspect the navigation menu structure"
   - Must use: `browser_snapshot` (NOT screenshot)
   - Must analyze semantic structure

3. **tool_availability_detection**
   - User input: "Test http://localhost:3000 for accessibility"
   - Must acknowledge when MCP tools unavailable
   - Must recommend proper setup

### High Priority Scenarios

These scenarios require **80%+ compliance**:

4. **playwright_console_error_monitoring**
   - Must use: `browser_console_messages`
   - Must avoid: Chrome DevTools console tools

5. **playwright_network_monitoring**
   - Must use: `browser_network_requests`
   - Must avoid: Chrome DevTools network tools

6. **playwright_interaction_tools**
   - Must use: `browser_type`, `browser_click`, `browser_fill_form`
   - Must avoid: Chrome DevTools interaction tools

7. **mixed_tool_scenario**
   - Must use Playwright for primary tasks
   - Can use Chrome DevTools only for performance profiling

### Medium Priority Scenarios

8. **chrome_devtools_fallback**
   - Validates fallback to Chrome DevTools when Playwright unavailable
   - Threshold: 80%

9. **performance_profiling**
   - Validates appropriate tool selection for performance testing
   - Threshold: 70%

### Low Priority Scenarios

10. **bash_last_resort_fallback**
    - Validates Bash usage only when no MCP available
    - Threshold: 60%

## Test Output

### Successful Test Example

```
tests/eval/test_cases/test_web_qa_mcp_prioritization.py::TestWebQAMCPPrioritization::test_playwright_navigation_and_snapshot PASSED

DeepEval Results:
- MCPToolPrioritizationMetric: 1.0 (PASSED)
  Reason: Perfect MCP tool prioritization
```

### Failed Test Example

```
tests/eval/test_cases/test_web_qa_mcp_prioritization.py::TestWebQAMCPPrioritization::test_playwright_navigation_and_snapshot FAILED

DeepEval Results:
- MCPToolPrioritizationMetric: 0.4 (FAILED)
  Reason: Tool prioritization violations: Used Chrome DevTools instead of Playwright: navigate_page; Missing required tool: browser_snapshot
```

## Extending the Tests

### Add New Scenario

1. Edit `tests/eval/scenarios/web_qa_mcp_prioritization.json`
2. Add new scenario object:

```json
{
  "id": "new_scenario_id",
  "category": "playwright_mcp_prioritization",
  "severity": "high",
  "description": "Test description",
  "user_input": "User request text",
  "context": {
    "available_tools": ["mcp__playwright__*"],
    "preferred_tools": ["mcp__playwright__browser_snapshot"]
  },
  "expected_behavior": {
    "must_use_tools": ["mcp__playwright__browser_snapshot"],
    "must_not_use_tools": ["Bash"]
  },
  "success_criteria": {
    "uses_playwright": true,
    "has_evidence": true
  }
}
```

3. Run the parametrized test:

```bash
pytest tests/eval/test_cases/test_web_qa_mcp_prioritization.py::test_all_scenarios[new_scenario_id] -v
```

### Add New Test Method

1. Edit `tests/eval/test_cases/test_web_qa_mcp_prioritization.py`
2. Add new test method to `TestWebQAMCPPrioritization` class:

```python
def test_my_new_scenario(self):
    """Test description."""
    scenario = get_scenario_by_id("new_scenario_id")

    test_case = LLMTestCase(
        input=scenario["user_input"],
        actual_output=self._generate_expected_response(scenario),
        context=[scenario["context"]],
    )

    metric = MCPToolPrioritizationMetric(threshold=0.9)
    assert_test(test_case, [metric])
```

## Integration with Real Agent

To test with actual web-qa agent responses:

1. Configure web-qa agent endpoint
2. Implement response capture
3. Run integration tests:

```bash
pytest tests/eval/test_cases/test_web_qa_mcp_prioritization.py -m integration
```

Currently, integration tests are skipped and require implementation.

## Troubleshooting

### Test Failures

**Symptom**: Tests fail with "Missing required tool"

**Solution**: Check that `_generate_expected_response()` includes all required tools from scenario's `must_use_tools` list.

**Symptom**: Tests fail with "Used forbidden tool"

**Solution**: Verify the expected response doesn't use tools from scenario's `must_not_use_tools` list.

### Metric Scoring

**Symptom**: Score lower than expected

**Solution**: Review `MCPToolPrioritizationMetric.measure()` to understand score adjustments:
- Missing required tool: -0.3
- Using forbidden tool: -0.4
- Using Chrome DevTools when Playwright available: -0.3
- Using screenshot instead of snapshot: -0.2
- Using Bash when MCP available: -0.4
- Missing evidence: -0.3

## CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
- name: Run Web-QA MCP Prioritization Tests
  run: |
    pytest tests/eval/test_cases/test_web_qa_mcp_prioritization.py \
      -v \
      -m "critical or high" \
      --tb=short
```

## Related Documentation

- **MCP Integration Guide**: `docs/_archive/2025-12-implementation/web-qa-mcp-browser-integration-2025-12-18.md`
- **Web-QA Agent**: `.claude/agents/web-qa.md`
- **DeepEval Framework**: `tests/eval/README.md`

## Support

For questions or issues:
1. Check test output for specific violation details
2. Review scenario JSON for expected behavior
3. Examine metric implementation in `mcp_tool_prioritization.py`
4. Consult MCP integration guide for tool usage patterns
