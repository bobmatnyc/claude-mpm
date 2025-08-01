"""Constants for Claude MPM."""

from enum import Enum


class CLIPrefix(str, Enum):
    """CLI command prefix constants."""
    MPM = "--mpm:"
    
    def __add__(self, other: str) -> str:
        """Allow prefix + command concatenation."""
        return self.value + other
    
    def wrap(self, flag: str) -> str:
        """Wrap a flag with the prefix."""
        if flag.startswith("--"):
            return f"--mpm:{flag[2:]}"
        elif flag.startswith("-"):
            return f"-mpm:{flag[1:]}"
        return self.value + flag


class CLICommands(str, Enum):
    """CLI command constants."""
    RUN = "run"
    TICKETS = "tickets"
    INFO = "info"
    AGENTS = "agents"
    UI = "ui"
    MEMORY = "memory"
    
    def with_prefix(self, prefix: CLIPrefix = CLIPrefix.MPM) -> str:
        """Get command with prefix."""
        return prefix + self.value
    
    @classmethod
    def get_mpm_commands(cls) -> list[str]:
        """Get list of MPM-specific commands with prefix."""
        return [cmd.with_prefix() for cmd in cls]
    
    @classmethod
    def is_mpm_command(cls, command: str) -> bool:
        """Check if a command is an MPM command."""
        # Check both with and without prefix
        if command.startswith(CLIPrefix.MPM.value):
            base_command = command[len(CLIPrefix.MPM.value):]
            return base_command in [cmd.value for cmd in cls]
        return command in [cmd.value for cmd in cls]


class AgentCommands(str, Enum):
    """Agent subcommand constants."""
    LIST = "list"
    DEPLOY = "deploy"
    FORCE_DEPLOY = "force-deploy"
    CLEAN = "clean"


class MemoryCommands(str, Enum):
    """Memory subcommand constants."""
    STATUS = "status"
    VIEW = "view"
    ADD = "add"
    CLEAN = "clean"


class CLIFlags(str, Enum):
    """CLI flag constants (without prefix)."""
    # Logging flags
    DEBUG = "debug"
    LOGGING = "logging"
    LOG_DIR = "log-dir"
    
    # Framework flags
    FRAMEWORK_PATH = "framework-path"
    AGENTS_DIR = "agents-dir"
    
    # Hook flags
    NO_HOOKS = "no-hooks"
    
    # Ticket flags
    NO_TICKETS = "no-tickets"
    
    # Input/output flags
    INPUT = "input"
    NON_INTERACTIVE = "non-interactive"
    
    # Orchestration flags
    SUBPROCESS = "subprocess"
    INTERACTIVE_SUBPROCESS = "interactive-subprocess"
    TODO_HIJACK = "todo-hijack"
    
    # Agent flags
    NO_NATIVE_AGENTS = "no-native-agents"
    
    def with_prefix(self, short: bool = False) -> str:
        """Get flag with MPM prefix."""
        prefix = CLIPrefix.MPM.value
        if short and self in [self.DEBUG, self.INPUT]:
            # Short flags
            return f"-mpm:{self.value[0]}"
        return f"{prefix}{self.value}"


class LogLevel(str, Enum):
    """Logging level constants."""
    OFF = "OFF"
    INFO = "INFO"
    DEBUG = "DEBUG"


class OrchestratorMode(str, Enum):
    """Orchestrator mode constants."""
    SYSTEM_PROMPT = "system_prompt"
    SUBPROCESS = "subprocess"
    INTERACTIVE_SUBPROCESS = "interactive_subprocess"


class EnvironmentVars(str, Enum):
    """Environment variable constants."""
    CLAUDE_CONFIG_DIR = "CLAUDE_CONFIG_DIR"
    CLAUDE_MAX_PARALLEL_SUBAGENTS = "CLAUDE_MAX_PARALLEL_SUBAGENTS"
    CLAUDE_TIMEOUT = "CLAUDE_TIMEOUT"
    CLAUDE_MPM_DEBUG = "CLAUDE_MPM_DEBUG"
    
    # Default values
    DEFAULT_MAX_AGENTS = "10"
    DEFAULT_TIMEOUT = "600000"  # 10 minutes in milliseconds


class Paths(str, Enum):
    """Path constants."""
    CLAUDE_AGENTS_DIR = ".claude/agents"
    CLAUDE_CONFIG_DIR = ".claude"
    MPM_LOG_DIR = ".claude-mpm/logs"
    MPM_SESSION_DIR = ".claude-mpm/session"
    MPM_PROMPTS_DIR = ".claude-mpm/prompts"
    
    
class AgentMetadata(str, Enum):
    """Agent metadata field constants."""
    NAME = "name"
    DESCRIPTION = "description"
    VERSION = "version"
    AUTHOR = "author"
    TAGS = "tags"
    TOOLS = "tools"
    PRIORITY = "priority"
    TIMEOUT = "timeout"
    MAX_TOKENS = "max_tokens"
    TEMPERATURE = "temperature"
    
    # Default values
    DEFAULT_AUTHOR = "claude-mpm"
    DEFAULT_VERSION = "1.0.0"
    DEFAULT_PRIORITY = "medium"
    DEFAULT_TIMEOUT = 600
    DEFAULT_MAX_TOKENS = 8192
    DEFAULT_TEMPERATURE = 0.5