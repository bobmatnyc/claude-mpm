# Git Sync Progress Bar Investigation

**Date**: 2025-12-01
**Investigator**: Research Agent
**Status**: Root Cause Identified
**Severity**: Medium (User-facing bug, cosmetic but confusing)

## Executive Summary

The skills sync progress bar is stuck at 0% and shows incorrect counts (1/272 vs expected behavior) due to a **fundamental mismatch between how the progress callback is being called vs. how the ProgressBar expects updates**.

**Root Cause**: Skills sync passes **incremental updates** (`progress_callback(1)`) but ProgressBar expects **absolute positions** (`update(current_position)`).

**Impact**:
- Skills sync progress bar stuck at 0% despite files being synced
- Misleading user feedback (shows 1/272 when it should show progress)
- Inconsistent terminology ("Deploying skills" vs "Syncing skills")

## Problem Details

### 1. Progress Bar Stuck at 0% (1/272)

**User Report**:
```
Syncing skills [░░░░░░░░░░░░░░░░░░░░] 0% (1/272)
```

**Expected Behavior**:
```
Syncing skills [████░░░░░░░░░░░░░░░░] 18% (50/272)
Syncing skills [████████░░░░░░░░░░░░] 36% (100/272)
Syncing skills [████████████████████] 100% (272/272)
```

### 2. Wording Inconsistency

**Current Output**:
```
Syncing skills [░░░░░░░░░░░░░░░░░░░░] 0% (1/272)        # Phase 1: File sync
Deploying skills [████████████████████] 100% (37/37)     # Phase 2: Skill deployment
```

**Expected Output**:
```
Syncing skills [████████████████████] 100% (272/272)    # Phase 1: File sync
Deploying skills [████████████████████] 100% (37/37)    # Phase 2: Skill deployment
```

## Root Cause Analysis

### How Agents Work (CORRECT Implementation)

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/sources/git_source_sync_service.py`
**Lines**: 281-285

```python
for idx, agent_filename in enumerate(agent_list, start=1):
    try:
        # Update progress bar with current file
        if progress_bar:
            progress_bar.update(idx, message=agent_filename)  # ← ABSOLUTE POSITION
```

**Key Point**: Agents pass `idx` (1, 2, 3, ..., N) which is the **absolute position**.

### How Skills Sync Works (BROKEN Implementation)

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/skills/git_skill_source_manager.py`
**Lines**: 486-488

```python
# Call progress callback if provided
if progress_callback:
    progress_callback(1)  # ← INCREMENTAL UPDATE (WRONG!)
```

**Key Point**: Skills pass `1` for every file, expecting the callback to **accumulate** the increments.

### ProgressBar Implementation

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/progress.py`
**Lines**: 148-164

```python
def update(self, current: int, message: str = "") -> None:
    """Update progress bar to current position.

    Args:
        current: Current progress value (0 to total)  # ← EXPECTS ABSOLUTE POSITION
        message: Optional message to display after progress bar (e.g., filename)
    """
    self.current = min(current, self.total)  # Clamp to total
```

**Key Point**: ProgressBar expects `current` to be the **absolute position** (50 out of 272), not an increment (+1).

### Why Progress Stays at 0%

1. **First file syncs**: `progress_callback(1)` → ProgressBar sets `self.current = 1`
2. **Second file syncs**: `progress_callback(1)` → ProgressBar sets `self.current = 1` (again!)
3. **Third file syncs**: `progress_callback(1)` → ProgressBar sets `self.current = 1` (still 1!)
4. **Result**: Progress bar never advances beyond 1/272 = 0.36% → displays as 0%

### Why Agents Work Correctly

Agents use `enumerate(agent_list, start=1)` which gives:
- 1st file: `idx=1` → `update(1)` → 1/N
- 2nd file: `idx=2` → `update(2)` → 2/N
- 3rd file: `idx=3` → `update(3)` → 3/N
- **Result**: Progress advances correctly

## Code Locations

### 1. Skills Sync Bug (PRIMARY ISSUE)

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/skills/git_skill_source_manager.py`

**Location 1: File Sync Phase** (Line 486-488):
```python
# Call progress callback if provided
if progress_callback:
    progress_callback(1)  # BUG: Should pass cumulative count, not increment
```

**Location 2: Deployment Phase** (Line 769-770):
```python
if progress_callback:
    progress_callback(1)  # BUG: Same issue in deployment
```

### 2. Progress Bar Implementation (CORRECT)

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/progress.py`

**Line 148-164**: `update()` method expects absolute position

### 3. Skills Sync Entry Point

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/startup.py`

**Sync Phase** (Line 472-482):
```python
sync_progress = ProgressBar(
    total=total_file_count if total_file_count > 0 else 1,
    prefix="Syncing skills",
    show_percentage=True,
    show_counter=True,
)

results = manager.sync_all_sources(
    force=False, progress_callback=sync_progress.update
)
```

**Deployment Phase** (Line 498-508):
```python
deploy_progress = ProgressBar(
    total=skill_count,
    prefix="Deploying skills",  # ← Correct terminology (this is actual deployment)
    show_percentage=True,
    show_counter=True,
)

deployment_result = manager.deploy_skills(
    force=False, progress_callback=deploy_progress.update
)
```

## Understanding 272 vs 37 Discrepancy

**272 files**: Total files in Git repository (includes all `.md`, `.json`, `.gitignore` files)
- This is the **file sync count** (Phase 1: downloading raw files from GitHub)
- Calculated via GitHub Tree API in `startup.py` lines 442-469

**37 skills**: Actual skills discovered after parsing (only valid `SKILL.md` files with metadata)
- This is the **skill deployment count** (Phase 2: deploying to `~/.claude/skills/`)
- Some files are not skills (README.md, metadata.json, etc.)
- Some files are documentation or nested directories

**Code Location for File Count** (`startup.py` line 454-464):
```python
# Use Tree API to discover all files
all_files = manager._discover_repository_files_via_tree_api(
    owner_repo, source.branch
)

# Count relevant files (markdown, JSON)
relevant_files = [
    f
    for f in all_files
    if f.endswith(".md") or f.endswith(".json") or f == ".gitignore"
]
total_file_count += len(relevant_files)  # This is 272
```

**Code Location for Skill Count** (`startup.py` line 493-494):
```python
all_skills = manager.get_all_skills()
skill_count = len(all_skills)  # This is 37
```

## Solution Options

### Option 1: Change Skills to Use Absolute Position (Recommended)

**Pros**:
- Consistent with agents implementation
- No API change to ProgressBar
- More intuitive for developers

**Cons**:
- Requires tracking file index in skills sync

**Implementation**: Add counter tracking in `_recursive_sync_repository()`:

```python
def _recursive_sync_repository(
    self,
    source: SkillSource,
    cache_path: Path,
    force: bool = False,
    progress_callback=None,
) -> Tuple[int, int]:
    # ... existing code ...

    files_updated = 0
    files_cached = 0

    for idx, file_path in enumerate(relevant_files, start=1):  # ← Add enumerate
        # ... download logic ...

        if progress_callback:
            progress_callback(idx)  # ← Pass absolute position, not increment
```

### Option 2: Create Wrapper for Incremental Updates

**Pros**:
- No changes to existing skills sync logic
- Encapsulates accumulation logic

**Cons**:
- Additional complexity
- Two different callback patterns in codebase

**Implementation**: Create accumulating wrapper in `startup.py`:

```python
# Create accumulating progress callback
current_count = 0
def accumulating_callback(increment: int):
    nonlocal current_count
    current_count += increment
    sync_progress.update(current_count)

results = manager.sync_all_sources(
    force=False, progress_callback=accumulating_callback
)
```

### Option 3: Change ProgressBar API to Support Both Modes

**Pros**:
- Supports both incremental and absolute updates
- Backward compatible

**Cons**:
- API complexity
- Potential for misuse

**Implementation**: Add mode parameter to ProgressBar

## Recommendation

**Use Option 1**: Change skills sync to use absolute positioning.

**Rationale**:
1. Consistent with existing agents implementation
2. Simpler mental model (position vs. increment)
3. No additional abstraction layers
4. Easier to debug and reason about

## Next Steps

1. **Fix skills sync progress** (HIGH PRIORITY):
   - Modify `_recursive_sync_repository()` to use `enumerate()` and pass absolute position
   - Modify `deploy_skills()` to use `enumerate()` and pass absolute position
   - Test with actual sync operation

2. **Verify agents sync still works** (MEDIUM PRIORITY):
   - Agents already use correct pattern, no changes needed
   - Regression test to ensure no unintended side effects

3. **Update documentation** (LOW PRIORITY):
   - Document progress callback API contract
   - Clarify that callbacks receive absolute position, not increments

## Testing Checklist

- [ ] Skills sync progress bar advances correctly
- [ ] Skills sync progress reaches 100%
- [ ] Final count matches total files (272/272)
- [ ] Agents sync still works correctly (regression test)
- [ ] Deployment phase shows correct terminology
- [ ] Both TTY and non-TTY modes work

## Related Files

### Primary Changes Required
1. `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/skills/git_skill_source_manager.py`
   - Line 486-488: Fix `_recursive_sync_repository()` callback
   - Line 769-770: Fix `deploy_skills()` callback

### No Changes Required (Already Correct)
1. `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/progress.py`
   - ProgressBar implementation is correct
2. `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/sources/git_source_sync_service.py`
   - Agents already use correct pattern
3. `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/startup.py`
   - Entry point is correct, just passes callback through

## Appendix: Progress Callback API Contract

**Expected Signature**:
```python
def progress_callback(current: int) -> None:
    """Called with current absolute position.

    Args:
        current: Current count (1 to total), not an increment

    Example:
        callback(1)   # First item
        callback(2)   # Second item
        callback(3)   # Third item
    """
```

**NOT**:
```python
def progress_callback(increment: int) -> None:
    """WRONG: This is not how the API works"""
    callback(1)  # +1
    callback(1)  # +1 (this doesn't add up!)
```
