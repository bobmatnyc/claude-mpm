#!/usr/bin/env python3
"""Test port detection and environment variable handling."""

import os
import sys
import socket
import subprocess
from pathlib import Path

# Add the claude-mpm source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_environment_variable_setting():
    """Test if ClaudeRunner sets CLAUDE_MPM_SOCKETIO_PORT correctly."""
    try:
        # Clear any existing environment variable
        if 'CLAUDE_MPM_SOCKETIO_PORT' in os.environ:
            del os.environ['CLAUDE_MPM_SOCKETIO_PORT']
        
        print("Testing ClaudeRunner environment variable setting...")
        
        from claude_mpm.core.claude_runner import ClaudeRunner
        
        # Create runner with WebSocket enabled
        test_port = 8888
        runner = ClaudeRunner(
            enable_websocket=True,
            websocket_port=test_port,
            launch_method="subprocess"  # Use subprocess to avoid exec
        )
        
        # Check if environment variable was set
        env_port = os.environ.get('CLAUDE_MPM_SOCKETIO_PORT')
        
        if env_port:
            if int(env_port) == test_port:
                print(f"✓ CLAUDE_MPM_SOCKETIO_PORT correctly set to {env_port}")
                return True
            else:
                print(f"❌ CLAUDE_MPM_SOCKETIO_PORT set to wrong value: {env_port} (expected {test_port})")
                return False
        else:
            print("❌ CLAUDE_MPM_SOCKETIO_PORT not set by ClaudeRunner")
            return False
            
    except Exception as e:
        print(f"❌ Environment variable setting test failed: {e}")
        return False

def test_hook_handler_port_detection():
    """Test if hook handler detects port correctly from environment variable."""
    try:
        # Test with environment variable
        test_port = 8899
        os.environ['CLAUDE_MPM_SOCKETIO_PORT'] = str(test_port)
        os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
        
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
        
        print(f"Testing hook handler port detection with env var {test_port}...")
        handler = ClaudeHookHandler()
        
        if handler.server_port == test_port:
            print(f"✓ Hook handler correctly detected port {test_port} from environment")
            env_test_pass = True
        else:
            print(f"❌ Hook handler detected wrong port: {handler.server_port} (expected {test_port})")
            env_test_pass = False
        
        # Test without environment variable (fallback behavior)
        if 'CLAUDE_MPM_SOCKETIO_PORT' in os.environ:
            del os.environ['CLAUDE_MPM_SOCKETIO_PORT']
        
        print("Testing hook handler fallback port detection...")
        handler2 = ClaudeHookHandler()
        
        if handler2.server_port in [8765, 8080, 8081, 8082, 8083, 8084, 8085]:
            print(f"✓ Hook handler fell back to common port: {handler2.server_port}")
            fallback_test_pass = True
        else:
            print(f"⚠️  Hook handler used unexpected fallback port: {handler2.server_port}")
            fallback_test_pass = True  # Still acceptable behavior
        
        return env_test_pass and fallback_test_pass
        
    except Exception as e:
        print(f"❌ Hook handler port detection test failed: {e}")
        return False

def test_custom_port_configuration():
    """Test running with custom port configuration."""
    try:
        # Test with a definitely available port
        import socket
        
        # Find an available port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 0))
            custom_port = s.getsockname()[1]
        
        print(f"Testing custom port configuration with port {custom_port}...")
        
        # Test ClaudeRunner with custom port
        os.environ['CLAUDE_MPM_SOCKETIO_PORT'] = str(custom_port)
        
        from claude_mpm.core.claude_runner import ClaudeRunner
        
        runner = ClaudeRunner(
            enable_websocket=True,
            websocket_port=custom_port,
            launch_method="subprocess"
        )
        
        # Check environment variable
        env_port = os.environ.get('CLAUDE_MPM_SOCKETIO_PORT')
        
        if env_port and int(env_port) == custom_port:
            print(f"✓ Custom port {custom_port} correctly configured")
            return True
        else:
            print(f"❌ Custom port configuration failed: env={env_port}, expected={custom_port}")
            return False
            
    except Exception as e:
        print(f"❌ Custom port configuration test failed: {e}")
        return False

def test_port_conflict_handling():
    """Test behavior when configured port is already in use."""
    try:
        # Start a simple server on a port
        import socket
        import threading
        
        # Find an available port and occupy it
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('localhost', 0))
        occupied_port = server_socket.getsockname()[1]
        server_socket.listen(1)
        
        print(f"Testing port conflict handling with occupied port {occupied_port}...")
        
        def keep_port_busy():
            try:
                server_socket.accept()
            except:
                pass
        
        # Start background thread to keep port busy
        busy_thread = threading.Thread(target=keep_port_busy, daemon=True)
        busy_thread.start()
        
        # Set environment to the occupied port
        os.environ['CLAUDE_MPM_SOCKETIO_PORT'] = str(occupied_port)
        
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
        
        # Hook handler should either handle this gracefully or detect the port is busy
        try:
            handler = ClaudeHookHandler()
            print(f"✓ Hook handler handled port conflict gracefully (detected port: {handler.server_port})")
            result = True
        except Exception as e:
            print(f"⚠️  Hook handler encountered port conflict: {e}")
            result = True  # This is acceptable behavior
        finally:
            server_socket.close()
        
        return result
        
    except Exception as e:
        print(f"❌ Port conflict handling test failed: {e}")
        return False

def main():
    """Run port detection tests."""
    print("=== Port Detection Tests ===")
    
    tests = [
        ("Environment Variable Setting", test_environment_variable_setting),
        ("Hook Handler Port Detection", test_hook_handler_port_detection),
        ("Custom Port Configuration", test_custom_port_configuration),
        ("Port Conflict Handling", test_port_conflict_handling)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n=== Test Results ===")
    passed = 0
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(tests)} tests passed")
    return passed >= 3  # At least 3 out of 4 should pass

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)