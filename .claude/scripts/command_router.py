#!/usr/bin/env python3
"""Simple command router for /mpm: commands."""

import sys
from typing import Dict, Callable, Optional


class CommandRouter:
    """Simple command dispatcher for /mpm: commands."""
    
    def __init__(self):
        self.commands: Dict[str, Callable] = {}
        self._register_builtin_commands()
    
    def _register_builtin_commands(self):
        """Register built-in commands."""
        self.register("test", self._test_command)
    
    def register(self, command: str, handler: Callable):
        """Register a command handler."""
        self.commands[command] = handler
    
    def _test_command(self, *args) -> str:
        """Simple test command that returns Hello World."""
        return "Hello World"
    
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