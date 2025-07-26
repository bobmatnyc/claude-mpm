# Documentation Cleanup Summary

## Changes Made

This document summarizes the documentation cleanup performed to remove references to the obsolete `framework/` directory structure.

## Updated Files

### 1. `/docs/STRUCTURE.md`
- **Removed**: References to `framework/` directory and `framework/agent-roles/` subdirectory
- **Updated**: Agent templates now correctly shown as JSON files in `src/claude_mpm/agents/templates/`
- **Changed**: Documentation now states that agent templates use JSON format (not Markdown)

### 2. `/docs/developer/STRUCTURE.md`
- **Removed**: References to `framework/` directory and `framework/agent-roles/` subdirectory  
- **Updated**: Agent templates now correctly shown as JSON files in `src/claude_mpm/agents/templates/`
- **Changed**: Documentation now states that agent templates use JSON format (not Markdown)

### 3. `/docs/developer/06-internals/migrations/path_resolver_migration.md`
- **Updated**: Example code that referenced `framework/agent-roles` now shows the correct path `agents/templates`
- **Changed**: Function name from `_get_framework_agent_roles_dir()` to `_get_agent_templates_dir()`

## Current Structure

The current agent system structure is:

```
src/claude_mpm/
└── agents/
    └── templates/              # Agent templates (JSON format)
        ├── documentation_agent.json
        ├── engineer_agent.json
        ├── qa_agent.json
        ├── research_agent.json
        ├── security_agent.json
        └── ...                 # Other agent templates
```

## Migration Summary

- **Old Structure**: `framework/agent-roles/*.md` (Markdown agent definitions)
- **New Structure**: `src/claude_mpm/agents/templates/*.json` (JSON agent templates)

All agent templates are now:
1. Located in the standard Python package structure under `src/`
2. Stored as JSON files for better programmatic access
3. Dynamically discovered and loaded by the agent registry

## Files Not Updated

The following archived documentation files were found to contain references to the framework directory but were not updated as they are historical records:
- `/docs/developer/archive/developer/framework_generator_agent_loader_analysis.md`
- `/docs/developer/archive/developer/STRUCTURE.md`

These archived files preserve the historical context and should not be modified.