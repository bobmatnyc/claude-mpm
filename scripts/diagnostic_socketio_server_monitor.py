#!/usr/bin/env python3
"""Socket.IO Server-Side Event Monitoring Diagnostic.

This script starts a Socket.IO server with enhanced logging to monitor:
1. All incoming connections and their namespaces
2. All events being emitted to clients
3. Client authentication attempts
4. Event broadcast success/failure

WHY this diagnostic:
- Identifies if the server is receiving hook handler connections
- Shows exactly what events are being emitted and to which namespaces
- Reveals any authentication or connection issues
- Provides detailed timing information
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any

try:
    import socketio
    from aiohttp import web
    SOCKETIO_AVAILABLE = True
except ImportError:
    print("ERROR: python-socketio package not installed. Run: pip install python-socketio[asyncio_client] aiohttp")
    sys.exit(1)


class DiagnosticSocketIOServer:
    """Enhanced Socket.IO server with comprehensive event monitoring."""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.start_time = datetime.now()
        self.connection_count = 0
        self.event_count = 0
        self.namespace_connections = {}
        
        print(f"🔍 DIAGNOSTIC: Starting Socket.IO server monitor on {host}:{port}")
        print(f"📅 Start time: {self.start_time.isoformat()}")
        print("=" * 80)
        
        # Create Socket.IO server with diagnostic settings
        self.sio = socketio.AsyncServer(
            cors_allowed_origins="*",
            async_mode='aiohttp',
            ping_timeout=60,
            ping_interval=25,
            logger=True,  # Enable Socket.IO internal logging
            engineio_logger=True
        )
        
        # Create aiohttp app
        self.app = web.Application()
        self.sio.attach(self.app)
        
        self._setup_diagnostic_handlers()
        self._setup_routes()
    
    def _setup_diagnostic_handlers(self):
        """Setup diagnostic event handlers for all namespaces."""
        
        namespaces = ['/system', '/session', '/claude', '/agent', '/hook', '/todo', '/memory', '/log']
        
        for namespace in namespaces:
            self._setup_namespace_handlers(namespace)
        
        # Setup default namespace handlers too
        @self.sio.event
        async def connect(sid, environ, auth):
            self.connection_count += 1
            timestamp = datetime.now().isoformat()
            print(f"🔗 CONNECTION [DEFAULT]: {sid} at {timestamp}")
            print(f"   Auth: {auth}")
            print(f"   Environ keys: {list(environ.keys())}")
            print(f"   Total connections: {self.connection_count}")
            return True
        
        @self.sio.event
        async def disconnect(sid):
            timestamp = datetime.now().isoformat()
            print(f"❌ DISCONNECT [DEFAULT]: {sid} at {timestamp}")
    
    def _setup_namespace_handlers(self, namespace: str):
        """Setup diagnostic handlers for a specific namespace."""
        
        @self.sio.event(namespace=namespace)
        async def connect(sid, environ, auth):
            self.connection_count += 1
            if namespace not in self.namespace_connections:
                self.namespace_connections[namespace] = []
            self.namespace_connections[namespace].append(sid)
            
            timestamp = datetime.now().isoformat()
            print(f"🔗 CONNECTION [{namespace}]: {sid} at {timestamp}")
            print(f"   Auth provided: {bool(auth)}")
            if auth:
                print(f"   Auth data: {auth}")
            print(f"   Namespace connections: {len(self.namespace_connections[namespace])}")
            print(f"   Total connections: {self.connection_count}")
            
            # Join default room for this namespace
            room_name = f"{namespace.lstrip('/')}_room"
            await self.sio.enter_room(sid, room_name, namespace=namespace)
            print(f"   Joined room: {room_name}")
            
            return True
        
        @self.sio.event(namespace=namespace)
        async def disconnect(sid):
            if namespace in self.namespace_connections:
                if sid in self.namespace_connections[namespace]:
                    self.namespace_connections[namespace].remove(sid)
            
            timestamp = datetime.now().isoformat()
            print(f"❌ DISCONNECT [{namespace}]: {sid} at {timestamp}")
            remaining = len(self.namespace_connections.get(namespace, []))
            print(f"   Remaining in namespace: {remaining}")
    
    def _setup_routes(self):
        """Setup diagnostic HTTP routes."""
        
        async def diagnostic_status(request):
            """Diagnostic status endpoint with detailed information."""
            uptime_seconds = (datetime.now() - self.start_time).total_seconds()
            
            status = {
                "server": "diagnostic-socketio-monitor",
                "status": "running",
                "start_time": self.start_time.isoformat(),
                "uptime_seconds": uptime_seconds,
                "total_connections": self.connection_count,
                "total_events_emitted": self.event_count,
                "namespace_connections": {
                    ns: len(clients) 
                    for ns, clients in self.namespace_connections.items()
                },
                "host": self.host,
                "port": self.port,
                "timestamp": datetime.now().isoformat()
            }
            return web.json_response(status)
        
        async def emit_test_event(request):
            """Test endpoint to emit events to all namespaces."""
            test_data = {
                "message": "Diagnostic test event",
                "timestamp": datetime.now().isoformat(),
                "test_id": f"test_{int(time.time())}"
            }
            
            results = {}
            namespaces = ['/system', '/session', '/claude', '/agent', '/hook', '/todo', '/memory', '/log']
            
            for namespace in namespaces:
                try:
                    room_name = f"{namespace.lstrip('/')}_room"
                    await self.sio.emit('diagnostic_test', test_data, room=room_name, namespace=namespace)
                    self.event_count += 1
                    results[namespace] = "success"
                    print(f"📤 TEST EVENT EMITTED: {namespace}/diagnostic_test")
                    print(f"   Data: {test_data}")
                    print(f"   Room: {room_name}")
                except Exception as e:
                    results[namespace] = f"error: {e}"
                    print(f"❌ TEST EVENT FAILED: {namespace}/diagnostic_test - {e}")
            
            return web.json_response({
                "status": "test_events_sent",
                "results": results,
                "data": test_data
            })
        
        self.app.router.add_get('/diagnostic/status', diagnostic_status)
        self.app.router.add_post('/diagnostic/test-event', emit_test_event)
        self.app.router.add_get('/diagnostic/test-event', emit_test_event)  # Allow GET for browser testing
    
    async def emit_diagnostic_event(self, namespace: str, event: str, data: Dict[str, Any]):
        """Emit event with diagnostic logging."""
        self.event_count += 1
        timestamp = datetime.now().isoformat()
        
        print(f"📤 EMITTING EVENT: {namespace}/{event} at {timestamp}")
        print(f"   Data: {json.dumps(data, indent=2)[:300]}...")
        
        try:
            room_name = f"{namespace.lstrip('/')}_room"
            await self.sio.emit(event, data, room=room_name, namespace=namespace)
            print(f"   ✅ Successfully emitted to room: {room_name}")
        except Exception as e:
            print(f"   ❌ Failed to emit: {e}")
    
    def run(self):
        """Run the diagnostic server."""
        print(f"🚀 Starting diagnostic Socket.IO server on {self.host}:{self.port}")
        print("📊 Monitor output will show all connections and events")
        print("🌐 Access diagnostic status: http://localhost:8765/diagnostic/status")
        print("🧪 Test events: http://localhost:8765/diagnostic/test-event")
        print("=" * 80)
        
        try:
            web.run_app(
                self.app,
                host=self.host,
                port=self.port,
                access_log=None
            )
        except KeyboardInterrupt:
            print("\n🛑 Diagnostic server stopped by user")
        except Exception as e:
            print(f"❌ Diagnostic server error: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main diagnostic entry point."""
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8765
    
    server = DiagnosticSocketIOServer(port=port)
    server.run()


if __name__ == "__main__":
    main()