#!/usr/bin/env python3
"""
Quick test to verify the Socket.IO hook fix works.
"""

import json
import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def test_fixed_hook_handler():
    """Test the fixed hook handler."""
    print("🧪 Testing fixed hook handler...")
    
    # Set up environment
    env = os.environ.copy()
    env['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
    env['CLAUDE_MPM_SOCKETIO_PORT'] = '8765'
    env['PYTHONPATH'] = str(project_root / "src")
    
    # Create test event
    hook_event = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "Test fixed hook handler",
        "session_id": "test_fix_123",
        "cwd": str(Path.cwd()),
        "timestamp": datetime.now().isoformat()
    }
    
    hook_json = json.dumps(hook_event)
    
    # Run hook handler
    hook_handler_path = project_root / "src" / "claude_mpm" / "hooks" / "claude_hooks" / "hook_handler.py"
    
    try:
        result = subprocess.run(
            [sys.executable, str(hook_handler_path)],
            input=hook_json,
            text=True,
            capture_output=True,
            env=env,
            timeout=10
        )
        
        print(f"📤 Exit code: {result.returncode}")
        print(f"📤 Stdout: {result.stdout}")
        if result.stderr:
            print(f"📤 Stderr: {result.stderr}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_connection_pool_fix():
    """Test the fixed connection pool."""
    print("🧪 Testing fixed connection pool...")
    
    try:
        from claude_mpm.core.socketio_pool import get_connection_pool
        
        # Get pool and test emission
        pool = get_connection_pool()
        
        test_data = {
            'event_type': 'test_fixed_pool',
            'message': 'Testing fixed connection pool',
            'timestamp': datetime.now().isoformat()
        }
        
        print("📤 Emitting test event...")
        pool.emit_event('/hook', 'test_event', test_data)
        
        # Wait for batch processing
        time.sleep(2)
        
        # Check stats
        stats = pool.get_stats()
        print(f"📊 Pool stats: {json.dumps(stats, indent=2)}")
        
        # Success if no errors and connection was attempted
        return stats['total_errors'] == 0
        
    except Exception as e:
        print(f"❌ Connection pool test failed: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        return False

def main():
    """Run quick tests to verify fixes."""
    print("🔧 Testing Socket.IO Hook Integration Fixes")
    print("=" * 50)
    
    # Test 1: Hook handler subprocess
    hook_test = test_fixed_hook_handler()
    print(f"Hook handler test: {'✅ PASS' if hook_test else '❌ FAIL'}")
    
    # Test 2: Connection pool
    pool_test = test_connection_pool_fix()
    print(f"Connection pool test: {'✅ PASS' if pool_test else '❌ FAIL'}")
    
    print("=" * 50)
    
    if hook_test and pool_test:
        print("✅ All fixes verified! Socket.IO hook integration should now work.")
        print("\nTo use with Claude:")
        print("export CLAUDE_MPM_HOOK_DEBUG=true")
        print("export CLAUDE_MPM_SOCKETIO_PORT=8765")
        print("./claude-mpm run -i 'your prompt' --monitor")
        return True
    else:
        print("❌ Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)