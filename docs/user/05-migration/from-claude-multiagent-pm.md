# Differences from claude-multiagent-pm

This document explains the key differences between Claude MPM and its predecessor, claude-multiagent-pm.

## Overview

Claude MPM is a fork and evolution of claude-multiagent-pm that fundamentally changes how Claude is orchestrated. While claude-multiagent-pm relies on CLAUDE.md file configuration within Claude's environment, Claude MPM takes a **subprocess orchestration approach** where Claude runs as a managed child process.

## Key Architectural Differences

### 1. Context Loading Method

| Aspect | claude-multiagent-pm | Claude MPM |
|--------|---------------------|------------|
| **Context Method** | CLAUDE.md file in project | Subprocess with injected prompts |
| **Claude Awareness** | Claude reads CLAUDE.md directly | Claude receives instructions via stdin |
| **Control Level** | Limited to file content | Full process control |
| **Flexibility** | Static until file updated | Dynamic injection possible |

### 2. Orchestration Model

**claude-multiagent-pm:**
- Relies on Claude's built-in file reading
- Framework instructions in CLAUDE.md
- Claude manages its own context
- No external process control

**Claude MPM:**
- Launches Claude as subprocess
- Injects framework instructions programmatically
- Full control over I/O streams
- Can intercept and modify all communication

### 3. Feature Comparison

| Feature | claude-multiagent-pm | Claude MPM |
|---------|---------------------|------------|
| **Agent System** | ✅ Via CLAUDE.md | ✅ Via subprocess injection |
| **Ticket Extraction** | ❌ Manual | ✅ Automatic pattern detection |
| **Session Logging** | ❌ | ✅ Comprehensive logging |
| **Process Control** | ❌ | ✅ Full subprocess management |
| **Dynamic Context** | ❌ | ✅ Runtime injection |
| **Error Recovery** | Limited | ✅ Process-level recovery |
| **Memory Protection** | ❌ | ✅ Real-time monitoring |

### 4. Agent Integration

Both projects share the same agent system, but differ in how agents are invoked:

**claude-multiagent-pm:**
```markdown
# CLAUDE.md contains agent definitions
# Claude reads and follows instructions
# No external monitoring of delegations
```

**Claude MPM:**
```python
# Subprocess orchestrator injects instructions
# Monitors output for delegation patterns
# Can intercept and log all agent interactions
# Automatic ticket creation from patterns
```

## Migration Guide

### For Users

If you're coming from claude-multiagent-pm:

1. **Installation is different:**
   ```bash
   # Old way: npm install claude-multiagent-pm
   # New way: 
   git clone https://github.com/yourusername/claude-mpm.git
   cd claude-mpm
   ./install_dev.sh
   ```

2. **No CLAUDE.md needed in your project:**
   - Framework instructions are injected automatically
   - Your project stays clean
   - No framework files to maintain

3. **New features available:**
   - Automatic ticket extraction
   - Session logging
   - Better error handling
   - Process control

### For Developers

Key changes to understand:

1. **Subprocess Architecture:**
   ```python
   # Claude runs as a child process
   process = subprocess.Popen(["claude"], ...)
   
   # Full control over communication
   process.stdin.write(framework_instructions + user_input)
   output = process.stdout.read()
   ```

2. **Pattern Detection:**
   - Output is monitored in real-time
   - Patterns trigger actions (tickets, delegation)
   - Everything is logged

3. **Framework Loading:**
   - Still uses the same agent definitions
   - But injected via subprocess, not file reading
   - More dynamic and flexible

## Benefits of Subprocess Approach

### 1. Enhanced Control
- Start/stop Claude programmatically
- Intercept all communication
- Modify behavior at runtime

### 2. Better Integration
- Works with any Claude installation
- No project file pollution
- Cleaner git repositories

### 3. Advanced Features
- Real-time pattern detection
- Automatic ticket creation
- Comprehensive logging
- Memory protection

### 4. Improved Reliability
- Process-level error handling
- Automatic recovery
- Resource management

## When to Use Which

### Use claude-multiagent-pm when:
- You want simple file-based configuration
- You're already using CLAUDE.md extensively
- You don't need subprocess features
- You prefer minimal tooling

### Use Claude MPM when:
- You want automatic ticket extraction
- You need session logging
- You want process-level control
- You need dynamic context injection
- You want cleaner project directories

## Compatibility

### Agent Compatibility
Claude MPM maintains full compatibility with claude-multiagent-pm agents:
- Same agent template format
- Same specialization system
- Same delegation patterns

### Framework Compatibility
- Can read existing INSTRUCTIONS.md or CLAUDE.md
- Supports the same agent hierarchy
- Uses the same discovery mechanisms

### What's Not Compatible
- Installation method (different)
- Runtime behavior (subprocess vs file)
- Configuration approach (programmatic vs static)

## Summary

Claude MPM represents an evolution in Claude orchestration, moving from static file-based configuration to dynamic subprocess management. This enables powerful new features while maintaining the core multi-agent concepts that make the framework valuable.

The subprocess approach provides more control, better integration, and advanced features that weren't possible with file-based configuration alone. However, both approaches have their place, and the choice depends on your specific needs and preferences.