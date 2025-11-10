#!/usr/bin/env python3
"""
Multi-Language Analyzer
========================

Analyzes multiple programming languages using tree-sitter.

WHY: Tree-sitter provides consistent parsing across multiple languages,
allowing us to support JavaScript, TypeScript, and other languages.
"""

import importlib.util
from pathlib import Path
from typing import ClassVar, List, Optional

from ...core.logging_config import get_logger
from ..code_tree_events import CodeNodeEvent, CodeTreeEventEmitter
from .models import CodeNode

# Check for tree-sitter availability
if importlib.util.find_spec("tree_sitter"):
    import tree_sitter

    TREE_SITTER_AVAILABLE = True
else:
    TREE_SITTER_AVAILABLE = False
    tree_sitter = None


class MultiLanguageAnalyzer:
    """Analyzes multiple programming languages using tree-sitter."""

    LANGUAGE_PARSERS: ClassVar[dict] = {
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
            with file_path.open("rb") as f:
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
