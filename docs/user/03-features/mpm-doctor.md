# Enhanced MPM Doctor Command

The `claude-mpm doctor` command provides comprehensive diagnostics for your Claude MPM installation with enhanced reporting capabilities, automatic fix suggestions, detailed health analysis, and improved MCP service detection.

> **⚠️ Important**: Claude MPM extends **Claude Code (CLI)**, not Claude Desktop (app). All MCP integrations work with Claude Code's CLI interface only.

## Overview

The enhanced doctor command performs deep health checks across all major components of your Claude MPM setup:
- Installation integrity and dependency verification
- Configuration validation and optimization
- Claude Code CLI integration and MCP connectivity
- Agent deployments and availability
- MCP server connectivity and service status with improved detection
- Optional MCP services verification (mcp-vector-search, kuzu-memory)
- Monitor service health and performance
- File system permissions and security
- Common issues detection and resolution
- Enhanced reporting with multiple output formats

## Quick Start Examples

```bash
# Basic health check with enhanced output
claude-mpm doctor

# Generate comprehensive markdown report
claude-mpm doctor --verbose --output-file

# Create detailed report with custom filename
claude-mpm doctor --verbose --output-file system-health-report.md

# JSON output for automation and monitoring
claude-mpm doctor --json --output system-status.json

# Check specific components only
claude-mpm doctor --checks installation configuration agents

# Attempt automatic fixes for detected issues
claude-mpm doctor --fix --verbose
```

## Enhanced Command Syntax

```bash
claude-mpm doctor [OPTIONS]
claude-mpm diagnose [OPTIONS]     # alias
claude-mpm check-health [OPTIONS] # alias
```

## New and Enhanced Options

### Enhanced Output Control
- `--verbose`, `-v` - Show detailed diagnostic information including:
  - Internal system checks and validation details
  - Service-specific configuration analysis
  - MCP services status with version information
  - Performance metrics and optimization suggestions
  - Debug details for advanced troubleshooting

- `--output-file [PATH]` - **NEW FEATURE**: Save comprehensive report to file
  - When used without path: defaults to `mmp-doctor-report.md`
  - Automatically adds `.md` extension if none provided
  - Forces markdown format for optimal readability
  - Example: `--output-file health-check` creates `health-check.md`

- `--output FILE`, `-o FILE` - Save output to specified file (alternative syntax)
  - Supports `.md`, `.json`, `.txt` extensions
  - Format determined by file extension

- `--json` - Output structured JSON for programmatic processing
  - Includes metadata, timestamps, and detailed metrics
  - Perfect for monitoring systems and automation
  - Contains fix suggestions in machine-readable format

- `--markdown` - Generate comprehensive markdown reports
  - Rich formatting with status badges and tables
  - Expandable detail sections for complex diagnostics
  - Includes system overview and recommendations

- `--no-color` - Disable colored output for:
  - Terminal compatibility and CI/CD pipelines
  - Log file generation without ANSI codes
  - Accessibility and screen reader compatibility

### Advanced Diagnostic Selection
- `--checks CHECKS` - Run specific check categories for targeted analysis:
  - `installation` - Verify Claude MPM installation, dependencies, and Python environment
  - `configuration` - Validate configuration files, settings, and environment variables
  - `filesystem` - Check directory structure, permissions, and storage
  - `claude` - Test Claude Code CLI integration and version compatibility
  - `agents` - Verify agent deployments, availability, and configuration
  - `mcp` - Check MCP server configuration, connectivity, and service status
  - `monitor` - Validate monitoring service health and WebSocket connectivity
  - `common` - Scan for frequently encountered issues and patterns

### Performance and Automation
- `--parallel` - **EXPERIMENTAL**: Run checks concurrently for faster execution
  - Reduces diagnostic time for comprehensive checks
  - Maintains accuracy while improving performance
  - Best for automated health monitoring

### Intelligent Auto-Remediation
- `--fix` - **EXPERIMENTAL**: Attempt automatic resolution of detected issues
  - Safe, non-destructive fixes only
  - Automatic permission corrections
  - Configuration file repairs
  - Missing directory creation
  - Agent deployment fixes
  - Service restart attempts

## Enhanced Output Formats

### Terminal Output (Default)
Interactive, color-coded display with:
- Status indicators with emoji and color coding
- Hierarchical issue organization
- Immediate fix suggestions
- Progress indicators and timing
- Summary statistics and recommendations

### Markdown Report Format
Comprehensive documentation including:
```markdown
# Claude MPM Doctor Report

**Generated:** 2024-01-15 14:30:22
**Version:** 4.4.1

## System Overview
| Component | Value |
|-----------|-------|
| Platform | Darwin 23.1.0 |
| Python Version | 3.11.7 |
| Claude MPM Version | 4.4.1 |

## MCP Services Status
| Service | Installed | Accessible | Version | Status | Type |
|---------|-----------|------------|---------|--------|------|
| mcp-vector-search | ✅ | ✅ | 1.2.0 | ✅ | Optional |
| kuzu-memory | ✅ | ✅ | 0.8.1 | ✅ | Optional |

**Note**: MCP services are optional dependencies. Missing services trigger automatic installation on first use.

## Detailed Diagnostic Results
### ✅ Installation
![OK](https://img.shields.io/badge/status-OK-green)
**Message:** All components properly installed

### ⚠️ Configuration
![Warning](https://img.shields.io/badge/status-Warning-yellow)
**Message:** Minor configuration optimizations available
**Fix Available:**
```bash
claude-mpm config optimize
```
```

### JSON Report Format
Structured data for automation:
```json
{
  "metadata": {
    "tool": "claude-mpm doctor",
    "version": "4.4.1",
    "timestamp": "2024-01-15T14:30:22Z",
    "verbose": true
  },
  "summary": {
    "overall_status": "warning",
    "ok_count": 6,
    "warning_count": 1,
    "error_count": 0,
    "skipped_count": 0
  },
  "results": [
    {
      "category": "Installation",
      "status": "ok",
      "message": "All components properly installed",
      "details": {
        "claude_mpm_version": "4.4.1",
        "python_version": "3.11.7"
      }
    }
  ],
  "fixes": [
    {
      "category": "Configuration", 
      "command": "claude-mpm config optimize",
      "description": "Apply recommended configuration optimizations"
    }
  ]
}
```

## Interactive Mode Usage

Enhanced slash command support in Claude Code:

```
/mpm-doctor
/mpm-doctor --verbose
/mpm-doctor --no-color
/mpm-doctor --checks installation agents
```

**Interactive Mode Features:**
- Real-time diagnostic streaming
- Interactive fix confirmations
- Contextual help and explanations
- Session-aware recommendations
- Integration with Claude Code's tool ecosystem

**Limitations in Interactive Mode:**
- No file output options (console only)
- Limited to `--verbose` and `--no-color` flags
- Cannot use `--fix` flag (manual fixes recommended)

## Understanding Enhanced Output

### Status Indicators with Context
- ✅ **OK**: Component functioning optimally, no action required
- ⚠️ **WARNING**: Non-critical issue affecting performance or features
- ❌ **ERROR**: Critical issue requiring immediate attention
- ℹ️ **INFO**: Informational message or optimization opportunity
- ⏭️ **SKIPPED**: Check bypassed due to prerequisites or configuration

### Enhanced Exit Codes
- `0` - All checks passed, system healthy
- `1` - Warnings found, system functional but suboptimal
- `2` - Critical errors detected, immediate action required
- `130` - Process interrupted by user (Ctrl+C)

### Performance Metrics
The enhanced doctor command now reports:
- Check execution times
- Resource utilization during diagnostics
- Service response times
- Cache hit rates and optimization opportunities

## Enhanced MCP Service Diagnostics (v4.4.x)

The doctor command now provides enhanced diagnostics for optional MCP services with improved detection and resolution capabilities.

### MCP Service Detection Improvements

**Previous Behavior**:
- Basic service availability checking
- Limited error information
- No distinction between optional vs. required services

**Enhanced Behavior (v4.4.x)**:
- **Accurate Detection**: Distinguishes between "not installed" vs. "not accessible"
- **Optional Service Awareness**: Clearly identifies which services are optional dependencies
- **Fallback Installation Status**: Reports whether automatic installation succeeded/failed
- **PATH Resolution**: Detects PATH issues with pipx-installed services
- **Version Validation**: Verifies compatibility with current Claude MPM version

### Enhanced MCP Diagnostic Examples

```bash
# Basic MCP service check
claude-mpm doctor --checks mcp

# Detailed MCP service analysis
claude-mpm doctor --checks mcp --verbose

# Generate MCP service report
claude-mpm doctor --checks mcp --output-file mcp-services-report.md

# Check MCP alongside installation
claude-mpm doctor --checks installation mcp --verbose
```

### MCP Service Status Interpretation

**Status Indicators**:
- ✅ **Available**: Service installed and accessible
- ⚠️ **Optional Not Found**: Service not installed but optional (triggers auto-install)
- ❌ **Required Missing**: Critical service missing (immediate action needed)
- 🔧 **PATH Issue**: Service installed but not accessible (PATH configuration needed)
- 📦 **Auto-Installing**: Automatic installation in progress

### New MCP Diagnostic Outputs

**Enhanced Console Output**:
```
📋 MCP Services Check
├── mcp-vector-search
│   ├── ✅ Installation: Found via pipx
│   ├── ✅ Accessibility: Command available in PATH
│   ├── ✅ Version: 1.2.0 (compatible)
│   └── ✅ Type: Optional dependency
├── kuzu-memory
│   ├── ⚠️ Installation: Not found
│   ├── 📦 Auto-Install: Attempting pipx installation...
│   ├── ✅ Fallback: Successfully installed
│   └── ✅ Type: Optional dependency
```

**Enhanced JSON Output**:
```json
{
  "mcp_services": {
    "mcp-vector-search": {
      "installed": true,
      "accessible": true,
      "version": "1.2.0",
      "compatible": true,
      "installation_method": "pipx",
      "type": "optional",
      "status": "available"
    },
    "kuzu-memory": {
      "installed": false,
      "accessible": false,
      "version": null,
      "auto_install_attempted": true,
      "auto_install_success": true,
      "type": "optional",
      "status": "auto_installed"
    }
  }
}
```

### Troubleshooting MCP Service Issues

**Issue**: MCP services not detected after installation
```bash
# Verify pipx PATH configuration
pipx ensurepath
source ~/.bashrc  # or ~/.zshrc

# Check pipx installations
pipx list

# Re-run diagnostic
claude-mpm doctor --checks mcp --verbose
```

**Issue**: Automatic installation fails
```bash
# Check pipx availability
which pipx || python -m pip install --user pipx

# Manual installation
pipx install mcp-vector-search kuzu-memory

# Configure for Claude MPM
claude-mpm mcp-pipx-config
```

**Issue**: Version compatibility warnings
```bash
# Check current versions
pipx list | grep -E "(mcp-vector-search|kuzu-memory)"

# Update to latest versions
pipx upgrade mcp-vector-search kuzu-memory

# Verify compatibility
claude-mpm doctor --checks mcp --verbose
```

## Advanced Diagnostic Scenarios

### Comprehensive System Audit
```bash
# Full system health audit with detailed report
claude-mpm doctor --verbose --output-file system-audit-$(date +%Y%m%d).md
```

### Automated Monitoring Integration
```bash
# JSON output for monitoring systems
claude-mpm doctor --json --no-color > /tmp/claude-mpm-health.json

# Parse with jq for specific metrics
claude-mpm doctor --json | jq '.summary.error_count'
```

### Targeted Component Testing
```bash
# Test only MCP and agent systems
claude-mpm doctor --checks mcp agents --verbose

# Quick installation verification
claude-mpm doctor --checks installation --parallel
```

### Development and CI/CD Integration
```bash
# Pre-deployment health check
claude-mpm doctor --parallel --no-color --json

# Post-installation verification
claude-mpm doctor --fix --verbose --output-file deployment-verification.md
```

## Common Issues and Enhanced Resolutions

### Agent Deployment Issues
**Enhanced Detection**: Doctor now identifies:
- Missing agent directories
- Permission issues with agent files
- Version mismatches between templates and deployments
- Claude Code CLI integration problems

**Auto-Fix Capabilities**:
```bash
# Automatic agent deployment repair
claude-mpm doctor --fix --checks agents
```

### MCP Service Problems
**Enhanced Analysis** (v4.4.x improvements):
- **Accurate Service Detection**: Improved detection of optional MCP services
- **Installation Status**: Distinguishes between not installed vs. not accessible
- **Version Compatibility**: Checks MCP service versions against requirements
- **Fallback Installation**: Identifies when automatic installation is needed
- **Configuration Validation**: Verifies MCP service configuration and connectivity

**Common MCP Service Issues**:
- **Service Not Found**: Optional MCP services not installed
- **PATH Issues**: Services installed but not accessible (common with pipx)
- **Version Conflicts**: Incompatible MCP service versions
- **Configuration Errors**: Invalid or missing MCP configuration files

**Enhanced Resolution Workflow**:
```bash
# 1. Comprehensive MCP service diagnosis
claude-mpm doctor --checks mcp --verbose

# 2. Check if MCP services are needed vs. optional
claude-mpm doctor --checks mcp installation --verbose

# 3. Generate detailed MCP diagnostic report
claude-mpm doctor --checks mcp --output-file mcp-diagnostic.md

# 4. Manual MCP service installation if needed
pipx install mcp-vector-search kuzu-memory

# 5. Configure MCP services for pipx
claude-mpm mcp-pipx-config

# 6. Verify fixes
claude-mpm doctor --checks mcp --verbose
```

### Configuration Optimization
**New Feature**: Doctor identifies optimization opportunities:
- Cache configuration improvements
- Performance tuning suggestions
- Security hardening recommendations
- Resource allocation optimization

### Memory and Performance Issues
**Enhanced Monitoring**:
- Memory usage analysis
- Service performance metrics
- Cache efficiency reporting
- Resource bottleneck identification

## Integration with Claude MPM Ecosystem

### Memory System Integration
```bash
# Combine with memory diagnostics
claude-mpm doctor --verbose && claude-mpm memory status
```

### Monitor Dashboard Integration
```bash
# Start monitoring during health check
claude-mpm monitor &
claude-mpm doctor --verbose --output-file health-with-monitoring.md
```

### Agent Manager Coordination
```bash
# Complete agent ecosystem health check
claude-mpm doctor --checks agents --verbose
claude-mpm agent-manager list
claude-mpm agent-manager test <agent-id>
```

## Best Practices for Enhanced Doctor Usage

### Regular Health Monitoring
```bash
# Weekly automated health check
#!/bin/bash
REPORT_DATE=$(date +%Y%m%d)
claude-mpm doctor --verbose --output-file "weekly-health-$REPORT_DATE.md"
if [ $? -ne 0 ]; then
    echo "Health issues detected, check report for details"
fi
```

### Development Workflow Integration
```bash
# Pre-commit health verification
claude-mpm doctor --parallel --checks installation configuration

# Post-deployment validation
claude-mpm doctor --fix --verbose --output-file deployment-$(git rev-parse --short HEAD).md
```

### Team Collaboration
```bash
# Generate shareable health report
claude-mpm doctor --verbose --markdown --output-file team-system-status.md

# Create JSON for automated processing
claude-mpm doctor --json --output system-metrics.json
```

## Security and Privacy Considerations

The enhanced doctor command:
- ✅ Never exposes sensitive configuration data in reports
- ✅ Sanitizes file paths and personal information
- ✅ Provides anonymous system metrics only
- ✅ Respects user privacy in generated reports
- ✅ Validates all inputs for security

## Troubleshooting the Doctor Command

If the doctor command itself encounters issues:

```bash
# Enable debug logging
export CLAUDE_MPM_LOG_LEVEL=DEBUG
claude-mpm doctor --verbose

# Use minimal check set
claude-mpm doctor --checks installation

# Force basic output mode
claude-mpm doctor --no-color
```

## Related Commands and Ecosystem

- `claude-mpm config validate` - Validate configuration files
- `claude-mpm agent-manager list` - List available agents
- `claude-mpm mcp status` - Check MCP server status
- `claude-mpm monitor status` - Monitor service health
- `claude-mpm memory status` - Memory system diagnostics
- `claude-mpm cleanup` - System cleanup and optimization

## See Also

- [CLI Commands Reference](../../reference/CLI_COMMANDS.md) - Complete CLI documentation
- [Troubleshooting Guide](../troubleshooting.md) - General troubleshooting procedures
- [Agent Management](../02-guides/agent-management.md) - Agent deployment and management
- [Configuration Guide](../02-guides/configuration.md) - Configuration optimization
- [Performance Monitoring](./dashboard-enhancements.md) - Monitoring and performance analysis

The enhanced `claude-mpm doctor` command represents a significant advancement in system diagnostics, providing comprehensive health analysis with intelligent reporting and automated remediation capabilities.