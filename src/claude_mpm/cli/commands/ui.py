"""
UI command implementation for claude-mpm.

WHY: This module provides terminal UI functionality for users who prefer a
visual interface over command-line interaction.
"""

from ...core.logger import get_logger


def run_terminal_ui(args):
    """
    Run the terminal UI.
    
    WHY: Some users prefer a visual interface with multiple panes showing different
    aspects of the system. This command launches either a rich terminal UI or a
    basic curses UI depending on availability and user preference.
    
    DESIGN DECISION: We try the rich UI first as it provides a better experience,
    but fall back to curses if rich is not available. This ensures the UI works
    on all systems.
    
    Args:
        args: Parsed command line arguments with optional 'mode' attribute
    """
    logger = get_logger("cli")
    
    ui_mode = getattr(args, 'mode', 'terminal')
    
    try:
        if ui_mode == 'terminal':
            # Try rich UI first
            try:
                from ...ui.rich_terminal_ui import main as run_rich_ui
                logger.info("Starting rich terminal UI...")
                run_rich_ui()
            except ImportError:
                # Fallback to curses UI
                logger.info("Rich not available, falling back to curses UI...")
                from ...ui.terminal_ui import TerminalUI
                ui = TerminalUI()
                ui.run()
        else:
            # Use curses UI explicitly
            from ...ui.terminal_ui import TerminalUI
            ui = TerminalUI()
            ui.run()
    except ImportError as e:
        logger.error(f"UI module not found: {e}")
        print(f"Error: Terminal UI requires 'curses' (built-in) or 'rich' (pip install rich)")
        return 1
    except Exception as e:
        logger.error(f"Error running terminal UI: {e}")
        print(f"Error: {e}")
        return 1
    
    return 0