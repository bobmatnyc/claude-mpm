#!/usr/bin/env python3
"""Test subprocess.Popen approach for Claude process control."""

import os
import pty
import select
import subprocess
import sys
import termios
import tty
from threading import Thread
import time

class ClaudeSubprocessManager:
    """Manages Claude as a subprocess with PTY."""
    
    def __init__(self):
        self.claude_process = None
        self.master_fd = None
        self.running = False
        
    def start(self):
        """Launch Claude as managed subprocess with PTY."""
        print("Starting Claude subprocess with PTY...")
        
        # Create PTY for Claude (gives it proper terminal)
        self.master_fd, slave_fd = pty.openpty()
        
        # Set terminal size
        import struct
        import fcntl
        import termios as term
        
        # Get current terminal size
        try:
            rows, cols = os.popen('stty size', 'r').read().split()
            rows, cols = int(rows), int(cols)
        except:
            rows, cols = 24, 80
            
        # Set PTY size
        winsize = struct.pack('HHHH', rows, cols, 0, 0)
        fcntl.ioctl(self.master_fd, term.TIOCSWINSZ, winsize)
        
        # Prepare environment
        env = os.environ.copy()
        env['TERM'] = 'xterm-256color'
        env['CLAUDE_MPM_ACTIVE'] = '1'
        
        # Launch Claude with PTY
        try:
            self.claude_process = subprocess.Popen(
                ['claude'],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=env
            )
            
            # Close slave in parent (child has it)
            os.close(slave_fd)
            
            self.running = True
            print(f"Claude started with PID: {self.claude_process.pid}")
            
            # Start I/O threads
            self.start_io_threads()
            
        except Exception as e:
            print(f"Failed to start Claude: {e}")
            if self.master_fd:
                os.close(self.master_fd)
            raise
            
    def start_io_threads(self):
        """Start threads for I/O handling."""
        # Thread to read from Claude and write to stdout
        def read_claude():
            while self.running:
                try:
                    # Check if data available
                    r, _, _ = select.select([self.master_fd], [], [], 0.1)
                    if r:
                        data = os.read(self.master_fd, 4096)
                        if data:
                            sys.stdout.write(data.decode('utf-8', errors='replace'))
                            sys.stdout.flush()
                except OSError:
                    break
                    
        # Thread to read from stdin and write to Claude
        def read_stdin():
            # Save original terminal settings
            old_settings = termios.tcgetattr(sys.stdin)
            try:
                # Set raw mode for stdin
                tty.setraw(sys.stdin)
                
                while self.running:
                    try:
                        # Check if input available
                        r, _, _ = select.select([sys.stdin], [], [], 0.1)
                        if r:
                            char = sys.stdin.read(1)
                            if char:
                                os.write(self.master_fd, char.encode())
                    except OSError:
                        break
            finally:
                # Restore terminal settings
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                
        # Start threads
        claude_reader = Thread(target=read_claude, daemon=True)
        stdin_reader = Thread(target=read_stdin, daemon=True)
        
        claude_reader.start()
        stdin_reader.start()
        
    def wait(self):
        """Wait for Claude process to complete."""
        try:
            self.claude_process.wait()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.shutdown()
            
    def shutdown(self):
        """Clean shutdown of Claude process."""
        self.running = False
        
        if self.claude_process and self.claude_process.poll() is None:
            # Try graceful shutdown first
            try:
                self.claude_process.terminate()
                self.claude_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                # Force kill if needed
                self.claude_process.kill()
                self.claude_process.wait()
                
        if self.master_fd:
            try:
                os.close(self.master_fd)
            except:
                pass
                
        print("\nClaude subprocess terminated.")


def main():
    """Test the subprocess approach."""
    manager = ClaudeSubprocessManager()
    
    try:
        manager.start()
        manager.wait()
    except Exception as e:
        print(f"Error: {e}")
        manager.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    main()