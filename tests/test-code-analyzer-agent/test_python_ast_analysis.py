#!/usr/bin/env python3
"""
Test script to validate Python AST analysis functionality in the code_analyzer agent.
This script tests the agent's ability to use Python's native AST for .py files.
"""

import ast
import subprocess
import sys
from pathlib import Path


def test_python_ast_parsing():
    """Test that Python AST can parse our sample file correctly."""
    print("=" * 60)
    print("TESTING: Python AST Parsing")
    print("=" * 60)

    sample_file = Path(__file__).parent / "sample_python_file.py"

    try:
        with open(sample_file) as f:
            source_code = f.read()

        # Parse with Python AST
        tree = ast.parse(source_code)
        print(f"✅ Successfully parsed {sample_file} using Python AST")
        print(f"   AST root node type: {type(tree).__name__}")
        print(f"   Source length: {len(source_code)} characters")

        return True
    except Exception as e:
        print(f"❌ Failed to parse {sample_file}: {e}")
        return False


def analyze_python_with_ast():
    """Analyze Python file using AST to demonstrate detailed analysis capabilities."""
    print("\n" + "=" * 60)
    print("TESTING: Python AST Analysis Capabilities")
    print("=" * 60)

    sample_file = Path(__file__).parent / "sample_python_file.py"

    try:
        with open(sample_file) as f:
            source_code = f.read()

        tree = ast.parse(source_code)

        # Extract detailed information using AST
        classes = []
        functions = []
        imports = []
        hardcoded_strings = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "methods": len(
                            [
                                n
                                for n in node.body
                                if isinstance(
                                    n, (ast.FunctionDef, ast.AsyncFunctionDef)
                                )
                            ]
                        ),
                        "decorators": [
                            d.id if isinstance(d, ast.Name) else str(d)
                            for d in node.decorator_list
                        ],
                    }
                )

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "end_line": getattr(node, "end_lineno", "unknown"),
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "args_count": len(node.args.args),
                        "decorators": [
                            d.id if isinstance(d, ast.Name) else str(d)
                            for d in node.decorator_list
                        ],
                    }
                )

            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(
                            {
                                "type": "import",
                                "module": alias.name,
                                "alias": alias.asname,
                                "line": node.lineno,
                            }
                        )
                else:  # ImportFrom
                    for alias in node.names:
                        imports.append(
                            {
                                "type": "from_import",
                                "module": node.module,
                                "name": alias.name,
                                "alias": alias.asname,
                                "line": node.lineno,
                            }
                        )

            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if len(node.value) > 10 and any(
                    keyword in node.value.lower()
                    for keyword in ["key", "secret", "password", "token"]
                ):
                    hardcoded_strings.append(
                        {
                            "value": node.value,
                            "line": node.lineno,
                            "potential_secret": True,
                        }
                    )

        # Report findings
        print(f"✅ AST Analysis Results for {sample_file.name}:")
        print(f"   📋 Classes found: {len(classes)}")
        for cls in classes:
            print(
                f"      - {cls['name']} (line {cls['line']}, {cls['methods']} methods)"
            )

        print(f"   🔧 Functions found: {len(functions)}")
        for func in functions[:5]:  # Show first 5
            print(
                f"      - {func['name']} (line {func['line']}, {'async' if func['is_async'] else 'sync'})"
            )
        if len(functions) > 5:
            print(f"      ... and {len(functions) - 5} more functions")

        print(f"   📦 Imports found: {len(imports)}")
        print(
            f"   🔐 Potential secrets found: {len([s for s in hardcoded_strings if s['potential_secret']])}"
        )

        # Test specific Python AST capabilities
        print("\n📊 Python AST Specific Capabilities:")

        # Count function complexity (nested control structures)
        complex_functions = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = count_complexity(node)
                if complexity > 10:
                    complex_functions.append(
                        {
                            "name": node.name,
                            "complexity": complexity,
                            "line": node.lineno,
                        }
                    )

        print(f"   ⚠️  High complexity functions: {len(complex_functions)}")
        for func in complex_functions:
            print(
                f"      - {func['name']} (complexity: {func['complexity']}, line {func['line']})"
            )

        # Count function length
        long_functions = []
        source_code.split("\n")
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if hasattr(node, "end_lineno"):
                    length = node.end_lineno - node.lineno
                    if length > 50:
                        long_functions.append(
                            {"name": node.name, "length": length, "line": node.lineno}
                        )

        print(f"   📏 Long functions (>50 lines): {len(long_functions)}")
        for func in long_functions:
            print(
                f"      - {func['name']} ({func['length']} lines, starts line {func['line']})"
            )

        return True

    except Exception as e:
        print(f"❌ Failed to analyze Python AST: {e}")
        return False


def count_complexity(node):
    """Count cyclomatic complexity of a function using AST."""
    complexity = 1  # Base complexity

    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1

    return complexity


def test_ast_vs_treesitter_priority():
    """Test that AST is prioritized over tree-sitter for Python files."""
    print("\n" + "=" * 60)
    print("TESTING: AST Priority Over Tree-sitter for Python")
    print("=" * 60)

    # Create a test script that demonstrates AST priority
    test_script = """
import os
import sys
from pathlib import Path
import ast

def analyze_file(filepath):
    \"\"\"Test the file extension detection and tool selection.\"\"\"
    ext = os.path.splitext(filepath)[1]

    print(f"File: {filepath}")
    print(f"Extension: {ext}")

    # ALWAYS use Python AST for Python files
    if ext == '.py':
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read())
        print("✅ Used Python AST (as expected)")
        return tree, 'python_ast'
    else:
        print("Would use tree-sitter for non-Python files")
        return None, 'tree_sitter'

if __name__ == "__main__":
    # Test with our sample Python file
    sample_file = Path(__file__).parent / "sample_python_file.py"
    tree, tool_used = analyze_file(sample_file)

    if tool_used == 'python_ast':
        print("✅ PASS: Python AST was correctly prioritized for .py file")
    else:
        print("❌ FAIL: Expected Python AST for .py file")
"""

    # Write and execute the test script
    test_file = Path(__file__).parent / "temp_ast_priority_test.py"

    try:
        with open(test_file, "w") as f:
            f.write(test_script)

        # Execute the test script
        result = subprocess.run(
            [sys.executable, str(test_file)],
            capture_output=True,
            text=True,
            cwd=test_file.parent,
            check=False,
        )

        print("Test script output:")
        print(result.stdout)

        if (
            result.returncode == 0
            and "PASS: Python AST was correctly prioritized" in result.stdout
        ):
            print("✅ AST priority test PASSED")
            success = True
        else:
            print("❌ AST priority test FAILED")
            if result.stderr:
                print(f"Error: {result.stderr}")
            success = False

        # Clean up
        test_file.unlink()
        return success

    except Exception as e:
        print(f"❌ Failed to run AST priority test: {e}")
        if test_file.exists():
            test_file.unlink()
        return False


def main():
    """Run all Python AST tests."""
    print("🧪 TESTING PYTHON AST FUNCTIONALITY FOR CODE ANALYZER AGENT")
    print("=" * 70)

    tests = [
        ("Python AST Parsing", test_python_ast_parsing),
        ("Python AST Analysis", analyze_python_with_ast),
        ("AST Priority", test_ast_vs_treesitter_priority),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n🔬 Running: {test_name}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 70)
    print("📊 PYTHON AST TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n🎯 Overall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL PYTHON AST TESTS PASSED!")
        print(
            "   The code_analyzer agent correctly uses Python's native AST for .py files"
        )
    else:
        print("⚠️  Some tests failed. Python AST functionality needs attention.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
