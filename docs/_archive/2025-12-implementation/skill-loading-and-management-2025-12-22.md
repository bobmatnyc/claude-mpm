# Skill Loading and Management Research

**Research Date:** 2025-12-22
**Objective:** Investigate how claude-mpm loads and manages skills for agent integration
**Context:** Understanding skill installation, loading mechanisms, and agent-skill mapping for future skill management improvements

---

## Executive Summary

Claude-mpm implements a sophisticated multi-layered skill management system that:
1. **Downloads skills from GitHub** collections to `~/.claude/skills/` (Claude Code's global directory)
2. **Maps skills to agents** via YAML registry (`config/skills_registry.yaml`)
3. **Injects skills into agent context** dynamically at runtime (without modifying template files)
4. **Supports selective deployment** - only installs skills referenced by agents (reduces from ~78 to ~20 skills)
5. **Manages multiple skill collections** with priority ordering

**Key Insight:** Skills are NOT stored in project directories. They are deployed to Claude Code's global `~/.claude/skills/` directory and Claude Code loads them at **STARTUP ONLY**.

---

## 1. Skill Loading Mechanism

### 1.1 Where Skills Are Loaded From

**Claude Code Global Directory:**
```
~/.claude/skills/
├── claude-mpm/              # Collection directory (git repo)
│   ├── manifest.json
│   ├── skills/
│   │   ├── universal/
│   │   ├── toolchains/
│   │   └── ...
├── toolchains-python-core/  # Individual skill (deployed)
├── toolchains-ai-protocols-mcp/
└── ...
```

**Key Locations:**
- **Global skills:** `~/.claude/skills/` (Claude Code loads these at startup)
- **Collections:** `~/.claude/skills/{collection-name}/` (git repositories)
- **Deployed skills:** `~/.claude/skills/{skill-name}/` (copied from collections)

**File:** `src/claude_mpm/services/skills_deployer.py:58`
```python
CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills"
```

### 1.2 Skill Installation Flow

**Multi-Collection Architecture (Phase 2):**

```
1. GitHub Download (git clone/pull)
   └─> ~/.claude/skills/{collection-name}/
       └─> Parse manifest.json
           └─> Discover skills

2. Selective Filtering
   └─> Read agent frontmatter (.claude/agents/*.md)
       └─> Extract skills: field
           └─> Query SkillToAgentMapper for inference
               └─> Combine explicit + inferred

3. Deployment (copy to flat structure)
   └─> ~/.claude/skills/{collection-name}/skills/category/skill-name/
       └─> Copy to: ~/.claude/skills/skill-name/
           └─> Claude Code discovers at startup
```

**Code References:**
- **SkillsDeployerService:** `src/claude_mpm/services/skills_deployer.py:39-1017`
  - `deploy_skills()` - Main deployment entry point (line 79)
  - `_download_from_github()` - Git clone/pull collections (line 486)
  - `_deploy_skill()` - Copy individual skill to Claude directory (line 740)

### 1.3 Skill Loading Trigger

**CRITICAL:** Claude Code loads skills **ONLY AT STARTUP**.

**Evidence:**
```python
# File: src/claude_mpm/services/skills_deployer.py:256-274
if restart_required:
    claude_running = self._is_claude_code_running()
    if claude_running:
        restart_instructions = (
            "⚠️  Claude Code is currently running.\n"
            "Skills are only loaded at STARTUP.\n"
            "Please restart Claude Code for new skills to be available.\n"
        )
```

**Restart Detection:** `_is_claude_code_running()` checks for Claude Code process (line 865)

---

## 2. Agent-Skill References

### 2.1 How Agents Declare Skills

Agents reference skills in **YAML frontmatter** of markdown files:

**Example:** `.claude/agents/golang-engineer.md:1-7`
```yaml
---
name: golang-engineer
description: "Use this agent when you need to implement..."
model: sonnet
type: engineer
version: "1.0.0"
---
```

**Note:** The example above does **NOT** have a `skills:` field. Skills are assigned separately via registry.

**Skills Field Format (when present):**
```yaml
# Legacy format (flat list)
skills:
  - test-driven-development
  - systematic-debugging

# New format (required/optional)
skills:
  required:
    - test-driven-development
    - systematic-debugging
  optional:
    - code-review
    - git-worktrees
```

**Code Reference:**
- **Frontmatter Parser:** `src/claude_mpm/services/skills/selective_skill_deployer.py:43-74`
  - `parse_agent_frontmatter()` - Extract YAML from markdown
  - `get_skills_from_agent()` - Parse skills field (both formats)

### 2.2 Agent-Skill Mapping Registry

**Source of Truth:** `config/skills_registry.yaml`

**Structure:**
```yaml
version: 1.0.0
last_updated: 2025-11-07

# Agent-to-skills mappings
agent_skills:
  engineer:
    required:
      - test-driven-development
      - systematic-debugging
    optional:
      - code-review
      - git-worktrees

  python_engineer:
    required:
      - test-driven-development
      - systematic-debugging
    optional:
      - async-testing

  golang_engineer:
    required:
      - test-driven-development
      - systematic-debugging

# Skill metadata
skills_metadata:
  test-driven-development:
    category: testing
    source: superpowers
    description: "Enforces RED/GREEN/REFACTOR TDD cycle"
    url: "https://github.com/obra/superpowers-skills/..."
```

**Registry Operations:**
- **SkillsRegistry:** `src/claude_mpm/skills/skills_registry.py:27-348`
  - `get_agent_skills()` - Get skills for agent (line 87)
  - `get_skill_metadata()` - Get skill metadata (line 112)
  - `validate_registry()` - Validate structure (line 205)

### 2.3 Dynamic Skill Injection

**Key Principle:** Skills are injected **at runtime** WITHOUT modifying template files.

**AgentSkillsInjector:** `src/claude_mpm/skills/agent_skills_injector.py:29-325`

**Methods:**
1. `enhance_agent_template()` (line 63)
   - Reads agent JSON template
   - Queries registry for skills
   - Adds `skills` field dynamically
   - Returns enhanced template dict

2. `generate_frontmatter_with_skills()` (line 121)
   - Generates YAML frontmatter with skills
   - Combines required + optional into single list

3. `inject_skills_documentation()` (line 177)
   - Adds "## Available Skills" section to markdown
   - Lists skills with descriptions
   - Informs agent about auto-loading

**Example Enhancement:**
```python
# Input: agent template without skills
template = {
    "agent_id": "engineer",
    "metadata": {"description": "Software development"}
}

# Output: enhanced with skills from registry
enhanced = {
    "agent_id": "engineer",
    "metadata": {"description": "Software development"},
    "skills": {
        "required": ["test-driven-development", "systematic-debugging"],
        "optional": ["code-review", "git-worktrees"],
        "auto_load": True
    }
}
```

---

## 3. Skill Installation

### 3.1 Installation Architecture

**Multi-Collection Support (v5.4+):**

```
~/.claude-mpm/config.json
{
  "skills": {
    "collections": {
      "claude-mpm": {
        "url": "https://github.com/bobmatnyc/claude-mpm-skills",
        "enabled": true,
        "priority": 1,
        "last_update": "2025-11-21T15:30:00Z"
      },
      "obra-superpowers": {
        "url": "https://github.com/obra/superpowers",
        "enabled": true,
        "priority": 2
      }
    },
    "default_collection": "claude-mpm"
  }
}
```

**Collection Management:**
- **SkillsConfig:** `src/claude_mpm/services/skills_config.py:49-180`
  - `add_collection()` - Add new collection
  - `get_collections()` - List all collections
  - `set_default_collection()` - Set default
  - `enable_collection()` / `disable_collection()`

### 3.2 Installation Process

**SkillsDeployerService.deploy_skills():**

**Step 1: Download from GitHub** (line 132)
```python
skills_data = self._download_from_github(collection_name)
# Result: ~/.claude/skills/{collection-name}/ (git repo)
```

**Step 2: Parse Manifest** (line 148)
```python
skills = self._flatten_manifest_skills(manifest)
# Supports both legacy and nested structures
```

**Step 3: Filter Skills** (line 165)
```python
filtered_skills = self._filter_skills(skills, toolchain, categories)
# Apply toolchain and category filters
```

**Step 4: Selective Deployment** (line 173, optional)
```python
if selective:
    required_skill_names = get_required_skills_from_agents(agents_dir)
    filtered_skills = [s for s in filtered_skills
                      if s.get("name") in required_skill_names]
# Only deploy skills referenced by agents
```

**Step 5: Deploy Skills** (line 227)
```python
for skill in filtered_skills:
    result = self._deploy_skill(skill, collection_dir, force=force)
# Copy from collection to ~/.claude/skills/{skill-name}/
```

**Step 6: Restart Warning** (line 255)
```python
if restart_required:
    warn_about_restart()
# Skills only load at Claude Code startup
```

### 3.3 Skill Storage Structure

**Collection Directory (Persistent):**
```
~/.claude/skills/claude-mpm/
├── .git/                    # Git repository
├── manifest.json            # Skill metadata
├── skills/
│   ├── universal/
│   │   ├── debugging/
│   │   │   └── systematic-debugging/
│   │   │       └── SKILL.md
│   ├── toolchains/
│   │   ├── python/
│   │   │   ├── core/
│   │   │   └── frameworks/
│   │   │       └── django/
│   │   │           └── SKILL.md
```

**Deployed Skills (Flat for Claude Code):**
```
~/.claude/skills/
├── systematic-debugging/     # Copied from collection
│   └── SKILL.md
├── toolchains-python-core/
│   └── SKILL.md
├── toolchains-python-frameworks-django/
│   └── SKILL.md
```

---

## 4. Differentiating Claude-MPM vs User Skills

### 4.1 Current Implementation

**Problem:** No built-in mechanism to differentiate claude-mpm installed skills from user-installed skills.

**Current Structure:**
```
~/.claude/skills/
├── claude-mpm/                    # Collection (claude-mpm managed)
├── obra-superpowers/              # Collection (potentially user-added)
├── systematic-debugging/          # Deployed skill (could be from any source)
├── my-custom-skill/               # User-installed (how to identify?)
```

**Detection Strategy (Inferred):**

1. **Collections are identifiable:**
   - Collections have `.git/` directory
   - Collections have `manifest.json`
   - Collections listed in `~/.claude-mpm/config.json`

2. **Deployed skills from collections:**
   - Compare skill names against collection manifests
   - Check if skill exists in any enabled collection
   - **Gap:** No metadata file marking source collection

3. **User-installed skills (orphaned):**
   - Skills NOT found in any collection manifest
   - Skills NOT in `~/.claude-mpm/config.json`
   - **Risk:** Deleted if collection reinstalled

### 4.2 Recommended Tagging Approach

**Option 1: Skill Metadata File**
```
~/.claude/skills/systematic-debugging/
├── SKILL.md
└── .mpm-metadata.json    # NEW: Track installation source
```

**Metadata Structure:**
```json
{
  "installed_by": "claude-mpm",
  "source": "claude-mpm-collection",
  "collection_url": "https://github.com/bobmatnyc/claude-mpm-skills",
  "installed_at": "2025-12-22T10:30:00Z",
  "skill_path": "skills/universal/debugging/systematic-debugging",
  "version": "1.0.0"
}
```

**Option 2: Collection Index File**
```
~/.claude/skills/.mpm-deployed-skills.json
{
  "systematic-debugging": {
    "collection": "claude-mpm",
    "installed_at": "2025-12-22T10:30:00Z"
  },
  "toolchains-python-core": {
    "collection": "claude-mpm",
    "installed_at": "2025-12-22T10:30:00Z"
  }
}
```

**Advantages:**
- Central index for quick lookup
- Atomic updates
- Easy cleanup on collection removal
- No per-skill file overhead

**Implementation Location:**
- Modify `SkillsDeployerService._deploy_skill()` to write metadata
- Add cleanup logic in `remove_collection()`

---

## 5. Code Locations Summary

### 5.1 Skill Loading & Deployment

| Component | File | Key Methods | Lines |
|-----------|------|-------------|-------|
| **SkillsDeployerService** | `src/claude_mpm/services/skills_deployer.py` | `deploy_skills()`, `_download_from_github()`, `_deploy_skill()` | 39-1017 |
| **SkillsConfig** | `src/claude_mpm/services/skills_config.py` | `add_collection()`, `get_collections()`, `set_default_collection()` | 49-180 |
| **Selective Deployment** | `src/claude_mpm/services/skills/selective_skill_deployer.py` | `get_required_skills_from_agents()`, `parse_agent_frontmatter()` | 1-180 |

### 5.2 Agent-Skill Mapping

| Component | File | Key Methods | Lines |
|-----------|------|-------------|-------|
| **SkillsRegistry** | `src/claude_mpm/skills/skills_registry.py` | `get_agent_skills()`, `get_skill_metadata()`, `validate_registry()` | 27-348 |
| **AgentSkillsInjector** | `src/claude_mpm/skills/agent_skills_injector.py` | `enhance_agent_template()`, `inject_skills_documentation()` | 29-325 |
| **SkillsService** | `src/claude_mpm/skills/skills_service.py` | `get_skills_for_agent()`, `deploy_bundled_skills()` | 30-400 |
| **SkillToAgentMapper** | `src/claude_mpm/services/skills/skill_to_agent_mapper.py` | `get_agents_for_skill()`, `infer_agents_from_pattern()` | 51-407 |

### 5.3 Configuration Files

| File | Purpose | Structure |
|------|---------|-----------|
| `~/.claude-mpm/config.json` | Collection management | `{"skills": {"collections": {...}, "default_collection": "..."}}` |
| `config/skills_registry.yaml` | Agent-skill mappings | `agent_skills: {agent_id: {required: [...], optional: [...]}}` |
| `~/.claude/skills/{collection}/manifest.json` | Skill metadata | `{"skills": {"universal": [...], "toolchains": {...}}}` |

---

## 6. Key Findings

### 6.1 Skill Loading Mechanism

✅ **Skills are loaded from:** `~/.claude/skills/` (Claude Code's global directory)
✅ **Loading trigger:** Claude Code startup ONLY (requires restart)
✅ **Installation method:** Git clone/pull to collection dirs, then copy to flat structure
✅ **Selective deployment:** Filters to agent-referenced skills (reduces deployment by ~75%)

### 6.2 Agent-Skill References

✅ **Declaration location:** YAML frontmatter in `.claude/agents/*.md` (optional)
✅ **Source of truth:** `config/skills_registry.yaml` (explicit mappings)
✅ **Injection mechanism:** Dynamic runtime injection via `AgentSkillsInjector`
✅ **Format support:** Both legacy flat list and new required/optional dict

### 6.3 Skill Installation

✅ **Collections supported:** Multiple GitHub repositories with priority ordering
✅ **Storage:** Collections in `~/.claude/skills/{collection}/`, deployed to `~/.claude/skills/{skill-name}/`
✅ **Updates:** Git pull for collections, re-deploy for individual skills
✅ **Management:** CLI commands via `claude-mpm skills` (deploy, list, remove)

### 6.4 Differentiation Gap

⚠️ **No built-in tagging:** Skills deployed by claude-mpm are not explicitly marked
⚠️ **Risk:** User-installed skills could be deleted during collection cleanup
⚠️ **Detection:** Only possible by cross-referencing collection manifests
💡 **Solution:** Add `.mpm-metadata.json` per skill OR central `.mpm-deployed-skills.json`

---

## 7. Recommendations

### 7.1 Immediate Actions

1. **Add Skill Source Tracking**
   - Implement `.mpm-deployed-skills.json` index
   - Track installation source (collection name)
   - Update `_deploy_skill()` to write metadata
   - Add cleanup on collection removal

2. **Improve Agent Frontmatter Documentation**
   - Document skills field format in agent template guide
   - Provide examples of required/optional structure
   - Explain relationship to registry

3. **Enhance CLI Feedback**
   - Show which skills are from which collection in `skills list`
   - Warn when removing collection with deployed skills
   - Provide `skills orphan` command to find user-installed skills

### 7.2 Future Enhancements

1. **Skill Versioning**
   - Track skill version in metadata
   - Warn on version conflicts
   - Support skill updates without full redeployment

2. **Agent-Skill Validation**
   - Check if all agent-referenced skills are deployed
   - Warn about missing skills at agent load time
   - Auto-suggest deployments for missing skills

3. **Collection Priorities**
   - Allow skill precedence when multiple collections have same skill
   - Support collection-specific overrides
   - Enable per-project collection preferences

---

## 8. Example Agent Templates

### 8.1 Agent with Skills in Frontmatter

**File:** `.claude/agents/golang-engineer.md`
```yaml
---
name: golang-engineer
description: "Go 1.23-1.24 specialist..."
model: sonnet
type: engineer
version: "1.0.0"
# Skills field NOT present - assigned via registry
---
# Golang Engineer
...
```

**Registry Entry:** `config/skills_registry.yaml:69-72`
```yaml
golang_engineer:
  required:
    - test-driven-development
    - systematic-debugging
```

### 8.2 Skill Directory Structure

**Example Skill:** `~/.claude/skills/systematic-debugging/`
```
systematic-debugging/
├── SKILL.md                    # Skill instructions
├── references/                 # Optional references
│   └── example.md
└── .mpm-metadata.json         # NEW: Proposed metadata
```

**SKILL.md Format:**
```markdown
---
name: systematic-debugging
category: debugging
version: 1.0.0
---

# Systematic Debugging

Instructions for systematic debugging approach...
```

---

## 9. Testing Evidence

**Test Files Reviewed:**
- `tests/test_skills_deployer.py` - Deployment tests
- `tests/services/skills/test_selective_skill_deployer.py` - Selective deployment
- `tests/services/skills/test_skill_to_agent_mapper.py` - Agent-skill mapping

**Key Test Insights:**
- Mock CLAUDE_SKILLS_DIR in tests (line 134-136)
- Validate flat structure deployment (line 303)
- Test both frontmatter formats (legacy + new)
- Verify collection git operations

---

## 10. Migration Path Analysis

**Current State (As-Is):**
```
User installs skills manually
  └─> ~/.claude/skills/my-skill/
      └─> NO tracking metadata

Claude-mpm deploys skills
  └─> ~/.claude/skills/skill-from-collection/
      └─> NO source tracking
```

**Desired State (To-Be):**
```
User installs skills manually
  └─> ~/.claude/skills/my-skill/
      └─> .mpm-metadata.json (installed_by: "user")

Claude-mpm deploys skills
  └─> ~/.claude/skills/skill-from-collection/
      └─> .mpm-metadata.json (installed_by: "claude-mpm", collection: "...")
```

**Migration Strategy:**
1. On first deployment with new version:
   - Scan existing skills in `~/.claude/skills/`
   - Check against all collection manifests
   - Tag known skills with collection metadata
   - Tag unknown skills as user-installed

2. Preserve user skills during operations:
   - Skip deletion of user-tagged skills
   - Warn before overwriting user skills
   - Provide merge/conflict resolution

---

## Conclusion

Claude-mpm implements a well-architected skill management system with:
- ✅ Multi-collection support with git-based updates
- ✅ Selective deployment based on agent requirements
- ✅ Dynamic skill injection without template modifications
- ✅ YAML-based registry for agent-skill mappings

**Primary Gap:** No metadata tracking for deployed skills makes it difficult to differentiate claude-mpm managed skills from user-installed skills.

**Next Steps:**
1. Implement `.mpm-deployed-skills.json` tracking index
2. Update deployment logic to write metadata on install
3. Add cleanup protection for user-installed skills
4. Enhance CLI commands to show skill sources

**Implementation Priority:** High (prevents accidental deletion of user skills)
