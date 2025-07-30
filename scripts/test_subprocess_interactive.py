#!/usr/bin/env python3
"""Interactive test of subprocess.Popen with PTY for Claude."""

import os
import pty
import subprocess
import sys
import select
import termios
import tty
import signal

class ClaudeSubprocessController:
    """Controls Claude via subprocess with PTY."""
    
    def __init__(self):
        self.process = None
        self.master_fd = None
        self.original_tty = None
        
    def start(self):
        """Start Claude subprocess with PTY."""
        # Save original terminal settings
        if sys.stdin.isatty():
            self.original_tty = termios.tcgetattr(sys.stdin)
            
        # Create PTY
        self.master_fd, slave_fd = pty.openpty()
        
        # Set up environment
        env = os.environ.copy()
        env['TERM'] = 'xterm-256color'
        
        # Start Claude
        self.process = subprocess.Popen(
            ['claude'],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env
        )
        
        # Close slave in parent
        os.close(slave_fd)
        
        print(f"Claude started with PID: {self.process.pid}")
        print("Press Ctrl+D to exit\n")
        
        # Set terminal to raw mode
        if sys.stdin.isatty():
            tty.setraw(sys.stdin)
            
    def run_interactive(self):
        """Run interactive I/O loop."""
        try:
            while True:
                # Check for data from Claude
                r, _, _ = select.select([self.master_fd, sys.stdin], [], [], 0)
                
                if self.master_fd in r:
                    try:
                        data = os.read(self.master_fd, 4096)
                        if data:
                            os.write(sys.stdout.fileno(), data)
                        else:
                            break  # EOF
                    except OSError:
                        break
                        
                if sys.stdin in r:
                    try:
                        data = os.read(sys.stdin.fileno(), 4096)
                        if data:
                            # Check for Ctrl+D
                            if b'\x04' in data:
                                break
                            os.write(self.master_fd, data)
                    except OSError:
                        break
                        
                # Check if process is still running
                if self.process.poll() is not None:
                    break
                    
        finally:
            self.cleanup()
            
    def cleanup(self):
        """Clean up resources."""
        # Restore terminal
        if self.original_tty and sys.stdin.isatty():
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.original_tty)
            
        # Close PTY
        if self.master_fd:
            try:
                os.close(self.master_fd)
            except:
                pass
                
        # Terminate process if still running
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
                
        print(f"\n\nClaude process terminated (exit code: {self.process.returncode if self.process else 'N/A'})")


def main():
    """Run interactive Claude subprocess."""
    controller = ClaudeSubprocessController()
    
    # Handle Ctrl+C gracefully
    def signal_handler(signum, frame):
        controller.cleanup()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        controller.start()
        controller.run_interactive()
    except Exception as e:
        print(f"\nError: {e}")
        controller.cleanup()
        

if __name__ == "__main__":
    main()