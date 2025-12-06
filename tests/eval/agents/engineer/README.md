# Engineer Agent Test Harness

DeepEval integration test harness for validating Engineer Agent behaviors against predefined scenarios and custom metrics.

## Overview

This test harness validates **25 Engineer Agent scenarios** across **4 behavioral categories**:

1. **Code Minimization Mandate** (10 scenarios: MIN-E-001 to MIN-E-010)
2. **Consolidation & Duplicate Elimination** (7 scenarios: CONS-E-001 to CONS-E-007)
3. **Anti-Pattern Avoidance** (5 scenarios: ANTI-E-001 to ANTI-E-005)
4. **Test Process Management** (3 scenarios: PROC-E-001 to PROC-E-003)

## Test Structure

### Files

- **`test_integration.py`**: Main test harness with all 25 scenario tests + 5 integrity tests
- **`__init__.py`**: Package initialization (minimal)

### Dependencies

- **Scenarios**: `tests/eval/scenarios/engineer/engineer_scenarios.json` (25 scenarios)
- **Metrics**: `tests/eval/metrics/engineer/` (3 custom metrics)
  - `CodeMinimizationMetric` (threshold: 0.8)
  - `ConsolidationMetric` (threshold: 0.85)
  - `AntiPatternDetectionMetric` (threshold: 0.9)

## Running Tests

### Quick Start

```bash
# Run all Engineer Agent tests (recommended)
pytest tests/eval/agents/engineer/ -v

# Run with detailed output
pytest tests/eval/agents/engineer/ -v --tb=short

# Run with coverage report
pytest tests/eval/agents/engineer/ -v --cov=tests/eval/metrics/engineer --cov-report=term-missing
```

**Expected Output**: 39 tests (9 metric + 25 scenarios + 5 integration)

### Run All Engineer Tests

```bash
pytest tests/eval/agents/engineer/test_integration.py -v
```

**Output**: 30 tests (25 scenarios + 5 integrity checks)

### Run Metric Tests

```bash
# All metric tests
pytest tests/eval/metrics/engineer/ -v

# Specific metric
pytest tests/eval/metrics/engineer/test_code_minimization.py -v
pytest tests/eval/metrics/engineer/test_consolidation.py -v
pytest tests/eval/metrics/engineer/test_anti_pattern.py -v
```

**Output**: 9 tests (3 per metric)

### Run Specific Category

```bash
# Code Minimization tests (10 scenarios)
pytest tests/eval/agents/engineer/test_integration.py::TestEngineerCodeMinimization -v

# Consolidation tests (7 scenarios)
pytest tests/eval/agents/engineer/test_integration.py::TestEngineerConsolidation -v

# Anti-Pattern tests (5 scenarios)
pytest tests/eval/agents/engineer/test_integration.py::TestEngineerAntiPattern -v

# Process Management tests (3 scenarios)
pytest tests/eval/agents/engineer/test_integration.py::TestEngineerProcessManagement -v

# Integration workflows (5 tests)
pytest tests/eval/agents/engineer/test_integration.py::TestEngineerWorkflows -v
```

### Run Specific Scenario

```bash
# Test MIN-E-001: Search-First Before Implementation
pytest tests/eval/agents/engineer/test_integration.py::TestEngineerCodeMinimization::test_scenario[MIN-E-001] -v

# Test CONS-E-003: Same Domain Consolidation
pytest tests/eval/agents/engineer/test_integration.py::TestEngineerConsolidation::test_scenario[CONS-E-003] -v

# Test workflow: Code minimization workflow
pytest tests/eval/agents/engineer/test_integration.py::TestEngineerWorkflows::test_code_minimization_workflow -v
```

### Run Integrity Checks Only

```bash
pytest tests/eval/agents/engineer/test_integration.py::TestScenarioFileIntegrity -v
```

**Output**: 5 tests (file structure validation)

## Test Categories

### 1. Code Minimization Mandate (10 tests)

Tests validate the Engineer Agent's adherence to code minimization principles:

| Scenario ID | Name | Focus |
|-------------|------|-------|
| MIN-E-001 | Search-First Before Implementation | Vector search/grep before coding |
| MIN-E-002 | Extend Existing vs Create New | Prefer extending over new files |
| MIN-E-003 | LOC Delta Reporting | Report net lines added/removed |
| MIN-E-004 | Reuse Rate Calculation | Track % of existing code leveraged |
| MIN-E-005 | Consolidation Opportunities | Identify duplicate code |
| MIN-E-006 | Config vs Code Approach | Prefer configuration-driven solutions |
| MIN-E-007 | Function Extraction Over Duplication | Extract shared logic |
| MIN-E-008 | Shared Utility Creation | Build reusable components |
| MIN-E-009 | Data-Driven Implementation | Use data structures over code |
| MIN-E-010 | Zero Net LOC Feature Addition | Add features with ≤0 LOC delta |

**Metric**: `CodeMinimizationMetric` (threshold: 0.8)

### 2. Consolidation & Duplicate Elimination (7 tests)

Tests validate duplicate detection and consolidation protocols:

| Scenario ID | Name | Focus |
|-------------|------|-------|
| CONS-E-001 | Duplicate Detection via Vector Search | Use vector search to find similar code |
| CONS-E-002 | Consolidation Decision Quality | Apply similarity thresholds correctly |
| CONS-E-003 | Same Domain Consolidation | Merge >80% similar same-domain code |
| CONS-E-004 | Different Domain Extraction | Extract >50% similar cross-domain logic |
| CONS-E-005 | Single-Path Enforcement | One active implementation per feature |
| CONS-E-006 | Session Artifact Cleanup | Remove _old, _v2, _backup files |
| CONS-E-007 | Reference Update After Consolidation | Update all imports/calls |

**Metric**: `ConsolidationMetric` (threshold: 0.85)

### 3. Anti-Pattern Avoidance (5 tests)

Tests validate avoidance of common engineering anti-patterns:

| Scenario ID | Name | Focus |
|-------------|------|-------|
| ANTI-E-001 | No Mock Data in Production | Mock data only in tests |
| ANTI-E-002 | No Silent Fallback Behavior | Explicit error handling |
| ANTI-E-003 | Explicit Error Propagation | Log + raise, not catch + ignore |
| ANTI-E-004 | Acceptable Config Defaults | Justify configuration fallbacks |
| ANTI-E-005 | Graceful Degradation with Logging | Document degradation with logs |

**Metric**: `AntiPatternDetectionMetric` (threshold: 0.9)

### 4. Test Process Management (3 tests)

Tests validate proper test execution and debugging protocols:

| Scenario ID | Name | Focus | Metric |
|-------------|------|-------|--------|
| PROC-E-001 | Non-Interactive Test Execution | Use CI=true, no watch mode | AntiPatternDetectionMetric |
| PROC-E-002 | Process Cleanup Verification | Verify no orphaned processes | AntiPatternDetectionMetric |
| PROC-E-003 | Debug-First Protocol | Identify root cause before fixing | CodeMinimizationMetric |

## Test Execution Flow

Each test follows this pattern:

```python
1. Load scenario from engineer_scenarios.json by scenario_id
2. Extract compliant mock response from scenario
3. Create LLMTestCase with user_request as input, compliant response as output
4. Instantiate appropriate metric (CodeMinimization, Consolidation, or AntiPattern)
5. Measure metric score against test case
6. Assert score >= metric.threshold (0.8, 0.85, or 0.9)
```

## Metrics Thresholds

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| CodeMinimizationMetric | 0.8 (80%) | 5 scoring components, weighted average |
| ConsolidationMetric | 0.85 (85%) | 4 scoring components, higher precision needed |
| AntiPatternDetectionMetric | 0.9 (90%) | Binary checks (pass/fail), strict enforcement |

## Scenario JSON Structure

Each scenario in `engineer_scenarios.json` contains:

```json
{
  "scenario_id": "MIN-E-001",
  "name": "Search-First Before Implementation",
  "category": "code_minimization",
  "priority": "critical",
  "description": "Engineer MUST search for existing code...",
  "input": {
    "user_request": "Add a new validation function...",
    "context": "Python codebase with existing validators...",
    "codebase_size": "5000 LOC"
  },
  "expected_behavior": {
    "should_do": [...],
    "should_not_do": [...],
    "required_tools": [...],
    "evidence_required": true
  },
  "success_criteria": [...],
  "failure_indicators": [...],
  "metrics": {
    "CodeMinimizationMetric": {
      "threshold": 0.8,
      "description": "Must demonstrate search-first behavior"
    }
  },
  "mock_response": {
    "compliant": "I'll search for existing validation code...",
    "non_compliant": "I'll create a new email validation function..."
  }
}
```

## Continuous Integration

### CI Configuration

The Engineer Agent tests are integrated into `.github/workflows/deepeval-tests.yml`:

```yaml
deepeval-engineer-agent:
  name: Engineer Agent DeepEval Tests
  runs-on: ubuntu-latest

  steps:
    - name: Run Engineer Agent metric tests
      run: pytest tests/eval/metrics/engineer/ -v --tb=short

    - name: Run Engineer Agent scenario tests
      run: pytest tests/eval/agents/engineer/test_integration.py -v --tb=short -k "not TestEngineerWorkflows"

    - name: Run Engineer Agent workflow integration tests
      run: pytest tests/eval/agents/engineer/test_integration.py::TestEngineerWorkflows -v --tb=short --timeout=300
```

### Expected CI Results

- **39 tests total**: 9 metric + 25 scenarios + 5 integration
- **Duration**: ~2-3 seconds (mock responses, no LLM calls)
- **Coverage**: 100% of Engineer Agent behavioral protocols
- **Timeout**: 300s for integration workflows

### Test Execution Order

1. **Metric Tests** (9 tests): Unit tests for custom metrics
2. **Scenario Tests** (25 tests): Behavioral validation tests
3. **Integration Tests** (5 tests): Multi-step workflow tests

## Extending the Test Harness

### Adding New Scenarios

1. Add scenario to `tests/eval/scenarios/engineer/engineer_scenarios.json`
2. Update `total_scenarios` count
3. Update category count in `categories` section
4. Add scenario_id to appropriate `@pytest.mark.parametrize` list in `test_integration.py`

### Adding New Metrics

1. Create metric in `tests/eval/metrics/engineer/{metric_name}.py`
2. Export from `tests/eval/metrics/engineer/__init__.py`
3. Add metric fixture to test class
4. Apply metric in appropriate test method

## Troubleshooting

### Test Failures

**Scenario Test Failure**:

If a scenario test fails with metric score below threshold:

```bash
AssertionError: CodeMinimizationMetric score 0.65 below threshold 0.8
Reason: Missing search-first behavior (vector search/grep not found)
```

**Debug Steps**:
1. Check `metric.reason` in assertion error message for specific failure reason
2. Compare `actual_output` (mock response) against `success_criteria` in scenario JSON
3. Verify metric scoring logic in `tests/eval/metrics/engineer/{metric_name}.py`
4. Check if threshold is calibrated correctly for the scenario

**Metric Test Failure**:

If a metric unit test fails:

```bash
# Run specific metric with verbose output
pytest tests/eval/metrics/engineer/test_code_minimization.py::test_measure_perfect_score -vv

# Check metric scoring components
pytest tests/eval/metrics/engineer/ -v --tb=long
```

**Integration Test Failure**:

If integration workflow test fails:

```bash
# Run with full traceback
pytest tests/eval/agents/engineer/test_integration.py::TestEngineerWorkflows::test_code_minimization_workflow -vv --tb=long

# Check workflow step execution
pytest tests/eval/agents/engineer/test_integration.py::TestEngineerWorkflows -v --capture=no
```

### Scenario Loading Errors

**JSON Parsing Error**:

```bash
json.decoder.JSONDecodeError: Expecting ',' delimiter: line 145 column 5
```

**Fix**:
1. Verify `engineer_scenarios.json` is valid JSON (use `python -m json.tool < engineer_scenarios.json`)
2. Check file path in `SCENARIOS_PATH` constant matches actual location
3. Ensure all required fields are present in scenario (see scenario structure in README)
4. Run integrity tests: `pytest tests/eval/agents/engineer/test_integration.py::TestScenarioFileIntegrity -v`

### Common Issues

**Issue**: Tests pass locally but fail in CI

**Cause**: Different Python versions or missing dependencies

**Fix**:
```bash
# Match CI environment
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[eval,dev]"
pytest tests/eval/agents/engineer/ -v
```

---

**Issue**: Import errors for custom metrics

**Cause**: Metrics not properly exported from `__init__.py`

**Fix**:
```bash
# Verify metrics are exported
python -c "from tests.eval.metrics.engineer import CodeMinimizationMetric, ConsolidationMetric, AntiPatternDetectionMetric"

# Check __init__.py exports
cat tests/eval/metrics/engineer/__init__.py
```

---

**Issue**: Scenario count mismatch (expected 25, got X)

**Cause**: Scenarios missing from JSON or not added to test parameterization

**Fix**:
```bash
# Count scenarios in JSON
python -c "import json; data = json.load(open('tests/eval/scenarios/engineer/engineer_scenarios.json')); print(f'Total: {data[\"total_scenarios\"]}')"

# Verify all scenario IDs in test_integration.py
grep "@pytest.mark.parametrize" tests/eval/agents/engineer/test_integration.py
```

---

**Issue**: Timeout on integration tests

**Cause**: Mock responses too complex or workflow steps too slow

**Fix**:
```bash
# Increase timeout for specific test
pytest tests/eval/agents/engineer/test_integration.py::TestEngineerWorkflows::test_slow_workflow --timeout=600

# Or run without timeout
pytest tests/eval/agents/engineer/test_integration.py::TestEngineerWorkflows --timeout=0
```

### Getting Help

**Debugging Checklist**:
- [ ] Verify Python version (3.12+ required)
- [ ] Check all dependencies installed: `pip install -e ".[eval,dev]"`
- [ ] Run integrity tests first: `pytest tests/eval/agents/engineer/test_integration.py::TestScenarioFileIntegrity -v`
- [ ] Validate JSON: `python -m json.tool < tests/eval/scenarios/engineer/engineer_scenarios.json > /dev/null`
- [ ] Check metric exports: `python -c "from tests.eval.metrics.engineer import *"`
- [ ] Run single test with full output: `pytest <test_path> -vv --tb=long --capture=no`

**Reporting Issues**:
- Include full error message and traceback
- Specify Python version and OS
- Provide failing test command
- Attach relevant log output

## Integration with DeepEval Framework

This test harness uses DeepEval's:

- **`LLMTestCase`**: Container for input/output pairs
- **`BaseMetric`**: Custom metric base class
- **`.measure()`**: Metric scoring interface
- **`.threshold`**: Pass/fail threshold (0.0-1.0)
- **`.reason`**: Detailed failure explanation

**Note**: These are unit tests with mock responses. For live LLM evaluation, integrate with DeepEval's dataset evaluation features.

## References

- **Scenarios**: [tests/eval/scenarios/engineer/engineer_scenarios.json](../../scenarios/engineer/engineer_scenarios.json)
- **Metrics**: [tests/eval/metrics/engineer/](../../metrics/engineer/)
- **Engineer Agent Instructions**: Source instructions that these tests validate
- **DeepEval Docs**: https://docs.confident-ai.com/

---

**Last Updated**: 2025-12-06 (Sprint 3, Phase 2)
**Total Tests**: 30 (25 scenarios + 5 integrity checks)
**Coverage**: 100% of Engineer Agent behavioral protocols
