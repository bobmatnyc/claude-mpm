# Development Setup

This guide walks you through setting up a complete development environment for Claude MPM.

## Prerequisites

### System Requirements

- **Operating System**: macOS, Linux, or Windows with WSL2
- **Python**: 3.8 or higher
- **Memory**: 8GB RAM minimum (16GB recommended)
- **Disk Space**: 2GB free space

### Required Software

```bash
# Check Python version (3.8+ required)
python --version

# Check pip availability
pip --version

# Check git installation
git --version

# Check Claude CLI (must be installed separately)
claude --version
```

### Installing Claude CLI

Claude MPM requires the Claude CLI to be installed:

```bash
# macOS with Homebrew
brew tap anthropics/claude
brew install claude

# Linux/WSL
# Download from https://claude.ai/cli
# Follow installation instructions

# Verify installation
claude --version
```

## Repository Setup

### 1. Clone the Repository

```bash
# Clone via HTTPS
git clone https://github.com/your-repo/claude-mpm.git
cd claude-mpm

# Or clone via SSH
git clone git@github.com:your-repo/claude-mpm.git
cd claude-mpm
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Verify activation
which python
# Should show: /path/to/claude-mpm/venv/bin/python
```

### 3. Install Dependencies

```bash
# Install claude-mpm in development mode
pip install -e ".[dev]"

# This installs:
# - claude-mpm package in editable mode
# - All runtime dependencies
# - Development dependencies (pytest, black, flake8, etc.)

# Verify installation
pip list | grep claude-mpm
# Should show: claude-mpm (version) /path/to/claude-mpm
```

### 4. Install Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Run hooks manually (optional)
pre-commit run --all-files
```

## Development Tools Setup

### 1. Code Formatting (Black)

```bash
# Black is installed with dev dependencies
# Configure in pyproject.toml
cat pyproject.toml | grep -A 10 "[tool.black]"

# Format code
black src/ tests/

# Check formatting without changes
black --check src/ tests/
```

### 2. Linting (Flake8)

```bash
# Configure flake8
cat > .flake8 << EOF
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = .git,__pycache__,venv,build,dist
EOF

# Run linting
flake8 src/ tests/
```

### 3. Type Checking (MyPy)

```bash
# Configure mypy
cat > mypy.ini << EOF
[mypy]
python_version = 3.8
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True

[mypy-tests.*]
disallow_untyped_defs = False
EOF

# Run type checking
mypy src/
```

### 4. Testing (Pytest)

```bash
# Configure pytest
cat > pytest.ini << EOF
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
EOF

# Run tests
pytest

# With coverage
pytest --cov=src/claude_mpm --cov-report=html
```

## IDE Configuration

### Visual Studio Code

1. **Install Python Extension**
   ```bash
   code --install-extension ms-python.python
   ```

2. **Create Workspace Settings**
   ```bash
   mkdir -p .vscode
   cat > .vscode/settings.json << 'EOF'
   {
       "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
       "python.linting.enabled": true,
       "python.linting.flake8Enabled": true,
       "python.linting.pylintEnabled": false,
       "python.formatting.provider": "black",
       "python.testing.pytestEnabled": true,
       "python.testing.unittestEnabled": false,
       "editor.formatOnSave": true,
       "editor.rulers": [88],
       "[python]": {
           "editor.codeActionsOnSave": {
               "source.organizeImports": true
           }
       },
       "files.exclude": {
           "**/__pycache__": true,
           "**/*.pyc": true,
           ".pytest_cache": true,
           ".mypy_cache": true
       }
   }
   EOF
   ```

3. **Create Launch Configuration**
   ```bash
   cat > .vscode/launch.json << 'EOF'
   {
       "version": "0.2.0",
       "configurations": [
           {
               "name": "Claude MPM",
               "type": "python",
               "request": "launch",
               "module": "claude_mpm.cli_main",
               "args": [],
               "console": "integratedTerminal",
               "justMyCode": false
           },
           {
               "name": "Debug Current Test",
               "type": "python",
               "request": "launch",
               "module": "pytest",
               "args": ["-vv", "${file}"],
               "console": "integratedTerminal",
               "justMyCode": false
           }
       ]
   }
   EOF
   ```

### PyCharm

1. **Open Project**
   - File → Open → Select claude-mpm directory

2. **Configure Interpreter**
   - PyCharm → Preferences → Project → Python Interpreter
   - Click gear icon → Add
   - Select "Existing Environment"
   - Choose: `claude-mpm/venv/bin/python`

3. **Configure Code Style**
   - Preferences → Editor → Code Style → Python
   - Set "Line length" to 88
   - Enable "Use Black formatter"

4. **Configure Testing**
   - Preferences → Tools → Python Integrated Tools
   - Set "Default test runner" to pytest
   - Set "Docstring format" to Google

## Environment Configuration

### 1. Create Environment File

```bash
# Create .env file for development
cat > .env << 'EOF'
# Development settings
CLAUDE_MPM_DEBUG=true
CLAUDE_MPM_LOG_LEVEL=DEBUG
CLAUDE_MPM_LOG_DIR=./logs

# Subprocess settings
CLAUDE_MPM_SUBPROCESS_DEBUG=true
CLAUDE_MPM_SUBPROCESS_TIMEOUT=300

# Hook settings
CLAUDE_MPM_HOOK_PORT=8080
CLAUDE_MPM_HOOK_DEBUG=true

# Agent settings
CLAUDE_MPM_MAX_AGENTS=4
CLAUDE_MPM_AGENT_TIMEOUT=300

# Ticket settings
CLAUDE_MPM_NO_TICKETS=false
AI_TRACKDOWN_API_KEY=your-dev-key-here
EOF

# Load environment variables
source .env
```

### 2. Create Local Configuration

```bash
# Create local config directory
mkdir -p .claude-pm/config

# Create development config
cat > .claude-pm/config/development.yaml << 'EOF'
# Development configuration
debug: true
log_level: DEBUG

orchestrator:
  type: subprocess
  timeout: 300
  max_parallel_agents: 4

hooks:
  enabled: true
  debug: true
  port: 8080

agents:
  discovery_paths:
    - .claude-pm/agents/project-specific
    - ~/.claude-pm/agents/user-defined
    - src/claude_mpm/agents/templates

tickets:
  enabled: true
  integrations:
    ai_trackdown:
      enabled: true
      project_id: dev-project
EOF
```

## Dependency Management

### Core Dependencies

```bash
# View core dependencies
cat pyproject.toml | grep -A 20 "dependencies ="

# Key dependencies:
# - pydantic: Data validation
# - rich: Terminal formatting
# - click: CLI framework
# - pyyaml: Configuration
# - aiohttp: Async HTTP
```

### Development Dependencies

```bash
# View dev dependencies
cat pyproject.toml | grep -A 20 "[project.optional-dependencies]"

# Key dev dependencies:
# - pytest: Testing framework
# - black: Code formatter
# - flake8: Linter
# - mypy: Type checker
# - coverage: Code coverage
```

### Updating Dependencies

```bash
# Update all dependencies
pip install --upgrade -e ".[dev]"

# Update specific dependency
pip install --upgrade pytest

# Generate requirements file
pip freeze > requirements-dev.txt
```

## Troubleshooting Setup

### Common Issues

#### 1. Python Version Mismatch
```bash
# Error: Python 3.7 or lower
# Solution: Install Python 3.8+
pyenv install 3.10.0
pyenv local 3.10.0
```

#### 2. Claude CLI Not Found
```bash
# Error: claude: command not found
# Solution: Add Claude to PATH
export PATH="$PATH:/path/to/claude/bin"
# Add to ~/.bashrc or ~/.zshrc
```

#### 3. Import Errors
```bash
# Error: ModuleNotFoundError: claude_mpm
# Solution: Install in development mode
pip install -e .

# Verify PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
```

#### 4. Permission Errors
```bash
# Error: Permission denied
# Solution: Fix script permissions
chmod +x scripts/*.sh
chmod +x claude-mpm
```

#### 5. Virtual Environment Issues
```bash
# Error: No module named 'venv'
# Solution: Install python3-venv
sudo apt-get install python3-venv  # Ubuntu/Debian
sudo yum install python3-venv       # CentOS/RHEL
```

## Verification

### Run Verification Script

```bash
# Create verification script
cat > scripts/verify_setup.sh << 'EOF'
#!/bin/bash
set -e

echo "Verifying Claude MPM development setup..."

# Check Python version
python_version=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [[ $(echo "$python_version >= 3.8" | bc) -eq 1 ]]; then
    echo "✓ Python $python_version"
else
    echo "✗ Python $python_version (3.8+ required)"
    exit 1
fi

# Check Claude CLI
if command -v claude &> /dev/null; then
    echo "✓ Claude CLI installed"
else
    echo "✗ Claude CLI not found"
    exit 1
fi

# Check package installation
if pip show claude-mpm &> /dev/null; then
    echo "✓ claude-mpm installed"
else
    echo "✗ claude-mpm not installed"
    exit 1
fi

# Check imports
python -c "import claude_mpm" && echo "✓ Can import claude_mpm"
python -c "from claude_mpm.core import ClaudeLauncher" && echo "✓ Can import core modules"

# Run basic tests
if pytest tests/test_imports.py -v; then
    echo "✓ Basic tests pass"
else
    echo "✗ Basic tests fail"
    exit 1
fi

# Check CLI
if ./claude-mpm --version; then
    echo "✓ CLI works"
else
    echo "✗ CLI fails"
    exit 1
fi

echo ""
echo "✅ Setup verification complete!"
EOF

chmod +x scripts/verify_setup.sh
./scripts/verify_setup.sh
```

## Next Steps

1. **Read Architecture**: Understand the [system architecture](../01-architecture/)
2. **Review Standards**: Follow [coding standards](coding-standards.md)
3. **Run Tests**: Learn the [testing approach](testing.md)
4. **Start Coding**: Pick an issue and start contributing!

## Quick Reference

```bash
# Activate environment
source venv/bin/activate

# Run tests
pytest

# Format code
black src/ tests/

# Run linter
flake8 src/

# Type check
mypy src/

# Run claude-mpm
./claude-mpm

# Run with debug
CLAUDE_MPM_DEBUG=true ./claude-mpm
```