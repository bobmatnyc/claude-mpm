"""
Parser for the 'install' command.

WHY: Follows the same pattern as other subparsers (e.g. setup_parser, tools_parser)
     so that the install command integrates cleanly into the CLI.
"""

from ..commands.install import LANGUAGE_CONFIGS


def add_install_subparser(subparsers) -> None:
    """Register the 'install' command and its subcommands with the main parser.

    Args:
        subparsers: The subparsers action from the main ArgumentParser.
    """
    install_parser = subparsers.add_parser(
        "install",
        help="Install optional features (e.g. language server support)",
        description=(
            "Install optional claude-mpm features.\n\n"
            "Subcommands:\n"
            "  lsp   Install language server binary + Claude Code plugin for the current project"
        ),
    )

    install_subparsers = install_parser.add_subparsers(
        dest="install_command",
        help="Feature to install",
    )

    # ---- lsp subcommand ----
    valid_languages = [cfg["name"] for cfg in LANGUAGE_CONFIGS]

    lsp_parser = install_subparsers.add_parser(
        "lsp",
        help="Install language server(s) for the current project",
        description=(
            "Auto-detect project language(s) from the current directory and install:\n"
            "  - Language server binary (e.g. pyright, gopls, rust-analyzer)\n"
            "  - Claude Code plugin (via 'claude plugin install')\n"
            "  - ENABLE_LSP_TOOL=1 in ~/.claude/settings.json\n\n"
            "Detection priority: Rust -> Go -> Java -> TypeScript -> JavaScript -> Python\n"
            "If multiple languages are detected, all are installed."
        ),
    )

    lsp_parser.add_argument(
        "--language",
        "-l",
        choices=valid_languages,
        metavar="LANG",
        help=(
            f"Override language detection. Valid values: {', '.join(valid_languages)}"
        ),
    )

    lsp_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Reinstall binary even if already installed",
    )

    install_parser.set_defaults(func=None)
