"""Unit tests for the hello_world() function."""

import io
import sys
import unittest
from contextlib import redirect_stdout

# Add the parent directory to the path to import hello_world
sys.path.insert(0, '/Users/masa/Projects/claude-mpm')
from hello_world import hello_world


class TestHelloWorld(unittest.TestCase):
    """Test cases for the hello_world function."""

    def test_hello_world_output(self):
        """Test that hello_world() prints the correct message."""
        # Capture stdout
        captured_output = io.StringIO()
        
        # Redirect stdout to capture the print output
        with redirect_stdout(captured_output):
            hello_world()
        
        # Get the captured output
        output = captured_output.getvalue()
        
        # Verify the output
        self.assertEqual(output, "Hello, World!\n")
    
    def test_hello_world_returns_none(self):
        """Test that hello_world() returns None."""
        # Redirect stdout to suppress output during test
        with redirect_stdout(io.StringIO()):
            result = hello_world()
        
        # Verify the function returns None
        self.assertIsNone(result)
    
    def test_hello_world_no_side_effects(self):
        """Test that hello_world() can be called multiple times without issues."""
        captured_output = io.StringIO()
        
        with redirect_stdout(captured_output):
            # Call the function multiple times
            hello_world()
            hello_world()
            hello_world()
        
        output = captured_output.getvalue()
        
        # Verify each call produces the expected output
        expected_output = "Hello, World!\nHello, World!\nHello, World!\n"
        self.assertEqual(output, expected_output)


if __name__ == "__main__":
    unittest.main()