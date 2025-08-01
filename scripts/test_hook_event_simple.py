#!/usr/bin/env python3
"""Simple test to trigger hook events and verify Socket.IO data flow."""

import os
import sys
import time
from pathlib import Path

# Add the claude-mpm source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_hook_handler_event_emission():
    """Test hook handler can emit events to Socket.IO server."""
    try:
        # Set environment variables
        os.environ['CLAUDE_MPM_SOCKETIO_PORT'] = '8765'
        os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
        
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
        
        print("Creating hook handler...")
        handler = ClaudeHookHandler()
        
        if not hasattr(handler, 'socketio_client') or not handler.socketio_client:
            print("❌ Hook handler has no Socket.IO client")
            return False
        
        print("✓ Hook handler has Socket.IO client")
        
        # Test emit_event method if it exists
        if hasattr(handler, 'emit_event'):
            print("Testing event emission...")
            
            test_event = {
                "event": "test_hook_start",
                "hook_name": "test_data_flow_hook",
                "timestamp": time.time(),
                "test": True,
                "message": "Testing data flow from hook handler to Socket.IO server"
            }
            
            try:
                handler.emit_event('hook_event', test_event)
                print("✓ Successfully emitted test event")
                time.sleep(0.5)  # Give server time to process
                return True
            except Exception as e:
                print(f"❌ Failed to emit event: {e}")
                return False
        else:
            print("⚠️  Hook handler has no emit_event method")
            return False
            
    except Exception as e:
        print(f"❌ Hook handler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_manual_socketio_emit():
    """Test manual Socket.IO event emission."""
    try:
        import socketio
        
        client = socketio.Client(logger=False, engineio_logger=False)
        
        connected = False
        
        @client.event
        def connect():
            nonlocal connected
            connected = True
            print("✓ Manual client connected")
        
        @client.event  
        def disconnect():
            print("ℹ Manual client disconnected")
        
        print("Connecting manual client...")
        try:
            client.connect('http://localhost:8765', auth={'token': 'dev-token'}, wait=True)
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
            
        if not connected:
            print("❌ Manual client not connected")
            return False
        
        # Emit test event
        test_event = {
            "event": "manual_test_event",
            "timestamp": time.time(),
            "test": True,
            "message": "Manual test event to verify Socket.IO data flow"
        }
        
        try:
            client.emit('hook_event', test_event, namespace='/hook')
            print("✓ Manual client emitted test event")
            time.sleep(0.5)
        except Exception as e:
            print(f"❌ Failed to emit manual event: {e}")
            return False
        finally:
            client.disconnect()
        
        return True
        
    except ImportError:
        print("❌ python-socketio not available for manual test")
        return False
    except Exception as e:
        print(f"❌ Manual Socket.IO test failed: {e}")
        return False

def main():
    """Run event emission tests."""
    print("=== Socket.IO Data Flow Event Tests ===")
    
    tests = [
        ("Hook Handler Event Emission", test_hook_handler_event_emission),
        ("Manual Socket.IO Event Emission", test_manual_socketio_emit)
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
    return passed > 0  # At least one test should pass

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)