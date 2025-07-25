"""Terminal UI for claude-mpm with multiple panes."""

import curses
import subprocess
import threading
import queue
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
from datetime import datetime

try:
    from ..services.ticket_manager import TicketManager
    from ..core.logger import get_logger
except ImportError:
    from claude_mpm.services.ticket_manager import TicketManager
    from claude_mpm.core.logger import get_logger


class TerminalUI:
    """Multi-pane terminal UI for claude-mpm."""
    
    def __init__(self):
        self.logger = get_logger("terminal_ui")
        self.ticket_manager = None
        self.todos = []
        self.tickets = []
        self.claude_output = []
        self.active_pane = 0  # 0=claude, 1=todos, 2=tickets
        self.claude_process = None
        self.output_queue = queue.Queue()
        
        # Try to initialize ticket manager
        try:
            self.ticket_manager = TicketManager()
        except Exception as e:
            self.logger.warning(f"Ticket manager not available: {e}")
    
    def run(self):
        """Run the terminal UI."""
        curses.wrapper(self._main)
    
    def _main(self, stdscr):
        """Main curses loop."""
        # Setup
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)   # Non-blocking input
        stdscr.timeout(100) # Refresh every 100ms
        
        # Initialize color pairs
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)   # Header
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Active pane
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Success
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)    # Error
        
        # Start Claude process
        self._start_claude()
        
        # Load initial data
        self._load_todos()
        self._load_tickets()
        
        while True:
            # Get terminal size
            height, width = stdscr.getmaxyx()
            
            # Clear screen
            stdscr.clear()
            
            # Draw UI
            self._draw_header(stdscr, width)
            self._draw_panes(stdscr, height, width)
            self._draw_footer(stdscr, height, width)
            
            # Handle input
            key = stdscr.getch()
            if key == ord('q') or key == ord('Q'):
                if self._confirm_quit(stdscr):
                    break
            elif key == ord('\t'):  # Tab to switch panes
                self.active_pane = (self.active_pane + 1) % 3
            elif key == curses.KEY_F5:  # Refresh
                self._load_todos()
                self._load_tickets()
            elif key == ord('n') or key == ord('N'):  # New ticket
                if self.active_pane == 2:
                    self._create_ticket(stdscr)
            
            # Update Claude output
            self._update_claude_output()
            
            # Refresh display
            stdscr.refresh()
    
    def _draw_header(self, stdscr, width):
        """Draw the header."""
        header = " Claude MPM Terminal UI "
        padding = (width - len(header)) // 2
        stdscr.attron(curses.color_pair(1))
        stdscr.addstr(0, 0, " " * width)
        stdscr.addstr(0, padding, header)
        stdscr.attroff(curses.color_pair(1))
    
    def _draw_panes(self, stdscr, height, width):
        """Draw the three panes."""
        # Calculate pane dimensions
        pane_height = height - 3  # Minus header and footer
        claude_width = width // 2
        side_width = width - claude_width - 1
        
        # Draw Claude pane (left half)
        self._draw_claude_pane(stdscr, 1, 0, pane_height, claude_width)
        
        # Draw vertical separator
        for y in range(1, height - 1):
            stdscr.addch(y, claude_width, '│')
        
        # Draw ToDo pane (top right)
        todo_height = pane_height // 2
        self._draw_todo_pane(stdscr, 1, claude_width + 1, todo_height, side_width)
        
        # Draw horizontal separator
        stdscr.hline(todo_height + 1, claude_width + 1, '─', side_width)
        
        # Draw Tickets pane (bottom right)
        ticket_height = pane_height - todo_height - 1
        self._draw_ticket_pane(stdscr, todo_height + 2, claude_width + 1, ticket_height, side_width)
    
    def _draw_claude_pane(self, stdscr, y, x, height, width):
        """Draw Claude output pane."""
        # Title
        title = " Claude Output "
        if self.active_pane == 0:
            stdscr.attron(curses.color_pair(2))
        stdscr.addstr(y, x, title + " " * (width - len(title)))
        if self.active_pane == 0:
            stdscr.attroff(curses.color_pair(2))
        
        # Content
        content_height = height - 2
        start_line = max(0, len(self.claude_output) - content_height)
        
        for i, line in enumerate(self.claude_output[start_line:start_line + content_height]):
            if y + i + 2 < y + height:
                truncated = line[:width-2] if len(line) > width-2 else line
                try:
                    stdscr.addstr(y + i + 2, x + 1, truncated)
                except curses.error:
                    pass  # Ignore if we can't write (edge of screen)
    
    def _draw_todo_pane(self, stdscr, y, x, height, width):
        """Draw ToDo list pane."""
        # Title
        title = f" ToDo List ({len(self.todos)}) "
        if self.active_pane == 1:
            stdscr.attron(curses.color_pair(2))
        stdscr.addstr(y, x, title + " " * (width - len(title)))
        if self.active_pane == 1:
            stdscr.attroff(curses.color_pair(2))
        
        # Content
        content_height = height - 2
        for i, todo in enumerate(self.todos[:content_height]):
            if y + i + 2 < y + height:
                status_icon = "✓" if todo.get('status') == 'completed' else "○"
                priority = todo.get('priority', 'medium')[0].upper()
                text = f"{status_icon} [{priority}] {todo.get('content', '')}"
                truncated = text[:width-2] if len(text) > width-2 else text
                
                # Color based on status
                if todo.get('status') == 'completed':
                    stdscr.attron(curses.color_pair(3))
                try:
                    stdscr.addstr(y + i + 2, x + 1, truncated)
                except curses.error:
                    pass
                if todo.get('status') == 'completed':
                    stdscr.attroff(curses.color_pair(3))
    
    def _draw_ticket_pane(self, stdscr, y, x, height, width):
        """Draw Tickets pane."""
        # Title
        title = f" Tickets ({len(self.tickets)}) [N]ew "
        if self.active_pane == 2:
            stdscr.attron(curses.color_pair(2))
        stdscr.addstr(y, x, title + " " * (width - len(title)))
        if self.active_pane == 2:
            stdscr.attroff(curses.color_pair(2))
        
        # Content
        content_height = height - 2
        for i, ticket in enumerate(self.tickets[:content_height]):
            if y + i + 2 < y + height:
                ticket_id = ticket.get('id', 'N/A')
                title = ticket.get('title', 'No title')
                text = f"[{ticket_id}] {title}"
                truncated = text[:width-2] if len(text) > width-2 else text
                try:
                    stdscr.addstr(y + i + 2, x + 1, truncated)
                except curses.error:
                    pass
    
    def _draw_footer(self, stdscr, height, width):
        """Draw the footer."""
        footer = " [Tab] Switch Pane | [F5] Refresh | [Q] Quit "
        stdscr.attron(curses.color_pair(1))
        stdscr.addstr(height - 1, 0, " " * width)
        stdscr.addstr(height - 1, 0, footer)
        stdscr.attroff(curses.color_pair(1))
    
    def _start_claude(self):
        """Start Claude process in a thread."""
        def run_claude():
            try:
                cmd = ["claude", "--model", "opus", "--dangerously-skip-permissions"]
                self.claude_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                
                # Read output
                for line in iter(self.claude_process.stdout.readline, ''):
                    if line:
                        self.output_queue.put(line.rstrip())
                        
            except Exception as e:
                self.output_queue.put(f"Error starting Claude: {e}")
        
        thread = threading.Thread(target=run_claude, daemon=True)
        thread.start()
    
    def _update_claude_output(self):
        """Update Claude output from queue."""
        try:
            while True:
                line = self.output_queue.get_nowait()
                self.claude_output.append(line)
                # Keep last 1000 lines
                if len(self.claude_output) > 1000:
                    self.claude_output = self.claude_output[-1000:]
        except queue.Empty:
            pass
    
    def _load_todos(self):
        """Load ToDo items from Claude's todo file."""
        try:
            # Look for Claude's todo files
            todo_dir = Path.home() / ".claude" / "todos"
            if todo_dir.exists():
                todos = []
                for todo_file in todo_dir.glob("*.json"):
                    try:
                        with open(todo_file, 'r') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                todos.extend(data)
                    except:
                        pass
                
                # Sort by priority and status
                priority_order = {'high': 0, 'medium': 1, 'low': 2}
                todos.sort(key=lambda x: (
                    x.get('status') == 'completed',
                    priority_order.get(x.get('priority', 'medium'), 1)
                ))
                self.todos = todos[:20]  # Keep top 20
        except Exception as e:
            self.logger.error(f"Error loading todos: {e}")
    
    def _load_tickets(self):
        """Load tickets from ticket manager."""
        if self.ticket_manager:
            try:
                self.tickets = self.ticket_manager.list_recent_tickets(limit=20)
            except Exception as e:
                self.logger.error(f"Error loading tickets: {e}")
    
    def _create_ticket(self, stdscr):
        """Create a new ticket."""
        if not self.ticket_manager:
            return
        
        # Simple input dialog
        curses.echo()
        stdscr.addstr(10, 10, "Enter ticket title: ")
        stdscr.refresh()
        title = stdscr.getstr(10, 30, 60).decode('utf-8')
        curses.noecho()
        
        if title:
            try:
                ticket = self.ticket_manager.create_ticket(
                    title=title,
                    description="Created from Terminal UI",
                    priority="medium"
                )
                self._load_tickets()
            except Exception as e:
                self.logger.error(f"Error creating ticket: {e}")
    
    def _confirm_quit(self, stdscr):
        """Confirm quit dialog."""
        height, width = stdscr.getmaxyx()
        msg = "Really quit? (y/n)"
        y = height // 2
        x = (width - len(msg)) // 2
        
        stdscr.addstr(y, x, msg)
        stdscr.refresh()
        
        key = stdscr.getch()
        return key == ord('y') or key == ord('Y')


def main():
    """Run the terminal UI."""
    ui = TerminalUI()
    ui.run()


if __name__ == "__main__":
    main()