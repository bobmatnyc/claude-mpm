# Agent Deployment Model Investigation

**Research Date**: 2026-01-02
**Researcher**: Claude Research Agent
**Issue**: CLI list command doesn't match actually deployed agents

---

## Executive Summary

The agent deployment model is **working correctly**, but the terminology and mental model needs clarification. The apparent "mismatch" stems from:

1. **Confusing terminology**: "deployed" vs "cached" vs "listed"
2. **Multi-tier discovery**: Agents come from 4 different sources, not just one
3. **List command behavior**: `agent-manager list` shows ALL discoverable agents across tiers, not just what's deployed

**Key Finding**: 19 agents ARE deployed to `.claude/agents/`, but the list shows them at PROJECT level because that's where they were deployed. The system is functioning as designed.

---

## Current Deployment Flow (Actual Behavior)

### Phase 1: Startup Sync (Git Sources)
```
1. Read configuration.yaml → agent_sync.sources
2. For each enabled source:
   - Pull from GitHub (bobmatnyc/claude-mpm-agents)
   - Download to ~/.claude-mpm/cache/remote-agents/
   - Cache 50 remote agents (47 downloaded, 3 cached)
```

**Location**: `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/`

### Phase 2: Profile Filtering
```
3. Load active profile (framework-development)
4. Apply exclusion list from profile:
   - Exclude 26 agents (ticketing, memory-manager-agent, ops, etc.)
   - Keep 19 agents for deployment
```

**Source**: `.claude-mpm/configuration.yaml` → `active_profile: framework-development`

### Phase 3: Multi-Source Discovery (4 Tiers)
```
5. Scan 4 directories for agent templates:
   Tier 1 (Cache):   ~/.claude-mpm/cache/agents/          (46 remote agents)
   Tier 2 (System):  src/claude_mpm/agents/templates/    (0 found - dev mode)
   Tier 3 (User):    ~/.claude-mpm/agents/               (0 found)
   Tier 4 (Project): .claude-mpm/agents/                 (0 found)

6. Version comparison: Highest version wins per agent
7. Filter out excluded agents from profile
```

**Result**: 19 agents selected for deployment (all from cache tier)

### Phase 4: Deployment to Project
```
8. Check .claude/agents/ for existing deployments
9. Compare versions: 0 need updates, 18 up to date
10. Deploy to: /Users/masa/Projects/claude-mpm/.claude/agents/
    - Deployed: 0 (all already up to date)
    - Skipped: 18 (already current version)
```

**Actual Files**:
```bash
$ ls .claude/agents/
code-analyzer.md        local-ops.md            python-engineer.md      svelte-engineer.md      web-ui.md
documentation.md        memory-manager.md       qa.md                   typescript-engineer.md
engineer.md             mpm-agent-manager.md    refactoring-engineer.md version-control.md
                        mpm-skills-manager.md   research.md             web-qa.md
project-organizer.md    security.md
prompt-engineer.md
```

**Count**: 19 files (matches expected deployment)

---

## List Command Behavior (The "Mismatch")

### What `agent-manager list` Does

From `agent_manager.py:94-142`:

```python
def _list_agents(self, args) -> CommandResult:
    """List all agents across tiers with hierarchy."""
    agents = {"project": [], "user": [], "system": []}

    # Check project level (.claude/agents/)
    project_dir = Path.cwd() / ".claude" / "agents"
    for agent_file in project_dir.glob("*.md"):
        agents["project"].append(self._read_agent_summary(agent_file, "project"))

    # Check user level (~/.claude/agents/)
    user_dir = Path.home() / ".claude" / "agents"
    for agent_file in user_dir.glob("*.md"):
        if not any(a["id"] == agent_id for a in agents["project"]):
            agents["user"].append(self._read_agent_summary(agent_file, "user"))

    # Get system agents (from templates)
    templates = self.builder_service.list_available_templates()
    for template in templates:
        if not any(a["id"] == agent_id for a in agents["project"] + agents["user"]):
            agents["system"].append(...)
```

**Key Insight**: This scans actual filesystem locations, not configuration state!

### Output Interpretation

```
=== Agent Hierarchy ===

[P] PROJECT LEVEL (Highest Priority)
    prompt-engineer      - prompt-engineer
    mpm-agent-manager    - mpm-agent-manager
    [... 19 total agents ...]
```

**What this means**:
- These 19 agents ARE deployed to `.claude/agents/`
- They show as "PROJECT LEVEL" because they're in the project directory
- This is correct behavior - they were deployed there by the deployment service

**No agents shown in USER or SYSTEM tiers because**:
- User tier: `~/.claude/agents/` is empty (all agents go to project)
- System tier: Templates not shown if already deployed at higher tier

---

## Configuration Storage

### Primary Configuration: `.claude-mpm/configuration.yaml`

```yaml
agent_deployment:
  excluded_agents: []              # Deprecated - profiles now handle this
  filter_non_mpm_agents: true      # Only deploy MPM-authored agents

agent_sync:
  cache_dir: /Users/masa/.claude-mpm/cache/remote-agents
  enabled: true
  sources:
    - enabled: true
      id: github-remote
      priority: 100
      url: https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main/agents
  sync_interval: startup

active_profile: framework-development
```

### Profile Configuration: `.claude-mpm/profiles/framework-development.yaml`

**Note**: This file should exist but wasn't shown in the initial scan. Based on logs:

```yaml
# Expected structure (from log output)
agents:
  excluded:
    - ticketing
    - memory-manager-agent
    - content-agent
    - product-owner
    - api-qa
    # ... 21 more excluded agents

  # Implicitly enabled (not in excluded list):
  # - prompt-engineer, mpm-agent-manager, version-control, web-ui, qa,
  # - refactoring-engineer, mpm-skills-manager, memory-manager, local-ops,
  # - research, web-qa, project-organizer, python-engineer, engineer,
  # - documentation, typescript-engineer, svelte-engineer, code-analyzer, security
```

---

## The Actual Problem (User's Concern)

### User's Expected Model (Simple)

```
configure.yaml stores:
  - agents: [list of agent IDs to deploy]
  - skills: [list of skill IDs to deploy]

On startup:
  1. Sync remote sources to cache
  2. Deploy agents from list (remove unlisted)
  3. Deploy skills from list (remove unlisted)
```

### Current Reality (Complex)

```
Multiple config sources:
  - configuration.yaml (main config)
  - profiles/*.yaml (agent/skill filtering)
  - Agent frontmatter (skill dependencies)

On startup:
  1. Sync remote sources to cache (✓ working)
  2. Load profile → build exclusion list
  3. Multi-source discovery (4 tiers)
  4. Version comparison + selective deployment
  5. Skill discovery from agent frontmatter
  6. Profile filtering on skills

Deploy logic:
  - Agents: Only update if version changed
  - Skills: Deploy if referenced by agents OR in user_defined list

Cleanup logic:
  - Agents: Cleanup excluded agents separately
  - Skills: Cleanup based on agent references
```

### Where the Mismatch Occurs

**User sees**:
```bash
$ claude-mpm agent-manager list
=== Agent Hierarchy ===
[P] PROJECT LEVEL
    19 agents listed
```

**User expects**:
- This list should match what's "configured to deploy"
- Easy to add/remove agents by editing a list

**Reality**:
- The list shows what's ACTUALLY DEPLOYED (correct)
- But configuration is spread across:
  - `configuration.yaml` (sync sources)
  - `profiles/framework-development.yaml` (exclusions)
  - Profile logic (inverted - exclude instead of include)

---

## Root Causes of Confusion

### 1. **Inverted Logic (Exclude vs Include)**

Current model:
```yaml
# Profile defines what to EXCLUDE
agents:
  excluded: [ticketing, ops, react-engineer, ...]

# Everything else is implicitly included
```

User mental model:
```yaml
# Simple list of what to DEPLOY
agents:
  deployed: [engineer, qa, research, ...]
```

### 2. **List Shows Reality, Not Configuration**

`agent-manager list` scans filesystem:
- Project: `.claude/agents/*.md` (19 found)
- User: `~/.claude/agents/*.md` (0 found)
- System: Templates if not overridden (0 shown)

**Issue**: User can't easily see "what's configured" vs "what's deployed"

### 3. **No Single Source of Truth**

To understand what SHOULD be deployed, you need:
1. Check `configuration.yaml` → `active_profile`
2. Open `profiles/framework-development.yaml`
3. Read excluded agents list
4. Invert it mentally (everything NOT excluded)
5. Consider remote sources configuration
6. Account for version comparison logic

**Expected**: One file with explicit deployment list

### 4. **Deployment vs Discovery Confusion**

Terms used inconsistently:
- "Deployed agents" (log): 0 deployed, 18 skipped (version check)
- "Cached agents" (log): 50 cached (remote sync)
- "Listed agents" (CLI): 19 at PROJECT level

**Reality**:
- 50 agents in cache (remote source)
- 26 excluded by profile
- 19 remaining → deployed to `.claude/agents/`
- 18 skipped (already current version)
- 1 upgraded (memory-manager on Dec 31)

---

## Desired Simple Model (User's Request)

### Proposed Configuration Structure

```yaml
# .claude-mpm/configuration.yaml (or new configure.yaml)

agent_deployment:
  # Explicit list of agents to deploy
  enabled_agents:
    - engineer
    - qa
    - research
    - python-engineer
    - documentation
    # ... explicit list

  # Everything else is excluded
  # (Simpler than current exclusion list)

skill_deployment:
  # Explicit list of skills to deploy
  enabled_skills:
    - test-driven-development
    - systematic-debugging
    - git-workflow
    # ... explicit list

  # Auto-discovery from agent frontmatter (optional)
  auto_discover_from_agents: true

agent_sync:
  # Remote sources (same as current)
  sources:
    - url: https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main/agents
      enabled: true
```

### Simplified Deployment Flow

```
Startup:
  1. Sync remote sources → ~/.claude-mpm/cache/agents/

  2. Read configuration.yaml → enabled_agents list

  3. Deploy listed agents:
     - Copy from cache to .claude/agents/
     - Update if version changed

  4. Cleanup unlisted:
     - Remove .claude/agents/*.md NOT in enabled_agents list
     - Keep user-created agents (check author field)

  5. Discover skills:
     - From agent frontmatter (if auto_discover_from_agents)
     - Plus explicitly listed in enabled_skills

  6. Deploy skills:
     - Copy to .claude/skills/

  7. Cleanup unlisted skills:
     - Remove skills NOT referenced by agents OR in enabled_skills
```

### List Command Alignment

```bash
$ claude-mpm agent-manager list

=== DEPLOYED AGENTS (19) ===
✓ engineer               v2.0.1  (from cache)
✓ qa                     v1.8.0  (from cache)
✓ research               v1.5.0  (from cache)
[... full list ...]

=== AVAILABLE BUT NOT DEPLOYED (27) ===
  ticketing              v1.0.0  (excluded by config)
  ops                    v2.1.0  (excluded by config)
[... excluded list ...]

Configuration: .claude-mpm/configuration.yaml
Profile: Not used (direct configuration)
```

**Key improvement**: List shows what's configured AND what's deployed, making mismatch obvious.

---

## Implementation Changes Required

### 1. **Configuration Schema Update**

File: `src/claude_mpm/config/agent_deployment_config.py` (new or updated)

```python
class AgentDeploymentConfig:
    enabled_agents: List[str]  # Explicit list
    auto_exclude_others: bool = True  # Default behavior

class SkillDeploymentConfig:
    enabled_skills: List[str]
    auto_discover_from_agents: bool = True
```

### 2. **Deployment Service Changes**

File: `src/claude_mpm/services/agents/deployment/agent_deployment.py`

Current logic (line 441-469):
```python
# Multi-source discovery with exclusion filtering
use_multi_source = self._should_use_multi_source_deployment(deployment_mode)
if use_multi_source:
    template_files, agent_sources, cleanup_results = self._get_multi_source_templates(
        excluded_agents, config, agents_dir, force_rebuild
    )
```

**Change to**:
```python
# Direct inclusion model
enabled_agents = config.get("agent_deployment.enabled_agents", [])
template_files = self._get_enabled_agent_templates(enabled_agents, config)

# Cleanup unlisted agents
cleanup_results = self._cleanup_unlisted_agents(
    agents_dir, enabled_agents, preserve_user_agents=True
)
```

### 3. **List Command Reconciliation**

File: `src/claude_mpm/cli/commands/agent_manager.py`

Current (line 94):
```python
def _list_agents(self, args) -> CommandResult:
    """List all agents across tiers with hierarchy."""
    # Scans filesystem only
```

**Change to**:
```python
def _list_agents(self, args) -> CommandResult:
    """List deployed vs configured agents with reconciliation."""

    # 1. Get configured agents
    config = Config.load()
    enabled = config.get("agent_deployment.enabled_agents", [])

    # 2. Scan deployed agents
    deployed = self._scan_deployed_agents()

    # 3. Compare and show diff
    return self._format_reconciliation_view(enabled, deployed)
```

### 4. **Startup Sync Decoupling**

Current: Deployment happens during startup sync (tightly coupled)

**Proposed**: Separate concerns
```python
# Startup flow:
1. startup_sync.py → Sync remote sources to cache (no deployment)
2. agent_deployment.py → Deploy configured agents from cache
3. skills_deployer.py → Deploy skills based on agents + config
```

---

## Migration Path (Backward Compatibility)

### Option A: Dual Mode (Recommended)

Support both models during transition:

```yaml
# configuration.yaml
agent_deployment:
  mode: "profile"  # or "explicit"

  # Profile mode (current behavior)
  profile: framework-development

  # Explicit mode (new behavior)
  enabled_agents:
    - engineer
    - qa
    # ...
```

### Option B: Auto-Migration

On first run with new version:
```python
def migrate_profile_to_explicit(profile_name: str) -> List[str]:
    """Convert profile exclusions to explicit inclusion list."""
    profile = load_profile(profile_name)
    all_agents = discover_all_available_agents()
    excluded = profile.get("agents.excluded", [])

    # Invert: all - excluded = enabled
    enabled = [a for a in all_agents if a not in excluded]

    # Save to configuration
    config.set("agent_deployment.enabled_agents", enabled)
    config.set("agent_deployment.migrated_from_profile", profile_name)
```

### Option C: CLI Migration Command

```bash
$ claude-mpm agent-manager migrate-config \
    --from profile:framework-development \
    --to explicit \
    --preview

Preview of migration:
  Current: profile 'framework-development' excludes 26 agents
  New:     explicit list enables 19 agents

  Enabled agents:
    - engineer
    - qa
    [... list ...]

  Confirm migration? [y/N]
```

---

## Testing Strategy

### Unit Tests

```python
def test_explicit_agent_list_deployment():
    """Test deployment with explicit enabled_agents list."""
    config = {
        "agent_deployment": {
            "enabled_agents": ["engineer", "qa", "research"]
        }
    }

    service = AgentDeploymentService(config=config)
    results = service.deploy_agents()

    assert len(results["deployed"]) == 3
    assert "engineer" in results["deployed"]
    assert "ticketing" not in results["deployed"]

def test_cleanup_unlisted_agents():
    """Test removal of agents not in enabled list."""
    # Setup: Deploy 5 agents
    # Config: enabled_agents = ["engineer", "qa"]
    # Expected: 3 agents removed, 2 kept
    ...

def test_list_shows_configured_vs_deployed():
    """Test list command shows reconciliation view."""
    # Setup: enabled_agents = 19, deployed = 18 (1 missing)
    # Expected: List shows mismatch with explanation
    ...
```

### Integration Tests

```bash
# Test full deployment flow
$ claude-mpm test-deployment-flow \
    --config test-configs/explicit-agents.yaml \
    --verify-cleanup \
    --verify-list-accuracy
```

---

## Recommendation

### Immediate Actions (v5.5.0)

1. **Add reconciliation view to list command**
   - Show configured vs deployed agents
   - Highlight mismatches
   - Provide explanation of current model

2. **Document current model clearly**
   - Update README with tier discovery explanation
   - Add "Understanding Agent Deployment" guide
   - Clarify profile exclusion logic

3. **Add `--show-config` flag to list**
   ```bash
   $ claude-mpm agent-manager list --show-config

   Configuration Source: profile 'framework-development'
   Exclusion List: 26 agents
   Enabled Agents: 19 (all except excluded)
   Deployed: 19 agents in .claude/agents/
   Status: ✓ In sync
   ```

### Future Enhancement (v6.0.0)

4. **Implement explicit inclusion model**
   - New configuration schema
   - Migration command
   - Backward compatibility mode

5. **Simplify deployment logic**
   - Remove multi-tier discovery complexity
   - Single source of truth: `enabled_agents` list
   - Clearer separation: sync vs deploy vs cleanup

6. **Unified configuration file**
   - Consolidate `configuration.yaml` and profiles
   - Or deprecate profiles in favor of explicit lists

---

## Questions for User

1. **Configuration preference**:
   - Keep profiles with exclusion lists?
   - Switch to explicit inclusion lists?
   - Support both modes?

2. **Cleanup behavior**:
   - Auto-remove unlisted agents on every startup?
   - Require explicit `--cleanup` flag?
   - Preserve user-created agents always?

3. **List command behavior**:
   - Show configured agents (from config)?
   - Show deployed agents (from filesystem)?
   - Show both with reconciliation view?

4. **Migration strategy**:
   - Automatic migration on version upgrade?
   - Manual migration command required?
   - Dual-mode support during transition period?

---

## Related Files

### Configuration
- `.claude-mpm/configuration.yaml` - Main configuration
- `.claude-mpm/profiles/framework-development.yaml` - Profile with exclusions (expected but not verified)

### Deployment
- `src/claude_mpm/services/agents/deployment/agent_deployment.py` - Main deployment service
- `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py` - Multi-tier discovery
- `src/claude_mpm/services/agents/startup_sync.py` - Startup sync orchestration

### CLI
- `src/claude_mpm/cli/commands/agent_manager.py` - List command implementation
- `src/claude_mpm/cli/parsers/agents_parser.py` - CLI argument parsing (expected)

### Discovery
- `src/claude_mpm/services/agents/deployment/agent_discovery_service.py` - Template discovery
- `src/claude_mpm/services/agents/git_source_manager.py` - Remote source sync

---

## Conclusion

**The deployment model is NOT broken** - it's functioning as designed. The issue is:

1. **Complexity**: 4-tier discovery, exclusion-based filtering, profile system
2. **Terminology**: Inconsistent use of "deployed", "cached", "listed"
3. **Expectation gap**: User wants simple explicit lists, system uses profile exclusions

**Short-term fix**: Add reconciliation view to `agent-manager list` showing configured vs deployed agents.

**Long-term solution**: Implement explicit inclusion model with migration path from current profile-based exclusions.

**Immediate value**: This research document clarifies the mental model and provides a roadmap for simplification.
