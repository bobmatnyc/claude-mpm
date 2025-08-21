# CLI BaseCommand Patterns - Developer Guide

## Overview

The Claude MPM CLI has been migrated to use a standardized BaseCommand pattern that provides consistent behavior, error handling, and output formatting across all commands. This guide explains how to work with and extend the BaseCommand system.

## Architecture

### BaseCommand Pattern

All CLI commands inherit from the `BaseCommand` abstract base class, which provides:

- **Consistent Execution Flow**: Standardized command lifecycle
- **Error Handling**: Unified error handling and reporting
- **Configuration Management**: Lazy-loaded configuration with caching
- **Output Formatting**: Structured output in multiple formats (text, JSON, YAML, table)
- **Logging Setup**: Automatic logging configuration
- **Argument Validation**: Built-in argument validation patterns

### Command Hierarchy

```
BaseCommand (Abstract)
├── ServiceCommand (Abstract) - For service-related commands
├── AgentCommand (Abstract) - For agent management commands
├── MemoryCommand (Abstract) - For memory management commands
├── ConfigCommand - Configuration management
├── AggregateCommand - Data aggregation
└── [Other specific commands]
```

## Creating a New Command

### 1. Basic Command Structure

```python
from claude_mpm.cli.shared.command_base import BaseCommand, CommandResult
from argparse import Namespace

class MyCommand(BaseCommand):
    """My custom command implementation."""
    
    def __init__(self):
        super().__init__("my-command")
    
    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments."""
        if not hasattr(args, 'required_arg'):
            return "Missing required argument: required_arg"
        return None
    
    def run(self, args) -> CommandResult:
        """Execute the command logic."""
        try:
            # Your command logic here
            result_data = {"processed": True}
            return CommandResult.success_result(
                "Command completed successfully",
                data=result_data
            )
        except Exception as e:
            return CommandResult.error_result(f"Command failed: {e}")
```

### 2. Service Command Pattern

For commands that interact with services:

```python
from claude_mpm.cli.shared.command_base import ServiceCommand, CommandResult
from my_service import MyService

class MyServiceCommand(ServiceCommand):
    """Command for managing my service."""
    
    def __init__(self):
        super().__init__("my-service", MyService)
    
    def run(self, args) -> CommandResult:
        """Execute service command."""
        # Access service via self.service property
        result = self.service.perform_operation(args.operation)
        return CommandResult.success_result("Operation completed", data=result)
```

### 3. Agent Command Pattern

For agent-related commands:

```python
from claude_mpm.cli.shared.command_base import AgentCommand, CommandResult

class MyAgentCommand(AgentCommand):
    """Command for agent operations."""
    
    def __init__(self):
        super().__init__("my-agent-cmd")
    
    def run(self, args) -> CommandResult:
        """Execute agent command."""
        agent_dir = self.get_agent_dir(args)
        agent_pattern = self.get_agent_pattern(args)
        
        # Your agent logic here
        return CommandResult.success_result("Agent operation completed")
```

## Command Features

### Configuration Management

Commands automatically have access to configuration:

```python
def run(self, args) -> CommandResult:
    # Access configuration
    config_value = self.config.get("my_setting", "default_value")
    
    # Load specific config file
    self.load_config(args)  # Uses args.config if provided
    
    return CommandResult.success_result("Config loaded")
```

### Working Directory

Commands have access to the working directory:

```python
def run(self, args) -> CommandResult:
    working_dir = self.working_dir  # Path object
    config_file = working_dir / ".claude-mpm" / "config.yaml"
    
    return CommandResult.success_result(f"Working in {working_dir}")
```

### Logging

Commands have automatic logging setup:

```python
def run(self, args) -> CommandResult:
    self.logger.info("Starting command execution")
    self.logger.debug("Debug information")
    
    return CommandResult.success_result("Command completed")
```

## Output Formatting

### CommandResult Structure

All commands return `CommandResult` objects:

```python
# Success result
CommandResult.success_result(
    message="Operation completed",
    data={"key": "value"}  # Optional structured data
)

# Error result
CommandResult.error_result(
    message="Operation failed",
    exit_code=2,  # Optional custom exit code
    data={"error_details": "..."}  # Optional error data
)
```

### Automatic Formatting

The BaseCommand system automatically formats output based on the `--format` argument:

- **text**: Human-readable text output (default)
- **json**: JSON format for programmatic use
- **yaml**: YAML format for configuration files
- **table**: Tabular format for structured data

### Custom Output Handling

```python
def run(self, args) -> CommandResult:
    result_data = {"items": [{"name": "item1"}, {"name": "item2"}]}
    
    # The framework will automatically format based on args.format
    return CommandResult.success_result(
        "Found 2 items",
        data=result_data
    )
```

## Error Handling

### Built-in Error Handling

The BaseCommand system provides automatic error handling:

```python
def run(self, args) -> CommandResult:
    # Exceptions are automatically caught and converted to error results
    raise ValueError("Something went wrong")
    # This becomes: CommandResult.error_result("Something went wrong")
```

### Custom Error Handling

```python
def run(self, args) -> CommandResult:
    try:
        # Risky operation
        result = risky_operation()
        return CommandResult.success_result("Success", data=result)
    except SpecificError as e:
        return CommandResult.error_result(f"Specific error: {e}", exit_code=2)
    except Exception as e:
        self.logger.exception("Unexpected error")
        return CommandResult.error_result(f"Unexpected error: {e}")
```

## Argument Patterns

### Common Arguments

Use shared argument patterns for consistency:

```python
from claude_mpm.cli.shared.argument_patterns import (
    add_common_arguments,
    add_logging_arguments,
    add_output_arguments
)

def add_my_command_args(parser):
    """Add arguments for my command."""
    add_common_arguments(parser)  # --verbose, --quiet, --debug
    add_output_arguments(parser)  # --format, --output
    
    # Command-specific arguments
    parser.add_argument("--my-option", help="My custom option")
```

### Validation Patterns

```python
def validate_args(self, args) -> Optional[str]:
    """Validate command arguments."""
    # Check required arguments
    if not args.required_field:
        return "Missing required field"
    
    # Validate argument values
    if args.count < 0:
        return "Count must be non-negative"
    
    # Validate file paths
    if args.input_file and not Path(args.input_file).exists():
        return f"Input file not found: {args.input_file}"
    
    return None  # No validation errors
```

## Testing Commands

### Unit Testing

```python
import pytest
from argparse import Namespace
from my_command import MyCommand

class TestMyCommand:
    def setup_method(self):
        self.command = MyCommand()
    
    def test_successful_execution(self):
        args = Namespace(required_arg="value")
        result = self.command.execute(args)
        
        assert result.success is True
        assert result.exit_code == 0
        assert "success" in result.message.lower()
    
    def test_validation_error(self):
        args = Namespace()  # Missing required_arg
        result = self.command.execute(args)
        
        assert result.success is False
        assert result.exit_code == 1
        assert "required argument" in result.message
```

### Integration Testing

```python
def test_command_integration():
    """Test command with real dependencies."""
    command = MyCommand()
    args = Namespace(
        required_arg="test_value",
        format="json",
        verbose=True
    )
    
    result = command.execute(args)
    
    assert result.success is True
    assert result.data is not None
```

## Best Practices

### 1. Command Design
- Keep commands focused on a single responsibility
- Use descriptive command names and help text
- Provide meaningful error messages
- Include structured data in results for programmatic use

### 2. Error Handling
- Validate arguments early and provide clear error messages
- Use appropriate exit codes (0=success, 1=general error, 2=usage error)
- Log errors appropriately (debug for expected errors, error for unexpected)

### 3. Output
- Always return CommandResult objects
- Include structured data for complex results
- Use consistent message formatting
- Support all output formats when possible

### 4. Configuration
- Use the shared configuration system
- Support both file-based and environment variable configuration
- Provide sensible defaults

### 5. Testing
- Write unit tests for command logic
- Test argument validation
- Test error conditions
- Include integration tests for complex commands

## Migration Guide

### Migrating Existing Commands

1. **Inherit from BaseCommand**: Change your command class to inherit from `BaseCommand`
2. **Implement required methods**: Add `run()` and optionally `validate_args()`
3. **Return CommandResult**: Update your command to return `CommandResult` objects
4. **Update argument handling**: Use shared argument patterns where possible
5. **Add tests**: Create comprehensive tests for your migrated command

### Backward Compatibility

The BaseCommand system maintains backward compatibility through wrapper functions:

```python
def legacy_command_function(args) -> int:
    """Legacy function wrapper."""
    command = MyCommand()
    result = command.execute(args)
    
    # Print structured output if needed
    if hasattr(args, 'format') and args.format in ['json', 'yaml']:
        command.print_result(result, args)
    
    return result.exit_code
```

## Examples

See the following files for complete examples:
- `src/claude_mpm/cli/commands/config.py` - Configuration management
- `src/claude_mpm/cli/commands/aggregate.py` - Data aggregation
- `tests/cli/test_base_command.py` - Comprehensive test examples

## Support

For questions about the BaseCommand pattern:
1. Check existing command implementations for patterns
2. Review the test suite for usage examples
3. Consult the API documentation for detailed method signatures
