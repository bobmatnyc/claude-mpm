# Automatically configure agents based on project detection

Automatically detect your project's toolchain and configure the most appropriate agents.

## Usage

```
/mpm-auto-configure [options]
```

## Description

This command provides intelligent auto-configuration that:
1. Scans your project to detect programming languages, frameworks, and tools
2. Recommends the most appropriate agents for your stack
3. Optionally deploys the recommended agents with confirmation

This is the fastest way to get started with Claude MPM in any project!

## Options

- `--preview` - Show what would be configured without making any changes
- `--yes` - Automatically apply recommendations without prompting
- `--force` - Force reconfiguration even if agents are already deployed

## Implementation

When you run `/mpm-auto-configure`, the PM will:

1. **Detect Your Stack**:
   - Scan for package.json, requirements.txt, Cargo.toml, go.mod, etc.
   - Identify frameworks (FastAPI, Next.js, React, Express, etc.)
   - Detect testing tools (pytest, Jest, Playwright, etc.)
   - Find build tools and deployment configurations

2. **Recommend Agents**:
   - **Essential agents**: Required for your primary stack
   - **Recommended agents**: Complementary agents for full functionality
   - **Optional agents**: Specialized agents for detected tools

3. **Deploy Agents** (with confirmation):
   - Show what will be deployed
   - Request confirmation (unless --yes is used)
   - Deploy agents to your project
   - Verify deployment success

## Examples

### Preview Mode (Recommended First Step)
```
/mpm-auto-configure --preview
```
Shows what would be configured without making changes. Great for understanding recommendations before applying.

### Interactive Configuration
```
/mpm-auto-configure
```
Detect, recommend, and prompt for confirmation before deploying.

### Automatic Configuration
```
/mpm-auto-configure --yes
```
Automatically apply all recommendations without prompting. Best for quick setup.

### Force Reconfiguration
```
/mpm-auto-configure --force
```
Reconfigure agents even if some are already deployed. Useful for stack changes.

## Expected Output

```
🤖 Auto-Configuration for Claude MPM
=====================================

Step 1: Detecting Project Stack
--------------------------------
✓ Detected Python 3.11
✓ Detected FastAPI 0.104.0
✓ Detected pytest 7.4.0
✓ Detected Docker configuration
✓ Detected Vercel deployment

Step 2: Agent Recommendations
------------------------------
Essential Agents (3):
  ✓ fastapi-engineer - FastAPI framework detected
  ✓ python-engineer - Python project support
  ✓ api-qa - API testing and validation

Recommended Agents (2):
  ○ docker-ops - Docker configuration found
  ○ vercel-ops - Vercel deployment detected

Optional Agents (1):
  ○ playwright-qa - Browser testing capability

Step 3: Deploy Agents
---------------------
Deploy 5 agents? (y/n): y

Deploying agents...
✓ fastapi-engineer deployed
✓ python-engineer deployed
✓ api-qa deployed
✓ docker-ops deployed
✓ vercel-ops deployed

🎉 Auto-configuration complete!
5 agents deployed successfully.

Next steps:
- Run /mpm-agents to see your deployed agents
- Start working with specialized agents for your stack
- Use /mpm-help for more information
```

## What Gets Detected

### Languages
- Python (CPython, PyPy)
- JavaScript/TypeScript (Node.js, Deno, Bun)
- Rust
- Go
- Java

### Python Frameworks
- FastAPI
- Flask
- Django
- Starlette
- Pyramid

### JavaScript/TypeScript Frameworks
- Next.js
- React
- Vue
- Svelte
- Angular
- Express
- Nest.js
- Fastify

### Testing Tools
- pytest (Python)
- unittest (Python)
- Jest (JavaScript)
- Vitest (JavaScript)
- Playwright (Browser)
- Cypress (Browser)

### Build Tools
- Vite
- Webpack
- Rollup
- esbuild
- Turbopack

### Deployment Platforms
- Vercel
- Railway
- Docker
- PM2
- Kubernetes

## Agent Mapping Examples

### Python + FastAPI
**Essential:**
- fastapi-engineer
- python-engineer
- api-qa

**Recommended:**
- docker-ops (if Docker detected)
- vercel-ops (if Vercel detected)

### Next.js + React
**Essential:**
- nextjs-engineer
- react-engineer
- web-qa

**Recommended:**
- playwright-qa (if Playwright detected)
- vercel-ops (if Vercel detected)

### Full-Stack (FastAPI + React)
**Essential:**
- fastapi-engineer
- python-engineer
- react-engineer
- api-qa
- web-qa

**Recommended:**
- playwright-qa
- docker-ops
- local-ops-agent

## Default Configuration Fallback

When auto-configuration cannot detect your project's toolchain (e.g., a new or uncommon language/framework), it automatically falls back to a sensible set of default general-purpose agents instead of leaving your project unconfigured.

### When Defaults are Applied

Default agents are deployed when:
- Primary language is detected as "Unknown"
- No specific framework or toolchain can be identified
- No agent recommendations can be generated from detected technologies

### Default Agents

The following general-purpose agents are recommended with moderate confidence (0.7):

- **engineer**: General-purpose engineer for code implementation
- **research**: Code exploration and analysis
- **qa**: Testing and quality assurance
- **ops**: Infrastructure and deployment operations
- **documentation**: Documentation and technical writing

All default recommendations will be marked with `is_default: True` in the metadata.

### Disabling Default Fallback

To disable the default configuration fallback, edit `.claude-mpm/config/agent_capabilities.yaml`:

```yaml
default_configuration:
  enabled: false  # Disable default fallback
```

When disabled, auto-configuration will recommend zero agents if the toolchain cannot be detected.

### Customizing Defaults

You can customize which agents are deployed by default by editing the `default_configuration.agents` section in `.claude-mpm/config/agent_capabilities.yaml`:

```yaml
default_configuration:
  enabled: true
  min_confidence: 0.7  # Confidence score for default recommendations
  agents:
    - agent_id: engineer
      reasoning: "General-purpose engineer for code implementation"
      priority: 1
    - agent_id: research
      reasoning: "Code exploration and analysis"
      priority: 2
    # Add or remove agents as needed
```

## Tips

1. **Start with preview**: Always run with `--preview` first to see recommendations
2. **Review carefully**: Check that detected stack matches your project
3. **Customize later**: You can always deploy/remove agents manually after auto-config
4. **Re-run after changes**: Run again with `--force` if you add new frameworks
5. **Complementary commands**: Use `/mpm-agents-detect` and `/mpm-agents-recommend` for more details

## Related Commands

- `/mpm-agents-detect` - Just show detected toolchain
- `/mpm-agents-recommend` - Show recommendations without deploying
- `/mpm-agents` - Manage agents manually
- `/mpm-help agents` - Learn about manual agent management
