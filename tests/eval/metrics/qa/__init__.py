"""
QA Agent Custom DeepEval Metrics.

This module provides specialized metrics for testing QA Agent behaviors:

1. TestExecutionSafetyMetric: Validates safe test execution practices
   - Pre-flight checks (inspects package.json before running tests)
   - CI mode usage (uses CI=true or equivalent non-interactive modes)
   - No watch mode (NEVER uses vitest/jest watch mode)
   - Process cleanup verification (checks for orphaned processes)

2. CoverageQualityMetric: Validates test coverage analysis quality
   - Coverage tool usage (nyc, istanbul, c8, vitest --coverage)
   - Critical path focus (prioritizes uncovered critical paths)
   - Memory-efficient analysis (limits file reads, uses grep)
   - High-impact test prioritization (focuses on important tests)

3. ProcessManagementMetric: Validates process lifecycle management
   - Pre-flight checks (inspects test commands before execution)
   - Post-execution verification (verifies clean process state)
   - Hanging process detection (detects stuck test processes)
   - Orphaned process cleanup (cleans up node/vitest processes)

Usage:
    from tests.eval.metrics.qa import (
        TestExecutionSafetyMetric,
        CoverageQualityMetric,
        ProcessManagementMetric
    )

    # Create metrics
    test_safety = TestExecutionSafetyMetric(threshold=1.0)  # Strict
    coverage = CoverageQualityMetric(threshold=0.85)
    process_mgmt = ProcessManagementMetric(threshold=0.9)

    # Measure against test case
    score = test_safety.measure(test_case)
"""

from tests.eval.metrics.qa.coverage_quality_metric import (
    CoverageQualityMetric,
    create_coverage_quality_metric,
)
from tests.eval.metrics.qa.process_management_metric import (
    ProcessManagementMetric,
    create_process_management_metric,
)
from tests.eval.metrics.qa.test_execution_safety_metric import (
    TestExecutionSafetyMetric,
    create_test_execution_safety_metric,
)

__all__ = [
    "CoverageQualityMetric",
    "ProcessManagementMetric",
    "TestExecutionSafetyMetric",
    "create_coverage_quality_metric",
    "create_process_management_metric",
    "create_test_execution_safety_metric",
]
