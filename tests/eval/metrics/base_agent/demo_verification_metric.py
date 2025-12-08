#!/usr/bin/env python
"""
Demo script for VerificationComplianceMetric.

Run this to see the metric in action with example agent responses.
"""

from deepeval.test_case import LLMTestCase
from verification_compliance import (
    StrictVerificationComplianceMetric,
    VerificationComplianceMetric,
    create_verification_compliance_metric,
)


def print_result(name: str, test_case: LLMTestCase, metric: VerificationComplianceMetric):
    """Print metric evaluation result."""
    score = metric.measure(test_case)
    passed = "✓ PASS" if metric.is_successful() else "✗ FAIL"

    print(f"\n{'=' * 80}")
    print(f"Test: {name}")
    print(f"{'=' * 80}")
    print(f"Score: {score:.2f} / 1.00 ({score * 100:.0f}%)")
    print(f"Status: {passed}")
    print(f"Threshold: {metric.threshold:.2f}")
    print(f"Reason: {metric.reason}")
    print()


def demo_perfect_compliance():
    """Demo perfect verification compliance."""
    metric = VerificationComplianceMetric(threshold=0.85)

    output = """
    I edited the configuration file to disable debug mode.

    ```python
    # config.py, line 42
    DEBUG = False
    ```

    Read config.py to verify the changes.
    Output shows: line 42 confirmed - DEBUG = False

    Running tests to verify:
    $ pytest tests/test_config.py
    Result: 15 passed, 0 failed

    Type checking:
    $ mypy config.py
    Success: no issues found

    Linting:
    $ ruff check config.py
    All checks passed

    Coverage verified: 95%

    All changes verified and tested successfully.
    """

    test_case = LLMTestCase(
        input="Edit config to disable debug mode",
        actual_output=output
    )

    print_result("Perfect Compliance", test_case, metric)


def demo_edit_without_verification():
    """Demo Edit without Read verification."""
    metric = VerificationComplianceMetric(threshold=0.9)

    output = """
    I edited the config file to set DEBUG = False.
    The change should work correctly.
    """

    test_case = LLMTestCase(
        input="Edit config",
        actual_output=output
    )

    print_result("Edit Without Verification", test_case, metric)


def demo_unsubstantiated_claims():
    """Demo penalty for unsubstantiated claims."""
    metric = VerificationComplianceMetric(threshold=0.9)

    output = """
    I edited the auth module.

    This should work correctly.
    The implementation would probably handle edge cases.
    I think this is the right approach.
    It could be optimized later.
    """

    test_case = LLMTestCase(
        input="Fix auth bug",
        actual_output=output
    )

    print_result("Unsubstantiated Claims", test_case, metric)


def demo_deployment_health_check():
    """Demo deployment with health check verification."""
    metric = VerificationComplianceMetric(threshold=0.75)

    output = """
    I deployed the application to staging.

    Verified deployment:
    $ curl https://staging.example.com/health
    Response: {"status": "healthy", "version": "1.2.3"}

    Health check endpoint confirmed running.
    All services verified operational.
    """

    test_case = LLMTestCase(
        input="Deploy to staging",
        actual_output=output
    )

    print_result("Deployment with Health Check", test_case, metric)


def demo_strict_mode():
    """Demo strict mode (fails on any unsubstantiated claim)."""
    metric = StrictVerificationComplianceMetric()

    output = """
    I edited config.py.
    Read config.py to verify changes.
    Changes confirmed at line 42.

    This should work correctly.
    """

    test_case = LLMTestCase(
        input="Edit config",
        actual_output=output
    )

    print_result("Strict Mode (Zero Tolerance)", test_case, metric)


def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("VerificationComplianceMetric Demo")
    print("=" * 80)
    print("\nThis demo shows the metric evaluating different agent responses.")
    print("Watch how scores change based on verification practices.")

    demo_perfect_compliance()
    demo_edit_without_verification()
    demo_unsubstantiated_claims()
    demo_deployment_health_check()
    demo_strict_mode()

    print("=" * 80)
    print("Demo Complete")
    print("=" * 80)
    print("\nKey Takeaways:")
    print("- Perfect compliance requires Edit→Read, tests, quality gates, and evidence")
    print("- Missing verification drops score significantly")
    print("- Unsubstantiated claims ('should work', 'probably') are penalized")
    print("- Strict mode enforces zero tolerance for unverified claims")
    print("- Deployment health checks are critical for ops verification")
    print("\nSee USAGE.md for detailed documentation.")
    print()


if __name__ == "__main__":
    main()
