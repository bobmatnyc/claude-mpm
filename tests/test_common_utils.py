"""
Comprehensive test coverage for common utility functions.
This ensures behavior is preserved when replacing duplicate implementations.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from claude_mpm.utils.common import (
    check_command_exists,
    deprecated,
    ensure_path_exists,
    find_files,
    get_env_bool,
    get_env_int,
    get_env_list,
    get_file_size,
    import_from_string,
    load_json_safe,
    load_yaml_safe,
    read_file_if_exists,
    run_command_safe,
    safe_import,
    save_json_safe,
    save_yaml_safe,
    write_file_safe,
)


class TestJSONUtilities(unittest.TestCase):
    """Test JSON utility functions."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_file = self.temp_dir / "test.json"

    def tearDown(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            import shutil

            shutil.rmtree(self.temp_dir)

    def test_load_json_safe_valid(self):
        """Test loading valid JSON."""
        test_data = {"key": "value", "number": 42}
        self.test_file.write_text(json.dumps(test_data))

        result = load_json_safe(self.test_file)
        self.assertEqual(result, test_data)

    def test_load_json_safe_missing_file(self):
        """Test loading from missing file."""
        result = load_json_safe(self.temp_dir / "missing.json")
        self.assertEqual(result, {})

        # With custom default
        result = load_json_safe(
            self.temp_dir / "missing.json", default={"default": True}
        )
        self.assertEqual(result, {"default": True})

    def test_load_json_safe_invalid_json(self):
        """Test loading invalid JSON."""
        self.test_file.write_text("not valid json")

        result = load_json_safe(self.test_file)
        self.assertEqual(result, {})

    def test_save_json_safe(self):
        """Test saving JSON safely."""
        test_data = {"key": "value", "list": [1, 2, 3]}

        success = save_json_safe(self.test_file, test_data)
        self.assertTrue(success)
        self.assertTrue(self.test_file.exists())

        # Verify content
        loaded = json.loads(self.test_file.read_text())
        self.assertEqual(loaded, test_data)

    def test_save_json_safe_creates_parents(self):
        """Test that parent directories are created."""
        nested_file = self.temp_dir / "nested" / "dir" / "test.json"
        test_data = {"test": True}

        success = save_json_safe(nested_file, test_data)
        self.assertTrue(success)
        self.assertTrue(nested_file.exists())


class TestYAMLUtilities(unittest.TestCase):
    """Test YAML utility functions."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_file = self.temp_dir / "test.yaml"

    def tearDown(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            import shutil

            shutil.rmtree(self.temp_dir)

    def test_load_yaml_safe_valid(self):
        """Test loading valid YAML."""
        test_data = {"key": "value", "list": [1, 2, 3]}
        self.test_file.write_text(yaml.dump(test_data))

        result = load_yaml_safe(self.test_file)
        self.assertEqual(result, test_data)

    def test_load_yaml_safe_missing_file(self):
        """Test loading from missing file."""
        result = load_yaml_safe(self.temp_dir / "missing.yaml")
        self.assertEqual(result, {})

    def test_save_yaml_safe(self):
        """Test saving YAML safely."""
        test_data = {"key": "value", "nested": {"inner": True}}

        success = save_yaml_safe(self.test_file, test_data)
        self.assertTrue(success)
        self.assertTrue(self.test_file.exists())

        # Verify content
        loaded = yaml.safe_load(self.test_file.read_text())
        self.assertEqual(loaded, test_data)


class TestPathUtilities(unittest.TestCase):
    """Test path and file utility functions."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            import shutil

            shutil.rmtree(self.temp_dir)

    def test_ensure_path_exists_directory(self):
        """Test ensuring directory exists."""
        test_dir = self.temp_dir / "test_dir"
        self.assertFalse(test_dir.exists())

        result = ensure_path_exists(test_dir)
        self.assertTrue(result)
        self.assertTrue(test_dir.exists())
        self.assertTrue(test_dir.is_dir())

    def test_ensure_path_exists_file_parent(self):
        """Test ensuring file parent directory exists."""
        test_file = self.temp_dir / "nested" / "file.txt"

        result = ensure_path_exists(test_file, is_file=True)
        self.assertTrue(result)
        self.assertTrue(test_file.parent.exists())
        self.assertFalse(test_file.exists())  # File itself not created

    def test_read_file_if_exists(self):
        """Test reading file if it exists."""
        test_file = self.temp_dir / "test.txt"
        test_content = "test content"
        test_file.write_text(test_content)

        result = read_file_if_exists(test_file)
        self.assertEqual(result, test_content)

    def test_read_file_if_exists_missing(self):
        """Test reading missing file."""
        result = read_file_if_exists(self.temp_dir / "missing.txt")
        self.assertEqual(result, "")

        # With custom default
        result = read_file_if_exists(self.temp_dir / "missing.txt", default="default")
        self.assertEqual(result, "default")

    def test_write_file_safe(self):
        """Test writing file safely."""
        test_file = self.temp_dir / "test.txt"
        test_content = "test content"

        success = write_file_safe(test_file, test_content)
        self.assertTrue(success)
        self.assertTrue(test_file.exists())
        self.assertEqual(test_file.read_text(), test_content)

    def test_get_file_size(self):
        """Test getting file size."""
        test_file = self.temp_dir / "test.txt"
        test_content = "12345"
        test_file.write_text(test_content)

        size = get_file_size(test_file)
        self.assertEqual(size, len(test_content))

    def test_get_file_size_missing(self):
        """Test getting size of missing file."""
        size = get_file_size(self.temp_dir / "missing.txt")
        self.assertEqual(size, 0)

    def test_find_files(self):
        """Test finding files with pattern."""
        # Create test files
        (self.temp_dir / "test1.txt").write_text("")
        (self.temp_dir / "test2.txt").write_text("")
        (self.temp_dir / "other.py").write_text("")
        subdir = self.temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "test3.txt").write_text("")

        # Find all txt files recursively
        txt_files = find_files(self.temp_dir, "*.txt")
        self.assertEqual(len(txt_files), 3)

        # Find txt files non-recursively
        txt_files = find_files(self.temp_dir, "*.txt", recursive=False)
        self.assertEqual(len(txt_files), 2)


class TestSubprocessUtilities(unittest.TestCase):
    """Test subprocess utility functions."""

    def test_run_command_safe_success(self):
        """Test running successful command."""
        result = run_command_safe(["echo", "test"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("test", result.stdout)

    def test_run_command_safe_failure(self):
        """Test handling command failure."""
        with self.assertRaises(subprocess.CalledProcessError):
            run_command_safe(["false"], check=True)

    def test_run_command_safe_timeout(self):
        """Test command timeout."""
        with self.assertRaises(subprocess.TimeoutExpired):
            run_command_safe(["sleep", "10"], timeout=0.1)

    def test_check_command_exists(self):
        """Test checking if command exists."""
        # Common commands that should exist
        self.assertTrue(check_command_exists("echo"))
        self.assertTrue(check_command_exists("ls"))

        # Command that shouldn't exist
        self.assertFalse(check_command_exists("nonexistent_command_xyz"))


class TestEnvironmentUtilities(unittest.TestCase):
    """Test environment variable utility functions."""

    def test_get_env_bool(self):
        """Test getting boolean from environment."""
        # Test true values
        for value in ["1", "true", "yes", "on", "TRUE", "YES", "ON"]:
            with patch.dict(os.environ, {"TEST_VAR": value}):
                self.assertTrue(get_env_bool("TEST_VAR"))

        # Test false values
        for value in ["0", "false", "no", "off", ""]:
            with patch.dict(os.environ, {"TEST_VAR": value}):
                self.assertFalse(get_env_bool("TEST_VAR"))

        # Test default
        self.assertFalse(get_env_bool("MISSING_VAR"))
        self.assertTrue(get_env_bool("MISSING_VAR", default=True))

    def test_get_env_int(self):
        """Test getting integer from environment."""
        with patch.dict(os.environ, {"TEST_VAR": "42"}):
            self.assertEqual(get_env_int("TEST_VAR"), 42)

        with patch.dict(os.environ, {"TEST_VAR": "invalid"}):
            self.assertEqual(get_env_int("TEST_VAR"), 0)
            self.assertEqual(get_env_int("TEST_VAR", default=10), 10)

    def test_get_env_list(self):
        """Test getting list from environment."""
        with patch.dict(os.environ, {"TEST_VAR": "a,b,c"}):
            self.assertEqual(get_env_list("TEST_VAR"), ["a", "b", "c"])

        with patch.dict(os.environ, {"TEST_VAR": "a;b;c"}):
            self.assertEqual(get_env_list("TEST_VAR", separator=";"), ["a", "b", "c"])

        # Test with spaces
        with patch.dict(os.environ, {"TEST_VAR": " a , b , c "}):
            self.assertEqual(get_env_list("TEST_VAR"), ["a", "b", "c"])

        # Test default
        self.assertEqual(get_env_list("MISSING_VAR"), [])
        self.assertEqual(get_env_list("MISSING_VAR", default=["x"]), ["x"])


class TestImportUtilities(unittest.TestCase):
    """Test import utility functions."""

    def test_safe_import_success(self):
        """Test successful import."""
        module = safe_import("os")
        self.assertIsNotNone(module)
        self.assertEqual(module.__name__, "os")

    def test_safe_import_failure(self):
        """Test failed import with fallback."""
        module = safe_import("nonexistent_module")
        self.assertIsNone(module)

        module = safe_import("nonexistent_module", fallback="fallback")
        self.assertEqual(module, "fallback")

    def test_import_from_string(self):
        """Test importing from string path."""
        # Import a class
        Path_class = import_from_string("pathlib.Path")
        self.assertEqual(Path_class, Path)

        # Import a function
        join_func = import_from_string("os.path.join")
        self.assertEqual(join_func, os.path.join)

        # Failed import
        result = import_from_string("nonexistent.module.Class")
        self.assertIsNone(result)


class TestDeprecation(unittest.TestCase):
    """Test deprecation decorator."""

    def test_deprecated_decorator(self):
        """Test that deprecated decorator warns."""

        @deprecated()
        def old_function():
            return "result"

        with self.assertWarns(DeprecationWarning):
            result = old_function()
            self.assertEqual(result, "result")

    def test_deprecated_with_replacement(self):
        """Test deprecated decorator with replacement."""

        @deprecated(replacement="new_function")
        def old_function():
            return "result"

        with self.assertWarns(DeprecationWarning) as cm:
            old_function()
            self.assertIn("new_function", str(cm.warnings[0].message))


class TestPerformanceComparison(unittest.TestCase):
    """Compare performance of old patterns vs new utilities."""

    def test_json_loading_performance(self):
        """Test that consolidated JSON loading is efficient."""
        import time

        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Create test file
            test_file = temp_dir / "test.json"
            test_file.write_text('{"test": true}')

            # Test old pattern
            start = time.time()
            for _ in range(100):
                try:
                    with test_file.open() as f:
                        data = json.load(f)
                except FileNotFoundError:
                    data = {}
            old_duration = time.time() - start

            # Test new pattern
            start = time.time()
            for _ in range(100):
                data = load_json_safe(test_file)
            new_duration = time.time() - start

            # New pattern should be comparable (within 2x)
            self.assertLess(new_duration, old_duration * 2)

        finally:
            import shutil

            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    unittest.main()
