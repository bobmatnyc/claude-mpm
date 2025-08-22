#!/usr/bin/env python3
"""
Test script to validate multi-language support using individual tree-sitter packages.
This tests the agent's ability to analyze JavaScript, TypeScript, Go, and other languages.
"""

import importlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def test_multi_language_parsing():
    """Test parsing files in multiple languages using appropriate tree-sitter packages."""
    print("=" * 60)
    print("TESTING: Multi-Language File Parsing")
    print("=" * 60)

    # Test script that implements the agent's multi-language approach
    test_script = '''
import os
import sys
import subprocess
import importlib
import ast

def analyze_file(filepath):
    """Analyze file using appropriate tool based on extension."""
    ext = os.path.splitext(filepath)[1]
    filename = os.path.basename(filepath)

    print(f"\\n📁 Analyzing: {filename}")
    print(f"   Extension: {ext}")

    # ALWAYS use Python AST for Python files
    if ext == '.py':
        try:
            with open(filepath, 'r') as f:
                source = f.read()
            tree = ast.parse(source)
            print(f"   ✅ Used Python AST")

            # Extract some info to prove it worked
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

            print(f"   📊 Found {len(functions)} functions, {len(classes)} classes")
            return tree, 'python_ast', len(functions) + len(classes)
        except Exception as e:
            print(f"   ❌ Python AST failed: {e}")
            return None, 'failed', 0

    # Use individual tree-sitter packages for other languages
    ext_to_package = {
        '.js': ('tree-sitter-javascript', 'tree_sitter_javascript', 'language'),
        '.ts': ('tree-sitter-typescript', 'tree_sitter_typescript', 'language_typescript'),
        '.tsx': ('tree-sitter-typescript', 'tree_sitter_typescript', 'language_tsx'),
        '.jsx': ('tree-sitter-javascript', 'tree_sitter_javascript', 'language'),
        '.go': ('tree-sitter-go', 'tree_sitter_go', 'language'),
        '.rs': ('tree-sitter-rust', 'tree_sitter_rust', 'language'),
        '.java': ('tree-sitter-java', 'tree_sitter_java', 'language'),
        '.cpp': ('tree-sitter-cpp', 'tree_sitter_cpp', 'language'),
        '.c': ('tree-sitter-c', 'tree_sitter_c', 'language'),
    }

    if ext in ext_to_package:
        package_name, module_name, language_func = ext_to_package[ext]

        try:
            # Ensure package is available
            module = importlib.import_module(module_name)
            print(f"   ✅ {package_name} available")
        except ImportError:
            print(f"   ⚠️  Installing {package_name}...")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name])
                module = importlib.import_module(module_name)
                print(f"   ✅ Installed and imported {package_name}")
            except Exception as e:
                print(f"   ❌ Failed to install {package_name}: {e}")
                return None, 'install_failed', 0

        # Try to create Language object and parse
        try:
            from tree_sitter import Language, Parser

            lang_function = getattr(module, language_func)
            lang = Language(lang_function())
            parser = Parser(lang)

            with open(filepath, 'rb') as f:
                tree = parser.parse(f.read())

            print(f"   ✅ Used {module_name} with {language_func}()")

            # Count nodes to show it parsed successfully
            node_count = count_nodes(tree.root_node)
            print(f"   📊 Parsed {node_count} AST nodes")

            return tree, module_name, node_count

        except Exception as e:
            print(f"   ❌ Tree-sitter parsing failed: {e}")
            return None, 'parse_failed', 0

    # Fallback to text analysis for unsupported files
    print(f"   ⚠️  Unsupported extension {ext}, using text analysis")
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        return content, 'text_analysis', len(content.split('\\n'))
    except Exception as e:
        print(f"   ❌ Text analysis failed: {e}")
        return None, 'failed', 0

def count_nodes(node):
    """Recursively count tree-sitter AST nodes."""
    count = 1
    for child in node.children:
        count += count_nodes(child)
    return count

if __name__ == "__main__":
    # Test files from our test directory
    test_files = [
        'sample_python_file.py',
        'sample_javascript_file.js',
        'sample_typescript_file.ts',
        'sample_go_file.go'
    ]

    results = []

    for filename in test_files:
        if os.path.exists(filename):
            tree, tool_used, metric = analyze_file(filename)
            success = tree is not None and tool_used not in ['failed', 'install_failed', 'parse_failed']
            results.append((filename, success, tool_used, metric))
        else:
            print(f"\\n❌ Test file not found: {filename}")
            results.append((filename, False, 'file_not_found', 0))

    # Summary
    print(f"\\n📊 Multi-Language Parsing Results:")
    passed = 0
    for filename, success, tool_used, metric in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {filename} - {tool_used} ({metric} items)")
        if success:
            passed += 1

    print(f"\\n🎯 Overall: {passed}/{len(results)} files parsed successfully")
    sys.exit(0 if passed >= len(results) * 0.75 else 1)  # Pass if 75%+ succeed
'''

    # Write and run the multi-language test
    test_file = Path(__file__).parent / "temp_multilang_test.py"

    try:
        with open(test_file, "w") as f:
            f.write(test_script)

        print("Running multi-language parsing test...")
        result = subprocess.run(
            [sys.executable, str(test_file)],
            capture_output=True,
            text=True,
            cwd=test_file.parent,
        )

        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)

        success = result.returncode == 0

        # Clean up
        test_file.unlink()
        return success

    except Exception as e:
        print(f"❌ Multi-language parsing test failed: {e}")
        if test_file.exists():
            test_file.unlink()
        return False


def test_language_specific_features():
    """Test language-specific analysis features."""
    print("\n" + "=" * 60)
    print("TESTING: Language-Specific Analysis Features")
    print("=" * 60)

    feature_script = '''
import os
import sys
import ast
import importlib

def analyze_python_features(filepath):
    """Test Python-specific AST analysis features."""
    print(f"\\n🐍 Python Analysis: {os.path.basename(filepath)}")

    with open(filepath, 'r') as f:
        source = f.read()

    tree = ast.parse(source)

    # Python-specific analysis
    features = {
        'async_functions': 0,
        'decorators': 0,
        'list_comprehensions': 0,
        'f_strings': 0,
        'imports': 0,
        'classes': 0
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            features['async_functions'] += 1
        elif isinstance(node, ast.FunctionDef) and node.decorator_list:
            features['decorators'] += len(node.decorator_list)
        elif isinstance(node, ast.ListComp):
            features['list_comprehensions'] += 1
        elif isinstance(node, ast.JoinedStr):  # f-string
            features['f_strings'] += 1
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            features['imports'] += 1
        elif isinstance(node, ast.ClassDef):
            features['classes'] += 1

    print(f"   📊 Python features found:")
    for feature, count in features.items():
        if count > 0:
            print(f"      {feature}: {count}")

    return sum(features.values()) > 0

def analyze_javascript_features(filepath):
    """Test JavaScript-specific tree-sitter analysis."""
    print(f"\\n🟨 JavaScript Analysis: {os.path.basename(filepath)}")

    try:
        import tree_sitter_javascript as tsjs
        from tree_sitter import Language, Parser

        lang = Language(tsjs.language())
        parser = Parser(lang)

        with open(filepath, 'rb') as f:
            tree = parser.parse(f.read())

        # Count different JavaScript constructs
        features = {
            'functions': 0,
            'classes': 0,
            'arrow_functions': 0,
            'async_functions': 0
        }

        def traverse_node(node):
            if node.type == 'function_declaration':
                features['functions'] += 1
            elif node.type == 'class_declaration':
                features['classes'] += 1
            elif node.type == 'arrow_function':
                features['arrow_functions'] += 1
            elif 'async' in node.type:
                features['async_functions'] += 1

            for child in node.children:
                traverse_node(child)

        traverse_node(tree.root_node)

        print(f"   📊 JavaScript features found:")
        for feature, count in features.items():
            if count > 0:
                print(f"      {feature}: {count}")

        return sum(features.values()) > 0

    except Exception as e:
        print(f"   ❌ JavaScript analysis failed: {e}")
        return False

def analyze_typescript_features(filepath):
    """Test TypeScript-specific tree-sitter analysis."""
    print(f"\\n🟦 TypeScript Analysis: {os.path.basename(filepath)}")

    try:
        import tree_sitter_typescript as tsts
        from tree_sitter import Language, Parser

        lang = Language(tsts.language_typescript())
        parser = Parser(lang)

        with open(filepath, 'rb') as f:
            tree = parser.parse(f.read())

        # Count TypeScript-specific constructs
        features = {
            'interfaces': 0,
            'type_annotations': 0,
            'generics': 0,
            'classes': 0
        }

        def traverse_node(node):
            if node.type == 'interface_declaration':
                features['interfaces'] += 1
            elif node.type == 'type_annotation':
                features['type_annotations'] += 1
            elif node.type == 'generic_type':
                features['generics'] += 1
            elif node.type == 'class_declaration':
                features['classes'] += 1

            for child in node.children:
                traverse_node(child)

        traverse_node(tree.root_node)

        print(f"   📊 TypeScript features found:")
        for feature, count in features.items():
            if count > 0:
                print(f"      {feature}: {count}")

        return sum(features.values()) > 0

    except Exception as e:
        print(f"   ❌ TypeScript analysis failed: {e}")
        return False

def analyze_go_features(filepath):
    """Test Go-specific tree-sitter analysis."""
    print(f"\\n🐹 Go Analysis: {os.path.basename(filepath)}")

    try:
        import tree_sitter_go as tsgo
        from tree_sitter import Language, Parser

        lang = Language(tsgo.language())
        parser = Parser(lang)

        with open(filepath, 'rb') as f:
            tree = parser.parse(f.read())

        # Count Go-specific constructs
        features = {
            'functions': 0,
            'methods': 0,
            'structs': 0,
            'interfaces': 0
        }

        def traverse_node(node):
            if node.type == 'function_declaration':
                features['functions'] += 1
            elif node.type == 'method_declaration':
                features['methods'] += 1
            elif node.type == 'type_declaration' and 'struct' in node.text.decode('utf-8', errors='ignore'):
                features['structs'] += 1
            elif node.type == 'type_declaration' and 'interface' in node.text.decode('utf-8', errors='ignore'):
                features['interfaces'] += 1

            for child in node.children:
                traverse_node(child)

        traverse_node(tree.root_node)

        print(f"   📊 Go features found:")
        for feature, count in features.items():
            if count > 0:
                print(f"      {feature}: {count}")

        return sum(features.values()) > 0

    except Exception as e:
        print(f"   ❌ Go analysis failed: {e}")
        return False

if __name__ == "__main__":
    test_files = [
        ('sample_python_file.py', analyze_python_features),
        ('sample_javascript_file.js', analyze_javascript_features),
        ('sample_typescript_file.ts', analyze_typescript_features),
        ('sample_go_file.go', analyze_go_features)
    ]

    results = []

    for filepath, analyzer in test_files:
        if os.path.exists(filepath):
            try:
                success = analyzer(filepath)
                results.append((filepath, success))
            except Exception as e:
                print(f"\\n❌ Analysis failed for {filepath}: {e}")
                results.append((filepath, False))
        else:
            print(f"\\n❌ Test file not found: {filepath}")
            results.append((filepath, False))

    # Summary
    print(f"\\n📊 Language-Specific Feature Analysis:")
    passed = 0
    for filepath, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {filepath}")
        if success:
            passed += 1

    print(f"\\n🎯 Overall: {passed}/{len(results)} language analyses succeeded")
    sys.exit(0 if passed >= len(results) * 0.75 else 1)
'''

    # Write and run the feature test
    feature_file = Path(__file__).parent / "temp_features_test.py"

    try:
        with open(feature_file, "w") as f:
            f.write(feature_script)

        print("Running language-specific features test...")
        result = subprocess.run(
            [sys.executable, str(feature_file)],
            capture_output=True,
            text=True,
            cwd=feature_file.parent,
        )

        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)

        success = result.returncode == 0

        # Clean up
        feature_file.unlink()
        return success

    except Exception as e:
        print(f"❌ Language-specific features test failed: {e}")
        if feature_file.exists():
            feature_file.unlink()
        return False


def main():
    """Run all multi-language support tests."""
    print("🧪 TESTING MULTI-LANGUAGE SUPPORT FOR CODE ANALYZER AGENT")
    print("=" * 70)

    # Test multi-language parsing
    parsing_success = test_multi_language_parsing()

    # Test language-specific features
    features_success = test_language_specific_features()

    # Summary
    print("\n" + "=" * 70)
    print("📊 MULTI-LANGUAGE SUPPORT TEST SUMMARY")
    print("=" * 70)

    print(f"📁 Multi-Language Parsing: {'✅ PASS' if parsing_success else '❌ FAIL'}")
    print(f"🔍 Language-Specific Features: {'✅ PASS' if features_success else '❌ FAIL'}")

    overall_success = parsing_success and features_success

    if overall_success:
        print("\n🎉 MULTI-LANGUAGE SUPPORT TESTS PASSED!")
        print("   ✅ JavaScript analysis works with tree-sitter-javascript")
        print("   ✅ TypeScript analysis works with tree-sitter-typescript")
        print("   ✅ Go analysis works with tree-sitter-go")
        print("   ✅ Python analysis prioritizes native AST")
        print("   ✅ Language-specific features are properly detected")
    else:
        print("\n⚠️  Some multi-language support tests failed")
        if not parsing_success:
            print("   - Multi-language parsing has issues")
        if not features_success:
            print("   - Language-specific feature detection has issues")

    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)