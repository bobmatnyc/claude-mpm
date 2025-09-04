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
    import pathspec

    PATHSPEC_AVAILABLE = True
except ImportError:
    PATHSPEC_AVAILABLE = False
    pathspec = None

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


class GitignoreManager:
    """Manages .gitignore pattern matching for file filtering.

    WHY: Properly respecting .gitignore patterns ensures we don't analyze
    or display files that should be ignored in the repository.
    """

    # Default patterns that should always be ignored
    DEFAULT_PATTERNS = [
        ".git/",
        "__pycache__/",
        "*.pyc",
        "*.pyo",
        ".DS_Store",
        ".pytest_cache/",
        ".mypy_cache/",
        "dist/",
        "build/",
        "*.egg-info/",
        ".coverage",
        ".tox/",
        "htmlcov/",
        ".idea/",
        ".vscode/",
        "*.swp",
        "*.swo",
        "*~",
        "Thumbs.db",
        "node_modules/",
        ".venv/",
        "venv/",
        "env/",
        ".env",
        "*.log",
        ".ipynb_checkpoints/",
        "__MACOSX/",
        ".Spotlight-V100/",
        ".Trashes/",
        "desktop.ini",
    ]

    # Additional patterns to hide dotfiles (when enabled)
    DOTFILE_PATTERNS = [
        ".*",  # All dotfiles
        ".*/",  # All dot directories
    ]

    # Important files/directories to always show
    DOTFILE_EXCEPTIONS = {
        # Removed .gitignore from exceptions - it should be hidden by default
        ".env.example",
        ".env.sample",
        ".gitlab-ci.yml",
        ".travis.yml",
        ".dockerignore",
        ".editorconfig",
        ".eslintrc",
        ".prettierrc",
        # Removed .github from exceptions - it should be hidden by default
    }

    def __init__(self):
        """Initialize the GitignoreManager."""
        self.logger = get_logger(__name__)
        self._pathspec_cache: Dict[str, Any] = {}
        self._gitignore_cache: Dict[str, List[str]] = {}
        self._use_pathspec = PATHSPEC_AVAILABLE

        if not self._use_pathspec:
            self.logger.warning(
                "pathspec library not available - using basic pattern matching"
            )

    def get_ignore_patterns(self, working_dir: Path) -> List[str]:
        """Get all ignore patterns for a directory.

        Args:
            working_dir: The working directory to search for .gitignore files

        Returns:
            Combined list of ignore patterns from all sources
        """
        # Always include default patterns
        patterns = self.DEFAULT_PATTERNS.copy()

        # Don't add dotfile patterns here - handle them separately in should_ignore
        # This prevents exceptions from being overridden by the .* pattern

        # Find and parse .gitignore files
        gitignore_files = self._find_gitignore_files(working_dir)
        for gitignore_file in gitignore_files:
            patterns.extend(self._parse_gitignore(gitignore_file))

        return patterns

    def should_ignore(self, path: Path, working_dir: Path) -> bool:
        """Check if a path should be ignored based on patterns.

        Args:
            path: The path to check
            working_dir: The working directory (for relative path calculation)

        Returns:
            True if the path should be ignored
        """
        # Get the filename
        filename = path.name

        # 1. ALWAYS hide system files regardless of settings
        ALWAYS_HIDE = {".DS_Store", "Thumbs.db", ".pyc", ".pyo", ".pyd"}
        if filename in ALWAYS_HIDE or filename.endswith((".pyc", ".pyo", ".pyd")):
            return True

        # 2. Check dotfiles - ALWAYS filter them out (except exceptions)
        if filename.startswith("."):
            # Hide all dotfiles except those in the exceptions list
            # This means: return True (ignore) if NOT in exceptions
            return filename not in self.DOTFILE_EXCEPTIONS

        # Get or create PathSpec for this working directory
        pathspec_obj = self._get_pathspec(working_dir)

        if pathspec_obj:
            # Use pathspec for accurate matching
            try:
                rel_path = path.relative_to(working_dir)
                rel_path_str = str(rel_path)

                # For directories, also check with trailing slash
                if path.is_dir():
                    return pathspec_obj.match_file(
                        rel_path_str
                    ) or pathspec_obj.match_file(rel_path_str + "/")
                return pathspec_obj.match_file(rel_path_str)
            except ValueError:
                # Path is outside working directory
                return False
        else:
            # Fallback to basic pattern matching
            return self._basic_should_ignore(path, working_dir)

    def _get_pathspec(self, working_dir: Path) -> Optional[Any]:
        """Get or create a PathSpec object for the working directory.

        Args:
            working_dir: The working directory

        Returns:
            PathSpec object or None if not available
        """
        if not self._use_pathspec:
            return None

        cache_key = str(working_dir)
        if cache_key not in self._pathspec_cache:
            patterns = self.get_ignore_patterns(working_dir)
            try:
                self._pathspec_cache[cache_key] = pathspec.PathSpec.from_lines(
                    "gitwildmatch", patterns
                )
            except Exception as e:
                self.logger.warning(f"Failed to create PathSpec: {e}")
                return None

        return self._pathspec_cache[cache_key]

    def _find_gitignore_files(self, working_dir: Path) -> List[Path]:
        """Find all .gitignore files in the directory tree.

        Args:
            working_dir: The directory to search

        Returns:
            List of .gitignore file paths
        """
        gitignore_files = []

        # Check for .gitignore in working directory
        main_gitignore = working_dir / ".gitignore"
        if main_gitignore.exists():
            gitignore_files.append(main_gitignore)

        # Also check parent directories up to repository root
        current = working_dir
        while current != current.parent:
            parent_gitignore = current.parent / ".gitignore"
            if parent_gitignore.exists():
                gitignore_files.append(parent_gitignore)

            # Stop if we find a .git directory (repository root)
            if (current / ".git").exists():
                break

            current = current.parent

        return gitignore_files

    def _parse_gitignore(self, gitignore_path: Path) -> List[str]:
        """Parse a .gitignore file and return patterns.

        Args:
            gitignore_path: Path to .gitignore file

        Returns:
            List of patterns from the file
        """
        cache_key = str(gitignore_path)

        # Check cache
        if cache_key in self._gitignore_cache:
            return self._gitignore_cache[cache_key]

        patterns = []
        try:
            with open(gitignore_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        patterns.append(line)

            self._gitignore_cache[cache_key] = patterns
        except Exception as e:
            self.logger.warning(f"Failed to parse {gitignore_path}: {e}")

        return patterns

    def _basic_should_ignore(self, path: Path, working_dir: Path) -> bool:
        """Basic pattern matching fallback when pathspec is not available.

        Args:
            path: The path to check
            working_dir: The working directory

        Returns:
            True if the path should be ignored
        """
        path_str = str(path)
        path_name = path.name

        # 1. ALWAYS hide system files regardless of settings
        ALWAYS_HIDE = {".DS_Store", "Thumbs.db", ".pyc", ".pyo", ".pyd"}
        if path_name in ALWAYS_HIDE or path_name.endswith((".pyc", ".pyo", ".pyd")):
            return True

        # 2. Check dotfiles - ALWAYS filter them out (except exceptions)
        if path_name.startswith("."):
            # Only show if in exceptions list
            return path_name not in self.DOTFILE_EXCEPTIONS

        patterns = self.get_ignore_patterns(working_dir)

        for pattern in patterns:
            # Skip dotfile patterns since we already handled them above
            if pattern in [".*", ".*/"]:
                continue

            # Simple pattern matching
            if pattern.endswith("/"):
                # Directory pattern
                if path.is_dir() and path_name == pattern[:-1]:
                    return True
            elif pattern.startswith("*."):
                # Extension pattern
                if path_name.endswith(pattern[1:]):
                    return True
            elif "*" in pattern:
                # Wildcard pattern (simplified)
                import fnmatch

                if fnmatch.fnmatch(path_name, pattern):
                    return True
            elif pattern in path_str:
                # Substring match
                return True
            elif path_name == pattern:
                # Exact match
                return True

        return False

    def clear_cache(self):
        """Clear all caches."""
        self._pathspec_cache.clear()
        self._gitignore_cache.clear()


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
        except:
            return f"{var_name} = ..."


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
                # Silently skip unavailable parsers - will fall back to basic file discovery
                self.logger.debug(f"Language parser not available for {lang}: {e}")

    def analyze_file(self, file_path: Path, language: str) -> List[CodeNode]:
        """Analyze a file using tree-sitter.

        Args:
            file_path: Path to source file
            language: Programming language

        Returns:
            List of code nodes found in the file
        """
        if language not in self.parsers:
            # No parser available - return empty list to fall back to basic discovery
            self.logger.debug(
                f"No parser available for language: {language}, using basic file discovery"
            )
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

    # Define code file extensions at class level for directory filtering
    CODE_EXTENSIONS = {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".mjs",  # Added missing extension
        ".cjs",  # Added missing extension
        ".java",
        ".cpp",
        ".c",
        ".h",
        ".hpp",
        ".cs",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".scala",
        ".r",
        ".m",
        ".mm",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".ps1",
        ".bat",
        ".cmd",
        ".sql",
        ".html",
        ".css",
        ".scss",
        ".sass",
        ".less",
        ".xml",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".md",
        ".rst",
        ".txt",
    }

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

    def __init__(
        self,
        emit_events: bool = True,
        cache_dir: Optional[Path] = None,
        emitter: Optional[CodeTreeEventEmitter] = None,
    ):
        """Initialize the code tree analyzer.

        Args:
            emit_events: Whether to emit Socket.IO events
            cache_dir: Directory for caching analysis results
            emitter: Optional event emitter to use (creates one if not provided)
        """
        self.logger = get_logger(__name__)
        self.emit_events = emit_events
        self.cache_dir = cache_dir or Path.home() / ".claude-mpm" / "code-cache"

        # Initialize gitignore manager (always filters dotfiles)
        self.gitignore_manager = GitignoreManager()
        self._last_working_dir = None

        # Use provided emitter or create one
        if emitter:
            self.emitter = emitter
        elif emit_events:
            self.emitter = CodeTreeEventEmitter(use_stdout=True)
        else:
            self.emitter = None

        # Initialize language analyzers
        self.python_analyzer = PythonAnalyzer(self.emitter)
        self.multi_lang_analyzer = MultiLanguageAnalyzer(self.emitter)

        # For JavaScript/TypeScript
        self.javascript_analyzer = self.multi_lang_analyzer
        self.generic_analyzer = self.multi_lang_analyzer

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
                # Use gitignore manager for filtering with directory as working dir
                if self.gitignore_manager.should_ignore(file_path, directory):
                    continue

                # Also check additional patterns
                if ignore_patterns and any(
                    p in str(file_path) for p in ignore_patterns
                ):
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

                    # If no nodes found and we have a valid language, emit basic file info
                    if not nodes and language != "unknown":
                        self.logger.debug(
                            f"No AST nodes found for {file_path}, using basic discovery"
                        )

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
        """Check if file should be ignored.

        Uses GitignoreManager for proper pattern matching.
        """
        # Get the working directory (use parent for files, self for directories)
        if file_path.is_file():
            working_dir = file_path.parent
        else:
            # For directories during discovery, use the parent
            working_dir = (
                file_path.parent if file_path.parent != file_path else Path.cwd()
            )

        # Use gitignore manager for checking
        if self.gitignore_manager.should_ignore(file_path, working_dir):
            return True

        # Also check any additional patterns provided
        if patterns:
            path_str = str(file_path)
            return any(pattern in path_str for pattern in patterns)

        return False

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

    def has_code_files(
        self, directory: Path, depth: int = 5, current_depth: int = 0
    ) -> bool:
        """Check if directory contains code files up to 5 levels deep.

        Args:
            directory: Directory to check
            depth: Maximum depth to search
            current_depth: Current recursion depth

        Returns:
            True if directory contains code files within depth levels
        """
        if current_depth >= depth:
            return False

        # Skip checking these directories entirely
        SKIP_DIRS = {
            "node_modules",
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "dist",
            "build",
            ".tox",
            "htmlcov",
            ".pytest_cache",
            ".mypy_cache",
            "coverage",
            ".idea",
            ".vscode",
            "env",
            ".coverage",
            "__MACOSX",
            ".ipynb_checkpoints",
        }
        # Skip directories in the skip list or egg-info directories
        if directory.name in SKIP_DIRS or directory.name.endswith(".egg-info"):
            return False

        try:
            for item in directory.iterdir():
                # Skip hidden items in scan
                if item.name.startswith("."):
                    continue

                if item.is_file():
                    # Check if it's a code file
                    ext = item.suffix.lower()
                    if ext in self.CODE_EXTENSIONS:
                        return True
                elif item.is_dir() and current_depth < depth - 1:
                    # Skip egg-info directories in the recursive check too
                    if item.name.endswith(".egg-info"):
                        continue
                    if self.has_code_files(item, depth, current_depth + 1):
                        return True

        except (PermissionError, OSError):
            pass

        return False

    def discover_top_level(
        self, directory: Path, ignore_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Discover only top-level directories and files for lazy loading.

        Args:
            directory: Root directory to discover
            ignore_patterns: Patterns to ignore

        Returns:
            Dictionary with top-level structure
        """
        # CRITICAL FIX: Use the directory parameter as the base for relative paths
        # NOT the current working directory. This ensures we only show items
        # within the requested directory, not parent directories.
        Path(directory).absolute()

        # Emit discovery start event
        if self.emitter:
            from datetime import datetime

            self.emitter.emit(
                "info",
                {
                    "type": "discovery.start",
                    "action": "scanning_directory",
                    "path": str(directory),
                    "message": f"Starting discovery of {directory.name}",
                    "timestamp": datetime.now().isoformat(),
                },
            )

        result = {
            "path": str(directory),
            "name": directory.name,
            "type": "directory",
            "children": [],
        }

        try:
            # Clear cache if working directory changed
            if self._last_working_dir != directory:
                self.gitignore_manager.clear_cache()
                self._last_working_dir = directory

            # Get immediate children only (no recursion)
            files_count = 0
            dirs_count = 0
            ignored_count = 0

            for item in directory.iterdir():
                # Use gitignore manager for filtering with the directory as working dir
                if self.gitignore_manager.should_ignore(item, directory):
                    if self.emitter:
                        from datetime import datetime

                        self.emitter.emit(
                            "info",
                            {
                                "type": "filter.gitignore",
                                "path": str(item),
                                "reason": "gitignore pattern",
                                "message": f"Ignored by gitignore: {item.name}",
                                "timestamp": datetime.now().isoformat(),
                            },
                        )
                    ignored_count += 1
                    continue

                # Also check additional patterns if provided
                if ignore_patterns and any(p in str(item) for p in ignore_patterns):
                    if self.emitter:
                        from datetime import datetime

                        self.emitter.emit(
                            "info",
                            {
                                "type": "filter.pattern",
                                "path": str(item),
                                "reason": "custom pattern",
                                "message": f"Ignored by pattern: {item.name}",
                                "timestamp": datetime.now().isoformat(),
                            },
                        )
                    ignored_count += 1
                    continue

                if item.is_dir():
                    # Check if directory contains code files (recursively checking subdirectories)
                    # Important: We want to include directories even if they only have code
                    # in subdirectories (like src/claude_mpm/*.py)
                    if not self.has_code_files(item, depth=5):
                        if self.emitter:
                            from datetime import datetime

                            self.emitter.emit(
                                "info",
                                {
                                    "type": "filter.no_code",
                                    "path": str(item.name),
                                    "reason": "no code files",
                                    "message": f"Skipped directory without code: {item.name}",
                                    "timestamp": datetime.now().isoformat(),
                                },
                            )
                        ignored_count += 1
                        continue

                    # Directory - return just the item name
                    # The frontend will construct the full path by combining parent path with child name
                    path_str = item.name

                    # Emit directory found event
                    if self.emitter:
                        from datetime import datetime

                        self.emitter.emit(
                            "info",
                            {
                                "type": "discovery.directory",
                                "path": str(item),
                                "message": f"Found directory: {item.name}",
                                "timestamp": datetime.now().isoformat(),
                            },
                        )
                    dirs_count += 1

                    child = {
                        "path": path_str,
                        "name": item.name,
                        "type": "directory",
                        "discovered": False,
                        "children": [],
                    }
                    result["children"].append(child)

                    # Don't emit directory discovered event here with empty children
                    # The actual discovery will happen when the directory is clicked
                    # This prevents confusing the frontend with empty directory events
                    # if self.emitter:
                    #     self.emitter.emit_directory_discovered(path_str, [])

                elif item.is_file():
                    # Check if it's a supported code file or a special file we want to show
                    if item.suffix in self.supported_extensions or item.name in [
                        ".gitignore",
                        ".env.example",
                        ".env.sample",
                    ]:
                        # File - mark for lazy analysis
                        language = self._get_language(item)

                        # File path should be just the item name
                        # The frontend will construct the full path by combining parent path with child name
                        path_str = item.name

                        # Emit file found event
                        if self.emitter:
                            from datetime import datetime

                            self.emitter.emit(
                                "info",
                                {
                                    "type": "discovery.file",
                                    "path": str(item),
                                    "language": language,
                                    "size": item.stat().st_size,
                                    "message": f"Found file: {item.name} ({language})",
                                    "timestamp": datetime.now().isoformat(),
                                },
                            )
                        files_count += 1

                        child = {
                            "path": path_str,
                            "name": item.name,
                            "type": "file",
                            "language": language,
                            "size": item.stat().st_size,
                            "analyzed": False,
                        }
                        result["children"].append(child)

                        if self.emitter:
                            self.emitter.emit_file_discovered(
                                path_str, language, item.stat().st_size
                            )

        except PermissionError as e:
            self.logger.warning(f"Permission denied accessing {directory}: {e}")
            if self.emitter:
                self.emitter.emit_error(str(directory), f"Permission denied: {e}")

        # Emit discovery complete event with stats
        if self.emitter:
            from datetime import datetime

            self.emitter.emit(
                "info",
                {
                    "type": "discovery.complete",
                    "path": str(directory),
                    "stats": {
                        "files": files_count,
                        "directories": dirs_count,
                        "ignored": ignored_count,
                    },
                    "message": f"Discovery complete: {files_count} files, {dirs_count} directories, {ignored_count} ignored",
                    "timestamp": datetime.now().isoformat(),
                },
            )

        return result

    def discover_directory(
        self, dir_path: str, ignore_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Discover contents of a specific directory for lazy loading.

        Args:
            dir_path: Directory path to discover
            ignore_patterns: Patterns to ignore

        Returns:
            Dictionary with directory contents
        """
        directory = Path(dir_path)
        if not directory.exists() or not directory.is_dir():
            return {"error": f"Invalid directory: {dir_path}"}

        # Clear cache if working directory changed
        if self._last_working_dir != directory.parent:
            self.gitignore_manager.clear_cache()
            self._last_working_dir = directory.parent

        # The discover_top_level method will emit all the INFO events
        return self.discover_top_level(directory, ignore_patterns)

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a specific file and return its AST structure.

        Args:
            file_path: Path to file to analyze

        Returns:
            Dictionary with file analysis results
        """
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return {"error": f"Invalid file: {file_path}"}

        # Get language first (needed for return statement)
        language = self._get_language(path)

        # Emit analysis start event
        if self.emitter:
            from datetime import datetime

            self.emitter.emit(
                "info",
                {
                    "type": "analysis.start",
                    "file": str(path),
                    "language": language,
                    "message": f"Analyzing: {path.name}",
                    "timestamp": datetime.now().isoformat(),
                },
            )

        # Check cache
        file_hash = self._get_file_hash(path)
        cache_key = f"{file_path}:{file_hash}"

        if cache_key in self.cache:
            nodes = self.cache[cache_key]
            if self.emitter:
                from datetime import datetime

                self.emitter.emit(
                    "info",
                    {
                        "type": "cache.hit",
                        "file": str(path),
                        "message": f"Using cached analysis for {path.name}",
                        "timestamp": datetime.now().isoformat(),
                    },
                )
        else:
            # Analyze file
            if self.emitter:
                from datetime import datetime

                self.emitter.emit(
                    "info",
                    {
                        "type": "cache.miss",
                        "file": str(path),
                        "message": f"Cache miss, analyzing fresh: {path.name}",
                        "timestamp": datetime.now().isoformat(),
                    },
                )

            if language == "python":
                analyzer = self.python_analyzer
            elif language in {"javascript", "typescript"}:
                analyzer = self.javascript_analyzer
            else:
                analyzer = self.generic_analyzer

            start_time = time.time()

            # Emit parsing event
            if self.emitter:
                from datetime import datetime

                self.emitter.emit(
                    "info",
                    {
                        "type": "analysis.parse",
                        "file": str(path),
                        "message": f"Parsing file content: {path.name}",
                        "timestamp": datetime.now().isoformat(),
                    },
                )

            nodes = analyzer.analyze_file(path) if analyzer else []
            duration = time.time() - start_time

            # Cache results
            self.cache[cache_key] = nodes

            # Filter internal functions before emitting
            filtered_nodes = []
            classes_count = 0
            functions_count = 0
            methods_count = 0

            for node in nodes:
                # Only include main structural elements
                if not self._is_internal_node(node):
                    # Emit found element event
                    if self.emitter:
                        from datetime import datetime

                        self.emitter.emit(
                            "info",
                            {
                                "type": f"analysis.{node.node_type}",
                                "name": node.name,
                                "file": str(path),
                                "line_start": node.line_start,
                                "complexity": node.complexity,
                                "message": f"Found {node.node_type}: {node.name}",
                                "timestamp": datetime.now().isoformat(),
                            },
                        )

                        # Count node types
                        if node.node_type == "class":
                            classes_count += 1
                        elif node.node_type == "function":
                            functions_count += 1
                        elif node.node_type == "method":
                            methods_count += 1

                    filtered_nodes.append(
                        {
                            "name": node.name,
                            "type": node.node_type,
                            "line_start": node.line_start,
                            "line_end": node.line_end,
                            "complexity": node.complexity,
                            "has_docstring": node.has_docstring,
                            "signature": node.signature,
                        }
                    )

            # Emit analysis complete event with stats
            if self.emitter:
                from datetime import datetime

                self.emitter.emit(
                    "info",
                    {
                        "type": "analysis.complete",
                        "file": str(path),
                        "stats": {
                            "classes": classes_count,
                            "functions": functions_count,
                            "methods": methods_count,
                            "total_nodes": len(filtered_nodes),
                        },
                        "duration": duration,
                        "message": f"Analysis complete: {classes_count} classes, {functions_count} functions, {methods_count} methods",
                        "timestamp": datetime.now().isoformat(),
                    },
                )

                self.emitter.emit_file_analyzed(file_path, filtered_nodes, duration)

        # Prepare the nodes data
        final_nodes = (
            filtered_nodes
            if "filtered_nodes" in locals()
            else [
                {
                    "name": n.name,
                    "type": n.node_type,
                    "line_start": n.line_start,
                    "line_end": n.line_end,
                    "complexity": n.complexity,
                    "has_docstring": n.has_docstring,
                    "signature": n.signature,
                }
                for n in nodes
                if not self._is_internal_node(n)
            ]
        )

        # Convert nodes to elements format for dashboard compatibility
        elements = []
        for node in final_nodes:
            element = {
                "name": node["name"],
                "type": node["type"],
                "line": node["line_start"],  # Dashboard expects 'line' not 'line_start'
                "complexity": node["complexity"],
                "signature": node.get("signature", ""),
                "has_docstring": node.get("has_docstring", False),
            }
            # Add methods if it's a class (for expandable tree)
            if node["type"] == "class":
                element["methods"] = []  # Could be populated with class methods
            elements.append(element)

        return {
            "path": file_path,
            "language": language,
            "nodes": final_nodes,  # Keep for backward compatibility
            "elements": elements,  # Add for dashboard compatibility
            "complexity": sum(e["complexity"] for e in elements),
            "lines": len(elements),  # Simple line count approximation
            "stats": {
                "classes": len([e for e in elements if e["type"] == "class"]),
                "functions": len([e for e in elements if e["type"] == "function"]),
                "methods": len([e for e in elements if e["type"] == "method"]),
                "variables": len([e for e in elements if e["type"] == "variable"]),
                "imports": len([e for e in elements if e["type"] == "import"]),
                "total": len(elements),
            },
        }

    def _is_internal_node(self, node: CodeNode) -> bool:
        """Check if node is an internal function that should be filtered."""
        # Don't filter classes - always show them
        if node.node_type == "class":
            return False

        # Don't filter variables or imports - they're useful for tree view
        if node.node_type in ["variable", "import"]:
            return False

        name_lower = node.name.lower()

        # Filter only very specific internal patterns
        # Be more conservative - only filter obvious internal handlers
        if name_lower.startswith("handle_") or name_lower.startswith("on_"):
            return True

        # Filter Python magic methods except important ones
        if name_lower.startswith("__") and name_lower.endswith("__"):
            # Keep important magic methods
            important_magic = [
                "__init__",
                "__call__",
                "__enter__",
                "__exit__",
                "__str__",
                "__repr__",
            ]
            return node.name not in important_magic

        # Filter very generic getters/setters only if they're trivial
        if (name_lower.startswith("get_") or name_lower.startswith("set_")) and len(
            node.name
        ) <= 8:
            return True

        # Don't filter single underscore functions - they're often important
        # (like _setup_logging, _validate_input, etc.)
        return False

        return False

    @property
    def supported_extensions(self):
        """Get list of supported file extensions."""
        return {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}

    def _get_language(self, file_path: Path) -> str:
        """Determine language from file extension."""
        ext = file_path.suffix.lower()
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".mjs": "javascript",
            ".cjs": "javascript",
        }
        return language_map.get(ext, "unknown")
