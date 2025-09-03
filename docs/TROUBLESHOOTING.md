# Claude MPM Troubleshooting Guide

**Version**: 4.2.2  
**Last Updated**: September 2, 2025

Comprehensive troubleshooting guide for common Claude MPM issues with step-by-step solutions.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Installation Issues](#installation-issues)
- [Agent Problems](#agent-problems)
- [Service Issues](#service-issues)
- [Performance Problems](#performance-problems)
- [Development Issues](#development-issues)
- [Quality Gate Failures](#quality-gate-failures)
- [Deployment Problems](#deployment-problems)
- [Getting Help](#getting-help)

## Quick Diagnostics

### System Health Check

```bash
# Quick system status
./scripts/claude-mpm info

# Verify installation
./scripts/claude-mpm --version
python -c "import claude_mpm; print(claude_mpm.__version__)"

# Check dependencies
pip list | grep claude-mpm
pip check

# Test basic functionality  
./scripts/claude-mpm agents list --system
```

### Environment Verification

```bash
# Check Python environment
python --version
which python

# Verify virtual environment (if using)
echo $VIRTUAL_ENV
pip list | head -10

# Check PATH and executables
which claude-mpm
echo $PATH | tr ':' '\n' | grep claude
```

### Log Analysis

```bash
# Check recent logs
tail -50 .claude-mpm/logs/claude-mpm.log

# Search for errors
grep -n "ERROR\|CRITICAL" .claude-mpm/logs/*.log | tail -20

# Enable debug logging
export CLAUDE_MPM_LOG_LEVEL=DEBUG
./scripts/claude-mpm run --debug
```

## Installation Issues

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'claude_mpm'`

**Solutions:**

```bash
# Solution 1: Reinstall in development mode
pip uninstall claude-mpm
cd /path/to/claude-mpm
pip install -e .

# Solution 2: Check PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
python -c "import sys; print('\n'.join(sys.path))"

# Solution 3: Verify installation
pip show claude-mpm
ls -la $(pip show claude-mpm | grep Location | cut -d' ' -f2)/claude_mpm/
```

### Permission Errors

**Problem**: `Permission denied` during installation

**Solutions:**

```bash
# Solution 1: User installation
pip install --user -e .

# Solution 2: Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -e .

# Solution 3: Check file permissions
ls -la setup.py pyproject.toml
chmod +r setup.py pyproject.toml
```

### Dependency Conflicts

**Problem**: Conflicting package versions

**Solutions:**

```bash
# Check for conflicts
pip check

# View dependency tree
pip install pipdeptree
pipdeptree

# Create clean environment
python -m venv clean-env
source clean-env/bin/activate
pip install -e .

# Use requirements file
pip install -r requirements.txt
```

### Command Not Found

**Problem**: `claude-mpm: command not found`

**Solutions:**

```bash
# Check installation location
pip show claude-mpm | grep Location

# Add to PATH
export PATH="$PATH:$HOME/.local/bin"

# Use full path temporarily
python -m claude_mpm --version

# Create alias
alias claude-mpm='python -m claude_mpm'
```

## Agent Problems

### Agent Not Found

**Problem**: `ValueError: No agent found with name: my_agent`

**Diagnosis:**

```bash
# Check agent hierarchy
./scripts/claude-mpm agents list --by-tier

# Verify file exists
ls -la .claude-mpm/agents/my_agent.*

# Check file format
file .claude-mpm/agents/my_agent.*
```

**Solutions:**

```bash
# Fix file naming (must match agent ID)
mv .claude-mpm/agents/wrong_name.md .claude-mpm/agents/my_agent.md

# Fix frontmatter issues
./scripts/claude-mpm agents fix my_agent --dry-run
./scripts/claude-mpm agents fix my_agent

# Verify agent loads
python -c "
from claude_mpm.agents.agent_loader import get_agent_prompt
try:
    prompt = get_agent_prompt('my_agent')
    print('✅ Agent loaded successfully')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

### Wrong Agent Version Loading

**Problem**: System agent loads instead of project agent

**Diagnosis:**

```bash
# Check tier precedence
./scripts/claude-mpm agents list --by-tier

# View specific agent details
./scripts/claude-mpm agents view my_agent

# Check file naming consistency
ls -la .claude-mpm/agents/
```

**Solutions:**

```bash
# Ensure correct file naming
# File name must match agent_id in frontmatter
cat .claude-mpm/agents/my_agent.md | head -10

# Fix naming mismatch
# If agent_id is "engineer" but file is "eng.md":
mv .claude-mpm/agents/eng.md .claude-mpm/agents/engineer.md

# Force cache refresh
python -c "
from claude_mpm.agents.agent_loader import clear_agent_cache
clear_agent_cache('my_agent')
"
```

### Schema Validation Errors

**Problem**: Agent behaves unexpectedly due to invalid configuration

**Diagnosis:**

```bash
# Check for validation issues
./scripts/claude-mpm agents fix --all --dry-run

# View agent configuration
./scripts/claude-mpm agents view problematic_agent

# Manual validation
python -c "
from claude_mpm.validation.agent_validator import validate_agent_file
result = validate_agent_file('.claude-mpm/agents/my_agent.md')
print(f'Valid: {result.valid}')
print(f'Errors: {result.errors}')
"
```

**Solutions:**

```bash
# Auto-fix common issues
./scripts/claude-mpm agents fix my_agent

# Fix manually
# Common issues:
# - Missing version field
# - Incorrect field types (string instead of array)
# - Invalid field names

# Example fix:
cat > .claude-mpm/agents/my_agent.md << 'EOF'
---
description: My agent description
version: 1.0.0
tools: ["tool1", "tool2"]  # Array, not string
---
# My Agent
Instructions here...
EOF
```

### Agent Deployment Issues

**Problem**: Agents not deploying to `.claude/agents/`

**Diagnosis:**

```bash
# Check deployment status
./scripts/claude-mpm agents list --deployed

# Verify target directory
ls -la .claude/agents/

# Check deployment logs
grep "deploy" .claude-mpm/logs/claude-mpm.log | tail -10
```

**Solutions:**

```bash
# Force clean deployment
./scripts/claude-mpm agents clean
./scripts/claude-mpm agents force-deploy

# Check permissions
ls -ld .claude/
mkdir -p .claude/agents
chmod 755 .claude .claude/agents

# Manual verification
./scripts/claude-mpm agents deploy --verbose
ls -la .claude/agents/
```

## Service Issues

### SocketIO Connection Errors

**Problem**: WebSocket connection failures

**Diagnosis:**

```bash
# Check port availability
netstat -an | grep 876[0-9]
lsof -i :8765

# Test connection manually
curl -I http://localhost:8765
telnet localhost 8765
```

**Solutions:**

```bash
# Kill existing processes
pkill -f socketio_server
pkill -f claude-mpm

# Use different port
export CLAUDE_MPM_SOCKETIO_PORT=8766
./scripts/claude-mpm run

# Check firewall
# Linux
sudo ufw status
# macOS  
sudo pfctl -sr | grep 8765
```

### Service Registration Errors

**Problem**: `ServiceError: Service not registered`

**Diagnosis:**

```bash
# Check service registration
python -c "
from claude_mpm.services.core import ServiceContainer
container = ServiceContainer()
print('Registered services:')
for service in container.list_registered():
    print(f'  {service}')
"

# Enable debug logging
export CLAUDE_MPM_LOG_LEVEL=DEBUG
```

**Solutions:**

```bash
# Restart with clean state
./scripts/claude-mpm run --clean-start

# Manual service registration check
python -c "
from claude_mpm.services.core import ServiceContainer
from claude_mpm.services.agents import IAgentRegistry, AgentRegistry

container = ServiceContainer()
if not container.is_registered(IAgentRegistry):
    container.register(IAgentRegistry, AgentRegistry, singleton=True)
    print('Service registered successfully')
"
```

### Cache Issues

**Problem**: Changes not reflected, stale data

**Diagnosis:**

```bash
# Check cache status
python -c "
from claude_mpm.services.core.cache import CacheService
cache = CacheService.get_instance()
stats = cache.get_stats()
print(f'Hit rate: {stats[\"hit_rate_percent\"]}%')
print(f'Total entries: {stats[\"total_entries\"]}')
"
```

**Solutions:**

```bash
# Clear all caches
python -c "
from claude_mpm.services.core.cache import CacheService
from claude_mpm.agents.agent_loader import clear_agent_cache
clear_agent_cache()  # Agent cache
CacheService.get_instance().clear()  # Service cache
"

# Disable caching temporarily
export CLAUDE_MPM_ENABLE_CACHE=false
./scripts/claude-mpm run

# Adjust cache TTL
export CLAUDE_MPM_CACHE_TTL=300  # 5 minutes
```

## Performance Problems

### Slow Startup

**Problem**: Claude MPM takes long time to initialize

**Diagnosis:**

```bash
# Profile startup time
time ./scripts/claude-mpm --help

# Check for blocking operations
strace -c ./scripts/claude-mpm --help 2>&1 | tail -20

# Monitor system resources
top -p $(pgrep -f claude-mpm)
```

**Solutions:**

```bash
# Enable cache warming
export CLAUDE_MPM_WARM_CACHE=true

# Check lazy loading implementation
grep -r "lazy_import" src/claude_mpm/ | wc -l

# Optimize agent discovery
export CLAUDE_MPM_AGENT_SCAN_INTERVAL=3600  # 1 hour

# Use faster Python interpreter
python3.11 -m claude_mpm --version  # If available
```

### High Memory Usage

**Problem**: Excessive memory consumption

**Diagnosis:**

```bash
# Monitor memory usage
python -m memory_profiler ./scripts/claude-mpm run &
ps aux | grep claude-mpm

# Check for memory leaks
valgrind --tool=memcheck --leak-check=full python -m claude_mpm run
```

**Solutions:**

```bash
# Reduce cache size
export CLAUDE_MPM_CACHE_MAX_SIZE=100MB

# Optimize agent loading
export CLAUDE_MPM_LAZY_AGENT_LOADING=true

# Garbage collection tuning
export PYTHONHASHSEED=0
python -X dev -m claude_mpm run  # Development mode
```

### Network Timeouts

**Problem**: Network operations timing out

**Diagnosis:**

```bash
# Test network connectivity
ping github.com
curl -I https://api.anthropic.com/health

# Check DNS resolution
nslookup api.anthropic.com
dig +short api.anthropic.com
```

**Solutions:**

```bash
# Increase timeout values
export CLAUDE_MPM_NETWORK_TIMEOUT=60
export CLAUDE_MPM_RETRY_ATTEMPTS=3

# Use different network interface
export http_proxy=http://proxy:8080
export https_proxy=http://proxy:8080

# Test with minimal configuration
./scripts/claude-mpm run --offline-mode
```

## Development Issues

### Import Path Problems

**Problem**: Relative import errors in development

**Solutions:**

```bash
# Use absolute imports
# Good: from claude_mpm.services.agents import AgentRegistry
# Bad:  from ..agents import AgentRegistry

# Set PYTHONPATH correctly
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Verify module structure
find src/claude_mpm/ -name "*.py" | head -10
python -c "import claude_mpm.services.agents; print('OK')"
```

### Git Hook Failures

**Problem**: Pre-commit hooks failing

**Diagnosis:**

```bash
# Check hook status
ls -la .git/hooks/
cat .git/hooks/pre-commit

# Test hooks manually
.git/hooks/pre-commit
.git/hooks/prepare-commit-msg .git/COMMIT_EDITMSG
```

**Solutions:**

```bash
# Reinstall hooks
rm .git/hooks/pre-commit .git/hooks/prepare-commit-msg
./scripts/install_hooks.sh

# Skip hooks temporarily (emergency only)
git commit --no-verify -m "Emergency commit"

# Fix hook permissions
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/prepare-commit-msg
```

### IDE Integration Issues

**Problem**: IDE not recognizing modules

**Solutions:**

```bash
# VS Code settings (.vscode/settings.json)
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.analysis.extraPaths": ["./src"],
    "python.terminal.activateEnvironment": true
}

# PyCharm: Mark src as Sources Root
# Right-click src/ -> Mark Directory as -> Sources Root

# Update IDE settings
code --install-extension ms-python.python
code --install-extension ms-python.pylance
```

## Quality Gate Failures

### Linting Errors

**Problem**: `make quality` fails with linting errors

**Diagnosis:**

```bash
# Run individual linting tools
ruff check src/
black --check src/
isort --check-only src/
flake8 src/
mypy src/
```

**Solutions:**

```bash
# Auto-fix what can be fixed
make lint-fix

# Fix remaining issues manually
ruff check --fix src/          # Fix Ruff issues
black src/                     # Format code
isort src/                     # Sort imports

# Address mypy issues
# Add type annotations
# Fix import issues
# Use # type: ignore for unavoidable issues
```

### Test Failures

**Problem**: Tests failing during quality check

**Diagnosis:**

```bash
# Run tests with verbose output
pytest -v tests/

# Run specific failing test
pytest -v tests/test_specific.py::test_function

# Check test dependencies
pip list | grep pytest
```

**Solutions:**

```bash
# Update test dependencies
pip install pytest pytest-cov pytest-mock

# Fix test isolation issues
pytest --lf  # Run last failed tests
pytest -k "test_name"  # Run specific test pattern

# Update fixtures
# Check for hardcoded paths
# Update mocked data
```

### Coverage Issues

**Problem**: Test coverage below threshold

**Diagnosis:**

```bash
# Generate coverage report
pytest --cov=claude_mpm --cov-report=html tests/
open htmlcov/index.html

# Find uncovered lines
pytest --cov=claude_mpm --cov-report=term-missing tests/
```

**Solutions:**

```bash
# Add tests for uncovered code
# Focus on business logic
# Add integration tests
# Update coverage configuration in pyproject.toml

[tool.coverage.run]
omit = [
    "*/tests/*",
    "*/venv/*",
    "*/build/*"
]
```

## Deployment Problems

### Build Failures

**Problem**: `python -m build` fails

**Diagnosis:**

```bash
# Check build dependencies
pip install --upgrade build setuptools wheel

# Verify project configuration
python -m build --help
cat pyproject.toml | grep -A10 "\[build-system\]"
```

**Solutions:**

```bash
# Clean build environment
rm -rf dist/ build/ *.egg-info/

# Update build dependencies
pip install --upgrade build setuptools wheel pip

# Build with verbose output
python -m build --sdist --wheel --outdir dist/ . --verbose

# Check generated files
tar -tzf dist/claude-mpm-*.tar.gz | head -20
unzip -l dist/claude-mpm-*.whl | head -20
```

### PyPI Upload Issues

**Problem**: `twine upload` fails

**Diagnosis:**

```bash
# Check package validity
twine check dist/*

# Verify authentication
ls ~/.pypirc
cat ~/.pypirc  # Check credentials
```

**Solutions:**

```bash
# Configure PyPI credentials
pip install twine
twine configure

# Upload to test PyPI first
twine upload --repository testpypi dist/*

# Fix package metadata
# Update version in pyproject.toml
# Fix long_description format
# Update classifiers
```

### Version Inconsistencies

**Problem**: Version mismatch between files

**Diagnosis:**

```bash
# Check all version sources
./scripts/manage_version.py status
cat VERSION
cat BUILD_NUMBER
python -c "import claude_mpm; print(claude_mpm.__version__)"
grep -r "version.*=" pyproject.toml
```

**Solutions:**

```bash
# Rebuild version consistency
./scripts/manage_version.py rebuild

# Manual version sync
echo "4.2.2" > VERSION
echo "332" > BUILD_NUMBER
./scripts/manage_version.py sync

# Reinstall after version fix
pip install -e .
```

## Getting Help

### Collecting Diagnostic Information

When reporting issues, include:

```bash
# System information
./scripts/claude-mpm info > system-info.txt

# Version information
./scripts/claude-mpm --version
python --version
pip list | grep claude-mpm

# Error logs
tail -100 .claude-mpm/logs/claude-mpm.log > error-logs.txt

# Configuration
cat .claude-mpm/config/*.yaml > config-info.txt  # If exists

# Environment variables
env | grep CLAUDE_MPM > env-vars.txt
```

### Debug Mode

```bash
# Enable comprehensive debugging
export CLAUDE_MPM_LOG_LEVEL=DEBUG
export CLAUDE_MPM_DEBUG=true
./scripts/claude-mpm run --debug --verbose > debug-output.txt 2>&1
```

### Minimal Reproduction

Create minimal test case:

```bash
# Create clean test environment
mkdir test-claude-mpm
cd test-claude-mpm
python -m venv venv
source venv/bin/activate

# Install minimal version
pip install claude-mpm

# Test specific functionality
claude-mpm --version
claude-mpm agents list --system

# Document exact steps that reproduce issue
```

### Community Support

1. **Search Existing Issues**: Check GitHub Issues for similar problems
2. **Documentation**: Re-read relevant documentation sections
3. **Discord/Slack**: Join community channels for real-time help
4. **Stack Overflow**: Tag questions with `claude-mpm`
5. **GitHub Discussions**: For general questions and feature requests

### Creating Issue Reports

Include in your issue report:

- **Environment**: OS, Python version, Claude MPM version
- **Steps to Reproduce**: Exact commands and configuration
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Logs**: Relevant log excerpts (not full logs)
- **System Info**: Output of `./scripts/claude-mpm info`

---

## Related Documentation

- [DEVELOPMENT.md](DEVELOPMENT.md) - Development workflows and debugging
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment and release procedures  
- [AGENTS.md](AGENTS.md) - Agent troubleshooting and management
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture for deep debugging