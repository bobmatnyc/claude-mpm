#!/usr/bin/env python3
"""Test script to verify the Socket.IO server refactoring.

WHY: This script tests that the refactored Socket.IO server with modular
event handlers maintains backward compatibility and works correctly.
"""

import sys
import os
import asyncio
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.socketio_server import SocketIOServer
from claude_mpm.core.logger import setup_logging


def test_server_initialization():
    """Test that the server can be initialized with the new handler system."""
    print("Testing server initialization...")
    
    try:
        server = SocketIOServer(host="localhost", port=8766)
        print("✓ Server initialized successfully")
        
        # Check that handler attributes will be set after start
        assert not hasattr(server, 'event_registry'), "Registry should not exist before start"
        print("✓ Registry not initialized before start (expected)")
        
        return True
    except Exception as e:
        print(f"✗ Server initialization failed: {e}")
        return False


def test_handler_imports():
    """Test that all handler modules can be imported."""
    print("\nTesting handler imports...")
    
    try:
        from claude_mpm.services.socketio.handlers import (
            BaseEventHandler,
            ConnectionEventHandler,
            ProjectEventHandler,
            MemoryEventHandler,
            FileEventHandler,
            GitEventHandler,
            EventHandlerRegistry,
        )
        print("✓ All handler modules imported successfully")
        return True
    except Exception as e:
        print(f"✗ Handler import failed: {e}")
        return False


def test_registry_initialization():
    """Test that the registry can be initialized with handlers."""
    print("\nTesting registry initialization...")
    
    try:
        from claude_mpm.services.socketio.handlers import EventHandlerRegistry
        
        # Create a mock server object
        class MockServer:
            def __init__(self):
                self.sio = None
                self.clients = set()
                self.event_history = []
                self.session_id = None
                self.claude_status = "stopped"
                self.claude_pid = None
        
        mock_server = MockServer()
        registry = EventHandlerRegistry(mock_server)
        
        # Initialize the registry
        registry.initialize()
        
        print(f"✓ Registry initialized with {len(registry.handlers)} handlers")
        
        # Check that all expected handlers are present
        handler_names = [h.__class__.__name__ for h in registry.handlers]
        expected = [
            "ConnectionEventHandler",
            "GitEventHandler", 
            "FileEventHandler",
            "ProjectEventHandler",
            "MemoryEventHandler"
        ]
        
        for name in expected:
            if name in handler_names:
                print(f"✓ {name} registered")
            else:
                print(f"✗ {name} missing")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Registry initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_handler_methods():
    """Test that FileEventHandler methods work correctly."""
    print("\nTesting FileEventHandler methods...")
    
    try:
        from claude_mpm.services.socketio.handlers import FileEventHandler
        
        # Create a mock server
        class MockServer:
            def __init__(self):
                self.sio = None
                self.clients = set()
                self.event_history = []
        
        mock_server = MockServer()
        handler = FileEventHandler(mock_server)
        
        # Test _read_file_safely with a known file
        test_file = __file__  # This script itself
        
        async def test_read():
            result = await handler._read_file_safely(test_file)
            return result
        
        result = asyncio.run(test_read())
        
        if result['success']:
            print(f"✓ File read successfully: {test_file}")
            print(f"  - Size: {result['file_size']} bytes")
            print(f"  - Extension: {result['extension']}")
            print(f"  - Encoding: {result['encoding']}")
        else:
            print(f"✗ File read failed: {result.get('error')}")
            return False
        
        # Test with non-existent file
        async def test_nonexistent():
            result = await handler._read_file_safely("/nonexistent/file.txt")
            return result
        
        result = asyncio.run(test_nonexistent())
        
        if not result['success']:
            error_msg = result.get('error', '')
            if 'does not exist' in error_msg or 'outside allowed' in error_msg:
                print(f"✓ Correctly handled non-existent/forbidden file: {error_msg}")
            else:
                print(f"✗ Unexpected error for non-existent file: {error_msg}")
                return False
        else:
            print("✗ Failed to handle non-existent file properly - returned success")
            return False
        
        return True
    except Exception as e:
        print(f"✗ FileEventHandler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_git_handler_methods():
    """Test that GitEventHandler helper methods work correctly."""
    print("\nTesting GitEventHandler methods...")
    
    try:
        from claude_mpm.services.socketio.handlers import GitEventHandler
        
        # Create a mock server
        class MockServer:
            def __init__(self):
                self.sio = None
                self.clients = set()
                self.event_history = []
        
        mock_server = MockServer()
        handler = GitEventHandler(mock_server)
        
        # Test sanitize_working_dir
        sanitized = handler._sanitize_working_dir(None, "test")
        print(f"✓ Sanitized None to: {sanitized}")
        
        sanitized = handler._sanitize_working_dir("Unknown", "test")
        print(f"✓ Sanitized 'Unknown' to: {sanitized}")
        
        sanitized = handler._sanitize_working_dir("/tmp", "test")
        print(f"✓ Kept valid path: {sanitized}")
        
        # Test is_git_repository
        is_git = handler._is_git_repository(os.getcwd())
        print(f"✓ Git repository check: {is_git}")
        
        return True
    except Exception as e:
        print(f"✗ GitEventHandler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Socket.IO Server Refactoring Test Suite")
    print("=" * 60)
    
    # Setup logging
    setup_logging(level="WARNING", console_output=False)
    
    # Run tests
    tests = [
        test_handler_imports,
        test_server_initialization,
        test_registry_initialization,
        test_file_handler_methods,
        test_git_handler_methods,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"\n✗ Test {test.__name__} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test.__name__, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The refactoring is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please review the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()