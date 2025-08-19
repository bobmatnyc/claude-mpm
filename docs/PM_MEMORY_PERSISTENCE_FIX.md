# PM Memory Persistence Fix Documentation

## Issue Summary
The PM (Project Manager) agent's memories were not persisting properly across projects due to several issues:
1. Memory files were being deleted during migration instead of preserved
2. PM memories were being saved to project-level directory instead of user-level
3. Memory hook service had placeholder implementation and wasn't actually saving memories

## Fixes Implemented

### 1. Migration Logic Fix (agent_memory_manager.py)
**Location**: `_get_memory_file_with_migration` method

**Changes**:
- Added special handling for PM agent during migration
- PM memory files are now backed up instead of deleted during migration
- Other agents still have old files deleted to avoid confusion

**Code Changes**:
```python
# Special handling for PM to preserve memories
is_pm = agent_id.upper() == "PM"

if is_pm:
    # For PM, create backup instead of deleting
    backup_file = directory / f"{agent_id}_agent.md.backup"
    old_file_agent.rename(backup_file)
else:
    # For other agents, delete old file
    old_file_agent.unlink()
```

### 2. Directory Selection Logic Fix
**Location**: Multiple methods in `agent_memory_manager.py`

**Changes in `load_agent_memory`**:
- PM always loads from user-level directory (`~/.claude-mpm/memories/`)
- Other agents use both user and project directories with aggregation

**Changes in `_save_memory_file`**:
- PM memories always save to user directory
- Added explicit PM detection: `is_pm = agent_id.upper() == "PM"`
- Enhanced logging to show which directory was used

**Changes in `_create_default_memory`**:
- Added `use_user_dir` parameter
- PM default memories created in user directory
- Other agents create defaults in project directory

### 3. Memory Hook Service Implementation
**Location**: `memory_hook_service.py`

**Changes in `_save_new_memories_hook`**:
- Replaced placeholder with actual implementation
- Extracts agent_id from context (defaults to PM if not found)
- Extracts response text from various possible locations
- Calls `AgentMemoryManager.extract_and_update_memory()`
- Added comprehensive error handling and logging

**Key Implementation**:
```python
# Extract agent_id from various possible locations
agent_id = data.get('agent_id') or \
           data.get('agent_type') or \
           data.get('subagent_type') or \
           "PM"  # Default to PM

# Extract and save memories
memory_manager = get_memory_manager()
success = memory_manager.extract_and_update_memory(agent_id, response_text)
```

### 4. Enhanced Logging
**Throughout all modified files**:

- Added debug logging for PM detection
- Log which directory (user vs project) is being used
- Log memory extraction and saving operations
- Include memory item previews in logs
- Added info logs for successful operations

## Testing Results

### Test Coverage
1. ✅ PM memories saved to user directory
2. ✅ Other agent memories saved to project directory
3. ✅ PM memory migration preserves old files (creates backups)
4. ✅ PM memories persist across different projects
5. ✅ Duplicate prevention still works correctly
6. ✅ Memory hook service extracts and saves memories

### Verification Commands
```bash
# Run the test suite
python scripts/test_pm_memory_persistence.py

# Check PM memory location
ls -la ~/.claude-mpm/memories/PM_memories.md

# Check project memories
ls -la .claude-mpm/memories/

# View PM memory content
cat ~/.claude-mpm/memories/PM_memories.md
```

## Directory Structure After Fix
```
~/.claude-mpm/memories/           # User-level (global) memories
├── PM_memories.md                # PM memories (always here)
├── PM.md.backup                   # Backup of old format (if migrated)
└── [other global agent memories]

./.claude-mpm/memories/           # Project-level memories
├── engineer_memories.md          # Engineer agent memories
├── research_memories.md          # Research agent memories
├── qa_memories.md                # QA agent memories
└── [other project-specific agent memories]
```

## Key Behavioral Changes

1. **PM Memory Persistence**: PM memories now persist across all projects since they're stored at the user level
2. **Migration Safety**: Old PM memory files are backed up instead of deleted
3. **Automatic Memory Extraction**: Hook service now automatically extracts memories from agent responses
4. **Clear Separation**: PM memories (global coordination) vs other agent memories (project-specific)

## Impact on System

- **Backward Compatible**: Existing memory files are preserved and migrated
- **No Breaking Changes**: All existing APIs and interfaces maintained
- **Enhanced Reliability**: PM won't lose memories when switching projects
- **Better Debugging**: Comprehensive logging for troubleshooting

## Future Improvements

1. Consider adding memory versioning for rollback capability
2. Add memory export/import functionality
3. Implement memory compression for very large memories
4. Add memory search and cross-reference capabilities