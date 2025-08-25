# Agent Dependencies Management

## Overview

Claude MPM features a comprehensive dependency management system that allows agents to declare their Python and system dependencies, which are automatically aggregated during the build process and made available as optional pip extras.

This system enables:
- **Declarative Dependencies**: Agents specify their requirements in configuration files
- **Automatic Aggregation**: Dependencies are collected from all agent sources during build
- **Version Conflict Resolution**: Intelligent handling of conflicting version requirements
- **Optional Installation**: Users can choose to install agent dependencies with `pip install claude-mpm[agents]`
- **Build Integration**: Seamless integration with the project's build and packaging process

## Architecture

### Dependency Sources

Dependencies are aggregated from agents across three tiers in precedence order:

1. **PROJECT** - `.claude-mpm/agents/` (JSON format only)
2. **USER** - `~/.claude-mpm/agents/` (any format)
3. **SYSTEM** - Built-in framework agents (`src/claude_mpm/agents/templates/`)

### Aggregation Process

The dependency aggregation system:

1. **Scans** all agent directories for configuration files (JSON/YAML)
2. **Extracts** dependency information from each agent
3. **Normalizes** dependency strings to package name and version specifier
4. **Resolves** version conflicts using highest compatible version strategy
5. **Updates** `pyproject.toml` with the `[agents]` optional dependency group
6. **Validates** all dependencies for correct format and installability

## Agent Configuration

### Declaring Dependencies

Agents declare dependencies in their configuration files using the `dependencies` section:

```json
{
  "agent_id": "data_analyst",
  "agent_version": "1.0.0",
  "dependencies": {
    "python": [
      "pandas>=2.0.0",
      "numpy>=1.24.0",
      "matplotlib>=3.7.0",
      "seaborn>=0.12.0"
    ],
    "system": [
      "git",
      "ripgrep"
    ],
    "optional": false
  }
}
```

### Dependency Schema

The `dependencies` object supports these fields:

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `python` | `array` | Python packages with optional version specifiers | No |
| `system` | `array` | System-level dependencies (commands in PATH) | No |
| `optional` | `boolean` | Whether dependencies are optional for agent function | No |

### Python Dependencies Format

Python dependencies follow standard pip requirement syntax:

```json
{
  "python": [
    "package_name",                    // Latest version
    "package_name>=1.0.0",            // Minimum version
    "package_name==1.2.3",            // Exact version
    "package_name>=1.0.0,<2.0.0",     // Version range
    "package_name[extra1,extra2]>=1.0" // With extras
  ]
}
```

### System Dependencies

System dependencies are commands that should be available in the user's PATH:

```json
{
  "system": [
    "git",           // Version control
    "ripgrep",       // Fast text search
    "docker",        // Containerization
    "kubectl",       // Kubernetes CLI
    "terraform"      // Infrastructure as code
  ]
}
```

**Note**: System dependencies are documented but not automatically installed. Users must install them manually through their system package manager.

## Version Conflict Resolution

When multiple agents declare dependencies on the same package with different version requirements, the system uses intelligent conflict resolution:

### Resolution Strategy

1. **Parse All Specifiers**: Extract version requirements from all agents
2. **Compatibility Check**: Validate that requirements can be satisfied together
3. **Highest Minimum**: Select the highest minimum version requirement
4. **Range Intersection**: Find overlapping version ranges when possible
5. **Fallback**: Use first declared version if resolution fails

### Examples

```json
// Agent A declares: "pandas>=1.5.0"
// Agent B declares: "pandas>=2.0.0" 
// Resolution: "pandas>=2.0.0" (highest minimum)

// Agent A declares: "numpy>=1.20.0,<2.0.0"
// Agent B declares: "numpy>=1.24.0"
// Resolution: "numpy>=1.24.0,<2.0.0" (intersection)

// Agent A declares: "requests==2.28.0"
// Agent B declares: "requests>=2.30.0"
// Resolution: Conflict logged, uses "requests==2.28.0" (first)
```

## Using the Aggregation System

### Manual Aggregation

Run the aggregation script manually to update dependencies:

```bash
# View what would be changed without modifying files
python scripts/aggregate_agent_dependencies.py --dry-run

# Update pyproject.toml with current agent dependencies
python scripts/aggregate_agent_dependencies.py

# Enable verbose logging for debugging
python scripts/aggregate_agent_dependencies.py --verbose

# Specify custom project root
python scripts/aggregate_agent_dependencies.py --project-root /path/to/project
```

### Build Integration

The aggregation is typically integrated into the build process:

```bash
# In CI/CD pipelines or before releases
python scripts/aggregate_agent_dependencies.py
git add pyproject.toml
git commit -m "Update agent dependencies"
```

### Installation Options

Users can install Claude MPM with different dependency sets:

```bash
# Core functionality only
pip install claude-mpm

# With agent dependencies (recommended)
pip install "claude-mpm[agents]"

# With development dependencies
pip install "claude-mpm[dev]"

# With all optional dependencies
pip install "claude-mpm[agents,dev]"
```

## Best Practices

### For Agent Developers

1. **Minimal Dependencies**: Only declare truly necessary dependencies
2. **Version Constraints**: Use appropriate version ranges, not exact pins
3. **Optional vs Required**: Mark dependencies as optional if the agent can function without them
4. **Documentation**: Document what each dependency is used for
5. **Testing**: Test agents with minimum required dependency versions

### Dependency Declaration Guidelines

```json
{
  "dependencies": {
    "python": [
      // Good: Reasonable minimum version with room for updates
      "pandas>=2.0.0",
      
      // Avoid: Too restrictive, blocks updates
      "pandas==2.0.1",
      
      // Good: Range that allows patch updates
      "matplotlib>=3.7.0,<4.0.0",
      
      // Good: Feature-based minimum version
      "numpy>=1.24.0"  // Requires specific NumPy features
    ],
    "optional": false  // Be explicit about requirement level
  }
}
```

### For Package Maintainers

1. **Regular Updates**: Run aggregation before releases
2. **Conflict Monitoring**: Watch for version conflicts in logs
3. **Dependency Auditing**: Review aggregated dependencies for security
4. **Documentation**: Keep dependency documentation current

## Troubleshooting

### Common Issues

#### Aggregation Script Fails

```bash
# Check Python environment
python --version
pip list | grep -E "(packaging|toml|pyyaml)"

# Install missing dependencies
pip install packaging toml pyyaml

# Run with verbose logging
python scripts/aggregate_agent_dependencies.py --verbose
```

#### Version Conflicts

```bash
# Check conflict details in logs
python scripts/aggregate_agent_dependencies.py --verbose 2>&1 | grep -i conflict

# Review specific agent dependencies
grep -r "dependencies" .claude-mpm/agents/ src/claude_mpm/agents/templates/
```

#### Missing Dependencies After Installation

```bash
# Verify installation includes agents extra
pip show claude-mpm | grep -A 20 "Requires:"

# Reinstall with agents extra
pip install --force-reinstall "claude-mpm[agents]"

# Check what's actually in the agents extra
python -c "import pkg_resources; print(pkg_resources.get_distribution('claude-mpm').extras)"
```

### Debugging

#### Verbose Logging

```bash
# Enable detailed logging
python scripts/aggregate_agent_dependencies.py --verbose

# Log to file for analysis
python scripts/aggregate_agent_dependencies.py --verbose > aggregation.log 2>&1
```

#### Manual Inspection

```python
# Inspect aggregation results
import json
from pathlib import Path

# Load an agent config
with open('.claude-mpm/agents/my_agent.json') as f:
    config = json.load(f)
    print("Dependencies:", config.get('dependencies', {}))

# Check pyproject.toml
import toml
with open('pyproject.toml') as f:
    project = toml.load(f)
    print("Agents extra:", project['project']['optional-dependencies']['agents'])
```

## Advanced Topics

### Custom Aggregation Scripts

For specialized workflows, you can create custom aggregation scripts:

```python
#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0, 'scripts')

from aggregate_agent_dependencies import DependencyAggregator

# Custom aggregator with filtering
class FilteredAggregator(DependencyAggregator):
    def extract_dependencies(self, config):
        deps = super().extract_dependencies(config)
        # Filter out certain packages
        return [d for d in deps if not d.startswith('dev-')]

aggregator = FilteredAggregator(Path.cwd())
success = aggregator.run()
```

### Integration with Package Managers

#### Poetry Integration

```toml
# pyproject.toml for Poetry projects
[tool.poetry.extras]
agents = ["pandas", "numpy", "matplotlib"]

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

#### Conda Integration

```yaml
# environment.yml
name: claude-mpm-agents
dependencies:
  - python>=3.8
  - pip
  - pip:
    - claude-mpm[agents]
```

### CI/CD Integration

#### GitHub Actions

```yaml
name: Update Agent Dependencies
on:
  push:
    paths:
      - 'src/claude_mpm/agents/templates/*.json'
      - '.claude-mpm/agents/*.json'

jobs:
  update-deps:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install packaging toml pyyaml
        
      - name: Aggregate agent dependencies
        run: python scripts/aggregate_agent_dependencies.py
        
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add pyproject.toml
          git diff --staged --quiet || git commit -m "chore: update agent dependencies"
          git push
```

## Migration Guide

### From Manual to Automatic Dependencies

If you're upgrading from manually managed dependencies:

1. **Audit Current Dependencies**: Review what's currently in `pyproject.toml`
2. **Identify Agent Needs**: Determine which dependencies belong to which agents
3. **Add to Agent Configs**: Update agent configurations with dependencies
4. **Run Aggregation**: Execute the aggregation script
5. **Verify Results**: Ensure all needed dependencies are included
6. **Test Installation**: Verify `pip install claude-mpm[agents]` works
7. **Update Documentation**: Update any dependency installation instructions

### Version Constraint Migration

```bash
# Before: Manual pyproject.toml
[project.optional-dependencies]
agents = ["pandas==2.0.1", "numpy==1.24.0"]

# After: Agent-declared dependencies
# In agent config:
{
  "dependencies": {
    "python": ["pandas>=2.0.0", "numpy>=1.24.0"]
  }
}

# Aggregated result:
[project.optional-dependencies]
agents = ["numpy>=1.24.0", "pandas>=2.0.0"]
```

## Security Considerations

### Dependency Security

1. **Audit Dependencies**: Regularly audit aggregated dependencies for vulnerabilities
2. **Version Pinning**: Consider pinning to specific versions in production
3. **Source Validation**: Ensure agent sources are trusted
4. **Minimal Installation**: Only install necessary dependency groups

### Example Security Workflow

```bash
# Audit dependencies before release
pip install safety
safety check --json requirements.txt

# Pin dependencies for production
pip freeze > requirements-lock.txt

# Verify only trusted agent sources
ls -la .claude-mpm/agents/
ls -la ~/.claude-mpm/agents/
```

## Future Enhancements

### Planned Features

1. **Dependency Caching**: Cache dependency resolution for faster builds
2. **Conflict Reporting**: Enhanced conflict detection and reporting
3. **Auto-Updates**: Automated dependency updates with compatibility checks
4. **Integration Testing**: Automated testing of agent dependencies
5. **Dependency Graphs**: Visualization of dependency relationships

### Contributing

To contribute to the dependency management system:

1. Fork the repository
2. Create feature branch: `git checkout -b feature/dependency-enhancement`
3. Add tests for new functionality
4. Update documentation
5. Submit pull request

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed guidelines.