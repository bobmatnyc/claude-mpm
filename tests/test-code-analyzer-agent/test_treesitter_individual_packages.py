#!/usr/bin/env python3
"""
Test script to validate individual tree-sitter package imports and Language object creation.
This tests the Python 3.13 compatible import pattern using individual packages.
"""

import importlib
import subprocess
import sys
from pathlib import Path


def check_package_installed(package_name):
    """Check if a package is installed."""
    try:
        module_name = package_name.replace("-", "_")
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def install_package(package_name):
    """Install a package using pip."""
    try:
        print(f"   Installing {package_name}...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"   Failed to install {package_name}: {e}")
        return False


def test_individual_package_imports():
    """Test the new import pattern for individual tree-sitter packages."""
    print("=" * 60)
    print("TESTING: Individual Tree-sitter Package Imports")
    print("=" * 60)

    # List of individual packages to test
    packages_to_test = [
        ("tree-sitter-javascript", "tree_sitter_javascript"),
        ("tree-sitter-typescript", "tree_sitter_typescript"),
        ("tree-sitter-go", "tree_sitter_go"),
        ("tree-sitter-rust", "tree_sitter_rust"),
        ("tree-sitter-java", "tree_sitter_java"),
        ("tree-sitter-c", "tree_sitter_c"),
        ("tree-sitter-cpp", "tree_sitter_cpp"),
    ]

    results = []

    for package_name, module_name in packages_to_test:
        print(f"\n🔍 Testing {package_name}:")

        # Check if package is installed
        if not check_package_installed(package_name):
            print(f"   ⚠️  {package_name} not installed")

            # Try to install it
            if install_package(package_name):
                print(f"   ✅ Successfully installed {package_name}")
            else:
                print(f"   ❌ Failed to install {package_name}")
                results.append((package_name, False, "Installation failed"))
                continue
        else:
            print(f"   ✅ {package_name} already installed")

        # Test the Python 3.13 compatible import pattern
        try:
            # This is the new import pattern from the agent
            module = importlib.import_module(module_name)
            print(f"   ✅ Successfully imported {module_name}")

            # Test if it has the language() function
            if hasattr(module, "language"):
                print(f"   ✅ {module_name}.language() function found")

                # Test creating Language object
                try:
                    # This requires tree-sitter core to be installed
                    from tree_sitter import Language

                    Language(module.language())
                    print("   ✅ Successfully created Language object")
                    results.append((package_name, True, "All tests passed"))
                except ImportError:
                    print(
                        "   ⚠️  tree-sitter core not available, but module import works"
                    )
                    results.append((package_name, True, "Import works, core missing"))
                except Exception as e:
                    print(f"   ❌ Failed to create Language object: {e}")
                    results.append(
                        (package_name, False, f"Language creation failed: {e}")
                    )
            else:
                print(f"   ❌ {module_name}.language() function not found")
                results.append((package_name, False, "No language() function"))

        except ImportError as e:
            print(f"   ❌ Failed to import {module_name}: {e}")
            results.append((package_name, False, f"Import failed: {e}"))
        except Exception as e:
            print(f"   ❌ Unexpected error with {module_name}: {e}")
            results.append((package_name, False, f"Unexpected error: {e}"))

    return results


def test_language_object_creation():
    """Test Language object creation with available packages."""
    print("\n" + "=" * 60)
    print("TESTING: Language Object Creation")
    print("=" * 60)

    # Check if tree-sitter core is available
    try:
        from tree_sitter import Language, Parser

        print("✅ tree-sitter core is available")
    except ImportError:
        print("⚠️  tree-sitter core not available, installing...")
        if install_package("tree-sitter"):
            try:
                from tree_sitter import Language, Parser

                print("✅ tree-sitter core installed and imported")
            except ImportError:
                print("❌ tree-sitter core installation failed")
                return []
        else:
            print("❌ Failed to install tree-sitter core")
            return []

    # Test Language creation for available packages
    test_cases = [
        ("tree_sitter_javascript", ".js"),
        ("tree_sitter_typescript", ".ts"),
        ("tree_sitter_go", ".go"),
        ("tree_sitter_rust", ".rs"),
    ]

    results = []

    for module_name, file_ext in test_cases:
        print(f"\n🔍 Testing Language object for {module_name}:")

        try:
            module = importlib.import_module(module_name)
            lang = Language(module.language())
            Parser(lang)

            print(f"   ✅ Created Language and Parser for {file_ext} files")
            results.append((module_name, True, "Language object created successfully"))

        except ImportError:
            print(f"   ⚠️  {module_name} not available (skipping)")
            results.append((module_name, False, "Module not available"))
        except Exception as e:
            print(f"   ❌ Failed to create Language object: {e}")
            results.append((module_name, False, f"Language creation failed: {e}"))

    return results


def test_python313_compatibility():
    """Test Python 3.13 compatibility requirements."""
    print("\n" + "=" * 60)
    print("TESTING: Python 3.13 Compatibility")
    print("=" * 60)

    print(f"Python version: {sys.version}")

    # Test 1: Ensure we're NOT using tree-sitter-language-pack
    print("\n🔍 Checking for tree-sitter-language-pack dependency:")
    try:
        import tree_sitter_language_pack

        print("❌ FAIL: tree-sitter-language-pack is installed (should not be used)")
        return False
    except ImportError:
        print("✅ PASS: tree-sitter-language-pack not found (as expected)")

    # Test 2: Verify individual packages work
    print("\n🔍 Testing individual package pattern:")

    test_script = '''
import sys
import importlib

def test_individual_imports():
    """Test the exact import pattern from the agent."""
    # This mimics the code_analyzer agent pattern
    ext_to_package = {
        '.js': ('tree-sitter-javascript', 'tree_sitter_javascript'),
        '.ts': ('tree-sitter-typescript', 'tree_sitter_typescript'),
        '.go': ('tree-sitter-go', 'tree_sitter_go'),
        '.rs': ('tree-sitter-rust', 'tree_sitter_rust'),
    }

    working_packages = []

    for ext, (package_name, module_name) in ext_to_package.items():
        try:
            # Python 3.13 compatible import pattern
            module = importlib.import_module(module_name)
            if hasattr(module, 'language'):
                working_packages.append((ext, module_name))
                print(f"✅ {ext}: {module_name} works")
            else:
                print(f"❌ {ext}: {module_name} missing language() function")
        except ImportError:
            print(f"⚠️  {ext}: {module_name} not available")

    return len(working_packages) > 0

if __name__ == "__main__":
    success = test_individual_imports()
    sys.exit(0 if success else 1)
'''

    # Write and run the test
    test_file = Path(__file__).parent / "temp_python313_test.py"

    try:
        with test_file.open("w") as f:
            f.write(test_script)

        result = subprocess.run(
            [sys.executable, str(test_file)],
            capture_output=True,
            text=True,
            cwd=test_file.parent,
            check=False,
        )

        print("Individual package test output:")
        print(result.stdout)

        success = result.returncode == 0

        if success:
            print("✅ PASS: Individual packages pattern works")
        else:
            print("❌ FAIL: Individual packages pattern failed")
            if result.stderr:
                print(f"Error: {result.stderr}")

        # Clean up
        test_file.unlink()
        return success

    except Exception as e:
        print(f"❌ Python 3.13 compatibility test failed: {e}")
        if test_file.exists():
            test_file.unlink()
        return False


def main():
    """Run all tree-sitter individual package tests."""
    print("🧪 TESTING INDIVIDUAL TREE-SITTER PACKAGES FOR CODE ANALYZER AGENT")
    print("=" * 70)

    # Test individual package imports
    import_results = test_individual_package_imports()

    # Test Language object creation
    language_results = test_language_object_creation()

    # Test Python 3.13 compatibility
    python313_compat = test_python313_compatibility()

    # Summary
    print("\n" + "=" * 70)
    print("📊 TREE-SITTER INDIVIDUAL PACKAGES TEST SUMMARY")
    print("=" * 70)

    print("\n📦 Individual Package Import Results:")
    successful_imports = 0
    for package_name, success, message in import_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {package_name} - {message}")
        if success:
            successful_imports += 1

    print("\n🔗 Language Object Creation Results:")
    successful_languages = 0
    for module_name, success, message in language_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {module_name} - {message}")
        if success:
            successful_languages += 1

    print("\n🐍 Python 3.13 Compatibility:")
    status = "✅ PASS" if python313_compat else "❌ FAIL"
    print(f"{status}: Python 3.13 compatibility requirements")

    # Overall assessment
    print("\n🎯 Overall Results:")
    print(
        f"   📦 Package imports: {successful_imports}/{len(import_results)} successful"
    )
    print(
        f"   🔗 Language objects: {successful_languages}/{len(language_results)} successful"
    )
    print(f"   🐍 Python 3.13 compat: {'✅' if python313_compat else '❌'}")

    overall_success = (
        successful_imports > 0
        and python313_compat  # At least some packages work  # Python 3.13 compatibility is essential
    )

    if overall_success:
        print("\n🎉 TREE-SITTER INDIVIDUAL PACKAGES TESTS PASSED!")
        print("   The code_analyzer agent can use individual tree-sitter packages")
        print("   Python 3.13 compatibility requirements are met")
    else:
        print("\n⚠️  Some tree-sitter tests failed:")
        if not python313_compat:
            print("   - Python 3.13 compatibility issues detected")
        if successful_imports == 0:
            print("   - No individual packages could be imported")

    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
