#!/usr/bin/env python3
"""Simple system health check for claude-mpm."""

import sys
import os
import subprocess
from pathlib import Path

def print_status(test_name, passed, details=""):
    """Print test status with formatting."""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"      {details}")

def test_python_environment():
    """Check Python environment setup."""
    print("\n1. Testing Python Environment:")
    
    # Check Python version
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    print_status(
        "Python version", 
        version.major == 3 and version.minor >= 8,
        f"Python {version_str}"
    )
    
    # Check if we're in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    print_status("Virtual environment", in_venv, 
                 "Active" if in_venv else "Not detected")
    
    return True

def test_package_import():
    """Test importing claude_mpm package."""
    print("\n2. Testing Package Import:")
    
    try:
        import claude_mpm
        print_status("Import claude_mpm", True)
        
        # Check package path
        package_path = Path(claude_mpm.__file__).parent
        print_status("Package location", True, str(package_path))
        
        # Try importing key modules
        modules_to_test = [
            "claude_mpm.core",
            "claude_mpm.agents",
            "claude_mpm.hooks",
            "claude_mpm.services",
            "claude_mpm.orchestration"
        ]
        
        all_imported = True
        for module in modules_to_test:
            try:
                __import__(module)
                print_status(f"Import {module}", True)
            except ImportError as e:
                print_status(f"Import {module}", False, str(e))
                all_imported = False
        
        return all_imported
        
    except ImportError as e:
        print_status("Import claude_mpm", False, str(e))
        return False

def test_basic_functionality():
    """Test basic functionality."""
    print("\n3. Testing Basic Functionality:")
    
    try:
        # Test agent registry - try different import paths
        try:
            from claude_mpm.services.agent_registry import AgentRegistry
        except ImportError:
            try:
                from claude_mpm.core.agent_registry import AgentRegistry
            except ImportError:
                # Use the agent functions directly
                from claude_mpm.agents import list_available_agents
                agents = list_available_agents()
                print_status("Agent discovery", True, f"Found {len(agents)} agents")
                registry_found = False
        
        if 'AgentRegistry' in locals():
            registry = AgentRegistry()
            agents = registry.discover_agents()
            print_status("AgentRegistry creation", True, f"Found {len(agents)} agents")
        
        # Test hook service exists
        from claude_mpm.services.hook_service import HookRegistry
        registry = HookRegistry()
        print_status("HookRegistry creation", True, 
                    "Hook service available")
        
        # Test simple runner exists
        from claude_mpm.core.simple_runner import SimpleClaudeRunner
        print_status("SimpleClaudeRunner import", True)
        
        return True
        
    except Exception as e:
        print_status("Basic functionality", False, str(e))
        return False

def test_cli_availability():
    """Test CLI script availability."""
    print("\n4. Testing CLI Availability:")
    
    # Check if cli.py exists
    cli_path = Path(__file__).parent.parent / "src" / "claude_mpm" / "cli.py"
    cli_exists = cli_path.exists()
    print_status("cli.py exists", cli_exists, str(cli_path))
    
    # Check if main script exists
    main_script = Path(__file__).parent.parent / "claude-mpm"
    script_exists = main_script.exists()
    print_status("claude-mpm script exists", script_exists, str(main_script))
    
    # Try running help command
    if script_exists:
        try:
            result = subprocess.run(
                [str(main_script), "--help"],
                capture_output=True,
                text=True,
                timeout=5
            )
            help_works = result.returncode == 0
            print_status("CLI help command", help_works,
                        "Exit code: " + str(result.returncode))
        except Exception as e:
            print_status("CLI help command", False, str(e))
    
    return cli_exists and script_exists

def main():
    """Run all tests."""
    print("=" * 60)
    print("CLAUDE-MPM SYSTEM HEALTH CHECK")
    print("=" * 60)
    
    results = []
    
    # Run all tests
    results.append(("Environment", test_python_environment()))
    results.append(("Package Import", test_package_import()))
    results.append(("Basic Functionality", test_basic_functionality()))
    results.append(("CLI Availability", test_cli_availability()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ System is healthy and ready to use!")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())