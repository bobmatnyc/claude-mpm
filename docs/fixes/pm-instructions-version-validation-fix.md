# Fix Summary: PM Instructions Version Validation

## Problem
PM was loading stale PM_INSTRUCTIONS v0006 instead of current v0007 due to missing version validation.

### Root Cause
`instruction_loader.py` had early return when `PM_INSTRUCTIONS_DEPLOYED.md` existed, without checking if the deployed version was stale compared to source.

**Before Fix:**
```python
# Lines 104-113 (OLD CODE)
deployed_path = self.current_dir / ".claude-mpm" / "PM_INSTRUCTIONS_DEPLOYED.md"
if deployed_path.exists():
    loaded_content = self.file_loader.try_load_file(
        deployed_path, "deployed PM_INSTRUCTIONS_DEPLOYED.md"
    )
    if loaded_content:
        content["framework_instructions"] = loaded_content
        content["loaded"] = True
        self.logger.info("Loaded PM_INSTRUCTIONS_DEPLOYED.md from .claude-mpm/")
        return  # ❌ PROBLEM: No version check!
```

### Symptoms
- Source file: v0007 (Dec 22 23:59)
- Deployed file: v0006 (Dec 22 16:39)
- PM loaded: v0006 (stale)
- Silent failure (no warning logs)

## Solution

### 1. Added Version Extraction Method
```python
def _extract_version(self, file_content: str) -> int:
    """Extract version number from PM_INSTRUCTIONS_VERSION comment.

    Args:
        file_content: Content of the file to extract version from

    Returns:
        Version number as integer, or 0 if not found
    """
    import re

    match = re.search(r"PM_INSTRUCTIONS_VERSION:\s*(\d+)", file_content)
    if match:
        return int(match.group(1))
    return 0  # No version = oldest
```

### 2. Added Version Validation Logic
```python
# Lines 128-157 (NEW CODE)
if deployed_path.exists():
    # ✓ Validate version before using deployed file
    deployed_content = deployed_path.read_text()
    deployed_version = self._extract_version(deployed_content)

    # Check source version for comparison
    if pm_instructions_path.exists():
        source_content = pm_instructions_path.read_text()
        source_version = self._extract_version(source_content)

        if deployed_version < source_version:
            # ✓ Reject stale deployed file
            self.logger.warning(
                f"Deployed PM instructions v{deployed_version:04d} is stale, "
                f"source is v{source_version:04d}. Using source instead."
            )
            # Fall through to source loading - don't return early
        else:
            # Version OK, use deployed
            content["framework_instructions"] = deployed_content
            content["loaded"] = True
            self.logger.info(
                f"Loaded PM_INSTRUCTIONS_DEPLOYED.md v{deployed_version:04d} from .claude-mpm/"
            )
            return  # Stop here - deployed version is current
```

### 3. Forced Redeploy
Removed stale deployed file to trigger fresh deployment:
```bash
rm -f .claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md
```

## Verification

### Test Results
All test cases passed:

**Test Case 1: No deployed file**
- ✓ Uses source v0007
- ✓ Logs warning about missing deployed file

**Test Case 2: Stale deployed file (v0006)**
- ✓ Detects version mismatch
- ✓ Rejects stale v0006
- ✓ Falls through to source v0007
- ✓ Logs warning: "Deployed PM instructions v0006 is stale, source is v0007"

**Test Case 3: Current deployed file (v0007)**
- ✓ Uses deployed v0007
- ✓ Logs success: "Loaded PM_INSTRUCTIONS_DEPLOYED.md v0007"

### Current State
- Source: v0007 (44,051 chars)
- Deployed: REMOVED (will be regenerated on next deploy)
- PM loads: v0007 ✓

## Files Modified

### `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/framework/loaders/instruction_loader.py`
- Added `_extract_version()` method (lines 91-105)
- Enhanced `_load_filesystem_framework_instructions()` with version validation (lines 107-157)
- Removed duplicate `pm_instructions_path` definition

**Lines Changed:** ~50 lines modified
**LOC Delta:** +30 lines (version validation logic)

## Benefits

1. **Prevents Stale Versions**: Deployed files are validated against source
2. **Clear Warnings**: Logs explicit version mismatch warnings
3. **Automatic Fallback**: Falls through to source when deployed is stale
4. **Future-Proof**: Any v0008, v0009, etc. will automatically be preferred

## Edge Cases Handled

1. **No deployed file**: Uses source (existing behavior)
2. **Stale deployed file**: Uses source (NEW - fixed)
3. **Current deployed file**: Uses deployed (existing behavior)
4. **No version in deployed**: Treated as v0000, source preferred
5. **No version in source**: Both v0000, deployed used (backward compat)
6. **Source doesn't exist**: Uses deployed even if no version (production mode)

## Rollout

### Immediate Effect
- PM now loads v0007 correctly ✓
- No breaking changes (backward compatible)
- Existing workflows unaffected

### Next Deploy
When `mpm deploy` runs next:
1. Will create new `PM_INSTRUCTIONS_DEPLOYED.md` with v0007
2. Version validation will pass
3. Deployed file will be used for performance

## Monitoring

Check logs for version warnings:
```bash
grep "PM instructions.*stale" ~/.claude-mpm/logs/latest.log
```

Expected output if deployed is stale:
```
WARNING - Deployed PM instructions v0006 is stale, source is v0007. Using source instead.
```

## Related Files
- Source: `src/claude_mpm/agents/PM_INSTRUCTIONS.md` (v0007)
- Deployed: `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md` (removed, will regenerate)
- Cache: `.claude-mpm/PM_INSTRUCTIONS.md` (v0006, not used by loader)

---

**Status**: ✅ FIXED AND VERIFIED
**Version Now Loaded**: v0007
**Date**: 2025-12-23
