#!/usr/bin/env python3
"""
Comprehensive Unit Tests for ProjectAnalyzer Refactoring
=========================================================

Tests all aspects of the ProjectAnalyzer class and its refactored services.
Tests are designed to guide the refactoring process.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from claude_mpm.services.project.analyzer import (ProjectAnalyzer,
                                                  ProjectCharacteristics)


class TestProjectCharacteristics:
    """Test the ProjectCharacteristics dataclass."""

    def test_initialization(self):
        """Test basic initialization of ProjectCharacteristics."""
        characteristics = ProjectCharacteristics(
            project_name="test_project",
            primary_language="python",
            languages=["python", "javascript"],
            frameworks=["django", "react"],
            architecture_type="web_application",
            main_modules=["core", "api"],
            key_directories=["src", "tests"],
            entry_points=["main.py"],
            testing_framework="pytest",
            test_patterns=["unit_tests"],
            package_manager="pip",
            build_tools=["make"],
            databases=["postgresql"],
            web_frameworks=["django"],
            api_patterns=["REST"],
            key_dependencies=["django", "pytest"],
            code_conventions=["pep8"],
            configuration_patterns=["yaml"],
            project_terminology=["api", "endpoint"],
            documentation_files=["README.md"],
            important_configs=["pyproject.toml"],
        )

        assert characteristics.project_name == "test_project"
        assert characteristics.primary_language == "python"
        assert "django" in characteristics.frameworks

    def test_to_dict(self):
        """Test conversion to dictionary."""
        characteristics = ProjectCharacteristics(
            project_name="test",
            primary_language="python",
            languages=[],
            frameworks=[],
            architecture_type="unknown",
            main_modules=[],
            key_directories=[],
            entry_points=[],
            testing_framework=None,
            test_patterns=[],
            package_manager=None,
            build_tools=[],
            databases=[],
            web_frameworks=[],
            api_patterns=[],
            key_dependencies=[],
            code_conventions=[],
            configuration_patterns=[],
            project_terminology=[],
            documentation_files=[],
            important_configs=[],
        )

        result = characteristics.to_dict()
        assert isinstance(result, dict)
        assert result["project_name"] == "test"
        assert result["primary_language"] == "python"


class TestProjectAnalyzer:
    """Test the main ProjectAnalyzer class."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure."""
        # Create basic project structure
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        (tmp_path / "docs").mkdir()

        # Create package.json
        package_json = {
            "name": "test-project",
            "dependencies": {"express": "^4.18.0", "react": "^18.0.0"},
            "devDependencies": {"jest": "^29.0.0"},
            "scripts": {"build": "webpack --mode production"},
        }
        (tmp_path / "package.json").write_text(json.dumps(package_json))

        # Create requirements.txt
        (tmp_path / "requirements.txt").write_text(
            """
django==4.2
pytest==7.4
psycopg2==2.9
        """
        )

        # Create some source files
        (tmp_path / "src" / "main.py").write_text(
            """
from flask import Flask
import asyncio

app = Flask(__name__)

@app.route('/')
async def home():
    return "Hello World"

class UserService:
    def __init__(self):
        self.db = None
        """
        )

        # Create test file
        (tmp_path / "tests" / "test_main.py").write_text(
            """
import pytest

def test_example():
    assert True
        """
        )

        # Create README
        (tmp_path / "README.md").write_text("# Test Project")

        return tmp_path

    def test_initialization(self, temp_project):
        """Test analyzer initialization."""
        analyzer = ProjectAnalyzer(working_directory=temp_project)
        assert analyzer.working_directory == temp_project
        assert analyzer._analysis_cache is None

    def test_analyze_project_basic(self, temp_project):
        """Test basic project analysis."""
        analyzer = ProjectAnalyzer(working_directory=temp_project)
        characteristics = analyzer.analyze_project()

        assert characteristics.project_name == temp_project.name
        assert characteristics.languages  # Should detect languages
        assert characteristics.key_directories  # Should find directories

    def test_analyze_config_files(self, temp_project):
        """Test configuration file analysis."""
        analyzer = ProjectAnalyzer(working_directory=temp_project)
        characteristics = ProjectCharacteristics(
            project_name="test",
            primary_language=None,
            languages=[],
            frameworks=[],
            architecture_type="unknown",
            main_modules=[],
            key_directories=[],
            entry_points=[],
            testing_framework=None,
            test_patterns=[],
            package_manager=None,
            build_tools=[],
            databases=[],
            web_frameworks=[],
            api_patterns=[],
            key_dependencies=[],
            code_conventions=[],
            configuration_patterns=[],
            project_terminology=[],
            documentation_files=[],
            important_configs=[],
        )

        analyzer._analyze_config_files(characteristics)

        # Should detect both package.json and requirements.txt
        assert "package.json" in characteristics.important_configs
        assert "requirements.txt" in characteristics.important_configs
        assert characteristics.package_manager in ["npm", "pip"]

    def test_parse_package_json(self, temp_project):
        """Test package.json parsing."""
        analyzer = ProjectAnalyzer(working_directory=temp_project)
        characteristics = ProjectCharacteristics(
            project_name="test",
            primary_language=None,
            languages=[],
            frameworks=[],
            architecture_type="unknown",
            main_modules=[],
            key_directories=[],
            entry_points=[],
            testing_framework=None,
            test_patterns=[],
            package_manager=None,
            build_tools=[],
            databases=[],
            web_frameworks=[],
            api_patterns=[],
            key_dependencies=[],
            code_conventions=[],
            configuration_patterns=[],
            project_terminology=[],
            documentation_files=[],
            important_configs=[],
        )

        analyzer._parse_package_json(temp_project / "package.json", characteristics)

        assert "express" in characteristics.web_frameworks
        assert "react" in characteristics.frameworks
        assert characteristics.testing_framework == "jest"
        assert any("webpack" in tool for tool in characteristics.build_tools)

    def test_parse_python_dependencies(self, temp_project):
        """Test Python dependency parsing."""
        analyzer = ProjectAnalyzer(working_directory=temp_project)
        characteristics = ProjectCharacteristics(
            project_name="test",
            primary_language=None,
            languages=[],
            frameworks=[],
            architecture_type="unknown",
            main_modules=[],
            key_directories=[],
            entry_points=[],
            testing_framework=None,
            test_patterns=[],
            package_manager=None,
            build_tools=[],
            databases=[],
            web_frameworks=[],
            api_patterns=[],
            key_dependencies=[],
            code_conventions=[],
            configuration_patterns=[],
            project_terminology=[],
            documentation_files=[],
            important_configs=[],
        )

        analyzer._parse_python_dependencies(
            temp_project / "requirements.txt", characteristics
        )

        assert "django" in characteristics.web_frameworks
        assert characteristics.testing_framework == "pytest"
        assert "psycopg2" in characteristics.databases

    def test_analyze_directory_structure(self, temp_project):
        """Test directory structure analysis."""
        analyzer = ProjectAnalyzer(working_directory=temp_project)
        characteristics = ProjectCharacteristics(
            project_name="test",
            primary_language=None,
            languages=[],
            frameworks=[],
            architecture_type="unknown",
            main_modules=[],
            key_directories=[],
            entry_points=[],
            testing_framework=None,
            test_patterns=[],
            package_manager=None,
            build_tools=[],
            databases=[],
            web_frameworks=[],
            api_patterns=[],
            key_dependencies=[],
            code_conventions=[],
            configuration_patterns=[],
            project_terminology=[],
            documentation_files=[],
            important_configs=[],
        )

        analyzer._analyze_directory_structure(characteristics)

        assert "src" in characteristics.key_directories
        assert "tests" in characteristics.key_directories
        assert "docs" in characteristics.key_directories
        assert "src/main.py" in characteristics.entry_points

    def test_analyze_source_code(self, temp_project):
        """Test source code analysis."""
        analyzer = ProjectAnalyzer(working_directory=temp_project)
        characteristics = ProjectCharacteristics(
            project_name="test",
            primary_language=None,
            languages=[],
            frameworks=[],
            architecture_type="unknown",
            main_modules=[],
            key_directories=[],
            entry_points=[],
            testing_framework=None,
            test_patterns=[],
            package_manager=None,
            build_tools=[],
            databases=[],
            web_frameworks=[],
            api_patterns=[],
            key_dependencies=[],
            code_conventions=[],
            configuration_patterns=[],
            project_terminology=[],
            documentation_files=[],
            important_configs=[],
        )

        analyzer._analyze_source_code(characteristics)

        assert "python" in characteristics.languages
        assert any("flask" in fw.lower() for fw in characteristics.frameworks)
        assert "Async Programming" in characteristics.code_conventions
        assert "Object Oriented" in characteristics.code_conventions

    def test_analyze_testing_patterns(self, temp_project):
        """Test testing pattern analysis."""
        analyzer = ProjectAnalyzer(working_directory=temp_project)
        characteristics = ProjectCharacteristics(
            project_name="test",
            primary_language=None,
            languages=[],
            frameworks=[],
            architecture_type="unknown",
            main_modules=[],
            key_directories=[],
            entry_points=[],
            testing_framework=None,
            test_patterns=[],
            package_manager=None,
            build_tools=[],
            databases=[],
            web_frameworks=[],
            api_patterns=[],
            key_dependencies=[],
            code_conventions=[],
            configuration_patterns=[],
            project_terminology=[],
            documentation_files=[],
            important_configs=[],
        )

        analyzer._analyze_testing_patterns(characteristics)

        assert any(
            "Tests in /tests/ directory" in pattern
            for pattern in characteristics.test_patterns
        )

    def test_infer_architecture_type(self, temp_project):
        """Test architecture type inference."""
        analyzer = ProjectAnalyzer(working_directory=temp_project)

        # Test with web framework
        characteristics = ProjectCharacteristics(
            project_name="test",
            primary_language="python",
            languages=["python"],
            frameworks=[],
            architecture_type="unknown",
            main_modules=[],
            key_directories=["api"],
            entry_points=[],
            testing_framework=None,
            test_patterns=[],
            package_manager=None,
            build_tools=[],
            databases=[],
            web_frameworks=["flask"],
            api_patterns=[],
            key_dependencies=[],
            code_conventions=[],
            configuration_patterns=[],
            project_terminology=[],
            documentation_files=[],
            important_configs=[],
        )

        analyzer._infer_architecture_type(characteristics)
        assert characteristics.architecture_type == "REST API Service"

    def test_caching(self, temp_project):
        """Test analysis caching."""
        analyzer = ProjectAnalyzer(working_directory=temp_project)

        # First call should analyze
        result1 = analyzer.analyze_project()
        assert analyzer._analysis_cache is not None

        # Second call should use cache
        with patch.object(analyzer, "_analyze_config_files") as mock_analyze:
            result2 = analyzer.analyze_project()
            mock_analyze.assert_not_called()

        assert result1.project_name == result2.project_name

        # Force refresh should bypass cache
        with patch.object(analyzer, "_analyze_config_files") as mock_analyze:
            analyzer.analyze_project(force_refresh=True)
            mock_analyze.assert_called_once()

    def test_get_project_context_summary(self, temp_project):
        """Test project context summary generation."""
        analyzer = ProjectAnalyzer(working_directory=temp_project)
        summary = analyzer.get_project_context_summary()

        assert temp_project.name in summary
        assert any(
            lang in summary.lower() for lang in ["python", "javascript", "mixed"]
        )

    def test_get_important_files_for_context(self, temp_project):
        """Test important files identification."""
        analyzer = ProjectAnalyzer(working_directory=temp_project)
        files = analyzer.get_important_files_for_context()

        assert "README.md" in files
        assert "package.json" in files
        assert "requirements.txt" in files

    def test_interface_methods(self, temp_project):
        """Test interface adapter methods."""
        analyzer = ProjectAnalyzer(working_directory=temp_project)

        # Test detect_technology_stack
        tech_stack = analyzer.detect_technology_stack()
        assert isinstance(tech_stack, list)
        assert len(tech_stack) > 0

        # Test analyze_code_patterns
        patterns = analyzer.analyze_code_patterns()
        assert isinstance(patterns, dict)
        assert "code_conventions" in patterns
        assert "architecture_type" in patterns

        # Test get_project_structure
        structure = analyzer.get_project_structure()
        assert isinstance(structure, dict)
        assert "project_name" in structure
        assert "key_directories" in structure

        # Test identify_entry_points
        entry_points = analyzer.identify_entry_points()
        assert isinstance(entry_points, list)
        assert all(isinstance(p, Path) for p in entry_points)

    def test_error_handling(self, temp_project):
        """Test error handling in analysis."""
        analyzer = ProjectAnalyzer(working_directory=temp_project)

        # Mock an error during analysis
        with patch.object(
            analyzer, "_analyze_config_files", side_effect=Exception("Test error")
        ):
            characteristics = analyzer.analyze_project()

            # Should return minimal characteristics on error
            assert characteristics.project_name == temp_project.name
            assert characteristics.primary_language == "unknown"
            assert characteristics.architecture_type == "unknown"

    def test_extract_project_terminology(self, temp_project):
        """Test project terminology extraction."""
        analyzer = ProjectAnalyzer(working_directory=temp_project)
        characteristics = ProjectCharacteristics(
            project_name="MyTestProject",
            primary_language="python",
            languages=["python"],
            frameworks=[],
            architecture_type="unknown",
            main_modules=["UserService", "AuthModule"],
            key_directories=["authentication", "database"],
            entry_points=[],
            testing_framework=None,
            test_patterns=[],
            package_manager=None,
            build_tools=[],
            databases=[],
            web_frameworks=[],
            api_patterns=[],
            key_dependencies=[],
            code_conventions=[],
            configuration_patterns=[],
            project_terminology=[],
            documentation_files=[],
            important_configs=[],
        )

        analyzer._extract_project_terminology(characteristics)

        # Should extract meaningful terms
        assert len(characteristics.project_terminology) > 0
        # Should not include common words
        assert "test" not in [t.lower() for t in characteristics.project_terminology]


class TestRefactoredServices:
    """Test the refactored service classes (to be implemented)."""

    def test_language_analyzer_service(self):
        """Test LanguageAnalyzerService functionality."""
        # This will test the new LanguageAnalyzerService after refactoring

    def test_metrics_collector_service(self):
        """Test MetricsCollectorService functionality."""
        # This will test the new MetricsCollectorService after refactoring

    def test_dependency_analyzer_service(self):
        """Test DependencyAnalyzerService functionality."""
        # This will test the new DependencyAnalyzerService after refactoring

    def test_security_scanner_service(self):
        """Test SecurityScannerService functionality."""
        # This will test the new SecurityScannerService after refactoring

    def test_quality_analyzer_service(self):
        """Test QualityAnalyzerService functionality."""
        # This will test the new QualityAnalyzerService after refactoring

    def test_service_integration(self):
        """Test integration between refactored services."""
        # This will test how the services work together

    def test_dependency_injection(self):
        """Test dependency injection pattern."""
        # This will test the DI pattern implementation

    def test_backward_compatibility(self):
        """Test that refactored code maintains backward compatibility."""
        # This will ensure existing code continues to work
