# ❓ Claude MPM FAQ

**Frequently Asked Questions**
**Version 4.3.3** | Last Updated: September 19, 2025

## 🚀 Getting Started

### Q: What is Claude MPM and how is it different from regular Claude Code?
**A:** Claude MPM (Multi-Agent Project Manager) extends Claude Code with:
- **15+ specialized agents** that automatically handle different aspects of development
- **Persistent sessions** that remember your work across interactions
- **Real-time monitoring** dashboard to see agent collaboration
- **Project memory** that learns your coding patterns and preferences

Think of it as giving Claude Code a team of expert assistants that work together on your projects.

### Q: Do I need special permissions or subscriptions?
**A:** No special permissions needed! Claude MPM works with:
- ✅ Any Claude Code subscription (Free, Pro, Team)
- ✅ Standard Python 3.8+ installation
- ✅ No additional API keys or external services required

### Q: What's the difference between `pip install claude-mpm` and `pipx install "claude-mpm[monitor]"`?
**A:**
- **`pip install claude-mpm`**: Basic installation, works in virtual environments
- **`pipx install "claude-mpm[monitor]"`**: Recommended installation with:
  - Real-time monitoring dashboard
  - Socket.IO support for live updates
  - Isolated environment (pipx best practice)
  - Full feature set including web interface

**Recommendation**: Use pipx with monitor support for the complete experience.

## 🤖 Agent System

### Q: How does the multi-agent system work?
**A:** Claude MPM uses a three-tier agent hierarchy:
1. **PM (Project Manager)**: Orchestrates and delegates tasks
2. **Specialists**: 15+ expert agents (Engineer, QA, Documentation, Security, etc.)
3. **Automatic Routing**: PM analyzes your request and assigns to appropriate specialists

**Example**: "Improve this code" → PM → Engineer (refactoring) → QA (testing) → Documentation (updates)

### Q: Can I see which agents are working on my tasks?
**A:** Yes! Use the monitoring dashboard:
```bash
claude-mpm run --monitor
```
Visit http://localhost:8765 to see:
- Which agents are currently active
- Task delegation flow
- File operations in real-time
- Agent collaboration patterns

### Q: Can I create custom agents for my project?
**A:** Absolutely! Create project-specific agents:
```bash
# Create agent directory
mkdir -p .claude-mpm/agents

# Create custom agent (example)
cat > .claude-mpm/agents/my_expert.md << 'EOF'
---
description: Expert in my project's specific patterns
version: 1.0.0
---
# My Project Expert
Specialized knowledge of our coding standards...
EOF
```

See [Agent Creation Guide](../developer/07-agent-system/creation-guide.md) for details.

### Q: Do agents remember things between sessions?
**A:** Yes! The memory system provides:
- **Project-specific learning**: Agents remember your coding patterns
- **Persistent knowledge**: Retained across sessions and restarts
- **Simple updates**: Use JSON `remember` field in responses
- **Initialization**: Run `claude-mpm memory init` to start learning

## 🔧 Usage & Features

### Q: What are Claude Code slash commands and how do they work?
**A:** Claude MPM adds special commands to Claude Code sessions:
- **`/mpm-doctor`**: Health check and diagnostics
- **`/mpm-init`**: Initialize project for Claude MPM
- **`/mpm-agents`**: Manage and deploy agents
- **`/mpm-resume`**: Resume previous session

These work automatically in any Claude Code session once Claude MPM is installed.

### Q: How do I resume a previous session?
**A:** Multiple ways:
```bash
# Command line
claude-mpm resume

# In Claude Code session
/mmp-resume

# Or specify session
claude-mpm resume --session <session-id>
```

All your work, context, and agent memories are automatically restored.

### Q: What is the MCP Gateway?
**A:** The MCP (Model Context Protocol) Gateway enables:
- **External tool integration**: Connect Claude MPM to other services
- **Custom tool development**: Build your own integrations
- **Protocol-based communication**: Standard interface for extensions
- **Extensible architecture**: Add capabilities without modifying core

Start with: `claude-mpm mcp`

### Q: How do I clean up old conversation history?
**A:** Use the cleanup command:
```bash
# Clean old conversations (default: 30 days)
claude-mpm cleanup-memory

# Keep only recent conversations
claude-mpm cleanup-memory --days 7

# See what would be cleaned (dry run)
claude-mpm cleanup-memory --dry-run
```

This helps manage memory usage for large conversation histories.

## 🐛 Troubleshooting

### Q: "Agent not found" error - what does this mean?
**A:** This usually means agent deployment issues. Fix with:
```bash
# Diagnose the problem
claude-mpm doctor

# Or check agent status
claude-mpm agents list

# Deploy agents if needed
claude-mpm agents deploy
```

See [Troubleshooting Guide](troubleshooting.md) for detailed solutions.

### Q: The monitoring dashboard won't load at http://localhost:8765
**A:** Common causes and fixes:
1. **Missing monitor dependencies**:
   ```bash
   pipx install "claude-mpm[monitor]"
   ```
2. **Port already in use**:
   ```bash
   # Check what's using port 8765
   lsof -i :8765
   # Or use different port
   claude-mpm run --monitor --port 8766
   ```
3. **Check dependencies**:
   ```bash
   python scripts/check_monitor_deps.py
   ```

### Q: Commands like `claude-mpm` not found after installation
**A:** Path issues. Solutions:
1. **For pipx users**:
   ```bash
   pipx ensurepath
   source ~/.bashrc  # or ~/.zshrc
   ```
2. **For pip users**: Make sure virtual environment is activated
3. **Manual path**: Add to your shell profile:
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```

### Q: "Permission denied" or "Access denied" errors
**A:** Usually file permission issues:
```bash
# Check permissions
ls -la ~/.claude-mpm/

# Fix permissions
chmod -R 755 ~/.claude-mpm/
chmod -R 644 ~/.claude-mpm/*.json

# For project agents
chmod -R 755 .claude-mpm/
```

### Q: Performance is slow or agents take a long time
**A:** Performance optimization:
1. **Enable caching** (automatic in v4.3.3+)
2. **Check system resources**:
   ```bash
   claude-mpm doctor --verbose
   ```
3. **Clean up memory**:
   ```bash
   claude-mpm cleanup-memory
   ```
4. **Optimize project size**: Large projects may need longer processing

## 🔄 Migration & Updates

### Q: How do I upgrade from an older version?
**A:** Safe upgrade process:
```bash
# Backup current setup
cp -r ~/.claude-mpm ~/.claude-mpm-backup

# Upgrade
pipx upgrade claude-mpm
# or for pip: pip install --upgrade claude-mpm

# Check version
claude-mpm --version

# Run health check
claude-mpm doctor
```

See [Migration Guide](MIGRATION.md) for version-specific instructions.

### Q: Can I use Claude MPM with existing projects?
**A:** Yes! Claude MPM works with any project:
1. **Navigate to project directory**
2. **Run**: `claude-mpm` or `/mpm-init` in Claude Code
3. **Optional**: Create project-specific agents in `.claude-mpm/agents/`
4. **Optional**: Initialize memory: `claude-mpm memory init`

No modifications to existing code required.

### Q: What happens to my data if I uninstall?
**A:** Your data locations:
- **Agent memories**: `~/.claude-mpm/memories/`
- **Session data**: `~/.claude-mpm/sessions/`
- **Project agents**: `.claude-mpm/agents/` (in each project)

Data persists after uninstall. To completely remove:
```bash
# Uninstall
pipx uninstall claude-mpm

# Remove data (optional)
rm -rf ~/.claude-mpm
rm -rf .claude-mpm  # In each project directory
```

## 🏗️ Advanced Usage

### Q: Can I run Claude MPM in CI/CD pipelines?
**A:** Yes! Use non-interactive mode:
```bash
# Non-interactive execution
claude-mpm run -i "analyze code quality" --non-interactive

# With specific output format
claude-mpm run -i "generate test report" --output json

# In CI environments
claude-mpm doctor --quiet  # Exit codes for automation
```

### Q: How do I integrate with external tools?
**A:** Use the MCP Gateway:
1. **Start MCP server**: `claude-mpm mcp`
2. **Configure tools**: See [MCP Documentation](03-features/mcp-gateway.md)
3. **Custom integrations**: Develop protocol-compliant tools
4. **Examples**: Database connections, API integrations, custom workflows

### Q: Can I modify agent behavior or create agent templates?
**A:** Yes! Several approaches:
1. **Custom project agents**: `.claude-mpm/agents/my_agent.md`
2. **Agent templates**: See [Schema Reference](../developer/10-schemas/agent_schema_documentation.md)
3. **Memory configuration**: Influence agent learning patterns
4. **Service customization**: Advanced - modify service layer behavior

See [Developer Documentation](../developer/README.md) for advanced customization.

## 🤝 Support & Community

### Q: Where can I get help if my question isn't answered here?
**A:** Support resources:
1. **📖 [Troubleshooting Guide](troubleshooting.md)** - Comprehensive problem-solving
2. **🐛 [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues)** - Report bugs and get help
3. **📚 [Complete Documentation](../README.md)** - Full feature reference
4. **💻 [Developer Guide](../developer/README.md)** - Technical details

### Q: How can I contribute to Claude MPM?
**A:** We welcome contributions!
1. **Start with**: [Contributing Guide](../developer/03-development/README.md)
2. **Understand architecture**: [Architecture Overview](../developer/ARCHITECTURE.md)
3. **Follow standards**: [Development Standards](../developer/README.md#documentation-standards)
4. **Submit PRs**: Follow quality workflow: `make lint-fix` → `make quality` → `make test`

### Q: Is Claude MPM open source?
**A:** Yes! Claude MPM is open source under MIT License:
- **Source**: [GitHub Repository](https://github.com/bobmatnyc/claude-mpm)
- **License**: MIT - see [LICENSE](../../LICENSE) file
- **Contributing**: All contributions welcome following our guidelines
- **Community**: Built by and for the Claude Code community

---

**❓ Don't see your question?**
- Check the [Troubleshooting Guide](troubleshooting.md) for technical issues
- Browse [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues) for known problems
- Create a new issue with the "question" label for community help