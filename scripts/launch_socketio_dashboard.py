#!/usr/bin/env python3
"""Socket.IO Dashboard Launcher for Claude MPM.

WHY: This script provides a streamlined solution for launching the Socket.IO
monitoring dashboard using only the Python Socket.IO server implementation.
It handles server startup, dashboard creation, and browser opening.

DESIGN DECISION: Uses only python-socketio and aiohttp for a clean,
Node.js-free implementation. This simplifies deployment and reduces
dependencies while maintaining full functionality.

The script handles:
1. Python Socket.IO server startup
2. Dashboard HTML creation and serving
3. Browser opening with proper URL construction
4. Background/daemon mode operation
5. Graceful error handling and user feedback
"""

import argparse
import os
import sys
import time
import webbrowser
import signal
from pathlib import Path
from typing import Optional

# Get script directory for relative paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

def check_python_dependencies() -> bool:
    """Check if Python Socket.IO dependencies are available.
    
    WHY: We need python-socketio and aiohttp packages for the server.
    This function validates the environment and provides clear feedback.
    
    Returns:
        bool: True if Python dependencies are ready, False otherwise
    """
    try:
        import socketio
        import aiohttp
        socketio_version = getattr(socketio, '__version__', 'unknown')
        aiohttp_version = getattr(aiohttp, '__version__', 'unknown')
        print(f"✓ python-socketio v{socketio_version} detected")
        print(f"✓ aiohttp v{aiohttp_version} detected")
        return True
    except ImportError as e:
        print(f"❌ Required Python packages missing: {e}")
        print("   Install with: pip install python-socketio aiohttp")
        return False



def create_dashboard_html(port: int):
    """Create the Socket.IO dashboard HTML file.
    
    WHY: The dashboard provides a comprehensive web interface for monitoring
    Claude MPM sessions in real-time. It includes event filtering, search,
    metrics, and export capabilities.
    
    Args:
        port: Port number for the Socket.IO server
    """
    dashboard_html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude MPM Socket.IO Dashboard</title>
    <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }}
        
        .header h1 {{
            color: #4a5568;
            margin-bottom: 10px;
            font-size: 28px;
        }}
        
        .status-bar {{
            display: flex;
            gap: 20px;
            align-items: center;
            flex-wrap: wrap;
            margin-top: 15px;
        }}
        
        .status-item {{
            background: #f7fafc;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            border-left: 4px solid #4299e1;
        }}
        
        .status-connected {{
            border-left-color: #48bb78;
        }}
        
        .status-disconnected {{
            border-left-color: #f56565;
        }}
        
        .controls {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }}
        
        .control-group {{
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
            margin-bottom: 15px;
        }}
        
        .control-group:last-child {{
            margin-bottom: 0;
        }}
        
        .control-group label {{
            font-weight: 600;
            color: #4a5568;
            min-width: 100px;
        }}
        
        input, select, button {{
            padding: 8px 12px;
            border: 2px solid #e2e8f0;
            border-radius: 6px;
            font-size: 14px;
            transition: all 0.2s;
        }}
        
        input:focus, select:focus {{
            outline: none;
            border-color: #4299e1;
            box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.1);
        }}
        
        button {{
            background: #4299e1;
            color: white;
            border: none;
            cursor: pointer;
            font-weight: 600;
            padding: 10px 20px;
        }}
        
        button:hover {{
            background: #3182ce;
            transform: translateY(-1px);
        }}
        
        button:active {{
            transform: translateY(0);
        }}
        
        .btn-secondary {{
            background: #718096;
        }}
        
        .btn-secondary:hover {{
            background: #4a5568;
        }}
        
        .btn-success {{
            background: #48bb78;
        }}
        
        .btn-success:hover {{
            background: #38a169;
        }}
        
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .metric-card {{
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        }}
        
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            color: #4299e1;
            margin-bottom: 5px;
        }}
        
        .metric-label {{
            color: #718096;
            font-size: 14px;
        }}
        
        .events-container {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            height: 600px;
            display: flex;
            flex-direction: column;
        }}
        
        .events-header {{
            display: flex;
            justify-content: between;
            align-items: center;
            margin-bottom: 15px;
            flex-wrap: wrap;
            gap: 10px;
        }}
        
        .events-list {{
            flex: 1;
            overflow-y: auto;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 10px;
            background: #f8f9fa;
        }}
        
        .event-item {{
            background: white;
            border-radius: 6px;
            padding: 12px;
            margin-bottom: 8px;
            border-left: 4px solid #4299e1;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .event-item:hover {{
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            transform: translateX(2px);
        }}
        
        .event-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;
        }}
        
        .event-type {{
            font-weight: 600;
            color: #2d3748;
        }}
        
        .event-timestamp {{
            font-size: 12px;
            color: #718096;
        }}
        
        .event-data {{
            font-size: 14px;
            color: #4a5568;
            margin-top: 5px;
        }}
        
        .event-session {{
            background: white;
            border-left-color: #48bb78;
        }}
        
        .event-claude {{
            background: white;
            border-left-color: #ed8936;
        }}
        
        .event-agent {{
            background: white;
            border-left-color: #9f7aea;
        }}
        
        .event-hook {{
            background: white;
            border-left-color: #38b2ac;
        }}
        
        .event-todo {{
            background: white;
            border-left-color: #e53e3e;
        }}
        
        .event-memory {{
            background: white;
            border-left-color: #d69e2e;
        }}
        
        .event-log {{
            background: white;
            border-left-color: #718096;
        }}
        
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
        }}
        
        .modal-content {{
            background-color: white;
            margin: 5% auto;
            padding: 20px;
            border-radius: 12px;
            width: 80%;
            max-width: 800px;
            max-height: 80%;
            overflow-y: auto;
        }}
        
        .close {{
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }}
        
        .close:hover {{
            color: #000;
        }}
        
        pre {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            font-size: 12px;
            line-height: 1.4;
        }}
        
        .no-events {{
            text-align: center;
            color: #718096;
            padding: 40px;
            font-style: italic;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            
            .control-group {{
                flex-direction: column;
                align-items: stretch;
            }}
            
            .control-group label {{
                min-width: auto;
            }}
            
            .metrics {{
                grid-template-columns: 1fr;
            }}
            
            .modal-content {{
                width: 95%;
                margin: 10% auto;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Claude MPM Socket.IO Dashboard</h1>
            <p>Real-time monitoring of Claude MPM sessions and events</p>
            <div class="status-bar">
                <div id="connection-status" class="status-item status-disconnected">
                    🔴 Disconnected
                </div>
                <div id="socket-id" class="status-item">
                    Socket ID: Not connected
                </div>
                <div id="server-info" class="status-item">
                    Server: Not connected
                </div>
            </div>
        </div>
        
        <div class="controls">
            <div class="control-group">
                <label>Connection:</label>
                <button id="connect-btn" onclick="connectSocket()">Connect</button>
                <button id="disconnect-btn" onclick="disconnectSocket()" class="btn-secondary">Disconnect</button>
                <input type="text" id="port-input" value="{port}" placeholder="Port" style="width: 80px;">
            </div>
            <div class="control-group">
                <label>Filters:</label>
                <input type="text" id="search-input" placeholder="Search events..." style="width: 200px;">
                <select id="event-type-filter">
                    <option value="">All Events</option>
                    <option value="session">Session</option>
                    <option value="claude">Claude</option>
                    <option value="agent">Agent</option>
                    <option value="hook">Hook</option>
                    <option value="todo">Todo</option>
                    <option value="memory">Memory</option>
                    <option value="log">Log</option>
                </select>
                <button onclick="clearEvents()" class="btn-secondary">Clear Events</button>
                <button onclick="exportEvents()" class="btn-success">Export JSON</button>
            </div>
        </div>
        
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value" id="total-events">0</div>
                <div class="metric-label">Total Events</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="events-per-minute">0</div>
                <div class="metric-label">Events/Min</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="unique-types">0</div>
                <div class="metric-label">Event Types</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="error-count">0</div>
                <div class="metric-label">Errors</div>
            </div>
        </div>
        
        <div class="events-container">
            <div class="events-header">
                <h3>📊 Live Events</h3>
                <div>
                    <button onclick="requestHistory()" class="btn-secondary">Load History</button>
                    <button onclick="toggleAutoScroll()" id="autoscroll-btn" class="btn-secondary">Auto-scroll: ON</button>
                </div>
            </div>
            <div class="events-list" id="events-list">
                <div class="no-events">
                    Connect to Socket.IO server to see events...
                </div>
            </div>
        </div>
    </div>
    
    <!-- Event Detail Modal -->
    <div id="event-modal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <h2>Event Details</h2>
            <div id="event-detail-content"></div>
        </div>
    </div>
    
    <script>
        // Global state
        let socket = null;
        let events = [];
        let filteredEvents = [];
        let autoScroll = true;
        let eventTypeCount = {{}};
        let errorCount = 0;
        let eventsThisMinute = 0;
        let lastMinute = new Date().getMinutes();
        
        // Initialize from URL params
        const urlParams = new URLSearchParams(window.location.search);
        const defaultPort = urlParams.get('port') || '{port}';
        const autoConnect = urlParams.get('autoconnect') === 'true';
        
        document.getElementById('port-input').value = defaultPort;
        
        if (autoConnect) {{
            connectSocket();
        }}
        
        function connectSocket() {{
            const port = document.getElementById('port-input').value || defaultPort;
            const url = `http://localhost:${{port}}`;
            
            if (socket && socket.connected) {{
                socket.disconnect();
            }}
            
            console.log(`Connecting to Socket.IO server at ${{url}}`);
            
            socket = io(url, {{
                autoConnect: true,
                reconnection: true,
                reconnectionDelay: 1000,
                reconnectionDelayMax: 5000,
                maxReconnectionAttempts: 5
            }});
            
            socket.on('connect', () => {{
                console.log('Connected to Socket.IO server');
                updateConnectionStatus('Connected', 'connected');
                document.getElementById('socket-id').textContent = `Socket ID: ${{socket.id}}`;
                requestStatus();
            }});
            
            socket.on('disconnect', (reason) => {{
                console.log('Disconnected from server:', reason);
                updateConnectionStatus('Disconnected', 'disconnected');
                document.getElementById('socket-id').textContent = 'Socket ID: Not connected';
            }});
            
            socket.on('connect_error', (error) => {{
                console.error('Connection error:', error);
                updateConnectionStatus('Connection Error', 'disconnected');
            }});
            
            socket.on('status', (data) => {{
                console.log('Server status:', data);
                document.getElementById('server-info').textContent = 
                    `Server: ${{data.server || 'Unknown'}} (${{data.clients_connected || 0}} clients)`;
            }});
            
            socket.on('claude_event', (eventData) => {{
                console.log('Received event:', eventData);
                addEvent(eventData);
            }});
            
            socket.on('history', (data) => {{
                console.log('Received history:', data.events.length, 'events');
                if (data.events && data.events.length > 0) {{
                    events = data.events.concat(events);
                    updateDisplay();
                }}
            }});
        }}
        
        function disconnectSocket() {{
            if (socket) {{
                socket.disconnect();
            }}
        }}
        
        function updateConnectionStatus(status, type) {{
            const statusEl = document.getElementById('connection-status');
            statusEl.textContent = type === 'connected' ? '🟢 ' + status : '🔴 ' + status;
            statusEl.className = 'status-item status-' + type;
        }}
        
        function requestStatus() {{
            if (socket && socket.connected) {{
                socket.emit('get_status');
            }}
        }}
        
        function requestHistory() {{
            if (socket && socket.connected) {{
                socket.emit('get_history', {{
                    limit: 100,
                    event_types: []
                }});
            }}
        }}
        
        function addEvent(eventData) {{
            events.unshift(eventData);
            
            // Track metrics
            const eventType = eventData.type ? eventData.type.split('.')[0] : 'unknown';
            eventTypeCount[eventType] = (eventTypeCount[eventType] || 0) + 1;
            
            if (eventData.type && eventData.type.includes('error')) {{
                errorCount++;
            }}
            
            // Track events per minute
            const currentMinute = new Date().getMinutes();
            if (currentMinute !== lastMinute) {{
                eventsThisMinute = 1;
                lastMinute = currentMinute;
            }} else {{
                eventsThisMinute++;
            }}
            
            // Limit history
            if (events.length > 1000) {{
                events = events.slice(0, 1000);
            }}
            
            updateDisplay();
        }}
        
        function updateDisplay() {{
            applyFilters();
            renderEvents();
            updateMetrics();
        }}
        
        function applyFilters() {{
            const searchTerm = document.getElementById('search-input').value.toLowerCase();
            const eventTypeFilter = document.getElementById('event-type-filter').value;
            
            filteredEvents = events.filter(event => {{
                // Search filter
                if (searchTerm) {{
                    const searchableText = JSON.stringify(event).toLowerCase();
                    if (!searchableText.includes(searchTerm)) {{
                        return false;
                    }}
                }}
                
                // Event type filter
                if (eventTypeFilter) {{
                    const eventType = event.type ? event.type.split('.')[0] : '';
                    if (eventType !== eventTypeFilter) {{
                        return false;
                    }}
                }}
                
                return true;
            }});
        }}
        
        function renderEvents() {{
            const eventsList = document.getElementById('events-list');
            
            if (filteredEvents.length === 0) {{
                eventsList.innerHTML = '<div class="no-events">No events match current filters...</div>';
                return;
            }}
            
            const eventsHtml = filteredEvents.map((event, index) => {{
                const eventType = event.type ? event.type.split('.')[0] : 'unknown';
                const timestamp = new Date(event.timestamp).toLocaleTimeString();
                const dataPreview = JSON.stringify(event.data || {{}}).substring(0, 100);
                
                return `
                    <div class="event-item event-${{eventType}}" onclick="showEventDetails(${{index}})">
                        <div class="event-header">
                            <span class="event-type">${{event.type || 'unknown'}}</span>
                            <span class="event-timestamp">${{timestamp}}</span>
                        </div>
                        <div class="event-data">${{dataPreview}}${{dataPreview.length >= 100 ? '...' : ''}}</div>
                    </div>
                `;
            }}).join('');
            
            eventsList.innerHTML = eventsHtml;
            
            // Auto-scroll to bottom
            if (autoScroll) {{
                eventsList.scrollTop = eventsList.scrollHeight;
            }}
        }}
        
        function updateMetrics() {{
            document.getElementById('total-events').textContent = events.length;
            document.getElementById('events-per-minute').textContent = eventsThisMinute;
            document.getElementById('unique-types').textContent = Object.keys(eventTypeCount).length;
            document.getElementById('error-count').textContent = errorCount;
        }}
        
        function showEventDetails(index) {{
            const event = filteredEvents[index];
            const modal = document.getElementById('event-modal');
            const content = document.getElementById('event-detail-content');
            
            content.innerHTML = `
                <h3>${{event.type || 'Unknown Event'}}</h3>
                <p><strong>Timestamp:</strong> ${{event.timestamp}}</p>
                <h4>Event Data:</h4>
                <pre>${{JSON.stringify(event, null, 2)}}</pre>
            `;
            
            modal.style.display = 'block';
        }}
        
        function closeModal() {{
            document.getElementById('event-modal').style.display = 'none';
        }}
        
        function clearEvents() {{
            events = [];
            filteredEvents = [];
            eventTypeCount = {{}};
            errorCount = 0;
            eventsThisMinute = 0;
            updateDisplay();
        }}
        
        function exportEvents() {{
            const dataToExport = {{
                timestamp: new Date().toISOString(),
                total_events: events.length,
                filtered_events: filteredEvents.length,
                events: filteredEvents
            }};
            
            const blob = new Blob([JSON.stringify(dataToExport, null, 2)], 
                                 {{ type: 'application/json' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `claude-mpm-events-${{new Date().toISOString().slice(0, 10)}}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }}
        
        function toggleAutoScroll() {{
            autoScroll = !autoScroll;
            const btn = document.getElementById('autoscroll-btn');
            btn.textContent = `Auto-scroll: ${{autoScroll ? 'ON' : 'OFF'}}`;
            btn.className = autoScroll ? 'btn-secondary' : 'btn-secondary';
        }}
        
        // Event listeners
        document.getElementById('search-input').addEventListener('input', updateDisplay);
        document.getElementById('event-type-filter').addEventListener('change', updateDisplay);
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {{
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {{
                e.preventDefault();
                document.getElementById('search-input').focus();
            }}
            if ((e.ctrlKey || e.metaKey) && e.key === 'e') {{
                e.preventDefault();
                exportEvents();
            }}
            if ((e.ctrlKey || e.metaKey) && e.key === 'r') {{
                e.preventDefault();
                clearEvents();
            }}
            if (e.key === 'Escape') {{
                closeModal();
            }}
        }});
        
        // Click outside modal to close
        window.onclick = function(event) {{
            const modal = document.getElementById('event-modal');
            if (event.target === modal) {{
                closeModal();
            }}
        }}
        
        // Periodic updates
        setInterval(() => {{
            updateMetrics();
            if (socket && socket.connected) {{
                requestStatus();
            }}
        }}, 30000); // Every 30 seconds
        
        console.log('Claude MPM Socket.IO Dashboard loaded');
        console.log('Auto-connect:', autoConnect);
        console.log('Default port:', defaultPort);
    </script>
</body>
</html>'''
    
    dashboard_path = SCRIPT_DIR / "claude_mpm_socketio_dashboard.html"
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        f.write(dashboard_html_content)
    
    print(f"✓ Created Socket.IO dashboard at {dashboard_path}")

def check_server_running(port: int) -> bool:
    """Check if a Socket.IO server is already running on the specified port.
    
    WHY: We want to avoid starting multiple servers on the same port
    and provide clear feedback to users about existing servers.
    
    Args:
        port: Port number to check
        
    Returns:
        bool: True if server is running, False otherwise
    """
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('127.0.0.1', port))
            if result == 0:
                print(f"✓ Socket.IO server already running on port {port}")
                return True
    except Exception:
        pass
    
    return False

def start_python_server(port: int, daemon: bool = False) -> Optional:
    """Start the Python Socket.IO server.
    
    WHY: Uses python-socketio and aiohttp for a clean, Node.js-free
    implementation that handles all Socket.IO functionality.
    
    Args:
        port: Port number for the server
        daemon: Whether to run in background mode
        
    Returns:
        Thread object if successful, None otherwise
    """
    try:
        # Import the existing Python Socket.IO server
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from claude_mpm.services.socketio_server import SocketIOServer
        
        server = SocketIOServer(port=port)
        
        if daemon:
            # Start in background thread
            server.start()
            print(f"🚀 Python Socket.IO server started on port {port}")
            return server.thread
        else:
            # Start and block
            print(f"🚀 Starting Python Socket.IO server on port {port}")
            server.start()
            
            # Keep alive until interrupted
            try:
                while server.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\\n🛑 Shutting down Python server...")
                server.stop()
            
            return None
            
    except Exception as e:
        print(f"❌ Failed to start Python server: {e}")
        return None

def open_dashboard(port: int, no_browser: bool = False):
    """Open the Socket.IO dashboard in browser.
    
    WHY: Users need easy access to the monitoring dashboard. This function
    handles URL construction and browser opening with fallback options.
    
    Args:
        port: Port number for the Socket.IO server
        no_browser: Skip browser opening if True
    """
    if no_browser:
        print(f"📊 Dashboard available at: http://localhost:{port}/claude_mpm_socketio_dashboard.html")
        return
    
    dashboard_url = f"http://localhost:{port}/claude_mpm_socketio_dashboard.html?autoconnect=true&port={port}"
    
    try:
        print(f"🌐 Opening dashboard: {dashboard_url}")
        webbrowser.open(dashboard_url)
        
    except Exception as e:
        print(f"⚠️  Failed to open browser automatically: {e}")
        print(f"📊 Dashboard: {dashboard_url}")

def cleanup_handler(signum, frame):
    """Handle cleanup on shutdown signals.
    
    WHY: Proper cleanup ensures sockets are closed and resources freed
    when the script is terminated.
    """
    print("\\n🛑 Shutting down Socket.IO launcher...")
    sys.exit(0)

def main():
    """Main entry point for the Socket.IO dashboard launcher.
    
    WHY: This orchestrates the entire launch process, from dependency checking
    to server startup and dashboard opening, with comprehensive error handling.
    """
    parser = argparse.ArgumentParser(
        description="Launch Socket.IO dashboard for Claude MPM monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python launch_socketio_dashboard.py                    # Start with default settings
  python launch_socketio_dashboard.py --port 3000       # Use specific port
  python launch_socketio_dashboard.py --daemon          # Run in background
  python launch_socketio_dashboard.py --no-browser      # Don't open browser
  python launch_socketio_dashboard.py --setup-only      # Just create files
        '''
    )
    
    parser.add_argument('--port', type=int, default=3000,
                       help='Socket.IO server port (default: 3000)')
    parser.add_argument('--daemon', action='store_true',
                       help='Run server in background mode')
    parser.add_argument('--no-browser', action='store_true',
                       help='Skip opening browser automatically')
    parser.add_argument('--setup-only', action='store_true',
                       help='Create necessary files without starting server')
    
    args = parser.parse_args()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, cleanup_handler)
    signal.signal(signal.SIGTERM, cleanup_handler)
    
    print("🚀 Claude MPM Socket.IO Dashboard Launcher")
    print("=" * 50)
    
    # Create dashboard HTML (always needed)
    create_dashboard_html(args.port)
    
    if args.setup_only:
        # Just setup files, don't start server
        print("📁 Setup complete - files created")
        return
    
    # Check if server is already running
    if check_server_running(args.port):
        print(f"✅ Using existing server on port {args.port}")
        open_dashboard(args.port, args.no_browser)
        return
    
    # Check Python dependencies
    if not check_python_dependencies():
        print("❌ Required Python packages not available")
        sys.exit(1)
    
    # Start Python Socket.IO server
    print("🟢 Using Python Socket.IO server")
    
    try:
        server_thread = start_python_server(args.port, args.daemon)
        
        if server_thread or not args.daemon:
            # Server started or is starting
            time.sleep(2)  # Give server time to start
            open_dashboard(args.port, args.no_browser)
            
            if args.daemon and server_thread:
                print(f"🔄 Python server running in background")
                print(f"   Dashboard: http://localhost:{args.port}/claude_mpm_socketio_dashboard.html")
        else:
            print("❌ Failed to start Socket.IO server")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\\n✅ Socket.IO launcher stopped")
    except Exception as e:
        print(f"❌ Launcher error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()