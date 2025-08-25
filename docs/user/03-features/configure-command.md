# Configure Command

The `claude-mpm configure` command provides an interactive terminal-based interface for managing claude-mpm configurations, agents, and behavior files.

## Overview

The configure command offers both interactive (TUI) and non-interactive modes for:
- Managing agent configurations (enable/disable)
- Editing agent JSON templates
- Managing behavior files (identity and workflow)
- Switching between project-level and user-level configurations
- Displaying version information

## Usage

### Interactive Mode

Launch the interactive TUI:
```bash
claude-mpm configure
```

This opens a menu-driven interface with options for:
- Agent Management
- Template Editing (coming soon)
- Behavior File Management (coming soon)
- Configuration Scope switching
- Version Information display

### Non-Interactive Commands

#### List Agents
```bash
claude-mpm configure --list-agents
```
Displays all available agents in JSON format.

#### Enable/Disable Agents
```bash
# Enable an agent
claude-mpm configure --enable-agent engineer

# Disable an agent
claude-mpm configure --disable-agent designer
```

#### Export/Import Configuration
```bash
# Export current configuration
claude-mpm configure --export-config my_config.json

# Import configuration
claude-mpm configure --import-config my_config.json
```

#### Version Information
```bash
claude-mpm configure --version-info
```
Displays Claude MPM, Claude Code, and Python versions.

### Direct Navigation

Jump directly to specific sections:
```bash
# Open agent management directly
claude-mpm configure --agents

# Open template editing directly
claude-mpm configure --templates

# Open behavior file management directly
claude-mpm configure --behaviors
```

### Configuration Scope

Manage configurations at different levels:
```bash
# Project-level configuration (default)
claude-mpm configure --scope project

# User-level configuration
claude-mpm configure --scope user

# Specify a different project directory
claude-mpm configure --project-dir /path/to/project
```

## Display Options

Customize the interface appearance:
```bash
# Disable colors in the TUI
claude-mpm configure --no-colors

# Use compact display mode
claude-mpm configure --compact
```

## Configuration Storage

### Project-Level
- Location: `.claude-mpm/agent_states.json` in the project directory
- Contains agent enable/disable states for the current project

### User-Level
- Location: `~/.claude-mpm/agent_states.json`
- Contains global agent configurations

## Available Agents

The configure command manages these default agents:
- **engineer**: Software engineering and architecture specialist
- **researcher**: Research and information gathering specialist
- **writer**: Documentation and content creation specialist
- **analyst**: Data analysis and visualization specialist
- **designer**: UI/UX design and frontend specialist
- **tester**: Testing and quality assurance specialist
- **devops**: Infrastructure and deployment specialist
- **security**: Security analysis and vulnerability assessment

## Examples

### Example 1: Quick Agent Setup
```bash
# List all agents
claude-mpm configure --list-agents

# Enable specific agents for your project
claude-mpm configure --enable-agent engineer
claude-mpm configure --enable-agent tester

# Disable unused agents
claude-mpm configure --disable-agent designer
```

### Example 2: Configuration Management
```bash
# Export your team's configuration
claude-mpm configure --export-config team_config.json

# Share with team members who can import it
claude-mpm configure --import-config team_config.json
```

### Example 3: Interactive Configuration
```bash
# Launch interactive mode
claude-mpm configure

# In the TUI:
# - Press [1] for Agent Management
# - Press [e] to enable an agent
# - Enter the agent ID
# - Press [b] to go back
# - Press [q] to quit
```

## Integration with Claude MPM

The configure command integrates with other claude-mpm features:
- Agent states affect which agents are available during `claude-mpm run`
- Configurations can be project-specific or global
- Settings persist across sessions

## Future Enhancements

Planned features include:
- Full template editing in external editors
- Behavior file creation and management
- Agent dependency resolution
- Custom agent creation wizard
- Configuration validation and testing