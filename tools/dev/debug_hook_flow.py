#!/usr/bin/env python3
"""Debug the entire hook flow from Claude to Socket.IO"""

import os
import subprocess
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def check_environment():
    """Check environment variables"""
    print("=== Environment Check ===")
    print(
        f"CLAUDE_MPM_HOOK_DEBUG: {os.environ.get('CLAUDE_MPM_HOOK_DEBUG', 'Not set')}"
    )
    print(
        f"CLAUDE_MPM_SOCKETIO_PORT: {os.environ.get('CLAUDE_MPM_SOCKETIO_PORT', 'Not set')}"
    )
    print(f"PYTHONPATH includes src: {'src' in os.environ.get('PYTHONPATH', '')}")
    print()


def check_hook_wrapper():
    """Check if hook wrapper is in place"""
    print("=== Hook Wrapper Check ===")
    wrapper_path = os.path.expanduser("~/.claude/claude_code/hook")
    if os.path.exists(wrapper_path):
        print(f"✅ Hook wrapper exists at: {wrapper_path}")
        # Check if it points to our hook handler
        with open(wrapper_path) as f:
            content = f.read()
            if "claude_mpm" in content:
                print("✅ Hook wrapper contains claude_mpm reference")
            else:
                print("❌ Hook wrapper doesn't reference claude_mpm")
                print(f"Content preview: {content[:200]}...")
    else:
        print(f"❌ Hook wrapper not found at: {wrapper_path}")
    print()


def test_hook_handler_directly():
    """Test the hook handler directly"""
    print("=== Direct Hook Handler Test ===")

    # Set environment
    os.environ["CLAUDE_MPM_HOOK_DEBUG"] = "true"
    os.environ["CLAUDE_MPM_SOCKETIO_PORT"] = "8765"

    try:
        from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        print("✅ Hook handler created")

        # Test initialization
        handler._init_connection_pool()
        print("✅ Connection pool initialized")

        # Create a test hook event
        test_event = {
            "action": "hook",
            "hook": {
                "type": "user_prompt_submitted",
                "prompt": "Test prompt for debugging",
            },
        }

        # Simulate hook handling
        handler.handle_hook(test_event)
        print("✅ Test hook handled")

    except Exception as e:
        print(f"❌ Error in hook handler: {e}")
        import traceback

        traceback.print_exc()
    print()


def check_socketio_connection():
    """Check if we can connect to Socket.IO server"""
    print("=== Socket.IO Connection Test ===")

    try:
        import socketio

        sio = socketio.Client()

        @sio.event
        def connect():
            print("✅ Connected to Socket.IO server")

        @sio.event
        def connect_error(data):
            print(f"❌ Connection error: {data}")

        print("Attempting to connect to localhost:8765...")
        sio.connect("http://localhost:8765", wait=True, wait_timeout=5)

        if sio.connected:
            print("✅ Successfully connected")
            # Try emitting a test event
            sio.emit("test_event", {"message": "Debug test"})
            print("✅ Test event emitted")
            sio.disconnect()
        else:
            print("❌ Failed to connect")

    except Exception as e:
        print(f"❌ Socket.IO connection error: {e}")
    print()


def test_hook_via_subprocess():
    """Test hook by running a subprocess that should trigger hooks"""
    print("=== Subprocess Hook Test ===")

    # Create a test script that the hook handler will process
    test_script = """
import json
import sys

# Simulate a user prompt hook
hook_data = {
    "action": "hook",
    "hook": {
        "type": "user_prompt_submitted",
        "prompt": "Debug test prompt"
    }
}

print(json.dumps(hook_data))
sys.stdout.flush()
"""

    # Set environment
    env = os.environ.copy()
    env["CLAUDE_MPM_HOOK_DEBUG"] = "true"
    env["CLAUDE_MPM_SOCKETIO_PORT"] = "8765"

    # Find hook handler path
    hook_handler = os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
        "claude_mpm",
        "hooks",
        "claude_hooks",
        "hook_handler.py",
    )

    print(f"Running hook handler: {hook_handler}")

    # Run the hook handler as it would be run by Claude
    proc = subprocess.Popen(
        [sys.executable, hook_handler],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )

    # Send test hook data
    stdout, stderr = proc.communicate(input=test_script)

    print("STDOUT:", stdout)
    print("STDERR:", stderr)
    print()


def check_hook_installation():
    """Check if hooks are properly installed"""
    print("=== Hook Installation Check ===")

    # Run the install hooks script
    install_script = os.path.join(os.path.dirname(__file__), "install_hooks.py")
    if os.path.exists(install_script):
        print("Running hook installation...")
        result = subprocess.run(
            [sys.executable, install_script], capture_output=True, text=True, check=False
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
    else:
        print("❌ install_hooks.py not found")
    print()


def main():
    print("Claude MPM Hook Flow Debugger")
    print("=" * 50)

    check_environment()
    check_hook_wrapper()
    check_socketio_connection()
    test_hook_handler_directly()
    test_hook_via_subprocess()
    check_hook_installation()

    print("\n=== Summary ===")
    print("1. Check if Socket.IO server is running on port 8765")
    print("2. Ensure CLAUDE_MPM_HOOK_DEBUG=true is set")
    print("3. Ensure CLAUDE_MPM_SOCKETIO_PORT=8765 is set")
    print("4. Verify hook wrapper is installed at ~/.claude/claude_code/hook")
    print("5. Run Claude with --monitor flag")


if __name__ == "__main__":
    main()
