"""Shared questionary styles for consistent TUI across Claude MPM.

This module provides unified styling for all interactive questionary interfaces
to ensure visual consistency across agent wizard, skill selector, and other TUI components.
"""

from questionary import Style

# Standard cyan-themed style for all selectors
# Matches the pattern used in agent_wizard.py and skill_selector.py
MPM_STYLE = Style(
    [
        ("qmark", "fg:cyan bold"),
        ("question", "bold"),
        ("answer", "fg:cyan"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan bold"),
        ("selected", "fg:cyan"),
    ]
)

# Banner constants for consistent formatting
BANNER_WIDTH = 60
BANNER_CHAR = "="


def print_banner(title: str, width: int = BANNER_WIDTH) -> None:
    """Print a styled banner matching agent selector format.

    Args:
        title: Title text to display in the banner
        width: Total width of the banner in characters (default: 60)

    Example:
        >>> print_banner("Agent Creation Wizard")
        ============================================================
                        Agent Creation Wizard
        ============================================================
    """
    print()
    print(BANNER_CHAR * width)
    print(f"{title:^{width}}")
    print(BANNER_CHAR * width)
    print()


def print_section_header(emoji: str, title: str, width: int = BANNER_WIDTH) -> None:
    """Print a section header with emoji and title.

    Args:
        emoji: Emoji to display before the title
        title: Section title text
        width: Total width of the header line (default: 60)

    Example:
        >>> print_section_header("🔧", "Agent Management Menu")

        ============================================================
        🔧  Agent Management Menu
        ============================================================
    """
    print()
    print(BANNER_CHAR * width)
    print(f"{emoji}  {title}")
    print(BANNER_CHAR * width)
