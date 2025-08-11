# Enhanced Configure Window Implementation

## Overview

The new ConfigScreenV2 provides a comprehensive configuration management interface for the Terminal Monitor with registry-based site identification and enhanced YAML editing capabilities.

## Key Features

### 1. Registry Integration
- **ProjectRegistry Service**: Automatically discovers and tracks all claude-mpm projects
- **Site Identification**: Each project gets a unique UUID-based registry entry
- **Metadata Collection**: Captures git status, environment details, and project characteristics
- **Persistent Tracking**: Registry files stored in `~/.claude-mpm/registry/`

### 2. Three-Column Layout

```
┌─────────────────────────────────────────────────────────────┐
│                    Configure Window                          │
├───────────────┬──────────────────────────────┬──────────────┤
│  Instances    │    [Instance Name]           │              │
│               │  ┌──────────────────────────┐│              │
│  Framework    │  │ Configuration│Instructions│Agents       │
│  [Global]     │  ├──────────────────────────┤│              │
│               │  │                          ││              │
│  Registry     │  │   Form/YAML Editor      ││              │
│  Project A    │  │                          ││              │
│  Project B    │  │                          ││              │
│               │  │                          ││              │
│  Local        │  │                          ││              │
│  Project C    │  │                          ││              │
│  Project D    │  └──────────────────────────┘│              │
│               ├────────────────────────────────┤              │
│               │ Actions                        │              │
│               │ [Install Agents] [Import] [↻] │              │
└───────────────┴────────────────────────────────┴──────────────┘
```

### 3. YAML Form Editor

The YAMLFormWidget provides dynamic form generation from YAML structure:

#### Features:
- **Automatic Field Discovery**: Recursively parses YAML to generate form fields
- **Type-Appropriate Widgets**:
  - Text fields for strings
  - Numeric inputs with validation
  - Checkboxes for booleans
  - List editors with add/remove capabilities
  - Nested object support with indentation

#### Form/YAML Toggle:
- **Form Mode**: Structured editing with validation
- **YAML Mode**: Direct text editing for advanced users
- **Seamless Switching**: Preserves changes when toggling modes
- **Real-time Validation**: Shows syntax errors immediately

### 4. Agent Management

#### Install Agents Dialog:
```python
# Lists all available agents from framework
# Users select agents via checkboxes
# Deploys selected agents to project
```

#### Import Agents Dialog:
```python
# File path input for custom agent files
# Supports .yaml, .yml, .json, .md formats
# Copies agent to project's .claude/agents/
```

## Implementation Details

### Core Components

#### 1. ConfigScreenV2 (`config_screen_v2.py`)
- Main screen class with three-column layout
- Manages instance list, tabs, and actions
- Handles registry and discovery integration

#### 2. YAMLFormWidget
- Dynamic form generation from YAML data
- Recursive field creation for nested structures
- Type validation and conversion
- List item management

#### 3. EnhancedConfigEditor
- Dual-mode editor (Form/YAML)
- Mode switching with validation
- Save/load functionality
- Default configuration generation

### Service Integration

#### ProjectRegistry
- Discovers projects across the system
- Maintains project metadata
- Provides UUID-based identification
- Tracks project lifecycle

#### InstallationDiscovery
- Scans workspace directories
- Creates Installation objects
- Detects toolchains and git status
- Caches discovery results

#### AgentDeploymentService
- Lists available agents
- Deploys single agents
- Manages agent versions
- Handles template building

## Usage

### Running with ConfigScreenV2

```python
# In app.py, ConfigScreenV2 is now default
app = MPMManagerApp(use_v2_config=True)  # Default
```

### Test Script

```bash
# Run the test script to verify functionality
./scripts/test_config_screen_v2.py
```

## Key Improvements Over Original

1. **Registry-Based Discovery**: Projects tracked persistently across sessions
2. **Form-Based Editing**: No more YAML syntax errors for users
3. **Hierarchical Organization**: Projects grouped by type (Framework/Registry/Local)
4. **Agent Management UI**: Built-in dialogs for agent installation
5. **Enhanced Metadata**: Shows git branch, toolchains, and project info

## Keyboard Shortcuts

- **Ctrl+S**: Save current configuration/instructions
- **F5/Ctrl+R**: Refresh installations list
- **Tab**: Navigate between fields in form mode
- **Ctrl+Q**: Quit application

## Configuration Storage

### Registry Files
```yaml
# ~/.claude-mpm/registry/{uuid}.yaml
project_id: "unique-uuid"
project_path: "/path/to/project"
project_name: "My Project"
metadata:
  created_at: "2024-01-01T00:00:00Z"
  last_accessed: "2024-01-01T00:00:00Z"
  access_count: 5
git:
  is_repo: true
  branch: "main"
  remote_url: "https://github.com/user/repo"
```

### Project Configuration
```yaml
# .claude-mpm/config.yaml
project:
  name: "Project Name"
  type: "python"
  description: "Project description"
agents:
  registry_path: ".claude/agents/"
  deployed: ["engineer", "qa", "pm"]
  auto_deploy: true
memory:
  provider: "sqlite"
  database_path: ".claude-mpm/memory/knowledge.db"
  size_limit_mb: 100.0
```

## Future Enhancements

1. **Memory Visualization**: Show agent memory usage and contents
2. **Ticket Management**: Integrate ticket viewing/editing
3. **Log Streaming**: Real-time log viewing with filtering
4. **Project Templates**: Pre-configured project setups
5. **Bulk Operations**: Apply changes to multiple projects
6. **Search/Filter**: Find projects by name, type, or metadata
7. **Export/Import**: Configuration backup and sharing

## Testing Checklist

- [x] Registry discovers all projects
- [x] Form editor generates fields from YAML
- [x] Form/YAML toggle preserves data
- [x] Agent installation dialog works
- [x] Agent import from file works
- [x] Configuration saves correctly
- [x] Instructions editor loads/saves
- [x] Project selection updates all views
- [x] Keyboard shortcuts function
- [x] Error handling shows appropriate messages

## Architecture Benefits

1. **Separation of Concerns**: Each component has a single responsibility
2. **Reusability**: Widgets can be used in other screens
3. **Extensibility**: Easy to add new field types or agents
4. **Maintainability**: Clear structure and documentation
5. **User Experience**: Intuitive interface with visual feedback