#!/usr/bin/env python3
"""Simple test of subprocess.Popen with PTY for Claude."""

import os
import pty
import subprocess
import sys
import select
import signal

def run_claude_subprocess():
    """Run Claude as subprocess with PTY."""
    print("Starting Claude with subprocess.Popen and PTY...")
    
    # Create PTY
    master_fd, slave_fd = pty.openpty()
    
    # Set up environment
    env = os.environ.copy()
    env['TERM'] = 'xterm-256color'
    
    # Start Claude process
    try:
        process = subprocess.Popen(
            ['claude'],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env
        )
        
        # Close slave in parent
        os.close(slave_fd)
        
        print(f"Claude started with PID: {process.pid}")
        print("Type your messages below. Press Ctrl+C to exit.\n")
        
        # Make stdin non-blocking
        import fcntl
        flags = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        
        # Main I/O loop
        while True:
            # Check for output from Claude
            r, _, _ = select.select([master_fd], [], [], 0)
            if r:
                try:
                    data = os.read(master_fd, 4096)
                    if data:
                        sys.stdout.write(data.decode('utf-8', errors='replace'))
                        sys.stdout.flush()
                    else:
                        break  # EOF
                except OSError:
                    break
                    
            # Check for input from user
            r, _, _ = select.select([sys.stdin], [], [], 0)
            if r:
                try:
                    data = sys.stdin.read()
                    if data:
                        os.write(master_fd, data.encode())
                except (OSError, IOError):
                    pass
                    
            # Check if process is still running
            if process.poll() is not None:
                print(f"\nClaude process exited with code: {process.returncode}")
                break
                
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        process.terminate()
        process.wait()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        os.close(master_fd)
        

if __name__ == "__main__":
    run_claude_subprocess()