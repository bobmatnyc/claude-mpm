"""
Comprehensive unit tests for the calculator module.

This test suite provides complete coverage of all functions in the calculator module,
including normal operations, edge cases, and error conditions.
"""

import unittest
from calculator import add, subtract, multiply, divide


class TestCalculator(unittest.TestCase):
    """Test suite for calculator module functions."""
    
    # Tests for add function
    def test_add_positive_integers(self):
        """Test adding two positive integers."""
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(add(10, 20), 30)
        self.assertEqual(add(1, 1), 2)
    
    def test_add_negative_integers(self):
        """Test adding negative integers."""
        self.assertEqual(add(-2, -3), -5)
        self.assertEqual(add(-5, 3), -2)
        self.assertEqual(add(5, -3), 2)
    
    def test_add_floats(self):
        """Test adding floating point numbers."""
        self.assertAlmostEqual(add(2.5, 3.7), 6.2)
        self.assertAlmostEqual(add(0.1, 0.2), 0.3, places=7)
        self.assertAlmostEqual(add(-1.5, 2.5), 1.0)
    
    def test_add_mixed_types(self):
        """Test adding integers and floats."""
        self.assertEqual(add(2, 3.5), 5.5)
        self.assertEqual(add(3.5, 2), 5.5)
        self.assertEqual(add(-2, 3.5), 1.5)
    
    def test_add_zero(self):
        """Test adding with zero."""
        self.assertEqual(add(0, 5), 5)
        self.assertEqual(add(5, 0), 5)
        self.assertEqual(add(0, 0), 0)
        self.assertEqual(add(0, -5), -5)
    
    # Tests for subtract function
    def test_subtract_positive_integers(self):
        """Test subtracting positive integers."""
        self.assertEqual(subtract(5, 3), 2)
        self.assertEqual(subtract(20, 10), 10)
        self.assertEqual(subtract(3, 3), 0)
    
    def test_subtract_negative_integers(self):
        """Test subtracting negative integers."""
        self.assertEqual(subtract(-5, -3), -2)
        self.assertEqual(subtract(-3, -5), 2)
        self.assertEqual(subtract(5, -3), 8)
        self.assertEqual(subtract(-5, 3), -8)
    
    def test_subtract_floats(self):
        """Test subtracting floating point numbers."""
        self.assertAlmostEqual(subtract(5.7, 2.2), 3.5)
        self.assertAlmostEqual(subtract(0.3, 0.1), 0.2, places=7)
        self.assertAlmostEqual(subtract(-1.5, -2.5), 1.0)
    
    def test_subtract_mixed_types(self):
        """Test subtracting integers and floats."""
        self.assertEqual(subtract(5, 2.5), 2.5)
        self.assertEqual(subtract(2.5, 2), 0.5)
        self.assertEqual(subtract(-2, 3.5), -5.5)
    
    def test_subtract_zero(self):
        """Test subtracting with zero."""
        self.assertEqual(subtract(5, 0), 5)
        self.assertEqual(subtract(0, 5), -5)
        self.assertEqual(subtract(0, 0), 0)
        self.assertEqual(subtract(0, -5), 5)
    
    # Tests for multiply function
    def test_multiply_positive_integers(self):
        """Test multiplying positive integers."""
        self.assertEqual(multiply(2, 3), 6)
        self.assertEqual(multiply(5, 4), 20)
        self.assertEqual(multiply(7, 1), 7)
    
    def test_multiply_negative_integers(self):
        """Test multiplying negative integers."""
        self.assertEqual(multiply(-2, -3), 6)
        self.assertEqual(multiply(-2, 3), -6)
        self.assertEqual(multiply(2, -3), -6)
    
    def test_multiply_floats(self):
        """Test multiplying floating point numbers."""
        self.assertAlmostEqual(multiply(2.5, 4.0), 10.0)
        self.assertAlmostEqual(multiply(0.1, 0.2), 0.02)
        self.assertAlmostEqual(multiply(-1.5, 2.0), -3.0)
    
    def test_multiply_mixed_types(self):
        """Test multiplying integers and floats."""
        self.assertEqual(multiply(2, 2.5), 5.0)
        self.assertEqual(multiply(2.5, 2), 5.0)
        self.assertEqual(multiply(-3, 1.5), -4.5)
    
    def test_multiply_zero(self):
        """Test multiplying with zero."""
        self.assertEqual(multiply(0, 5), 0)
        self.assertEqual(multiply(5, 0), 0)
        self.assertEqual(multiply(0, 0), 0)
        self.assertEqual(multiply(0, -5), 0)
        self.assertEqual(multiply(0, 3.14), 0)
    
    def test_multiply_one(self):
        """Test multiplying with one (identity property)."""
        self.assertEqual(multiply(1, 5), 5)
        self.assertEqual(multiply(5, 1), 5)
        self.assertEqual(multiply(1, -5), -5)
        self.assertEqual(multiply(1, 3.14), 3.14)
    
    # Tests for divide function
    def test_divide_positive_integers(self):
        """Test dividing positive integers."""
        self.assertEqual(divide(6, 2), 3)
        self.assertEqual(divide(20, 4), 5)
        self.assertEqual(divide(7, 7), 1)
    
    def test_divide_negative_numbers(self):
        """Test dividing negative numbers."""
        self.assertEqual(divide(-6, -2), 3)
        self.assertEqual(divide(-6, 2), -3)
        self.assertEqual(divide(6, -2), -3)
    
    def test_divide_floats(self):
        """Test dividing floating point numbers."""
        self.assertAlmostEqual(divide(7.5, 2.5), 3.0)
        self.assertAlmostEqual(divide(1.0, 3.0), 0.333333, places=5)
        self.assertAlmostEqual(divide(-4.5, 1.5), -3.0)
    
    def test_divide_mixed_types(self):
        """Test dividing integers and floats."""
        self.assertEqual(divide(5, 2.0), 2.5)
        self.assertEqual(divide(5.0, 2), 2.5)
        self.assertEqual(divide(7, 2), 3.5)
    
    def test_divide_result_is_float(self):
        """Test that division always returns a float."""
        result = divide(4, 2)
        self.assertIsInstance(result, float)
        self.assertEqual(result, 2.0)
    
    def test_divide_by_one(self):
        """Test dividing by one (identity property)."""
        self.assertEqual(divide(5, 1), 5)
        self.assertEqual(divide(-5, 1), -5)
        self.assertEqual(divide(3.14, 1), 3.14)
    
    def test_divide_zero_dividend(self):
        """Test dividing zero by non-zero numbers."""
        self.assertEqual(divide(0, 5), 0)
        self.assertEqual(divide(0, -5), 0)
        self.assertEqual(divide(0, 3.14), 0)
    
    def test_divide_by_zero_raises_error(self):
        """Test that dividing by zero raises ValueError."""
        with self.assertRaises(ValueError) as context:
            divide(5, 0)
        self.assertEqual(str(context.exception), "Cannot divide by zero")
        
        with self.assertRaises(ValueError) as context:
            divide(-5, 0)
        self.assertEqual(str(context.exception), "Cannot divide by zero")
        
        with self.assertRaises(ValueError) as context:
            divide(0, 0)
        self.assertEqual(str(context.exception), "Cannot divide by zero")
        
        with self.assertRaises(ValueError) as context:
            divide(3.14, 0)
        self.assertEqual(str(context.exception), "Cannot divide by zero")
        
        with self.assertRaises(ValueError) as context:
            divide(5, 0.0)
        self.assertEqual(str(context.exception), "Cannot divide by zero")
    
    # Edge cases and special values
    def test_very_large_numbers(self):
        """Test operations with very large numbers."""
        large1 = 10**100
        large2 = 10**100
        
        self.assertEqual(add(large1, large2), 2 * 10**100)
        self.assertEqual(subtract(large1, large2), 0)
        self.assertEqual(multiply(large1, 2), 2 * 10**100)
        self.assertEqual(divide(large1, large1), 1.0)
    
    def test_very_small_numbers(self):
        """Test operations with very small numbers."""
        small1 = 10**-100
        small2 = 10**-100
        
        self.assertAlmostEqual(add(small1, small2), 2 * 10**-100)
        self.assertAlmostEqual(subtract(small1, small2), 0)
        self.assertAlmostEqual(multiply(small1, 10**100), 1.0)
        self.assertAlmostEqual(divide(small1, small1), 1.0)
    
    def test_precision_edge_cases(self):
        """Test floating point precision edge cases."""
        # Test known floating point precision issues
        result = add(0.1, 0.2)
        self.assertAlmostEqual(result, 0.3, places=15)
        
        # Test subtraction that should equal zero
        result = subtract(1.1, 1.1)
        self.assertEqual(result, 0)
        
        # Test division that results in repeating decimal
        result = divide(1, 3)
        self.assertAlmostEqual(result, 0.333333333333, places=10)


if __name__ == '__main__':
    unittest.main()