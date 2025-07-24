"""Hook service lifecycle manager for claude-mpm."""

import os
import sys
import time
import socket
import signal
import atexit
import subprocess
from pathlib import Path
from typing import Optional, Tuple
import json
import psutil
import logging

try:
    from ..utils.logger import get_logger
    from ..config.hook_config import HookConfig
except ImportError:
    from utils.logger import get_logger
    from config.hook_config import HookConfig


class HookServiceManager:
    """Manages the hook service lifecycle."""
    
    def __init__(self, port: Optional[int] = None, log_dir: Optional[Path] = None):
        """Initialize hook service manager.
        
        Args:
            port: Specific port to use (if None, will find available port)
            log_dir: Directory for hook service logs
        """
        self.logger = get_logger("hook_service_manager")
        self.config = HookConfig()
        self.port = port or self._find_available_port()
        self.log_dir = log_dir or self.config.HOOK_SERVICE_LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Process management
        self.pid_dir = self.config.HOOK_SERVICE_PID_DIR
        self.pid_dir.mkdir(parents=True, exist_ok=True)
        self.pid_file = self.pid_dir / f"hook_service_{self.port}.pid"
        self.process = None
        self._service_started = False
        
        # Register cleanup
        atexit.register(self.stop_service)
        signal.signal(signal.SIGTERM, lambda sig, frame: self.stop_service())
        signal.signal(signal.SIGINT, lambda sig, frame: self.stop_service())
    
    def _find_available_port(self) -> int:
        """Find an available port in the configured range."""
        start = self.config.PORT_RANGE_START
        end = self.config.PORT_RANGE_END
        for port in range(start, end):
            if self._is_port_available(port):
                return port
        raise RuntimeError(f"No available ports found in range {start}-{end}")
    
    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except OSError:
            return False
    
    def _check_existing_service(self) -> bool:
        """Check if hook service is already running on the port."""
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text().strip())
                # Check if process exists and is our hook service
                if psutil.pid_exists(pid):
                    process = psutil.Process(pid)
                    if 'python' in process.name().lower() and 'hook_service.py' in ' '.join(process.cmdline()):
                        # Test if service is responsive
                        if self._test_service_health():
                            self.logger.info(f"Found existing hook service on port {self.port} (PID: {pid})")
                            return True
                        else:
                            self.logger.warning(f"Existing hook service on port {self.port} is not responding")
                            self._cleanup_stale_pidfile()
            except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied) as e:
                self.logger.debug(f"Error checking existing service: {e}")
                self._cleanup_stale_pidfile()
        
        return False
    
    def _cleanup_stale_pidfile(self):
        """Remove stale PID file."""
        if self.pid_file.exists():
            self.pid_file.unlink()
    
    def _test_service_health(self) -> bool:
        """Test if the hook service is healthy."""
        import requests
        try:
            url = self.config.get_hook_service_url(self.port) + self.config.HEALTH_ENDPOINT
            response = requests.get(url, timeout=self.config.HEALTH_CHECK_TIMEOUT)
            return response.status_code == 200
        except:
            return False
    
    def start_service(self, force: bool = False) -> bool:
        """Start the hook service if not already running.
        
        Args:
            force: Force restart even if service is already running
            
        Returns:
            True if service was started or already running, False on error
        """
        # Check if already running
        if not force and self._check_existing_service():
            self._service_started = True
            return True
        
        # Stop any existing service if forcing
        if force:
            self.stop_service()
        
        # Start new service
        try:
            # Find hook service script
            hook_service_path = self._find_hook_service_script()
            if not hook_service_path:
                self.logger.warning("Hook service script not found")
                return False
            
            # Prepare log files
            stdout_log = self.log_dir / f"hook_service_{self.port}.log"
            stderr_log = self.log_dir / f"hook_service_{self.port}.error.log"
            
            # Start subprocess
            cmd = [
                sys.executable,
                str(hook_service_path),
                "--port", str(self.port),
                "--log-level", "INFO"
            ]
            
            self.logger.info(f"Starting hook service on port {self.port}")
            
            with open(stdout_log, 'a') as stdout_file, open(stderr_log, 'a') as stderr_file:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    start_new_session=True  # Detach from parent process group
                )
            
            # Wait for service to start
            start_wait = int(self.config.SERVICE_START_TIMEOUT * 10)  # Convert to tenths of seconds
            for _ in range(start_wait):
                if self._test_service_health():
                    # Save PID
                    self.pid_file.write_text(str(self.process.pid))
                    self._service_started = True
                    self.logger.info(f"Hook service started successfully on port {self.port} (PID: {self.process.pid})")
                    return True
                time.sleep(0.1)
            
            # Service didn't start properly
            self.logger.error("Hook service failed to start within timeout")
            self.stop_service()
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to start hook service: {e}")
            return False
    
    def _find_hook_service_script(self) -> Optional[Path]:
        """Find the hook service script."""
        # Try different locations
        possible_paths = [
            # Relative to this file (same directory)
            Path(__file__).parent / "hook_service.py",
            # In src/services directory
            Path(__file__).parent.parent / "services" / "hook_service.py",
            # In project root
            Path(__file__).parent.parent.parent / "hook_service.py",
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return None
    
    def stop_service(self):
        """Stop the hook service if running."""
        if self.process and self.process.poll() is None:
            self.logger.info(f"Stopping hook service on port {self.port}")
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            finally:
                self.process = None
        
        # Clean up PID file
        if self.pid_file.exists():
            self.pid_file.unlink()
        
        self._service_started = False
    
    def get_service_info(self) -> dict:
        """Get information about the running service."""
        return {
            "running": self._service_started and self._test_service_health(),
            "port": self.port,
            "pid": self.process.pid if self.process else None,
            "url": self.config.get_hook_service_url(self.port)
        }
    
    def is_available(self) -> bool:
        """Check if hook service is available and healthy."""
        return self._service_started and self._test_service_health()