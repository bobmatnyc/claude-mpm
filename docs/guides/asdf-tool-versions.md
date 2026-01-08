# ASDF Tool Version Management

Manage consistent tool versions across your development environment using ASDF version manager.

## Overview

[ASDF](https://asdf-vm.com) is a CLI tool that manages runtime versions for multiple languages and tools through a single interface. For Claude MPM users, ASDF solves common version compatibility issues by ensuring consistent versions of Python, uv, Node.js, and other development tools across different projects.

### Why Use ASDF with MPM?

- **Eliminates Version Mismatches**: Automatically use the correct Python/uv version per project
- **Reduces Installation Issues**: No more "Python 3.9 vs 3.11" conflicts
- **Simplifies Onboarding**: New team members get correct versions with one command
- **Per-Project Configuration**: Each project defines its own tool requirements
- **Zero Manual Switching**: Tools automatically use project-defined versions

## Installation

### 1. Install ASDF

**macOS (Homebrew):**
```bash
brew install asdf
echo -e "\n. $(brew --prefix asdf)/libexec/asdf.sh" >> ~/.zshrc
source ~/.zshrc
```

**Linux:**
```bash
git clone https://github.com/asdf-vm/asdf.git ~/.asdf --branch v0.14.0
echo '. "$HOME/.asdf/asdf.sh"' >> ~/.bashrc
source ~/.bashrc
```

**For other installation methods**, see: https://asdf-vm.com/guide/getting-started.html

### 2. Install Required Plugins

```bash
# Python plugin
asdf plugin add python

# uv plugin
asdf plugin add uv https://github.com/b1-luettje/asdf-uv.git

# Node.js plugin (optional, for monitoring dashboard)
asdf plugin add nodejs
```

## Usage with Claude MPM

### Basic Workflow

1. **Create `.tool-versions` file** in your project root:

```bash
# Example .tool-versions for Claude MPM projects
python 3.11.12
uv 0.9.17
```

2. **Install specified versions**:

```bash
asdf install
```

3. **Tools are automatically shimmed** - ASDF intercepts tool calls and uses project-defined versions

4. **Verify versions**:

```bash
python --version  # Uses 3.11.12 from .tool-versions
uv --version      # Uses 0.9.17 from .tool-versions
```

### Example `.tool-versions` Files

**Claude MPM Development:**
```
python 3.11.12
uv 0.9.17
nodejs 20.11.0
```

**Python-Only Project:**
```
python 3.11.12
uv 0.9.17
```

**Minimal Setup:**
```
python 3.11
```

### Directory-Specific Versions

ASDF automatically detects `.tool-versions` in parent directories:

```
~/projects/
├── project-a/
│   └── .tool-versions  # python 3.11
└── project-b/
    └── .tool-versions  # python 3.12
```

When you `cd project-a`, Python 3.11 is used. When you `cd project-b`, Python 3.12 is used.

## Benefits for MPM Users

### 1. Solves Version Compatibility Issues

**Problem:**
```bash
# System has Python 3.9, MPM requires 3.11+
pip install claude-mpm[monitor]
# Error: Python 3.11+ required
```

**Solution with ASDF:**
```bash
# Project defines correct version
echo "python 3.11.12" >> .tool-versions
asdf install python 3.11.12

# Now installation works
pip install claude-mpm[monitor]
```

### 2. Ensures Consistent Tool Versions

**Without ASDF:**
- Developer A: Python 3.11.5, uv 0.8.0
- Developer B: Python 3.12.1, uv 0.9.17
- Result: "Works on my machine" syndrome

**With ASDF:**
- All developers: Python 3.11.12, uv 0.9.17 (from `.tool-versions`)
- Result: Consistent behavior across team

### 3. Reduces Installation Troubleshooting

Common MPM installation issues resolved by ASDF:

- ✅ **Python version too old**: ASDF installs correct version automatically
- ✅ **uv version mismatch**: `.tool-versions` ensures consistency
- ✅ **Multiple Python installations conflict**: ASDF shims handle routing
- ✅ **Virtual environment issues**: Correct Python version used per project

## Integration with Project Scaffolding

### Creating New MPM Projects

When starting a new project with Claude MPM:

1. **Initialize project directory**:

```bash
mkdir my-mpm-project
cd my-mpm-project
```

2. **Create `.tool-versions`**:

```bash
cat > .tool-versions <<EOF
python 3.11.12
uv 0.9.17
EOF
```

3. **Install tools**:

```bash
asdf install
```

4. **Initialize MPM**:

```bash
claude-mpm init
```

### Template `.tool-versions` for MPM Projects

Save as `.tool-versions` in your project root:

```
# Claude MPM recommended tool versions
python 3.11.12
uv 0.9.17

# Optional: Node.js for monitoring dashboard
# nodejs 20.11.0
```

## Common Commands

```bash
# Install all tools from .tool-versions
asdf install

# Install specific tool
asdf install python 3.11.12

# List installed versions
asdf list python

# Set global default (fallback when no .tool-versions)
asdf global python 3.11.12

# Set local project version (creates/updates .tool-versions)
asdf local python 3.11.12

# Show current versions
asdf current

# Update plugin
asdf plugin update python
```

## Troubleshooting

### Python/uv Not Found After Installation

**Symptom:** `python: command not found` after `asdf install`

**Solution:** Ensure ASDF is properly sourced in your shell:

```bash
# For zsh (macOS default)
echo -e "\n. $(brew --prefix asdf)/libexec/asdf.sh" >> ~/.zshrc
source ~/.zshrc

# For bash
echo -e "\n. $HOME/.asdf/asdf.sh" >> ~/.bashrc
source ~/.bashrc
```

### Wrong Version Being Used

**Symptom:** `python --version` shows wrong version

**Solutions:**

1. **Check `.tool-versions` exists**:
```bash
cat .tool-versions
```

2. **Verify version is installed**:
```bash
asdf list python
# If version missing, run: asdf install
```

3. **Check ASDF is active**:
```bash
which python
# Should show: /Users/you/.asdf/shims/python
```

### Plugin Installation Fails

**Symptom:** `asdf plugin add python` fails

**Solution:** Update ASDF plugin repository:

```bash
asdf plugin update --all
asdf plugin add python
```

## Best Practices

1. **Commit `.tool-versions` to Git** - Ensures all team members use same versions
2. **Pin specific versions** - Use `3.11.12` not `3.11` for reproducibility
3. **Update regularly** - Keep tools updated but test before committing changes
4. **Document in README** - Mention ASDF requirement in project documentation
5. **Use with CI/CD** - Install ASDF in CI pipelines for consistency

## Resources

- **ASDF Documentation**: https://asdf-vm.com
- **Python Plugin**: https://github.com/asdf-community/asdf-python
- **uv Plugin**: https://github.com/b1-luettje/asdf-uv
- **Claude MPM Installation**: [installation.md](../getting-started/installation.md)

## Related Documentation

- [Installation Guide](../getting-started/installation.md) - Main MPM installation instructions
- [Troubleshooting](../user/troubleshooting.md) - General troubleshooting guide
- [Quick Start](../getting-started/quick-start.md) - Get started with MPM in 5 minutes

---

**Next Steps:**
- Install ASDF and required plugins
- Create `.tool-versions` in your project
- Run `asdf install` to get correct tool versions
- Proceed with [MPM installation](../getting-started/installation.md)
