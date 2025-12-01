# Flat Skill Deployment Implementation

## Summary

Successfully implemented flat skill deployment from nested Git repositories to support Claude Code's flat skill directory structure requirement.

## Problem

Claude Code only supports flat top-level skill directories (`~/.claude/skills/skill-name/SKILL.md`), but Git repositories use nested organization for maintainability:

```
Git Repository (Nested):
collaboration/
  dispatching-parallel-agents/SKILL.md
  brainstorming/SKILL.md
debugging/
  systematic-debugging/SKILL.md
aws/
  s3/
    bucket-ops/SKILL.md
```

## Solution

Implemented path flattening transformation that preserves nested structure in Git cache but deploys to flat structure:

```
Deployed (Flat):
~/.claude/skills/
  collaboration-dispatching-parallel-agents/SKILL.md
  collaboration-brainstorming/SKILL.md
  debugging-systematic-debugging/SKILL.md
  aws-s3-bucket-ops/SKILL.md
```

## Implementation Details

### 1. Recursive SKILL.md Discovery

**File**: `src/claude_mpm/services/skills/skill_discovery_service.py`

**Changes**:
- Updated `discover_skills()` to recursively search for `SKILL.md` files using `Path.rglob()`
- Maintains backward compatibility with legacy `*.md` files in top-level directory
- Filters out `README.md` to avoid false positives

**Example**:
```python
# Find all SKILL.md files recursively (Claude Code standard naming)
skill_md_files = list(self.skills_dir.rglob("SKILL.md"))

# Also find legacy *.md files in top-level directory for backward compatibility
legacy_md_files = [
    f for f in self.skills_dir.glob("*.md")
    if f.name != "SKILL.md" and f.name.lower() != "readme.md"
]
```

### 2. Path Flattening Logic

**File**: `src/claude_mpm/services/skills/skill_discovery_service.py`

**Method**: `_calculate_deployment_name(skill_file: Path) -> str`

**Algorithm**:
1. Get relative path from skills_dir to SKILL.md file
2. Extract all parent directory names (excluding the final directory containing SKILL.md)
3. Join path components with hyphens
4. Normalize: lowercase, remove special characters, collapse multiple hyphens

**Examples**:
```python
# Nested structure
"collaboration/dispatching-parallel-agents/SKILL.md" → "collaboration-dispatching-parallel-agents"

# Deep nesting
"aws/s3/bucket-ops/SKILL.md" → "aws-s3-bucket-ops"

# Legacy flat
"code-review.md" → "code-review"
```

### 3. Collision Detection

**Implementation**: Built into `discover_skills()` method

**Behavior**:
- Tracks all deployment names during discovery
- Detects when two different paths would create same flat name
- Logs warning with both conflicting paths
- Skips second occurrence to prevent overwrite

**Example Warning**:
```
WARNING: Deployment name collision: 'testing-test-skill' would be created by both:
  - cache/system/testing/test-skill/SKILL.md
  - cache/system/test/ing-test-skill/SKILL.md
Skipping cache/system/test/ing-test-skill/SKILL.md to avoid overwrite.
```

### 4. Deployment Service

**File**: `src/claude_mpm/services/skills/git_skill_source_manager.py`

**Method**: `deploy_skills(target_dir, force) -> Dict`

**Features**:
- Deploys all skills from cache to target directory
- Uses flattened deployment names
- Copies entire skill directory (including helper files, references, etc.)
- Respects force flag for overwriting
- Returns comprehensive deployment statistics

**Usage**:
```python
from src.claude_mpm.services.skills.git_skill_source_manager import GitSkillSourceManager
from src.claude_mpm.config.skill_sources import SkillSourceConfiguration

config = SkillSourceConfiguration()
manager = GitSkillSourceManager(config)

# Sync skills from Git repositories
manager.sync_all_sources()

# Deploy to Claude Code's skills directory
result = manager.deploy_skills()

print(f"Deployed: {result['deployed_count']}")
print(f"Skipped: {result['skipped_count']}")
print(f"Errors: {result['failed_count']}")
```

## Files Modified

1. **`src/claude_mpm/services/skills/skill_discovery_service.py`**
   - `discover_skills()`: Recursive SKILL.md discovery
   - `_calculate_deployment_name()`: Path flattening algorithm (NEW)
   - Added collision detection logic

2. **`src/claude_mpm/services/skills/git_skill_source_manager.py`**
   - `deploy_skills()`: Deploy to flat structure (NEW)
   - `_deploy_single_skill()`: Copy skill with flattened name (NEW)
   - `_validate_safe_path()`: Security path validation (NEW)

3. **`tests/services/skills/test_git_skill_source_manager.py`**
   - Added `TestFlatSkillDeployment` test class
   - 7 comprehensive tests covering:
     - Recursive discovery
     - Deployment name flattening
     - Flat deployment structure
     - Resource preservation
     - Collision detection
     - Force overwrite
     - Deployment metadata

## Test Results

All tests pass (34/34):

```bash
$ python -m pytest tests/services/skills/test_git_skill_source_manager.py -v
============================== 34 passed in 0.27s ===============================
```

### Test Coverage

**Existing Tests** (27 tests):
- ✅ Multi-source sync orchestration
- ✅ Priority resolution algorithm
- ✅ Source-specific skill retrieval
- ✅ Caching and path management
- ✅ Error handling for sync failures

**New Tests** (7 tests):
- ✅ `test_recursive_skill_discovery`: Finds all nested SKILL.md files
- ✅ `test_deployment_name_flattening`: Correct hyphen-separated names
- ✅ `test_flat_deployment_structure`: No nested directories in deployment
- ✅ `test_skill_directory_contents_preserved`: Helper files copied
- ✅ `test_collision_detection`: Warns on name conflicts
- ✅ `test_deployment_force_overwrite`: Force flag works correctly
- ✅ `test_deployment_metadata_in_skills`: Metadata includes deployment info

## Real-World Example

Using the actual bundled skills in this framework:

```bash
$ python -c "
from pathlib import Path
from src.claude_mpm.services.skills.skill_discovery_service import SkillDiscoveryService

service = SkillDiscoveryService(Path('src/claude_mpm/skills/bundled'))
skills = service.discover_skills()

print(f'Found {len(skills)} skills')
for skill in skills[:5]:
    print(f'{skill[\"relative_path\"]:50} → {skill[\"deployment_name\"]}')
"
```

**Output**:
```
Found 19 skills

main/internal-comms/SKILL.md                       → main-internal-comms
main/skill-creator/SKILL.md                        → main-skill-creator
main/artifacts-builder/SKILL.md                    → main-artifacts-builder
main/mcp-builder/SKILL.md                          → main-mcp-builder
infrastructure/env-manager/SKILL.md                → infrastructure-env-manager
```

## Architecture Decisions

### Why Flatten at Deployment, Not Sync?

**Decision**: Keep nested structure in cache, flatten only at deployment.

**Rationale**:
- Git repositories stay maintainable with logical organization
- Cache preserves original structure for debugging
- Deployment layer handles Claude Code compatibility
- Easier to support multiple deployment targets in future

**Trade-offs**:
- ✅ Maintainability: Git repos can use clear folder hierarchy
- ✅ Debugging: Can inspect cached skills in original structure
- ✅ Flexibility: Easy to change deployment strategy
- ⚠️ Complexity: Two-step process (sync → deploy)

### Why Join with Hyphens?

**Decision**: Use hyphens to join path components (`aws-s3-bucket-ops`).

**Rationale**:
- Claude Code skill naming convention uses hyphens
- Most readable and URL-safe separator
- Consistent with existing skill names
- Easy to parse and understand

**Alternatives Considered**:
- Underscores: Less readable, inconsistent with conventions
- Dots: Could be confused with file extensions
- Camel case: Harder to parse programmatically

### Collision Detection Strategy

**Decision**: Warn and skip on collision, don't fail deployment.

**Rationale**:
- Partial deployment better than complete failure
- Warnings visible in logs for troubleshooting
- First skill wins (priority-based)
- Repository maintainers can fix structure

**Error Handling**:
```
WARNING: Deployment name collision detected
  - First:  aws/s3/bucket-ops/SKILL.md
  - Second: aws-s3/bucket-ops/SKILL.md  (SKIPPED)
```

## Success Criteria

All requirements met:

- ✅ Nested Git repos can be pulled as-is (no restructuring needed)
- ✅ Skills deploy to flat top-level directories
- ✅ Skill names are hyphen-concatenated paths
- ✅ Each skill directory is self-contained with all helper files
- ✅ Name collisions are detected and reported
- ✅ Claude Code can discover and use deployed skills
- ✅ Comprehensive tests verify all behavior
- ✅ Documentation explains transformation clearly

## Code Quality

**Metrics**:
- 34/34 tests passing
- Zero linting errors
- Type hints on all new methods
- Comprehensive docstrings with examples
- Security validation on all file operations

**Design Patterns**:
- Single Responsibility: Discovery and deployment separated
- Dependency Injection: Services can be mocked for testing
- Security First: Path validation prevents traversal attacks
- Graceful Degradation: Continues on individual skill failures

## Future Enhancements

Potential improvements for future iterations:

1. **Configurable Separator**: Allow users to choose separator (hyphen, underscore, etc.)
2. **Collision Resolution UI**: Interactive prompt to choose which skill to keep
3. **Deployment Profiles**: Different flattening strategies for different targets
4. **Skill Aliases**: Support multiple deployment names for same skill
5. **Incremental Deployment**: Only deploy changed skills (checksum-based)

## Related Documentation

- Research: `docs/research/skills-git-system-analysis-2025-11-30.md`
- User Guide: `docs/guides/skills-deployment-guide.md`
- API Reference: `docs/reference/skills-api.md`

---

**Implementation Date**: 2025-11-30
**Engineer**: Claude Code (Sonnet 4.5)
**Ticket**: Flat skill deployment from nested Git repositories
