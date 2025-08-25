# Agent Management TUI - Enhanced 3-Pane Interface

## Overview

The Agent Management screen has been redesigned with a comprehensive 3-pane interface that provides full control over agent deployment and management.

## Features

### 3-Pane Layout

1. **Left Pane: Categories**
   - Three tabs: System, Project, User
   - Shows agents organized by source
   - Visual indicators for deployment status (✓/✗)

2. **Middle Pane: Agent List**
   - Detailed table view of agents in selected category
   - Shows: Name, Deployment Status, Version, Template Path
   - Search functionality to filter agents
   - Click to select an agent for details

3. **Right Pane: Agent Details & Actions**
   - Comprehensive agent information
   - Action buttons for agent management

### Agent Information Display

- **Basic Info**: Name, Category, Version
- **Deployment Status**: Shows if deployed to .claude/agents/
- **Description**: Full agent description
- **Template Path**: Location of JSON template
- **Deployment Path**: Where agent is deployed (if deployed)
- **Model**: AI model configuration
- **Tools**: List of available tools
- **Last Modified**: Template modification timestamp

### Available Actions

#### 1. Toggle Deployment
- **Deploy**: Converts JSON template to Markdown and deploys to .claude/agents/
- **Undeploy**: Removes agent from .claude/agents/
- Button label changes based on current state

#### 2. View Properties
- Opens modal with full JSON template
- Read-only view for inspection
- Available for all agents

#### 3. Copy to Project/User
- Copy system agents to project (.claude-mpm/agents/) or user (~/.claude-mpm/agents/) directories
- Creates local customizable copy
- Disabled if agent already exists in target location

#### 4. Edit
- Edit JSON template for project/user agents
- System agents cannot be edited (must copy first)
- Opens editor dialog with JSON content

#### 5. Delete
- Remove project/user agents
- System agents cannot be deleted
- Automatically undeploys if deployed

## Agent Discovery

The system discovers agents from three sources:

1. **System Agents**
   - Location: `src/claude_mpm/agents/templates/`
   - Read-only, provided by claude-mpm
   - Can be copied for customization

2. **Project Agents**
   - Location: `.claude-mpm/agents/`
   - Project-specific customizations
   - Editable and deletable

3. **User Agents**
   - Location: `~/.claude-mpm/agents/`
   - User-level customizations
   - Shared across all projects

## Deployment Process

When deploying an agent:

1. Reads JSON template from source directory
2. Converts to Markdown format with YAML frontmatter
3. Writes to `.claude/agents/` directory
4. Agent becomes available to Claude Code

## Testing

Run the test script to try the new interface:

```bash
./scripts/test_agent_management_tui.py
```

Or launch the full configuration TUI:

```bash
claude-mpm configure
```

Then navigate to Agent Management using Ctrl+A or by selecting it from the sidebar.

## Keyboard Shortcuts

- **Tab**: Navigate between panes
- **Enter**: Select item
- **Ctrl+A**: Jump to Agent Management
- **Ctrl+Q**: Quit application
- **Arrow Keys**: Navigate lists and tables

## Implementation Details

### Key Classes

- **AgentInfo**: Extended agent model with deployment tracking
- **AgentDiscovery**: Service to find agents from all sources
- **AgentManagementScreen**: Main screen with 3-pane layout
- **ViewAgentPropertiesDialog**: Modal for viewing JSON

### Deployment Status Checking

The system checks if an agent is deployed by looking for corresponding `.md` files in `.claude/agents/`. It tries multiple naming patterns:
- `{agent_name}.md`
- `{agent_name_with_underscores}.md`
- `{agent_name}-agent.md`

### JSON to Markdown Conversion

The deployment process converts JSON templates to Markdown with:
- YAML frontmatter for metadata
- Instructions section
- Tools section
- Proper formatting for Claude Code

## Benefits

1. **Visual Deployment Status**: Instantly see which agents are deployed
2. **Multi-Source Management**: Handle system, project, and user agents in one place
3. **Safe Operations**: Confirmation dialogs for destructive actions
4. **Live Updates**: UI refreshes after each operation
5. **Search & Filter**: Quickly find agents
6. **Full CRUD**: Create (copy), Read, Update (edit), Delete operations

## Future Enhancements

Potential improvements:
- Batch operations (deploy/undeploy multiple agents)
- Agent dependency visualization
- Template validation before deployment
- Import/Export functionality
- Version comparison between deployed and template
- Agent usage statistics