"""Commander chat REPL interface."""

import asyncio
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
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


class CommandCompleter(Completer):
    """Autocomplete for slash commands and instance names."""

    COMMANDS = [
        ("register", "Register and start a new instance"),
        ("start", "Start a registered instance"),
        ("stop", "Stop a running instance"),
        ("close", "Close instance and merge worktree"),
        ("connect", "Connect to an instance"),
        ("disconnect", "Disconnect from current instance"),
        ("switch", "Switch to another instance"),
        ("list", "List all instances"),
        ("ls", "List all instances (alias)"),
        ("status", "Show connection status"),
        ("help", "Show help"),
        ("exit", "Exit commander"),
        ("quit", "Exit commander (alias)"),
        ("q", "Exit commander (alias)"),
    ]

    def __init__(self, get_instances_func):
        """Initialize with function to get instance names.

        Args:
            get_instances_func: Callable that returns list of instance names.
        """
        self.get_instances = get_instances_func

    def get_completions(self, document, complete_event):
        """Generate completions for the current input.

        Args:
            document: The document being edited.
            complete_event: The completion event.

        Yields:
            Completion objects for matching commands or instance names.
        """
        text = document.text_before_cursor

        # Complete slash commands
        if text.startswith("/"):
            cmd_text = text[1:].lower()
            # Check if we're completing command args (has space after command)
            if " " in cmd_text:
                # Complete instance names after certain commands
                parts = cmd_text.split()
                cmd = parts[0]
                partial = parts[-1] if len(parts) > 1 else ""
                if cmd in ("start", "stop", "close", "connect", "switch"):
                    yield from self._complete_instance_names(partial)
            else:
                # Complete command names
                for cmd, desc in self.COMMANDS:
                    if cmd.startswith(cmd_text):
                        yield Completion(
                            cmd,
                            start_position=-len(cmd_text),
                            display_meta=desc,
                        )

        # Complete instance names after @ prefix
        elif text.startswith("@"):
            partial = text[1:]
            yield from self._complete_instance_names(partial)

        # Complete instance names inside parentheses
        elif text.startswith("("):
            # Extract partial name, stripping ) and : if present
            partial = text[1:].rstrip("):")
            yield from self._complete_instance_names(partial)

    def _complete_instance_names(self, partial: str):
        """Generate completions for instance names.

        Args:
            partial: Partial instance name typed so far.

        Yields:
            Completion objects for matching instance names.
        """
        try:
            instances = self.get_instances()
            for name in instances:
                if name.lower().startswith(partial.lower()):
                    yield Completion(
                        name,
                        start_position=-len(partial),
                        display_meta="instance",
                    )
        except Exception:  # nosec B110 - Graceful fallback if instance lookup fails
            pass


class CommanderREPL:
    """Interactive REPL for Commander mode."""

    CAPABILITIES_CONTEXT = """
MPM Commander Capabilities:

INSTANCE MANAGEMENT (use / prefix):
- /list, /ls: Show all running Claude Code instances with their status
- /register <path> <framework> <name>: Register, start, and auto-connect
- /start <name>: Start a registered instance by name
- /stop <name>: Stop a running instance (keeps worktree)
- /close <name> [--no-merge]: Close instance, merge worktree to main, and cleanup
- /connect <name>: Connect to a specific instance for interactive chat
- /switch <name>: Alias for /connect
- /disconnect: Disconnect from current instance
- /status: Show current connection status

DIRECT MESSAGING (both syntaxes work the same):
- @<name> <message>: Send message directly to any instance
- (<name>) <message>: Same as @name (parentheses syntax)
- Instance names appear in responses: @myapp: response summary...

WHEN CONNECTED:
- Send natural language messages to Claude (no / prefix)
- Receive streaming responses
- Access instance memory and context
- Execute multi-turn conversations

BUILT-IN COMMANDS:
- /help: Show available commands
- /exit, /quit, /q: Exit Commander

FEATURES:
- Real-time streaming responses
- Direct @mention messaging to any instance
- Worktree isolation and merge workflow
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
        self._instance_ready: dict[str, bool] = {}

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

        # Create completer for slash commands and instance names
        completer = CommandCompleter(self._get_instance_names)

        prompt = PromptSession(
            history=FileHistory(str(history_path)),
            completer=completer,
            complete_while_typing=False,  # Only complete on Tab
        )

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

        # Check for direct @mention first (before any other parsing)
        mention = self._parse_mention(input_text)
        if mention:
            target, message = mention
            await self._cmd_message_instance(target, message)
            return

        # Check if it's a built-in slash command first
        command = self.parser.parse(input_text)
        if command:
            await self._execute_command(command)
            return

        # Use LLM to classify natural language input
        intent_result = await self._classify_intent_llm(input_text)
        intent = intent_result.get("intent", "chat")
        args = intent_result.get("args", {})

        # Handle command intents detected by LLM
        if intent == "register":
            await self._cmd_register_from_args(args)
        elif intent == "start":
            await self._cmd_start_from_args(args)
        elif intent == "stop":
            await self._cmd_stop_from_args(args)
        elif intent in {"connect", "switch"}:
            await self._cmd_connect_from_args(args)
        elif intent == "disconnect":
            await self._cmd_disconnect([])
        elif intent == "list":
            await self._cmd_list([])
        elif intent == "status":
            await self._cmd_status([])
        elif intent == "help":
            await self._cmd_help([])
        elif intent == "exit":
            await self._cmd_exit([])
        elif intent == "capabilities":
            await self._handle_capabilities(input_text)
        elif intent == "greeting":
            self._handle_greeting()
        elif intent == "message":
            # Handle @mention detected by LLM
            target = args.get("target")
            message = args.get("message")
            if target and message:
                await self._cmd_message_instance(target, message)
            else:
                await self._send_to_instance(input_text)
        else:
            # Default to chat - send to connected instance
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
            CommandType.CLOSE: self._cmd_close,
            CommandType.REGISTER: self._cmd_register,
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

    def _parse_mention(self, text: str) -> tuple[str, str] | None:
        """Parse @name or (name) message patterns - both work the same.

        Both syntaxes are equivalent:
          @name message
          (name) message
          (name): message

        Args:
            text: User input text.

        Returns:
            Tuple of (target_name, message) if pattern matches, None otherwise.
        """
        # @name message
        match = re.match(r"^@(\w+)\s+(.+)$", text.strip())
        if match:
            return match.group(1), match.group(2)

        # (name): message or (name) message - same behavior as @name
        match = re.match(r"^\((\w+)\):?\s*(.+)$", text.strip())
        if match:
            return match.group(1), match.group(2)

        return None

    async def _classify_intent_llm(self, text: str) -> dict:
        """Use LLM to classify user intent.

        Args:
            text: User input text.

        Returns:
            Dict with 'intent' and 'args' keys.
        """
        if not self.llm:
            return {"intent": "chat", "args": {}}

        system_prompt = """Classify user intent. Return JSON only.

Commands available:
- register: Register new instance (needs: path, framework, name)
- start: Start registered instance (needs: name)
- stop: Stop instance (needs: name)
- connect: Connect to instance (needs: name)
- disconnect: Disconnect from current instance
- switch: Switch to different instance (needs: name)
- list: List instances
- status: Show status
- help: Show help
- exit: Exit commander

If user wants a command, extract arguments.
If user is chatting/asking questions, intent is "chat".

Examples:
"register my project at ~/foo as myapp using mpm" -> {"intent":"register","args":{"path":"~/foo","framework":"mpm","name":"myapp"}}
"start myapp" -> {"intent":"start","args":{"name":"myapp"}}
"stop the server" -> {"intent":"stop","args":{"name":null}}
"list instances" -> {"intent":"list","args":{}}
"hello how are you" -> {"intent":"chat","args":{}}
"what can you do" -> {"intent":"capabilities","args":{}}
"@izzie show me the code" -> {"intent":"message","args":{"target":"izzie","message":"show me the code"}}
"(myapp): what's the status" -> {"intent":"message","args":{"target":"myapp","message":"what's the status"}}

Return ONLY valid JSON."""

        try:
            messages = [{"role": "user", "content": f"Classify: {text}"}]
            response = await self.llm.chat(messages, system=system_prompt)
            return json.loads(response.strip())
        except (json.JSONDecodeError, Exception):  # nosec B110 - Graceful fallback
            return {"intent": "chat", "args": {}}

    def _handle_greeting(self) -> None:
        """Handle greeting intent."""
        self._print(
            "Hello! I'm MPM Commander. Type '/help' for commands, or '/list' to see instances."
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
        """Start instance: start <name> OR start <path> [--framework cc|mpm] [--name name]."""
        if not args:
            self._print("Usage: start <name>  (for registered instances)")
            self._print("       start <path> [--framework cc|mpm] [--name name]")
            return

        # Check if first arg is a registered instance name (no path separators)
        if len(args) == 1 and "/" not in args[0] and not args[0].startswith("~"):
            name = args[0]
            try:
                instance = await self.instances.start_by_name(name)
                if instance:
                    self._print(f"Started registered instance '{name}'")
                    self._print(
                        f"  Tmux: {instance.tmux_session}:{instance.pane_target}"
                    )
                else:
                    self._print(f"No registered instance named '{name}'")
                    self._print(
                        "Use 'register <path> <framework> <name>' to register first"
                    )
            except Exception as e:
                self._print(f"Error starting instance: {e}")
            return

        # Path-based start logic
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

    async def _cmd_close(self, args: list[str]) -> None:
        """Close instance: merge worktree to main and end session.

        Usage: /close <name> [--no-merge]
        """
        if not args:
            self._print("Usage: /close <name> [--no-merge]")
            return

        name = args[0]
        merge = "--no-merge" not in args

        # Disconnect if we were connected
        if self.session.context.connected_instance == name:
            self.session.disconnect()

        success, msg = await self.instances.close_instance(name, merge=merge)
        if success:
            self._print(f"Closed '{name}'")
            if merge:
                self._print("  Worktree merged to main")
        else:
            self._print(f"Error: {msg}")

    async def _cmd_register(self, args: list[str]) -> None:
        """Register and start an instance: register <path> <framework> <name>."""
        if len(args) < 3:
            self._print("Usage: register <path> <framework> <name>")
            self._print("  framework: cc (Claude Code) or mpm")
            return

        path, framework, name = args[0], args[1], args[2]
        path = Path(path).expanduser().resolve()

        if framework not in ("cc", "mpm"):
            self._print(f"Unknown framework: {framework}. Use 'cc' or 'mpm'")
            return

        # Validate path
        if not path.exists():
            self._print(f"Error: Path does not exist: {path}")
            return

        if not path.is_dir():
            self._print(f"Error: Path is not a directory: {path}")
            return

        try:
            instance = await self.instances.register_instance(
                str(path), framework, name
            )
            self._print(f"Registered and started '{name}' ({framework}) at {path}")
            self._print(f"  Tmux: {instance.tmux_session}:{instance.pane_target}")
            self._print(f"Waiting for '{name}' to be ready...")

            # Wait for instance to be ready before auto-connecting
            ready = await self.instances.wait_for_ready(name, timeout=30)
            if ready:
                self.session.connect_to(name)
                self._print(f"Connected to '{name}'")
        except Exception as e:
            self._print(f"Failed to register: {e}")

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
Commander Commands (use / prefix):
  /register <path> <framework> <name>
                        Register, start, and auto-connect to instance
  /start <name>         Start a registered instance by name
  /stop <name>          Stop an instance (keeps worktree)
  /close <name> [--no-merge]
                        Close instance: merge worktree to main and cleanup
  /connect <name>       Connect to an instance
  /switch <name>        Alias for /connect
  /disconnect           Disconnect from current instance
  /list, /ls            List active instances
  /status               Show current session status
  /help                 Show this help message
  /exit, /quit, /q      Exit Commander

Direct Messaging (both syntaxes work the same):
  @<name> <message>     Send message to specific instance
  (<name>) <message>    Same as @name (parentheses syntax)

Natural Language:
  Any input without / prefix is sent to the connected instance.

Examples:
  /register ~/myproject cc myapp  # Register, start, and connect
  /start myapp                    # Start registered instance
  /close myapp                    # Merge worktree to main and cleanup
  /close myapp --no-merge         # Cleanup without merging
  @myapp show me the code         # Direct message to myapp
  (izzie) what's the status       # Same as @izzie
  Fix the authentication bug      # Send to connected instance
  /exit
"""
        self._print(help_text)

    async def _cmd_exit(self, args: list[str]) -> None:
        """Exit the REPL."""
        self._running = False

    # Helper methods for LLM-extracted arguments

    async def _cmd_register_from_args(self, args: dict) -> None:
        """Handle register command from LLM-extracted args.

        Args:
            args: Dict with optional 'path', 'framework', 'name' keys.
        """
        path = args.get("path")
        framework = args.get("framework")
        name = args.get("name")

        if not all([path, framework, name]):
            self._print("I need the path, framework, and name to register an instance.")
            self._print("Example: 'register ~/myproject as myapp using mpm'")
            return

        await self._cmd_register([path, framework, name])

    async def _cmd_start_from_args(self, args: dict) -> None:
        """Handle start command from LLM-extracted args.

        Args:
            args: Dict with optional 'name' key.
        """
        name = args.get("name")
        if not name:
            # Try to infer from connected instance or list available
            instances = self.instances.list_instances()
            if len(instances) == 1:
                name = instances[0].name
            else:
                self._print("Which instance should I start?")
                await self._cmd_list([])
                return

        await self._cmd_start([name])

    async def _cmd_stop_from_args(self, args: dict) -> None:
        """Handle stop command from LLM-extracted args.

        Args:
            args: Dict with optional 'name' key.
        """
        name = args.get("name")
        if not name:
            # Try to use connected instance
            if self.session.context.is_connected:
                name = self.session.context.connected_instance
            else:
                self._print("Which instance should I stop?")
                await self._cmd_list([])
                return

        await self._cmd_stop([name])

    async def _cmd_connect_from_args(self, args: dict) -> None:
        """Handle connect command from LLM-extracted args.

        Args:
            args: Dict with optional 'name' key.
        """
        name = args.get("name")
        if not name:
            instances = self.instances.list_instances()
            if len(instances) == 1:
                name = instances[0].name
            else:
                self._print("Which instance should I connect to?")
                await self._cmd_list([])
                return

        await self._cmd_connect([name])

    async def _cmd_message_instance(self, target: str, message: str) -> None:
        """Send message to specific instance without connecting.

        Args:
            target: Instance name to message.
            message: Message to send.
        """
        # Check if instance exists
        inst = self.instances.get_instance(target)
        if not inst:
            # Try to start if registered
            try:
                inst = await self.instances.start_by_name(target)
            except Exception:
                inst = None

            if not inst:
                self._print(
                    f"Instance '{target}' not found. Use /list to see instances."
                )
                return

        # Send message to instance
        await self.instances.send_to_instance(target, message)

        # Wait for and display response
        if self.relay:
            try:
                output = await self.relay.get_latest_output(
                    target, inst.pane_target, context=message
                )
                self._display_response(target, output)
            except Exception as e:
                self._print(f"\n[Error getting response from {target}: {e}]")

    def _display_response(self, instance_name: str, response: str) -> None:
        """Display response from instance above prompt.

        Args:
            instance_name: Name of the instance that responded.
            response: Response content.
        """
        # Summarize if too long
        summary = response[:100] + "..." if len(response) > 100 else response
        summary = summary.replace("\n", " ")
        print(f"\n@{instance_name}: {summary}")

    async def _send_to_instance(self, message: str) -> None:
        """Send natural language to connected instance.

        Args:
            message: User message to send.
        """
        # Check if instance is connected and ready
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
            instance_name = metadata.get("instance_name", "")

            # Mark instance as ready
            if instance_name:
                self._instance_ready[instance_name] = True

            if metadata.get("timeout"):
                print(f"\n[Warning] {event.title} (startup timeout, may still work)")
            else:
                print(f"\n[Ready] {event.title}")

            # Show ready notification based on whether this is the connected instance
            if (
                instance_name
                and instance_name == self.session.context.connected_instance
            ):
                print(f"\n({instance_name}) ready")
            elif instance_name:
                print(f"   Use @{instance_name} or /connect {instance_name}")
        elif event.type == EventType.INSTANCE_ERROR:
            print(f"\n[Error] {event.title}: {event.content}")

    def _get_prompt(self) -> str:
        """Get prompt string.

        Returns:
            Prompt string for input, showing instance name when ready.
        """
        connected = self.session.context.connected_instance
        if connected and self._instance_ready.get(connected):
            return f"Commander ({connected})> "
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
        print("Type '/help' for commands, or natural language to chat.")
        print()

    def _get_instance_names(self) -> list[str]:
        """Get list of instance names for autocomplete.

        Returns:
            List of instance names (running and registered).
        """
        names: list[str] = []

        # Running instances
        if self.instances:
            try:
                for inst in self.instances.list_instances():
                    if inst.name not in names:
                        names.append(inst.name)
            except Exception:  # nosec B110 - Graceful fallback
                pass

        # Registered instances from state store
        if self.instances and hasattr(self.instances, "_state_store"):
            try:
                state_store = self.instances._state_store
                if state_store:
                    for name in state_store.load_instances():
                        if name not in names:
                            names.append(name)
            except Exception:  # nosec B110 - Graceful fallback
                pass

        return names
