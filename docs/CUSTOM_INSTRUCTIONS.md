# Custom Instructions with .claude-mpm Directory

## Overview

Claude MPM supports custom instructions through `.claude-mpm/` directories, allowing you to override or extend the framework's default behavior at both user and project levels. The framework **never** reads from `.claude/` directories to avoid conflicts with Claude Code's native configuration.

## Directory Structure

```
project/
├── .claude-mpm/                 # Project-level customizations
│   ├── INSTRUCTIONS.md          # Custom PM instructions
│   ├── WORKFLOW.md              # Custom workflow phases
│   ├── MEMORY.md                # Custom memory rules
│   └── memories/
│       ├── PM_memories.md       # PM's accumulated memories
│       └── [agent]_memories.md  # Agent-specific memories
└── .claude/                      # IGNORED - Claude Code's directory
    └── (any files here are ignored by Claude MPM)

~/.claude-mpm/                    # User-level customizations
├── INSTRUCTIONS.md               # User's default PM instructions
├── WORKFLOW.md                   # User's default workflow
├── MEMORY.md                     # User's default memory rules
└── memories/
    ├── PM_memories.md            # User's global PM memories
    └── [agent]_memories.md      # User's global agent memories
```

## File Loading Precedence

The framework loads files in the following order (highest priority first):

### INSTRUCTIONS.md
1. **Project**: `./.claude-mpm/INSTRUCTIONS.md` (overrides all)
2. **User**: `~/.claude-mpm/INSTRUCTIONS.md` (overrides system)
3. **System**: Built-in framework instructions (default)

### WORKFLOW.md
1. **Project**: `./.claude-mpm/WORKFLOW.md` (overrides all)
2. **User**: `~/.claude-mpm/WORKFLOW.md` (overrides system)
3. **System**: `src/claude_mpm/agents/WORKFLOW.md` (default)

### MEMORY.md
1. **Project**: `./.claude-mpm/MEMORY.md` (overrides all)
2. **User**: `~/.claude-mpm/MEMORY.md` (overrides system)
3. **System**: `src/claude_mpm/agents/MEMORY.md` (default)

### Actual Memories
- **User memories**: `~/.claude-mpm/memories/PM_memories.md` (loaded first)
- **Project memories**: `./.claude-mpm/memories/PM_memories.md` (merged/overrides user)
- **Agent memories**: Only loaded if the agent is deployed in `.claude/agents/`

## Creating Custom Instructions

### Project-Specific Instructions

Create a `.claude-mpm/` directory in your project root:

```bash
mkdir -p .claude-mpm/memories
```

Add custom instructions:

```markdown
# .claude-mpm/INSTRUCTIONS.md
# Custom Project PM Instructions

## Project Rules
- Always prioritize security
- Use TypeScript for new code
- Follow TDD practices

## Custom Delegation
- Security reviews go to Security agent first
- API changes require Documentation updates
```

### User-Level Instructions

Create a `.claude-mpm/` directory in your home folder:

```bash
mkdir -p ~/.claude-mpm/memories
```

Add your personal defaults that apply to all projects:

```markdown
# ~/.claude-mpm/INSTRUCTIONS.md
# My Personal PM Instructions

## My Preferences
- Always create comprehensive tests
- Prefer functional programming
- Document all decisions
```

## Memory Management

### PM Memories

Store accumulated project knowledge:

```markdown
# .claude-mpm/memories/PM_memories.md
# Project Manager Memories

## Project Context
- Using PostgreSQL for database
- API requires JWT authentication
- Performance target: <100ms response

## Technical Decisions
- Chose React for frontend
- Using GitHub Actions for CI/CD
```

### Agent Memories

Store agent-specific memories (only loaded if agent is deployed):

```markdown
# .claude-mpm/memories/engineer_memories.md
# Engineer Agent Memories

## Code Patterns
- Use dependency injection
- Implement repository pattern
- Follow SOLID principles
```

## Important Notes

### Security Considerations

1. **`.claude/` is NEVER read**: The framework completely ignores `.claude/` directories to avoid conflicts with Claude Code
2. **Clear labeling**: Custom instructions are clearly labeled with their source level (project/user) in the output
3. **No duplication**: The framework doesn't load CLAUDE.md files since Claude Code already reads them

### Best Practices

1. **Project-specific overrides**: Use project-level files for project-specific requirements
2. **User defaults**: Use user-level files for your personal preferences across all projects
3. **Keep it focused**: Don't duplicate system instructions; only add what's different
4. **Version control**: Include `.claude-mpm/` in version control for team consistency
5. **Document decisions**: Use memories to track important project decisions

### Debugging

To verify what's being loaded:

```python
from claude_mpm.core.framework_loader import FrameworkLoader

loader = FrameworkLoader()
content = loader.framework_content

print(f"Custom instructions: {content.get('custom_instructions_level', 'none')}")
print(f"Workflow level: {content.get('workflow_instructions_level', 'system')}")
print(f"Memory level: {content.get('memory_instructions_level', 'system')}")
```

## Examples

See `examples/claude_mpm_custom_instructions.py` for a complete working example.

## Migration from .claude

If you have existing customizations in `.claude/`:

1. Copy relevant files to `.claude-mpm/`
2. Rename if needed (e.g., `CLAUDE.md` → `INSTRUCTIONS.md`)
3. Remove Claude MPM-specific content from `.claude/` (keep only Claude Code config)
4. Test to ensure proper loading

## Troubleshooting

### Custom Instructions Not Loading

1. Check file paths are correct
2. Ensure `.claude-mpm/` (not `.claude/`) directory is used
3. Verify file names are exactly `INSTRUCTIONS.md`, `WORKFLOW.md`, `MEMORY.md`
4. Check logs for loading messages

### Precedence Issues

- Project files ALWAYS override user files
- User files ALWAYS override system defaults
- Use logging to see which level is being loaded

### Memory Not Loading

- Agent memories only load if agent is deployed in `.claude/agents/`
- Check agent names match exactly (including underscores/hyphens)
- Ensure memory files end with `_memories.md`