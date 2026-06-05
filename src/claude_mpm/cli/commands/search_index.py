"""
``claude-mpm search-index`` command — manage the trusty-search opt-in allowlist.

WHAT: CLI entry point for add / list / remove operations on the trusty-search
      ``indexes.toml`` opt-in allowlist.  Never auto-indexes; requires an
      explicit path argument from the user.
WHY:  trusty-search (trusty-tools#767) moves to an opt-in indexing model.
      MPM owns the tool-side write path so users have a single, safe command
      to register project roots rather than hand-editing TOML.

DENYLIST enforced on add:
  - $HOME itself
  - /tmp, /, /etc, /var
  - ~/.ssh, ~/.aws, ~/.gnupg, ~/.config/gcloud, ~/.kube, ~/.docker
  - Any directory whose top level contains a .env file

References
----------
LINK: none  (introduced by GitHub issue #668)
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from ...services.trusty_search_allowlist import (
    AllowlistWriteError,
    DeniedPathError,
    add_root,
    default_allowlist_path,
    list_roots,
    remove_root,
)

console = Console()


def add_search_index_parser(subparsers) -> None:
    """Register the ``search-index`` command group with its subcommands.

    WHAT: Adds ``search-index`` (alias ``si``) with three sub-actions:
    ``add``, ``list``, and ``remove``.  Uses argparse nested subparsers so
    the command reads naturally as ``claude-mpm search-index add <path>``.
    WHY:  Keeps the allowlist surface explicit and symmetrical with
    ``trusty-search index`` / ``trusty-search list``.
    """
    import argparse

    group_parser = subparsers.add_parser(
        "search-index",
        aliases=["si"],
        help="Manage the trusty-search opt-in index allowlist",
        description=(
            "Manage which project roots trusty-search is allowed to index.\n\n"
            "trusty-search uses an opt-in model: a directory is indexed ONLY if\n"
            "explicitly registered here.  MPM never auto-registers directories.\n\n"
            "The allowlist lives at:\n"
            f"  {default_allowlist_path()}"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Register a project root for indexing
  claude-mpm search-index add ~/Projects/my-app

  # Register with an explicit index name
  claude-mpm search-index add ~/Projects/my-app --name my-app

  # List all registered roots
  claude-mpm search-index list

  # Remove a project root
  claude-mpm search-index remove ~/Projects/my-app
""",
    )

    sub = group_parser.add_subparsers(dest="si_subcommand", metavar="SUBCOMMAND")
    sub.required = True

    # ---- add ----
    add_p = sub.add_parser(
        "add",
        help="Add a directory root to the allowlist",
        description=(
            "Register a project directory for trusty-search indexing.\n\n"
            "The path is resolved to its absolute canonical form before writing.\n"
            "Adding an already-registered root is a safe no-op (idempotent).\n\n"
            "REFUSED paths: $HOME, /tmp, /, /etc, /var, ~/.ssh, ~/.aws, ~/.gnupg,\n"
            "~/.config/gcloud, ~/.kube, ~/.docker, and any directory that contains\n"
            "a top-level .env file."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_p.add_argument("path", help="Directory to register for indexing")
    add_p.add_argument(
        "--name",
        "-n",
        dest="index_id",
        metavar="NAME",
        default=None,
        help=(
            "Override the index ID (default: directory basename). "
            "Must match [A-Za-z0-9._-]+ after sanitization."
        ),
    )
    add_p.set_defaults(func=_handle_add)

    # ---- list ----
    list_p = sub.add_parser(
        "list",
        aliases=["ls"],
        help="List all registered roots",
        description="Show all project roots currently in the trusty-search allowlist.",
    )
    list_p.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output as JSON instead of a formatted table",
    )
    list_p.set_defaults(func=_handle_list)

    # ---- remove ----
    rm_p = sub.add_parser(
        "remove",
        aliases=["rm"],
        help="Remove a directory root from the allowlist",
        description=(
            "Un-register a project directory from the trusty-search allowlist.\n"
            "The path is resolved before matching so both the raw and canonical\n"
            "forms are accepted.  No-op when the entry does not exist."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    rm_p.add_argument("path", help="Directory to remove from the allowlist")
    rm_p.set_defaults(func=_handle_remove)

    group_parser.set_defaults(func=_handle_group_default)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def _handle_group_default(args) -> int:
    """Show help when ``search-index`` is called without a subcommand."""
    # argparse sub.required=True handles this — guard is defensive.
    console.print(
        "[yellow]Usage:[/yellow] claude-mpm search-index <add|list|remove> ...\n"
        "Run [cyan]claude-mpm search-index --help[/cyan] for details."
    )
    return 1


def _handle_add(args) -> int:
    """Execute ``search-index add <path> [--name NAME]``.

    WHAT: Calls :func:`add_root` with the user-supplied path.  Prints a
    clear success or already-exists message.  On denylist or validation
    errors, prints a red error and exits with code 1.
    WHY:  All path resolution, denylist checking, and TOML writing is
    delegated to the service layer; this handler only handles I/O.
    """
    try:
        added, message = add_root(args.path, index_id=getattr(args, "index_id", None))
    except DeniedPathError as exc:
        console.print(f"[red]Denied:[/red] {exc}")
        return 1
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        return 1
    except AllowlistWriteError as exc:
        console.print(f"[red]Write error:[/red] {exc}")
        return 1

    if added:
        console.print(f"[green]Added:[/green] {message}")
        console.print(
            "[dim]Run [cyan]trusty-search index[/cyan] inside the directory "
            "to trigger the initial index build.[/dim]"
        )
    else:
        console.print(f"[yellow]Already registered:[/yellow] {message}")
    return 0


def _handle_list(args) -> int:
    """Execute ``search-index list [--json]``.

    WHAT: Reads the allowlist and renders it either as a Rich table (default)
    or as JSON (with ``--json``).  Exits with code 0 even when the list is
    empty.
    WHY:  Provides a read-only view of the allowlist without invoking the
    daemon so it works even when trusty-search is not running.
    """
    try:
        entries = list_roots()
    except AllowlistWriteError as exc:
        console.print(f"[red]Read error:[/red] {exc}")
        return 1

    if getattr(args, "output_json", False):
        import json

        console.print(json.dumps(entries, indent=2, default=str))
        return 0

    if not entries:
        console.print(
            "[yellow]No entries in the trusty-search allowlist.[/yellow]\n"
            "Use [cyan]claude-mpm search-index add <path>[/cyan] to register a project."
        )
        return 0

    table = Table(title="trusty-search opt-in allowlist", show_header=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Root path", style="white")
    table.add_column("Flags", style="dim")

    for entry in entries:
        flags_parts: list[str] = []
        if entry.get("colocated"):
            flags_parts.append("colocated")
        if entry.get("lexical_only"):
            flags_parts.append("lexical_only")
        if entry.get("skip_kg"):
            flags_parts.append("skip_kg")
        flags = ", ".join(flags_parts) if flags_parts else ""

        table.add_row(
            str(entry.get("id", "")),
            str(entry.get("root_path", "")),
            flags,
        )

    console.print(table)
    return 0


def _handle_remove(args) -> int:
    """Execute ``search-index remove <path>``.

    WHAT: Calls :func:`remove_root` with the user-supplied path.  Prints a
    success or not-found message.  On write errors exits with code 1.
    WHY:  Lets users cleanly un-register a project without hand-editing TOML.
    """
    try:
        removed, message = remove_root(args.path)
    except AllowlistWriteError as exc:
        console.print(f"[red]Write error:[/red] {exc}")
        return 1

    if removed:
        console.print(f"[green]Removed:[/green] {message}")
    else:
        console.print(f"[yellow]Not found:[/yellow] {message}")
    return 0


# ---------------------------------------------------------------------------
# Top-level dispatch (called from executor)
# ---------------------------------------------------------------------------


def handle_search_index(args) -> int:
    """Dispatch the search-index command to the appropriate subcommand handler.

    WHAT: If args carries a ``func`` attribute (set by argparse set_defaults),
    calls it; otherwise falls back to showing help.
    WHY:  Consistent with how other command handlers work in this codebase —
    argparse ``set_defaults(func=...)`` lets us avoid a manual if/elif chain.
    """
    func = getattr(args, "func", None)
    if callable(func):
        return func(args)
    return _handle_group_default(args)
