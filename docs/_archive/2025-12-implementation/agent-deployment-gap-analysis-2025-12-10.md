# Agent Deployment Gap Analysis

**Date**: 2025-12-10
**Issue**: Agent selection in `claude-mpm configure` doesn't create `.md` files in `.claude/agents/`

## Executive Summary

The `claude-mpm configure` command allows users to enable/disable agents interactively, but **it only updates a state JSON file and does NOT trigger actual agent deployment**. This creates a disconnect between user expectations (selecting agents should deploy them) and actual behavior (selection only updates configuration).

## The Missing Link

### What Users Expect
1. User selects agents in `claude-mpm configure`
2. Saves changes with `[s]` option
3. `.md` files appear in `.claude/agents/`

### What Actually Happens
1. User selects agents in `claude-mpm configure`
2. Saves changes with `[s]` option
3. **Only** `.claude-mpm/agent_states.json` is updated
4. **NO** `.md` files are created

## Architecture Investigation

### Configure Command Flow

**File**: `src/claude_mpm/cli/commands/configure.py`

```
User selects agents
    ↓
_toggle_agents_interactive() handles selection
    ↓
agent_manager.commit_deferred_changes()
    ↓
Saves to agent_states.json
    ↓
*** STOPS HERE - NO DEPLOYMENT ***
```

### Agent State Manager

**File**: `src/claude_mpm/cli/commands/agent_state_manager.py`

```python
def commit_deferred_changes(self) -> None:
    """Save all deferred changes at once."""
    for agent_name, enabled in self.deferred_changes.items():
        if agent_name not in self.states:
            self.states[agent_name] = {}
        self.states[agent_name]["enabled"] = enabled
    self._save_states()  # Only writes to agent_states.json
    self.deferred_changes.clear()
```

**Problem**: This method only persists state to JSON, it does NOT call any deployment service.

### Actual Deployment Logic

**File**: `src/claude_mpm/services/agents/deployment/agent_deployment.py`

The `AgentDeploymentService.deploy_agents()` method handles actual file creation:
- Loads agent templates
- Builds agent markdown with YAML frontmatter
- Writes `.md` files to `.claude/agents/`

**File**: `src/claude_mpm/services/agents/deployment/single_agent_deployer.py`

```python
def deploy_single_agent(self, ...):
    # Line 69: Determine target file path
    target_file = agents_dir / f"{agent_name}.md"

    # Line 91-93: Build and write agent content
    agent_content = self.template_builder.build_agent_markdown(...)
    target_file.write_text(agent_content)  # THIS creates the .md file
```

## The Gap

**Configure command** → Updates `agent_states.json` only
**Deployment service** → Creates actual `.md` files

**Missing**: No connection between configure selection and deployment service.

## Where Deployment IS Triggered

Currently, agent deployment happens in these scenarios:

1. **`claude-mpm run` startup** - Deploys all agents automatically
2. **`mpm-agents-deploy` command** - Manual deployment trigger
3. **Programmatic API calls** - Direct service invocation

**NOT triggered by**: `claude-mpm configure` agent selection

## Root Cause Analysis

### Design Intent vs. Implementation

The architecture appears designed for:
1. **State Management**: Track which agents are enabled/disabled
2. **Lazy Deployment**: Deploy agents at runtime (during `run` command)

However, this creates UX confusion:
- Users expect immediate feedback (files appear when selected)
- Actual deployment is deferred until runtime
- No clear indication that deployment is deferred

### Code Evidence

**agent_state_manager.py:65-70**
```python
def set_agent_enabled(self, agent_name: str, enabled: bool):
    """Set agent enabled state."""
    if agent_name not in self.states:
        self.states[agent_name] = {}
    self.states[agent_name]["enabled"] = enabled
    self._save_states()  # Only saves JSON
```

**No calls to**:
- `AgentDeploymentService.deploy_agents()`
- `SingleAgentDeployer.deploy_single_agent()`
- Any file creation logic

## Solution Options

### Option 1: Add Deployment Call to Configure (RECOMMENDED)

**Pros**:
- Matches user expectations
- Immediate feedback
- Clear cause-and-effect

**Cons**:
- Increases configure command latency
- More complex error handling needed

**Implementation**:
```python
# In agent_state_manager.py
def commit_deferred_changes(self) -> None:
    """Save all deferred changes and trigger deployment."""
    for agent_name, enabled in self.deferred_changes.items:
        if agent_name not in self.states:
            self.states[agent_name] = {}
        self.states[agent_name]["enabled"] = enabled
    self._save_states()

    # NEW: Trigger deployment for enabled agents
    self._deploy_enabled_agents()

    self.deferred_changes.clear()
```

### Option 2: Add Explicit "Deploy" Action in Configure Menu

**Pros**:
- Gives users control over when deployment happens
- Separates selection from deployment
- Allows batch selection then single deploy

**Cons**:
- Extra step for users
- Still requires explicit action

**Implementation**:
```python
# In configure.py _show_main_menu()
text_deploy = Text("  ")
text_deploy.append("[d]", style="bold green")
text_deploy.append(" Deploy selected agents")
self.console.print(text_deploy)
```

### Option 3: Clarify UX with Messages (MINIMAL)

**Pros**:
- No code changes to deployment logic
- Quick fix

**Cons**:
- Doesn't solve the core UX problem
- Users still confused

**Implementation**:
```python
# In configure.py after commit_deferred_changes()
self.console.print("[yellow]Changes saved to configuration.[/yellow]")
self.console.print("[blue]Run 'claude-mpm run' to deploy selected agents.[/blue]")
```

## Files Analyzed

1. `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py` (478-553)
2. `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/agent_state_manager.py` (complete)
3. `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/deployment/agent_deployment.py` (294-541)
4. `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/deployment/single_agent_deployer.py` (38-121)

## Recommendations

1. **Immediate Fix** (Option 3): Add clear messaging that deployment happens at runtime
2. **Short-term Enhancement** (Option 2): Add explicit "Deploy" menu option
3. **Long-term Improvement** (Option 1): Integrate deployment into commit flow with progress indicators

## Next Steps

1. Confirm expected behavior with product owner
2. Choose solution approach based on UX requirements
3. Implement solution with proper error handling
4. Add tests for deployment trigger
5. Update documentation to clarify deployment timing

## Memory Usage Statistics

- Files read: 4 source files
- Search operations: Strategic grep patterns for discovery
- Memory-efficient investigation using targeted reads and line offsets
- No full codebase loading required
