#!/usr/bin/env python3
"""
Cleanup script for redundant MCP processes.

WHY: Multiple MCP server instances can accumulate over time, each consuming
400MB+ of memory. This script identifies and cleans up redundant processes.

USAGE:
    python scripts/cleanup_mcp_processes.py [--dry-run]
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def find_mcp_processes():
    """Find all MCP-related processes."""
    try:
        # Use ps to find processes
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            check=True
        )
        
        processes = []
        for line in result.stdout.splitlines():
            # Look for MCP-related processes
            if any(keyword in line.lower() for keyword in ["mcp", "vector_search", "claude-mpm"]):
                # Skip the grep process itself
                if "grep" not in line:
                    parts = line.split(None, 10)
                    if len(parts) >= 11:
                        pid = int(parts[1])
                        cpu = parts[2]
                        mem = parts[3]
                        vsz = parts[4]
                        rss = parts[5]
                        cmd = parts[10]
                        
                        # Parse memory usage (RSS in KB)
                        try:
                            rss_mb = int(rss) / 1024
                        except:
                            rss_mb = 0
                        
                        processes.append({
                            "pid": pid,
                            "cpu": cpu,
                            "mem": mem,
                            "rss_mb": rss_mb,
                            "cmd": cmd
                        })
        
        return processes
        
    except subprocess.CalledProcessError as e:
        print(f"Error running ps: {e}", file=sys.stderr)
        return []


def identify_redundant_processes(processes):
    """Identify which processes are redundant."""
    # Group processes by type
    mcp_servers = []
    vector_search = []
    other = []
    
    for proc in processes:
        cmd = proc["cmd"]
        if "mcp_vector_search" in cmd or "vector_search" in cmd:
            vector_search.append(proc)
        elif "mcp server" in cmd or "mcp_server" in cmd:
            mcp_servers.append(proc)
        else:
            other.append(proc)
    
    # Identify redundant processes (keep only the newest one of each type)
    redundant = []
    
    # For vector search, keep only one (the one with lowest PID, likely oldest and fully loaded)
    if len(vector_search) > 1:
        # Sort by PID (ascending)
        vector_search.sort(key=lambda x: x["pid"])
        # Keep the first one, mark others as redundant
        redundant.extend(vector_search[1:])
    
    # For MCP servers, keep a reasonable number (3-5)
    if len(mcp_servers) > 5:
        # Sort by PID (ascending)
        mcp_servers.sort(key=lambda x: x["pid"])
        # Keep the first 3, mark others as redundant
        redundant.extend(mcp_servers[3:])
    
    return redundant


def cleanup_process(pid, dry_run=False):
    """Clean up a single process."""
    if dry_run:
        print(f"  [DRY RUN] Would terminate PID {pid}")
        return True
    
    try:
        # Try graceful termination first
        os.kill(pid, signal.SIGTERM)
        print(f"  Sent SIGTERM to PID {pid}")
        
        # Wait a bit for process to terminate
        time.sleep(1)
        
        # Check if process still exists
        try:
            os.kill(pid, 0)  # Signal 0 just checks if process exists
            # Process still running, force kill
            os.kill(pid, signal.SIGKILL)
            print(f"  Force killed PID {pid}")
        except ProcessLookupError:
            # Process already terminated
            pass
        
        return True
        
    except ProcessLookupError:
        print(f"  Process {pid} already terminated")
        return True
    except PermissionError:
        print(f"  Permission denied to terminate PID {pid}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  Error terminating PID {pid}: {e}", file=sys.stderr)
        return False


def main():
    """Main cleanup function."""
    parser = argparse.ArgumentParser(description="Clean up redundant MCP processes")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed process information"
    )
    args = parser.parse_args()
    
    print("🔍 Searching for MCP processes...")
    processes = find_mcp_processes()
    
    if not processes:
        print("✅ No MCP processes found")
        return 0
    
    print(f"\n📊 Found {len(processes)} MCP-related processes:")
    
    # Calculate total memory usage
    total_memory = sum(p["rss_mb"] for p in processes)
    
    # Show process summary
    for proc in processes:
        if args.verbose:
            print(f"  PID {proc['pid']:6d}: {proc['rss_mb']:6.1f} MB - {proc['cmd'][:80]}")
        else:
            # Shorten command for display
            cmd_short = proc["cmd"].split()[-1] if proc["cmd"] else "unknown"
            if "/" in cmd_short:
                cmd_short = cmd_short.split("/")[-1]
            print(f"  PID {proc['pid']:6d}: {proc['rss_mb']:6.1f} MB - {cmd_short}")
    
    print(f"\n💾 Total memory usage: {total_memory:.1f} MB")
    
    # Identify redundant processes
    redundant = identify_redundant_processes(processes)
    
    if not redundant:
        print("\n✅ No redundant processes found")
        return 0
    
    redundant_memory = sum(p["rss_mb"] for p in redundant)
    print(f"\n⚠️  Found {len(redundant)} redundant processes using {redundant_memory:.1f} MB:")
    
    for proc in redundant:
        cmd_short = proc["cmd"].split()[-1] if proc["cmd"] else "unknown"
        if "/" in cmd_short:
            cmd_short = cmd_short.split("/")[-1]
        print(f"  PID {proc['pid']:6d}: {proc['rss_mb']:6.1f} MB - {cmd_short}")
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No processes will be terminated")
    else:
        print("\n🧹 Cleaning up redundant processes...")
    
    # Clean up redundant processes
    success_count = 0
    for proc in redundant:
        if cleanup_process(proc["pid"], args.dry_run):
            success_count += 1
    
    if not args.dry_run:
        print(f"\n✅ Cleaned up {success_count}/{len(redundant)} processes")
        print(f"💾 Freed approximately {redundant_memory:.1f} MB of memory")
    else:
        print(f"\n📊 Would clean up {len(redundant)} processes")
        print(f"💾 Would free approximately {redundant_memory:.1f} MB of memory")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())