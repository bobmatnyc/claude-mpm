#!/usr/bin/env python3
"""
Python Analyzer
===============

Analyzes Python source code using AST.

WHY: Python's built-in AST module provides rich structural information
that we can leverage for detailed analysis.
"""

import ast
from pathlib import Path
from typing import List, Optional

from ...core.logging_config import get_logger
from ..code_tree_events import CodeNodeEvent, CodeTreeEventEmitter
from .models import CodeNode


class PythonAnalyzer:
    """Analyzes Python source code using AST."""

    def __init__(self, emitter: Optional[CodeTreeEventEmitter] = None):
        self.logger = get_logger(__name__)
        self.emitter = emitter

    def analyze_file(self, file_path: Path) -> List[CodeNode]:
        """Analyze a Python file and extract code structure.

        Args:
            file_path: Path to Python file

        Returns:
            List of code nodes found in the file
        """
        nodes = []

        try:
            with Path(file_path).open(
                encoding="utf-8",
            ) as f:
                source = f.read()

            tree = ast.parse(source, filename=str(file_path))
            nodes = self._extract_nodes(tree, file_path, source)

        except SyntaxError as e:
            self.logger.warning(f"Syntax error in {file_path}: {e}")
            if self.emitter:
                self.emitter.emit_error(str(file_path), f"Syntax error: {e}")
        except Exception as e:
            self.logger.error(f"Error analyzing {file_path}: {e}")
            if self.emitter:
                self.emitter.emit_error(str(file_path), str(e))

        return nodes

    def _extract_nodes(
        self, tree: ast.AST, file_path: Path, source: str
    ) -> List[CodeNode]:
        """Extract code nodes from AST tree.

        Args:
            tree: AST tree
            file_path: Source file path
            source: Source code text

        Returns:
            List of extracted code nodes
        """
        nodes = []
        source.splitlines()

        class NodeVisitor(ast.NodeVisitor):
            def __init__(self, parent_name: Optional[str] = None):
                self.parent_name = parent_name
                self.current_class = None

            def visit_ClassDef(self, node):
                # Extract class information
                class_node = CodeNode(
                    file_path=str(file_path),
                    node_type="class",
                    name=node.name,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    has_docstring=bool(ast.get_docstring(node)),
                    decorators=[self._decorator_name(d) for d in node.decorator_list],
                    parent=self.parent_name,
                    complexity=self._calculate_complexity(node),
                    signature=self._get_class_signature(node),
                )

                nodes.append(class_node)

                # Emit event if emitter is available
                if self.emitter:
                    self.emitter.emit_node(
                        CodeNodeEvent(
                            file_path=str(file_path),
                            node_type="class",
                            name=node.name,
                            line_start=node.lineno,
                            line_end=node.end_lineno or node.lineno,
                            complexity=class_node.complexity,
                            has_docstring=class_node.has_docstring,
                            decorators=class_node.decorators,
                            parent=self.parent_name,
                            children_count=len(node.body),
                        )
                    )

                # Visit class members
                old_class = self.current_class
                self.current_class = node.name
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.visit_FunctionDef(child, is_method=True)
                self.current_class = old_class

            def visit_FunctionDef(self, node, is_method=False):
                # Determine node type
                node_type = "method" if is_method else "function"
                parent = self.current_class if is_method else self.parent_name

                # Extract function information
                func_node = CodeNode(
                    file_path=str(file_path),
                    node_type=node_type,
                    name=node.name,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    has_docstring=bool(ast.get_docstring(node)),
                    decorators=[self._decorator_name(d) for d in node.decorator_list],
                    parent=parent,
                    complexity=self._calculate_complexity(node),
                    signature=self._get_function_signature(node),
                )

                nodes.append(func_node)

                # Emit event if emitter is available
                if self.emitter:
                    self.emitter.emit_node(
                        CodeNodeEvent(
                            file_path=str(file_path),
                            node_type=node_type,
                            name=node.name,
                            line_start=node.lineno,
                            line_end=node.end_lineno or node.lineno,
                            complexity=func_node.complexity,
                            has_docstring=func_node.has_docstring,
                            decorators=func_node.decorators,
                            parent=parent,
                            children_count=0,
                        )
                    )

            def visit_Assign(self, node):
                # Handle module-level variable assignments
                if self.current_class is None:  # Only module-level assignments
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            var_node = CodeNode(
                                file_path=str(file_path),
                                node_type="variable",
                                name=target.id,
                                line_start=node.lineno,
                                line_end=node.end_lineno or node.lineno,
                                parent=self.parent_name,
                                complexity=0,
                                signature=f"{target.id} = ...",
                            )
                            nodes.append(var_node)

                            # Emit event if emitter is available
                            if self.emitter:
                                self.emitter.emit_node(
                                    CodeNodeEvent(
                                        file_path=str(file_path),
                                        node_type="variable",
                                        name=target.id,
                                        line_start=node.lineno,
                                        line_end=node.end_lineno or node.lineno,
                                        parent=self.parent_name,
                                    )
                                )

            def visit_AsyncFunctionDef(self, node):
                self.visit_FunctionDef(node)

            def _decorator_name(self, decorator):
                """Extract decorator name from AST node."""
                if isinstance(decorator, ast.Name):
                    return decorator.id
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Name):
                        return decorator.func.id
                    if isinstance(decorator.func, ast.Attribute):
                        return decorator.func.attr
                return "unknown"

            def _calculate_complexity(self, node):
                """Calculate cyclomatic complexity of a node."""
                complexity = 1  # Base complexity

                for child in ast.walk(node):
                    if isinstance(
                        child, (ast.If, ast.While, ast.For, ast.ExceptHandler)
                    ):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1

                return complexity

            def _get_function_signature(self, node):
                """Extract function signature."""
                args = []
                for arg in node.args.args:
                    args.append(arg.arg)
                return f"{node.name}({', '.join(args)})"

            def _get_class_signature(self, node):
                """Extract class signature."""
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                base_str = f"({', '.join(bases)})" if bases else ""
                return f"class {node.name}{base_str}"

        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_node = CodeNode(
                        file_path=str(file_path),
                        node_type="import",
                        name=alias.name,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        signature=f"import {alias.name}",
                    )
                    nodes.append(import_node)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    import_node = CodeNode(
                        file_path=str(file_path),
                        node_type="import",
                        name=f"{module}.{alias.name}",
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        signature=f"from {module} import {alias.name}",
                    )
                    nodes.append(import_node)

        # Visit all nodes
        visitor = NodeVisitor()
        visitor.emitter = self.emitter
        visitor.visit(tree)

        return nodes

    def _get_assignment_signature(self, node: ast.Assign, var_name: str) -> str:
        """Get assignment signature string."""
        try:
            # Try to get a simple representation of the value
            if isinstance(node.value, ast.Constant):
                if isinstance(node.value.value, str):
                    return f'{var_name} = "{node.value.value}"'
                return f"{var_name} = {node.value.value}"
            if isinstance(node.value, ast.Name):
                return f"{var_name} = {node.value.id}"
            if isinstance(node.value, ast.List):
                return f"{var_name} = [...]"
            if isinstance(node.value, ast.Dict):
                return f"{var_name} = {{...}}"
            return f"{var_name} = ..."
        except Exception:
            return f"{var_name} = ..."
