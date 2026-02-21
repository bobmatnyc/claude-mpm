# Agent Sourcing Research - Version 1

**Research Date:** February 21, 2026
**Focus:** Understanding `claude-mpm configure` agent status determination

## Quick Summary

This research folder contains analysis of how Claude MPM determines whether agents show as "Installed" or "Available" in the configuration interface.

## Files

- **`agent-status-determination-analysis.md`** - Complete technical analysis with code flow, debug output, and architectural findings

## Key Findings

### How Status Is Actually Determined

1. **Agent Discovery:** GitSourceManager scans `~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents/*.md`
2. **Status Check:** Looks for matching `.claude/agents/{agent-name}.md` files in project directory
3. **Status Assignment:**
   - **"Installed"** = Physical .md file exists in `.claude/agents/`
   - **"Available"** = No physical .md file found

### Current Runtime Behavior (vs Designed)

| Component | Designed | Actually Used |
|-----------|----------|---------------|
| Agent Discovery | Local templates + Git cache | Git cache only |
| Status Detection | Virtual deployment state | Physical .md files |

### Architecture Summary

```
Discovery: ~/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents/agents/*.md
            ↓
Status Check: .claude/agents/*.md files exist?
            ↓
Result: 15 "Installed" | 33 "Available" | 48 Total
```

## Research Context

This investigation was triggered by the question: *"What is the code flow which provides the 'Installed' vs 'Available' status information in claude-mpm configure?"*

The research revealed significant differences between the designed architecture (with virtual deployment state and dual discovery sources) and the actual runtime behavior (physical file detection with single Git source).

## Next Steps

- Investigate why virtual deployment state (`.mpm_deployment_state`) is not being used
- Determine if local JSON templates should be active
- Consider consolidating architecture to match actual usage patterns