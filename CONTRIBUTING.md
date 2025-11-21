# Contributing to Claude MPM

Welcome to the Claude MPM project! This guide will help you get started with contributing to our multi-agent project management framework.

## Quick Start Development Workflow

Claude MPM uses a **quality-first development approach** with three essential commands that should be part of your daily workflow:

### 🚀 Essential Commands

```bash
# 1. Auto-fix code issues during development
make lint-fix

# 2. Run all quality checks before commits
make quality

# 3. Build with complete quality validation for releases
make safe-release-build
```

### Daily Development Flow

1. **During Development**: Use `make lint-fix` frequently to maintain code quality
   - Uses **Ruff** (10-200x faster than traditional tools)
   - Auto-fixes formatting, import sorting, and simple linting issues
   - Safe to run anytime - only fixes issues, never breaks code
   - Keeps your code clean as you work

2. **Before Commits**: Always run `make quality` before committing
   - Runs comprehensive quality checks (ruff linting + formatting, mypy type checking, structure validation)
   - Catches issues early in the development cycle
   - **Required step** - don't skip this!

3. **For Releases**: Use `make safe-release-build` for any release builds
   - Complete pre-publish quality gate plus build process
   - Ensures all releases meet our quality standards
   - Mandatory for all production releases

### Modern Tooling (10-200x faster)

We use **Ruff** for unified linting and formatting, replacing multiple legacy tools:

- **What Ruff replaces**: black (formatting), isort (import sorting), flake8 (linting), pyupgrade (syntax modernization)
- **Performance**: 10-200x faster than traditional Python linting tools
- **Still use mypy**: Type checking remains with mypy (Ruff doesn't replace type checkers)
- **Configuration**: All settings in `pyproject.toml` under `[tool.ruff]`

## Quick Reference

| Command | When to Use | What It Does | Time |
|---------|-------------|--------------|------|
| `make lint-fix` | During development | Auto-fixes formatting, imports, simple issues | ~30s |
| `make quality` | Before every commit | Comprehensive quality checks and validation | ~2-3min |
| `make safe-release-build` | For releases | Complete quality gate + safe build | ~5-10min |

## Commit Guidelines

### Before Every Commit

**Always run the quality check:**
```bash
# This should pass before you commit
make quality
```

If `make quality` fails:
1. First try `make lint-fix` to auto-fix common issues
2. Address any remaining issues manually
3. Run `make quality` again to verify fixes

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/) for automatic versioning:

- `feat:` - New features (minor version bump)
- `fix:` - Bug fixes (patch version bump) 
- `feat!:` or `BREAKING CHANGE:` - Breaking changes (major version bump)
- `perf:` - Performance improvements
- `refactor:` - Code refactoring
- `docs:` - Documentation updates
- `test:` - Test additions/updates

Example:
```bash
git commit -m "feat: add new quality validation commands to development workflow"
```

## Development Environment

### Setup

Claude MPM supports both Mamba (recommended) and traditional Python environments:

```bash
# Clone and setup
git clone https://github.com/your-repo/claude-mpm.git
cd claude-mpm

# Setup with automatic environment detection
make setup

# Or use specific environment
make setup --use-venv  # Force traditional venv
```

### Environment Benefits

- **Mamba (Recommended)**: 50-80% faster dependency resolution, optimized binaries
- **Auto-detection**: `./scripts/claude-mpm` automatically uses the best available environment
- **Project-specific**: Environments are isolated per project

## Code Quality Standards

### Architecture Principles

1. **Service-Oriented Architecture**: Use our five specialized service domains
2. **Interface-Based Contracts**: All services implement explicit interfaces
3. **Dependency Injection**: Use service container for loose coupling
4. **Performance**: Implement caching and lazy loading appropriately
5. **Security**: Follow security guidelines in [docs/reference/SECURITY.md](docs/reference/SECURITY.md)

### Code Structure

- **Scripts**: ALL scripts go in `/scripts/`, NEVER in project root
- **Tests**: ALL tests go in `/tests/`, NEVER in project root  
- **Python modules**: Always under `/src/claude_mpm/`
- **Import conventions**: Use full package names: `from claude_mpm.module import ...`

### Testing Requirements

We maintain 85%+ test coverage across:

1. **Unit Tests**: Individual services and components
2. **Integration Tests**: Service interactions and interfaces
3. **Performance Tests**: Caching and optimization verification
4. **Security Tests**: Input validation and security measures
5. **E2E Tests**: Complete user workflows

#### Running Tests

Tests are configured to run in parallel by default using pytest-xdist, providing 3-4x speedup:

```bash
# Run all tests in parallel (default, fastest)
make test

# Run tests serially for debugging
make test-serial

# Run only unit tests (fast)
make test-fast

# Run with coverage report
make test-coverage

# Run specific test types
make test-unit          # Unit tests only
make test-integration   # Integration tests only
make test-e2e          # End-to-end tests only
```

**Parallelization Details:**
- Tests use all available CPU cores by default (`-n auto`)
- Expected speedup: 3-4x faster than serial execution
- Typical execution time: ~30-45 seconds (down from 2-3 minutes)
- Use `make test-serial` for debugging race conditions or fixture issues

**Writing Thread-Safe Tests:**
- Ensure test fixtures are isolated (use `tmp_path` for file operations)
- Avoid shared state between tests
- Use `@pytest.mark.serial` for tests that must run sequentially
- Mock external services to prevent port conflicts

## Documentation

### Key Documentation Locations

- **Start Here**: [docs/README.md](docs/README.md) - Complete navigation guide
- **Architecture**: [docs/developer/ARCHITECTURE.md](docs/developer/ARCHITECTURE.md) - Service architecture
- **Structure**: [docs/developer/STRUCTURE.md](docs/developer/STRUCTURE.md) - File organization
- **Services**: [docs/developer/SERVICES.md](docs/developer/SERVICES.md) - Service development
- **Quality**: [docs/developer/QA.md](docs/developer/QA.md) - Testing procedures
- **Deployment**: [docs/reference/DEPLOY.md](docs/reference/DEPLOY.md) - Release process

### Documentation Standards

1. **Service Documentation**: Document all interfaces and implementations
2. **Architecture Updates**: Keep architecture docs current with changes
3. **Migration Guides**: Document breaking changes and upgrade paths
4. **Performance Metrics**: Document performance expectations and benchmarks

## Common Development Tasks

### Adding a New Service

1. **Create Interface**: Define service contract in `src/claude_mpm/services/core/interfaces.py`
2. **Implement Service**: Create implementation in appropriate service domain
3. **Register Service**: Add to service container for dependency injection
4. **Add Tests**: Unit, integration, and interface compliance tests
5. **Update Documentation**: Document in [docs/developer/SERVICES.md](docs/developer/SERVICES.md)

### Adding CLI Commands

1. Create command module in `src/claude_mpm/cli/commands/`
2. Register in `src/claude_mpm/cli/parser.py`
3. Follow existing command patterns
4. Use dependency injection for service access
5. Add comprehensive tests and documentation

### Modifying PM Instructions

1. Edit `src/claude_mpm/agents/INSTRUCTIONS.md` for PM behavior
2. Edit `src/claude_mpm/agents/BASE_PM.md` for framework requirements  
3. Test with `./claude-mpm run` in interactive mode
4. Update tests for PM behavior changes

## Troubleshooting

### Common Issues

1. **Quality Check Failures**: Run `make lint-fix` first, then address remaining issues
2. **Import Errors**: Ensure virtual environment is activated and PYTHONPATH includes `src/`
3. **Service Resolution Errors**: Check service container registration
4. **Version Errors**: Run `pip install -e .` for proper installation

### Getting Help

- **Development Guidelines**: **Read [CLAUDE.md](CLAUDE.md) first** - Critical guide to the three environments and deployment architecture
- **Documentation**: Comprehensive guides in [docs/](docs/)
- **Architecture**: [docs/developer/ARCHITECTURE.md](docs/developer/ARCHITECTURE.md) for service architecture
- **Quality Issues**: See [docs/reference/DEPLOY.md#quality-gates](docs/reference/DEPLOY.md#quality-gates)

## Project Overview

Claude MPM is a framework that extends Claude Code with multi-agent orchestration capabilities, featuring:

- **Service-Oriented Architecture**: Five specialized service domains
- **Interface-Based Contracts**: All services implement explicit interfaces
- **Dependency Injection**: Service container with automatic resolution
- **Performance Optimizations**: Lazy loading, multi-level caching, connection pooling
- **Security Framework**: Input validation, path traversal prevention
- **Backward Compatibility**: Lazy imports maintain existing import paths

## Release Process

For maintainers handling releases:

```bash
# Patch release (bug fixes)
make release-patch

# Minor release (new features) 
make release-minor

# Major release (breaking changes)
make release-major

# Publish to all channels
make release-publish
```

All releases require passing the complete quality gate (`make pre-publish`).

---

## Questions?

- 📚 **Start with**: [docs/README.md](docs/README.md) for complete documentation navigation
- 🏗️ **Architecture**: [docs/developer/ARCHITECTURE.md](docs/developer/ARCHITECTURE.md) for system design
- 🔧 **Development**: [CLAUDE.md](CLAUDE.md) for detailed development guidelines
- 🚀 **Deployment**: [docs/reference/DEPLOY.md](docs/reference/DEPLOY.md) for release process

Thank you for contributing to Claude MPM! 🚀