# CLAUDE.md - Development Guide for Claude-MPM Contributors

> **Critical Reading for Contributors**: This document explains the three distinct environments in the Claude-MPM ecosystem and how they interact. Understanding this distinction is essential to avoid architectural confusion.

---

## Table of Contents

1. [Understanding the Three Environments](#understanding-the-three-environments)
2. [Critical Architecture Principles](#critical-architecture-principles)
3. [Common Mistakes to Avoid](#common-mistakes-to-avoid)
4. [Local Development Workflow](#local-development-workflow)
5. [Architecture Diagrams](#architecture-diagrams)
6. [File Locations Reference](#file-locations-reference)
7. [Makefile Targets for Development](#makefile-targets-for-development)
8. [Key Source Files](#key-source-files)

---

## Understanding the Three Environments

Claude-MPM operates across three distinct environments. **Never confuse these**:

| Aspect | Development Environment | Installed Product | End User Projects |
|--------|------------------------|-------------------|-------------------|
| **Purpose** | Develop claude-mpm itself | Production package installed via pip/pipx | Projects that USE claude-mpm |
| **Location** | `/Users/masa/Projects/claude-mpm/` | `site-packages/claude_mpm/` | Any directory (e.g., `~/myproject/`) |
| **Command Source** | `src/claude_mpm/commands/*.md` | `site-packages/claude_mpm/commands/*.md` | N/A (uses deployed commands) |
| **Command Deployment** | Copied to `~/.claude/commands/` | Copied to `~/.claude/commands/` | Already deployed in `~/.claude/commands/` |
| **Agent Source** | `src/claude_mpm/agents/*.{md,json,yaml}` | `site-packages/claude_mpm/agents/*.{md,json,yaml}` | N/A (uses deployed agents) |
| **Agent Deployment** | Copied to `.claude/agents/` | Copied to `.claude/agents/` | Already deployed in `.claude/agents/` |
| **Configuration** | `.claude-mpm/` (dev testing) | N/A | `.claude-mpm/` (project-specific) |
| **Git Tracking** | Everything tracked | N/A (installed via pip) | `.claude-mpm/` tracked, `.claude/agents/` ignored |

### Key Distinctions

1. **Development Environment (This Repo)**
   - Where you develop and test claude-mpm itself
   - Source files in `src/claude_mpm/`
   - Use `pip install -e .` for editable installation
   - Commands deploy from source to `~/.claude/commands/`
   - Agents deploy from source to `.claude/agents/`

2. **Installed Product (Production)**
   - What users install via `pip install claude-mpm`
   - Files packaged in `site-packages/claude_mpm/`
   - Commands deploy from site-packages to `~/.claude/commands/`
   - Agents deploy from site-packages to `.claude/agents/`

3. **End User Projects**
   - Any project using claude-mpm
   - Has `.claude-mpm/` configuration directory
   - Has `.claude/agents/` with deployed agent templates
   - Uses commands from `~/.claude/commands/` (user-level)

---

## Critical Architecture Principles

### 1. Commands are USER-LEVEL

```
Commands deploy to: ~/.claude/commands/
Scope: Shared across ALL projects
Reason: Claude Code discovers commands from ~/.claude/commands/
```

**Key Points:**
- Commands are NOT project-specific
- One user has one set of commands
- Commands apply to all projects a user works on
- Updates deploy globally for the user

### 2. Agents are PROJECT-LEVEL

```
Agents deploy to: .claude/agents/
Scope: Per-project (each project has its own agents)
Reason: Different projects may need different agent configurations
```

**Key Points:**
- Agents ARE project-specific
- Each project gets its own `.claude/agents/` directory
- Agent customization happens per-project
- Updates deploy per-project

### 3. Always COPY, Never Symlink

```
❌ WRONG: ln -s src/claude_mpm/commands ~/.claude/commands
✅ RIGHT: Copy files from source to destination
```

**Why This Matters:**
- Deployment means COPYING files, not symlinking
- Development environment must simulate production behavior
- Production uses installed files from site-packages
- Symlinks create false assumptions about file locations

### 4. Simulate Production in Development

```
Development should behave like:
  pip install claude-mpm  (not pip install -e .)
```

**How to Achieve This:**
1. Install in editable mode: `pip install -e .`
2. Use deployment services to COPY files to deployment locations
3. Never directly access source files from deployed locations
4. Test with proper deployment, not source access

---

## Common Mistakes to Avoid

### ❌ CRITICAL MISTAKES

1. **DON'T symlink `.claude/commands/` to source files**
   ```bash
   # ❌ WRONG - Creates architectural confusion
   ln -s ~/Projects/claude-mpm/src/claude_mpm/commands ~/.claude/commands

   # ✅ RIGHT - Use deployment service
   python3 -c "from claude_mpm.services.command_deployment_service import deploy_commands_on_startup; deploy_commands_on_startup(force=True)"
   ```

2. **DON'T symlink `.claude/agents/` to source files**
   ```bash
   # ❌ WRONG - Breaks project-level isolation
   ln -s ~/Projects/claude-mpm/src/claude_mpm/agents .claude/agents

   # ✅ RIGHT - Use deployment service
   claude-mpm agents deploy
   ```

3. **DON'T confuse project's `.claude/` with `~/.claude/`**
   ```
   ~/.claude/commands/        # User-level commands (global)
   ~/myproject/.claude/agents/ # Project-level agents (local)
   ```

   These are DIFFERENT directories with DIFFERENT purposes!

4. **DON'T skip deployment in development**
   ```bash
   # ❌ WRONG - Directly access source
   cat src/claude_mpm/commands/mpm-config.md

   # ✅ RIGHT - Test deployed version
   cat ~/.claude/commands/mpm-config.md
   ```

### ✅ CORRECT PRACTICES

1. **ALWAYS use deployment services**
   - `deploy_commands_on_startup()` for commands
   - `AgentDeploymentService` for agents

2. **ALWAYS test with proper deployment**
   - Install in editable mode
   - Deploy files properly
   - Test from deployment locations

3. **ALWAYS maintain clear separation**
   - Source: `src/claude_mpm/`
   - Installed: `site-packages/claude_mpm/`
   - Deployed: `~/.claude/commands/` and `.claude/agents/`

4. **ALWAYS copy, never symlink**
   - Deployment = copying files
   - Not symlinking or aliasing

---

## Local Development Workflow

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm

# 2. Complete development setup
make dev-complete
# This runs:
#   - pip install -e . (editable install)
#   - setup pre-commit hooks
#   - configure code formatting

# 3. Verify installation
claude-mpm --version
```

### Testing Command Changes

When you modify commands in `src/claude_mpm/commands/*.md`:

```bash
# 1. Make your changes
vim src/claude_mpm/commands/mpm-config.md

# 2. Force redeploy to ~/.claude/commands/
python3 -c "from claude_mpm.services.command_deployment_service import deploy_commands_on_startup; deploy_commands_on_startup(force=True)"

# 3. Verify deployment
ls -la ~/.claude/commands/mpm-config.md
cat ~/.claude/commands/mpm-config.md

# 4. Test in Claude Code
claude-code
# Then use: /mpm-config
```

**Alternative: Use CLI**
```bash
# If deployment helper exists
make deploy-commands  # (if target exists)
```

### Testing Agent Changes

When you modify agents in `src/claude_mpm/agents/*.{md,json,yaml}`:

```bash
# 1. Make your changes
vim src/claude_mpm/agents/engineer.md

# 2. Deploy to current project
cd ~/test-project  # Navigate to test project
claude-mpm agents deploy

# 3. Verify deployment
ls -la .claude/agents/engineer.md
cat .claude/agents/engineer.md

# 4. Test in Claude Code
claude-mpm run
# Agents are now available
```

### Running in Development Mode

```bash
# Development mode uses editable install
# Changes to source are immediately available

# 1. Run claude-mpm (uses editable install)
./scripts/claude-mpm run

# 2. Or use installed command
claude-mpm run

# 3. With monitoring
claude-mpm run --monitor

# 4. Interactive mode
claude-mpm  # No arguments = interactive
```

### Code Quality Workflow

```bash
# During development - auto-fix issues
make lint-fix

# Before commits - comprehensive checks
make quality

# For releases - complete validation
make safe-release-build
```

---

## Architecture Diagrams

### Command Deployment Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    COMMAND DEPLOYMENT FLOW                   │
└─────────────────────────────────────────────────────────────┘

SOURCE (Development)
src/claude_mpm/commands/*.md
  │
  │ (pip install / pip install -e .)
  ↓
INSTALLED (Package)
site-packages/claude_mpm/commands/*.md
  │
  │ (deploy_commands_on_startup)
  │  - CommandDeploymentService
  │  - Copies files (NOT symlinks)
  ↓
DEPLOYED (User-Level)
~/.claude/commands/mpm-*.md
  │
  │ (Claude Code discovers)
  ↓
AVAILABLE IN CLAUDE CODE
/mpm-config, /mpm-agents, /mpm-doctor, etc.

KEY:
  User-level scope: Commands shared across ALL projects
  Deployment method: COPY files from source to destination
  Never symlink: Production uses installed files, not source
```

### Agent Deployment Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    AGENT DEPLOYMENT FLOW                     │
└─────────────────────────────────────────────────────────────┘

SOURCE (Development)
src/claude_mpm/agents/*.{md,json,yaml}
  │
  │ (pip install / pip install -e .)
  ↓
INSTALLED (Package)
site-packages/claude_mpm/agents/*.{md,json,yaml}
  │
  │ (AgentDeploymentService)
  │  - Multi-source deployment
  │  - Per-project deployment
  │  - Copies files (NOT symlinks)
  ↓
DEPLOYED (Project-Level)
.claude/agents/*.md
  │
  │ (Claude Code discovers)
  ↓
AVAILABLE IN PROJECT
Engineer, Research, Documentation, QA, etc.

KEY:
  Project-level scope: Each project has its own agents
  Deployment method: COPY files from source to destination
  Gitignored: .claude/agents/ not tracked in user projects
  Per-project: Different projects can have different agent configs
```

### Three Environments Interaction

```
┌─────────────────────────────────────────────────────────────┐
│              THREE ENVIRONMENTS ARCHITECTURE                 │
└─────────────────────────────────────────────────────────────┘

DEVELOPMENT ENVIRONMENT
~/Projects/claude-mpm/
├── src/claude_mpm/
│   ├── commands/*.md          ← SOURCE for commands
│   ├── agents/*.{md,json}     ← SOURCE for agents
│   └── services/
│       ├── command_deployment_service.py
│       └── agents/deployment/
├── .claude-mpm/               ← Dev testing config
└── .git/                      ← Git repository

        │
        │ pip install -e .
        │ (editable install)
        ↓

INSTALLED PRODUCT
~/.local/pipx/venvs/claude-mpm/lib/python3.13/site-packages/claude_mpm/
├── commands/*.md              ← PACKAGED commands
├── agents/*.{md,json}         ← PACKAGED agents
└── services/
    ├── command_deployment_service.py
    └── agents/deployment/

        │
        │ Deployment Services
        │ (COPY, not symlink)
        ↓

DEPLOYMENT TARGETS

USER-LEVEL (Commands)
~/.claude/commands/mpm-*.md    ← DEPLOYED commands (ALL projects)

PROJECT-LEVEL (Agents)
~/myproject/.claude/agents/*.md ← DEPLOYED agents (per project)
~/myproject/.claude-mpm/        ← Project config

KEY PRINCIPLE:
  Source → Installed → Deployed
  Always COPY at each stage, NEVER symlink
  Development must simulate production behavior
```

---

## File Locations Reference

### Quick Reference Table

| File Type | Source (Dev) | Installed (Package) | Deployed To | Scope | Git Tracked |
|-----------|-------------|---------------------|-------------|-------|-------------|
| **Commands** | `src/claude_mpm/commands/` | `site-packages/claude_mpm/commands/` | `~/.claude/commands/` | User-level (global) | Source only |
| **Agents** | `src/claude_mpm/agents/` | `site-packages/claude_mpm/agents/` | `.claude/agents/` | Project-level (local) | Source only |
| **Config** | `.claude-mpm/` | N/A | `.claude-mpm/` | Project-level (local) | Yes |
| **Skills** | `src/claude_mpm/skills/bundled/` | `site-packages/claude_mpm/skills/bundled/` | Referenced, not copied | Bundled | Source only |

### Detailed Locations

#### Commands

```
Development:   ~/Projects/claude-mpm/src/claude_mpm/commands/*.md
Installed:     ~/.local/pipx/venvs/claude-mpm/.../claude_mpm/commands/*.md
Deployed:      ~/.claude/commands/mpm-*.md
Discovered by: Claude Code (user-level commands)
Scope:         Global (all projects)
```

#### Agents

```
Development:   ~/Projects/claude-mpm/src/claude_mpm/agents/*.{md,json,yaml}
Installed:     ~/.local/pipx/venvs/claude-mpm/.../claude_mpm/agents/*
Deployed:      ~/myproject/.claude/agents/*.md
Discovered by: Claude Code (project-level agents)
Scope:         Per-project (local)
```

#### Configuration

```
Development:   ~/Projects/claude-mpm/.claude-mpm/
User Projects: ~/myproject/.claude-mpm/
Scope:         Project-specific
Git Tracked:   Yes (configuration is tracked)
```

#### Skills

```
Bundled:       src/claude_mpm/skills/bundled/*.md
User:          ~/.config/claude-mpm/skills/*.md
Project:       .claude-mpm/skills/*.md
Scope:         Three-tier (bundled/user/project)
```

---

## Makefile Targets for Development

### Essential Development Targets

```bash
# Complete development setup (recommended for new contributors)
make dev-complete
# Runs: setup-dev + setup-pre-commit
# Does: Editable install + shell config + pre-commit hooks

# Install in development mode
make setup-dev
# Runs: pip install -e . + shell configuration

# Auto-fix code formatting issues
make lint-fix
# Runs: black + isort (auto-fixes common issues)

# Run comprehensive quality checks
make quality
# Runs: lint + type-check + tests (required before commit)

# Run pre-commit hooks manually
make pre-commit-run
# Runs: All pre-commit hooks on all files

# Format code
make format
# Runs: black + isort

# Type checking
make type-check
# Runs: mypy
```

### Testing Targets

```bash
# Test installation
make test-installation
# Verifies: Installation + command availability + version

# Show installation info
make info
# Displays: Paths, versions, configuration
```

### Release Targets (Maintainers Only)

```bash
# Release with quality gate
make safe-release-build
# Runs: Complete quality validation + build

# Patch release (bug fixes)
make release-patch

# Minor release (new features)
make release-minor

# Major release (breaking changes)
make release-major

# Publish release
make release-publish
```

### Suggested New Targets

Consider adding these targets for better development workflow:

```makefile
deploy-commands:  ## Force deploy commands to ~/.claude/commands/
	python3 -c "from claude_mpm.services.command_deployment_service import deploy_commands_on_startup; deploy_commands_on_startup(force=True)"

deploy-agents:  ## Deploy agents to current project's .claude/agents/
	claude-mpm agents deploy

test-deployment:  ## Test command and agent deployment
	@echo "Testing command deployment..."
	@make deploy-commands
	@echo "Testing agent deployment..."
	@make deploy-agents
	@echo "Deployment test complete!"

clean-deployment:  ## Clean deployed commands and agents
	rm -rf ~/.claude/commands/mpm-*.md
	rm -rf .claude/agents/*.md
	@echo "Cleaned deployment directories"
```

---

## Key Source Files

### Package Configuration

**File:** `pyproject.toml` (line 99-100)

```toml
[tool.setuptools.package-data]
claude_mpm = [
    "commands/*.md",          # Command source files
    "agents/*.md",            # Agent markdown templates
    "agents/*.json",          # Agent JSON schemas
    "agents/*.yaml",          # Agent YAML configs
    "skills/bundled/*.md",    # Bundled skills
    # ... other package data
]
```

**Purpose:** Ensures command and agent files are included in the installed package.

### Command Deployment

**File:** `src/claude_mpm/services/command_deployment_service.py`

**Key Methods:**
- `deploy_commands(force: bool)` - Deploy commands to ~/.claude/commands/
- Uses `get_package_resource_path()` to find installed commands
- Copies files from site-packages to ~/.claude/commands/

**Usage:**
```python
from claude_mpm.services.command_deployment_service import CommandDeploymentService

service = CommandDeploymentService()
service.deploy_commands(force=True)
```

### Agent Deployment

**Files:**
- `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py`
- `src/claude_mpm/services/agents/deployment/refactored_agent_deployment_service.py`

**Key Features:**
- Multi-source support (bundled/user/project)
- Per-project deployment to .claude/agents/
- Template compilation and skill injection

**Usage:**
```python
from claude_mpm.services.agents.deployment import AgentDeploymentService

service = AgentDeploymentService()
service.deploy_to_project(project_path)
```

### Auto-Deployment on Startup

**File:** `src/claude_mpm/cli/commands/run.py` (line 798)

**Function:** `deploy_commands_on_startup()`

**Purpose:** Automatically deploys commands when claude-mpm starts

**Behavior:**
- Checks if commands exist in ~/.claude/commands/
- Deploys if missing or if force=True
- Ensures user always has latest commands

### Path Resolution

**File:** `src/claude_mpm/core/unified_paths.py`

**Key Functions:**
- `get_package_resource_path(resource: str)` - Find installed resources
- `get_commands_dir()` - Get commands directory
- `get_agents_dir()` - Get agents directory

**Purpose:** Abstracts path resolution for both development and production.

---

## Best Practices Summary

### For Command Development

1. Edit source: `src/claude_mpm/commands/*.md`
2. Force redeploy: `python3 -c "...deploy_commands_on_startup(force=True)"`
3. Test deployed: `cat ~/.claude/commands/mpm-*.md`
4. Test in Claude: `/mpm-command-name`

### For Agent Development

1. Edit source: `src/claude_mpm/agents/*.{md,json,yaml}`
2. Deploy to project: `claude-mpm agents deploy`
3. Test deployed: `cat .claude/agents/agent-name.md`
4. Test in Claude: Use agent in session

### For Testing

1. Use editable install: `pip install -e .`
2. Deploy properly (don't symlink)
3. Test from deployment locations
4. Verify in clean environment before release

### For Quality

1. Run `make lint-fix` during development
2. Run `make quality` before commits
3. Never commit without passing quality checks
4. Use pre-commit hooks (installed by `make dev-complete`)

---

## Troubleshooting

### Commands Not Available in Claude Code

**Problem:** `/mpm-config` not found

**Solution:**
```bash
# 1. Check deployment
ls -la ~/.claude/commands/mpm-config.md

# 2. Force redeploy
python3 -c "from claude_mpm.services.command_deployment_service import deploy_commands_on_startup; deploy_commands_on_startup(force=True)"

# 3. Restart Claude Code
```

### Agents Not Available in Project

**Problem:** Engineer agent not found

**Solution:**
```bash
# 1. Check deployment
ls -la .claude/agents/engineer.md

# 2. Deploy agents
claude-mpm agents deploy

# 3. Verify installation
claude-mpm doctor --checks agents
```

### Source Changes Not Reflected

**Problem:** Made changes to source but not seeing them

**Checklist:**
1. Did you redeploy? (Changes to source don't auto-deploy)
2. Are you testing from deployed location?
3. Is editable install active? (`pip show claude-mpm`)
4. Did you restart Claude Code?

### Symlink Issues

**Problem:** Accidentally created symlinks

**Solution:**
```bash
# 1. Remove symlinks
rm ~/.claude/commands  # If it's a symlink
rm .claude/agents      # If it's a symlink

# 2. Recreate as directories
mkdir -p ~/.claude/commands
mkdir -p .claude/agents

# 3. Proper deployment
python3 -c "from claude_mpm.services.command_deployment_service import deploy_commands_on_startup; deploy_commands_on_startup(force=True)"
claude-mpm agents deploy
```

---

## Additional Resources

### Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines and quality standards
- **[docs/developer/ARCHITECTURE.md](docs/developer/ARCHITECTURE.md)** - Service-oriented architecture
- **[docs/developer/SERVICES.md](docs/developer/SERVICES.md)** - Service development guide
- **[docs/developer/STRUCTURE.md](docs/developer/STRUCTURE.md)** - File organization
- **[docs/reference/DEPLOY.md](docs/reference/DEPLOY.md)** - Release process

### Getting Help

1. **Check Documentation**: Comprehensive guides in `docs/`
2. **Review Architecture**: Understand the system design
3. **Run Quality Checks**: `make quality` catches many issues
4. **Ask for Help**: Open an issue on GitHub

---

## Questions?

- 📚 **Documentation**: [docs/README.md](docs/README.md) for complete navigation
- 🏗️ **Architecture**: [docs/developer/ARCHITECTURE.md](docs/developer/ARCHITECTURE.md) for system design
- 🚀 **Deployment**: [docs/reference/DEPLOY.md](docs/reference/DEPLOY.md) for release process
- 💬 **Community**: [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues) for questions and discussions

---

**Remember:** Source → Installed → Deployed. Always COPY, never symlink. Development should simulate production.

Thank you for contributing to Claude MPM! 🚀
