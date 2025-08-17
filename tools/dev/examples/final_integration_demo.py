#!/usr/bin/env python3
"""Final integration demo showing the complete PM hook system working."""

import sys
import time
import webbrowser
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from claude_mpm.core.pm_hook_interceptor import trigger_pm_todowrite_hooks
    from claude_mpm.services.websocket_server import get_server_instance
    IMPORTS_OK = True
except ImportError as e:
    print(f"Import error: {e}")
    IMPORTS_OK = False


def demonstrate_pm_hook_system():
    """Demonstrate the complete PM hook system working."""
    print("🚀 Claude MPM PM Hook System Integration Demo")
    print("=" * 60)
    
    if not IMPORTS_OK:
        print("❌ Required imports not available")
        return False
    
    # Get server instance
    try:
        server = get_server_instance()
        print("✓ Socket.IO server instance obtained")
    except Exception as e:
        print(f"❌ Could not get server instance: {e}")
        return False
    
    # Open dashboard
    dashboard_url = "http://localhost:8765/dashboard?autoconnect=true&port=8765"
    print(f"\n📊 Opening Socket.IO dashboard...")
    print(f"   URL: {dashboard_url}")
    
    try:
        webbrowser.open(dashboard_url)
        print("✓ Dashboard opened in browser")
    except Exception as e:
        print(f"⚠️  Could not open browser: {e}")
        print(f"   Please manually open: {dashboard_url}")
    
    print("\n⏳ Waiting 5 seconds for dashboard to load and connect...")
    time.sleep(5)
    
    # Demonstrate different types of events
    print("\n🎯 Demonstrating PM Hook System Events:")
    print("   (Watch the dashboard for real-time events)")
    
    # 1. Direct server events
    print("\n1. 📤 Direct Server Events")
    server.emit_event('/system', 'status', {
        'message': 'Demo started',
        'source': 'integration_demo',
        'timestamp': time.time()
    })
    
    server.emit_event('/session', 'start', {
        'session_id': 'demo-session-123',
        'start_time': time.time(),
        'launch_method': 'demo',
        'working_directory': str(Path.cwd())
    })
    print("   ✓ Emitted system status and session start events")
    time.sleep(2)
    
    # 2. PM TodoWrite hook events
    print("\n2. 📝 PM TodoWrite Hook Events")
    
    demo_todos = [
        {
            "id": f"demo-todo-1-{int(time.time())}",
            "content": "[Research] Demo: Investigate new feature requirements",
            "status": "pending",
            "priority": "high"
        },
        {
            "id": f"demo-todo-2-{int(time.time())}",
            "content": "[Engineer] Demo: Implement the new feature",
            "status": "in_progress", 
            "priority": "high"
        },
        {
            "id": f"demo-todo-3-{int(time.time())}",
            "content": "[QA] Demo: Test the new feature thoroughly",
            "status": "pending",
            "priority": "medium"
        }
    ]
    
    success = trigger_pm_todowrite_hooks(demo_todos)
    if success:
        print(f"   ✓ Triggered PM TodoWrite hooks for {len(demo_todos)} todos")
    else:
        print(f"   ⚠️  PM TodoWrite hooks may not have triggered properly")
    
    time.sleep(2)
    
    # 3. Todo update events
    print("\n3. 📋 Todo Update Events")
    server.emit_event('/todo', 'updated', {
        'todos': demo_todos,
        'stats': {
            'total': len(demo_todos),
            'pending': sum(1 for t in demo_todos if t['status'] == 'pending'),
            'in_progress': sum(1 for t in demo_todos if t['status'] == 'in_progress'),
            'completed': sum(1 for t in demo_todos if t['status'] == 'completed')
        },
        'source': 'PM_demo'
    })
    print("   ✓ Emitted todo update event")
    time.sleep(2)
    
    # 4. Agent delegation events
    print("\n4. 🤖 Agent Delegation Events")
    server.emit_event('/agent', 'task_delegated', {
        'agent': 'Research',
        'task': 'Investigate new feature requirements',
        'status': 'started',
        'source': 'PM_demo'
    })
    
    server.emit_event('/agent', 'task_delegated', {
        'agent': 'Engineer', 
        'task': 'Implement the new feature',
        'status': 'in_progress',
        'source': 'PM_demo'
    })
    print("   ✓ Emitted agent delegation events")
    time.sleep(2)
    
    # 5. Memory system events
    print("\n5. 🧠 Memory System Events")
    server.emit_event('/memory', 'updated', {
        'agent_id': 'PM',
        'learning_type': 'pattern_recognition',
        'content': 'TodoWrite operations from PM now trigger consistent hook events',
        'section': 'pm_operations'
    })
    print("   ✓ Emitted memory system event")
    time.sleep(2)
    
    # 6. Session end
    print("\n6. 🏁 Session End Events")
    server.emit_event('/session', 'end', {
        'session_id': 'demo-session-123',
        'end_time': time.time(),
        'duration_seconds': 30
    })
    print("   ✓ Emitted session end event")
    
    print("\n🎉 Integration Demo Complete!")
    print("\nWhat you should see in the dashboard:")
    print("   • System status events")
    print("   • Session start/end events") 
    print("   • Hook events (pre_tool, post_tool)")
    print("   • Todo updates with statistics")
    print("   • Agent delegation events")
    print("   • Memory system updates")
    
    print(f"\n📊 Dashboard URL: {dashboard_url}")
    print("\nThe PM hook system is now fully operational! 🚀")
    
    return True


def main():
    """Run the integration demo."""
    return 0 if demonstrate_pm_hook_system() else 1


if __name__ == "__main__":
    sys.exit(main())