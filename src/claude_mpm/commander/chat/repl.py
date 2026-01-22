"""Commander chat REPL interface."""

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from claude_mpm.commander.instance_manager import InstanceManager
from claude_mpm.commander.llm.openrouter_client import OpenRouterClient
from claude_mpm.commander.models.events import EventType
from claude_mpm.commander.proxy.relay import OutputRelay
from claude_mpm.commander.session.manager import SessionManager

from .commands import Command, CommandParser, CommandType

if TYPE_CHECKING:
    from claude_mpm.commander.events.manager import EventManager
    from claude_mpm.commander.models.events import Event


class CommanderREPL:
    """Interactive REPL for Commander mode."""

    CAPABILITIES_CONTEXT = """
MPM Commander Capabilities:

INSTANCE MANAGEMENT:
- list/ls: Show all running Claude Code instances with their status
- connect <name>: Connect to a specific instance for interactive chat
- disconnect: Disconnect from current instance
- start <name>: Start a new Claude Code instance
- stop <name>: Stop a running instance
- status: Show current connection status

WHEN CONNECTED:
- Send natural language messages to Claude
- Receive streaming responses
- Access instance memory and context
- Execute multi-turn conversations

BUILT-IN COMMANDS:
- help: Show available commands
- exit/quit/q: Exit Commander

FEATURES:
- Real-time streaming responses
- Instance discovery via daemon
- Automatic reconnection handling
- Session context preservation
"""

    def __init__(
        self,
        instance_manager: InstanceManager,
        session_manager: SessionManager,
        output_relay: Optional[OutputRelay] = None,
        llm_client: Optional[OpenRouterClient] = None,
        event_manager: Optional["EventManager"] = None,
    ):
        """Initialize REPL.

        Args:
            instance_manager: Manages Claude instances.
            session_manager: Manages chat session state.
            output_relay: Optional relay for instance output.
            llm_client: Optional OpenRouter client for chat.
            event_manager: Optional event manager for notifications.
        """
        self.instances = instance_manager
        self.session = session_manager
        self.relay = output_relay
        self.llm = llm_client
        self.event_manager = event_manager
        self.parser = CommandParser()
        self._running = False

    async def run(self) -> None:
        """Start the REPL loop."""
        self._running = True
        self._print_welcome()

        # Wire up EventManager to InstanceManager
        if self.event_manager and self.instances:
            self.instances.set_event_manager(self.event_manager)

        # Subscribe to instance lifecycle events
        if self.event_manager:
            self.event_manager.subscribe(
                EventType.INSTANCE_STARTING, self._on_instance_event
            )
            self.event_manager.subscribe(
                EventType.INSTANCE_READY, self._on_instance_event
            )
            self.event_manager.subscribe(
                EventType.INSTANCE_ERROR, self._on_instance_event
            )

        # Setup history file
        history_path = Path.home() / ".claude-mpm" / "commander_history"
        history_path.parent.mkdir(parents=True, exist_ok=True)

        prompt = PromptSession(history=FileHistory(str(history_path)))

        while self._running:
            try:
                user_input = await asyncio.to_thread(prompt.prompt, self._get_prompt())
                await self._handle_input(user_input.strip())
            except KeyboardInterrupt:
                continue
            except EOFError:
                break

        self._print("\nGoodbye!")

    async def _handle_input(self, input_text: str) -> None:
        """Handle user input - command or natural language.

        Args:
            input_text: User input string.
        """
        if not input_text:
            return

        # Check if it's a built-in command
        command = self.parser.parse(input_text)
        if command:
            await self._execute_command(command)
        else:
            # Natural language - send to connected instance
            await self._send_to_instance(input_text)

    async def _execute_command(self, cmd: Command) -> None:
        """Execute a built-in command.

        Args:
            cmd: Parsed command.
        """
        handlers = {
            CommandType.LIST: self._cmd_list,
            CommandType.START: self._cmd_start,
            CommandType.STOP: self._cmd_stop,
            CommandType.CONNECT: self._cmd_connect,
            CommandType.DISCONNECT: self._cmd_disconnect,
            CommandType.STATUS: self._cmd_status,
            CommandType.HELP: self._cmd_help,
            CommandType.EXIT: self._cmd_exit,
        }
        handler = handlers.get(cmd.type)
        if handler:
            await handler(cmd.args)

    def _classify_intent(self, text: str) -> str:
        """Classify user input intent.

        Args:
            text: User input text.

        Returns:
            Intent type: 'greeting', 'capabilities', or 'chat'.
        """
        t = text.lower().strip()
        if any(t.startswith(g) for g in ["hello", "hi", "hey", "howdy"]):
            return "greeting"
        if any(p in t for p in ["what can you", "can you", "help me", "how do i"]):
            return "capabilities"
        return "chat"

    def _handle_greeting(self) -> None:
        """Handle greeting intent."""
        self._print(
            "Hello! I'm MPM Commander. Type 'help' for commands, or 'list' to see instances."
        )

    async def _handle_capabilities(self, query: str = "") -> None:
        """Answer questions about capabilities, using LLM if available.

        Args:
            query: Optional user query about capabilities.
        """
        if query and self.llm:
            try:
                messages = [
                    {
                        "role": "user",
                        "content": f"Based on these capabilities:\n{self.CAPABILITIES_CONTEXT}\n\nUser asks: {query}",
                    }
                ]
                system = (
                    "Answer concisely about MPM Commander capabilities. "
                    "If asked about something not in the capabilities, say so."
                )
                response = await self.llm.chat(messages, system=system)
                self._print(response)
                return
            except Exception:  # nosec B110 - Graceful fallback to static output
                pass
        # Fallback to static output
        self._print(self.CAPABILITIES_CONTEXT)

    async def _cmd_list(self, args: list[str]) -> None:
        """List active instances."""
        instances = self.instances.list_instances()
        if not instances:
            self._print("No active instances.")
        else:
            self._print("Active instances:")
            for inst in instances:
                status = (
                    "→" if inst.name == self.session.context.connected_instance else " "
                )
                git_info = f" [{inst.git_branch}]" if inst.git_branch else ""
                self._print(
                    f"  {status} {inst.name} ({inst.framework}){git_info} - {inst.project_path}"
                )

    async def _cmd_start(self, args: list[str]) -> None:
        """Start a new instance: start <path> [--framework cc|mpm] [--name name]."""
        if not args:
            self._print("Usage: start <path> [--framework cc|mpm] [--name name]")
            return

        # Parse arguments
        project_path = Path(args[0]).expanduser().resolve()
        framework = "cc"  # default
        name = project_path.name  # default

        # Parse optional flags
        i = 1
        while i < len(args):
            if args[i] == "--framework" and i + 1 < len(args):
                framework = args[i + 1]
                i += 2
            elif args[i] == "--name" and i + 1 < len(args):
                name = args[i + 1]
                i += 2
            else:
                i += 1

        # Validate path
        if not project_path.exists():
            self._print(f"Error: Path does not exist: {project_path}")
            return

        if not project_path.is_dir():
            self._print(f"Error: Path is not a directory: {project_path}")
            return

        # Start instance
        try:
            instance = await self.instances.start_instance(
                name, project_path, framework
            )
            self._print(f"Started instance '{name}' ({framework}) at {project_path}")
            self._print(f"Tmux: {instance.tmux_session}:{instance.pane_target}")
        except Exception as e:
            self._print(f"Error starting instance: {e}")

    async def _cmd_stop(self, args: list[str]) -> None:
        """Stop an instance: stop <name>."""
        if not args:
            self._print("Usage: stop <instance-name>")
            return

        name = args[0]

        try:
            await self.instances.stop_instance(name)
            self._print(f"Stopped instance '{name}'")

            # Disconnect if we were connected
            if self.session.context.connected_instance == name:
                self.session.disconnect()
        except Exception as e:
            self._print(f"Error stopping instance: {e}")

    async def _cmd_connect(self, args: list[str]) -> None:
        """Connect to an instance: connect <name>."""
        if not args:
            self._print("Usage: connect <instance-name>")
            return

        name = args[0]
        inst = self.instances.get_instance(name)
        if not inst:
            self._print(f"Instance '{name}' not found")
            return

        self.session.connect_to(name)
        self._print(f"Connected to {name}")

    async def _cmd_disconnect(self, args: list[str]) -> None:
        """Disconnect from current instance."""
        if not self.session.context.is_connected:
            self._print("Not connected to any instance")
            return

        name = self.session.context.connected_instance
        self.session.disconnect()
        self._print(f"Disconnected from {name}")

    async def _cmd_status(self, args: list[str]) -> None:
        """Show status of current session."""
        if self.session.context.is_connected:
            name = self.session.context.connected_instance
            inst = self.instances.get_instance(name)
            if inst:
                self._print(f"Connected to: {name}")
                self._print(f"  Framework: {inst.framework}")
                self._print(f"  Project: {inst.project_path}")
                if inst.git_branch:
                    self._print(f"  Git: {inst.git_branch} ({inst.git_status})")
                self._print(f"  Tmux: {inst.tmux_session}:{inst.pane_target}")
            else:
                self._print(f"Connected to: {name} (instance no longer exists)")
        else:
            self._print("Not connected to any instance")

        self._print(f"Messages in history: {len(self.session.context.messages)}")

    async def _cmd_help(self, args: list[str]) -> None:
        """Show help message."""
        help_text = """
Commander Commands:
  list, ls, instances   List active instances
  start <path>          Start new instance at path
    --framework <cc|mpm>  Specify framework (default: cc)
    --name <name>         Specify instance name (default: dir name)
  stop <name>           Stop an instance
  connect <name>        Connect to an instance
  disconnect            Disconnect from current instance
  status                Show current session status
  help                  Show this help message
  exit, quit, q         Exit Commander

Natural Language:
  When connected to an instance, any input that is not a built-in
  command will be sent to the connected instance as a message.

Examples:
  start ~/myproject --framework cc --name myapp
  connect myapp
  Fix the authentication bug in login.py
  disconnect
  exit
"""
        self._print(help_text)

    async def _cmd_exit(self, args: list[str]) -> None:
        """Exit the REPL."""
        self._running = False

    async def _send_to_instance(self, message: str) -> None:
        """Send natural language to connected instance.

        Args:
            message: User message to send.
        """
        # Check for greeting/capabilities intent before requiring connection
        intent = self._classify_intent(message)
        if intent == "greeting":
            self._handle_greeting()
            return
        if intent == "capabilities":
            await self._handle_capabilities(message)
            return

        if not self.session.context.is_connected:
            self._print("Not connected to any instance. Use 'connect <name>' first.")
            return

        name = self.session.context.connected_instance
        inst = self.instances.get_instance(name)
        if not inst:
            self._print(f"Instance '{name}' no longer exists")
            self.session.disconnect()
            return

        self._print(f"[Sending to {name}...]")
        await self.instances.send_to_instance(name, message)
        self.session.add_user_message(message)

        # Wait for and display response
        if self.relay:
            try:
                output = await self.relay.get_latest_output(
                    name, inst.pane_target, context=message
                )
                self._print(f"\n[Response from {name}]:\n{output}")
                self.session.add_assistant_message(output)
            except Exception as e:
                self._print(f"\n[Error getting response: {e}]")

    def _on_instance_event(self, event: "Event") -> None:
        """Handle instance lifecycle events with interrupt display.

        Args:
            event: The event to handle.
        """
        if event.type == EventType.INSTANCE_STARTING:
            print(f"\n[Starting] {event.title}")
        elif event.type == EventType.INSTANCE_READY:
            metadata = event.context or {}
            if metadata.get("timeout"):
                print(f"\n[Warning] {event.title} (startup timeout, may still work)")
            else:
                print(f"\n[Ready] {event.title}")
            # Show prompt hint
            instance_name = metadata.get("instance_name", "")
            if instance_name:
                print(f"   Use 'connect {instance_name}' to start chatting")
        elif event.type == EventType.INSTANCE_ERROR:
            print(f"\n[Error] {event.title}: {event.content}")

    def _get_prompt(self) -> str:
        """Get prompt string based on connection state.

        Returns:
            Prompt string for input.
        """
        if self.session.context.is_connected:
            return f"Commander ({self.session.context.connected_instance})> "
        return "Commander> "

    def _print(self, msg: str) -> None:
        """Print message to console.

        Args:
            msg: Message to print.
        """
        print(msg)

    def _print_welcome(self) -> None:
        """Print welcome message."""
        print("╔══════════════════════════════════════════╗")
        print("║  MPM Commander - Interactive Mode        ║")
        print("╚══════════════════════════════════════════╝")
        print("Type 'help' for commands, or natural language to chat.")
        print()
