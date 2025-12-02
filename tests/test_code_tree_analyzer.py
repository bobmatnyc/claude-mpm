#!/usr/bin/env python3
"""
Test Code Tree Analyzer
========================

WHY: Verify that the code tree analyzer correctly parses and analyzes
Python code structures with proper event emission.

DESIGN DECISIONS:
- Test AST parsing for Python files
- Verify event emission functionality
- Test caching mechanisms
- Validate tree structure building
"""

# Add src to path for testing
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.tools.code_tree_analyzer import CodeTreeAnalyzer, PythonAnalyzer
from claude_mpm.tools.code_tree_builder import CodeTreeBuilder
from claude_mpm.tools.code_tree_events import CodeNodeEvent, CodeTreeEventEmitter


class TestPythonAnalyzer(unittest.TestCase):
    """Test Python AST analyzer functionality."""

    def setUp(self):
        """Create test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_analyze_simple_function(self):
        """Test analyzing a simple Python function."""
        # Create test file
        test_file = self.test_dir / "test.py"
        test_file.write_text(
            '''
def hello_world():
    """Say hello."""
    print("Hello, World!")

def add(a, b):
    """Add two numbers."""
    return a + b
'''
        )

        # Analyze file
        analyzer = PythonAnalyzer()
        nodes = analyzer.analyze_file(test_file)

        # Verify results
        self.assertEqual(len(nodes), 2)

        # Check first function
        hello = nodes[0]
        self.assertEqual(hello.node_type, "function")
        self.assertEqual(hello.name, "hello_world")
        self.assertTrue(hello.has_docstring)
        self.assertEqual(hello.line_start, 2)

        # Check second function
        add_func = nodes[1]
        self.assertEqual(add_func.node_type, "function")
        self.assertEqual(add_func.name, "add")
        self.assertTrue(add_func.has_docstring)

    def test_analyze_class_with_methods(self):
        """Test analyzing a class with methods."""
        test_file = self.test_dir / "test_class.py"
        test_file.write_text(
            '''
class Calculator:
    """A simple calculator class."""

    def __init__(self):
        """Initialize calculator."""
        self.result = 0

    def add(self, value):
        """Add a value."""
        self.result += value
        return self.result

    @property
    def get_result(self):
        """Get the result."""
        return self.result
'''
        )

        analyzer = PythonAnalyzer()
        nodes = analyzer.analyze_file(test_file)

        # Should find 1 class and 3 methods
        classes = [n for n in nodes if n.node_type == "class"]
        methods = [n for n in nodes if n.node_type == "method"]

        self.assertEqual(len(classes), 1)
        self.assertEqual(len(methods), 3)

        # Check class
        calc_class = classes[0]
        self.assertEqual(calc_class.name, "Calculator")
        self.assertTrue(calc_class.has_docstring)

        # Check decorators
        prop_method = next(m for m in methods if m.name == "get_result")
        self.assertIn("property", prop_method.decorators)

    def test_complexity_calculation(self):
        """Test complexity calculation for functions."""
        test_file = self.test_dir / "complex.py"
        test_file.write_text(
            '''
def complex_function(x):
    """A function with high complexity."""
    if x > 0:
        if x > 10:
            for i in range(x):
                if i % 2 == 0:
                    print(i)
                else:
                    continue
        elif x > 5:
            while x > 0:
                x -= 1
    else:
        try:
            return 1 / x
        except:
            return 0
'''
        )

        analyzer = PythonAnalyzer()
        nodes = analyzer.analyze_file(test_file)

        self.assertEqual(len(nodes), 1)
        func = nodes[0]
        self.assertGreater(func.complexity, 5)  # Should have high complexity


class TestCodeTreeBuilder(unittest.TestCase):
    """Test code tree builder functionality."""

    def setUp(self):
        """Create test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

        # Create test directory structure
        (self.test_dir / "src").mkdir()
        (self.test_dir / "src" / "module1.py").write_text("def func1(): pass")
        (self.test_dir / "src" / "module2.py").write_text("def func2(): pass")
        (self.test_dir / "tests").mkdir()
        (self.test_dir / "tests" / "test_module.py").write_text("def test_func(): pass")
        (self.test_dir / "node_modules").mkdir()
        (self.test_dir / "node_modules" / "package.js").write_text("// ignored")
        (self.test_dir / ".gitignore").write_text("node_modules/\n*.pyc")

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_build_tree_structure(self):
        """Test building directory tree structure."""
        builder = CodeTreeBuilder()
        tree = builder.build_tree(
            self.test_dir, file_extensions=[".py"], use_gitignore=True
        )

        # Check root
        self.assertEqual(tree.type, "directory")
        self.assertGreater(len(tree.children), 0)

        # Check that node_modules is ignored
        child_names = [c.name for c in tree.children]
        self.assertNotIn("node_modules", child_names)

        # Check that src and tests are included
        self.assertIn("src", child_names)
        self.assertIn("tests", child_names)

        # Check statistics
        stats = builder.get_stats()
        self.assertEqual(stats["files_found"], 3)  # 2 in src, 1 in tests
        self.assertIn("python", stats["languages"])

    def test_gitignore_parsing(self):
        """Test .gitignore pattern matching."""
        from claude_mpm.tools.code_tree_analyzer import GitignoreManager

        manager = GitignoreManager()

        # Test that node_modules is ignored
        self.assertTrue(
            manager.should_ignore(self.test_dir / "node_modules", self.test_dir)
        )
        self.assertTrue(
            manager.should_ignore(
                self.test_dir / "node_modules" / "package.js", self.test_dir
            )
        )

        # Test that pyc files are ignored
        self.assertTrue(
            manager.should_ignore(self.test_dir / "test.pyc", self.test_dir)
        )

        # Test that py files are not ignored
        self.assertFalse(
            manager.should_ignore(self.test_dir / "test.py", self.test_dir)
        )


class TestCodeTreeAnalyzer(unittest.TestCase):
    """Test the main code tree analyzer."""

    def setUp(self):
        """Create test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

        # Create test Python file
        test_file = self.test_dir / "test.py"
        test_file.write_text(
            """
class TestClass:
    def method1(self):
        return 1

def test_function():
    return 2
"""
        )

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    @patch("claude_mpm.tools.code_tree_events.socketio")
    def test_analyze_directory(self, mock_socketio):
        """Test analyzing a directory with event emission."""
        # Create analyzer without events
        analyzer = CodeTreeAnalyzer(emit_events=False)

        # Analyze directory
        result = analyzer.analyze_directory(self.test_dir, languages=["python"])

        # Check results
        self.assertIn("tree", result)
        self.assertIn("nodes", result)
        self.assertIn("stats", result)

        # Check statistics
        stats = result["stats"]
        self.assertEqual(stats["files_processed"], 1)
        self.assertEqual(stats["classes"], 1)
        self.assertEqual(stats["functions"], 2)  # 1 function + 1 method

        # Check tree structure
        tree = result["tree"]
        self.assertEqual(tree["type"], "directory")

    def test_caching(self):
        """Test that analysis results are cached."""
        cache_dir = self.test_dir / ".cache"
        analyzer = CodeTreeAnalyzer(emit_events=False, cache_dir=cache_dir)

        # First analysis
        result1 = analyzer.analyze_directory(self.test_dir)
        nodes1 = result1["nodes"]

        # Second analysis should use cache
        result2 = analyzer.analyze_directory(self.test_dir)
        nodes2 = result2["nodes"]

        # Results should be identical
        self.assertEqual(len(nodes1), len(nodes2))

        # Cache should exist
        self.assertTrue(cache_dir.exists())
        cache_file = cache_dir / "code_tree_cache.json"
        self.assertTrue(cache_file.exists())


class TestEventEmitter(unittest.TestCase):
    """Test event emission functionality."""

    @patch("claude_mpm.tools.code_tree_events.socketio.Client")
    def test_event_batching(self, mock_client_class):
        """Test that events are batched correctly."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        emitter = CodeTreeEventEmitter(
            socketio_url="http://test:8765", batch_size=3, batch_timeout=0.1
        )

        # Emit multiple node events
        for i in range(5):
            node = CodeNodeEvent(
                file_path=f"test{i}.py",
                node_type="function",
                name=f"func{i}",
                line_start=i,
                line_end=i + 10,
            )
            emitter.emit_node(node)

        # Wait for batch timeout
        import time

        time.sleep(0.2)

        # Check statistics
        stats = emitter.get_stats()
        self.assertEqual(stats["nodes_found"], 5)


if __name__ == "__main__":
    unittest.main()
