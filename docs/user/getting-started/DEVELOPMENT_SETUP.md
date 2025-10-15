# Development Environment Setup

This guide covers setting up a development environment for claude-mpm using Python virtual environments (venv).

## Table of Contents
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Development Workflow](#development-workflow)
- [Managing Dependencies](#managing-dependencies)
- [Troubleshooting](#troubleshooting)

## Quick Start

The claude-mpm development script automatically creates and manages a Python virtual environment:

```bash
# Automatic venv creation and activation
./scripts/claude-mpm --help

# Or manually activate the venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

## Prerequisites

### Required
- **Python 3.8+** (Python 3.11 recommended)
- **pip** (usually comes with Python)
- **git** (for development)

### Installing Python

#### macOS
```bash
# Using Homebrew
brew install python@3.11

# Verify installation
python3 --version
```

#### Linux (Ubuntu/Debian)
```bash
# Install Python
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# Verify installation
python3.11 --version
```

#### Windows
1. Download Python from [python.org](https://www.python.org/downloads/)
2. Run installer and check "Add Python to PATH"
3. Verify in Command Prompt: `python --version`

## Environment Setup

### Automatic Setup (Recommended)

The `./scripts/claude-mpm` script handles all environment setup automatically:

```bash
# Navigate to project directory
cd claude-mpm/

# Run any command - venv is created automatically
./scripts/claude-mpm --help

# The script will:
# 1. Create venv/ directory if it doesn't exist
# 2. Activate the virtual environment
# 3. Install all dependencies from pyproject.toml
# 4. Set up PYTHONPATH correctly
```

### Manual Setup

If you prefer manual control:

```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows

# 3. Upgrade pip
pip install --upgrade pip

# 4. Install claude-mpm in development mode
pip install -e .[dev]

# 5. Verify installation
claude-mpm --version
```

### Project Structure

```
claude-mpm/
├── pyproject.toml          # Python package dependencies
├── scripts/
│   └── claude-mpm          # Auto-managing launcher script
├── venv/                   # Virtual environment (created automatically)
│   ├── bin/                # Executables (Scripts/ on Windows)
│   ├── lib/                # Python packages
│   └── ...
└── src/
    └── claude_mpm/         # Source code
```

## Development Workflow

### Starting Development

```bash
# Option 1: Use the wrapper script (recommended)
./scripts/claude-mpm run

# Option 2: Activate venv manually
source venv/bin/activate
claude-mpm run
```

### Running Tests

```bash
# Run all tests
./scripts/claude-mpm pytest tests/

# Run specific test file
./scripts/claude-mpm pytest tests/test_specific.py

# With coverage report
./scripts/claude-mpm pytest --cov=claude_mpm tests/
```

### Code Quality Checks

```bash
# Auto-fix formatting and imports
make lint-fix

# Run all quality checks
make quality

# Individual checks
./scripts/claude-mpm ruff check src/
./scripts/claude-mpm black --check src/
./scripts/claude-mpm mypy src/
```

### Environment Variables

The development environment sets these automatically:

- `DISABLE_TELEMETRY=1` - Disables telemetry by default
- `PYTHONPATH` - Includes the `src/` directory
- `CLAUDE_MPM_USER_PWD` - Preserves the original working directory
- `CLAUDE_MPM_DEBUG` - Set to 1 when using `--debug` flag

## Managing Dependencies

### Installing Dependencies

All dependencies are managed through `pyproject.toml`:

```bash
# Install core dependencies
pip install -e .

# Install with development tools
pip install -e .[dev]

# Install with all optional features
pip install -e .[agents,dev]
```

### Adding New Dependencies

1. Edit `pyproject.toml`:
   ```toml
   [project]
   dependencies = [
       "existing-package>=1.0.0",
       "new-package>=2.0.0",  # Add here
   ]
   ```

2. Install the updated dependencies:
   ```bash
   pip install -e .[dev]
   ```

3. Update requirements lock file (if using):
   ```bash
   pip freeze > requirements-dev.txt
   ```

### Updating Dependencies

```bash
# Update all dependencies to latest compatible versions
pip install --upgrade -e .[dev]

# Update specific package
pip install --upgrade package-name

# Check for outdated packages
pip list --outdated
```

## Environment Comparison

### venv Advantages

- **Built-in**: No additional installation required
- **Lightweight**: Minimal overhead
- **Standard**: Works everywhere Python works
- **Simple**: Easy to understand and debug
- **Fast setup**: Quick environment creation
- **PyPI packages**: Direct access to all Python packages

### Why venv-only?

Claude MPM previously supported both Mamba and venv, but we've standardized on venv because:

1. **Simplicity**: One clear way to manage environments
2. **Reliability**: Fewer dependency conflicts
3. **Maintenance**: Easier to support and document
4. **Compatibility**: Works in all Python environments
5. **Corporate-friendly**: No issues with conda channels

## Troubleshooting

### Common Issues

#### venv not activating

**macOS/Linux:**
```bash
# Ensure script is executable
chmod +x scripts/claude-mpm

# Try sourcing directly
source venv/bin/activate
```

**Windows:**
```powershell
# If execution policy blocks activation
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate
venv\Scripts\activate
```

#### Python version mismatch

```bash
# Specify Python version explicitly
python3.11 -m venv venv

# Verify correct version
python --version
```

#### Import errors after installation

```bash
# Reinstall in editable mode
pip install -e .[dev]

# Verify PYTHONPATH includes src/
echo $PYTHONPATH  # Should include project/src
```

#### Permission denied errors

```bash
# Fix script permissions
chmod +x scripts/claude-mpm

# Fix venv permissions
chmod -R u+w venv/
```

#### Dependency conflicts

```bash
# Clean install
rm -rf venv/
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
```

### Package Installation Issues

#### SSL/Certificate errors

```bash
# Upgrade certifi
pip install --upgrade certifi

# Use trusted host (temporary workaround)
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -e .[dev]
```

#### Behind corporate proxy

```bash
# Set proxy environment variables
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080

# Or configure pip
pip config set global.proxy http://proxy.company.com:8080
```

### Performance Issues

#### Slow pip installations

```bash
# Use pip cache
pip install -e .[dev] --cache-dir ~/.cache/pip

# Upgrade pip to latest version
pip install --upgrade pip
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .[dev]

      - name: Run tests
        run: pytest tests/
```

### GitLab CI

```yaml
test:
  image: python:3.11
  before_script:
    - python -m venv venv
    - source venv/bin/activate
    - pip install --upgrade pip
    - pip install -e .[dev]
  script:
    - pytest tests/
  cache:
    paths:
      - venv/
```

## Best Practices

1. **Always use venv** for isolated development environments
2. **Keep dependencies updated** but test thoroughly
3. **Use editable installs** (`pip install -e .`) during development
4. **Document new dependencies** in pyproject.toml
5. **Test with clean environments** before committing
6. **Use `make quality`** before pushing code
7. **Activate venv** before running any Python commands

## Cleaning Up

### Remove virtual environment

```bash
# Deactivate first (if activated)
deactivate

# Remove venv directory
rm -rf venv/
```

### Clean Python cache

```bash
# Remove all __pycache__ directories
find . -type d -name __pycache__ -exec rm -rf {} +

# Remove .pyc files
find . -type f -name "*.pyc" -delete
```

## Support

For environment-related issues:

1. **Check this documentation** for common solutions
2. **Review [CLAUDE.md](../../../CLAUDE.md)** for project guidelines
3. **Check existing issues** on [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues)
4. **Create a new issue** with:
   - Python version (`python --version`)
   - Operating system
   - Error messages
   - Steps to reproduce

## Additional Resources

- [Python venv documentation](https://docs.python.org/3/library/venv.html)
- [pip User Guide](https://pip.pypa.io/en/stable/user_guide/)
- [pyproject.toml specification](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [Claude MPM Documentation Index](../../README.md)
