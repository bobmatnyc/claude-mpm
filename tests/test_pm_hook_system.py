#!/usr/bin/env python3
"""Test the complete PM hook system including TodoWrite interception."""

import sys
import time
import webbrowser
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from claude_mpm.core.pm_hook_interceptor import get_pm_hook_interceptor, trigger_pm_todowrite_hooks
    from claude_mpm.core.hook_manager import get_hook_manager
    from claude_mpm.services.websocket_server import get_server_instance
    import socketio
    IMPORTS_OK = True
except ImportError as e:
    print(f"Import error: {e}")
    IMPORTS_OK = False


def test_pm_hook_interceptor():
    """Test the PM hook interceptor functionality."""
    print("=== Testing PM Hook Interceptor ===")
    
    if not IMPORTS_OK:
        print("❌ Required imports not available")
        return False
    
    try:
        # Get the interceptor
        interceptor = get_pm_hook_interceptor()
        print("✓ PM hook interceptor created")
        
        # Test manual hook triggering
        test_todos = [
            {
                "id": "test-pm-1",
                "content": "[Research] Test todo from PM hook interceptor",
                "status": "pending",
                "priority": "high"
            },
            {
                "id": "test-pm-2", 
                "content": "[Engineer] Another test todo from PM",
                "status": "in_progress",
                "priority": "medium"
            }
        ]
        
        print(f"Triggering manual TodoWrite hooks for {len(test_todos)} todos...")
        success = interceptor.trigger_manual_todowrite_hooks(test_todos)
        
        if success:
            print("✓ Manual TodoWrite hooks triggered successfully")
        else:
            print("❌ Manual TodoWrite hooks failed")
            return False
        
        # Test the convenience function
        print("Testing convenience function...")
        success2 = trigger_pm_todowrite_hooks([{
            "id": "test-convenience",
            "content": "[QA] Test todo from convenience function",
            "status": "pending",
            "priority": "low"
        }])
        
        if success2:
            print("✓ Convenience function worked")
        else:
            print("❌ Convenience function failed")
        
        return success and success2
        
    except Exception as e:
        print(f"❌ PM hook interceptor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_server_events():
    """Test if the server is receiving and can emit events."""
    print("\n=== Testing Server Event System ===")
    
    try:
        # Get server instance
        server = get_server_instance()
        
        if not server:
            print("❌ Could not get server instance")
            return False
        
        print("✓ Got server instance")
        
        # Test emitting events directly
        print("Emitting test events directly to server...")
        
        # Test hook events
        server.emit_event('/hook', 'pre_tool', {
            'tool_name': 'TodoWrite',
            'source': 'direct_test',
            'test': True
        })
        
        server.emit_event('/hook', 'post_tool', {
            'tool_name': 'TodoWrite',
            'exit_code': 0,
            'source': 'direct_test',
            'test': True
        })
        
        # Test todo events
        server.emit_event('/todo', 'updated', {
            'todos': [
                {
                    'id': 'direct-test-1',
                    'content': '[Research] Direct server test todo',
                    'status': 'pending',
                    'priority': 'high'
                }
            ],
            'stats': {'total': 1, 'pending': 1, 'completed': 0, 'in_progress': 0},
            'source': 'direct_test'
        })
        
        print("✓ Events emitted directly to server")
        return True
        
    except Exception as e:
        print(f"❌ Server event test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dashboard_connectivity():
    """Test if dashboard can be accessed."""
    print("\n=== Testing Dashboard Connectivity ===")
    
    try:
        import requests
        
        # Test dashboard endpoint
        response = requests.get("http://localhost:8765/dashboard", timeout=5)
        if response.status_code == 200:
            print("✓ Dashboard accessible")
            dashboard_working = True
        else:
            print(f"❌ Dashboard returned {response.status_code}")
            dashboard_working = False
        
        # Test Socket.IO endpoint
        response2 = requests.get("http://localhost:8765/socket.io/?EIO=4&transport=polling", timeout=5)
        if response2.status_code == 200:
            print("✓ Socket.IO endpoint accessible")
            socketio_working = True
        else:
            print(f"❌ Socket.IO endpoint returned {response2.status_code}")
            socketio_working = False
        
        return dashboard_working and socketio_working
        
    except Exception as e:
        print(f"❌ Dashboard connectivity test failed: {e}")
        return False


def run_integration_test():
    """Run a complete integration test with dashboard."""
    print("\n=== Running Integration Test ===")
    
    print("1. Opening dashboard in browser...")
    try:
        dashboard_url = "http://localhost:8765/dashboard?autoconnect=true&port=8765"
        webbrowser.open(dashboard_url)
        print(f"✓ Opened dashboard: {dashboard_url}")
    except Exception as e:
        print(f"⚠️  Could not open browser: {e}")
    
    print("\n2. Waiting 3 seconds for dashboard to load...")
    time.sleep(3)
    
    print("\n3. Triggering a series of test events...")
    
    # Get interceptor
    interceptor = get_pm_hook_interceptor()
    
    # Series of test events
    test_scenarios = [
        {
            "name": "Research Task",
            "todos": [{
                "id": f"integration-test-1-{int(time.time())}",
                "content": "[Research] Integration test - research task",
                "status": "pending",
                "priority": "high"
            }]
        },
        {
            "name": "Engineering Task", 
            "todos": [{
                "id": f"integration-test-2-{int(time.time())}",
                "content": "[Engineer] Integration test - engineering task",
                "status": "in_progress",
                "priority": "high"
            }]
        },
        {
            "name": "Multiple Tasks",
            "todos": [
                {
                    "id": f"integration-test-3a-{int(time.time())}",
                    "content": "[QA] Integration test - QA task",
                    "status": "pending",
                    "priority": "medium"
                },
                {
                    "id": f"integration-test-3b-{int(time.time())}",
                    "content": "[Documentation] Integration test - documentation task", 
                    "status": "completed",
                    "priority": "low"
                }
            ]
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n   {i}. {scenario['name']} ({len(scenario['todos'])} todos)")
        success = interceptor.trigger_manual_todowrite_hooks(scenario['todos'])
        if success:
            print(f"      ✓ Events triggered successfully")
        else:
            print(f"      ❌ Events failed to trigger")
        
        # Small delay between scenarios
        time.sleep(1)
    
    print("\n4. Integration test complete!")
    print("   Check the dashboard for the test events.")
    print("   You should see hook events and todo updates in real-time.")
    
    return True


def main():
    """Run all tests."""
    print("PM Hook System Test")
    print("=" * 50)
    
    if not IMPORTS_OK:
        print("❌ Required imports failed - cannot run tests")
        return 1
    
    results = []
    
    # Test 1: PM Hook Interceptor
    results.append(("PM Hook Interceptor", test_pm_hook_interceptor()))
    
    # Test 2: Server Events
    results.append(("Server Events", test_server_events()))
    
    # Test 3: Dashboard Connectivity  
    results.append(("Dashboard Connectivity", test_dashboard_connectivity()))
    
    # Integration Test (always run for demonstration)
    print("\n" + "=" * 50)
    run_integration_test()
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results:")
    
    for i, (name, result) in enumerate(results, 1):
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{i}. {name}: {status}")
    
    all_passed = all(result for _, result in results)
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    if all_passed:
        print("\n🎉 PM Hook System is working!")
        print("   - TodoWrite operations from PM will now trigger hooks")
        print("   - Events will be visible in the Socket.IO dashboard")
        print("   - Real-time monitoring of PM operations is enabled")
    else:
        print("\n🔧 Some issues detected in PM hook system")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())