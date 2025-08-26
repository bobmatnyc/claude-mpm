#!/usr/bin/env python3
"""
Code Tree Analyzer
==================

WHY: Analyzes source code using AST to extract structure and metrics,
supporting multiple languages and emitting incremental events for visualization.

DESIGN DECISIONS:
- Use Python's ast module for Python files
- Use tree-sitter for multi-language support
- Extract comprehensive metadata (complexity, docstrings, etc.)
- Cache parsed results to avoid re-processing
- Support incremental processing with checkpoints
"""

import ast
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tree_sitter
    import tree_sitter_javascript
    import tree_sitter_python
    import tree_sitter_typescript

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    tree_sitter = None

from ..core.logging_config import get_logger
from .code_tree_events import CodeNodeEvent, CodeTreeEventEmitter


@dataclass
class CodeNode:
    """Represents a node in the code tree."""

    file_path: str
    node_type: str
    name: str
    line_start: int
    line_end: int
    complexity: int = 0
    has_docstring: bool = False
    decorators: List[str] = None
    parent: Optional[str] = None
    children: List["CodeNode"] = None
    language: str = "python"
    signature: str = ""
    metrics: Dict[str, Any] = None

    def __post_init__(self):
        if self.decorators is None:
            self.decorators = []
        if self.children is None:
            self.children = []
        if self.metrics is None:
            self.metrics = {}


class PythonAnalyzer:
    """Analyzes Python source code using AST.

    WHY: Python's built-in AST module provides rich structural information
    that we can leverage for detailed analysis.
    """

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
            with open(file_path, encoding="utf-8") as f:
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


class MultiLanguageAnalyzer:
    """Analyzes multiple programming languages using tree-sitter.

    WHY: Tree-sitter provides consistent parsing across multiple languages,
    allowing us to support JavaScript, TypeScript, and other languages.
    """

    LANGUAGE_PARSERS = {
        "python": "tree_sitter_python",
        "javascript": "tree_sitter_javascript",
        "typescript": "tree_sitter_typescript",
    }

    def __init__(self, emitter: Optional[CodeTreeEventEmitter] = None):
        self.logger = get_logger(__name__)
        self.emitter = emitter
        self.parsers = {}
        self._init_parsers()

    def _init_parsers(self):
        """Initialize tree-sitter parsers for supported languages."""
        if not TREE_SITTER_AVAILABLE:
            self.logger.warning(
                "tree-sitter not available - multi-language support disabled"
            )
            return

        for lang, module_name in self.LANGUAGE_PARSERS.items():
            try:
                # Dynamic import of language module
                module = __import__(module_name)
                parser = tree_sitter.Parser()
                # Different tree-sitter versions have different APIs
                if hasattr(parser, "set_language"):
                    parser.set_language(tree_sitter.Language(module.language()))
                else:
                    # Newer API
                    lang_obj = tree_sitter.Language(module.language())
                    parser = tree_sitter.Parser(lang_obj)
                self.parsers[lang] = parser
            except (ImportError, AttributeError) as e:
                self.logger.warning(f"Language parser not available for {lang}: {e}")

    def analyze_file(self, file_path: Path, language: str) -> List[CodeNode]:
        """Analyze a file using tree-sitter.

        Args:
            file_path: Path to source file
            language: Programming language

        Returns:
            List of code nodes found in the file
        """
        if language not in self.parsers:
            self.logger.warning(f"No parser available for language: {language}")
            return []

        nodes = []

        try:
            with open(file_path, "rb") as f:
                source = f.read()

            parser = self.parsers[language]
            tree = parser.parse(source)

            # Extract nodes based on language
            if language in {"javascript", "typescript"}:
                nodes = self._extract_js_nodes(tree, file_path, source)
            else:
                nodes = self._extract_generic_nodes(tree, file_path, source, language)

        except Exception as e:
            self.logger.error(f"Error analyzing {file_path}: {e}")
            if self.emitter:
                self.emitter.emit_error(str(file_path), str(e))

        return nodes

    def _extract_js_nodes(self, tree, file_path: Path, source: bytes) -> List[CodeNode]:
        """Extract nodes from JavaScript/TypeScript files."""
        nodes = []

        def walk_tree(node, parent_name=None):
            if node.type == "class_declaration":
                # Extract class
                name_node = node.child_by_field_name("name")
                if name_node:
                    class_node = CodeNode(
                        file_path=str(file_path),
                        node_type="class",
                        name=source[name_node.start_byte : name_node.end_byte].decode(
                            "utf-8"
                        ),
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        parent=parent_name,
                        language="javascript",
                    )
                    nodes.append(class_node)

                    if self.emitter:
                        self.emitter.emit_node(
                            CodeNodeEvent(
                                file_path=str(file_path),
                                node_type="class",
                                name=class_node.name,
                                line_start=class_node.line_start,
                                line_end=class_node.line_end,
                                parent=parent_name,
                                language="javascript",
                            )
                        )

            elif node.type in (
                "function_declaration",
                "arrow_function",
                "method_definition",
            ):
                # Extract function
                name_node = node.child_by_field_name("name")
                if name_node:
                    func_name = source[
                        name_node.start_byte : name_node.end_byte
                    ].decode("utf-8")
                    func_node = CodeNode(
                        file_path=str(file_path),
                        node_type=(
                            "function" if node.type != "method_definition" else "method"
                        ),
                        name=func_name,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        parent=parent_name,
                        language="javascript",
                    )
                    nodes.append(func_node)

                    if self.emitter:
                        self.emitter.emit_node(
                            CodeNodeEvent(
                                file_path=str(file_path),
                                node_type=func_node.node_type,
                                name=func_name,
                                line_start=func_node.line_start,
                                line_end=func_node.line_end,
                                parent=parent_name,
                                language="javascript",
                            )
                        )

            # Recursively walk children
            for child in node.children:
                walk_tree(child, parent_name)

        walk_tree(tree.root_node)
        return nodes

    def _extract_generic_nodes(
        self, tree, file_path: Path, source: bytes, language: str
    ) -> List[CodeNode]:
        """Generic node extraction for other languages."""
        # Simple generic extraction - can be enhanced per language
        nodes = []

        def walk_tree(node):
            # Look for common patterns
            if "class" in node.type or "struct" in node.type:
                nodes.append(
                    CodeNode(
                        file_path=str(file_path),
                        node_type="class",
                        name=f"{node.type}_{node.start_point[0]}",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        language=language,
                    )
                )
            elif "function" in node.type or "method" in node.type:
                nodes.append(
                    CodeNode(
                        file_path=str(file_path),
                        node_type="function",
                        name=f"{node.type}_{node.start_point[0]}",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        language=language,
                    )
                )

            for child in node.children:
                walk_tree(child)

        walk_tree(tree.root_node)
        return nodes


class CodeTreeAnalyzer:
    """Main analyzer that coordinates language-specific analyzers.

    WHY: Provides a unified interface for analyzing codebases with multiple
    languages, handling caching and incremental processing.
    """

    # File extensions to language mapping
    LANGUAGE_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".mjs": "javascript",
        ".cjs": "javascript",
    }

    def __init__(self, emit_events: bool = True, cache_dir: Optional[Path] = None):
        """Initialize the code tree analyzer.

        Args:
            emit_events: Whether to emit Socket.IO events
            cache_dir: Directory for caching analysis results
        """
        self.logger = get_logger(__name__)
        self.emit_events = emit_events
        self.cache_dir = cache_dir or Path.home() / ".claude-mpm" / "code-cache"

        # Initialize event emitter - use stdout mode for subprocess communication
        self.emitter = CodeTreeEventEmitter(use_stdout=True) if emit_events else None

        # Initialize language analyzers
        self.python_analyzer = PythonAnalyzer(self.emitter)
        self.multi_lang_analyzer = MultiLanguageAnalyzer(self.emitter)

        # Cache for processed files
        self.cache = {}
        self._load_cache()

    def analyze_directory(
        self,
        directory: Path,
        languages: Optional[List[str]] = None,
        ignore_patterns: Optional[List[str]] = None,
        max_depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Analyze a directory and build code tree.

        Args:
            directory: Directory to analyze
            languages: Languages to include (None for all)
            ignore_patterns: Patterns to ignore
            max_depth: Maximum directory depth

        Returns:
            Dictionary containing the code tree and statistics
        """
        if self.emitter:
            self.emitter.start()

        start_time = time.time()
        all_nodes = []
        files_processed = 0
        total_files = 0

        # Collect files to process
        files_to_process = []
        for ext, lang in self.LANGUAGE_MAP.items():
            if languages and lang not in languages:
                continue

            for file_path in directory.rglob(f"*{ext}"):
                # Apply ignore patterns
                if self._should_ignore(file_path, ignore_patterns):
                    continue

                # Check max depth
                if max_depth:
                    depth = len(file_path.relative_to(directory).parts) - 1
                    if depth > max_depth:
                        continue

                files_to_process.append((file_path, lang))

        total_files = len(files_to_process)

        # Process files
        for file_path, language in files_to_process:
            # Check cache
            file_hash = self._get_file_hash(file_path)
            cache_key = f"{file_path}:{file_hash}"

            if cache_key in self.cache:
                nodes = self.cache[cache_key]
                self.logger.debug(f"Using cached results for {file_path}")
            else:
                # Emit file start event
                if self.emitter:
                    self.emitter.emit_file_start(str(file_path), language)

                file_start = time.time()

                # Analyze based on language
                if language == "python":
                    nodes = self.python_analyzer.analyze_file(file_path)
                else:
                    nodes = self.multi_lang_analyzer.analyze_file(file_path, language)

                # Cache results
                self.cache[cache_key] = nodes

                # Emit file complete event
                if self.emitter:
                    self.emitter.emit_file_complete(
                        str(file_path), len(nodes), time.time() - file_start
                    )

            all_nodes.extend(nodes)
            files_processed += 1

            # Emit progress
            if self.emitter and files_processed % 10 == 0:
                self.emitter.emit_progress(
                    files_processed, total_files, f"Processing {file_path.name}"
                )

        # Build tree structure
        tree = self._build_tree(all_nodes, directory)

        # Calculate statistics
        duration = time.time() - start_time
        stats = {
            "files_processed": files_processed,
            "total_nodes": len(all_nodes),
            "duration": duration,
            "classes": sum(1 for n in all_nodes if n.node_type == "class"),
            "functions": sum(
                1 for n in all_nodes if n.node_type in ("function", "method")
            ),
            "imports": sum(1 for n in all_nodes if n.node_type == "import"),
            "languages": list(
                {n.language for n in all_nodes if hasattr(n, "language")}
            ),
            "avg_complexity": (
                sum(n.complexity for n in all_nodes) / len(all_nodes)
                if all_nodes
                else 0
            ),
        }

        # Save cache
        self._save_cache()

        # Stop emitter
        if self.emitter:
            self.emitter.stop()

        return {"tree": tree, "nodes": all_nodes, "stats": stats}

    def _should_ignore(self, file_path: Path, patterns: Optional[List[str]]) -> bool:
        """Check if file should be ignored."""
        if not patterns:
            patterns = []

        # Default ignore patterns
        default_ignores = [
            "__pycache__",
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "dist",
            "build",
            ".pytest_cache",
            ".mypy_cache",
        ]

        all_patterns = default_ignores + patterns

        return any(pattern in str(file_path) for pattern in all_patterns)

    def _get_file_hash(self, file_path: Path) -> str:
        """Get hash of file contents for caching."""
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            hasher.update(f.read())
        return hasher.hexdigest()

    def _build_tree(self, nodes: List[CodeNode], root_dir: Path) -> Dict[str, Any]:
        """Build hierarchical tree structure from flat nodes list."""
        tree = {
            "name": root_dir.name,
            "type": "directory",
            "path": str(root_dir),
            "children": [],
        }

        # Group nodes by file
        files_map = {}
        for node in nodes:
            if node.file_path not in files_map:
                files_map[node.file_path] = {
                    "name": Path(node.file_path).name,
                    "type": "file",
                    "path": node.file_path,
                    "children": [],
                }

            # Add node to file
            node_dict = {
                "name": node.name,
                "type": node.node_type,
                "line_start": node.line_start,
                "line_end": node.line_end,
                "complexity": node.complexity,
                "has_docstring": node.has_docstring,
                "decorators": node.decorators,
                "signature": node.signature,
            }
            files_map[node.file_path]["children"].append(node_dict)

        # Build directory structure
        for file_path, file_node in files_map.items():
            rel_path = Path(file_path).relative_to(root_dir)
            parts = rel_path.parts

            current = tree
            for part in parts[:-1]:
                # Find or create directory
                dir_node = None
                for child in current["children"]:
                    if child["type"] == "directory" and child["name"] == part:
                        dir_node = child
                        break

                if not dir_node:
                    dir_node = {"name": part, "type": "directory", "children": []}
                    current["children"].append(dir_node)

                current = dir_node

            # Add file to current directory
            current["children"].append(file_node)

        return tree

    def _load_cache(self):
        """Load cache from disk."""
        cache_file = self.cache_dir / "code_tree_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    cache_data = json.load(f)
                    # Reconstruct CodeNode objects
                    for key, nodes_data in cache_data.items():
                        self.cache[key] = [
                            CodeNode(**node_data) for node_data in nodes_data
                        ]
                self.logger.info(f"Loaded cache with {len(self.cache)} entries")
            except Exception as e:
                self.logger.warning(f"Failed to load cache: {e}")

    def _save_cache(self):
        """Save cache to disk."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_dir / "code_tree_cache.json"

        try:
            # Convert CodeNode objects to dictionaries
            cache_data = {}
            for key, nodes in self.cache.items():
                cache_data[key] = [
                    {
                        "file_path": n.file_path,
                        "node_type": n.node_type,
                        "name": n.name,
                        "line_start": n.line_start,
                        "line_end": n.line_end,
                        "complexity": n.complexity,
                        "has_docstring": n.has_docstring,
                        "decorators": n.decorators,
                        "parent": n.parent,
                        "language": n.language,
                        "signature": n.signature,
                    }
                    for n in nodes
                ]

            with open(cache_file, "w") as f:
                json.dump(cache_data, f, indent=2)

            self.logger.info(f"Saved cache with {len(self.cache)} entries")
        except Exception as e:
            self.logger.warning(f"Failed to save cache: {e}")
