#!/usr/bin/env python3
"""
Test the batch processing functionality of the Socket.IO connection pool.
"""

import asyncio
import json
import os
import sys
import time
import threading
from pathlib import Path
from datetime import datetime

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def test_batch_processing():
    """Test the batch processing mechanism."""
    print("🧪 Testing Socket.IO batch processing")
    print("=" * 50)
    
    # Set up environment
    os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
    os.environ['CLAUDE_MPM_SOCKETIO_PORT'] = '8765'
    
    try:
        from claude_mpm.core.socketio_pool import get_connection_pool
        
        # Get connection pool
        pool = get_connection_pool()
        print(f"✅ Got connection pool: {pool._running}")
        
        # Check batch thread
        print(f"📊 Batch thread status: {pool.batch_thread.is_alive() if pool.batch_thread else 'None'}")
        print(f"📊 Batch running: {pool.batch_running}")
        
        # Monitor events received by server
        events_received = []
        
        try:
            import socketio
            
            async def start_monitor():
                client = socketio.AsyncClient()
                
                @client.event
                async def connect():
                    print("✅ Monitor connected to server")
                
                @client.event
                async def claude_event(data):
                    print(f"📨 Monitor received: {data.get('type', 'unknown')}")
                    events_received.append(data)
                
                try:
                    await client.connect('http://localhost:8765')
                    # Monitor for events
                    await asyncio.sleep(8)
                    await client.disconnect()
                except Exception as e:
                    print(f"Monitor error: {e}")
            
            # Start monitor in background thread
            def run_monitor():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(start_monitor())
            
            monitor_thread = threading.Thread(target=run_monitor, daemon=True)
            monitor_thread.start()
            time.sleep(1)  # Let monitor connect
            
        except ImportError:
            print("⚠️ Can't monitor - no socketio client")
            monitor_thread = None
        
        # Add several test events to trigger batch processing
        print(f"\n🧪 Adding test events to batch queue...")
        
        for i in range(3):
            test_data = {
                'event_type': f'batch_test_{i}',
                'message': f'Batch test event {i}',
                'timestamp': datetime.now().isoformat(),
                'test_id': i
            }
            
            print(f"📤 Adding event {i} to batch queue")
            pool.emit_event('/hook', f'batch_test_{i}', test_data)
            
            # Check queue size
            print(f"   Queue size after event {i}: {len(pool.batch_queue)}")
            
            time.sleep(0.5)  # Small delay between events
        
        print(f"\n⏳ Waiting for batch processing...")
        time.sleep(5)  # Wait for batch processing
        
        # Check final state
        stats = pool.get_stats()
        print(f"\n📊 Final stats:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # Wait for monitor
        if monitor_thread:
            monitor_thread.join(timeout=3)
        
        print(f"\n🎯 Results:")
        print(f"   Events added to queue: 3")
        print(f"   Events sent: {stats.get('total_events_sent', 0)}")
        print(f"   Events received by monitor: {len(events_received)}")
        print(f"   Errors: {stats.get('total_errors', 0)}")
        print(f"   Queue size: {stats.get('batch_queue_size', 0)}")
        print(f"   Circuit state: {stats.get('circuit_state', 'unknown')}")
        
        return len(events_received) > 0
        
    except Exception as e:
        print(f"❌ Batch processing test failed: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        return False

def debug_batch_thread():
    """Debug the batch processing thread."""
    print("\n🔍 Debugging batch processing thread")
    print("=" * 50)
    
    try:
        from claude_mpm.core.socketio_pool import get_connection_pool
        
        pool = get_connection_pool()
        
        print(f"📊 Batch thread info:")
        if pool.batch_thread:
            print(f"   Thread alive: {pool.batch_thread.is_alive()}")
            print(f"   Thread name: {pool.batch_thread.name}")
            print(f"   Thread daemon: {pool.batch_thread.daemon}")
        else:
            print(f"   No batch thread!")
        
        print(f"   Batch running flag: {pool.batch_running}")
        print(f"   Pool running flag: {pool._running}")
        print(f"   Batch window: {pool.batch_window_ms}ms")
        
        # Check if batch processor is actually working by manually calling it
        print(f"\n🧪 Testing batch processor method directly...")
        
        # Add a test event
        from claude_mpm.core.socketio_pool import BatchEvent
        test_event = BatchEvent(
            namespace='/hook',
            event='debug_test',
            data={'message': 'Direct batch test', 'timestamp': datetime.now().isoformat()}
        )
        
        pool.batch_queue.append(test_event)
        print(f"   Added test event to queue (size: {len(pool.batch_queue)})")
        
        # Manually process batch
        current_batch = [pool.batch_queue.popleft()] if pool.batch_queue else []
        if current_batch:
            print(f"   Processing batch of {len(current_batch)} events...")
            pool._process_batch(current_batch)
            print(f"   Batch processing completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Batch thread debug failed: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        return False

def main():
    """Run batch processing tests."""
    print("🧪 Socket.IO Batch Processing Debug")
    print("=" * 60)
    
    # Test 1: Normal batch processing
    batch_success = test_batch_processing()
    
    # Test 2: Debug batch thread
    thread_success = debug_batch_thread()
    
    print("\n" + "=" * 60)
    print("🎯 Debug Results:")
    print(f"   Batch processing: {'✅ Working' if batch_success else '❌ Issues'}")
    print(f"   Thread debugging: {'✅ Working' if thread_success else '❌ Issues'}")
    
    if not batch_success:
        print("\n💡 Batch processing issues detected:")
        print("   - Events may not be reaching the Socket.IO server")
        print("   - Check batch thread lifecycle")
        print("   - Check connection establishment")
        print("   - Check event emission logic")
    
    return batch_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)