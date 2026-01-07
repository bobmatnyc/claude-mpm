# Doctor Command User Guide

Complete guide to using the `doctor` command for system diagnostics and health monitoring.

## Table of Contents

- [What is the Doctor Command?](#what-is-the-doctor-command)
- [Quick Start](#quick-start)
- [Common Use Cases](#common-use-cases)
- [Understanding Check Results](#understanding-check-results)
- [Agent Sources Health Checks](#agent-sources-health-checks)
- [Generating Reports](#generating-reports)
- [Troubleshooting Common Issues](#troubleshooting-common-issues)
- [Best Practices](#best-practices)

## What is the Doctor Command?

The `doctor` command is Claude MPM's comprehensive health diagnostic tool. It checks your installation, configuration, agents, and services to identify issues and provide solutions.

**Think of it as**:
- A health check for your Claude MPM installation
- A diagnostic tool for troubleshooting
- A report generator for sharing system status
- A validation tool before deployment

## Quick Start

### Run Your First Health Check

```bash
# Run all diagnostic checks
claude-mpm doctor
```

**Expected Output**:
```bash
Running diagnostics...

✅ Installation: OK
✅ Configuration: OK
✅ Filesystem: OK
✅ Claude Code: OK
✅ Agents: OK
✅ Agent Sources: OK
✅ MCP Services: OK
✅ Monitor: OK

🎉 Overall Status: Healthy
```

### Get Detailed Information

```bash
# Run with verbose output
claude-mpm doctor --verbose
```

### Generate a Report

```bash
# Create timestamped report file
claude-mpm doctor --output-file
```

## Common Use Cases

### 1. After Installation

**Scenario**: You just installed Claude MPM and want to verify everything works.

```bash
# Basic health check
claude-mpm doctor

# If issues found, get details
claude-mpm doctor --verbose
```

**What to look for**:
- ✅ All checks should pass
- ✅ Agents deployed successfully
- ✅ Configuration files created

**If something fails**:
```bash
# Try automatic fixes
claude-mpm doctor --fix

# Generate detailed report
claude-mpm doctor --verbose --output-file setup-report.md
```

### 2. Before Deployment

**Scenario**: You want to ensure your system is ready for production deployment.

```bash
# Check critical components
claude-mpm doctor --checks configuration agents agent-sources

# Generate compliance report
claude-mpm doctor --output-file pre-deployment-$(date +%Y%m%d).md
```

**What to verify**:
- ✅ Configuration valid
- ✅ Required agents present
- ✅ Agent sources accessible
- ✅ No critical errors

### 3. Troubleshooting Issues

**Scenario**: Claude MPM isn't working as expected.

```bash
# Run diagnostics to identify issues
claude-mpm doctor --verbose

# Focus on specific area
claude-mpm doctor --checks agent-sources --verbose

# Try automatic fixes
claude-mpm doctor --fix
```

**Common patterns**:
- Agent not available → Check `agents` and `agent-sources`
- Commands failing → Check `installation` and `configuration`
- Services unreachable → Check `mcp` and network connectivity

### 4. After Configuration Changes

**Scenario**: You added a new agent source or modified configuration.

```bash
# Verify configuration changes
claude-mpm doctor --checks configuration agent-sources

# Check agent discovery
claude-mpm agents available
```

### 5. Sharing System Status

**Scenario**: You need to share system information with team or support.

```bash
# Generate comprehensive report
claude-mpm doctor --verbose --output-file system-status.md

# Include version information
claude-mpm --version >> system-status.md
```

## Understanding Check Results

### Status Indicators

**✅ OK (Green)**
- Check passed successfully
- No action required
- System component healthy

**⚠️ Warning (Yellow)**
- Non-critical issue detected
- System functional but needs attention
- Recommended to address

**❌ Error (Red)**
- Critical issue detected
- System may not function correctly
- Requires immediate action

**ℹ️ Info (Blue)**
- Informational message
- No action required
- FYI or suggestion

### Example Output Interpretation

```bash
✅ Installation: OK
   All required packages installed

⚠️ Configuration: Warning
   Using default configuration (no custom settings)

❌ Agent Sources: Error
   Configuration file missing

✅ Agents: OK (12 deployed)
   All required agents present
```

**What this means**:
1. **Installation is good** - Claude MPM properly installed
2. **Configuration works** - Default config used (might want to customize)
3. **Agent sources needs attention** - Missing configuration (critical)
4. **Agents are deployed** - System can function

**Priority**:
1. Fix agent sources error first (critical)
2. Consider customizing configuration later (optional)

## Agent Sources Health Checks

The agent sources check verifies your Git-based agent system is healthy and properly configured.

### What Gets Checked

The doctor command performs **8 comprehensive checks** for agent sources:

#### 1. Configuration File Exists

**What it checks**: `~/.claude-mpm/config/agent_sources.yaml` exists

**Why it matters**: Configuration file is required for agent source management

**If missing**:
```bash
❌ Agent Sources: Configuration file not found
   → Run: claude-mpm source add https://github.com/bobmatnyc/claude-mpm-agents
```

**How to fix**:
```bash
# Add default system repository (auto-creates config)
claude-mpm source add https://github.com/bobmatnyc/claude-mpm-agents

# Verify configuration created
claude-mpm doctor --checks agent-sources
```

#### 2. Configuration Valid YAML

**What it checks**: YAML file parses correctly with valid structure

**Why it matters**: Invalid YAML prevents agent source loading

**If invalid**:
```bash
❌ Agent Sources: Configuration invalid
   Parse error at line 5: mapping values are not allowed here
```

**How to fix**:
```bash
# Open configuration file
nano ~/.claude-mpm/config/agent_sources.yaml

# Common YAML issues:
# - Use spaces (not tabs) for indentation
# - Quote URLs if they contain special characters
# - Check colon spacing (space after colon)

# Example valid configuration:
disable_system_repo: false
repositories:
  - url: https://github.com/mycompany/agents
    priority: 100
    enabled: true
```

#### 3. At Least One Source Configured

**What it checks**: Configuration has at least one repository

**Why it matters**: Need at least one source to provide agents

**If none**:
```bash
⚠️ Agent Sources: No sources configured
   → Add system repository: claude-mpm source add <url>
```

**How to fix**:
```bash
# Add default system repository
claude-mpm source add https://github.com/bobmatnyc/claude-mpm-agents

# Or add your custom repository
claude-mpm source add https://github.com/mycompany/agents --priority 50
```

#### 4. System Repository Accessible

**What it checks**: Default system repository is reachable (if enabled)

**Why it matters**: System repo provides core agents

**If unreachable**:
```bash
⚠️ Agent Sources: System repository unreachable
   Status: Connection timeout
   → Check network connectivity
```

**How to fix**:
```bash
# 1. Check network
ping github.com

# 2. Test URL in browser
# Visit: https://github.com/bobmatnyc/claude-mpm-agents

# 3. System continues with cached agents (no immediate action needed)

# 4. Try force sync when network available
claude-mpm source sync --force
```

#### 5. Enabled Sources Reachable

**What it checks**: All enabled repositories are accessible

**Why it matters**: Unreachable sources can't provide agents

**If unreachable**:
```bash
⚠️ Agent Sources: Some sources unreachable (1/2 reachable)
   Details:
     ✅ bobmatnyc/claude-mpm-agents (200 OK)
     ❌ mycompany/agents (404 Not Found)
```

**How to fix**:
```bash
# 1. Verify repository exists
# Visit: https://github.com/mycompany/agents

# 2. Check repository URL
claude-mpm source info mycompany/agents

# 3. Update URL if needed
claude-mpm source remove mycompany/agents
claude-mpm source add https://github.com/mycompany/correct-agents

# 4. Or temporarily disable
claude-mpm source disable mycompany/agents
```

#### 6. Cache Directory Healthy

**What it checks**: `~/.claude-mpm/cache/remote-agents/` is writable

**Why it matters**: Cache directory stores synced agents

**If not writable**:
```bash
❌ Agent Sources: Cache directory not writable
   Path: /Users/user/.claude-mpm/cache/remote-agents
   → Fix permissions: chmod 755 /Users/user/.claude-mpm/cache/
```

**How to fix**:
```bash
# 1. Check permissions
ls -ld ~/.claude-mpm/cache/remote-agents/

# 2. Fix permissions
chmod 755 ~/.claude-mpm/cache/
chmod 755 ~/.claude-mpm/cache/remote-agents/

# 3. Check disk space
df -h ~/.claude-mpm/cache/

# 4. Clear cache if corrupted
rm -rf ~/.claude-mpm/cache/remote-agents/*
claude-mpm source sync --force
```

#### 7. Priority Conflicts

**What it checks**: No duplicate priorities across sources

**Why it matters**: Duplicate priorities create ambiguous agent resolution

**If conflicts**:
```bash
ℹ️ Agent Sources: Priority conflicts detected
   Sources with priority 100: 2
     - bobmatnyc/claude-mpm-agents
     - mycompany/agents
   → Assign unique priorities for clear precedence
```

**How to fix**:
```bash
# 1. List sources to see conflicts
claude-mpm source list

# 2. Assign unique priorities
# Lower number = higher precedence

# Override system agents with custom
claude-mpm source set-priority mycompany/agents 50

# Or make custom supplementary
claude-mpm source set-priority mycompany/agents 150

# 3. Verify resolution
claude-mpm doctor --checks agent-sources
```

#### 8. Agents Discovered

**What it checks**: Agents successfully discovered from sources

**Why it matters**: Need agents to use Claude MPM features

**If none**:
```bash
⚠️ Agent Sources: No agents discovered
   → Sync sources: claude-mpm source sync
```

**How to fix**:
```bash
# 1. Sync all sources
claude-mpm source sync

# 2. Check cache directory
ls ~/.claude-mpm/cache/remote-agents/

# 3. Verify sources configured
claude-mpm source list

# 4. Force re-sync if needed
claude-mpm source sync --force

# 5. Deploy agents
claude-mpm agents deploy-all

# 6. Verify agents available
claude-mpm agents available
```

### Example Output

#### Healthy System

```bash
$ claude-mpm doctor --checks agent-sources

✅ Agent Sources: All checks passed (2 source(s), 12 agent(s))
   ├─ Configuration file: Found
   ├─ YAML validity: Valid
   ├─ Sources configured: 2 (2 enabled)
   ├─ System repository: Accessible
   ├─ Enabled sources: 2/2 reachable
   ├─ Cache directory: Healthy
   ├─ Priority conflicts: None
   └─ Agents discovered: 12 total
```

#### System with Issues

```bash
$ claude-mpm doctor --checks agent-sources

⚠️ Agent Sources: Issues detected
   ├─ Configuration file: Found
   ├─ YAML validity: Valid
   ├─ Sources configured: 2 (2 enabled)
   ├─ System repository: Accessible
   ├─ Enabled sources: 1/2 reachable
   │  └─ ❌ mycompany/agents: 404 Not Found
   ├─ Cache directory: Healthy
   ├─ Priority conflicts: 1 conflict
   │  └─ ⚠️ Priority 100: 2 sources (ambiguous)
   └─ Agents discovered: 10 total

⚠️ Recommendations:
   1. Fix unreachable source: mycompany/agents
   2. Resolve priority conflict for clear precedence
```

### Verbose Output

For detailed diagnostics:

```bash
$ claude-mpm doctor --checks agent-sources --verbose

✅ Agent Sources: All checks passed

Configuration File Exists
  ✅ OK
  Path: /Users/user/.claude-mpm/config/agent_sources.yaml
  Size: 234 bytes
  Modified: 2025-11-30 12:00:00

Configuration Valid YAML
  ✅ OK
  Sources defined: 2
  System repo disabled: false

Sources Configured
  ✅ OK
  Total sources: 2
  Enabled: 2
  Disabled: 0

System Repository Accessible
  ✅ OK
  URL: https://github.com/bobmatnyc/claude-mpm-agents
  Status: 200 OK
  Response time: 124ms
  ETag: "abc123..."

Enabled Sources Reachable
  ✅ OK (2/2 reachable)
  Details:
    ✅ bobmatnyc/claude-mpm-agents
       URL: https://github.com/bobmatnyc/claude-mpm-agents
       Status: 200 OK
       Response time: 124ms

    ✅ mycompany/agents
       URL: https://github.com/mycompany/agents
       Status: 200 OK
       Response time: 156ms

Cache Directory Healthy
  ✅ OK
  Path: /Users/user/.claude-mpm/cache/remote-agents
  Exists: Yes
  Writable: Yes
  Size: 2.4 MB
  Files: 12 agent files

Priority Conflicts
  ✅ No conflicts
  Unique priorities: 2
  Priority distribution:
    - Priority 50: mycompany/agents
    - Priority 100: bobmatnyc/claude-mpm-agents

Agents Discovered
  ✅ OK (12 total)

  bobmatnyc/claude-mpm-agents (priority: 100): 10 agents
    - engineer.md
    - documentation.md
    - qa.md
    - research.md
    - ops.md
    - ticketing.md
    - python-engineer.md
    - react-engineer.md
    - golang-engineer.md
    - local-ops-agent.md

  mycompany/agents (priority: 50): 2 agents
    - engineer.md (overrides system engineer)
    - custom-agent.md
```

## Generating Reports

### Why Generate Reports?

- **Sharing system status** with team members
- **Documenting issues** for support tickets
- **Compliance and auditing** requirements
- **Baseline snapshots** for system health
- **Historical tracking** of system changes

### Report Types

#### 1. Quick Report (Auto-named)

```bash
# Generates: mpm-doctor-report-20251130-143025.md
claude-mpm doctor --output-file
```

**Best for**: Daily health checks, quick snapshots

#### 2. Custom Named Report

```bash
# Generates: health-check.md
claude-mpm doctor --output-file health-check.md
```

**Best for**: Specific purposes (pre-deployment, post-installation)

#### 3. Detailed Verbose Report

```bash
# Generates detailed report with all sub-checks
claude-mpm doctor --verbose --output-file detailed-report.md
```

**Best for**: Troubleshooting, support tickets, comprehensive audits

#### 4. Focused Report (Specific Checks)

```bash
# Only agent sources health
claude-mpm doctor --checks agent-sources --output-file agent-sources-report.md

# Multiple specific checks
claude-mpm doctor --checks configuration agents agent-sources --output-file config-report.md
```

**Best for**: Targeted diagnostics, specific component health

### Report Format

Reports include:

**Header Section**:
```markdown
# Claude MPM Doctor Report

**Generated:** 2025-11-30 14:30:25 UTC
**System:** Darwin 25.1.0 (arm64)
**Python:** 3.13.7
**claude-mpm:** 4.26.5
**Working Directory:** /Users/user/Projects/my-project
```

**Summary Section**:
```markdown
## Summary Statistics

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ OK | 10 | 90% |
| ⚠️  Warning | 1 | 10% |
| ❌ Error | 0 | 0% |

### 🎉 Overall Status: **Healthy**
```

**Detailed Results**:
```markdown
### ✅ Agent Sources

![OK](https://img.shields.io/badge/status-OK-green)

**Message:** All checks passed (2 source(s), 12 agent(s))

<details>
<summary>Details</summary>

```json
{
  "config_exists": true,
  "total_sources": 2,
  "enabled_sources": 2,
  "reachable_sources": 2,
  "agents_discovered": 12
}
```
</details>
```

**Footer Metadata**:
```markdown
---

## Report Metadata

- **Tool:** `claude-mpm doctor`
- **Version:** 4.26.5
- **Generated:** 2025-11-30 14:30:25 UTC

---

🤖 *Generated with [Claude Code](https://claude.com/claude-code)*
```

### Report Organization

**For daily monitoring**:
```bash
# Create reports directory
mkdir -p reports/doctor

# Generate daily report
claude-mpm doctor --output-file reports/doctor/$(date +%Y-%m-%d).md
```

**For issue tracking**:
```bash
# Generate report with issue number
claude-mpm doctor --verbose --output-file reports/issue-1234-diagnostics.md
```

**For version tracking**:
```bash
# Include version in filename
VERSION=$(claude-mpm --version | cut -d' ' -f2)
claude-mpm doctor --output-file reports/health-v${VERSION}.md
```

## Troubleshooting Common Issues

### Issue: Configuration File Missing

**Symptom**:
```bash
❌ Configuration: Configuration file not found
```

**Solution**:
```bash
# Initialize Claude MPM (creates default configuration)
claude-mpm init

# Or add default system repository
claude-mpm source add https://github.com/bobmatnyc/claude-mpm-agents

# Verify configuration created
claude-mpm doctor --checks configuration
```

### Issue: No Agents Deployed

**Symptom**:
```bash
⚠️ Agents: No agents deployed
```

**Solution**:
```bash
# Deploy all agents
claude-mpm agents deploy-all

# Or deploy minimal set
claude-mpm agents deploy-minimal

# Or auto-detect toolchain
claude-mpm agents deploy-auto

# Verify agents deployed
ls .claude/agents/
claude-mpm doctor --checks agents
```

### Issue: Agent Sources Unreachable

**Symptom**:
```bash
⚠️ Agent Sources: Sources unreachable
```

**Solution**:
```bash
# 1. Check network
ping github.com

# 2. Check repository URLs
claude-mpm source list

# 3. Test URL in browser
# Visit problematic repository URL

# 4. System continues with cached agents
claude-mpm agents available

# 5. Force sync when network available
claude-mpm source sync --force
```

### Issue: Permission Denied

**Symptom**:
```bash
❌ Filesystem: Permission denied: ~/.claude-mpm/cache/
```

**Solution**:
```bash
# Fix directory permissions
chmod 755 ~/.claude-mpm/
chmod 755 ~/.claude-mpm/cache/
chmod 755 ~/.claude-mpm/cache/remote-agents/

# Verify permissions
ls -ld ~/.claude-mpm/cache/

# Re-run diagnostics
claude-mpm doctor --checks filesystem
```

### Issue: Invalid YAML Configuration

**Symptom**:
```bash
❌ Configuration: YAML parse error
```

**Solution**:
```bash
# Open configuration file
nano ~/.claude-mpm/config/agent_sources.yaml

# Common fixes:
# 1. Use spaces (not tabs) for indentation
# 2. Add space after colons
# 3. Quote URLs if they contain special characters
# 4. Check bracket/brace matching

# Validate YAML online
# Visit: https://www.yamllint.com/

# Or use Python
python3 -c "import yaml; yaml.safe_load(open('~/.claude-mpm/config/agent_sources.yaml'))"
```

### Issue: Priority Conflicts

**Symptom**:
```bash
ℹ️ Agent Sources: Priority conflicts detected
```

**Solution**:
```bash
# List sources to identify conflicts
claude-mpm source list

# Assign unique priorities
# Lower = higher precedence

# Example: Custom agents override system
claude-mpm source set-priority mycompany/agents 50

# Example: Community agents supplement
claude-mpm source set-priority community/contrib 150

# Verify no conflicts
claude-mpm doctor --checks agent-sources
```

## Best Practices

### 1. Regular Health Checks

Run diagnostics regularly to catch issues early:

```bash
# Weekly health check
claude-mpm doctor --output-file reports/weekly-$(date +%Y-%m-%d).md

# After major changes
claude-mpm doctor --verbose

# Before deployment
claude-mpm doctor --checks configuration agents agent-sources
```

### 2. Baseline Reports

Create baseline reports for comparison:

```bash
# Initial setup baseline
claude-mpm doctor --verbose --output-file baseline-$(date +%Y%m%d).md

# Compare later
diff baseline-20251130.md current-report.md
```

### 3. Focused Diagnostics

Use specific checks when troubleshooting:

```bash
# Agent issues → check agents and sources
claude-mpm doctor --checks agents agent-sources

# Configuration issues → check config only
claude-mpm doctor --checks configuration

# Service issues → check MCP services
claude-mpm doctor --checks mcp
```

### 4. Automation

Integrate into workflows:

```bash
# Pre-commit hook
#!/bin/bash
if ! claude-mpm doctor --checks configuration; then
    echo "Configuration invalid, commit aborted"
    exit 1
fi

# CI/CD pipeline
claude-mpm doctor --json > health.json
if [ $? -ne 0 ]; then
    echo "Health check failed"
    exit 1
fi

# Daily monitoring (cron)
0 9 * * * cd /path/to/project && claude-mpm doctor --output-file reports/daily-$(date +\%Y\%m\%d).md
```

### 5. Verbose Mode for Issues

Always use verbose mode when troubleshooting:

```bash
# Detailed diagnostics
claude-mpm doctor --verbose --checks agent-sources

# Save verbose report
claude-mpm doctor --verbose --output-file issue-diagnostics.md
```

### 6. Clean Reports for Sharing

Generate clean reports for team/support:

```bash
# Comprehensive report
claude-mpm doctor --verbose --output-file system-health-$(date +%Y%m%d).md

# Add system information
echo "## Additional Information" >> system-health-*.md
claude-mpm --version >> system-health-*.md
python --version >> system-health-*.md
uname -a >> system-health-*.md
```

## Next Steps

### After Running Doctor

1. **All checks passed** (✅):
   - You're ready to use Claude MPM
   - Consider setting up automated monitoring
   - Bookmark report for future reference

2. **Warnings detected** (⚠️):
   - Review warnings and decide priority
   - Non-critical issues can often wait
   - Consider addressing before deployment

3. **Errors detected** (❌):
   - Address errors immediately
   - Use verbose mode for details
   - Generate report for support if needed

### Learn More

- **[CLI Reference](../reference/cli-doctor.md)** - Complete command reference
- **[Single-Tier Agent System](single-tier-agent-system.md)** - Agent sources in depth
- **[Configuration Reference](../configuration/reference.md)** - Configuration options
- **[Troubleshooting Guide](../user/troubleshooting.md)** - General troubleshooting
- **[Agent Sources API](../reference/agent-sources-api.md)** - Technical reference

---

**Need Help?**

- Run `claude-mpm doctor --verbose` for detailed diagnostics
- Generate report: `claude-mpm doctor --output-file issue-report.md`
- Check [Troubleshooting Guide](../user/troubleshooting.md)
- Report issues: [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues)
