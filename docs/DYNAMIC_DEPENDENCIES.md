# Dynamic Agent Dependency Management

## Overview

Claude MPM now supports **dynamic dependency checking** that only loads and verifies dependencies for agents that are actually deployed, rather than requiring all possible agent dependencies to be installed upfront.

## Key Features

### 1. Startup Dependency Check
When you run `claude-mpm`, it automatically:
- Discovers which agents are deployed in `.claude/agents/`
- Loads dependency requirements from their configuration files
- Checks if required Python packages are installed
- Shows a brief warning if dependencies are missing

```bash
$ claude-mpm
Deployed agents: 15 (3 project, 0 user, 12 system)
⚠️  27 agent dependencies missing
   Run 'pip install "claude-mpm[agents]"' to install all agent dependencies
```

### 2. Agent Dependency Subcommands
Dependency management is integrated into the `agents` command as subcommands:

```bash
# Check dependencies for all deployed agents
claude-mpm agents deps-check

# Check dependencies for a specific agent
claude-mpm agents deps-check --agent engineer

# List all dependencies from deployed agents
claude-mpm agents deps-list

# Output in pip-installable format
claude-mpm agents deps-list --format pip > requirements.txt

# Install missing dependencies
claude-mpm agents deps-install

# Dry run to see what would be installed
claude-mpm agents deps-install --dry-run

# Install for specific agent only
claude-mpm agents deps-install --agent data_engineer
```

### 3. Smart Dependency Resolution
The system intelligently:
- Only checks dependencies for agents that are deployed
- Tracks which packages have already been checked to avoid duplicates
- Distinguishes between missing packages and wrong versions
- Provides clear installation instructions

## How It Works

### Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ .claude/agents/ │────>│ AgentDependency  │────>│ Agent Configs   │
│   (deployed)    │     │     Loader       │     │ (.json files)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Check Installed      │
                    │     Packages          │
                    └──────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Generate Report    │
                    │  & Recommendations   │
                    └──────────────────────┘
```

### Discovery Process

1. **Agent Discovery**: Scans `.claude/agents/` for deployed `.md` files
2. **Config Loading**: Finds corresponding `.json` configs in:
   - `.claude-mpm/agents/` (PROJECT)
   - `~/.claude-mpm/agents/` (USER)
   - `src/claude_mpm/agents/templates/` (SYSTEM)
3. **Dependency Extraction**: Reads `dependencies.python` from configs
4. **Version Checking**: Uses `importlib.metadata` to check installed versions
5. **Report Generation**: Creates actionable recommendations

## Usage Examples

### Basic Workflow

```bash
# Deploy agents
claude-mpm agents deploy

# Check what's missing
claude-mpm agents deps-check

# Install missing dependencies
claude-mpm agents deps-install

# Or install all at once
pip install "claude-mpm[agents]"
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Deploy Agents
  run: claude-mpm agents deploy
  
- name: Check Dependencies
  run: |
    if ! claude-mpm agents deps-check; then
      echo "Missing dependencies detected"
      claude-mpm agents deps-install
    fi
```

### Selective Installation

```bash
# Only install dependencies for specific agent
claude-mpm agents deps-check --agent data_engineer
claude-mpm agents deps-install --agent data_engineer

# Export dependencies for requirements.txt
claude-mpm agents deps-list --format pip > agent-requirements.txt
pip install -r agent-requirements.txt
```

## Benefits

### 1. **Reduced Installation Size**
- Core installation: ~50 MB
- With all agents: ~500 MB
- Dynamic loading: Only what you need

### 2. **Faster Startup**
- No need to load unused dependencies
- Checks are cached per session
- Optional auto-install for convenience

### 3. **Better Compatibility**
- Avoid version conflicts from unused agents
- Install only compatible versions
- Clear reporting of conflicts

### 4. **Improved Developer Experience**
- Clear visibility into what's needed
- Actionable error messages
- Multiple installation options

## Configuration

### Disable Dependency Checking
To skip dependency checks at startup:

```python
# In run.py or via environment variable
args.check_dependencies = False
```

### Auto-Install Mode
Enable automatic installation of missing dependencies:

```python
from claude_mpm.utils.agent_dependency_loader import AgentDependencyLoader

loader = AgentDependencyLoader(auto_install=True)
results = loader.load_and_check()
```

## Comparison: Static vs Dynamic

| Aspect | Static (Old) | Dynamic (New) |
|--------|-------------|---------------|
| **Installation** | All dependencies upfront | Only what's deployed |
| **Size** | ~500 MB | 50-200 MB typical |
| **Conflicts** | All agents compete | Only active agents |
| **Startup** | No checks | Quick dependency scan |
| **Flexibility** | One size fits all | Tailored to usage |
| **Updates** | Rebuild & reinstall | Deploy & check |

## Troubleshooting

### Missing Dependencies After Installation

```bash
# Clear package cache and retry
pip cache purge
pip install --force-reinstall "claude-mpm[agents]"

# Check what's actually installed
pip list | grep -E "(pandas|numpy|etc)"
```

### Version Conflicts

```bash
# See detailed version information
claude-mpm agents deps-check --verbose

# Install specific version
pip install "pandas==2.1.0"
```

### System Dependencies

Some agents require system commands (git, docker, etc.):

```bash
# macOS
brew install git ripgrep docker

# Ubuntu/Debian
apt-get install git ripgrep docker.io

# Check system dependencies
which git docker kubectl
```

## Future Enhancements

### Planned Features

1. **Dependency Caching**: Cache resolution results for faster subsequent checks
2. **Virtual Environments**: Auto-create isolated environments per project
3. **Conflict Resolution**: Interactive resolution of version conflicts
4. **Dependency Groups**: Install subsets like `[data]`, `[security]`, `[ops]`
5. **Update Notifications**: Alert when newer versions are available

### Contributing

To add dependencies to an agent:

1. Edit the agent's JSON configuration
2. Add to the `dependencies.python` array
3. Run aggregation script (for build-time inclusion)
4. Test with dynamic loader

```json
{
  "dependencies": {
    "python": [
      "new-package>=1.0.0",
      "another-package[extra]>=2.0.0"
    ]
  }
}
```

## Summary

Dynamic dependency management makes Claude MPM more efficient and flexible by:
- Loading only what's needed
- Providing clear visibility into requirements
- Offering multiple installation strategies
- Reducing conflicts and bloat

This approach ensures agents have their required tools available while keeping the core system lightweight and fast.