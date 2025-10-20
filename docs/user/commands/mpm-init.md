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

### Quick Update Mode

The `--quick-update` flag enables a lightweight documentation update based on recent git activity:

**Basic quick update** (analyzes last 30 days):
```bash
claude-mpm mpm-init --quick-update
```

**Customize analysis period**:
```bash
claude-mpm mpm-init --quick-update --days 7    # Last 7 days
claude-mpm mpm-init --quick-update --days 14   # Last 14 days
claude-mpm mpm-init --quick-update --days 60   # Last 60 days
claude-mpm mpm-init --quick-update --days 90   # Last 90 days
```

**Non-interactive mode** (view report only, no changes):
```bash
claude-mpm mpm-init --quick-update --non-interactive
```

**Export activity report**:
```bash
# Export to default location (docs/reports/activity-report-{timestamp}.md)
claude-mpm mpm-init --quick-update --export

# Export to specific file
claude-mpm mpm-init --quick-update --export my-report.md

# Combine with other options
claude-mpm mpm-init --quick-update --days 14 --export --non-interactive
```

Quick update mode:
- Analyzes recent git commits and file changes
- Shows activity metrics (commits, authors, changed files)
- Displays hot files and active branches
- Provides documentation freshness recommendations
- Optionally appends activity summary to CLAUDE.md
- Can export report to markdown file

### Session Management (Pause/Resume)

**NEW in v4.8.5**: Save and restore session state across Claude sessions for seamless context continuity.

#### Pause Session

Capture and save your current session state:

```bash
# Basic pause
claude-mpm mpm-init pause

# Pause with summary
claude-mpm mpm-init pause -s "Implemented user authentication"

# Pause with accomplishments and next steps
claude-mpm mpm-init pause \
  -s "Working on API integration" \
  -a "Added OAuth2 client" \
  -a "Implemented token refresh" \
  -a "Created integration tests" \
  -n "Add rate limiting" \
  -n "Document API endpoints"

# Pause without creating git commit
claude-mpm mpm-init pause --no-commit -s "WIP: refactoring auth module"
```

**Pause Options:**
- `-s, --summary TEXT`: Summary of what you were working on
- `-a, --accomplishment TEXT`: Things accomplished (can be used multiple times)
- `-n, --next-step TEXT`: Next steps to continue (can be used multiple times)
- `--no-commit`: Skip creating git commit with session information

**What Gets Saved:**
- Conversation context and summary
- Current git repository state (branch, commit, status)
- Active and completed todo items
- Working directory changes
- Session timestamp and metadata
- Project path and version information

#### Resume Session

Load and restore a paused session:

```bash
# Resume most recent session
claude-mpm mpm-init resume

# List all available paused sessions
claude-mpm mpm-init resume --list

# Resume specific session
claude-mpm mpm-init resume --session-id session-20251020-143022
```

**Resume Options:**
- `--session-id TEXT`: Resume specific session by ID
- `--list`: List all available paused sessions with timestamps

**What Gets Restored:**
- Full conversation context and progress
- Git state at time of pause
- Todo items (active and completed)
- Next steps and accomplishments
- **Change detection**: Shows what changed since pause (commits, files, conflicts)

**Change Detection:**

When resuming, the system automatically detects:
- New commits since pause
- Modified files
- Branch changes
- Potential conflicts
- Uncommitted changes

This ensures you're immediately aware of any changes that occurred while the session was paused.

#### Session Storage

Sessions are stored in `.claude-mpm/sessions/pause/`:
- **Format**: JSON with checksums for data integrity
- **Security**: Files created with `0600` permissions (owner-only access)
- **Naming**: `session-YYYYMMDD-HHMMSS.json`
- **Git Integration**: Optional commit created with pause info (unless `--no-commit`)

#### Use Cases

**Context Continuity:**
```bash
# End of day
claude-mpm mpm-init pause -s "Completed user module" \
  -a "Implemented CRUD operations" \
  -n "Add input validation"

# Next morning
claude-mpm mpm-init resume
# Returns: Full context plus any changes made by team members
```

**Team Handoffs:**
```bash
# Developer A finishes work
claude-mpm mpm-init pause -s "Authentication module ready for review" \
  -a "All tests passing" \
  -n "Needs code review" \
  -n "Consider performance optimization"

# Developer B picks up
claude-mpm mpm-init resume --list  # See available sessions
claude-mpm mpm-init resume --session-id session-20251020-170000
```

**Long-Running Projects:**
```bash
# Pause at natural break points
claude-mpm mpm-init pause -s "Milestone 2 complete" \
  -a "Payment integration done" \
  -a "Email notifications working" \
  -n "Start Milestone 3: Analytics dashboard"

# Resume days or weeks later
claude-mpm mpm-init resume
# Returns: Full context of where you left off
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

## Activity Reports

When using `--quick-update --export`, a markdown report is generated with:

### Report Contents
- **Summary metrics**: Commits, contributors, files changed, current branch
- **Recent commits**: Last 10 commits with hashes and messages
- **Most changed files**: Top 10 files by change frequency
- **Active branches**: List of active development branches
- **CLAUDE.md status**: Size, priority markers, last modified
- **Recommendations**: Actionable suggestions based on analysis

### Report Location
- **Default**: `docs/reports/activity-report-{timestamp}.md`
- **Custom**: Specify any path with `--export PATH`
- **Git-ignored**: Reports directory is automatically ignored

### Use Cases
1. **Team updates**: Share activity summaries with team members
2. **Progress tracking**: Document development velocity over time
3. **Documentation audits**: Identify when CLAUDE.md needs updates
4. **Project reviews**: Quick overview of recent project activity
5. **CI/CD integration**: Automated documentation freshness checks

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