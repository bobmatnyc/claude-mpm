# CLI Refactoring Guide

This guide shows how to refactor the main() function in `/src/claude_mpm/cli.py` to reduce complexity from 16 to under 10.

## Current Issues

1. **High Cyclomatic Complexity (16)**
   - Multiple nested conditionals
   - Duplicate argument definitions
   - Mixed concerns in one function

2. **Code Duplication**
   - Arguments defined twice (global level + run subcommand)
   - Similar patterns repeated for each command

3. **Poor Maintainability**
   - Adding new commands requires multiple changes
   - Hard to test individual components

## Refactoring Steps

### Step 1: Update imports in cli.py

```python
# Add to imports
from .cli import ArgumentRegistry, CommandRegistry, register_standard_commands
```

### Step 2: Replace main() function

Replace the entire `main()` function with:

```python
def main(argv: Optional[list] = None):
    """Main CLI entry point with reduced complexity."""
    # Initialize registries
    arg_registry = ArgumentRegistry()
    cmd_registry = CommandRegistry(arg_registry)
    
    # Register standard commands
    register_standard_commands(cmd_registry)
    
    # Create parser
    parser = argparse.ArgumentParser(
        prog="claude-mpm",
        description=f"Claude Multi-Agent Project Manager v{__version__}",
        epilog="By default, runs an orchestrated Claude session."
    )
    
    # Store version for ArgumentRegistry
    parser._version = f"claude-mpm {__version__}"
    
    # Apply global arguments
    arg_registry.apply_arguments(parser, groups=['global'])
    
    # Apply run arguments at top level (for default behavior)
    arg_registry.apply_arguments(parser, groups=['run'], exclude=['no_hooks'])
    
    # Set up subcommands
    cmd_registry.setup_subcommands(parser)
    
    # Parse arguments
    args = parser.parse_args(argv)
    
    # Set up logging
    _setup_logging(args)
    
    # Initialize hook service
    hook_manager = _initialize_hook_service(args)
    
    try:
        # Execute command
        result = cmd_registry.execute_command(args, hook_manager=hook_manager)
        if result is None and not args.command:
            parser.print_help()
            return 1
        return result or 0
        
    except KeyboardInterrupt:
        get_logger("cli").info("Session interrupted by user")
        return 0
    except Exception as e:
        logger = get_logger("cli")
        logger.error(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    finally:
        if hook_manager:
            hook_manager.stop_service()
```

### Step 3: Extract helper functions

Add these helper functions after main():

```python
def _setup_logging(args):
    """Set up logging based on arguments."""
    if args.debug and args.logging == "OFF":
        args.logging = "DEBUG"
    
    if args.logging != "OFF":
        setup_logging(level=args.logging, log_dir=args.log_dir)
    else:
        import logging
        logger = logging.getLogger("cli")
        logger.setLevel(logging.WARNING)


def _initialize_hook_service(args):
    """Initialize hook service if enabled."""
    if getattr(args, 'no_hooks', False):
        return None
        
    try:
        from .config.hook_config import HookConfig
        
        if not HookConfig.is_hooks_enabled():
            get_logger("cli").info("Hooks disabled via configuration")
            return None
            
        hook_manager = HookServiceManager(log_dir=args.log_dir)
        if hook_manager.start_service():
            logger = get_logger("cli")
            logger.info(f"Hook service started on port {hook_manager.port}")
            print(f"Hook service started on port {hook_manager.port}")
            return hook_manager
        else:
            logger = get_logger("cli")
            logger.warning("Failed to start hook service")
            print("Failed to start hook service, continuing without hooks")
            return None
            
    except Exception as e:
        get_logger("cli").warning(f"Hook service init failed: {e}")
        return None
```

### Step 4: Update command handler signatures

Ensure all command handlers accept `**kwargs`:

```python
def run_session(args, hook_manager=None, **kwargs):
    """Run an orchestrated Claude session."""
    # ... existing implementation

def list_tickets(args, **kwargs):
    """List recent tickets."""
    # ... existing implementation

def show_info(args, hook_manager=None, **kwargs):
    """Show framework and configuration information."""
    # ... existing implementation
```

## Benefits Achieved

### Complexity Reduction
- **Before**: Cyclomatic complexity of 16
- **After**: Cyclomatic complexity of ~8

### Code Organization
- Centralized argument definitions
- No duplicate argument definitions
- Clear separation of concerns
- Easier to add new commands

### Maintainability
- New commands can be added with a single `register()` call
- Arguments are defined once and reused
- Helper functions are testable in isolation
- Registry pattern allows for extension

## Adding New Commands

With the registry system, adding a new command is simple:

```python
# In your code or plugin
def my_command(args, **kwargs):
    """Implementation of your command."""
    print(f"Running my command with args: {args}")
    return 0

# Register it
cmd_registry.register(
    name='mycommand',
    help_text='Description of my command',
    handler=my_command,
    argument_groups=['framework'],  # Reuse existing argument groups
    extra_args={
        'custom_arg': {
            'flags': ['--custom'],
            'type': str,
            'help': 'A custom argument for this command'
        }
    }
)
```

## Testing

The refactored code is easier to test:

```python
# Test argument registry
def test_argument_registry():
    registry = ArgumentRegistry()
    parser = argparse.ArgumentParser()
    registry.apply_arguments(parser, groups=['logging'])
    
    # Verify logging arguments were added
    args = parser.parse_args(['--logging', 'DEBUG'])
    assert args.logging == 'DEBUG'

# Test command registry
def test_command_registry():
    arg_reg = ArgumentRegistry()
    cmd_reg = CommandRegistry(arg_reg)
    
    called = False
    def test_handler(args, **kwargs):
        nonlocal called
        called = True
        return 0
    
    cmd_reg.register('test', 'Test command', test_handler)
    
    parser = argparse.ArgumentParser()
    cmd_reg.setup_subcommands(parser)
    
    args = parser.parse_args(['test'])
    result = cmd_reg.execute_command(args)
    
    assert called
    assert result == 0
```

## Migration Checklist

- [ ] Create `/src/claude_mpm/cli/` directory
- [ ] Create `args.py` with ArgumentRegistry
- [ ] Create `commands.py` with CommandRegistry
- [ ] Create `__init__.py` to export classes
- [ ] Update imports in `cli.py`
- [ ] Replace main() function
- [ ] Add helper functions
- [ ] Update command handler signatures
- [ ] Test the refactored CLI
- [ ] Verify complexity is reduced to ≤10