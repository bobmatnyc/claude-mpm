# PM Framework Skills Architecture Research

**Date**: 2026-01-07
**Research Focus**: Framework-level PM skills storage and loading pattern
**Context**: Understanding how PM skills are bundled with claude-mpm framework

## Executive Summary

PM skills are framework-level skills that ALWAYS deploy with the PM agent, distinct from optional project-level skills. They are stored in the source code and automatically deployed to projects during initialization.

## Key Findings

### 1. Storage Location

Framework PM skills are stored in:

```
/Users/masa/Projects/claude-mpm/src/claude_mpm/skills/bundled/pm/
```

**Current PM Skills** (7 total):
- `pm-bug-reporting/` - Bug reporting workflows
- `pm-delegation-patterns/` - Common delegation templates
- `pm-git-file-tracking/` - Git file tracking protocol
- `pm-pr-workflow/` - Branch protection and PR workflows
- `pm-teaching-mode/` - Teaching mode interactions
- `pm-ticketing-integration/` - Ticket-driven development
- `pm-verification-protocols/` - QA verification requirements

### 2. Skill File Structure

**Directory Structure** (new format):
```
pm-git-file-tracking/
└── SKILL.md          # Skill content with frontmatter
```

**Frontmatter Format**:
```yaml
---
name: pm-git-file-tracking
version: "1.0.0"
description: Protocol for tracking files immediately after agent creation
when_to_use: after agent creates files, before marking todo complete, git operations
category: pm-workflow
tags: [git, file-tracking, workflow, pm-required]
---

# Skill content here
```

**Legacy Format** (fallback support):
```
skill-name.md         # Flat file in .claude-mpm/templates/
```

### 3. Deployment Architecture

**Source → Deployment Flow**:

```
Package Installation:
src/claude_mpm/skills/bundled/pm/
    └── pm-git-file-tracking/SKILL.md

↓ (deployment via PMSkillsDeployerService)

Project Initialization:
.claude-mpm/skills/pm/
    └── pm-git-file-tracking.md     # Deployed copy
```

**Deployment Service**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/pm_skills_deployer.py`

**Key Operations**:
1. **Discovery**: Scan `skills/bundled/pm/` for skill directories
2. **Deployment**: Copy `SKILL.md` → `.claude-mpm/skills/pm/{name}.md`
3. **Registry**: Track versions in `.claude-mpm/pm_skills_registry.yaml`
4. **Verification**: Checksum validation for integrity
5. **Updates**: Detect and deploy updated skills

### 4. PM Instructions Integration

**Reference Location**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`

**Loading Pattern** - Skills referenced inline with marker:

```markdown
## PM Skills System

PM instructions are enhanced by dynamically-loaded skills from `.claude-mpm/skills/pm/`.

**Available PM Skills:**
- `pm-git-file-tracking` - Git file tracking protocol
- `pm-pr-workflow` - Branch protection and PR creation
- `pm-ticketing-integration` - Ticket-driven development
- `pm-delegation-patterns` - Common workflow patterns
- `pm-verification-protocols` - QA verification requirements

Skills are loaded automatically when relevant context is detected.
```

**Inline References** - Skills invoked in context:

```markdown
## Git File Tracking Protocol

**[SKILL: pm-git-file-tracking]**

Track files IMMEDIATELY after an agent creates them.
See pm-git-file-tracking skill for complete protocol.

**Key points:**
- BLOCKING: Cannot mark todo complete until files tracked
- Run `git status` → `git add` → `git commit` sequence
```

**Pattern**:
- PM instructions provide high-level overview
- Detailed protocols delegated to skill files
- Skills referenced via `**[SKILL: skill-name]**` marker
- Context-aware loading (skills activated when relevant)

### 5. Version Tracking and Updates

**Registry File**: `.claude-mpm/pm_skills_registry.yaml`

**Registry Structure**:
```yaml
version: "1.0.0"
deployed_at: "2026-01-07T10:30:00Z"
skills:
  - name: pm-git-file-tracking
    version: "1.0.0"
    deployed_at: "2026-01-07T10:30:00Z"
    checksum: "sha256_hash_here"
```

**Update Detection**:
- Checksum comparison (bundled vs deployed)
- Version mismatch detection
- Missing skill detection
- Automatic update on `claude-mpm init`

### 6. Security and Validation

**Path Traversal Protection**:
```python
def _validate_safe_path(self, base: Path, target: Path) -> bool:
    """Ensure target path is within base directory."""
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False
```

**YAML Bomb Prevention**:
```python
MAX_YAML_SIZE = 10 * 1024 * 1024  # 10MB limit
```

**Checksum Validation**:
```python
def _compute_checksum(self, file_path: Path) -> str:
    """Compute SHA256 checksum of file content."""
    sha256 = hashlib.sha256()
    # Read in 64KB chunks for large files
    ...
```

## Pattern for Adding New Framework PM Skill

### Step 1: Create Skill Directory

```bash
cd /Users/masa/Projects/claude-mpm/src/claude_mpm/skills/bundled/pm/

mkdir pm-new-skill-name
cd pm-new-skill-name
touch SKILL.md
```

### Step 2: Write Skill Content

**File**: `pm-new-skill-name/SKILL.md`

```markdown
---
name: pm-new-skill-name
version: "1.0.0"
description: Brief description of skill purpose
when_to_use: trigger conditions, keywords, scenarios
category: pm-workflow
tags: [tag1, tag2, pm-required]
---

# Skill Title

**Critical Principle**: Core concept or rule

## Section 1: Protocol Details

Detailed instructions...

## Section 2: Examples

```bash
# Example commands
```

## Section 3: Integration

How this skill integrates with other PM workflows...
```

### Step 3: Reference in PM_INSTRUCTIONS.md

**Update skill list** (line 48-54):
```markdown
**Available PM Skills:**
- `pm-git-file-tracking` - Git file tracking protocol
- `pm-pr-workflow` - Branch protection and PR creation
- `pm-ticketing-integration` - Ticket-driven development
- `pm-delegation-patterns` - Common workflow patterns
- `pm-verification-protocols` - QA verification requirements
- `pm-new-skill-name` - Brief description         # ADD HERE
```

**Add inline reference** (in relevant section):
```markdown
## Relevant Section

**[SKILL: pm-new-skill-name]**

Brief overview with reference to skill.
See pm-new-skill-name skill for complete protocol.

**Key points:**
- Critical point 1
- Critical point 2
```

### Step 4: Deploy and Test

```bash
# Deploy to project
cd /path/to/test/project
claude-mpm init

# Verify deployment
ls -la .claude-mpm/skills/pm/
cat .claude-mpm/pm_skills_registry.yaml

# Check skill is loaded
grep -r "pm-new-skill-name" .claude-mpm/
```

### Step 5: Update Documentation

Add to changelog, update version in `pm_skills_deployer.py` if needed.

## Architecture Decisions

### Why Bundle PM Skills with Framework?

**Rationale**:
1. **Consistency**: All PM agents follow same protocols
2. **Versioning**: Skills update with framework
3. **Quality**: Framework-maintained quality standards
4. **Deployment**: Zero-config deployment to projects

**Trade-offs**:
- ✅ Always available, no manual setup
- ✅ Version-tracked and validated
- ❌ Requires framework update to change skills
- ❌ Cannot customize without forking

### Why Separate from Project Skills?

**Project Skills** (`.claude/skills/`):
- User-created or community-contributed
- Project-specific knowledge
- Optional, customizable
- Managed via skill-creator skill

**Framework PM Skills** (`.claude-mpm/skills/pm/`):
- Framework-maintained
- PM operational protocols
- Required for PM functionality
- Managed via pm_skills_deployer service

**Separation Benefits**:
- Clear ownership boundaries
- Independent lifecycle management
- Framework skills guaranteed available
- Project skills don't interfere with PM operation

### Why Directory Structure vs Flat Files?

**Directory Structure** (preferred):
```
pm-skill-name/
├── SKILL.md          # Main skill content
├── examples/         # Future: Example files
└── tests/            # Future: Validation tests
```

**Advantages**:
- Scalable for complex skills
- Room for future enhancements
- Clear skill boundaries
- Consistent with skill-creator pattern

**Legacy Flat Files** (fallback):
```
skill-name.md
```

**Why Keep Legacy Support**:
- Backward compatibility
- Smooth migration path
- Development mode support
- Graceful degradation

## Key Files Reference

| File | Purpose | Path |
|------|---------|------|
| PM Skills Storage | Bundled framework skills | `/src/claude_mpm/skills/bundled/pm/` |
| Deployment Service | Handles deployment logic | `/src/claude_mpm/services/pm_skills_deployer.py` |
| PM Instructions | References and loads skills | `/src/claude_mpm/agents/PM_INSTRUCTIONS.md` |
| Skill Presets | Preset configurations | `/src/claude_mpm/config/skill_presets.py` |
| Deployed Skills | Project-level copies | `.claude-mpm/skills/pm/` |
| Registry | Version tracking | `.claude-mpm/pm_skills_registry.yaml` |

## Related Services

**Skills Service** (`src/claude_mpm/skills/skills_service.py`):
- Manages project-level skills (`.claude/skills/`)
- Different from PM skills deployment
- User-facing skill management

**PM Skills Deployer** (`src/claude_mpm/services/pm_skills_deployer.py`):
- Manages framework PM skills (`.claude-mpm/skills/pm/`)
- Framework-level deployment
- PM operational protocols

**Skill Presets** (`src/claude_mpm/config/skill_presets.py`):
- Predefined skill bundles (python-min, python-max, etc.)
- NOT related to PM framework skills
- For project-level skill deployment

## Usage Examples

### Deploying PM Skills to Project

```python
from pathlib import Path
from claude_mpm.services.pm_skills_deployer import PMSkillsDeployerService

# Initialize deployer
deployer = PMSkillsDeployerService()

# Deploy to project
project_dir = Path("/path/to/project")
result = deployer.deploy_pm_skills(project_dir, force=False)

print(f"Deployed: {len(result.deployed)} skills")
print(f"Skipped: {len(result.skipped)} skills")
print(f"Errors: {len(result.errors)}")
```

### Verifying PM Skills

```python
# Check deployment status
verify_result = deployer.verify_pm_skills(project_dir)

if not verify_result.verified:
    print("Warnings:")
    for warning in verify_result.warnings:
        print(f"  - {warning}")

    print(f"\nMissing skills: {verify_result.missing_skills}")
    print(f"Outdated skills: {verify_result.outdated_skills}")
```

### Checking for Updates

```python
# Get available updates
updates = deployer.check_updates_available(project_dir)

for update in updates:
    print(f"{update.skill_name}:")
    print(f"  Current: {update.current_version}")
    print(f"  New: {update.new_version}")
    print(f"  Changed: {update.checksum_changed}")
```

## Recommendations

### For Adding New PM Skills

1. **Start with clear use case**: What PM workflow needs this skill?
2. **Define trigger conditions**: When should PM load this skill?
3. **Follow existing patterns**: Use git-file-tracking as template
4. **Keep skills focused**: One workflow/protocol per skill
5. **Reference from PM_INSTRUCTIONS.md**: Inline reference pattern
6. **Include examples**: Show correct vs incorrect patterns
7. **Test deployment**: Verify in clean project

### For Skill Content

1. **Frontmatter required**: Name, version, description, when_to_use, tags
2. **Clear structure**: Use headers, lists, code blocks
3. **Examples first**: Show patterns before explaining
4. **Critical principles**: Highlight blocking/required behaviors
5. **Integration notes**: How skill relates to other PM workflows
6. **Decision trees**: Use ASCII diagrams for complex flows
7. **Enforcement**: Mention circuit breakers if applicable

### For Maintenance

1. **Version tracking**: Update version when content changes
2. **Checksum validation**: Ensures integrity across deployments
3. **Registry updates**: Automatic on deployment
4. **Backward compatibility**: Support legacy formats
5. **Security validation**: Path traversal and YAML bomb checks
6. **Non-blocking verification**: Warnings instead of errors
7. **Update detection**: Automatic checksum comparison

## Conclusion

Framework PM skills provide a robust, version-tracked system for deploying essential PM operational protocols. The pattern is clear:

1. **Create** skill in `src/claude_mpm/skills/bundled/pm/{name}/SKILL.md`
2. **Reference** in `PM_INSTRUCTIONS.md` with `**[SKILL: name]**` marker
3. **Deploy** automatically via `pm_skills_deployer` service
4. **Track** in `.claude-mpm/pm_skills_registry.yaml`
5. **Validate** with checksum and security checks

This architecture ensures all PM agents have consistent, framework-maintained protocols while maintaining clear separation from project-level skills.

---

**Research completed**: 2026-01-07
**Source code version**: Current main branch
**Key files analyzed**: 7 files, 3000+ lines of code
**Skills discovered**: 7 PM framework skills
