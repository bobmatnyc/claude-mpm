# QA Agent DeepEval Test Harness

Integration tests for QA Agent behaviors across 20 scenarios in 4 categories.

## Test Categories

### 1. Test Execution Safety (7 scenarios)
**TST-QA-001 to TST-QA-007**

Validates safe test execution practices:
- CI mode usage (CI=true npm test)
- No watch mode (NEVER uses vitest/jest watch)
- Package.json inspection before tests
- Process cleanup verification
- Timeout handling
- Output capture and reporting

**Metric**: `TestExecutionSafetyMetric` (threshold: 1.0 - strict)

### 2. Memory-Efficient Testing (6 scenarios)
**MEM-QA-001 to MEM-QA-006**

Validates memory-efficient testing patterns:
- File read limits (3-5 files max)
- Grep-based test discovery
- Representative test sampling
- Critical path focus
- Coverage tool usage (no manual calculation)

**Metric**: `CoverageQualityMetric` (threshold: 0.85)

### 3. Process Management (4 scenarios)
**PROC-QA-001 to PROC-QA-004**

Validates process lifecycle management:
- Pre-flight checks before test execution
- Post-execution verification
- Hanging process detection
- Orphaned process cleanup

**Metric**: `ProcessManagementMetric` (threshold: 0.9)

### 4. Coverage Analysis (3 scenarios)
**COV-QA-001 to COV-QA-003**

Validates coverage analysis practices:
- Coverage report analysis
- Critical path identification
- High-impact test prioritization

**Metric**: `CoverageQualityMetric` (threshold: 0.85-0.9)

## Running Tests

### Run All QA Agent Tests
```bash
pytest tests/eval/agents/qa/test_integration.py -v
```

### Run Specific Category
```bash
# Test execution safety
pytest tests/eval/agents/qa/test_integration.py::TestQATestExecutionSafety -v

# Memory-efficient testing
pytest tests/eval/agents/qa/test_integration.py::TestQAMemoryEfficientTesting -v

# Process management
pytest tests/eval/agents/qa/test_integration.py::TestQAProcessManagement -v

# Coverage analysis
pytest tests/eval/agents/qa/test_integration.py::TestQACoverageAnalysis -v
```

### Run Specific Scenario
```bash
# CI mode enforcement
pytest tests/eval/agents/qa/test_integration.py::TestQATestExecutionSafety::test_scenario[TST-QA-001] -v

# Watch mode detection
pytest tests/eval/agents/qa/test_integration.py::TestQATestExecutionSafety::test_scenario[TST-QA-002] -v

# Pre-flight checks
pytest tests/eval/agents/qa/test_integration.py::TestQAProcessManagement::test_scenario[PROC-QA-001-1.0] -v
```

### Run Integration Workflow Tests
```bash
# All workflow tests (slow)
pytest tests/eval/agents/qa/test_integration.py::TestQAWorkflows -v -m slow

# Specific workflow
pytest tests/eval/agents/qa/test_integration.py::TestQAWorkflows::test_qa_ci_mode_enforcement -v
```

### Run with DeepEval Reporting
```bash
# Generate DeepEval test report
pytest tests/eval/agents/qa/test_integration.py -v --deepeval

# Run with coverage
pytest tests/eval/agents/qa/test_integration.py --cov=tests.eval.metrics.qa --cov-report=html
```

## Scenario Descriptions

### Test Execution Safety Scenarios

| ID | Name | Description | Threshold |
|----|------|-------------|-----------|
| TST-QA-001 | CI Mode Usage | Must use CI=true for JavaScript tests | 1.0 |
| TST-QA-002 | No Watch Mode | NEVER use watch mode (memory leaks) | 1.0 |
| TST-QA-003 | Explicit Run Mode | Must use `vitest run` not `vitest` | 1.0 |
| TST-QA-004 | Package.json Inspection | Check package.json BEFORE running tests | 1.0 |
| TST-QA-005 | Process Cleanup | Verify process cleanup with ps aux | 1.0 |
| TST-QA-006 | Timeout Handling | Handle test timeouts properly | 0.9 |
| TST-QA-007 | Output Capture | Capture and report test output | 0.8 |

### Memory-Efficient Testing Scenarios

| ID | Name | Description | Threshold |
|----|------|-------------|-----------|
| MEM-QA-001 | File Read Limits | Max 3-5 files read for test analysis | 0.85 |
| MEM-QA-002 | Grep Discovery | Use grep for test discovery (not file reads) | 0.85 |
| MEM-QA-003 | No Full Reads | Don't read all test files | 0.85 |
| MEM-QA-004 | Representative Sampling | Sample 3-5 representative files | 0.85 |
| MEM-QA-005 | Critical Path Focus | Focus on uncovered critical paths | 0.85 |
| MEM-QA-006 | Coverage Tools | Use coverage tools (not manual calc) | 0.85 |

### Process Management Scenarios

| ID | Name | Description | Threshold |
|----|------|-------------|-----------|
| PROC-QA-001 | Pre-Flight Checks | Inspect package.json, check processes | 1.0 |
| PROC-QA-002 | Post-Execution Verify | Verify clean process state after tests | 1.0 |
| PROC-QA-003 | Hanging Detection | Detect hanging test processes | 0.8 |
| PROC-QA-004 | Orphaned Cleanup | Clean up orphaned node/vitest processes | 1.0 |

### Coverage Analysis Scenarios

| ID | Name | Description | Threshold |
|----|------|-------------|-----------|
| COV-QA-001 | Coverage Report Analysis | Analyze coverage reports, identify gaps | 0.9 |
| COV-QA-002 | Critical Path ID | Identify uncovered critical paths | 0.8 |
| COV-QA-003 | High-Impact Prioritization | Prioritize high-impact tests over 100% | 0.8 |

## Integration Workflow Tests

### 1. test_qa_ci_mode_enforcement
**Full CI mode workflow validation**

Combines:
- TST-QA-001: CI Mode Usage
- TST-QA-004: Package.json Inspection

Flow:
1. Check package.json → Detect watch mode risk
2. Use CI=true override → Execute tests
3. Verify output → Process cleanup

Threshold: 1.0 (strict)

### 2. test_qa_watch_mode_detection
**Watch mode prevention and detection**

Combines:
- TST-QA-002: No Watch Mode
- TST-QA-003: Explicit Run Mode

Flow:
1. Detect watch mode intent → Block execution
2. Suggest safe alternative → Document why forbidden

Threshold: 1.0 (strict)

### 3. test_qa_process_cleanup
**Complete process management workflow**

Combines:
- PROC-QA-001: Pre-Flight Checks
- PROC-QA-002: Post-Execution Verification
- PROC-QA-004: Orphaned Cleanup

Flow:
1. Pre-flight check → Execute tests
2. Post-execution verify → Clean orphaned
3. Final verification

Threshold: 0.9

### 4. test_qa_coverage_analysis
**Coverage tool usage and critical path focus**

Combines:
- COV-QA-001: Coverage Report Analysis
- COV-QA-002: Critical Path Identification
- COV-QA-003: High-Impact Prioritization

Flow:
1. Run coverage tool → Analyze report
2. Identify critical paths → Prioritize tests

Threshold: 0.85

### 5. test_qa_memory_efficiency
**Memory-efficient testing approach**

Combines:
- MEM-QA-001: File Read Limits
- MEM-QA-002: Grep Discovery
- MEM-QA-004: Representative Sampling

Flow:
1. Use grep → Sample representative tests
2. Coverage tools → Avoid exhaustive reads

Threshold: 0.85

## Troubleshooting

### Test Failures

**TestExecutionSafetyMetric failures**:
- **Watch mode detected**: Response uses `--watch` or similar
- **No CI mode**: Missing `CI=true` or `vitest run`
- **No pre-flight**: Doesn't inspect package.json before tests
- **No cleanup**: Missing `ps aux` verification

**CoverageQualityMetric failures**:
- **No coverage tool**: Missing `pytest --cov` or equivalent
- **No critical path focus**: Doesn't prioritize uncovered critical code
- **Memory inefficient**: Reads too many files (>5)
- **No grep usage**: Doesn't use grep for test discovery

**ProcessManagementMetric failures**:
- **No pre-flight**: Doesn't check configuration before tests
- **No post-verify**: Doesn't verify process state after tests
- **No cleanup**: Doesn't kill orphaned processes

### Common Issues

**Threshold too strict**:
```python
# Relax threshold if needed (but justify)
metric = TestExecutionSafetyMetric(threshold=0.9)  # Instead of 1.0
```

**Scenario file not found**:
```bash
# Verify scenarios file exists
ls -la tests/eval/scenarios/qa/qa_scenarios.json
```

**Import errors**:
```bash
# Ensure metrics are installed
pytest tests/eval/metrics/qa/ -v
```

## Metrics Deep Dive

### TestExecutionSafetyMetric

**Scoring Algorithm** (weighted):
- Pre-Flight Check (30%): Inspects package.json
- CI Mode Usage (40%): Uses CI=true or equivalent
- No Watch Mode (20%): NEVER uses watch mode
- Process Cleanup (10%): Checks for orphaned processes

**CRITICAL**: Watch mode detection = automatic 0.0 score

**Patterns Detected**:
- Pre-flight: `package.json`, `inspect`, `before running`
- CI Mode: `CI=true`, `vitest run`, `jest --ci`
- Watch Mode (FORBIDDEN): `--watch`, `vitest` without `run`
- Cleanup: `ps aux`, `process`, `cleanup`, `orphaned`

### CoverageQualityMetric

**Scoring Algorithm** (weighted):
- Coverage Tool Usage (35%): Uses coverage tools
- Critical Path Focus (30%): Prioritizes uncovered critical paths
- Memory-Efficient Analysis (20%): Grep, limited file reads
- High-Impact Prioritization (15%): Focuses on important tests

**Patterns Detected**:
- Coverage Tools: `--coverage`, `nyc`, `istanbul`, `pytest-cov`
- Critical Path: `critical path`, `uncovered`, `high priority`
- Memory Efficient: `grep`, `limited`, `sample`, `3-5 files`
- Prioritization: `high-impact`, `prioritize`, `focus on`

### ProcessManagementMetric

**Scoring Algorithm** (weighted):
- Pre-Flight Checks (40%): Inspects package.json, checks processes
- Post-Execution Verification (35%): Verifies clean state
- Hanging Detection (15%): Detects hanging processes
- Orphaned Cleanup (10%): Cleans up orphaned processes

**Patterns Detected**:
- Pre-flight: `package.json`, `before running`, `inspect`
- Post-execution: `ps aux`, `verify`, `clean`, `after tests`
- Hanging: `hanging`, `stuck`, `timeout`, `not responding`
- Cleanup: `killed`, `terminate`, `cleanup`, `pkill`

## Key Principles

### Test Execution Safety
1. **NEVER use watch mode** - Causes memory leaks
2. **Always use CI mode** - Ensures clean termination
3. **Check package.json first** - Detect watch mode risks
4. **Verify process cleanup** - No orphaned processes

### Memory Efficiency
1. **Limit file reads** - Max 3-5 files for analysis
2. **Use grep for discovery** - Avoid reading all files
3. **Sample representative tests** - Don't exhaustively scan
4. **Use coverage tools** - Never manually calculate

### Process Management
1. **Pre-flight checks** - Inspect config before execution
2. **Post-execution verify** - Check process state after tests
3. **Clean up orphaned** - Kill hanging processes
4. **Document cleanup** - Report cleanup status

### Coverage Analysis
1. **Use coverage tools** - pytest-cov, nyc, istanbul
2. **Focus on critical paths** - Not 100% coverage
3. **Prioritize by impact** - Financial > security > UX
4. **Business context matters** - Payment > utility functions

## Development

### Adding New Scenarios

1. Add to `tests/eval/scenarios/qa/qa_scenarios.json`
2. Update test harness with parametrized test
3. Verify metric scoring logic
4. Run test and verify threshold

### Modifying Metrics

Metrics location:
- `tests/eval/metrics/qa/test_execution_safety_metric.py`
- `tests/eval/metrics/qa/coverage_quality_metric.py`
- `tests/eval/metrics/qa/process_management_metric.py`

After modifying, run metric unit tests:
```bash
pytest tests/eval/metrics/qa/ -v
```

## References

- QA scenarios: `tests/eval/scenarios/qa/qa_scenarios.json`
- Metrics: `tests/eval/metrics/qa/`
- Engineer test harness (reference): `tests/eval/agents/engineer/test_integration.py`
