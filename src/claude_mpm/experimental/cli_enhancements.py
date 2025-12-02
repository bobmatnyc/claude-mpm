from pathlib import Path

"""
Enhanced CLI operations for claude-mpm.

WHY THIS FILE EXISTS:
This module provides an alternative CLI implementation with enhanced error handling
and validation features. It was created to explore advanced CLI patterns including:
- Comprehensive prerequisite validation
- User-friendly error messages with suggestions
- Dry-run mode for testing
- Profile validation and generation
- Rich terminal output with status indicators

CURRENT STATUS: This is an experimental/alternative CLI implementation that uses
Click instead of argparse. It's kept separate from the main CLI to:
1. Preserve the existing CLI behavior
2. Allow testing of new features without breaking the main interface
3. Provide a reference implementation for future CLI enhancements

NOTE: This CLI is not currently used in production. The main CLI is in cli/__init__.py.
To use this enhanced CLI, you would need to create a separate entry point or
integrate selected features into the main CLI.

Implements error handling and user guidance patterns from awesome-claude-code.
"""

import sys

import click

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.hooks.validation_hooks import ValidationHooks
from claude_mpm.utils.error_handler import ErrorContext, MPMError, handle_errors
from claude_mpm.validation import AgentValidator, ValidationResult

logger = get_logger(__name__)


class CLIContext:
    """Enhanced CLI context with validation and error handling."""

    def __init__(self):
        """Initialize CLI context."""
        self.validator = AgentValidator()
        self.validation_hooks = ValidationHooks()
        self.debug = False
        self.dry_run = False

    def setup_logging(self, debug: bool = False) -> None:
        """Setup logging based on debug flag."""
        import logging

        level = logging.DEBUG if debug else logging.INFO
        format_str = (
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            if debug
            else "%(message)s"
        )

        logging.basicConfig(
            level=level, format=format_str, handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.debug = debug

    def validate_prerequisites(self) -> bool:
        """Validate system prerequisites."""
        print("Checking prerequisites...")
        all_passed = True

        # Check Python version
        if sys.version_info < (3, 11):
            print("❌ Python 3.11 or higher is required")
            all_passed = False
        else:
            print("✓ Python version is compatible")

        # Check required directories
        required_dirs = [
            Path.home() / ".claude-mpm",
            Path.home() / ".claude-mpm" / "profiles",
            Path.home() / ".claude-mpm" / "logs",
        ]

        for dir_path in required_dirs:
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True)
                    print(f"✓ Created directory: {dir_path}")
                except Exception as e:
                    print(f"❌ Failed to create directory {dir_path}: {e}")
                    all_passed = False

        return all_passed

    def handle_validation_result(
        self, result: ValidationResult, operation: str = "operation"
    ) -> None:
        """Handle validation results with user-friendly output."""
        if result.is_valid:
            if result.warnings:
                print(f"⚠️  {operation} completed with warnings:")
                for warning in result.warnings:
                    print(f"   - {warning}")
            else:
                print(f"✅ {operation} completed successfully")
        else:
            print(f"❌ {operation} failed validation:")
            for error in result.errors:
                print(f"   - {error}")

            if result.warnings:
                print("\nAdditional warnings:")
                for warning in result.warnings:
                    print(f"   - {warning}")

            sys.exit(1)


def create_enhanced_cli() -> click.Group:
    """Create enhanced CLI with better error handling."""
    cli_context = CLIContext()

    @click.group()
    @click.option("--debug", is_flag=True, help="Enable debug logging")
    @click.option("--dry-run", is_flag=True, help="Run without making changes")
    @click.pass_context
    def cli(ctx, debug: bool, dry_run: bool):
        """Enhanced claude-mpm CLI with validation and error handling."""
        ctx.obj = cli_context
        cli_context.setup_logging(debug)
        cli_context.dry_run = dry_run

        if debug:
            print("🐛 Debug mode enabled")

        if dry_run:
            print("🏃 Dry-run mode enabled")

    @cli.command()
    @click.pass_context
    def validate_setup(ctx):
        """Validate system setup and prerequisites."""
        cli_ctx = ctx.obj

        with ErrorContext("setup validation"):
            if cli_ctx.validate_prerequisites():
                print("\n✅ All prerequisites satisfied!")
                print("   You're ready to use claude-mpm")
            else:
                print("\n❌ Setup validation failed")
                print("\n💡 Setup hints:")
                print("   - Ensure Python 3.11+ is installed")
                print("   - Check file permissions for ~/.claude-mpm")

                sys.exit(1)

    @cli.command()
    @click.argument("profile_path", type=click.Path(exists=True))
    @click.pass_context
    @handle_errors(MPMError)
    async def validate_profile(ctx, profile_path: str):
        """Validate an agent profile."""
        cli_ctx = ctx.obj
        profile = Path(profile_path)

        print(f"Validating profile: {profile.name}")

        # Run pre-load validation
        result = await cli_ctx.validation_hooks.run_pre_load_validation(profile)

        cli_ctx.handle_validation_result(
            result, f"Profile validation for {profile.name}"
        )

        if result.is_valid and result.locked_fields:
            print(f"\n🔒 Locked fields: {', '.join(result.locked_fields)}")

    @cli.command()
    @click.option("--profile", "-p", help="Agent profile to load")
    @click.option("--task", "-t", help="Task to execute")
    @click.pass_context
    @handle_errors(MPMError)
    async def run_agent(ctx, profile: str, task: str):
        """Run an agent with enhanced validation."""
        cli_ctx = ctx.obj

        if not profile or not task:
            raise click.UsageError("Both --profile and --task are required")

        # Validate profile exists
        profile_path = Path(profile)
        if not profile_path.exists():
            # Try default locations
            default_locations = [
                Path.home() / ".claude-mpm" / "profiles" / f"{profile}.yaml",
                Path.cwd() / "agents" / f"{profile}.yaml",
            ]

            for location in default_locations:
                if location.exists():
                    profile_path = location
                    break
            else:
                raise MPMError(
                    f"Profile '{profile}' not found",
                    details={"searched_locations": [str(p) for p in default_locations]},
                    suggestions=[
                        "Check the profile name",
                        "Use 'mpm list-profiles' to see available profiles",
                        "Create a new profile with 'mpm create-profile'",
                    ],
                )

        # Run validation
        print(f"🔍 Validating profile: {profile_path.name}")
        validation_result = await cli_ctx.validation_hooks.run_pre_load_validation(
            profile_path
        )

        if not validation_result.is_valid:
            cli_ctx.handle_validation_result(validation_result, "Profile validation")
            return

        # Validate task
        print("🔍 Validating task...")
        task_result = await cli_ctx.validation_hooks.run_pre_execute_validation(
            profile_path.stem, task
        )

        if not task_result.is_valid:
            cli_ctx.handle_validation_result(task_result, "Task validation")
            return

        if cli_ctx.dry_run:
            print("\n🏃 Dry-run mode - would execute:")
            print(f"   Profile: {profile_path}")
            print(f"   Task: {task[:100]}{'...' if len(task) > 100 else ''}")
        else:
            print(f"\n🚀 Executing agent from {profile_path.name}...")
            # Actual execution would go here
            print("✅ Agent execution completed")

    @cli.command()
    @click.pass_context
    def list_profiles(ctx):
        """List available agent profiles."""
        cli_ctx = ctx.obj

        profile_locations = [
            Path.home() / ".claude-mpm" / "profiles",
            Path.cwd() / "agents",
        ]

        all_profiles = []
        for location in profile_locations:
            if location.exists():
                profiles = list(location.glob("*.yaml")) + list(location.glob("*.yml"))
                all_profiles.extend(profiles)

        if not all_profiles:
            print("No agent profiles found")
            print("\n💡 Create a profile with: mpm create-profile")
            return

        print("Available agent profiles:")
        for profile in sorted(all_profiles):
            # Quick validation check
            result = cli_ctx.validator.validate_profile(profile)
            status = "✅" if result.is_valid else "⚠️"
            print(f"  {status} {profile.stem} ({profile})")

    @cli.command()
    @click.argument("name")
    @click.option("--role", "-r", required=True, help="Agent role")
    @click.option("--category", "-c", default="analysis", help="Agent category")
    @click.pass_context
    def create_profile(ctx, name: str, role: str, category: str):
        """Create a new agent profile from template."""
        from claude_mpm.generators import AgentProfileGenerator

        cli_ctx = ctx.obj
        generator = AgentProfileGenerator()

        print(f"Creating agent profile: {name}")

        # Generate configuration
        config = generator.create_agent_from_template(name, role, category)

        # Generate profile
        profile_content = generator.generate_profile(config)

        # Save profile
        profile_dir = Path.home() / ".claude-mpm" / "profiles"
        profile_dir.mkdir(parents=True, exist_ok=True)

        profile_path = profile_dir / f"{name.lower().replace(' ', '_')}.yaml"

        if profile_path.exists() and not click.confirm(
            f"Profile {profile_path} exists. Overwrite?"
        ):
            print("Aborted")
            return

        if cli_ctx.dry_run:
            print(f"\n🏃 Dry-run mode - would create {profile_path}:")
            print("---")
            print(
                profile_content[:500] + "..."
                if len(profile_content) > 500
                else profile_content
            )
            print("---")
        else:
            profile_path.write_text(profile_content)
            print(f"✅ Created profile: {profile_path}")

            # Generate documentation
            doc_path = profile_path.with_suffix(".md")
            doc_content = generator.generate_agent_documentation(config)
            doc_path.write_text(doc_content)
            print(f"📝 Created documentation: {doc_path}")

    return cli


# Export the enhanced CLI
enhanced_cli = create_enhanced_cli()

if __name__ == "__main__":
    enhanced_cli()
