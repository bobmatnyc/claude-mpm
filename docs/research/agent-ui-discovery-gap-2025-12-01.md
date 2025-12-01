# Agent Configuration UI Discovery System Gap

**Research Date:** 2025-12-01
**Researcher:** Claude (Research Agent)
**Issue:** Configuration UI shows only local agents, not discovered remote agents

## Executive Summary

The `claude-mpm agents manage` command uses an **outdated agent loading system** that only displays local agents from `.claude-mpm/agents/` directories, completely bypassing the new **RemoteAgentDiscoveryService** which successfully discovers 44 agents from `bobmatnyc/claude-mpm-agents` repository.

**Impact:** Users cannot see or manage 40+ available agents through the interactive UI, only through CLI commands like `claude-mpm agents list --system`.

---

## Current State

### ✅ What's Working

1. **Agent Source Configuration** (Verified)
   - System source properly configured: `bobmatnyc/claude-mpm-agents`
   - Configuration file: `~/.claude-mpm/config/agent_sources.yaml`
   - Status: Enabled, Priority 100

2. **Agent Discovery & Caching** (Verified)
   - 71 agent files cached in: `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/`
   - Startup sync working: "Syncing agents: 44/44 (100%)"
   - Sample agents discovered:
     - `agents/documentation/documentation.md`
     - `agents/universal/research.md`
     - `agents/engineer/python/python-engineer.md`
     - ... (41 more)

3. **CLI Listing Commands** (Verified)
   - `claude-mpm agents list --system` shows all 44 agents
   - `claude-mpm agent-source list` shows configured source
   - Templates deployed to: `~/.claude-mpm/templates/` (85 .md files)

### ❌ What's Broken

**Configuration UI (`claude-mpm agents manage`)**
- Shows: "📭 No local agents found"
- Expected: Should show 40+ discovered remote agents
- Actual behavior: Only scans `.claude-mpm/agents/` (empty)
- Missing: Integration with RemoteAgentDiscoveryService

---

## Root Cause Analysis

### Architecture Disconnect

```
┌─────────────────────────────────────────────────────┐
│          WHAT SHOULD HAPPEN (Expected)              │
├─────────────────────────────────────────────────────┤
│  claude-mpm agents manage                           │
│         ↓                                            │
│  AgentWizard.run_interactive_manage()               │
│         ↓                                            │
│  RemoteAgentDiscoveryService.discover_all()  ← NEW  │
│         ↓                                            │
│  Display 44 agents from git sources                 │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│          WHAT ACTUALLY HAPPENS (Current)            │
├─────────────────────────────────────────────────────┤
│  claude-mpm agents manage                           │
│         ↓                                            │
│  AgentWizard.run_interactive_manage()               │
│         ↓                                            │
│  LocalAgentTemplateManager.list_local_templates() ← OLD │
│         ↓                                            │
│  Scans: .claude-mpm/agents/ (empty)                │
│         ↓                                            │
│  Display: "No local agents found"                   │
└─────────────────────────────────────────────────────┘
```

### Code Evidence

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/agent_wizard.py`

```python
# Line 120-129
def run_interactive_manage(self) -> Tuple[bool, str]:
    """Run interactive agent management menu."""
    try:
        while True:
            # List current local agents
            templates = self.manager.list_local_templates()  # ← PROBLEM!

            # Only shows agents from:
            # - .claude-mpm/agents/ (project)
            # - ~/.claude-mpm/agents/ (user)
            # Does NOT query discovery service!
```

**LocalAgentTemplateManager Scope:**

```python
# File: src/claude_mpm/services/agents/local_template_manager.py
# Lines 134-136

self.project_agents_dir = self.working_directory / ".claude-mpm" / "agents"
self.user_agents_dir = Path.home() / ".claude-mpm" / "agents"

# Does NOT scan:
# ❌ ~/.claude-mpm/cache/remote-agents/ (discovered agents)
# ❌ ~/.claude-mpm/templates/ (deployed agents)
```

### Verified Directory States

```bash
# User-level agents (empty)
~/.claude-mpm/agents/
└── user-defined/  (empty directory)

# Project-level agents (empty)
/Users/masa/Projects/claude-mpm/.claude-mpm/agents/
└── (empty)

# Discovered remote agents (NOT SCANNED BY UI)
~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/
├── agents/documentation/documentation.md
├── agents/universal/research.md
├── agents/engineer/python/python-engineer.md
└── ... (41 more agents)

# Deployed templates (NOT SCANNED BY UI)
~/.claude-mpm/templates/
├── research.md
├── python-engineer.md
├── documentation.md
├── mpm-agent-manager.md
├── mpm-skills-manager.md
└── ... (80 more templates)
```

---

## Why System Source Auto-Configuration Works

The system source IS properly auto-configured during startup. Evidence:

1. **Configuration File Created:**
   ```yaml
   # ~/.claude-mpm/config/agent_sources.yaml
   disable_system_repo: true
   repositories:
     - url: https://github.com/bobmatnyc/claude-mpm-agents
       subdirectory: agents
       enabled: true
       priority: 100
   ```

2. **Startup Sync Executes:**
   ```
   Syncing agents: 44/44 (100%) - universal/research.md
   ```

3. **Agents Cached Successfully:**
   ```bash
   $ ls ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/
   # 44 agent directories with .md files
   ```

**The problem is NOT configuration or discovery - it's UI integration.**

---

## Detailed Impact Analysis

### User Experience Impact

**Current Workflow (Broken):**
```bash
$ claude-mpm agents manage
# Shows: "📭 No local agents found"
# Options:
#   1. Create new agent  ← User must manually create from scratch
#   2. Import agents
#   3. Exit
```

**Expected Workflow (Should Be):**
```bash
$ claude-mpm agents manage
# Should show: "📋 Found 44 agent(s):"
#   1. 📚 research - Research & Analysis Agent
#   2. 🐍 python-engineer - Python Development Expert
#   3. 📖 documentation - Documentation Specialist
#   ... (41 more)
#   45. Create new agent
#   46. Exit
```

### Workaround Available

Users CAN access agents via CLI commands:
```bash
# List all system agents
$ claude-mpm agents list --system

# Deploy specific agent
$ claude-mpm agents deploy research

# View agent details
$ claude-mpm agents info research
```

**But NOT via interactive UI.**

---

## Proposed Solutions

### Solution 1: Integrate Discovery Service into UI (Recommended)

**Complexity:** Medium
**Impact:** High
**Backward Compatibility:** Full

**Changes Required:**

**File:** `src/claude_mpm/cli/interactive/agent_wizard.py`

```python
# Current (Line 26-28)
class AgentWizard:
    def __init__(self):
        self.manager = LocalAgentTemplateManager()
        self.logger = logger

# Proposed
class AgentWizard:
    def __init__(self):
        self.manager = LocalAgentTemplateManager()
        self.discovery_service = RemoteAgentDiscoveryService()  # NEW
        self.logger = logger
```

**File:** `src/claude_mpm/cli/interactive/agent_wizard.py` (Line 120-158)

```python
# Current
def run_interactive_manage(self) -> Tuple[bool, str]:
    while True:
        templates = self.manager.list_local_templates()  # Only local

        if not templates:
            print("\n📭 No local agents found.")
            # ...

# Proposed
def run_interactive_manage(self) -> Tuple[bool, str]:
    while True:
        # Combine local + discovered agents
        local_templates = self.manager.list_local_templates()
        discovered_agents = self.discovery_service.discover_all()

        # Merge and prioritize (local overrides discovered)
        all_agents = self._merge_agent_sources(local_templates, discovered_agents)

        if not all_agents:
            print("\n📭 No agents found.")
            # ...
        else:
            print(f"\n📋 Found {len(all_agents)} agent(s):")
            for i, agent in enumerate(all_agents, 1):
                tier_icon = self._get_tier_icon(agent)
                source_label = self._get_source_label(agent)
                print(f"   {i}. {tier_icon} {agent.agent_id} - {agent.name} {source_label}")
```

**Helper Methods:**

```python
def _merge_agent_sources(
    self,
    local: List[LocalAgentTemplate],
    discovered: List[DiscoveredAgent]
) -> List[AgentInfo]:
    """Merge local and discovered agents with precedence."""
    merged = {}

    # Add discovered agents (lower priority)
    for agent in discovered:
        merged[agent.agent_id] = AgentInfo(
            agent_id=agent.agent_id,
            name=agent.metadata.get('name', agent.agent_id),
            source='discovered',
            tier='system',
            priority=agent.priority
        )

    # Add local agents (higher priority, overrides)
    for template in local:
        merged[template.agent_id] = AgentInfo(
            agent_id=template.agent_id,
            name=template.metadata.get('name', template.agent_id),
            source='local',
            tier=template.tier,
            priority=template.priority
        )

    # Sort by priority (higher first)
    return sorted(merged.values(), key=lambda a: a.priority, reverse=True)

def _get_tier_icon(self, agent: AgentInfo) -> str:
    """Get icon for agent tier."""
    return {
        'project': '🏢',
        'user': '👤',
        'system': '📦',
        'discovered': '🌐'
    }.get(agent.tier, '📄')

def _get_source_label(self, agent: AgentInfo) -> str:
    """Get source label for display."""
    if agent.source == 'local':
        return f"[{agent.tier}]"
    return "[system]"
```

**Testing:**
```python
# Unit test
def test_agent_wizard_shows_discovered_agents():
    wizard = AgentWizard()
    agents = wizard._get_all_agents()

    # Should include both local and discovered
    assert len(agents) >= 44  # At least system agents

    # Should prioritize local over system
    local_python = create_local_agent('python-engineer')
    wizard.manager.save_local_template(local_python, 'project')

    agents = wizard._get_all_agents()
    python_agent = next(a for a in agents if a.agent_id == 'python-engineer')
    assert python_agent.source == 'local'  # Local wins
```

---

### Solution 2: Unified Agent Registry (Future Enhancement)

**Complexity:** High
**Impact:** Very High
**Backward Compatibility:** Breaking

Create a unified agent registry that abstracts all agent sources:

```python
class UnifiedAgentRegistry:
    """Single source of truth for all agents."""

    def __init__(self):
        self.local_manager = LocalAgentTemplateManager()
        self.discovery_service = RemoteAgentDiscoveryService()
        self.deployment_service = AgentDeploymentService()

    def list_all(self, include_deployed=True, include_discovered=True) -> List[AgentInfo]:
        """List all agents from all sources."""
        pass

    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent by ID from any source."""
        pass

    def resolve_precedence(self, agent_id: str) -> AgentInfo:
        """Resolve which version wins (local > user > system > discovered)."""
        pass
```

**This would require refactoring all agent-related commands.**

---

## Recommended Implementation Plan

### Phase 1: Quick Fix (1-2 hours)

1. **Modify AgentWizard to show discovered agents**
   - File: `src/claude_mpm/cli/interactive/agent_wizard.py`
   - Add RemoteAgentDiscoveryService integration
   - Merge local + discovered agents
   - Test interactive UI

2. **Add source indicators in UI**
   - Show [system] vs [project] vs [user] labels
   - Add legend explaining sources

3. **Handle agent selection from different sources**
   - When user selects discovered agent:
     - Option 1: Copy to local for customization
     - Option 2: View details (read-only)
     - Option 3: Deploy as-is

### Phase 2: Enhanced UI (2-3 hours)

1. **Add filtering options**
   - View only local agents
   - View only system agents
   - View all agents

2. **Add search/filter by category**
   - Engineer agents
   - QA agents
   - Ops agents
   - Documentation agents

3. **Improve agent details view**
   - Show full metadata
   - Show dependencies
   - Show version info
   - Show source repository

### Phase 3: Registry Refactoring (Future)

1. **Create UnifiedAgentRegistry**
2. **Migrate all commands to use registry**
3. **Add caching layer**
4. **Add version conflict resolution**

---

## Testing Strategy

### Unit Tests

```python
# tests/cli/interactive/test_agent_wizard_discovery.py

def test_wizard_lists_discovered_agents(mock_discovery_service):
    """Wizard should show discovered agents from git sources."""
    wizard = AgentWizard()
    agents = wizard._get_all_agents()

    assert len(agents) >= 40
    assert any(a.agent_id == 'research' for a in agents)
    assert any(a.agent_id == 'python-engineer' for a in agents)

def test_wizard_prioritizes_local_over_discovered():
    """Local agents should override discovered agents with same ID."""
    wizard = AgentWizard()

    # Create local agent with same ID as discovered
    local_research = LocalAgentTemplate(agent_id='research', tier='project')
    wizard.manager.save_local_template(local_research, 'project')

    agents = wizard._get_all_agents()
    research = next(a for a in agents if a.agent_id == 'research')

    assert research.source == 'local'
    assert research.tier == 'project'

def test_wizard_handles_empty_directories_gracefully():
    """Should still show discovered agents even if local dirs empty."""
    wizard = AgentWizard()

    # Ensure local dirs are empty
    assert not wizard.manager.list_local_templates()

    # Should still show discovered agents
    agents = wizard._get_all_agents()
    assert len(agents) >= 40
```

### Integration Tests

```bash
# Test interactive flow
$ python -m pytest tests/integration/test_agent_wizard_flow.py -v

# Test with real repositories
$ INTEGRATION_TEST=true python -m pytest tests/integration/test_discovery_integration.py
```

### Manual Testing

```bash
# 1. Ensure system source configured
$ claude-mpm agent-source list
# Should show bobmatnyc/claude-mpm-agents

# 2. Run interactive UI
$ claude-mpm agents manage
# Should show 44+ agents

# 3. Create local agent
# Select option to create new agent
# Verify it appears at top of list (higher priority)

# 4. Test filtering
# Should be able to filter by source (local/system)

# 5. Test selection
# Select system agent
# Should offer: Copy to local, View details, Deploy
```

---

## Security & Risk Considerations

### Security

- ✅ **No new security risks** - using existing discovery service
- ✅ **Read-only access** to discovered agents (cannot modify git source directly)
- ✅ **Local customization safe** - copies to local before editing

### Backward Compatibility

- ✅ **Fully compatible** - existing local agents still work
- ✅ **No breaking changes** - additive functionality only
- ✅ **Graceful degradation** - if discovery fails, shows local agents only

### Performance

- ⚠️ **Potential latency** - discovery service may be slow on first run
- ✅ **Caching mitigates** - subsequent runs use cached results
- 💡 **Optimization**: Add loading indicator during discovery

---

## Files Modified

### Primary Changes

1. **`src/claude_mpm/cli/interactive/agent_wizard.py`**
   - Add discovery service integration
   - Modify `run_interactive_manage()` to merge sources
   - Add helper methods for merging/sorting

2. **`src/claude_mpm/services/agents/local_template_manager.py`** (Optional)
   - Add method to merge with discovered agents
   - Or keep separation of concerns (recommended)

### New Files

1. **`src/claude_mpm/models/agent_info.py`** (if needed)
   - Unified agent info dataclass
   - Supports both local and discovered sources

2. **`tests/cli/interactive/test_agent_wizard_discovery.py`**
   - Unit tests for discovery integration

### Documentation Updates

1. **`docs/user-guide/agent-management.md`**
   - Update to reflect new UI capabilities
   - Explain source precedence

2. **`docs/architecture/agent-discovery.md`**
   - Document UI integration with discovery service

---

## Conclusion

**Root Cause:** Configuration UI uses old `LocalAgentTemplateManager` which only scans `.claude-mpm/agents/` directories, completely bypassing the new `RemoteAgentDiscoveryService`.

**Fix:** Integrate `RemoteAgentDiscoveryService` into `AgentWizard` to display discovered agents alongside local agents.

**Estimated Effort:** 2-4 hours for complete implementation + testing

**Priority:** High - users cannot discover available agents through UI

**Next Steps:**
1. Implement Solution 1 (discovery service integration)
2. Add unit tests
3. Test interactive flow
4. Update documentation
5. Consider Phase 2 enhancements based on user feedback

---

## Appendix: Command Reference

### Working Commands

```bash
# List all system agents (works)
$ claude-mpm agents list --system

# List deployed agents (works)
$ claude-mpm agents list --deployed

# Show agent sources (works)
$ claude-mpm agent-source list

# Deploy specific agent (works)
$ claude-mpm agents deploy <agent-id>
```

### Broken Commands

```bash
# Interactive agent management (broken - shows no agents)
$ claude-mpm agents manage
```

### Verification Commands

```bash
# Check cache directory
$ ls ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/

# Check templates directory
$ ls ~/.claude-mpm/templates/

# Check local agents directories (should be empty)
$ ls ~/.claude-mpm/agents/
$ ls .claude-mpm/agents/

# Count discovered agents
$ find ~/.claude-mpm/cache/remote-agents/bobmatnyc -name "*.md" | wc -l
# Expected: 71 (includes non-agent .md files)

# Count actual agent files
$ ls ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/*/*.md | wc -l
# Expected: ~44
```

---

**Research Complete:** 2025-12-01
**Memory Usage:** Within limits (strategic sampling, no full file reads)
**Confidence:** High (verified through code analysis, directory inspection, and command execution)
