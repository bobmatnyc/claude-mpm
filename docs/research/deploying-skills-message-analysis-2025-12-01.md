# Deploying Skills Message Analysis

**Date**: 2025-12-01
**Research Type**: Code Analysis
**Objective**: Locate and analyze the "Deploying skills X/39 (100%)" message generation

---

## Executive Summary

The "Deploying skills" progress message is generated in `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/startup.py` at **line 525**. The current message format is accurate but doesn't reflect the actual deployment architecture, which deploys **project-level directories** (flat structure) rather than individual skill files.

**Key Finding**: The message correctly counts individual skills (39 total), but users might expect to see project-level directory counts instead. The deployment phase flattens nested Git repository structures into single hyphenated directories (e.g., `collaboration/parallel-agents/` → `collaboration-parallel-agents/`).

---

## File Location

**Primary File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/startup.py`
**Line Number**: 525
**Function**: `sync_skill_sources_on_startup()`

### Code Context

```python
# Line 516-528
if results["synced_count"] > 0:
    # Get all skills to determine deployment count
    all_skills = manager.get_all_skills()
    skill_count = len(all_skills)

    if skill_count > 0:
        # Create progress bar for deployment phase
        deploy_progress = ProgressBar(
            total=skill_count,
            prefix="Deploying skills",  # ← LINE 525: Message defined here
            show_percentage=True,
            show_counter=True,
        )
```

---

## Available Variables at Line 525

### From Sync Phase (results object)

```python
results = {
    "synced_count": int,           # Number of sources synced (e.g., 3)
    "failed_count": int,           # Failed sources
    "total_files_updated": int,    # Files downloaded this sync
    "total_files_cached": int,     # Files already cached
    "sources": {                   # Per-source details
        "source_id": {
            "synced": bool,
            "files_updated": int,
            "skills_discovered": int,
            "error": str
        }
    },
    "timestamp": str
}
```

### From Deployment Phase

```python
# Available BEFORE progress bar creation (line 525)
enabled_sources = config.get_enabled_sources()  # List of GitSkillSource objects
all_skills = manager.get_all_skills()           # List[Dict] with source_id metadata
skill_count = len(all_skills)                   # Total skills (e.g., 39)

# Available AFTER deployment (line 539+)
deployment_result = {
    "deployed_count": int,        # Newly deployed skills
    "skipped_count": int,         # Already present skills
    "failed_count": int,          # Failed deployments
    "deployed_skills": List[str], # Deployment names
    "skipped_skills": List[str],  # Skipped deployment names
    "errors": List[str]           # Error messages
}
```

### Skill Object Structure

Each skill in `all_skills` contains:

```python
{
    "skill_id": str,              # Unique skill identifier
    "name": str,                  # Display name
    "description": str,           # Description
    "version": str,               # Skill version
    "tags": List[str],            # Category tags
    "agent_types": List[str],     # Applicable agent types
    "content": str,               # Full skill content
    "source_id": str,             # Which source (e.g., "anthropic-managed")
    "source_priority": int,       # Priority for conflict resolution
    "source_file": str,           # Original file path
    "deployment_name": str        # Flattened directory name (added during deployment)
}
```

---

## Deployment Architecture

### Phase 1: Sync Skills from Git Sources

- Downloads `.md` and `.json` files from Git repositories
- Caches files in nested structure: `~/.claude_mpm/skills/cache/{source_id}/{nested/path}/`
- Example: `anthropic-managed/collaboration/parallel-agents/SKILL.md`

### Phase 2: Deploy Skills to Project Directory

- **Input**: Nested cache structure with multiple levels
- **Output**: Flat directory structure with hyphenated names
- **Target**: `./.claude/skills/` (project-level, not user-level `~/.claude/skills/`)

**Transformation Example**:
```
Cache:   collaboration/dispatching-parallel-agents/SKILL.md
Deploy:  collaboration-dispatching-parallel-agents/SKILL.md
         (single directory, hyphen-separated path)
```

### Why Flattening Matters

Claude Code expects skills in a **flat directory structure** at `~/.claude/skills/`. The deployment phase converts nested Git repository organization into this flat structure by:

1. **Path Concatenation**: Joins nested path with hyphens
2. **Directory Creation**: Creates single top-level directory per skill
3. **File Copying**: Copies all skill files (SKILL.md, manifest.json, etc.)

**Example Deployment**:
```
Source Cache:
  ~/.claude_mpm/skills/cache/anthropic-managed/
    ├── collaboration/
    │   └── parallel-agents/
    │       ├── SKILL.md
    │       └── manifest.json

Deployed:
  ./.claude/skills/
    └── collaboration-parallel-agents/
        ├── SKILL.md
        └── manifest.json
```

---

## Current Message Analysis

### Current Format

```
Deploying skills: 39/39 (100%)
```

**What it shows**:
- Total individual skills discovered across all sources
- Counter increments for each skill file processed
- Percentage of skills deployed

**What it doesn't show**:
- Number of project-level directories created
- Which sources are being deployed
- Cache vs. manifest skill counts

---

## Suggested Message Formats

### Option 1: Emphasize Project-Level Deployment (Recommended)

```
Deploying skill directories: 39/39 (100%)
```

**Rationale**: Clarifies that deployment creates **directories** (one per skill), not just copies files. This aligns with the flattening architecture.

**Completion message** (already accurate):
```
Complete: 15 deployed, 24 already present (39 total)
```

---

### Option 2: Show Source Count Context

```
Deploying skills from 3 sources: 39/39 (100%)
```

**Rationale**: Provides context about how many Git sources contributed to the 39 skills.

**Implementation**:
```python
source_count = len(enabled_sources)
deploy_progress = ProgressBar(
    total=skill_count,
    prefix=f"Deploying skills from {source_count} {'source' if source_count == 1 else 'sources'}",
    show_percentage=True,
    show_counter=True,
)
```

---

### Option 3: Two-Part Message (More Verbose)

```
Deploying skills [████████████████████] 100% (39/39)
Flattening structure from 3 sources
```

**Rationale**: Separates **count** (39 skills) from **architecture** (flattening from sources).

---

### Option 4: Simple Clarification

```
Deploying 39 skills to project
```

**Rationale**: Emphasizes destination (project directory) rather than source count.

---

## Implementation Recommendations

### Recommended Change: Option 1

**Current Code** (line 525):
```python
deploy_progress = ProgressBar(
    total=skill_count,
    prefix="Deploying skills",
    show_percentage=True,
    show_counter=True,
)
```

**Suggested Change**:
```python
deploy_progress = ProgressBar(
    total=skill_count,
    prefix="Deploying skill directories",  # Clarifies flat structure creation
    show_percentage=True,
    show_counter=True,
)
```

**Why Option 1**:
1. **Minimal change**: Only 1 word added
2. **Accurate**: Reflects that deployment creates directories
3. **User-friendly**: "directories" hints at the flattening process
4. **Consistent**: Completion message already explains deployed vs. cached

---

## Additional Context Variables Available

### Source-Level Grouping

The `manager.get_all_skills()` method internally groups skills by source:

```python
# From git_skill_source_manager.py:284
skills_by_source = {}

for source in sources:
    cache_path = self._get_source_cache_path(source)
    discovery_service = SkillDiscoveryService(cache_path)
    source_skills = discovery_service.discover_skills()

    # Tag with source metadata
    for skill in source_skills:
        skill["source_id"] = source.id
        skill["source_priority"] = source.priority

    skills_by_source[source.id] = source_skills
```

**Skills per source** can be calculated:
```python
from collections import Counter
source_counts = Counter(skill["source_id"] for skill in all_skills)
# Example: {"anthropic-managed": 38, "custom-project": 1}
```

---

## Code Flow Summary

1. **Line 446**: Get `enabled_sources` from configuration
2. **Line 496**: Sync all sources (downloads files to cache)
3. **Line 518**: Get `all_skills` (discovers skills across sources)
4. **Line 525**: **Create ProgressBar with "Deploying skills" message**
5. **Line 532**: Deploy skills (flatten to `./.claude/skills/`)
6. **Line 546**: Show completion message with deployment breakdown

---

## Related Files

- **Progress Bar Implementation**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/progress.py`
- **Skill Manager**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/skills/git_skill_source_manager.py`
- **Deployment Method**: `git_skill_source_manager.py:987` (`deploy_skills()`)
- **Skill Discovery**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/skills/discovery.py`

---

## Testing Considerations

If message is changed, update these test files:

1. **Unit Test**: `/Users/masa/Projects/claude-mpm/tests/cli/test_skills_startup_sync.py:226`
   ```python
   assert deploy_call[1]["prefix"] == "Deploying skills"
   ```

2. **Documentation**: Update all references in:
   - `PROGRESS_INDICATORS_VISUAL_COMPARISON.md`
   - `PROGRESS_INDICATORS_TEST_SUMMARY.md`
   - `STARTUP_QA_SUMMARY.md`
   - `docs/research/progress-bar-*.md`

---

## Conclusion

**File Location**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/startup.py:525`

**Current Message**: `"Deploying skills"`

**Available Data**:
- `skill_count`: Total skills (39)
- `enabled_sources`: List of Git sources (e.g., 3 sources)
- `results["synced_count"]`: Successfully synced sources
- Individual skills with `source_id` metadata

**Recommended New Message**: `"Deploying skill directories"`

**Rationale**: Clarifies that deployment creates flat directory structure, aligning user expectations with the actual flattening architecture described in code comments.

**Impact**: Low-risk change requiring test update and documentation refresh.

---

## Next Steps

1. Decide on preferred message format (Option 1 recommended)
2. Update `startup.py:525` with new message
3. Update test assertion in `test_skills_startup_sync.py:226`
4. Update documentation files referencing the old message
5. Run integration tests to verify behavior unchanged
6. Update CHANGELOG with message clarification

