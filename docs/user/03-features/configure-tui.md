# Configuration Terminal Interface

Claude MPM provides two configuration interface modes for managing agents, templates, and behavior files:

1. **Textual Full-Screen TUI** - Modern, windowed interface (recommended)
2. **Rich Menu Interface** - Classic menu-based navigation (fallback)

## Launching the Configuration Interface

```bash
# Auto-detect and use best available interface
claude-mpm configure

# Force Rich menu interface
claude-mpm configure --force-rich

# Disable Textual TUI
claude-mpm configure --no-textual

# Jump directly to specific screens
claude-mpm configure --agents      # Agent management
claude-mpm configure --templates   # Template editing
claude-mpm configure --behaviors   # Behavior files
claude-mpm configure --settings    # Settings and version info
```

## Textual Full-Screen TUI

The modern Textual-based interface provides a professional, full-screen terminal experience with:

### Features
- **Full-screen windowed interface** with responsive layout
- **Mouse support** - Click on UI elements
- **Keyboard navigation** - Tab, arrows, and shortcuts
- **Live search/filtering** for agents
- **Modal dialogs** for confirmations
- **Professional dark theme** with CSS styling
- **Smooth animations** and transitions

### Interface Layout

```
┌─────────────────────────────────────────────────────────┐
│ Claude MPM Configuration v4.1.5         [Clock] [Status] │
├──────────────┬──────────────────────────────────────────┤
│ Navigation   │                                          │
│              │         Main Content Area                │
│ 🤖 Agents    │                                          │
│ 📝 Templates │    (Changes based on selection)         │
│ 📁 Behaviors │                                          │
│ ⚙️ Settings  │                                          │
│              │                                          │
├──────────────┴──────────────────────────────────────────┤
│ [^A] Agents [^T] Templates [^B] Behaviors [^Q] Quit     │
└─────────────────────────────────────────────────────────┘
```

### Screens

#### 1. Agent Management Screen
- **DataTable** showing all discovered agents
- **Status indicators** (✓ Enabled / ✗ Disabled)
- **Live search** to filter agents
- **Bulk actions** (Enable All / Disable All)
- **Click or Enter** to toggle agent state

#### 2. Template Editing Screen
- **Split view** with template list and viewer
- **Syntax highlighting** for JSON
- **Edit capabilities** for custom templates
- **Create copies** of system templates
- **Reset** custom templates to defaults

#### 3. Behavior Files Screen
- **Tree view** of behavior files
- **YAML editor** with syntax highlighting
- **Save/Import/Export** functionality
- **Identity and workflow** configuration

#### 4. Settings Screen
- **Scope management** (project/user)
- **Version information** display
- **Configuration export/import**
- **System information**

### Keyboard Shortcuts

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+A` | Navigate to Agents | Jump to Agent Management |
| `Ctrl+T` | Navigate to Templates | Jump to Template Editing |
| `Ctrl+B` | Navigate to Behaviors | Jump to Behavior Files |
| `Ctrl+S` | Navigate to Settings | Jump to Settings |
| `Ctrl+Q` | Quit | Exit the interface |
| `Tab` | Next Element | Move to next UI element |
| `Shift+Tab` | Previous Element | Move to previous UI element |
| `Enter` | Select/Activate | Activate current element |
| `Arrow Keys` | Navigate | Move within lists/tables |
| `F1` | Help | Show keyboard shortcuts |

### Mouse Support
- **Click** on navigation items to switch screens
- **Click** on table rows to select
- **Click** on buttons to activate
- **Scroll** in scrollable areas

## Rich Menu Interface (Fallback)

The classic Rich-based interface provides menu-driven navigation when:
- Terminal doesn't support full-screen mode
- Textual is not installed
- User prefers menu navigation
- Running with `--force-rich` flag

### Features
- Terminal-based menu navigation
- Colored output with Rich formatting
- Tables and panels for data display
- Interactive prompts for user input
- Works in any terminal

### Menu Structure

```
═══════════════════════════════════════════
    Claude MPM Configuration Interface
═══════════════════════════════════════════
Scope: PROJECT | Directory: /current/path

Main Menu:
[1] Agent Management     Enable/disable agents
[2] Template Editing     Edit agent templates
[3] Behavior Files       Manage configs
[4] Switch Scope         Current: project
[5] Version Info         Display versions
[q] Quit                 Exit interface

Select an option [q]: _
```

## Non-Interactive Commands

For scripting and automation, use non-interactive flags:

```bash
# List all agents (JSON output)
claude-mpm configure --list-agents

# Enable/disable specific agents
claude-mpm configure --enable-agent engineer
claude-mpm configure --disable-agent research

# Export/import configuration
claude-mpm configure --export-config config.json
claude-mpm configure --import-config config.json

# Show version information
claude-mpm configure --version-info
```

## Configuration Scopes

Claude MPM supports two configuration scopes:

### Project Scope (default)
- Configuration stored in `.claude-mpm/` in project directory
- Settings specific to current project
- Isolated from other projects

### User Scope
- Configuration stored in `~/.claude-mpm/`
- Global settings for all projects
- Shared across projects

Switch scopes:
```bash
# Use project scope (default)
claude-mpm configure --scope project

# Use user scope
claude-mpm configure --scope user
```

## Terminal Requirements

### For Textual TUI
- **Terminal**: Not `dumb` terminal
- **TTY**: Both stdin and stdout must be TTY
- **Size**: Minimum 80x24 characters
- **Support**: Most modern terminals (iTerm2, Terminal.app, Alacritty, Windows Terminal, etc.)

### For Rich Menu
- Any terminal with basic color support
- Works over SSH and in containers

## Installation

The Textual TUI is included with claude-mpm installation:

```bash
# Install claude-mpm with TUI support
pip install claude-mpm

# Or upgrade existing installation
pip install --upgrade claude-mpm
```

## Troubleshooting

### TUI doesn't launch
1. Check terminal support: `echo $TERM`
2. Verify TTY: `tty`
3. Check size: `stty size`
4. Try forcing Rich: `claude-mpm configure --force-rich`

### Display issues
1. Ensure terminal supports Unicode
2. Try different terminal emulator
3. Use `--no-colors` for plain text

### Performance
1. Textual TUI is optimized for local use
2. Over SSH, consider using `--force-rich`
3. In containers, may need to set `TERM=xterm-256color`

## Examples

### Quick Agent Enable
```bash
# Interactive with direct navigation
claude-mpm configure --agents

# Non-interactive
claude-mpm configure --enable-agent engineer
```

### Template Customization
```bash
# Jump to template editing
claude-mpm configure --templates

# Will create custom copy and open editor
```

### Check Configuration
```bash
# View all settings and versions
claude-mpm configure --settings

# Export current configuration
claude-mpm configure --export-config my-config.json
```

## Best Practices

1. **Use Textual TUI** for interactive configuration management
2. **Use non-interactive flags** for scripting and CI/CD
3. **Export configurations** before major changes
4. **Use project scope** for project-specific settings
5. **Use user scope** for personal preferences

## Related Documentation

- [Agent Management](../02-guides/agent-management.md)
- [Template Customization](../02-guides/template-customization.md)
- [Behavior Files](../02-guides/behavior-files.md)
- [CLI Reference](../04-reference/cli.md)