# Claude MPM Configuration Reference

Complete configuration reference for Claude MPM including the Resume Log System.

## Table of Contents

- [Configuration File Location](#configuration-file-location)
- [Configuration Structure](#configuration-structure)
- [Context Management](#context-management)
- [Resume Logs](#resume-logs)
- [Session Management](#session-management)
- [Agent Configuration](#agent-configuration)
- [Skills Configuration](#skills-configuration)
- [MCP Gateway](#mcp-gateway)
- [Monitoring](#monitoring)
- [Examples](#examples)

## Configuration File Location

Claude MPM uses YAML configuration files located in `.claude-mpm/`:

```
.claude-mpm/
├── configuration.yaml      # Main configuration
├── local-ops-config.yaml  # Local deployment config
└── config.yaml            # Legacy/alternative config
```

**Primary Configuration**: `.claude-mpm/configuration.yaml`

## Configuration Structure

### Minimal Configuration

```yaml
# Minimal configuration - uses defaults for everything
context_management:
  enabled: true
```

### Full Configuration Example

```yaml
# Complete configuration with all options

# Context Management & Resume Logs
context_management:
  enabled: true
  budget_total: 200000

  thresholds:
    caution: 0.70
    warning: 0.85
    critical: 0.95

  resume_logs:
    enabled: true
    auto_generate: true
    auto_load: true
    max_tokens: 10000
    storage_dir: ".claude-mpm/resume-logs"
    format: "markdown"

    triggers:
      - "model_context_window_exceeded"
      - "max_tokens"
      - "manual_pause"
      - "threshold_critical"
      - "threshold_warning"

    cleanup:
      enabled: true
      keep_count: 10
      auto_cleanup: true

    token_allocation:
      context_metrics: 500
      mission_summary: 1000
      accomplishments: 2000
      key_findings: 2500
      decisions: 1500
      next_steps: 1500
      critical_context: 1000

# Session Management
session:
  auto_save: true
  save_interval: 300  # seconds
  max_history: 100

# Agent System
agents:
  enabled: true
  auto_deploy: false
  tier_priority: ["project", "user", "system"]

# Skills System
skills:
  enabled: true
  auto_link: true
  assignments:
    engineer:
      - git-workflow
      - test-driven-development
    qa:
      - test-driven-development
      - systematic-debugging

# MCP Gateway
mcp_gateway:
  enabled: true
  tools:
    - name: kuzu-memory
      enabled: true
    - name: mcp-vector-search
      enabled: true
      auto_install: true

# Monitoring
monitoring:
  enabled: false
  port: 8765
  host: "localhost"

# Logging
logging:
  level: "INFO"
  file: ".claude-mpm/logs/claude-mpm.log"
  max_size: 10485760  # 10MB
  backup_count: 5
```

## Context Management

Configuration for context window management and token tracking.

### Basic Settings

```yaml
context_management:
  enabled: true              # Enable context management
  budget_total: 200000      # Total token budget (Claude 3.5 Sonnet)
```

**Options**:
- `enabled` (boolean): Enable context management system
  - Default: `true`
  - Recommended: `true` (essential for resume logs)

- `budget_total` (integer): Total token budget for the model
  - Default: `200000` (Claude 3.5 Sonnet)
  - Claude 3 Opus: `200000`
  - Claude 3 Haiku: `200000`
  - Adjust based on model used

### Threshold Configuration

```yaml
context_management:
  thresholds:
    caution: 0.70      # 70% - First warning (60k buffer)
    warning: 0.85      # 85% - Strong warning (30k buffer)
    critical: 0.95     # 95% - Critical alert (10k buffer)
```

**Threshold Levels**:

| Threshold | Percentage | Tokens Used (200k total) | Remaining | Action |
|-----------|-----------|--------------------------|-----------|---------|
| `caution` | 70% | 140,000 | 60,000 | Plan transition |
| `warning` | 85% | 170,000 | 30,000 | Wrap up current task |
| `critical` | 95% | 190,000 | 10,000 | Stop new work |

**Customization**:
```yaml
# More aggressive thresholds (earlier warnings)
thresholds:
  caution: 0.60    # 60% - Very early warning
  warning: 0.75    # 75% - Earlier wrap-up
  critical: 0.90   # 90% - Earlier critical

# More conservative thresholds (later warnings)
thresholds:
  caution: 0.80    # 80% - Later warning
  warning: 0.90    # 90% - Later wrap-up
  critical: 0.95   # 95% - Standard critical
```

**Recommendations**:
- **Default (70/85/95)**: Best for most use cases
- **Aggressive (60/75/90)**: For very long sessions
- **Conservative (80/90/95)**: For short, focused sessions

## Resume Logs

Configuration for automatic resume log generation.

### Basic Configuration

```yaml
context_management:
  resume_logs:
    enabled: true          # Enable resume logs
    auto_generate: true    # Auto-generate on triggers
    auto_load: true        # Auto-load on session start
    max_tokens: 10000     # Maximum tokens per log
    storage_dir: ".claude-mpm/resume-logs"  # Storage location
    format: "markdown"     # Output format
```

**Options**:

- `enabled` (boolean): Enable resume log system
  - Default: `true`
  - Set to `false` to completely disable

- `auto_generate` (boolean): Automatically generate logs on triggers
  - Default: `true`
  - Set to `false` for manual generation only

- `auto_load` (boolean): Automatically load latest log on session start
  - Default: `true`
  - Set to `false` to disable automatic loading

- `max_tokens` (integer): Maximum tokens per resume log
  - Default: `10000`
  - Range: `5000` - `15000`
  - Smaller = less context, faster generation
  - Larger = more context, more token usage

- `storage_dir` (string): Directory for resume logs
  - Default: `".claude-mpm/resume-logs"`
  - Can be absolute or relative path

- `format` (string): Output format for resume logs
  - Default: `"markdown"`
  - Currently only `"markdown"` supported
  - Future: `"json"`, `"html"`

### Trigger Configuration

```yaml
context_management:
  resume_logs:
    triggers:
      - "model_context_window_exceeded"  # API limit exceeded
      - "max_tokens"                     # Token limit reached
      - "manual_pause"                   # User paused session
      - "threshold_critical"             # 95% threshold
      - "threshold_warning"              # 85% threshold (optional)
```

**Available Triggers**:

| Trigger | Description | Recommended |
|---------|-------------|-------------|
| `model_context_window_exceeded` | Claude API context limit exceeded | ✅ Yes |
| `max_tokens` | Model token limit reached | ✅ Yes |
| `manual_pause` | User explicitly paused session (`/pause`) | ✅ Yes |
| `threshold_critical` | 95% threshold reached | ✅ Yes |
| `threshold_warning` | 85% threshold reached | ⚠️ Optional |
| `threshold_caution` | 70% threshold reached | ❌ No (too early) |

**Recommendations**:
- **Minimal**: `["manual_pause", "threshold_critical"]`
- **Standard**: `["model_context_window_exceeded", "max_tokens", "manual_pause", "threshold_critical"]`
- **Aggressive**: Add `"threshold_warning"` for earlier generation

### Cleanup Configuration

```yaml
context_management:
  resume_logs:
    cleanup:
      enabled: true        # Enable automatic cleanup
      keep_count: 10      # Keep last 10 resume logs
      auto_cleanup: true  # Cleanup on session start
```

**Options**:

- `enabled` (boolean): Enable cleanup system
  - Default: `true`
  - Set to `false` to keep all resume logs

- `keep_count` (integer): Number of logs to retain
  - Default: `10`
  - Range: `5` - `50`
  - Older logs deleted automatically

- `auto_cleanup` (boolean): Run cleanup on session start
  - Default: `true`
  - Set to `false` for manual cleanup only

**Storage Recommendations**:
```yaml
# Minimal storage (keep last 5)
cleanup:
  keep_count: 5

# Standard storage (keep last 10)
cleanup:
  keep_count: 10

# Extended storage (keep last 20)
cleanup:
  keep_count: 20

# Archive everything (no cleanup)
cleanup:
  enabled: false
```

### Token Allocation Configuration

```yaml
context_management:
  resume_logs:
    token_allocation:
      context_metrics: 500      # 5% - Session metrics
      mission_summary: 1000     # 10% - High-level goal
      accomplishments: 2000     # 20% - Completed work
      key_findings: 2500        # 25% - Discoveries
      decisions: 1500           # 15% - Choices made
      next_steps: 1500          # 15% - Remaining work
      critical_context: 1000    # 10% - Essential state
```

**Default Distribution** (10,000 tokens total):
- Context Metrics: 500 tokens (5%)
- Mission Summary: 1,000 tokens (10%)
- Accomplishments: 2,000 tokens (20%)
- Key Findings: 2,500 tokens (25%)
- Decisions: 1,500 tokens (15%)
- Next Steps: 1,500 tokens (15%)
- Critical Context: 1,000 tokens (10%)

**Customization Examples**:

```yaml
# Emphasize next steps (action-oriented)
token_allocation:
  context_metrics: 400
  mission_summary: 800
  accomplishments: 1500
  key_findings: 2000
  decisions: 1200
  next_steps: 2500      # Increased
  critical_context: 1600

# Emphasize findings (research-oriented)
token_allocation:
  context_metrics: 400
  mission_summary: 800
  accomplishments: 1500
  key_findings: 3500    # Increased
  decisions: 1000
  next_steps: 1300
  critical_context: 1500

# Balanced (default)
token_allocation:
  context_metrics: 500
  mission_summary: 1000
  accomplishments: 2000
  key_findings: 2500
  decisions: 1500
  next_steps: 1500
  critical_context: 1000
```

**Constraints**:
- Total must equal `max_tokens` (default 10,000)
- Minimum 200 tokens per section
- Maximum 4,000 tokens per section

## Session Management

Configuration for session save/resume behavior.

```yaml
session:
  auto_save: true          # Automatically save session state
  save_interval: 300       # Save every 5 minutes
  max_history: 100         # Keep last 100 conversation turns
  enable_git_tracking: true # Track git state in sessions
```

**Options**:

- `auto_save` (boolean): Enable automatic session saving
  - Default: `true`
  - Saves session state periodically

- `save_interval` (integer): Seconds between auto-saves
  - Default: `300` (5 minutes)
  - Range: `60` - `1800`

- `max_history` (integer): Maximum conversation turns to keep
  - Default: `100`
  - Older turns pruned to save memory

- `enable_git_tracking` (boolean): Include git state in sessions
  - Default: `true`
  - Tracks branch, status, diffs

## Agent Configuration

Configuration for agent system.

```yaml
agents:
  enabled: true                              # Enable agent system
  auto_deploy: false                         # Auto-deploy on project init
  tier_priority: ["project", "user", "system"]  # Search priority
  default_agents: ["pm", "engineer", "qa"]  # Always load these
```

**Options**:

- `enabled` (boolean): Enable multi-agent system
  - Default: `true`
  - Core feature - recommended to keep enabled

- `auto_deploy` (boolean): Auto-deploy agents on `claude-mpm init`
  - Default: `false`
  - Set to `true` for automatic agent deployment

- `tier_priority` (array): Order to search for agents
  - Default: `["project", "user", "system"]`
  - Project agents override user, user overrides system

- `default_agents` (array): Agents to always load
  - Default: `["pm", "engineer", "qa"]`
  - Core agents for basic functionality

## Skills Configuration

Configuration for skills system.

```yaml
skills:
  enabled: true           # Enable skills system
  auto_link: true         # Auto-link skills to agents
  assignments:
    engineer:
      - git-workflow
      - test-driven-development
      - refactoring-patterns
    qa:
      - test-driven-development
      - systematic-debugging
    security:
      - security-scanning
```

**Options**:

- `enabled` (boolean): Enable skills system
  - Default: `true`
  - Provides reusable expertise modules

- `auto_link` (boolean): Automatically link skills to agents
  - Default: `true`
  - Maps skills based on agent type

- `assignments` (dict): Manual skill-to-agent mappings
  - Format: `agent_name: [skill1, skill2, ...]`
  - Overrides auto-linking for specified agents

**Auto-Link Mapping**:
- `git-workflow` → version control agents
- `test-driven-development` → QA, engineer agents
- `security-scanning` → security, ops agents
- `docker-containerization` → ops, devops agents

## MCP Gateway

Configuration for Model Context Protocol integration.

```yaml
mcp_gateway:
  enabled: true          # Enable MCP gateway
  tools:
    - name: kuzu-memory
      enabled: true
      config: {}
    - name: mcp-vector-search
      enabled: true
      auto_install: true
      config:
        index_dir: ".mcp-vector-search"
```

**Options**:

- `enabled` (boolean): Enable MCP gateway
  - Default: `true`
  - Enables external tool integration

- `tools` (array): List of MCP tools
  - Each tool has `name`, `enabled`, and optional `config`

**Built-in Tools**:

| Tool | Description | Auto-Install |
|------|-------------|--------------|
| `kuzu-memory` | Project knowledge graph | ✅ Required |
| `mcp-vector-search` | Semantic code search | ⚠️ Optional |
| `mcp-browser` | Browser automation | ⚠️ Optional |

## Monitoring

Configuration for real-time monitoring dashboard.

```yaml
monitoring:
  enabled: false         # Enable monitoring
  port: 8765            # Dashboard port
  host: "localhost"     # Dashboard host
  update_interval: 1000 # Update every 1 second (ms)
```

**Options**:

- `enabled` (boolean): Enable monitoring dashboard
  - Default: `false`
  - Set to `true` or use `--monitor` flag

- `port` (integer): Port for dashboard
  - Default: `8765`
  - Range: `1024` - `65535`

- `host` (string): Host for dashboard
  - Default: `"localhost"`
  - Use `"0.0.0.0"` for network access

- `update_interval` (integer): Update frequency in milliseconds
  - Default: `1000` (1 second)
  - Range: `500` - `5000`

## Examples

### Configuration for Short Sessions

```yaml
# Optimized for focused, short sessions (< 50k tokens)
context_management:
  enabled: true
  budget_total: 200000
  thresholds:
    caution: 0.80   # Later warning
    warning: 0.90
    critical: 0.95

  resume_logs:
    enabled: true
    auto_generate: true
    max_tokens: 5000  # Smaller logs for short sessions
    triggers:
      - "manual_pause"
      - "threshold_critical"
    cleanup:
      keep_count: 5   # Keep fewer logs
```

### Configuration for Long Research Sessions

```yaml
# Optimized for extended research sessions
context_management:
  enabled: true
  budget_total: 200000
  thresholds:
    caution: 0.60   # Earlier warning
    warning: 0.75
    critical: 0.90

  resume_logs:
    enabled: true
    auto_generate: true
    max_tokens: 15000  # Larger logs for more context
    triggers:
      - "model_context_window_exceeded"
      - "max_tokens"
      - "manual_pause"
      - "threshold_warning"  # Generate at 75%
      - "threshold_critical"

    token_allocation:
      context_metrics: 500
      mission_summary: 1000
      accomplishments: 2000
      key_findings: 5000   # Emphasize findings
      decisions: 2000
      next_steps: 2000
      critical_context: 2500
```

### Configuration for Team Collaboration

```yaml
# Optimized for team handoffs
context_management:
  enabled: true
  resume_logs:
    enabled: true
    auto_generate: true
    storage_dir: ".claude-mpm/resume-logs"
    cleanup:
      keep_count: 20  # Keep more logs for history
      auto_cleanup: false  # Manual cleanup

# Commit resume logs to git
# .gitignore should NOT exclude .claude-mpm/resume-logs/
```

### Configuration for CI/CD Integration

```yaml
# Optimized for deployment automation
context_management:
  enabled: true
  resume_logs:
    enabled: true
    auto_generate: true
    triggers:
      - "manual_pause"  # Only on explicit pause
    cleanup:
      enabled: false  # Keep all logs for audit trail

session:
  auto_save: true
  save_interval: 60  # More frequent saves
```

### Minimal Configuration (Defaults)

```yaml
# Minimal - use all defaults
context_management:
  enabled: true
```

This is equivalent to:
```yaml
context_management:
  enabled: true
  budget_total: 200000
  thresholds:
    caution: 0.70
    warning: 0.85
    critical: 0.95
  resume_logs:
    enabled: true
    auto_generate: true
    auto_load: true
    max_tokens: 10000
    storage_dir: ".claude-mpm/resume-logs"
    format: "markdown"
    triggers:
      - "model_context_window_exceeded"
      - "max_tokens"
      - "manual_pause"
      - "threshold_critical"
    cleanup:
      enabled: true
      keep_count: 10
      auto_cleanup: true
```

## Environment Variables

Configuration can also be set via environment variables:

```bash
# Context management
export CLAUDE_MPM_CONTEXT_ENABLED=true
export CLAUDE_MPM_BUDGET_TOTAL=200000

# Resume logs
export CLAUDE_MPM_RESUME_LOGS_ENABLED=true
export CLAUDE_MPM_RESUME_LOGS_MAX_TOKENS=10000
export CLAUDE_MPM_RESUME_LOGS_STORAGE_DIR=".claude-mpm/resume-logs"

# Monitoring
export CLAUDE_MPM_MONITOR_ENABLED=false
export CLAUDE_MPM_MONITOR_PORT=8765
```

**Priority**: Environment variables > configuration file > defaults

## Validation

Configuration is validated on startup. Common errors:

**Invalid threshold values**:
```yaml
# ERROR: Thresholds must be 0.0 - 1.0
thresholds:
  caution: 70  # Should be 0.70
```

**Invalid token budget**:
```yaml
# ERROR: Token allocation exceeds max_tokens
resume_logs:
  max_tokens: 10000
  token_allocation:
    accomplishments: 15000  # Exceeds total!
```

**Invalid storage directory**:
```yaml
# ERROR: Storage directory must be writable
resume_logs:
  storage_dir: "/root/.claude-mpm"  # Permission denied
```

## Related Documentation

- [User Guide - Resume Logs](user/resume-logs.md) - User documentation
- [Developer Architecture](developer/resume-log-architecture.md) - Technical details
- [Examples](examples/resume-log-examples.md) - Real-world examples

## Summary

Key configuration points:
- ✅ Resume logs enabled by default with sensible settings
- ✅ Graduated thresholds (70%/85%/95%) provide proactive management
- ✅ 10k-token budget intelligently distributed
- ✅ Automatic cleanup keeps last 10 logs
- ✅ Zero-configuration operation out of the box
- ✅ Extensive customization for specific use cases
