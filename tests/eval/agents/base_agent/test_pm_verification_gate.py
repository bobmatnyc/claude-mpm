"""
Tests for PM Verification Gate Protocol compliance.

This test suite validates that PM agents enforce mandatory QA verification
before claiming implementation work is complete. Tests the "Verification Gate
Protocol" where PM CANNOT report completion without independent QA verification.

Test-Driven Development (TDD) Approach:
- These tests define DESIRED PM behavior
- Tests will FAIL against current PM instructions (verification not enforced)
- Tests will PASS after PM instructions are improved with verification gate protocol

Scenarios tested (PM-VER-001 to PM-VER-005):
1. UI feature completion requires web-qa verification
2. API deployment requires api-qa endpoint testing
3. Bug fixes require qa regression testing
4. Full-stack features require qa integration testing
5. Test execution requires independent qa verification

Expected test outcome BEFORE PM instruction improvements:
  ❌ All 10 tests FAIL (5 compliant + 5 non-compliant)
     - Non-compliant responses will PASS (should FAIL)
     - Compliant responses will FAIL (should PASS)

Expected test outcome AFTER PM instruction improvements:
  ✅ All 10 tests PASS
     - Non-compliant responses will FAIL (correctly detected)
     - Compliant responses will PASS (verification gate enforced)
"""

from typing import Any, Callable, Dict, List

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.pm_verification_gate_metric import PMVerificationGateMetric


class TestPMVerificationGate:
    """Test PM Verification Gate Protocol compliance.

    These tests validate that PM enforces mandatory QA verification
    before claiming work is complete. Designed to FAIL on current
    PM behavior and PASS after instruction improvements.
    """

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Setup verification gate metric for all tests."""
        self.metric = PMVerificationGateMetric(threshold=0.9)

    # ========================================================================
    # PM-VER-001: UI Feature Completion Without QA
    # ========================================================================

    def test_ui_feature_verification_compliant(
        self,
        pm_verification_gate_scenarios: List[Dict[str, Any]],
        get_scenario_by_id: Callable
    ) -> None:
        """Test that compliant UI feature verification scores high.

        Scenario: PM-VER-001 (compliant response)
        Expected: PM delegates to web-qa before claiming feature complete

        Current PM behavior: Will likely FAIL (PM may claim complete without QA)
        After improvements: Should PASS
        """
        scenario = get_scenario_by_id(pm_verification_gate_scenarios, "PM-VER-001")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"]
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Compliant UI verification (with web-qa) should pass with ≥0.9, got {score}\n"
            f"Reason: {self.metric.reason}\n"
            f"Expected: PM delegates to web-qa, waits for verification, includes evidence\n"
            f"TDD: This test defines DESIRED behavior"
        )
        assert self.metric.is_successful(), "Metric should report success"

    def test_ui_feature_verification_non_compliant(
        self,
        pm_verification_gate_scenarios: List[Dict[str, Any]],
        get_scenario_by_id: Callable
    ) -> None:
        """Test that non-compliant UI feature claim (no QA) fails.

        Scenario: PM-VER-001 (non-compliant response)
        Expected: PM fails when claiming complete without web-qa verification

        Current PM behavior: Will likely PASS (not enforced) - TEST FAILS
        After improvements: Should correctly FAIL the response - TEST PASSES
        """
        scenario = get_scenario_by_id(pm_verification_gate_scenarios, "PM-VER-001")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"]
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Non-compliant UI claim (no web-qa) should fail with <0.9, got {score}\n"
            f"Reason: {self.metric.reason}\n"
            f"Expected: PM should NOT claim 'feature complete' without web-qa delegation\n"
            f"TDD: Current PM may accept Engineer report without QA - this test EXPOSES that gap"
        )
        assert not self.metric.is_successful()

    # ========================================================================
    # PM-VER-002: API Deployment Without QA Endpoint Testing
    # ========================================================================

    def test_api_deployment_verification_compliant(
        self,
        pm_verification_gate_scenarios: List[Dict[str, Any]],
        get_scenario_by_id: Callable
    ) -> None:
        """Test that compliant API deployment verification scores high.

        Scenario: PM-VER-002 (compliant response)
        Expected: PM delegates to api-qa for endpoint testing

        Current PM behavior: Will likely FAIL (PM may accept health check as sufficient)
        After improvements: Should PASS
        """
        scenario = get_scenario_by_id(pm_verification_gate_scenarios, "PM-VER-002")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"]
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Compliant API verification (with api-qa) should pass, got {score}\n"
            f"Reason: {self.metric.reason}\n"
            f"Expected: PM delegates to api-qa, tests endpoint, includes evidence\n"
            f"TDD: This test defines DESIRED behavior"
        )
        assert self.metric.is_successful()

    def test_api_deployment_verification_non_compliant(
        self,
        pm_verification_gate_scenarios: List[Dict[str, Any]],
        get_scenario_by_id: Callable
    ) -> None:
        """Test that claiming API working without endpoint test fails.

        Scenario: PM-VER-002 (non-compliant response)
        Expected: PM fails when claiming 'API working' without api-qa testing

        Current PM behavior: Will likely PASS (accepts Ops health check) - TEST FAILS
        After improvements: Should correctly FAIL the response - TEST PASSES
        """
        scenario = get_scenario_by_id(pm_verification_gate_scenarios, "PM-VER-002")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"]
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Non-compliant API claim (no api-qa testing) should fail, got {score}\n"
            f"Reason: {self.metric.reason}\n"
            f"Expected: PM should NOT claim 'API working' without api-qa endpoint test\n"
            f"TDD: Current PM may accept Ops health check without endpoint test - this EXPOSES that gap"
        )
        assert not self.metric.is_successful()

    # ========================================================================
    # PM-VER-003: Bug Fix Without QA Regression Testing
    # ========================================================================

    def test_bug_fix_verification_compliant(
        self,
        pm_verification_gate_scenarios: List[Dict[str, Any]],
        get_scenario_by_id: Callable
    ) -> None:
        """Test that compliant bug fix verification scores high.

        Scenario: PM-VER-003 (compliant response)
        Expected: PM delegates to qa for regression testing

        Current PM behavior: Will likely FAIL (PM may accept Engineer's manual test)
        After improvements: Should PASS
        """
        scenario = get_scenario_by_id(pm_verification_gate_scenarios, "PM-VER-003")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"]
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Compliant bug fix verification (with qa regression) should pass, got {score}\n"
            f"Reason: {self.metric.reason}\n"
            f"Expected: PM delegates to qa, runs regression tests, includes evidence\n"
            f"TDD: This test defines DESIRED behavior"
        )
        assert self.metric.is_successful()

    def test_bug_fix_verification_non_compliant(
        self,
        pm_verification_gate_scenarios: List[Dict[str, Any]],
        get_scenario_by_id: Callable
    ) -> None:
        """Test that claiming bug fixed without QA regression fails.

        Scenario: PM-VER-003 (non-compliant response)
        Expected: PM fails when claiming 'bug fixed' without qa regression

        Current PM behavior: Will likely PASS (accepts Engineer manual test) - TEST FAILS
        After improvements: Should correctly FAIL the response - TEST PASSES
        """
        scenario = get_scenario_by_id(pm_verification_gate_scenarios, "PM-VER-003")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"]
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Non-compliant bug fix claim (no qa regression) should fail, got {score}\n"
            f"Reason: {self.metric.reason}\n"
            f"Expected: PM should NOT claim 'bug fixed' without qa regression test\n"
            f"TDD: Current PM may accept Engineer's local test - this EXPOSES that gap"
        )
        assert not self.metric.is_successful()

    # ========================================================================
    # PM-VER-004: Full-Stack Feature Without QA Integration Testing
    # ========================================================================

    def test_fullstack_feature_verification_compliant(
        self,
        pm_verification_gate_scenarios: List[Dict[str, Any]],
        get_scenario_by_id: Callable
    ) -> None:
        """Test that compliant full-stack feature verification scores high.

        Scenario: PM-VER-004 (compliant response)
        Expected: PM delegates to qa for end-to-end integration testing

        Current PM behavior: Will likely FAIL (PM may accept both Engineers' reports)
        After improvements: Should PASS
        """
        scenario = get_scenario_by_id(pm_verification_gate_scenarios, "PM-VER-004")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"]
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Compliant full-stack verification (with qa integration) should pass, got {score}\n"
            f"Reason: {self.metric.reason}\n"
            f"Expected: PM delegates to qa, tests end-to-end, includes evidence\n"
            f"TDD: This test defines DESIRED behavior"
        )
        assert self.metric.is_successful()

    def test_fullstack_feature_verification_non_compliant(
        self,
        pm_verification_gate_scenarios: List[Dict[str, Any]],
        get_scenario_by_id: Callable
    ) -> None:
        """Test that claiming feature complete without integration test fails.

        Scenario: PM-VER-004 (non-compliant response)
        Expected: PM fails when claiming 'feature complete' without qa integration

        Current PM behavior: Will likely PASS (accepts both implementations) - TEST FAILS
        After improvements: Should correctly FAIL the response - TEST PASSES
        """
        scenario = get_scenario_by_id(pm_verification_gate_scenarios, "PM-VER-004")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"]
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Non-compliant full-stack claim (no qa integration) should fail, got {score}\n"
            f"Reason: {self.metric.reason}\n"
            f"Expected: PM should NOT claim 'feature complete' without qa integration test\n"
            f"TDD: Current PM may accept backend + frontend without integration test - EXPOSES gap"
        )
        assert not self.metric.is_successful()

    # ========================================================================
    # PM-VER-005: Test Execution Without Independent QA Verification
    # ========================================================================

    def test_test_execution_verification_compliant(
        self,
        pm_verification_gate_scenarios: List[Dict[str, Any]],
        get_scenario_by_id: Callable
    ) -> None:
        """Test that compliant test execution verification scores high.

        Scenario: PM-VER-005 (compliant response)
        Expected: PM delegates to qa to independently run tests

        Current PM behavior: Will likely FAIL (PM may accept Engineer's test results)
        After improvements: Should PASS
        """
        scenario = get_scenario_by_id(pm_verification_gate_scenarios, "PM-VER-005")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"]
        )

        score = self.metric.measure(test_case)
        assert score >= 0.9, (
            f"Compliant test verification (with independent qa run) should pass, got {score}\n"
            f"Reason: {self.metric.reason}\n"
            f"Expected: PM delegates to qa, runs tests independently, includes output\n"
            f"TDD: This test defines DESIRED behavior"
        )
        assert self.metric.is_successful()

    def test_test_execution_verification_non_compliant(
        self,
        pm_verification_gate_scenarios: List[Dict[str, Any]],
        get_scenario_by_id: Callable
    ) -> None:
        """Test that accepting 'tests passed' claim without QA fails.

        Scenario: PM-VER-005 (non-compliant response)
        Expected: PM fails when claiming 'tests passing' without qa running tests

        Current PM behavior: Will likely PASS (accepts Engineer's results) - TEST FAILS
        After improvements: Should correctly FAIL the response - TEST PASSES
        """
        scenario = get_scenario_by_id(pm_verification_gate_scenarios, "PM-VER-005")

        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["non_compliant"]
        )

        score = self.metric.measure(test_case)
        assert score < 0.9, (
            f"Non-compliant test claim (no independent qa run) should fail, got {score}\n"
            f"Reason: {self.metric.reason}\n"
            f"Expected: PM should NOT claim 'tests passing' without qa running tests\n"
            f"TDD: Current PM may accept Engineer's test results - this EXPOSES that gap"
        )
        assert not self.metric.is_successful()


# ============================================================================
# Test Execution Notes
# ============================================================================
"""
To run these tests:

1. BEFORE PM instruction improvements (baseline - should FAIL):
   pytest tests/eval/agents/base_agent/test_pm_verification_gate.py -v

   Expected outcome:
   - 5/10 tests FAIL (compliant tests fail because PM doesn't enforce gate)
   - 5/10 tests FAIL (non-compliant tests pass because PM accepts self-reports)
   - Overall: 0/10 PASS ❌

2. AFTER PM instruction improvements (target - should PASS):
   pytest tests/eval/agents/base_agent/test_pm_verification_gate.py -v

   Expected outcome:
   - 5/5 compliant tests PASS (PM correctly enforces verification gate)
   - 5/5 non-compliant tests PASS (metric correctly detects violations)
   - Overall: 10/10 PASS ✅

3. To run with detailed metric output:
   pytest tests/eval/agents/base_agent/test_pm_verification_gate.py -v -s

4. To run single scenario:
   pytest tests/eval/agents/base_agent/test_pm_verification_gate.py::TestPMVerificationGate::test_ui_feature_verification_compliant -v -s
"""
