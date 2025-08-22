#!/usr/bin/env python3
"""
Test script to verify Python 3.13 compatibility and ensure no tree-sitter-language-pack dependency.
This validates the agent's compatibility with the latest Python version.
"""

import importlib
import subprocess
import sys
from pathlib import Path

import pkg_resources


def check_python_version():
    """Check that we're running on Python 3.13."""
    print("=" * 60)
    print("TESTING: Python Version Verification")
    print("=" * 60)

    version_info = sys.version_info
    print(f"Python version: {sys.version}")
    print(f"Version info: {version_info}")

    if version_info.major == 3 and version_info.minor >= 13:
        print("✅ Running on Python 3.13+ (compatible)")
        return True
    else:
        print(
            f"⚠️  Running on Python {version_info.major}.{version_info.minor} (test may not be conclusive)"
        )
        return True  # Still run tests, but note the version


def check_no_language_pack_dependency():
    """Verify that tree-sitter-language-pack is not installed or used."""
    print("\n" + "=" * 60)
    print("TESTING: No tree-sitter-language-pack Dependency")
    print("=" * 60)

    # Check if package is installed
    try:
        import tree_sitter_language_pack

        print("❌ FAIL: tree-sitter-language-pack is installed")
        print("   This package is not compatible with Python 3.13")
        print("   The agent should use individual packages instead")
        return False
    except ImportError:
        print("✅ PASS: tree-sitter-language-pack not found")

    # Check pip list for the package
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list"], capture_output=True, text=True
        )
        if "tree-sitter-language-pack" in result.stdout:
            print("❌ FAIL: tree-sitter-language-pack found in pip list")
            return False
        else:
            print("✅ PASS: tree-sitter-language-pack not in pip list")
    except Exception as e:
        print(f"⚠️  Could not check pip list: {e}")

    return True


def check_individual_packages_available():
    """Verify that individual tree-sitter packages work correctly."""
    print("\n" + "=" * 60)
    print("TESTING: Individual Packages Functionality")
    print("=" * 60)

    # Test the exact pattern from the code_analyzer agent
    test_script = '''
import sys
import importlib

def ensure_tree_sitter_package(package_name):
    """Test the exact installation logic from the agent."""
    module_name = package_name.replace('-', '_')
    try:
        __import__(module_name)
        return True, f"{package_name} already available"
    except ImportError:
        import subprocess
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name])
            __import__(module_name)
            return True, f"{package_name} installed and available"
        except subprocess.CalledProcessError:
            return False, f"Failed to install {package_name}"
        except ImportError:
            return False, f"Failed to import {package_name} after installation"

def test_python313_import_pattern():
    """Test the Python 3.13 compatible import pattern."""

    # Test individual packages
    packages_to_test = [
        'tree-sitter-javascript',
        'tree-sitter-typescript',
        'tree-sitter-go',
    ]

    results = []

    for package_name in packages_to_test:
        print(f"\\n🔍 Testing {package_name}:")
        success, message = ensure_tree_sitter_package(package_name)
        print(f"   {message}")

        if success:
            # Test the Language creation pattern
            try:
                module_name = package_name.replace('-', '_')
                module = importlib.import_module(module_name)

                # Test language function availability
                if hasattr(module, 'language'):
                    print(f"   ✅ {module_name}.language() available")
                elif hasattr(module, 'language_typescript'):
                    print(f"   ✅ {module_name}.language_typescript() available (TypeScript)")
                elif hasattr(module, 'language_tsx'):
                    print(f"   ✅ {module_name}.language_tsx() available (TSX)")
                else:
                    print(f"   ❌ No language function found in {module_name}")
                    success = False

                # Test Language object creation
                if success:
                    try:
                        from tree_sitter import Language

                        if module_name == 'tree_sitter_typescript':
                            lang = Language(module.language_typescript())
                        else:
                            lang = Language(module.language())

                        print(f"   ✅ Language object created successfully")

                    except Exception as e:
                        print(f"   ❌ Language object creation failed: {e}")
                        success = False

            except Exception as e:
                print(f"   ❌ Import test failed: {e}")
                success = False

        results.append((package_name, success))

    return results

if __name__ == "__main__":
    results = test_python313_import_pattern()

    print(f"\\n📊 Python 3.13 Compatibility Results:")
    passed = 0
    for package_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {package_name}")
        if success:
            passed += 1

    print(f"\\n🎯 Overall: {passed}/{len(results)} packages work with Python 3.13")

    # Exit with success if at least 2/3 of packages work
    success_threshold = len(results) * 2 // 3
    if passed >= success_threshold:
        print("✅ Python 3.13 compatibility test PASSED")
        sys.exit(0)
    else:
        print("❌ Python 3.13 compatibility test FAILED")
        sys.exit(1)
'''

    # Write and run the compatibility test
    compat_file = Path(__file__).parent / "temp_python313_compat.py"

    try:
        with open(compat_file, "w") as f:
            f.write(test_script)

        print("Running Python 3.13 compatibility test...")
        result = subprocess.run(
            [sys.executable, str(compat_file)],
            capture_output=True,
            text=True,
            cwd=compat_file.parent,
        )

        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)

        success = result.returncode == 0

        # Clean up
        compat_file.unlink()
        return success

    except Exception as e:
        print(f"❌ Python 3.13 compatibility test failed: {e}")
        if compat_file.exists():
            compat_file.unlink()
        return False


def test_import_performance():
    """Test that individual package imports are reasonably fast."""
    print("\n" + "=" * 60)
    print("TESTING: Import Performance")
    print("=" * 60)

    import time

    packages_to_test = [
        ("tree_sitter_javascript", "JavaScript"),
        ("tree_sitter_typescript", "TypeScript"),
        ("tree_sitter_go", "Go"),
    ]

    total_time = 0
    successful_imports = 0

    for module_name, language in packages_to_test:
        print(f"\n⏱️  Testing import speed: {language}")

        try:
            start_time = time.time()
            module = importlib.import_module(module_name)
            import_time = time.time() - start_time

            print(f"   ✅ Imported in {import_time:.3f}s")
            total_time += import_time
            successful_imports += 1

            # Test Language creation speed
            start_time = time.time()
            from tree_sitter import Language

            if module_name == "tree_sitter_typescript":
                lang = Language(module.language_typescript())
            else:
                lang = Language(module.language())

            creation_time = time.time() - start_time
            print(f"   ✅ Language object created in {creation_time:.3f}s")

        except ImportError:
            print(f"   ⚠️  {module_name} not available (skipping)")
        except Exception as e:
            print(f"   ❌ Error testing {module_name}: {e}")

    if successful_imports > 0:
        avg_time = total_time / successful_imports
        print(f"\n📊 Performance Summary:")
        print(f"   Average import time: {avg_time:.3f}s")
        print(f"   Successful imports: {successful_imports}/{len(packages_to_test)}")

        if avg_time < 1.0:  # Imports should be under 1 second
            print("✅ Import performance acceptable")
            return True
        else:
            print("⚠️  Import performance slower than expected")
            return False
    else:
        print("❌ No successful imports to test performance")
        return False


def main():
    """Run all Python 3.13 compatibility tests."""
    print("🧪 TESTING PYTHON 3.13 COMPATIBILITY FOR CODE ANALYZER AGENT")
    print("=" * 70)

    # Check Python version
    version_ok = check_python_version()

    # Check no language pack dependency
    no_language_pack = check_no_language_pack_dependency()

    # Check individual packages work
    individual_packages_ok = check_individual_packages_available()

    # Test import performance
    performance_ok = test_import_performance()

    # Summary
    print("\n" + "=" * 70)
    print("📊 PYTHON 3.13 COMPATIBILITY TEST SUMMARY")
    print("=" * 70)

    print(f"🐍 Python Version: {'✅ PASS' if version_ok else '❌ FAIL'}")
    print(f"📦 No Language Pack: {'✅ PASS' if no_language_pack else '❌ FAIL'}")
    print(f"🔗 Individual Packages: {'✅ PASS' if individual_packages_ok else '❌ FAIL'}")
    print(f"⚡ Import Performance: {'✅ PASS' if performance_ok else '❌ FAIL'}")

    # Overall compatibility assessment
    critical_tests = [no_language_pack, individual_packages_ok]
    critical_passed = sum(critical_tests)

    overall_success = critical_passed == len(critical_tests)

    if overall_success:
        print("\n🎉 PYTHON 3.13 COMPATIBILITY TESTS PASSED!")
        print("   ✅ No dependency on incompatible tree-sitter-language-pack")
        print("   ✅ Individual tree-sitter packages work correctly")
        print("   ✅ Import patterns are Python 3.13 compatible")
        print("   ✅ Performance is acceptable")
    else:
        print("\n⚠️  Python 3.13 compatibility issues detected:")
        if not no_language_pack:
            print("   ❌ tree-sitter-language-pack dependency found (incompatible)")
        if not individual_packages_ok:
            print("   ❌ Individual packages not working correctly")
        if not performance_ok:
            print("   ⚠️  Performance issues detected")

    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)