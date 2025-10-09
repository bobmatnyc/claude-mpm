# Claude MPM Scripts

This directory contains essential utility scripts for Claude MPM development, deployment, and maintenance.

## 📦 Installation & Deployment Scripts

### Core Installation
- **`install.sh`** - Basic installation script for production use
- **`install_dev.sh`** - Development installation with enhanced features and debugging
- **`deploy_local.sh`** - Enhanced local deployment script with comprehensive setup
- **`uninstall.sh`** - Clean uninstallation script
- **`pipx-install-local`** - Install claude-mpm from local source to any directory using pipx

### Local Development
- **`claude-mpm`** - Main development script (run from project root only)
- **`claude-mpm-dev`** - Development variant with additional debugging
- **`claude-mpm-mamba`** - Mamba/Conda environment variant

## 🚀 Build & Release Scripts

### Version Management
- **`manage_version.py`** - Semantic version management utilities
- **`increment_build.py`** - Automatic build number tracking and increment
- **`release.py`** - Comprehensive release management script

## 🧪 Development & Testing Scripts

### Code Quality
- **`setup_pre_commit.sh`** - Set up pre-commit hooks for code quality
- **`pre-commit-build.sh`** - Pre-commit build validation
- **`apply_deprecation_policy.py`** - Apply deprecation policies to codebase

### Testing
- **`run_all_tests.sh`** - Run complete test suite
- **`run_e2e_tests.sh`** - End-to-end testing suite

### Monitoring
- **`monitor_memory.sh`** - Memory usage monitoring and alerts

## 🖥️ CLI Wrappers

### Main Commands
- **`claude-mpm`** - Main CLI wrapper script (shell)
- **`claude-mpm-socketio`** - SocketIO daemon wrapper
- **`ticket`** - Ticket management CLI wrapper (shell)
- **`ticket.py`** - Python ticket management script

## 🛠️ Build Tools

### Dashboard & Assets
- **`build-dashboard.sh`** - Build dashboard assets using Vite

### Package Management
- **`package-lock.json`** - npm package lock file
- **`postinstall.js`** - npm post-install script

## 📋 Usage Guidelines

### For Contributors
```bash
# Development installation (recommended for contributors)
./scripts/install_dev.sh

# Set up development environment
./scripts/setup_pre_commit.sh

# Run all tests
./scripts/run_all_tests.sh
```

### For Releases
```bash
# Check current version
python scripts/manage_version.py check

# Increment build number
python scripts/increment_build.py --all-changes

# Create release
python scripts/release.py --patch
```

### For Maintenance
```bash
# Check for obsolete code
python scripts/apply_deprecation_policy.py --dry-run

# Build dashboard
./scripts/build-dashboard.sh

# Monitor memory usage
./scripts/monitor_memory.sh
```

## 📖 Getting Help

Most scripts support `--help` flag:
```bash
python scripts/release.py --help
python scripts/manage_version.py --help
./scripts/deploy_local.sh --help
```

For detailed documentation, see:
- [DEPLOY.md](../docs/DEPLOY.md) - Deployment guide
- [VERSIONING.md](../docs/VERSIONING.md) - Version management
- [QA.md](../docs/QA.md) - Testing procedures