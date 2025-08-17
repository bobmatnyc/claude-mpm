from pathlib import Path

# \!/usr/bin/env python3
"""
Ticket CLI module for claude-mpm.

This module provides the entry point for the 'ticket' alias command.
It delegates to the scripts/ticket.py module for implementation.
"""

import sys


def main():
    """Main entry point for ticket CLI alias."""
    # Import and run the main ticket CLI
    try:
        # Try to import from scripts
        scripts_dir = Path(__file__).parent.parent.parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))

        from ticket import main as ticket_main

        return ticket_main()
    except ImportError:
        print("Error: Ticket functionality not available")
        print("Install ai-trackdown-pytools: pip install ai-trackdown-pytools")
        return 1
    except Exception as e:
        print(f"Error running ticket command: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
