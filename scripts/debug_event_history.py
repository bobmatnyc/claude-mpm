#!/usr/bin/env python3
"""Debug script to check what's actually stored in event history."""

import asyncio
import socketio
import json

async def check_history():
    client = socketio.AsyncClient()
    
    try:
        await client.connect("http://localhost:8766")
        print("✅ Connected to server")
        
        # Request history
        history_future = asyncio.Future()
        
        @client.on("history")
        async def on_history(data):
            history_future.set_result(data)
        
        await client.emit("get_history", {"limit": 10})
        
        history_data = await asyncio.wait_for(history_future, timeout=5)
        
        print(f"\n📊 Found {history_data.get('count', 0)} events in history")
        print("\nEvent details:")
        
        for i, event in enumerate(history_data.get('events', [])[-5:], 1):
            print(f"\n{i}. Event structure:")
            print(json.dumps(event, indent=2))
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(check_history())