#!/usr/bin/env python3
"""
Ticket Management CLI - delegates to aitrackdown.

This module provides a wrapper that delegates all ticket operations
to the aitrackdown command-line tool.
"""

import sys
import subprocess
import argparse


def main():
    """Main entry point that delegates to aitrackdown."""
    parser = argparse.ArgumentParser(
        description="Ticket management for Claude MPM (delegates to aitrackdown)",
        add_help=False
    )
    
    # Capture all arguments
    parser.add_argument('command', nargs='?', help='Command to run')
    parser.add_argument('args', nargs=argparse.REMAINDER, help='Arguments for the command')
    
    args = parser.parse_args()
    
    # Map common commands to aitrackdown equivalents
    if args.command == 'create':
        # Check if type is specified
        if any(arg in ['-t', '--type'] for arg in args.args):
            try:
                type_idx = args.args.index('-t') if '-t' in args.args else args.args.index('--type')
                if type_idx + 1 < len(args.args):
                    ticket_type = args.args[type_idx + 1]
                    # Remove type arguments
                    remaining_args = args.args[:type_idx] + args.args[type_idx + 2:]
                    
                    if ticket_type == 'epic':
                        cmd = ['aitrackdown', 'epic', 'create'] + remaining_args
                    elif ticket_type == 'issue':
                        cmd = ['aitrackdown', 'issue', 'create'] + remaining_args
                    else:
                        cmd = ['aitrackdown', 'task', 'create'] + remaining_args
                else:
                    cmd = ['aitrackdown', 'task', 'create'] + args.args
            except:
                cmd = ['aitrackdown', 'task', 'create'] + args.args
        else:
            cmd = ['aitrackdown', 'task', 'create'] + args.args
    
    elif args.command == 'list':
        cmd = ['aitrackdown', 'task', 'list'] + args.args
    
    elif args.command in ['view', 'show']:
        cmd = ['aitrackdown', 'task', 'show'] + args.args
    
    elif args.command == 'update':
        cmd = ['aitrackdown', 'task', 'update'] + args.args
    
    elif args.command == 'close':
        if args.args:
            cmd = ['aitrackdown', 'task', 'complete', args.args[0]] + args.args[1:]
        else:
            cmd = ['aitrackdown', 'task', 'complete']
    
    elif args.command in ['help', '--help', '-h', None]:
        print("Claude MPM Ticket Management (powered by aitrackdown)")
        print()
        print("Usage:")
        print("  claude-mpm-ticket create <title> [options]")
        print("  claude-mpm-ticket list [options]")
        print("  claude-mpm-ticket view <id>")
        print("  claude-mpm-ticket update <id> [options]")
        print("  claude-mpm-ticket close <id>")
        print()
        print("Examples:")
        print('  claude-mpm-ticket create "Fix bug" -p high')
        print('  claude-mpm-ticket create "New feature" -t issue')
        print('  claude-mpm-ticket create "Roadmap" -t epic')
        print('  claude-mpm-ticket list')
        print('  claude-mpm-ticket view TSK-0001')
        print()
        print("For full options, use: aitrackdown --help")
        return
    
    else:
        # Pass through to aitrackdown
        cmd = ['aitrackdown'] + ([args.command] if args.command else []) + args.args
    
    # Execute the command
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except FileNotFoundError:
        print("Error: aitrackdown not found. Please ensure ai-trackdown-pytools is installed.")
        print("Install with: pip install ai-trackdown-pytools")
        sys.exit(1)


if __name__ == "__main__":
    main()