"""
Pre-split verification tests for test_agent_deployment_comprehensive.py.

These tests verify that splitting the file is safe by checking:
1. Base class inheritance pattern
2. Fixture dependencies
3. Test class boundaries
4. Import structure
5. Current test count

Run these BEFORE splitting. If they pass, the split should be safe.
"""

import ast
from pathlib import Path

import pytest


class TestPreSplitVerification:
    """Verification tests before splitting test_agent_deployment_comprehensive.py."""

    @pytest.fixture
    def test_file_path(self):
        """Path to the file we're planning to split."""
        return Path("tests/services/agents/deployment/test_agent_deployment_comprehensive.py")

    @pytest.fixture
    def test_file_content(self, test_file_path):
        """Content of the test file."""
        return test_file_path.read_text()

    def test_file_exists(self, test_file_path):
        """Verify the test file exists."""
        assert test_file_path.exists()

    def test_has_base_class(self, test_file_content):
        """Verify TestAgentDeploymentService base class exists."""
        assert 'class TestAgentDeploymentService' in test_file_content

    def test_base_class_has_fixtures(self, test_file_content):
        """Verify base class contains pytest fixtures."""
        # Parse to find fixtures in base class
        tree = ast.parse(test_file_content)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'TestAgentDeploymentService':
                # Check for pytest.fixture decorators in this class
                fixture_count = 0
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        for decorator in item.decorator_list:
                            if isinstance(decorator, ast.Attribute):
                                if decorator.attr == 'fixture':
                                    fixture_count += 1

                assert fixture_count >= 4, f"Expected 4+ fixtures, found {fixture_count}"

    def test_count_test_classes(self, test_file_content):
        """Verify we know how many test classes exist (should be 12)."""
        class_count = test_file_content.count('class Test')
        assert class_count == 12, f"Expected 12 test classes, found {class_count}"

    def test_count_inheriting_classes(self, test_file_content):
        """Verify 11 classes inherit from TestAgentDeploymentService."""
        tree = ast.parse(test_file_content)

        inheriting_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
                if node.name != 'TestAgentDeploymentService':
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == 'TestAgentDeploymentService':
                            inheriting_classes.append(node.name)

        assert len(inheriting_classes) == 11, \
            f"Expected 11 inheriting classes, found {len(inheriting_classes)}"

    def test_count_test_functions(self, test_file_content):
        """Verify we know how many test functions exist (should be ~63)."""
        test_count = test_file_content.count('def test_')
        assert 60 <= test_count <= 70, f"Expected ~63 tests, found {test_count}"

    def test_imports_resolve(self):
        """Verify all critical imports can be resolved."""
        try:
            from claude_mpm.services.agents.deployment.agent_deployment import (
                AgentDeploymentService
            )
            assert AgentDeploymentService is not None
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")

    def test_base_class_extractable(self, test_file_content):
        """Verify base class can be extracted to conftest.py."""
        # Find the base class definition
        tree = ast.parse(test_file_content)

        base_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'TestAgentDeploymentService':
                base_class = node
                break

        assert base_class is not None, "Base class not found"

        # Verify it has fixtures (makes it suitable for conftest.py)
        has_fixtures = any(
            isinstance(item, ast.FunctionDef) and
            any(isinstance(d, ast.Attribute) and d.attr == 'fixture' for d in item.decorator_list)
            for item in base_class.body
        )

        assert has_fixtures, "Base class has no fixtures - extraction not needed"

    def test_split_boundaries_identified(self, test_file_content):
        """Verify we can identify clear split boundaries."""
        expected_classes = [
            'TestAgentDeploymentService',  # Base class
            'TestDeploymentOperations',
            'TestTemplateDiscovery',
            'TestBaseAgentOperations',
            'TestVersionManagement',
            'TestConfiguration',
            'TestValidationAndRepair',
            'TestResultsManagement',
            'TestErrorHandling',
            'TestHelperMethods',
            'TestMultiSourceIntegration',
            'TestDeploymentIntegration',
        ]

        for expected_class in expected_classes:
            assert f'class {expected_class}' in test_file_content, \
                f"Expected test class not found: {expected_class}"

    def test_file_size_justifies_split(self, test_file_path):
        """Verify file is large enough to justify splitting."""
        lines = len(test_file_path.read_text().splitlines())
        assert lines > 1000, f"File only {lines} lines - may not need split"

    def test_proposed_split_reduces_size(self, test_file_path):
        """Verify proposed split will reduce average file size."""
        current_lines = len(test_file_path.read_text().splitlines())
        proposed_files = 8  # 8 test files + 1 conftest
        average_after_split = current_lines / proposed_files
        assert average_after_split < 200, \
            f"Average file size after split ({average_after_split:.0f} lines) still too large"

    def test_fixtures_are_in_base_class(self, test_file_content):
        """Verify fixtures are centralized in base class (not scattered)."""
        # Parse the file
        tree = ast.parse(test_file_content)

        # Find all fixture definitions
        base_class_fixtures = []
        other_fixtures = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        for decorator in item.decorator_list:
                            if isinstance(decorator, ast.Attribute) and decorator.attr == 'fixture':
                                if node.name == 'TestAgentDeploymentService':
                                    base_class_fixtures.append(item.name)
                                else:
                                    other_fixtures.append(item.name)

        # Most fixtures should be in base class
        assert len(base_class_fixtures) >= len(other_fixtures), \
            "Fixtures scattered across classes - split will be complex"
