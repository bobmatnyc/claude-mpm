# Show available agents and their versions

Show all available Claude MPM agents with their versions and deployment status.

## Usage

```
/mpm-agents
```

## Description

This command lists all available Claude MPM agents, including both built-in agents and any custom agents you've created. It shows their current deployment status, version information, and capabilities.

## What This Command Does

When you run `/mpm-agents`, I will:

1. **List Available Agents**: Run `claude-mpm agents list` to show all agents
2. **Display Agent Information**:
   - Agent names and IDs
   - Brief descriptions
   - Model preferences (opus, sonnet, haiku)
   - Tool availability
   - Version information
   - Deployment status

## Output Example

The command displays agents in a formatted table showing:
- Agent name and description
- Version and model preference
- Tools available to the agent
- Current deployment status

## Implementation

To show available agents, I'll execute:
```bash
claude-mpm agents list --deployed
```

This will display all deployed agents that are currently available for use.

Alternatively, you can use these variations:
- `claude-mpm agents list --system` - Show system agents
- `claude-mpm agents list --by-tier` - Group agents by precedence tier
- `claude-mpm agents list --all` - Show all agents including undeployed

## Auto-Configuration Subcommands (NEW!)

### Quick Agent Setup

Claude MPM now includes intelligent auto-configuration that detects your project and recommends the right agents:

#### `agents detect`
Scan your project to detect toolchain and frameworks:
```bash
claude-mpm agents detect
```

Shows detected:
- Programming languages (Python, Node.js, Rust, Go, etc.)
- Frameworks (FastAPI, Next.js, React, Express, etc.)
- Testing tools (pytest, Jest, Playwright, etc.)
- Build tools and package managers
- Deployment configurations

#### `agents recommend`
Get agent recommendations based on detected toolchain:
```bash
claude-mpm agents recommend
```

Shows:
- Essential agents for your stack
- Recommended complementary agents
- Optional specialized agents
- Rationale for each recommendation

#### `auto-configure`
Automatically detect, recommend, and deploy agents:
```bash
claude-mpm auto-configure --preview  # See what would be configured
claude-mpm auto-configure            # Interactive configuration
claude-mpm auto-configure --yes      # Auto-apply without prompts
```

**Example workflow:**
1. Run `claude-mpm agents detect` to see what's detected
2. Run `claude-mpm agents recommend` to see suggestions
3. Run `claude-mpm auto-configure` to apply configuration
4. Or skip straight to `claude-mpm auto-configure --yes`

### Supported Stacks

**Python:**
- FastAPI, Flask, Django → fastapi-engineer, python-engineer
- pytest, unittest → api-qa, python-qa

**JavaScript/TypeScript:**
- Next.js → nextjs-engineer, react-engineer
- React, Vue, Svelte → react-engineer, web-qa
- Express, Nest.js → node-engineer, api-qa
- Jest, Vitest, Playwright → playwright-qa, web-qa

**Full-Stack Projects:**
Automatically recommends both frontend and backend agents based on your complete stack.

**Deployment:**
- Vercel → vercel-ops
- Railway → railway-ops
- Docker → docker-ops
- PM2 → local-ops-agent

## Related Commands

For more information on auto-configuration:
- `/mpm-help auto-configure` - Detailed auto-configuration help
- `/mpm-agents-detect` - Run detection via slash command
- `/mpm-agents-recommend` - Show recommendations via slash command
- `/mpm-auto-configure` - Run auto-configuration via slash command