# Why Claude MPM Can't Be a Plugin

## Executive Summary

Claude MPM cannot be distributed as a Claude Code plugin due to a fundamental architectural incompatibility. MPM must inject PM_INSTRUCTIONS **before** Claude Code starts, but plugins execute **after** Claude Code initializes. This document explains the technical reasons and architectural constraints.

## The Problem

### MPM's Core Architecture Requirement

Claude MPM operates as a **wrapper** around Claude Code, injecting system instructions before the CLI initializes:

```
┌─────────────────────────────────────────────┐
│  User runs: claude-mpm                      │
└─────────────────┬───────────────────────────┘
                  │
                  v
┌─────────────────────────────────────────────┐
│  MPM Wrapper Process                        │
│  • Loads agent configurations               │
│  • Injects PM_INSTRUCTIONS environment var  │
│  • Sets up hooks/commands/MCP               │
└─────────────────┬───────────────────────────┘
                  │
                  v
┌─────────────────────────────────────────────┐
│  subprocess.run(['claude', ...])            │
│  Claude Code starts WITH PM_INSTRUCTIONS    │
└─────────────────────────────────────────────┘
```

### Plugin Execution Timing

Claude Code plugins execute **inside** the Claude Code process **after** initialization:

```
┌─────────────────────────────────────────────┐
│  User runs: claude                          │
└─────────────────┬───────────────────────────┘
                  │
                  v
┌─────────────────────────────────────────────┐
│  Claude Code Initializes                    │
│  • Loads configuration                      │
│  • Starts CLI interface                     │
│  • System instructions ALREADY processed    │
└─────────────────┬───────────────────────────┘
                  │
                  v
┌─────────────────────────────────────────────┐
│  Plugins Load (AFTER Claude Code starts)    │
│  • Too late to inject system instructions   │
│  • Can only add tools/hooks/commands        │
└─────────────────────────────────────────────┘
```

## Technical Details

### What PM_INSTRUCTIONS Does

The `PM_INSTRUCTIONS` environment variable contains:

1. **Agent System Instructions**: The complete Project Manager agent persona that orchestrates task delegation
2. **Multi-Agent Coordination**: Rules for when and how to delegate to specialized agents
3. **Context Management**: Session persistence, resume logs, and memory integration
4. **Behavioral Modifications**: How Claude should handle tasks, communicate, and make decisions

This must be available **before** Claude Code processes its first user input.

### Plugin Capabilities vs Requirements

| Requirement | Plugin Can Do? | Why/Why Not |
|------------|----------------|-------------|
| Inject system instructions | ❌ No | Too late - Claude already initialized |
| Add slash commands | ✅ Yes | Commands load after startup |
| Add custom hooks | ✅ Yes | Hooks integrate post-startup |
| Provide MCP services | ✅ Yes | MCP tools load dynamically |
| Modify Claude's core behavior | ❌ No | Requires pre-initialization setup |

### Why Timing Matters

Claude Code's initialization sequence:

1. **Parse CLI arguments** (happens first)
2. **Load system configuration** (including instructions)
3. **Initialize LLM session** (with baked-in instructions)
4. **Load plugins** (too late for #2 and #3)
5. **Start interactive session**

MPM needs to inject at step #2, but plugins load at step #4.

## Research Findings

From investigation of Claude Code v2.0.36:

### Plugin Architecture Discovery

1. **Plugin Location**: `~/.config/claude/plugins/`
2. **Plugin Format**: Directory structure with `plugin.json` manifest
3. **Execution Context**: Inside Claude Code process, post-initialization
4. **Capability Scope**: Tools, commands, hooks - NOT system instructions

### Key Quote from Research

> "Plugins run WITHIN Claude Code AFTER it starts. They cannot modify the initial system instructions or environment that Claude loads during startup. For that, you need wrapper architecture."

### Verification Steps Taken

1. ✅ Examined Claude Code plugin directory structure
2. ✅ Reviewed plugin.json schema and capabilities
3. ✅ Tested plugin loading sequence with sample plugin
4. ✅ Confirmed plugins load AFTER initialization
5. ✅ Validated that PM_INSTRUCTIONS requires pre-launch injection

## Alternative Architectures Considered

### Option 1: Plugin with Pre-Launch Script ❌

**Idea**: Create a plugin that includes a launcher script.

**Problem**: Still requires user to run the script instead of `claude`, defeating the purpose.

### Option 2: MCP-Only Implementation ❌

**Idea**: Provide only MCP tools, no system instruction modification.

**Problem**: Loses multi-agent orchestration - the core value proposition of MPM.

### Option 3: Fork Claude Code ❌

**Idea**: Modify Claude Code to support pre-initialization plugins.

**Problem**: Unsustainable maintenance burden, loses official updates.

### Option 4: CLI Wrapper ✅ (Current Solution)

**Idea**: Separate `claude-mpm` command that wraps `claude`.

**Advantages**:
- Full control over initialization sequence
- Can inject PM_INSTRUCTIONS before Claude starts
- Clean separation of concerns
- Maintains compatibility with official Claude Code updates
- Allows bundling of additional tools (dashboard, MCP gateway)

**Disadvantages**:
- Requires separate installation (acceptable trade-off)
- Users must remember to run `claude-mpm` instead of `claude`

## Conclusion

The CLI wrapper architecture is not just a design choice - it's the **only viable approach** for MPM's functionality. The plugin system is excellent for extending Claude Code with tools and commands, but cannot support the deep behavioral modifications that enable MPM's multi-agent orchestration.

## Recommendations

### For Users

**If you want MPM features**: Use the CLI wrapper via `claude-mpm` command.

**If you only need tools**: Consider MCP services (kuzu-memory, mcp-vector-search, etc.) which work as plugins.

### For Plugin Developers

Plugins are great for:
- ✅ Adding specialized tools
- ✅ Integrating external services
- ✅ Providing domain-specific slash commands
- ✅ Creating custom hooks for workflows

Plugins **cannot** be used for:
- ❌ Modifying Claude's core behavior
- ❌ Injecting system instructions
- ❌ Pre-initialization setup
- ❌ Wrapping/intercepting Claude invocation

### For Future Claude Code Versions

If Anthropic adds support for:
1. **Pre-initialization hooks**: Plugins that run before system instruction loading
2. **System instruction modification API**: Safe way to inject instructions
3. **Behavioral profiles**: User-configurable instruction templates

Then plugin-based distribution might become viable. Until then, wrapper architecture remains necessary.

## Architectural Diagram

```
┌──────────────────────────────────────────────────────────┐
│                    USER INVOCATION                        │
└─────────────┬────────────────────────────────────────────┘
              │
              ├──────────────────────────────────────────────┐
              │                                              │
              v                                              v
    ┌─────────────────┐                          ┌──────────────────┐
    │  claude-mpm     │  WRAPPER (Pre-launch)    │     claude       │  PLUGIN (Post-launch)
    │                 │                          │                  │
    │  ✅ PM_INSTRUCT │                          │  ❌ PM_INSTRUCT  │
    │  ✅ Multi-Agent │                          │  ❌ Multi-Agent  │
    │  ✅ Session Mgmt│                          │  ✅ Tools/Cmds   │
    │  ✅ Context Ctrl│                          │  ✅ MCP Services │
    └────────┬────────┘                          └──────────────────┘
             │
             v
    ┌─────────────────┐
    │  Claude Code    │
    │  (with PM)      │
    └─────────────────┘
```

## References

- Claude Code Documentation: https://docs.anthropic.com/en/docs/claude-code
- MPM Architecture: `/docs/developer/ARCHITECTURE.md`
- Plugin Research Session: November 10, 2025

---

**Last Updated**: November 10, 2025
**Version**: 1.0.0
**Status**: Authoritative explanation of architectural constraints
