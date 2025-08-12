# PM (Project Manager) Architecture

## Overview

The Claude MPM Project Manager (PM) uses a sophisticated instruction architecture that separates **framework requirements** from **customizable instructions**. This ensures core framework behaviors are preserved while allowing project-specific customization.

## Architecture Components

### 1. BASE_PM.md - Framework Requirements

**Location**: `src/claude_mpm/agents/BASE_PM.md`

Contains non-negotiable framework requirements that apply to ALL PM configurations:

- **TodoWrite prefix rules** - Mandatory [Agent] prefixes for task delegation
- **Memory management protocols** - How to detect and route memory requests
- **Agent delegation workflows** - Required sequence (Research → Engineer → QA → Documentation)
- **Structured response format** - JSON format for logging and tracking
- **Template variables** - Dynamic injection points like `{{current-date}}` and `{{agent-capabilities}}`

### 2. INSTRUCTIONS.md - Customizable Instructions

**Location**: `src/claude_mpm/agents/INSTRUCTIONS.md`

Contains project-specific PM customizations that can be modified:

- **Project-specific workflows** - Custom delegation patterns
- **Domain knowledge** - Project context and requirements
- **Communication style** - Tone and interaction preferences  
- **Custom agent configurations** - Specialized agents for the project
- **Override behaviors** - Project-specific exceptions to defaults

### 3. Instruction Injection Architecture

The PM instructions are assembled and injected at runtime, not read from files during execution.

#### Runtime Assembly Process

1. **INSTRUCTIONS.md Loading**: Custom project instructions are loaded first
2. **BASE_PM.md Injection**: Framework requirements are appended after custom instructions
3. **Template Variable Resolution**: Dynamic values are injected:
   - `{{current-date}}` → Current system date
   - `{{agent-capabilities}}` → Dynamically discovered agent capabilities
4. **System Prompt Formation**: Complete instruction set passed to Claude

#### Precedence Model

```
┌─────────────────────────────────┐
│     CUSTOM INSTRUCTIONS.md      │  ← Project-specific (can override)
├─────────────────────────────────┤
│      FRAMEWORK BASE_PM.md       │  ← Framework requirements (mandatory)
├─────────────────────────────────┤
│    TEMPLATE VARIABLES          │  ← Dynamic values injected
│  • {{current-date}}            │
│  • {{agent-capabilities}}      │
└─────────────────────────────────┘
```

**Important**: BASE_PM.md requirements OVERRIDE conflicting instructions in INSTRUCTIONS.md to ensure framework integrity.

## Template Variables

### {{current-date}}

Provides temporal context for time-sensitive decisions:

```markdown
**Today's Date**: 2025-08-12
Apply date awareness to all time-sensitive tasks and decisions.
```

### {{agent-capabilities}}

Dynamically generated list of available agents and their capabilities:

```markdown
## Available Agents

**Engineering Agents:**
- [Engineer] Core development and implementation tasks
  - Tools: Write, Edit, Read, Grep, MultiEdit
  - Specializations: Full-stack development, API design

**Research Agents:**  
- [Research] Analysis, investigation, and discovery
  - Tools: Grep, Read, WebSearch
  - Specializations: Codebase analysis, requirement gathering
```

This ensures PM instructions always reflect the current agent deployment state.

## Deployment and Usage

### How PM Instructions Are Used

1. **Framework Loading**: `claude_runner.py` loads INSTRUCTIONS.md
2. **Template Processing**: Variables resolved with current system state  
3. **Base Framework Injection**: BASE_PM.md appended via `--append-system-prompt`
4. **Claude Execution**: Complete instruction set passed to Claude API

### PM is NOT an Agent

**Important**: The PM does not exist as a deployable agent file (no `pm.json`). Instead:

- PM instructions are **injected directly** into Claude sessions
- **Framework-controlled**: Cannot be overridden at user/project level
- **Always active**: PM identity is established through instruction injection
- **Non-delegable**: PM operations cannot be delegated to other agents

### Verification and Identity

When PM identity verification is requested:

```python
# CORRECT: PM confirms active injected instructions
"I am operating under the PM instructions currently governing my behavior"

# INCORRECT: PM attempts to read template files  
"Let me read my PM instructions from BASE_PM.md..."
```

The PM's identity IS the instructions currently active, not what's stored in template files.

## Customization Patterns

### Project-Specific INSTRUCTIONS.md

```markdown
# Custom Project Manager for E-Commerce Platform

## Project Context
Working on a high-traffic e-commerce platform with strict security requirements.

## Custom Workflows
- All payment-related tasks require Security agent review
- Performance testing required for checkout flow changes
- Documentation must include load testing results

## Communication Style  
- Use concise, business-focused summaries
- Include performance metrics in all reports
- Escalate security issues immediately
```

### Framework BASE_PM.md (Non-modifiable)

```markdown
# Base PM Framework Requirements

## TodoWrite Framework Requirements
**ALWAYS use [Agent] prefix for delegated tasks**:
- ✅ [Engineer] Implement user registration endpoint
- ❌ [PM] Update system configuration

## Memory Management Protocol
**MANDATORY for ALL user prompts** - evaluate for memory indicators...
```

## Benefits of This Architecture

### 1. **Framework Integrity**
- Core behaviors cannot be accidentally overridden
- Consistent TodoWrite patterns across all projects
- Reliable memory management protocols

### 2. **Project Flexibility** 
- INSTRUCTIONS.md can be fully customized for project needs
- Domain-specific workflows and preferences
- Custom agent configurations and priorities

### 3. **Dynamic Adaptation**
- Agent capabilities reflect current deployment state
- Date awareness for time-sensitive tasks
- Automatic discovery of project-specific agents

### 4. **Maintainability**
- Clear separation between framework and customization
- Template variables reduce duplication
- Centralized framework updates in BASE_PM.md

## Best Practices

### For Framework Developers

1. **BASE_PM.md Changes**: Only modify for framework-wide requirements
2. **Template Variables**: Add new variables for common dynamic content
3. **Precedence Rules**: Ensure BASE_PM.md overrides are clearly documented
4. **Testing**: Verify template resolution in various project contexts

### For Project Maintainers

1. **INSTRUCTIONS.md Focus**: Keep project-specific, avoid duplicating BASE_PM.md
2. **Testing Customizations**: Verify custom workflows with real agent delegations  
3. **Documentation**: Document project-specific PM behaviors
4. **Template Usage**: Leverage `{{agent-capabilities}}` for dynamic agent selection

### For Claude MPM Users

1. **Identity Verification**: PM identity is active instructions, not template files
2. **Customization Scope**: Only INSTRUCTIONS.md can be customized
3. **Framework Updates**: BASE_PM.md updates apply automatically to all projects
4. **Troubleshooting**: Check both INSTRUCTIONS.md and BASE_PM.md for behavior sources

## Implementation Details

### Code References

- **Instruction Loading**: `src/claude_mpm/core/claude_runner.py`
- **Template Processing**: `src/claude_mpm/agents/BASE_PM.md` 
- **Agent Capabilities**: `src/claude_mpm/services/agents/registry/deployed_agent_discovery.py`
- **Framework Injection**: `--append-system-prompt` in Claude runner

### Configuration Integration

The PM architecture integrates with the broader configuration system:

- **Agent Discovery**: Uses same discovery system as other agents
- **Memory Integration**: Leverages agent memory protocols  
- **Hook Integration**: PM responses processed by same hook system
- **Response Tracking**: PM activities logged with structured responses

This architecture ensures the PM system is both powerful and maintainable while preserving the flexibility that makes Claude MPM adaptable to diverse project needs.