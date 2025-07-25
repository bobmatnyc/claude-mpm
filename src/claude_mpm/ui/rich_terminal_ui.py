"""Terminal UI using rich library for Claude MPM."""

import asyncio
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def create_layout() -> Layout:
    """Create the layout structure."""
    layout = Layout()
    
    # Split into header and body
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=1)
    )
    
    # Split body into left (Claude) and right (todos/tickets)
    layout["body"].split_row(
        Layout(name="claude", ratio=2),
        Layout(name="sidebar", ratio=1)
    )
    
    # Split sidebar into todos and tickets
    layout["sidebar"].split_column(
        Layout(name="todos"),
        Layout(name="tickets")
    )
    
    return layout


class ClaudeUI:
    """Rich-based terminal UI for Claude MPM."""
    
    def __init__(self):
        self.console = Console()
        self.claude_output = []
        self.todos = []
        self.tickets = []
        self.process = None
        self.running = False
        
        # Get directories
        self.home_dir = Path.home()
        self.claude_dir = self.home_dir / ".claude"
        self.todo_file = self.claude_dir / "todos.json"
        self.tickets_dir = Path.cwd() / "tickets" / "tasks"
    
    async def start_claude(self):
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
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            
            # Start reading output
            asyncio.create_task(self.read_claude_output())
            
        except Exception as e:
            self.claude_output.append(f"Error starting Claude: {e}")
    
    async def read_claude_output(self):
        """Read output from Claude subprocess."""
        if not self.process:
            return
            
        while self.running:
            try:
                line = await self.process.stdout.readline()
                if line:
                    self.claude_output.append(line.decode().strip())
                    # Keep last 100 lines
                    if len(self.claude_output) > 100:
                        self.claude_output = self.claude_output[-100:]
                else:
                    await asyncio.sleep(0.1)
            except:
                break
    
    def load_todos(self):
        """Load todos from file."""
        try:
            if self.todo_file.exists():
                with open(self.todo_file, 'r') as f:
                    data = json.load(f)
                    self.todos = data.get('todos', [])
        except:
            self.todos = []
    
    def load_tickets(self):
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
    
    def create_header(self) -> Panel:
        """Create header panel."""
        header_text = Text("Claude MPM Terminal UI", style="bold white on blue", justify="center")
        instructions = Text("Q: Quit | F5: Refresh | Tab: Switch Panes", style="dim", justify="center")
        
        content = Text()
        content.append(header_text)
        content.append("\\n")
        content.append(instructions)
        
        return Panel(content, style="white on blue", height=3)
    
    def create_claude_panel(self) -> Panel:
        """Create Claude output panel."""
        content = Text()
        for line in self.claude_output[-50:]:  # Show last 50 lines
            content.append(line + "\\n")
        
        return Panel(
            content,
            title="[bold green]Claude Output[/bold green]",
            border_style="green"
        )
    
    def create_todos_panel(self) -> Panel:
        """Create todos panel."""
        table = Table(show_header=False, padding=0, box=None)
        table.add_column("Status", width=3)
        table.add_column("Content", overflow="ellipsis")
        table.add_column("Priority", width=8)
        
        for todo in self.todos[:20]:  # Show max 20 todos
            status_icon = {
                'pending': '○',
                'in_progress': '◐',
                'completed': '●'
            }.get(todo.get('status', 'pending'), '?')
            
            priority = todo.get('priority', 'medium')
            priority_style = {
                'high': 'bold red',
                'medium': 'yellow',
                'low': 'green'
            }.get(priority, 'white')
            
            table.add_row(
                status_icon,
                todo.get('content', ''),
                Text(priority, style=priority_style)
            )
        
        return Panel(
            table,
            title=f"[bold green]ToDos ({len(self.todos)})[/bold green]",
            border_style="green"
        )
    
    def create_tickets_panel(self) -> Panel:
        """Create tickets panel."""
        table = Table(show_header=False, padding=0, box=None)
        table.add_column("ID", width=15)
        table.add_column("Modified", width=16)
        
        for ticket in self.tickets[:20]:  # Show max 20 tickets
            table.add_row(
                ticket['id'],
                ticket['modified']
            )
        
        return Panel(
            table,
            title=f"[bold green]Recent Tickets ({len(self.tickets)})[/bold green]",
            border_style="green"
        )
    
    def create_footer(self) -> Panel:
        """Create footer panel."""
        return Panel(
            Text("Ready", style="dim"),
            style="white on blue",
            height=1
        )
    
    def update_layout(self, layout: Layout):
        """Update the layout with current data."""
        layout["header"].update(self.create_header())
        layout["claude"].update(self.create_claude_panel())
        layout["todos"].update(self.create_todos_panel())
        layout["tickets"].update(self.create_tickets_panel())
        layout["footer"].update(self.create_footer())
    
    async def run(self):
        """Run the UI."""
        # Initialize
        self.running = True
        layout = create_layout()
        
        # Start Claude
        await self.start_claude()
        
        # Main loop
        with Live(layout, console=self.console, screen=True, refresh_per_second=4) as live:
            while self.running:
                # Update data
                self.load_todos()
                self.load_tickets()
                
                # Update display
                self.update_layout(layout)
                
                # Check for quit
                # Note: Rich doesn't have built-in keyboard handling in Live mode
                # For a production version, you'd want to add proper keyboard handling
                
                await asyncio.sleep(0.25)
        
        # Cleanup
        if self.process:
            self.process.terminate()
            await self.process.wait()


def main():
    """Main entry point."""
    ui = ClaudeUI()
    
    try:
        asyncio.run(ui.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()