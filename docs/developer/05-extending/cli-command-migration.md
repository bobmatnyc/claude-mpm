# CLI Command Migration Guide

## Overview

This guide helps developers migrate existing CLI commands to the new BaseCommand pattern introduced in EP-0002 (Code Duplication Reduction Project). The BaseCommand pattern provides consistent behavior, error handling, and output formatting across all CLI commands.

## Migration Benefits

### Before Migration
- Inconsistent error handling across commands
- Duplicate configuration loading code
- Varied output formats
- Manual argument validation
- Scattered logging setup

### After Migration
- ✅ Consistent command execution flow
- ✅ Standardized error handling and exit codes
- ✅ Unified output formatting (text, JSON, YAML, table)
- ✅ Automatic configuration management
- ✅ Built-in logging setup
- ✅ Comprehensive test patterns

## Migration Steps

### Step 1: Analyze Current Command

Before migrating, understand your current command structure:

```python
# OLD PATTERN - Before migration
def my_command_function(args):
    """Legacy command function."""
    try:
        # Manual configuration loading
        config = load_config(args.config)
        
        # Manual logging setup
        setup_logging(args.verbose, args.debug)
        
        # Command logic
        result = perform_operation(args)
        
        # Manual output formatting
        if args.format == 'json':
            print(json.dumps(result))
        else:
            print(f"Operation completed: {result}")
        
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1
```

### Step 2: Create BaseCommand Class

Transform the function into a BaseCommand class:

```python
# NEW PATTERN - After migration
from claude_mpm.cli.shared.command_base import BaseCommand, CommandResult
from argparse import Namespace
from typing import Optional

class MyCommand(BaseCommand):
    """My command using BaseCommand pattern."""
    
    def __init__(self):
        super().__init__("my-command")
    
    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments."""
        # Move argument validation here
        if not hasattr(args, 'required_field'):
            return "Missing required field"
        return None
    
    def run(self, args) -> CommandResult:
        """Execute the command logic."""
        # Configuration and logging are automatically handled
        
        # Your command logic here
        result = self.perform_operation(args)
        
        # Return structured result
        return CommandResult.success_result(
            "Operation completed successfully",
            data=result
        )
    
    def perform_operation(self, args):
        """Your existing command logic."""
        # Move your existing logic here
        pass
```

### Step 3: Create Backward Compatibility Wrapper

Maintain backward compatibility with a wrapper function:

```python
def my_command_function(args) -> int:
    """Backward compatibility wrapper."""
    command = MyCommand()
    result = command.execute(args)
    
    # Handle structured output for legacy callers
    if hasattr(args, 'format') and args.format in ['json', 'yaml']:
        command.print_result(result, args)
    
    return result.exit_code
```

### Step 4: Update Argument Parser

Use shared argument patterns:

```python
# OLD PATTERN
def add_my_command_args(parser):
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--config', '-c', type=str)
    parser.add_argument('--format', choices=['text', 'json'])

# NEW PATTERN
from claude_mpm.cli.shared.argument_patterns import (
    add_common_arguments,
    add_output_arguments
)

def add_my_command_args(parser):
    add_common_arguments(parser)  # --verbose, --debug, etc.
    add_output_arguments(parser)  # --format, --output
    
    # Command-specific arguments
    parser.add_argument('--my-option', help='My custom option')
```

### Step 5: Update Tests

Create comprehensive tests using the new patterns:

```python
import pytest
from argparse import Namespace
from my_command import MyCommand

class TestMyCommand:
    def setup_method(self):
        self.command = MyCommand()
    
    def test_successful_execution(self):
        args = Namespace(required_field="value")
        result = self.command.execute(args)
        
        assert result.success is True
        assert result.exit_code == 0
        assert "completed successfully" in result.message
    
    def test_validation_error(self):
        args = Namespace()  # Missing required_field
        result = self.command.execute(args)
        
        assert result.success is False
        assert result.exit_code == 1
        assert "required field" in result.message
    
    def test_output_formatting(self):
        args = Namespace(required_field="value", format="json")
        result = self.command.execute(args)
        
        assert result.success is True
        assert result.data is not None
```

## Migration Patterns

### Service Commands

For commands that interact with services:

```python
# OLD PATTERN
def service_command(args):
    service = MyService()
    result = service.operation()
    return 0 if result else 1

# NEW PATTERN
from claude_mpm.cli.shared.command_base import ServiceCommand

class MyServiceCommand(ServiceCommand):
    def __init__(self):
        super().__init__("my-service", MyService)
    
    def run(self, args) -> CommandResult:
        result = self.service.operation()  # self.service is auto-created
        return CommandResult.success_result("Operation completed", data=result)
```

### Agent Commands

For agent-related commands:

```python
# OLD PATTERN
def agent_command(args):
    agent_dir = args.agent_dir or os.getcwd()
    # Manual agent discovery logic
    return 0

# NEW PATTERN
from claude_mpm.cli.shared.command_base import AgentCommand

class MyAgentCommand(AgentCommand):
    def __init__(self):
        super().__init__("my-agent-cmd")
    
    def run(self, args) -> CommandResult:
        agent_dir = self.get_agent_dir(args)  # Built-in helper
        agent_pattern = self.get_agent_pattern(args)
        
        # Your agent logic here
        return CommandResult.success_result("Agent operation completed")
```

### Memory Commands

For memory-related commands:

```python
# OLD PATTERN
def memory_command(args):
    memory_dir = args.memory_dir or default_memory_dir()
    # Manual memory operations
    return 0

# NEW PATTERN
from claude_mpm.cli.shared.command_base import MemoryCommand

class MyMemoryCommand(MemoryCommand):
    def __init__(self):
        super().__init__("my-memory-cmd")
    
    def run(self, args) -> CommandResult:
        memory_dir = self.get_memory_dir(args)  # Built-in helper
        
        # Your memory logic here
        return CommandResult.success_result("Memory operation completed")
```

## Common Migration Issues

### Issue 1: Configuration Loading

**Problem**: Manual configuration loading code
```python
# OLD - Manual loading
config = Config(args.config) if args.config else Config()
```

**Solution**: Use automatic configuration
```python
# NEW - Automatic loading
def run(self, args) -> CommandResult:
    # Configuration available as self.config
    value = self.config.get("my_setting", "default")
```

### Issue 2: Error Handling

**Problem**: Inconsistent error handling
```python
# OLD - Manual error handling
try:
    result = operation()
    print("Success")
    return 0
except Exception as e:
    print(f"Error: {e}")
    return 1
```

**Solution**: Use CommandResult
```python
# NEW - Structured error handling
def run(self, args) -> CommandResult:
    try:
        result = operation()
        return CommandResult.success_result("Success", data=result)
    except SpecificError as e:
        return CommandResult.error_result(f"Specific error: {e}", exit_code=2)
```

### Issue 3: Output Formatting

**Problem**: Manual output formatting
```python
# OLD - Manual formatting
if args.format == 'json':
    print(json.dumps(result))
elif args.format == 'yaml':
    print(yaml.dump(result))
else:
    print(f"Result: {result}")
```

**Solution**: Automatic formatting
```python
# NEW - Automatic formatting
def run(self, args) -> CommandResult:
    # Framework handles formatting based on args.format
    return CommandResult.success_result("Operation completed", data=result)
```

## Testing Migration

### Test Checklist

- [ ] Command executes successfully with valid arguments
- [ ] Argument validation works correctly
- [ ] Error handling produces appropriate exit codes
- [ ] All output formats work (text, JSON, YAML, table)
- [ ] Configuration loading works
- [ ] Logging setup functions correctly
- [ ] Backward compatibility wrapper works
- [ ] Integration tests pass

### Test Template

```python
class TestMigratedCommand:
    def setup_method(self):
        self.command = MyCommand()
    
    def test_migration_compatibility(self):
        """Test that migration maintains compatibility."""
        # Test with various argument combinations
        test_cases = [
            Namespace(required_field="value"),
            Namespace(required_field="value", format="json"),
            Namespace(required_field="value", verbose=True),
        ]
        
        for args in test_cases:
            result = self.command.execute(args)
            assert result is not None
            assert hasattr(result, 'success')
            assert hasattr(result, 'exit_code')
    
    def test_backward_compatibility(self):
        """Test that legacy function wrapper works."""
        from my_command import my_command_function
        
        args = Namespace(required_field="value")
        exit_code = my_command_function(args)
        assert exit_code == 0
```

## Migration Checklist

### Pre-Migration
- [ ] Identify all functions/methods to migrate
- [ ] Document current behavior and edge cases
- [ ] Identify dependencies and integrations
- [ ] Plan backward compatibility strategy

### During Migration
- [ ] Create BaseCommand class
- [ ] Implement `run()` method
- [ ] Add argument validation in `validate_args()`
- [ ] Update argument parser to use shared patterns
- [ ] Create backward compatibility wrapper
- [ ] Write comprehensive tests

### Post-Migration
- [ ] Verify all tests pass
- [ ] Test backward compatibility
- [ ] Update documentation
- [ ] Add deprecation warnings to old functions
- [ ] Plan removal timeline for legacy code

## Best Practices

1. **Incremental Migration**: Migrate commands one at a time
2. **Maintain Compatibility**: Always provide backward compatibility wrappers
3. **Test Thoroughly**: Include unit, integration, and compatibility tests
4. **Document Changes**: Update documentation and add migration notes
5. **Use Shared Patterns**: Leverage existing argument patterns and utilities
6. **Handle Errors Gracefully**: Use appropriate exit codes and error messages

## Examples

See these files for complete migration examples:
- `src/claude_mpm/cli/commands/config.py` - Configuration command migration
- `src/claude_mpm/cli/commands/aggregate.py` - Aggregate command migration
- `tests/cli/test_config_command.py` - Comprehensive test examples

## Support

For migration assistance:
1. Review existing migrated commands for patterns
2. Check the test suite for examples
3. Consult the BaseCommand API documentation
4. Follow the established patterns in the codebase
