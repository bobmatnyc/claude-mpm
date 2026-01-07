# User-Requested Skills Feature

## Overview

This feature allows users to manually select and manage skills beyond what agents automatically reference. User-requested skills are protected from automatic cleanup, giving users control over their skill configuration.

## Architecture

### Core Components

1. **Deployment Index** (`~/.claude/skills/.mpm-deployed-skills.json`):
   ```json
   {
     "deployed_skills": {
       "skill-name": {
         "collection": "claude-mpm-skills",
         "deployed_at": "2025-12-22T10:30:00Z"
       }
     },
     "user_requested_skills": [
       "django-framework",
       "fastapi-patterns",
       "playwright-e2e-testing"
     ],
     "last_sync": "2025-12-22T10:30:00Z"
   }
   ```

2. **Programmatic API** (`selective_skill_deployer.py`):
   - `get_user_requested_skills(claude_skills_dir: Path) -> List[str]`
   - `add_user_requested_skill(skill_name: str, claude_skills_dir: Path) -> bool`
   - `remove_user_requested_skill(skill_name: str, claude_skills_dir: Path) -> bool`
   - `is_user_requested_skill(skill_name: str, claude_skills_dir: Path) -> bool`

3. **Orphan Cleanup Protection**:
   - Modified `cleanup_orphan_skills()` to preserve user-requested skills
   - User-requested skills are treated as required (never cleaned up)
   - Final required set = `agent_referenced ∪ user_requested`

### Interactive CLI Command

The existing `claude-mpm skills configure` command was enhanced to:
- Track user-requested skills when installing via interactive selection
- Show `[user]` label for user-requested skills
- Automatically add/remove skills from user_requested_skills list
- Protect user-requested skills from orphan cleanup

#### Usage Example

```bash
# Interactive skill selection
claude-mpm skills configure
```

**Interactive Flow**:
1. Shows all available skills from GitHub with checkboxes
2. Pre-selects already installed skills
3. Marks user-requested skills with `[user]` label
4. User selects/deselects skills using Space key
5. Shows summary of changes (install/remove)
6. Apply/Adjust/Cancel options
7. Installs selected skills and marks them as user-requested
8. Removes deselected skills from user-requested list

#### UI Example

```
Interactive Skills Configuration

Select skills to install/uninstall using checkboxes
● = Installed, ○ = Available
[user] = User-requested (protected from auto-cleanup)

Fetching available skills from GitHub...

? Select skills (Space to toggle, Enter to confirm):
 ◉ django-framework (python) [user]
 ◯ fastapi-patterns (python)
 ◉ playwright-e2e-testing (testing) [user]
 ◯ react-hooks-patterns (javascript)
 ◉ systematic-debugging (universal)
```

## Benefits

### For Users

1. **Manual Control**: Install any skill regardless of agent references
2. **Protected from Cleanup**: User-requested skills are never auto-removed
3. **Visual Feedback**: `[user]` label clearly shows which skills are user-requested
4. **Flexible Management**: Add/remove skills via interactive UI

### For System

1. **Backward Compatible**: Old index files without `user_requested_skills` work fine
2. **Clear Separation**: Agent-referenced vs user-requested skills are distinct
3. **Consistent API**: Same interface as other skill management functions
4. **Well Tested**: Comprehensive test coverage for all scenarios

## Implementation Details

### Deployment Index Structure

The index now has three key fields:
- `deployed_skills`: All deployed skills with metadata
- `user_requested_skills`: Skills manually requested by user (protected list)
- `last_sync`: Last sync timestamp

### Orphan Cleanup Logic

```python
# Old logic (before user-requested skills)
orphaned = tracked_skills - required_skills

# New logic (with user-requested skills)
user_requested = set(index.get("user_requested_skills", []))
all_required = required_skills | user_requested  # Union
orphaned = tracked_skills - all_required
```

### Interactive CLI Integration

The `_configure_skills()` method in `cli/commands/skills.py` was enhanced:
1. Loads `user_requested_skills` from index
2. Shows `[user]` label for user-requested skills
3. Calls `add_user_requested_skill()` when installing
4. Calls `remove_user_requested_skill()` when removing
5. Updates skill status on each install/remove operation

## Testing

Comprehensive test coverage in `tests/services/skills/test_selective_skill_deployer.py`:

### Test Classes

1. **TestUserRequestedSkills**: Tests for add/remove/get operations
   - `test_add_user_requested_skill`
   - `test_add_duplicate_user_requested_skill`
   - `test_remove_user_requested_skill`
   - `test_remove_nonexistent_user_requested_skill`
   - `test_is_user_requested_skill`
   - `test_get_user_requested_skills_empty`
   - `test_get_user_requested_skills_multiple`

2. **TestCleanupOrphanSkillsWithUserRequested**: Tests for orphan cleanup
   - `test_cleanup_preserves_user_requested_skills`
   - `test_cleanup_with_no_user_requested_skills`
   - `test_cleanup_all_skills_protected`

3. **TestDeploymentIndexBackwardCompatibility**: Tests for backward compatibility
   - `test_load_old_index_without_user_requested_skills`
   - `test_save_and_load_index_preserves_user_requested`

### Test Results

All 33 tests pass, including the 12 new tests for user-requested skills functionality.

## Migration Guide

### From Old System

No migration needed - the system is fully backward compatible:
1. Old index files without `user_requested_skills` are auto-upgraded
2. New field is added as empty list on first load
3. Existing deployed skills are preserved

### For Developers

If you're using the selective skill deployer API:

```python
from pathlib import Path
from claude_mpm.services.skills.selective_skill_deployer import (
    add_user_requested_skill,
    get_user_requested_skills,
    remove_user_requested_skill,
)

# Get Claude skills directory
claude_skills_dir = Path.home() / ".claude" / "skills"

# Add user-requested skill
add_user_requested_skill("django-framework", claude_skills_dir)

# Check user-requested skills
user_skills = get_user_requested_skills(claude_skills_dir)
print(f"User requested: {user_skills}")

# Remove user-requested skill
remove_user_requested_skill("django-framework", claude_skills_dir)
```

## Future Enhancements

Potential improvements for future versions:

1. **Bulk Operations**: Add/remove multiple skills at once via CLI
2. **Skill Collections**: Group related user-requested skills
3. **Skill Profiles**: Save/load skill configurations as profiles
4. **Skill Dependencies**: Auto-add dependent skills when user requests parent
5. **Skill Recommendations**: Suggest skills based on project analysis

## Related Files

- Implementation: `src/claude_mpm/services/skills/selective_skill_deployer.py`
- CLI Command: `src/claude_mpm/cli/commands/skills.py`
- Tests: `tests/services/skills/test_selective_skill_deployer.py`
- Parser: `src/claude_mpm/cli/parsers/skills_parser.py`
- Constants: `src/claude_mpm/constants.py` (SkillsCommands.CONFIGURE)

## LOC Delta

**Added**: ~260 lines (API functions + tests + CLI integration)
**Modified**: ~80 lines (existing functions updated)
**Net Change**: +340 lines

**Breakdown**:
- API functions in `selective_skill_deployer.py`: +120 lines
- Test classes in `test_selective_skill_deployer.py`: +240 lines
- CLI integration in `skills.py`: +40 lines (modified existing method)
- Index structure updates: -40 lines (consolidated)

## Conclusion

The user-requested skills feature provides a clean, well-tested, and backward-compatible way for users to manually manage their skill configuration. The interactive CLI makes it easy to use, while the programmatic API enables automation and integration with other tools.
