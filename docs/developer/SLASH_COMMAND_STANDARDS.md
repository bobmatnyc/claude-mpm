# Slash Command Standards

**Version**: 1.0.0
**Last Updated**: 2025-10-08
**Status**: Active Standard

This document establishes comprehensive standards for developing, documenting, and maintaining slash commands in the Claude MPM project. Following these standards ensures consistency, maintainability, and excellent user experience across all commands.

## Table of Contents

- [Introduction](#introduction)
- [Command Structure Standards](#command-structure-standards)
- [Documentation Standards](#documentation-standards)
- [Parser Implementation Standards](#parser-implementation-standards)
- [Interaction Patterns](#interaction-patterns)
- [Error Handling Standards](#error-handling-standards)
- [Testing Standards](#testing-standards)
- [Quality Checklist](#quality-checklist)
- [Examples](#examples)
- [Reference Tables](#reference-tables)

---

## Introduction

### Purpose

Slash commands are the primary interface for Claude MPM users to interact with the system. Inconsistent command design leads to:
- **Poor User Experience**: Users must learn different patterns for each command
- **Higher Support Burden**: Inconsistent documentation and error messages
- **Increased Maintenance**: Each command implements patterns differently
- **Testing Gaps**: Lack of standardized testing approaches

This document provides clear, actionable standards to eliminate these issues.

### Why Consistency Matters

**User Benefits:**
- Predictable command behavior across all features
- Consistent documentation format for easier learning
- Uniform error messages and recovery patterns
- Reliable automation support

**Developer Benefits:**
- Clear patterns to follow when creating new commands
- Reduced code review time with established standards
- Easier maintenance with consistent structure
- Better test coverage through standard patterns

### When to Follow These Standards

**MUST follow these standards for:**
- All new slash commands
- Major refactoring of existing commands
- Commands exposed to end users
- Commands that will be automated

**SHOULD follow these standards for:**
- Internal development commands
- Experimental features
- Legacy command improvements

**MAY deviate with justification for:**
- Emergency hotfixes (with follow-up standardization)
- Special-purpose commands with unique requirements

---

## Command Structure Standards

### Decision Tree: Choosing Command Structure

```
┌─────────────────────────────────────┐
│ Does command perform multiple       │
│ distinct operations?                │
└─────────────┬───────────────────────┘
              │
        ┌─────┴─────┐
        │           │
       YES          NO
        │           │
        ▼           ▼
┌───────────────┐  ┌────────────────────┐
│ Use Pattern 1 │  │ Single operation?  │
│ (Subcommands) │  └─────────┬──────────┘
└───────────────┘            │
                        ┌────┴────┐
                        │         │
                       YES        NO
                        │         │
                        ▼         ▼
                ┌──────────────┐ ┌─────────────────┐
                │ Use Pattern 2│ │ Use Pattern 3   │
                │ (Flags Only) │ │ (PM Delegation) │
                └──────────────┘ └─────────────────┘
```

### Pattern 1: Complex Multi-Operation Commands (Subcommands)

**When to Use:**
- Command performs 3+ distinct operations
- Operations have different argument requirements
- Clear conceptual separation between operations
- Each operation could be standalone

**Structure:**
```
/command <subcommand> [options] [arguments]

Examples:
  /monitor start [--port 8765]
  /monitor stop [--force]
  /monitor status [--verbose]
```

**Characteristics:**
- **Subcommands**: Named operations (start, stop, status, etc.)
- **Shared flags**: Common options before subcommand
- **Subcommand-specific flags**: Operation-specific options after subcommand
- **Help hierarchy**: `--help` at both command and subcommand level

**Example Commands:**
- `/monitor`: start, stop, restart, status, logs, clear
- `/tickets`: create, list, view, update, search, close, delete
- `/agents`: list, deploy, validate, clean

**Implementation Pattern:**
```python
def command_handler(args):
    """Main command entry point."""
    subcommand_map = {
        'start': handle_start,
        'stop': handle_stop,
        'status': handle_status
    }

    handler = subcommand_map.get(args.subcommand)
    if handler:
        return handler(args)
    else:
        return CommandResult.error_result(f"Unknown subcommand: {args.subcommand}")
```

### Pattern 2: Single-Operation Commands (Flags Only)

**When to Use:**
- Command performs one primary operation
- Variations controlled by flags/options
- No conceptually distinct operations
- Simple, focused functionality

**Structure:**
```
/command [options] [arguments]

Examples:
  /analyze [--format json] [--verbose]
  /info [--agents] [--config]
  /cleanup [--dry-run] [--force]
```

**Characteristics:**
- **No subcommands**: Direct operation execution
- **Flag-based variation**: Behavior modified by flags
- **Single help screen**: All options in one view
- **Clear default behavior**: Works without flags

**Example Commands:**
- `/analyze`: Analyze current context
- `/info`: Display system information
- `/cleanup`: Clean up temporary files

**Implementation Pattern:**
```python
def command_handler(args):
    """Execute single operation with flag variations."""
    if args.dry_run:
        return preview_operation(args)

    result = perform_operation(args)

    if args.format == 'json':
        return format_json(result)
    else:
        return format_text(result)
```

### Pattern 3: Information Commands (PM Delegation)

**When to Use:**
- Command provides information only
- No system modifications
- PM agent can handle the request
- Simple query or display operation

**Structure:**
```
/command [simple-filter]

Examples:
  /status
  /version
  /help [topic]
```

**Characteristics:**
- **Minimal arguments**: Simple filters or none
- **PM delegation**: PM agent handles the request
- **Read-only**: No state modifications
- **Quick response**: Fast, lightweight operation

**Example Commands:**
- `/status`: Show current system status
- `/version`: Display version information
- `/help`: Show help information

**Implementation Pattern:**
```python
def command_handler(args):
    """Delegate to PM agent for information retrieval."""
    return delegate_to_pm(
        query=f"Show {args.topic or 'general'} information",
        context=gather_context(args)
    )
```

---

## Documentation Standards

### Required Sections for Every Command

All slash commands MUST include the following documentation sections:

#### 1. Purpose Statement
**Length**: 1-2 sentences
**Content**: Clear description of what the command does and when to use it

```markdown
## Purpose
Monitors the Claude MPM system in real-time, tracking agent activities, file operations, and system events.
Use this command to observe system behavior, debug issues, or verify operations.
```

#### 2. Usage Synopsis
**Format**: Standardized command syntax
**Content**: All command variations with brackets for optional elements

```markdown
## Usage
/monitor start [--port PORT] [--background]
/monitor stop [--force]
/monitor status [--verbose]
/monitor logs [--tail N] [--filter PATTERN]
/monitor clear
```

#### 3. Arguments and Options
**Format**: Table with columns: Argument | Type | Required | Default | Description
**Content**: All arguments, flags, and options

```markdown
## Arguments

| Argument      | Type    | Required | Default | Description                           |
|---------------|---------|----------|---------|---------------------------------------|
| subcommand    | string  | Yes      | -       | Operation: start, stop, status, etc.  |
| --port        | integer | No       | 8765    | WebSocket port for monitoring         |
| --background  | flag    | No       | false   | Run monitor in background             |
| --force       | flag    | No       | false   | Force stop without graceful shutdown  |
| --verbose     | flag    | No       | false   | Show detailed status information      |
```

#### 4. Examples
**Minimum**: 3 practical examples
**Content**: Common use cases with expected output

```markdown
## Examples

**Start monitoring on default port:**
```
/monitor start
```
Output: Monitor started on port 8765. Access dashboard at http://localhost:3000

**Check monitor status with details:**
```
/monitor status --verbose
```
Output: Monitor running (PID: 12345), Port: 8765, Uptime: 2h 15m, Connections: 3

**Stop monitor gracefully:**
```
/monitor stop
```
Output: Monitor stopped gracefully. All connections closed.
```

#### 5. Exit Codes
**Format**: Table mapping codes to meanings
**Content**: All possible exit codes and their significance

```markdown
## Exit Codes

| Code | Meaning                              | Example Scenario                    |
|------|--------------------------------------|-------------------------------------|
| 0    | Success                              | Monitor started successfully        |
| 1    | General error                        | Monitor already running             |
| 2    | Invalid arguments                    | Invalid port number                 |
| 3    | Service unavailable                  | Port already in use                 |
| 4    | Operation timeout                    | Monitor failed to start in 30s      |
```

#### 6. Related Commands
**Content**: Links to complementary commands
**Format**: Bullet list with brief explanations

```markdown
## Related Commands

- `/cleanup`: Clean up monitor logs and temporary files
- `/config`: Configure monitor settings and preferences
- `/info`: View monitor configuration and status
```

### Documentation Length Guidelines

| Command Type          | Target Lines | Maximum Lines | Rationale                           |
|-----------------------|--------------|---------------|-------------------------------------|
| Simple (Info)         | 50-75        | 100           | Quick reference, minimal complexity |
| Standard (Single-op)  | 100-150      | 200           | Clear examples, thorough coverage   |
| Complex (Multi-op)    | 150-250      | 300           | Each subcommand needs documentation |

### Example Formatting Standards

**Good Example:**
```markdown
**Start monitor with custom port:**
```bash
/monitor start --port 9000
```
Expected output:
```
Monitor started successfully
Port: 9000
Dashboard: http://localhost:3000
Status: Ready
```
```

**Poor Example:**
```markdown
Start the monitor:
/monitor start --port 9000
```

**Standards:**
- Use bold for example titles
- Use code blocks with bash syntax highlighting
- Include expected output when relevant
- Show both success and error cases

### Cross-Referencing Conventions

**Internal References:**
```markdown
See [Monitor Configuration](#monitor-configuration) for details.
For port settings, refer to the [Port Management](#port-management) section.
```

**External References:**
```markdown
See [MONITOR.md](../MONITOR.md) for architecture details.
Configuration format documented in [CONFIG.md](../reference/CONFIG.md).
```

**Command References:**
```markdown
Use `/cleanup --monitor` to clean monitor logs.
Related: `/monitor status`, `/info --monitor`
```

---

## Parser Implementation Standards

### Required Components

Every slash command parser MUST include:

#### 1. Argument Groups
**Purpose**: Organize related arguments for better help display
**Implementation**:

```python
def create_parser():
    parser = argparse.ArgumentParser(description="Monitor system")

    # Required arguments group
    required = parser.add_argument_group('required arguments')
    required.add_argument('subcommand', choices=['start', 'stop', 'status'])

    # Optional arguments group
    optional = parser.add_argument_group('optional arguments')
    optional.add_argument('--port', type=int, default=8765)
    optional.add_argument('--verbose', action='store_true')

    # Advanced options group
    advanced = parser.add_argument_group('advanced options')
    advanced.add_argument('--timeout', type=int, default=30)

    return parser
```

#### 2. Help Text
**Standards:**
- **Command description**: Clear, concise purpose statement
- **Argument help**: Explain each argument with examples
- **Usage examples**: Show common patterns
- **Exit code documentation**: List all exit codes

```python
parser = argparse.ArgumentParser(
    prog='/monitor',
    description='Monitor Claude MPM system in real-time',
    epilog='Examples:\n'
           '  /monitor start --port 9000\n'
           '  /monitor status --verbose\n'
           '  /monitor logs --tail 100',
    formatter_class=argparse.RawDescriptionHelpFormatter
)

parser.add_argument(
    '--port',
    type=int,
    default=8765,
    metavar='PORT',
    help='WebSocket port (default: 8765). Must be 1024-65535.'
)
```

#### 3. Type Hints
**Requirements:**
- All function signatures use type hints
- Return types specified
- Optional types properly marked

```python
from typing import Optional, List
from argparse import Namespace, ArgumentParser

def create_parser() -> ArgumentParser:
    """Create argument parser for monitor command."""
    pass

def handle_command(args: Namespace) -> CommandResult:
    """Execute monitor command."""
    pass

def validate_port(port: int) -> Optional[str]:
    """Validate port number.

    Returns:
        Error message if invalid, None if valid
    """
    if not 1024 <= port <= 65535:
        return f"Port must be between 1024 and 65535, got {port}"
    return None
```

### Standard Flag Names

Use these standard flag names for consistency:

| Flag Name        | Purpose                          | Type    | Example              |
|------------------|----------------------------------|---------|----------------------|
| `--verbose`      | Enable detailed output           | flag    | `--verbose`          |
| `-v`             | Short form of --verbose          | flag    | `-v`                 |
| `--debug`        | Enable debug mode                | flag    | `--debug`            |
| `--quiet`        | Suppress non-error output        | flag    | `--quiet`            |
| `-q`             | Short form of --quiet            | flag    | `-q`                 |
| `--dry-run`      | Preview without executing        | flag    | `--dry-run`          |
| `--force`        | Skip confirmations               | flag    | `--force`            |
| `-f`             | Short form of --force            | flag    | `-f`                 |
| `--format`       | Output format                    | choice  | `--format json`      |
| `--output`       | Output file path                 | path    | `--output file.txt`  |
| `-o`             | Short form of --output           | path    | `-o file.txt`        |
| `--config`       | Configuration file path          | path    | `--config cfg.yaml`  |
| `--help`         | Show help message                | flag    | `--help`             |
| `-h`             | Short form of --help             | flag    | `-h`                 |
| `--version`      | Show version information         | flag    | `--version`          |
| `--timeout`      | Operation timeout in seconds     | int     | `--timeout 30`       |
| `--limit`        | Limit results count              | int     | `--limit 50`         |
| `--filter`       | Filter pattern                   | string  | `--filter "error"`   |

### Error Handling Requirements

#### Input Validation
```python
def validate_args(args: Namespace) -> Optional[str]:
    """Validate command arguments.

    Returns error message if invalid, None if valid.
    """
    # Validate required fields
    if not args.subcommand:
        return "Subcommand required: start, stop, or status"

    # Validate value ranges
    if args.port and not 1024 <= args.port <= 65535:
        return f"Invalid port: {args.port}. Must be 1024-65535."

    # Validate file paths
    if args.config and not Path(args.config).exists():
        return f"Config file not found: {args.config}"

    # Validate mutually exclusive options
    if args.quiet and args.verbose:
        return "Cannot use --quiet and --verbose together"

    return None
```

#### Error Message Format
```python
def format_error(error_type: str, details: str, suggestion: str = None) -> str:
    """Format error message consistently.

    Args:
        error_type: Type of error (e.g., "Invalid Port")
        details: Specific error details
        suggestion: Optional recovery suggestion
    """
    message = f"Error: {error_type}\n{details}"
    if suggestion:
        message += f"\n\nSuggestion: {suggestion}"
    return message

# Usage
error = format_error(
    "Invalid Port",
    "Port 80 is reserved and cannot be used.",
    "Try a port between 8000-9000 (e.g., --port 8765)"
)
```

### Return Value Conventions

All command handlers MUST return `CommandResult`:

```python
from claude_mpm.cli.shared.command_base import CommandResult

def handle_command(args: Namespace) -> CommandResult:
    """Execute command and return standardized result."""

    # Success case
    if operation_successful:
        return CommandResult.success_result(
            message="Monitor started successfully",
            data={"port": args.port, "pid": process_id}
        )

    # Error case
    return CommandResult.error_result(
        message="Failed to start monitor: port already in use",
        exit_code=3,
        data={"port": args.port, "error": "EADDRINUSE"}
    )
```

---

## Interaction Patterns

### Interactive vs Non-Interactive Guidelines

#### When to Use Interactive Mode

**Use interactive prompts for:**
- Destructive operations (delete, overwrite)
- Operations requiring user decision
- Multi-step wizards
- First-time setup

**Example:**
```python
def delete_operation(args: Namespace) -> CommandResult:
    """Delete operation with confirmation."""
    if not args.force:
        confirm = input(f"Delete {args.target}? This cannot be undone. [y/N]: ")
        if confirm.lower() != 'y':
            return CommandResult.success_result("Operation cancelled")

    # Proceed with deletion
    perform_delete(args.target)
    return CommandResult.success_result(f"Deleted {args.target}")
```

#### When to Avoid Interactive Mode

**Avoid interactive prompts for:**
- Read-only operations
- Operations in pipelines
- Automated workflows
- Status/info commands

### Supporting Automation

All commands MUST support non-interactive execution:

```python
parser.add_argument(
    '--non-interactive',
    action='store_true',
    help='Run without interactive prompts (fail if input needed)'
)

parser.add_argument(
    '--yes', '-y',
    action='store_true',
    help='Automatically answer yes to all prompts'
)

def handle_confirmation(args: Namespace, prompt: str) -> bool:
    """Handle user confirmation with automation support."""
    if args.yes:
        return True

    if args.non_interactive:
        raise RuntimeError("Cannot proceed: interactive input required but --non-interactive specified")

    response = input(f"{prompt} [y/N]: ")
    return response.lower() == 'y'
```

### Progress Indication Standards

#### Short Operations (<5 seconds)
```python
print("Starting monitor...", flush=True)
result = start_monitor()
print("✓ Monitor started")
```

#### Medium Operations (5-30 seconds)
```python
from claude_mpm.utils.progress import ProgressBar

with ProgressBar(total=100, desc="Initializing") as progress:
    for step in initialization_steps:
        step.execute()
        progress.update(step.weight)
```

#### Long Operations (>30 seconds)
```python
from claude_mpm.utils.progress import Spinner

with Spinner("Processing large dataset...") as spinner:
    result = long_running_operation()
    spinner.success("Processing complete")
```

#### Background Operations
```python
def start_background_operation(args: Namespace) -> CommandResult:
    """Start operation in background with status file."""
    pid = start_daemon()

    status_file = Path("/tmp/operation.status")
    status_file.write_text(json.dumps({
        "pid": pid,
        "status": "running",
        "started_at": datetime.now().isoformat()
    }))

    return CommandResult.success_result(
        f"Operation started in background (PID: {pid})\n"
        f"Monitor progress: /monitor status"
    )
```

---

## Error Handling Standards

### Exit Code Conventions

| Code | Category              | Description                                    | When to Use                          |
|------|-----------------------|------------------------------------------------|--------------------------------------|
| 0    | Success               | Operation completed successfully               | All successful operations            |
| 1    | General Error         | Operation failed for general reason            | Unexpected errors, failures          |
| 2    | Usage Error           | Invalid arguments or command usage             | Argument validation failures         |
| 3    | Service Unavailable   | Required service or resource unavailable       | Port in use, service not running     |
| 4    | Operation Timeout     | Operation exceeded time limit                  | Timeouts, unresponsive services      |
| 5    | Permission Denied     | Insufficient permissions                       | File access denied, auth failures    |
| 6    | Not Found             | Requested resource not found                   | File not found, missing config       |
| 7    | Already Exists        | Resource already exists                        | Duplicate creation attempts          |
| 8    | Invalid State         | Operation not valid in current state           | Wrong state transitions              |

### Error Message Formatting

#### Standard Error Format
```python
def create_error_message(
    title: str,
    details: str,
    suggestion: Optional[str] = None,
    docs_link: Optional[str] = None
) -> str:
    """Create standardized error message.

    Args:
        title: Brief error title (e.g., "Invalid Configuration")
        details: Detailed error explanation
        suggestion: Optional recovery suggestion
        docs_link: Optional documentation reference

    Returns:
        Formatted error message
    """
    message = f"❌ {title}\n\n{details}"

    if suggestion:
        message += f"\n\n💡 Suggestion: {suggestion}"

    if docs_link:
        message += f"\n\n📚 Documentation: {docs_link}"

    return message
```

#### Example Error Messages

**Good Error Message:**
```
❌ Monitor Failed to Start

Port 8765 is already in use by another process.

💡 Suggestion: Try one of these options:
   1. Stop the existing monitor: /monitor stop
   2. Use a different port: /monitor start --port 9000
   3. Find the process using the port: lsof -i :8765

📚 Documentation: See docs/MONITOR.md#port-conflicts
```

**Poor Error Message:**
```
Error: Failed
```

### Recovery Suggestion Patterns

Provide actionable recovery suggestions:

```python
RECOVERY_PATTERNS = {
    "port_in_use": {
        "suggestion": "Try using a different port with --port <number>",
        "command": "/monitor start --port 9000"
    },
    "service_not_running": {
        "suggestion": "Start the service first",
        "command": "/monitor start"
    },
    "permission_denied": {
        "suggestion": "Run with appropriate permissions or check file ownership",
        "command": "sudo /command or chmod +x file"
    },
    "config_not_found": {
        "suggestion": "Create configuration file or specify path with --config",
        "command": "/config init"
    }
}

def suggest_recovery(error_type: str) -> str:
    """Get recovery suggestion for error type."""
    pattern = RECOVERY_PATTERNS.get(error_type)
    if pattern:
        return f"{pattern['suggestion']}\nExample: {pattern['command']}"
    return "Check logs for more details: /monitor logs"
```

### Logging Level Guidelines

| Level    | When to Use                              | Example                                      |
|----------|------------------------------------------|----------------------------------------------|
| DEBUG    | Development info, detailed flow          | "Entering function with args: {...}"        |
| INFO     | Normal operation events                  | "Monitor started on port 8765"              |
| WARNING  | Unexpected but handled situations        | "Config file not found, using defaults"     |
| ERROR    | Operation failures requiring attention   | "Failed to start monitor: port in use"      |
| CRITICAL | System failures requiring intervention   | "Database connection lost, shutting down"   |

```python
import logging

def monitor_command(args: Namespace) -> CommandResult:
    """Monitor command with appropriate logging."""
    logger = logging.getLogger(__name__)

    logger.debug(f"Monitor command called with args: {args}")

    logger.info("Starting monitor service")

    if not config_exists():
        logger.warning("No config file found, using default settings")

    try:
        start_monitor(args.port)
        logger.info(f"Monitor started successfully on port {args.port}")
    except PortInUseError as e:
        logger.error(f"Failed to start monitor: {e}")
        return CommandResult.error_result(str(e), exit_code=3)
    except Exception as e:
        logger.critical(f"Unexpected error starting monitor: {e}", exc_info=True)
        return CommandResult.error_result("Critical error", exit_code=1)

    return CommandResult.success_result("Monitor started")
```

---

## Testing Standards

### Unit Test Requirements

Every slash command MUST have unit tests covering:

1. **Successful execution** - Happy path
2. **Argument validation** - All validation rules
3. **Error conditions** - Expected failures
4. **Edge cases** - Boundary conditions

```python
import pytest
from argparse import Namespace
from unittest.mock import Mock, patch
from my_command import monitor_command

class TestMonitorCommand:
    """Unit tests for monitor command."""

    def test_successful_start(self):
        """Test successful monitor start."""
        args = Namespace(subcommand='start', port=8765, background=False)
        result = monitor_command(args)

        assert result.success is True
        assert result.exit_code == 0
        assert "started successfully" in result.message.lower()

    def test_invalid_port(self):
        """Test validation of invalid port."""
        args = Namespace(subcommand='start', port=80, background=False)
        result = monitor_command(args)

        assert result.success is False
        assert result.exit_code == 2
        assert "invalid port" in result.message.lower()

    def test_port_in_use(self):
        """Test error when port already in use."""
        args = Namespace(subcommand='start', port=8765, background=False)

        with patch('my_command.start_monitor') as mock_start:
            mock_start.side_effect = PortInUseError("Port 8765 in use")
            result = monitor_command(args)

        assert result.success is False
        assert result.exit_code == 3
        assert "port" in result.message.lower()

    def test_edge_case_min_port(self):
        """Test minimum valid port number."""
        args = Namespace(subcommand='start', port=1024, background=False)
        result = monitor_command(args)
        assert result.success is True

    def test_edge_case_max_port(self):
        """Test maximum valid port number."""
        args = Namespace(subcommand='start', port=65535, background=False)
        result = monitor_command(args)
        assert result.success is True
```

### Integration Test Requirements

Test commands in realistic scenarios:

```python
class TestMonitorIntegration:
    """Integration tests for monitor command."""

    def test_start_stop_lifecycle(self):
        """Test complete start-stop lifecycle."""
        # Start monitor
        start_args = Namespace(subcommand='start', port=8765)
        start_result = monitor_command(start_args)
        assert start_result.success is True

        # Verify running
        status_args = Namespace(subcommand='status', verbose=False)
        status_result = monitor_command(status_args)
        assert "running" in status_result.message.lower()

        # Stop monitor
        stop_args = Namespace(subcommand='stop', force=False)
        stop_result = monitor_command(stop_args)
        assert stop_result.success is True

        # Verify stopped
        status_result = monitor_command(status_args)
        assert "not running" in status_result.message.lower()

    def test_error_recovery(self):
        """Test recovery from error conditions."""
        # Try to stop when not running
        stop_args = Namespace(subcommand='stop', force=False)
        result = monitor_command(stop_args)
        assert result.exit_code == 8  # Invalid state

        # Start should work after
        start_args = Namespace(subcommand='start', port=8765)
        result = monitor_command(start_args)
        assert result.success is True
```

### Documentation Validation Tests

Ensure documentation stays current:

```python
def test_documentation_completeness():
    """Verify command documentation is complete."""
    doc_path = Path("docs/commands/monitor.md")
    assert doc_path.exists(), "Documentation file missing"

    content = doc_path.read_text()

    # Check required sections
    required_sections = [
        "## Purpose",
        "## Usage",
        "## Arguments",
        "## Examples",
        "## Exit Codes",
        "## Related Commands"
    ]
    for section in required_sections:
        assert section in content, f"Missing required section: {section}"

    # Check all subcommands documented
    subcommands = ['start', 'stop', 'status', 'logs', 'clear']
    for cmd in subcommands:
        assert cmd in content, f"Subcommand not documented: {cmd}"

def test_help_matches_documentation():
    """Verify --help output matches documentation."""
    parser = create_monitor_parser()
    help_text = parser.format_help()

    # Extract documented flags
    doc_path = Path("docs/commands/monitor.md")
    doc_content = doc_path.read_text()

    # Find all --flags in documentation
    import re
    doc_flags = set(re.findall(r'--[\w-]+', doc_content))
    help_flags = set(re.findall(r'--[\w-]+', help_text))

    # Ensure documentation covers all flags
    missing_flags = help_flags - doc_flags
    assert not missing_flags, f"Flags not documented: {missing_flags}"
```

### Example Test Template

```python
"""
Test module for /command slash command.

Coverage requirements:
- Happy path execution
- All argument validation rules
- Error conditions and recovery
- Edge cases and boundary values
- Integration scenarios
- Documentation completeness
"""

import pytest
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from claude_mpm.cli.commands.my_command import (
    my_command,
    create_parser,
    validate_args
)
from claude_mpm.cli.shared.command_base import CommandResult


class TestCommandValidation:
    """Test argument validation logic."""

    def test_valid_args(self):
        """Test validation passes with valid arguments."""
        args = Namespace(required_field="value", optional_field=None)
        error = validate_args(args)
        assert error is None

    def test_missing_required_field(self):
        """Test validation fails with missing required field."""
        args = Namespace(required_field=None)
        error = validate_args(args)
        assert error is not None
        assert "required" in error.lower()


class TestCommandExecution:
    """Test command execution logic."""

    def test_successful_execution(self):
        """Test command executes successfully."""
        args = Namespace(required_field="value")
        result = my_command(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.exit_code == 0

    def test_error_handling(self):
        """Test command handles errors appropriately."""
        args = Namespace(required_field="invalid")
        result = my_command(args)

        assert result.success is False
        assert result.exit_code > 0
        assert len(result.message) > 0


class TestCommandIntegration:
    """Test command in realistic scenarios."""

    def test_end_to_end_workflow(self):
        """Test complete command workflow."""
        # Setup
        setup_result = setup_test_environment()
        assert setup_result is True

        # Execute
        args = Namespace(operation="test")
        result = my_command(args)
        assert result.success is True

        # Verify
        assert verify_operation_completed()

        # Cleanup
        cleanup_test_environment()


class TestCommandDocumentation:
    """Test documentation completeness and accuracy."""

    def test_documentation_exists(self):
        """Verify command documentation file exists."""
        doc_path = Path("docs/commands/my_command.md")
        assert doc_path.exists()

    def test_required_sections_present(self):
        """Verify all required documentation sections exist."""
        doc_path = Path("docs/commands/my_command.md")
        content = doc_path.read_text()

        required_sections = [
            "## Purpose",
            "## Usage",
            "## Arguments",
            "## Examples",
            "## Exit Codes"
        ]
        for section in required_sections:
            assert section in content
```

---

## Quality Checklist

### Pre-Submission Checklist for New Commands

Use this checklist before submitting a new slash command:

#### Implementation
- [ ] Command follows appropriate pattern (subcommands/flags/delegation)
- [ ] All required arguments validated
- [ ] Type hints on all functions
- [ ] Proper error handling with exit codes
- [ ] Returns `CommandResult` consistently
- [ ] Logging at appropriate levels
- [ ] Non-interactive mode supported (--yes, --non-interactive)
- [ ] Progress indication for long operations

#### Documentation
- [ ] Documentation file created in `docs/commands/`
- [ ] All required sections present (Purpose, Usage, Arguments, Examples, Exit Codes)
- [ ] Minimum 3 practical examples
- [ ] All arguments documented in table format
- [ ] Exit codes documented with scenarios
- [ ] Related commands cross-referenced
- [ ] Length within guidelines for command type

#### Testing
- [ ] Unit tests for successful execution
- [ ] Unit tests for argument validation
- [ ] Unit tests for error conditions
- [ ] Unit tests for edge cases
- [ ] Integration tests for realistic scenarios
- [ ] Documentation validation tests
- [ ] Test coverage >80%

#### Parser
- [ ] Argument groups organized logically
- [ ] Help text clear and complete
- [ ] Standard flag names used
- [ ] Epilog includes examples
- [ ] Mutually exclusive arguments handled
- [ ] Default values documented

#### Code Quality
- [ ] Passes `make lint-fix`
- [ ] Passes `make quality`
- [ ] No duplicate code with other commands
- [ ] Follows project coding standards
- [ ] Type hints validated with mypy

### Review Checklist for Existing Commands

Use this checklist when reviewing or refactoring existing commands:

#### Consistency Review
- [ ] Command structure matches standards pattern
- [ ] Flag names follow standard conventions
- [ ] Error messages use standard format
- [ ] Exit codes match standard conventions
- [ ] Documentation structure matches template

#### Functionality Review
- [ ] All features properly tested
- [ ] Error handling comprehensive
- [ ] Edge cases covered
- [ ] Performance acceptable
- [ ] Resource cleanup proper

#### Documentation Review
- [ ] Documentation up-to-date with code
- [ ] Examples work as written
- [ ] No broken cross-references
- [ ] Exit codes documented accurately
- [ ] Help text matches documentation

#### User Experience Review
- [ ] Command intuitive to use
- [ ] Error messages helpful
- [ ] Progress indication clear
- [ ] Automation-friendly
- [ ] Consistent with other commands

### Validation Tools to Run

Run these tools before considering a command complete:

```bash
# Code quality and linting
make lint-fix          # Auto-fix formatting and imports
make quality           # Run all quality checks

# Testing
pytest tests/cli/commands/test_my_command.py -v --cov
pytest tests/cli/commands/ -k "my_command" --cov-report=html

# Documentation validation
python scripts/validate_command_docs.py my_command

# Integration testing
./scripts/run_e2e_tests.sh my_command

# Manual testing
/my-command --help
/my-command <various arguments>
```

---

## Examples

### Example 1: Well-Structured Multi-Operation Command

This example demonstrates a complete, well-structured command following all standards:

```python
"""
Monitor command implementation.

This module implements the /monitor slash command following Claude MPM
slash command standards. It provides system monitoring capabilities with
start, stop, status, logs, and clear operations.
"""

import logging
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Optional

from claude_mpm.cli.shared.command_base import BaseCommand, CommandResult
from claude_mpm.services.monitoring.monitor_service import MonitorService


class MonitorCommand(BaseCommand):
    """Monitor system command implementation.

    Provides real-time monitoring of Claude MPM system operations including
    agent activities, file operations, and system events.
    """

    def __init__(self):
        """Initialize monitor command."""
        super().__init__("monitor")
        self.logger = logging.getLogger(__name__)

    def validate_args(self, args: Namespace) -> Optional[str]:
        """Validate command arguments.

        Args:
            args: Parsed command arguments

        Returns:
            Error message if validation fails, None if valid
        """
        # Validate subcommand
        valid_subcommands = ['start', 'stop', 'status', 'logs', 'clear']
        if args.subcommand not in valid_subcommands:
            return f"Invalid subcommand: {args.subcommand}. Must be one of: {', '.join(valid_subcommands)}"

        # Validate port range
        if hasattr(args, 'port') and args.port:
            if not 1024 <= args.port <= 65535:
                return f"Invalid port: {args.port}. Must be between 1024 and 65535."

        # Validate tail count
        if hasattr(args, 'tail') and args.tail:
            if args.tail < 1:
                return "Tail count must be positive"

        return None

    def run(self, args: Namespace) -> CommandResult:
        """Execute monitor command.

        Args:
            args: Validated command arguments

        Returns:
            CommandResult with execution status and data
        """
        # Route to appropriate subcommand handler
        handlers = {
            'start': self._handle_start,
            'stop': self._handle_stop,
            'status': self._handle_status,
            'logs': self._handle_logs,
            'clear': self._handle_clear
        }

        handler = handlers.get(args.subcommand)
        if not handler:
            return CommandResult.error_result(
                f"No handler for subcommand: {args.subcommand}",
                exit_code=2
            )

        return handler(args)

    def _handle_start(self, args: Namespace) -> CommandResult:
        """Handle monitor start subcommand."""
        self.logger.info(f"Starting monitor on port {args.port}")

        try:
            service = MonitorService()

            # Check if already running
            if service.is_running():
                return CommandResult.error_result(
                    "Monitor is already running\n\n"
                    "💡 Suggestion: Stop the existing monitor first with: /monitor stop",
                    exit_code=8  # Invalid state
                )

            # Start the monitor
            result = service.start(
                port=args.port,
                background=args.background
            )

            self.logger.info(f"Monitor started successfully (PID: {result['pid']})")

            return CommandResult.success_result(
                f"✓ Monitor started successfully\n"
                f"Port: {args.port}\n"
                f"Dashboard: http://localhost:3000\n"
                f"PID: {result['pid']}",
                data=result
            )

        except PortInUseError as e:
            self.logger.error(f"Port {args.port} already in use")
            return CommandResult.error_result(
                f"❌ Failed to Start Monitor\n\n"
                f"Port {args.port} is already in use by another process.\n\n"
                f"💡 Suggestion: Try one of these options:\n"
                f"   1. Use a different port: /monitor start --port 9000\n"
                f"   2. Find the process using the port: lsof -i :{args.port}\n"
                f"   3. Stop other monitor instances: /monitor stop",
                exit_code=3  # Service unavailable
            )
        except Exception as e:
            self.logger.exception("Unexpected error starting monitor")
            return CommandResult.error_result(
                f"❌ Unexpected Error\n\n{str(e)}",
                exit_code=1
            )

    def _handle_stop(self, args: Namespace) -> CommandResult:
        """Handle monitor stop subcommand."""
        self.logger.info("Stopping monitor")

        try:
            service = MonitorService()

            # Check if running
            if not service.is_running():
                return CommandResult.error_result(
                    "Monitor is not running\n\n"
                    "💡 Suggestion: Start the monitor with: /monitor start",
                    exit_code=8  # Invalid state
                )

            # Confirm if not forced
            if not args.force and not args.yes:
                confirm = input("Stop monitor? [y/N]: ")
                if confirm.lower() != 'y':
                    return CommandResult.success_result("Operation cancelled")

            # Stop the monitor
            service.stop(force=args.force)

            self.logger.info("Monitor stopped successfully")

            return CommandResult.success_result("✓ Monitor stopped successfully")

        except TimeoutError:
            self.logger.error("Monitor stop timed out")
            return CommandResult.error_result(
                "❌ Stop Timed Out\n\n"
                "Monitor did not stop within timeout period.\n\n"
                "💡 Suggestion: Try force stop: /monitor stop --force",
                exit_code=4  # Timeout
            )
        except Exception as e:
            self.logger.exception("Error stopping monitor")
            return CommandResult.error_result(
                f"❌ Error Stopping Monitor\n\n{str(e)}",
                exit_code=1
            )

    # Additional handlers omitted for brevity...


def create_parser() -> ArgumentParser:
    """Create argument parser for monitor command.

    Returns:
        Configured ArgumentParser instance
    """
    parser = ArgumentParser(
        prog='/monitor',
        description='Monitor Claude MPM system in real-time',
        epilog='Examples:\n'
               '  /monitor start --port 9000\n'
               '  /monitor status --verbose\n'
               '  /monitor logs --tail 100 --filter "error"',
        formatter_class=RawDescriptionHelpFormatter
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest='subcommand', required=True)

    # Start subcommand
    start_parser = subparsers.add_parser('start', help='Start monitor service')
    start_parser.add_argument(
        '--port',
        type=int,
        default=8765,
        metavar='PORT',
        help='WebSocket port (default: 8765, range: 1024-65535)'
    )
    start_parser.add_argument(
        '--background',
        action='store_true',
        help='Run monitor in background'
    )

    # Stop subcommand
    stop_parser = subparsers.add_parser('stop', help='Stop monitor service')
    stop_parser.add_argument(
        '--force',
        action='store_true',
        help='Force stop without graceful shutdown'
    )
    stop_parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompt'
    )

    # Status subcommand
    status_parser = subparsers.add_parser('status', help='Show monitor status')
    status_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed status information'
    )

    # Additional subcommands omitted for brevity...

    return parser


# Module exports
__all__ = ['MonitorCommand', 'create_parser']
```

### Common Mistakes to Avoid

#### ❌ Mistake 1: Inconsistent Error Messages
```python
# BAD: Inconsistent error format
return CommandResult.error_result("Error!")

# GOOD: Structured error message
return CommandResult.error_result(
    "❌ Invalid Configuration\n\n"
    "Port number must be between 1024 and 65535.\n\n"
    "💡 Suggestion: Try --port 8765",
    exit_code=2
)
```

#### ❌ Mistake 2: Missing Validation
```python
# BAD: No validation
def run(self, args):
    service.start(args.port)  # What if port is invalid?

# GOOD: Proper validation
def validate_args(self, args):
    if not 1024 <= args.port <= 65535:
        return f"Invalid port: {args.port}"
    return None
```

#### ❌ Mistake 3: Poor Help Text
```python
# BAD: Vague help text
parser.add_argument('--port', help='Port')

# GOOD: Descriptive help with context
parser.add_argument(
    '--port',
    type=int,
    default=8765,
    metavar='PORT',
    help='WebSocket port for monitor service (default: 8765, range: 1024-65535)'
)
```

#### ❌ Mistake 4: Inconsistent Flag Names
```python
# BAD: Non-standard flag names
parser.add_argument('--show-all')      # Should be --verbose
parser.add_argument('--skip-confirm')  # Should be --yes or --force

# GOOD: Standard flag names
parser.add_argument('--verbose', '-v', action='store_true')
parser.add_argument('--yes', '-y', action='store_true')
```

#### ❌ Mistake 5: No Automation Support
```python
# BAD: Always prompts user
confirm = input("Continue? [y/N]: ")

# GOOD: Supports automation
if not args.yes:
    if args.non_interactive:
        raise RuntimeError("Interactive input required but --non-interactive specified")
    confirm = input("Continue? [y/N]: ")
else:
    confirm = 'y'
```

---

## Reference Tables

### Standard Exit Codes Reference

| Code | Constant Name          | Meaning                   | Usage Pattern                         |
|------|------------------------|---------------------------|---------------------------------------|
| 0    | EXIT_SUCCESS           | Success                   | Operation completed successfully      |
| 1    | EXIT_GENERAL_ERROR     | General error             | Unexpected errors, generic failures   |
| 2    | EXIT_USAGE_ERROR       | Invalid usage             | Argument validation, wrong usage      |
| 3    | EXIT_SERVICE_ERROR     | Service unavailable       | Service not running, port conflicts   |
| 4    | EXIT_TIMEOUT           | Operation timeout         | Timeouts, unresponsive operations     |
| 5    | EXIT_PERMISSION_ERROR  | Permission denied         | Access denied, auth failures          |
| 6    | EXIT_NOT_FOUND         | Resource not found        | File/config not found, missing data   |
| 7    | EXIT_ALREADY_EXISTS    | Resource exists           | Duplicate creation, conflicts         |
| 8    | EXIT_INVALID_STATE     | Invalid state             | Wrong state for operation             |

### Standard Flag Reference

| Flag             | Short | Type    | Purpose                           | Default  |
|------------------|-------|---------|-----------------------------------|----------|
| --verbose        | -v    | flag    | Enable detailed output            | false    |
| --quiet          | -q    | flag    | Suppress non-error output         | false    |
| --debug          | -d    | flag    | Enable debug mode                 | false    |
| --dry-run        | -     | flag    | Preview without executing         | false    |
| --force          | -f    | flag    | Skip confirmations                | false    |
| --yes            | -y    | flag    | Answer yes to all prompts         | false    |
| --non-interactive| -     | flag    | Fail if interaction needed        | false    |
| --format         | -     | choice  | Output format (json/yaml/table)   | text     |
| --output         | -o    | path    | Output file path                  | stdout   |
| --config         | -c    | path    | Configuration file path           | default  |
| --timeout        | -     | int     | Operation timeout (seconds)       | 30       |
| --limit          | -l    | int     | Limit result count                | 100      |
| --filter         | -     | string  | Filter pattern/expression         | none     |
| --help           | -h    | flag    | Show help message                 | -        |
| --version        | -     | flag    | Show version information          | -        |

### Argument Group Naming Conventions

| Group Name          | Purpose                                  | Example Arguments                    |
|---------------------|------------------------------------------|--------------------------------------|
| required arguments  | Arguments that must be provided          | subcommand, input_file               |
| optional arguments  | Common optional flags and options        | --verbose, --format, --output        |
| advanced options    | Advanced/expert options                  | --timeout, --retry-count, --threads  |
| filtering options   | Data filtering and selection             | --filter, --type, --status, --limit  |
| output options      | Output control and formatting            | --format, --output, --no-color       |
| configuration       | Configuration and settings               | --config, --profile, --env           |

---

## Enforcement and Updates

### Automated Enforcement

The project includes automated checks to enforce these standards:

```bash
# Run standards validation
python scripts/validate_command_standards.py

# Check specific command
python scripts/validate_command_standards.py /monitor

# Generate standards report
python scripts/validate_command_standards.py --report
```

### Standards Updates

This document is a living standard. To propose updates:

1. Open an issue with the "standards" label
2. Provide rationale and examples
3. Demonstrate backward compatibility or migration path
4. Update this document via pull request
5. Update validation scripts if needed

### Quality Score Matrix

Commands are scored on standardization (from research analysis):

| Score | Rating    | Description                              | Action Required                |
|-------|-----------|------------------------------------------|--------------------------------|
| 90+   | Excellent | Fully compliant, exemplary               | None - use as reference        |
| 80-89 | Good      | Minor inconsistencies                    | Minor cleanup recommended      |
| 70-79 | Fair      | Several improvements needed              | Refactoring suggested          |
| 60-69 | Poor      | Significant standards violations         | Refactoring required           |
| <60   | Critical  | Major issues, non-compliant              | Immediate refactoring required |

---

## Summary

Following these standards ensures:

✅ **Consistent User Experience** - Predictable patterns across all commands
✅ **Better Documentation** - Complete, standardized documentation
✅ **Easier Maintenance** - Clear patterns reduce complexity
✅ **Higher Quality** - Comprehensive testing and validation
✅ **Better Automation** - Non-interactive support built-in

For questions about these standards, see:
- [CLI Architecture](../src/claude_mpm/cli/README.md)
- [BaseCommand Patterns](./03-development/cli-basecommand-patterns.md)
- [Development Guidelines](../../CLAUDE.md)

**Document Version**: 1.0.0
**Effective Date**: 2025-10-08
**Review Cycle**: Quarterly
