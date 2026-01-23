"""Commander chat REPL interface."""

import asyncio
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from prompt_toolkit import PromptSession, prompt as pt_prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout


class RequestStatus(Enum):
    """Status of a pending request."""

    QUEUED = "queued"
    SENDING = "sending"
    WAITING = "waiting"
    STARTING = "starting"  # Instance starting up
    COMPLETED = "completed"
    ERROR = "error"


class RequestType(Enum):
    """Type of pending request."""

    MESSAGE = "message"  # Message to instance
    STARTUP = "startup"  # Instance startup/ready wait


@dataclass
class PendingRequest:
    """Tracks an in-flight request to an instance."""

    id: str
    target: str  # Instance name
    message: str
    request_type: RequestType = RequestType.MESSAGE
    status: RequestStatus = RequestStatus.QUEUED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    response: Optional[str] = None
    error: Optional[str] = None

    def elapsed_seconds(self) -> int:
        """Get elapsed time since request was created."""
        return int((datetime.now(timezone.utc) - self.created_at).total_seconds())

    def display_message(self, max_len: int = 40) -> str:
        """Get truncated message for display."""
        msg = self.message.replace("\n", " ")
        if len(msg) > max_len:
            return msg[: max_len - 3] + "..."
        return msg


@dataclass
class SavedRegistration:
    """A saved instance registration for persistence."""

    name: str
    path: str
    framework: str  # "cc" or "mpm"
    registered_at: str  # ISO timestamp

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "path": self.path,
            "framework": self.framework,
            "registered_at": self.registered_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SavedRegistration":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            path=data["path"],
            framework=data["framework"],
            registered_at=data.get(
                "registered_at", datetime.now(timezone.utc).isoformat()
            ),
        )


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
        ("connect", "Connect to instance (starts from saved if needed)"),
        ("disconnect", "Disconnect from current instance"),
        ("switch", "Switch to another instance"),
        ("list", "List all instances"),
        ("ls", "List all instances (alias)"),
        ("saved", "List saved registrations"),
        ("forget", "Remove a saved registration"),
        ("status", "Show connection status"),
        ("send", "Send literal text to tmux session"),
        ("cleanup", "Clean up orphan tmux panes"),
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
- /register <path> <framework> <name>: Register, start, and auto-connect (creates worktree)
- /start <name>: Start a registered instance by name
- /start <path> [--framework cc|mpm] [--name name]: Start new instance (creates worktree)
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

        # Async request tracking
        self._pending_requests: dict[str, PendingRequest] = {}
        self._request_queue: asyncio.Queue[PendingRequest] = asyncio.Queue()
        self._response_task: Optional[asyncio.Task] = None
        self._startup_tasks: dict[str, asyncio.Task] = {}  # Background startup tasks
        self._stdout_context = None  # For patch_stdout

        # Bottom toolbar status for spinners
        self._toolbar_status = ""
        self.prompt_session: Optional[PromptSession] = None

        # Persistent registration config
        self._config_dir = Path.cwd() / ".claude-mpm" / "commander"
        self._config_file = self._config_dir / "registrations.json"
        self._saved_registrations: dict[str, SavedRegistration] = {}
        self._load_registrations()

    def _get_bottom_toolbar(self) -> str:
        """Get bottom toolbar status for prompt_toolkit.

        Returns:
            Status string for display in toolbar, or empty string if no status.
        """
        return self._toolbar_status

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

        self.prompt_session = PromptSession(
            history=FileHistory(str(history_path)),
            completer=completer,
            complete_while_typing=False,  # Only complete on Tab
            bottom_toolbar=self._get_bottom_toolbar,
        )

        # Start background response processor
        self._response_task = asyncio.create_task(self._process_responses())

        # Use patch_stdout to allow printing above prompt
        with patch_stdout():
            while self._running:
                try:
                    # Show pending requests status above prompt
                    self._render_pending_status()
                    user_input = await self.prompt_session.prompt_async(
                        self._get_prompt
                    )
                    await self._handle_input(user_input.strip())
                except KeyboardInterrupt:
                    continue
                except EOFError:
                    break

        # Cleanup
        if self._response_task:
            self._response_task.cancel()
            try:
                await self._response_task
            except asyncio.CancelledError:
                pass

        # Stop all running instances before exiting
        instances_to_stop = self.instances.list_instances()
        for instance in instances_to_stop:
            try:
                await self.instances.stop_instance(instance.name)
            except Exception as e:
                self._print(f"Warning: Failed to stop '{instance.name}': {e}")

        self._print("\nGoodbye!")

    def _load_registrations(self) -> None:
        """Load saved registrations from config file."""
        if not self._config_file.exists():
            return
        try:
            with self._config_file.open() as f:
                data = json.load(f)
            for reg_data in data.get("registrations", []):
                reg = SavedRegistration.from_dict(reg_data)
                self._saved_registrations[reg.name] = reg
        except (json.JSONDecodeError, KeyError, OSError):
            # Ignore corrupt/unreadable config
            pass

    def _save_registrations(self) -> None:
        """Save registrations to config file."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "registrations": [
                reg.to_dict() for reg in self._saved_registrations.values()
            ]
        }
        with self._config_file.open("w") as f:
            json.dump(data, f, indent=2)

    def _save_registration(self, name: str, path: str, framework: str) -> None:
        """Save a single registration."""
        reg = SavedRegistration(
            name=name,
            path=path,
            framework=framework,
            registered_at=datetime.now(timezone.utc).isoformat(),
        )
        self._saved_registrations[name] = reg
        self._save_registrations()

    def _forget_registration(self, name: str) -> bool:
        """Remove a saved registration. Returns True if removed."""
        if name in self._saved_registrations:
            del self._saved_registrations[name]
            self._save_registrations()
            return True
        return False

    async def _handle_input(self, input_text: str) -> None:
        """Handle user input - command or natural language.

        Args:
            input_text: User input string.
        """
        if not input_text:
            return

        # Parse @instance prefix for slash commands
        target_instance = None
        remaining_text = input_text
        if input_text.startswith("@"):
            parts = input_text.split(None, 1)
            if len(parts) >= 1:
                target_instance = parts[0][1:]  # Remove @ prefix
                remaining_text = parts[1] if len(parts) > 1 else ""

        # Check for direct @mention message (if no slash command follows)
        if target_instance and not remaining_text.startswith("/"):
            mention = self._parse_mention(input_text)
            if mention:
                target, message = mention
                await self._cmd_message_instance(target, message)
                return

        # Check if it's a built-in slash command (parse the remaining text)
        command_text = remaining_text if target_instance else input_text
        command = self.parser.parse(command_text)
        if command:
            await self._execute_command(command, target_instance=target_instance)
            return

        # If we had @instance prefix but no command, it was a message
        if target_instance:
            message = remaining_text
            if message:
                await self._cmd_message_instance(target_instance, message)
            else:
                self._print(
                    f"Instance '{target_instance}' prefix requires a message or command"
                )
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

    async def _execute_command(
        self, cmd: Command, target_instance: Optional[str] = None
    ) -> None:
        """Execute a built-in command.

        Args:
            cmd: Parsed command.
            target_instance: Optional target instance name for @instance prefix.
        """
        handlers = {
            CommandType.LIST: self._cmd_list,
            CommandType.START: self._cmd_start,
            CommandType.STOP: self._cmd_stop,
            CommandType.CLOSE: self._cmd_close,
            CommandType.REGISTER: self._cmd_register,
            CommandType.CONNECT: self._cmd_connect,
            CommandType.DISCONNECT: self._cmd_disconnect,
            CommandType.SAVED: self._cmd_saved,
            CommandType.FORGET: self._cmd_forget,
            CommandType.STATUS: self._cmd_status,
            CommandType.HELP: self._cmd_help,
            CommandType.EXIT: self._cmd_exit,
            CommandType.MPM_OAUTH: self._cmd_oauth,
            CommandType.CLEANUP: self._cmd_cleanup,
            CommandType.SEND: self._cmd_send,
        }
        handler = handlers.get(cmd.type)
        if handler:
            # For target-specific commands, pass target_instance if provided
            if cmd.type in {CommandType.STATUS, CommandType.SEND, CommandType.STOP}:
                await handler(cmd.args, target_instance=target_instance)
            else:
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
        """List instances: both running and saved registrations.

        Shows:
        - Running instances with status (connected, ready, or connecting)
        - Saved registrations that are not currently running
        """
        running_instances = self.instances.list_instances()
        running_names = {inst.name for inst in running_instances}
        saved_registrations = self._saved_registrations

        # Collect all unique names
        all_names = set(running_names) | set(saved_registrations.keys())

        if not all_names:
            self._print("No instances (running or saved).")
            self._print("Use '/register <path> <framework> <name>' to create one.")
            return

        # Build output
        self._print("Sessions:")

        # Display in order: running first, then saved
        for name in sorted(all_names):
            inst = next((i for i in running_instances if i.name == name), None)
            is_connected = inst and name == self.session.context.connected_instance

            if inst:
                # Running instance
                git_info = f" [{inst.git_branch}]" if inst.git_branch else ""

                # Determine status
                if is_connected:
                    instance_status = "connected"
                elif inst.ready:
                    instance_status = "ready"
                else:
                    instance_status = "starting"

                # Format with right-aligned path
                line = f"  {name} (running, {instance_status})"
                path_display = f"{inst.project_path}{git_info}"
                # Pad to align paths
                padding = max(1, 40 - len(line))
                self._print(f"{line}{' ' * padding}{path_display}")
            else:
                # Saved registration (not running)
                reg = saved_registrations[name]
                line = f"  {name} (saved)"
                # Pad to align paths
                padding = max(1, 40 - len(line))
                self._print(f"{line}{' ' * padding}{reg.path}")

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

        # Register and start instance (creates worktree for git repos)
        try:
            instance = await self.instances.register_instance(
                str(project_path), framework, name
            )
            self._print(f"Started instance '{name}' ({framework}) at {project_path}")
            self._print(f"  Tmux: {instance.tmux_session}:{instance.pane_target}")

            # Check if worktree was created
            if self.instances._state_store:
                registered = self.instances._state_store.get_instance(name)
                if registered and registered.use_worktree and registered.worktree_path:
                    self._print(f"  Worktree: {registered.worktree_path}")
                    self._print(f"  Branch: {registered.worktree_branch}")

            # Spawn background task to wait for ready (non-blocking with spinner)
            self._spawn_startup_task(name, auto_connect=True, timeout=30)
        except Exception as e:
            self._print(f"Error starting instance: {e}")

    async def _cmd_stop(
        self, args: list[str], target_instance: Optional[str] = None
    ) -> None:
        """Stop an instance.

        Usage:
            /stop <name>      # Stop by name
            @instance /stop   # Stop specific instance via @instance prefix

        Args:
            args: Command arguments (instance name, if not using @instance prefix).
            target_instance: Optional target instance name from @instance prefix.
        """
        # Use target instance if provided via @instance prefix
        if target_instance:
            name = target_instance
        else:
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

            # Save registration for persistence
            self._save_registration(name, str(path), framework)

            # Spawn background task to wait for ready (non-blocking with spinner)
            self._spawn_startup_task(name, auto_connect=True, timeout=30)
        except Exception as e:
            self._print(f"Failed to register: {e}")

    async def _cmd_connect(self, args: list[str]) -> None:
        """Connect to an instance: connect <name>.

        If instance is not running but has saved registration, start it first.
        """
        if not args:
            self._print("Usage: connect <instance-name>")
            return

        name = args[0]
        inst = self.instances.get_instance(name)

        if not inst:
            # Check if we have a saved registration
            saved = self._saved_registrations.get(name)
            if saved:
                self._print(f"Starting '{name}' from saved config...")
                try:
                    instance = await self.instances.register_instance(
                        saved.path, saved.framework, name
                    )
                    self._print(f"Started '{name}' ({saved.framework}) at {saved.path}")
                    self._print(
                        f"  Tmux: {instance.tmux_session}:{instance.pane_target}"
                    )
                    # Spawn background task to wait for ready (non-blocking with spinner)
                    self._spawn_startup_task(name, auto_connect=True, timeout=30)
                    return
                except Exception as e:
                    self._print(f"Failed to start from saved config: {e}")
                    return
            else:
                self._print(f"Instance '{name}' not found")
                self._print("  Use /saved to see saved registrations")
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

    async def _cmd_status(
        self, args: list[str], target_instance: Optional[str] = None
    ) -> None:
        """Show status of current session or a specific instance.

        Args:
            args: Command arguments (unused if target_instance is provided).
            target_instance: Optional target instance name from @instance prefix.
        """
        # Use target instance if provided via @instance prefix
        if target_instance:
            inst = self.instances.get_instance(target_instance)
            if not inst:
                self._print(f"Instance '{target_instance}' not found")
                return
            self._print(f"Status of {target_instance}:")
            self._print(f"  Framework: {inst.framework}")
            self._print(f"  Project: {inst.project_path}")
            if inst.git_branch:
                self._print(f"  Git: {inst.git_branch} ({inst.git_status})")
            self._print(f"  Tmux: {inst.tmux_session}:{inst.pane_target}")
            self._print(f"  Ready: {'Yes' if inst.ready else 'No'}")
            return

        # Default behavior - show connected instance status
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

    async def _cmd_send(
        self, args: list[str], target_instance: Optional[str] = None
    ) -> None:
        """Send literal text directly to a tmux session.

        Usage:
            /send /help                    # Send to connected instance
            /send /mpm-status
            /send ls -la
            @instance /send /help          # Send to specific instance

        The text (including slash commands) is sent verbatim to the pane.

        Args:
            args: Command arguments (the text to send).
            target_instance: Optional target instance name from @instance prefix.
        """
        if not args:
            self._print("Usage: /send <text>")
            self._print("Send literal text to the tmux session")
            return

        # Determine target instance
        if target_instance:
            instance_name = target_instance
            inst = self.instances.get_instance(instance_name)
            if not inst:
                self._print(f"Instance '{instance_name}' not found")
                return
        else:
            if not self.session.context.is_connected:
                self._print("Not connected to any instance")
                return
            instance_name = self.session.context.connected_instance
            inst = self.instances.get_instance(instance_name)
            if not inst:
                self._print(f"Instance '{instance_name}' no longer exists")
                return

        # Reconstruct the full text from args
        text = " ".join(args)
        pane_target = f"{inst.tmux_session}:{inst.pane_target}"

        try:
            success = self.instances.orchestrator.send_keys(pane_target, text)
            if success:
                self._print(f"Sent to {instance_name}: {text}")
            else:
                self._print(f"Failed to send to {instance_name}")
        except Exception as e:
            self._print(f"Error sending to {instance_name}: {e}")

    async def _cmd_saved(self, args: list[str]) -> None:
        """List saved registrations."""
        if not self._saved_registrations:
            self._print("No saved registrations")
            self._print("  Use /register to create one")
            return

        self._print("Saved registrations:")
        for reg in self._saved_registrations.values():
            running = self.instances.get_instance(reg.name) is not None
            status = " (running)" if running else ""
            self._print(f"  {reg.name}: {reg.path} [{reg.framework}]{status}")

    async def _cmd_forget(self, args: list[str]) -> None:
        """Remove a saved registration: forget <name>."""
        if not args:
            self._print("Usage: forget <name>")
            return

        name = args[0]
        if self._forget_registration(name):
            self._print(f"Removed saved registration '{name}'")
        else:
            self._print(f"No saved registration named '{name}'")

    async def _cmd_help(self, args: list[str]) -> None:
        """Show help message."""
        help_text = """
Commander Commands (use / prefix):
  /register <path> <framework> <name>
                        Register, start, and auto-connect (creates worktree)
  /connect <name>       Connect to instance (starts from saved config if needed)
  /switch <name>        Alias for /connect
  /disconnect           Disconnect from current instance
  /start <name>         Start a registered instance by name
  /start <path>         Start new instance (creates worktree for git repos)
  /stop <name>          Stop an instance (keeps worktree)
  /close <name> [--no-merge]
                        Close instance: merge worktree to main and cleanup
  /list, /ls            List active instances
  /saved                List saved registrations
  /forget <name>        Remove a saved registration
  /status               Show current session status
  /send <text>          Send literal text directly to connected tmux session
  /cleanup [--force]    Clean up orphan tmux panes (--force to kill them)
  /help                 Show this help message
  /exit, /quit, /q      Exit Commander

Direct Messaging (both syntaxes work the same):
  @<name> <message>     Send message to specific instance
  (<name>) <message>    Same as @name (parentheses syntax)

Instance-Targeted Commands (@ prefix):
  @<name> /status       Show status of specific instance
  @<name> /send <text>  Send text to specific instance (no connection needed)
  @<name> /stop         Stop specific instance

Natural Language:
  Any input without / prefix is sent to the connected instance.

Git Worktree Isolation:
  When starting instances in git repos, a worktree is created on a
  session-specific branch. Use /close to merge changes back to main.

Examples:
  /register ~/myproject cc myapp  # Register, start, and connect
  /start ~/myproject              # Start with auto-detected name
  /start myapp                    # Start registered instance
  /close myapp                    # Merge worktree to main and cleanup
  /close myapp --no-merge         # Cleanup without merging
  /cleanup                        # Show orphan panes
  /cleanup --force                # Kill orphan panes
  @myapp show me the code         # Direct message to myapp
  (izzie) what's the status       # Same as @izzie
  @duetto /status                 # Check status of duetto instance
  @mpm /send /help                # Send /help to mpm instance
  @duetto /stop                   # Stop duetto without connecting
  Fix the authentication bug      # Send to connected instance
  /exit
"""
        self._print(help_text)

    async def _cmd_exit(self, args: list[str]) -> None:
        """Exit the REPL and stop all running instances."""
        # Stop all running instances before exiting
        instances_to_stop = self.instances.list_instances()
        for instance in instances_to_stop:
            try:
                await self.instances.stop_instance(instance.name)
            except Exception as e:
                self._print(f"Warning: Failed to stop '{instance.name}': {e}")

        self._running = False

    async def _cmd_oauth(self, args: list[str]) -> None:
        """Handle OAuth command with subcommands.

        Usage:
            /mpm-oauth                 - Show help
            /mpm-oauth list            - List OAuth-capable services
            /mpm-oauth setup <service> - Set up OAuth for a service
            /mpm-oauth status <service> - Show token status
            /mpm-oauth revoke <service> - Revoke OAuth tokens
            /mpm-oauth refresh <service> - Refresh OAuth tokens
        """
        if not args:
            await self._cmd_oauth_help()
            return

        subcommand = args[0].lower()
        subargs = args[1:] if len(args) > 1 else []

        if subcommand == "help":
            await self._cmd_oauth_help()
        elif subcommand == "list":
            await self._cmd_oauth_list()
        elif subcommand == "setup":
            if not subargs:
                self._print("Usage: /mpm-oauth setup <service>")
                return
            await self._cmd_oauth_setup(subargs[0])
        elif subcommand == "status":
            if not subargs:
                self._print("Usage: /mpm-oauth status <service>")
                return
            await self._cmd_oauth_status(subargs[0])
        elif subcommand == "revoke":
            if not subargs:
                self._print("Usage: /mpm-oauth revoke <service>")
                return
            await self._cmd_oauth_revoke(subargs[0])
        elif subcommand == "refresh":
            if not subargs:
                self._print("Usage: /mpm-oauth refresh <service>")
                return
            await self._cmd_oauth_refresh(subargs[0])
        else:
            self._print(f"Unknown subcommand: {subcommand}")
            await self._cmd_oauth_help()

    async def _cmd_oauth_help(self) -> None:
        """Print OAuth command help."""
        help_text = """
OAuth Commands:
  /mpm-oauth list            List OAuth-capable MCP services
  /mpm-oauth setup <service> Set up OAuth authentication for a service
  /mpm-oauth status <service> Show token status for a service
  /mpm-oauth revoke <service> Revoke OAuth tokens for a service
  /mpm-oauth refresh <service> Refresh OAuth tokens for a service
  /mpm-oauth help            Show this help message

Examples:
  /mpm-oauth list
  /mpm-oauth setup google-drive
  /mpm-oauth status google-drive
"""
        self._print(help_text)

    async def _cmd_oauth_list(self) -> None:
        """List OAuth-capable services from MCP registry."""
        try:
            from claude_mpm.services.mcp_service_registry import MCPServiceRegistry

            registry = MCPServiceRegistry()
            services = registry.list_oauth_services()

            if not services:
                self._print("No OAuth-capable services found.")
                return

            self._print("OAuth-capable services:")
            for service in services:
                self._print(f"  - {service}")
        except ImportError:
            self._print("MCP Service Registry not available.")
        except Exception as e:
            self._print(f"Error listing services: {e}")

    def _load_oauth_credentials_from_env_files(self) -> tuple[str | None, str | None]:
        """Load OAuth credentials from .env files.

        Checks .env.local first (user overrides), then .env.
        Returns tuple of (client_id, client_secret), either may be None.
        """
        client_id = None
        client_secret = None

        # Priority order: .env.local first (user overrides), then .env
        env_files = [".env.local", ".env"]

        for env_file in env_files:
            env_path = Path.cwd() / env_file
            if env_path.exists():
                try:
                    with open(env_path) as f:
                        for line in f:
                            line = line.strip()
                            # Skip empty lines and comments
                            if not line or line.startswith("#"):
                                continue
                            if "=" in line:
                                key, _, value = line.partition("=")
                                key = key.strip()
                                value = value.strip().strip('"').strip("'")

                                if key == "GOOGLE_OAUTH_CLIENT_ID" and not client_id:
                                    client_id = value
                                elif (
                                    key == "GOOGLE_OAUTH_CLIENT_SECRET"
                                    and not client_secret
                                ):
                                    client_secret = value

                        # If we found both, no need to check more files
                        if client_id and client_secret:
                            break
                except Exception:  # nosec B110 - intentionally ignore .env file read errors
                    # Silently ignore read errors
                    pass

        return client_id, client_secret

    async def _cmd_oauth_setup(self, service_name: str) -> None:
        """Set up OAuth for a service.

        Args:
            service_name: Name of the service to authenticate.
        """
        # Priority: 1) .env files, 2) environment variables, 3) interactive prompt
        # Check .env files first
        client_id, client_secret = self._load_oauth_credentials_from_env_files()

        # Fall back to environment variables if not found in .env files
        if not client_id:
            client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
        if not client_secret:
            client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")

        # If credentials missing, prompt for them interactively
        if not client_id or not client_secret:
            self._console.print(
                "\n[yellow]Google OAuth credentials not found.[/yellow]"
            )
            self._console.print(
                "Checked: .env.local, .env, and environment variables.\n"
            )
            self._console.print(
                "Get credentials from: https://console.cloud.google.com/apis/credentials\n"
            )
            self._console.print(
                "[dim]Tip: Add to .env.local for automatic loading:[/dim]"
            )
            self._console.print('[dim]  GOOGLE_OAUTH_CLIENT_ID="your-client-id"[/dim]')
            self._console.print(
                '[dim]  GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret"[/dim]\n'  # pragma: allowlist secret
            )

            try:
                client_id = pt_prompt("Enter GOOGLE_OAUTH_CLIENT_ID: ")
                if not client_id.strip():
                    self._print("Error: Client ID is required")
                    return

                client_secret = pt_prompt(
                    "Enter GOOGLE_OAUTH_CLIENT_SECRET: ", is_password=True
                )
                if not client_secret.strip():
                    self._print("Error: Client Secret is required")
                    return

                # Set in environment for this session
                os.environ["GOOGLE_OAUTH_CLIENT_ID"] = client_id.strip()
                os.environ["GOOGLE_OAUTH_CLIENT_SECRET"] = client_secret.strip()
                self._console.print(
                    "\n[green]Credentials set for this session.[/green]"
                )

                # Ask if user wants to save credentials
                save_response = pt_prompt(
                    "\nSave credentials to shell profile? (y/n): "
                )
                if save_response.strip().lower() in ("y", "yes"):
                    self._console.print("\nAdd these lines to your shell profile:")
                    self._console.print(
                        f'  export GOOGLE_OAUTH_CLIENT_ID="{client_id.strip()}"'
                    )
                    self._console.print(
                        f'  export GOOGLE_OAUTH_CLIENT_SECRET="{client_secret.strip()}"'
                    )
                    self._console.print("")

            except (EOFError, KeyboardInterrupt):
                self._print("\nCredential entry cancelled.")
                return

        try:
            from claude_mpm.auth import OAuthManager

            manager = OAuthManager()

            self._print(f"Setting up OAuth for '{service_name}'...")
            self._print("Opening browser for authentication...")
            self._print("Callback server listening on http://localhost:8085/callback")

            result = await manager.authenticate(service_name)

            if result.success:
                self._print(f"OAuth setup complete for '{service_name}'")
                self._print(f"  Token expires: {result.expires_at}")
            else:
                self._print(f"OAuth setup failed: {result.error}")
        except ImportError:
            self._print("OAuth module not available.")
        except Exception as e:
            self._print(f"Error during OAuth setup: {e}")

    async def _cmd_oauth_status(self, service_name: str) -> None:
        """Show OAuth token status for a service.

        Args:
            service_name: Name of the service to check.
        """
        try:
            from claude_mpm.auth import OAuthManager

            manager = OAuthManager()
            status = await manager.get_status(service_name)

            if status is None:
                self._print(f"No OAuth tokens found for '{service_name}'")
                return

            self._print_token_status(service_name, status, stored=True)
        except ImportError:
            self._print("OAuth module not available.")
        except Exception as e:
            self._print(f"Error checking status: {e}")

    async def _cmd_oauth_revoke(self, service_name: str) -> None:
        """Revoke OAuth tokens for a service.

        Args:
            service_name: Name of the service to revoke.
        """
        try:
            from claude_mpm.auth import OAuthManager

            manager = OAuthManager()

            self._print(f"Revoking OAuth tokens for '{service_name}'...")
            result = await manager.revoke(service_name)

            if result.success:
                self._print(f"OAuth tokens revoked for '{service_name}'")
            else:
                self._print(f"Failed to revoke: {result.error}")
        except ImportError:
            self._print("OAuth module not available.")
        except Exception as e:
            self._print(f"Error revoking tokens: {e}")

    async def _cmd_oauth_refresh(self, service_name: str) -> None:
        """Refresh OAuth tokens for a service.

        Args:
            service_name: Name of the service to refresh.
        """
        try:
            from claude_mpm.auth import OAuthManager

            manager = OAuthManager()

            self._print(f"Refreshing OAuth tokens for '{service_name}'...")
            result = await manager.refresh(service_name)

            if result.success:
                self._print(f"OAuth tokens refreshed for '{service_name}'")
                self._print(f"  New expiry: {result.expires_at}")
            else:
                self._print(f"Failed to refresh: {result.error}")
        except ImportError:
            self._print("OAuth module not available.")
        except Exception as e:
            self._print(f"Error refreshing tokens: {e}")

    async def _cmd_cleanup(self, args: list[str]) -> None:
        """Clean up orphan tmux panes not in tracked instances.

        Identifies all tmux panes in the commander session and removes those
        that are not associated with any tracked instance.

        Usage:
            /cleanup              - Show orphan panes without killing
            /cleanup --force      - Kill orphan panes
        """
        force_kill = "--force" in args

        # Get all panes in the commander session
        try:
            all_panes = self.instances.orchestrator.list_panes()
        except Exception as e:
            self._print(f"Error listing panes: {e}")
            return

        # Get tracked instance pane targets
        tracked_instances = self.instances.list_instances()
        tracked_panes = {inst.pane_target for inst in tracked_instances}

        # Find orphan panes (panes not in any tracked instance)
        orphan_panes = []
        for pane in all_panes:
            pane_id = pane["id"]
            session_pane_target = (
                f"{self.instances.orchestrator.session_name}:{pane_id}"
            )

            # Skip if this pane is tracked
            if session_pane_target in tracked_panes:
                continue

            orphan_panes.append((session_pane_target, pane["path"]))

        if not orphan_panes:
            self._print("No orphan panes found.")
            return

        # Display orphan panes
        self._print(f"Found {len(orphan_panes)} orphan pane(s):")
        for target, path in orphan_panes:
            self._print(f"  - {target} ({path})")

        if force_kill:
            # Kill orphan panes
            killed_count = 0
            for target, path in orphan_panes:
                try:
                    self.instances.orchestrator.kill_pane(target)
                    killed_count += 1
                    self._print(f"  Killed: {target}")
                except Exception as e:
                    self._print(f"  Error killing {target}: {e}")

            self._print(f"\nCleaned up {killed_count} orphan pane(s).")
        else:
            self._print("\nUse '/cleanup --force' to remove these panes.")

    def _print_token_status(
        self, name: str, status: dict, stored: bool = False
    ) -> None:
        """Print token status information.

        Args:
            name: Service name.
            status: Status dict with token info.
            stored: Whether tokens are stored.
        """
        self._print(f"OAuth Status for '{name}':")
        self._print(f"  Stored: {'Yes' if stored else 'No'}")

        if status.get("valid"):
            self._print("  Status: Valid")
        else:
            self._print("  Status: Invalid/Expired")

        if status.get("expires_at"):
            self._print(f"  Expires: {status['expires_at']}")

        if status.get("scopes"):
            self._print(f"  Scopes: {', '.join(status['scopes'])}")

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
        """Send message to specific instance without connecting (non-blocking).

        Enqueues the request and returns immediately. Response will appear
        above the prompt when it arrives.

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
                if inst:
                    # Spawn background startup task (non-blocking)
                    self._spawn_startup_task(target, auto_connect=False, timeout=30)
                    self._print(
                        f"Starting '{target}'... message will be sent when ready"
                    )
            except Exception:
                inst = None

            if not inst:
                self._print(
                    f"Instance '{target}' not found. Use /list to see instances."
                )
                return

        # Create and enqueue request (non-blocking)
        request = PendingRequest(
            id=str(uuid.uuid4())[:8],
            target=target,
            message=message,
        )
        self._pending_requests[request.id] = request
        await self._request_queue.put(request)

        # Return immediately - response will be handled by _process_responses

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
        """Send natural language to connected instance (non-blocking).

        Enqueues the request and returns immediately. Response will appear
        above the prompt when it arrives.

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

        # Create and enqueue request (non-blocking)
        request = PendingRequest(
            id=str(uuid.uuid4())[:8],
            target=name,
            message=message,
        )
        self._pending_requests[request.id] = request
        await self._request_queue.put(request)
        self.session.add_user_message(message)

        # Return immediately - response will be handled by _process_responses

    async def _process_responses(self) -> None:
        """Background task that processes queued requests and waits for responses."""
        while self._running:
            try:
                # Get next request from queue (with timeout to allow checking _running)
                try:
                    request = await asyncio.wait_for(
                        self._request_queue.get(), timeout=0.5
                    )
                except asyncio.TimeoutError:
                    continue

                # Update status and send to instance
                request.status = RequestStatus.SENDING
                self._render_pending_status()

                inst = self.instances.get_instance(request.target)
                if not inst:
                    request.status = RequestStatus.ERROR
                    request.error = f"Instance '{request.target}' no longer exists"
                    print(f"\n[{request.target}] {request.error}")
                    continue

                # Send to instance
                await self.instances.send_to_instance(request.target, request.message)
                request.status = RequestStatus.WAITING
                self._render_pending_status()

                # Give tmux time to process the message and produce output
                await asyncio.sleep(0.2)

                # Wait for response
                if self.relay:
                    try:
                        output = await self.relay.get_latest_output(
                            request.target, inst.pane_target, context=request.message
                        )
                        request.status = RequestStatus.COMPLETED
                        request.response = output

                        # Display response above prompt
                        self._display_response(request.target, output)
                        self.session.add_assistant_message(output)
                    except Exception as e:
                        request.status = RequestStatus.ERROR
                        request.error = str(e)
                        print(f"\n[{request.target}] Error: {e}")
                else:
                    # No relay available, simple send without response capture
                    request.status = RequestStatus.COMPLETED
                    print(f"\n[{request.target}] Message sent (no relay for response)")

                # Remove from pending after a short delay
                await asyncio.sleep(0.5)
                self._pending_requests.pop(request.id, None)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"\nResponse processor error: {e}")

    def _render_pending_status(self) -> None:
        """Render pending request status above the prompt."""
        pending = [
            r
            for r in self._pending_requests.values()
            if r.status not in (RequestStatus.COMPLETED, RequestStatus.ERROR)
        ]
        if not pending:
            return

        # Build status line
        status_parts = []
        for req in pending:
            elapsed = req.elapsed_seconds()
            status_indicator = {
                RequestStatus.QUEUED: "...",
                RequestStatus.SENDING: ">>>",
                RequestStatus.WAITING: "...",
                RequestStatus.STARTING: "...",
            }.get(req.status, "?")
            status_parts.append(
                f"{status_indicator} [{req.target}] {req.display_message(30)} ({elapsed}s)"
            )

        # Print above prompt (patch_stdout handles cursor positioning)
        for part in status_parts:
            print(part)

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
            Prompt string for input, showing instance name when connected.
        """
        connected = self.session.context.connected_instance
        if connected:
            return f"Commander ({connected})> "
        return "Commander> "

    def _print(self, msg: str) -> None:
        """Print message to console.

        Args:
            msg: Message to print.
        """
        print(msg)

    def _spawn_startup_task(
        self, name: str, auto_connect: bool = True, timeout: int = 30
    ) -> None:
        """Spawn a background task to wait for instance ready.

        This returns immediately - the wait happens in the background.
        Prints status when starting and when complete.

        Args:
            name: Instance name to wait for
            auto_connect: Whether to auto-connect when ready
            timeout: Maximum seconds to wait
        """
        # Print starting message (once)
        print(f"Waiting for '{name}' to be ready...")

        # Spawn background task
        task = asyncio.create_task(
            self._wait_for_ready_background(name, auto_connect, timeout)
        )
        self._startup_tasks[name] = task

    async def _wait_for_ready_background(
        self, name: str, auto_connect: bool, timeout: int
    ) -> None:
        """Background task that waits for instance ready.

        Updates bottom toolbar with spinner animation, then prints result when done.

        Args:
            name: Instance name to wait for
            auto_connect: Whether to auto-connect when ready
            timeout: Maximum seconds to wait
        """
        elapsed = 0.0
        interval = 0.1  # Update spinner every 100ms
        spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        frame_idx = 0

        try:
            while elapsed < timeout:
                inst = self.instances.get_instance(name)
                if inst and inst.ready:
                    # Clear toolbar and print success
                    self._toolbar_status = ""
                    if self.prompt_session:
                        self.prompt_session.app.invalidate()
                    print(f"'{name}' ready ({int(elapsed)}s)")

                    if auto_connect:
                        self.session.connect_to(name)
                        print(f"  Connected to '{name}'")

                    # Cleanup
                    self._startup_tasks.pop(name, None)
                    return

                # Update toolbar with spinner frame
                frame = spinner_frames[frame_idx % len(spinner_frames)]
                self._toolbar_status = (
                    f"{frame} Waiting for '{name}'... ({int(elapsed)}s)"
                )
                if self.prompt_session:
                    self.prompt_session.app.invalidate()
                frame_idx += 1

                await asyncio.sleep(interval)
                elapsed += interval

            # Timeout - clear toolbar and show warning
            self._toolbar_status = ""
            if self.prompt_session:
                self.prompt_session.app.invalidate()
            print(f"'{name}' startup timeout ({timeout}s) - may still work")

            # Still auto-connect on timeout (instance may become ready later)
            if auto_connect:
                self.session.connect_to(name)
                print(f"  Connected to '{name}' (may not be fully ready)")

            # Cleanup
            self._startup_tasks.pop(name, None)

        except asyncio.CancelledError:
            self._toolbar_status = ""
            self._startup_tasks.pop(name, None)
        except Exception as e:
            self._toolbar_status = ""
            print(f"'{name}' startup error: {e}")
            self._startup_tasks.pop(name, None)

    async def _wait_for_ready_with_spinner(self, name: str, timeout: int = 30) -> bool:
        """Wait for instance to be ready with animated spinner (BLOCKING).

        NOTE: This method blocks. For non-blocking, use _spawn_startup_task().

        Shows an animated waiting indicator that updates in place.

        Args:
            name: Instance name to wait for
            timeout: Maximum seconds to wait

        Returns:
            True if instance became ready, False on timeout
        """
        spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        frame_idx = 0
        elapsed = 0.0
        interval = 0.1  # Update spinner every 100ms

        while elapsed < timeout:
            inst = self.instances.get_instance(name)
            if inst and inst.ready:
                # Clear spinner line and show success
                sys.stdout.write(f"\r\033[K'{name}' ready\n")
                sys.stdout.flush()
                return True

            # Show spinner with elapsed time
            frame = spinner_frames[frame_idx % len(spinner_frames)]
            sys.stdout.write(
                f"\r{frame} Waiting for '{name}' to be ready... ({int(elapsed)}s)"
            )
            sys.stdout.flush()

            await asyncio.sleep(interval)
            elapsed += interval
            frame_idx += 1

        # Timeout - clear spinner and show warning
        sys.stdout.write(f"\r\033[K'{name}' startup timeout (may still work)\n")
        sys.stdout.flush()
        return False

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
