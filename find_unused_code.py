#!/usr/bin/env python3
"""
Find potentially unused code, imports, and dead code patterns.
"""

import ast
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


class UnusedCodeFinder:
    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.imports = defaultdict(set)  # file -> set of imports
        self.definitions = defaultdict(set)  # file -> set of defined symbols
        self.usages = defaultdict(set)  # file -> set of used symbols
        self.all_symbols = set()
        self.file_contents = {}

    def find_python_files(self):
        """Find all Python files."""
        python_files = []
        for root, dirs, files in os.walk(self.root_path):
            dirs[:] = [
                d
                for d in dirs
                if d not in {".git", "__pycache__", ".pytest_cache", "venv", ".venv"}
            ]
            for file in files:
                if file.endswith(".py"):
                    python_files.append(Path(root) / file)
        return python_files

    def analyze_file(self, file_path):
        """Analyze a single file for imports, definitions, and usage."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.file_contents[file_path] = content

            tree = ast.parse(content)

            # Find imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.imports[file_path].add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        full_name = f"{module}.{alias.name}" if module else alias.name
                        self.imports[file_path].add(full_name)

                # Find function and class definitions
                elif isinstance(node, ast.FunctionDef):
                    self.definitions[file_path].add(node.name)
                    self.all_symbols.add(node.name)
                elif isinstance(node, ast.ClassDef):
                    self.definitions[file_path].add(node.name)
                    self.all_symbols.add(node.name)

                # Find variable assignments
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.definitions[file_path].add(target.id)
                            self.all_symbols.add(target.id)

                # Find name usages
                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    self.usages[file_path].add(node.id)

                # Find attribute access
                elif isinstance(node, ast.Attribute):
                    self.usages[file_path].add(node.attr)

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

    def find_large_test_files(self):
        """Find large test files that might be obsolete."""
        large_tests = []
        for file_path in self.file_contents:
            if "test" in str(file_path).lower():
                lines = len(self.file_contents[file_path].split("\n"))
                if lines > 300:
                    large_tests.append(
                        {
                            "file": str(file_path.relative_to(self.root_path)),
                            "lines": lines,
                        }
                    )
        return sorted(large_tests, key=lambda x: x["lines"], reverse=True)

    def find_duplicate_patterns(self):
        """Find files with similar patterns that might be duplicates."""
        patterns = defaultdict(list)

        for file_path, content in self.file_contents.items():
            # Simple pattern: count of imports, functions, classes
            lines = content.split("\n")
            import_count = len(
                [
                    l
                    for l in lines
                    if l.strip().startswith("import ") or l.strip().startswith("from ")
                ]
            )
            func_count = len([l for l in lines if re.match(r"^\s*def ", l)])
            class_count = len([l for l in lines if re.match(r"^\s*class ", l)])

            pattern = (import_count, func_count, class_count)
            patterns[pattern].append(file_path)

        # Find patterns with multiple files
        duplicates = []
        for pattern, files in patterns.items():
            if len(files) > 1 and pattern != (0, 0, 0):  # Skip empty files
                duplicates.append(
                    {
                        "pattern": f"{pattern[0]} imports, {pattern[1]} functions, {pattern[2]} classes",
                        "files": [str(f.relative_to(self.root_path)) for f in files],
                        "count": len(files),
                    }
                )

        return sorted(duplicates, key=lambda x: x["count"], reverse=True)

    def find_unused_imports(self):
        """Find potentially unused imports."""
        unused = []

        for file_path, imports in self.imports.items():
            file_usages = self.usages[file_path]

            for import_name in imports:
                # Simple check: if import name not found in usages
                base_name = import_name.split(".")[-1]
                if base_name not in file_usages and import_name not in file_usages:
                    # Additional check: not used in string literals
                    content = self.file_contents[file_path]
                    if base_name not in content.replace(
                        f"import {import_name}", ""
                    ).replace(f"from {import_name}", ""):
                        unused.append(
                            {
                                "file": str(file_path.relative_to(self.root_path)),
                                "import": import_name,
                            }
                        )

        return unused

    def find_dead_code_patterns(self):
        """Find potential dead code patterns."""
        dead_patterns = []

        for file_path, content in self.file_contents.items():
            lines = content.split("\n")

            # Look for TODO/FIXME/XXX comments
            todos = []
            for i, line in enumerate(lines, 1):
                if re.search(r"#.*\b(TODO|FIXME|XXX|HACK)\b", line, re.IGNORECASE):
                    todos.append(i)

            # Look for commented out code blocks
            commented_blocks = []
            in_block = False
            block_start = 0
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if (
                    stripped.startswith("#") and len(stripped) > 10
                ):  # Likely commented code
                    if not in_block:
                        in_block = True
                        block_start = i
                elif in_block and not stripped.startswith("#"):
                    if i - block_start > 3:  # Block of 3+ lines
                        commented_blocks.append((block_start, i - 1))
                    in_block = False

            # Look for empty functions/classes
            empty_defs = []
            for i, line in enumerate(lines, 1):
                if re.match(r"^\s*(def|class)\s+\w+", line):
                    # Check if next few lines are just pass/docstring
                    next_lines = lines[i : i + 5] if i < len(lines) - 5 else lines[i:]
                    non_empty = [
                        l
                        for l in next_lines
                        if l.strip()
                        and not l.strip().startswith('"""')
                        and not l.strip().startswith("'''")
                        and l.strip() != "pass"
                    ]
                    if len(non_empty) <= 1:
                        empty_defs.append(i)

            if todos or commented_blocks or empty_defs:
                dead_patterns.append(
                    {
                        "file": str(file_path.relative_to(self.root_path)),
                        "todos": len(todos),
                        "commented_blocks": len(commented_blocks),
                        "empty_definitions": len(empty_defs),
                        "total_issues": len(todos)
                        + len(commented_blocks)
                        + len(empty_defs),
                    }
                )

        return sorted(dead_patterns, key=lambda x: x["total_issues"], reverse=True)

    def analyze(self):
        """Run complete analysis."""
        files = self.find_python_files()
        print(f"Analyzing {len(files)} Python files for unused code...")

        for file_path in files:
            self.analyze_file(file_path)

        return {
            "large_tests": self.find_large_test_files(),
            "duplicate_patterns": self.find_duplicate_patterns(),
            "unused_imports": self.find_unused_imports(),
            "dead_code_patterns": self.find_dead_code_patterns(),
        }


def main():
    if len(sys.argv) > 1:
        root_path = sys.argv[1]
    else:
        root_path = "."

    finder = UnusedCodeFinder(root_path)
    results = finder.analyze()

    print("\n" + "=" * 80)
    print("UNUSED CODE ANALYSIS REPORT")
    print("=" * 80)

    print(f"\nLARGE TEST FILES (>300 lines):")
    for item in results["large_tests"][:10]:
        print(f"  {item['file']}: {item['lines']} lines")

    print(f"\nPOTENTIAL DUPLICATE PATTERNS:")
    for item in results["duplicate_patterns"][:10]:
        print(f"  {item['pattern']} - {item['count']} files:")
        for file in item["files"][:3]:  # Show first 3
            print(f"    {file}")
        if len(item["files"]) > 3:
            print(f"    ... and {len(item['files']) - 3} more")

    print(f"\nDEAD CODE PATTERNS:")
    for item in results["dead_code_patterns"][:15]:
        print(
            f"  {item['file']}: {item['todos']} TODOs, {item['commented_blocks']} comment blocks, {item['empty_definitions']} empty defs"
        )

    print(f"\nPOTENTIALLY UNUSED IMPORTS (first 20):")
    for item in results["unused_imports"][:20]:
        print(f"  {item['file']}: {item['import']}")


if __name__ == "__main__":
    main()
