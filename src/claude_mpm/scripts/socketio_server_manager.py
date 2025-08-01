#!/usr/bin/env python3
"""Socket.IO Server Manager - Deployment-agnostic server management.

This script provides unified management for Socket.IO servers across different deployment scenarios:
- Local development
- PyPI installation
- Docker containers
- System service installation

Features:
- Start/stop/restart standalone servers
- Version compatibility checking
- Health monitoring and diagnostics
- Multi-instance management
- Automatic dependency installation
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class ServerManager:
    """Manages Socket.IO server instances across different deployment modes."""
    
    def __init__(self):
        self.base_port = 8765
        self.max_instances = 5
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent
        
    def get_server_info(self, port: int) -> Optional[Dict]:
        """Get server information from a running instance."""
        if not REQUESTS_AVAILABLE:
            return None
        
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=2.0)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None
    
    def list_running_servers(self) -> List[Dict]:
        """List all running Socket.IO servers."""
        running_servers = []
        
        for port in range(self.base_port, self.base_port + self.max_instances):
            server_info = self.get_server_info(port)
            if server_info:
                server_info['port'] = port
                running_servers.append(server_info)
        
        return running_servers
    
    def find_available_port(self, start_port: int = None) -> int:
        """Find the next available port for a new server."""
        start_port = start_port or self.base_port
        
        for port in range(start_port, start_port + self.max_instances):
            if not self.get_server_info(port):
                return port
        
        raise RuntimeError(f"No available ports found in range {start_port}-{start_port + self.max_instances}")
    
    def start_server(self, port: int = None, server_id: str = None, 
                    host: str = "localhost") -> bool:
        """Start a standalone Socket.IO server."""
        
        # Find available port if not specified
        if port is None:
            try:
                port = self.find_available_port()
            except RuntimeError as e:
                print(f"Error: {e}")
                return False
        
        # Check if server is already running on this port
        if self.get_server_info(port):
            print(f"Server already running on port {port}")
            return False
        
        # Try different ways to start the server based on deployment
        success = False
        
        # Method 1: Try installed claude-mpm package
        try:
            cmd = [
                sys.executable, "-m", "claude_mpm.services.standalone_socketio_server",
                "--host", host,
                "--port", str(port)
            ]
            if server_id:
                cmd.extend(["--server-id", server_id])
            
            print(f"Starting server on {host}:{port} using installed package...")
            
            # Start in background
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Wait for server to start
            for _ in range(10):  # Wait up to 10 seconds
                time.sleep(1)
                if self.get_server_info(port):
                    success = True
                    break
                    
        except Exception as e:
            print(f"Failed to start via installed package: {e}")
        
        # Method 2: Try local development mode
        if not success:
            try:
                server_path = self.project_root / "src" / "claude_mpm" / "services" / "standalone_socketio_server.py"
                if server_path.exists():
                    cmd = [
                        sys.executable, str(server_path),
                        "--host", host,
                        "--port", str(port)
                    ]
                    if server_id:
                        cmd.extend(["--server-id", server_id])
                    
                    print(f"Starting server using local development mode...")
                    
                    # Set PYTHONPATH for local development
                    env = os.environ.copy()
                    src_path = str(self.project_root / "src")
                    if "PYTHONPATH" in env:
                        env["PYTHONPATH"] = f"{src_path}:{env['PYTHONPATH']}"
                    else:
                        env["PYTHONPATH"] = src_path
                    
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
                    
                    # Wait for server to start
                    for _ in range(10):
                        time.sleep(1)
                        if self.get_server_info(port):
                            success = True
                            break
                            
            except Exception as e:
                print(f"Failed to start in development mode: {e}")
        
        if success:
            print(f"✅ Server started successfully on {host}:{port}")
            return True
        else:
            print(f"❌ Failed to start server on {host}:{port}")
            return False
    
    def stop_server(self, port: int = None, server_id: str = None) -> bool:
        """Stop a running Socket.IO server."""
        
        if port is None and server_id is None:
            print("Must specify either port or server_id")
            return False
        
        # Find server by ID if port not specified
        if port is None:
            running_servers = self.list_running_servers()
            for server in running_servers:
                if server.get('server_id') == server_id:
                    port = server['port']
                    break
            
            if port is None:
                print(f"Server with ID '{server_id}' not found")
                return False
        
        # Get server info
        server_info = self.get_server_info(port)
        if not server_info:
            print(f"No server running on port {port}")
            return False
        
        # Try to get PID and send termination signal
        pid = server_info.get('pid')
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"✅ Sent termination signal to server (PID: {pid})")
                
                # Wait for server to stop
                for _ in range(10):
                    time.sleep(1)
                    if not self.get_server_info(port):
                        print(f"✅ Server stopped successfully")
                        return True
                
                # Force kill if still running
                try:
                    os.kill(pid, signal.SIGKILL)
                    print(f"⚠️ Force killed server (PID: {pid})")
                    return True
                except:
                    pass
                    
            except OSError as e:
                print(f"Error stopping server: {e}")
        
        print(f"❌ Failed to stop server on port {port}")
        return False
    
    def restart_server(self, port: int = None, server_id: str = None) -> bool:
        """Restart a Socket.IO server."""
        
        # Stop the server first
        if self.stop_server(port, server_id):
            time.sleep(2)  # Give it time to fully stop
            
            # Start it again
            if port is None:
                port = self.find_available_port()
            
            return self.start_server(port)
        
        return False
    
    def status(self, verbose: bool = False) -> None:
        """Show status of all Socket.IO servers."""
        running_servers = self.list_running_servers()
        
        if not running_servers:
            print("No Socket.IO servers currently running")
            return
        
        print(f"Found {len(running_servers)} running server(s):")
        print()
        
        for server in running_servers:
            port = server['port']
            server_id = server.get('server_id', 'unknown')
            version = server.get('server_version', 'unknown')
            uptime = server.get('uptime_seconds', 0)
            clients = server.get('clients_connected', 0)
            
            print(f"🖥️  Server ID: {server_id}")
            print(f"   Port: {port}")
            print(f"   Version: {version}")
            print(f"   Uptime: {self._format_uptime(uptime)}")
            print(f"   Clients: {clients}")
            
            if verbose:
                print(f"   PID: {server.get('pid', 'unknown')}")
                print(f"   Host: {server.get('host', 'unknown')}")
                
                # Get additional stats
                stats = self._get_server_stats(port)
                if stats:
                    events_processed = stats.get('events', {}).get('total_processed', 0)
                    clients_served = stats.get('connections', {}).get('total_served', 0)
                    print(f"   Events processed: {events_processed}")
                    print(f"   Total clients served: {clients_served}")
            
            print()
    
    def health_check(self, port: int = None) -> bool:
        """Perform health check on server(s)."""
        
        if port:
            # Check specific server
            server_info = self.get_server_info(port)
            if server_info:
                status = server_info.get('status', 'unknown')
                print(f"Server on port {port}: {status}")
                return status == 'healthy'
            else:
                print(f"No server found on port {port}")
                return False
        else:
            # Check all servers
            running_servers = self.list_running_servers()
            if not running_servers:
                print("No servers running")
                return False
            
            all_healthy = True
            for server in running_servers:
                port = server['port']
                status = server.get('status', 'unknown')
                server_id = server.get('server_id', 'unknown')
                print(f"Server {server_id} (port {port}): {status}")
                if status != 'healthy':
                    all_healthy = False
            
            return all_healthy
    
    def install_dependencies(self) -> bool:
        """Install required dependencies for Socket.IO server."""
        dependencies = ['python-socketio>=5.11.0', 'aiohttp>=3.9.0', 'requests>=2.25.0']
        
        print("Installing Socket.IO server dependencies...")
        
        try:
            cmd = [sys.executable, '-m', 'pip', 'install'] + dependencies
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Dependencies installed successfully")
                return True
            else:
                print(f"❌ Failed to install dependencies: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error installing dependencies: {e}")
            return False
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in a human-readable way."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"
    
    def _get_server_stats(self, port: int) -> Optional[Dict]:
        """Get detailed server statistics."""
        if not REQUESTS_AVAILABLE:
            return None
        
        try:
            response = requests.get(f"http://localhost:{port}/stats", timeout=2.0)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Socket.IO Server Manager")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start a Socket.IO server')
    start_parser.add_argument('--port', type=int, help='Port to bind to (auto-detect if not specified)')
    start_parser.add_argument('--host', default='localhost', help='Host to bind to')
    start_parser.add_argument('--server-id', help='Custom server ID')
    
    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop a Socket.IO server')
    stop_parser.add_argument('--port', type=int, help='Port of server to stop')
    stop_parser.add_argument('--server-id', help='Server ID to stop')
    
    # Restart command
    restart_parser = subparsers.add_parser('restart', help='Restart a Socket.IO server')
    restart_parser.add_argument('--port', type=int, help='Port of server to restart')
    restart_parser.add_argument('--server-id', help='Server ID to restart')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show server status')
    status_parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed information')
    
    # Health check command
    health_parser = subparsers.add_parser('health', help='Perform health check')
    health_parser.add_argument('--port', type=int, help='Port to check (all servers if not specified)')
    
    # Install dependencies command
    subparsers.add_parser('install-deps', help='Install required dependencies')
    
    # List command
    subparsers.add_parser('list', help='List running servers')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = ServerManager()
    
    if args.command == 'start':
        success = manager.start_server(
            port=args.port,
            server_id=args.server_id,
            host=args.host
        )
        sys.exit(0 if success else 1)
    
    elif args.command == 'stop':
        success = manager.stop_server(
            port=args.port,
            server_id=args.server_id
        )
        sys.exit(0 if success else 1)
    
    elif args.command == 'restart':
        success = manager.restart_server(
            port=args.port,
            server_id=args.server_id
        )
        sys.exit(0 if success else 1)
    
    elif args.command == 'status':
        manager.status(verbose=args.verbose)
    
    elif args.command == 'health':
        healthy = manager.health_check(port=args.port)
        sys.exit(0 if healthy else 1)
    
    elif args.command == 'install-deps':
        success = manager.install_dependencies()
        sys.exit(0 if success else 1)
    
    elif args.command == 'list':
        manager.status(verbose=False)


if __name__ == "__main__":
    main()