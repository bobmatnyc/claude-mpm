# Development Improvements

This document outlines the recent improvements made to the claude-mpm development workflow, including automated code formatting and formal deprecation policies.

## Overview

The claude-mpm project has implemented several key improvements to enhance code quality, maintainability, and developer experience:

1. **Automated Code Formatting** - Pre-commit hooks with Black, isort, flake8, and mypy
2. **Formal Deprecation Policy** - Structured approach to removing obsolete code
3. **Enhanced Development Workflow** - Improved tooling and documentation

## 1. Automated Code Formatting

### What's New

- **Pre-commit hooks** automatically format code before commits
- **Consistent code style** enforced across the entire project
- **Multiple tools integrated**: Black, isort, flake8, mypy, bandit
- **IDE integration** documented for VS Code and PyCharm

### Setup

#### Quick Setup
```bash
# Complete development setup with formatting
make dev-complete
```

#### Manual Setup
```bash
# Set up pre-commit hooks only
make setup-pre-commit

# Or run the setup script directly
./scripts/setup_pre_commit.sh
```

### Tools Configured

| Tool | Purpose | Configuration |
|------|---------|---------------|
| **Black** | Code formatting | Line length: 88, Python 3.8+ |
| **isort** | Import sorting | Black-compatible profile |
| **flake8** | Linting | Max line length: 88, ignore E203/W503 |
| **mypy** | Type checking | Module-specific strictness levels |
| **bandit** | Security scanning | JSON output format |

### Usage

#### Automatic (Recommended)
```bash
git add .
git commit -m "Your message"
# Hooks run automatically
```

#### Manual Commands
```bash
make format      # Format code with Black and isort
make lint        # Run flake8 linting
make type-check  # Run mypy type checking
make pre-commit-run  # Run all hooks manually
```

### Benefits

- **Consistent code style** across all contributors
- **Reduced review time** - no more style discussions
- **Better code quality** - automatic linting and type checking
- **Security improvements** - automatic vulnerability scanning
- **IDE integration** - works with popular editors

## 2. Formal Deprecation Policy

### What's New

- **Structured deprecation process** with clear timelines
- **Automated obsolete file detection** and removal
- **Deprecation warnings** for experimental code
- **Migration documentation** and guidance

### Deprecation Lifecycle

1. **Phase 1 (3 months)**: Deprecation warnings, full functionality
2. **Phase 2 (6 months)**: Reduced support, migration emphasis
3. **Phase 3 (12 months)**: Removal with major version bump

### Categories

#### Immediate Removal
- One-time cleanup scripts
- Empty or minimal files
- Backup files (`*.bak`, `*_original.py`)

#### Experimental Code (3 months)
- `src/claude_mpm/experimental/cli_enhancements.py`
- Prototype features and proof-of-concepts

#### Legacy Modules (12 months)
- `src/claude_mpm/cli_module/` - Old CLI architecture
- Legacy service implementations

### Usage

#### Check for Obsolete Files
```bash
make deprecation-check
# or
python scripts/apply_deprecation_policy.py --dry-run
```

#### Apply Deprecation Policy
```bash
make deprecation-apply
# or
python scripts/apply_deprecation_policy.py
```

#### Phase-Specific Application
```bash
# Apply only immediate removals
python scripts/apply_deprecation_policy.py --phase immediate

# Add warnings to experimental code
python scripts/apply_deprecation_policy.py --phase experimental
```

### Benefits

- **Cleaner codebase** - systematic removal of obsolete code
- **Clear migration paths** - users know what to expect
- **Reduced maintenance burden** - less code to maintain
- **Better organization** - focus on current architecture

## 3. Enhanced Development Workflow

### New Make Targets

#### Code Quality
```bash
make format           # Format code with Black and isort
make lint            # Run linting checks
make type-check      # Run type checking
make pre-commit-run  # Run all pre-commit hooks
```

#### Development Setup
```bash
make dev-complete    # Complete development setup
make setup-pre-commit # Set up pre-commit hooks only
```

#### Deprecation Management
```bash
make deprecation-check  # Check for obsolete files
make deprecation-apply  # Apply deprecation policy
make cleanup           # Alias for deprecation-check
```

### Documentation Updates

#### New Documentation
- [Code Formatting Guidelines](CODE_FORMATTING.md)
- [Deprecation Policy](DEPRECATION_POLICY.md)
- [Development Improvements](DEVELOPMENT_IMPROVEMENTS.md) (this document)

#### Updated Documentation
- Enhanced Makefile with new targets
- Updated development setup instructions
- Improved contributor guidelines

### Configuration Files

#### New Files
- `.pre-commit-config.yaml` - Pre-commit hook configuration
- `scripts/setup_pre_commit.sh` - Pre-commit setup script
- `scripts/apply_deprecation_policy.py` - Deprecation policy implementation

#### Updated Files
- `pyproject.toml` - Added pre-commit to dev dependencies
- `Makefile` - Added code quality and deprecation targets
- `.gitignore` - Enhanced patterns for obsolete files

## Migration Guide

### For Existing Developers

1. **Update your development environment**:
   ```bash
   make dev-complete
   ```

2. **Verify pre-commit hooks are working**:
   ```bash
   make pre-commit-run
   ```

3. **Update your IDE configuration** (see [Code Formatting](CODE_FORMATTING.md))

### For New Developers

1. **Clone the repository**
2. **Run the complete setup**:
   ```bash
   make dev-complete
   ```
3. **Start developing** - formatting happens automatically!

### For CI/CD

Update your CI/CD pipelines to include:
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run code quality checks
make pre-commit-run

# Run tests
pytest
```

## Best Practices

### Code Quality

1. **Let the tools do the work** - don't manually format code
2. **Fix linting issues promptly** - don't ignore warnings
3. **Add type annotations** - help mypy catch issues
4. **Review pre-commit changes** - understand what was changed

### Deprecation Management

1. **Monitor deprecation warnings** - plan migrations early
2. **Use migration periods** - don't wait until the last minute
3. **Report migration issues** - help improve the process
4. **Read release notes** - stay informed about changes

### Development Workflow

1. **Use make targets** - they're optimized and consistent
2. **Keep dependencies updated** - run setup periodically
3. **Follow the documentation** - it's kept up to date
4. **Contribute improvements** - help make it better

## Troubleshooting

### Pre-commit Issues

**Problem**: Pre-commit hooks fail
**Solution**: 
1. Review the changes made by hooks
2. Fix any remaining linting issues
3. Commit again

**Problem**: Hooks are too slow
**Solution**: 
1. Use `pre-commit run --files <specific-files>` for partial runs
2. Consider excluding large files or directories

### Deprecation Issues

**Problem**: Code uses deprecated features
**Solution**:
1. Check the deprecation warnings
2. Follow migration guidance in documentation
3. Update to new patterns

**Problem**: Migration path unclear
**Solution**:
1. Check [Deprecation Policy](DEPRECATION_POLICY.md)
2. Look for examples in the codebase
3. Open an issue for clarification

## Future Improvements

### Planned Enhancements

1. **Additional linting tools** - pylint, vulture for dead code detection
2. **Performance monitoring** - track code quality metrics
3. **Automated dependency updates** - dependabot or similar
4. **Enhanced CI/CD integration** - quality gates and reporting

### Community Contributions

We welcome contributions to improve the development workflow:

1. **Tool suggestions** - recommend better tools or configurations
2. **Documentation improvements** - help make guides clearer
3. **Automation enhancements** - improve scripts and workflows
4. **Best practice sharing** - contribute patterns and examples

## Support

### Getting Help

1. **Documentation** - Check the developer docs first
2. **GitHub Issues** - Report problems or ask questions
3. **Code Examples** - Look at existing code for patterns
4. **Community** - Engage with other contributors

### Reporting Issues

When reporting development workflow issues:

1. **Include your environment** - OS, Python version, tools
2. **Provide reproduction steps** - how to trigger the issue
3. **Share error messages** - full output helps diagnosis
4. **Suggest solutions** - if you have ideas

---

**Last Updated**: 2025-08-17
**Version**: 1.0
**Related Documents**: 
- [Code Formatting Guidelines](CODE_FORMATTING.md)
- [Deprecation Policy](DEPRECATION_POLICY.md)
- [Architecture Documentation](../ARCHITECTURE.md)
