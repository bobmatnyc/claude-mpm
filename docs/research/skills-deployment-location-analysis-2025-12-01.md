# Skills Deployment Location Analysis

**Date**: 2025-12-01
**Researcher**: Research Agent
**Task**: Find where skills are being deployed and determine how to change from user to project directory

## Executive Summary

Skills are currently **hardcoded** to deploy to the **user directory** (`~/.claude/skills/`) in multiple locations throughout the codebase. This differs from the agent deployment model, which uses **user directory only** (`~/.claude/agents/`) for single-tier deployment. To change skills to deploy to project directory, several key files need modification.

## Current Deployment Architecture

### Skills Deployment Flow

```
1. User runs: claude-mpm skills deploy
2. SkillsDeployerService downloads from GitHub
3. Deploys to: ~/.claude/skills/ (HARDCODED)
4. Collections stored in: ~/.claude/skills/{collection_name}/
```

### Agent Deployment Flow (For Comparison)

```
1. User runs: claude-mpm agents deploy
2. SingleTierDeploymentService syncs from Git sources
3. Deploys to: ~/.claude/agents/ (HARDCODED)
4. No project-level deployment option
```

**Key Difference**: Both agents and skills use single-tier deployment to user directory. Neither supports project-level deployment currently.

## Code Locations - Skills Deployment

### 1. SkillsDeployerService (Primary Deployment Logic)

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/skills_deployer.py`

**Line 58**: Hardcoded deployment directory
```python
CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills"
```

**Line 77**: Directory creation
```python
self.CLAUDE_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
```

**Lines used throughout**:
- Line 341-342: Check for existing skills
- Line 378-389: Remove skills operations
- Line 467: Collection deployment target
- Line 697: Individual skill deployment
- Line 761: Path validation

**Docstrings mentioning ~/.claude/skills/**:
- Lines 3, 9, 19, 44, 92, 327, 430, 682, 686

### 2. SkillsService (Bundled Skills Deployment)

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/skills/skills_service.py`

**Line 64**: Deployment path for bundled skills
```python
self.deployed_skills_path: Path = self.project_root / ".claude" / "skills"
```

**Important Note**: This DOES use project root, but only for bundled skills deployed on startup. External skills from GitHub still go to user directory.

### 3. CLI Commands

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/skills.py`

**Line 609**: Display current deployment directory
```python
console.print(f"[dim]Directory: {result['claude_skills_dir']}[/dim]\n")
```

**References to ~/.claude/skills/**:
- Line 16-17: Documentation comments

### 4. CLI Parsers

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/parsers/skills_parser.py`

**Help text references**:
- Line 141: Deploy command help
- Line 189: Check command help
- Line 195: Remove command help

### 5. Skills Registry

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/skills/registry.py`

**Line 124**: User skills directory for registry
```python
user_skills_dir = Path.home() / ".claude" / "skills"
```

**Line 171**: Project skills directory for registry
```python
project_skills_dir = Path.cwd() / ".claude" / "skills"
```

**Note**: Registry already supports BOTH user and project directories for discovery!

### 6. Startup Scripts

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/startup.py`

**Line 97**: Comment about bundled skills deployment
```python
# WHY: Automatically deploy skills from the bundled/ directory to .claude/skills/
```

**Line 153**: Comment about skills discovery
```python
# WHY: Automatically discover and link skills added to .claude/skills/
```

### 7. Interactive Wizards

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/interactive/skills_wizard.py**

**Line 406**: Comment about skills registry reload
```python
# 1. Reload the skills registry (picks up new skills from .claude/skills/)
```

## Code Locations - Agent Deployment (For Comparison)

### Agent Deployment Directory

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/agents.py`

**Line 1691**: Hardcoded agent deployment directory
```python
deployment_dir = Path.home() / ".claude" / "agents"
```

**Line 1779**: Another instance
```python
deployment_dir = Path.home() / ".claude" / "agents"
```

### SingleTierDeploymentService

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/single_tier_deployment_service.py`

**Constructor receives deployment_dir as parameter**:
```python
def __init__(
    self,
    config: AgentSourceConfiguration,
    deployment_dir: Path,  # ← Passed in, not hardcoded in service
    cache_root: Optional[Path] = None,
):
```

**Key Insight**: Agents use **dependency injection** for deployment_dir, while skills use **class constant**.

## Problem Analysis

### Why Skills Deploy to User Directory

1. **Hardcoded Class Constant**: `CLAUDE_SKILLS_DIR` in SkillsDeployerService
2. **No Configuration Option**: Unlike agents, no config parameter for deployment target
3. **Direct Path Construction**: Multiple locations construct `Path.home() / ".claude" / "skills"`
4. **Documentation Assumption**: All docs assume ~/.claude/skills/ deployment

### Differences from Agent Deployment

| Aspect | Agents | Skills |
|--------|--------|--------|
| **Deployment Pattern** | Dependency Injection | Hardcoded Class Constant |
| **Configuration** | Passed to constructor | Not configurable |
| **Tiers** | Single-tier (user only) | Single-tier (user only) |
| **Project Support** | Not supported | Not supported (bundled only) |
| **Discovery** | Single location | Registry supports both user+project |

## Solution Options

### Option 1: Make Skills Deployment Configurable (Recommended)

**Approach**: Follow agent pattern with dependency injection

**Changes Required**:
1. Add `deployment_dir` parameter to `SkillsDeployerService.__init__()`
2. Replace `CLAUDE_SKILLS_DIR` class constant with instance variable
3. Update all CLI commands to pass deployment directory
4. Add configuration option to skills config
5. Update documentation and help text

**Pros**:
- Consistent with agent deployment pattern
- Allows user vs project choice
- Backward compatible (default to user dir)

**Cons**:
- Requires changes in 5+ files
- Need migration path for existing deployments

### Option 2: Add Project-Level Skills Support

**Approach**: Two-tier deployment like old agent system

**Changes Required**:
1. Add project detection logic
2. Implement priority resolution (project > user)
3. Update discovery and registry to merge sources
4. Add CLI flag for deployment target

**Pros**:
- Full project-level skills support
- Better isolation per project

**Cons**:
- Much larger change scope
- Reintroduces complexity removed from agents
- May not be needed (agents don't support this)

### Option 3: Hybrid - Bundled to Project, External to User

**Approach**: Keep current architecture, clarify intentions

**Changes Required**:
1. Document that external skills go to user directory (global)
2. Document that bundled skills go to project directory (local)
3. Add note explaining design decision

**Pros**:
- No code changes needed
- Clear separation of concerns
- Matches current behavior

**Cons**:
- User expectations may differ
- Less flexible than Option 1

## Recommended Implementation Plan

### Phase 1: Add Deployment Directory Parameter

**Target**: Make SkillsDeployerService accept deployment_dir parameter

1. **Update SkillsDeployerService constructor**:
```python
def __init__(
    self,
    repo_url: Optional[str] = None,
    toolchain_analyzer: Optional[any] = None,
    deployment_dir: Optional[Path] = None,  # ← Add this
):
    super().__init__()
    self.repo_url = repo_url or self.DEFAULT_REPO_URL
    self.toolchain_analyzer = toolchain_analyzer
    self.skills_config = SkillsConfig()

    # Use provided deployment_dir or default to user directory
    self.deployment_dir = deployment_dir or (Path.home() / ".claude" / "skills")
    self.deployment_dir.mkdir(parents=True, exist_ok=True)
```

2. **Replace all CLAUDE_SKILLS_DIR references** with `self.deployment_dir`

3. **Update CLI commands** to pass deployment directory:
```python
# In cli/commands/skills.py
def _deploy_skills(self, args) -> CommandResult:
    # Determine deployment directory
    if args.project:  # New --project flag
        deployment_dir = Path.cwd() / ".claude" / "skills"
    else:
        deployment_dir = Path.home() / ".claude" / "skills"

    deployer = SkillsDeployerService(deployment_dir=deployment_dir)
    result = deployer.deploy_skills(...)
```

### Phase 2: Add Configuration Support

**Target**: Add skills deployment directory to config

1. **Add to skills config** (config/skills.yaml or similar):
```yaml
skills:
  deployment_target: "user"  # or "project"
  user_dir: "~/.claude/skills"
  project_dir: ".claude/skills"
```

2. **Update SkillsConfig** to read deployment preferences

3. **CLI respects config** but allows override with flags

### Phase 3: Update Documentation

**Target**: Document new deployment options

1. Update all references to ~/.claude/skills/
2. Add examples for user vs project deployment
3. Document migration from user to project directory
4. Update CLI help text

## File Modification Checklist

### Core Changes (Phase 1)

- [ ] `/src/claude_mpm/services/skills_deployer.py` (Lines: 58, 77, 341, 378, 467, 697, 761)
  - Convert `CLAUDE_SKILLS_DIR` class constant to `deployment_dir` instance variable
  - Add `deployment_dir` parameter to `__init__()`
  - Update all 7+ references to use `self.deployment_dir`

- [ ] `/src/claude_mpm/cli/commands/skills.py` (Line: 609, others)
  - Update `_deploy_skills()` to construct deployment_dir based on flags
  - Pass deployment_dir to SkillsDeployerService constructor
  - Add --project flag to deploy to project directory

- [ ] `/src/claude_mpm/skills/registry.py` (Lines: 124, 171)
  - Already supports both user and project - no changes needed
  - May want to add priority logic if both exist

### Documentation Updates (Phase 3)

- [ ] `/src/claude_mpm/services/skills_deployer.py` (Docstrings: Lines 3, 9, 19, 44, 92, 327, 430, 682, 686)
- [ ] `/src/claude_mpm/cli/parsers/skills_parser.py` (Help text: Lines 141, 189, 195)
- [ ] `/src/claude_mpm/cli/startup.py` (Comments: Lines 97, 153)
- [ ] `/src/claude_mpm/cli/interactive/skills_wizard.py` (Comments: Line 406)
- [ ] `/src/claude_mpm/agents/templates/research.md` (Lines: 152, 1003)

### Optional Changes

- [ ] `/src/claude_mpm/skills/skills_service.py` (Line 64)
  - Already uses project_root for bundled skills - works correctly
  - May want to align with new deployment_dir pattern

## Testing Strategy

### Unit Tests

1. Test SkillsDeployerService with different deployment_dir values
2. Test path validation for user vs project directories
3. Test backward compatibility (no deployment_dir provided)

### Integration Tests

1. Deploy skills to user directory
2. Deploy skills to project directory
3. Verify skills registry finds skills in both locations
4. Test conflict resolution (same skill in both locations)

### Manual Testing

1. `claude-mpm skills deploy` → deploys to ~/.claude/skills/
2. `claude-mpm skills deploy --project` → deploys to .claude/skills/
3. Verify Claude Code can load from both locations
4. Test multi-collection deployment to different targets

## Migration Path

### For Existing Users

**Current State**: All skills in ~/.claude/skills/

**Migration Options**:

1. **No Migration**: Keep using user directory (default)
2. **Copy to Project**: `cp -r ~/.claude/skills/ .claude/skills/`
3. **Symlink**: `ln -s ~/.claude/skills/ .claude/skills/`

**Recommended**: Document both options, let users choose based on needs.

## Related Work

### Agent Deployment Research

**Reference**: Similar analysis for agents would show:
- Agents moved FROM multi-tier TO single-tier (user only)
- Design decision: Simplified to user directory only
- Rationale: Reduced complexity without losing functionality

**Question**: Should skills follow same pattern?

**Answer**: Probably yes - single-tier (user) is simpler and matches agent pattern. But adding configurability doesn't hurt.

## Risks and Mitigation

### Risk 1: Breaking Existing Deployments

**Mitigation**: Default to ~/.claude/skills/ for backward compatibility

### Risk 2: Claude Code Compatibility

**Mitigation**: Test that Claude Code loads from both locations

### Risk 3: Collection Management Complexity

**Mitigation**: Collections stay in user directory, individual skills can be copied to project

### Risk 4: Path Traversal Security

**Mitigation**: Already have `_validate_safe_path()` - ensure it works with new paths

## Open Questions

1. **Should collections be stored in user or project directory?**
   - Current: User directory only
   - Proposed: Keep in user, copy skills to project if needed

2. **How to handle updates for project-deployed skills?**
   - Option A: Update requires re-deploy
   - Option B: Skills in project are snapshots, don't auto-update

3. **Should we support both user and project simultaneously?**
   - Like skills registry already does for discovery
   - Priority: Project > User (for conflict resolution)

4. **Do we need this feature at all?**
   - Agents don't support project-level deployment
   - Why should skills be different?
   - **Counter**: Agents are global tools, skills might be project-specific

## Conclusion

**Current Deployment**:
- Skills deploy to `~/.claude/skills/` (hardcoded in 7+ locations)
- No configuration option exists
- Different from agent pattern (which uses dependency injection)

**To Change to Project Directory**:
1. Add `deployment_dir` parameter to SkillsDeployerService
2. Update CLI to pass project directory: `Path.cwd() / ".claude" / "skills"`
3. Update documentation and help text
4. Test both user and project deployment

**Recommended Approach**:
- Follow **Option 1** (dependency injection pattern)
- Make deployment directory configurable
- Default to user directory for backward compatibility
- Add `--project` flag for project-level deployment
- Update 7+ files with code changes
- Update 10+ files with documentation

**Timeline Estimate**:
- Phase 1 (Core): 2-3 hours
- Phase 2 (Config): 1-2 hours
- Phase 3 (Docs): 1-2 hours
- Testing: 2-3 hours
- **Total**: 6-10 hours

**Priority**: Medium (Nice to have, not critical)

## References

- Design Doc: `docs/design/claude-mpm-skills-integration-design.md`
- SKILL.md Spec: `docs/design/SKILL-MD-FORMAT-SPECIFICATION.md`
- Agent Deployment: `src/claude_mpm/services/agents/single_tier_deployment_service.py`
- Skills Registry: `src/claude_mpm/skills/registry.py`
