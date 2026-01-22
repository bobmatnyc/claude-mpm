"""Built-in Commander chat commands."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CommandType(Enum):
    """Built-in command types."""

    LIST = "list"
    START = "start"
    STOP = "stop"
    CLOSE = "close"
    REGISTER = "register"
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    SAVED = "saved"
    FORGET = "forget"
    STATUS = "status"
    HELP = "help"
    EXIT = "exit"
    INSTANCES = "instances"  # alias for list
    OAUTH = "oauth"


@dataclass
class Command:
    """Parsed command with args."""

    type: CommandType
    args: list[str]
    raw: str


class CommandParser:
    """Parses user input into commands."""

    # Map slash command names to CommandType
    SLASH_COMMANDS = {
        "register": CommandType.REGISTER,
        "start": CommandType.START,
        "stop": CommandType.STOP,
        "close": CommandType.CLOSE,
        "connect": CommandType.CONNECT,
        "disconnect": CommandType.DISCONNECT,
        "switch": CommandType.CONNECT,  # alias for connect
        "list": CommandType.LIST,
        "ls": CommandType.LIST,
        "saved": CommandType.SAVED,
        "forget": CommandType.FORGET,
        "status": CommandType.STATUS,
        "help": CommandType.HELP,
        "exit": CommandType.EXIT,
        "quit": CommandType.EXIT,
        "q": CommandType.EXIT,
        "oauth": CommandType.OAUTH,
    }

    def parse(self, input_text: str) -> Optional[Command]:
        """Parse input into a Command.

        Returns None if input is not a slash command (natural language).
        System commands must start with '/'.

        Args:
            input_text: Raw user input.

        Returns:
            Command if input is a slash command, None otherwise.

        Example:
            >>> parser = CommandParser()
            >>> cmd = parser.parse("/list")
            >>> cmd.type
            <CommandType.LIST: 'list'>
            >>> parser.parse("tell me about the code")
            None
        """
        if not input_text:
            return None

        # System commands must start with /
        if not input_text.startswith("/"):
            return None

        # Remove the leading / and parse
        cmd_line = input_text[1:]
        parts = cmd_line.split()
        if not parts:
            return None

        command_str = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        # Check if it's a valid slash command
        if command_str in self.SLASH_COMMANDS:
            cmd_type = self.SLASH_COMMANDS[command_str]
            return Command(type=cmd_type, args=args, raw=input_text)

        # Unknown slash command
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
