#!/usr/bin/env python3
"""Test memory services reorganization."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_direct_imports():
    """Test direct imports from new locations."""
    print("Testing direct imports from new locations...")
    
    try:
        # Import from new locations
        from claude_mpm.services.memory.builder import MemoryBuilder
        print("✓ MemoryBuilder imported from memory.builder")
        
        from claude_mpm.services.memory.router import MemoryRouter
        print("✓ MemoryRouter imported from memory.router")
        
        from claude_mpm.services.memory.optimizer import MemoryOptimizer
        print("✓ MemoryOptimizer imported from memory.optimizer")
        
        from claude_mpm.services.memory.cache.simple_cache import SimpleCacheService
        print("✓ SimpleCacheService imported from memory.cache.simple_cache")
        
        from claude_mpm.services.memory.cache.shared_prompt_cache import SharedPromptCache
        print("✓ SharedPromptCache imported from memory.cache.shared_prompt_cache")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_package_imports():
    """Test imports from package __init__ files."""
    print("\nTesting imports from package __init__ files...")
    
    try:
        # Import from memory package
        from claude_mpm.services.memory import MemoryBuilder, MemoryRouter, MemoryOptimizer
        print("✓ Memory services imported from memory package")
        
        # Import from cache package
        from claude_mpm.services.memory.cache import SimpleCacheService, SharedPromptCache
        print("✓ Cache services imported from memory.cache package")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_backward_compatibility():
    """Test backward compatibility through services module."""
    print("\nTesting backward compatibility...")
    
    try:
        # Import through services module for backward compatibility
        from claude_mpm.services import (
            MemoryBuilder,
            MemoryRouter,
            MemoryOptimizer,
            SimpleCacheService,
            SharedPromptCache
        )
        print("✓ All memory services imported via backward compatibility")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_instantiation():
    """Test that services can be instantiated."""
    print("\nTesting service instantiation...")
    
    try:
        from claude_mpm.services.memory import MemoryBuilder, MemoryRouter, MemoryOptimizer
        from claude_mpm.services.memory.cache import SimpleCacheService, SharedPromptCache
        
        # Test instantiation
        builder = MemoryBuilder()
        print("✓ MemoryBuilder instantiated")
        
        router = MemoryRouter()
        print("✓ MemoryRouter instantiated")
        
        optimizer = MemoryOptimizer()
        print("✓ MemoryOptimizer instantiated")
        
        cache = SimpleCacheService()
        print("✓ SimpleCacheService instantiated")
        
        prompt_cache = SharedPromptCache()
        print("✓ SharedPromptCache instantiated")
        
        return True
    except Exception as e:
        print(f"✗ Instantiation error: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Memory Services Reorganization Test")
    print("=" * 60)
    
    all_passed = True
    
    # Run tests
    all_passed &= test_direct_imports()
    all_passed &= test_package_imports()
    all_passed &= test_backward_compatibility()
    all_passed &= test_instantiation()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed! Reorganization successful.")
    else:
        print("❌ Some tests failed. Please review the errors above.")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())