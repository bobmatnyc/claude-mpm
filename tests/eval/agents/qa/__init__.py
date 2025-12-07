"""
QA Agent DeepEval Integration Tests.

This package contains integration tests for QA Agent behaviors across 20 scenarios
in 4 categories:

1. Test Execution Safety (7 scenarios: TST-QA-001 to TST-QA-007)
   - CI mode usage, no watch mode, package.json inspection
   - Process cleanup, timeout handling, output capture

2. Memory-Efficient Testing (6 scenarios: MEM-QA-001 to MEM-QA-006)
   - File read limits, grep-based discovery, representative sampling
   - Critical path focus, coverage tool usage

3. Process Management (4 scenarios: PROC-QA-001 to PROC-QA-004)
   - Pre-flight checks, post-execution verification
   - Hanging detection, orphaned cleanup

4. Coverage Analysis (3 scenarios: COV-QA-001 to COV-QA-003)
   - Coverage report analysis, critical path identification
   - High-impact test prioritization

Usage:
    # Run all QA Agent integration tests
    pytest tests/eval/agents/qa/ -v

    # Run specific category
    pytest tests/eval/agents/qa/test_integration.py::TestQATestExecutionSafety -v

    # Run integration workflows
    pytest tests/eval/agents/qa/test_integration.py::TestQAWorkflows -v
"""

__all__ = ["test_integration"]
