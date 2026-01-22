"""Built-in Commander chat commands."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CommandType(Enum):
    """Built-in command types."""

    LIST = "list"
    START = "start"
    STOP = "stop"
    REGISTER = "register"
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    STATUS = "status"
    HELP = "help"
    EXIT = "exit"
    INSTANCES = "instances"  # alias for list


@dataclass
class Command:
    """Parsed command with args."""

    type: CommandType
    args: list[str]
    raw: str


class CommandParser:
    """Parses user input into commands."""

    ALIASES = {
        "ls": CommandType.LIST,
        "instances": CommandType.LIST,
        "quit": CommandType.EXIT,
        "q": CommandType.EXIT,
    }

    def parse(self, input_text: str) -> Optional[Command]:
        """Parse input into a Command.

        Returns None if input is not a built-in command (natural language).

        Args:
            input_text: Raw user input.

        Returns:
            Command if input is a built-in command, None otherwise.

        Example:
            >>> parser = CommandParser()
            >>> cmd = parser.parse("list")
            >>> cmd.type
            <CommandType.LIST: 'list'>
            >>> parser.parse("tell me about the code")
            None
        """
        if not input_text:
            return None

        parts = input_text.split()
        command_str = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        # Check if it's an alias
        if command_str in self.ALIASES:
            cmd_type = self.ALIASES[command_str]
            return Command(type=cmd_type, args=args, raw=input_text)

        # Check if it's a direct command
        try:
            cmd_type = CommandType(command_str)
            return Command(type=cmd_type, args=args, raw=input_text)
        except ValueError:
            # Not a built-in command
            return None

    def is_command(self, input_text: str) -> bool:
        """Check if input is a built-in command.

        Args:
            input_text: Raw user input.

        Returns:
            True if input is a built-in command, False otherwise.

        Example:
            >>> parser = CommandParser()
            >>> parser.is_command("list")
            True
            >>> parser.is_command("tell me about the code")
            False
        """
        return self.parse(input_text) is not None
