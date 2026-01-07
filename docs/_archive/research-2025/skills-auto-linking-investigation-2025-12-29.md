# Skills Auto-Linking to Deployed Agents Investigation

**Research Date:** 2025-12-29
**Researcher:** Research Agent
**Objective:** Investigate current skill-agent linking mechanism and identify implementation path for auto-linking skills to deployed agents with cleanup of non-linked skills

---

## Executive Summary

**Current State:**
- Skills ARE already linked to agents via the `skills` field in agent JSON templates
- Skills deployment uses **selective deployment** based on agent requirements
- Two-source skill discovery: explicit frontmatter + SkillToAgentMapper inference
- User override mechanism exists via `configuration.yaml` (user_defined vs agent_referenced)
- Orphan cleanup logic ALREADY exists in `selective_skill_deployer.py`

**Key Finding:** The requested functionality (auto-link skills to agents and cleanup non-linked skills) **is already implemented** in the selective deployment system. The gap is in **enforcing** selective deployment by default and removing the `--all-skills` escape hatch.

**Recommendation:**
1. Make selective deployment the ONLY mode (remove `--all-skills` flag)
2. Enhance user communication about what skills were auto-detected
3. Add CLI command to show agent-to-skill mapping
4. Improve user override workflow in `skills configure` command

---

## 1. Current Architecture

### 1.1 Agent-Skill Linking Mechanism

**Location:** Agent JSON templates have explicit `skills` field

**Example:** `/src/claude_mpm/agents/templates/archive/engineer.json`
```json
{
  "agent_id": "engineer",
  "skills": [
    "test-driven-development",
    "systematic-debugging",
    "async-testing",
    "performance-profiling",
    "security-scanning",
    "api-documentation",
    "git-workflow",
    "code-review",
    "refactoring-patterns",
    "database-migration",
    "docker-containerization"
  ]
}
```

**Format:** Flat list of skill names (kebab-case)

**Injection Point:** `AgentSkillsInjector` enhances agent templates at runtime:
- Reads skills from SkillsService registry
- Adds `skills` field to agent JSON
- Generates YAML frontmatter with skills
- Injects skills documentation into agent markdown

### 1.2 Skill Discovery (Dual-Source)

**Service:** `SelectiveSkillDeployer` (`src/claude_mpm/services/skills/selective_skill_deployer.py`)

**Two discovery sources:**

1. **Explicit Frontmatter Declarations** (`get_skills_from_agent()`)
   - Parses YAML frontmatter from deployed agents (`.claude/agents/*.md`)
   - Supports legacy format: `skills: [skill-a, skill-b]`
   - Supports new format: `skills: {required: [...], optional: [...]}`
   - Extracts union of required + optional skills

2. **SkillToAgentMapper Inference** (`get_skills_from_mapping()`)
   - Pattern-based skill discovery using YAML configuration
   - Maps skill paths to agent IDs: `toolchains/python/frameworks/django → [python-engineer, engineer]`
   - Inference rules for language, framework, domain patterns
   - Configuration: `/src/claude_mpm/config/skill_to_agent_mapping.yaml`

**Combined Result:** Union of explicit + inferred skills (normalized to kebab-case)

### 1.3 Skill Deployment Flow

**Entry Point:** `claude-mpm skills deploy-github` command

**Key Flag:** `--all-skills` (disables selective deployment)

**Deployment Logic:**
```python
# In skills.py CLI command (line 567)
selective=not all_skills  # Selective mode enabled by default, disabled with --all-skills
```

**Selective Deployment Service:** `SkillsDeployerService`
```python
def deploy_skills(
    collection=None,
    toolchain=None,
    categories=None,
    force=False,
    selective=True  # Default: only deploy agent-referenced skills
):
    if selective:
        required_skills = get_required_skills_from_agents(agents_dir)
        # Deploy ONLY skills in required_skills
    else:
        # Deploy ALL available skills (current escape hatch)
```

### 1.4 Orphan Cleanup Logic

**Function:** `cleanup_orphan_skills()` in `selective_skill_deployer.py` (lines 376-479)

**Cleanup Algorithm:**
1. Load deployment tracking index (`.mpm-deployed-skills.json`)
2. Identify orphaned skills: `tracked - (required ∪ user_requested)`
3. Remove orphaned skill directories from `~/.claude/skills/`
4. Update deployment index

**Protection:** User-requested skills NEVER cleaned up (treated as required)

**Deployment Index Structure:**
```json
{
  "deployed_skills": {
    "skill-name": {
      "collection": "claude-mpm-skills",
      "deployed_at": "2025-12-22T10:30:00Z"
    }
  },
  "user_requested_skills": ["skill-a", "skill-b"],
  "last_sync": "2025-12-22T10:30:00Z"
}
```

---

## 2. User Override Mechanism

### 2.1 Configuration Structure

**File:** `.claude-mpm/configuration.yaml`

**Skills Section:**
```yaml
skills:
  agent_referenced: []  # Auto-populated from agent scan (read-only)
  user_defined: []      # User override - if non-empty, ONLY these are deployed
```

**Priority Logic:** `get_skills_to_deploy()` in `selective_skill_deployer.py` (lines 531-578)
```python
if user_defined:
    return (user_defined, "user_defined")
else:
    return (agent_referenced, "agent_referenced")
```

### 2.2 Interactive Configuration

**Command:** `claude-mpm skills configure`

**Workflow:**
1. Display current mode (user_defined vs agent_referenced)
2. Offer mode switching:
   - View current skills
   - Switch to user mode (manual selection)
   - Reset to agent mode (auto-detection)
3. If user mode: checkbox-based skill selection from GitHub
4. Save to `configuration.yaml`
5. Prompt to run `claude-mpm init` to deploy

**Implementation:** `/src/claude_mpm/cli/commands/skills.py` lines 974-1227

---

## 3. Gap Analysis

### 3.1 What Works

✅ **Agent-skill linking exists** via `skills` field in JSON templates
✅ **Selective deployment implemented** (dual-source discovery)
✅ **Orphan cleanup logic exists** (`cleanup_orphan_skills()`)
✅ **User override mechanism works** (configuration.yaml)
✅ **Deployment tracking** (`.mpm-deployed-skills.json` index)

### 3.2 What Doesn't Work

❌ **Selective deployment is optional** (`--all-skills` flag exists)
❌ **Cleanup not enforced by default** (user must explicitly trigger)
❌ **Poor visibility** of what skills were auto-detected
❌ **No agent-to-skill mapping CLI command** (hard to debug)
❌ **Skills configure UX** doesn't show agent-scanned skills clearly

### 3.3 User Request Interpretation

**What user likely wants:**
1. **Default behavior:** Only deploy skills linked to deployed agents (no `--all-skills`)
2. **Automatic cleanup:** Remove orphaned skills on every deployment
3. **Better visibility:** Show which skills were detected from which agents
4. **Override mechanism:** Keep user_defined override for power users

**What user likely DOESN'T want:**
- Complete removal of manual skill selection (breaks power user workflows)
- Breaking change for existing projects with manually-deployed skills

---

## 4. Implementation Recommendations

### 4.1 High Priority Changes

#### A. Remove `--all-skills` Flag (Breaking Change)

**File:** `src/claude_mpm/cli/commands/skills.py`

**Current (line 567):**
```python
selective=not all_skills  # Disable selective mode if --all-skills is set
```

**Proposed:**
```python
selective=True  # ALWAYS use selective deployment (no escape hatch)
```

**Impact:** Forces selective deployment for all users (breaking change)

**Migration Path:** Users who need all skills must use `user_defined` in configuration.yaml

---

#### B. Enable Automatic Cleanup on Deploy

**File:** `src/claude_mpm/services/skills_deployer.py`

**Add to `deploy_skills()` method:**
```python
def deploy_skills(
    collection=None,
    toolchain=None,
    categories=None,
    force=False
):
    # ... existing deployment logic ...

    # NEW: Automatic cleanup after deployment
    from .skills.selective_skill_deployer import cleanup_orphan_skills
    from pathlib import Path

    claude_skills_dir = Path.home() / ".claude" / "skills"
    required_skills = set(deployed_skills)  # Skills just deployed

    cleanup_result = cleanup_orphan_skills(claude_skills_dir, required_skills)

    if cleanup_result["removed_count"] > 0:
        console.print(f"\n[yellow]🧹 Cleaned up {cleanup_result['removed_count']} orphaned skills[/yellow]")
        for skill in cleanup_result["removed_skills"]:
            console.print(f"  • {skill}")
```

---

#### C. Add Agent-to-Skill Mapping CLI Command

**New Command:** `claude-mpm skills show-mapping [--agent AGENT_ID]`

**Implementation:**
```python
def _show_mapping(self, args) -> CommandResult:
    """Show agent-to-skill mapping for debugging."""
    from ...services.skills.selective_skill_deployer import (
        get_required_skills_from_agents,
        parse_agent_frontmatter,
        get_skills_from_agent
    )
    from pathlib import Path

    agents_dir = Path.cwd() / ".claude" / "agents"
    agent_filter = getattr(args, "agent", None)

    # Scan agents
    agent_files = list(agents_dir.glob("*.md"))

    console.print("\n[bold cyan]Agent-to-Skill Mapping:[/bold cyan]\n")

    for agent_file in sorted(agent_files):
        agent_id = agent_file.stem

        if agent_filter and agent_id != agent_filter:
            continue

        frontmatter = parse_agent_frontmatter(agent_file)
        skills = get_skills_from_agent(frontmatter)

        console.print(f"[green]{agent_id}[/green] ({len(skills)} skills)")
        for skill in sorted(skills):
            console.print(f"  • {skill}")
        console.print()

    return CommandResult(success=True, exit_code=0)
```

---

#### D. Improve `skills configure` UX

**Enhancement:** Show agent-scanned skills with agent attribution

**Current UX:**
```
Switching to User Mode - Manual Skill Selection
Fetching available skills from GitHub...
```

**Proposed UX:**
```
Switching to User Mode - Manual Skill Selection

Currently deployed agents require these skills:
  engineer (11 skills):
    • test-driven-development
    • systematic-debugging
    • ...

  python-engineer (8 skills):
    • python-style
    • pydantic
    • ...

Total agent-scanned skills: 28 unique skills

Would you like to:
  [1] Keep agent-scanned skills (recommended)
  [2] Customize skill selection
  [3] Cancel
```

---

### 4.2 Medium Priority Changes

#### E. Add Deployment Summary

**Enhancement:** Show which agents required which skills during deployment

**Example Output:**
```
✓ Deployed 28 skills based on agent requirements:

Agent Requirements:
  engineer → 11 skills (test-driven-development, systematic-debugging, ...)
  python-engineer → 8 skills (python-style, pydantic, ...)
  typescript-engineer → 6 skills (typescript-core, nextjs-core, ...)

Deployment Mode: agent_referenced (auto-detected)
Override: Use `claude-mpm skills configure` to manually select skills
```

---

#### F. Add Skill Audit Command

**New Command:** `claude-mpm skills audit`

**Purpose:** Show deployment status, orphans, and recommendations

**Example Output:**
```
Skills Deployment Audit

Deployed: 28 skills
  ✓ 25 required by agents
  ✓ 3 user-requested
  ⚠️  5 orphaned (no longer required)

Orphaned Skills:
  • old-skill-a (deployed 30 days ago, no agent references)
  • old-skill-b (deployed 45 days ago, no agent references)

Recommendations:
  [1] Run cleanup: claude-mpm skills cleanup
  [2] Review user-requested skills: claude-mpm skills configure
```

---

### 4.3 Low Priority Changes

#### G. Enhanced Logging

**Add debug logging throughout selective deployment:**
```python
logger.debug(f"Scanning agent {agent_id}: found {len(agent_skills)} explicit skills")
logger.debug(f"Mapper inference for {agent_id}: {len(mapped_skills)} skills")
logger.info(f"Combined skills for {agent_id}: {len(combined_skills)} unique skills")
```

---

#### H. Configuration Schema Validation

**Add validation to ensure configuration.yaml schema is correct:**
```python
def validate_skills_config(config_path: Path) -> bool:
    """Validate skills section in configuration.yaml."""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    if "skills" not in config:
        return False

    skills_config = config["skills"]

    # Ensure required keys exist
    if "agent_referenced" not in skills_config:
        logger.warning("Missing skills.agent_referenced in configuration.yaml")
        skills_config["agent_referenced"] = []

    if "user_defined" not in skills_config:
        logger.warning("Missing skills.user_defined in configuration.yaml")
        skills_config["user_defined"] = []

    # Validate types
    if not isinstance(skills_config["agent_referenced"], list):
        logger.error("skills.agent_referenced must be a list")
        return False

    if not isinstance(skills_config["user_defined"], list):
        logger.error("skills.user_defined must be a list")
        return False

    return True
```

---

## 5. Key Files to Modify

### 5.1 Primary Files

| File | Lines | Purpose | Change Type |
|------|-------|---------|-------------|
| `src/claude_mpm/cli/commands/skills.py` | 567, 974-1227 | CLI commands | Modify |
| `src/claude_mpm/services/skills_deployer.py` | deploy_skills() | Add auto-cleanup | Modify |
| `src/claude_mpm/services/skills/selective_skill_deployer.py` | 376-479 | Cleanup logic | Use existing |
| `src/claude_mpm/config/skill_to_agent_mapping.yaml` | All | Mapping config | No change |

### 5.2 Testing Files

| File | Purpose |
|------|---------|
| `tests/services/skills/test_selective_skill_deployer.py` | Test cleanup logic |
| `tests/services/skills/test_skill_to_agent_mapper.py` | Test mapping inference |

---

## 6. Migration Path

### 6.1 Breaking Changes

**Change:** Remove `--all-skills` flag from `claude-mpm skills deploy-github`

**Impact:** Users who rely on deploying ALL skills must migrate to user_defined mode

**Migration Steps:**
1. Run `claude-mpm skills deploy-github --all-skills` one last time (before upgrade)
2. Upgrade to new version
3. Run `claude-mpm skills configure`
4. Select "Switch to user mode"
5. Select all desired skills
6. Run `claude-mpm init` to deploy

### 6.2 Deprecation Timeline

**Phase 1 (Recommended):** Deprecation warning
- Keep `--all-skills` flag but show deprecation warning
- Warning: "Flag --all-skills is deprecated and will be removed in v6.0.0. Use `claude-mpm skills configure` instead."
- Target: v5.5.x releases

**Phase 2:** Removal
- Remove `--all-skills` flag entirely
- Force selective deployment
- Target: v6.0.0

---

## 7. Testing Strategy

### 7.1 Unit Tests

**Test selective deployment logic:**
```python
def test_selective_deployment_only_deploys_agent_referenced():
    """Ensure selective mode deploys ONLY agent-scanned skills."""
    # Setup: Deploy agents with specific skills
    # Act: Deploy with selective=True
    # Assert: Only agent-scanned skills deployed
    pass

def test_cleanup_removes_orphaned_skills():
    """Ensure cleanup removes skills not referenced by agents."""
    # Setup: Deploy extra skills manually
    # Act: Run cleanup with current agent requirements
    # Assert: Orphaned skills removed
    pass

def test_user_requested_skills_never_cleaned():
    """Ensure user_requested skills protected from cleanup."""
    # Setup: Add skill to user_requested_skills
    # Act: Run cleanup without agent references
    # Assert: User-requested skill still present
    pass
```

### 7.2 Integration Tests

**Test end-to-end workflow:**
```python
def test_deploy_with_agent_detection():
    """Test full deployment with agent-based detection."""
    # 1. Deploy agents with skills
    # 2. Run skills deploy (selective)
    # 3. Verify correct skills deployed
    # 4. Verify cleanup removed orphans
    pass

def test_user_override_workflow():
    """Test user_defined override mechanism."""
    # 1. Set user_defined in configuration.yaml
    # 2. Run skills deploy
    # 3. Verify user_defined skills deployed (not agent_referenced)
    pass
```

---

## 8. Risks and Mitigation

### 8.1 Risk: Breaking Existing Workflows

**Risk:** Users who rely on `--all-skills` flag will break

**Mitigation:**
- Deprecation warning in v5.5.x
- Clear migration guide in CHANGELOG
- Auto-migration helper: `claude-mpm skills migrate`

### 8.2 Risk: Over-Aggressive Cleanup

**Risk:** Cleanup removes skills user manually deployed

**Mitigation:**
- User-requested skills protection (already implemented)
- Dry-run mode: `claude-mpm skills cleanup --dry-run`
- Confirmation prompt before cleanup

### 8.3 Risk: Deployment Index Corruption

**Risk:** `.mpm-deployed-skills.json` becomes corrupted

**Mitigation:**
- Graceful fallback to empty index
- Validate index on load
- Backup index before modifications

---

## 9. Documentation Updates

### 9.1 User Documentation

**New Docs Needed:**
- "Skills Auto-Linking Guide" (how it works, how to override)
- "Migrating from --all-skills" (breaking change guide)
- "Skills Configuration Reference" (configuration.yaml schema)

### 9.2 CLI Help Text

**Update help text for:**
- `claude-mpm skills deploy-github` (remove --all-skills, explain selective)
- `claude-mpm skills configure` (explain agent mode vs user mode)
- `claude-mpm skills audit` (new command)
- `claude-mpm skills show-mapping` (new command)

---

## 10. Success Metrics

### 10.1 Behavioral Metrics

**Target:**
- 85% of deployments use agent-referenced mode (up from current unknown%)
- <5% of users manually override with user_defined
- 100% of orphaned skills cleaned up within 1 deployment cycle

### 10.2 Code Quality Metrics

**Target:**
- Test coverage for selective deployment: 90%+
- Zero breaking changes without deprecation warnings
- <3 bug reports related to skill cleanup in first month

---

## 11. Conclusion

**Summary:** The requested functionality (auto-link skills to agents and cleanup non-linked skills) is **already implemented** via the selective deployment system. The main gap is **enforcement** (making selective deployment the default and only mode).

**Recommended Implementation Path:**

1. **Immediate (v5.5.x):**
   - Add deprecation warning for `--all-skills` flag
   - Add `claude-mpm skills show-mapping` command
   - Enhance `skills configure` UX with agent attribution

2. **Breaking (v6.0.0):**
   - Remove `--all-skills` flag
   - Enable automatic cleanup on every deployment
   - Add `claude-mpm skills audit` command

3. **Future Enhancements:**
   - Auto-migration helper (`claude-mpm skills migrate`)
   - Dry-run mode for cleanup
   - Configuration schema validation

**Effort Estimate:**
- Immediate changes: 4-6 hours
- Breaking changes: 3-4 hours
- Testing: 4-6 hours
- Documentation: 2-3 hours
- **Total: 13-19 hours**

**Risk Level:** Medium (breaking change requires careful migration planning)

**Value:** High (simplifies skills management, reduces clutter, enforces best practices)

---

## Appendices

### A. Current Selective Deployment Data Flow

```
User runs: claude-mpm skills deploy-github
    ↓
CLI extracts --all-skills flag
    ↓
Calls SkillsDeployerService.deploy_skills(selective=not all_skills)
    ↓
IF selective=True:
    ↓
    Get required skills from agents (dual-source):
        ↓
        1. Scan .claude/agents/*.md frontmatter
        2. Query SkillToAgentMapper for inference
        3. Combine: required_skills = frontmatter ∪ mapped
    ↓
    Filter available skills by required_skills
    ↓
    Deploy ONLY required skills
    ↓
    (Optional) Cleanup orphaned skills
ELSE:
    ↓
    Deploy ALL available skills (current escape hatch)
```

### B. SkillToAgentMapper Configuration Sample

```yaml
skill_mappings:
  toolchains/python/frameworks/django:
    - python-engineer
    - data-engineer
    - engineer

  toolchains/typescript/frameworks/nextjs:
    - typescript-engineer
    - nextjs-engineer
    - engineer

inference_rules:
  language_patterns:
    python: [python-engineer, data-engineer, engineer]
    typescript: [typescript-engineer, engineer]

  framework_patterns:
    django: [python-engineer, engineer]
    nextjs: [typescript-engineer, nextjs-engineer]

all_agents_list:
  - engineer
  - python-engineer
  - typescript-engineer
  - ... (all agent IDs)
```

### C. Deployment Index Schema

**File:** `~/.claude/skills/.mpm-deployed-skills.json`

```json
{
  "deployed_skills": {
    "test-driven-development": {
      "collection": "claude-mpm-skills",
      "deployed_at": "2025-12-22T10:30:00Z"
    },
    "systematic-debugging": {
      "collection": "claude-mpm-skills",
      "deployed_at": "2025-12-22T10:30:00Z"
    }
  },
  "user_requested_skills": [
    "manual-skill-a",
    "manual-skill-b"
  ],
  "last_sync": "2025-12-22T10:30:00Z"
}
```

**Purpose:**
- Track which skills claude-mpm deployed
- Protect user-requested skills from cleanup
- Enable orphan detection

---

## References

- Agent Skills Injector: `src/claude_mpm/skills/agent_skills_injector.py`
- Selective Skill Deployer: `src/claude_mpm/services/skills/selective_skill_deployer.py`
- Skill-to-Agent Mapper: `src/claude_mpm/services/skills/skill_to_agent_mapper.py`
- Skills CLI Commands: `src/claude_mpm/cli/commands/skills.py`
- Mapping Configuration: `src/claude_mpm/config/skill_to_agent_mapping.yaml`
- Configuration Schema: `.claude-mpm/configuration.yaml` (skills section)

---

**End of Investigation Report**
