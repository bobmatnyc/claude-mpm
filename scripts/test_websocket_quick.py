#!/usr/bin/env python3
"""Quick WebSocket connection test."""

import asyncio
import json
import websockets

async def quick_test():
    """Quick test to verify WebSocket server is running."""
    uri = "ws://localhost:8765"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✓ Connected to {uri}")
            
            # Get status
            await websocket.send(json.dumps({"command": "get_status"}))
            response = await websocket.recv()
            status = json.loads(response)
            
            print(f"✓ Server responded with status: {status['type']}")
            print(f"  Claude status: {status['data']['claude_status']}")
            print(f"  Session ID: {status['data']['session_id']}")
            
            return True
            
    except ConnectionRefusedError:
        print(f"✗ Could not connect to {uri}")
        print("  Make sure claude-mpm is running with --websocket flag")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(quick_test())
    exit(0 if success else 1)