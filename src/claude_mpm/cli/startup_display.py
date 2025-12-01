"""
Startup display banner for Claude MPM.

Shows welcome message, version info, ASCII art, and what's new section.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List

from claude_mpm.utils.git_analyzer import is_git_repository

# ANSI color codes
CYAN = "\033[36m"  # Cyan for header highlight (Claude Code style)
DIM = "\033[2m"  # Dim text for subtle launch message
RESET = "\033[0m"

# Banner dimension defaults (will be calculated based on terminal width)
MIN_WIDTH = 100  # Minimum banner width
MAX_WIDTH = 200  # Maximum banner width
DEFAULT_WIDTH = 160  # Default if terminal width cannot be determined


def _get_terminal_width() -> int:
    """
    Get terminal width with reasonable bounds.

    Returns:
        Terminal width (75% of actual) clamped between MIN_WIDTH and MAX_WIDTH
    """
    try:
        full_width = shutil.get_terminal_size().columns
        # Use 75% of terminal width for more compact display
        width = int(full_width * 0.75)
        # Apply reasonable bounds
        return max(MIN_WIDTH, min(width, MAX_WIDTH))
    except Exception:
        # 75% of 160 = 120
        return 120


def _get_username() -> str:
    """Get username from environment or default to 'User'."""
    return os.environ.get("USER") or os.environ.get("USERNAME") or "User"


def _get_recent_commits(max_commits: int = 3) -> List[str]:
    """
    Get recent git commits for display in startup banner.

    Args:
        max_commits: Maximum number of commits to retrieve (default: 3)

    Returns:
        List of formatted commit strings (hash • relative_time • message)
        Empty list if not a git repo or if any error occurs

    Format: "a3f5b7c • 2 hours ago • fix: resolve critical error"
    """
    try:
        # Check if we're in a git repository
        if not is_git_repository("."):
            return []

        # Run git log with custom format
        result = subprocess.run(
            ["git", "log", "--format=%h • %ar • %s", f"-{max_commits}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )

        if not result.stdout.strip():
            return []

        # Split into lines and return
        commits = [
            line.strip() for line in result.stdout.strip().split("\n") if line.strip()
        ]
        return commits[:max_commits]

    except Exception:
        # Fail silently - return empty list on any error
        # (not a git repo, git not installed, timeout, etc.)
        return []


def _strip_ansi_codes(text: str) -> str:
    """Remove ANSI color codes from text."""
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_escape.sub("", text)


def _get_display_width(text: str) -> int:
    """
    Calculate display width accounting for emojis and wide characters.

    Args:
        text: Text to measure (without ANSI codes)

    Returns:
        Display width in terminal columns
    """
    width = 0
    for char in text:
        # Emoji and wide characters take 2 columns
        if ord(char) > 0x1F000:  # Emoji range
            width += 2
        else:
            width += 1
    return width


def _parse_changelog_highlights(max_items: int = 3, max_width: int = 130) -> List[str]:
    """
    Parse CHANGELOG.md to extract highlights from latest version.

    Args:
        max_items: Maximum number of highlights to return
        max_width: Maximum width for each highlight

    Returns:
        List of formatted bullet points for display.
    """
    changelog_path = Path(__file__).parent.parent.parent.parent / "CHANGELOG.md"

    if not changelog_path.exists():
        return ["No changelog available"]

    try:
        with open(changelog_path, encoding="utf-8") as f:
            lines = f.readlines()

        # Find latest version section (skip [Unreleased])
        in_version_section = False
        highlights = []

        for i, line in enumerate(lines):
            line = line.rstrip()

            # Skip unreleased section
            if line.startswith("## [Unreleased]"):
                continue

            # Found latest version
            if line.startswith("## [") and not in_version_section:
                in_version_section = True
                continue

            # Next version section means we're done
            if line.startswith("## [") and in_version_section:
                break

            # Extract any bullet points from any section in latest version
            if in_version_section:
                # Skip section headers
                if line.startswith("###"):
                    continue

                # Extract bullet points
                if line.startswith("-"):
                    # Get first line of multi-line items
                    item = line[2:].strip()  # Remove "- " prefix

                    # Clean up markdown formatting
                    item = item.replace("**", "")  # Remove bold markers

                    # Truncate if too long
                    if len(item) > max_width:
                        item = item[: max_width - 3] + "..."

                    highlights.append(item)

                    if len(highlights) >= max_items:
                        break

        if not highlights:
            highlights = ["See CHANGELOG.md for details"]

        return highlights[:max_items]

    except Exception:
        return ["See CHANGELOG.md for details"]


def _get_alien_art() -> List[str]:
    """Return multi-alien ASCII art with teal/cyan highlighting."""
    return [
        f"{CYAN}▐▛███▜▌ ▐▛███▜▌{RESET}",  # Two aliens - Width: 15 chars
        f"{CYAN}▝▜█████▛▘▝▜█████▛▘{RESET}",  # Two aliens base - Width: 18 chars
        f"{CYAN}▘▘ ▝▝    ▘▘ ▝▝{RESET}",  # Two aliens feet - Width: 14 chars
    ]


def _format_logging_status(logging_level: str) -> str:
    """Format logging status with helpful indicator."""
    if logging_level == "OFF":
        return "Logging: OFF (default)"
    if logging_level == "DEBUG":
        return f"Logging: {logging_level} (verbose)"
    return f"Logging: {logging_level}"


def _get_cwd_display(max_width: int = 40) -> str:
    """Get current working directory, truncated if needed."""
    cwd = str(Path.cwd())

    if len(cwd) <= max_width:
        return cwd

    # Truncate from the left with ellipsis
    return "..." + cwd[-(max_width - 3) :]


def _format_two_column_line(
    left: str, right: str, left_panel_width: int, right_panel_width: int
) -> str:
    """
    Format a two-column line with precise width control.

    Args:
        left: Left panel content (will be centered in left_panel_width)
        right: Right panel content (will be left-aligned in right_panel_width)
        left_panel_width: Width of left panel in characters
        right_panel_width: Width of right panel in characters

    Returns:
        Formatted line with exact character widths
    """
    # Strip ANSI codes for width calculation
    left_display = _strip_ansi_codes(left)
    right_display = _strip_ansi_codes(right)

    # Calculate actual display width
    left_width = _get_display_width(left_display)
    right_width = _get_display_width(right_display)

    # Calculate padding for left panel (centered)
    left_padding = (left_panel_width - left_width) // 2
    right_padding = left_panel_width - left_width - left_padding

    # Format left panel with centering
    left_formatted = " " * left_padding + left + " " * right_padding

    # Format right panel (left-aligned)
    # Right panel content should exactly fill right_panel_width
    right_formatted = right + " " * (right_panel_width - right_width)

    return f"│{left_formatted}│ {right_formatted}│"


def display_startup_banner(version: str, logging_level: str) -> None:
    """
    Display startup banner with welcome message and info.

    Banner dynamically adjusts to terminal width with cyan header highlight
    (Claude Code style).

    Args:
        version: Claude MPM version string
        logging_level: Current logging level (OFF/INFO/DEBUG)
    """
    # Note: Banner is shown BEFORE "Launching Claude..." progress bar (in cli/__init__.py)
    # This ensures users see welcome message before background services start
    print()  # Empty line before banner

    # Get terminal width and calculate panel sizes
    terminal_width = _get_terminal_width()
    left_panel_width = int(terminal_width * 0.25)  # ~25% for left panel
    # -4 accounts for: 2 borders (│) + 2 column separators (│ and space)
    right_panel_width = terminal_width - left_panel_width - 4

    username = _get_username()

    # Get recent git commits for "Recent activity" section
    recent_commits = _get_recent_commits(max_commits=3)

    # Build header line with cyan highlight (Claude Code style)
    header = f"─── Claude MPM v{version} "
    header_padding = "─" * (terminal_width - len(header) - 2)  # -2 for ╭╮
    top_line = f"{CYAN}╭{header}{header_padding}╮{RESET}"

    # Build content lines (plain text, no color)
    lines = []

    # Line 1: Empty left | "Recent activity" right
    lines.append(
        _format_two_column_line(
            "", "Recent activity", left_panel_width, right_panel_width
        )
    )

    # Lines 2-4: Welcome message + commit activity (3 lines total)
    welcome_msg = f"Welcome back {username}!"

    # Truncate commits to fit right panel width (leave 2 chars margin)
    max_commit_width = right_panel_width - 2
    truncated_commits = []
    for commit in recent_commits:
        if len(commit) > max_commit_width:
            truncated_commits.append(commit[: max_commit_width - 3] + "...")
        else:
            truncated_commits.append(commit)

    # Line 2: Welcome message | First commit or "No recent activity"
    if truncated_commits:
        lines.append(
            _format_two_column_line(
                welcome_msg, truncated_commits[0], left_panel_width, right_panel_width
            )
        )
    else:
        lines.append(
            _format_two_column_line(
                welcome_msg, "No recent activity", left_panel_width, right_panel_width
            )
        )

    # Line 3: Empty left | Second commit or empty
    if len(truncated_commits) >= 2:
        lines.append(
            _format_two_column_line(
                "", truncated_commits[1], left_panel_width, right_panel_width
            )
        )
    else:
        lines.append(
            _format_two_column_line("", "", left_panel_width, right_panel_width)
        )

    # Line 4: Empty left | Third commit or empty
    if len(truncated_commits) >= 3:
        lines.append(
            _format_two_column_line(
                "", truncated_commits[2], left_panel_width, right_panel_width
            )
        )
    else:
        lines.append(
            _format_two_column_line("", "", left_panel_width, right_panel_width)
        )

    # Line 5: Empty left | separator right
    separator = "─" * right_panel_width
    lines.append(
        _format_two_column_line("", separator, left_panel_width, right_panel_width)
    )

    # Line 6: Alien art line 1 | "What's new"
    alien_art = _get_alien_art()
    lines.append(
        _format_two_column_line(
            alien_art[0], "What's new", left_panel_width, right_panel_width
        )
    )

    # Lines 7-8: More alien art | changelog highlights
    max_highlight_width = right_panel_width - 5  # Leave some margin
    highlights = _parse_changelog_highlights(max_items=3, max_width=max_highlight_width)

    if len(highlights) >= 1:
        lines.append(
            _format_two_column_line(
                alien_art[1], highlights[0], left_panel_width, right_panel_width
            )
        )
    else:
        lines.append(
            _format_two_column_line(
                alien_art[1], "", left_panel_width, right_panel_width
            )
        )

    if len(highlights) >= 2:
        lines.append(
            _format_two_column_line(
                alien_art[2], highlights[1], left_panel_width, right_panel_width
            )
        )
    else:
        lines.append(
            _format_two_column_line(
                alien_art[2], "", left_panel_width, right_panel_width
            )
        )

    # Line 9: Empty | third highlight or link
    if len(highlights) >= 3:
        lines.append(
            _format_two_column_line(
                "", highlights[2], left_panel_width, right_panel_width
            )
        )
    else:
        lines.append(
            _format_two_column_line(
                "", "/mpm-help for more", left_panel_width, right_panel_width
            )
        )

    # Line 10: Model info | separator
    separator = "─" * right_panel_width
    lines.append(
        _format_two_column_line(
            "Sonnet 4.5 · Claude MPM", separator, left_panel_width, right_panel_width
        )
    )

    # Line 11: CWD | MPM Commands header
    cwd = _get_cwd_display(left_panel_width - 2)
    lines.append(
        _format_two_column_line(
            cwd, "MPM Commands", left_panel_width, right_panel_width
        )
    )

    # Line 12: Empty | /mpm command
    lines.append(
        _format_two_column_line(
            "", "  /mpm        - MPM overview", left_panel_width, right_panel_width
        )
    )

    # Line 13: Empty | /mpm-agents command
    lines.append(
        _format_two_column_line(
            "", "  /mpm-agents - Show agents", left_panel_width, right_panel_width
        )
    )

    # Line 14: Empty | /mpm-doctor command
    lines.append(
        _format_two_column_line(
            "", "  /mpm-doctor - Run diagnostics", left_panel_width, right_panel_width
        )
    )

    # Line 15: Empty | empty
    lines.append(_format_two_column_line("", "", left_panel_width, right_panel_width))

    # Line 16: Empty | autocomplete tip
    lines.append(
        _format_two_column_line(
            "", "Type / for autocomplete", left_panel_width, right_panel_width
        )
    )

    # Build bottom line (plain text, no color)
    bottom_line = f"╰{'─' * (terminal_width - 2)}╯"

    # Print banner (only header has cyan color)
    print(top_line)
    for line in lines:
        print(line)
    print(bottom_line)
    print()  # Empty line after banner


def should_show_banner(args) -> bool:
    """
    Determine if startup banner should be displayed.

    Skip banner for: --help, --version, info, doctor, config, configure commands
    """
    # Check for help/version flags
    if hasattr(args, "help") and args.help:
        return False
    if hasattr(args, "version") and args.version:
        return False

    # Check for commands that should skip banner
    skip_commands = {"info", "doctor", "config", "configure"}
    if hasattr(args, "command") and args.command in skip_commands:
        return False

    return True
