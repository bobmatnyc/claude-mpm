# Deployment Operations Guide

This document provides comprehensive operational guidance for the claude-mpm deployment pipeline, including configuration, workflows, monitoring, and troubleshooting.

## Overview

The claude-mpm deployment system handles:
- Agent deployment to Claude Code's `.claude/agents/` directory
- Version management and semantic versioning
- Multi-channel package distribution (PyPI, npm)
- Environment configuration for agent discovery

## Deployment Components

### 1. Agent Deployment Service
**Location**: `src/claude_mpm/services/agent_deployment.py`

The core service responsible for:
- Building agent YAML files from JSON templates
- Managing version updates and migrations
- Deploying agents to target directories
- Setting environment variables for discovery

**Key Operations**:
- `deploy_agents()`: Main deployment method
- `verify_deployment()`: Post-deployment validation
- `set_claude_environment()`: Environment configuration
- `clean_deployment()`: Cleanup operations

### 2. Version Management
**Location**: `scripts/manage_version.py`

Implements semantic versioning with:
- Git tags as primary version source
- Conventional commits for automatic bumping
- VERSION file synchronization
- Changelog generation

**Version Bump Rules**:
- MAJOR: Breaking changes (`BREAKING CHANGE:` or `feat!:`)
- MINOR: New features (`feat:`)
- PATCH: Bug fixes (`fix:`) or performance (`perf:`)

### 3. Release Automation
**Location**: `scripts/release.py`

Unified release system for:
- PyPI package publishing
- npm package publishing (@bobmatnyc/claude-mpm)
- GitHub release creation
- Version synchronization across channels

## Deployment Workflows

### Standard Agent Deployment

```bash
# 1. Deploy agents to local .claude directory
python -m claude_mpm.services.agent_deployment

# 2. Verify deployment
python scripts/test_agent_deployment.py

# 3. Set environment variables
export CLAUDE_CONFIG_DIR=~/.claude
export CLAUDE_MAX_PARALLEL_SUBAGENTS=5
export CLAUDE_TIMEOUT=600
```

### Version Release Process

```bash
# 1. Check current version
python scripts/manage_version.py --current

# 2. Bump version based on commits
python scripts/manage_version.py --bump auto

# 3. Create release
python scripts/release.py --version patch
```

### Emergency Manual Release

```bash
# Use legacy publish script for manual control
./scripts/publish.sh
# Then manually:
twine upload dist/*
npm publish
```

## Environment Configuration

### Required Environment Variables

```bash
# Agent discovery
CLAUDE_CONFIG_DIR=~/.claude              # Agent configuration directory
CLAUDE_MAX_PARALLEL_SUBAGENTS=5         # Concurrent agent limit
CLAUDE_TIMEOUT=600                      # Agent execution timeout (seconds)

# Development
PYTHONPATH=$PYTHONPATH:src              # Include source in Python path
NODE_ENV=production                     # Node environment for npm
```

### Production Environment Setup

1. **System Requirements**:
   - Python 3.8+
   - Node.js 14+
   - Git 2.0+
   - Write access to ~/.claude/

2. **Credentials Required**:
   - PyPI: ~/.pypirc configuration
   - npm: npm login credentials
   - GitHub: gh CLI authentication

## Monitoring and Health Checks

### Deployment Metrics

Monitor these key metrics:
- **Deployment Time**: Target < 10 seconds for full deployment
- **Agent Count**: Should match template count (typically 8)
- **Error Rate**: Must be 0 for successful deployment
- **Version Migration**: Track agents needing updates

### Health Check Commands

```bash
# Verify agent deployment
python -c "from claude_mpm.services.agents.deployment import AgentDeploymentService; \
          s = AgentDeploymentService(); \
          print(s.verify_deployment())"

# List available agents
python -c "from claude_mpm.services.agents.deployment import AgentDeploymentService; \
          s = AgentDeploymentService(); \
          print(s.list_available_agents())"

# Check version sync
python scripts/check_version_sync.py
```

### Log Monitoring

Key log files to monitor:
- Agent deployment logs: Check for deployment errors
- Version migration logs: Track version updates
- Environment setup logs: Verify configuration

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Agent Deployment Failures

**Symptom**: Agents not appearing in Claude Code
```bash
# Check deployment
ls -la ~/.claude/agents/

# Verify environment
echo $CLAUDE_CONFIG_DIR

# Re-deploy with force
python -m claude_mpm.services.agent_deployment --force
```

#### 2. Version Mismatch

**Symptom**: PyPI and npm versions out of sync
```bash
# Check versions
cat VERSION
npm view @bobmatnyc/claude-mpm version

# Force sync
python scripts/release.py --sync-only
```

#### 3. Template Loading Errors

**Symptom**: JSON parse errors during deployment
```bash
# Validate templates
for f in src/claude_mpm/agents/templates/*.json; do
    jq . "$f" > /dev/null || echo "Invalid: $f"
done

# Check base agent
jq . src/claude_mpm/agents/base_agent.json
```

#### 4. Environment Not Set

**Symptom**: Agents not discovered by Claude Code
```bash
# Set in current shell
source <(python -c "from claude_mpm.services.agents.deployment import AgentDeploymentService; \
                     s = AgentDeploymentService(); \
                     for k,v in s.set_claude_environment().items(): \
                         print(f'export {k}={v}')")

# Add to shell profile for persistence
echo 'export CLAUDE_CONFIG_DIR=~/.claude' >> ~/.bashrc
```

## Rollback Procedures

### Agent Rollback

```bash
# 1. Backup current agents
cp -r ~/.claude/agents ~/.claude/agents.backup

# 2. Clean system agents
python -c "from claude_mpm.services.agents.deployment import AgentDeploymentService; \
          s = AgentDeploymentService(); \
          s.clean_deployment()"

# 3. Deploy previous version
git checkout v2.0.0
python -m claude_mpm.services.agent_deployment
```

### Version Rollback

```bash
# 1. Delete incorrect tag
git tag -d v2.1.0
git push origin :refs/tags/v2.1.0

# 2. Reset VERSION file
echo "2.0.0" > VERSION

# 3. Revert package.json
git checkout HEAD~1 package.json

# 4. Update PyPI (cannot delete, only yank)
# Visit https://pypi.org/project/claude-mpm/
# Yank the incorrect version

# 5. npm unpublish (within 72 hours)
npm unpublish @bobmatnyc/claude-mpm@2.1.0
```

## Performance Optimization

### Deployment Performance

1. **Skip Unchanged Agents**: 
   - Version checking prevents unnecessary rebuilds
   - Typical skip rate: 70-90% after initial deployment

2. **Parallel Processing**:
   - Agent deployments are independent
   - Consider parallel deployment for large agent sets

3. **File I/O Optimization**:
   - Minimize template reads
   - Batch YAML writes
   - Use in-memory building

### Runtime Performance

1. **Agent Discovery**:
   - Cache agent metadata
   - Minimize directory scans
   - Use indexed lookups

2. **Resource Limits**:
   ```bash
   # Adjust based on system resources
   export CLAUDE_MAX_PARALLEL_SUBAGENTS=3  # For low-memory systems
   export CLAUDE_TIMEOUT=300               # For faster timeouts
   ```

## Security Considerations

### Deployment Security

1. **File Permissions**:
   ```bash
   # Ensure proper permissions
   chmod 755 ~/.claude
   chmod 644 ~/.claude/agents/*.yaml
   ```

2. **Agent Validation**:
   - Only system agents (claude-mpm authored) are managed
   - User agents are preserved during cleanup
   - Version tracking prevents tampering

3. **Credential Management**:
   - Never commit credentials
   - Use environment variables
   - Rotate tokens regularly

## Continuous Integration

### Recommended CI/CD Pipeline

```yaml
# Example GitHub Actions workflow
name: Deploy Claude MPM

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
          
      - name: Install dependencies
        run: |
          pip install -e .
          pip install build twine
          
      - name: Run tests
        run: ./scripts/run_all_tests.sh
        
      - name: Deploy agents
        run: python -m claude_mpm.services.agent_deployment
        
      - name: Build and publish
        run: python scripts/release.py --version ${{ github.ref_name }}
```

## Best Practices

### Deployment Best Practices

1. **Always Test First**:
   ```bash
   # Test deployment to temporary directory
   python scripts/test_agent_deployment.py
   ```

2. **Version Everything**:
   - Tag releases consistently
   - Document changes in CHANGELOG
   - Keep VERSION file updated

3. **Monitor Deployments**:
   - Log all deployment operations
   - Track success/failure metrics
   - Set up alerts for failures

4. **Backup Before Major Changes**:
   ```bash
   tar -czf claude-backup-$(date +%Y%m%d).tar.gz ~/.claude/
   ```

### Operational Excellence

1. **Documentation**:
   - Keep operational docs updated
   - Document all manual interventions
   - Maintain runbooks for common issues

2. **Automation**:
   - Automate repetitive tasks
   - Use scripts for consistency
   - Implement health checks

3. **Communication**:
   - Announce deployments
   - Document breaking changes
   - Provide migration guides

## Conclusion

The claude-mpm deployment system is designed for reliability, consistency, and ease of operation. By following these operational guidelines, you can ensure smooth deployments and quick resolution of any issues that arise.

For additional support, refer to:
- [DEPLOY.md](DEPLOY.md) - Deployment procedures
- [VERSIONING.md](VERSIONING.md) - Version management
- [QA.md](QA.md) - Quality assurance procedures