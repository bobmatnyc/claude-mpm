"""

import pytest

# Skip entire module - Factorial example module not found - example code removed
pytestmark = pytest.mark.skip(reason="Factorial example module not found - example code removed")

Comprehensive test suite for the factorial module.

This test suite validates all three factorial implementations (iterative, recursive, wrapper)
including edge cases, boundary conditions, type validation, and error handling.
"""

import sys

import pytest

# from .factorial import factorial, factorial_iterative, factorial_recursive


# Test content commented due to missing imports
'''
class TestFactorialIterative:
    """Test cases for the iterative factorial implementation."""

    def test_basic_cases():
        """Test basic factorial calculations."""
        assert factorial_iterative(0) == 1
        assert factorial_iterative(1) == 1
        assert factorial_iterative(2) == 2
        assert factorial_iterative(3) == 6
        assert factorial_iterative(4) == 24
        assert factorial_iterative(5) == 120
        assert factorial_iterative(10) == 3628800

    def test_medium_numbers():
        """Test factorial of medium-sized numbers."""
        assert factorial_iterative(15) == 1307674368000
        assert factorial_iterative(20) == 2432902008176640000

    def test_float_whole_numbers():
        """Test that float inputs representing whole numbers are accepted."""
        assert factorial_iterative(5.0) == 120
        assert factorial_iterative(0.0) == 1
        assert factorial_iterative(10.0) == 3628800

    def test_negative_numbers():
        """Test that negative numbers raise ValueError."""
        with pytest.raises(
            ValueError, match="Factorial is not defined for negative numbers"
        ):
            factorial_iterative(-1)
        with pytest.raises(
            ValueError, match="Factorial is not defined for negative numbers"
        ):
            factorial_iterative(-10)
        with pytest.raises(ValueError, match="Input must be a whole number"):
            factorial_iterative(-0.5)

    def test_non_integer_floats():
        """Test that non-integer floats raise ValueError."""
        with pytest.raises(ValueError, match="Input must be a whole number"):
            factorial_iterative(3.14)
        with pytest.raises(ValueError, match="Input must be a whole number"):
            factorial_iterative(2.5)
        with pytest.raises(ValueError, match="Input must be a whole number"):
            factorial_iterative(0.1)

    def test_type_errors():
        """Test that invalid types raise TypeError."""
        with pytest.raises(TypeError, match="Input must be a number"):
            factorial_iterative("5")
        with pytest.raises(TypeError, match="Input must be a number"):
            factorial_iterative([5])
        with pytest.raises(TypeError, match="Input must be a number"):
            factorial_iterative(None)
        with pytest.raises(TypeError, match="Input must be a number"):
            factorial_iterative({"n": 5})

    def test_boundary_conditions():
        """Test boundary conditions for the iterative approach."""
        # Test maximum supported value
        assert factorial_iterative(170) > 0  # Should succeed

        # Test value beyond limit
        with pytest.raises(
            ValueError, match="Input too large. Maximum supported value is 170"
        ):
            factorial_iterative(171)
        with pytest.raises(
            ValueError, match="Input too large. Maximum supported value is 170"
        ):
            factorial_iterative(1000)

    def test_large_but_valid_numbers():
        """Test factorial of large numbers within limits."""
        # These should succeed without overflow
        result_50 = factorial_iterative(50)
        assert (
            result_50
            == 30414093201713378043612608166064768844377641568960512000000000000
        )

        result_100 = factorial_iterative(100)
        assert result_100 > 0  # Very large number, just verify it's computed


class TestFactorialRecursive:
    """Test cases for the recursive factorial implementation."""

    def test_basic_cases():
        """Test basic factorial calculations."""
        assert factorial_recursive(0) == 1
        assert factorial_recursive(1) == 1
        assert factorial_recursive(2) == 2
        assert factorial_recursive(3) == 6
        assert factorial_recursive(4) == 24
        assert factorial_recursive(5) == 120
        assert factorial_recursive(10) == 3628800

    def test_medium_numbers():
        """Test factorial of medium-sized numbers."""
        assert factorial_recursive(15) == 1307674368000
        assert factorial_recursive(20) == 2432902008176640000

    def test_float_whole_numbers():
        """Test that float inputs representing whole numbers are accepted."""
        assert factorial_recursive(5.0) == 120
        assert factorial_recursive(0.0) == 1
        assert factorial_recursive(10.0) == 3628800

    def test_negative_numbers():
        """Test that negative numbers raise ValueError."""
        with pytest.raises(ValueError):
            factorial_recursive(-1)
        with pytest.raises(ValueError):
            factorial_recursive(-10)

    def test_non_integer_floats():
        """Test that non-integer floats raise ValueError."""
        with pytest.raises(ValueError, match="Input must be a whole number"):
            factorial_recursive(3.14)
        with pytest.raises(ValueError, match="Input must be a whole number"):
            factorial_recursive(2.5)

    def test_type_errors():
        """Test that invalid types raise TypeError."""
        with pytest.raises(TypeError, match="Input must be a number"):
            factorial_recursive("5")
        with pytest.raises(TypeError, match="Input must be a number"):
            factorial_recursive([5])
        with pytest.raises(TypeError, match="Input must be a number"):
            factorial_recursive(None)

    def test_recursion_limit():
        """Test that large numbers raise ValueError due to recursion limit."""
        # Test value within safe recursion limit
        assert factorial_recursive(100) > 0  # Should succeed

        # Test value beyond recursion limit
        with pytest.raises(ValueError, match="Input too large for recursive approach"):
            factorial_recursive(997)
        with pytest.raises(ValueError, match="Input too large for recursive approach"):
            factorial_recursive(1000)

    def test_consistency_with_iterative():
        """Test that recursive and iterative methods produce same results."""
        for n in range(50):  # Test range where both methods work
            assert factorial_recursive(n) == factorial_iterative(n)


class TestFactorialWrapper:
    """Test cases for the factorial wrapper function."""

    def test_default_method():
        """Test that default method is iterative."""
        assert factorial(5) == 120
        assert factorial(10) == 3628800
        assert factorial(0) == 1

    def test_explicit_iterative():
        """Test explicit iterative method selection."""
        assert factorial(5, method="iterative") == 120
        assert factorial(10, method="iterative") == 3628800

    def test_explicit_recursive():
        """Test explicit recursive method selection."""
        assert factorial(5, method="recursive") == 120
        assert factorial(10, method="recursive") == 3628800

    def test_invalid_method():
        """Test that invalid method raises ValueError."""
        with pytest.raises(
            ValueError,
            match="Invalid method 'invalid'. Choose 'iterative' or 'recursive'.",
        ):
            factorial(5, method="invalid")
        with pytest.raises(
            ValueError,
            match="Invalid method 'ITERATIVE'. Choose 'iterative' or 'recursive'.",
        ):
            factorial(5, method="ITERATIVE")  # Case sensitive

    def test_method_specific_limits():
        """Test that method-specific limits are enforced."""
        # Iterative should handle 170
        assert factorial(170, method="iterative") > 0

        # Iterative should fail at 171
        with pytest.raises(ValueError, match="Input too large"):
            factorial(171, method="iterative")

        # Recursive should fail at 997
        with pytest.raises(ValueError, match="Input too large for recursive approach"):
            factorial(997, method="recursive")

    def test_error_propagation():
        """Test that errors from underlying methods are propagated."""
        # Type errors
        with pytest.raises(TypeError, match="Input must be a number"):
            factorial("5")

        # Value errors
        with pytest.raises(
            ValueError, match="Factorial is not defined for negative numbers"
        ):
            factorial(-5)

        with pytest.raises(ValueError, match="Input must be a whole number"):
            factorial(3.14)

    def test_float_handling():
        """Test that wrapper properly handles float inputs."""
        assert factorial(5.0) == 120
        assert factorial(10.0, method="iterative") == 3628800
        assert factorial(10.0, method="recursive") == 3628800


class TestPerformanceAndStress:
    """Performance and stress tests for factorial implementations."""

    def test_performance_comparison():
        """Compare performance of iterative vs recursive for small numbers."""
        import time

        # Test with a number that both can handle
        n = 100

        # Time iterative
        start = time.time()
        for _ in range(1000):
            factorial_iterative(n)
        iterative_time = time.time() - start

        # Time recursive
        start = time.time()
        for _ in range(1000):
            factorial_recursive(n)
        recursive_time = time.time() - start

        # Both should complete reasonably fast
        assert iterative_time < 1.0  # Should take less than 1 second
        assert recursive_time < 1.0  # Should take less than 1 second

        # Note: Iterative is typically faster for larger n
        print(f"\nPerformance for n={n} (1000 iterations):")
        print(f"Iterative: {iterative_time:.4f}s")
        print(f"Recursive: {recursive_time:.4f}s")

    def test_stress_iterative():
        """Stress test the iterative implementation."""
        # Test multiple large calculations
        large_numbers = [150, 160, 165, 169, 170]
        for n in large_numbers:
            result = factorial_iterative(n)
            assert result > 0
            assert isinstance(result, int)

    def test_edge_case_zero_consistency():
        """Ensure 0! = 1 is consistent across all implementations."""
        assert factorial_iterative(0) == 1
        assert factorial_recursive(0) == 1
        assert factorial(0) == 1
        assert factorial(0, method="iterative") == 1
        assert factorial(0, method="recursive") == 1


class TestDocstringExamples:
    """Test the examples provided in the docstrings."""

    def test_iterative_docstring_examples():
        """Test examples from factorial_iterative docstring."""
        assert factorial_iterative(5) == 120
        assert factorial_iterative(0) == 1
        assert factorial_iterative(1) == 1

    def test_recursive_docstring_examples():
        """Test examples from factorial_recursive docstring."""
        assert factorial_recursive(5) == 120
        assert factorial_recursive(0) == 1
        assert factorial_recursive(1) == 1

    def test_wrapper_docstring_examples():
        """Test examples from factorial wrapper docstring."""
        assert factorial(5) == 120
        assert factorial(5, method="recursive") == 120
        assert factorial(0) == 1
        assert factorial(10.0) == 3628800


# Test runner for when this file is executed directly
'''
if __name__ == "__main__":
    # Run with verbose output and coverage if available
    # pytest.main([__file__, "-v", "--tb=short"])
    pass