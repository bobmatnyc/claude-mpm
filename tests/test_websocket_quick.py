#!/usr/bin/env python3
"""Quick WebSocket connection test."""

import asyncio
import json
import sys
import websockets

async def quick_test(port=8765):
    """Quick test to verify WebSocket server is running."""
    uri = f"ws://localhost:{port}"
    
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
            print(f"  Instance port: {status['data'].get('websocket_port', 'unknown')}")
            
            return True
            
    except ConnectionRefusedError:
        print(f"✗ Could not connect to {uri}")
        print("  Make sure claude-mpm is running with --monitor flag")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    success = asyncio.run(quick_test(port))
    exit(0 if success else 1)