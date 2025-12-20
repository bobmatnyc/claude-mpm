"""
Configuration management commands for claude-mpm CLI.

WHY: Users need a simple way to validate and manage their configuration from
the command line. This module provides commands for configuration validation,
viewing, and troubleshooting.

DESIGN DECISIONS:
- Use BaseCommand for consistent CLI patterns
- Leverage shared utilities for argument parsing and output formatting
- Provide clear, actionable output with standardized error handling
- Support multiple output formats (json, yaml, table, text)
"""

import json
from pathlib import Path
from typing import Any, Dict

import yaml
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from ...core.config import Config
from ...core.enums import OutputFormat
from ...utils.console import console
from ..shared import BaseCommand, CommandResult


def _is_structured_output(args) -> bool:
    """Check if args specify structured output format (JSON/YAML)."""
    if hasattr(args, "format"):
        fmt = str(args.format).lower()
        return fmt in (OutputFormat.JSON, OutputFormat.YAML)
    return False


class ConfigCommand(BaseCommand):
    """Configuration management command using shared utilities."""

    def __init__(self):
        super().__init__("config")

    def _get_output_format(self, args) -> str:
        """
        Get output format from args with enum default.

        Args:
            args: Command arguments

        Returns:
            Output format string (compatible with both enum and string usage)
        """
        return getattr(args, "format", OutputFormat.TEXT)

    def _is_structured_format(self, format_str: str) -> bool:
        """
        Check if format is structured (JSON/YAML).

        Args:
            format_str: Format string to check

        Returns:
            True if format is JSON or YAML
        """
        fmt = str(format_str).lower()
        return fmt in (OutputFormat.JSON, OutputFormat.YAML)

    def validate_args(self, args) -> str:
        """Validate command arguments."""
        # If no config_command specified, default to 'auto' (preview mode)
        if not hasattr(args, "config_command") or not args.config_command:
            args.config_command = "auto"
            args.preview = True  # Default to preview when no args

        valid_commands = ["validate", "view", "status", "auto", "gitignore"]
        if args.config_command not in valid_commands:
            return f"Unknown config command: {args.config_command}. Valid commands: {', '.join(valid_commands)}"

        return None

    def run(self, args) -> CommandResult:
        """Execute the configuration command."""
        if args.config_command == "validate":
            return self._validate_config(args)
        if args.config_command == "view":
            return self._view_config(args)
        if args.config_command == "status":
            return self._show_config_status(args)
        if args.config_command == "gitignore":
            self._show_gitignore_recommendations()
            return CommandResult.success_result("Gitignore recommendations displayed")
        if args.config_command == "auto":
            return self._auto_configure(args)
        return CommandResult.error_result(
            f"Unknown config command: {args.config_command}"
        )

    def _validate_config(self, args) -> CommandResult:
        """Validate configuration file."""
        config_file = getattr(args, "config_file", None) or Path(
            ".claude-mpm/configuration.yaml"
        )

        # Check if file exists
        if not config_file.exists():
            error_msg = f"Configuration file not found: {config_file}"
            suggestion = (
                f"Create with: mkdir -p {config_file.parent} && touch {config_file}"
            )

            if self._is_structured_format(self._get_output_format(args)):
                return CommandResult.error_result(
                    error_msg,
                    data={"suggestion": suggestion, "config_file": str(config_file)},
                )
            console.print(f"[red]✗ {error_msg}[/red]")
            console.print(f"[yellow]→ {suggestion}[/yellow]")
            return CommandResult.error_result(error_msg)

        try:
            # Load and validate configuration
            if config_file != Path(".claude-mpm/configuration.yaml"):
                # Use specific config file
                config = Config(config_file=config_file)
            else:
                # Use default config
                config = self.config
            is_valid, errors, warnings = config.validate_configuration()

            # Prepare result data
            result_data = {
                "config_file": str(config_file),
                "valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "error_count": len(errors),
                "warning_count": len(warnings),
            }

            # Handle output format
            output_format = self._get_output_format(args)
            if self._is_structured_format(output_format):
                if is_valid and not warnings:
                    return CommandResult.success_result(
                        "Configuration is valid", data=result_data
                    )
                if is_valid and warnings:
                    message = f"Configuration is valid with {len(warnings)} warning(s)"
                    exit_code = 2 if getattr(args, "strict", False) else 0
                    return CommandResult(
                        success=True,
                        exit_code=exit_code,
                        message=message,
                        data=result_data,
                    )
                return CommandResult.error_result(
                    f"Configuration validation failed with {len(errors)} error(s)",
                    data=result_data,
                )
            # Rich console output for text format
            console.print(
                f"\n[bold blue]Validating configuration: {config_file}[/bold blue]\n"
            )

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
                return CommandResult.success_result("Configuration is valid")
            if is_valid and warnings:
                console.print(
                    f"\n[green]✓ Configuration is valid with {len(warnings)} warning(s)[/green]"
                )
                exit_code = 2 if getattr(args, "strict", False) else 0
                return CommandResult(
                    success=True,
                    exit_code=exit_code,
                    message="Configuration valid with warnings",
                )
            console.print(
                f"\n[red]✗ Configuration validation failed with {len(errors)} error(s)[/red]"
            )
            console.print(
                "\n[yellow]Run 'python scripts/validate_configuration.py' for detailed analysis[/yellow]"
            )
            return CommandResult.error_result("Configuration validation failed")

        except Exception as e:
            self.logger.error(f"Configuration validation error: {e}", exc_info=True)

            if self._is_structured_format(self._get_output_format(args)):
                return CommandResult.error_result(
                    f"Failed to validate configuration: {e}",
                    data={"config_file": str(config_file), "exception": str(e)},
                )
            console.print(f"[red]Failed to validate configuration: {e}[/red]")
            return CommandResult.error_result(f"Failed to validate configuration: {e}")

    def _view_config(self, args) -> CommandResult:
        """View current configuration."""
        try:
            # Load configuration
            config_file = getattr(args, "config_file", None)
            config = Config(config_file=config_file)

            # Get configuration as dictionary
            config_dict = config.to_dict()

            # Filter by section if specified
            section = getattr(args, "section", None)
            if section:
                if section in config_dict:
                    config_dict = {section: config_dict[section]}
                else:
                    error_msg = f"Section '{section}' not found in configuration"
                    available_sections = list(config_dict.keys())

                    if self._is_structured_format(self._get_output_format(args)):
                        return CommandResult.error_result(
                            error_msg, data={"available_sections": available_sections}
                        )
                    console.print(f"[red]{error_msg}[/red]")
                    console.print(
                        f"[yellow]Available sections: {', '.join(available_sections)}[/yellow]"
                    )
                    return CommandResult.error_result(error_msg)

            # Handle output format
            output_format = self._get_output_format(args)

            if str(output_format).lower() == OutputFormat.JSON:
                if hasattr(args, "output") and args.output:
                    # Use shared output handling
                    return CommandResult.success_result(
                        "Configuration retrieved", data=config_dict
                    )
                # Direct console output with syntax highlighting
                output = json.dumps(config_dict, indent=2)
                syntax = Syntax(output, "json", theme="monokai", line_numbers=False)
                console.print(syntax)
                return CommandResult.success_result(
                    "Configuration displayed", data=config_dict
                )

            if str(output_format).lower() == OutputFormat.YAML:
                if hasattr(args, "output") and args.output:
                    # Use shared output handling
                    return CommandResult.success_result(
                        "Configuration retrieved", data=config_dict
                    )
                # Direct console output with syntax highlighting
                output = yaml.dump(
                    config_dict, default_flow_style=False, sort_keys=False
                )
                syntax = Syntax(output, "yaml", theme="monokai", line_numbers=False)
                console.print(syntax)
                return CommandResult.success_result("Configuration displayed")

            if output_format == "table":
                self._display_config_table(config_dict)
                return CommandResult.success_result("Configuration displayed")

            # text format
            self._display_config_table(config_dict)
            return CommandResult.success_result("Configuration displayed")

        except Exception as e:
            self.logger.error(f"Configuration view error: {e}", exc_info=True)

            if self._is_structured_format(self._get_output_format(args)):
                return CommandResult.error_result(
                    f"Failed to view configuration: {e}", data={"exception": str(e)}
                )
            console.print(f"[red]Failed to view configuration: {e}[/red]")
            return CommandResult.error_result(f"Failed to view configuration: {e}")

    def _show_config_status(self, args) -> CommandResult:
        """Show configuration status and health."""
        try:
            # Load configuration
            config_file = getattr(args, "config_file", None)
            config = Config(config_file=config_file)

            # Get status
            status = config.get_configuration_status()

            # Handle output format
            output_format = self._get_output_format(args)

            if self._is_structured_format(output_format):
                # Structured output
                result_data = status.copy()

                # Add response logging details if requested
                if getattr(args, "check_response_logging", False):
                    result_data["response_logging_config"] = config.get(
                        "response_logging", {}
                    )

                if status["valid"]:
                    return CommandResult.success_result(
                        "Configuration status retrieved", data=result_data
                    )
                return CommandResult.error_result(
                    "Configuration has issues", data=result_data
                )

            # Rich console output for text format
            self._display_status_panel(status)

            # Show detailed errors/warnings if verbose
            if getattr(args, "verbose", False):
                self._display_detailed_status(status)

            # Check response logging specifically
            if getattr(args, "check_response_logging", False):
                self._display_response_logging_config(config)

            return (
                CommandResult.success_result("Configuration status displayed")
                if status["valid"]
                else CommandResult.error_result("Configuration has issues")
            )

        except Exception as e:
            self.logger.error(f"Configuration status error: {e}", exc_info=True)

            if self._is_structured_format(self._get_output_format(args)):
                return CommandResult.error_result(
                    f"Failed to get configuration status: {e}",
                    data={"exception": str(e)},
                )
            console.print(f"[red]Failed to get configuration status: {e}[/red]")
            return CommandResult.error_result(
                f"Failed to get configuration status: {e}"
            )

    def _display_status_panel(self, status: Dict[str, Any]) -> None:
        """Display configuration status panel."""
        panel_content = []

        # Basic info
        panel_content.append("[bold]Configuration Status[/bold]")
        panel_content.append(f"Valid: {'✓' if status.get('valid', False) else '✗'}")
        panel_content.append(f"Loaded from: {status.get('loaded_from', 'defaults')}")
        panel_content.append(f"Total keys: {status.get('key_count', 'unknown')}")

        # Feature status (only if available)
        if "response_logging_enabled" in status or "memory_enabled" in status:
            panel_content.append("\n[bold]Features:[/bold]")
            if "response_logging_enabled" in status:
                panel_content.append(
                    f"Response Logging: {'✓ Enabled' if status['response_logging_enabled'] else '✗ Disabled'}"
                )
            if "memory_enabled" in status:
                panel_content.append(
                    f"Memory System: {'✓ Enabled' if status['memory_enabled'] else '✗ Disabled'}"
                )

        # Errors and warnings (only if available)
        if status.get("errors"):
            panel_content.append(f"\n[red]Errors: {len(status['errors'])}[/red]")
        if status.get("warnings"):
            panel_content.append(
                f"\n[yellow]Warnings: {len(status['warnings'])}[/yellow]"
            )

        # Display panel
        panel = Panel(
            "\n".join(panel_content),
            title="Configuration Status",
            border_style="green" if status.get("valid", False) else "red",
        )
        console.print(panel)

    def _display_detailed_status(self, status: Dict[str, Any]) -> None:
        """Display detailed errors and warnings."""
        if status.get("errors"):
            console.print("\n[bold red]Errors:[/bold red]")
            for error in status["errors"]:
                console.print(f"  [red]• {error}[/red]")

        if status.get("warnings"):
            console.print("\n[bold yellow]Warnings:[/bold yellow]")
            for warning in status["warnings"]:
                console.print(f"  [yellow]• {warning}[/yellow]")

    def _display_response_logging_config(self, config: Config) -> None:
        """Display response logging configuration table."""
        console.print("\n[bold]Response Logging Configuration:[/bold]")
        rl_config = config.get("response_logging", {})

        table = Table(show_header=True)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Enabled", str(rl_config.get("enabled", False)))
        table.add_row("Format", rl_config.get("format", "json"))
        table.add_row("Use Async", str(rl_config.get("use_async", True)))
        table.add_row(
            "Session Directory",
            rl_config.get("session_directory", ".claude-mpm/responses"),
        )
        table.add_row("Compression", str(rl_config.get("enable_compression", False)))

        console.print(table)

    def _display_config_table(self, config_dict: dict, prefix: str = "") -> None:
        """Display configuration as a formatted table."""
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

    def _flatten_config(self, config: dict, prefix: str = "") -> dict:
        """Flatten nested configuration dictionary."""
        flattened = {}

        for key, value in config.items():
            new_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                flattened.update(self._flatten_config(value, new_key))
            elif isinstance(value, list):
                flattened[new_key] = str(value)
            else:
                flattened[new_key] = value

        return flattened

    def _show_gitignore_recommendations(self) -> None:
        """Show recommended .gitignore patterns for Claude MPM projects.

        This displays recommended gitignore patterns without making any changes
        to the user's .gitignore file. Users can choose to apply these manually.
        """
        console.print(
            "\n[bold cyan]Recommended .gitignore Patterns for Claude MPM[/bold cyan]\n"
        )

        console.print("[bold]Track agent memories, ignore runtime data:[/bold]")
        console.print("[dim]# Add this to your .gitignore:[/dim]\n")

        # The recommended gitignore block
        recommended_patterns = """# Claude MPM - Track memories, ignore runtime data
.claude-mpm/*
!.claude-mpm/memories/
.claude-mpm/memories/*
!.claude-mpm/memories/*.md"""

        # Display in a panel for clarity
        from rich.panel import Panel

        panel = Panel(
            recommended_patterns,
            title="Recommended .gitignore Patterns",
            border_style="green",
            padding=(1, 2),
        )
        console.print(panel)

        # Explanation
        console.print("\n[bold]What this does:[/bold]")
        console.print(
            "  • Track [cyan].claude-mpm/memories/*.md[/cyan] (agent memories are valuable)"
        )
        console.print(
            "  • Ignore everything else in [dim].claude-mpm/[/dim] (cache, logs, sessions, tmp)"
        )
        console.print(
            "  • Services (mcp-vector-search, kuzu-memory, etc.) handle their own .gitignore"
        )

        console.print(
            "\n[yellow]Note:[/yellow] These patterns are recommendations only."
        )
        console.print("       Add them manually to your .gitignore if desired.\n")

    def _auto_configure(self, args) -> CommandResult:
        """
        Run auto-configuration to detect toolchain and recommend agents/skills.

        This delegates to the AutoConfigureCommand for the actual implementation.
        """
        # Check if user wants gitignore recommendations
        if hasattr(args, "gitignore") and args.gitignore:
            self._show_gitignore_recommendations()
            return CommandResult.success_result("Gitignore recommendations displayed")

        try:
            # Import AutoConfigureCommand
            from .auto_configure import AutoConfigureCommand

            # Create auto-configure command instance
            auto_cmd = AutoConfigureCommand()

            # Run auto-configuration
            return auto_cmd.run(args)

        except ImportError as e:
            self.logger.error(f"AutoConfigureCommand not available: {e}")
            return CommandResult.error_result(
                "Auto-configuration feature not available. "
                "Please ensure all dependencies are installed."
            )
        except Exception as e:
            self.logger.error(f"Auto-configuration failed: {e}", exc_info=True)
            return CommandResult.error_result(f"Auto-configuration failed: {e}")


def manage_config(args) -> int:
    """Main entry point for configuration management commands.

    DEPRECATED: This function is no longer used by the CLI. The 'config' command
    is now aliased to 'configure' and launches the interactive TUI. This function
    is maintained for backward compatibility with MCP and other internal uses only.

    Use manage_configure() instead for the interactive configuration interface.

    This function maintains backward compatibility while using the new BaseCommand pattern.
    """
    command = ConfigCommand()
    result = command.execute(args)

    # Print result if not already handled
    if _is_structured_output(args):
        command.print_result(result, args)

    return result.exit_code


# Legacy function for backward compatibility
def validate_config(args) -> int:
    """Legacy function for backward compatibility."""
    command = ConfigCommand()
    result = command.execute(args)
    return result.exit_code


def view_config(args) -> int:
    """Legacy function for backward compatibility."""
    command = ConfigCommand()
    result = command.execute(args)
    return result.exit_code


def show_config_status(args) -> int:
    """Legacy function for backward compatibility."""
    command = ConfigCommand()
    result = command.execute(args)
    return result.exit_code


def display_config_table(config_dict: dict, prefix: str = "") -> None:
    """Legacy function for backward compatibility."""
    command = ConfigCommand()
    command._display_config_table(config_dict, prefix)
