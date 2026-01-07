# Auto-Configuration

Auto-configuration scans your project, recommends the right agents, and deploys them for you.

## Quick Start

```bash
# Analyze and deploy (interactive)
claude-mpm auto-configure

# Preview without changes
claude-mpm auto-configure --preview

# Lower the confidence threshold
claude-mpm auto-configure --threshold 60
```

## What It Does

- Detects languages, frameworks, and tooling
- Maps findings to recommended agents
- Deploys approved agents into the project

## When to Use It

- First time setup on a new or existing project
- A stack has changed and you want updated recommendations
- You want a baseline agent set without manual selection

## Related Docs

- **User Guide**: [../user/user-guide.md](../user/user-guide.md)
- **Agent Presets**: [../user/agent-presets.md](../user/agent-presets.md)
- **Troubleshooting**: [../user/troubleshooting.md](../user/troubleshooting.md)
