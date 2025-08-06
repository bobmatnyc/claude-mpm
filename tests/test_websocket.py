#!/usr/bin/env python3
"""Test WebSocket server integration."""

import asyncio
import json
import websockets
import sys
import time

async def test_websocket_client():
    """Connect to WebSocket server and listen for events."""
    uri = "ws://localhost:8765"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            
            # Subscribe to all events
            await websocket.send(json.dumps({
                "command": "subscribe",
                "channels": ["*"]
            }))
            
            # Listen for events
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    event = json.loads(message)
                    
                    # Pretty print the event
                    event_type = event.get("type", "unknown")
                    timestamp = event.get("timestamp", "")
                    data = event.get("data", {})
                    
                    print(f"\n[{timestamp}] {event_type}")
                    if event_type == "claude.output":
                        # Special handling for output to make it readable
                        content = data.get("content", "")
                        stream = data.get("stream", "stdout")
                        print(f"  [{stream}] {repr(content[:100])}")
                    else:
                        for key, value in data.items():
                            print(f"  {key}: {value}")
                            
                except asyncio.TimeoutError:
                    # No message received, continue
                    pass
                except websockets.exceptions.ConnectionClosed:
                    print("\nConnection closed")
                    break
                    
    except ConnectionRefusedError:
        print(f"Could not connect to {uri}")
        print("Make sure claude-mpm is running with --monitor flag")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted")
    except Exception as e:
        print(f"Error: {e}")
        
if __name__ == "__main__":
    print("WebSocket test client - Connecting to claude-mpm WebSocket server")
    print("Run this while claude-mpm is active with --monitor flag")
    print("Press Ctrl+C to stop\n")
    
    asyncio.run(test_websocket_client())