# MPM-Init Command

The `mpm-init` command initializes projects for optimal use with Claude Code and Claude MPM by delegating to the Agentic Coder Optimizer agent.

## Overview

`mpm-init` establishes clear, single-path project standards ensuring there's **ONE way to do ANYTHING** in your project. This removes ambiguity for AI agents and human developers alike.

## What It Does

When you run `mpm-init`, the Agentic Coder Optimizer agent will:

1. **Analyze** your project structure and existing configurations
2. **Create/Update CLAUDE.md** with comprehensive project documentation
3. **Establish Single-Path Workflows** - ONE command for each operation
4. **Configure Development Tools** - Linting, formatting, testing
5. **Set Up Memory Systems** - Initialize `.claude-mpm/memories/` for project knowledge
6. **Document Project Structure** - Clear guidelines on file organization
7. **Create Quick Start Guide** - Step-by-step setup instructions

## Usage

### Basic Initialization

Initialize the current directory:
```bash
claude-mpm mpm-init
```

Initialize a specific project:
```bash
claude-mpm mpm-init /path/to/project
```

### With Project Type

Specify the type of project for optimized setup:
```bash
claude-mpm mpm-init --project-type web
claude-mpm mpm-init --project-type api
claude-mpm mpm-init --project-type cli
```

Available project types:
- `web` - Web applications
- `api` - REST APIs and backends
- `cli` - Command-line tools
- `library` - Reusable libraries
- `mobile` - Mobile applications
- `desktop` - Desktop applications
- `fullstack` - Full-stack applications
- `data` - Data processing pipelines
- `ml` - Machine learning projects

### With Framework

Specify a framework for tailored configuration:
```bash
claude-mpm mpm-init --project-type web --framework react
claude-mpm mpm-init --project-type api --framework fastapi
claude-mpm mpm-init --framework django
```

Common frameworks:
- **Web**: react, vue, angular, nextjs, svelte
- **API**: fastapi, django, flask, express, nestjs
- **Mobile**: react-native, flutter, ionic
- **ML**: pytorch, tensorflow, scikit-learn

### Force Reinitialization

If your project already has a CLAUDE.md file:
```bash
claude-mpm mpm-init --force
```

### Initialization Modes

**Minimal** (CLAUDE.md only):
```bash
claude-mpm mpm-init --minimal
```

**Comprehensive** (includes CI/CD, deployment):
```bash
claude-mpm mpm-init --comprehensive
```

### Other Options

**Dry run** (preview without changes):
```bash
claude-mpm mpm-init --dry-run
```

**Verbose output**:
```bash
claude-mpm mpm-init --verbose
```

**JSON output**:
```bash
claude-mpm mpm-init --json
```

**List available templates**:
```bash
claude-mpm mpm-init --list-templates
```

## What Gets Created

### CLAUDE.md

The main documentation file for AI agents containing:
- Project overview and purpose
- Architecture and key components
- Development guidelines
- ONE clear way to: build, test, deploy, lint, format
- Links to all relevant documentation
- Common tasks and workflows

Example structure:
```markdown
# Project Name

## Overview
Brief description of what this project does...

## Quick Start
1. Install: `npm install`
2. Build: `npm run build`
3. Test: `npm test`
4. Deploy: `npm run deploy`

## Architecture
- `/src` - Source code
- `/tests` - Test files
- `/docs` - Documentation

## Development
ONE way to do everything:
- Format code: `npm run format`
- Lint: `npm run lint`
- Type check: `npm run type-check`
```

### Memory System

Creates `.claude-mpm/memories/` with initial memory files:
- `project.md` - Project-specific knowledge
- `patterns.md` - Common patterns and conventions
- `decisions.md` - Architectural decisions

### Development Tools

Sets up or verifies:
- `.eslintrc` / `.flake8` - Linting configuration
- `.prettierrc` / `pyproject.toml` - Formatting standards
- `jest.config.js` / `pytest.ini` - Testing framework
- `.pre-commit-config.yaml` - Git hooks

### GitHub Integration

When applicable, creates:
- `.github/workflows/ci.yml` - CI/CD pipeline
- `.github/ISSUE_TEMPLATE/` - Issue templates
- `.github/PULL_REQUEST_TEMPLATE.md` - PR template

## Examples

### React Web App
```bash
claude-mpm mpm-init --project-type web --framework react
```

Creates optimized setup for React with:
- Component structure guidelines
- State management patterns
- Testing with Jest/React Testing Library
- Build optimization with Webpack/Vite

### FastAPI REST API
```bash
claude-mpm mpm-init --project-type api --framework fastapi
```

Creates optimized setup for FastAPI with:
- API endpoint organization
- Database model patterns
- Testing with pytest
- OpenAPI documentation

### Python Library
```bash
claude-mpm mpm-init --project-type library --language python
```

Creates optimized setup for Python library with:
- Package structure
- Testing and coverage
- Documentation with Sphinx
- PyPI publishing workflow

## Best Practices

1. **Run Early**: Initialize projects at the start for maximum benefit
2. **Be Specific**: Provide project type and framework for better optimization
3. **Review Output**: Check the generated CLAUDE.md and customize as needed
4. **Commit Changes**: Add initialization files to version control
5. **Team Alignment**: Share CLAUDE.md with team members

## Troubleshooting

### Project already initialized
Use `--force` to reinitialize or manually edit CLAUDE.md

### Agent not available
Ensure claude-mpm is properly installed and configured

### Customization needed
After initialization, manually edit files to match specific requirements

## Related Commands

- `claude-mpm run` - Run Claude with the configured project
- `claude-mpm agents list` - View available agents
- `claude-mpm memory` - Manage project memories
- `claude-mpm configure` - Configure Claude MPM settings

## Philosophy

The `mpm-init` command embodies the principle that **clarity beats flexibility**. By establishing ONE way to do each task, we:
- Reduce cognitive load
- Improve AI agent understanding
- Accelerate onboarding
- Minimize errors
- Increase productivity

Projects initialized with `mpm-init` are optimized for both human developers and AI assistants, creating a symbiotic development environment.