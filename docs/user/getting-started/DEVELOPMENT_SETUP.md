# Development Environment Setup

This guide covers setting up a development environment for claude-mpm using either Mamba (recommended) or Python venv.

## Table of Contents
- [Quick Start](#quick-start)
- [Mamba Setup (Recommended)](#mamba-setup-recommended)
- [Traditional venv Setup](#traditional-venv-setup)
- [Environment Management](#environment-management)
- [Troubleshooting](#troubleshooting)

## Quick Start

The claude-mpm development script automatically detects and uses the best available environment manager:

```bash
# Automatic detection (uses Mamba if available, falls back to venv)
./scripts/claude-mpm --help

# Force venv usage even if Mamba is available
./scripts/claude-mpm --use-venv --help

# Use Mamba explicitly
./scripts/claude-mpm-mamba --help
```

## Mamba Setup (Recommended)

### Why Mamba?

Mamba offers several advantages over traditional Python virtual environments:

- **Faster dependency resolution**: Mamba's libsolv solver is significantly faster than pip
- **Better compiled package management**: Optimized binaries for packages like pandas, numpy, tree-sitter
- **Cross-platform consistency**: Same environment across macOS, Linux, and Windows
- **Parallel downloads**: Faster environment setup and updates
- **Environment reproducibility**: Exact package versions across all developers
- **Memory efficiency**: Shared package cache reduces disk usage

### Installing Mamba

#### Option 1: Mambaforge (Recommended)
```bash
# macOS/Linux
curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh"
bash Mambaforge-$(uname)-$(uname -m).sh

# Follow the installer prompts, then restart your shell
```

#### Option 2: Install Mamba in existing Conda
```bash
conda install mamba -n base -c conda-forge
```

#### Option 3: Micromamba (Lightweight)
```bash
# macOS with Homebrew
brew install micromamba

# Linux/macOS with curl
curl micro.mamba.pm/install.sh | bash
```

### Creating the Mamba Environment

Once Mamba is installed, the development script handles environment creation automatically:

```bash
# First run creates the environment
./scripts/claude-mpm-mamba --help

# Or manually create from environment.yml
mamba env create -f environment.yml
mamba activate claude-mpm
```

### Updating the Environment

```bash
# Update environment to match environment.yml
./scripts/claude-mpm-mamba --update-env --help

# Or manually
mamba env update -n claude-mpm -f environment.yml --prune
```

## Traditional venv Setup

If you prefer or need to use Python's built-in venv:

```bash
# The script automatically creates and manages the venv
./scripts/claude-mpm --use-venv --help

# Or manually
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .[dev]
```

## Environment Management

### Environment Structure

```
claude-mpm/
├── environment.yml          # Mamba environment specification
├── pyproject.toml          # Python package dependencies
├── scripts/
│   ├── claude-mpm          # Auto-detecting launcher
│   └── claude-mpm-mamba    # Mamba-specific launcher
└── venv/                   # Traditional venv (if used)
```

### Key Environment Variables

Both environments set these variables:
- `DISABLE_TELEMETRY=1` - Disables telemetry by default
- `PYTHONPATH` - Includes the `src/` directory
- `CLAUDE_MPM_USER_PWD` - Preserves the original working directory
- `CLAUDE_MPM_DEV_ENV` - Set to "mamba" in Mamba environments

### Development Workflow

1. **Start development session**:
   ```bash
   # Auto-detect best environment
   ./scripts/claude-mpm run
   
   # With specific environment
   ./scripts/claude-mpm-mamba run        # Mamba
   ./scripts/claude-mpm --use-venv run   # venv
   ```

2. **Run tests**:
   ```bash
   ./scripts/claude-mpm-mamba pytest tests/
   ```

3. **Update dependencies**:
   ```bash
   # Mamba
   mamba env update -n claude-mpm -f environment.yml --prune
   
   # venv
   pip install -e .[dev] --upgrade
   ```

### Adding Dependencies

#### For Mamba environments:
1. Add conda packages to `environment.yml` under `dependencies:`
2. Add pip-only packages to `environment.yml` under `pip:`
3. Update the environment: `mamba env update -n claude-mpm -f environment.yml`

#### For all environments:
1. Add to `pyproject.toml` under `dependencies` or `optional-dependencies`
2. Mamba users: Also add to `environment.yml` for consistency
3. Update: `pip install -e .[dev]`

## Environment Comparison

| Feature | Mamba | venv |
|---------|-------|------|
| Setup Speed | Faster (parallel downloads) | Slower (sequential) |
| Dependency Resolution | Fast (libsolv) | Slower (pip resolver) |
| Binary Packages | Optimized | Source/wheels |
| Disk Usage | Efficient (shared cache) | Per-environment |
| Cross-platform | Excellent | Good |
| Python-only packages | Good | Excellent |
| Corporate Environments | May need proxy config | Usually works |

## Troubleshooting

### Mamba Issues

**Environment not activating:**
```bash
# Initialize conda/mamba for your shell
mamba init bash  # or zsh, fish, etc.
# Restart shell
```

**Package conflicts:**
```bash
# Clean and recreate environment
mamba env remove -n claude-mpm
mamba env create -f environment.yml
```

**Behind corporate proxy:**
```bash
# Configure conda/mamba proxy
mamba config --set proxy_servers.http http://proxy.company.com:8080
mamba config --set proxy_servers.https https://proxy.company.com:8080
```

### venv Issues

**Python version mismatch:**
```bash
# Specify Python version
python3.11 -m venv venv
```

**Permission errors:**
```bash
# Fix permissions
chmod +x scripts/claude-mpm
```

### General Issues

**Import errors:**
```bash
# Ensure editable install
pip install -e .[dev]
```

**Script not found:**
```bash
# Add to PATH
export PATH="$PATH:$(pwd)/scripts"
```

## Best Practices

1. **Use Mamba for development** when possible for better performance and consistency
2. **Keep environment.yml updated** when adding dependencies
3. **Document environment-specific code** if any
4. **Test with both environments** before major releases
5. **Use --update-env flag** periodically to sync dependencies

## Migration Guide

### From venv to Mamba

1. Install Mamba (see above)
2. Run: `./scripts/claude-mpm-mamba --help`
3. Environment will be created automatically
4. Remove old venv if desired: `rm -rf venv/`

### From Mamba to venv

1. Run: `./scripts/claude-mpm --use-venv --help`
2. venv will be created automatically
3. Remove Mamba env if desired: `mamba env remove -n claude-mpm`

## CI/CD Considerations

For CI/CD pipelines, you can use either environment:

```yaml
# GitHub Actions with Mamba
- uses: conda-incubator/setup-miniconda@v2
  with:
    miniforge-version: latest
    environment-file: environment.yml
    activate-environment: claude-mpm

# GitHub Actions with venv
- name: Setup Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.11'
- name: Install dependencies
  run: |
    pip install -e .[dev]
```

## Support

For environment-related issues:
1. Check this documentation
2. Review [CLAUDE.md](../CLAUDE.md) for project guidelines
3. Check existing issues on GitHub
4. Create a new issue with environment details