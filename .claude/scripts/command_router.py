#!/usr/bin/env python3
"""Simple command router for /mpm commands."""

import sys
import subprocess
from pathlib import Path
from typing import Dict, Callable, Optional


class CommandRouter:
    """Simple command dispatcher for /mpm commands."""
    
    def __init__(self):
        self.commands: Dict[str, Callable] = {}
        self._register_builtin_commands()
    
    def _register_builtin_commands(self):
        """Register built-in commands."""
        self.register("test", self._test_command)
        self.register("help", self._help_command)
        self.register("memory", self._memory_command)
    
    def register(self, command: str, handler: Callable):
        """Register a command handler."""
        self.commands[command] = handler
    
    def _test_command(self, *args) -> str:
        """Simple test command that returns Hello World."""
        return "Hello World"
    
    def _help_command(self, *args) -> str:
        """Show help for available /mpm commands."""
        help_text = """
Available /mpm commands:

Basic Commands:
  /mpm test                    - Test command that returns Hello World
  /mpm help                    - Show this help message

Memory Commands:
  /mpm memory init             - Initialize project-specific memories
  /mpm memory status           - Show memory system status and health
  /mpm memory show [agent_id]  - Show agent memories (all agents if no ID provided)
  /mpm memory view [agent_id]  - Alias for 'show' - display agent memories
  /mpm memory optimize [agent_id] - Optimize memory files by removing duplicates
  /mpm memory build [--force]  - Build memories from project documentation
  /mpm memory route <content>  - Test memory command routing logic
  /mpm memory cross-ref [query] - Find cross-references and patterns across memories

Usage Examples:
  /mpm memory status          - Show overall memory system health
  /mpm memory show            - Show all agent memories with content
  /mpm memory view research   - Show memory for specific 'research' agent
  /mpm memory optimize        - Optimize all agent memories
  /mpm memory build --force   - Force rebuild memories from documentation
"""
        return help_text.strip()
    
    def _memory_command(self, *args) -> str:
        """Handle memory subcommands by delegating to claude-mpm CLI."""
        if not args:
            return "Memory subcommand required. Use '/mpm help' to see available commands."
        
        # Special handling for 'init' command
        if args[0] == "init":
            return self._memory_init_command()
        
        # Find the claude-mpm executable
        claude_mpm_path = self._find_claude_mpm()
        if not claude_mpm_path:
            return "Error: claude-mpm executable not found. Please ensure it's installed and in PATH."
        
        # Build command: claude-mpm memory <subcommand> [args...]
        cmd = [str(claude_mpm_path), "memory"] + list(args)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                cwd=Path.cwd()  # Use current working directory
            )
            
            if result.returncode == 0:
                return result.stdout.strip() or "Command completed successfully"
            else:
                error_msg = result.stderr.strip()
                if error_msg:
                    return f"Memory command failed: {error_msg}"
                else:
                    return f"Memory command failed with return code {result.returncode}"
        
        except Exception as e:
            return f"Error executing memory command: {str(e)}"
    
    def _memory_init_command(self) -> str:
        """Handle memory init command by creating a prompt for memory initialization."""
        prompt = """
[Task: Initialize Project-Specific Memories]

Please analyze this project and create custom memories for all agents based on the actual codebase. 

Your task:
1. Scan the project structure, documentation, and source code
2. Identify key patterns, conventions, and project-specific knowledge
3. Create targeted memories for each agent type (engineer, research, qa, etc.)
4. Use the 'claude-mpm memory add' command to add these memories

Focus on:
- Project-specific architectural patterns and design decisions
- Coding conventions observed in the actual source code
- Key modules, APIs, and integration points
- Testing patterns and quality standards
- Performance considerations specific to this project
- Common pitfalls or mistakes to avoid based on the codebase
- Domain-specific terminology and concepts

For each insight you discover, add it to the appropriate agent's memory using:
claude-mpm memory add <agent> <type> "<content>"

Where <type> is one of: pattern, error, optimization, preference, context

Example:
- If you find the project uses dependency injection, add:
  claude-mpm memory add engineer pattern "Use dependency injection pattern with @inject decorators"
- If you find a testing convention, add:
  claude-mpm memory add qa pattern "All test files must follow test_<module>_<feature>.py naming"

Begin by examining the project structure and key files, then systematically build memories for each agent.
"""
        return prompt.strip()
    
    def _find_claude_mpm(self) -> Optional[Path]:
        """Find the claude-mpm executable."""
        # Try different locations
        possible_paths = [
            # Local script in current directory
            Path("./claude-mpm"),
            # Installed in virtual environment
            Path("./venv/bin/claude-mpm"),
            # System PATH
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_file():
                return path
        
        # Try to find in PATH using which/where
        try:
            result = subprocess.run(
                ["which", "claude-mpm"] if sys.platform != "win32" else ["where", "claude-mpm"],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                return Path(result.stdout.strip().split('\n')[0])
        except:
            pass
        
        return None
    
    def execute(self, command: str, *args) -> Optional[str]:
        """Execute a command and return the result."""
        if command in self.commands:
            return self.commands[command](*args)
        return None
    
    def list_commands(self) -> list:
        """List all available commands."""
        return list(self.commands.keys())


def main():
    """Main entry point for command router."""
    router = CommandRouter()
    
    if len(sys.argv) < 2:
        print("Usage: command_router.py <command> [args...]")
        print(f"Available commands: {', '.join(router.list_commands())}")
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    result = router.execute(command, *args)
    if result is not None:
        print(result)
    else:
        print(f"Unknown command: {command}")
        print(f"Available commands: {', '.join(router.list_commands())}")
        sys.exit(1)


if __name__ == "__main__":
    main()