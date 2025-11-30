# Doctor Command CLI Reference

**Command**: `claude-mpm doctor`
**Aliases**: `diagnose`, `check-health`
**Category**: System Diagnostics

Complete reference for the `doctor` command - Claude MPM's comprehensive system health diagnostics tool.

## Table of Contents

- [Overview](#overview)
- [Basic Usage](#basic-usage)
- [Options](#options)
- [Check Categories](#check-categories)
- [Output Formats](#output-formats)
- [Examples](#examples)
- [Exit Codes](#exit-codes)
- [Related Commands](#related-commands)

## Overview

The `doctor` command performs comprehensive health checks on your Claude MPM installation, configuration, and integrated services. It identifies issues, provides diagnostic information, and suggests fixes.

**When to use**:
- After installation to verify setup
- When experiencing unexpected behavior
- Before deployment to validate configuration
- To generate shareable diagnostic reports
- To monitor agent source health

## Basic Usage

```bash
# Run all diagnostic checks
claude-mpm doctor

# Run with verbose output
claude-mpm doctor --verbose

# Run specific checks only
claude-mpm doctor --checks agent-sources

# Generate shareable report
claude-mpm doctor --output-file
```

## Options

### `--verbose`, `-v`

Show detailed diagnostic information including sub-checks and additional context.

```bash
claude-mpm doctor --verbose
```

**What it includes**:
- Detailed check results with sub-items
- Configuration file paths and values
- Dependency versions
- Network connectivity details
- Cache statistics

### `--json`

Output results in JSON format for programmatic processing.

```bash
claude-mpm doctor --json
```

**JSON Structure**:
```json
{
  "status": "healthy",
  "checks": [
    {
      "name": "installation",
      "status": "ok",
      "message": "Installation is healthy",
      "details": { ... }
    }
  ],
  "summary": {
    "total": 8,
    "ok": 7,
    "warning": 1,
    "error": 0
  }
}
```

### `--markdown`

Output results in Markdown format (default for `--output-file`).

```bash
claude-mpm doctor --markdown
```

### `--fix`

**⚠️ Experimental**: Attempt to automatically fix detected issues.

```bash
claude-mpm doctor --fix
```

**What it can fix**:
- Missing configuration files
- Directory permissions
- Cache corruption
- Some MCP service issues

**Safety Notes**:
- Creates backups before modifications
- Prompts for confirmation on destructive changes
- May not fix all issues automatically
- Review changes after running

### `--checks [CHECKS ...]`

Run only specific diagnostic checks instead of all checks.

```bash
claude-mpm doctor --checks installation configuration
```

**Available Checks**:
- `installation` - Verify claude-mpm installation
- `configuration` - Check configuration files
- `filesystem` - Verify directory structure
- `claude` - Check Claude Code integration
- `agents` - Check agent deployment
- `agent-sources` - Check agent source configuration (NEW)
- `mcp` - Check MCP server configuration
- `monitor` - Check monitoring service
- `common` - Check for common issues

**Multiple Checks**:
```bash
# Check agents and agent sources
claude-mpm doctor --checks agents agent-sources

# Check configuration and filesystem
claude-mpm doctor --checks configuration filesystem
```

### `--parallel`

Run checks in parallel for faster execution (experimental).

```bash
claude-mpm doctor --parallel
```

**Notes**:
- Reduces total execution time
- Some checks still run sequentially for dependencies
- May produce interleaved output without `--output-file`

### `--no-color`

Disable colored output (useful for CI/CD or logging).

```bash
claude-mpm doctor --no-color
```

### `--output`, `-o OUTPUT`

Save output to specified file (legacy option, use `--output-file` instead).

```bash
claude-mpm doctor --output report.txt
```

### `--output-file [FILE]`

Save diagnostic report to file with enhanced formatting and metadata.

**Formats**:

1. **Auto-generated timestamped filename** (no argument):
```bash
claude-mpm doctor --output-file
# Creates: mpm-doctor-report-20251130-143025.md
```

2. **Custom filename** (with argument):
```bash
claude-mpm doctor --output-file health-report.md
# Creates: health-report.md
```

3. **With directory path** (creates parent directories):
```bash
claude-mpm doctor --output-file reports/health.md
# Creates: reports/health.md (creates 'reports/' if needed)
```

**Report Features**:
- ✅ Timestamped generation date (UTC)
- ✅ System information (OS, Python version, claude-mpm version)
- ✅ Working directory
- ✅ Summary statistics with status counts
- ✅ Overall health assessment
- ✅ Detailed check results with collapsible sections
- ✅ Metadata footer with tool version
- ✅ Claude Code attribution
- ✅ Documentation links

**Example Report Header**:
```markdown
# Claude MPM Doctor Report

**Generated:** 2025-11-30 14:30:25 UTC
**System:** Darwin 25.1.0 (arm64)
**Python:** 3.13.7
**claude-mpm:** 4.26.5
**Working Directory:** /Users/masa/Projects/claude-mpm
```

## Check Categories

### Installation Check

**What it checks**:
- Claude MPM package installed and importable
- Version information available
- Core dependencies present
- Package integrity

**Common Issues**:
- ❌ Package not found - reinstall with `pip install claude-mpm`
- ⚠️ Outdated version - upgrade with `pip install --upgrade claude-mpm`
- ❌ Missing dependencies - reinstall or run `pip install -e .` in dev mode

### Configuration Check

**What it checks**:
- Configuration files exist
- Valid YAML/JSON syntax
- Required fields present
- Value types correct
- Paths valid

**Checked Files**:
- `~/.claude-mpm/config/config.yaml`
- `.claude-mpm/config.yaml` (project-level)
- `~/.claude-mpm/config/agent_sources.yaml`

**Common Issues**:
- ❌ Invalid YAML syntax - check indentation and quotes
- ⚠️ Missing configuration - run `claude-mpm init` to create defaults
- ⚠️ Invalid paths - update configuration with correct paths

### Filesystem Check

**What it checks**:
- Required directories exist
- Proper permissions (read/write)
- Sufficient disk space
- Directory structure intact

**Checked Directories**:
- `~/.claude-mpm/` (user data)
- `~/.claude-mpm/cache/` (cache directory)
- `~/.claude-mpm/cache/remote-agents/` (agent cache)
- `.claude/` (project directory)
- `.claude/agents/` (agent deployment)
- `.claude-mpm/` (project-local configuration)

**Common Issues**:
- ❌ Permission denied - run `chmod 755 ~/.claude-mpm/`
- ⚠️ Directory missing - run `claude-mpm init` to create structure
- ❌ Disk full - free up space or change cache location

### Claude Code Integration Check

**What it checks**:
- Claude Code installed
- Compatible version
- Agent discovery working
- Native slash commands available

**Common Issues**:
- ⚠️ Claude Code not found - install from https://claude.com/claude-code
- ⚠️ Version mismatch - update Claude Code to latest version
- ⚠️ Agents not discovered - check `.claude/agents/` directory

### Agents Check

**What it checks**:
- Agents deployed to `.claude/agents/`
- Agent files valid (proper format)
- Required agents present (minimal set)
- Agent versions tracked

**Required Agents** (minimal set):
- `engineer.md`
- `documentation.md`
- `qa.md`
- `research.md`
- `ops.md`
- `ticketing.md`

**Common Issues**:
- ⚠️ No agents deployed - run `claude-mpm agents deploy-all`
- ⚠️ Invalid agent format - re-deploy with `claude-mpm agents deploy-all --force-sync`
- ⚠️ Missing required agents - run `claude-mpm agents deploy-minimal`

### Agent Sources Check (NEW)

**What it checks**:

1. **Configuration File Exists** (ERROR if missing)
   - Checks `~/.claude-mpm/config/agent_sources.yaml`
   - Suggests: `claude-mpm source add <url>`

2. **Configuration Valid YAML** (ERROR if invalid)
   - Parses YAML and validates structure
   - Reports parse errors with line numbers

3. **At Least One Source Configured** (WARNING if none)
   - Counts total and enabled sources
   - Suggests adding default system repository

4. **System Repository Accessible** (WARNING if unreachable)
   - HTTP HEAD request to system repo
   - Only checked if system repo enabled
   - Tests: `https://github.com/bobmatnyc/claude-mpm-agents`

5. **Enabled Sources Reachable** (WARNING if unreachable)
   - HTTP HEAD requests to all enabled sources
   - Reports reachable/unreachable counts
   - Details per-source status

6. **Cache Directory Healthy** (ERROR if not writable)
   - Checks `~/.claude-mpm/cache/remote-agents/`
   - Tests write permissions
   - Suggests permission fixes

7. **Priority Conflicts** (INFO if detected)
   - Identifies sources with same priority
   - Potential ambiguous resolution
   - Suggests unique priorities

8. **Agents Discovered** (WARNING if none)
   - Counts agents from all sources
   - Groups by source
   - Reports total agent count

**Output Example**:
```bash
✅ Agent Sources: OK
   ├─ Configuration file: Found
   ├─ YAML validity: Valid
   ├─ Sources configured: 2 (2 enabled)
   ├─ System repository: Accessible
   ├─ Enabled sources: 2/2 reachable
   ├─ Cache directory: Healthy (/Users/user/.claude-mpm/cache/remote-agents)
   ├─ Priority conflicts: None
   └─ Agents discovered: 12 total
      ├─ bobmatnyc/claude-mpm-agents (priority: 100): 10 agents
      └─ mycompany/agents (priority: 50): 2 agents
```

**Common Issues**:
- ❌ **Configuration file missing**
  - **Fix**: `claude-mpm source add https://github.com/bobmatnyc/claude-mpm-agents`
  - System auto-creates default configuration on first sync

- ❌ **Invalid YAML syntax**
  - **Fix**: Check indentation (must use spaces, not tabs)
  - Validate at: https://www.yamllint.com/
  - Example valid configuration:
    ```yaml
    disable_system_repo: false
    repositories:
      - url: https://github.com/mycompany/agents
        priority: 100
        enabled: true
    ```

- ⚠️ **No sources configured**
  - **Fix**: Add default system repository
  - Command: `claude-mpm source add https://github.com/bobmatnyc/claude-mpm-agents`

- ⚠️ **System repository unreachable**
  - **Check network**: `ping github.com`
  - **Check URL**: Verify in browser
  - System continues with cached agents

- ⚠️ **Sources unreachable**
  - **Fix**: Check network connectivity
  - **Fix**: Verify repository URLs
  - **Fix**: Check GitHub status
  - System falls back to cached agents

- ❌ **Cache directory not writable**
  - **Fix**: `chmod 755 ~/.claude-mpm/cache/`
  - **Fix**: Check disk space
  - **Fix**: Check directory ownership

- ℹ️ **Priority conflicts detected**
  - **Impact**: Ambiguous resolution order for agents
  - **Fix**: Assign unique priorities
  - Example: `claude-mpm source set-priority mycompany/agents 50`

- ⚠️ **No agents discovered**
  - **Fix**: Sync sources with `claude-mpm source sync`
  - **Fix**: Check repository contains agents
  - **Fix**: Deploy agents with `claude-mpm agents deploy-all`

**Verbose Output**:
```bash
claude-mpm doctor --checks agent-sources --verbose

✅ Agent Sources: All checks passed

   1. Configuration File Exists: ✅ OK
      Path: /Users/user/.claude-mpm/config/agent_sources.yaml
      Size: 234 bytes

   2. Configuration Valid YAML: ✅ OK
      Sources defined: 2
      System repo disabled: false

   3. Sources Configured: ✅ OK
      Total sources: 2
      Enabled sources: 2
      Disabled sources: 0

   4. System Repository Accessible: ✅ OK
      URL: https://github.com/bobmatnyc/claude-mpm-agents
      Status: 200 OK
      Response time: 124ms

   5. Enabled Sources Reachable: ✅ OK
      Reachable: 2/2
      Details:
        ✅ bobmatnyc/claude-mpm-agents (200 OK, 124ms)
        ✅ mycompany/agents (200 OK, 156ms)

   6. Cache Directory Healthy: ✅ OK
      Path: /Users/user/.claude-mpm/cache/remote-agents
      Writable: Yes
      Size: 2.4 MB
      Files: 12

   7. Priority Conflicts: ✅ No conflicts
      Unique priorities: 2
      Priority distribution:
        - 50: mycompany/agents
        - 100: bobmatnyc/claude-mpm-agents

   8. Agents Discovered: ✅ OK (12 total)
      bobmatnyc/claude-mpm-agents (10 agents):
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

      mycompany/agents (2 agents):
        - engineer.md (overrides system)
        - custom-agent.md
```

**Troubleshooting Guide**:

See [Agent Sources Troubleshooting](#agent-sources-troubleshooting) section below for detailed solutions.

### MCP Check

**What it checks**:
- MCP server configuration
- Service health (vector-search, browser, ticketer)
- Service connectivity
- Configuration validity

**Common Issues**:
- ⚠️ Service not configured - add to configuration
- ⚠️ Service unreachable - check service status
- ⚠️ Authentication required - configure credentials

### Monitor Check

**What it checks**:
- Monitoring service status
- Process running
- Configuration valid
- Log files accessible

**Common Issues**:
- ⚠️ Service not running - start with `claude-mpm monitor start`
- ⚠️ Configuration missing - run `claude-mpm init`

### Common Issues Check

**What it checks**:
- Known issue patterns
- Frequent error scenarios
- Misconfiguration patterns
- Environment issues

**What it detects**:
- Python version incompatibility
- Conflicting installations
- Path issues
- Permission problems

## Output Formats

### Console Output (Default)

Colored, human-readable output with symbols and indentation.

```bash
$ claude-mpm doctor

Running diagnostics...

✅ Installation: OK
✅ Configuration: OK
✅ Filesystem: OK
✅ Claude Code: OK
✅ Agents: OK
✅ Agent Sources: OK
   ├─ Configuration file: Found
   ├─ Enabled sources: 2/2 reachable
   ├─ Cache directory: Healthy
   └─ Agents discovered: 12 total
✅ MCP Services: OK
✅ Monitor: OK
✅ Common Issues: None detected

🎉 Overall Status: Healthy

All checks passed. Your system is ready to use.
```

### JSON Output

Structured data for programmatic processing.

```bash
$ claude-mpm doctor --json
```

```json
{
  "status": "healthy",
  "timestamp": "2025-11-30T14:30:25.123456Z",
  "version": "4.26.5",
  "system": {
    "os": "Darwin 25.1.0",
    "arch": "arm64",
    "python": "3.13.7"
  },
  "checks": [
    {
      "name": "agent-sources",
      "category": "configuration",
      "status": "ok",
      "message": "All checks passed (2 source(s), 12 agent(s))",
      "details": {
        "config_exists": true,
        "config_valid": true,
        "total_sources": 2,
        "enabled_sources": 2,
        "reachable_sources": 2,
        "cache_healthy": true,
        "priority_conflicts": 0,
        "agents_discovered": 12
      }
    }
  ],
  "summary": {
    "total": 8,
    "ok": 8,
    "warning": 0,
    "error": 0
  }
}
```

### Markdown Output (Report File)

Enhanced report with metadata, statistics, and formatting.

```bash
$ claude-mpm doctor --output-file
Report saved to: mpm-doctor-report-20251130-143025.md
```

**Report Structure**:
1. Header with system information
2. Summary statistics
3. Overall health assessment
4. Detailed check results
5. Metadata footer

**Features**:
- Timestamped generation date
- System information
- Collapsible detail sections
- Status badges
- JSON data blocks for details
- Navigation links

## Examples

### Basic Diagnostics

```bash
# Run all checks
claude-mpm doctor

# Run with verbose output
claude-mpm doctor --verbose

# Run without colors (for CI/CD)
claude-mpm doctor --no-color
```

### Specific Checks

```bash
# Check only agent sources
claude-mpm doctor --checks agent-sources

# Check agents and agent sources
claude-mpm doctor --checks agents agent-sources

# Check configuration and filesystem
claude-mpm doctor --checks configuration filesystem
```

### Generate Reports

```bash
# Generate timestamped report
claude-mpm doctor --output-file
# Creates: mpm-doctor-report-20251130-143025.md

# Custom filename
claude-mpm doctor --output-file health-check.md

# Report in subdirectory
claude-mpm doctor --output-file reports/doctor-$(date +%Y%m%d).md

# Verbose report with all details
claude-mpm doctor --verbose --output-file detailed-report.md
```

### JSON Output for Automation

```bash
# JSON for parsing
claude-mpm doctor --json > health.json

# Check specific category in CI/CD
claude-mpm doctor --checks agent-sources --json | jq '.status'

# Extract error count
claude-mpm doctor --json | jq '.summary.error'
```

### Auto-Fix Issues

```bash
# Try to fix issues automatically
claude-mpm doctor --fix

# Fix with verbose output
claude-mpm doctor --fix --verbose

# Fix specific checks only
claude-mpm doctor --checks configuration --fix
```

### Parallel Execution

```bash
# Run checks in parallel
claude-mpm doctor --parallel

# Parallel with report output
claude-mpm doctor --parallel --output-file fast-report.md
```

## Exit Codes

The `doctor` command uses standard exit codes:

- `0` - All checks passed (healthy)
- `1` - One or more warnings (mostly healthy)
- `2` - One or more errors (needs attention)
- `3` - Critical errors (system not functional)

**Usage in Scripts**:
```bash
#!/bin/bash

if claude-mpm doctor --checks agent-sources; then
    echo "Agent sources healthy, proceeding..."
else
    echo "Agent sources check failed, aborting"
    exit 1
fi
```

**Check Exit Code**:
```bash
claude-mpm doctor
echo "Exit code: $?"
```

## Agent Sources Troubleshooting

### Configuration Issues

**Problem**: Configuration file doesn't exist
```bash
$ claude-mpm doctor --checks agent-sources
❌ Agent Sources: Configuration file not found
```

**Solution**:
```bash
# Add default system repository (auto-creates config)
claude-mpm source add https://github.com/bobmatnyc/claude-mpm-agents

# Verify configuration created
ls -l ~/.claude-mpm/config/agent_sources.yaml
```

---

**Problem**: Invalid YAML syntax
```bash
❌ Agent Sources: Configuration invalid
   Parse error at line 5: mapping values are not allowed here
```

**Solution**:
```bash
# Open configuration file
nano ~/.claude-mpm/config/agent_sources.yaml

# Common issues:
# 1. Tabs instead of spaces (use 2 spaces for indentation)
# 2. Missing quotes around URLs
# 3. Incorrect indentation

# Example valid configuration:
disable_system_repo: false
repositories:
  - url: https://github.com/mycompany/agents
    priority: 100
    enabled: true
```

### Network Issues

**Problem**: Sources unreachable
```bash
⚠️ Agent Sources: Some sources unreachable
   Enabled sources: 1/2 reachable
```

**Solutions**:
```bash
# 1. Check network connectivity
ping github.com

# 2. Test repository URL in browser
# Visit: https://github.com/mycompany/agents

# 3. Check GitHub status
# Visit: https://www.githubstatus.com

# 4. Force re-sync
claude-mpm source sync --force

# 5. Use cached agents (system continues working)
claude-mpm agents deploy-all
```

### Cache Issues

**Problem**: Cache directory not writable
```bash
❌ Agent Sources: Cache directory not writable
```

**Solutions**:
```bash
# 1. Check permissions
ls -ld ~/.claude-mpm/cache/remote-agents/

# 2. Fix permissions
chmod 755 ~/.claude-mpm/cache/
chmod 755 ~/.claude-mpm/cache/remote-agents/

# 3. Check disk space
df -h ~/.claude-mpm/cache/

# 4. Clear cache if needed
rm -rf ~/.claude-mpm/cache/remote-agents/*
claude-mpm source sync --force
```

### Priority Conflicts

**Problem**: Multiple sources with same priority
```bash
ℹ️ Agent Sources: Priority conflicts detected
   Sources with priority 100: 2
```

**Solution**:
```bash
# List sources to see conflicts
claude-mpm source list

# Assign unique priorities
claude-mpm source set-priority mycompany/agents 50
claude-mpm source set-priority community/contrib 150

# Verify resolution
claude-mpm doctor --checks agent-sources
```

### Agent Discovery Issues

**Problem**: No agents discovered
```bash
⚠️ Agent Sources: No agents discovered
```

**Solutions**:
```bash
# 1. Sync sources
claude-mpm source sync

# 2. Check cache directory
ls ~/.claude-mpm/cache/remote-agents/

# 3. Verify sources configured
claude-mpm source list

# 4. Add default system repository if needed
claude-mpm source add https://github.com/bobmatnyc/claude-mpm-agents

# 5. Force re-sync
claude-mpm source sync --force

# 6. Deploy agents
claude-mpm agents deploy-all
```

## Related Commands

### Complementary Diagnostics

```bash
# MCP-specific health checks
claude-mpm verify

# MCP with auto-fix
claude-mpm verify --fix

# Check specific MCP service
claude-mpm verify --service mcp-vector-search
```

### Agent Source Management

```bash
# List configured sources
claude-mpm source list

# Sync all sources
claude-mpm source sync

# Add new source
claude-mpm source add https://github.com/mycompany/agents --priority 50

# Get source information
claude-mpm source info mycompany/agents
```

### Agent Deployment

```bash
# Deploy all agents
claude-mpm agents deploy-all

# Deploy minimal set
claude-mpm agents deploy-minimal

# Auto-detect and deploy
claude-mpm agents deploy-auto

# List available agents
claude-mpm agents available
```

## Best Practices

### Regular Health Checks

Run diagnostics regularly to catch issues early:

```bash
# Weekly health check
claude-mpm doctor --output-file

# Before deployment
claude-mpm doctor --checks configuration agents agent-sources

# After major changes
claude-mpm doctor --verbose
```

### CI/CD Integration

```bash
#!/bin/bash
# In your CI/CD pipeline

# Run diagnostics
claude-mpm doctor --json > doctor-report.json

# Check exit code
if [ $? -ne 0 ]; then
    echo "Health check failed"
    cat doctor-report.json
    exit 1
fi

# Extract and log summary
jq '.summary' doctor-report.json
```

### Monitoring Automation

```bash
# Cron job for daily health reports
0 9 * * * cd /path/to/project && claude-mpm doctor --output-file reports/daily-$(date +\%Y\%m\%d).md
```

### Shareable Reports

When reporting issues:

```bash
# Generate comprehensive report
claude-mpm doctor --verbose --output-file issue-report.md

# Include system information
claude-mpm --version >> issue-report.md
python --version >> issue-report.md
uname -a >> issue-report.md

# Share issue-report.md with support
```

## See Also

- **[Single-Tier Agent System Guide](../guides/single-tier-agent-system.md)** - Complete agent sources documentation
- **[Configuration Reference](configuration.md)** - Configuration file formats
- **[Agent Sources API](agent-sources-api.md)** - Technical API reference
- **[Troubleshooting Guide](../user/troubleshooting.md)** - General troubleshooting
- **[MCP Services](SERVICES.md)** - MCP service documentation

---

**Need Help?**

- Run `claude-mpm doctor --verbose` for detailed diagnostics
- Check [Troubleshooting Guide](../user/troubleshooting.md)
- Report issues: [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues)
