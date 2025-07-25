"""Rich terminal UI for claude-mpm with live updates."""

import asyncio
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.syntax import Syntax
from rich.align import Align
from rich.box import ROUNDED
from rich import print as rprint

try:
    from ..services.ticket_manager import TicketManager
    from ..core.logger import get_logger
except ImportError:
    from claude_mpm.services.ticket_manager import TicketManager
    from claude_mpm.core.logger import get_logger


class RichTerminalUI:
    """Rich terminal UI with live updates."""
    
    def __init__(self):
        self.console = Console()
        self.logger = get_logger("rich_ui")
        self.ticket_manager = None
        self.todos = []
        self.tickets = []
        self.claude_output = []
        self.claude_process = None
        self.running = True
        
        # Try to initialize ticket manager
        try:
            self.ticket_manager = TicketManager()
        except Exception as e:
            self.logger.warning(f"Ticket manager not available: {e}")
        
        # Create layout
        self.layout = Layout()
        self._setup_layout()
    
    def _setup_layout(self):
        """Setup the layout structure."""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # Split body into two columns
        self.layout["body"].split_row(
            Layout(name="main", ratio=2),
            Layout(name="sidebar", ratio=1)
        )
        
        # Split sidebar into two sections
        self.layout["sidebar"].split_column(
            Layout(name="todos"),
            Layout(name="tickets")
        )
    
    def _make_header(self) -> Panel:
        """Create header panel."""
        grid = Table.grid(expand=True)
        grid.add_column(justify="left")
        grid.add_column(justify="center")
        grid.add_column(justify="right")
        
        grid.add_row(
            "[bold blue]Claude MPM[/bold blue]",
            "[yellow]Terminal UI[/yellow]",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        return Panel(grid, style="white on blue", box=ROUNDED)
    
    def _make_footer(self) -> Panel:
        """Create footer panel."""
        text = Text()
        text.append("[F5]", style="bold yellow")
        text.append(" Refresh  ", style="white")
        text.append("[Ctrl+N]", style="bold yellow")
        text.append(" New Ticket  ", style="white")
        text.append("[Ctrl+C]", style="bold yellow")
        text.append(" Quit", style="white")
        
        return Panel(Align.center(text), style="white on blue", box=ROUNDED)
    
    def _make_claude_panel(self) -> Panel:
        """Create Claude output panel."""
        # Show last 30 lines
        lines = self.claude_output[-30:] if self.claude_output else ["Waiting for Claude to start..."]
        content = "\n".join(lines)
        
        return Panel(
            content,
            title="[bold]Claude Output[/bold]",
            border_style="green",
            box=ROUNDED
        )
    
    def _make_todos_panel(self) -> Panel:
        """Create todos panel."""
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("", width=2)
        table.add_column("Priority", width=8)
        table.add_column("Task", overflow="fold")
        
        for todo in self.todos[:10]:  # Show top 10
            status_icon = "✓" if todo.get('status') == 'completed' else "○"
            priority = todo.get('priority', 'medium')
            content = todo.get('content', '')
            
            # Color based on priority
            if priority == 'high':
                style = "bold red"
            elif priority == 'low':
                style = "dim"
            else:
                style = "white"
            
            if todo.get('status') == 'completed':
                style = "green"
            
            table.add_row(status_icon, priority.upper(), content, style=style)
        
        return Panel(
            table,
            title=f"[bold]ToDo List ({len(self.todos)})[/bold]",
            border_style="blue",
            box=ROUNDED
        )
    
    def _make_tickets_panel(self) -> Panel:
        """Create tickets panel."""
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("ID", width=10)
        table.add_column("Priority", width=8)
        table.add_column("Title", overflow="fold")
        
        for ticket in self.tickets[:10]:  # Show top 10
            ticket_id = ticket.get('id', 'N/A')
            priority = ticket.get('priority', 'medium')
            title = ticket.get('title', 'No title')
            
            # Color based on priority
            if priority == 'high':
                style = "bold red"
            elif priority == 'low':
                style = "dim"
            else:
                style = "white"
            
            table.add_row(ticket_id, priority.upper(), title, style=style)
        
        return Panel(
            table,
            title=f"[bold]Tickets ({len(self.tickets)})[/bold]",
            border_style="magenta",
            box=ROUNDED
        )
    
    def _update_layout(self):
        """Update all layout panels."""
        self.layout["header"].update(self._make_header())
        self.layout["footer"].update(self._make_footer())
        self.layout["main"].update(self._make_claude_panel())
        self.layout["todos"].update(self._make_todos_panel())
        self.layout["tickets"].update(self._make_tickets_panel())
    
    def _start_claude(self):
        """Start Claude process in a thread."""
        def run_claude():
            try:
                # Load system instructions
                from ..core.simple_runner import SimpleClaudeRunner
                runner = SimpleClaudeRunner(enable_tickets=False)
                system_prompt = runner._create_system_prompt()
                
                cmd = ["claude", "--model", "opus", "--dangerously-skip-permissions"]
                if system_prompt:
                    cmd.extend(["--append-system-prompt", system_prompt])
                
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
                    if line and self.running:
                        self.claude_output.append(line.rstrip())
                        # Keep last 1000 lines
                        if len(self.claude_output) > 1000:
                            self.claude_output = self.claude_output[-1000:]
                        
            except Exception as e:
                self.claude_output.append(f"Error starting Claude: {e}")
        
        thread = threading.Thread(target=run_claude, daemon=True)
        thread.start()
    
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
                self.todos = todos
        except Exception as e:
            self.logger.error(f"Error loading todos: {e}")
    
    def _load_tickets(self):
        """Load tickets from ticket manager."""
        if self.ticket_manager:
            try:
                self.tickets = self.ticket_manager.list_recent_tickets(limit=20)
            except Exception as e:
                self.logger.error(f"Error loading tickets: {e}")
    
    async def _refresh_data(self):
        """Refresh data periodically."""
        while self.running:
            self._load_todos()
            self._load_tickets()
            await asyncio.sleep(5)  # Refresh every 5 seconds
    
    async def run(self):
        """Run the rich terminal UI."""
        # Start Claude
        self._start_claude()
        
        # Initial data load
        self._load_todos()
        self._load_tickets()
        
        # Start refresh task
        refresh_task = asyncio.create_task(self._refresh_data())
        
        try:
            with Live(self.layout, refresh_per_second=2, screen=True) as live:
                while self.running:
                    self._update_layout()
                    await asyncio.sleep(0.5)
        except KeyboardInterrupt:
            self.running = False
        finally:
            refresh_task.cancel()
            if self.claude_process:
                self.claude_process.terminate()
    
    def stop(self):
        """Stop the UI."""
        self.running = False


def main():
    """Run the rich terminal UI."""
    ui = RichTerminalUI()
    asyncio.run(ui.run())


if __name__ == "__main__":
    main()