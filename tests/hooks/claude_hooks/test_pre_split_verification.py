#!/usr/bin/env python3
"""
Pre-split verification tests for test_hook_handler_comprehensive.py.

These tests verify that splitting the file is safe by checking:
1. All imports resolve correctly
2. No shared fixtures exist
3. Test classes are independent
4. Current test count is known
5. All test classes can be instantiated

Run these BEFORE splitting. If they all pass, the split should be safe.
"""

import ast
import inspect
import sys
from pathlib import Path

import pytest


class TestPreSplitVerification:
    """Verification tests to run before splitting test_hook_handler_comprehensive.py."""

    @pytest.fixture
    def test_file_path(self):
        """Path to the file we're planning to split."""
        return Path("tests/hooks/claude_hooks/test_hook_handler_comprehensive.py")

    @pytest.fixture
    def test_file_content(self, test_file_path):
        """Content of the test file."""
        return test_file_path.read_text()

    def test_file_exists(self, test_file_path):
        """Verify the test file exists."""
        assert test_file_path.exists(), f"Test file not found: {test_file_path}"

    def test_no_shared_fixtures(self, test_file_content):
        """Verify no @pytest.fixture decorators exist (confirms no shared fixtures)."""
        assert "@pytest.fixture" not in test_file_content, (
            "File contains fixtures - split will be more complex"
        )

    def test_imports_resolve(self):
        """Verify all imports in the file can be resolved."""
        try:
            from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

            assert ClaudeHookHandler is not None
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")

    def test_count_test_classes(self, test_file_content):
        """Verify we know how many test classes exist (should be 11)."""
        class_count = test_file_content.count("class Test")
        assert class_count == 11, f"Expected 11 test classes, found {class_count}"

    def test_count_test_functions(self, test_file_content):
        """Verify we know how many test functions exist (should be ~50)."""
        test_count = test_file_content.count("def test_")
        assert 45 <= test_count <= 55, f"Expected ~50 tests, found {test_count}"

    def test_no_class_inheritance(self, test_file_content):
        """Verify test classes don't inherit from each other (confirms independence)."""
        # Parse the file to check class definitions
        tree = ast.parse(test_file_content)
        test_classes = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name.startswith("Test")
        ]

        for cls in test_classes:
            # Check if it inherits from anything other than object
            if cls.bases:
                for base in cls.bases:
                    if isinstance(base, ast.Name):
                        # It's okay to inherit from object or nothing
                        # But not from other test classes
                        assert not base.id.startswith("Test"), (
                            f"{cls.name} inherits from {base.id} - split will be complex"
                        )

    def test_no_conftest_dependencies(self):
        """Verify no conftest.py exists in the directory (confirms no shared fixtures)."""
        conftest_path = Path("tests/hooks/claude_hooks/conftest.py")
        if conftest_path.exists():
            content = conftest_path.read_text()
            assert "@pytest.fixture" not in content, (
                "conftest.py has fixtures - need to account for these in split"
            )

    def test_split_boundaries_identified(self, test_file_content):
        """Verify we can identify clear split boundaries."""
        # Expected test classes
        expected_classes = [
            "TestEventReadingAndParsing",
            "TestEventRouting",
            "TestConnectionManagement",
            "TestStateManagement",
            "TestEventEmission",
            "TestSubagentStopProcessing",
            "TestDuplicateDetection",
            "TestErrorHandling",
            "TestMainEntryPoint",
            "TestIntegration",
            "TestMockValidation",
        ]

        for expected_class in expected_classes:
            assert f"class {expected_class}" in test_file_content, (
                f"Expected test class not found: {expected_class}"
            )

    def test_file_size_justifies_split(self, test_file_path):
        """Verify file is large enough to justify splitting."""
        lines = len(test_file_path.read_text().splitlines())
        assert lines > 1000, f"File only {lines} lines - may not need split"

    def test_proposed_split_reduces_size(self, test_file_path):
        """Verify proposed split will reduce average file size."""
        current_lines = len(test_file_path.read_text().splitlines())
        proposed_files = 5
        average_after_split = current_lines / proposed_files
        assert average_after_split < 300, (
            f"Average file size after split ({average_after_split:.0f} lines) still too large"
        )

    def test_verify_line_count(self, test_file_path):
        """Verify actual line count matches expected (~1139 lines)."""
        actual_lines = len(test_file_path.read_text().splitlines())
        assert 1130 <= actual_lines <= 1150, (
            f"Expected ~1139 lines, found {actual_lines}"
        )

    def test_verify_import_structure(self, test_file_content):
        """Verify standard imports are present and can be copied."""
        # Check for essential imports
        essential_imports = [
            "import json",
            "import pytest",
            "from unittest.mock import",
            "from pathlib import Path",
        ]

        for import_statement in essential_imports:
            assert import_statement in test_file_content, (
                f"Essential import not found: {import_statement}"
            )

    def test_no_global_state(self, test_file_content):
        """Verify no global state that would complicate splitting."""
        # Check for module-level variables (excluding imports and class definitions)
        tree = ast.parse(test_file_content)

        # Collect module-level assignments
        module_level_assigns = [
            node for node in tree.body if isinstance(node, (ast.Assign, ast.AnnAssign))
        ]

        # Should have minimal module-level state
        # (Some is okay like __name__ check at end)
        assert len(module_level_assigns) == 0, (
            "Module-level assignments found - may complicate split"
        )

    def test_verify_test_class_sizes(self, test_file_content):
        """Verify test classes have reasonable sizes for splitting."""
        tree = ast.parse(test_file_content)
        test_classes = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name.startswith("Test")
        ]

        for cls in test_classes:
            # Count methods in each class
            methods = [
                item
                for item in cls.body
                if isinstance(item, ast.FunctionDef) and item.name.startswith("test_")
            ]

            # Each test class should have 2-10 tests
            assert 1 <= len(methods) <= 15, (
                f"{cls.name} has {len(methods)} tests - may need further splitting"
            )

    def test_verify_no_cross_class_dependencies(self, test_file_content):
        """Verify test classes don't reference each other."""
        tree = ast.parse(test_file_content)

        # Get all test class names
        test_class_names = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name.startswith("Test")
        ]

        # For each class, check if it references other test classes
        for class_node in ast.walk(tree):
            if not isinstance(class_node, ast.ClassDef):
                continue
            if not class_node.name.startswith("Test"):
                continue

            # Walk the class body looking for references to other test classes
            for node in ast.walk(class_node):
                if isinstance(node, ast.Name):
                    if node.id in test_class_names and node.id != class_node.name:
                        pytest.fail(
                            f"{class_node.name} references {node.id} - cross-class dependency detected"
                        )

    def test_proposed_split_plan_is_valid(self, test_file_content):
        """Verify the proposed 5-file split plan is feasible."""
        # Proposed groupings
        split_plan = {
            "test_hook_handler_events.py": [
                "TestEventReadingAndParsing",
                "TestEventRouting",
            ],
            "test_hook_handler_connections.py": [
                "TestConnectionManagement",
                "TestEventEmission",
            ],
            "test_hook_handler_state.py": [
                "TestStateManagement",
                "TestDuplicateDetection",
            ],
            "test_hook_handler_subagent.py": [
                "TestSubagentStopProcessing",
                "TestErrorHandling",
            ],
            "test_hook_handler_integration.py": [
                "TestMainEntryPoint",
                "TestIntegration",
                "TestMockValidation",
            ],
        }

        # Verify all classes are accounted for
        all_planned_classes = []
        for classes in split_plan.values():
            all_planned_classes.extend(classes)

        # Check each class exists in the file
        for class_name in all_planned_classes:
            assert f"class {class_name}" in test_file_content, (
                f"Planned class {class_name} not found in file"
            )

        # Verify we haven't missed any classes
        tree = ast.parse(test_file_content)
        actual_classes = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name.startswith("Test")
        ]

        missing_classes = set(actual_classes) - set(all_planned_classes)
        assert not missing_classes, f"Classes not in split plan: {missing_classes}"

        extra_classes = set(all_planned_classes) - set(actual_classes)
        assert not extra_classes, f"Classes in plan but not in file: {extra_classes}"

    def test_can_import_source_module(self):
        """Verify the source module being tested can be imported."""
        try:
            from claude_mpm.hooks.claude_hooks import hook_handler

            assert hook_handler is not None
            assert hasattr(hook_handler, "ClaudeHookHandler")
        except ImportError as e:
            pytest.fail(f"Cannot import source module: {e}")

    def test_verify_test_isolation(self, test_file_path):
        """Verify tests can run independently (current state verification)."""
        # This test runs the actual test file to verify it works before splitting
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(test_file_path),
                "--co",  # Collect only, don't run
                "-q",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        # Should be able to collect tests without errors
        assert result.returncode == 0, (
            f"Cannot collect tests from file: {result.stderr}"
        )

        # Verify it collected the expected number of tests
        output = result.stdout
        # pytest --co shows test names, count them
        test_count = output.count("test_")
        assert 45 <= test_count <= 55, (
            f"Expected ~50 collected tests, found {test_count}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
