#!/usr/bin/env python3
"""Verify EventBus relay status when Socket.IO server is running.

This script checks if the EventBus relay is properly initialized
and running when the Socket.IO server starts.
"""

import json
import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import required components
from claude_mpm.services.event_bus import EventBus, SocketIORelay
from claude_mpm.services.event_bus.config import get_config
import socketio


def check_eventbus_config():
    """Check EventBus configuration."""
    print("\n" + "="*60)
    print("1. EventBus Configuration")
    print("="*60)
    
    config = get_config()
    print(f"   EventBus enabled: {config.enabled}")
    print(f"   Relay enabled: {config.relay_enabled}")
    print(f"   Relay port: {config.relay_port}")
    print(f"   Debug mode: {config.debug}")
    
    return config.enabled and config.relay_enabled


def check_server_integration():
    """Check if Socket.IO server has EventBus integration."""
    print("\n" + "="*60)
    print("2. Socket.IO Server Integration")
    print("="*60)
    
    # Try to connect and check server status
    client = socketio.Client(logger=False, engineio_logger=False)
    
    server_info = {}
    
    @client.on('connect')
    def on_connect():
        print("✅ Connected to Socket.IO server")
        # Request server status
        client.emit('get_status')
    
    @client.on('server_status')
    def on_status(data):
        server_info.update(data)
    
    try:
        client.connect("http://localhost:8765", wait=True, wait_timeout=2)
        time.sleep(1)  # Wait for status response
        
        if server_info:
            print(f"   Server info received: {json.dumps(server_info, indent=2)}")
        else:
            print("   No server status received")
        
        client.disconnect()
        return True
    except Exception as e:
        print(f"❌ Could not connect to server: {e}")
        return False


def check_relay_instance():
    """Check if a relay instance exists and is running."""
    print("\n" + "="*60)
    print("3. EventBus Relay Instance")
    print("="*60)
    
    # Check if we can get the relay instance
    try:
        from claude_mpm.services.event_bus.relay import _relay_instance
        
        if _relay_instance:
            print("✅ Global relay instance exists")
            stats = _relay_instance.get_stats()
            print(f"   Enabled: {stats['enabled']}")
            print(f"   Connected: {stats['connected']}")
            print(f"   Events relayed: {stats['events_relayed']}")
            print(f"   Events failed: {stats['events_failed']}")
            return True
        else:
            print("❌ No global relay instance found")
            print("   The relay may not be started by the Socket.IO server")
            return False
    except ImportError:
        print("⚠️ Could not import relay module")
        return False


def test_manual_relay():
    """Test creating and using a relay manually."""
    print("\n" + "="*60)
    print("4. Manual Relay Test")
    print("="*60)
    
    # Create a relay manually
    relay = SocketIORelay(8765)
    relay.enable()
    relay.debug = True
    relay.start()
    
    print("✅ Created and started manual relay")
    
    # Get EventBus and publish a test event
    bus = EventBus.get_instance()
    bus.set_debug(True)
    
    test_event = {
        "test": "manual_relay_test",
        "timestamp": time.time()
    }
    
    print("\n   Publishing test event to EventBus...")
    bus.publish("hook.test_event", test_event)
    
    # Wait a moment
    time.sleep(1)
    
    # Check relay stats
    stats = relay.get_stats()
    print(f"\n   Relay stats after test:")
    print(f"   - Events relayed: {stats['events_relayed']}")
    print(f"   - Events failed: {stats['events_failed']}")
    print(f"   - Connected: {stats['connected']}")
    
    relay.stop()
    
    return stats['events_relayed'] > 0


def main():
    """Run all checks."""
    print("\n" + "="*80)
    print("EventBus Relay Status Verification")
    print("="*80)
    
    # Enable debug
    os.environ["CLAUDE_MPM_RELAY_DEBUG"] = "true"
    os.environ["CLAUDE_MPM_EVENTBUS_DEBUG"] = "true"
    
    # Run checks
    config_ok = check_eventbus_config()
    server_ok = check_server_integration()
    relay_exists = check_relay_instance()
    manual_ok = test_manual_relay()
    
    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    print(f"✅ EventBus config enabled: {config_ok}")
    print(f"{'✅' if server_ok else '❌'} Socket.IO server running: {server_ok}")
    print(f"{'✅' if relay_exists else '❌'} Global relay instance exists: {relay_exists}")
    print(f"{'✅' if manual_ok else '❌'} Manual relay works: {manual_ok}")
    
    if not relay_exists and server_ok:
        print("\n⚠️ ISSUE IDENTIFIED:")
        print("The Socket.IO server is running but hasn't started the EventBus relay.")
        print("This means the EventBusIntegration in the server isn't working properly.")
        print("\nPossible causes:")
        print("1. EventBusIntegration not being initialized")
        print("2. Configuration preventing relay startup")
        print("3. Error during relay initialization")


if __name__ == "__main__":
    main()