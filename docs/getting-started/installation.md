# Installation

Install Claude MPM and verify Claude Code CLI is available.

## Requirements

- **Claude Code CLI v1.0.92+**: https://docs.anthropic.com/en/docs/claude-code
- **Python 3.11 - 3.13** (Python 3.13 recommended)

> **Python Version Warning**:
> - macOS default Python 3.9 is **too old** - installation will fail or get outdated version
> - Python 3.13 is **recommended** and fully tested
> - Python 3.14 is **NOT yet supported** - installation will fail

**Tip**: Use [ASDF version manager](../guides/asdf-tool-versions.md) to manage Python and uv versions consistently across projects.

## Critical: Installation Location

**IMPORTANT**: Install Claude MPM from your **home directory**, NOT from within a cloned git repository.

```bash
# CORRECT - Install from home directory
cd ~
uv tool install claude-mpm[monitor,data-processing] --python 3.13

# WRONG - Do NOT install from within the git repo
cd ~/Projects/claude-mpm  # <-- This causes conflicts!
uv tool install claude-mpm  # <-- Will fail or behave unexpectedly
```

Installing from within the git repository causes path conflicts and unexpected behavior.

## Install (Recommended: uv with Python 3.13)

```bash
# Navigate to home directory first
cd ~

# Install with explicit Python version (recommended)
uv tool install "claude-mpm[monitor,data-processing]" --python 3.13

# Optional: Install companion MCP tools
uv tool install kuzu-memory --python 3.13
uv tool install mcp-browser --python 3.13
uv tool install mcp-ticketer --python 3.13
uv tool install mcp-vector-search --python 3.13
```

## Install (pipx)

```bash
# Navigate to home directory first
cd ~

python -m pip install --user pipx
python -m pipx ensurepath

# Ensure you have Python 3.11+ in your PATH
pipx install "claude-mpm[monitor]"
```

## Install (pip)

```bash
pip install "claude-mpm[monitor]"
```

## Install (Homebrew, macOS)

```bash
brew tap bobmatnyc/tools
brew install claude-mpm
```

## Install from Source (Developers)

```bash
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm
pip install -e ".[dev,monitor]"
```

## Post-Installation Setup (Required)

After installing claude-mpm, you must complete these setup steps before running `claude-mpm doctor`:

### 1. Create Required Directories

```bash
mkdir -p ~/.claude/{responses,memory,logs}
```

### 2. Deploy Agents

```bash
claude-mpm agents deploy
```

### 3. Add Skill Source (Optional but Recommended)

```bash
claude-mpm skill-source add https://github.com/bobmatnyc/claude-mpm-skills
```

### 4. Verify Installation

```bash
# Run diagnostics
claude-mpm doctor --verbose

# Check versions
claude --version
claude-mpm --version
```

### 5. Auto-Configure (Optional)

```bash
# Detect your project stack and deploy appropriate agents
claude-mpm auto-configure
```

## Complete Installation Sequence

Here is the complete installation sequence for a fresh setup:

```bash
# Step 1: Navigate to home directory (IMPORTANT!)
cd ~

# Step 2: Install claude-mpm with Python 3.13
uv tool install claude-mpm[monitor,data-processing] --python 3.13

# Step 3: Install companion tools (optional but recommended)
uv tool install kuzu-memory --python 3.13
uv tool install mcp-browser --python 3.13
uv tool install mcp-ticketer --python 3.13
uv tool install mcp-vector-search --python 3.13

# Step 4: Create required directories
mkdir -p ~/.claude/{responses,memory,logs}

# Step 5: Deploy agents
claude-mpm agents deploy

# Step 6: Add skill source
claude-mpm skill-source add https://github.com/bobmatnyc/claude-mpm-skills

# Step 7: Verify installation
claude-mpm doctor --verbose

# Step 8: Auto-configure (when in a project directory)
cd ~/your-project
claude-mpm auto-configure
```

## Next Steps

- **Quick Start**: [quick-start.md](quick-start.md)
- **Auto-Configuration**: [auto-configuration.md](auto-configuration.md)

## Troubleshooting

### Python Version Issues

**Problem**: Installation fails or gets old version with macOS default Python

**Solution**: Use explicit Python 3.13:
```bash
cd ~
uv tool install claude-mpm[monitor,data-processing] --python 3.13
```

### Installation from Git Repo

**Problem**: Strange behavior or conflicts after installation

**Solution**: Reinstall from home directory:
```bash
cd ~
uv tool uninstall claude-mpm
uv tool install claude-mpm[monitor,data-processing] --python 3.13
```

### Doctor Command Fails

**Problem**: `claude-mpm doctor` shows errors about missing directories or agents

**Solution**: Complete the post-installation setup:
```bash
mkdir -p ~/.claude/{responses,memory,logs}
claude-mpm agents deploy
claude-mpm skill-source add https://github.com/bobmatnyc/claude-mpm-skills
```

### Version Compatibility Issues

If you encounter Python or uv version mismatches, consider using [ASDF version manager](../guides/asdf-tool-versions.md) to ensure consistent tool versions.

### General Issues

See [../user/troubleshooting.md](../user/troubleshooting.md) if installation fails.
