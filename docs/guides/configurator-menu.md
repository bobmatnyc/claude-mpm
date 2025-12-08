# Claude MPM Configurator - User Guide

## Arrow-Key Navigation (New in v5.0.2)

The Claude MPM configurator now supports intuitive arrow-key navigation! No more guessing which letter to type.

---

## How to Use

### Starting the Configurator

```bash
claude-mpm configure
```

### Navigation Controls

| Key | Action |
|-----|--------|
| **↑ / ↓** | Navigate up/down through menu options |
| **Enter** | Select highlighted option |
| **Ctrl+C** | Cancel and go back to previous menu |

---

## Main Menu

When you start the configurator, you'll see:

```
? Main Menu:
❯ Agent Management
  Skills Management
  Template Editing
  Behavior Files
  Startup Configuration
  Switch Scope (Current: project)
  Version Info
  ────────────────────────────────────────
  Save & Launch Claude MPM
  Quit
```

### Options Explained

1. **Agent Management**: Enable/disable agents, deploy from repositories
2. **Skills Management**: Configure which skills are available to agents
3. **Template Editing**: Customize agent behavior templates
4. **Behavior Files**: Manage identity and workflow configurations
5. **Startup Configuration**: Choose which services start automatically
6. **Switch Scope**: Toggle between project and user-level settings
7. **Version Info**: Display version information
8. **Save & Launch**: Save all changes and start Claude MPM
9. **Quit**: Exit without launching

---

## Agent Management Menu

When you select "Agent Management", you'll see:

```
? Agent Management:
❯ Manage sources (add/remove repositories)
  Deploy agents (individual selection)
  Deploy preset (predefined sets)
  Remove agents
  View agent details
  Toggle agents (legacy enable/disable)
  ────────────────────────────────────────
  ← Back to main menu
```

### Options Explained

1. **Manage sources**: Add/remove agent repositories
2. **Deploy agents**: Choose individual agents to deploy
3. **Deploy preset**: Deploy predefined agent sets
4. **Remove agents**: Remove deployed agents
5. **View agent details**: See information about agents
6. **Toggle agents**: Enable/disable agents (legacy feature)

---

## Tips

### Quick Navigation

- **Use arrow keys** instead of typing letters
- **Press Enter** when the option you want is highlighted
- **Press Ctrl+C** to cancel or go back

### Visual Feedback

- The **❯** pointer shows your current selection
- Highlighted text indicates what will be selected
- Separators (────) group related options

### Accessibility

The menu system is designed to be:
- **Keyboard-friendly**: No mouse required
- **Screen-reader compatible**: Works with terminal screen readers
- **Color-blind safe**: Uses bold text in addition to color

---

## Troubleshooting

### Menu doesn't appear

If you see errors about missing `questionary`:

```bash
# Reinstall dependencies
pip install -e .
```

### Arrow keys don't work

- **Windows**: Use Windows Terminal or WSL (not Command Prompt)
- **macOS/Linux**: Should work in all standard terminals
- **SSH sessions**: Ensure terminal supports ANSI escape codes

### Still showing old menu

If you see the old letter-based menu:

```bash
# Check your version
claude-mpm --version

# Should be v5.0.2 or higher
# If not, update:
pip install --upgrade claude-mpm
```

---

## Comparison: Old vs New

### Old Menu (Before v5.0.2)

```
Agent Management Options:
  [s] Manage sources (add/remove repositories)
  [d] Deploy agents (individual selection)
  [p] Deploy preset (predefined sets)
  [r] Remove agents
  [v] View agent details
  [t] Toggle agents (legacy enable/disable)
  [b] Back to main menu

Select option: _
```

❌ Problems:
- Had to type single letters
- Easy to make typos
- Not obvious what to do

### New Menu (v5.0.2+)

```
? Agent Management:
❯ Manage sources (add/remove repositories)
  Deploy agents (individual selection)
  Deploy preset (predefined sets)
  Remove agents
  View agent details
  Toggle agents (legacy enable/disable)
  ────────────────────────────────────────
  ← Back to main menu
```

✅ Benefits:
- Arrow keys navigate
- Visual pointer
- Clear options
- Industry-standard UX

---

## Advanced Usage

### Non-Interactive Mode

The configurator still supports CLI flags for scripting:

```bash
# List agents (non-interactive)
claude-mpm configure --list-agents

# Enable an agent (non-interactive)
claude-mpm configure --enable-agent my-agent

# Export configuration
claude-mpm configure --export-config config.json
```

### Direct Navigation

Jump directly to specific sections:

```bash
# Open agent management
claude-mpm configure --agents

# Open template editor
claude-mpm configure --templates

# Open behavior management
claude-mpm configure --behaviors

# Open startup configuration
claude-mpm configure --startup
```

---

## Keyboard Shortcuts Summary

| Action | Key |
|--------|-----|
| Navigate up | ↑ |
| Navigate down | ↓ |
| Select option | Enter |
| Cancel/Go back | Ctrl+C |
| Quit configurator | Select "Quit" option |

---

## Getting Help

- **Documentation**: https://github.com/bobmatnyc/claude-mpm
- **Issues**: https://github.com/bobmatnyc/claude-mpm/issues
- **Version info**: `claude-mpm --version`

---

*Last updated: 2025-12-02*
*Claude MPM v5.0.2+*
