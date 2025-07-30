#!/usr/bin/env python3
"""Test script to verify WebSocket memory events are working correctly."""

import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.websocket_server import get_websocket_server
from claude_mpm.services.agent_memory_manager import AgentMemoryManager
from claude_mpm.hooks.memory_integration_hook import MemoryPreDelegationHook
from claude_mpm.hooks.base_hook import HookContext, HookType
from claude_mpm.core.config import Config


async def test_memory_websocket_events():
    """Test that memory operations emit proper WebSocket events."""
    print("🧪 Testing Memory WebSocket Events\n")
    
    # Start WebSocket server
    ws_server = get_websocket_server()
    ws_server.start()  # This starts in a separate thread
    await asyncio.sleep(1.0)  # Give server time to start
    print("✅ WebSocket server started on port 8765")
    
    # Create config with memory enabled
    config = Config(config={
        'memory': {
            'enabled': True,
            'auto_learning': True,
            'limits': {
                'default_size_kb': 8,
                'max_sections': 10,
                'max_items_per_section': 15
            }
        }
    })
    
    # Create memory manager
    memory_manager = AgentMemoryManager(config)
    print("✅ Memory manager created")
    
    # Test 1: Load agent memory (will create if doesn't exist)
    print("\n📝 Test 1: Loading agent memory...")
    memory_content = memory_manager.load_agent_memory("test_websocket")
    print(f"   Memory loaded, size: {len(memory_content)} bytes")
    
    # Test 2: Add a learning
    print("\n📝 Test 2: Adding a learning...")
    success = memory_manager.add_learning(
        "test_websocket",
        "pattern",
        "WebSocket events track memory operations"
    )
    print(f"   Learning added: {success}")
    
    # Test 3: Memory injection via hook
    print("\n📝 Test 3: Testing memory injection hook...")
    pre_hook = MemoryPreDelegationHook(config)
    context = HookContext(
        hook_type=HookType.PRE_DELEGATION,
        data={
            'agent': 'test_websocket',
            'prompt': 'Test prompt',
            'session_id': 'test-ws-123'
        },
        metadata={},
        timestamp=None
    )
    result = pre_hook.execute(context)
    print(f"   Memory injected: {result.success}")
    
    # Wait a bit for events to be processed
    await asyncio.sleep(0.5)
    
    # Check event history
    print("\n📊 WebSocket Event History:")
    events = list(ws_server.event_history)  # Access the deque directly
    memory_events = [e for e in events if e['type'].startswith('memory:')]
    
    if memory_events:
        print(f"   Found {len(memory_events)} memory events:")
        for event in memory_events:
            print(f"   - {event['type']}: {json.dumps(event['data'], indent=6)}")
    else:
        print("   ❌ No memory events found!")
    
    # Stop WebSocket server
    print("\n🛑 Stopping WebSocket server...")
    ws_server.stop()
    
    print("✅ Test complete!")


async def monitor_memory_events():
    """Simple monitor to display memory events in real-time."""
    import websockets
    
    print("📡 Connecting to WebSocket server...")
    print("   Monitoring memory events (Ctrl+C to stop)\n")
    
    try:
        async with websockets.connect("ws://localhost:8765") as websocket:
            while True:
                message = await websocket.recv()
                event = json.loads(message)
                
                if event['type'].startswith('memory:'):
                    timestamp = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                    print(f"[{timestamp.strftime('%H:%M:%S')}] {event['type']}")
                    for key, value in event['data'].items():
                        print(f"         {key}: {value}")
                    print()
    except KeyboardInterrupt:
        print("\n✅ Monitoring stopped")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Memory WebSocket Events")
    parser.add_argument(
        "--monitor", 
        action="store_true", 
        help="Monitor memory events in real-time"
    )
    args = parser.parse_args()
    
    if args.monitor:
        asyncio.run(monitor_memory_events())
    else:
        asyncio.run(test_memory_websocket_events())


if __name__ == "__main__":
    main()