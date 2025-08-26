#!/usr/bin/env python3
"""
Validation-First Development Example

This module demonstrates the validation-first pattern from awesome-claude-code.
Key principles:
1. Validate with real data before writing tests
2. Track ALL validation failures
3. Report comprehensive results
4. Use external research after 3 failures
"""

import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Third-party imports
from loguru import logger

# Sample input data for validation
SAMPLE_DATA = {
    "users": [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
    ],
    "transactions": [
        {"id": 1, "user_id": 1, "amount": 100.50, "status": "completed"},
        {"id": 2, "user_id": 2, "amount": 250.00, "status": "pending"},
    ],
}


@dataclass
class ValidationResult:
    """Result of a validation test."""

    test_name: str
    passed: bool
    expected: Any
    actual: Any
    error_message: Optional[str] = None


class DataProcessor:
    """Example data processor with validation-first approach."""

    def __init__(self):
        self.validation_attempts = 0
        self.external_research_used = False

    def process_user_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process user data and return summary."""
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")

        users = data.get("users", [])
        if not users:
            return {"user_count": 0, "users": []}

        # Process users
        processed_users = []
        for user in users:
            processed = {
                "id": user["id"],
                "display_name": user["name"].upper(),
                "email_domain": user["email"].split("@")[1],
            }
            processed_users.append(processed)

        return {"user_count": len(processed_users), "users": processed_users}

    def calculate_transaction_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate transaction summary statistics."""
        transactions = data.get("transactions", [])

        if not transactions:
            return {
                "total_amount": 0,
                "completed_count": 0,
                "pending_count": 0,
                "average_amount": 0,
            }

        total_amount = sum(t["amount"] for t in transactions)
        completed = [t for t in transactions if t["status"] == "completed"]
        pending = [t for t in transactions if t["status"] == "pending"]

        return {
            "total_amount": total_amount,
            "completed_count": len(completed),
            "pending_count": len(pending),
            "average_amount": total_amount / len(transactions),
        }

    def validate_data_integrity(self, data: Dict[str, Any]) -> bool:
        """Validate that all user_ids in transactions exist."""
        users = data.get("users", [])
        transactions = data.get("transactions", [])

        user_ids = {u["id"] for u in users}
        transaction_user_ids = {t["user_id"] for t in transactions}

        return transaction_user_ids.issubset(user_ids)


def run_validation_tests(processor: DataProcessor) -> List[ValidationResult]:
    """Run all validation tests and collect results."""
    all_validation_results = []

    # Test 1: Basic user data processing
    test1_result = ValidationResult(
        test_name="Basic user data processing", passed=False, expected=None, actual=None
    )

    try:
        result = processor.process_user_data(SAMPLE_DATA)
        expected = {
            "user_count": 2,
            "users": [
                {"id": 1, "display_name": "ALICE", "email_domain": "example.com"},
                {"id": 2, "display_name": "BOB", "email_domain": "example.com"},
            ],
        }

        test1_result.expected = expected
        test1_result.actual = result
        test1_result.passed = result == expected

        if not test1_result.passed:
            test1_result.error_message = f"Expected {expected}, got {result}"

    except Exception as e:
        test1_result.error_message = f"Exception: {e!s}"

    all_validation_results.append(test1_result)

    # Test 2: Transaction summary calculation
    test2_result = ValidationResult(
        test_name="Transaction summary calculation",
        passed=False,
        expected=None,
        actual=None,
    )

    try:
        result = processor.calculate_transaction_summary(SAMPLE_DATA)
        expected = {
            "total_amount": 350.50,
            "completed_count": 1,
            "pending_count": 1,
            "average_amount": 175.25,
        }

        test2_result.expected = expected
        test2_result.actual = result
        test2_result.passed = result == expected

        if not test2_result.passed:
            test2_result.error_message = f"Expected {expected}, got {result}"

    except Exception as e:
        test2_result.error_message = f"Exception: {e!s}"

    all_validation_results.append(test2_result)

    # Test 3: Data integrity validation
    test3_result = ValidationResult(
        test_name="Data integrity validation", passed=False, expected=True, actual=None
    )

    try:
        result = processor.validate_data_integrity(SAMPLE_DATA)
        test3_result.actual = result
        test3_result.passed = result

        if not test3_result.passed:
            test3_result.error_message = "Data integrity check failed"

    except Exception as e:
        test3_result.error_message = f"Exception: {e!s}"

    all_validation_results.append(test3_result)

    # Test 4: Empty data handling
    test4_result = ValidationResult(
        test_name="Empty data handling",
        passed=False,
        expected={"user_count": 0, "users": []},
        actual=None,
    )

    try:
        result = processor.process_user_data({"users": []})
        test4_result.actual = result
        test4_result.passed = result == test4_result.expected

        if not test4_result.passed:
            test4_result.error_message = (
                f"Expected {test4_result.expected}, got {result}"
            )

    except Exception as e:
        test4_result.error_message = f"Exception: {e!s}"

    all_validation_results.append(test4_result)

    # Test 5: Error handling for invalid input
    test5_result = ValidationResult(
        test_name="Error handling for invalid input",
        passed=False,
        expected="ValueError",
        actual=None,
    )

    try:
        result = processor.process_user_data("invalid")
        test5_result.actual = "No exception raised"
        test5_result.passed = False
        test5_result.error_message = "Expected ValueError, but no exception was raised"
    except ValueError:
        test5_result.actual = "ValueError"
        test5_result.passed = True
    except Exception as e:
        test5_result.actual = type(e).__name__
        test5_result.error_message = f"Expected ValueError, got {type(e).__name__}"

    all_validation_results.append(test5_result)

    return all_validation_results


def simulate_external_research():
    """Simulate using external research after 3 failures."""
    logger.info("🔍 Using external research tools after 3 validation failures...")
    logger.info("  - Searching for 'Python data validation best practices'")
    logger.info("  - Reviewing similar implementations on GitHub")
    logger.info("  - Checking Stack Overflow for common patterns")
    logger.info("📚 Research findings incorporated into implementation")


if __name__ == "__main__":
    # Initialize processor
    processor = DataProcessor()

    # Run validation tests
    logger.info("🧪 Starting validation tests with real data...")
    validation_results = run_validation_tests(processor)

    # Collect failures
    all_validation_failures = []
    total_tests = len(validation_results)

    for result in validation_results:
        if not result.passed:
            failure_msg = f"{result.test_name}: {result.error_message}"
            all_validation_failures.append(failure_msg)
            logger.error(f"  ❌ {failure_msg}")
        else:
            logger.success(f"  ✅ {result.test_name}: PASSED")

    # Check if we need external research (3+ failures)
    if len(all_validation_failures) >= 3 and not processor.external_research_used:
        simulate_external_research()
        processor.external_research_used = True
        # In real implementation, we would retry after research

    # Final validation report
    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)

    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for i, failure in enumerate(all_validation_failures, 1):
            print(f"  {i}. {failure}")
        print("\nNext steps:")
        print("  1. Fix the failing validations")
        print("  2. Ensure all tests pass with real data")
        print("  3. Only then proceed to write formal tests")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("\nValidation successful! You can now:")
        print("  1. Write formal unit tests based on these validations")
        print("  2. Add edge case testing")
        print("  3. Implement performance optimizations")
        sys.exit(0)
