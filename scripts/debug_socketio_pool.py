#!/usr/bin/env python3
"""
Debug the Socket.IO connection pool to see why events aren't being sent.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def debug_connection_pool():
    """Debug the Socket.IO connection pool functionality."""
    print("🔍 Debugging Socket.IO Connection Pool")
    print("=" * 50)
    
    # Set up environment
    os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
    os.environ['CLAUDE_MPM_SOCKETIO_PORT'] = '8765'
    
    try:
        from claude_mpm.core.socketio_pool import get_connection_pool, SOCKETIO_AVAILABLE
        
        if not SOCKETIO_AVAILABLE:
            print("❌ Socket.IO packages not available")
            return False
        
        print("✅ Socket.IO packages available")
        
        # Get connection pool
        pool = get_connection_pool()
        print(f"✅ Connection pool obtained: {pool}")
        print(f"   Running: {pool._running}")
        print(f"   Pool initialized: {pool.pool_initialized}")
        
        # Check server detection
        print(f"   Server URL: {pool.server_url}")
        print(f"   Server port: {pool.server_port}")
        
        # Get initial stats
        stats = pool.get_stats()
        print(f"\n📊 Initial pool stats:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # Test direct event emission
        print(f"\n🧪 Testing direct event emission...")
        
        test_data = {
            'event_type': 'debug_test',
            'message': 'Direct pool debug test',
            'timestamp': datetime.now().isoformat(),
            'debug': True
        }
        
        # Emit event
        pool.emit_event('/hook', 'debug_test', test_data)
        print("✅ Event emitted to pool")
        
        # Wait for batch processing
        print("⏳ Waiting for batch processing...")
        time.sleep(3)
        
        # Check updated stats
        updated_stats = pool.get_stats()
        print(f"\n📊 Updated pool stats:")
        for key, value in updated_stats.items():
            print(f"   {key}: {value}")
        
        # Check connection pool internal state
        print(f"\n🔍 Pool internal state:")
        print(f"   Available connections: {len(pool.available_connections)}")
        print(f"   Active connections: {len(pool.active_connections)}")
        print(f"   Connection stats: {len(pool.connection_stats)}")
        print(f"   Batch queue size: {len(pool.batch_queue)}")
        print(f"   Batch running: {pool.batch_running}")
        print(f"   Circuit breaker state: {pool.circuit_breaker.state}")
        print(f"   Circuit breaker failures: {pool.circuit_breaker.failure_count}")
        
        # Try to manually process batch
        print(f"\n🧪 Testing manual batch processing...")
        if pool.batch_queue:
            print(f"   Found {len(pool.batch_queue)} events in queue")
            # Get the current batch
            current_batch = []
            while pool.batch_queue and len(current_batch) < 5:
                current_batch.append(pool.batch_queue.popleft())
            
            if current_batch:
                print(f"   Processing batch of {len(current_batch)} events...")
                pool._process_batch(current_batch)
                print("✅ Manual batch processing completed")
        else:
            print("   No events in batch queue")
        
        # Final stats
        final_stats = pool.get_stats()
        print(f"\n📊 Final pool stats:")
        for key, value in final_stats.items():
            print(f"   {key}: {value}")
        
        # Check if events were sent
        events_sent = final_stats.get('total_events_sent', 0)
        errors = final_stats.get('total_errors', 0)
        
        print(f"\n🎯 Results:")
        print(f"   Events sent: {events_sent}")
        print(f"   Errors: {errors}")
        print(f"   Circuit breaker: {final_stats.get('circuit_state', 'unknown')}")
        
        return events_sent > 0 and errors == 0
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        return False

def test_simple_socketio_client():
    """Test a simple Socket.IO client to verify server is working."""
    print("\n🧪 Testing simple Socket.IO client connection")
    print("=" * 50)
    
    try:
        import socketio
        
        async def test_client():
            client = socketio.AsyncClient()
            success = False
            
            @client.event
            async def connect():
                print("✅ Simple client connected successfully")
                nonlocal success
                success = True
            
            @client.event
            async def disconnect():
                print("🔌 Simple client disconnected")
            
            try:
                await client.connect('http://localhost:8765')
                await asyncio.sleep(2)
                
                # Try to emit an event
                await client.emit('test_event', {'message': 'Simple client test'})
                print("📤 Sent test event")
                
                await asyncio.sleep(1)
                await client.disconnect()
                
                return success
                
            except Exception as e:
                print(f"❌ Simple client error: {e}")
                return False
        
        # Run the async test
        result = asyncio.run(test_client())
        return result
        
    except ImportError:
        print("❌ Socket.IO not available")
        return False
    except Exception as e:
        print(f"❌ Simple client test failed: {e}")
        return False

def main():
    """Run Socket.IO pool debugging."""
    print("🔍 Socket.IO Connection Pool Debug Tool")
    print("=" * 60)
    
    # Test 1: Debug connection pool
    pool_success = debug_connection_pool()
    
    # Test 2: Simple client test
    client_success = test_simple_socketio_client()
    
    print("\n" + "=" * 60)
    print("🎯 Debug Results:")
    print(f"   Connection pool: {'✅ Working' if pool_success else '❌ Issues'}")
    print(f"   Simple client:   {'✅ Working' if client_success else '❌ Issues'}")
    
    if client_success and not pool_success:
        print("\n💡 Analysis: Socket.IO server is working, but connection pool has issues")
        print("   - Check connection pool's batch processing")
        print("   - Check circuit breaker state")
        print("   - Verify connection establishment")
    elif not client_success:
        print("\n💡 Analysis: Socket.IO server connection issues")
        print("   - Check if server is running on port 8765")
        print("   - Check server configuration")
    else:
        print("\n✅ Both tests passed - integration should be working")
    
    return pool_success and client_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)