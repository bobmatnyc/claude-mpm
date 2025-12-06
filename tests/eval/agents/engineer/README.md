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

### Run All Engineer Tests

```bash
pytest tests/eval/agents/engineer/test_integration.py -v
```

**Output**: 30 tests (25 scenarios + 5 integrity checks)

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
```

### Run Specific Scenario

```bash
# Test MIN-E-001: Search-First Before Implementation
pytest tests/eval/agents/engineer/test_integration.py::TestEngineerCodeMinimization::test_scenario[MIN-E-001] -v

# Test CONS-E-003: Same Domain Consolidation
pytest tests/eval/agents/engineer/test_integration.py::TestEngineerConsolidation::test_scenario[CONS-E-003] -v
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

Add to `.github/workflows/deepeval.yml`:

```yaml
- name: Run Engineer Agent Tests
  run: |
    pytest tests/eval/agents/engineer/test_integration.py -v \
      --junitxml=test-results/engineer-agent.xml \
      --html=test-results/engineer-agent.html
```

### Expected Results

- **30 tests** should pass (25 scenarios + 5 integrity)
- **Duration**: ~1-2 seconds (mock responses, no LLM calls)
- **Coverage**: All Engineer Agent behavioral protocols

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

If a scenario test fails:

1. Check `metric.reason` in assertion error message
2. Compare `actual_output` against `success_criteria` in scenario JSON
3. Verify metric scoring components in metric implementation
4. Check threshold value is appropriate for metric

### Scenario Loading Errors

If scenario loading fails:

1. Verify `engineer_scenarios.json` is valid JSON
2. Check file path in `SCENARIOS_PATH` constant
3. Ensure all required fields are present in scenario
4. Run integrity tests: `pytest tests/eval/agents/engineer/test_integration.py::TestScenarioFileIntegrity -v`

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
