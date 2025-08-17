#!/usr/bin/env python3
"""
MCP Services Monitor - Comprehensive monitoring and stabilization for MCP services.

This script monitors eva-memory, cloud bridge, and desktop gateway services,
automatically restarting them on failure and preventing port conflicts.
"""

import argparse
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Event, Thread
from typing import Dict, List, Optional, Tuple

import psutil
import requests
import yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class ServiceConfig:
    """Configuration for a single MCP service."""

    name: str
    command: List[str]
    port: int
    health_endpoint: str
    health_timeout: int = 5
    startup_timeout: int = 30
    restart_delay: int = 5
    max_retries: int = 3
    log_file: Optional[str] = None
    env_vars: Dict[str, str] = None
    working_dir: Optional[str] = None


class MCPServiceMonitor:
    """Monitor and manage MCP services."""

    def __init__(self, config_path: str, log_dir: str = None):
        self.config_path = Path(config_path)
        self.log_dir = Path(log_dir) if log_dir else Path.home() / ".mcp" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self.setup_logging()

        # Load configuration
        self.services: Dict[str, ServiceConfig] = {}
        self.processes: Dict[str, subprocess.Popen] = {}
        self.load_config()

        # Control flags
        self.shutdown_event = Event()
        self.monitor_threads: Dict[str, Thread] = {}

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def setup_logging(self):
        """Configure logging for the monitor."""
        log_file = (
            self.log_dir / f"mcp_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
        )

        self.logger = logging.getLogger("MCPMonitor")
        self.logger.info(f"MCP Service Monitor started. Logging to {log_file}")

    def load_config(self):
        """Load service configurations from YAML file."""
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)

            for service_name, service_config in config["services"].items():
                self.services[service_name] = ServiceConfig(
                    name=service_name,
                    command=service_config["command"],
                    port=service_config["port"],
                    health_endpoint=service_config.get(
                        "health_endpoint",
                        f"http://localhost:{service_config['port']}/health",
                    ),
                    health_timeout=service_config.get("health_timeout", 5),
                    startup_timeout=service_config.get("startup_timeout", 30),
                    restart_delay=service_config.get("restart_delay", 5),
                    max_retries=service_config.get("max_retries", 3),
                    log_file=service_config.get("log_file"),
                    env_vars=service_config.get("env_vars", {}),
                    working_dir=service_config.get("working_dir"),
                )

            self.logger.info(f"Loaded configuration for {len(self.services)} services")

        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_event.set()

    def is_port_available(self, port: int) -> bool:
        """Check if a port is available for binding."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return True
        except OSError:
            return False

    def find_process_on_port(self, port: int) -> Optional[int]:
        """Find the PID of process listening on the given port."""
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port and conn.status == "LISTEN":
                    return conn.pid
        except (psutil.AccessDenied, PermissionError):
            # On macOS, we might not have permission to view all connections
            # Try using lsof as a fallback
            try:
                result = subprocess.run(
                    ["lsof", "-ti", f":{port}"], capture_output=True, text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    return int(result.stdout.strip().split("\n")[0])
            except:
                pass
        return None

    def kill_process_on_port(self, port: int) -> bool:
        """Kill process listening on the given port."""
        pid = self.find_process_on_port(port)
        if pid:
            try:
                process = psutil.Process(pid)
                self.logger.warning(
                    f"Killing process {pid} ({process.name()}) on port {port}"
                )
                process.terminate()
                process.wait(timeout=5)
                return True
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                try:
                    process.kill()
                    return True
                except:
                    return False
        return False

    def check_health(self, service: ServiceConfig) -> bool:
        """Check if a service is healthy via its health endpoint."""
        try:
            # Create session with retry strategy
            session = requests.Session()
            retry = Retry(
                total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504]
            )
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("http://", adapter)
            session.mount("https://", adapter)

            response = session.get(
                service.health_endpoint, timeout=service.health_timeout
            )

            return response.status_code == 200

        except Exception as e:
            self.logger.debug(f"Health check failed for {service.name}: {e}")
            return False

    def start_service(self, service: ServiceConfig) -> Optional[subprocess.Popen]:
        """Start a single service."""
        # Check if port is available
        if not self.is_port_available(service.port):
            self.logger.warning(f"Port {service.port} is in use for {service.name}")
            if self.kill_process_on_port(service.port):
                time.sleep(2)  # Give time for port to be released
            else:
                self.logger.error(
                    f"Failed to free port {service.port} for {service.name}"
                )
                return None

        # Prepare environment
        env = os.environ.copy()
        if service.env_vars:
            env.update(service.env_vars)

        # Prepare log file
        log_file = None
        if service.log_file:
            log_path = self.log_dir / service.log_file
            log_file = open(log_path, "a")

        try:
            self.logger.info(f"Starting {service.name} on port {service.port}")

            process = subprocess.Popen(
                service.command,
                env=env,
                cwd=service.working_dir,
                stdout=log_file or subprocess.PIPE,
                stderr=log_file or subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )

            # Wait for service to start
            start_time = time.time()
            while time.time() - start_time < service.startup_timeout:
                if self.check_health(service):
                    self.logger.info(
                        f"{service.name} started successfully (PID: {process.pid})"
                    )
                    return process

                if process.poll() is not None:
                    self.logger.error(
                        f"{service.name} exited during startup with code {process.returncode}"
                    )
                    return None

                time.sleep(1)

            self.logger.error(
                f"{service.name} failed to become healthy within {service.startup_timeout}s"
            )
            process.terminate()
            return None

        except Exception as e:
            self.logger.error(f"Failed to start {service.name}: {e}")
            if log_file:
                log_file.close()
            return None

    def stop_service(self, service_name: str):
        """Stop a running service gracefully."""
        if service_name in self.processes:
            process = self.processes[service_name]
            if process and process.poll() is None:
                self.logger.info(f"Stopping {service_name} (PID: {process.pid})")
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.logger.warning(f"Force killing {service_name}")
                    process.kill()
                    process.wait()

            del self.processes[service_name]

    def monitor_service(self, service_name: str):
        """Monitor a single service and restart if needed."""
        service = self.services[service_name]
        consecutive_failures = 0

        while not self.shutdown_event.is_set():
            try:
                # Check if process exists and is running
                process = self.processes.get(service_name)

                if process and process.poll() is None:
                    # Process is running, check health
                    if self.check_health(service):
                        consecutive_failures = 0
                        time.sleep(10)  # Health check interval
                        continue
                    else:
                        self.logger.warning(f"{service_name} health check failed")

                # Service is not running or unhealthy
                consecutive_failures += 1

                if consecutive_failures > service.max_retries:
                    self.logger.error(
                        f"{service_name} exceeded max retries ({service.max_retries})"
                    )
                    time.sleep(60)  # Back off for a minute
                    consecutive_failures = 0
                    continue

                # Stop existing process if any
                self.stop_service(service_name)

                # Wait before restart
                self.logger.info(
                    f"Restarting {service_name} in {service.restart_delay}s..."
                )
                time.sleep(service.restart_delay)

                # Start service
                process = self.start_service(service)
                if process:
                    self.processes[service_name] = process
                else:
                    self.logger.error(f"Failed to start {service_name}")

            except Exception as e:
                self.logger.error(f"Error monitoring {service_name}: {e}")
                time.sleep(10)

    def start_monitoring(self):
        """Start monitoring all configured services."""
        self.logger.info("Starting MCP service monitoring...")

        # Start each service
        for service_name, service in self.services.items():
            process = self.start_service(service)
            if process:
                self.processes[service_name] = process

                # Start monitor thread
                monitor_thread = Thread(
                    target=self.monitor_service,
                    args=(service_name,),
                    name=f"Monitor-{service_name}",
                )
                monitor_thread.daemon = True
                monitor_thread.start()
                self.monitor_threads[service_name] = monitor_thread
            else:
                self.logger.error(
                    f"Failed to start {service_name}, skipping monitoring"
                )

    def stop_monitoring(self):
        """Stop all services and monitoring threads."""
        self.logger.info("Stopping MCP service monitoring...")

        # Signal shutdown
        self.shutdown_event.set()

        # Stop all services
        for service_name in list(self.processes.keys()):
            self.stop_service(service_name)

        # Wait for monitor threads
        for thread in self.monitor_threads.values():
            thread.join(timeout=5)

        self.logger.info("MCP service monitoring stopped")

    def status(self) -> Dict[str, Dict]:
        """Get status of all services."""
        status = {}

        for service_name, service in self.services.items():
            process = self.processes.get(service_name)

            status[service_name] = {
                "running": process is not None and process.poll() is None,
                "pid": process.pid if process and process.poll() is None else None,
                "port": service.port,
                "healthy": self.check_health(service) if process else False,
            }

        return status

    def run(self):
        """Main monitoring loop."""
        try:
            self.start_monitoring()

            # Main loop - print status periodically
            while not self.shutdown_event.is_set():
                time.sleep(30)

                # Print status
                status = self.status()
                self.logger.info("Service status:")
                for service_name, info in status.items():
                    self.logger.info(
                        f"  {service_name}: "
                        f"{'Running' if info['running'] else 'Stopped'} "
                        f"(PID: {info['pid'] or 'N/A'}, "
                        f"Port: {info['port']}, "
                        f"Healthy: {info['healthy']})"
                    )

        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        finally:
            self.stop_monitoring()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Monitor and manage MCP services")
    parser.add_argument(
        "-c",
        "--config",
        default="config/mcp_services.yaml",
        help="Path to services configuration file",
    )
    parser.add_argument(
        "-l", "--log-dir", help="Directory for log files (default: ~/.mcp/logs)"
    )
    parser.add_argument(
        "--status", action="store_true", help="Show service status and exit"
    )

    args = parser.parse_args()

    # Resolve config path
    config_path = Path(args.config)
    if not config_path.is_absolute():
        # Try relative to script location first
        script_dir = Path(__file__).parent.parent
        if (script_dir / config_path).exists():
            config_path = script_dir / config_path
        else:
            config_path = Path.cwd() / config_path

    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)

    # Create monitor
    monitor = MCPServiceMonitor(str(config_path), args.log_dir)

    if args.status:
        # Just show status and exit
        monitor.start_monitoring()
        time.sleep(5)  # Give services time to start

        status = monitor.status()
        print("\nMCP Service Status:")
        print("-" * 50)
        for service_name, info in status.items():
            print(
                f"{service_name:20} {'Running' if info['running'] else 'Stopped':10} "
                f"PID: {info['pid'] or 'N/A':8} Port: {info['port']:5} "
                f"Healthy: {info['healthy']}"
            )
        print("-" * 50)

        monitor.stop_monitoring()
    else:
        # Run continuous monitoring
        monitor.run()


if __name__ == "__main__":
    main()
