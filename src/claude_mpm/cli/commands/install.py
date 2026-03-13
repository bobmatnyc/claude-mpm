"""
Install command for claude-mpm features.

Subcommands:
  lsp   - Install language server(s) for the current project

WHY: Provides a unified entry point for installing optional features such as
     LSP (Language Server Protocol) support, which requires detecting the project
     language and installing the appropriate binaries and Claude Code plugins.

DESIGN DECISIONS:
- Detect languages from files present in CWD; multiple languages are supported.
- Use shutil.which() to check for already-installed binaries before reinstalling.
- subprocess.run() is used with inherited stdio so binary install output shows live.
- Settings are modified via read-modify-write to preserve existing user config.
- Rich console for output, matching the style of other claude-mpm commands.
"""

import json
import shutil
import subprocess  # nosec B404
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()

# ---------------------------------------------------------------------------
# Language detection configuration
# ---------------------------------------------------------------------------

# Each entry describes one language the installer understands.
#
# Fields:
#   detect_files    - list of glob patterns (relative to CWD) whose presence
#                     indicates this language
#   binary_check    - name of the binary to check with shutil.which()
#   install_cmd     - shell command (as list) to install the language server
#   plugin          - plugin spec passed to `claude plugin install`
#   language_label  - human-readable label shown in output
#
# Detection priority: Rust -> Go -> Java -> TypeScript -> JavaScript -> Python

LANGUAGE_CONFIGS: list[dict] = [
    {
        "name": "rust",
        "language_label": "Rust",
        "detect_files": ["Cargo.toml"],
        "binary_check": "rust-analyzer",
        "install_cmd": ["rustup", "component", "add", "rust-analyzer"],
        "plugin": "rust-analyzer@claude-code-lsps",
    },
    {
        "name": "go",
        "language_label": "Go",
        "detect_files": ["go.mod"],
        "binary_check": "gopls",
        "install_cmd": ["go", "install", "golang.org/x/tools/gopls@latest"],
        "plugin": "gopls@claude-code-lsps",
    },
    {
        "name": "java",
        "language_label": "Java",
        "detect_files": ["pom.xml", "build.gradle"],
        "binary_check": "jdtls",
        "install_cmd": ["brew", "install", "jdtls"],
        "plugin": "jdtls@claude-code-lsps",
    },
    {
        "name": "typescript",
        "language_label": "TypeScript",
        # TypeScript requires BOTH tsconfig.json AND package.json
        "detect_files": ["tsconfig.json"],
        "detect_requires_also": ["package.json"],
        "binary_check": "vtsls",
        "install_cmd": [
            "npm",
            "install",
            "-g",
            "@vtsls/language-server",
            "typescript",
        ],
        "plugin": "vtsls@claude-code-lsps",
    },
    {
        "name": "javascript",
        "language_label": "JavaScript",
        # JavaScript: package.json present but no tsconfig.json
        "detect_files": ["package.json"],
        "detect_excludes": ["tsconfig.json"],
        "binary_check": "vtsls",
        "install_cmd": [
            "npm",
            "install",
            "-g",
            "@vtsls/language-server",
            "typescript",
        ],
        "plugin": "vtsls@claude-code-lsps",
    },
    {
        "name": "python",
        "language_label": "Python",
        "detect_files": ["pyproject.toml", "setup.py", "setup.cfg"],
        "detect_glob": ["*.py"],
        "binary_check": "pyright",
        "install_cmd": ["npm", "install", "-g", "pyright"],
        "plugin": "pyright@claude-code-lsps",
    },
]


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


def detect_languages(cwd: Path) -> list[str]:
    """Detect project languages by inspecting files in cwd.

    Returns a list of language names in detection-priority order.

    Args:
        cwd: Directory to inspect (usually Path.cwd()).

    Returns:
        List of detected language names, e.g. ["python", "typescript"].
    """
    detected: list[str] = []

    for cfg in LANGUAGE_CONFIGS:
        name = cfg["name"]

        # Primary detection: any of detect_files must be present
        primary_files = cfg.get("detect_files", [])
        primary_hit = any((cwd / f).exists() for f in primary_files)

        # Glob-based detection (e.g. *.py)
        glob_patterns = cfg.get("detect_glob", [])
        glob_hit = any(bool(list(cwd.glob(pat))) for pat in glob_patterns)

        if not (primary_hit or glob_hit):
            continue  # primary signal absent

        # Additional required files (AND condition)
        also_required = cfg.get("detect_requires_also", [])
        if also_required and not all((cwd / f).exists() for f in also_required):
            continue

        # Exclusion files (if present, skip this language)
        excludes = cfg.get("detect_excludes", [])
        if excludes and any((cwd / f).exists() for f in excludes):
            continue

        detected.append(name)

    return detected


def _config_for(language: str) -> Optional[dict]:
    """Return the language config dict for a given language name, or None."""
    for cfg in LANGUAGE_CONFIGS:
        if cfg["name"] == language:
            return cfg
    return None


# ---------------------------------------------------------------------------
# Settings.json helper
# ---------------------------------------------------------------------------

CLAUDE_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"


def _set_lsp_enabled_in_settings(settings_path: Path = CLAUDE_SETTINGS_PATH) -> bool:
    """Set ENABLE_LSP_TOOL=1 in ~/.claude/settings.json under the 'env' key.

    Reads existing settings (if any), merges the value, and writes back.

    Args:
        settings_path: Path to settings.json (injectable for testing).

    Returns:
        True if settings were updated, False on error.
    """
    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        existing: dict = {}
        if settings_path.exists():
            try:
                existing = json.loads(settings_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                console.print(
                    f"[yellow]Warning: Could not parse {settings_path}, "
                    "will overwrite with minimal settings.[/yellow]"
                )

        # Merge: preserve all existing keys, add/update env.ENABLE_LSP_TOOL
        env_block = existing.get("env", {})
        if not isinstance(env_block, dict):
            env_block = {}
        env_block["ENABLE_LSP_TOOL"] = "1"
        existing["env"] = env_block

        settings_path.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return True
    except OSError as exc:
        console.print(f"[red]Error writing settings: {exc}[/red]")
        return False


# ---------------------------------------------------------------------------
# Installation helpers
# ---------------------------------------------------------------------------


def _install_binary(cfg: dict, force: bool) -> bool:
    """Install the language server binary for a language config.

    Args:
        cfg: Language config dict.
        force: If True, reinstall even if already present.

    Returns:
        True if installation succeeded (or binary already present), False on error.
    """
    binary = cfg["binary_check"]
    label = cfg["language_label"]
    cmd = cfg["install_cmd"]

    if not force and shutil.which(binary):
        console.print(
            f"  [green]Binary '[bold]{binary}[/bold]' already installed.[/green] "
            "(use --force to reinstall)"
        )
        return True

    console.print(f"  Installing [bold]{binary}[/bold] for {label}...")
    console.print(f"    Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(  # nosec B603
            cmd,
            check=False,
        )
        if result.returncode == 0:
            console.print(
                f"  [green]Binary '[bold]{binary}[/bold]' installed successfully.[/green]"
            )
            return True
        console.print(
            f"  [yellow]Warning: Binary install returned exit code "
            f"{result.returncode}.[/yellow]"
        )
        return False
    except FileNotFoundError:
        console.print(
            f"  [red]Error: Install command not found: {cmd[0]}[/red]\n"
            f"  Please ensure '{cmd[0]}' is available and retry."
        )
        return False
    except OSError as exc:
        console.print(f"  [red]Error running install command: {exc}[/red]")
        return False


def _install_plugin(cfg: dict) -> bool:
    """Install the Claude Code plugin for a language config.

    Runs: claude plugin install <plugin>

    Args:
        cfg: Language config dict.

    Returns:
        True if plugin installation succeeded, False on error.
    """
    plugin = cfg["plugin"]
    label = cfg["language_label"]
    cmd = ["claude", "plugin", "install", plugin]

    console.print(
        f"  Installing Claude Code plugin [bold]{plugin}[/bold] for {label}..."
    )

    claude_bin = shutil.which("claude")
    if not claude_bin:
        console.print(
            "  [yellow]Warning: 'claude' binary not found in PATH. "
            "Skipping plugin installation.[/yellow]\n"
            "  Install Claude Code CLI and re-run to install plugins."
        )
        return False

    try:
        result = subprocess.run(  # nosec B603
            cmd,
            check=False,
        )
        if result.returncode == 0:
            console.print(
                f"  [green]Plugin '[bold]{plugin}[/bold]' installed successfully.[/green]"
            )
            return True
        console.print(
            f"  [yellow]Warning: Plugin install returned exit code "
            f"{result.returncode}.[/yellow]"
        )
        return False
    except OSError as exc:
        console.print(f"  [red]Error running plugin install: {exc}[/red]")
        return False


# ---------------------------------------------------------------------------
# LSP subcommand handler
# ---------------------------------------------------------------------------


def _install_lsp(args) -> int:
    """Handle `claude-mpm install lsp`.

    Args:
        args: Parsed CLI arguments with attributes:
            - language (str | None): override language detection
            - force (bool): reinstall even if already installed

    Returns:
        0 on success, 1 on failure.
    """
    force: bool = getattr(args, "force", False)
    language_override: Optional[str] = getattr(args, "language", None)
    cwd = Path.cwd()

    # ---- Determine which languages to install ----
    if language_override:
        langs = [language_override.lower()]
        cfg_check = _config_for(langs[0])
        if cfg_check is None:
            valid = [c["name"] for c in LANGUAGE_CONFIGS]
            console.print(
                f"[red]Unknown language '[bold]{language_override}[/bold]'.[/red]\n"
                f"Valid options: {', '.join(valid)}"
            )
            return 1
        console.print(
            f"\n[cyan]Language override:[/cyan] using [bold]{language_override}[/bold]\n"
        )
    else:
        langs = detect_languages(cwd)
        if not langs:
            console.print(
                "\n[yellow]No supported project languages detected in the current directory.[/yellow]\n"
                "Supported indicators: Cargo.toml, go.mod, pom.xml, build.gradle, "
                "tsconfig.json, package.json, pyproject.toml, setup.py, *.py\n\n"
                "Use [bold]--language[/bold] to specify a language explicitly.\n"
            )
            return 1

        label_list = ", ".join(
            (_config_for(l) or {}).get("language_label", l) for l in langs
        )
        console.print(
            f"\n[cyan]Detected language(s):[/cyan] [bold]{label_list}[/bold]\n"
        )

    # ---- Install each language ----
    any_failure = False

    for lang in langs:
        cfg = _config_for(lang)
        if cfg is None:
            continue  # Should not happen; guard anyway

        label = cfg["language_label"]
        console.print(f"[bold underline]{label} LSP[/bold underline]")

        # Step 1: Install binary
        binary_ok = _install_binary(cfg, force)
        if not binary_ok:
            console.print(
                "  [yellow]Continuing with plugin installation despite binary "
                "install failure.[/yellow]"
            )
            any_failure = True

        # Step 2: Install Claude Code plugin
        plugin_ok = _install_plugin(cfg)
        if not plugin_ok:
            any_failure = True

        # Step 3: Update settings.json
        console.print("  Updating ~/.claude/settings.json...")
        settings_ok = _set_lsp_enabled_in_settings()
        if settings_ok:
            console.print(
                "  [green]ENABLE_LSP_TOOL=1 set in ~/.claude/settings.json[/green]"
            )
        else:
            any_failure = True

        console.print()

    # ---- Final summary ----
    if any_failure:
        console.print(
            "[yellow]Some steps encountered warnings or errors. "
            "Review the output above.[/yellow]\n"
        )
    else:
        console.print("[green]LSP installation complete.[/green]\n")

    console.print(
        "[bold]Reminder:[/bold] Restart Claude Code to activate LSP support.\n"
    )

    return 1 if any_failure else 0


# ---------------------------------------------------------------------------
# Top-level install command dispatcher
# ---------------------------------------------------------------------------


def manage_install(args) -> int:
    """Dispatch install subcommands.

    Entry point called by executor.py for the 'install' command.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code (0 = success, 1 = failure).
    """
    subcommand = getattr(args, "install_command", None)

    if subcommand == "lsp":
        return _install_lsp(args)

    # No subcommand - show help
    console.print("\n[yellow]No subcommand specified.[/yellow]")
    console.print("\nAvailable subcommands:")
    console.print(
        "  [cyan]lsp[/cyan]  - Install language server(s) for the current project"
    )
    console.print(
        "\nRun [cyan]claude-mpm install <subcommand> --help[/cyan] for more info.\n"
    )
    return 1
