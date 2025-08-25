# Mamba Environment Support for Claude MPM

This directory contains scripts that support both Mamba/Conda and traditional Python venv environments.

## Quick Start

```bash
# Automatic detection (recommended)
./claude-mpm [command]

# Force Mamba environment
./claude-mpm-mamba [command]

# Force venv environment
./claude-mpm --use-venv [command]
```

## Scripts Overview

### `claude-mpm`
The main launcher script with automatic environment detection:
- Checks for Mamba/Conda availability
- Uses Mamba if available and `environment.yml` exists
- Falls back to venv if Mamba is not available
- Supports `--use-venv` flag to force venv usage

### `claude-mpm-mamba`
Dedicated Mamba environment launcher:
- Creates conda environment from `environment.yml`
- Manages environment activation
- Supports `--update-env` flag for dependency updates
- Provides better performance for compiled packages

### `test_mamba_env.sh`
Test script to verify Mamba setup:
- Checks Mamba/Conda installation
- Verifies environment creation
- Tests package installation
- Validates script functionality

## Environment Detection Logic

```
1. Check for --use-venv flag → Use venv if present
2. Check for Mamba/Conda command → Use Mamba if available
3. Check for environment.yml → Use Mamba if exists
4. Default → Fall back to venv
```

## Benefits of Mamba

- **50-80% faster** dependency resolution
- **Optimized binaries** for scientific packages
- **Parallel downloads** for faster setup
- **Shared package cache** reduces disk usage
- **Better reproducibility** across platforms

## Installation

### Install Mamba (if not already installed)

```bash
# Option 1: Mambaforge (recommended)
curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh"
bash Mambaforge-$(uname)-$(uname -m).sh

# Option 2: Add to existing Conda
conda install mamba -n base -c conda-forge

# Option 3: Micromamba (lightweight)
brew install micromamba  # macOS
# or
curl micro.mamba.pm/install.sh | bash  # Linux/macOS
```

### Create Environment

The environment is created automatically on first run:

```bash
./claude-mpm-mamba --help
```

Or manually:

```bash
mamba env create -f ../environment.yml
mamba activate claude-mpm
```

## Updating Dependencies

### With Mamba
```bash
# Update environment from environment.yml
./claude-mpm-mamba --update-env [command]

# Or manually
mamba env update -n claude-mpm -f ../environment.yml --prune
```

### With venv
```bash
# Update pip packages
./claude-mpm --use-venv --help  # Auto-updates if needed

# Or manually
source venv/bin/activate
pip install -e ..[dev] --upgrade
```

## Troubleshooting

### "Mamba/Conda not found"
- Install Mamba using instructions above
- Ensure Mamba is in your PATH
- Restart your terminal after installation

### "Environment 'claude-mpm' not found"
- Run `./claude-mpm-mamba --help` to auto-create
- Or manually: `mamba env create -f ../environment.yml`

### "Package conflicts"
- Remove and recreate: `mamba env remove -n claude-mpm`
- Then: `mamba env create -f ../environment.yml`

### Performance Issues
- Update environment: `./claude-mpm-mamba --update-env`
- Clear conda cache: `mamba clean --all`
- Check disk space for package cache

## Environment Variables

Both environments set:
- `DISABLE_TELEMETRY=1` - Disables telemetry
- `PYTHONPATH` - Includes src/ directory
- `CLAUDE_MPM_USER_PWD` - Original working directory
- `CLAUDE_MPM_DEV_ENV=mamba` - In Mamba environments only

## For CI/CD

GitHub Actions example:

```yaml
# With Mamba
- uses: conda-incubator/setup-miniconda@v2
  with:
    miniforge-version: latest
    environment-file: environment.yml
    activate-environment: claude-mpm

# With venv
- uses: actions/setup-python@v4
  with:
    python-version: '3.11'
- run: pip install -e .[dev]
```

## Support

See [docs/DEVELOPMENT_SETUP.md](../docs/DEVELOPMENT_SETUP.md) for complete documentation.