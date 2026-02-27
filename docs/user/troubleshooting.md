---
title: Troubleshooting
version: 4.21.1
last_updated: 2025-11-09
status: current
---

# Troubleshooting

Common issues and solutions for Claude MPM.

## Table of Contents

- [Installation Issues](#installation-issues)
  - [Claude Code Not Installed](#claude-code-not-installed)
  - [Claude Code Version Outdated](#claude-code-version-outdated)
  - [Command Not Found](#command-not-found-claude-mpm)
  - [Monitor Dashboard Issues](#monitor-dashboard-wont-load)
  - [Python Version Mismatch](#python-version-mismatch)
  - [Dependency Conflicts](#dependency-conflicts)
- [Agent Issues](#agent-issues)
  - [Agent not found Error](#agent-not-found-error)
  - [Agent Won't Load](#agent-wont-load)
  - [PM Agent Not Delegating](#pm-agent-not-delegating)
  - [Agent Source Issues](#agent-source-issues)
    - [Agent Source Update Timeout](#agent-source-update-timeout)
    - [Git Authentication Failures](#git-authentication-failures)
    - [Agent Not Found from Source](#agent-not-found-from-source)
    - [Priority Conflicts](#priority-conflicts)
    - [Common Error Messages](#common-error-messages)
- [Skill Source Issues](#skill-source-issues)
  - [GitHub API Rate Limit (HTTP 403)](#github-api-rate-limit-http-403)
- [Monitoring Issues](#monitoring-issues)
- [Local Deployment Issues](#local-deployment-issues)
- [Memory Issues](#memory-issues)
- [Session Issues](#session-issues)
- [Performance Issues](#performance-issues)
- [Update Checking Issues](#update-checking-issues)
  - [Update Checks Not Running](#update-checks-not-running)
  - [False Update Notifications](#false-update-available-notifications)
  - [Update Check Timeouts](#update-check-timeouts)
  - [Claude Code Compatibility Warnings](#claude-code-compatibility-warnings)
- [Diagnostics](#diagnostics)

## Installation Issues

### Claude Code Not Installed

**Problem**: `claude: command not found` or Claude MPM reports Claude Code missing.

**Why This Matters**: Claude MPM requires Claude Code CLI (v1.0.92+) to function. It's not the same as Claude Desktop.

**Solutions:**

```bash
# 1. Check if Claude Code is installed
which claude
claude --version

# 2. Install Claude Code if missing
# Visit: https://docs.anthropic.com/en/docs/claude-code
# Download and install for your platform

# 3. Verify Claude Code is in PATH
# Add to ~/.bashrc or ~/.zshrc if needed:
export PATH="$PATH:$HOME/.local/bin"  # Adjust path as needed
source ~/.bashrc  # or ~/.zshrc

# 4. Verify installation
claude --version  # Should show v1.0.92 or higher

# 5. Run Claude MPM diagnostics
claude-mpm doctor
```

**Version Requirements:**
- **Minimum**: v1.0.92 (hooks support)
- **Recommended**: v2.0.30+ (latest features)

### Claude Code Version Outdated

**Problem**: Claude Code version is below v1.0.92.

**Solutions:**

```bash
# Check current version
claude --version

# Update Claude Code
# Method depends on installation method:

# Homebrew (macOS):
brew upgrade claude

# Manual installation:
# Download latest from https://docs.anthropic.com/en/docs/claude-code

# Verify update
claude --version

# Confirm compatibility
claude-mpm doctor --checks updates
```

**Feature Availability by Version:**

| Feature | Minimum Version | Recommended Version |
|---------|----------------|---------------------|
| Basic hooks support | v1.0.92 | v2.0.30+ |
| Full MCP integration | v2.0.12 | v2.0.30+ |
| Update checking | v1.0.92 | v2.0.30+ |

### "command not found: claude-mpm"

**Problem**: Claude MPM not in PATH after installation.

**Solutions:**

```bash
# If installed with pipx
pipx ensurepath
source ~/.bashrc  # or ~/.zshrc

# Verify installation
which claude-mpm
claude-mpm --version

# Reinstall if needed
pipx reinstall claude-mpm
```

### Monitor Dashboard Won't Load

**Problem**: Installed without `[monitor]` extra.

**Solution:**

```bash
# Reinstall with monitor support
pipx uninstall claude-mpm
pipx install "claude-mpm[monitor]"

# Verify
claude-mpm doctor --checks monitor
```

### Python Version Mismatch

**Problem**: Python version is incompatible (too old or too new).

**Version Requirements:**
- **Minimum**: Python 3.11
- **Recommended**: Python 3.13
- **NOT Supported**: Python 3.14 (not yet compatible)
- **Too Old**: Python 3.9, 3.10 (macOS default 3.9 is too old)

**Solution:**

```bash
# Check version
python --version

# Install Python 3.13 (recommended)
# On macOS with Homebrew:
brew install python@3.13

# On Ubuntu:
sudo apt install python3.13

# Use explicit Python version with uv:
cd ~
uv tool install "claude-mpm[monitor,data-processing]" --python 3.13
```

**macOS Users**: The default system Python is 3.9, which is too old. Always use the `--python 3.13` flag when installing with uv:

```bash
cd ~
uv tool install "claude-mpm[monitor,data-processing]" --python 3.13
```

**Python 3.14 Users**: Python 3.14 is not yet supported. Downgrade to Python 3.13:

```bash
# Install Python 3.13
brew install python@3.13

# Reinstall claude-mpm with Python 3.13
uv tool uninstall claude-mpm
uv tool install "claude-mpm[monitor,data-processing]" --python 3.13
```

### Installation Location Issues

**Problem**: Installation conflicts or unexpected behavior when installing from within a git repository.

**Cause**: Installing claude-mpm while inside the cloned git repository causes path conflicts.

**Solution**: Always install from your home directory:

```bash
# CORRECT - Install from home directory
cd ~
uv tool install "claude-mpm[monitor,data-processing]" --python 3.13

# WRONG - Do NOT install from within the git repo
cd ~/Projects/claude-mpm  # <-- This causes problems!
uv tool install claude-mpm  # <-- Will fail or behave unexpectedly
```

**If you already installed from the git repo:**

```bash
# Uninstall
cd ~
uv tool uninstall claude-mpm

# Reinstall correctly
uv tool install "claude-mpm[monitor,data-processing]" --python 3.13
```

### Pre-Doctor Setup Missing

**Problem**: `claude-mpm doctor` fails with errors about missing directories, agents, or skills.

**Cause**: Post-installation setup steps were not completed.

**Solution**: Run these commands before `claude-mpm doctor`:

```bash
# 1. Create required directories
mkdir -p ~/.claude/{responses,memory,logs}

# 2. Deploy agents
claude-mpm agents deploy

# 3. Add skill source (recommended)
claude-mpm skill-source add https://github.com/bobmatnyc/claude-mpm-skills

# 4. Now run doctor
claude-mpm doctor --verbose
```

**Complete Post-Installation Checklist:**

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `mkdir -p ~/.claude/{responses,memory,logs}` | Create required directories |
| 2 | `claude-mpm agents deploy` | Deploy agent definitions |
| 3 | `claude-mpm skill-source add https://github.com/bobmatnyc/claude-mpm-skills` | Add skill repository |
| 4 | `claude-mpm doctor --verbose` | Verify installation |
| 5 | `claude-mpm auto-configure` | Configure for your project |

### Dependency Conflicts

**Problem**: pip reports dependency conflicts.

**Solution:**

```bash
# Use pipx for isolated installation
pipx install "claude-mpm[monitor]"

# Or create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install "claude-mpm[monitor]"
```

## Agent Issues

### "Agent not found" Error

**Problem**: Agent file missing or corrupted.

**Solutions:**

```bash
# Diagnose
claude-mpm doctor
# or in Claude session:
/mpm-doctor

# Redeploy system agents
claude-mpm agents deploy --system

# List available agents
claude-mpm agents list --by-tier
```

### Agent Won't Load

**Problem**: Syntax error or invalid frontmatter in agent file.

**Solutions:**

```bash
# Validate agent
claude-mpm agents validate

# Check specific agent
claude-mpm agents validate --agent pm

# View validation errors (detailed)
claude-mpm agents validate --verbose
```

**Common issues:**
- Missing required frontmatter fields (`name`, `model`, `instructions`)
- Invalid YAML in frontmatter block
- Unescaped special characters in instructions
- Wrong file extension (must be `.md`)

### PM Agent Not Delegating

**Problem**: PM agent handles tasks directly instead of delegating.

**Checklist:**
1. Verify specialist agents are loaded: `claude-mpm agents list`
2. Check PM agent instructions include delegation patterns
3. Ensure task matches specialist capabilities
4. Review with monitoring: `claude-mpm run --monitor`

**Common causes:**
- Specialist agent files missing
- Task too simple (doesn't require delegation)
- PM instructions modified incorrectly

### Agent Source Issues

Claude MPM uses git-first architecture for agent deployment. Agents are sourced from Git repositories by default.

**Documentation:**
- [Agent Sources User Guide](agent-sources.md) - Complete guide with examples
- [CLI Reference](../reference/cli-agent-source.md) - All `agent-source` commands
- [Migration Guide](../migration/agent-sources-git-default-v4.5.0.md) - Historical reference (v4.x)

**Quick Diagnostics:**
```bash
# Check agent source health
claude-mpm doctor --checks agent-sources --verbose

# List all sources
claude-mpm agent-source list

# Update all sources
claude-mpm agent-source update
```

#### Agent Source Update Timeout

**Problem**: `agent-source update` times out or hangs.

**Causes:**
- Slow network connection
- Large repository size
- GitHub API rate limiting
- Firewall blocking GitHub

**Solutions:**

```bash
# 1. Check network connectivity
ping github.com
curl -I https://github.com

# 2. Run diagnostics
claude-mpm doctor --checks agent-sources --verbose

# 3. Use --force to bypass cache
claude-mpm agent-source update --force

# 4. Update specific source only
claude-mpm agent-source update <source-id>

# 5. Check GitHub status
# Visit: https://www.githubstatus.com/
```

#### Git Authentication Failures

**Problem**: `Authentication failed` or `Permission denied` errors.

**Causes:**
- Private repositories without credentials
- Expired access tokens
- SSH key authentication (not supported)

**Solutions:**

```bash
# 1. Use HTTPS URLs (not SSH)
# ✓ Correct: https://github.com/owner/repo
# ✗ Wrong: git@github.com:owner/repo.git

# 2. For private repos, use personal access token
claude-mpm agent-source add \
  https://YOUR_TOKEN@github.com/owner/private-repo

# 3. Verify repository accessibility
curl -I https://github.com/owner/repo

# 4. Check repository is public or you have access
```

**Security note:** Store tokens securely, never commit them.

#### Agent Not Found from Source

**Problem**: Agent exists in source but not available for deployment.

**Diagnosis:**

```bash
# 1. List sources and check status
claude-mpm agent-source list

# 2. Update sources
claude-mpm agent-source update --force

# 3. Show source details with agents
claude-mpm agent-source show <source-id> --agents

# 4. Check cache directory
ls -la ~/.claude-mpm/agent-sources/<source-id>/

# 5. Run diagnostics
claude-mpm doctor --checks agent-sources --verbose
```

**Solutions:**

```bash
# Enable disabled source
claude-mpm agent-source enable <source-id>

# Force sync
claude-mpm agent-source update --force

# Clear cache and re-sync
rm -rf ~/.claude-mpm/agent-sources/<source-id>/
claude-mpm agent-source update <source-id>

# Verify agent file format
cat ~/.claude-mpm/agent-sources/<source-id>/<agent>.md
```

#### Priority Conflicts

**Problem**: Wrong agent version deployed, unexpected agent behavior.

**Causes:**
- Multiple sources with same priority
- Multiple sources providing same agent name
- Misunderstanding priority order (lower = higher precedence)

**Diagnosis:**

```bash
# 1. Check priority configuration
claude-mpm agent-source list --by-priority

# 2. Run conflict detection
claude-mpm doctor --checks agent-sources --verbose

# 3. Check deployed agent source
claude-mpm agents list-deployed
```

**Solutions:**

```bash
# Set distinct priorities (remove and re-add)
claude-mpm agent-source remove source1
claude-mpm agent-source add <url1> --priority 10

# Disable conflicting source temporarily
claude-mpm agent-source disable source2

# Use project-local override (highest priority)
cp ~/.claude-mpm/agent-sources/source1/agent.md \
   .claude-mpm/agents/agent.md

# Redeploy with --force
claude-mpm agents deploy <agent-name> --force
```

**Best practice:** Use distinct priority ranges (see [Agent Sources Guide - Priority System](agent-sources.md#priority-system)).

#### Common Error Messages

**Error: `Source already configured`**

```bash
# Check existing sources
claude-mpm agent-source list

# Remove old source first
claude-mpm agent-source remove <source-id>

# Re-add with new settings
claude-mpm agent-source add <url> --priority <new-priority>
```

**Error: `Invalid Git URL format`**

```bash
# ✓ Valid formats:
https://github.com/owner/repo
https://github.com/owner/repo.git

# ✗ Invalid formats:
git@github.com:owner/repo.git  # SSH not supported
github.com/owner/repo          # Missing protocol
```

**Error: `Failed to fetch repository`**

```bash
# Verify URL manually
curl -I https://github.com/owner/repo

# For private repos, use token
claude-mpm agent-source add \
  https://TOKEN@github.com/owner/private-repo

# Check network/firewall
ping github.com
```

**Error: `No agents found in source`**

```bash
# Verify subdirectory path
claude-mpm agent-source show <source-id>

# Remove and re-add with correct subdirectory
claude-mpm agent-source remove <source-id>
claude-mpm agent-source add <url> --subdirectory correct/path

# Force update
claude-mpm agent-source update --force
```

## Skill Source Issues

### GitHub API Rate Limit (HTTP 403)

**Problem**: `skill-source add` or `skill-source update` fails with HTTP 403 error or rate limit message.

**Cause**: GitHub's API has rate limits:
- **Without authentication**: 60 requests/hour (shared by IP)
- **With authentication**: 5,000 requests/hour

**Symptoms:**
```
Error: HTTP 403 Forbidden
Error: rate limit exceeded
Error: API rate limit exceeded for IP address
```

**Solution**: Set a GitHub token in your environment:

```bash
# Option 1: Set GITHUB_TOKEN
export GITHUB_TOKEN=your_github_token

# Option 2: Set GH_TOKEN (also supported)
export GH_TOKEN=your_github_token

# Add to shell profile for persistence
echo 'export GITHUB_TOKEN=your_github_token' >> ~/.bashrc  # or ~/.zshrc
source ~/.bashrc  # or ~/.zshrc

# Retry the operation
claude-mpm skill-source add https://github.com/bobmatnyc/claude-mpm-skills
```

**Creating a GitHub Token:**

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a descriptive name (e.g., "claude-mpm")
4. **No scopes needed** for public repositories
5. Click "Generate token"
6. Copy the token and set it as shown above

**Token Requirements:**
- Only public repository read access is needed
- No special scopes required
- Classic tokens with no scopes selected work fine
- Fine-grained tokens with "Public Repositories (read-only)" also work

**Verify Token is Set:**

```bash
# Check if token is available
echo $GITHUB_TOKEN
# or
echo $GH_TOKEN

# Test GitHub API access
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/rate_limit
```

**Expected output shows higher limits:**
```json
{
  "rate": {
    "limit": 5000,
    "remaining": 4999,
    ...
  }
}
```

**If Still Failing:**

```bash
# Check current rate limit status
curl https://api.github.com/rate_limit

# Wait for rate limit reset (shown in response)
# Or use a different network/IP

# Clear any cached failures
rm -rf ~/.claude-mpm/cache/skill-sources/
claude-mpm skill-source update --force
```

## Monitoring Issues

### Dashboard Connection Refused

**Problem**: Cannot connect to http://localhost:8765

**Solutions:**

```bash
# Check if monitor is running
ps aux | grep "claude-mpm.*monitor"

# Kill existing monitor process
pkill -f "claude-mpm.*monitor"

# Restart with monitor
claude-mpm run --monitor

# Try different port
claude-mpm run --monitor --port 8766
```

### Dashboard Shows No Data

**Problem**: Dashboard loads but no agent activity visible.

**Solutions:**

1. Verify WebSocket connection in browser console
2. Check session is active: `claude-mpm status`
3. Restart monitor: Stop and `claude-mpm run --monitor`
4. Clear browser cache and reload

### Dashboard Disconnects Frequently

**Problem**: WebSocket connection drops repeatedly.

**Solutions:**

```bash
# Check firewall settings
# Allow port 8765

# Use different port
claude-mpm run --monitor --port 8080

# Check resource usage
claude-mpm doctor --checks performance
```

## Local Deployment Issues

### Deployment Won't Start

**Problem**: `local-deploy start` fails immediately.

**Solutions:**

```bash
# Check command is valid
npm run dev  # or your command

# Verify directory exists
cd /path/to/project
ls -la

# Check configuration
cat .claude-mpm/local-ops-config.yaml

# View detailed errors
claude-mpm local-deploy start --command "npm run dev" --verbose
```

**Common causes:**
- Invalid command
- Working directory doesn't exist
- Port already in use
- Missing dependencies (npm install, pip install, etc.)

### Health Check Failing

**Problem**: Deployment starts but health check fails.

**Solutions:**

```bash
# Check health URL manually
curl http://localhost:3000

# Increase initial delay
claude-mpm local-deploy start \
  --command "npm run dev" \
  --health-url "http://localhost:3000" \
  --health-initial-delay 30  # seconds

# Disable health check temporarily
claude-mpm local-deploy start \
  --command "npm run dev" \
  --no-health-check
```

**Configuration adjustment:**

```yaml
deployments:
  my-app:
    health_check:
      initial_delay: 30  # Increase if app is slow to start
      interval: 60       # Check less frequently
      timeout: 10        # Increase if endpoint is slow
```

### Auto-Restart Loop

**Problem**: Deployment restarts continuously.

**Solutions:**

```bash
# View logs
claude-mpm local-deploy logs <deployment-id>

# Check for errors
claude-mpm local-deploy monitor <deployment-id>

# Disable auto-restart temporarily
claude-mpm local-deploy start \
  --command "npm run dev" \
  --no-auto-restart
```

**Common causes:**
- Application crashes immediately (missing dependencies, config error)
- Port already in use
- Memory threshold too low
- Error pattern too broad

### Memory Threshold Alerts

**Problem**: Constant memory threshold warnings.

**Solutions:**

```bash
# Increase threshold
# Edit .claude-mpm/local-ops-config.yaml:
resource_monitoring:
  memory_threshold_mb: 1024  # Increase from 512

# Or disable
resource_monitoring:
  enabled: false
```

## Memory Issues

### Memory Not Persisting

**Problem**: Agent learnings don't persist across sessions.

**Solutions:**

```bash
# Verify memory system
claude-mpm stats

# Check if memories are being stored
claude-mpm recall "recent learning"

# Reinitialize project
claude-mpm init
```

**Checklist:**
- `.claude-mpm/` directory exists in project
- `memory.db` file present in `.claude-mpm/`
- Sufficient disk space

### Memory Queries Return Nothing

**Problem**: `claude-mpm recall` returns empty results.

**Solutions:**

```bash
# List all memories
claude-mpm recall ""

# Check memory stats
claude-mpm stats

# Verify memory storage format
# Agent must use correct JSON format:
{
  "memory-update": {
    "Project Architecture": ["info here"]
  }
}
```

### Memory Database Corrupted

**Problem**: Memory errors or crashes when querying.

**Solutions:**

```bash
# Backup existing
cp .claude-mpm/memory.db .claude-mpm/memory.db.backup

# Reinitialize (WARNING: loses memories)
rm .claude-mpm/memory.db
claude-mpm init

# Or restore from backup
cp .claude-mpm/memory.db.backup .claude-mpm/memory.db
```

## Session Issues

### Can't Resume Session

**Problem**: `/resume` or `claude-mpm run --resume` fails.

**Solutions:**

```bash
# List available sessions
ls .claude-mpm/sessions/

# Check session file integrity
cat .claude-mpm/sessions/<session-id>.json

# Verify session data
claude-mpm status

# Start new session if corrupted
claude-mpm run  # without --resume
```

### Session State Incomplete

**Problem**: Resumed session missing context.

**Solutions:**

1. Verify pause was successful: Check `.claude-mpm/sessions/` for recent files
2. Review git state: `git status` to see if changes were captured
3. Check todos: Session should restore todo list
4. Manual context: Provide additional context if needed

### Multiple Sessions Conflict

**Problem**: Multiple Claude sessions interfering.

**Solutions:**

```bash
# List active sessions
ps aux | grep claude-mpm

# Stop all sessions
pkill -f claude-mpm

# Start single session
claude-mpm run
```

## Performance Issues

### Slow Response Times

**Problem**: Agent responses taking too long.

**Solutions:**

```bash
# Check metrics
claude-mpm run --monitor
# View latency in dashboard

# Verify caching enabled
# Check .claude-mpm/config.yaml:
performance:
  caching:
    git_branch: true
    ttl: 300

# Clear corrupted cache
rm -rf .claude-mpm/cache/
```

### High Memory Usage

**Problem**: Claude MPM consuming excessive memory.

**Solutions:**

```bash
# Check memory usage
ps aux | grep claude-mpm

# Restart session
pkill -f claude-mpm
claude-mpm run

# Reduce cache size
# Edit .claude-mpm/config.yaml:
performance:
  cache_size_mb: 50  # Reduce from 100
```

### Hook System Slow

**Problem**: Hook execution causing delays.

**Solutions:**

```bash
# Disable unused hooks temporarily
# Edit .claude-mpm/config.yaml:
hooks:
  pre_execution:
    enabled: false

# Check hook execution times in monitor
claude-mpm run --monitor

# Review hook implementations
cat .claude-mpm/hooks/*
```

## Update Checking Issues

### Update Checks Not Running

**Problem**: No update notifications appear on startup.

**Solutions:**

```bash
# 1. Check configuration
cat ~/.claude-mpm/configuration.yaml | grep -A 6 "updates:"

# 2. Verify not disabled via environment variable
echo $CLAUDE_MPM_SKIP_UPDATE_CHECK

# 3. Check cache status
ls -la ~/.cache/claude-mpm/version-checks/

# 4. Clear cache and retry
rm -rf ~/.cache/claude-mpm/version-checks/
claude-mpm run

# 5. Enable debug mode to see update check logs
claude-mpm --debug run 2>&1 | grep -i "update\|upgrade"
```

**Configuration:**

Edit `~/.claude-mpm/configuration.yaml`:

```yaml
updates:
  check_enabled: true          # Must be true
  check_frequency: "daily"     # Try "always" for testing
  check_claude_code: true      # Enable Claude Code checks
```

### False "Update Available" Notifications

**Problem**: Update notification shows but version is already latest.

**Solutions:**

```bash
# 1. Clear version cache
rm -rf ~/.cache/claude-mpm/version-checks/

# 2. Verify installed version
claude-mpm --version
pip show claude-mpm | grep Version

# 3. Check PyPI for actual latest version
curl -s https://pypi.org/pypi/claude-mpm/json | grep -o '"version":"[^"]*"' | head -1

# 4. Reinstall if versions don't match
pipx reinstall claude-mpm
# or
pip install --force-reinstall claude-mpm
```

### Update Check Timeouts

**Problem**: Slow startup due to update checks.

**Solutions:**

```bash
# 1. Reduce check frequency
# Edit ~/.claude-mpm/configuration.yaml:
updates:
  check_frequency: "weekly"  # Instead of "daily" or "always"

# 2. Increase cache TTL (check less often)
updates:
  cache_ttl: 604800  # 7 days in seconds

# 3. Disable temporarily
CLAUDE_MPM_SKIP_UPDATE_CHECK=1 claude-mpm run

# 4. Disable permanently (not recommended)
updates:
  check_enabled: false
```

### Claude Code Compatibility Warnings

**Problem**: Warnings about Claude Code version on every startup.

**Solutions:**

```bash
# 1. Update Claude Code (recommended)
brew upgrade claude  # macOS with Homebrew
# or download from https://docs.anthropic.com/en/docs/claude-code

# 2. Verify version meets requirements
claude --version  # Should be v1.0.92+, ideally v2.0.30+

# 3. Disable Claude Code checking (not recommended)
# Edit ~/.claude-mpm/configuration.yaml:
updates:
  check_claude_code: false

# 4. Check for PATH issues
which claude
echo $PATH | grep -o '[^:]*claude[^:]*'
```

## Diagnostics

### System Diagnostics

```bash
# Full system check
claude-mpm doctor

# Specific checks
claude-mpm doctor --checks installation
claude-mpm doctor --checks agents
claude-mpm doctor --checks monitor
claude-mpm doctor --checks performance

# Verbose output
claude-mpm doctor --verbose
```

### In Claude Code Session

```bash
# Run diagnostics
/mpm-doctor

# Check agent status
/mpm-agents list

# Reinitialize project
/mpm-init
```

### Debug Mode

```bash
# Run with debug logging
claude-mpm run --debug

# Or set environment variable
export CLAUDE_MPM_DEBUG=1
claude-mpm run
```

### Logging

```bash
# View logs
tail -f .claude-mpm/logs/claude-mpm.log

# View specific log level
grep ERROR .claude-mpm/logs/claude-mpm.log

# View dashboard logs
tail -f .claude-mpm/logs/monitor.log
```

### Common Log Locations

- **Main log**: `.claude-mpm/logs/claude-mpm.log`
- **Monitor log**: `.claude-mpm/logs/monitor.log`
- **Deployment logs**: `.claude-mpm/logs/deployments/<deployment-id>.log`
- **Agent logs**: `.claude-mpm/logs/agents/<agent-name>.log`

## Getting More Help

### Collect Debug Information

```bash
# Generate debug report
claude-mpm doctor --report > debug-report.txt

# Include:
claude-mpm --version
python --version
pip show claude-mpm
ls -la .claude-mpm/
```

### Report Issues

1. Run `claude-mpm doctor --report`
2. Include relevant logs from `.claude-mpm/logs/`
3. Describe steps to reproduce
4. Report on GitHub Issues: https://github.com/bobmatnyc/claude-mpm/issues

### Quick Fixes

**Nuclear option** (loses configuration and memories):
```bash
# Backup first
cp -r .claude-mpm .claude-mpm.backup

# Remove configuration
rm -rf .claude-mpm

# Reinitialize
claude-mpm init
claude-mpm auto-configure
```

---

**Still stuck?** Check [User Guide](user-guide.md) or [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues).
