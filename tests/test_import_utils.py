"""Tests for import utilities."""

import logging
import sys
from pathlib import Path

# Add src to path to test absolute imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from claude_mpm.utils.imports import safe_import, safe_import_multiple


def test_safe_import_basic():
    """Test basic module import."""
    # Test importing a standard library module
    os_module = safe_import("os")
    assert os_module is not None
    assert hasattr(os_module, "path")
    print("✓ Basic module import works")


def test_safe_import_with_fallback():
    """Test import with fallback."""
    # Test with a non-existent primary, but valid fallback
    json_module = safe_import("nonexistent.module", "json")
    assert json_module is not None
    assert hasattr(json_module, "loads")
    print("✓ Fallback import works")


def test_safe_import_from_list():
    """Test importing specific items from a module."""
    # Import single function
    loads = safe_import("json", from_list=["loads"])
    assert loads is not None
    assert callable(loads)
    print("✓ Single function import works")

    # Import multiple functions
    loads, dumps = safe_import("json", from_list=["loads", "dumps"])
    assert loads is not None
    assert dumps is not None
    assert callable(loads) and callable(dumps)
    print("✓ Multiple function import works")


def test_safe_import_with_logger():
    """Test import with logging."""
    # Set up a simple logger
    logger = logging.getLogger("test")
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    # Test with logger
    module = safe_import("nonexistent.module", "sys", logger=logger)
    assert module is not None
    print("✓ Import with logging works")


def test_safe_import_multiple():
    """Test importing multiple modules at once."""
    imports = [
        ("os", None, ["path"]),  # Import os.path
        ("json", None, ["loads", "dumps"]),  # Import multiple from json
        {"primary": "sys", "as": "system"},  # Import with alias
    ]

    results = safe_import_multiple(imports)

    assert "path" in results
    assert "loads" in results
    assert "dumps" in results
    assert "system" in results
    assert hasattr(results["system"], "version")
    print("✓ Multiple imports work")


def test_real_world_pattern():
    """Test the real-world pattern from claude_mpm."""
    # Simulate the common pattern in claude_mpm
    # This would normally be relative imports in the actual code
    get_logger = safe_import("claude_mpm.utils.logger", from_list=["get_logger"])

    # Even if it fails, it should return None gracefully
    if get_logger is None:
        print("✓ Failed import returns None gracefully")
    else:
        print("✓ Real-world pattern import works")


def run_tests():
    """Run all tests."""
    print("Testing import utilities...")
    print("-" * 40)

    test_safe_import_basic()
    test_safe_import_with_fallback()
    test_safe_import_from_list()
    test_safe_import_with_logger()
    test_safe_import_multiple()
    test_real_world_pattern()

    print("-" * 40)
    print("All tests passed! ✅")


if __name__ == "__main__":
    run_tests()
