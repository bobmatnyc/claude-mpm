# CLI Agents Command Reference

**Version**: 5.0.0
**Status**: Current
**Last Updated**: 2025-12-01

Complete reference for all `claude-mpm agents` CLI commands.

## Table of Contents

- [Overview](#overview)
- [Command Summary](#command-summary)
- [Agent Detection](#agent-detection)
- [Agent Recommendations](#agent-recommendations)
- [Auto-Configuration](#auto-configuration)
- [Agent Deployment](#agent-deployment)
- [Agent Management](#agent-management)
- [Examples](#examples)
- [Related Documentation](#related-documentation)

---

## Overview

The `claude-mpm agents` command group provides comprehensive agent management capabilities:

- **Detection**: Scan project to discover technologies
- **Recommendations**: Get intelligent agent suggestions
- **Auto-configuration**: Detect, recommend, and deploy automatically
- **Deployment**: Deploy agents from presets or individually
- **Management**: List, update, and manage deployed agents

---

## Command Summary

| Command | Purpose | New in v5.0 |
|---------|---------|-------------|
| `agents detect` | Scan project for technologies | ✨ Yes |
| `agents recommend` | Get agent recommendations | ✨ Yes |
| `agents auto-configure` | Full auto-configuration workflow | ✨ Yes |
| `agents deploy` | Deploy agents (preset or individual) | Enhanced |
| `agents list` | List all available agents | Existing |
| `agents status` | Show deployment status | Existing |
| `agents sync` | Sync remote agent sources | Existing |

---

## Agent Detection

### `claude-mpm agents detect`

Scan project directory to detect programming languages, frameworks, tools, and configurations.

#### Synopsis

```bash
claude-mpm agents detect [OPTIONS]
```

#### Description

Analyzes your project to understand the technology stack without making any changes. This is useful for:
- Understanding what Claude MPM can detect
- Debugging auto-configuration
- Planning manual agent deployment
- Verification of project structure

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--path PATH` | Path | Current directory | Project directory to scan |
| `--json` | Flag | False | Output JSON format (for scripting) |
| `--verbose` | Flag | False | Show detailed evidence for detections |
| `--debug` | Flag | False | Enable debug logging |

#### Detection Capabilities

**Languages** (8+):
- Python, JavaScript, TypeScript, Go, Rust, PHP, Ruby, Java

**Frameworks** (20+):
- Backend: FastAPI, Django, Flask, Express, NestJS, Spring Boot, Laravel, Rails
- Frontend: React, Next.js, Vue, Svelte, Angular
- Testing: pytest, Jest, Playwright, Cypress

**Deployment Targets**:
- Docker, Vercel, Railway, Kubernetes, GitHub Actions

#### Examples

```bash
# Basic detection in current directory
claude-mpm agents detect

# Detect in specific project
claude-mpm agents detect --path /path/to/project

# JSON output for scripting
claude-mpm agents detect --json > detection.json

# Verbose output with evidence
claude-mpm agents detect --verbose

# Debug mode for troubleshooting
claude-mpm agents detect --debug
```

#### Sample Output

```
📊 Project Toolchain Analysis
Project: /Users/dev/my-fastapi-project

🔤 Detected Languages:
┌──────────┬─────────┬────────────────────┐
│ Language │ Version │ Confidence         │
├──────────┼─────────┼────────────────────┤
│ Python   │ 3.11.0  │ ██████████ 100%    │
│ TypeScript│ 5.0.0  │ ████████░░  80%    │
└──────────┴─────────┴────────────────────┘

🏗️  Detected Frameworks:
┌──────────┬─────────┬──────────┬────────────────────┐
│ Framework│ Version │ Category │ Confidence         │
├──────────┼─────────┼──────────┼────────────────────┤
│ FastAPI  │ 0.104.1 │ backend  │ ██████████  95%    │
│ pytest   │ 7.4.0   │ testing  │ ████████░░  85%    │
└──────────┴─────────┴──────────┴────────────────────┘

🚀 Deployment Targets:
┌────────┬────────────────────┐
│ Target │ Confidence         │
├────────┼────────────────────┤
│ Docker │ ██████████  90%    │
└────────┴────────────────────┘

✅ Analysis complete: 2 language(s), 2 framework(s), 1 deployment target(s)
```

#### JSON Output Format

```json
{
  "project_path": "/Users/dev/my-project",
  "languages": [
    {
      "language": "Python",
      "version": "3.11.0",
      "confidence": 1.0,
      "evidence": ["main.py", "requirements.txt", "pyproject.toml"]
    }
  ],
  "frameworks": [
    {
      "name": "FastAPI",
      "version": "0.104.1",
      "category": "backend",
      "confidence": 0.95,
      "evidence": ["from fastapi import", "FastAPI() call"]
    }
  ],
  "deployment_targets": [
    {
      "target_type": "docker",
      "confidence": 0.9,
      "evidence": ["Dockerfile", "docker-compose.yml"]
    }
  ]
}
```

#### Exit Codes

- `0`: Success
- `1`: Detection failed (errors)
- `130`: User cancelled (Ctrl+C)

#### Related

- User Guide: [Auto-Configuration Guide](../getting-started/auto-configuration.md#detection-details)
- Slash Command: `/mpm-configure` (unified configuration interface)

---

## Agent Recommendations

### `claude-mpm agents recommend`

Analyze detection results and recommend agents based on your project stack.

#### Synopsis

```bash
claude-mpm agents recommend [OPTIONS]
```

#### Description

Uses detection results to generate intelligent agent recommendations. Agents are categorized by importance (Essential, Recommended, Optional) with confidence scores and rationale.

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--path PATH` | Path | Current directory | Project directory to analyze |
| `--threshold INT` | Integer | 70 | Confidence threshold (0-100) |
| `--preview` | Flag | False | Show recommendations without deploying |
| `--json` | Flag | False | Output JSON format |
| `--output FORMAT` | String | text | Output format: text or json |

#### Confidence Thresholds

| Threshold | Behavior | Use Case |
|-----------|----------|----------|
| **50-60** | More suggestions, some weak matches | Exploratory, learning |
| **70** | Balanced (default) | Most projects |
| **80-90** | Stricter, only strong matches | Production, minimal setups |

#### Examples

```bash
# Get recommendations (default threshold: 70)
claude-mpm agents recommend

# Lower threshold for more suggestions
claude-mpm agents recommend --threshold 60

# Higher threshold for stricter matching
claude-mpm agents recommend --threshold 85

# Preview without side effects
claude-mpm agents recommend --preview

# Specific project path
claude-mpm agents recommend --path /path/to/project

# JSON output for automation
claude-mpm agents recommend --json
```

#### Sample Output

```
💡 Agent Recommendations for your project

📋 ESSENTIAL (8 agents) - Core agents for detected technologies:
  ✓ universal/memory-manager      (95%) - Project memory management
    Rationale: Required for all projects

  ✓ engineer/backend/python-engineer (95%) - Python/FastAPI development
    Rationale: Python detected with high confidence (100%)

  ✓ engineer/frontend/react-engineer (85%) - React development
    Rationale: React framework detected (85% confidence)

  ✓ qa/api-qa                     (90%) - API testing
    Rationale: FastAPI backend requires API testing

  ✓ qa/web-qa                     (85%) - Frontend testing
    Rationale: React frontend requires UI testing

  ✓ ops/core/ops                  (80%) - Docker operations
    Rationale: Docker deployment detected (90% confidence)

  ✓ security/security             (75%) - Security scanning
    Rationale: Web applications need security review

  ✓ documentation/documentation   (70%) - Documentation generation
    Rationale: All projects benefit from documentation

📋 RECOMMENDED (3 agents) - Enhance development workflow:
  ○ universal/research             (70%) - Research and analysis
    Rationale: Helpful for looking up API documentation

  ○ documentation/ticketing        (65%) - Ticket management
    Rationale: Project management integration available

  ○ universal/code-analyzer        (60%) - Code quality analysis
    Rationale: Multi-language project benefits from analysis

📋 OPTIONAL (2 agents) - Specialized capabilities:
  ○ ops/platform/vercel-ops        (55%) - Vercel deployment
    Rationale: No Vercel config detected, but framework compatible

  ○ qa/qa                          (50%) - General QA
    Rationale: Complement specialized QA agents

Summary:
- 8 essential agents (strongly recommended)
- 3 recommended agents (enhance workflow)
- 2 optional agents (specialized needs)

💡 To deploy: claude-mpm agents auto-configure --yes
```

#### JSON Output Format

```json
{
  "status": "success",
  "project_path": "/Users/dev/my-project",
  "recommendations": {
    "essential": [
      {
        "agent_id": "universal/memory-manager",
        "confidence": 0.95,
        "rationale": "Required for all projects",
        "category": "essential"
      }
    ],
    "recommended": [...],
    "optional": [...]
  },
  "summary": {
    "essential_count": 8,
    "recommended_count": 3,
    "optional_count": 2,
    "total": 13
  }
}
```

#### Exit Codes

- `0`: Success
- `1`: Recommendation failed
- `130`: User cancelled

#### Related

- User Guide: [Auto-Configuration Guide](../getting-started/auto-configuration.md#recommendation-engine)
- Slash Command: `/mpm-configure` (unified configuration interface)

---

## Auto-Configuration

### `claude-mpm agents auto-configure`

Complete auto-configuration workflow: detect → recommend → deploy.

#### Synopsis

```bash
claude-mpm agents auto-configure [OPTIONS]
```

#### Description

Performs full auto-configuration in three phases:
1. **Detect**: Scan project for technologies
2. **Recommend**: Generate agent recommendations
3. **Deploy**: Deploy approved agents

This is the recommended way to set up agents for a new project.

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--path PATH` | Path | Current directory | Project directory |
| `--threshold INT` | Integer | 70 | Confidence threshold (0-100) |
| `--preview` | Flag | False | Preview without deploying |
| `--yes` | Flag | False | Auto-approve (non-interactive) |
| `--force` | Flag | False | Redeploy even if agents exist |
| `--json` | Flag | False | Output JSON format |

#### Workflow Modes

**Interactive Mode** (default):
- Shows detection results
- Displays recommendations
- Asks for confirmation before deploying

**Non-Interactive Mode** (`--yes`):
- Auto-approves all recommendations
- Useful for scripts and CI/CD
- No user prompts

**Preview Mode** (`--preview`):
- Shows what would be configured
- No deployments or changes
- Safe for exploration

#### Examples

```bash
# Interactive auto-configuration (recommended)
claude-mpm agents auto-configure

# Non-interactive (for scripts/CI)
claude-mpm agents auto-configure --yes

# Preview what would be configured
claude-mpm agents auto-configure --preview

# Force reconfiguration
claude-mpm agents auto-configure --force --yes

# Custom threshold
claude-mpm agents auto-configure --threshold 80

# Specific project
claude-mpm agents auto-configure --path /path/to/project

# JSON output for automation
claude-mpm agents auto-configure --json --yes
```

#### Interactive Workflow

```
🔍 Detecting project stack...
  ✓ Found: Python 3.11, FastAPI 0.104, React 18.2
  ✓ Detected 2 languages, 2 frameworks, 1 deployment target

💡 Recommending agents...
  ✓ 8 essential agents
  ✓ 3 recommended agents
  ✓ 2 optional agents

Recommendations:
  Essential (8): memory-manager, python-engineer, react-engineer, ...
  Recommended (3): research, ticketing, code-analyzer
  Optional (2): vercel-ops, qa

📦 Deploy 11 agents to .claude-mpm/cache/agents/? [Y/n]: y

🚀 Deploying agents...
  ✓ universal/memory-manager
  ✓ engineer/backend/python-engineer
  ✓ engineer/frontend/react-engineer
  ... (8 more)

✅ Auto-configuration complete!
   - 11 agents deployed
   - Configuration saved to .claude-mpm/

Next steps:
  - Start session: claude-mpm run
  - Check status: claude-mpm status
  - List agents: claude-mpm agents list
```

#### Exit Codes

- `0`: Success (agents deployed)
- `1`: Configuration failed
- `2`: User declined deployment
- `130`: User cancelled (Ctrl+C)

#### Related

- User Guide: [Auto-Configuration Guide](../getting-started/auto-configuration.md)
- Slash Command: `/mpm-configure` (unified configuration interface)
- Comparison: [Auto-Configure vs Presets](../getting-started/auto-configuration.md#comparison-with-other-methods)

---

## Agent Deployment

### `claude-mpm agents deploy`

Deploy agents from presets or individually.

#### Synopsis

```bash
# Deploy from preset
claude-mpm agents deploy --preset <preset-name>

# Deploy individual agent
claude-mpm agents deploy <agent-id>

# Deploy multiple agents
claude-mpm agents deploy <agent-id-1> <agent-id-2> ...
```

#### Description

Deploy agents to `.claude-mpm/cache/agents/` either from curated presets or by specifying individual agent IDs.

#### Preset Options (New in v5.0)

| Option | Type | Description |
|--------|------|-------------|
| `--preset NAME` | String | Deploy preset bundle |
| `--list-presets` | Flag | Show all available presets |

#### Deployment Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--force` | Flag | False | Redeploy even if exists |
| `--skip-dependencies` | Flag | False | Don't deploy dependencies |
| `--dry-run` | Flag | False | Preview without deploying |

#### Available Presets

| Preset Name | Agents | Description |
|-------------|--------|-------------|
| `minimal` | 6 | Essential agents for any project |
| `python-dev` | 8 | Python backend development |
| `python-fullstack` | 12 | Python + React full-stack |
| `javascript-backend` | 8 | Node.js backend |
| `react-dev` | 9 | React frontend |
| `nextjs-fullstack` | 13 | Next.js full-stack |
| `rust-dev` | 7 | Rust systems development |
| `golang-dev` | 8 | Go backend development |
| `java-dev` | 9 | Java/Spring Boot |
| `mobile-flutter` | 8 | Flutter mobile apps |
| `data-eng` | 10 | Data engineering stack |

#### Examples

**Preset Deployment:**
```bash
# Deploy Python development preset
claude-mpm agents deploy --preset python-dev

# Deploy Next.js full-stack preset
claude-mpm agents deploy --preset nextjs-fullstack

# List all available presets
claude-mpm agents deploy --list-presets

# Force redeploy preset
claude-mpm agents deploy --preset python-dev --force
```

**Individual Agent Deployment:**
```bash
# Deploy single agent
claude-mpm agents deploy engineer/backend/python-engineer

# Deploy multiple agents
claude-mpm agents deploy \
  universal/memory-manager \
  engineer/backend/python-engineer \
  qa/api-qa

# Force redeploy
claude-mpm agents deploy engineer/backend/python-engineer --force

# Dry run (preview)
claude-mpm agents deploy --preset python-dev --dry-run
```

**Combined Approach:**
```bash
# Deploy preset + custom agent
claude-mpm agents deploy --preset python-dev
claude-mpm agents deploy ops/platform/railway-ops
```

#### Exit Codes

- `0`: Success (all agents deployed)
- `1`: Deployment failed
- `2`: Invalid preset or agent ID
- `130`: User cancelled

#### Related

- User Guide: [Agent Presets Guide](../user/agent-presets.md)
- User Guide: [Agent Sources Guide](../user/agent-sources.md)
- Reference: [Available Agents](../agents/README.md)

---

## Agent Management

### `claude-mpm agents list`

List all available agents with deployment status.

#### Synopsis

```bash
claude-mpm agents list [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--deployed` | Flag | False | Show only deployed agents |
| `--available` | Flag | False | Show only available (not deployed) |
| `--json` | Flag | False | Output JSON format |

#### Examples

```bash
# List all agents
claude-mpm agents list

# List only deployed agents
claude-mpm agents list --deployed

# List available (not deployed) agents
claude-mpm agents list --available

# JSON output
claude-mpm agents list --json
```

#### Sample Output

```
📋 Claude MPM Agents

Deployed Agents (8):
  ✓ universal/memory-manager (v1.2.0)
  ✓ engineer/backend/python-engineer (v1.5.0)
  ✓ qa/api-qa (v1.3.0)
  ... (5 more)

Available Agents (25):
  ○ engineer/frontend/react-engineer (v1.4.0)
  ○ engineer/data/data-engineer (v1.1.0)
  ○ ops/platform/vercel-ops (v1.0.0)
  ... (22 more)

Summary:
  - 8 agents deployed
  - 25 agents available
  - 33 total agents
```

---

### `claude-mpm agents status`

Show deployment status and health of agents.

#### Synopsis

```bash
claude-mpm agents status [OPTIONS]
```

#### Description

Displays detailed status of deployed agents including versions, sources, and health.

#### Examples

```bash
# Show agent status
claude-mpm agents status

# JSON output
claude-mpm agents status --json
```

---

### `claude-mpm agents sync`

Sync remote agent sources to get latest updates.

#### Synopsis

```bash
claude-mpm agents sync [OPTIONS]
```

#### Description

Updates agent definitions from remote git repositories. This keeps your agents up-to-date with the latest improvements.

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--force` | Flag | False | Force sync even if up-to-date |
| `--source NAME` | String | all | Sync specific source only |

#### Examples

```bash
# Sync all sources
claude-mpm agents sync

# Force sync
claude-mpm agents sync --force

# Sync specific source
claude-mpm agents sync --source bobmatnyc/claude-mpm-agents
```

---

## Examples

### Example 1: New Python Project Setup

```bash
# Option A: Auto-configuration (recommended)
claude-mpm agents auto-configure

# Option B: Preset (faster)
claude-mpm agents deploy --preset python-dev

# Option C: Manual selection
claude-mpm agents deploy \
  universal/memory-manager \
  engineer/backend/python-engineer \
  qa/api-qa \
  ops/core/ops
```

---

### Example 2: Multi-Language Monorepo

```bash
# Detect what's in the project
claude-mpm agents detect --verbose

# Review recommendations
claude-mpm agents recommend --preview

# Deploy with lower threshold for more agents
claude-mpm agents auto-configure --threshold 65 --yes
```

---

### Example 3: Team Onboarding Script

```bash
#!/bin/bash
# onboard-new-dev.sh

echo "🚀 Setting up Claude MPM for team development..."

# Install Claude MPM (if needed)
if ! command -v claude-mpm &> /dev/null; then
  echo "Installing Claude MPM..."
  pipx install "claude-mpm[monitor]"
fi

# Deploy team standard agents
echo "Deploying team agent preset..."
claude-mpm agents deploy --preset python-fullstack --yes

# Verify deployment
echo "Verifying setup..."
claude-mpm doctor

echo "✅ Setup complete! Start with: claude-mpm run --monitor"
```

---

### Example 4: CI/CD Integration

```bash
# .github/workflows/claude-mpm-setup.yml

- name: Setup Claude MPM Agents
  run: |
    pip install claude-mpm

    # Auto-configure agents for CI environment
    claude-mpm agents auto-configure \
      --yes \
      --threshold 80 \
      --json > agents.json

    # Verify deployment
    claude-mpm agents list --deployed
```

---

### Example 5: Custom Agent Stack

```bash
# Start with minimal preset
claude-mpm agents deploy --preset minimal

# Add specific agents for our stack
claude-mpm agents deploy engineer/backend/golang-engineer
claude-mpm agents deploy engineer/frontend/react-engineer
claude-mpm agents deploy ops/platform/railway-ops

# Verify final configuration
claude-mpm agents list --deployed
```

---

## Related Documentation

### User Guides
- **[Auto-Configuration Guide](../getting-started/auto-configuration.md)** - Complete auto-configuration documentation
- **[Agent Presets Guide](../user/agent-presets.md)** - All preset details and use cases
- **[Agent Sources Guide](../user/agent-sources.md)** - Managing agent repositories

### Reference
- **[Slash Commands Reference](slash-commands.md)** - In-session command equivalents
- **[Agent Capabilities Reference](../agents/agent-capabilities-reference.md)** - Detailed agent descriptions

### Implementation
- **[Agent System Guide](../guides/single-tier-agent-system.md)** - Agent deployment details
- **[Auto-Configuration](../getting-started/auto-configuration.md)** - Detection workflow

---

**Need Help?**
- Run `claude-mpm agents --help` for command help
- Run `/mpm-doctor` to diagnose issues
- See [Troubleshooting Guide](../user/troubleshooting.md)

---

**Last Updated**: 2025-12-01
**Version**: 5.0.0
**Status**: Current
