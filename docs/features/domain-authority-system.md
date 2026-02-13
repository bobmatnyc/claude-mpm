# Domain Authority System

## Overview

The Domain Authority System is a core feature that provides intelligent agent and tool discovery for Claude MPM. It automatically generates context-aware documentation about available agents and tools, making them discoverable to the PM agent during task delegation.

## Key Components

### 1. Setup Registry Service

**File**: `src/claude_mpm/services/setup_registry.py`

The Setup Registry tracks all configured MCP servers and CLI tools in a centralized registry.

**Registry Location**: `~/.claude-mpm/setup-registry.json`

**Tracked Information**:
- Service name and type (MCP or CLI)
- Setup date and version
- Available tools/commands
- CLI help text
- Configuration location (user or project)

**Example Registry Entry**:
```json
{
  "services": {
    "gworkspace-mcp": {
      "type": "mcp",
      "version": "1.2.3",
      "setup_date": "2026-02-13T10:30:00-05:00",
      "tools": ["list_calendars", "create_event", "search_gmail_messages"],
      "cli_help": "Google Workspace MCP server...",
      "config_location": "user"
    }
  }
}
```

**API Methods**:
- `add_service()` - Register a new service
- `remove_service()` - Unregister a service
- `get_service()` - Get service details
- `list_services()` - List all services (optionally filtered by type)
- `get_all_tools()` - Get all tools grouped by service
- `get_services_with_details()` - Get full service registry

### 2. Dynamic Skills Generator

**File**: `src/claude_mpm/services/dynamic_skills_generator.py`

The Dynamic Skills Generator creates two special skills that PM uses for agent and tool selection:

**Generated Skills**:
1. **mpm-select-agents.md** - Lists all available agents with capabilities
2. **mpm-select-tools.md** - Lists all configured MCP/CLI tools with help text

**Skills Location**: `~/.claude-mpm/skills/dynamic/`

**Generation Trigger**: Runs automatically during Claude MPM startup

#### mpm-select-agents.md

Generated from `AgentCapabilitiesService.get_all_agents()`:

**Content Structure**:
```markdown
---
name: mpm-select-agents
description: Agent selection guide for PM delegation
version: 1.0.0
auto_generated: true
generated_at: 2026-02-13T10:30:00-05:00
when_to_use: When PM needs to select an agent for delegation
---

# Agent Selection Guide

## Available Agents

### Python Engineer
- **ID**: `engineer-python`
- **Type**: language-specialist
- **Location**: system
- **Description**: Python development and implementation
- **Capabilities**:
  - Python code writing
  - FastAPI/Django/Flask development
  - Package management
  - Testing with pytest

### Research Agent
- **ID**: `research`
- **Type**: investigation
- **Location**: system
- **Description**: Codebase analysis and investigation
- **Capabilities**:
  - Code pattern discovery
  - Architecture analysis
  - Technology assessment

## Selection Guidelines

- **Research**: Codebase analysis, investigation, understanding
- **Engineer**: Implementation, code writing, refactoring
- **QA**: Testing, verification, quality assurance
- **Ops**: Deployment, infrastructure, operations
- **Documentation**: Writing docs, guides, technical specifications
```

#### mpm-select-tools.md

Generated from `SetupRegistry.get_services_with_details()`:

**Content Structure**:
```markdown
---
name: mpm-select-tools
description: MCP and CLI tool selection guide
version: 1.0.0
auto_generated: true
generated_at: 2026-02-13T10:30:00-05:00
when_to_use: When PM needs to select an MCP tool or CLI command
---

# Tool Selection Guide

## MCP Tools

### gworkspace-mcp
- **Setup Date**: 2026-02-13T10:30:00-05:00
- **Version**: 1.2.3
- **Location**: user
- **Available Tools**:
  - `list_calendars`
  - `create_event`
  - `search_gmail_messages`
  - `get_gmail_message_content`
  - `search_drive_files`

**CLI Help**:
```
Google Workspace MCP server providing Gmail, Calendar, Drive, and Tasks integration
```

## CLI Tools

### claude-mpm
- **Setup Date**: 2026-02-13T10:30:00-05:00
- **Version**: 5.7.34

**Help**:
```
claude-mpm [OPTIONS] COMMAND [ARGS]...

Commands:
  agents      Manage agents
  skills      Manage skills
  setup       Configure MCP services
  ...
```
```

### 3. Startup Integration

**File**: `src/claude_mpm/cli/startup.py`

The Dynamic Skills Generator runs automatically during startup:

**Startup Sequence**:
1. Claude MPM CLI starts
2. `startup.py` initializes services
3. `DynamicSkillsGenerator.generate_all()` is called
4. Both `mpm-select-agents.md` and `mpm-select-tools.md` are regenerated
5. Skills are available for PM agent to use

**Why Startup Generation?**:
- Ensures skills are always current with latest agent/tool state
- No manual regeneration needed after installing new MCP servers
- Low overhead (milliseconds to generate)
- Skills automatically reflect changes in agent deployment

### 4. PM Agent Usage

**How PM Uses These Skills**:

When PM needs to delegate a task or select a tool:

1. **Agent Selection**:
   - PM reads `mpm-select-agents.md` to see available agents
   - Matches task requirements to agent capabilities
   - Selects appropriate agent for delegation

2. **Tool Selection**:
   - PM reads `mpm-select-tools.md` to see available MCP tools
   - Identifies tools that can solve the current problem
   - Uses tools directly or delegates to agent with tool access

**Example PM Workflow**:

```
User: "Search my Gmail for the latest invoice"

PM thinks:
1. Consults mpm-select-tools.md
2. Finds gworkspace-mcp with search_gmail_messages tool
3. Uses search_gmail_messages directly or delegates to agent
```

```
User: "Implement user authentication in Python"

PM thinks:
1. Consults mpm-select-agents.md
2. Finds Python Engineer agent with authentication capabilities
3. Delegates task to Python Engineer
```

## Benefits

### 1. Automatic Discovery
- No manual configuration of agent/tool lists
- Always up-to-date with current deployment state
- New agents/tools immediately discoverable

### 2. Context Efficiency
- Skills only loaded when PM needs them
- Progressive disclosure keeps context lean
- Generated content is concise and structured

### 3. Intelligent Routing
- PM makes informed delegation decisions
- Reduces trial-and-error in agent selection
- Improves task completion efficiency

### 4. Extensibility
- New agents automatically appear in mpm-select-agents.md
- New MCP servers automatically appear in mpm-select-tools.md
- Custom agents and tools seamlessly integrated

## Usage

### For Users

**No manual steps required!** The domain authority system works automatically.

**Verifying It's Working**:

```bash
# Check that dynamic skills are generated
ls ~/.claude-mpm/skills/dynamic/

# Expected output:
# mpm-select-agents.md
# mpm-select-tools.md

# View agent skill
cat ~/.claude-mpm/skills/dynamic/mpm-select-agents.md

# View tool skill
cat ~/.claude-mpm/skills/dynamic/mpm-select-tools.md
```

### For Developers

**Extending the System**:

```python
from claude_mpm.services.setup_registry import SetupRegistry
from claude_mpm.services.dynamic_skills_generator import DynamicSkillsGenerator

# Register a new MCP service
registry = SetupRegistry()
registry.add_service(
    name="my-custom-mcp",
    service_type="mcp",
    version="1.0.0",
    tools=["tool1", "tool2"],
    cli_help="My custom MCP server",
    config_location="user"
)

# Regenerate skills
generator = DynamicSkillsGenerator()
generator.generate_all()
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Claude MPM Startup                    │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              DynamicSkillsGenerator                      │
│                  .generate_all()                         │
└──────────┬────────────────────────────┬─────────────────┘
           │                            │
           ▼                            ▼
┌──────────────────────┐    ┌──────────────────────────┐
│ AgentCapabilitiesService│  │   SetupRegistry          │
│  .get_all_agents()   │    │ .get_services_with_details()│
└──────────┬───────────┘    └──────────┬───────────────┘
           │                            │
           │                            │
           ▼                            ▼
┌──────────────────────┐    ┌──────────────────────────┐
│ mpm-select-agents.md │    │ mpm-select-tools.md      │
│ (~/.claude-mpm/      │    │ (~/.claude-mpm/          │
│  skills/dynamic/)    │    │  skills/dynamic/)        │
└──────────┬───────────┘    └──────────┬───────────────┘
           │                            │
           └────────────┬───────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │     PM Agent          │
            │ - Reads skills        │
            │ - Selects agents      │
            │ - Uses tools          │
            │ - Delegates tasks     │
            └───────────────────────┘
```

## Technical Details

### Agent Discovery

Agents are discovered from three tiers (priority order):
1. **Project-level**: `.claude/agents/` (highest priority)
2. **User-level**: `~/.config/claude/agents/`
3. **System-level**: `~/.claude/agents/` (lowest priority)

**Data Source**: `AgentCapabilitiesService.get_all_agents()`

### Tool Discovery

Tools are discovered from Setup Registry which tracks:
- **MCP servers**: Configured in `.mcp.json` or `~/.claude.json`
- **CLI tools**: Registered during setup commands

**Data Source**: `SetupRegistry.get_services_with_details()`

### Skill Format

Generated skills follow the standard skill format:
- YAML frontmatter with metadata
- Markdown body with structured content
- Progressive disclosure sections (if applicable)

**Auto-generated marker**: `auto_generated: true` in frontmatter

### Thread Safety

Setup Registry uses thread-safe operations:
- Lock-based file access
- Atomic reads and writes
- Safe for concurrent access

## Future Enhancements

### Potential Improvements

1. **Tool Documentation Extraction**
   - Automatically extract MCP tool schemas
   - Include parameter descriptions in mpm-select-tools.md
   - Show usage examples for each tool

2. **Agent Performance Tracking**
   - Track which agents complete tasks successfully
   - Include success rates in mpm-select-agents.md
   - Recommend agents based on past performance

3. **Dynamic Priority**
   - Adjust agent/tool priority based on usage patterns
   - Promote frequently used agents/tools
   - Demote rarely used items

4. **Context-Aware Generation**
   - Generate skills specific to current project
   - Filter irrelevant agents/tools
   - Customize content based on project type

5. **Usage Analytics**
   - Track PM agent/tool selection patterns
   - Identify gaps in agent capabilities
   - Suggest new agents/tools to add

## Related Documentation

- [Skills Optimization](../user/skills-optimize.md) - Project-based skill recommendations
- [MCP-Skillset Integration](./mcp-skillset-integration.md) - RAG-powered skill recommendations
- [Agent Capabilities Service](../developer/services/agent-capabilities.md) - Agent discovery API
- [Setup Registry API](../developer/services/setup-registry.md) - Tool registration API

## Troubleshooting

### Skills Not Generated

**Symptom**: `~/.claude-mpm/skills/dynamic/` is empty

**Causes**:
1. Startup sequence not completing
2. Permission issues with directory

**Solution**:
```bash
# Manually trigger generation
python -c "
from claude_mpm.services.dynamic_skills_generator import DynamicSkillsGenerator
gen = DynamicSkillsGenerator()
gen.generate_all()
print('Skills generated successfully')
"

# Check permissions
ls -la ~/.claude-mpm/skills/dynamic/
```

### Outdated Content

**Symptom**: Skills don't reflect recent agent/tool changes

**Cause**: Skills generated at previous startup

**Solution**:
```bash
# Restart Claude MPM to regenerate
claude-mpm --help

# Or manually regenerate
python -c "
from claude_mpm.services.dynamic_skills_generator import DynamicSkillsGenerator
gen = DynamicSkillsGenerator()
gen.generate_all()
"
```

### PM Not Using Skills

**Symptom**: PM doesn't seem aware of agents/tools

**Cause**: Skills not in skill search path

**Solution**:
```bash
# Verify skills are in expected location
ls ~/.claude-mpm/skills/dynamic/mpm-select-*.md

# Check Claude Code can access skills
claude-mpm skills list | grep mpm-select
```

## Summary

The Domain Authority System provides automatic, up-to-date documentation of available agents and tools, enabling the PM agent to make intelligent delegation and tool selection decisions. It runs automatically at startup, requires no user configuration, and seamlessly adapts to changes in agent deployment and tool installation.

**Key Files**:
- `src/claude_mpm/services/setup_registry.py` - Tool registry
- `src/claude_mpm/services/dynamic_skills_generator.py` - Skill generator
- `src/claude_mpm/cli/startup.py` - Startup integration
- `~/.claude-mpm/skills/dynamic/mpm-select-agents.md` - Generated agent skill
- `~/.claude-mpm/skills/dynamic/mpm-select-tools.md` - Generated tool skill
- `~/.claude-mpm/setup-registry.json` - Tool registry data
