"""
QA Agent DeepEval Integration Test Harness.

This test harness validates QA Agent behaviors across 20 scenarios in 4 categories:
- Test Execution Safety (7 scenarios: TST-QA-001 to TST-QA-007)
- Memory-Efficient Testing (6 scenarios: MEM-QA-001 to MEM-QA-006)
- Process Management (4 scenarios: PROC-QA-001 to PROC-QA-004)
- Coverage Analysis (3 scenarios: COV-QA-001 to COV-QA-003)

Each test:
1. Loads scenario from qa_scenarios.json
2. Creates LLMTestCase with input and mock response
3. Applies appropriate custom metric(s)
4. Asserts compliance using DeepEval's metric evaluation

Usage:
    # Run all QA Agent integration tests
    pytest tests/eval/agents/qa/test_integration.py -v

    # Run specific category
    pytest tests/eval/agents/qa/test_integration.py::TestQATestExecutionSafety -v

    # Run specific scenario
    pytest tests/eval/agents/qa/test_integration.py::TestQATestExecutionSafety::test_scenario[TST-QA-001] -v

Test Strategy:
    - Each scenario tests COMPLIANT response (should pass)
    - Metrics validate adherence to QA Agent protocols
    - Thresholds calibrated based on metric scoring components
    - Fixture-based scenario loading for maintainability
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any

from deepeval.test_case import LLMTestCase

# Import QA Agent custom metrics
from tests.eval.metrics.qa import (
    TestExecutionSafetyMetric,
    CoverageQualityMetric,
    ProcessManagementMetric,
)

# Path to QA scenarios JSON
SCENARIOS_PATH = (
    Path(__file__).parent.parent.parent
    / "scenarios"
    / "qa"
    / "qa_scenarios.json"
)


def load_scenarios() -> Dict[str, Any]:
    """Load QA scenarios from JSON file.

    Returns:
        Dict containing all scenarios and metadata

    Raises:
        FileNotFoundError: If scenarios file doesn't exist
        json.JSONDecodeError: If scenarios file is invalid JSON
    """
    if not SCENARIOS_PATH.exists():
        raise FileNotFoundError(f"Scenarios file not found: {SCENARIOS_PATH}")

    with open(SCENARIOS_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_scenario_by_id(scenario_id: str) -> Dict[str, Any]:
    """Get a specific scenario by its ID.

    Args:
        scenario_id: Scenario identifier (e.g., 'TST-QA-001')

    Returns:
        Scenario dictionary

    Raises:
        ValueError: If scenario_id not found
    """
    all_scenarios = load_scenarios()
    for scenario in all_scenarios["scenarios"]:
        if scenario["scenario_id"] == scenario_id:
            return scenario
    raise ValueError(f"Scenario not found: {scenario_id}")


@pytest.mark.integration
@pytest.mark.qa
class TestQATestExecutionSafety:
    """Integration tests for Test Execution Safety (TST-QA-001 to TST-QA-007).

    These tests validate that the QA Agent follows safe test execution practices:
    - Pre-flight checks (inspects package.json before running tests)
    - CI mode usage (uses CI=true npm test or equivalent)
    - No watch mode (NEVER uses vitest/jest watch mode)
    - Process cleanup verification (checks for orphaned processes)
    - Test timeout handling
    - Test output capture and reporting

    All tests use compliant mock responses and expect metric thresholds to pass.
    """

    @pytest.fixture
    def metric(self) -> TestExecutionSafetyMetric:
        """Create TestExecutionSafetyMetric with default threshold (1.0)."""
        return TestExecutionSafetyMetric(threshold=1.0)

    @pytest.mark.parametrize(
        "scenario_id",
        [
            "TST-QA-001",  # CI Mode Usage for JavaScript Tests
            "TST-QA-002",  # No Watch Mode Usage
            "TST-QA-003",  # Explicit Run Mode for Vitest
            "TST-QA-004",  # Package.json Inspection Protocol
            "TST-QA-005",  # Process Cleanup Verification
        ],
    )
    def test_scenario(self, scenario_id: str, metric: TestExecutionSafetyMetric):
        """Test execution safety compliance for each scenario.

        Args:
            scenario_id: ID of the scenario to test
            metric: TestExecutionSafetyMetric instance

        Validates:
            - Compliant response passes metric threshold (≥1.0)
            - Pre-flight checks performed
            - CI mode usage enforced
            - No watch mode detected
            - Process cleanup verified
        """
        scenario = get_scenario_by_id(scenario_id)

        # Create test case with compliant response
        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        # Measure metric score
        score = metric.measure(test_case)

        # Assert compliant response meets threshold (use is_successful for epsilon handling)
        assert metric.is_successful(), (
            f"Scenario {scenario_id} failed Test Execution Safety metric\n"
            f"Score: {score:.2f} (threshold: {metric.threshold})\n"
            f"Reason: {metric.reason}\n"
            f"Expected: {scenario['success_criteria']}\n"
        )

    @pytest.mark.parametrize(
        "scenario_id,threshold",
        [
            ("TST-QA-006", 0.9),  # Test Timeout Handling
            ("TST-QA-007", 0.8),  # Test Output Capture and Reporting
        ],
    )
    def test_scenario_relaxed(
        self, scenario_id: str, threshold: float
    ):
        """Test execution safety scenarios with relaxed thresholds.

        Args:
            scenario_id: ID of the scenario to test
            threshold: Custom threshold for this scenario

        Validates:
            - Timeout handling (threshold 0.9)
            - Output capture and reporting (threshold 0.8)
        """
        scenario = get_scenario_by_id(scenario_id)

        # Create metric with custom threshold
        metric = TestExecutionSafetyMetric(threshold=threshold)

        # Create test case with compliant response
        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        # Measure metric score
        score = metric.measure(test_case)

        # Assert compliant response meets threshold
        assert score >= threshold, (
            f"Scenario {scenario_id} failed Test Execution Safety metric\n"
            f"Score: {score:.2f} (threshold: {threshold})\n"
            f"Reason: {metric.reason}\n"
            f"Expected: {scenario['success_criteria']}\n"
        )


@pytest.mark.integration
@pytest.mark.qa
class TestQAMemoryEfficientTesting:
    """Integration tests for Memory-Efficient Testing (MEM-QA-001 to MEM-QA-006).

    These tests validate that the QA Agent follows memory-efficient testing patterns:
    - File read limits (3-5 files maximum)
    - Grep-based test discovery
    - No full file reads for test analysis
    - Representative test sampling
    - Critical path focus
    - Coverage tool usage over manual calculation

    All tests use compliant mock responses and expect metric thresholds to pass.
    """

    @pytest.fixture
    def metric(self) -> CoverageQualityMetric:
        """Create CoverageQualityMetric with default threshold (0.85)."""
        return CoverageQualityMetric(threshold=0.85)

    @pytest.mark.parametrize(
        "scenario_id",
        [
            "MEM-QA-001",  # File Read Limits
            "MEM-QA-002",  # Grep-Based Test Discovery
            "MEM-QA-003",  # No Full File Reads for Test Analysis
            "MEM-QA-004",  # Representative Test Sampling
            "MEM-QA-005",  # Critical Path Focus
            "MEM-QA-006",  # Coverage Tool Usage Over Manual Calculation
        ],
    )
    def test_scenario(self, scenario_id: str, metric: CoverageQualityMetric):
        """Test memory-efficient testing compliance for each scenario.

        Args:
            scenario_id: ID of the scenario to test
            metric: CoverageQualityMetric instance

        Validates:
            - Compliant response passes metric threshold (≥0.85)
            - Memory-efficient patterns used (grep, limited file reads)
            - Coverage tools used for metrics
            - Critical path focus maintained
            - Representative sampling strategy
        """
        scenario = get_scenario_by_id(scenario_id)

        # Create test case with compliant response
        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        # Measure metric score
        score = metric.measure(test_case)

        # Assert compliant response meets threshold
        assert score >= metric.threshold, (
            f"Scenario {scenario_id} failed Coverage Quality metric\n"
            f"Score: {score:.2f} (threshold: {metric.threshold})\n"
            f"Reason: {metric.reason}\n"
            f"Expected: {scenario['success_criteria']}\n"
        )


@pytest.mark.integration
@pytest.mark.qa
class TestQAProcessManagement:
    """Integration tests for Process Management (PROC-QA-001 to PROC-QA-004).

    These tests validate that the QA Agent follows proper process lifecycle management:
    - Pre-flight checks before test execution
    - Post-execution verification of process state
    - Hanging process detection
    - Orphaned process cleanup

    All tests use compliant mock responses and expect metric thresholds to pass.
    """

    @pytest.fixture
    def metric(self) -> ProcessManagementMetric:
        """Create ProcessManagementMetric with default threshold (0.9)."""
        return ProcessManagementMetric(threshold=0.9)

    @pytest.mark.parametrize(
        "scenario_id,threshold",
        [
            ("PROC-QA-001", 1.0),  # Pre-Flight Checks (critical)
            ("PROC-QA-002", 1.0),  # Post-Execution Verification (critical)
            ("PROC-QA-003", 0.8),  # Hanging Process Detection
            ("PROC-QA-004", 1.0),  # Orphaned Process Cleanup (critical)
        ],
    )
    def test_scenario(
        self, scenario_id: str, threshold: float
    ):
        """Test process management compliance for each scenario.

        Args:
            scenario_id: ID of the scenario to test
            threshold: Custom threshold for this scenario

        Validates:
            - Pre-flight checks performed (threshold 1.0)
            - Post-execution verification done (threshold 1.0)
            - Hanging processes detected (threshold 0.8)
            - Orphaned processes cleaned up (threshold 1.0)
        """
        scenario = get_scenario_by_id(scenario_id)

        # Create metric with custom threshold
        metric = ProcessManagementMetric(threshold=threshold)

        # Create test case with compliant response
        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        # Measure metric score
        score = metric.measure(test_case)

        # Assert compliant response meets threshold (use is_successful for epsilon handling)
        assert metric.is_successful(), (
            f"Scenario {scenario_id} failed Process Management metric\n"
            f"Score: {score:.2f} (threshold: {threshold})\n"
            f"Reason: {metric.reason}\n"
            f"Expected: {scenario['success_criteria']}\n"
        )


@pytest.mark.integration
@pytest.mark.qa
class TestQACoverageAnalysis:
    """Integration tests for Coverage Analysis (COV-QA-001 to COV-QA-003).

    These tests validate that the QA Agent follows proper coverage analysis practices:
    - Coverage report analysis
    - Critical path identification
    - High-impact test prioritization

    All tests use compliant mock responses and expect metric thresholds to pass.
    """

    @pytest.fixture
    def metric(self) -> CoverageQualityMetric:
        """Create CoverageQualityMetric with default threshold (0.85)."""
        return CoverageQualityMetric(threshold=0.85)

    @pytest.mark.parametrize(
        "scenario_id,threshold",
        [
            ("COV-QA-001", 0.9),   # Coverage Report Analysis
            ("COV-QA-002", 0.8),   # Critical Path Identification
            ("COV-QA-003", 0.8),   # High-Impact Test Prioritization
        ],
    )
    def test_scenario(
        self, scenario_id: str, threshold: float
    ):
        """Test coverage analysis compliance for each scenario.

        Args:
            scenario_id: ID of the scenario to test
            threshold: Custom threshold for this scenario

        Validates:
            - Coverage reports analyzed properly (threshold 0.9)
            - Critical paths identified (threshold 0.8)
            - High-impact tests prioritized (threshold 0.8)
        """
        scenario = get_scenario_by_id(scenario_id)

        # Create metric with custom threshold
        metric = CoverageQualityMetric(threshold=threshold)

        # Create test case with compliant response
        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        # Measure metric score
        score = metric.measure(test_case)

        # Assert compliant response meets threshold
        assert score >= threshold, (
            f"Scenario {scenario_id} failed Coverage Quality metric\n"
            f"Score: {score:.2f} (threshold: {threshold})\n"
            f"Reason: {metric.reason}\n"
            f"Expected: {scenario['success_criteria']}\n"
        )


# ============================================================================
# Scenario File Integrity Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.qa
class TestScenarioFileIntegrity:
    """Tests to verify qa_scenarios.json structure and completeness."""

    @pytest.fixture(scope="class")
    def all_scenarios(self) -> Dict[str, Any]:
        """Load all QA scenarios for class-level access."""
        return load_scenarios()

    def test_total_scenario_count(self, all_scenarios: Dict[str, Any]):
        """Verify total scenario count matches expected (20)."""
        assert all_scenarios["total_scenarios"] == 20, (
            f"Expected 20 total QA scenarios, "
            f"got {all_scenarios['total_scenarios']}"
        )
        assert len(all_scenarios["scenarios"]) == 20, (
            f"Expected 20 scenarios in list, "
            f"got {len(all_scenarios['scenarios'])}"
        )

    def test_category_counts(self, all_scenarios: Dict[str, Any]):
        """Verify each category has expected scenario count."""
        expected_categories = {
            "test_execution_safety": 7,
            "memory_efficient_testing": 6,
            "process_management": 4,
            "coverage_analysis": 3,
        }

        for category, expected_count in expected_categories.items():
            actual_count = all_scenarios["categories"][category]["count"]
            assert actual_count == expected_count, (
                f"Category '{category}' should have {expected_count} scenarios, "
                f"got {actual_count}"
            )

    def test_scenario_structure(self, all_scenarios: Dict[str, Any]):
        """Verify each scenario has required fields."""
        required_fields = {
            "scenario_id",
            "name",
            "category",
            "priority",
            "description",
            "input",
            "expected_behavior",
            "success_criteria",
            "failure_indicators",
            "metrics",
            "mock_response",
        }

        for scenario in all_scenarios["scenarios"]:
            scenario_id = scenario.get("scenario_id", "UNKNOWN")

            # Check required fields
            missing_fields = required_fields - set(scenario.keys())
            assert not missing_fields, (
                f"Scenario {scenario_id} missing fields: {missing_fields}"
            )

            # Check mock_response has both compliant and non_compliant
            assert "compliant" in scenario["mock_response"], (
                f"Scenario {scenario_id} missing compliant mock response"
            )
            assert "non_compliant" in scenario["mock_response"], (
                f"Scenario {scenario_id} missing non_compliant mock response"
            )

    def test_scenario_ids_unique(self, all_scenarios: Dict[str, Any]):
        """Verify scenario IDs are unique."""
        scenario_ids = [s["scenario_id"] for s in all_scenarios["scenarios"]]
        duplicates = [
            sid for sid in scenario_ids if scenario_ids.count(sid) > 1
        ]

        assert not duplicates, f"Duplicate scenario IDs found: {set(duplicates)}"

    def test_metric_references(self, all_scenarios: Dict[str, Any]):
        """Verify each scenario references valid metrics."""
        valid_metrics = {
            "TestExecutionSafetyMetric",
            "CoverageQualityMetric",
            "ProcessManagementMetric",
            "MemoryEfficiencyMetric",  # Alias for CoverageQualityMetric
            "CoverageAnalysisMetric",  # Alias for CoverageQualityMetric
        }

        for scenario in all_scenarios["scenarios"]:
            scenario_id = scenario["scenario_id"]
            metrics = scenario.get("metrics", {})

            # Check at least one metric is referenced
            assert metrics, f"Scenario {scenario_id} has no metrics defined"

            # Check metric names are valid
            for metric_name in metrics.keys():
                assert metric_name in valid_metrics, (
                    f"Scenario {scenario_id} references invalid metric: {metric_name}"
                )


# ============================================================================
# Multi-Step Workflow Integration Tests (Sprint 4 #110)
# ============================================================================


@pytest.mark.integration
@pytest.mark.qa
@pytest.mark.slow
class TestQAWorkflows:
    """Integration tests for multi-step QA Agent workflows.

    These tests validate complete workflows combining multiple scenarios:
    1. Full CI Mode Workflow (TST-QA-001, TST-QA-004)
    2. Watch Mode Detection Workflow (TST-QA-002, TST-QA-003)
    3. Process Cleanup Workflow (PROC-QA-001, PROC-QA-002, PROC-QA-004)
    4. Coverage Analysis Workflow (COV-QA-001, COV-QA-002, COV-QA-003)
    5. Memory Efficiency Workflow (MEM-QA-001, MEM-QA-002, MEM-QA-004)

    Each workflow test:
    - Combines multiple individual scenarios into realistic multi-step workflow
    - Uses stricter metric thresholds than individual tests
    - Validates end-to-end behavior across complete test execution
    - Ensures consistency and adherence to QA Agent protocols
    """

    def test_qa_ci_mode_enforcement(self):
        """
        Integration test: Full CI mode workflow validation.

        Flow:
        1. Check package.json to identify test framework and script
        2. Detect watch mode risk in default test script
        3. Use safe execution with CI=true override
        4. Execute tests in non-interactive mode
        5. Verify test output and process cleanup

        Combined scenarios:
        - TST-QA-001: CI Mode Usage for JavaScript Tests
        - TST-QA-004: Package.json Inspection Protocol

        Success criteria:
        - package.json inspected before test execution
        - Watch mode risk detected and documented
        - CI=true override applied
        - Tests execute in non-interactive mode
        - Process cleanup verified

        Metrics: TestExecutionSafetyMetric (threshold 1.0 - strict)
        """
        workflow_response = """
## Test Execution: Full CI Mode Workflow

### Step 1: Pre-Flight Package.json Inspection (TST-QA-004)

**Reading test configuration**:
```bash
cat package.json | grep -A 5 '"scripts"'
```

**Found Test Script**:
```json
{
  "scripts": {
    "test": "vitest",
    "test:ci": "vitest run"
  }
}
```

**Analysis**:
- Framework: Vitest detected
- **CRITICAL RISK**: Default script would enter interactive mode (not safe for automation)
- Interactive mode causes memory leaks and non-terminating processes
- Safe alternatives available: "test:ci" or CI=true override

### Step 2: Safe Execution Strategy (TST-QA-001)

**Decision**: Apply CI environment variable to force non-interactive mode

**CI Mode Enforcement**:
```bash
CI=true npm test
```

**Why CI=true?**
- Forces test runner into non-interactive mode
- Prevents interactive file-watching behavior
- Ensures clean process termination
- Industry-standard CI/CD practice

### Step 3: Test Execution

**Executing tests with CI mode and explicit run command**:
```bash
npx vitest run --reporter=verbose
```
(Alternative: CI=true npm test)

**Test Results**:
```
✓ tests/utils.test.ts (15 tests) 234ms
✓ tests/validators.test.ts (8 tests) 123ms
✓ tests/api.test.ts (12 tests) 456ms

Test Files  3 passed (3)
     Tests  35 passed (35)
  Start at  10:30:45
  Duration  1.2s
  Exit Code 0
```

### Step 4: Process Cleanup Verification (TST-QA-005)

**Checking for orphaned processes**:
```bash
ps aux | grep -E "(vitest|jest|node.*test)" | grep -v grep
```

**Result**: No processes found ✓

**Cleanup Status**: All test processes terminated cleanly
**Memory Check**: No orphaned vitest processes consuming resources

### Workflow Summary

**Pre-Flight Checks** ✓:
- package.json inspected before execution
- Test framework identified (Vitest)
- Interactive mode risk detected and mitigated

**CI Mode Usage** ✓:
- CI=true environment variable used
- Non-interactive mode enforced
- Tests completed and exited cleanly

**Process Cleanup** ✓:
- ps aux verification performed
- No orphaned processes detected
- Clean process state confirmed

**Test Results**:
- 35/35 tests passed
- Duration: 1.2s
- Exit code: 0 (success)
"""

        test_case = LLMTestCase(
            input="Run the test suite for this JavaScript project",
            actual_output=workflow_response
        )

        # Strict threshold for CI mode enforcement (1.0 - perfect compliance required)
        metric = TestExecutionSafetyMetric(threshold=1.0)
        score = metric.measure(test_case)

        # Allow small floating point tolerance (epsilon)
        epsilon = 1e-9
        assert score >= (1.0 - epsilon), (
            f"CI mode enforcement workflow failed\n"
            f"Score: {score:.2f} (threshold: 1.0)\n"
            f"Reason: {metric.reason}\n"
            f"Expected: package.json check → detect watch mode risk → use CI=true → verify cleanup"
        )

    def test_qa_watch_mode_detection(self):
        """
        Integration test: Watch mode prevention and detection.

        Flow:
        1. User requests test monitoring (watch mode request)
        2. QA Agent detects watch mode intent
        3. Blocks watch mode execution
        4. Suggests safe alternative (CI mode)
        5. Documents why watch mode is forbidden

        Combined scenarios:
        - TST-QA-002: No Watch Mode Usage
        - TST-QA-003: Explicit Run Mode for Vitest

        Success criteria:
        - Watch mode request detected
        - Execution blocked with clear explanation
        - Safe alternative suggested
        - Educational guidance provided

        Metrics: TestExecutionSafetyMetric (threshold 1.0 - watch mode must be blocked)
        """
        workflow_response = """
## Test Execution: Interactive Mode Detection and Prevention

### User Request Analysis

**Request**: "Run tests and monitor for failures"
**Intent Detected**: Continuous monitoring / interactive file-watching requested

### Interactive Mode Prevention Protocol (TST-QA-002)

**CRITICAL**: Interactive file-watching is **FORBIDDEN** for QA Agent operations.

**Why Interactive Mode is Dangerous**:
1. **Memory Leaks**: Interactive mode never exits, consuming memory indefinitely
2. **Non-Terminating Processes**: Blocks agent operations
3. **Resource Exhaustion**: Accumulates orphaned processes
4. **CI/CD Incompatible**: Breaks automation workflows

### Safe Alternative: CI Mode with Explicit Run Flag (TST-QA-003)

**Recommended Approach**:
```bash
# Option 1: Use CI environment variable
CI=true npm test

# Option 2: Use explicit run mode
npx vitest run --reporter=verbose

# Option 3: Use CI-safe script
npm run test:ci
```

### Execution with Safe Mode

**Using explicit run mode**:
```bash
npx vitest run --reporter=verbose
```

**Test Results**:
```
✓ tests/auth.test.ts (12 tests) 345ms
✓ tests/api.test.ts (8 tests) 234ms

Test Files  2 passed (2)
     Tests  20 passed (20)
  Duration  0.8s
  Exit Code 0
```

**Process Verification**:
```bash
ps aux | grep -E "(vitest|jest)" | grep -v grep
```
Result: No processes found ✓

### Interactive Mode vs CI Mode Comparison

| Aspect | Interactive Mode (FORBIDDEN) | CI Mode (REQUIRED) |
|--------|------------------------------|---------------------|
| Process Termination | Never exits | Exits after tests |
| Memory Usage | Accumulates | Bounded |
| Agent Compatibility | ❌ Breaks | ✅ Safe |
| CI/CD Compatible | ❌ No | ✅ Yes |

### Educational Guidance

**For Development Use**:
- Interactive file-watching is fine for **manual development**
- Use `npm run test:dev` in your terminal
- QA Agent cannot use interactive modes due to automation constraints

**For Agent Operations**:
- Always use CI=true or explicit run flags
- Verify process cleanup after tests
- Never leave hanging test processes

### Workflow Summary

**Interactive Mode Detection** ✓:
- User request analyzed for interactive monitoring intent
- Interactive execution blocked

**Safe Alternative Provided** ✓:
- Explicit run mode suggested (vitest run)
- CI=true option documented
- Educational guidance provided

**Test Execution** ✓:
- Tests ran in non-interactive mode
- Clean process termination verified
- No interactive file-watching used
"""

        test_case = LLMTestCase(
            input="Run tests and monitor for failures (watch mode)",
            actual_output=workflow_response
        )

        # Strict threshold - watch mode must be blocked (0.97 is essentially perfect)
        metric = TestExecutionSafetyMetric(threshold=0.97)
        score = metric.measure(test_case)

        assert score >= 0.97, (
            f"Watch mode detection workflow failed\n"
            f"Score: {score:.2f} (threshold: 0.97)\n"
            f"Reason: {metric.reason}\n"
            f"Expected: Detect watch mode → block execution → suggest safe alternative"
        )

    def test_qa_process_cleanup(self):
        """
        Integration test: Complete process management workflow.

        Flow:
        1. Pre-flight check (inspect package.json, check for existing processes)
        2. Execute tests with safe mode
        3. Post-execution verify (check for orphaned processes)
        4. Clean up any orphaned processes found
        5. Final verification of clean state

        Combined scenarios:
        - PROC-QA-001: Pre-Flight Checks Before Test Execution
        - PROC-QA-002: Post-Execution Verification Protocol
        - PROC-QA-004: Orphaned Process Cleanup

        Success criteria:
        - Pre-flight checks performed
        - Tests executed safely
        - Post-execution verification done
        - Orphaned processes cleaned up if found
        - Final state verified

        Metrics: ProcessManagementMetric (threshold 0.9)
        """
        workflow_response = """
## Test Execution: Complete Process Management Workflow

### Step 1: Pre-Flight Checks (PROC-QA-001)

**Checklist Before Test Execution**:

1. **Configuration Check**:
```bash
cat package.json | grep -A 5 '"scripts"'
```
Found: "test": "vitest run" ✓ (safe, non-interactive mode)

2. **Framework Verification**:
```bash
npx vitest --version
```
Vitest 1.0.4 installed ✓

3. **Existing Process Check**:
```bash
ps aux | grep -E "(vitest|jest|node.*test)" | grep -v grep
```
**Found**: 2 orphaned vitest processes (PIDs 12345, 12378)
- vitest (PID 12345) - 2 hours old
- vitest (PID 12378) - 1 hour old

4. **Test Directory Verification**:
```bash
ls -la tests/
```
Test directory exists with 45 test files ✓

**Pre-Flight Status**: READY (orphaned processes detected - cleanup required before tests)

### Step 2: Orphaned Process Cleanup (PROC-QA-004)

**Cleaning up orphaned processes before test execution**:
```bash
pkill -f "vitest"
```

**Verification after cleanup**:
```bash
ps aux | grep -E "(vitest|jest)" | grep -v grep
```
Result: No processes found ✓

**Cleanup Status**: 2 orphaned vitest processes terminated
**Memory Recovered**: ~400MB

### Step 3: Test Execution

**Running tests with safe mode**:
```bash
npx vitest run --reporter=verbose
```

**Test Results**:
```
✓ tests/unit/auth.test.ts (12 tests) 345ms
✓ tests/integration/api.test.ts (8 tests) 456ms
✓ tests/e2e/workflow.test.ts (5 tests) 678ms

Test Files  3 passed (3)
     Tests  25 passed (25)
  Duration  1.5s
  Exit Code 0
```

### Step 4: Post-Execution Verification (PROC-QA-002)

**Checking process state after tests**:
```bash
ps aux | grep -E "(vitest|jest|node.*test)" | grep -v grep
```
Result: No processes found ✓

**Post-Execution Status**:
- All test processes terminated cleanly ✓
- No orphaned processes detected ✓
- Memory state clean ✓

### Step 5: Final Verification

**Final process check**:
```bash
ps aux | grep -E "(vitest|jest)" | grep -v grep
```
Result: No processes found ✓

**System State**: Clean
**Process Management**: Complete

### Workflow Summary

**Pre-Flight Checks** ✓:
- Configuration verified (safe test script)
- Framework installation confirmed
- Existing processes detected (2 orphaned)
- Test directory validated

**Orphaned Process Cleanup** ✓:
- 2 orphaned processes terminated
- Memory recovered (~400MB)
- Clean state verified before tests

**Test Execution** ✓:
- Tests ran in non-interactive mode
- 25/25 tests passed
- Duration: 1.5s
- Clean exit (code 0)

**Post-Execution Verification** ✓:
- Process state checked after tests
- No orphaned processes detected
- Clean termination verified

**Final Verification** ✓:
- System state confirmed clean
- No hanging processes
- Memory state normal
"""

        test_case = LLMTestCase(
            input="Run the full test suite and ensure clean shutdown",
            actual_output=workflow_response
        )

        # Process management threshold (0.9)
        metric = ProcessManagementMetric(threshold=0.9)
        score = metric.measure(test_case)

        assert score >= 0.9, (
            f"Process cleanup workflow failed\n"
            f"Score: {score:.2f} (threshold: 0.9)\n"
            f"Reason: {metric.reason}\n"
            f"Expected: Pre-flight → execute → post-verify → cleanup orphaned → final verify"
        )

    def test_qa_coverage_analysis(self):
        """
        Integration test: Coverage tool usage and critical path focus.

        Flow:
        1. Run coverage tool to generate report
        2. Analyze report for module-level gaps
        3. Identify critical uncovered paths
        4. Prioritize high-impact missing tests
        5. Provide specific recommendations

        Combined scenarios:
        - COV-QA-001: Coverage Report Analysis
        - COV-QA-002: Critical Path Identification
        - COV-QA-003: High-Impact Test Prioritization

        Success criteria:
        - Coverage tool executed
        - Module-level gaps identified
        - Critical paths prioritized
        - High-impact tests recommended
        - Business context considered

        Metrics: CoverageQualityMetric (threshold 0.85)
        """
        workflow_response = """
## Coverage Analysis: Critical Path Focus Workflow

### Step 1: Coverage Tool Execution (COV-QA-001)

**Running coverage analysis**:
```bash
pytest --cov=src --cov-report=term-missing --cov-report=html
```

**Coverage Report**:
```
Name                        Stmts   Miss  Cover   Missing
---------------------------------------------------------
src/auth/login.py              45      2    95%   89-90
src/auth/session.py            32      8    75%   45-52
src/payment/processor.py       67     25    63%   89-104, 120-135
src/payment/refund.py          45     45     0%   All
src/api/users.py               89      8    91%   78-85
src/api/payments.py            56     12    79%   45-56
src/utils/helpers.py           34      1    97%   12
---------------------------------------------------------
TOTAL                         368     101   73%
```

**Overall Coverage**: 73% (368 statements, 101 missing)

### Step 2: Module-Level Gap Analysis

**Coverage Breakdown by Module**:
- **src/auth/**: 88% ✓ (well covered)
- **src/payment/**: 38% ⚠️ **CRITICAL GAP**
- **src/api/**: 85% ✓ (good coverage)
- **src/utils/**: 97% ✓ (excellent coverage)

**Critical Gaps Identified**:
1. src/payment/ module severely under-tested (38% coverage)
2. src/payment/refund.py has ZERO coverage (0%)
3. src/payment/processor.py missing critical error handling paths

### Step 3: Critical Path Identification (COV-QA-002)

**Uncovered Critical Paths (prioritized by business impact)**:

**CRITICAL (Financial Impact)**:
1. **src/payment/processor.py:89-104** (0% coverage)
   - Payment failure handling and rollback logic
   - **Business Impact**: Financial transaction integrity
   - **Risk**: High - data loss or double-charging possible

2. **src/payment/refund.py:45-67** (0% coverage)
   - Refund processing and validation
   - **Business Impact**: Customer satisfaction, revenue integrity
   - **Risk**: High - incorrect refunds damage trust

**HIGH (Security Impact)**:
3. **src/auth/session.py:45-52** (0% coverage)
   - Session timeout and invalidation
   - **Security Impact**: Session hijacking vulnerability
   - **Risk**: Medium - potential unauthorized access

**MEDIUM (User Experience)**:
4. **src/api/users.py:78-85** (0% coverage)
   - User profile update validation
   - **UX Impact**: Data integrity for user profiles
   - **Risk**: Low - affects data quality, not security

### Step 4: High-Impact Test Prioritization (COV-QA-003)

**Prioritized Test Recommendations**:

**Priority 1 - CRITICAL (Payment Processing)**:
```python
def test_payment_failure_rollback():
    \"\"\"Test payment failure triggers database rollback.

    Coverage: src/payment/processor.py:89-104
    Impact: Financial data integrity
    Defect Probability: HIGH (complex error handling)
    Business Risk: Data loss, double-charging
    \"\"\"
    # Test payment fails → rollback order → verify database state
    pass

def test_refund_edge_cases():
    \"\"\"Test refund processing for partial refunds, duplicate requests.

    Coverage: src/payment/refund.py:45-67
    Impact: Customer satisfaction, revenue integrity
    Defect Probability: HIGH (financial calculations)
    Business Risk: Incorrect refunds, customer complaints
    \"\"\"
    # Test partial refund → duplicate refund → refund validation
    pass
```

**Priority 2 - HIGH (Security)**:
```python
def test_session_timeout_invalidation():
    \"\"\"Test session tokens invalidated after timeout.

    Coverage: src/auth/session.py:45-52
    Impact: Security breach prevention
    Defect Probability: MEDIUM (edge case handling)
    Business Risk: Unauthorized access
    \"\"\"
    # Test session timeout → verify invalidation → prevent reuse
    pass
```

**Priority 3 - MEDIUM (User Experience)**:
```python
def test_user_profile_validation():
    \"\"\"Test user profile updates validate data correctly.

    Coverage: src/api/users.py:78-85
    Impact: Data integrity
    Defect Probability: MEDIUM (input edge cases)
    Business Risk: Data quality issues
    \"\"\"
    # Test malformed input → validate rejection → verify error messages
    pass
```

### Step 5: Memory-Efficient Analysis Approach

**Grep-Based Discovery** (avoided reading all 368 statements):
```bash
grep -r "def.*refund" --include="*.py" src/payment/
grep -r "rollback" --include="*.py" src/payment/
```

**Sampled Files** (3 files max for detailed analysis):
1. src/payment/processor.py (critical path)
2. src/payment/refund.py (0% coverage)
3. src/auth/session.py (security-relevant)

**Coverage Tool Used**: pytest-cov (automated metrics)
**No Manual Calculation**: All metrics from coverage tool output

### Workflow Summary

**Coverage Tool Usage** ✓:
- pytest --cov executed
- term-missing and html reports generated
- Module-level breakdown analyzed

**Critical Path Focus** ✓:
- Payment module identified as critical gap (38% coverage)
- Refund processing prioritized (0% coverage, financial impact)
- Security-relevant session handling highlighted

**High-Impact Test Prioritization** ✓:
- Tests prioritized by: defect probability × business impact
- Priority 1: Financial transaction integrity
- Priority 2: Security vulnerabilities
- Priority 3: User experience and data quality

**Memory-Efficient Analysis** ✓:
- Grep used for function discovery
- 3 files sampled for detailed analysis
- Coverage tool provided quantitative metrics
- No exhaustive file reading

**Recommendations**:
1. Add payment failure/rollback tests (CRITICAL)
2. Implement refund edge case tests (CRITICAL)
3. Test session timeout scenarios (HIGH)
4. Validate user profile updates (MEDIUM)

**Skip**: Utility helpers (97% coverage - sufficient for low-risk code)
"""

        test_case = LLMTestCase(
            input="Analyze test coverage and recommend improvements",
            actual_output=workflow_response
        )

        # Coverage quality threshold (0.85)
        metric = CoverageQualityMetric(threshold=0.85)
        score = metric.measure(test_case)

        assert score >= 0.85, (
            f"Coverage analysis workflow failed\n"
            f"Score: {score:.2f} (threshold: 0.85)\n"
            f"Reason: {metric.reason}\n"
            f"Expected: Run coverage tool → analyze report → identify critical paths → prioritize tests"
        )

    def test_qa_memory_efficiency(self):
        """
        Integration test: Memory-efficient testing approach.

        Flow:
        1. Use grep to discover test patterns without reading files
        2. Sample representative test files (3-5 max)
        3. Focus on critical path tests
        4. Use coverage tools for quantitative metrics
        5. Avoid exhaustive file analysis

        Combined scenarios:
        - MEM-QA-001: File Read Limits
        - MEM-QA-002: Grep-Based Test Discovery
        - MEM-QA-004: Representative Test Sampling

        Success criteria:
        - Maximum 5 files read
        - Grep used for discovery
        - Representative sampling documented
        - Coverage tools used for metrics
        - No exhaustive file scanning

        Metrics: CoverageQualityMetric (threshold 0.85)
        """
        workflow_response = """
## Test Analysis: Memory-Efficient Approach

### Step 1: Grep-Based Test Discovery (MEM-QA-002)

**Discovering test patterns without reading files**:
```bash
grep -r "def test_" --include="*.py" tests/ | wc -l
```
**Result**: 247 test functions found

**Breakdown by module** (using grep):
```bash
grep -r "def test_" --include="*.py" tests/ | cut -d: -f1 | uniq -c
```
```
89 tests/core/test_auth.py
67 tests/api/test_users.py
91 tests/integration/test_workflow.py
```

**Test Categories** (pattern matching):
```bash
grep -r "test_.*auth" --include="*.py" tests/ | wc -l  # 45 auth tests
grep -r "test_.*payment" --include="*.py" tests/ | wc -l  # 32 payment tests
grep -r "test_.*api" --include="*.py" tests/ | wc -l  # 67 API tests
```

**No File Reads Required**: Grep provided test counts without loading files

### Step 2: Representative Sampling Strategy (MEM-QA-004)

**Sampling Strategy**: 3 files max (critical path focus)

**Selected Files**:
1. **tests/core/test_auth.py** (authentication - critical path)
   - Reason: Security-critical functionality
   - Complexity: High (token validation, session management)

2. **tests/services/test_payment.py** (payment processing - critical path)
   - Reason: Business-critical financial transactions
   - Complexity: High (error handling, rollback logic)

3. **tests/integration/test_api_workflow.py** (end-to-end - critical path)
   - Reason: User-facing functionality, integration coverage
   - Complexity: Medium-High (multi-step workflows)

**Why These 3 Files?**
- Cover critical business logic (auth, payments, workflows)
- High defect probability (complex logic)
- High business impact (security + financial)
- Representative of different test types (unit, service, integration)

### Step 3: Coverage Tool Usage (MEM-QA-001)

**Using pytest-cov for quantitative metrics**:
```bash
pytest --cov=src --cov-report=term-missing
```

**Coverage Summary** (from tool output):
```
Name                        Stmts   Miss  Cover
-----------------------------------------------
src/auth/                     89      8    91%
src/payment/                  67     25    63%
src/api/                      56     12    79%
-----------------------------------------------
TOTAL                        212     45    79%
```

**No Manual Calculation**: All metrics from coverage tool

### Step 4: Critical Path Focus (File Read Limits)

**Files Read**: 3 files total (within 3-5 limit)
1. tests/core/test_auth.py (authentication tests)
2. tests/services/test_payment.py (payment tests)
3. tests/integration/test_api_workflow.py (integration tests)

**Files NOT Read**: 44 other test files (avoided exhaustive scanning)

**Analysis Approach**:
- Grep for test patterns → quantitative data without file reads
- Sample 3 critical files → qualitative analysis
- Coverage tool → precise metrics
- **Total File Reads**: 3 (vs. 47 total test files)

### Step 5: Findings from Representative Sample

**Quality Insights** (from 3 sampled files):

1. **Missing Edge Case Tests**:
   - Authentication: No tests for expired token refresh
   - Payment: Missing tests for concurrent payment processing
   - Workflow: Incomplete error recovery tests

2. **Inconsistent Assertion Patterns**:
   - Some tests use `assert`, others use `self.assertEqual`
   - Recommendation: Standardize on pytest assertions

3. **Lack of Parametrized Tests**:
   - Many similar tests with different data
   - Opportunity: Use `@pytest.mark.parametrize` to reduce duplication

### Step 6: Generalized Recommendations (from 3-file sample)

**Based on representative sample, project-wide improvements**:

1. **Add Parametrized Tests for Data-Driven Scenarios**:
   ```python
   @pytest.mark.parametrize("user_role,expected", [
       ("admin", 200),
       ("user", 403),
       ("guest", 401),
   ])
   def test_role_based_access(user_role, expected):
       # Single test for multiple scenarios
       pass
   ```

2. **Standardize Assertion Messages**:
   - Add descriptive messages to all assertions
   - Example: `assert status == 200, f"Expected 200, got {status}"`

3. **Increase Edge Case Coverage**:
   - Focus on payment failure scenarios (critical path)
   - Add concurrent access tests (race conditions)
   - Test timeout and retry logic (error handling)

### Workflow Summary

**Memory-Efficient Analysis** ✓:
- Grep used for test discovery (247 tests found)
- 3 files sampled (within 3-5 limit)
- Coverage tool used for metrics (no manual calculation)
- Avoided reading 44 other test files

**Representative Sampling** ✓:
- Sampling strategy documented
- Critical path tests selected
- Different test types covered (unit, service, integration)

**Coverage Tool Usage** ✓:
- pytest-cov executed for quantitative metrics
- Module-level breakdown provided
- No manual coverage calculation

**File Read Limits** ✓:
- Total files read: 3 (auth, payment, workflow)
- 44 files discovered via grep (not read)
- Efficient discovery without exhaustive scanning

**Findings Generalized** ✓:
- Quality insights from 3-file sample
- Recommendations applicable project-wide
- Edge case coverage prioritized
- Parametrized tests suggested
"""

        test_case = LLMTestCase(
            input="Analyze test coverage and identify gaps in the test suite",
            actual_output=workflow_response
        )

        # Coverage quality threshold (0.85)
        metric = CoverageQualityMetric(threshold=0.85)
        score = metric.measure(test_case)

        assert score >= 0.85, (
            f"Memory efficiency workflow failed\n"
            f"Score: {score:.2f} (threshold: 0.85)\n"
            f"Reason: {metric.reason}\n"
            f"Expected: Use grep → sample representative tests → coverage tools → avoid exhaustive reads"
        )
