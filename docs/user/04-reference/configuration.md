# Configuration Reference

This guide covers all configuration options for Claude MPM.

## Configuration Overview

Claude MPM uses a hierarchical configuration system:

1. **System Defaults** - Built-in defaults
2. **User Config** - `~/.claude-mpm/config.yml`
3. **Project Config** - `.claude-mpm.yml` in project root
4. **Environment Variables** - `CLAUDE_MPM_*`
5. **Command Line** - Flags and options (highest priority)

## Configuration Files

### User Configuration

Location: `~/.claude-mpm/config.yml`

```yaml
# Global user preferences
model: opus
debug: false
session_dir: ~/.claude-mpm/sessions
log_dir: ~/.claude-mpm/logs

# Subprocess defaults
subprocess:
  enabled: false
  parallel: true
  memory_limit_mb: 2048
  timeout_seconds: 300

# Ticket defaults
tickets:
  enabled: true
  auto_create: true
  default_priority: medium
  default_type: task
```

### Project Configuration

Location: `.claude-mpm.yml` in project root

```yaml
# Project-specific settings
model: sonnet  # Override user default
agents_dir: .claude/agents

# Project subprocess settings
subprocess:
  enabled: true
  memory_limit_mb: 4096  # Higher limit for this project

# Custom ticket patterns
tickets:
  patterns:
    - "TODO:"
    - "FIXME:"
    - "HACK:"
  type_mapping:
    FIXME: bug
    HACK: task
```

### Framework Configuration

Location: Specified by `--framework-path` or auto-detected

```yaml
# Framework settings
agents:
  - name: Engineer
    triggers: ["implement", "create", "build"]
    template: engineer_agent.md
  - name: QA
    triggers: ["test", "verify", "check"]
    template: qa_agent.md

delegation:
  patterns:
    - '**{agent}**: {task}'
    - '→ {agent}: {task}'
```

## Environment Variables

### Core Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `CLAUDE_MPM_MODEL` | Default Claude model | `opus`, `sonnet`, `haiku` |
| `CLAUDE_MPM_DEBUG` | Enable debug mode | `true`, `false` |
| `CLAUDE_MPM_HOME` | Claude MPM home directory | `~/.claude-mpm` |
| `CLAUDE_MPM_SESSION_DIR` | Session log directory | `~/claude-sessions` |
| `CLAUDE_MPM_LOG_LEVEL` | Logging level | `DEBUG`, `INFO`, `WARNING` |

### Subprocess Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAUDE_MPM_SUBPROCESS` | Enable subprocess mode | `false` |
| `CLAUDE_MPM_PARALLEL` | Enable parallel execution | `true` |
| `CLAUDE_MPM_MEMORY_LIMIT` | Memory limit (MB) | `2048` |
| `CLAUDE_MPM_TIMEOUT` | Timeout (seconds) | `300` |
| `CLAUDE_MPM_MAX_PARALLEL` | Max parallel processes | `5` |

### Ticket Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAUDE_MPM_NO_TICKETS` | Disable ticket creation | `false` |
| `CLAUDE_MPM_TICKET_DIR` | Ticket directory | `./tickets` |
| `CLAUDE_MPM_TICKET_PREFIX` | Ticket ID prefix | `TSK` |

### Path Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `CLAUDE_PATH` | Claude CLI path | `/usr/local/bin/claude` |
| `CLAUDE_MPM_FRAMEWORK` | Framework path | `~/.claude-mpm/framework` |
| `CLAUDE_MPM_AGENTS` | Agents directory | `./.claude/agents` |

## Configuration Options

### Model Configuration

```yaml
# Model selection and options
model:
  default: opus
  fallback: sonnet
  options:
    opus:
      temperature: 0.7
      max_tokens: 4096
    sonnet:
      temperature: 0.8
      max_tokens: 4096
```

### Subprocess Configuration

```yaml
subprocess:
  # Enable subprocess orchestration
  enabled: true
  
  # Parallel execution
  parallel:
    enabled: true
    max_processes: 5
    batch_size: 3
  
  # Resource limits
  resources:
    memory_limit_mb: 2048
    cpu_limit_percent: 80
    timeout_seconds: 300
  
  # Process management
  process:
    shell: false
    encoding: utf-8
    buffer_size: 8192
    
  # Monitoring
  monitoring:
    interval_seconds: 1
    memory_warnings: true
    cpu_warnings: true
```

### Ticket Configuration

```yaml
tickets:
  # Enable automatic ticket creation
  enabled: true
  auto_create: true
  
  # Ticket patterns
  patterns:
    default:
      - "TODO:"
      - "TASK:"
      - "BUG:"
      - "FEATURE:"
    custom:
      - "FIXME:"
      - "HACK:"
      - "OPTIMIZE:"
  
  # Type mapping
  type_mapping:
    TODO: task
    TASK: task
    BUG: bug
    FEATURE: feature
    FIXME: bug
    HACK: task
    OPTIMIZE: enhancement
  
  # Priority rules
  priority_rules:
    keywords:
      critical: ["urgent", "critical", "blocker"]
      high: ["important", "high", "major"]
      medium: ["normal", "medium"]
      low: ["minor", "low", "trivial"]
    default: medium
  
  # Storage
  storage:
    directory: ./tickets
    tasks_dir: tasks
    epics_dir: epics
    format: markdown
```

### Logging Configuration

```yaml
logging:
  # Log levels
  level: INFO  # DEBUG, INFO, WARNING, ERROR
  
  # Log destinations
  destinations:
    console:
      enabled: true
      format: simple  # simple, detailed, json
    file:
      enabled: true
      directory: ~/.claude-mpm/logs
      rotation: daily
      retention_days: 30
      max_size_mb: 100
  
  # Session logging
  sessions:
    enabled: true
    directory: ~/.claude-mpm/sessions
    format: detailed
    include_timestamps: true
    include_metadata: true
```

### Agent Configuration

```yaml
agents:
  # Agent discovery
  discovery:
    directories:
      - .claude/agents
      - ~/.claude-mpm/agents
    auto_load: true
  
  # Built-in agents
  builtin:
    - name: Engineer
      enabled: true
      triggers: ["implement", "create", "build", "code"]
      memory_limit_mb: 3072
      timeout_seconds: 600
      
    - name: QA
      enabled: true
      triggers: ["test", "verify", "check", "validate"]
      memory_limit_mb: 2048
      timeout_seconds: 450
      
    - name: Research
      enabled: true
      triggers: ["research", "investigate", "analyze"]
      memory_limit_mb: 4096
      timeout_seconds: 900
  
  # Custom agents
  custom:
    - name: DataAnalyst
      template: data_analyst.md
      triggers: ["analyze data", "visualize", "statistics"]
      memory_limit_mb: 8192
```

### Agent Deployment Configuration

```yaml
agent_deployment:
  # List of agent IDs to exclude from deployment
  excluded_agents:
    - research
    - data_engineer
    - ops
  
  # Whether agent name matching is case-sensitive (default: false)
  case_sensitive: false
  
  # Whether to exclude agent dependencies (future feature)
  exclude_dependencies: false
```

#### Agent Exclusion Examples

**Minimal deployment** (only essential agents):
```yaml
agent_deployment:
  excluded_agents:
    - research
    - data_engineer
    - ops
    - version_control
```

**Security-focused deployment**:
```yaml
agent_deployment:
  excluded_agents:
    - engineer
    - documentation
    - research
    - ops
    - data_engineer
    - version_control
```

**Development environment** (exclude heavy agents):
```yaml
agent_deployment:
  excluded_agents:
    - ops          # Not needed for local dev
    - data_engineer # Heavy processing
  case_sensitive: false
```

#### CLI Override

Override exclusions for full deployment:
```bash
# Deploy all agents, ignoring exclusion configuration
claude-mpm agents deploy --include-all
```

See [Agent Exclusion Guide](../../AGENT_EXCLUSION.md) for comprehensive documentation.

### Memory Protection Configuration

```yaml
memory_protection:
  # Enable memory monitoring
  enabled: true
  
  # Thresholds
  thresholds:
    warning_percent: 75
    critical_percent: 90
    auto_summarize_percent: 85
  
  # Actions
  actions:
    on_warning: notify
    on_critical: summarize
    on_limit: stop
  
  # Context management
  context:
    preserve_recent: 10  # Keep last N exchanges
    preserve_patterns: ["TODO", "DECISION", "ticket"]
    compression_enabled: true
    compression_target: 0.3  # Compress to 30%
```

### Framework Configuration

```yaml
framework:
  # Framework loading
  auto_load: true
  path: auto  # auto, or specific path
  
  # Injection settings
  injection:
    mode: prepend  # prepend, append, replace
    max_size_kb: 50
    
  # Framework components
  components:
    instructions: true
    agents: true
    patterns: true
    examples: true
```

## Configuration Precedence

### Example Precedence

```bash
# 1. System default
model: opus

# 2. User config (~/.claude-mpm/config.yml)
model: sonnet

# 3. Project config (.claude-mpm.yml)
model: haiku

# 4. Environment variable
export CLAUDE_MPM_MODEL=sonnet

# 5. Command line (highest priority)
claude-mpm --model opus

# Result: opus (command line wins)
```

## Advanced Configuration

### Conditional Configuration

```yaml
# Environment-specific settings
environments:
  development:
    debug: true
    model: haiku  # Faster for dev
    subprocess:
      timeout_seconds: 60
      
  production:
    debug: false
    model: opus  # Best quality
    subprocess:
      timeout_seconds: 600
      memory_limit_mb: 8192
```

### Profile-Based Configuration

```yaml
# Named profiles
profiles:
  fast:
    model: haiku
    subprocess:
      enabled: false
    tickets:
      auto_create: false
      
  quality:
    model: opus
    subprocess:
      enabled: true
      parallel: true
    memory_protection:
      enabled: true
      
  debug:
    debug: true
    logging:
      level: DEBUG
      destinations:
        file:
          enabled: true
```

Use profiles:
```bash
claude-mpm --profile fast
claude-mpm --profile quality
```

### Plugin Configuration

```yaml
plugins:
  # Enable plugins
  enabled: true
  directory: ~/.claude-mpm/plugins
  
  # Specific plugins
  git_integration:
    enabled: true
    auto_commit: false
    commit_format: "claude-mpm: {ticket_id} - {message}"
    
  slack_notifications:
    enabled: false
    webhook_url: ${SLACK_WEBHOOK_URL}
    notify_on: ["ticket_created", "session_complete"]
```

## Configuration Commands

### View Configuration

```bash
# Show current configuration
claude-mpm config show

# Show specific setting
claude-mpm config get model
claude-mpm config get subprocess.memory_limit_mb

# Show configuration sources
claude-mpm config sources
```

### Modify Configuration

```bash
# Set user configuration
claude-mpm config set model sonnet
claude-mpm config set subprocess.enabled true

# Set project configuration
claude-mpm config set --project model opus

# Unset configuration
claude-mpm config unset debug
```

### Validate Configuration

```bash
# Check configuration validity
claude-mpm config validate

# Test configuration
claude-mpm config test
```

## Troubleshooting Configuration

### Common Issues

**Configuration not loading**:
```bash
# Check file permissions
ls -la ~/.claude-mpm/config.yml

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('.claude-mpm.yml'))"
```

**Environment variables not working**:
```bash
# Check variable is exported
echo $CLAUDE_MPM_MODEL

# Debug environment
claude-mpm info --verbose | grep Environment
```

**Wrong precedence**:
```bash
# Show all configuration sources
claude-mpm config sources --verbose

# Show effective configuration
claude-mpm config show --effective
```

## Best Practices

### 1. Use Project Config for Team Settings

```yaml
# .claude-mpm.yml (commit to git)
model: opus  # Team standard
subprocess:
  enabled: true
  memory_limit_mb: 4096
tickets:
  patterns: ["TODO:", "FIXME:", "BUG:"]
```

### 2. Use User Config for Personal Preferences

```yaml
# ~/.claude-mpm/config.yml (personal)
debug: true  # Your preference
session_dir: ~/my-claude-sessions
logging:
  level: DEBUG
```

### 3. Use Environment Variables for Secrets

```bash
# Don't put secrets in config files
export CLAUDE_MPM_API_KEY="secret-key"
export CLAUDE_MPM_WEBHOOK_URL="https://..."
```

### 4. Use Profiles for Different Contexts

```bash
# Development
claude-mpm --profile dev

# Production
claude-mpm --profile prod

# Quick tasks
claude-mpm --profile fast
```

## Next Steps

- See [CLI Commands](cli-commands.md) for command usage
- Check [Troubleshooting](troubleshooting.md) for issues
- Review [Basic Usage](../02-guides/basic-usage.md) for examples
- Explore [Features](../03-features/README.md) configuration