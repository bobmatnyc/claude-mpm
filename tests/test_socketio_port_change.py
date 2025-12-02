#!/usr/bin/env python3
"""Test script to verify Socket.IO port change from 8080 to 8765."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.constants import NetworkConfig


def test_port_configuration():
    """Test that Socket.IO ports have been correctly updated."""
    print("Testing Socket.IO port configuration...")
    print("=" * 50)

    # Test DEFAULT_SOCKETIO_PORT
    assert NetworkConfig.DEFAULT_SOCKETIO_PORT == 8765, (
        f"DEFAULT_SOCKETIO_PORT should be 8765, got {NetworkConfig.DEFAULT_SOCKETIO_PORT}"
    )
    print(f"✓ DEFAULT_SOCKETIO_PORT: {NetworkConfig.DEFAULT_SOCKETIO_PORT}")

    # Test DEFAULT_DASHBOARD_PORT
    assert NetworkConfig.DEFAULT_DASHBOARD_PORT == 8765, (
        f"DEFAULT_DASHBOARD_PORT should be 8765, got {NetworkConfig.DEFAULT_DASHBOARD_PORT}"
    )
    print(f"✓ DEFAULT_DASHBOARD_PORT: {NetworkConfig.DEFAULT_DASHBOARD_PORT}")

    # Test SOCKETIO_PORT_RANGE
    expected_range = (8765, 8785)
    assert expected_range == NetworkConfig.SOCKETIO_PORT_RANGE, (
        f"SOCKETIO_PORT_RANGE should be {expected_range}, got {NetworkConfig.SOCKETIO_PORT_RANGE}"
    )
    print(
        f"✓ SOCKETIO_PORT_RANGE: {NetworkConfig.SOCKETIO_PORT_RANGE[0]}-{NetworkConfig.SOCKETIO_PORT_RANGE[1]}"
    )

    # Test port range values
    port_start, port_end = NetworkConfig.SOCKETIO_PORT_RANGE
    assert port_start == 8765, f"Port range should start at 8765, got {port_start}"
    assert port_end == 8785, f"Port range should end at 8785, got {port_end}"
    print(f"✓ Port range verified: {port_end - port_start + 1} ports available")

    print("=" * 50)
    print("✅ All Socket.IO port configurations have been successfully updated!")
    print(f"   Default port: {NetworkConfig.DEFAULT_SOCKETIO_PORT}")
    print(
        f"   Port range: {NetworkConfig.SOCKETIO_PORT_RANGE[0]}-{NetworkConfig.SOCKETIO_PORT_RANGE[1]}"
    )
    return True


if __name__ == "__main__":
    try:
        test_port_configuration()
        sys.exit(0)
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
