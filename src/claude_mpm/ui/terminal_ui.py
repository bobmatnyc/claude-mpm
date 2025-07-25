"""Terminal UI using curses for Claude MPM."""

import curses
import json
import os
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Optional, List, Dict


class TerminalUI:
    """Terminal UI with multiple panes for Claude MPM."""
    
    def __init__(self):
        self.claude_output = []
        self.todos = []
        self.tickets = []
        self.command_queue = Queue()
        self.output_queue = Queue()
        self.process = None
        self.running = False
        
        # Get directories
        self.home_dir = Path.home()
        self.claude_dir = self.home_dir / ".claude"
        self.todo_file = self.claude_dir / "todos.json"
        self.tickets_dir = Path.cwd() / "tickets" / "tasks"
        
    def run(self):
        """Run the terminal UI."""
        curses.wrapper(self._main)
        
    def _main(self, stdscr):
        """Main curses loop."""
        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        
        # Configure screen
        stdscr.nodelay(True)
        curses.curs_set(0)
        
        # Start Claude subprocess
        self._start_claude()
        
        # Start output reader thread
        reader_thread = threading.Thread(target=self._read_claude_output)
        reader_thread.daemon = True
        reader_thread.start()
        
        # Main loop
        self.running = True
        while self.running:
            # Get screen dimensions
            height, width = stdscr.getmaxyx()
            
            # Clear screen
            stdscr.clear()
            
            # Draw UI
            self._draw_header(stdscr, width)
            self._draw_panes(stdscr, height, width)
            self._draw_footer(stdscr, height, width)
            
            # Refresh screen
            stdscr.refresh()
            
            # Handle input
            try:
                key = stdscr.getch()
                if key == ord('q') or key == ord('Q'):
                    self.running = False
                elif key == curses.KEY_F5:
                    self._refresh_data()
            except:
                pass
            
            # Update data
            self._update_claude_output()
            self._load_todos()
            self._load_tickets()
            
            # Small delay
            time.sleep(0.1)
        
        # Cleanup
        if self.process:
            self.process.terminate()
    
    def _start_claude(self):
        """Start Claude subprocess."""
        try:
            # Load system instructions
            from ..core.simple_runner import SimpleClaudeRunner
            runner = SimpleClaudeRunner(enable_tickets=False)
            system_prompt = runner._create_system_prompt()
            
            # Build command
            cmd = ["claude", "--model", "opus", "--dangerously-skip-permissions"]
            if system_prompt:
                cmd.extend(["--append-system-prompt", system_prompt])
            
            # Start process
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
        except Exception as e:
            self.claude_output.append(f"Error starting Claude: {e}")
    
    def _read_claude_output(self):
        """Read output from Claude subprocess."""
        if not self.process:
            return
            
        while self.running:
            try:
                line = self.process.stdout.readline()
                if line:
                    self.output_queue.put(line.strip())
            except:
                break
    
    def _update_claude_output(self):
        """Update Claude output from queue."""
        while not self.output_queue.empty():
            try:
                line = self.output_queue.get_nowait()
                self.claude_output.append(line)
                # Keep last 1000 lines
                if len(self.claude_output) > 1000:
                    self.claude_output = self.claude_output[-1000:]
            except:
                break
    
    def _load_todos(self):
        """Load todos from file."""
        try:
            if self.todo_file.exists():
                with open(self.todo_file, 'r') as f:
                    data = json.load(f)
                    self.todos = data.get('todos', [])
        except:
            self.todos = []
    
    def _load_tickets(self):
        """Load tickets from directory."""
        try:
            self.tickets = []
            if self.tickets_dir.exists():
                for ticket_file in sorted(self.tickets_dir.glob("*.md"))[:10]:
                    self.tickets.append({
                        'file': ticket_file.name,
                        'id': ticket_file.stem,
                        'modified': datetime.fromtimestamp(ticket_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                    })
        except:
            self.tickets = []
    
    def _refresh_data(self):
        """Refresh todos and tickets."""
        self._load_todos()
        self._load_tickets()
    
    def _draw_header(self, stdscr, width):
        """Draw header."""
        header = " Claude MPM Terminal UI "
        x = (width - len(header)) // 2
        stdscr.attron(curses.color_pair(1))
        stdscr.addstr(0, 0, " " * width)
        stdscr.addstr(0, x, header)
        stdscr.attroff(curses.color_pair(1))
    
    def _draw_footer(self, stdscr, height, width):
        """Draw footer."""
        footer = " Q: Quit | F5: Refresh | Tab: Switch Panes "
        x = (width - len(footer)) // 2
        stdscr.attron(curses.color_pair(1))
        stdscr.addstr(height - 1, 0, " " * width)
        stdscr.addstr(height - 1, x, footer)
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
        for x in range(claude_width + 1, width):
            stdscr.addch(todo_height + 1, x, '─')
        
        # Draw Tickets pane (bottom right)
        tickets_y = todo_height + 2
        tickets_height = pane_height - todo_height - 1
        self._draw_tickets_pane(stdscr, tickets_y, claude_width + 1, tickets_height, side_width)
    
    def _draw_claude_pane(self, stdscr, y, x, height, width):
        """Draw Claude output pane."""
        # Title
        stdscr.attron(curses.color_pair(2))
        stdscr.addstr(y, x + 2, "Claude Output")
        stdscr.attroff(curses.color_pair(2))
        
        # Content
        content_y = y + 2
        max_lines = height - 3
        
        # Show last n lines of output
        start_idx = max(0, len(self.claude_output) - max_lines)
        for i, line in enumerate(self.claude_output[start_idx:]):
            if i >= max_lines:
                break
            try:
                # Truncate line if too long
                if len(line) > width - 4:
                    line = line[:width - 7] + "..."
                stdscr.addstr(content_y + i, x + 2, line)
            except:
                pass
    
    def _draw_todo_pane(self, stdscr, y, x, height, width):
        """Draw ToDo pane."""
        # Title
        stdscr.attron(curses.color_pair(2))
        stdscr.addstr(y, x + 2, f"ToDos ({len(self.todos)})")
        stdscr.attroff(curses.color_pair(2))
        
        # Content
        content_y = y + 2
        max_lines = height - 3
        
        for i, todo in enumerate(self.todos[:max_lines]):
            if i >= max_lines:
                break
            
            # Status icon
            status_icon = {
                'pending': '○',
                'in_progress': '◐',
                'completed': '●'
            }.get(todo.get('status', 'pending'), '?')
            
            # Priority color
            priority = todo.get('priority', 'medium')
            if priority == 'high':
                stdscr.attron(curses.color_pair(3))
            
            # Format line
            content = todo.get('content', '')
            if len(content) > width - 8:
                content = content[:width - 11] + "..."
            
            line = f"{status_icon} {content}"
            
            try:
                stdscr.addstr(content_y + i, x + 2, line)
            except:
                pass
            
            if priority == 'high':
                stdscr.attroff(curses.color_pair(3))
    
    def _draw_tickets_pane(self, stdscr, y, x, height, width):
        """Draw Tickets pane."""
        # Title
        stdscr.attron(curses.color_pair(2))
        stdscr.addstr(y, x + 2, f"Recent Tickets ({len(self.tickets)})")
        stdscr.attroff(curses.color_pair(2))
        
        # Content
        content_y = y + 2
        max_lines = height - 3
        
        for i, ticket in enumerate(self.tickets[:max_lines]):
            if i >= max_lines:
                break
            
            # Format line
            id_str = ticket['id']
            if len(id_str) > 12:
                id_str = id_str[:12] + "..."
            
            line = f"{id_str} ({ticket['modified']})"
            if len(line) > width - 4:
                line = line[:width - 7] + "..."
            
            try:
                stdscr.addstr(content_y + i, x + 2, line)
            except:
                pass