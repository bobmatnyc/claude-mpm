#!/usr/bin/env python3
"""
Comprehensive Code Quality Analysis Script for Claude MPM
Analyzes imports, complexity, duplication, and structural issues.
"""

import ast
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


class CodeAnalyzer:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.src_path = self.root_path / "src" / "claude_mpm"
        self.issues = {
            "unused_imports": [],
            "circular_imports": [],
            "complex_functions": [],
            "long_files": [],
            "duplications": [],
            "import_organization": [],
        }
        self.import_graph = defaultdict(set)
        self.all_imports = defaultdict(set)
        self.defined_symbols = defaultdict(set)
        self.used_symbols = defaultdict(set)

    def analyze_file(self, filepath: Path) -> Dict:
        """Analyze a single Python file."""
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content, filename=str(filepath))

            file_info = {
                "path": str(filepath.relative_to(self.root_path)),
                "lines": len(content.splitlines()),
                "imports": [],
                "functions": [],
                "classes": [],
                "complexity": 0,
            }

            # Analyze imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        file_info["imports"].append(alias.name)
                        self.all_imports[filepath].add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        import_name = f"{module}.{alias.name}" if module else alias.name
                        file_info["imports"].append(import_name)
                        self.all_imports[filepath].add(import_name)

                        # Track internal imports for circular detection
                        if module and module.startswith("claude_mpm"):
                            self.import_graph[filepath].add(module)

                # Track function definitions and usage
                elif isinstance(node, ast.FunctionDef):
                    func_lines = (
                        node.end_lineno - node.lineno
                        if hasattr(node, "end_lineno")
                        else 0
                    )
                    complexity = self._calculate_complexity(node)

                    file_info["functions"].append(
                        {
                            "name": node.name,
                            "line": node.lineno,
                            "lines": func_lines,
                            "complexity": complexity,
                        }
                    )

                    self.defined_symbols[filepath].add(node.name)

                    # Check for high complexity
                    if complexity > 10:
                        self.issues["complex_functions"].append(
                            {
                                "file": str(filepath.relative_to(self.root_path)),
                                "function": node.name,
                                "line": node.lineno,
                                "complexity": complexity,
                                "lines": func_lines,
                            }
                        )

                # Track class definitions
                elif isinstance(node, ast.ClassDef):
                    class_lines = (
                        node.end_lineno - node.lineno
                        if hasattr(node, "end_lineno")
                        else 0
                    )
                    file_info["classes"].append(
                        {"name": node.name, "line": node.lineno, "lines": class_lines}
                    )
                    self.defined_symbols[filepath].add(node.name)

                # Track name usage
                elif isinstance(node, ast.Name):
                    self.used_symbols[filepath].add(node.id)

            # Check for long files
            if file_info["lines"] > 500:
                self.issues["long_files"].append(
                    {
                        "file": str(filepath.relative_to(self.root_path)),
                        "lines": file_info["lines"],
                        "functions": len(file_info["functions"]),
                        "classes": len(file_info["classes"]),
                    }
                )

            return file_info

        except Exception as e:
            print(f"Error analyzing {filepath}: {e}", file=sys.stderr)
            return None

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def detect_circular_imports(self):
        """Detect circular import dependencies."""

        def visit(node, path, visited):
            if node in path:
                cycle = path[path.index(node) :] + [node]
                cycle_str = " -> ".join(
                    [str(p.relative_to(self.root_path)) for p in cycle]
                )
                self.issues["circular_imports"].append(cycle_str)
                return

            if node in visited:
                return

            visited.add(node)
            for neighbor in self.import_graph.get(node, []):
                # Convert module name to file path
                module_parts = neighbor.replace("claude_mpm.", "").split(".")
                potential_file = self.src_path / "/".join(module_parts)

                if potential_file.with_suffix(".py").exists():
                    visit(potential_file.with_suffix(".py"), path + [node], visited)
                elif (potential_file / "__init__.py").exists():
                    visit(potential_file / "__init__.py", path + [node], visited)

        visited = set()
        for node in self.import_graph:
            if node not in visited:
                visit(node, [], visited)

    def analyze_all_files(self):
        """Analyze all Python files in the project."""
        print("Starting comprehensive analysis...")

        python_files = list(self.src_path.rglob("*.py"))
        print(f"Found {len(python_files)} Python files")

        file_stats = []
        for filepath in python_files:
            if "__pycache__" in str(filepath):
                continue

            info = self.analyze_file(filepath)
            if info:
                file_stats.append(info)

        print(f"Analyzed {len(file_stats)} files successfully")

        # Detect circular imports
        self.detect_circular_imports()

        return file_stats

    def find_duplicate_patterns(self, file_stats: List[Dict]):
        """Find duplicate code patterns."""
        # Simple heuristic: find functions with similar names
        function_names = defaultdict(list)

        for stat in file_stats:
            for func in stat["functions"]:
                name_normalized = func["name"].lower().replace("_", "")
                function_names[name_normalized].append(
                    {
                        "file": stat["path"],
                        "name": func["name"],
                        "line": func["line"],
                        "lines": func["lines"],
                    }
                )

        # Report potential duplicates
        for name, occurrences in function_names.items():
            if len(occurrences) > 1 and len(name) > 5:  # Meaningful names only
                self.issues["duplications"].append(
                    {"pattern": name, "occurrences": occurrences}
                )

    def generate_report(self) -> Dict:
        """Generate comprehensive analysis report."""
        return {
            "summary": {
                "unused_imports": len(self.issues["unused_imports"]),
                "circular_imports": len(self.issues["circular_imports"]),
                "complex_functions": len(self.issues["complex_functions"]),
                "long_files": len(self.issues["long_files"]),
                "potential_duplications": len(self.issues["duplications"]),
            },
            "issues": self.issues,
        }


def main():
    root_path = "/Users/masa/Projects/claude-mpm"
    analyzer = CodeAnalyzer(root_path)

    file_stats = analyzer.analyze_all_files()
    analyzer.find_duplicate_patterns(file_stats)

    report = analyzer.generate_report()

    # Output as JSON
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
