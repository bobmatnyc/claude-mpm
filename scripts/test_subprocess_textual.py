#!/usr/bin/env python3
"""Test subprocess.Popen approach with Textual UI."""

import os
import pty
import select
import subprocess
import sys
from threading import Thread
import asyncio
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, TextLog, Static, Label
from textual.reactive import reactive
from datetime import datetime


class MPMContextInjector:
    """Mock context injector for testing."""
    
    def prepare_claude_environment(self):
        """Prepare environment variables for Claude."""
        env = os.environ.copy()
        env['TERM'] = 'xterm-256color'
        env['CLAUDE_MPM_ACTIVE'] = '1'
        env['CLAUDE_MPM_VERSION'] = '3.1.3'
        return env
        
    def inject_on_startup(self, fd):
        """Inject initial context (placeholder)."""
        # In real implementation, would inject context here
        pass


class MPMEventBus:
    """Mock event bus for testing."""
    
    def emit(self, event, data=None):
        """Emit event (placeholder)."""
        pass


class ClaudePane(TextLog):
    """Widget to display Claude output."""
    
    def on_mount(self):
        self.write("[MPM] Claude process output will appear here...")


class StatusPanel(Static):
    """Status panel showing process info."""
    
    process_status = reactive("Starting...")
    pid = reactive("N/A")
    
    def compose(self) -> ComposeResult:
        yield Label("Claude Process Status", classes="status-header")
        yield Label(f"Status: {self.process_status}", id="status-text")
        yield Label(f"PID: {self.pid}", id="pid-text")
        
    def watch_process_status(self, status: str):
        """Update status display."""
        if label := self.query_one("#status-text", Label):
            label.update(f"Status: {status}")
            
    def watch_pid(self, pid: str):
        """Update PID display."""
        if label := self.query_one("#pid-text", Label):
            label.update(f"PID: {pid}")


class ClaudeMPMTerminalApp(App):
    """Textual app that manages Claude as subprocess."""
    
    CSS = """
    ClaudePane {
        border: solid green;
        height: 100%;
    }
    
    StatusPanel {
        border: solid blue;
        height: 5;
        padding: 1;
    }
    
    .status-header {
        text-style: bold;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.claude_process = None
        self.claude_master_fd = None
        self.context_injector = MPMContextInjector()
        self.event_bus = MPMEventBus()
        self.io_thread = None
        self.running = False
        
    def compose(self) -> ComposeResult:
        """Create UI layout."""
        yield Header()
        yield Container(
            Vertical(
                StatusPanel(id="status"),
                ClaudePane(id="claude-output"),
            )
        )
        yield Footer()
        
    def on_mount(self):
        """Start Claude as interactive subprocess."""
        self.start_claude_subprocess()
        self.start_io_monitoring()
        
    def start_claude_subprocess(self):
        """Launch Claude as managed subprocess with PTY."""
        status_panel = self.query_one("#status", StatusPanel)
        claude_pane = self.query_one("#claude-output", ClaudePane)
        
        try:
            # Prepare environment and context
            env = self.context_injector.prepare_claude_environment()
            
            # Create PTY for Claude (gives it proper terminal)
            master_fd, slave_fd = pty.openpty()
            
            # Set terminal size
            import struct
            import fcntl
            import termios
            
            # Set reasonable PTY size
            winsize = struct.pack('HHHH', 24, 80, 0, 0)
            fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
            
            # Launch Claude with PTY
            self.claude_process = subprocess.Popen(
                ['claude'],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=env,
                start_new_session=True,  # Create new session
                preexec_fn=os.setsid     # Become session leader
            )
            
            # Store PTY master for communication
            self.claude_master_fd = master_fd
            
            # Close slave in parent (child has it)
            os.close(slave_fd)
            
            # Update status
            status_panel.process_status = "Running"
            status_panel.pid = str(self.claude_process.pid)
            
            # Inject initial context
            self.context_injector.inject_on_startup(self.claude_master_fd)
            
            claude_pane.write(f"[MPM] Claude started with PID {self.claude_process.pid}")
            self.running = True
            
        except Exception as e:
            status_panel.process_status = f"Error: {str(e)}"
            claude_pane.write(f"[MPM] Failed to start Claude: {e}")
            if master_fd:
                os.close(master_fd)
                
    def start_io_monitoring(self):
        """Start monitoring Claude I/O in background thread."""
        if not self.claude_master_fd:
            return
            
        def monitor_claude():
            """Read from Claude and update UI."""
            claude_pane = self.query_one("#claude-output", ClaudePane)
            
            while self.running:
                try:
                    # Check if data available
                    r, _, _ = select.select([self.claude_master_fd], [], [], 0.1)
                    if r:
                        data = os.read(self.claude_master_fd, 4096)
                        if data:
                            # Post to UI thread
                            text = data.decode('utf-8', errors='replace')
                            self.call_from_thread(claude_pane.write, text)
                        else:
                            # EOF - process ended
                            break
                except OSError as e:
                    self.call_from_thread(claude_pane.write, f"\n[MPM] Read error: {e}")
                    break
                    
            # Process ended
            self.running = False
            status_panel = self.query_one("#status", StatusPanel)
            self.call_from_thread(lambda: setattr(status_panel, 'process_status', 'Terminated'))
            
        self.io_thread = Thread(target=monitor_claude, daemon=True)
        self.io_thread.start()
        
    async def on_key(self, event):
        """Handle keyboard input - send to Claude."""
        if self.claude_master_fd and self.running:
            try:
                # Send keypress to Claude
                key_data = event.character or event.key
                if key_data:
                    os.write(self.claude_master_fd, key_data.encode())
            except OSError:
                pass
                
    def on_unmount(self):
        """Clean up when app closes."""
        self.shutdown_claude()
        
    def shutdown_claude(self):
        """Shutdown Claude process cleanly."""
        self.running = False
        
        if self.claude_process and self.claude_process.poll() is None:
            try:
                self.claude_process.terminate()
                self.claude_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.claude_process.kill()
                self.claude_process.wait()
                
        if self.claude_master_fd:
            try:
                os.close(self.claude_master_fd)
            except:
                pass


def main():
    """Run the Textual app."""
    app = ClaudeMPMTerminalApp()
    app.run()


if __name__ == "__main__":
    main()