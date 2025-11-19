"""Centralized constants for Claude MPM.

This module consolidates all magic numbers and configuration constants
that were previously scattered throughout the codebase.
"""

from pathlib import Path
from typing import Tuple


class SystemLimits:
    """System-wide size and count limits."""

    # Instruction and content limits
    MAX_INSTRUCTION_LENGTH = 8000  # Maximum characters in agent instructions
    MAX_AGENT_CONFIG_SIZE = 1024 * 1024  # 1MB limit for agent config files
    MAX_FILE_SIZE = 1024 * 1024  # 1MB default file read limit

    # Memory and entry limits
    MAX_MEMORY_ENTRIES = 1000  # Maximum memory entries per agent
    MAX_EVENT_HISTORY = 1000  # Maximum events to keep in history
    MAX_EVENTS_BUFFER = 1000  # Maximum events to buffer in SocketIO
    MAX_QUEUE_SIZE = 10000  # Maximum queue size for async operations

    # File and directory limits
    MAX_FILES_TO_VALIDATE = 100  # Maximum files to validate in batch (DoS prevention)
    MAX_LOG_FILES = 50  # Maximum log files to retain

    # Content generation limits
    MIN_CONTENT_LENGTH = 1000  # Minimum content length for validation
    MAX_TOKEN_LIMIT = 8192  # Default max tokens for agent responses

    # Chunk sizes
    CHUNK_SIZE = 1024  # Default chunk size for file operations

    # Line limits
    MAX_LINES = 2000  # Default maximum lines to read from files


class NetworkConfig:
    """Network-related configuration constants."""

    # Port ranges
    SOCKETIO_PORT_RANGE: Tuple[int, int] = (8765, 8785)
    DEFAULT_SOCKETIO_PORT = 8765
    DEFAULT_DASHBOARD_PORT = 8765

    # Connection timeouts (seconds)
    CONNECTION_TIMEOUT = 5.0
    SOCKET_WAIT_TIMEOUT = 1.0
    RECONNECTION_DELAY = 0.5
    RECONNECTION_DELAY_MAX = 5.0
    RECONNECTION_ATTEMPTS = 3

    # Ping/Pong settings
    PING_INTERVAL = 30  # seconds
    PING_TIMEOUT = 120  # seconds
    PING_INTERVAL_FAST = 10  # seconds (debug mode)
    PING_TIMEOUT_FAST = 30  # seconds (debug mode)
    PING_INTERVAL_STANDARD = 25  # seconds (standard mode)
    PING_TIMEOUT_STANDARD = 90  # seconds (standard mode)

    # HTTP status codes
    HTTP_OK = 200
    HTTP_INTERNAL_ERROR = 500

    # Batch processing
    BATCH_INTERVAL = 0.1  # seconds between batch processing


class TimeoutConfig:
    """Timeout configuration constants."""

    # Query and operation timeouts (seconds)
    QUERY_TIMEOUT = 600  # 10 minutes for long-running queries
    DEFAULT_TIMEOUT = 600  # Default timeout for operations
    DEPLOYMENT_TIMEOUT = 120  # Timeout for deployment operations
    SUBPROCESS_TIMEOUT = 120000  # 2 minutes in milliseconds
    SUBPROCESS_WAIT = 2  # Seconds to wait for subprocess cleanup

    # Quick timeouts (seconds)
    QUICK_TIMEOUT = 2.0  # Quick operations timeout
    HEALTH_CHECK_TIMEOUT = 1.0  # Health check timeout
    FILE_OPERATION_TIMEOUT = 5.0  # File operation timeout

    # Session and thread timeouts
    SESSION_TIMEOUT = 30  # Session initialization timeout
    THREAD_JOIN_TIMEOUT = 5  # Thread join timeout
    WORKER_TIMEOUT = 60  # Worker thread timeout

    # Async operation timeouts
    QUEUE_GET_TIMEOUT = 0.1  # Queue get operation timeout
    FLUSH_TIMEOUT = 5.0  # Flush operation timeout

    # Performance monitoring intervals
    CPU_SAMPLE_INTERVAL = 0.1  # CPU sampling interval
    HEARTBEAT_INTERVAL = 100  # Heartbeat log interval (iterations)

    # Resource tier timeouts (min, max)
    INTENSIVE_TIMEOUT_RANGE = (600, 3600)  # 10 min to 1 hour
    STANDARD_TIMEOUT_RANGE = (300, 1200)  # 5 min to 20 min
    LIGHTWEIGHT_TIMEOUT_RANGE = (30, 600)  # 30 sec to 10 min


class ResourceLimits:
    """Resource limitation constants."""

    # Memory limits (MB) - (min, max) tuples
    INTENSIVE_MEMORY_RANGE = (4096, 8192)  # 4GB to 8GB
    STANDARD_MEMORY_RANGE = (2048, 4096)  # 2GB to 4GB
    LIGHTWEIGHT_MEMORY_RANGE = (512, 2048)  # 512MB to 2GB

    # CPU limits (%) - (min, max) tuples
    INTENSIVE_CPU_RANGE = (60, 100)  # 60% to 100%
    STANDARD_CPU_RANGE = (30, 60)  # 30% to 60%
    LIGHTWEIGHT_CPU_RANGE = (10, 30)  # 10% to 30%

    # Process limits
    MAX_PARALLEL_AGENTS = 10  # Maximum parallel subagents
    MAX_WORKERS = 4  # Maximum worker threads

    # Memory conversion
    BYTES_TO_MB = 1024 * 1024  # Conversion factor


class RetryConfig:
    """Retry configuration constants."""

    # Retry attempts
    MAX_RETRIES = 3
    MAX_CONNECTION_RETRIES = 3
    MAX_INSTALL_RETRIES = 3

    # Retry delays (seconds)
    INITIAL_RETRY_DELAY = 0.1  # 100ms initial delay
    MAX_RETRY_DELAY = 5.0  # Maximum retry delay
    EXPONENTIAL_BASE = 2  # Base for exponential backoff

    # Circuit breaker
    FAILURE_THRESHOLD = 5  # Failures before circuit opens
    SUCCESS_THRESHOLD = 3  # Successes to close circuit
    CIRCUIT_TIMEOUT = 300  # 5 minutes circuit breaker timeout
    FAILURE_WINDOW = 300  # 5 minutes failure tracking window
    MIN_RECOVERY_INTERVAL = 60  # 1 minute minimum between recoveries
    CRITICAL_THRESHOLD = 1  # Critical failures threshold


class ComplexityMetrics:
    """Code complexity and quality metrics."""

    # Complexity thresholds
    HIGH_COMPLEXITY = 10  # High cyclomatic complexity
    CRITICAL_COMPLEXITY = 20  # Critical cyclomatic complexity

    # Size thresholds
    LONG_FUNCTION_LINES = 50  # Function is getting long
    CRITICAL_FUNCTION_LINES = 100  # Function too long
    LARGE_CLASS_LINES = 300  # Class needs refactoring
    CRITICAL_CLASS_LINES = 500  # Class too large
    GOD_CLASS_LINES = 500  # God object threshold

    # Coupling thresholds
    HIGH_IMPORT_COUNT = 20  # High coupling
    CRITICAL_IMPORT_COUNT = 40  # Critical coupling/fan-out

    # Duplication thresholds
    DUPLICATION_WARNING = 5  # 5% duplication needs attention
    DUPLICATION_CRITICAL = 10  # 10% duplication is critical

    # Maintainability grades
    GRADE_A_THRESHOLD = 80
    GRADE_B_THRESHOLD = 60
    GRADE_C_THRESHOLD = 40
    GRADE_D_THRESHOLD = 20


class ErrorMessages:
    """Standardized error message templates."""

    # Validation errors
    INSTRUCTION_TOO_LONG = (
        "Instructions exceed {limit} character limit: {actual} characters"
    )
    CONFIG_TOO_LARGE = "Configuration file exceeds {limit} size limit: {actual} bytes"
    FILE_TOO_LARGE = "File exceeds maximum size of {limit} bytes"
    TOO_MANY_FILES = "Too many files to validate: {count} exceeds limit of {limit}"

    # Connection errors
    CONNECTION_FAILED = "Failed to connect to {service} on port {port}"
    CONNECTION_TIMEOUT = "Connection to {service} timed out after {timeout} seconds"
    PORT_IN_USE = "Port {port} is already in use"
    PORT_NOT_IN_RANGE = "Port {port} is outside allowed range {range}"

    # Resource errors
    MEMORY_EXCEEDED = "Memory usage {usage}MB exceeds limit of {limit}MB"
    CPU_EXCEEDED = "CPU usage {usage}% exceeds limit of {limit}%"
    QUEUE_FULL = "Queue is full: {size} items exceeds limit of {limit}"

    # Timeout errors
    OPERATION_TIMEOUT = "Operation timed out after {timeout} seconds"
    SUBPROCESS_TIMEOUT = "Subprocess timed out after {timeout} milliseconds"

    # Retry errors
    MAX_RETRIES_EXCEEDED = "Maximum retries ({max_retries}) exceeded for {operation}"
    CIRCUIT_OPEN = "Circuit breaker is open for {service}"


class Defaults:
    """Default configuration values."""

    # Agent defaults
    DEFAULT_AUTHOR = "claude-mpm"
    DEFAULT_VERSION = "1.0.0"
    DEFAULT_PRIORITY = "medium"
    DEFAULT_TEMPERATURE = 0.5

    # Logging defaults
    DEFAULT_LOG_LEVEL = "OFF"
    DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Session defaults
    DEFAULT_SESSION_PREFIX = "session"
    DEFAULT_WORKSPACE = ".claude-mpm"

    # Dashboard defaults
    DEFAULT_DASHBOARD_HOST = "localhost"
    DEFAULT_DASHBOARD_TITLE = "Claude MPM Dashboard"

    # Time formats
    TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
    LOG_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


class PerformanceConfig:
    """Performance optimization settings."""

    # Scoring weights for server selection
    VERSION_SCORE_MAJOR = 1000
    VERSION_SCORE_MINOR = 100
    VERSION_SCORE_PATCH = 1

    # Time conversion
    SECONDS_TO_MS = 1000
    MS_TO_SECONDS = 0.001

    # Logging frequencies
    LOG_EVERY_N_ITERATIONS = 100  # Log every N iterations
    LOG_EVERY_N_SECONDS = 10  # Log every N seconds

    # Batch sizes
    DEFAULT_BATCH_SIZE = 100
    MAX_BATCH_SIZE = 1000

    # Cache settings
    CACHE_CLEANUP_INTERVAL = 60  # seconds
    CACHE_TTL = 3600  # 1 hour default TTL

    # Memory thresholds
    LOW_MEMORY_THRESHOLD = 100  # MB
    CRITICAL_MEMORY_THRESHOLD = 50  # MB


class ValidationRules:
    """Validation rules and thresholds."""

    # Name validation
    MIN_NAME_LENGTH = 3
    MAX_NAME_LENGTH = 50

    # Version validation
    MIN_VERSION_PARTS = 3  # major.minor.patch

    # Description validation
    MIN_DESCRIPTION_LENGTH = 10
    MAX_DESCRIPTION_LENGTH = 500

    # Tag validation
    MAX_TAGS = 10
    MAX_TAG_LENGTH = 30

    # Tool validation
    MAX_TOOLS = 20

    # Priority levels
    VALID_PRIORITIES = ["low", "medium", "high", "critical"]

    # Resource tiers
    VALID_RESOURCE_TIERS = ["intensive", "standard", "lightweight"]


MAX_INSTRUCTION_LENGTH = SystemLimits.MAX_INSTRUCTION_LENGTH
MAX_AGENT_CONFIG_SIZE = SystemLimits.MAX_AGENT_CONFIG_SIZE
MAX_FILE_SIZE = SystemLimits.MAX_FILE_SIZE
SOCKETIO_PORT_RANGE = NetworkConfig.SOCKETIO_PORT_RANGE
QUERY_TIMEOUT = TimeoutConfig.QUERY_TIMEOUT
MAX_RETRIES = RetryConfig.MAX_RETRIES
DEFAULT_TIMEOUT = TimeoutConfig.DEFAULT_TIMEOUT


# ==============================================================================
# NEW ORGANIZED CONSTANTS (Phase 1 Refactoring)
# ==============================================================================


class NetworkPorts:
    """Network port configuration."""

    # Use existing values from NetworkConfig
    DEFAULT_SOCKETIO = NetworkConfig.DEFAULT_SOCKETIO_PORT
    DEFAULT_DASHBOARD = NetworkConfig.DEFAULT_DASHBOARD_PORT
    PORT_RANGE_START = NetworkConfig.SOCKETIO_PORT_RANGE[0]
    PORT_RANGE_END = NetworkConfig.SOCKETIO_PORT_RANGE[1]

    @classmethod
    def get_port_range(cls) -> range:
        """Get the valid port range."""
        return range(cls.PORT_RANGE_START, cls.PORT_RANGE_END + 1)


class ProjectPaths:
    """Project-specific paths and directories."""

    # Claude directories
    CLAUDE_DIR = ".claude"
    CLAUDE_AGENTS_DIR = ".claude/agents"
    CLAUDE_CONFIG_FILE = ".claude/config.yaml"

    # MPM directories
    MPM_DIR = ".claude-mpm"
    MPM_SESSION_DIR = ".claude-mpm/session"
    MPM_PROMPTS_DIR = ".claude-mpm/prompts"
    MPM_LOGS_DIR = ".claude-mpm/logs"
    MPM_CONFIG_DIR = ".claude-mpm/config"
    MPM_MEMORY_DIR = ".claude-mpm/memory"
    MPM_CACHE_DIR = ".claude-mpm/cache"

    # Config files
    MPM_CONFIG_FILE = "config.yaml"
    AGENT_CONFIG_FILE = "agent_config.yaml"
    EXPERIMENTAL_CONFIG = "experimental.json"
    SOCKETIO_CONFIG = "socketio_config.yaml"

    # Special files
    EXPERIMENTAL_ACCEPTED = ".experimental_accepted"
    VERSION_FILE = "VERSION"
    BUILD_NUMBER_FILE = "BUILD_NUMBER"

    @classmethod
    def get_mpm_home(cls) -> Path:
        """Get the MPM home directory."""
        return Path.home() / cls.MPM_DIR

    @classmethod
    def get_project_mpm_dir(cls) -> Path:
        """Get the project-specific MPM directory."""
        return Path.cwd() / cls.MPM_DIR

    @classmethod
    def get_claude_dir(cls) -> Path:
        """Get the Claude directory."""
        return Path.cwd() / cls.CLAUDE_DIR
