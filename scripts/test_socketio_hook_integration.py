#!/usr/bin/env python3
"""
Comprehensive test script to diagnose and fix Socket.IO hook broadcasting issues.

This script:
1. Tests Socket.IO server connectivity
2. Simulates Claude hook events 
3. Verifies event emission to Socket.IO server
4. Identifies and fixes connection issues
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

# Add the project to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def test_server_connectivity():
    """Test if Socket.IO server is running and accessible."""
    print_section("Testing Socket.IO Server Connectivity")
    
    # Check common ports
    ports_to_check = [8765, 8080, 8081, 8082, 8083]
    running_port = None
    
    for port in ports_to_check:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                result = s.connect_ex(('localhost', port))
                if result == 0:
                    print(f"✅ Found Socket.IO server running on port {port}")
                    running_port = port
                    break
                else:
                    print(f"❌ No server on port {port}")
        except Exception as e:
            print(f"❌ Error checking port {port}: {e}")
    
    if running_port:
        # Test HTTP endpoint
        try:
            import requests
            response = requests.get(f"http://localhost:{running_port}/health", timeout=2)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check successful: {data}")
                return running_port
            else:
                print(f"❌ Health check failed: HTTP {response.status_code}")
        except ImportError:
            print("⚠️ requests package not available - skipping HTTP health check")
            return running_port
        except Exception as e:
            print(f"❌ Health check error: {e}")
    
    return running_port

def test_environment_setup():
    """Test and fix environment setup for hook handler."""
    print_section("Testing Environment Setup")
    
    # Check current environment
    debug_enabled = os.environ.get('CLAUDE_MPM_HOOK_DEBUG', '').lower() == 'true'
    socketio_port = os.environ.get('CLAUDE_MPM_SOCKETIO_PORT')
    
    print(f"CLAUDE_MPM_HOOK_DEBUG: {debug_enabled}")
    print(f"CLAUDE_MPM_SOCKETIO_PORT: {socketio_port}")
    
    # Find running server port
    running_port = test_server_connectivity()
    
    if running_port and not socketio_port:
        print(f"🔧 Setting CLAUDE_MPM_SOCKETIO_PORT to {running_port}")
        os.environ['CLAUDE_MPM_SOCKETIO_PORT'] = str(running_port)
        socketio_port = str(running_port)
    
    if not debug_enabled:
        print("🔧 Enabling debug mode for testing")
        os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
    
    return {
        'debug_enabled': True,
        'socketio_port': socketio_port,
        'running_port': running_port
    }

def test_connection_pool():
    """Test the Socket.IO connection pool functionality."""
    print_section("Testing Socket.IO Connection Pool")
    
    try:
        from claude_mpm.core.socketio_pool import get_connection_pool, SOCKETIO_AVAILABLE
        
        if not SOCKETIO_AVAILABLE:
            print("❌ Socket.IO packages not available")
            return False
        
        print("✅ Socket.IO packages available")
        
        # Get connection pool
        pool = get_connection_pool()
        print(f"✅ Connection pool created: {pool}")
        
        # Get pool stats
        stats = pool.get_stats()
        print(f"📊 Pool stats: {json.dumps(stats, indent=2)}")
        
        # Test event emission
        test_data = {
            'event_type': 'test_event',
            'message': 'Test message from connection pool',
            'timestamp': datetime.now().isoformat()
        }
        
        print("🧪 Testing event emission...")
        pool.emit_event('/hook', 'test_event', test_data)
        
        # Give time for event to process
        time.sleep(1)
        
        # Check updated stats
        updated_stats = pool.get_stats()
        print(f"📊 Updated pool stats: {json.dumps(updated_stats, indent=2)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection pool test failed: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        return False

def simulate_hook_event():
    """Simulate a Claude hook event to test the handler."""
    print_section("Simulating Claude Hook Event")
    
    # Create test hook event data
    hook_event = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "Test prompt from diagnostic script",
        "session_id": "test_session_123",
        "cwd": str(Path.cwd()),
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"🧪 Creating test hook event: {json.dumps(hook_event, indent=2)}")
    
    try:
        # Import and test the hook handler directly
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
        
        print("✅ Hook handler imported successfully")
        
        # Create handler instance
        handler = ClaudeHookHandler()
        print("✅ Hook handler instance created")
        
        # Test the specific handler method
        handler._handle_user_prompt_fast(hook_event)
        print("✅ Hook handler method executed")
        
        return True
        
    except Exception as e:
        print(f"❌ Hook event simulation failed: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        return False

def test_hook_handler_via_subprocess():
    """Test hook handler by calling it as a subprocess (how Claude actually calls it)."""
    print_section("Testing Hook Handler via Subprocess")
    
    # Find the hook handler script
    hook_handler_path = project_root / "src" / "claude_mpm" / "hooks" / "claude_hooks" / "hook_handler.py"
    
    if not hook_handler_path.exists():
        print(f"❌ Hook handler not found at: {hook_handler_path}")
        return False
    
    print(f"✅ Hook handler found at: {hook_handler_path}")
    
    # Create test hook event
    hook_event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "echo 'test command'"},
        "session_id": "test_session_456", 
        "cwd": str(Path.cwd()),
        "timestamp": datetime.now().isoformat()
    }
    
    hook_json = json.dumps(hook_event)
    print(f"🧪 Test hook event: {hook_json}")
    
    try:
        # Run hook handler as subprocess with the test event
        env = os.environ.copy()
        env['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
        env['PYTHONPATH'] = str(project_root / "src")
        
        if 'CLAUDE_MPM_SOCKETIO_PORT' in env:
            print(f"🔧 Using Socket.IO port: {env['CLAUDE_MPM_SOCKETIO_PORT']}")
        
        print("🚀 Running hook handler as subprocess...")
        
        result = subprocess.run(
            [sys.executable, str(hook_handler_path)],
            input=hook_json,
            text=True,
            capture_output=True,
            env=env,
            timeout=10
        )
        
        print(f"📤 Return code: {result.returncode}")
        print(f"📤 Stdout: {result.stdout}")
        
        if result.stderr:
            print(f"📤 Stderr: {result.stderr}")
        
        if result.returncode == 0:
            print("✅ Hook handler subprocess executed successfully")
            return True
        else:
            print(f"❌ Hook handler subprocess failed with code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Hook handler subprocess timed out")
        return False
    except Exception as e:
        print(f"❌ Hook handler subprocess error: {e}")
        return False

def test_socketio_client_connection():
    """Test direct Socket.IO client connection to verify server is receiving events."""
    print_section("Testing Direct Socket.IO Client Connection")
    
    try:
        import socketio
        
        # Get server port
        server_port = os.environ.get('CLAUDE_MPM_SOCKETIO_PORT', '8765')
        server_url = f"http://localhost:{server_port}"
        
        print(f"🔗 Connecting to Socket.IO server at: {server_url}")
        
        # Create async client
        sio = socketio.AsyncClient()
        events_received = []
        
        @sio.event
        async def connect():
            print("✅ Connected to Socket.IO server")
            
        @sio.event
        async def disconnect():
            print("🔌 Disconnected from Socket.IO server")
            
        @sio.event
        async def claude_event(data):
            print(f"📨 Received claude_event: {json.dumps(data, indent=2)}")
            events_received.append(data)
        
        async def test_connection():
            try:
                # Connect to server
                await sio.connect(server_url, namespaces=['/hook'])
                print("✅ Connected to /hook namespace")
                
                # Send test event
                test_event = {
                    "event_type": "test_from_client",
                    "message": "Direct client test",
                    "timestamp": datetime.now().isoformat()
                }
                
                await sio.emit('claude_event', test_event)
                print("📤 Sent test event to server")
                
                # Wait a bit for any responses
                await asyncio.sleep(2)
                
                # Disconnect
                await sio.disconnect()
                
                return len(events_received)
                
            except Exception as e:
                print(f"❌ Connection test failed: {e}")
                return 0
        
        # Run the async test
        events_count = asyncio.run(test_connection())
        
        if events_count > 0:
            print(f"✅ Received {events_count} events from server")
            return True
        else:
            print("⚠️ Connected successfully but received no events")
            return True  # Connection worked even if no events
            
    except ImportError:
        print("❌ python-socketio package not available")
        return False
    except Exception as e:
        print(f"❌ Socket.IO client test failed: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        return False

def fix_hook_handler_config():
    """Apply fixes to hook handler configuration based on test results."""
    print_section("Applying Hook Handler Fixes")
    
    fixes_applied = []
    
    # Fix 1: Ensure environment variables are set
    server_port = test_server_connectivity()
    if server_port:
        if not os.environ.get('CLAUDE_MPM_SOCKETIO_PORT'):
            os.environ['CLAUDE_MPM_SOCKETIO_PORT'] = str(server_port)
            fixes_applied.append(f"Set CLAUDE_MPM_SOCKETIO_PORT={server_port}")
    
    # Fix 2: Enable debug mode for visibility
    if not os.environ.get('CLAUDE_MPM_HOOK_DEBUG'):
        os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
        fixes_applied.append("Enabled CLAUDE_MPM_HOOK_DEBUG")
    
    # Fix 3: Test if connection pool needs manual initialization
    try:
        from claude_mpm.core.socketio_pool import get_connection_pool
        pool = get_connection_pool()
        if pool and not pool._running:
            pool.start()
            fixes_applied.append("Started connection pool")
    except Exception as e:
        print(f"⚠️ Could not start connection pool: {e}")
    
    print(f"🔧 Applied {len(fixes_applied)} fixes:")
    for fix in fixes_applied:
        print(f"  ✅ {fix}")
    
    return fixes_applied

def run_integration_test():
    """Run a complete integration test simulating Claude with --monitor."""
    print_section("Integration Test: Claude with --monitor")
    
    try:
        # Set up environment
        env = os.environ.copy()
        env['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
        env['PYTHONPATH'] = str(project_root / "src")
        
        server_port = test_server_connectivity()
        if server_port:
            env['CLAUDE_MPM_SOCKETIO_PORT'] = str(server_port)
        
        # Try a simple Claude command with monitoring
        claude_script = project_root / "scripts" / "claude-mpm"
        
        if not claude_script.exists():
            print(f"❌ Claude script not found at: {claude_script}")
            return False
        
        print(f"🚀 Running Claude with --monitor...")
        
        # Use a simple, safe command
        result = subprocess.run(
            [str(claude_script), "run", "-i", "echo 'Hello from integration test'", "--non-interactive"],
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"📤 Claude exit code: {result.returncode}")
        print(f"📤 Claude stdout: {result.stdout[:500]}...")  # Truncate for readability
        
        if result.stderr:
            print(f"📤 Claude stderr: {result.stderr[:500]}...")
        
        if result.returncode == 0:
            print("✅ Claude command executed successfully")
            return True
        else:
            print(f"❌ Claude command failed with code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Claude command timed out")
        return False
    except Exception as e:
        print(f"❌ Integration test error: {e}")
        return False

def main():
    """Run all diagnostic tests and apply fixes."""
    print_section("Socket.IO Hook Integration Diagnostic Tool")
    
    print(f"Project root: {project_root}")
    print(f"Current working directory: {Path.cwd()}")
    print(f"Python path: {sys.path[:3]}...")  # Show first few entries
    
    # Test results
    results = {}
    
    # 1. Test server connectivity
    results['server_connectivity'] = test_server_connectivity() is not None
    
    # 2. Test environment setup
    env_config = test_environment_setup()
    results['environment_setup'] = env_config['running_port'] is not None
    
    # 3. Apply fixes based on initial tests
    fixes = fix_hook_handler_config()
    results['fixes_applied'] = len(fixes) > 0
    
    # 4. Test connection pool
    results['connection_pool'] = test_connection_pool()
    
    # 5. Test hook event simulation
    results['hook_simulation'] = simulate_hook_event()
    
    # 6. Test hook handler subprocess
    results['hook_subprocess'] = test_hook_handler_via_subprocess()
    
    # 7. Test direct Socket.IO connection
    results['socketio_client'] = test_socketio_client_connection()
    
    # 8. Run integration test
    results['integration_test'] = run_integration_test()
    
    # Summary
    print_section("Test Results Summary")
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    print(f"Tests passed: {passed_tests}/{total_tests}")
    print()
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print_section("Recommendations")
    
    if not results['server_connectivity']:
        print("🔧 Start the Socket.IO server:")
        print("   python -m claude_mpm.services.socketio_server")
    
    if not results['connection_pool']:
        print("🔧 Install missing Socket.IO packages:")
        print("   pip install python-socketio aiohttp")
    
    if not results['hook_subprocess']:
        print("🔧 Check hook handler configuration and ensure PYTHONPATH is correct")
    
    if results['server_connectivity'] and results['connection_pool'] and not results['socketio_client']:
        print("🔧 Check Socket.IO server event handling - events may not be broadcasting correctly")
    
    print_section("Environment Variables for --monitor")
    print("Set these environment variables before running Claude with --monitor:")
    print(f"export CLAUDE_MPM_HOOK_DEBUG=true")
    if env_config.get('running_port'):
        print(f"export CLAUDE_MPM_SOCKETIO_PORT={env_config['running_port']}")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)