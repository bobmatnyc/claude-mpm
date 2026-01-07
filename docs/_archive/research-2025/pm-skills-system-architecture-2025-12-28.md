# PM Skills System Architecture Research

**Date:** 2025-12-28
**Researcher:** Research Agent
**Objective:** Design PM skills deployment and startup verification system

---

## Executive Summary

This research analyzed the current skills infrastructure to design a PM-specific skills system that:
1. Deploys PM skills to per-project locations (`.claude-mpm/skills/pm/`)
2. Verifies PM skills on project initialization
3. Integrates with existing skills manager without disruption
4. Supports both bundled and fetched PM skills

**Key Finding:** The current architecture supports this extension with minimal modification. Skills can be deployed to project-specific locations and loaded via the existing `SkillManager` and `SkillsService` infrastructure.

---

## Current Architecture Overview

### 1. Skills Infrastructure Components

#### A. Core Services

**SkillsService** (`src/claude_mpm/skills/skills_service.py`)
- **Purpose:** Manages skill discovery, deployment, validation, and registry
- **Key Capabilities:**
  - Discovers skills from `src/claude_mpm/skills/bundled/`
  - Deploys to `.claude/skills/` (Claude Code's global directory)
  - Parses YAML frontmatter from `SKILL.md` files
  - Validates against SKILL.md specification (16 rules)
  - Version checking and updates
- **Deployment Target:** `~/.claude/skills/` (project root `.claude/skills/`)
- **Registry:** `config/skills_registry.yaml`

**SkillsDeployerService** (`src/claude_mpm/services/skills_deployer.py`)
- **Purpose:** Deploy skills from GitHub repositories
- **Key Capabilities:**
  - Downloads from GitHub (default: bobmatnyc/claude-mpm-skills)
  - Deploys to `~/.claude/skills/` directory
  - Filters by toolchain (python, javascript, rust)
  - Filters by categories (testing, debugging, web)
  - Detects Claude Code process and warns about restart
  - Supports collections via SkillsConfig
- **Important Note:** Skills are loaded at STARTUP ONLY by Claude Code
- **Deployment Flow:**
  1. Download skills from GitHub collection
  2. Parse manifest.json for metadata
  3. Filter by toolchain and categories
  4. (Optional) Selective deployment based on agent references
  5. Deploy to `~/.claude/skills/`
  6. Warn about Claude Code restart requirement

**SkillManager** (`src/claude_mpm/skills/skill_manager.py`)
- **Purpose:** Integrates skills with agents
- **Key Capabilities:**
  - Loads skill mappings from agent templates (`agents/templates/*.json`)
  - Maps agent IDs to skill names
  - Enhances agent prompts with skill content
  - Infers agents for skills based on tags/names
  - Saves/loads mappings from `.claude-mpm/skills_config.json`
- **Agent Mapping Source:** `agents/templates/*.json` files with `skills` field

#### B. Directory Structure

**Bundled Skills Location:**
```
src/claude_mpm/skills/bundled/
  ├── collaboration/
  │   ├── dispatching-parallel-agents/
  │   │   └── SKILL.md
  │   ├── brainstorming/
  │   │   └── SKILL.md
  │   └── ...
  ├── debugging/
  ├── infrastructure/
  ├── main/
  ├── php/
  ├── react/
  ├── rust/
  ├── tauri/
  └── testing/
```

**Deployed Skills Location:**
```
.claude/skills/  (or ~/.claude/skills/)
  ├── toolchains-python-frameworks-django/
  ├── toolchains-typescript-core/
  ├── universal-debugging-systematic-debugging/
  └── ...
```

**Per-Project Skills Config:**
```
.claude-mpm/
  └── skills_config.json  (agent-to-skill mappings)
```

#### C. Skill File Format

**SKILL.md Structure:**
```markdown
---
name: skill-name
description: Brief description (10-150 chars)
version: 1.0.0
category: development
progressive_disclosure:
  entry_point:
    summary: Quick summary
    when_to_use: When to use this skill
    quick_start: Quick start steps
  references:
    - file1.md
    - file2.md
---

# Skill Content

Main skill instructions and guidance...
```

**Validation Rules:**
- SKILL.md must exist
- YAML frontmatter required
- Required fields: name, description, version, category, progressive_disclosure
- Name format: `^[a-z][a-z0-9-]*[a-z0-9]$`
- Description length: 10-150 characters
- Optional directories: `scripts/`, `references/`

### 2. Startup and Initialization

#### A. Project Initialization Flow

**Entry Point:** `src/claude_mpm/cli/commands/mpm_init_handler.py`
- Handles `claude-mpm mpm-init` command
- Supports context/pause/resume subcommands
- Calls `MPMInitCommand.initialize_project()`
- Returns exit codes based on `OperationResult`

**Optimized Startup:** `src/claude_mpm/core/optimized_startup.py`
- **Purpose:** Deferred initialization for fast startup
- **Critical Services:** logger, config, paths, cli_parser
- **Deferred Services:** socketio, dashboard, memory, hooks, project_analyzer
- **Phases:**
  1. `initialize_minimal()` - Critical components only
  2. `initialize_services()` - Lazy or eager service loading
  3. `initialize_agents()` - Preload or on-demand
- **Lazy Loading:** Uses `LazyService` wrappers for deferred services

**Key Insight:** Skills are NOT part of critical startup path. They are loaded on-demand when agents are initialized.

### 3. Skills Manager Agent

**Location:** `.claude/agents/mpm-skills-manager.md`

**Core Responsibilities:**
- Skill lifecycle management (discovery, validation, deployment)
- Technology stack detection from project files
- Skill recommendation and matching
- Git repository operations and GitHub workflows
- Pull request creation with comprehensive context
- Manifest.json management and validation
- Skill structure validation

**Technology Detection Patterns:**
- Python: requirements.txt, pyproject.toml, setup.py, Pipfile
- JavaScript/TypeScript: package.json, tsconfig.json, .babelrc
- Ruby: Gemfile, *.gemspec
- Rust: Cargo.toml
- Go: go.mod
- Java: pom.xml, build.gradle
- Database: drivers in dependencies, .env files, docker-compose

**Skill Recommendation Logic:**
1. Technology Matching: Query manifest.json for available skills
2. Prioritization: Critical (must-have) → High → Medium → Low
3. Filtering: Remove already deployed, conflicting, incompatible

**Important:** This agent is NOT PM-specific. It manages general Claude MPM skills.

---

## Proposed PM Skills System Design

### 1. Architecture Overview

```
PM Skills System
├── Deployment Location: .claude-mpm/skills/pm/
├── Skills Sources:
│   ├── Bundled: src/claude_mpm/skills/bundled/pm/
│   └── Fetched: GitHub collections with "pm" category
├── Verification: On mpm-init and startup
└── Integration: Via SkillManager with PM-specific mappings
```

### 2. Deployment Flow

#### A. PM Skills Deployment Service

**New Service:** `PMSkillsDeployerService`
- **Location:** `src/claude_mpm/services/pm_skills_deployer.py`
- **Purpose:** Deploy PM-specific skills to project directory
- **Key Methods:**
  - `deploy_pm_skills()` - Deploy bundled PM skills
  - `fetch_pm_skills()` - Fetch PM skills from GitHub
  - `verify_pm_skills()` - Verify PM skills on startup
  - `update_pm_skills()` - Update PM skills to latest versions

**Deployment Target:** `.claude-mpm/skills/pm/`

**Deployment Triggers:**
1. `claude-mpm mpm-init` - Initial project setup
2. `claude-mpm skills deploy --pm` - Manual PM skills deployment
3. Startup verification (non-blocking)

#### B. Bundled PM Skills

**Location:** `src/claude_mpm/skills/bundled/pm/`

**Structure:**
```
src/claude_mpm/skills/bundled/pm/
  ├── project-planning/
  │   └── SKILL.md
  ├── task-delegation/
  │   └── SKILL.md
  ├── agent-coordination/
  │   └── SKILL.md
  ├── context-management/
  │   └── SKILL.md
  └── ticket-workflow/
      └── SKILL.md
```

**Skill Examples:**
1. **project-planning** - Project planning and estimation techniques
2. **task-delegation** - Effective task delegation to specialized agents
3. **agent-coordination** - Multi-agent coordination patterns
4. **context-management** - Managing project context across sessions
5. **ticket-workflow** - Ticket creation, updates, and workflows

#### C. Fetched PM Skills

**GitHub Collection:** PM skills can be fetched from external collections with `category: pm`

**manifest.json Structure:**
```json
{
  "skills": {
    "pm": [
      {
        "name": "project-planning",
        "category": "pm",
        "description": "Project planning techniques",
        "version": "1.0.0",
        "toolchain": ["universal"]
      }
    ]
  }
}
```

### 3. Startup Verification

#### A. Verification Hook

**Integration Point:** `OptimizedStartup._setup_agent_registry()`

**Verification Logic:**
```python
def _verify_pm_skills():
    """Verify PM skills are deployed (non-blocking)."""
    pm_skills_dir = Path.cwd() / ".claude-mpm" / "skills" / "pm"

    if not pm_skills_dir.exists():
        logger.warning("PM skills not deployed. Run 'claude-mpm skills deploy --pm'")
        return False

    # Count deployed PM skills
    skill_count = len(list(pm_skills_dir.glob("*/SKILL.md")))

    if skill_count == 0:
        logger.warning("No PM skills found. Run 'claude-mpm skills deploy --pm'")
        return False

    logger.info(f"PM skills verified: {skill_count} skills deployed")
    return True
```

**Non-Blocking:** Verification logs warnings but does not block startup.

#### B. Auto-Deployment Option

**Configuration:** `.claude-mpm/config.yaml`

```yaml
pm_skills:
  auto_deploy: true  # Auto-deploy PM skills on first mpm-init
  auto_update: false  # Auto-update PM skills on startup
  verify_on_startup: true  # Verify PM skills on startup
```

### 4. Skills Manager Integration

#### A. PM-Specific Agent Mappings

**Special Case Handling in SkillManager:**

```python
def get_agent_skills(self, agent_type: str) -> List[Skill]:
    """Get all skills for an agent (bundled + discovered + PM)."""

    # Existing logic for regular skills
    skills = self._get_regular_skills(agent_type)

    # Add PM skills for PM agent
    if agent_type == "pm" or "project-manager" in agent_type:
        pm_skills = self._get_pm_skills()
        skills.extend(pm_skills)

    return skills

def _get_pm_skills(self) -> List[Skill]:
    """Get PM skills from project directory."""
    pm_skills_dir = Path.cwd() / ".claude-mpm" / "skills" / "pm"

    if not pm_skills_dir.exists():
        return []

    skills = []
    for skill_dir in pm_skills_dir.iterdir():
        if skill_dir.is_dir():
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                skill = self._parse_skill(skill_md)
                skills.append(skill)

    return skills
```

#### B. Registry Updates

**PM Skills Registry:** `.claude-mpm/pm_skills_registry.yaml`

```yaml
version: "1.0.0"
last_updated: "2025-12-28T12:00:00Z"

pm_skills:
  project-planning:
    version: "1.0.0"
    category: pm
    deployed: true
    source: bundled

  task-delegation:
    version: "1.0.0"
    category: pm
    deployed: true
    source: bundled

agent_pm_skills:
  pm:
    required:
      - project-planning
      - task-delegation
      - agent-coordination
    optional:
      - context-management
      - ticket-workflow
```

### 5. Files That Need Modification

#### A. New Files

1. **`src/claude_mpm/services/pm_skills_deployer.py`**
   - PM skills deployment service
   - Handles bundled and fetched PM skills
   - Verification and updates

2. **`src/claude_mpm/skills/bundled/pm/`**
   - Directory for bundled PM skills
   - Initial PM skills (5-10 skills)

3. **`.claude-mpm/pm_skills_registry.yaml`**
   - PM skills registry (per-project)
   - Tracks deployed PM skills and versions

#### B. Modified Files

1. **`src/claude_mpm/skills/skill_manager.py`**
   - Add `_get_pm_skills()` method
   - Update `get_agent_skills()` to include PM skills for PM agent
   - Add PM skills path configuration

2. **`src/claude_mpm/core/optimized_startup.py`**
   - Add PM skills verification hook
   - Non-blocking warning if PM skills not deployed
   - Optional auto-deployment on first init

3. **`src/claude_mpm/cli/commands/mpm_init_handler.py`**
   - Add PM skills deployment step
   - Trigger PM skills verification
   - Log PM skills status

4. **`src/claude_mpm/cli/commands/skills.py`**
   - Add `--pm` flag for PM skills deployment
   - Add `--verify-pm` flag for PM skills verification
   - Add `--update-pm` flag for PM skills updates

5. **`src/claude_mpm/services/skills_config.py`**
   - Add PM skills configuration section
   - Load PM skills config from `.claude-mpm/config.yaml`

#### C. Configuration Files

1. **`.claude-mpm/config.yaml`**
   - Add `pm_skills` section with auto_deploy, auto_update, verify_on_startup

2. **`config/skills_registry.yaml`**
   - Add PM skills metadata (optional, if bundled)

---

## Recommended PM Skills Directory Structure

### Project Directory Structure

```
.claude-mpm/
  ├── skills/
  │   └── pm/
  │       ├── project-planning/
  │       │   ├── SKILL.md
  │       │   └── references/
  │       │       ├── planning-templates.md
  │       │       └── estimation-techniques.md
  │       ├── task-delegation/
  │       │   ├── SKILL.md
  │       │   └── examples/
  │       │       └── delegation-patterns.md
  │       ├── agent-coordination/
  │       │   └── SKILL.md
  │       ├── context-management/
  │       │   └── SKILL.md
  │       └── ticket-workflow/
  │           └── SKILL.md
  └── pm_skills_registry.yaml
```

### Bundled PM Skills Source

```
src/claude_mpm/skills/bundled/pm/
  ├── project-planning/
  │   └── SKILL.md
  ├── task-delegation/
  │   └── SKILL.md
  ├── agent-coordination/
  │   └── SKILL.md
  ├── context-management/
  │   └── SKILL.md
  └── ticket-workflow/
      └── SKILL.md
```

---

## Implementation Phases

### Phase 1: Core PM Skills Deployment (Week 1)

**Tasks:**
1. Create `src/claude_mpm/skills/bundled/pm/` directory
2. Implement 5 core PM skills (project-planning, task-delegation, agent-coordination, context-management, ticket-workflow)
3. Create `PMSkillsDeployerService` with basic deployment
4. Update `SkillManager` to include PM skills for PM agent
5. Add PM skills verification to `mpm-init` command

**Deliverables:**
- PM skills bundled in source tree
- PM skills deployed to `.claude-mpm/skills/pm/` on `mpm-init`
- PM agent loads PM skills automatically

### Phase 2: Startup Verification (Week 2)

**Tasks:**
1. Add PM skills verification hook to `OptimizedStartup`
2. Implement non-blocking warnings for missing PM skills
3. Add configuration options (`auto_deploy`, `auto_update`, `verify_on_startup`)
4. Create PM skills registry (`.claude-mpm/pm_skills_registry.yaml`)

**Deliverables:**
- Startup verification logs PM skills status
- Configuration options for PM skills behavior
- Registry tracks deployed PM skills

### Phase 3: CLI Commands (Week 3)

**Tasks:**
1. Add `--pm` flag to `claude-mpm skills deploy`
2. Add `--verify-pm` flag to `claude-mpm skills verify`
3. Add `--update-pm` flag to `claude-mpm skills update`
4. Implement PM skills fetching from GitHub collections

**Deliverables:**
- CLI commands for PM skills management
- Support for external PM skills collections
- Manual PM skills deployment and updates

### Phase 4: GitHub Collections Support (Week 4)

**Tasks:**
1. Define PM skills manifest.json structure
2. Update `SkillsDeployerService` to filter by `category: pm`
3. Add PM skills to default collections
4. Document PM skills contribution guidelines

**Deliverables:**
- PM skills can be fetched from GitHub
- Collections support `category: pm`
- Contribution guidelines for PM skills

---

## Special Considerations

### 1. Skills Manager Agent

**Current Behavior:** Manages general Claude MPM skills, not PM-specific.

**Recommendation:** Do NOT make mpm-skills-manager PM-aware. Instead:
- Create separate PM skills manager logic in `PMSkillsDeployerService`
- PM agent can use `PMSkillsDeployerService` directly
- Keep skills manager focused on general skills

**Rationale:** Separation of concerns. PM skills are project-specific, while general skills are user/system-wide.

### 2. Deployment Conflicts

**Issue:** PM skills deploy to `.claude-mpm/skills/pm/`, general skills to `.claude/skills/`

**Resolution:** No conflicts. Different directories, different scopes:
- `.claude/skills/` - Global skills (Claude Code)
- `.claude-mpm/skills/pm/` - Project-specific PM skills

### 3. Claude Code Integration

**Important:** Claude Code loads skills from `~/.claude/skills/` at STARTUP ONLY.

**PM Skills Location:** `.claude-mpm/skills/pm/` (NOT in Claude Code's path)

**How PM Skills Work:**
- PM skills are loaded by Claude MPM's `SkillManager`
- Injected into PM agent prompt at runtime
- Do NOT require Claude Code restart
- Scoped to Claude MPM project only

**Advantage:** PM skills are dynamic and project-specific, unlike global Claude Code skills.

### 4. Version Management

**PM Skills Versions:** Tracked in `.claude-mpm/pm_skills_registry.yaml`

**Update Strategy:**
1. Check bundled version vs deployed version
2. If bundled newer, offer to update
3. If fetched, check GitHub for updates
4. Update preserves user customizations (if any)

### 5. Skill Customization

**Per-Project PM Skills:** Users can customize PM skills in `.claude-mpm/skills/pm/`

**Update Behavior:**
- Updates check for local modifications
- Warn before overwriting customizations
- Offer to merge or preserve custom changes

---

## Risk Analysis

### Low Risk

1. **Deployment to new location** - `.claude-mpm/skills/pm/` does not conflict with existing directories
2. **Non-blocking verification** - Warnings do not disrupt startup
3. **Optional features** - Auto-deploy and auto-update are configurable

### Medium Risk

1. **SkillManager modifications** - Changes to core skill loading logic
   - **Mitigation:** Thorough testing, backward compatibility checks
2. **Startup performance impact** - PM skills verification adds startup time
   - **Mitigation:** Lazy loading, deferred verification, caching

### High Risk

1. **Skills path confusion** - Users may confuse `.claude/skills/` with `.claude-mpm/skills/pm/`
   - **Mitigation:** Clear documentation, CLI help messages, warnings
2. **PM agent not loading PM skills** - Integration failure
   - **Mitigation:** Integration tests, fallback to general skills

---

## Success Metrics

### Deployment Success

- PM skills deployed to `.claude-mpm/skills/pm/` on 95%+ of `mpm-init` runs
- No deployment failures on supported platforms
- Deployment time < 2 seconds for bundled PM skills

### Verification Success

- Startup verification completes in < 200ms
- Non-blocking warnings displayed when PM skills missing
- No false positives (warnings when PM skills are deployed)

### Integration Success

- PM agent loads PM skills 100% of the time when deployed
- PM skills enhance PM agent prompts correctly
- No conflicts with general skills

### User Experience

- Clear CLI messages about PM skills status
- Easy manual deployment with `--pm` flag
- Simple updates with `--update-pm` flag

---

## Conclusion

The current skills architecture fully supports PM-specific skills with minimal modification. The proposed design:

1. **Deploys PM skills** to `.claude-mpm/skills/pm/` (project-specific)
2. **Verifies on startup** with non-blocking warnings
3. **Integrates seamlessly** via SkillManager special-case handling
4. **Supports bundled and fetched** PM skills from GitHub
5. **Maintains separation** from general Claude Code skills

**Next Steps:**
1. Implement Phase 1 (Core PM Skills Deployment)
2. Create 5 core PM skills in `src/claude_mpm/skills/bundled/pm/`
3. Update `SkillManager` for PM-specific loading
4. Add PM skills deployment to `mpm-init`
5. Test on clean project initialization

**Estimated Timeline:** 4 weeks for full implementation (all phases)

**Recommended Start:** Phase 1 (Core PM Skills Deployment) - immediate priority
