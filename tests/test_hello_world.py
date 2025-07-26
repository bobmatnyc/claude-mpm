#!/usr/bin/env python3
"""Simple hello world test for claude-mpm."""

import unittest


def hello_world():
    """Return a hello world message."""
    return "Hello, World!"


class TestHelloWorld(unittest.TestCase):
    """Test cases for hello world function."""
    
    def test_hello_world_returns_correct_message(self):
        """Test that hello_world returns the expected message."""
        expected = "Hello, World!"
        actual = hello_world()
        self.assertEqual(expected, actual)
    
    def test_hello_world_returns_string(self):
        """Test that hello_world returns a string type."""
        result = hello_world()
        self.assertIsInstance(result, str)
    
    def test_hello_world_not_empty(self):
        """Test that hello_world doesn't return empty string."""
        result = hello_world()
        self.assertTrue(len(result) > 0)


if __name__ == "__main__":
    unittest.main()