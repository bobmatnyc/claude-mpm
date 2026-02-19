"""
GitHub multi-account management command.

WHY: Provides CLI interface for managing GitHub account switching and verification
in projects with multi-account setups using .gh-account file markers.

DESIGN DECISIONS:
- Subcommands: switch, verify, setup, status
- Uses rich for colored output matching claude-mpm style
- Integrates with GitHubAccountManager service
"""

from rich.console import Console
from rich.table import Table

from ...services.github import GitHubAccountManager


def add_gh_parser(subparsers):
    """Add gh command parser with subcommands."""
    parser = subparsers.add_parser(
        "gh",
        help="GitHub multi-account management",
        description="Manage GitHub account switching and verification for multi-account projects",
    )

    gh_subparsers = parser.add_subparsers(dest="gh_command", help="gh subcommands")

    # gh switch
    switch_parser = gh_subparsers.add_parser(
        "switch", help="Switch gh CLI to account specified in .gh-account file"
    )
    switch_parser.set_defaults(func=gh_switch_command)

    # gh verify
    verify_parser = gh_subparsers.add_parser(
        "verify", help="Verify GitHub setup (git config, SSH, gh CLI)"
    )
    verify_parser.set_defaults(func=gh_verify_command)

    # gh setup
    setup_parser = gh_subparsers.add_parser(
        "setup", help="Interactive setup for current project"
    )
    setup_parser.add_argument("--account", help="GitHub username")
    setup_parser.add_argument("--email", help="Git email")
    setup_parser.add_argument("--name", help="Git name")
    setup_parser.set_defaults(func=gh_setup_command)

    # gh status
    status_parser = gh_subparsers.add_parser(
        "status", help="Show current GitHub account configuration"
    )
    status_parser.set_defaults(func=gh_status_command)

    parser.set_defaults(func=gh_command)


def gh_command(args):
    """Main gh command - show help if no subcommand."""
    if not hasattr(args, "gh_command") or args.gh_command is None:
        console = Console()
        console.print("\n[yellow]No subcommand specified.[/yellow]")
        console.print("\nAvailable subcommands:")
        console.print(
            "  [cyan]switch[/cyan]  - Switch gh CLI to account in .gh-account"
        )
        console.print("  [cyan]verify[/cyan]  - Verify GitHub configuration")
        console.print(
            "  [cyan]setup[/cyan]   - Setup GitHub account for current project"
        )
        console.print("  [cyan]status[/cyan]  - Show current account status")
        console.print(
            "\nRun [cyan]claude-mpm gh <subcommand> --help[/cyan] for more info.\n"
        )
        return 1
    return 0


def gh_switch_command(args):
    """Switch gh CLI account based on .gh-account file."""
    console = Console()
    manager = GitHubAccountManager()

    # Find project root
    project_root = manager.find_project_root()
    if not project_root:
        console.print("\n[red]✗[/red] No .gh-account file found in project tree\n")
        return 1

    # Get required account
    required_account = manager.get_required_account()
    if not required_account:
        console.print(f"\n[red]✗[/red] .gh-account file at {project_root} is empty\n")
        return 1

    # Get current account
    current_account = manager.get_current_gh_account()

    if current_account == required_account:
        console.print(
            f"\n[green]✓[/green] Already using correct GitHub account: [cyan]{required_account}[/cyan]\n"
        )
        return 0

    # Switch account
    console.print(
        f"\n[yellow]→[/yellow] Switching gh CLI from [cyan]{current_account or 'unknown'}[/cyan] to [cyan]{required_account}[/cyan]..."
    )

    if manager.switch_account(required_account):
        console.print(
            f"[green]✓[/green] Now using GitHub account: [cyan]{required_account}[/cyan]\n"
        )
        return 0
    console.print(f"\n[red]✗[/red] Failed to switch to account: {required_account}")
    console.print(
        "[yellow]→[/yellow] Make sure gh CLI is authenticated with this account"
    )
    console.print("   Run: [cyan]gh auth login[/cyan]\n")
    return 1


def gh_verify_command(args):
    """Verify GitHub setup comprehensively."""
    console = Console()
    manager = GitHubAccountManager()

    console.print("\n[bold]GitHub Multi-Account Setup Verification[/bold]")
    console.print("=" * 50 + "\n")

    results = manager.verify_setup()
    all_passed = True

    # Project configuration
    console.print("[bold]1. Project Configuration[/bold]")
    if results["project_root"]:
        console.print(f"[green]✓[/green] Project root: {results['project_root']}")
        console.print(f"[green]✓[/green] .gh-account file: {results['expected_user']}")
    else:
        console.print("[red]✗[/red] .gh-account file not found")
        all_passed = False
    console.print()

    # Git configuration
    console.print("[bold]2. Git Configuration[/bold]")
    git_config = results["git_config"]

    for key, data in git_config.items():
        if data["valid"]:
            console.print(f"[green]✓[/green] {key}: {data['value']}")
        else:
            console.print(f"[red]✗[/red] {key}: {data['value'] or 'not set'}")
            all_passed = False
    console.print()

    # SSH connection
    console.print("[bold]3. SSH Connection[/bold]")
    ssh = results["ssh"]
    if ssh["authenticated"]:
        if ssh["valid"]:
            console.print(f"[green]✓[/green] SSH authenticates as: {ssh['user']}")
        else:
            console.print(
                f"[red]✗[/red] SSH authenticates as: {ssh['user']} (expected: {results['expected_user']})"
            )
            all_passed = False
    else:
        console.print("[red]✗[/red] SSH authentication failed")
        all_passed = False
    console.print()

    # gh CLI
    console.print("[bold]4. gh CLI Configuration[/bold]")
    gh_cli = results["gh_cli"]
    if gh_cli["authenticated"]:
        if gh_cli["valid"]:
            console.print(f"[green]✓[/green] gh CLI authenticates as: {gh_cli['user']}")
        else:
            console.print(
                f"[red]✗[/red] gh CLI authenticates as: {gh_cli['user']} (expected: {results['expected_user']})"
            )
            console.print("[yellow]→[/yellow] Run: [cyan]claude-mpm gh switch[/cyan]")
            all_passed = False
    else:
        console.print("[red]✗[/red] gh CLI authentication failed")
        console.print("[yellow]→[/yellow] Run: [cyan]gh auth login[/cyan]")
        all_passed = False
    console.print()

    # Summary
    console.print("=" * 50)
    if all_passed:
        console.print("[green]✓ All checks passed![/green]\n")
        return 0
    console.print("[red]✗ Some checks failed[/red]")
    console.print("[yellow]→[/yellow] See failures above and run suggested fixes.\n")
    return 1


def gh_setup_command(args):
    """Interactive setup for current project."""
    console = Console()
    manager = GitHubAccountManager()

    console.print("\n[bold]GitHub Multi-Account Setup[/bold]\n")

    # Get or prompt for account
    if not args.account:
        account = console.input("[cyan]GitHub username:[/cyan] ")
    else:
        account = args.account

    if not args.email:
        email = console.input("[cyan]Git email:[/cyan] ")
    else:
        email = args.email

    if not args.name:
        name = console.input("[cyan]Git name:[/cyan] ")
    else:
        name = args.name

    # Create .gh-account file
    project_dir = manager.project_dir
    gh_account_file = project_dir / ".gh-account"

    try:
        gh_account_file.write_text(account + "\n")
        console.print(f"\n[green]✓[/green] Created .gh-account file: {account}")
    except Exception as e:
        console.print(f"\n[red]✗[/red] Failed to create .gh-account file: {e}\n")
        return 1

    # Configure git
    import subprocess  # nosec B404

    try:
        subprocess.run(["git", "config", "user.email", email], check=True)  # nosec B603 B607
        console.print(f"[green]✓[/green] Set git user.email: {email}")

        subprocess.run(["git", "config", "user.name", name], check=True)  # nosec B603 B607
        console.print(f"[green]✓[/green] Set git user.name: {name}")

        subprocess.run(["git", "config", "github.user", account], check=True)  # nosec B603 B607
        console.print(f"[green]✓[/green] Set git github.user: {account}")
    except Exception as e:
        console.print(f"\n[red]✗[/red] Failed to configure git: {e}\n")
        return 1

    # Switch gh CLI account
    console.print(f"\n[yellow]→[/yellow] Switching gh CLI to {account}...")
    if manager.switch_account(account):
        console.print(f"[green]✓[/green] gh CLI switched to: {account}")
    else:
        console.print("[red]✗[/red] Failed to switch gh CLI account")
        console.print("[yellow]→[/yellow] You may need to authenticate first:")
        console.print("   Run: [cyan]gh auth login[/cyan]")

    console.print("\n[green]✓ Setup complete![/green]\n")
    return 0


def gh_status_command(args):
    """Show current GitHub account status."""
    console = Console()
    manager = GitHubAccountManager()

    # Get current state
    project_root = manager.find_project_root()
    required_account = manager.get_required_account()
    current_gh_account = manager.get_current_gh_account()

    # Create status table
    table = Table(
        title="GitHub Account Status", show_header=True, header_style="bold cyan"
    )
    table.add_column("Configuration", style="dim")
    table.add_column("Value", style="white")
    table.add_column("Status", justify="center")

    # Project configuration
    if project_root:
        table.add_row("Project Root", str(project_root), "[green]✓[/green]")
        table.add_row(
            "Required Account",
            required_account or "Not set",
            "[green]✓[/green]" if required_account else "[red]✗[/red]",
        )
    else:
        table.add_row("Project Root", "Not found", "[red]✗[/red]")
        table.add_row("Required Account", "N/A", "[dim]—[/dim]")

    # Current gh CLI account
    if current_gh_account:
        matches = required_account and current_gh_account == required_account
        status = "[green]✓[/green]" if matches else "[yellow]⚠[/yellow]"
        table.add_row("Current gh Account", current_gh_account, status)
    else:
        table.add_row("Current gh Account", "Not authenticated", "[red]✗[/red]")

    console.print()
    console.print(table)
    console.print()

    # Show action if mismatch
    if (
        required_account
        and current_gh_account
        and required_account != current_gh_account
    ):
        console.print("[yellow]⚠ Account mismatch detected[/yellow]")
        console.print(
            f"Run [cyan]claude-mpm gh switch[/cyan] to switch to {required_account}\n"
        )

    return 0


def manage_gh(args):
    """Entry point for gh command (used by CLI routing)."""
    # If a subcommand was specified, call its function directly
    if hasattr(args, "func") and args.func != gh_command:
        return args.func(args)
    # Otherwise, show help for gh command
    return gh_command(args)
