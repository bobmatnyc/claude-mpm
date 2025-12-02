"""
Tests for MermaidGeneratorService
==================================

Comprehensive test suite for the Mermaid diagram generation service.
"""

import pytest

from claude_mpm.services.visualization.mermaid_generator import (
    DiagramConfig,
    DiagramType,
    MermaidGeneratorService,
)


class TestMermaidGeneratorService:
    """Test suite for MermaidGeneratorService."""

    @pytest.fixture
    def service(self):
        """Create a service instance for testing."""
        service = MermaidGeneratorService()
        service.initialize()
        return service

    @pytest.fixture
    def sample_analysis_results(self):
        """Sample analysis results for testing."""
        return {
            "entry_points": {
                "cli": [
                    {
                        "file": "src/main.py",
                        "function": "main",
                        "line": 42,
                    },
                    {
                        "file": "src/cli.py",
                        "function": "run_cli",
                        "line": 15,
                    },
                ],
                "web": [
                    {
                        "file": "src/app.py",
                        "function": "create_app",
                        "line": 10,
                    }
                ],
            },
            "dependencies": {
                "src.main": ["os", "sys", "src.utils"],
                "src.utils": ["logging", "json"],
                "src.cli": ["argparse", "src.main"],
            },
            "imports": {
                "src/main.py": [
                    {"from": "os", "import": "path"},
                    {"from": "src.utils", "import": "helper"},
                ],
                "src/utils.py": [
                    {"module": "logging"},
                    {"from": "json", "import": "dumps"},
                ],
            },
            "classes": {
                "MyClass": {
                    "is_abstract": False,
                    "bases": ["BaseClass"],
                    "attributes": [
                        {"name": "value", "type": "int", "visibility": "+"},
                        {"name": "_internal", "type": "str", "visibility": "-"},
                    ],
                    "methods": [
                        {
                            "name": "process",
                            "parameters": ["data: str"],
                            "return_type": "bool",
                            "visibility": "+",
                        },
                        {
                            "name": "_validate",
                            "parameters": [],
                            "return_type": "None",
                            "visibility": "-",
                        },
                    ],
                    "associations": ["Helper"],
                },
                "BaseClass": {
                    "is_abstract": True,
                    "attributes": [],
                    "methods": [
                        {
                            "name": "abstract_method",
                            "parameters": [],
                            "return_type": "None",
                            "visibility": "+",
                        }
                    ],
                },
                "Helper": {
                    "attributes": [
                        {"name": "config", "type": "dict"},
                    ],
                    "methods": [{"name": "assist", "parameters": ["task: str"]}],
                },
            },
            "functions": {
                "main": {
                    "calls": ["parse_args", "run_app", "cleanup"],
                    "parameters": [],
                    "return_type": "int",
                },
                "parse_args": {
                    "calls": ["argparse.ArgumentParser"],
                    "parameters": [],
                    "return_type": "Namespace",
                },
                "run_app": {
                    "calls": ["initialize", "process_data", "save_results"],
                    "parameters": ["args: Namespace"],
                    "return_type": "None",
                },
                "cleanup": {
                    "calls": ["close_connections"],
                    "parameters": [],
                    "return_type": "None",
                },
            },
            "call_graph": {
                "main": [
                    {"function": "parse_args", "count": 1},
                    {"function": "run_app", "count": 1},
                    {"function": "cleanup", "count": 2},
                ],
                "run_app": [
                    {"function": "initialize", "count": 1},
                    {"function": "process_data", "count": 3},
                    {"function": "save_results", "count": 1},
                ],
            },
        }

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service.is_initialized
        assert not service.is_shutdown
        assert service.service_name == "MermaidGeneratorService"

    def test_service_shutdown(self, service):
        """Test service shutdown."""
        service.shutdown()
        assert service.is_shutdown
        assert len(service._node_id_cache) == 0

    def test_generate_entry_points_diagram(self, service, sample_analysis_results):
        """Test entry points diagram generation."""
        config = DiagramConfig(title="Test Entry Points")
        diagram = service.generate_diagram(
            DiagramType.ENTRY_POINTS, sample_analysis_results, config
        )

        assert "flowchart TB" in diagram
        assert "Test Entry Points" in diagram
        assert "main.py::main" in diagram
        assert "cli.py::run_cli" in diagram
        assert "app.py::create_app" in diagram
        assert "Application Start" in diagram
        assert "subgraph" in diagram

    def test_generate_module_deps_diagram(self, service, sample_analysis_results):
        """Test module dependencies diagram generation."""
        config = DiagramConfig(title="Test Dependencies", include_external=False)
        diagram = service.generate_diagram(
            DiagramType.MODULE_DEPS, sample_analysis_results, config
        )

        assert "flowchart TB" in diagram
        assert "Test Dependencies" in diagram
        assert "main" in diagram
        assert "utils" in diagram
        assert "cli" in diagram
        assert "-->" in diagram  # Import arrows

    def test_generate_class_hierarchy_diagram(self, service, sample_analysis_results):
        """Test class hierarchy diagram generation."""
        config = DiagramConfig(
            title="Test Class Hierarchy", show_parameters=True, show_return_types=True
        )
        diagram = service.generate_diagram(
            DiagramType.CLASS_HIERARCHY, sample_analysis_results, config
        )

        assert "classDiagram" in diagram
        assert "Test Class Hierarchy" in diagram
        assert "class MyClass" in diagram
        assert "class BaseClass" in diagram
        assert "class Helper" in diagram
        assert "<<abstract>>" in diagram
        assert "+process(data: str): bool" in diagram
        assert "BaseClass <|-- MyClass" in diagram  # Inheritance
        assert "MyClass --> Helper" in diagram  # Association

    def test_generate_call_graph_diagram(self, service, sample_analysis_results):
        """Test call graph diagram generation."""
        config = DiagramConfig(title="Test Call Graph")
        diagram = service.generate_diagram(
            DiagramType.CALL_GRAPH, sample_analysis_results, config
        )

        assert "flowchart TB" in diagram
        assert "Test Call Graph" in diagram
        assert "main" in diagram
        assert "parse_args" in diagram
        assert "run_app" in diagram
        assert "cleanup" in diagram
        assert "-->|2|" in diagram  # Call count label

    def test_empty_analysis_results(self, service):
        """Test handling of empty analysis results."""
        empty_results = {}

        # Entry points
        diagram = service.generate_diagram(DiagramType.ENTRY_POINTS, empty_results)
        assert "No entry points found" in diagram

        # Module deps
        diagram = service.generate_diagram(DiagramType.MODULE_DEPS, empty_results)
        assert "No dependencies found" in diagram

        # Class hierarchy
        diagram = service.generate_diagram(DiagramType.CLASS_HIERARCHY, empty_results)
        assert "No classes found" in diagram

        # Call graph
        diagram = service.generate_diagram(DiagramType.CALL_GRAPH, empty_results)
        assert "No functions found" in diagram

    def test_node_id_sanitization(self, service):
        """Test node ID sanitization."""
        test_cases = [
            ("simple", "simple"),
            ("with.dots", "with_dots"),
            ("with/slashes", "with_slashes"),
            ("with spaces", "with_spaces"),
            ("with-dashes", "with_dashes"),
            ("with(parens)", "with_parens"),
            ("with[brackets]", "with_brackets"),
            ("with{braces}", "with_braces"),
            ("with<angles>", "with_angles"),
            ("123start", "n_123start"),
            ("", "node"),
            ("graph", "graph_node"),  # Reserved keyword
            ("class", "class_node"),  # Reserved keyword
            ("@#$%^&*()", "node"),  # All special chars
            ("__multiple___underscores__", "multiple_underscores"),
        ]

        for input_id, expected in test_cases:
            result = service._sanitize_node_id(input_id)
            assert result == expected, (
                f"Failed for '{input_id}': got '{result}', expected '{expected}'"
            )

    def test_label_escaping(self, service):
        """Test label escaping for special characters."""
        test_cases = [
            ("simple", "simple"),
            ('with"quotes"', 'with\\"quotes\\"'),
            ("with'quotes'", "with\\'quotes\\'"),
            ("with`backticks`", "with\\`backticks\\`"),
            ("with[brackets]", "with&#91;brackets&#93;"),
            ("with{braces}", "with&#123;braces&#125;"),
            ("with<angles>", "with&lt;angles&gt;"),
            ("with&ampersand", "with&amp;ampersand"),
            ("with|pipe", "with&#124;pipe"),
            ("a" * 60, "a" * 47 + "..."),  # Long label truncation
        ]

        for input_label, expected in test_cases:
            result = service._escape_label(input_label)
            assert result == expected, (
                f"Failed for '{input_label}': got '{result}', expected '{expected}'"
            )

    def test_module_name_extraction(self, service):
        """Test module name extraction from paths."""
        test_cases = [
            ("src/main.py", "main"),
            ("lib/utils/helper.py", "utils.helper"),
            ("app/models/user.js", "models.user"),
            ("src/very/deep/nested/module.py", "deep.nested.module"),  # Truncated
            ("/absolute/path/to/file.py", "path.to.file"),
            ("simple.py", "simple"),
            ("module", "module"),
            ("", "module"),
        ]

        for input_path, expected in test_cases:
            result = service._extract_module_name(input_path)
            assert result == expected, (
                f"Failed for '{input_path}': got '{result}', expected '{expected}'"
            )

    def test_external_module_detection(self, service):
        """Test detection of external modules."""
        external_modules = [
            "os",
            "sys",
            "re",
            "json",
            "typing",
            "numpy",
            "pandas",
            "matplotlib",
            "requests",
            "flask",
            "django",
            "pytest",
            "unittest",
            "logging",
            "asyncio",
            "boto3",
            "azure",
            "_internal",
            "_private",
            "package-1.2.3",
        ]

        internal_modules = [
            "myapp",
            "src.utils",
            "app.models",
            "__main__",
            "__init__",
            "custom_module",
            "my_package.submodule",
        ]

        for module in external_modules:
            assert service._is_external_module(module), f"'{module}' should be external"

        for module in internal_modules:
            assert not service._is_external_module(module), (
                f"'{module}' should be internal"
            )

    def test_mermaid_syntax_validation(self, service):
        """Test Mermaid syntax validation."""
        # Valid diagrams
        valid_diagrams = [
            "flowchart TD\n    A --> B",
            "classDiagram\n    class MyClass {\n        +method()\n    }",
            "sequenceDiagram\n    A->>B: Hello",
            "graph LR\n    A[Node A] --> B[Node B]",
        ]

        for diagram in valid_diagrams:
            is_valid, error = service.validate_mermaid_syntax(diagram)
            assert is_valid, f"Diagram should be valid: {error}"
            assert error is None

        # Invalid diagrams
        invalid_diagrams = [
            ("", "Empty diagram"),
            ("invalid start", "Invalid diagram type"),
            ("flowchart TD\n    A[Open --> B", "Unbalanced brackets"),
            ("flowchart TD\n    A(Open --> B", "Unbalanced parentheses"),
            ("classDiagram\n    class A {\n        method()", "Unbalanced braces"),
            (
                "flowchart TD\n    subgraph sub\n    A --> B",
                "Unmatched subgraph blocks",
            ),
        ]

        for diagram, expected_error in invalid_diagrams:
            is_valid, error = service.validate_mermaid_syntax(diagram)
            assert not is_valid, "Diagram should be invalid"
            assert expected_error in error, (
                f"Expected '{expected_error}' in error message, got '{error}'"
            )

    def test_diagram_with_metadata(self, service):
        """Test formatting diagram with metadata."""
        diagram = "flowchart TD\n    A --> B"
        metadata = {
            "timestamp": "2024-01-01 12:00:00",
            "source": "test.py",
            "type": "call_graph",
            "stats": {
                "nodes": 10,
                "edges": 15,
                "depth": 3,
            },
        }

        formatted = service.format_diagram_with_metadata(diagram, metadata)

        assert "%% Diagram Metadata" in formatted
        assert "%% Generated: 2024-01-01 12:00:00" in formatted
        assert "%% Source: test.py" in formatted
        assert "%% Type: call_graph" in formatted
        assert "%% Statistics:" in formatted
        assert "%%   nodes: 10" in formatted
        assert "%%   edges: 15" in formatted
        assert "%%   depth: 3" in formatted
        assert diagram in formatted

    def test_unique_node_ids(self, service):
        """Test that node IDs are unique for different identifiers and consistent for same."""
        # Test that the same identifier always returns the same ID
        id1 = service._get_node_id("test")
        id2 = service._get_node_id("test")
        assert id1 == id2, "Same identifier should return same ID"

        # Test that similar but different identifiers get unique IDs
        identifiers = [
            "test",
            "test_1",  # Different identifier
            "test-1",  # Will sanitize to test_1, so needs unique ID
            "test.1",  # Will sanitize to test_1, so needs unique ID
            "test/1",  # Will sanitize to test_1, so needs unique ID
        ]

        ids_map = {}
        for identifier in identifiers:
            node_id = service._get_node_id(identifier)
            if identifier not in ids_map:
                ids_map[identifier] = node_id
            else:
                # Same identifier should always return same ID
                assert ids_map[identifier] == node_id

        # Different identifiers should have unique IDs
        unique_ids = list(ids_map.values())
        assert len(unique_ids) == len(set(unique_ids)), (
            f"Different identifiers should have unique IDs: {ids_map}"
        )

    def test_diagram_config_defaults(self):
        """Test DiagramConfig default values."""
        config = DiagramConfig()

        assert config.title is None
        assert config.direction == "TB"
        assert config.theme == "default"
        assert config.max_depth == 5
        assert config.include_external is False
        assert config.show_parameters is True
        assert config.show_return_types is True

    def test_diagram_config_custom(self):
        """Test DiagramConfig with custom values."""
        config = DiagramConfig(
            title="Custom Title",
            direction="LR",
            theme="dark",
            max_depth=3,
            include_external=True,
            show_parameters=False,
            show_return_types=False,
        )

        assert config.title == "Custom Title"
        assert config.direction == "LR"
        assert config.theme == "dark"
        assert config.max_depth == 3
        assert config.include_external is True
        assert config.show_parameters is False
        assert config.show_return_types is False

    def test_class_name_sanitization(self, service):
        """Test class name sanitization for class diagrams."""
        test_cases = [
            ("SimpleClass", "SimpleClass"),
            ("My-Class", "MyClass"),
            ("My.Class", "MyClass"),
            ("My Class", "MyClass"),
            ("123Class", "C_123Class"),
            ("@#$%^", "Class"),
            ("", "Class"),
        ]

        for input_name, expected in test_cases:
            result = service._sanitize_class_name(input_name)
            assert result == expected, (
                f"Failed for '{input_name}': got '{result}', expected '{expected}'"
            )

    def test_service_not_initialized(self):
        """Test that service raises error when not initialized."""
        service = MermaidGeneratorService()

        with pytest.raises(RuntimeError, match="Service not initialized"):
            service.generate_diagram(DiagramType.ENTRY_POINTS, {})

    def test_invalid_diagram_type(self, service):
        """Test handling of invalid diagram type."""
        with pytest.raises(ValueError, match="Unsupported diagram type"):
            service.generate_diagram("invalid_type", {})  # Not a valid DiagramType

    def test_complex_nested_structure(self, service):
        """Test handling of complex nested analysis results."""
        complex_results = {
            "classes": {
                "A": {
                    "bases": ["B", "C"],
                    "methods": [
                        {"name": f"method_{i}"}
                        for i in range(20)  # Many methods
                    ],
                    "attributes": [
                        {"name": f"attr_{i}", "type": "Any"}
                        for i in range(20)  # Many attributes
                    ],
                },
                "B": {"bases": ["D"]},
                "C": {"bases": ["D"]},
                "D": {"bases": []},
            }
        }

        diagram = service.generate_diagram(DiagramType.CLASS_HIERARCHY, complex_results)

        # Should limit methods and attributes to 10 each
        assert "method_0" in diagram
        assert "method_9" in diagram
        assert "method_10" not in diagram  # Should be truncated

        assert "attr_0" in diagram
        assert "attr_9" in diagram
        assert "attr_10" not in diagram  # Should be truncated
