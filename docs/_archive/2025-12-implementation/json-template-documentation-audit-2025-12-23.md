# JSON Template Documentation Audit - Outdated References

**Date:** 2025-12-23
**Status:** Complete
**Scope:** Search for outdated JSON template references in documentation

---

## Executive Summary

**Finding:** Multiple documentation files contain **OUTDATED** references to JSON-based agent templates, despite the system now using Markdown (.md) files with hierarchical BASE_AGENT.md inheritance.

**Current Reality:**
- Agents are stored as `.md` files with YAML frontmatter
- Hierarchical inheritance uses `BASE_AGENT.md` files (not `BASE_{TYPE}.md`)
- JSON files exist only in `templates/archive/` (39 archived files)
- One JSON file remains: `src/claude_mpm/agents/base_agent.json` (likely legacy)

**Impact:** Documentation mismatch creates confusion about how to create/manage agents.

---

## Current Agent File Structure (Actual Reality)

### Verified Agent Files

**Root Level Agents** (`src/claude_mpm/agents/`):
```
BASE_AGENT.md                      # ✅ ROOT INHERITANCE FILE
BASE_ENGINEER.md                   # ✅ ENGINEER INHERITANCE FILE
CLAUDE_MPM_OUTPUT_STYLE.md         # ✅ SHARED STYLE GUIDE
CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md # ✅ TEACHER STYLE GUIDE
MEMORY.md                          # ✅ MEMORY INSTRUCTIONS
PM_INSTRUCTIONS.md                 # ✅ PM-SPECIFIC INSTRUCTIONS
WORKFLOW.md                        # ✅ WORKFLOW GUIDE
base_agent.json                    # ⚠️ LEGACY JSON FILE (why still here?)
```

**Template Directory** (`src/claude_mpm/agents/templates/`):
```
templates/
├── README.md                      # ✅ PM TEMPLATES ECOSYSTEM GUIDE
├── archive/                       # ✅ 39 ARCHIVED JSON FILES
│   ├── agent-manager.json
│   ├── engineer.json
│   ├── python_engineer.json
│   └── ... (36 more archived .json files)
├── circuit-breakers.md            # ✅ PM CIRCUIT BREAKERS
├── git-file-tracking.md           # ✅ GIT TRACKING PROTOCOL
├── pm-examples.md                 # ✅ PM EXAMPLES
├── response-format.md             # ✅ RESPONSE FORMAT
└── ... (PM instruction templates)
```

**Deployed Agents** (`.claude/agents/`):
```
mpm-agent-manager.md               # ✅ DEPLOYED MARKDOWN AGENT
mpm-skills-manager.md              # ✅ DEPLOYED MARKDOWN AGENT
```

### Correct Agent Structure

**Format:** Markdown with YAML frontmatter + BASE_AGENT.md inheritance

**Example:**
```markdown
---
name: fastapi-engineer
description: FastAPI backend development specialist
version: 1.0.0
schema_version: 1.3.0
agent_id: fastapi-engineer
agent_type: engineer
model: sonnet
resource_tier: standard
tags:
  - python
  - backend
  - fastapi
category: engineering
---

# FastAPI Engineer

Expert in building async REST APIs with FastAPI.

## Specialization
- Async/await patterns
- Pydantic models
- Dependency injection
```

**Inheritance Chain:**
```
fastapi-engineer.md
  └─ inherits from: BASE_ENGINEER.md
       └─ inherits from: BASE_AGENT.md
```

---

## Files with OUTDATED JSON References

### 1. `.claude/templates/mpm-agent-manager.md`

**Location:** Lines 103-111
**Issue:** Shows JSON example in "Agent Level" section of hierarchical design doc

**Outdated Content:**
```markdown
### Agent Level: `engineering/python/backend/fastapi-engineer.md`

```json
{
  "name": "fastapi-engineer",
  "description": "FastAPI backend development specialist",
  "agent_type": "engineer",
  "instructions": "# FastAPI Engineer\n\nExpert in building async REST APIs..."
}
```
```

**Why It's Wrong:**
- Agents are **not** stored as JSON
- This is example code showing OLD format
- Current agents use `.md` files with YAML frontmatter

**Recommendation:**
Replace JSON example with correct Markdown format:
```markdown
### Agent Level: `engineering/python/backend/fastapi-engineer.md`

```markdown
---
name: fastapi-engineer
description: FastAPI backend development specialist
version: 1.0.0
agent_type: engineer
model: sonnet
---

# FastAPI Engineer

Expert in building async REST APIs with FastAPI.
```
```

**Priority:** HIGH (agent-manager is user-facing documentation)

---

### 2. `docs/design/hierarchical-base-agents.md`

**Location:** Lines 103-111
**Issue:** SAME as #1 - likely copied from same source

**Outdated Content:** Identical JSON example

**Recommendation:** Same fix as #1

**Priority:** HIGH (design documentation used by developers)

---

### 3. `docs/design/claude-mpm-skills-integration-design.md`

**Location:** Multiple references throughout (lines 72, 354-398, 1427-1462)
**Issue:** Entire design document assumes JSON templates

**Outdated Content:**
- "Enhanced JSON templates with skills field" (line 13)
- "Reads agent JSON templates" (line 32)
- "Agent Template Enhancement Service - Reads agent JSON templates" (line 35)
- Complete JSON template enhancement specifications (lines 354-711)

**Why It's Wrong:**
- This design doc was created when agents were JSON
- Skills integration should work with `.md` frontmatter, not JSON
- References to `AgentSkillsInjector` reading JSON templates

**Recommendation:**
**MAJOR REWRITE REQUIRED** - This entire design document needs updating:
1. Replace all references to "JSON templates" with "Markdown agents with YAML frontmatter"
2. Update `AgentSkillsInjector` to read/write YAML frontmatter instead of JSON
3. Update examples to show YAML frontmatter format
4. Update file paths from `.json` to `.md`

**Priority:** CRITICAL (this is a design specification document)

**Example Fix:**

**OLD (line 354-370):**
```markdown
### Current Template Structure

```json
{
  "agent_id": "engineer",
  "version": "2.0.0",
  "metadata": {
    "name": "Software Engineer",
    "description": "Software development and implementation"
  }
}
```

### Enhanced Template with Skills

```json
{
  "agent_id": "engineer",
  "version": "2.1.0",
  "skills": {
    "required": ["test-driven-development", "systematic-debugging"]
  }
}
```
```

**NEW:**
```markdown
### Current Agent Structure

```markdown
---
name: engineer
version: 2.0.0
description: Software development and implementation
agent_type: engineer
model: sonnet
---

# Software Engineer Agent
...
```

### Enhanced Agent with Skills

```markdown
---
name: engineer
version: 2.1.0
description: Software development and implementation
agent_type: engineer
model: sonnet
skills:
  - test-driven-development
  - systematic-debugging
---

# Software Engineer Agent
...
```
```

---

### 4. Research Documents (Multiple)

**Files with JSON References:**
1. `docs/research/agent-deployment-warnings-analysis-2025-12-19.md`
   - Lines: 8, 54, 154, 196, 243, 259
   - Context: Mentions "JSON templates" vs "Markdown agents"
   - Status: **INFORMATIONAL** (research doc, not user-facing)

2. `docs/research/skill-loading-and-management-2025-12-22.md`
   - Line 63: "Reads agent JSON template"
   - Status: **INFORMATIONAL** (research doc)

3. `docs/research/agent-count-discrepancy-2025-12-15.md`
   - Line: "JSON templates: 39 files"
   - Status: **ACCURATE** (correctly identifies archived JSONs)

4. `docs/research/agent-deployment-architecture-2025-12-09.md`
   - Line 178: "Also check for local JSON templates in .claude-mpm/agents/"
   - Status: **OUTDATED** (JSON templates no longer used)

5. `docs/research/agent-display-name-inconsistency-2025-12-15.md`
   - Context: "For local JSON templates, the code extracts `metadata.name`"
   - Status: **OUTDATED** (no longer using JSON)

6. `docs/research/base-agent-loader-analysis-2025-12-20.md`
   - Context: "JSON templates for reporting"
   - Status: **OUTDATED**

7. `docs/research/agent-matching-detection-analysis-2025-12-09.md`
   - Context: "Discovers JSON templates and user/project Markdown agents"
   - Status: **OUTDATED** (implies JSON templates still discovered)

**Recommendation for Research Docs:**
- Add **[HISTORICAL]** tag to research documents describing old JSON system
- Keep for historical reference but mark as obsolete
- Create NEW research document: "Agent Format Migration - JSON to Markdown"

**Priority:** LOW (research documents, not user-facing)

---

### 5. Migration Guides

**File:** `docs/migration/agent-sources-git-default-v4.5.0.md`

**Outdated Content:**
- Line: "disable_system_repo: false  # Used built-in JSON templates"
- Line: "If you prefer to continue using built-in JSON templates:"

**Why It's Wrong:**
- Migration guide still references JSON templates as an option
- Implies JSON templates are still supported

**Recommendation:**
Update migration guide to clarify:
```markdown
# Migration Note: JSON Templates Obsolete

**Historical Context:**
- v4.5.0 and earlier used JSON template files
- v5.0.0+ uses Markdown (.md) files with YAML frontmatter
- JSON templates moved to `templates/archive/` for reference

**If you have custom JSON agents:**
1. Convert JSON to Markdown format
2. Use YAML frontmatter for metadata
3. See: docs/reference/agent-format.md for conversion guide
```

**Priority:** MEDIUM (migration docs should be accurate)

---

### 6. Developer Documentation

**File:** `docs/developer/code-navigation/CODE-PATHS.md`

**Outdated Content:**
- Line: "Load JSON template"

**File:** `docs/developer/code-navigation/AGENT-SYSTEM.md`

**Outdated Content:**
- Line: "Load JSON template from templates/"

**Recommendation:**
Update both files:
```markdown
OLD: → Load JSON template
NEW: → Load Markdown agent with YAML frontmatter
```

**Priority:** HIGH (developer documentation must be accurate)

---

## Correct Documentation (Reference)

### File: `docs/design/hierarchical-base-agents.md`

**Lines 1-50:** CORRECTLY documents the current system:

```markdown
# Hierarchical BASE-AGENT.md Template Inheritance

## Overview

Claude MPM now supports hierarchical organization of agent templates using
`BASE-AGENT.md` files. This allows agent repositories to define shared
content at multiple levels of the directory tree, promoting code reuse
and consistent standards across related agents.

## Feature Description

When deploying an agent, Claude MPM automatically discovers and composes
`BASE-AGENT.md` files from the agent's directory hierarchy, walking up
from the agent file to the repository root.
```

**This is GOOD** - use this as reference for corrections.

**Note:** Same file has JSON example error at line 103-111 (see Issue #2 above)

---

### File: `src/claude_mpm/agents/templates/README.md`

**Entire file is CORRECT** - documents PM instruction templates, not agent format

**Excerpt:**
```markdown
# 🎯 PM Instruction Templates Ecosystem

Welcome to the PM Template Ecosystem - a modular system of specialized
templates that enforce PM delegation discipline through validation,
detection, examples, and standardization.
```

**This is GOOD** - PM templates are separate from agent format discussion.

---

## Recommended Actions

### Immediate (Critical)

1. **Update `docs/design/claude-mpm-skills-integration-design.md`**
   - Mark as [HISTORICAL] if not implementing
   - OR completely rewrite for Markdown+YAML format
   - Priority: CRITICAL
   - Estimated effort: 4-6 hours

2. **Fix `.claude/templates/mpm-agent-manager.md`**
   - Replace JSON example with Markdown example (lines 103-111)
   - Priority: HIGH
   - Estimated effort: 15 minutes

3. **Fix `docs/design/hierarchical-base-agents.md`**
   - Replace JSON example with Markdown example (lines 103-111)
   - Priority: HIGH
   - Estimated effort: 15 minutes

### High Priority

4. **Update Developer Documentation**
   - Fix `docs/developer/code-navigation/CODE-PATHS.md`
   - Fix `docs/developer/code-navigation/AGENT-SYSTEM.md`
   - Priority: HIGH
   - Estimated effort: 30 minutes

5. **Update Migration Guide**
   - Fix `docs/migration/agent-sources-git-default-v4.5.0.md`
   - Add JSON-to-Markdown migration instructions
   - Priority: MEDIUM
   - Estimated effort: 1 hour

### Low Priority (Cleanup)

6. **Mark Research Documents**
   - Add [HISTORICAL] tags to JSON-referencing research docs
   - Create new doc: "Agent Format Migration History"
   - Priority: LOW
   - Estimated effort: 1 hour

7. **Remove Legacy JSON File**
   - Investigate `src/claude_mpm/agents/base_agent.json`
   - Remove if no longer used, or document why it's still there
   - Priority: LOW
   - Estimated effort: 30 minutes (investigation + removal)

---

## Summary Statistics

**Total Files with JSON References:** 15+ files
**User-Facing Documentation Issues:** 3 critical
**Developer Documentation Issues:** 2 high priority
**Research Documentation Issues:** 7 informational (low priority)

**Estimated Total Effort:** 8-10 hours for complete cleanup

---

## Verification Checklist

After updates, verify:

- [ ] No references to "agent JSON template" in docs/
- [ ] No references to ".json template" in user-facing docs
- [ ] All examples show Markdown + YAML frontmatter format
- [ ] Migration guides clearly state JSON is obsolete
- [ ] Research docs tagged [HISTORICAL] where appropriate
- [ ] Developer docs reference `.md` files, not `.json`
- [ ] mpm-agent-manager.md has correct examples

---

## Related Documentation (Correct Format)

**For Reference When Updating:**

1. `src/claude_mpm/agents/BASE_AGENT.md` - Root inheritance file
2. `docs/design/hierarchical-base-agents.md` - Correct design (except one example)
3. `.claude/agents/*.md` - Live examples of deployed agents

**Search Commands:**
```bash
# Find all JSON references
grep -r "JSON template\|agent.*\.json\|\.json.*agent" docs/ --include="*.md"

# Find all agent definition references
grep -r "agent definition\|agent format\|agent schema" docs/ --include="*.md"

# Verify no JSON in agent paths
find . -name "*.json" -path "*/agents/*" ! -path "*/archive/*" ! -path "*/node_modules/*"
```

---

**Report Generated:** 2025-12-23
**Generated By:** research-agent
**Next Steps:** Review with team, prioritize fixes, create tickets for updates
