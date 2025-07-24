#!/usr/bin/env python3
"""Test subprocess interaction with Claude."""

import subprocess
import threading
import time
import sys
import os

def test_basic_claude():
    """Test basic Claude subprocess interaction."""
    print("=== Testing Basic Claude Subprocess ===\n")
    
    cmd = ["claude", "--model", "opus", "--dangerously-skip-permissions"]
    print(f"Command: {' '.join(cmd)}")
    
    try:
        # Start process
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0,  # Unbuffered
            env=os.environ.copy()
        )
        
        print(f"Process started with PID: {process.pid}")
        
        # Set up output readers
        def read_stdout():
            while True:
                char = process.stdout.read(1)
                if char:
                    sys.stdout.write(char)
                    sys.stdout.flush()
                else:
                    break
                    
        def read_stderr():
            while True:
                char = process.stderr.read(1)
                if char:
                    sys.stderr.write(f"[ERR] {char}")
                    sys.stderr.flush()
                else:
                    break
        
        # Start reader threads
        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait a moment for Claude to start
        time.sleep(1)
        
        # Send test input
        test_input = "Say 'Hello from subprocess test' and nothing else\n"
        print(f"\n[SENDING]: {test_input.strip()}")
        process.stdin.write(test_input)
        process.stdin.flush()
        
        # Wait for response
        time.sleep(5)
        
        # Send exit
        print("\n[SENDING]: exit")
        process.stdin.write("exit\n")
        process.stdin.flush()
        
        # Wait for process to end
        process.wait(timeout=2)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'process' in locals():
            process.terminate()

def test_pty_mode():
    """Test with pseudo-terminal."""
    print("\n\n=== Testing with PTY (Unix only) ===\n")
    
    try:
        import pty
        import select
        
        # Create pseudo-terminal
        master, slave = pty.openpty()
        
        cmd = ["claude", "--model", "opus", "--dangerously-skip-permissions"]
        print(f"Command: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            text=True
        )
        
        print(f"Process started with PID: {process.pid}")
        
        # Close slave end in parent
        os.close(slave)
        
        # Make master non-blocking
        import fcntl
        flags = fcntl.fcntl(master, fcntl.F_GETFL)
        fcntl.fcntl(master, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        
        # Read initial output
        time.sleep(1)
        while True:
            r, _, _ = select.select([master], [], [], 0)
            if r:
                data = os.read(master, 1024).decode('utf-8', errors='ignore')
                sys.stdout.write(data)
                sys.stdout.flush()
            else:
                break
        
        # Send test input
        test_input = "Say 'Hello from PTY test' and nothing else\n"
        print(f"\n[SENDING]: {test_input.strip()}")
        os.write(master, test_input.encode())
        
        # Read response
        time.sleep(5)
        while True:
            r, _, _ = select.select([master], [], [], 0)
            if r:
                data = os.read(master, 1024).decode('utf-8', errors='ignore')
                sys.stdout.write(data)
                sys.stdout.flush()
            else:
                break
                
        # Send exit
        print("\n[SENDING]: exit")
        os.write(master, b"exit\n")
        
        # Wait for process
        process.wait(timeout=2)
        
    except ImportError:
        print("PTY not available on this system")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'process' in locals():
            process.terminate()
        if 'master' in locals():
            os.close(master)

if __name__ == "__main__":
    test_basic_claude()
    if sys.platform != "win32":
        test_pty_mode()
    
    print("\n\n=== Diagnosis ===")
    print("If neither test shows Claude responding, the issue might be:")
    print("1. Claude expects a TTY/PTY for interactive mode")
    print("2. Claude might need different flags for subprocess mode")
    print("3. There might be initialization output we're not capturing")
    print("\nCheck ~/.claude-mpm/logs/latest.log for more details")