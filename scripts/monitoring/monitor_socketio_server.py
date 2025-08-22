#!/usr/bin/env python3
"""
Socket.IO Server Event Monitor

Monitors Socket.IO server emissions to verify that EventBus events
are properly reaching the Socket.IO layer and being emitted to clients.

Usage:
    python scripts/monitor_socketio_server.py [--port 8765] [--duration 60]
"""

import asyncio
import json
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
import argparse
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import socketio
    from claude_mpm.services.socketio.server.core import SocketIOServer
    from claude_mpm.services.event_bus.event_bus import EventBus
    from claude_mpm.services.events.core import Event
    print("✓ Socket.IO imports loaded successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure socketio is installed: pip install python-socketio")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SocketIOMonitor:
    """Monitor Socket.IO server for event emissions and client connections"""
    
    def __init__(self, port: int = 8765):
        self.port = port
        self.socket_server = None
        self.event_bus = None
        self.emissions_log = []
        self.connections_log = []
        self.monitoring = False
        
    async def start_monitoring(self, duration: int = 60):
        """Start monitoring Socket.IO server"""
        logger.info(f"🔍 Starting Socket.IO monitoring on port {self.port} for {duration} seconds...")
        
        try:
            # Initialize EventBus
            self.event_bus = EventBus()
            await self.event_bus.start()
            logger.info("✓ EventBus started")
            
            # Initialize Socket.IO server
            self.socket_server = SocketIOServer(port=self.port)
            await self.socket_server.start()
            logger.info(f"✓ Socket.IO server started on port {self.port}")
            
            # Set up monitoring hooks
            self._setup_monitoring_hooks()
            
            # Monitor for specified duration
            self.monitoring = True
            await self._monitor_for_duration(duration)
            
        except Exception as e:
            logger.error(f"❌ Failed to start monitoring: {e}")
            raise
        finally:
            await self._cleanup()
    
    def _setup_monitoring_hooks(self):
        """Set up hooks to monitor Socket.IO emissions and connections"""
        
        # Monitor client connections
        @self.socket_server.sio.event
        async def connect(sid):
            connection_info = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event': 'client_connected',
                'sid': sid,
                'client_count': len(self.socket_server.sio.manager.get_participants('/', '/'))
            }
            self.connections_log.append(connection_info)
            logger.info(f"🔌 Client connected: {sid}")
        
        @self.socket_server.sio.event
        async def disconnect(sid):
            connection_info = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event': 'client_disconnected',
                'sid': sid,
                'client_count': len(self.socket_server.sio.manager.get_participants('/', '/'))
            }
            self.connections_log.append(connection_info)
            logger.info(f"🔌 Client disconnected: {sid}")
        
        # Monkey patch the emit method to monitor emissions
        original_emit = self.socket_server.sio.emit
        
        async def monitored_emit(event, data=None, to=None, room=None, skip_sid=None, namespace='/', callback=None, **kwargs):
            # Log the emission
            emission_info = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_name': event,
                'data_type': type(data).__name__ if data is not None else 'None',
                'data_size': len(str(data)) if data is not None else 0,
                'to': to,
                'room': room,
                'skip_sid': skip_sid,
                'namespace': namespace
            }
            
            # Extract key data fields for analysis
            if data and isinstance(data, dict):
                emission_info['data_keys'] = list(data.keys())
                if 'type' in data:
                    emission_info['event_type'] = data['type']
                if 'subtype' in data:
                    emission_info['event_subtype'] = data['subtype']
            
            self.emissions_log.append(emission_info)
            
            # Log important events
            if event != 'ping':  # Skip ping spam
                logger.info(f"📡 Emitting '{event}' to {room or to or 'all'} ({emission_info['data_size']} chars)")
            
            # Call original emit
            return await original_emit(event, data, to, room, skip_sid, namespace, callback, **kwargs)
        
        # Replace the emit method
        self.socket_server.sio.emit = monitored_emit
    
    async def _monitor_for_duration(self, duration: int):
        """Monitor for the specified duration"""
        start_time = time.time()
        last_report = start_time
        
        while time.time() - start_time < duration and self.monitoring:
            # Report status every 10 seconds
            if time.time() - last_report >= 10:
                elapsed = int(time.time() - start_time)
                remaining = duration - elapsed
                emissions_count = len(self.emissions_log)
                connections_count = len([c for c in self.connections_log if c['event'] == 'client_connected'])
                
                logger.info(f"⏱️  Status: {elapsed}s elapsed, {remaining}s remaining | "
                          f"📡 {emissions_count} emissions | 🔌 {connections_count} clients connected")
                
                last_report = time.time()
            
            await asyncio.sleep(1)
    
    async def generate_test_event(self):
        """Generate a test event through EventBus to verify flow"""
        if self.event_bus:
            test_event = Event(
                type='test',
                subtype='monitor',
                data={
                    'message': 'Test event from SocketIO monitor',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'test_id': int(time.time())
                },
                source='socketio_monitor'
            )
            
            await self.event_bus.emit(test_event)
            logger.info("📨 Generated test event through EventBus")
    
    def generate_report(self) -> str:
        """Generate monitoring report"""
        # Count events by type
        emissions_by_event = {}
        emissions_by_type = {}
        
        for emission in self.emissions_log:
            event_name = emission['event_name']
            emissions_by_event[event_name] = emissions_by_event.get(event_name, 0) + 1
            
            if 'event_type' in emission:
                event_type = emission['event_type']
                if 'event_subtype' in emission:
                    event_type += '.' + emission['event_subtype']
                emissions_by_type[event_type] = emissions_by_type.get(event_type, 0) + 1
        
        # Count connections
        total_connections = len([c for c in self.connections_log if c['event'] == 'client_connected'])
        current_connections = sum(1 if c['event'] == 'client_connected' else -1 for c in self.connections_log)
        
        report = f"""
===============================================================================
📊 SOCKET.IO SERVER MONITORING REPORT
===============================================================================

🔌 Connection Summary:
   - Total connections during monitoring: {total_connections}
   - Current active connections: {max(0, current_connections)}
   - Connection events logged: {len(self.connections_log)}

📡 Emission Summary:
   - Total emissions: {len(self.emissions_log)}
   - Unique event names: {len(emissions_by_event)}
   - Events with type/subtype: {len(emissions_by_type)}

===============================================================================
📡 EMISSIONS BY EVENT NAME:
===============================================================================
"""
        
        for event_name, count in sorted(emissions_by_event.items(), key=lambda x: x[1], reverse=True):
            report += f"{event_name}: {count} emissions\n"
        
        if emissions_by_type:
            report += f"""
===============================================================================
📡 EMISSIONS BY EVENT TYPE:
===============================================================================
"""
            for event_type, count in sorted(emissions_by_type.items(), key=lambda x: x[1], reverse=True):
                report += f"{event_type}: {count} emissions\n"
        
        report += f"""
===============================================================================
🔍 DETAILED EMISSION LOG (Last 10):
===============================================================================
"""
        
        for emission in self.emissions_log[-10:]:
            timestamp = emission['timestamp']
            event_name = emission['event_name']
            data_info = f"{emission['data_type']} ({emission['data_size']} chars)"
            target = emission['room'] or emission['to'] or 'all'
            
            report += f"{timestamp}: {event_name} -> {target} | {data_info}\n"
            
            if 'data_keys' in emission:
                report += f"  Data keys: {emission['data_keys']}\n"
        
        report += f"""
===============================================================================
🔍 ANALYSIS:
===============================================================================

1. Event Flow Status:
"""
        
        if len(self.emissions_log) == 0:
            report += "   ❌ NO EMISSIONS DETECTED - Socket.IO server is not emitting any events\n"
        elif 'claude_event' not in emissions_by_event:
            report += "   ❌ NO 'claude_event' EMISSIONS - Dashboard expects 'claude_event' events\n"
        elif emissions_by_event.get('ping', 0) > 0 and len(emissions_by_event) == 1:
            report += "   ⚠️  ONLY PING/HEARTBEAT EVENTS - No actual data events being emitted\n"
        else:
            report += "   ✓ Event emissions detected\n"
        
        if current_connections <= 0:
            report += "   ⚠️  NO ACTIVE DASHBOARD CONNECTIONS - Open http://localhost:8765 in browser\n"
        else:
            report += f"   ✓ {current_connections} active dashboard connection(s)\n"
        
        report += f"""
2. Recommendations:
   - If no 'claude_event' emissions: Check EventBus to Socket.IO integration
   - If no dashboard connections: Open http://localhost:{self.port} in browser
   - If only heartbeat: Verify EventBus events are being generated
   - Check browser dev tools for received WebSocket messages

===============================================================================
"""
        
        return report
    
    async def _cleanup(self):
        """Clean up resources"""
        self.monitoring = False
        
        try:
            if self.socket_server:
                await self.socket_server.stop()
                logger.info("✓ Socket.IO server stopped")
        except Exception as e:
            logger.error(f"Error stopping Socket.IO server: {e}")
        
        try:
            if self.event_bus:
                await self.event_bus.stop()
                logger.info("✓ EventBus stopped")
        except Exception as e:
            logger.error(f"Error stopping EventBus: {e}")
    
    def stop_monitoring(self):
        """Stop monitoring (can be called from signal handler)"""
        self.monitoring = False

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Monitor Socket.IO server emissions')
    parser.add_argument('--port', type=int, default=8765, help='Socket.IO server port (default: 8765)')
    parser.add_argument('--duration', type=int, default=60, help='Monitoring duration in seconds (default: 60)')
    parser.add_argument('--generate-test', action='store_true', help='Generate test events during monitoring')
    
    args = parser.parse_args()
    
    print(f"""
🔍 Socket.IO Server Monitor
============================

Monitoring Socket.IO server on port {args.port} for {args.duration} seconds.
This will show what events are being emitted by the server.

Open http://localhost:{args.port} in your browser to connect the dashboard.

Press Ctrl+C to stop monitoring early.
""")
    
    monitor = SocketIOMonitor(port=args.port)
    
    try:
        # Start monitoring in background
        monitoring_task = asyncio.create_task(monitor.start_monitoring(args.duration))
        
        # Generate test events if requested
        if args.generate_test:
            async def generate_periodic_test_events():
                await asyncio.sleep(5)  # Wait for server to start
                for i in range(5):
                    await monitor.generate_test_event()
                    await asyncio.sleep(3)
            
            await asyncio.gather(
                monitoring_task,
                generate_periodic_test_events()
            )
        else:
            await monitoring_task
        
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring interrupted by user")
        monitor.stop_monitoring()
    except Exception as e:
        print(f"\n❌ Monitoring failed: {e}")
        return 1
    
    # Generate and display report
    report = monitor.generate_report()
    print(report)
    
    # Save report to file
    report_file = f"/tmp/socketio_monitor_report_{int(time.time())}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    logger.info(f"📄 Monitor report saved to: {report_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))