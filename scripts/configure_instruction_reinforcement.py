#!/usr/bin/env python3
"""
Configuration utility for instruction reinforcement system.

Allows enabling/disabling, setting injection interval, adding custom messages,
and viewing current configuration.
"""

import argparse
import json
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Any

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.config import Config
from claude_mpm.core.unified_paths import get_path_manager


def get_config_file_path() -> Path:
    """Get the path to the configuration file."""
    path_manager = get_path_manager()
    config_dir = path_manager.get_user_config_dir()

    # Try different config file names
    for filename in ["configuration.yaml", "configuration.yml"]:
        config_path = config_dir / filename
        if config_path.exists():
            return config_path

    # Default to configuration.yaml if none exist
    return config_dir / "configuration.yaml"


def load_config() -> Config:
    """Load the current configuration."""
    try:
        Config.reset_singleton()
        return Config()
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)


def load_config_file() -> Dict[str, Any]:
    """Load configuration from file, returning empty dict if none exists."""
    config_path = get_config_file_path()

    if not config_path.exists():
        return {}

    try:
        with open(config_path, "r") as f:
            if config_path.suffix == ".json":
                return json.load(f)
            else:  # YAML
                return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error reading config file {config_path}: {e}")
        return {}


def save_config_file(config_data: Dict[str, Any]) -> None:
    """Save configuration to file."""
    config_path = get_config_file_path()

    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_path, "w") as f:
            if config_path.suffix == ".json":
                json.dump(config_data, f, indent=2)
            else:  # YAML
                yaml.dump(config_data, f, default_flow_style=False, indent=2)

        print(f"✓ Configuration saved to {config_path}")
    except Exception as e:
        print(f"Error saving config file {config_path}: {e}")
        sys.exit(1)


def view_current_config():
    """View the current instruction reinforcement configuration."""
    print("🔍 Current Instruction Reinforcement Configuration")
    print("=" * 60)

    config = load_config()
    ir_config = config.get("instruction_reinforcement", {})

    if not ir_config:
        print("❌ No instruction reinforcement configuration found")
        print("   Using defaults from application")
        return

    print(f"Enabled: {ir_config.get('enabled', 'N/A')}")
    print(f"Test Mode: {ir_config.get('test_mode', 'N/A')}")
    print(f"Injection Interval: {ir_config.get('injection_interval', 'N/A')} seconds")

    test_messages = ir_config.get("test_messages", [])
    print(f"\nTest Messages ({len(test_messages)}):")
    for i, msg in enumerate(test_messages, 1):
        print(f"  {i}. {msg}")

    prod_messages = ir_config.get("production_messages", [])
    print(f"\nProduction Messages ({len(prod_messages)}):")
    for i, msg in enumerate(prod_messages, 1):
        print(f"  {i}. {msg}")

    # Show config file location
    config_path = get_config_file_path()
    if config_path.exists():
        print(f"\nConfig file: {config_path}")
    else:
        print(f"\nConfig file: {config_path} (will be created when modified)")


def enable_instruction_reinforcement(enabled: bool):
    """Enable or disable instruction reinforcement."""
    config_data = load_config_file()

    if "instruction_reinforcement" not in config_data:
        config_data["instruction_reinforcement"] = {}

    config_data["instruction_reinforcement"]["enabled"] = enabled

    save_config_file(config_data)

    status = "enabled" if enabled else "disabled"
    print(f"✓ Instruction reinforcement {status}")


def set_test_mode(test_mode: bool):
    """Set test mode for instruction reinforcement."""
    config_data = load_config_file()

    if "instruction_reinforcement" not in config_data:
        config_data["instruction_reinforcement"] = {}

    config_data["instruction_reinforcement"]["test_mode"] = test_mode

    save_config_file(config_data)

    mode = "test" if test_mode else "production"
    print(f"✓ Instruction reinforcement set to {mode} mode")


def set_injection_interval(interval: int):
    """Set the injection interval in seconds."""
    if interval < 1:
        print("❌ Injection interval must be at least 1 second")
        sys.exit(1)

    config_data = load_config_file()

    if "instruction_reinforcement" not in config_data:
        config_data["instruction_reinforcement"] = {}

    config_data["instruction_reinforcement"]["injection_interval"] = interval

    save_config_file(config_data)
    print(f"✓ Injection interval set to {interval} seconds")


def add_message(message: str, message_type: str):
    """Add a custom message to test or production messages."""
    if message_type not in ["test", "production"]:
        print("❌ Message type must be 'test' or 'production'")
        sys.exit(1)

    config_data = load_config_file()

    if "instruction_reinforcement" not in config_data:
        config_data["instruction_reinforcement"] = {}

    key = f"{message_type}_messages"
    if key not in config_data["instruction_reinforcement"]:
        config_data["instruction_reinforcement"][key] = []

    # Check if message already exists
    existing_messages = config_data["instruction_reinforcement"][key]
    if message in existing_messages:
        print(f"❌ Message already exists in {message_type} messages")
        return

    config_data["instruction_reinforcement"][key].append(message)

    save_config_file(config_data)
    print(f"✓ Added message to {message_type} messages: {message}")


def remove_message(message_index: int, message_type: str):
    """Remove a message by index from test or production messages."""
    if message_type not in ["test", "production"]:
        print("❌ Message type must be 'test' or 'production'")
        sys.exit(1)

    config_data = load_config_file()

    if "instruction_reinforcement" not in config_data:
        print(f"❌ No {message_type} messages found")
        return

    key = f"{message_type}_messages"
    messages = config_data["instruction_reinforcement"].get(key, [])

    if not messages:
        print(f"❌ No {message_type} messages found")
        return

    if message_index < 1 or message_index > len(messages):
        print(f"❌ Invalid message index. Must be between 1 and {len(messages)}")
        return

    removed_message = messages.pop(message_index - 1)

    save_config_file(config_data)
    print(f"✓ Removed {message_type} message: {removed_message}")


def reset_to_defaults():
    """Reset instruction reinforcement to default configuration."""
    config_data = load_config_file()

    # Remove instruction_reinforcement section to use defaults
    if "instruction_reinforcement" in config_data:
        del config_data["instruction_reinforcement"]

    save_config_file(config_data)
    print("✓ Instruction reinforcement reset to defaults")


def validate_configuration():
    """Validate the current configuration."""
    print("🔍 Validating Instruction Reinforcement Configuration")
    print("=" * 60)

    try:
        config = load_config()
        ir_config = config.get("instruction_reinforcement", {})

        errors = []
        warnings = []

        # Check enabled field
        enabled = ir_config.get("enabled")
        if enabled is not None and not isinstance(enabled, bool):
            errors.append(f"'enabled' must be boolean, got {type(enabled).__name__}")

        # Check test_mode field
        test_mode = ir_config.get("test_mode")
        if test_mode is not None and not isinstance(test_mode, bool):
            errors.append(
                f"'test_mode' must be boolean, got {type(test_mode).__name__}"
            )

        # Check injection_interval
        interval = ir_config.get("injection_interval")
        if interval is not None:
            if not isinstance(interval, (int, float)):
                errors.append(
                    f"'injection_interval' must be number, got {type(interval).__name__}"
                )
            elif interval < 1:
                errors.append("'injection_interval' must be at least 1 second")

        # Check message lists
        for msg_type in ["test_messages", "production_messages"]:
            messages = ir_config.get(msg_type)
            if messages is not None:
                if not isinstance(messages, list):
                    errors.append(
                        f"'{msg_type}' must be a list, got {type(messages).__name__}"
                    )
                elif not messages:
                    warnings.append(
                        f"'{msg_type}' is empty - no messages will be injected"
                    )
                else:
                    # Check message content
                    for i, msg in enumerate(messages, 1):
                        if not isinstance(msg, str):
                            errors.append(
                                f"'{msg_type}[{i}]' must be string, got {type(msg).__name__}"
                            )
                        elif not msg.strip():
                            warnings.append(
                                f"'{msg_type}[{i}]' is empty or whitespace only"
                            )

        # Report results
        if errors:
            print("❌ Configuration Errors:")
            for error in errors:
                print(f"   • {error}")

        if warnings:
            print("⚠️  Configuration Warnings:")
            for warning in warnings:
                print(f"   • {warning}")

        if not errors and not warnings:
            print("✓ Configuration is valid")

        return len(errors) == 0

    except Exception as e:
        print(f"❌ Error validating configuration: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Configure instruction reinforcement system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s view                                   # View current configuration
  %(prog)s enable                                 # Enable instruction reinforcement
  %(prog)s disable                                # Disable instruction reinforcement
  %(prog)s test-mode on                          # Enable test mode
  %(prog)s test-mode off                         # Enable production mode
  %(prog)s interval 10                           # Set injection interval to 10 seconds
  %(prog)s add-message test "[TEST] Custom msg"  # Add test message
  %(prog)s add-message prod "[PM] Production msg" # Add production message
  %(prog)s remove-message test 1                 # Remove first test message
  %(prog)s reset                                 # Reset to defaults
  %(prog)s validate                              # Validate configuration
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # View command
    subparsers.add_parser("view", help="View current configuration")

    # Enable/disable commands
    subparsers.add_parser("enable", help="Enable instruction reinforcement")
    subparsers.add_parser("disable", help="Disable instruction reinforcement")

    # Test mode command
    test_mode_parser = subparsers.add_parser(
        "test-mode", help="Set test/production mode"
    )
    test_mode_parser.add_argument(
        "mode", choices=["on", "off"], help="Enable (on) or disable (off) test mode"
    )

    # Interval command
    interval_parser = subparsers.add_parser("interval", help="Set injection interval")
    interval_parser.add_argument(
        "seconds", type=int, help="Injection interval in seconds (minimum 1)"
    )

    # Add message command
    add_parser = subparsers.add_parser("add-message", help="Add custom message")
    add_parser.add_argument(
        "type",
        choices=["test", "prod", "production"],
        help="Message type (test or production)",
    )
    add_parser.add_argument("message", help="Message text to add")

    # Remove message command
    remove_parser = subparsers.add_parser(
        "remove-message", help="Remove message by index"
    )
    remove_parser.add_argument(
        "type",
        choices=["test", "prod", "production"],
        help="Message type (test or production)",
    )
    remove_parser.add_argument(
        "index", type=int, help="Message index (starting from 1)"
    )

    # Reset command
    subparsers.add_parser("reset", help="Reset to default configuration")

    # Validate command
    subparsers.add_parser("validate", help="Validate current configuration")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "view":
            view_current_config()
        elif args.command == "enable":
            enable_instruction_reinforcement(True)
        elif args.command == "disable":
            enable_instruction_reinforcement(False)
        elif args.command == "test-mode":
            set_test_mode(args.mode == "on")
        elif args.command == "interval":
            set_injection_interval(args.seconds)
        elif args.command == "add-message":
            message_type = (
                "production" if args.type in ["prod", "production"] else "test"
            )
            add_message(args.message, message_type)
        elif args.command == "remove-message":
            message_type = (
                "production" if args.type in ["prod", "production"] else "test"
            )
            remove_message(args.index, message_type)
        elif args.command == "reset":
            reset_to_defaults()
        elif args.command == "validate":
            is_valid = validate_configuration()
            sys.exit(0 if is_valid else 1)

    except KeyboardInterrupt:
        print("\n❌ Operation cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
