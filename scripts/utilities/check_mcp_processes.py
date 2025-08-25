#!/usr/bin/env python3
"""
MCP Process Diagnostic Script
==============================

This script checks for running MCP server processes, displays their status,
and can optionally clean up orphaned processes.

WHY: Multiple MCP server instances can accumulate due to Claude Code's
spawning behavior, leading to memory issues. This tool helps diagnose and
manage these processes.

DESIGN DECISION: Use both PID files and system process scanning to provide
comprehensive visibility into all MCP-related processes.
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import psutil


def format_bytes(bytes_value: int) -> str:
    """
    Format bytes into human-readable string.

    Args:
        bytes_value: Number of bytes

    Returns:
        str: Formatted string (e.g., "1.5 GB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


def format_duration(start_time: float) -> str:
    """
    Format duration from start time to now.

    Args:
        start_time: Unix timestamp of start time

    Returns:
        str: Formatted duration (e.g., "2h 15m")
    """
    duration = datetime.now(timezone.utc).timestamp() - start_time

    if duration < 60:
        return f"{int(duration)}s"
    if duration < 3600:
        minutes = int(duration / 60)
        seconds = int(duration % 60)
        return f"{minutes}m {seconds}s"
    hours = int(duration / 3600)
    minutes = int((duration % 3600) / 60)
    return f"{hours}h {minutes}m"


class MCPProcessChecker:
    """Check and manage MCP server processes."""

    def __init__(self):
        """Initialize the process checker."""
        self.pid_dir = Path(tempfile.gettempdir()) / "claude-mpm-mcp"
        self.current_pid = os.getpid()

    def get_pid_file_info(self) -> List[Dict]:
        """
        Get information from PID files.

        Returns:
            List of process info dictionaries
        """
        if not self.pid_dir.exists():
            return []

        pid_info_list = []
        for pid_file in self.pid_dir.glob("mcp_server_*.pid"):
            try:
                with open(pid_file) as f:
                    info = json.load(f)
                    info["pid_file"] = str(pid_file)
                    pid_info_list.append(info)
            except Exception as e:
                print(f"Warning: Could not read {pid_file}: {e}")

        return pid_info_list

    def find_mcp_processes(self) -> List[psutil.Process]:
        """
        Find all MCP-related processes using psutil.

        Returns:
            List of Process objects
        """
        mcp_processes = []

        for proc in psutil.process_iter(
            ["pid", "name", "cmdline", "create_time", "memory_info"]
        ):
            try:
                cmdline = proc.info.get("cmdline", [])
                if cmdline and any("mcp" in str(arg).lower() for arg in cmdline):
                    # Check if it's related to claude-mpm
                    if any(
                        "claude-mpm" in str(arg)
                        or "mcp_wrapper" in str(arg)
                        or "stdio_server" in str(arg)
                        for arg in cmdline
                    ):
                        mcp_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return mcp_processes

    def get_process_details(self, proc: psutil.Process) -> Dict:
        """
        Get detailed information about a process.

        Args:
            proc: psutil Process object

        Returns:
            Dictionary with process details
        """
        try:
            memory_info = proc.memory_info()
            return {
                "pid": proc.pid,
                "name": proc.name(),
                "cmdline": " ".join(proc.cmdline()),
                "create_time": proc.create_time(),
                "memory_rss": memory_info.rss,
                "memory_vms": memory_info.vms,
                "cpu_percent": proc.cpu_percent(interval=0.1),
                "status": proc.status(),
                "ppid": proc.ppid(),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            return {"pid": proc.pid, "error": str(e)}

    def display_processes(self, verbose: bool = False):
        """
        Display information about MCP processes.

        Args:
            verbose: Show detailed information
        """
        print("=" * 80)
        print("🔍 MCP Process Status Report")
        print("=" * 80)
        print(f"Report generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Check PID files
        pid_file_info = self.get_pid_file_info()
        print(f"📁 PID Files Found: {len(pid_file_info)}")

        if pid_file_info:
            print("\nPID File Information:")
            for info in pid_file_info:
                pid = info.get("pid", "unknown")
                start_time = info.get("start_time", "unknown")
                ppid = info.get("ppid", "unknown")

                # Check if process is still running
                try:
                    proc = psutil.Process(pid)
                    status = "✅ Running"
                except (psutil.NoSuchProcess, ValueError):
                    status = "❌ Not running (stale)"

                print(f"  - PID {pid}: {status}")
                if verbose:
                    print(f"    Started: {start_time}")
                    print(f"    Parent PID: {ppid}")
                    print(f"    PID File: {info.get('pid_file', 'unknown')}")

        # Find actual running processes
        print("\n🔄 Running MCP Processes:")
        mcp_processes = self.find_mcp_processes()

        if not mcp_processes:
            print("  No MCP processes found")
        else:
            total_memory = 0
            process_table = []

            for proc in mcp_processes:
                details = self.get_process_details(proc)
                if "error" not in details:
                    total_memory += details["memory_rss"]
                    process_table.append(details)

            # Sort by memory usage
            process_table.sort(key=lambda x: x.get("memory_rss", 0), reverse=True)

            # Display process table
            print(f"\n  Found {len(process_table)} MCP process(es):")
            print("\n  PID     Memory    CPU%  Duration  Status    Command")
            print("  " + "-" * 70)

            for details in process_table:
                pid = details["pid"]
                memory = format_bytes(details["memory_rss"])
                cpu = details["cpu_percent"]
                duration = format_duration(details["create_time"])
                status = details["status"]

                # Truncate command for display
                cmd = details["cmdline"]
                if len(cmd) > 40 and not verbose:
                    cmd = cmd[:37] + "..."

                print(
                    f"  {pid:<7} {memory:<9} {cpu:>4.1f}% {duration:<9} {status:<9} {cmd}"
                )

                if verbose:
                    print(f"    Full command: {details['cmdline']}")
                    print(f"    Parent PID: {details['ppid']}")
                    print(f"    Virtual Memory: {format_bytes(details['memory_vms'])}")

            print(f"\n  📊 Total Memory Usage: {format_bytes(total_memory)}")

        # Check for issues
        print("\n⚠️  Potential Issues:")
        issues_found = False

        if len(mcp_processes) > 3:
            print(f"  - Multiple instances detected ({len(mcp_processes)} processes)")
            print("    Consider killing older instances to free memory")
            issues_found = True

        stale_pids = [
            info
            for info in pid_file_info
            if not self.is_process_running(info.get("pid", -1))
        ]
        if stale_pids:
            print(f"  - Found {len(stale_pids)} stale PID file(s)")
            print("    Run with --cleanup to remove them")
            issues_found = True

        if total_memory > 500 * 1024 * 1024:  # 500 MB
            print(f"  - High memory usage detected: {format_bytes(total_memory)}")
            print("    Consider restarting Claude Code")
            issues_found = True

        if not issues_found:
            print("  ✅ No issues detected")

    def is_process_running(self, pid: int) -> bool:
        """
        Check if a process is running.

        Args:
            pid: Process ID

        Returns:
            bool: True if running
        """
        try:
            proc = psutil.Process(pid)
            return proc.is_running()
        except (psutil.NoSuchProcess, ValueError):
            return False

    def cleanup_stale_files(self) -> int:
        """
        Clean up stale PID files.

        Returns:
            Number of files cleaned
        """
        if not self.pid_dir.exists():
            return 0

        cleaned = 0
        for pid_file in self.pid_dir.glob("mcp_server_*.pid"):
            try:
                with open(pid_file) as f:
                    info = json.load(f)

                pid = info.get("pid", -1)
                if not self.is_process_running(pid):
                    pid_file.unlink()
                    print(f"  Removed stale PID file for process {pid}")
                    cleaned += 1
            except Exception as e:
                print(f"  Warning: Could not process {pid_file}: {e}")

        return cleaned

    def kill_process(self, pid: int, force: bool = False) -> bool:
        """
        Kill a process.

        Args:
            pid: Process ID
            force: Use SIGKILL instead of SIGTERM

        Returns:
            bool: True if successful
        """
        try:
            proc = psutil.Process(pid)
            if force:
                proc.kill()  # SIGKILL
                print(f"  Force killed process {pid}")
            else:
                proc.terminate()  # SIGTERM
                print(f"  Terminated process {pid}")
            return True
        except psutil.NoSuchProcess:
            print(f"  Process {pid} not found")
            return False
        except psutil.AccessDenied:
            print(f"  Access denied to kill process {pid}")
            return False
        except Exception as e:
            print(f"  Error killing process {pid}: {e}")
            return False

    def kill_all_except_latest(self, force: bool = False) -> int:
        """
        Kill all MCP processes except the most recent one.

        Args:
            force: Use SIGKILL instead of SIGTERM

        Returns:
            Number of processes killed
        """
        mcp_processes = self.find_mcp_processes()

        if len(mcp_processes) <= 1:
            print("Only one or no MCP processes found, nothing to kill")
            return 0

        # Sort by creation time (oldest first)
        mcp_processes.sort(key=lambda p: p.create_time())

        # Keep the newest, kill the rest
        to_kill = mcp_processes[:-1]
        killed = 0

        print(f"Killing {len(to_kill)} older MCP process(es)...")
        for proc in to_kill:
            if self.kill_process(proc.pid, force):
                killed += 1

        return killed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check and manage MCP server processes"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed information"
    )
    parser.add_argument(
        "-c", "--cleanup", action="store_true", help="Clean up stale PID files"
    )
    parser.add_argument(
        "-k",
        "--kill-old",
        action="store_true",
        help="Kill all MCP processes except the newest",
    )
    parser.add_argument("--kill-pid", type=int, help="Kill a specific process by PID")
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Use SIGKILL instead of SIGTERM when killing processes",
    )

    args = parser.parse_args()

    # Check if psutil is installed
    try:
        import psutil
    except ImportError:
        print("Error: psutil is not installed")
        print("Install it with: pip install psutil")
        sys.exit(1)

    checker = MCPProcessChecker()

    # Handle specific actions
    if args.kill_pid:
        print(f"Killing process {args.kill_pid}...")
        if checker.kill_process(args.kill_pid, args.force):
            print("✅ Process killed successfully")
        else:
            print("❌ Failed to kill process")
            sys.exit(1)
    elif args.kill_old:
        killed = checker.kill_all_except_latest(args.force)
        print(f"✅ Killed {killed} process(es)")
    elif args.cleanup:
        print("Cleaning up stale PID files...")
        cleaned = checker.cleanup_stale_files()
        print(f"✅ Cleaned up {cleaned} stale PID file(s)")
    else:
        # Default: show status
        checker.display_processes(args.verbose)

    return 0


if __name__ == "__main__":
    sys.exit(main())
