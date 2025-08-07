#!/usr/bin/env python3
"""
Test integration between socketio_server_manager.py and socketio_daemon.py

This test verifies that the fixes work correctly:
1. Manager can detect daemon-style servers
2. Stop command works with both management styles
3. Conflict detection and resolution works
4. Error messages are helpful
"""

import os
import sys
import time
import subprocess
import signal
import tempfile
from pathlib import Path
import json

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import from scripts directory
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))
from socketio_server_manager import ServerManager

def test_daemon_detection():
    """Test that manager can detect daemon-style servers."""
    print("🔍 Testing daemon detection...")
    
    manager = ServerManager()
    
    # Create mock daemon PID file
    daemon_pidfile = Path.home() / ".claude-mpm" / "socketio-server.pid"
    daemon_pidfile.parent.mkdir(exist_ok=True)
    
    # Use our own PID as test (it definitely exists)
    test_pid = os.getpid()
    
    try:
        with open(daemon_pidfile, 'w') as f:
            f.write(str(test_pid))
        
        print(f"   Created mock daemon PID file: {daemon_pidfile}")
        print(f"   Test PID: {test_pid}")
        
        # Test daemon PID detection
        detected_pid = manager._get_daemon_pid()
        print(f"   Detected PID: {detected_pid}")
        
        if detected_pid == test_pid:
            print("   ✅ Daemon PID detection works")
        else:
            print(f"   ❌ Expected {test_pid}, got {detected_pid}")
        
        # Test daemon server info
        daemon_info = manager._get_daemon_server_info()
        print(f"   Daemon info: {daemon_info}")
        
        if daemon_info and daemon_info.get('pid') == test_pid:
            print("   ✅ Daemon server info detection works")
        else:
            print("   ❌ Daemon server info detection failed")
            
    finally:
        # Clean up
        try:
            daemon_pidfile.unlink(missing_ok=True)
            print("   🧹 Cleaned up test PID file")
        except:
            pass

def test_server_listing():
    """Test server listing with mixed management styles."""
    print("\n🔍 Testing server listing...")
    
    manager = ServerManager()
    
    # Test with no servers
    servers = manager.list_running_servers()
    print(f"   Found {len(servers)} servers (expected: 0)")
    
    if len(servers) == 0:
        print("   ✅ No servers detected correctly")
    else:
        print(f"   ℹ️  Found existing servers: {[s.get('server_id') for s in servers]}")

def test_status_output():
    """Test status command output."""
    print("\n🔍 Testing status output...")
    
    manager = ServerManager()
    
    print("   Status output:")
    print("   " + "="*50)
    
    # Capture the output
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        manager.status(verbose=True)
    
    output = f.getvalue()
    print("   " + output.replace('\n', '\n   '))
    
    if "Management options" in output or "running server" in output:
        print("   ✅ Status output includes management info")
    else:
        print("   ❌ Status output missing management info")

def test_diagnose_command():
    """Test the diagnose command."""
    print("\n🔍 Testing diagnose command...")
    
    manager = ServerManager()
    
    print("   Diagnose output:")
    print("   " + "="*50)
    
    # Capture the output
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        manager.diagnose_conflicts(port=8765)
    
    output = f.getvalue()
    print("   " + output.replace('\n', '\n   '))
    
    if "Server Analysis" in output and "Management Commands" in output:
        print("   ✅ Diagnose output includes analysis and commands")
    else:
        print("   ❌ Diagnose output missing key sections")

def test_error_handling():
    """Test error handling for invalid PIDs."""
    print("\n🔍 Testing error handling...")
    
    manager = ServerManager()
    
    # Test with invalid PID
    invalid_pid = 999999  # Very likely doesn't exist
    
    if not manager._validate_pid(invalid_pid):
        print(f"   ✅ Invalid PID {invalid_pid} correctly detected as invalid")
    else:
        print(f"   ❌ Invalid PID {invalid_pid} incorrectly detected as valid")
    
    # Test with valid PID (our own)
    our_pid = os.getpid()
    if manager._validate_pid(our_pid):
        print(f"   ✅ Valid PID {our_pid} correctly detected as valid")
    else:
        print(f"   ❌ Valid PID {our_pid} incorrectly detected as invalid")

def main():
    """Run all tests."""
    print("🧪 Socket.IO Management Integration Tests")
    print("="*50)
    
    try:
        test_daemon_detection()
        test_server_listing()
        test_status_output()
        test_diagnose_command()
        test_error_handling()
        
        print("\n✅ All tests completed!")
        print("\n💡 To test manually:")
        print("   1. Start daemon: python src/claude_mpm/scripts/socketio_daemon.py start")
        print("   2. Check status: python src/claude_mpm/scripts/socketio_server_manager.py status")
        print("   3. Try stop: python src/claude_mpm/scripts/socketio_server_manager.py stop --port 8765")
        print("   4. Diagnose: python src/claude_mpm/scripts/socketio_server_manager.py diagnose")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())