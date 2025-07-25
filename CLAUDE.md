# Claude MPM Project Guidelines

This document provides guidelines for working with the claude-mpm project.

## Project Overview

Claude MPM (Multi-Agent Project Manager) is a framework for Claude that enables multi-agent workflows and extensible capabilities.

## Key Resources

- 📁 **Project Structure**: See [docs/STRUCTURE.md](docs/STRUCTURE.md) for file organization
- 🧪 **Quality Assurance**: See [docs/QA.md](docs/QA.md) for testing guidelines
- 🚀 **Deployment**: See [docs/DEPLOY.md](docs/DEPLOY.md) for versioning and deployment
- 📊 **Logging**: See [docs/LOGGING.md](docs/LOGGING.md) for comprehensive logging guide
- 🔢 **Versioning**: See [docs/VERSIONING.md](docs/VERSIONING.md) for version management

## Development Guidelines

### Before Making Changes

1. **Understand the structure**: Always refer to `docs/STRUCTURE.md` when creating new files
   - **Scripts**: ALL scripts go in `/scripts/`, NEVER in project root
   - **Tests**: ALL tests go in `/tests/`, NEVER in project root
   - **Python modules**: Always under `/src/claude_mpm/`
2. **Run tests**: Execute E2E tests after significant changes using `./scripts/run_e2e_tests.sh`
3. **Check imports**: Ensure all imports use the full package name: `from claude_mpm.module import ...`

### Testing Requirements

**After significant changes, always run:**
```bash
# Quick E2E tests
./scripts/run_e2e_tests.sh

# Full test suite
./scripts/run_all_tests.sh
```

See [docs/QA.md](docs/QA.md) for detailed testing procedures.

### Key Components

1. **Agent System** (`src/claude_mpm/agents/`)
   - Templates for different agent roles
   - Dynamic discovery via `AgentRegistry`

2. **Hook System** (`src/claude_mpm/hooks/`)
   - Extensibility through pre/post hooks
   - Managed by hook service

3. **Services** (`src/claude_mpm/services/`)
   - Business logic layer
   - Hook service, agent management, etc.

## Quick Start

```bash
# Interactive mode
./claude-mpm

# Non-interactive mode
./claude-mpm run -i "Your prompt here" --non-interactive
```

## Common Issues

1. **Import Errors**: Ensure virtual environment is activated and PYTHONPATH includes `src/`
2. **Hook Service Errors**: Check port availability (8080-8099)
3. **Version Errors**: Run `pip install -e .` to ensure proper installation

## Contributing

1. Follow the structure in `docs/STRUCTURE.md`
2. Add tests for new features
3. Run QA checks per `docs/QA.md`
4. Update documentation as needed
5. Use [Conventional Commits](https://www.conventionalcommits.org/) for automatic versioning:
   - `feat:` for new features (minor version bump)
   - `fix:` for bug fixes (patch version bump)
   - `feat!:` or `BREAKING CHANGE:` for breaking changes (major version bump)

## Deployment

See [docs/DEPLOY.md](docs/DEPLOY.md) for the complete deployment process, including:
- Version management with `./scripts/manage_version.py`
- Building and publishing to PyPI
- Creating GitHub releases
- Post-deployment verification