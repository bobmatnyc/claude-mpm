#!/usr/bin/env python3
"""Migration script to help transition from HTTP-based hooks to JSON-RPC hooks."""

import subprocess
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def check_hook_service_running():
    """Check if the old HTTP hook service is running."""
    try:
        import requests

        response = requests.get("http://localhost:5001/health", timeout=1)
        return response.status_code == 200
    except:
        return False


def stop_hook_service():
    """Attempt to stop the HTTP hook service."""
    print("Attempting to stop HTTP hook service...")

    # Try to find and kill the process
    try:
        result = subprocess.run(
            ["pgrep", "-f", "hook_service.py"], capture_output=True, text=True, check=False
        )

        if result.returncode == 0:
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                if pid:
                    subprocess.run(["kill", pid], check=False)
                    print(f"  Stopped process {pid}")
            return True
        print("  No hook service process found")
        return False
    except Exception as e:
        print(f"  Error stopping service: {e}")
        return False


def test_json_rpc_hooks():
    """Test that JSON-RPC hooks are working."""
    from claude_mpm.hooks.json_rpc_hook_client import JSONRPCHookClient

    print("\nTesting JSON-RPC hooks...")
    try:
        client = JSONRPCHookClient()
        health = client.health_check()

        if health["status"] == "healthy":
            print("  ✓ JSON-RPC hooks are working")
            print(f"  ✓ Found {health['hook_count']} hooks")

            # Test execution
            results = client.execute_submit_hook("test prompt")
            print(f"  ✓ Successfully executed {len(results)} hooks")
            return True
        print(f"  ✗ Health check failed: {health}")
        return False
    except Exception as e:
        print(f"  ✗ Error testing JSON-RPC hooks: {e}")
        return False


def update_environment():
    """Update environment configuration."""
    print("\nUpdating environment configuration...")

    # Check for .env file
    env_file = Path(".env")
    if env_file.exists():
        content = env_file.read_text()

        # Remove old HTTP hook URL if present
        lines = content.split("\n")
        new_lines = []
        updated = False

        for line in lines:
            if line.startswith("CLAUDE_MPM_HOOKS_URL="):
                # Comment out old URL
                new_lines.append(f"# {line}  # Deprecated - using JSON-RPC hooks")
                updated = True
            elif line.startswith("CLAUDE_MPM_HOOKS_JSON_RPC="):
                # Update to ensure JSON-RPC is enabled
                new_lines.append("CLAUDE_MPM_HOOKS_JSON_RPC=true")
                updated = True
            else:
                new_lines.append(line)

        # Add JSON-RPC setting if not present
        if not any("CLAUDE_MPM_HOOKS_JSON_RPC" in line for line in lines):
            new_lines.append("\n# Use JSON-RPC hooks (no HTTP server needed)")
            new_lines.append("CLAUDE_MPM_HOOKS_JSON_RPC=true")
            updated = True

        if updated:
            env_file.write_text("\n".join(new_lines))
            print("  ✓ Updated .env file")
        else:
            print("  ✓ .env file already up to date")
    else:
        print("  No .env file found (OK - JSON-RPC is default)")


def main():
    """Run the migration process."""
    print("claude-mpm Hook System Migration")
    print("HTTP → JSON-RPC")
    print("=" * 50)

    # 1. Check if HTTP service is running
    print("\n1. Checking for HTTP hook service...")
    if check_hook_service_running():
        print("  ⚠ HTTP hook service is running on port 5001")
        if stop_hook_service():
            print("  ✓ Successfully stopped HTTP hook service")
        else:
            print("  ⚠ Could not stop service automatically")
            print("  Please stop it manually: pkill -f hook_service.py")
    else:
        print("  ✓ No HTTP hook service running")

    # 2. Test JSON-RPC hooks
    if not test_json_rpc_hooks():
        print("\n⚠ JSON-RPC hooks test failed!")
        print("Please check your installation and try again.")
        return 1

    # 3. Update environment
    update_environment()

    # 4. Summary
    print("\n" + "=" * 50)
    print("Migration Summary:")
    print("  ✓ HTTP hook service stopped (if running)")
    print("  ✓ JSON-RPC hooks tested successfully")
    print("  ✓ Environment configuration updated")
    print("\nYour hook system has been migrated to JSON-RPC!")
    print("\nBenefits:")
    print("  • No port exhaustion issues")
    print("  • No persistent server processes")
    print("  • Better resource efficiency")
    print("  • Simpler deployment")

    print("\nTo revert to HTTP hooks (not recommended):")
    print("  export CLAUDE_MPM_HOOKS_JSON_RPC=false")
    print("  python -m claude_mpm.services.hook_service")

    return 0


if __name__ == "__main__":
    sys.exit(main())
