# Installation Guide

Claude MPM can be installed via UV, pip, or npm. UV is recommended for the best experience.

## Prerequisites

- **Claude Code** 1.0.60 or later (required)
- **Python** 3.8 or later
- **Package Manager**: UV (recommended), pip, or npm

## Option 1: Install via UV (Recommended)

[UV](https://github.com/astral-sh/uv) is a fast Python package installer that handles virtual environments automatically:

```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install claude-mpm
uv pip install claude-mpm
```

## Option 2: Install via pip

Traditional Python installation:

```bash
# Create virtual environment (recommended)
python -m venv claude-mpm-env
source claude-mpm-env/bin/activate  # On Windows: claude-mpm-env\Scripts\activate

# Install claude-mpm
pip install claude-mpm
```

## Option 3: Install via npm (Wrapper)

The npm package provides a convenient wrapper that will install the Python package on first run:

```bash
npm install -g @bobmatnyc/claude-mpm
```

**Note**: This is just a wrapper - Python 3.8+ must be installed on your system.

## Verify Installation

After installation, verify it works:

```bash
# Show version and help
claude-mpm --help

# Test in interactive mode
claude-mpm

# Run a simple test
claude-mpm run -i "Say hello" --non-interactive
```

## Usage

### Interactive Mode (Default)

```bash
claude-mpm
```

This launches Claude Code with the PM framework loaded, including:
- System instructions for orchestration
- Deployed specialized agents (engineer, qa, research, etc.)
- Delegation-only operation mode

### Non-Interactive Mode

```bash
claude-mpm run -i "Your task here" --non-interactive
```

### Common Options

```bash
# Disable agent deployment
claude-mpm --no-native-agents

# Enable debug logging
claude-mpm --logging DEBUG

# Disable hooks
claude-mpm --no-hooks
```


## Development Installation

For contributing or modifying Claude MPM:

```bash
# Clone repository
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm

# Run development install script (auto-detects UV)
./install_dev.sh
```

## Troubleshooting

### "claude: command not found"

Install Claude Code 1.0.60+ from https://claude.ai/code

### "Python not found"

Install Python 3.8+ from:
- macOS: `brew install python@3.11`
- Ubuntu/Debian: `sudo apt install python3.11`
- Windows/Other: https://python.org

### PEP 668 "externally managed environment" error

Modern systems protect the global Python environment. Solutions:

1. **Use UV** (automatically handles virtual environments)
2. **Use pipx**: `pipx install claude-mpm`
3. **Use a virtual environment** (see pip instructions above)

### npm install fails

Ensure you have Node.js 14+ installed. The npm package is just a wrapper - the actual functionality requires Python.

## Updating

### UV
```bash
uv pip install --upgrade claude-mpm
```

### pip
```bash
pip install --upgrade claude-mpm
```

### npm
```bash
npm update -g @bobmatnyc/claude-mpm
```

## Uninstalling

### UV
```bash
uv pip uninstall claude-mpm
```

### pip
```bash
pip uninstall claude-mpm
```

### npm
```bash
npm uninstall -g @bobmatnyc/claude-mpm
```

## Next Steps

- See [Getting Started Guide](docs/user/01-getting-started/README.md)
- Read the [User Documentation](docs/user/README.md)
- Check out [Example Usage](docs/user/02-guides/basic-usage.md)