# Frequently Asked Questions (FAQ)

## General Questions

### What is Claude MPM?

Claude MPM (Multi-Agent Project Manager) is a powerful orchestration framework for Claude Code (CLI) that enables multi-agent workflows, session management, and real-time monitoring through a streamlined Rich-based interface.

### Do I need Claude Desktop or Claude Code?

**You need Claude Code CLI** (v1.0.92+), NOT Claude Desktop (the app). All MCP integrations work with Claude Code's CLI interface only.

- **Minimum version**: v1.0.92 (hooks support)
- **Recommended**: v2.0.30+ (latest features)
- **Install from**: https://docs.anthropic.com/en/docs/claude-code

### What's the difference between Claude Code and Claude Desktop?

- **Claude Code (CLI)**: Command-line interface for developers with MCP support, hooks, and automation
- **Claude Desktop (App)**: GUI application for general use without CLI features

Claude MPM requires the CLI version for its orchestration capabilities.

## Installation & Setup

### How do I install Claude MPM?

```bash
# Recommended: Install with monitoring dashboard
pipx install "claude-mpm[monitor]"

# Or with pip
pip install "claude-mpm[monitor]"

# Verify installation
claude-mpm --version
claude-mpm doctor
```

See [Installation Guide](../user/installation.md) for detailed instructions.

### What are the system requirements?

- **Python**: 3.8+ (3.11+ recommended)
- **Claude Code CLI**: v1.0.92 or higher
- **Operating System**: macOS, Linux, or Windows
- **Disk Space**: ~50MB for base installation
- **RAM**: Minimum 2GB available

### Should I use pip or pipx?

**pipx is recommended** for isolated installations:

```bash
# pipx (recommended) - isolated environment
pipx install "claude-mpm[monitor]"

# pip - global/virtualenv installation
pip install "claude-mpm[monitor]"
```

**Benefits of pipx:**
- ✅ Isolated environments prevent dependency conflicts
- ✅ Automatic PATH configuration
- ✅ Easy upgrades with `pipx upgrade claude-mpm`
- ✅ Fully supported

### What optional dependencies should I install?

**Recommended:**
- `[monitor]` - Full monitoring dashboard (Socket.IO, web server)
- `kuzu-memory` - Advanced memory management (separate package)
- `mcp-vector-search` - Semantic code search (separate package)

**Most users don't need:**
- `[mcp]` - Additional MCP services (mcp-browser, mcp-ticketer)

## Usage Questions

### How do I start Claude MPM?

```bash
# Interactive mode (recommended for beginners)
claude-mpm

# With monitoring dashboard
claude-mpm run --monitor

# Resume previous session
claude-mpm run --resume

# Use semantic code search
claude-mpm search "authentication logic"
```

See [Getting Started](../getting-started/) for complete usage.

### What are agents and how do they work?

Agents are specialized AI assistants that handle specific tasks:

- **PM (Project Manager)**: Orchestrates workflow and delegates to specialists
- **Engineer**: Software development and implementation
- **QA**: Testing and quality assurance
- **Documentation**: Creates and maintains docs
- **Security**: Security analysis and implementation
- **Research**: Code analysis and research

See [Agent System Overview](../AGENTS.md) for details.

### How do I use the monitoring dashboard?

```bash
# Start with monitoring
claude-mpm run --monitor

# Dashboard opens automatically at http://localhost:5000
```

The dashboard shows:
- Live agent activity
- File operations
- Session management
- Performance metrics

See [Monitoring Guide](../MONITOR.md) for details.

### What is the resume log system?

The Resume Log System automatically generates structured 10k-token logs when approaching Claude's context window limits, enabling seamless session continuity.

**Key features:**
- 🎯 Warnings at 70%, 85%, and 95% thresholds
- 📋 Structured logs for session resumption
- 🔄 Automatic context preservation
- ⚙️ Zero-configuration operation

See [Resume Logs Guide](../user/resume-logs.md) for complete documentation.

## Configuration Questions

### Where are configuration files stored?

```
~/.claude-mpm/                    # User-level configuration
  ├── configuration.yaml          # Main configuration
  ├── agents/                     # Custom agents
  └── skills/                     # Custom skills

.claude-mpm/                      # Project-level configuration
  ├── configuration.yaml          # Project config
  ├── agents/                     # Project agents
  ├── skills/                     # Project skills
  └── resume-logs/                # Session resume logs
```

See [Configuration Reference](../configuration.md) for details.

### How do I configure agents?

```bash
# Interactive configuration
claude-mpm configure

# Manual configuration
edit ~/.claude-mpm/configuration.yaml
```

See [User Guide - Configuration](../user/user-guide.md#configuration) for options.

### How do I manage skills?

```bash
# Interactive skills management
claude-mpm configure
# Choose option 2: Skills Management

# Skills are stored in:
# - Bundled: ~/.local/share/claude-mpm/skills/
# - User: ~/.config/claude-mpm/skills/
# - Project: .claude-mpm/skills/
```

See [Skills Guide](../user/skills-guide.md) for details.

## Troubleshooting

### Claude MPM won't start - what should I check?

```bash
# Run comprehensive diagnostics
claude-mpm doctor

# Check verbose output
claude-mpm doctor --verbose

# Check specific component
claude-mpm doctor --checks installation
```

Common issues:
1. **Claude Code not installed**: Install from https://docs.anthropic.com/en/docs/claude-code
2. **Wrong version**: Upgrade to v1.0.92+ with `claude upgrade`
3. **PATH issues**: Ensure `claude` command is accessible
4. **Python version**: Requires Python 3.11+ (kuzu-memory dependency)

See [Troubleshooting Guide](../user/troubleshooting.md) for solutions.

### How do I check for updates?

```bash
# Check for Claude MPM updates
claude-mpm doctor --checks updates

# Check Claude Code version
claude --version

# Update Claude MPM
pipx upgrade claude-mpm  # if installed with pipx
pip install --upgrade claude-mpm  # if installed with pip
```

Updates are automatically checked on startup (configurable in `configuration.yaml`).

### Memory usage is too high - what can I do?

Large conversation histories can consume 2GB+ of memory. Clean up old conversations:

```bash
# Clean up old conversation history
claude-mpm cleanup-memory

# Keep only recent conversations (last 7 days)
claude-mpm cleanup-memory --days 7
```

See [User Guide - Memory Management](../user/user-guide.md#memory-management) for details.

### How do I verify MCP services?

```bash
# Verify all MCP services
claude-mpm verify

# Auto-fix issues
claude-mpm verify --fix

# Verify specific service
claude-mpm verify --service kuzu-memory

# Get JSON output for automation
claude-mpm verify --json
```

See [MCP Gateway Documentation](../developer/13-mcp-gateway/README.md) for details.

## Advanced Questions

### Can I create custom agents?

Yes! Claude MPM supports three tiers of agents:

1. **System**: Bundled agents (read-only)
2. **User**: Custom agents in `~/.claude-mpm/agents/`
3. **Project**: Project-specific agents in `.claude-mpm/agents/`

See [Creating Agents](../agents/creating-agents.md) for step-by-step guide.

### How does the memory system work?

Agents learn project-specific patterns using a simple list format and can update memories via JSON response fields:

- `remember`: Incremental updates (add new learnings)
- `MEMORIES`: Complete replacement

Initialize with `claude-mpm memory init`.

See [Memory Integration](../developer/memory-integration.md) for technical details.

### What is the MCP Gateway?

The MCP Gateway enables integration with external tools and services through the Model Context Protocol:

- Custom tool development
- Protocol-based communication
- Extensible architecture
- Support for third-party MCP servers

See [MCP Gateway Documentation](../developer/13-mcp-gateway/README.md) for details.

### How do I contribute to Claude MPM?

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run quality checks: `make quality`
5. Submit pull request

See [Developer Guide](../developer/README.md) and [Contributing Guidelines](../developer/extending.md) for details.

## Integration Questions

### Does Claude MPM work with kuzu-memory?

Yes! `kuzu-memory` is a **recommended partner product** that provides:

- 🧠 Persistent project-specific knowledge graphs
- 🎯 Intelligent prompt enrichment
- 📊 Structured storage of project knowledge
- 🔄 Seamless zero-configuration integration

Install with: `pipx install kuzu-memory`

See [README - Recommended Partner Products](../../README.md#recommended-partner-products) for details.

### Does Claude MPM work with mcp-vector-search?

Yes! `mcp-vector-search` is another **recommended partner product** that enables:

- 🔍 Semantic code search by intent
- 🎯 Context-aware code discovery
- ⚡ Fast indexing for large codebases
- 📊 Pattern recognition and refactoring opportunities

Install with: `pipx install mcp-vector-search`

Use with: `claude-mpm search "authentication logic"` or `/mpm-search` in Claude Code sessions.

### What other MCP servers are supported?

Claude MPM includes MCP Gateway which supports:

- **Built-in**: mcp-browser, mcp-ticketer, filesystem, github
- **Partner**: kuzu-memory, mcp-vector-search
- **Custom**: Any MCP-compliant server

See [MCP Gateway Documentation](../developer/13-mcp-gateway/README.md) for integration details.

## Performance Questions

### Why is startup slow?

Claude MPM includes major performance optimizations:

- 91% latency reduction in hook system
- Git branch caching with 5-minute TTL
- Non-blocking HTTP fallback
- 50-80% overall improvement

If still slow:
1. Check network connectivity (MCP gateway initialization)
2. Disable unused agents in configuration
3. Reduce monitoring frequency if using `--monitor`

### How do I improve context management?

Use the Resume Log System:

- Automatic warnings at 70%/85%/95% thresholds
- 10k-token structured logs preserve context
- Seamless session resumption
- Zero configuration required

See [Resume Logs Guide](../user/resume-logs.md) for details.

### Can I disable features I don't use?

Yes, configure in `configuration.yaml`:

```yaml
# Disable auto-save
session:
  auto_save:
    enabled: false

# Disable resume logs
context_management:
  resume_logs:
    enabled: false

# Disable monitoring
monitoring:
  enabled: false
```

See [Configuration Reference](../configuration.md) for all options.

## See Also

- **[Getting Started Guide](../getting-started/)** - Installation and first steps
- **[User Guide](../user/user-guide.md)** - Complete feature documentation
- **[Troubleshooting Guide](../user/troubleshooting.md)** - Common issues and solutions
- **[Developer Guide](../developer/README.md)** - Technical documentation
- **[Agent System](../AGENTS.md)** - Agent development guide

---

**Still have questions?** Check the [Documentation Hub](../README.md) or open an issue on [GitHub](https://github.com/bobmatnyc/claude-mpm/issues).
