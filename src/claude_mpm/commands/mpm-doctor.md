# Run diagnostic checks on claude-mpm installation

Run comprehensive diagnostic checks on your Claude MPM installation to identify and fix common issues.

This command checks:
- Installation integrity
- Configuration validity
- WebSocket connectivity
- Agent deployment status
- Memory system health
- Hook service status

Usage: /mpm-doctor [options]

Options:
- --verbose: Show detailed output
- --no-color: Disable colored output  
- --checks [list]: Run specific checks only
- --fix: Attempt to fix identified issues

Examples:
- /mpm-doctor
- /mpm-doctor --verbose
- /mpm-doctor --fix