# Show claude-mpm status and environment

Display the current status of Claude MPM including environment information, active services, and system health.

## Usage

```
/mpm-status
```

## Description

This slash command delegates to the **PM agent** to gather and display comprehensive status information about your Claude MPM environment.

## Implementation

This slash command delegates to the **PM agent** to collect status information.

When you run `/mpm-status`, the PM will:
1. Check Claude MPM version and installation
2. Verify Python environment and dependencies
3. Query active services (WebSocket server, Hook Service, Monitor)
4. Report memory system status
5. Check agent deployment status
6. Summarize current configuration

## Information Displayed

The PM agent will gather and present:

- **Claude MPM Version**: Current version and build number
- **Python Environment**: Python version, virtual environment status
- **Active Services**:
  - WebSocket server status and port
  - Hook service status
  - Monitor/dashboard status
- **Memory Usage**: Agent memory files and sizes
- **Agent Deployment**: Deployed agents and their locations
- **Configuration**: Key configuration settings
- **Project Info**: Current project directory and git status

## Expected Output

```
Claude MPM Status Report
========================

Version: v4.5.15
Python: 3.11.13
Environment: Mamba (claude-mpm)

Services:
  ✓ WebSocket Server: Running (port 8765)
  ✓ Hook Service: Active
  ✓ Monitor: Running (port 3000)

Agents Deployed: 5
  - PM (Core)
  - Engineer
  - Prompt-Engineer
  - Tester
  - Project-Organizer

Memory Files: 3 (2.4 MB)
Configuration: Valid

Project: /Users/masa/Projects/my-project
Git Status: Clean (main branch)
```

## Related Commands

- `/mpm-doctor`: Diagnose issues and run health checks
- `/mpm-config`: View or modify configuration
- `/mpm-agents`: List and manage deployed agents