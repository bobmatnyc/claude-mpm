# Output Style System Documentation

## Overview

The Output Style System provides version-aware handling of Claude MPM's output style configuration. It automatically detects the Claude Desktop version and either:
- **Deploys** the output style to `~/.claude/output-styles/` for Claude >= 1.0.83
- **Injects** the output style content into framework instructions for older versions

## Key Components

### 1. OutputStyleManager (`src/claude_mpm/core/output_style_manager.py`)

Handles all output style operations:
- Claude version detection
- Output style content extraction
- Deployment to Claude Desktop
- Content injection for older versions

### 2. OUTPUT_STYLE.md (`src/claude_mpm/agents/OUTPUT_STYLE.md`)

The master output style file containing:
- YAML frontmatter with name and description
- PM delegation requirements
- Communication standards
- TodoWrite formatting rules
- Response format specifications

### 3. Framework Loader Integration

The `FrameworkLoader` automatically:
- Initializes the `OutputStyleManager` on first use
- Extracts output style content from INSTRUCTIONS.md and BASE_PM.md
- Deploys or injects based on Claude version

## How It Works

### Version Detection

```python
# Runs: claude --version
# Parses output like: "Claude 1.0.83"
```

### Version-Based Behavior

#### Claude >= 1.0.83 (Output Style Support)

1. **Extraction**: Content is extracted from INSTRUCTIONS.md and BASE_PM.md
2. **Saving**: OUTPUT_STYLE.md is created in `src/claude_mpm/agents/`
3. **Deployment**: File is copied to `~/.claude/output-styles/claude-mpm.md`
4. **Activation**: If new, settings.json is updated to set as active style

```
~/.claude/
├── output-styles/
│   └── claude-mpm.md     # Deployed output style
└── settings.json          # Contains: "activeOutputStyle": "claude-mpm"
```

#### Claude < 1.0.83 (No Output Style Support)

1. **Extraction**: Same content extraction process
2. **Injection**: Content is injected into framework instructions
3. **Delivery**: Included in the PM instructions sent to Claude

The injected content appears as:
```markdown
## Output Style Configuration
**Note: The following output style is injected for Claude < 1.0.83**

[Output style content without YAML frontmatter]
```

## Output Style Content Structure

The OUTPUT_STYLE.md file follows this structure:

```markdown
---
name: Claude MPM
description: Multi-Agent Project Manager orchestration mode
---

## Primary Sections
1. Primary Directive - Mandatory delegation rules
2. Core Operating Rules - Default behaviors and restrictions
3. Communication Standards - Tone and language requirements
4. Error Handling Protocol - 3-attempt process
5. Standard Operating Procedure - Workflow steps
6. TodoWrite Requirements - Task formatting rules
7. Response Format - Structured output requirements
```

## Testing

### Manual Testing

```bash
# Test output style extraction and deployment
python scripts/test_output_style.py

# Test with simulated older Claude version
python scripts/test_output_style_old_version.py
```

### Automated Tests

```bash
# Run comprehensive test suite
python tests/test_output_style_system.py
```

## File Locations

| File | Purpose |
|------|---------|
| `src/claude_mpm/agents/OUTPUT_STYLE.md` | Master output style file |
| `src/claude_mpm/core/output_style_manager.py` | Output style management logic |
| `~/.claude/output-styles/claude-mpm.md` | Deployed output style (>= 1.0.83) |
| `~/.claude/settings.json` | Claude Desktop settings |

## Logging

The system provides INFO-level logging for:
- Claude version detection
- Output style deployment decisions
- File operations (copying, settings updates)
- Injection vs deployment path taken

Example log output:
```
INFO - Detected Claude version: 1.0.83
INFO - Output style deployed to Claude Desktop >= 1.0.83
INFO - Deployed output style to ~/.claude/output-styles/claude-mpm.md
INFO - Activated claude-mpm output style in settings
```

## Troubleshooting

### Claude Not Found

If Claude Desktop is not in PATH:
- System will fall back to injection mode
- Output style content will be included in framework instructions

### Version Detection Fails

If version parsing fails:
- System assumes older version
- Falls back to injection mode

### Deployment Issues

If deployment fails:
- Check write permissions for `~/.claude/` directory
- Verify `~/.claude/output-styles/` directory can be created
- Check logs for specific error messages

## Benefits

1. **Automatic Version Handling**: No manual configuration needed
2. **Backward Compatibility**: Works with all Claude versions
3. **Clean Separation**: Output style logic separated from framework
4. **Maintainability**: Single source of truth in OUTPUT_STYLE.md
5. **User Experience**: Seamless experience regardless of Claude version

## Future Enhancements

- Support for multiple output style variants
- User-configurable style selection
- Project-specific output style overrides
- Output style versioning and migration