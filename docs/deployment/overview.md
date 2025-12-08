# Deployment Guide

Guide to deploying, releasing, and managing Claude MPM in production environments.

## Quick Links

- **[Complete Deployment Reference](reference/DEPLOY.md)** - Detailed deployment procedures
- **[Homebrew Troubleshooting](reference/HOMEBREW_UPDATE_TROUBLESHOOTING.md)** - Homebrew tap integration
- **[Publishing Guide](developer/publishing-guide.md)** - Release process for maintainers

## Installation Methods

### PyPI (Recommended)

```bash
# Install with monitoring dashboard
pipx install "claude-mpm[monitor]"

# Or with pip
pip install "claude-mpm[monitor]"

# Verify installation
claude-mpm --version
claude-mpm doctor
```

### Homebrew (macOS)

```bash
# Install from official tap
brew install bobmatnyc/tools/claude-mpm

# Verify installation
claude-mpm --version
claude-mpm doctor
```

### From Source

```bash
# Clone repository
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm

# Install in development mode
pip install -e ".[dev,monitor]"

# Verify installation
claude-mpm --version
```

See [user/installation.md](user/installation.md) for complete installation guide.

## Release Process (Maintainers)

### Version Management

```bash
# Update version and create release
./scripts/manage_version.py bump patch  # or minor, major

# Create Git tag
git tag -a v$(cat VERSION) -m "Release v$(cat VERSION)"
git push origin v$(cat VERSION)
```

### Publishing Workflow

The release process is automated through GitHub Actions:

**Phase 1: Local Preparation**
1. Update version with `manage_version.py`
2. Update CHANGELOG.md
3. Run quality checks: `make quality`
4. Commit changes

**Phase 2: PyPI Release**
1. Push tag triggers GitHub workflow
2. Automated build and test
3. PyPI package upload
4. Release notes generation

**Phase 3: Homebrew Update**
1. Automatic formula update
2. SHA256 checksum fetch from PyPI
3. Local formula testing
4. Commit and push to tap repository

**Phase 4: Verification**
1. Verify PyPI package
2. Verify Homebrew formula
3. Test installation methods
4. Update documentation

See [developer/publishing-guide.md](developer/publishing-guide.md) for complete process.

## Homebrew Tap Integration

The Homebrew tap is automatically updated during the release workflow:

**Automatic Update:**
```bash
# Triggered during release
make release-publish

# Or manual trigger
make update-homebrew-tap
```

**Manual Fallback:**
```bash
# If automation fails
cd /path/to/homebrew-tools
./scripts/update_formula.sh $(cat VERSION)
git add Formula/claude-mpm.rb
git commit -m "feat: update to v$(cat VERSION)"
git push origin main
```

See [reference/HOMEBREW_UPDATE_TROUBLESHOOTING.md](reference/HOMEBREW_UPDATE_TROUBLESHOOTING.md) for troubleshooting.

## Configuration Management

### System Configuration

Global defaults:
```
/usr/local/share/claude-mpm/
  └── configuration.yaml
```

### User Configuration

User-level settings:
```
~/.claude-mpm/
  ├── configuration.yaml          # Main configuration
  ├── agents/                     # Custom agents
  └── skills/                     # Custom skills
```

### Project Configuration

Project-specific settings:
```
.claude-mpm/
  ├── configuration.yaml          # Project config
  ├── agents/                     # Project agents
  ├── skills/                     # Project skills
  └── resume-logs/                # Session resume logs
```

See [configuration.md](configuration.md) for configuration options.

## Environment Variables

```bash
# Claude MPM specific
export CLAUDE_MPM_CONFIG=/path/to/config.yaml
export CLAUDE_MPM_LOG_LEVEL=DEBUG

# Claude Code CLI
export CLAUDE_API_KEY=your-api-key
```

## Health Checks

```bash
# Comprehensive diagnostics
claude-mpm doctor

# Verbose output
claude-mpm doctor --verbose

# Specific checks
claude-mpm doctor --checks installation configuration agents mcp

# Generate report
claude-mpm doctor --verbose --output-file doctor-report.md
```

## Monitoring

### Dashboard

```bash
# Start with monitoring
claude-mpm run --monitor

# Dashboard available at http://localhost:5000
```

### Metrics

- Agent activity tracking
- File operation monitoring
- Session state synchronization
- Performance metrics

See [developer/11-dashboard/README.md](developer/11-dashboard/README.md) for monitoring details.

## Troubleshooting

### Common Issues

**Claude Code not found:**
```bash
# Install Claude Code CLI
# https://docs.anthropic.com/en/docs/claude-code

# Verify installation
claude --version
```

**Permission errors:**
```bash
# Use pipx for isolated installation
pipx install "claude-mpm[monitor]"

# Or install in user directory
pip install --user "claude-mpm[monitor]"
```

**MCP service issues:**
```bash
# Verify MCP services
claude-mpm verify

# Auto-fix issues
claude-mpm verify --fix
```

See [user/troubleshooting.md](user/troubleshooting.md) for complete guide.

## Upgrading

### From PyPI

```bash
# Using pipx
pipx upgrade claude-mpm

# Using pip
pip install --upgrade claude-mpm
```

### From Homebrew

```bash
# Update formula
brew update

# Upgrade package
brew upgrade claude-mpm
```

### Migration

See [user/MIGRATION.md](user/MIGRATION.md) for version-specific migration guides.

## Production Considerations

### Performance

- Enable monitoring for production diagnostics
- Configure auto-save intervals appropriately
- Set context management thresholds
- Monitor memory usage with `cleanup-memory`

### Security

- Validate filesystem restrictions
- Configure input validation
- Review agent capabilities
- Audit MCP service integrations

### Reliability

- Configure auto-save (default: 5 minutes)
- Enable resume logs for session continuity
- Set up monitoring dashboard
- Regular backups of configuration and agents

## Deployment Checklist

- [ ] Install Claude Code CLI (v1.0.92+)
- [ ] Install Claude MPM with monitoring
- [ ] Run `claude-mpm doctor` diagnostics
- [ ] Configure user settings
- [ ] Initialize project configuration
- [ ] Test basic workflow
- [ ] Enable monitoring dashboard
- [ ] Verify MCP services
- [ ] Configure auto-save
- [ ] Set up resume logs

## See Also

- **[Complete Deployment Reference](reference/DEPLOY.md)** - Detailed procedures
- **[Installation Guide](user/installation.md)** - All installation methods
- **[Configuration Reference](configuration.md)** - Configuration options
- **[Troubleshooting](user/troubleshooting.md)** - Common issues
- **[Publishing Guide](developer/publishing-guide.md)** - Release process
- **[User Guide](user/user-guide.md)** - End-user documentation

---

**For detailed deployment procedures**: See [reference/DEPLOY.md](reference/DEPLOY.md)
