"""
Configuration management commands for claude-mpm CLI.

WHY: Users need a simple way to validate and manage their configuration from
the command line. This module provides commands for configuration validation,
viewing, and troubleshooting.

DESIGN DECISIONS:
- Integrate with existing CLI structure
- Provide clear, actionable output
- Support both validation and viewing operations
- Use consistent error codes for CI/CD integration
"""

import sys
from pathlib import Path
from typing import Optional
import json
import yaml

from ...core.config import Config
from ...core.logger import get_logger
from ...utils.console import console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel

logger = get_logger(__name__)


def manage_config(args) -> int:
    """Main entry point for configuration management commands.
    
    WHY: This dispatcher handles different configuration subcommands,
    routing to the appropriate handler based on user input.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    if args.config_command == 'validate':
        return validate_config(args)
    elif args.config_command == 'view':
        return view_config(args)
    elif args.config_command == 'status':
        return show_config_status(args)
    else:
        console.print(f"[red]Unknown config command: {args.config_command}[/red]")
        return 1


def validate_config(args) -> int:
    """Validate configuration file.
    
    WHY: Users need immediate feedback on configuration validity with
    clear guidance on how to fix any issues found.
    
    Args:
        args: Command line arguments including config file path
        
    Returns:
        Exit code (0=valid, 1=errors, 2=warnings in strict mode)
    """
    config_file = args.config_file or Path(".claude-mpm/configuration.yaml")
    
    console.print(f"\n[bold blue]Validating configuration: {config_file}[/bold blue]\n")
    
    # Check if file exists
    if not config_file.exists():
        console.print(f"[red]✗ Configuration file not found: {config_file}[/red]")
        console.print(f"[yellow]→ Create with: mkdir -p {config_file.parent} && touch {config_file}[/yellow]")
        return 1
        
    try:
        # Try to load configuration
        config = Config(config_file=config_file)
        
        # Validate configuration
        is_valid, errors, warnings = config.validate_configuration()
        
        # Display results
        if errors:
            console.print("[bold red]ERRORS:[/bold red]")
            for error in errors:
                console.print(f"  [red]✗ {error}[/red]")
                
        if warnings:
            console.print("\n[bold yellow]WARNINGS:[/bold yellow]")
            for warning in warnings:
                console.print(f"  [yellow]⚠ {warning}[/yellow]")
                
        # Show summary
        if is_valid and not warnings:
            console.print("\n[green]✓ Configuration is valid[/green]")
            return 0
        elif is_valid and warnings:
            console.print(f"\n[green]✓ Configuration is valid with {len(warnings)} warning(s)[/green]")
            return 2 if args.strict else 0
        else:
            console.print(f"\n[red]✗ Configuration validation failed with {len(errors)} error(s)[/red]")
            console.print("\n[yellow]Run 'python scripts/validate_configuration.py' for detailed analysis[/yellow]")
            return 1
            
    except Exception as e:
        console.print(f"[red]Failed to validate configuration: {e}[/red]")
        logger.exception("Configuration validation error")
        return 1


def view_config(args) -> int:
    """View current configuration.
    
    WHY: Users need to see their effective configuration including
    defaults and environment variable overrides.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success)
    """
    try:
        # Load configuration
        config_file = args.config_file
        config = Config(config_file=config_file)
        
        # Get configuration as dictionary
        config_dict = config.to_dict()
        
        # Filter by section if specified
        if args.section:
            if args.section in config_dict:
                config_dict = {args.section: config_dict[args.section]}
            else:
                console.print(f"[red]Section '{args.section}' not found in configuration[/red]")
                return 1
                
        # Format output
        if args.format == 'json':
            output = json.dumps(config_dict, indent=2)
            syntax = Syntax(output, "json", theme="monokai", line_numbers=False)
            console.print(syntax)
        elif args.format == 'yaml':
            output = yaml.dump(config_dict, default_flow_style=False, sort_keys=False)
            syntax = Syntax(output, "yaml", theme="monokai", line_numbers=False)
            console.print(syntax)
        else:  # table format
            display_config_table(config_dict)
            
        return 0
        
    except Exception as e:
        console.print(f"[red]Failed to view configuration: {e}[/red]")
        logger.exception("Configuration view error")
        return 1


def show_config_status(args) -> int:
    """Show configuration status and health.
    
    WHY: Users need a quick way to check if their configuration is
    working correctly, especially for response logging.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success)
    """
    try:
        # Load configuration
        config = Config(config_file=args.config_file)
        
        # Get status
        status = config.get_configuration_status()
        
        # Create status panel
        panel_content = []
        
        # Basic info
        panel_content.append(f"[bold]Configuration Status[/bold]")
        panel_content.append(f"Valid: {'✓' if status['valid'] else '✗'}")
        panel_content.append(f"Loaded from: {status.get('loaded_from', 'defaults')}")
        panel_content.append(f"Total keys: {status['key_count']}")
        
        # Feature status
        panel_content.append("\n[bold]Features:[/bold]")
        panel_content.append(
            f"Response Logging: {'✓ Enabled' if status['response_logging_enabled'] else '✗ Disabled'}"
        )
        panel_content.append(
            f"Memory System: {'✓ Enabled' if status['memory_enabled'] else '✗ Disabled'}"
        )
        
        # Errors and warnings
        if status['errors']:
            panel_content.append(f"\n[red]Errors: {len(status['errors'])}[/red]")
        if status['warnings']:
            panel_content.append(f"\n[yellow]Warnings: {len(status['warnings'])}[/yellow]")
            
        # Display panel
        panel = Panel(
            "\n".join(panel_content),
            title="Configuration Status",
            border_style="green" if status['valid'] else "red"
        )
        console.print(panel)
        
        # Show detailed errors/warnings if verbose
        if args.verbose:
            if status['errors']:
                console.print("\n[bold red]Errors:[/bold red]")
                for error in status['errors']:
                    console.print(f"  [red]• {error}[/red]")
                    
            if status['warnings']:
                console.print("\n[bold yellow]Warnings:[/bold yellow]")
                for warning in status['warnings']:
                    console.print(f"  [yellow]• {warning}[/yellow]")
                    
        # Check response logging specifically
        if args.check_response_logging:
            console.print("\n[bold]Response Logging Configuration:[/bold]")
            rl_config = config.get('response_logging', {})
            
            table = Table(show_header=True)
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("Enabled", str(rl_config.get('enabled', False)))
            table.add_row("Format", rl_config.get('format', 'json'))
            table.add_row("Use Async", str(rl_config.get('use_async', True)))
            table.add_row("Session Directory", rl_config.get('session_directory', '.claude-mpm/responses'))
            table.add_row("Compression", str(rl_config.get('enable_compression', False)))
            
            console.print(table)
            
        return 0 if status['valid'] else 1
        
    except Exception as e:
        console.print(f"[red]Failed to get configuration status: {e}[/red]")
        logger.exception("Configuration status error")
        return 1


def display_config_table(config_dict: dict, prefix: str = "") -> None:
    """Display configuration as a formatted table.
    
    Args:
        config_dict: Configuration dictionary
        prefix: Key prefix for nested values
    """
    table = Table(show_header=True, title="Configuration")
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    table.add_column("Type", style="dim")
    
    def add_items(d: dict, prefix: str = ""):
        for key, value in d.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict) and value:
                # Add nested items
                add_items(value, full_key)
            else:
                # Add leaf value
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:47] + "..."
                    
                type_str = type(value).__name__
                table.add_row(full_key, value_str, type_str)
                
    add_items(config_dict)
    console.print(table)