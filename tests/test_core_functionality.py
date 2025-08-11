#!/usr/bin/env python3
"""
Test script to verify core functionality after import fixes.
Tests agent loading, service registry, and CLI commands.
"""

import sys
import os
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_agent_loading():
    """Test agent loading functionality."""
    print("1. Testing Agent Loading...")
    try:
        from claude_mpm.agents.agent_loader import AgentLoader
        from claude_mpm.agents.base_agent_loader import prepend_base_instructions
        
        # Test agent loader
        loader = AgentLoader()
        print("   ✓ AgentLoader instantiated successfully")
        
        # Test agent listing
        agents = loader.list_agents()
        print(f"   ✓ Agent listing successful, found {len(agents)} agents")
        
        # Test base instructions
        sample_prompt = "Test prompt"
        full_prompt = prepend_base_instructions(sample_prompt)
        print(f"   ✓ Base instructions prepended, total length: {len(full_prompt)} chars")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Agent loading failed: {e}")
        traceback.print_exc()
        return False

def test_service_registry():
    """Test service registry functionality."""
    print("\n2. Testing Service Registry...")
    try:
        from claude_mpm.core.service_registry import ServiceRegistry, get_service_registry
        from claude_mpm.services import AgentDeploymentService
        
        # Test registry instantiation
        registry = ServiceRegistry()
        print("   ✓ ServiceRegistry instantiated successfully")
        
        # Test service registration by importing the service properly
        service_instance = AgentDeploymentService()
        print("   ✓ AgentDeploymentService instantiated successfully")
        
        # Test using the service registry's list functionality instead  
        services = registry.list_services()
        print(f"   ✓ Service listing successful, found {len(services)} registered services")
        
        # Test global registry
        global_registry = get_service_registry()
        print("   ✓ Global registry access successful")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Service registry failed: {e}")
        traceback.print_exc()
        return False

def test_cli_accessibility():
    """Test CLI command accessibility."""
    print("\n3. Testing CLI Accessibility...")
    try:
        from claude_mpm.cli.parser import create_parser
        from claude_mpm.cli.commands import run, memory
        
        # Test parser creation
        parser = create_parser()
        print("   ✓ CLI parser created successfully")
        
        # Test command modules are importable
        print("   ✓ CLI commands imported successfully")
        
        # Test parsing a simple command
        args = parser.parse_args(['run', '-i', 'test prompt', '--non-interactive'])
        print("   ✓ CLI argument parsing successful")
        
        return True
        
    except Exception as e:
        print(f"   ✗ CLI accessibility failed: {e}")
        traceback.print_exc()
        return False

def test_core_imports():
    """Test core module imports."""
    print("\n4. Testing Core Module Imports...")
    try:
        # Test core imports
        from claude_mpm.core import factories, logger, service_registry, claude_runner
        print("   ✓ Core modules imported successfully")
        
        # Test services imports (correct names)
        from claude_mpm.services import AgentDeploymentService
        from claude_mpm.services.claude_session_logger import ClaudeSessionLogger
        from claude_mpm.services.async_session_logger import AsyncSessionLogger
        print("   ✓ Service modules imported successfully")
        
        # Test config imports
        from claude_mpm.config import paths
        print("   ✓ Config modules imported successfully")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Core imports failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all core functionality tests."""
    print("=" * 80)
    print("Testing Core Functionality After Import Fixes")
    print("=" * 80)
    
    tests = [
        test_core_imports,
        test_agent_loading,
        test_service_registry,
        test_cli_accessibility
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"   ✗ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ ALL CORE FUNCTIONALITY TESTS PASSED")
        return 0
    else:
        print("❌ SOME CORE FUNCTIONALITY TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())