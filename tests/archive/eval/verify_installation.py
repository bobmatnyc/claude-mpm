"""
Verify DeepEval framework installation.

Run this script to check if all components are properly installed.

Usage:
    python tests/eval/verify_installation.py
"""

import sys
from pathlib import Path


def check_file_exists(file_path: Path, description: str) -> bool:
    """Check if a file exists and report."""
    exists = file_path.exists()
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {file_path.name}")
    return exists


def check_json_valid(file_path: Path, description: str) -> bool:
    """Check if JSON file is valid."""
    try:
        import json

        with open(file_path) as f:
            data = json.load(f)
        print(f"✅ {description}: {len(data.get('scenarios', []))} scenarios")
        return True
    except Exception as e:
        print(f"❌ {description}: Invalid JSON - {e}")
        return False


def check_python_import(module_path: str, description: str) -> bool:
    """Check if Python module can be imported."""
    try:
        __import__(module_path)
        print(f"✅ {description}: Imports successfully")
        return True
    except ImportError as e:
        print(f"❌ {description}: Import failed - {e}")
        return False
    except Exception as e:
        print(f"⚠️  {description}: Import error - {e}")
        return False


def main():
    """Run installation verification checks."""
    print("=" * 60)
    print("DeepEval Framework Installation Verification")
    print("=" * 60)

    eval_dir = Path(__file__).parent
    all_checks_passed = True

    print("\n📁 Directory Structure:")
    checks = [
        (eval_dir / "__init__.py", "Package init"),
        (eval_dir / "conftest.py", "Pytest fixtures"),
        (eval_dir / "README.md", "Documentation"),
        (eval_dir / "test_cases" / "__init__.py", "Test cases package"),
        (eval_dir / "test_cases" / "ticketing_delegation.py", "Ticketing tests"),
        (eval_dir / "test_cases" / "circuit_breakers.py", "Circuit breaker tests"),
        (eval_dir / "metrics" / "__init__.py", "Metrics package"),
        (eval_dir / "metrics" / "instruction_faithfulness.py", "Instruction metric"),
        (eval_dir / "metrics" / "delegation_correctness.py", "Delegation metric"),
        (eval_dir / "scenarios" / "__init__.py", "Scenarios package"),
        (eval_dir / "scenarios" / "ticketing_scenarios.json", "Ticketing scenarios"),
        (
            eval_dir / "scenarios" / "circuit_breaker_scenarios.json",
            "Circuit breaker scenarios",
        ),
        (eval_dir / "utils" / "__init__.py", "Utils package"),
        (eval_dir / "utils" / "pm_response_parser.py", "PM parser"),
    ]

    for file_path, description in checks:
        if not check_file_exists(file_path, description):
            all_checks_passed = False

    print("\n📄 JSON Scenario Files:")
    json_checks = [
        (eval_dir / "scenarios" / "ticketing_scenarios.json", "Ticketing scenarios"),
        (
            eval_dir / "scenarios" / "circuit_breaker_scenarios.json",
            "Circuit breaker scenarios",
        ),
    ]

    for file_path, description in json_checks:
        if not check_json_valid(file_path, description):
            all_checks_passed = False

    print("\n🐍 Python Module Imports:")
    import_checks = [
        ("tests.eval", "Package root"),
        ("tests.eval.utils.pm_response_parser", "PM parser"),
        ("tests.eval.conftest", "Pytest fixtures"),
    ]

    for module_path, description in import_checks:
        if not check_python_import(module_path, description):
            all_checks_passed = False

    print("\n📦 Dependencies Check:")
    dependencies = [
        ("deepeval", "DeepEval framework", True),
        ("pytest", "Pytest test runner", False),
        ("pytest_asyncio", "Async test support", True),
    ]

    for package, description, is_eval_only in dependencies:
        try:
            __import__(package)
            print(f"✅ {description}: Installed")
        except ImportError:
            if is_eval_only:
                print(
                    f"⚠️  {description}: Not installed (run: pip install -e '.[eval]')"
                )
                # Don't fail if eval dependencies not installed yet
            else:
                print(f"❌ {description}: Not installed")
                all_checks_passed = False

    print("\n" + "=" * 60)
    if all_checks_passed:
        print("✅ All core components verified successfully!")
        print("\nNext steps:")
        print("1. Install evaluation dependencies: pip install -e '.[eval]'")
        print("2. Run tests: pytest tests/eval/ -v")
        print("3. Read documentation: tests/eval/README.md")
    else:
        print("❌ Some checks failed. Please review errors above.")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
