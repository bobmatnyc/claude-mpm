# User Guide

Complete guide to Claude MPM features and workflows.

## Table of Contents

- [Auto-Configuration](#auto-configuration)
- [Agent System](#agent-system)
- [Skills System](#skills-system)
- [Memory System](#memory-system)
- [Local Process Management](#local-process-management)
- [Session Management](#session-management)
- [Real-Time Monitoring](#real-time-monitoring)
- [MCP Gateway](#mcp-gateway)
- [Best Practices](#best-practices)

## Auto-Configuration

**NEW in v4.10.0** - Automatically detect your project stack and configure agents.

### Quick Start

```bash
# Auto-configure current project
claude-mpm auto-configure

# Preview without applying
claude-mpm auto-configure --preview

# Lower confidence threshold (default 80%)
claude-mpm auto-configure --threshold 60
```

### How It Works

1. **Language Detection**: Scans project files to identify languages
2. **Framework Detection**: Analyzes configuration files to detect frameworks
3. **Tool Detection**: Identifies build tools, testing frameworks, databases
4. **Agent Recommendation**: Suggests agents with confidence scores
5. **Deployment**: Copies recommended agents to `.claude-agents/`

### Detected Technologies

**Languages**: Python, JavaScript, TypeScript, Go, Rust, PHP, Ruby, Java, C++, C#

**Frameworks**:
- Python: FastAPI, Flask, Django
- JavaScript/TypeScript: Next.js, React, Express, Vue, Angular
- Go: Gin, Echo, standard library
- Rust: Axum, Actix, Rocket
- PHP: Laravel, Symfony
- Ruby: Rails, Sinatra

**Tools**: Docker, Kubernetes, PostgreSQL, MySQL, MongoDB, Redis, testing frameworks

### Configuration

Settings in `.claude-mpm/config.yaml`:

```yaml
auto_configuration:
  enabled: true
  confidence_threshold: 80
  auto_deploy: true
  include_experimental: false
```

## Agent System

Claude MPM uses a three-tier agent hierarchy: PROJECT > USER > SYSTEM

### Agent Tiers

**PROJECT Tier** (`.claude-agents/`):
- Project-specific agents
- Highest priority
- Overrides USER and SYSTEM agents

**USER Tier** (`~/.claude-agents/`):
- Personal agents
- Overrides SYSTEM agents
- Shared across projects

**SYSTEM Tier** (bundled):
- Built-in agents
- Default agents like PM, Research, Engineer

### Agent Commands

```bash
# List all agents
claude-mpm agents list

# List by tier
claude-mpm agents list --by-tier

# Create new agent
claude-mpm agents create <name>

# Deploy agents
claude-mpm agents deploy

# Validate agents
claude-mpm agents validate
```

### Slash Commands

Use in Claude Code sessions:

```bash
# Manage agents
/mpm-agents

# List available agents
/mpm-agents list

# Deploy recommended agents
/mpm-agents deploy
```

### Agent Delegation

The PM (Project Manager) agent orchestrates workflow by delegating to specialists:

1. **Research Agent**: Codebase analysis, documentation review
2. **Engineer Agent**: Implementation, refactoring
3. **QA Agent**: Testing, validation, quality checks
4. **Documentation Agent**: Documentation generation

**Example Workflow:**
```
User: "Add authentication to the API"
↓
PM: Plans approach, delegates to Research
↓
Research: Analyzes codebase, identifies patterns
↓
PM: Delegates to Engineer
↓
Engineer: Implements authentication
↓
PM: Delegates to QA
↓
QA: Creates tests, validates implementation
↓
PM: Delegates to Documentation
↓
Documentation: Updates API docs
```

## Skills System

**NEW in v4.15.0** - Enhance agent capabilities with reusable skill modules.

### Overview

Claude MPM includes 20 bundled skills providing specialized expertise: `git-workflow`, `test-driven-development`, `code-review`, `refactoring-patterns`, `security-scanning`, `database-migration`, `docker-containerization`, `api-documentation`, `performance-profiling`, `systematic-debugging`, `async-testing`, `json-data-handling`, `pdf`, `xlsx`, `imagemagick`, `nextjs-local-dev`, `fastapi-local-dev`, `vite-local-dev`, `express-local-dev`, `web-performance-optimization`.

### Access Skills Management

```bash
claude-mpm configure
# Select option [2] Skills Management
```

Interactive menu provides:
- View bundled skills
- Select skills for agents
- Auto-link skills to agents
- Manage custom skills

### Auto-Linking (Recommended)

Automatically maps skills to compatible agents based on agent type:

```bash
# In Skills Management menu
# Select option [4] Auto-link skills
```

Maps skills intelligently:
- `git-workflow` → version control agents
- `test-driven-development` → QA and engineer agents
- `security-scanning` → security and ops agents

### Three-Tier System

Skills follow the same hierarchy as agents:

1. **BUNDLED**: 20 included skills (system-wide)
2. **USER**: Personal skills in `~/.claude/skills/`
3. **PROJECT**: Project-specific skills in `.claude/skills/`

Priority: PROJECT > USER > BUNDLED (project skills override user, user overrides bundled)

### Custom Skills

Create markdown files in `.claude/skills/` for project-specific expertise:

```bash
mkdir -p .claude/skills
cat > .claude/skills/custom-api-patterns.md << 'EOF'
# Custom API Patterns

## Project Guidelines
- Use async handlers for all endpoints
- Validate with Pydantic models
- Return structured JSON responses
EOF
```

Skills auto-discover on next run. Restart Claude Code session to activate.

### Skill Selection

Manually assign skills to specific agents:

```bash
# In Skills Management menu
# Select option [2] Select skills for an agent
# Choose agent, then select skills from list
```

Configuration saved to `.claude-mpm/config.yaml`:

```yaml
skills:
  assignments:
    engineer:
      - git-workflow
      - test-driven-development
      - refactoring-patterns
```

### Best Practices

**Use auto-linking for quick setup**: Covers most common scenarios efficiently.

**Add project skills for domain expertise**: Store project-specific patterns, conventions, and guidelines in `.claude/skills/`.

**Keep skills focused**: One skill per expertise area (e.g., separate database patterns from API patterns).

**Update skills as patterns evolve**: Skills are living documentation of project best practices.

### Version Tracking

All skills support semantic versioning (MAJOR.MINOR.PATCH) with YAML frontmatter:

```markdown
---
skill_id: my-skill
skill_version: 1.0.0
updated_at: 2025-10-30
tags:
  - category
  - topic
---

# My Skill

Skill content here...
```

**Check versions with the `/mpm-version` command:**

```
/mpm-version
```

This displays:
- Project version and build number
- All agents with versions (grouped by tier: system/user/project)
- All skills with versions (grouped by source: bundled/user/project)
- Summary statistics with totals

**Example output:**

```
Claude MPM Version Information
==============================

Project Version: 4.16.3
Build: 481

Agents (35 total)
-----------------
System Agents (30):
  ├─ engineer (3.9.1)
  ├─ pm (2.0.0)
  └─ ... (28 more)

Skills (20 total)
-----------------
Bundled Skills (20):
  ├─ test-driven-development (0.1.0)
  ├─ systematic-debugging (0.1.0)
  └─ ... (18 more)

Summary
-------
• Project: v4.16.3 (build 481)
• Agents: 35 total (30 system, 3 user, 2 project)
• Skills: 20 total (20 bundled, 0 user, 0 project)
```

**See [Skills Versioning Guide](skills-versioning.md) for complete documentation on:**
- Creating versioned skills
- Semantic versioning guidelines
- Migration strategies
- Best practices

## Memory System

Persistent learning across sessions using project-specific knowledge graphs.

### How It Works

Agents can store learnings via JSON response fields:

```json
{
  "memory-update": {
    "Project Architecture": ["Uses FastAPI with async endpoints"],
    "Implementation Guidelines": ["Always use Pydantic models for validation"],
    "Current Technical Context": ["Authentication uses JWT tokens"]
  }
}
```

Or simplified:

```json
{
  "remember": ["API uses REST conventions", "Tests use pytest fixtures"]
}
```

### Memory Categories

- **Project Architecture**: Architectural patterns and structures
- **Implementation Guidelines**: Coding standards and practices
- **Current Technical Context**: Project-specific technical details

### Memory Commands

```bash
# Query project memories
claude-mpm recall "authentication"

# View memory statistics
claude-mpm stats

# Enhance prompt with memories
claude-mpm enhance "how should I implement login?"
```

### Best Practices

**Store project-specific information:**
- ✅ "API uses FastAPI 0.104.0 with async"
- ✅ "Tests require pytest-asyncio fixture"
- ❌ "Python is a programming language" (too generic)

**Keep memories relevant:**
- ✅ "Auth tokens expire after 24 hours"
- ✅ "Database uses alembic for migrations"
- ❌ "Function should return None" (too specific to one function)

## Local Process Management

**NEW in v4.13.0** - Professional-grade local deployment with health monitoring.

### Quick Start

```bash
# Start development server
claude-mpm local-deploy start \
  --command "npm run dev" \
  --name "nextjs-dev" \
  --auto-restart

# Monitor deployment
claude-mpm local-deploy monitor <deployment-id>

# List all deployments
claude-mpm local-deploy list

# Stop deployment
claude-mpm local-deploy stop <deployment-id>
```

### Features

**Three-Tier Health Checks:**
1. **HTTP Health**: Endpoint availability and response codes
2. **Process Health**: Process status and stability
3. **Resource Health**: Memory and CPU usage

**Auto-Restart:**
- Automatic restart on crash
- Exponential backoff (1s → 2s → 4s → 8s → 16s → 32s → 60s max)
- Circuit breaker after 5 consecutive failures

**Monitoring:**
- Memory leak detection (configurable threshold)
- Resource exhaustion prevention
- Log error pattern matching
- Real-time metrics

### Configuration

Create `.claude-mpm/local-ops-config.yaml`:

```yaml
deployments:
  nextjs-dev:
    command: "npm run dev"
    directory: "."
    health_check:
      enabled: true
      url: "http://localhost:3000"
      interval: 30
      timeout: 10
      initial_delay: 5
    auto_restart:
      enabled: true
      max_attempts: 5
    resource_monitoring:
      memory_threshold_mb: 512
      check_interval: 60
    log_monitoring:
      error_patterns:
        - "ERROR"
        - "FATAL"
        - "Exception"
```

### Commands

```bash
# Start with config file
claude-mpm local-deploy start --config nextjs-dev

# Start with inline options
claude-mpm local-deploy start \
  --command "python -m uvicorn app:app --reload" \
  --name "api-server" \
  --health-url "http://localhost:8000/health" \
  --auto-restart

# Monitor specific deployment
claude-mpm local-deploy monitor <deployment-id>

# View logs
claude-mpm local-deploy logs <deployment-id>

# Restart deployment
claude-mpm local-deploy restart <deployment-id>

# Stop deployment
claude-mpm local-deploy stop <deployment-id>

# Stop all deployments
claude-mpm local-deploy stop --all
```

## Session Management

Save and resume Claude Code sessions with full context preservation.

### Pause Session

```bash
# In Claude Code session
/pause

# Or CLI
claude-mpm mpm-init pause
```

**What's saved:**
- Conversation history
- Current git state (branch, status)
- Todo list
- Accomplishments
- Project context

### Resume Session

```bash
# In Claude Code session
/resume

# Or CLI
claude-mpm mpm-init resume
```

**What happens:**
- Session state restored
- Automatic change detection since pause
- Git diff shown if changes detected
- Context enriched with changes

### Best Practices

**When to pause:**
- Before switching branches
- Before major refactoring
- End of work session
- Before long breaks

**What to check after resume:**
- Review detected changes
- Check git status
- Verify branch context
- Review todos

## Resume Log System

**NEW in v4.17.2** - Proactive context management for seamless session continuity.

### Overview

The Resume Log System automatically generates structured 10k-token logs when approaching Claude's context window limits, enabling you to resume work without losing important context.

**Key Benefits:**
- 🎯 Graduated warnings at 70%/85%/95% thresholds (60k token buffer at first warning)
- 📋 10k-token structured logs with 7 key sections
- 🔄 Automatic session resumption with full context
- ⚙️ Zero-configuration automatic operation
- 📁 Human-readable markdown format

### How It Works

**1. Automatic Token Tracking**
```bash
# Start session normally
claude-mpm run --monitor

# System tracks token usage automatically
# No user intervention required
```

**2. Graduated Warnings**
```
At 70% (140k tokens used, 60k remaining):
⚠️  Context Usage Caution: 70% capacity reached
60,000 tokens remaining - consider planning for session transition.

At 85% (170k tokens used, 30k remaining):
⚠️  Context Usage Warning: 85% capacity reached
30,000 tokens remaining - complete current task, avoid starting new work.

At 95% (190k tokens used, 10k remaining):
🚨 Context Usage Critical: 95% capacity reached
10,000 tokens remaining - STOP new work immediately.
Resume log will be generated automatically.
```

**3. Automatic Resume Log Generation**

When you hit 95% or explicitly pause:
```bash
# Manual pause
/pause

# Or automatic at 95% threshold
# Resume log generated: .claude-mpm/resume-logs/session-20251101_115000.md
```

**4. Seamless Resumption**

Start new session - previous context automatically loaded:
```bash
claude-mpm run

# You see:
# 📋 Resuming from previous session (20251101_115000)...
# Context: Implementing user authentication system
# Last task: JWT token generation completed
# Next: Create database migration
```

### Resume Log Structure

Each resume log contains 7 key sections with intelligent token allocation:

```markdown
# Session Resume Log: 20251101_115000

## Context Metrics (500 tokens)
- Token usage, percentage, stop reason

## Mission Summary (1,000 tokens)
- Overall goal and purpose of the session

## Accomplishments (2,000 tokens)
- What was completed during the session

## Key Findings (2,500 tokens)
- Important discoveries and learnings

## Decisions & Rationale (1,500 tokens)
- Why certain choices were made

## Next Steps (1,500 tokens)
- Clear actions to continue work

## Critical Context (1,000 tokens)
- Essential state, IDs, paths, and data
```

### Configuration

Resume logs work automatically with sensible defaults. Customize in `.claude-mpm/configuration.yaml`:

```yaml
context_management:
  enabled: true
  budget_total: 200000

  thresholds:
    caution: 0.70   # First warning - plan transition
    warning: 0.85   # Strong warning - wrap up
    critical: 0.95  # Urgent - stop new work

  resume_logs:
    enabled: true
    auto_generate: true
    max_tokens: 10000
    storage_dir: ".claude-mpm/resume-logs"
```

### Usage Examples

**Example 1: Long Implementation Session**
```bash
# Start working on feature
claude-mpm run

User: "Implement user authentication with JWT"

# Work progresses...
# At 70%: You get first warning, plan to wrap up soon
# At 85%: Complete current subtask
# At 95%: Resume log auto-generated

# Next day - start new session
claude-mpm run

# Previous context automatically loaded
# Continue seamlessly from where you left off
```

**Example 2: Multi-Day Project**
```bash
# Day 1: Research and Planning
claude-mpm run
User: "Research authentication best practices"
# Work...
User: "/pause"  # Manual pause at natural breakpoint

# Day 2: Implementation
claude-mpm run  # Previous research automatically loaded
User: "Implement authentication based on our research"
# Work...
User: "/pause"

# Day 3: Testing and Deployment
claude-mpm run  # Full context from Days 1 and 2
User: "Test and deploy authentication"
```

### Best Practices

**When to Pause Manually:**
- ✅ After completing a major feature
- ✅ Before switching to different component
- ✅ At end of work day
- ✅ After major refactoring

**How to Use Thresholds:**
- **At 70%**: Note current task, plan transition
- **At 85%**: Start wrapping up current subtask
- **At 95%**: Stop new work, let resume log generate

**Resume Log Quality:**
- Clear mission statements
- Specific accomplishments with file paths
- Actionable next steps
- Essential context (IDs, paths, environment variables)

### Viewing Resume Logs

```bash
# List all resume logs
ls -lh .claude-mpm/resume-logs/

# View latest resume log
cat .claude-mpm/resume-logs/session-*.md | tail -1

# Open in editor
code .claude-mpm/resume-logs/
```

### Advanced Features

**Custom Token Allocation:**
```yaml
context_management:
  resume_logs:
    token_allocation:
      context_metrics: 500
      mission_summary: 1000
      accomplishments: 2000
      key_findings: 2500    # Emphasize discoveries
      decisions: 1500
      next_steps: 1500
      critical_context: 1000
```

**Custom Triggers:**
```yaml
context_management:
  resume_logs:
    triggers:
      - "model_context_window_exceeded"
      - "manual_pause"
      - "threshold_critical"
      - "threshold_warning"  # Optional: generate at 85%
```

**Retention Policy:**
```yaml
context_management:
  resume_logs:
    cleanup:
      enabled: true
      keep_count: 10        # Keep last 10 logs
      auto_cleanup: true    # Cleanup on session start
```

### Troubleshooting

**Resume log not generated:**
- Check configuration: `resume_logs.enabled: true`
- Check triggers: Include appropriate triggers
- Verify storage directory exists and is writable

**Resume log not loading on startup:**
- Check `auto_load: true` in configuration
- Verify resume log files exist in storage directory
- Check file permissions

**Token usage not tracking:**
- Ensure context management is enabled
- Check response tracking is active
- Verify hooks are properly configured

### Related Documentation

- **Detailed Guide**: [resume-logs.md](resume-logs.md) - Complete documentation
- **Examples**: [../examples/resume-log-examples.md](../examples/resume-log-examples.md) - Tutorials and examples
- **Configuration**: [../configuration.md](../configuration.md) - Configuration reference
- **Architecture**: [../developer/resume-log-architecture.md](../developer/resume-log-architecture.md) - Technical details

## Real-Time Monitoring

Live dashboard showing agent collaboration and system metrics.

### Start Monitoring

```bash
# Interactive mode with dashboard
claude-mpm run --monitor

# Or start dashboard separately
claude-mpm monitor
```

Dashboard opens at http://localhost:8765

### Dashboard Features

**Agent Activity:**
- Active agents and their current tasks
- Delegation flow visualization
- Agent communication logs

**System Metrics:**
- Memory usage
- Request latency
- Cache hit rates
- Hook execution times

**Session Information:**
- Current session ID
- Session duration
- Total requests
- Active tickets

### WebSocket Events

Real-time updates via WebSocket:
- Agent started/stopped
- Task delegated
- Task completed
- Memory updated
- Error occurred

## MCP Gateway

Model Context Protocol integration for extensible tools.

### Overview

MCP Gateway provides:
- External tool connectivity
- Standardized tool interfaces
- Dynamic tool loading
- Error handling and fallbacks

### Available MCP Tools

**Included:**
- `kuzu-memory`: Project-specific knowledge graphs (bundled)

**Optional:**
- `mcp-vector-search`: Semantic code search (auto-install on first use)

### MCP Tool Auto-Install

When you first use semantic search features:

```
⚠️  mcp-vector-search not found
This package enables semantic code search (optional feature).

Installation options:
  1. Install via pip (recommended for this project)
  2. Install via pipx (isolated, system-wide)
  3. Skip (use traditional grep/glob instead)

Choose option (1/2/3) [3]:
```

**Recommendations:**
- **Option 1 (pip)**: Best for project-specific work
- **Option 2 (pipx)**: Best for system-wide availability
- **Option 3 (skip)**: System continues with grep/glob

After installation, vector search works seamlessly without prompts.

### Configuration

MCP settings in `.claude-mpm/config.yaml`:

```yaml
mcp_gateway:
  enabled: true
  tools:
    - name: kuzu-memory
      enabled: true
    - name: mcp-vector-search
      enabled: true
      auto_install: true
```

## Best Practices

### Project Setup

1. **Initialize once per project**: Run `claude-mpm init` or `/mpm-init`
2. **Auto-configure stack**: Run `claude-mpm auto-configure`
3. **Review deployed agents**: Check `.claude-agents/` directory
4. **Configure local deployments**: Set up `.claude-mpm/local-ops-config.yaml`

### Agent Usage

1. **Let PM delegate**: Trust the PM agent to orchestrate workflow
2. **Provide clear context**: Give agents specific, actionable requests
3. **Review delegation**: Use `--monitor` to see agent collaboration
4. **Customize agents**: Add project-specific agents to `.claude-agents/`

### Memory Management

1. **Store project-specific info**: Keep memories relevant to the project
2. **Use clear categories**: Organize under Architecture, Guidelines, Context
3. **Review memories**: Check what's stored with `claude-mpm recall`
4. **Update outdated info**: Memories persist across sessions

### Session Management

1. **Pause before switching**: Save state before branch changes
2. **Resume with context**: Review detected changes after resume
3. **Track work**: Use todos to maintain continuity
4. **Keep sessions focused**: Separate major features into different sessions

### Monitoring

1. **Use for complex tasks**: Enable `--monitor` for multi-step work
2. **Watch delegation flow**: Understand agent collaboration patterns
3. **Check metrics**: Monitor performance and identify bottlenecks
4. **Review logs**: Use dashboard to debug issues

---

**Next Steps:**
- Troubleshooting: See [troubleshooting.md](troubleshooting.md)
- Developer docs: See [../developer/architecture.md](../developer/architecture.md)
- Agent creation: See [../agents/creating-agents.md](../agents/creating-agents.md)
