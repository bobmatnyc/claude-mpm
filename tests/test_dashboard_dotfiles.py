#!/usr/bin/env python3
"""Test dashboard dotfile filtering issue"""

import asyncio
import json
import time
from pathlib import Path

import socketio

async def test_dashboard_discovery():
    """Test that frontend sends correct show_hidden_files value"""
    
    # Create a Socket.IO client
    sio = socketio.AsyncClient()
    
    received_data = []
    
    @sio.on('code:top_level:discovered')
    async def on_discovery(data):
        print(f"\n=== RECEIVED DISCOVERY RESPONSE ===")
        print(f"Request ID: {data.get('request_id')}")
        print(f"Path: {data.get('path')}")
        items = data.get('items', [])
        dotfiles = [item for item in items if item.get('name', '').startswith('.')]
        print(f"Total items: {len(items)}")
        print(f"Dotfiles found: {len(dotfiles)}")
        if dotfiles:
            print(f"Dotfile names: {[d.get('name') for d in dotfiles]}")
        received_data.append(data)
    
    @sio.on('connect')
    async def on_connect():
        print("Connected to dashboard Socket.IO server")
    
    @sio.on('disconnect')
    async def on_disconnect():
        print("Disconnected from server")
    
    try:
        # Connect to the server
        print("Connecting to http://localhost:5000...")
        await sio.connect('http://localhost:5000')
        
        # Wait a moment for connection to establish
        await asyncio.sleep(1)
        
        # Send discovery request with show_hidden_files=False (default)
        request_data = {
            'path': str(Path.cwd()),
            'ignore_patterns': [],
            'request_id': 'test-false-123',
            'show_hidden_files': False
        }
        
        print(f"\n=== SENDING REQUEST WITH show_hidden_files=False ===")
        print(f"Request data: {json.dumps(request_data, indent=2)}")
        
        await sio.emit('code:discover:top_level', request_data)
        
        # Wait for response
        await asyncio.sleep(2)
        
        # Now test with show_hidden_files=True
        request_data2 = {
            'path': str(Path.cwd()),
            'ignore_patterns': [],
            'request_id': 'test-true-456',
            'show_hidden_files': True
        }
        
        print(f"\n=== SENDING REQUEST WITH show_hidden_files=True ===")
        print(f"Request data: {json.dumps(request_data2, indent=2)}")
        
        await sio.emit('code:discover:top_level', request_data2)
        
        # Wait for response
        await asyncio.sleep(2)
        
        # Disconnect
        await sio.disconnect()
        
        # Analyze results
        print(f"\n\n=== SUMMARY ===")
        print(f"Received {len(received_data)} responses")
        
        for response in received_data:
            rid = response.get('request_id', 'unknown')
            items = response.get('items', [])
            dotfiles = [item for item in items if item.get('name', '').startswith('.')]
            if 'false' in rid:
                print(f"\nWith show_hidden_files=False:")
                print(f"  - {len(dotfiles)} dotfiles (should be 0)")
                if dotfiles:
                    print(f"  - ERROR: Dotfiles found when they shouldn't be: {[d.get('name') for d in dotfiles]}")
            elif 'true' in rid:
                print(f"\nWith show_hidden_files=True:")
                print(f"  - {len(dotfiles)} dotfiles (should be >0)")
                if not dotfiles:
                    print(f"  - ERROR: No dotfiles found when they should be visible")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if sio.connected:
            await sio.disconnect()

if __name__ == "__main__":
    # First, make sure the dashboard is running
    print("Make sure the dashboard is running: ./scripts/claude-mpm dashboard")
    print("Starting test in 3 seconds...")
    time.sleep(3)
    
    asyncio.run(test_dashboard_discovery())