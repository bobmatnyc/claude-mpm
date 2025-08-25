#!/usr/bin/env python3
"""
Verify Socket.IO stability fixes are properly configured.

WHY: Quick verification that all stability improvements are in place
and working as expected.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_server_config():
    """Check server configuration."""
    print("🔍 Checking Socket.IO Server Configuration...")

    try:

        # Read the source to verify actual values
        core_file = (
            Path(__file__).parent.parent
            / "src/claude_mpm/services/socketio/server/core.py"
        )
        content = core_file.read_text()

        checks = {
            "ping_interval=25": "✅ Engine.IO ping interval: 25 seconds",
            "ping_timeout=60": "✅ Engine.IO ping timeout: 60 seconds",
            "max_http_buffer_size=1e8": "✅ Max buffer size: 100MB",
        }

        for check, message in checks.items():
            if check in content:
                print(f"  {message}")
            else:
                print(f"  ❌ Missing: {check}")
                return False

    except Exception as e:
        print(f"  ❌ Error checking server config: {e}")
        return False

    return True


def check_handler_config():
    """Check connection handler configuration."""
    print("\n🔍 Checking Connection Handler Configuration...")

    try:

        # Read the source to verify actual values
        handler_file = (
            Path(__file__).parent.parent
            / "src/claude_mpm/services/socketio/handlers/connection.py"
        )
        content = handler_file.read_text()

        checks = {
            "self.ping_interval = 45": "✅ Custom ping interval: 45 seconds",
            "self.ping_timeout = 20": "✅ Custom ping timeout: 20 seconds",
            "self.stale_check_interval = 90": "✅ Stale check interval: 90 seconds",
        }

        for check, message in checks.items():
            if check in content:
                print(f"  {message}")
            else:
                print(f"  ❌ Missing: {check}")
                return False

    except Exception as e:
        print(f"  ❌ Error checking handler config: {e}")
        return False

    return True


def check_client_config():
    """Check dashboard client configuration."""
    print("\n🔍 Checking Dashboard Client Configuration...")

    try:
        # Read the client source
        client_file = (
            Path(__file__).parent.parent
            / "src/claude_mpm/dashboard/static/js/socket-client.js"
        )
        content = client_file.read_text()

        checks = {
            "reconnectionAttempts: Infinity": "✅ Infinite reconnection attempts",
            "timeout: 20000": "✅ Connection timeout: 20 seconds",
            "pingInterval: 25000": "✅ Client ping interval: 25 seconds",
            "pingTimeout: 60000": "✅ Client ping timeout: 60 seconds",
            "this.pingTimeout = 90000": "✅ Health check timeout: 90 seconds",
        }

        for check, message in checks.items():
            if check in content:
                print(f"  {message}")
            else:
                print(f"  ❌ Missing: {check}")
                return False

    except Exception as e:
        print(f"  ❌ Error checking client config: {e}")
        return False

    return True


def check_relay_config():
    """Check EventBus relay configuration."""
    print("\n🔍 Checking EventBus Relay Configuration...")

    try:

        # Read the source to verify actual values
        relay_file = (
            Path(__file__).parent.parent / "src/claude_mpm/services/event_bus/relay.py"
        )
        content = relay_file.read_text()

        checks = {
            "wait_timeout=10": "✅ Connection timeout: 10 seconds",
            "reconnection=True": "✅ Reconnection enabled",
            "transports=['websocket', 'polling']": "✅ Multiple transports configured",
        }

        for check, message in checks.items():
            if check in content:
                print(f"  {message}")
            else:
                print(f"  ❌ Missing: {check}")
                return False

    except Exception as e:
        print(f"  ❌ Error checking relay config: {e}")
        return False

    return True


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("🚀 SOCKET.IO STABILITY FIXES VERIFICATION")
    print("=" * 60)

    all_good = True

    # Run all checks
    all_good &= check_server_config()
    all_good &= check_handler_config()
    all_good &= check_client_config()
    all_good &= check_relay_config()

    print("\n" + "=" * 60)
    if all_good:
        print("✅ ALL STABILITY FIXES ARE PROPERLY CONFIGURED!")
        print("\nNext steps:")
        print("1. Start the Socket.IO server: claude-mpm monitor")
        print("2. Run stability test: python scripts/test_socketio_stability.py")
        print("3. Monitor dashboard for stable connections")
    else:
        print("❌ SOME CONFIGURATIONS ARE MISSING")
        print("\nPlease review the configurations above and fix any issues.")
    print("=" * 60)

    return 0 if all_good else 1


if __name__ == "__main__":
    sys.exit(main())
