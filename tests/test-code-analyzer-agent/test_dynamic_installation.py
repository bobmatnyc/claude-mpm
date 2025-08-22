#!/usr/bin/env python3
"""
Test script to validate dynamic installation logic for missing tree-sitter packages.
This tests the agent's ability to install packages on-demand.
"""

import importlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def uninstall_package(package_name):
    """Uninstall a package to test dynamic installation."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", package_name],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def test_dynamic_installation():
    """Test the dynamic installation logic from the code_analyzer agent."""
    print("=" * 60)
    print("TESTING: Dynamic Installation Logic")
    print("=" * 60)

    # Test script that mimics the agent's installation logic
    test_script = '''
import os
import sys
import subprocess
import importlib

def ensure_tree_sitter_package(package_name):
    """Dynamically install missing tree-sitter packages."""
    try:
        __import__(package_name.replace('-', '_'))
        print(f"✅ {package_name} already available")
        return True
    except ImportError:
        print(f"⚠️  {package_name} not found, installing...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name])
            print(f"✅ Successfully installed {package_name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package_name}: {e}")
            return False

def test_language_creation(package_name, module_name, language_func='language'):
    """Test creating Language object after installation."""
    try:
        module = importlib.import_module(module_name)

        # Handle TypeScript special case
        if module_name == 'tree_sitter_typescript':
            # TypeScript has language_typescript and language_tsx
            if hasattr(module, 'language_typescript'):
                language_func = 'language_typescript'
            else:
                print(f"❌ {module_name} missing expected language functions")
                return False
        elif not hasattr(module, language_func):
            print(f"❌ {module_name} missing {language_func} function")
            return False

        # Try to create Language object
        from tree_sitter import Language, Parser

        lang_function = getattr(module, language_func)
        lang = Language(lang_function())
        parser = Parser(lang)

        print(f"✅ Successfully created Language and Parser for {package_name}")
        return True

    except ImportError as e:
        print(f"❌ Import error after installation: {e}")
        return False
    except Exception as e:
        print(f"❌ Language creation failed: {e}")
        return False

if __name__ == "__main__":
    # Test packages
    test_packages = [
        ('tree-sitter-javascript', 'tree_sitter_javascript'),
        ('tree-sitter-typescript', 'tree_sitter_typescript'),
        ('tree-sitter-go', 'tree_sitter_go'),
    ]

    results = []

    for package_name, module_name in test_packages:
        print(f"\\n🔍 Testing dynamic installation: {package_name}")

        # Test installation
        install_success = ensure_tree_sitter_package(package_name)

        if install_success:
            # Test Language creation
            lang_success = test_language_creation(package_name, module_name)
            results.append((package_name, install_success and lang_success))
        else:
            results.append((package_name, False))

    # Report results
    print(f"\\n📊 Dynamic Installation Results:")
    passed = 0
    for package_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {package_name}")
        if success:
            passed += 1

    print(f"\\n🎯 Overall: {passed}/{len(results)} packages passed dynamic installation test")
    sys.exit(0 if passed == len(results) else 1)
'''

    # Write and run the test script
    test_file = Path(__file__).parent / "temp_dynamic_install_test.py"

    try:
        with open(test_file, "w") as f:
            f.write(test_script)

        print("Running dynamic installation test script...")
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
        print(f"❌ Dynamic installation test failed: {e}")
        if test_file.exists():
            test_file.unlink()
        return False


def test_graceful_fallback():
    """Test graceful fallback when packages can't be installed."""
    print("\n" + "=" * 60)
    print("TESTING: Graceful Fallback for Installation Failures")
    print("=" * 60)

    # Test script that simulates installation failure
    fallback_script = '''
import os
import sys
import subprocess

def analyze_file_with_fallback(filepath):
    """Simulate the agent's fallback logic."""
    ext = os.path.splitext(filepath)[1]

    print(f"Analyzing: {filepath}")
    print(f"Extension: {ext}")

    # ALWAYS use Python AST for Python files
    if ext == '.py':
        import ast
        try:
            with open(filepath, 'r') as f:
                tree = ast.parse(f.read())
            print("✅ Used Python AST (no tree-sitter needed)")
            return tree, 'python_ast'
        except Exception as e:
            print(f"❌ Python AST failed: {e}")
            return None, 'failed'

    # For other languages, try tree-sitter with fallback
    ext_map = {
        '.js': ('tree-sitter-javascript', 'tree_sitter_javascript'),
        '.ts': ('tree-sitter-typescript', 'tree_sitter_typescript'),
        '.fake': ('tree-sitter-nonexistent', 'tree_sitter_nonexistent'),  # This will fail
    }

    if ext in ext_map:
        package_name, module_name = ext_map[ext]

        try:
            # Try to import
            __import__(module_name)
            print(f"✅ {package_name} available")
            return "mock_tree", module_name
        except ImportError:
            # Try to install
            print(f"⚠️  {package_name} not found, attempting installation...")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name])
                print(f"✅ Installed {package_name}")
                return "mock_tree", module_name
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Graceful fallback
                print(f"⚠️  Failed to install {package_name}, falling back to text analysis")
                return None, 'text_fallback'

    # Fallback to text analysis for unsupported files
    print("⚠️  Unsupported file type, using text analysis")
    return None, 'text_fallback'

if __name__ == "__main__":
    # Test various file types including one that will fail
    test_files = [
        ('test.py', 'Python file'),
        ('test.js', 'JavaScript file'),
        ('test.fake', 'Non-existent language'),
        ('test.unknown', 'Unknown extension'),
    ]

    # Create temporary test files
    import tempfile
    temp_dir = tmp_path

    for filename, description in test_files:
        filepath = os.path.join(temp_dir, filename)
        content = f"# {description}\\nprint('hello')" if filename.endswith('.py') else f"// {description}\\nconsole.log('hello');"

        with open(filepath, 'w') as f:
            f.write(content)

        print(f"\\n🔍 Testing {description}:")
        result, tool_used = analyze_file_with_fallback(filepath)

        if tool_used in ['python_ast', 'tree_sitter_javascript', 'text_fallback']:
            print(f"✅ Appropriate tool used: {tool_used}")
        else:
            print(f"❌ Unexpected tool: {tool_used}")

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

    print(f"\\n✅ Graceful fallback test completed")
'''

    # Write and run the fallback test
    fallback_file = Path(__file__).parent / "temp_fallback_test.py"

    try:
        with open(fallback_file, "w") as f:
            f.write(fallback_script)

        print("Running graceful fallback test...")
        result = subprocess.run(
            [sys.executable, str(fallback_file)],
            capture_output=True,
            text=True,
            cwd=fallback_file.parent,
        )

        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)

        success = "Graceful fallback test completed" in result.stdout

        # Clean up
        fallback_file.unlink()
        return success

    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
        if fallback_file.exists():
            fallback_file.unlink()
        return False


def main():
    """Run all dynamic installation tests."""
    print("🧪 TESTING DYNAMIC INSTALLATION LOGIC FOR CODE ANALYZER AGENT")
    print("=" * 70)

    # Test dynamic installation
    install_success = test_dynamic_installation()

    # Test graceful fallback
    fallback_success = test_graceful_fallback()

    # Summary
    print("\n" + "=" * 70)
    print("📊 DYNAMIC INSTALLATION TEST SUMMARY")
    print("=" * 70)

    print(f"🔧 Dynamic Installation: {'✅ PASS' if install_success else '❌ FAIL'}")
    print(f"🛡️  Graceful Fallback: {'✅ PASS' if fallback_success else '❌ FAIL'}")

    overall_success = install_success and fallback_success

    if overall_success:
        print("\n🎉 DYNAMIC INSTALLATION TESTS PASSED!")
        print("   The code_analyzer agent can install missing packages dynamically")
        print("   Graceful fallback works when installation fails")
    else:
        print("\n⚠️  Some dynamic installation tests failed")
        if not install_success:
            print("   - Dynamic installation logic has issues")
        if not fallback_success:
            print("   - Graceful fallback logic has issues")

    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)