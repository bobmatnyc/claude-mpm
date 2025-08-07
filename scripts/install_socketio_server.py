#!/usr/bin/env python3
"""Socket.IO Server Installation Script.

This script handles installation and setup of the Socket.IO server
across different deployment scenarios and platforms.

Features:
- Automatic dependency detection and installation
- Platform-specific installation (Linux, macOS, Windows)
- Service/daemon installation for persistent operation
- Configuration file generation
- Validation and testing
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class SocketIOInstaller:
    """Handles installation of Socket.IO server across different platforms."""
    
    def __init__(self):
        self.platform = platform.system().lower()
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent
        self.python_executable = sys.executable
        
        # Installation paths by platform
        if self.platform == 'linux':
            self.service_dir = Path('/etc/systemd/system')
            self.bin_dir = Path('/usr/local/bin')
            self.config_dir = Path('/etc/claude-mpm')
        elif self.platform == 'darwin':  # macOS
            self.service_dir = Path.home() / 'Library' / 'LaunchAgents'
            self.bin_dir = Path('/usr/local/bin')
            self.config_dir = Path.home() / '.claude-mpm'
        elif self.platform == 'windows':
            self.service_dir = None  # Windows services handled differently
            self.bin_dir = Path(os.environ.get('USERPROFILE', '')) / 'AppData' / 'Local' / 'claude-mpm' / 'bin'
            self.config_dir = Path(os.environ.get('APPDATA', '')) / 'claude-mpm'
        else:
            raise RuntimeError(f"Unsupported platform: {self.platform}")
    
    def check_dependencies(self) -> Tuple[bool, List[str]]:
        """Check if required dependencies are installed."""
        required_packages = [
            'python-socketio>=5.11.0',
            'aiohttp>=3.9.0', 
            'requests>=2.25.0'
        ]
        
        missing = []
        
        for package in required_packages:
            package_name = package.split('>=')[0]
            try:
                __import__(package_name.replace('-', '_'))
            except ImportError:
                missing.append(package)
        
        return len(missing) == 0, missing
    
    def install_dependencies(self, missing_packages: List[str]) -> bool:
        """Install missing dependencies."""
        print("Installing required dependencies...")
        
        try:
            cmd = [self.python_executable, '-m', 'pip', 'install'] + missing_packages
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
    
    def create_startup_script(self, install_dir: Path) -> bool:
        """Create startup script for the Socket.IO server."""
        
        # Create the script content
        if self.platform == 'windows':
            script_name = 'claude-mpm-socketio.bat'
            script_content = f'''@echo off
REM Claude MPM Socket.IO Server Startup Script
"{self.python_executable}" -m claude_mpm.services.standalone_socketio_server %*
'''
        else:
            script_name = 'claude-mpm-socketio'
            script_content = f'''#!/bin/bash
# Claude MPM Socket.IO Server Startup Script
exec "{self.python_executable}" -m claude_mpm.services.standalone_socketio_server "$@"
'''
        
        script_path = install_dir / script_name
        
        try:
            install_dir.mkdir(parents=True, exist_ok=True)
            
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            if self.platform != 'windows':
                os.chmod(script_path, 0o755)
            
            print(f"✅ Created startup script: {script_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create startup script: {e}")
            return False
    
    def create_service_file(self, user_mode: bool = True) -> bool:
        """Create system service file for persistent operation."""
        
        if self.platform == 'linux':
            return self._create_systemd_service(user_mode)
        elif self.platform == 'darwin':
            return self._create_launchd_service()
        elif self.platform == 'windows':
            return self._create_windows_service()
        else:
            print(f"⚠️ Service installation not supported on {self.platform}")
            return False
    
    def _create_systemd_service(self, user_mode: bool) -> bool:
        """Create systemd service file for Linux."""
        
        service_content = f'''[Unit]
Description=Claude MPM Socket.IO Server
After=network.target
Wants=network.target

[Service]
Type=simple
ExecStart={self.python_executable} -m claude_mpm.services.standalone_socketio_server
Restart=always
RestartSec=5
Environment=PYTHONPATH={self.project_root / "src"}
WorkingDirectory={self.project_root}

[Install]
WantedBy={"default.target" if user_mode else "multi-user.target"}
'''
        
        if user_mode:
            service_dir = Path.home() / '.config' / 'systemd' / 'user'
            service_name = 'claude-mpm-socketio.service'
        else:
            service_dir = self.service_dir
            service_name = 'claude-mpm-socketio.service'
        
        service_path = service_dir / service_name
        
        try:
            service_dir.mkdir(parents=True, exist_ok=True)
            
            with open(service_path, 'w') as f:
                f.write(service_content)
            
            print(f"✅ Created systemd service: {service_path}")
            
            # Enable and start the service
            if user_mode:
                subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
                subprocess.run(['systemctl', '--user', 'enable', service_name], check=True)
                print(f"✅ Service enabled. Start with: systemctl --user start {service_name}")
            else:
                subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
                subprocess.run(['sudo', 'systemctl', 'enable', service_name], check=True)
                print(f"✅ Service enabled. Start with: sudo systemctl start {service_name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to create systemd service: {e}")
            return False
    
    def _create_launchd_service(self) -> bool:
        """Create launchd service file for macOS."""
        
        service_content = {
            "Label": "com.claude-mpm.socketio",
            "ProgramArguments": [
                self.python_executable,
                "-m", "claude_mpm.services.standalone_socketio_server"
            ],
            "RunAtLoad": True,
            "KeepAlive": True,
            "WorkingDirectory": str(self.project_root),
            "EnvironmentVariables": {
                "PYTHONPATH": str(self.project_root / "src")
            },
            "StandardOutPath": str(Path.home() / "Library" / "Logs" / "claude-mpm-socketio.log"),
            "StandardErrorPath": str(Path.home() / "Library" / "Logs" / "claude-mpm-socketio-error.log")
        }
        
        service_path = self.service_dir / 'com.claude-mpm.socketio.plist'
        
        try:
            self.service_dir.mkdir(parents=True, exist_ok=True)
            
            import plistlib
            with open(service_path, 'wb') as f:
                plistlib.dump(service_content, f)
            
            print(f"✅ Created launchd service: {service_path}")
            print(f"✅ Load with: launchctl load {service_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to create launchd service: {e}")
            return False
    
    def _create_windows_service(self) -> bool:
        """Create Windows service (placeholder - requires additional tools)."""
        print("⚠️ Windows service installation requires additional tools like NSSM or WinSW")
        print("   For now, you can run the server manually or use Task Scheduler")
        
        # Create a basic batch file for manual startup
        startup_script = self.bin_dir / 'start-claude-mpm-socketio.bat'
        
        script_content = f'''@echo off
title Claude MPM Socket.IO Server
cd /d "{self.project_root}"
"{self.python_executable}" -m claude_mpm.services.standalone_socketio_server
pause
'''
        
        try:
            self.bin_dir.mkdir(parents=True, exist_ok=True)
            
            with open(startup_script, 'w') as f:
                f.write(script_content)
            
            print(f"✅ Created startup script: {startup_script}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create startup script: {e}")
            return False
    
    def create_config_file(self, environment: str = "production") -> bool:
        """Create configuration file."""
        
        try:
            # Import config module
            sys.path.insert(0, str(self.project_root / "src"))
            from claude_mpm.config.socketio_config import SocketIOConfig
            
            if environment == "production":
                config = SocketIOConfig.for_production()
            elif environment == "docker":
                config = SocketIOConfig.for_docker()
            else:
                config = SocketIOConfig.for_development()
            
            self.config_dir.mkdir(parents=True, exist_ok=True)
            config_path = self.config_dir / 'socketio_config.json'
            
            with open(config_path, 'w') as f:
                json.dump(config.to_dict(), f, indent=2)
            
            print(f"✅ Created configuration file: {config_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create configuration file: {e}")
            return False
    
    def test_installation(self) -> bool:
        """Test the installation by checking imports and dependencies."""
        print("Testing installation...")
        
        try:
            # Try to import the server module
            sys.path.insert(0, str(self.project_root / "src"))
            from claude_mpm.services.standalone_socketio_server import StandaloneSocketIOServer, SOCKETIO_AVAILABLE
            
            if not SOCKETIO_AVAILABLE:
                print("❌ Socket.IO dependencies not available")
                return False
            
            # Create a test server instance (this only tests initialization, not startup)
            server = StandaloneSocketIOServer(port=8766)  # Use different port for testing
            
            # Check that the server was created properly
            if server.server_version != "1.0.0":
                print(f"❌ Unexpected server version: {server.server_version}")
                return False
            
            # Test that we can import client manager
            from claude_mpm.services.socketio_client_manager import SocketIOClientManager
            client_manager = SocketIOClientManager()
            
            # Test configuration
            from claude_mpm.config.socketio_config import get_config
            config = get_config()
            
            print("✅ Server module loads correctly")
            print("✅ Client manager loads correctly") 
            print("✅ Configuration system works")
            print("✅ Dependencies are properly installed")
            return True
            
        except ImportError as e:
            print(f"❌ Import error - missing dependencies: {e}")
            return False
        except Exception as e:
            print(f"❌ Installation test failed: {e}")
            return False
    
    def install(self, mode: str = "user", environment: str = "production", 
                create_service: bool = True) -> bool:
        """Perform complete installation."""
        
        print(f"Installing Claude MPM Socket.IO Server for {self.platform}...")
        print(f"Mode: {mode}, Environment: {environment}")
        print()
        
        # Step 1: Check and install dependencies
        deps_ok, missing = self.check_dependencies()
        if not deps_ok:
            print(f"Missing dependencies: {missing}")
            if not self.install_dependencies(missing):
                return False
        else:
            print("✅ All dependencies are already installed")
        
        # Step 2: Create startup script
        if not self.create_startup_script(self.bin_dir):
            return False
        
        # Step 3: Create configuration file
        if not self.create_config_file(environment):
            return False
        
        # Step 4: Create service file (optional)
        if create_service:
            user_mode = (mode == "user")
            self.create_service_file(user_mode)
        
        # Step 5: Test installation
        if not self.test_installation():
            print("⚠️ Installation completed but tests failed")
            return False
        
        print()
        print("✅ Installation completed successfully!")
        print()
        print("Next steps:")
        print(f"  1. Review configuration: {self.config_dir / 'socketio_config.json'}")
        print(f"  2. Start server: {self.bin_dir / 'claude-mpm-socketio'}")
        
        if create_service:
            if self.platform == 'linux':
                service_cmd = "systemctl --user start claude-mpm-socketio" if mode == "user" else "sudo systemctl start claude-mpm-socketio"
                print(f"  3. Or start as service: {service_cmd}")
            elif self.platform == 'darwin':
                print(f"  3. Or load service: launchctl load {self.service_dir / 'com.claude-mpm.socketio.plist'}")
        
        return True


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Install Claude MPM Socket.IO Server")
    
    parser.add_argument('--mode', choices=['user', 'system'], default='user',
                       help='Installation mode (user or system)')
    parser.add_argument('--environment', choices=['development', 'production', 'docker'],
                       default='production', help='Target environment')
    parser.add_argument('--no-service', action='store_true',
                       help='Skip service file creation')
    parser.add_argument('--test-only', action='store_true',
                       help='Only test dependencies and installation')
    
    args = parser.parse_args()
    
    installer = SocketIOInstaller()
    
    if args.test_only:
        success = installer.test_installation()
    else:
        success = installer.install(
            mode=args.mode,
            environment=args.environment,
            create_service=not args.no_service
        )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()