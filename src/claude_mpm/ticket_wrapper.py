#!/usr/bin/env python3
"""
Ticket module wrapper for backward compatibility.

This module provides backward compatibility for the ticket functionality
that was moved to the scripts directory.
"""

import sys
from pathlib import Path

# Add scripts directory to path so we can import the ticket module
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

# Import and re-export the main function
try:
    from ticket import main
except ImportError:
    # Fallback if direct import fails
    import importlib.util

    ticket_path = scripts_dir / "ticket.py"
    spec = importlib.util.spec_from_file_location("ticket", ticket_path)
    ticket_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ticket_module)
    main = ticket_module.main

__all__ = ["main"]
