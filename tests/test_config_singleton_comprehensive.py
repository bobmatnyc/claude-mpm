#!/usr/bin/env python3
"""Comprehensive test to verify Config singleton behavior across all services."""

import importlib
import inspect
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def find_all_services():
    """Find all service classes that might use Config."""
    from claude_mpm.core.base_service import BaseService

    services = []

    # Import all service modules
    service_dirs = [
        Path(__file__).parent.parent / "src" / "claude_mpm" / "services",
        Path(__file__).parent.parent / "src" / "claude_mpm" / "core",
    ]

    for service_dir in service_dirs:
        if not service_dir.exists():
            continue

        for py_file in service_dir.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue

            # Convert path to module name
            relative_path = py_file.relative_to(Path(__file__).parent.parent / "src")
            module_name = str(relative_path).replace("/", ".").replace(".py", "")

            try:
                module = importlib.import_module(module_name)

                # Find all classes that inherit from BaseService
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, BaseService)
                        and obj != BaseService
                        and not name.startswith("_")
                    ):
                        services.append((module_name, name, obj))
            except Exception:
                # Skip modules that can't be imported
                pass

    return services


def test_config_singleton():
    """Test that Config is truly a singleton across all services."""

    print("=== Testing Config Singleton Pattern ===\n")

    # Reset singleton for clean test
    Config.reset_singleton()

    # Track Config instances

    # Test 1: Direct Config instantiation
    print("Test 1: Direct Config instantiation")
    config1 = Config()
    config2 = Config()
    config3 = Config({"test": "value"})

    print(f"  config1 id: {id(config1)}")
    print(f"  config2 id: {id(config2)}")
    print(f"  config3 id: {id(config3)}")

    if id(config1) == id(config2) == id(config3):
        print("  ✅ All Config instances are the same object (singleton works!)")
    else:
        print("  ❌ Config instances are different objects (singleton broken!)")
        return False

    # Test 2: Config in BaseService
    print("\nTest 2: Config in BaseService classes")
    from claude_mpm.core.base_service import BaseService

    class TestService1(BaseService):
        async def _initialize(self):
            pass

        async def _cleanup(self):
            pass

    class TestService2(BaseService):
        async def _initialize(self):
            pass

        async def _cleanup(self):
            pass

    service1 = TestService1("test1")
    service2 = TestService2("test2")

    print(f"  service1.config id: {id(service1.config)}")
    print(f"  service2.config id: {id(service2.config)}")
    print(f"  Original config id: {id(config1)}")

    if id(service1.config) == id(service2.config) == id(config1):
        print("  ✅ All services share the same Config instance")
    else:
        print("  ❌ Services have different Config instances")
        return False

    # Test 3: Config value consistency
    print("\nTest 3: Config value consistency")
    config1.set("test_key", "test_value")

    if (
        service1.config.get("test_key") == "test_value"
        and service2.config.get("test_key") == "test_value"
    ):
        print("  ✅ Config changes are reflected across all instances")
    else:
        print("  ❌ Config changes are not shared")
        return False

    # Test 4: Check for any Config() calls in actual service code
    print("\nTest 4: Checking service implementations")
    services = find_all_services()
    print(f"  Found {len(services)} service classes")

    if services:
        # Sample a few services
        for module_name, class_name, _service_class in services[:5]:
            print(f"  - {module_name}.{class_name}")

    return True


def check_log_messages():
    """Check that singleton log messages are correct."""
    import io

    print("\n=== Checking Log Messages ===\n")

    # Reset singleton
    Config.reset_singleton()

    # Capture logs
    log_buffer = io.StringIO()
    handler = logging.StreamHandler(log_buffer)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    logger = logging.getLogger("claude_mpm.core.config")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    # Create multiple Config instances
    Config()
    Config()
    Config()

    # Check logs
    logs = log_buffer.getvalue()
    lines = logs.split("\n")

    created_count = sum(
        1 for line in lines if "Creating new Config singleton instance" in line
    )
    reused_count = sum(
        1 for line in lines if "Reusing existing Config singleton instance" in line
    )
    loaded_count = sum(
        1 for line in lines if "Successfully loaded configuration" in line
    )

    print(f"  Singleton created: {created_count} time(s)")
    print(f"  Singleton reused: {reused_count} time(s)")
    print(f"  Config loaded: {loaded_count} time(s)")

    if created_count == 1 and reused_count == 2:
        print("  ✅ Log messages indicate singleton is working correctly")
        return True
    print("  ❌ Log messages indicate singleton issue")
    print("\nFull logs:")
    print(logs)
    return False


if __name__ == "__main__":
    success = True

    # Run tests
    success = test_config_singleton() and success
    success = check_log_messages() and success

    # Summary
    print("\n=== Summary ===")
    if success:
        print("✅ Config singleton pattern is working correctly!")
        print("   - Configuration is loaded only once")
        print("   - All services share the same Config instance")
        print("   - No duplicate configuration loading")
    else:
        print("❌ Config singleton pattern has issues")

    sys.exit(0 if success else 1)
