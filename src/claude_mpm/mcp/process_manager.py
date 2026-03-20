#!/usr/bin/env python3
"""
MCP Process Manager
====================

Provides check and cleanup functionality for MCP server processes.

Merges logic from:
- scripts/utilities/check_mcp_processes.py
- scripts/utilities/cleanup_mcp_processes.py
"""

import argparse
import json
import os
import signal
import subprocess  # nosec B404
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path


def format_bytes(bytes_value: float) -> str:
    """Format bytes into human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


def format_duration(start_time: float) -> str:
    """Format duration from start time to now."""
    duration = datetime.now(UTC).timestamp() - start_time
    if duration < 60:
        return f"{int(duration)}s"
    if duration < 3600:
        minutes = int(duration / 60)
        seconds = int(duration % 60)
        return f"{minutes}m {seconds}s"
    hours = int(duration / 3600)
    minutes = int((duration % 3600) / 60)
    return f"{hours}h {minutes}m"


class MCPProcessManager:
    """Check and manage MCP server processes."""

    def __init__(self) -> None:
        self.pid_dir = Path(tempfile.gettempdir()) / "claude-mpm-mcp"
        self.current_pid = os.getpid()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def is_process_running(self, pid: int) -> bool:
        """Return True if the given PID is alive."""
        try:
            import psutil

            proc = psutil.Process(pid)
            return proc.is_running()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Check logic (from check_mcp_processes.py)
    # ------------------------------------------------------------------

    def check_processes(self) -> list[dict]:
        """
        Return a list of dicts describing running MCP-related processes.

        Each dict contains: pid, name, cmdline, create_time, memory_rss,
        memory_vms, cpu_percent, status, ppid.
        """
        try:
            import psutil
        except ImportError:
            return []

        results: list[dict] = []
        for proc in psutil.process_iter(
            ["pid", "name", "cmdline", "create_time", "memory_info"]
        ):
            try:
                cmdline = proc.info.get("cmdline", []) or []
                if not any("mcp" in str(arg).lower() for arg in cmdline):
                    continue
                if not any(
                    "claude-mpm" in str(arg)
                    or "mcp_wrapper" in str(arg)
                    or "stdio_server" in str(arg)
                    for arg in cmdline
                ):
                    continue
                try:
                    mem = proc.memory_info()
                    results.append(
                        {
                            "pid": proc.pid,
                            "name": proc.name(),
                            "cmdline": " ".join(proc.cmdline()),
                            "create_time": proc.create_time(),
                            "memory_rss": mem.rss,
                            "memory_vms": mem.vms,
                            "cpu_percent": proc.cpu_percent(interval=0.1),
                            "status": proc.status(),
                            "ppid": proc.ppid(),
                        }
                    )
                except Exception:
                    results.append({"pid": proc.pid, "error": "details unavailable"})
            except Exception:
                continue
        return results

    def display_processes(self, verbose: bool = False) -> None:
        """Print a human-readable process status report."""
        try:
            import psutil
        except ImportError:
            print("psutil not installed — install with: pip install psutil")
            return

        print("=" * 80)
        print("MCP Process Status Report")
        print("=" * 80)
        print(f"Report generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}")

        # PID files
        pid_file_info = self._get_pid_file_info()
        print(f"\nPID Files Found: {len(pid_file_info)}")
        for info in pid_file_info:
            pid = info.get("pid", "unknown")
            try:
                psutil.Process(pid)
                status = "Running"
            except Exception:
                status = "Not running (stale)"
            print(f"  - PID {pid}: {status}")
            if verbose:
                print(f"    Started: {info.get('start_time', 'unknown')}")
                print(f"    Parent PID: {info.get('ppid', 'unknown')}")

        # Live processes
        processes = self.check_processes()
        print(f"\nRunning MCP Processes: {len(processes)}")
        if not processes:
            print("  None found")
        else:
            total_mem = sum(p.get("memory_rss", 0) for p in processes)
            processes.sort(key=lambda x: x.get("memory_rss", 0), reverse=True)
            print("  PID     Memory    CPU%  Duration  Status    Command")
            print("  " + "-" * 70)
            for d in processes:
                if "error" in d:
                    continue
                cmd = (
                    d["cmdline"]
                    if verbose
                    else (
                        d["cmdline"][:37] + "..."
                        if len(d["cmdline"]) > 40
                        else d["cmdline"]
                    )
                )
                print(
                    f"  {d['pid']:<7} {format_bytes(d['memory_rss']):<9} "
                    f"{d['cpu_percent']:>4.1f}% {format_duration(d['create_time']):<9} "
                    f"{d['status']:<9} {cmd}"
                )
            print(f"\n  Total Memory Usage: {format_bytes(total_mem)}")

    def _get_pid_file_info(self) -> list[dict]:
        if not self.pid_dir.exists():
            return []
        results = []
        for pid_file in self.pid_dir.glob("mcp_server_*.pid"):
            try:
                with open(pid_file) as f:
                    info = json.load(f)
                info["pid_file"] = str(pid_file)
                results.append(info)
            except Exception as e:
                print(f"Warning: could not read {pid_file}: {e}")
        return results

    # ------------------------------------------------------------------
    # Cleanup logic (from cleanup_mcp_processes.py)
    # ------------------------------------------------------------------

    def cleanup_processes(self, dry_run: bool = False) -> int:
        """
        Find and terminate redundant MCP processes.

        Returns the number of processes terminated (or that would be
        terminated in dry-run mode).
        """
        try:
            result = subprocess.run(  # nosec B603,B607
                ["ps", "aux"], capture_output=True, text=True, check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"Error running ps: {e}", file=sys.stderr)
            return 0

        processes: list[dict] = []
        for line in result.stdout.splitlines():
            if any(kw in line.lower() for kw in ["mcp", "vector_search", "claude-mpm"]):
                if "grep" in line:
                    continue
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    try:
                        pid = int(parts[1])
                    except ValueError:
                        continue
                    try:
                        rss_mb = int(parts[5]) / 1024
                    except Exception:
                        rss_mb = 0.0
                    processes.append(
                        {
                            "pid": pid,
                            "cpu": parts[2],
                            "mem": parts[3],
                            "rss_mb": rss_mb,
                            "cmd": parts[10],
                        }
                    )

        if not processes:
            return 0

        redundant = self._identify_redundant(processes)
        if not redundant:
            return 0

        count = 0
        for proc in redundant:
            if self._terminate_pid(proc["pid"], dry_run=dry_run):
                count += 1
        return count

    def _identify_redundant(self, processes: list[dict]) -> list[dict]:
        mcp_servers, vector_search, redundant = [], [], []
        for proc in processes:
            cmd = proc["cmd"]
            if "mcp_vector_search" in cmd or "vector_search" in cmd:
                vector_search.append(proc)
            elif "mcp server" in cmd or "mcp_server" in cmd:
                mcp_servers.append(proc)

        if len(vector_search) > 1:
            vector_search.sort(key=lambda x: x["pid"])
            redundant.extend(vector_search[1:])

        if len(mcp_servers) > 5:
            mcp_servers.sort(key=lambda x: x["pid"])
            redundant.extend(mcp_servers[3:])

        return redundant

    def _terminate_pid(self, pid: int, dry_run: bool = False) -> bool:
        if dry_run:
            print(f"  [DRY RUN] Would terminate PID {pid}")
            return True
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"  Sent SIGTERM to PID {pid}")
            time.sleep(1)
            try:
                os.kill(pid, 0)
                os.kill(pid, signal.SIGKILL)
                print(f"  Force killed PID {pid}")
            except ProcessLookupError:
                pass
            return True
        except ProcessLookupError:
            print(f"  Process {pid} already terminated")
            return True
        except PermissionError:
            print(f"  Permission denied for PID {pid}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"  Error terminating PID {pid}: {e}", file=sys.stderr)
            return False

    def cleanup_stale_pid_files(self) -> int:
        """Remove PID files for processes that are no longer running."""
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
                print(f"  Warning: could not process {pid_file}: {e}")
        return cleaned


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Manage MCP server processes")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--check", action="store_true", help="Show process status (default)"
    )
    parser.add_argument(
        "--cleanup", action="store_true", help="Terminate redundant processes"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what cleanup would do"
    )
    parser.add_argument(
        "--clean-pids", action="store_true", help="Remove stale PID files"
    )
    args = parser.parse_args()

    mgr = MCPProcessManager()

    if args.cleanup or args.dry_run:
        n = mgr.cleanup_processes(dry_run=args.dry_run)
        if args.dry_run:
            print(f"Would clean up {n} process(es)")
        else:
            print(f"Cleaned up {n} process(es)")
    elif args.clean_pids:
        n = mgr.cleanup_stale_pid_files()
        print(f"Removed {n} stale PID file(s)")
    else:
        mgr.display_processes(verbose=args.verbose)

    return 0


if __name__ == "__main__":
    sys.exit(main())
