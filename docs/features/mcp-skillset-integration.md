# MCP-Skillset Integration

## Overview

mcp-skillset is an optional user-level MCP server that provides RAG-powered skill recommendations for Claude MPM. This document describes the integration and usage.

## Installation

mcp-skillset is installed as a **USER-LEVEL** MCP server (not project-specific), making it available across all Claude Code projects.

### Setup Command

```bash
# Install and configure mcp-skillset (user-level)
claude-mpm setup mcp-skillset

# Force reinstall
claude-mpm setup mcp-skillset --force
```

### What Happens During Setup

1. **Installation**: mcp-skillset is installed via your detected package manager (uv, pipx, or pip)
2. **Configuration**: Added to Claude Desktop config at:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%/Claude/claude_desktop_config.json`
3. **Scope**: Available to ALL projects (not project-specific)

### Configuration Location

**USER-LEVEL (Claude Desktop config):**
```json
{
  "mcpServers": {
    "mcp-skillset": {
      "type": "stdio",
      "command": "mcp-skillset",
      "args": ["mcp"],
      "env": {}
    }
  }
}
```

**NOT in project `.mcp.json`** - This is intentional. mcp-skillset provides cross-project skill recommendations.

## Integration with Skills Optimize

The `claude-mpm skills optimize` command can optionally query mcp-skillset for enhanced recommendations.

### Basic Usage

```bash
# Default: Use local manifest only
claude-mpm skills optimize

# Query mcp-skillset for RAG-powered recommendations
claude-mpm skills optimize --use-mcp-skillset
```

### With Additional Options

```bash
# Query mcp-skillset and auto-deploy recommendations
claude-mpm skills optimize --use-mcp-skillset --auto-deploy

# Query mcp-skillset with priority filter
claude-mpm skills optimize --use-mcp-skillset --priority critical

# Query mcp-skillset with max skills limit
claude-mpm skills optimize --use-mcp-skillset --max-skills 5
```

## How It Works

### Without mcp-skillset

1. `claude-mpm skills optimize` detects project technology stack
2. Recommends skills from local manifest (bobmatnyc/claude-mpm-skills)
3. Matches based on static tags and priority

### With mcp-skillset

1. `claude-mpm skills optimize --use-mcp-skillset` detects technology stack
2. **Queries mcp-skillset MCP tool** for RAG-powered recommendations
3. Combines results with local manifest
4. Enhanced matching based on semantic similarity

## Skills Manifest in mcp-skillset

The mcp-skillset MCP server provides:

- **MCP Tool**: `query_skills_manifest`
- **Input**: Technology stack (languages, frameworks, tools)
- **Output**: Skill recommendations with relevance scores
- **Source**: Claude MPM Skills repository (bobmatnyc/claude-mpm-skills)

### Expected Manifest Structure

```json
{
  "version": "1.0",
  "repositories": [
    {
      "url": "https://github.com/bobmatnyc/claude-mpm-skills",
      "priority": 1,
      "description": "Official Claude MPM skills repository"
    }
  ],
  "skills": [
    {
      "name": "toolchains-python-core",
      "source": "claude-mpm-skills",
      "category": "toolchains/python",
      "priority": 100,
      "triggers": ["*.py", "pyproject.toml"],
      "tags": ["python", "backend"],
      "description": "Python core development patterns"
    }
  ]
}
```

## Benefits

### User-Level Installation
- Install once, use everywhere
- No per-project configuration needed
- Consistent across all Claude Code sessions

### RAG-Powered Recommendations
- Semantic matching beyond static tags
- Context-aware suggestions
- Better discovery of relevant skills

### Fallback Behavior
- If mcp-skillset is unavailable: Falls back to local manifest
- If MCP query fails: Continues with local recommendations
- No disruption to existing workflow

## Comparison: User-Level vs Project-Level

| Aspect | mcp-skillset (USER-LEVEL) | mcp-vector-search (PROJECT-LEVEL) |
|--------|---------------------------|-------------------------------------|
| Config Location | Claude Desktop config | Project `.mcp.json` |
| Scope | All projects | Single project |
| Purpose | Skill recommendations | Code semantic search |
| Setup Command | `claude-mpm setup mcp-skillset` | `claude-mpm setup mcp-vector-search` |
| Deployment | One-time user-level | Per-project |

## Troubleshooting

### mcp-skillset not found

```bash
# Verify installation
which mcp-skillset

# Reinstall
claude-mpm setup mcp-skillset --force
```

### MCP tool not available

1. Restart Claude Code to reload MCP servers
2. Verify Claude Desktop config contains mcp-skillset entry
3. Check MCP server status in Claude Code (🔌 menu)

### Recommendations not enhanced

- Verify `--use-mcp-skillset` flag is used
- Check that mcp-skillset is loaded in Claude Code
- MCP integration requires Claude Code with MCP support

## Future Enhancements

Potential future improvements:

1. **Automatic Manifest Updates**: mcp-skillset could sync with bobmatnyc/claude-mpm-skills automatically
2. **Custom Repositories**: Support for additional skill repositories beyond official
3. **Usage Analytics**: Track which skills are most useful for which stacks
4. **Collaborative Filtering**: Learn from community skill usage patterns

## Related Documentation

- [Skills Optimization](../commands/skills-optimize.md)
- [MCP Server Setup](../setup/mcp-servers.md)
- [Skills Repository](https://github.com/bobmatnyc/claude-mpm-skills)
