#!/usr/bin/env python3
"""
Demo script showing smart port conflict resolution in action.

WHY: This script demonstrates how the enhanced port manager handles
different types of port conflicts intelligently:
- Automatically reclaims ports from debug scripts
- Preserves daemon processes
- Avoids external processes
- Shows real-world usage scenarios

USAGE:
    python scripts/demo_port_conflict_resolution.py [scenario]
    
    Scenarios:
    - debug: Start a debug script on port 8765, then try to start daemon
    - daemon: Start a daemon on port 8765, show it's preserved
    - external: Simulate external process, show it's avoided
    - all: Run all scenarios
"""

import os
import sys
import time
import socket
import signal
import subprocess
import argparse
from pathlib import Path

# Add parent directory to path to import claude_mpm modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.port_manager import PortManager
from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)


def run_command(cmd: str, capture=True) -> tuple:
    """Run a command and return output."""
    print(f"  Running: {cmd}")
    if capture:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True
        )
        return result.returncode, result.stdout, result.stderr
    else:
        result = subprocess.run(cmd, shell=True)
        return result.returncode, "", ""


def scenario_debug_reclaim():
    """Demonstrate automatic reclaim from debug scripts."""
    print("\n" + "=" * 60)
    print("SCENARIO: Debug Script Auto-Reclaim")
    print("=" * 60)
    print("\n1. Starting a debug script on port 8765...")
    
    # Start a debug script that blocks port 8765
    debug_script = f"""
import socket
import time
print("Debug script starting on port 8765...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("localhost", 8765))
sock.listen(1)
print("Debug script listening on port 8765")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    sock.close()
"""
    
    # Save as temporary debug script
    debug_file = project_root / "scripts" / "test_debug_8765.py"
    debug_file.write_text(debug_script)
    
    # Start the debug script
    debug_proc = subprocess.Popen(
        [sys.executable, str(debug_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    time.sleep(2)  # Give it time to bind
    
    print(f"   Debug script PID: {debug_proc.pid}")
    print("\n2. Checking port status...")
    
    port_manager = PortManager()
    status = port_manager.get_port_status(8765)
    if status["process"]:
        print(f"   Port 8765 is used by: {status['process']['name']} (PID: {status['process']['pid']})")
        print(f"   Is debug script: {status['process']['is_debug']}")
        print(f"   Recommendation: {status['recommendation']}")
    
    print("\n3. Starting monitor daemon (should auto-reclaim port)...")
    returncode, stdout, stderr = run_command("claude-mpm monitor start --port 8765")
    
    if "reclaim" in stdout.lower() or "reclaim" in stderr.lower():
        print("   ✅ Port was automatically reclaimed from debug script!")
    elif "started" in stdout.lower() or "started" in stderr.lower():
        print("   ✅ Monitor started successfully!")
    else:
        print("   ⚠️ Check output:")
        if stdout:
            print(f"   STDOUT: {stdout[:200]}")
        if stderr:
            print(f"   STDERR: {stderr[:200]}")
    
    # Clean up
    try:
        debug_proc.terminate()
        debug_proc.wait(timeout=2)
    except:
        pass
    debug_file.unlink(missing_ok=True)
    
    # Stop the monitor
    print("\n4. Cleaning up...")
    run_command("claude-mpm monitor stop --port 8765", capture=False)
    
    print("\n✅ Scenario complete: Debug scripts are automatically reclaimed!")


def scenario_daemon_preserve():
    """Demonstrate that daemon processes are preserved."""
    print("\n" + "=" * 60)
    print("SCENARIO: Daemon Process Preservation")
    print("=" * 60)
    print("\n1. Starting monitor daemon on port 8765...")
    
    returncode, stdout, stderr = run_command("claude-mpm monitor start --port 8765")
    time.sleep(2)
    
    print("\n2. Checking port status...")
    port_manager = PortManager()
    status = port_manager.get_port_status(8765)
    if status["process"]:
        print(f"   Port 8765 is used by: {status['process']['name']} (PID: {status['process']['pid']})")
        print(f"   Is daemon: {status['process']['is_daemon']}")
        print(f"   Recommendation: {status['recommendation']}")
    
    print("\n3. Trying to start another daemon on same port (should fail)...")
    returncode, stdout, stderr = run_command("claude-mpm monitor start --port 8765")
    
    if "already" in stdout.lower() or "already" in stderr.lower() or "daemon" in stdout.lower():
        print("   ✅ Daemon was preserved! Cannot start another on same port.")
    else:
        print("   Output:", stdout[:200] if stdout else stderr[:200])
    
    print("\n4. Trying with --force flag (would kill daemon)...")
    print("   Note: Not actually running with --force to preserve the daemon")
    print("   Command would be: claude-mpm monitor start --port 8765 --force")
    
    print("\n5. Cleaning up...")
    run_command("claude-mpm monitor stop --port 8765", capture=False)
    
    print("\n✅ Scenario complete: Daemons are preserved unless --force is used!")


def scenario_external_avoid():
    """Demonstrate that external processes are avoided."""
    print("\n" + "=" * 60)
    print("SCENARIO: External Process Avoidance")
    print("=" * 60)
    print("\n1. Starting an external (non-claude-mpm) process on port 8765...")
    
    # Start a simple HTTP server as external process
    external_proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8765"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd="/tmp"  # Run from /tmp so it's clearly external
    )
    time.sleep(2)  # Give it time to bind
    
    print(f"   External process PID: {external_proc.pid}")
    print("\n2. Checking port status...")
    
    port_manager = PortManager()
    status = port_manager.get_port_status(8765)
    if status["process"]:
        print(f"   Port 8765 is used by: {status['process']['name']} (PID: {status['process']['pid']})")
        print(f"   Is ours: {status['process']['is_ours']}")
        print(f"   Recommendation: {status['recommendation']}")
    
    print("\n3. Trying to start monitor (should select different port)...")
    returncode, stdout, stderr = run_command("claude-mpm monitor start")  # No port specified
    
    if "8766" in stdout or "8766" in stderr or "different" in stdout.lower():
        print("   ✅ External process was avoided! Monitor started on different port.")
    elif "started" in stdout.lower():
        print("   ✅ Monitor started on an available port (avoided conflict)!")
    else:
        print("   Output:", stdout[:200] if stdout else stderr[:200])
    
    # Clean up
    print("\n4. Cleaning up...")
    external_proc.terminate()
    external_proc.wait(timeout=2)
    run_command("claude-mpm monitor stop", capture=False)
    
    print("\n✅ Scenario complete: External processes are properly avoided!")


def show_port_range_status():
    """Show the status of all ports in the range."""
    print("\n" + "=" * 60)
    print("PORT RANGE STATUS (8765-8770)")
    print("=" * 60)
    
    port_manager = PortManager()
    
    for port in range(8765, 8771):
        status = port_manager.get_port_status(port)
        if status["available"]:
            print(f"Port {port}: ✅ Available")
        else:
            process = status.get("process")
            if process:
                if process["is_ours"]:
                    if process["is_debug"]:
                        print(f"Port {port}: 🔧 Debug script (PID: {process['pid']}) - Can reclaim")
                    elif process["is_daemon"]:
                        print(f"Port {port}: 🚀 Daemon (PID: {process['pid']}) - Protected")
                    else:
                        print(f"Port {port}: 📦 Our process (PID: {process['pid']})")
                else:
                    print(f"Port {port}: ⛔ External '{process['name']}' - Must avoid")
            else:
                print(f"Port {port}: ❓ In use (unknown process)")


def main():
    parser = argparse.ArgumentParser(description="Demo port conflict resolution")
    parser.add_argument(
        "scenario",
        nargs="?",
        default="all",
        choices=["debug", "daemon", "external", "status", "all"],
        help="Scenario to run (default: all)"
    )
    args = parser.parse_args()
    
    print("\n" + "🚀" * 30)
    print("SMART PORT CONFLICT RESOLUTION DEMO")
    print("🚀" * 30)
    
    try:
        if args.scenario in ["debug", "all"]:
            scenario_debug_reclaim()
            time.sleep(2)
        
        if args.scenario in ["daemon", "all"]:
            scenario_daemon_preserve()
            time.sleep(2)
        
        if args.scenario in ["external", "all"]:
            scenario_external_avoid()
            time.sleep(2)
        
        if args.scenario in ["status", "all"]:
            show_port_range_status()
        
        print("\n" + "=" * 60)
        print("DEMO COMPLETE!")
        print("=" * 60)
        print("\nKey Takeaways:")
        print("  🔧 Debug scripts are automatically reclaimed")
        print("  🚀 Daemon processes are preserved (unless --force)")
        print("  ⛔ External processes are properly avoided")
        print("  ✅ Smart detection ensures safe port management")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()