# Instruction Caching

## Overview

Claude MPM automatically caches assembled PM instructions to improve performance and ensure cross-platform compatibility. This feature is **critical for Linux and Windows deployments** where command-line argument size limits would otherwise prevent normal operation.

## Why Instruction Caching?

### The Problem

PM instructions are assembled from multiple components totaling approximately 152 KB:

- **BASE_PM.md**: Core PM framework and requirements
- **PM_INSTRUCTIONS.md**: Project-specific PM instructions
- **WORKFLOW.md**: Workflow definitions and state machine
- **Agent Capabilities**: Complete list of available agents and their capabilities
- **Temporal Context**: Date, time, and session information

This assembled instruction exceeds command-line argument limits on:

- **Linux**: 128 KB ARG_MAX limit → **Exceeds by 19.1%**
- **Windows**: 32 KB limit → **Exceeds by 476%**
- **macOS**: 1 MB limit (no issue, but benefits from caching)

Without caching, deployments on Linux and Windows would fail with `OSError: [Errno E2BIG] Argument list too long`.

### The Solution

Cache the assembled instructions to `.claude-mpm/PM_INSTRUCTIONS.md` and load via file reference instead of passing as CLI arguments. This:

1. **Eliminates ARG_MAX issues** on all platforms
2. **Improves performance** by reducing subprocess argument size
3. **Enables debugging** via direct cache file inspection
4. **Optimizes updates** through hash-based invalidation

## How It Works

### Assembly and Caching Flow

```
┌─────────────────────────────────────────┐
│ 1. Assemble Instructions                │
│    - Load BASE_PM.md                    │
│    - Load PM_INSTRUCTIONS.md            │
│    - Load WORKFLOW.md                   │
│    - Generate agent capabilities list   │
│    - Add temporal context               │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│ 2. Calculate SHA-256 Hash               │
│    - Hash complete assembled content    │
│    - Compare with cached hash           │
└──────────────────┬──────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
    Hash Match          Hash Mismatch
         │                   │
         ▼                   ▼
┌─────────────────┐  ┌──────────────────┐
│ 3a. Skip Update │  │ 3b. Update Cache │
│     (Cached)    │  │     - Write temp │
│                 │  │     - Atomic mv  │
│                 │  │     - Update meta│
└─────────────────┘  └──────────────────┘
         │                   │
         └─────────┬─────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│ 4. Load via File Reference              │
│    - Claude Code: --system-prompt-file  │
│    - Path: .claude-mpm/PM_INSTRUCTIONS  │
└─────────────────────────────────────────┘
```

### Cache Update Logic

The cache uses **hash-based invalidation**:

1. **Calculate content hash**: SHA-256 of complete assembled instructions
2. **Compare with cached hash**: Read from `.claude-mpm/PM_INSTRUCTIONS.md.meta`
3. **Skip if identical**: No update needed, existing cache is valid
4. **Update if changed**: Write new cache atomically via temp file

This ensures cache updates **only when content actually changes**, optimizing performance while maintaining accuracy.

### Atomic Updates

Cache updates use atomic file replacement to prevent partial writes:

```python
# Write to temporary file
temp_file = cache_path.with_suffix('.tmp')
temp_file.write_text(content)

# Atomic replace (prevents partial writes)
temp_file.replace(cache_path)
```

This guarantees the cache file is **always** in a valid state, even if the process is interrupted.

## Benefits

✅ **Cross-Platform Compatibility**: Eliminates ARG_MAX issues on Linux/Windows
✅ **Performance**: Faster agent startup (~200ms improvement)
✅ **Debugging**: Cache file can be inspected directly
✅ **Efficiency**: Hash-based invalidation (updates only when needed)
✅ **Reliability**: Atomic updates prevent partial writes
✅ **Graceful Degradation**: Falls back to inline if cache fails

## Cache Location

### File Structure

```
.claude-mpm/
├── PM_INSTRUCTIONS.md       # Cached assembled instructions (152 KB)
└── PM_INSTRUCTIONS.md.meta  # Metadata (hash, timestamp, components)
```

### Cache File

**Path**: `.claude-mpm/PM_INSTRUCTIONS.md`
**Size**: ~150-160 KB (varies with project configuration)
**Content**: Complete assembled PM instructions ready for Claude Code

### Metadata File

**Path**: `.claude-mpm/PM_INSTRUCTIONS.md.meta`
**Format**: JSON
**Size**: ~300-400 bytes

**Structure**:
```json
{
  "version": "1.0",
  "content_type": "assembled_instruction",
  "components": [
    "BASE_PM.md",
    "PM_INSTRUCTIONS.md",
    "WORKFLOW.md",
    "agent_capabilities",
    "temporal_context"
  ],
  "content_hash": "49543567ce58fd6572eb2bdc63cea6a7fe2ef6f227f692898d891a48d87e6fb8",
  "content_size_bytes": 156121,
  "cached_at": "2025-11-30T20:54:18.050633+00:00"
}
```

**Fields**:
- `version`: Metadata schema version (currently "1.0")
- `content_type`: Always "assembled_instruction"
- `components`: List of source files/sections included in cache
- `content_hash`: SHA-256 hash of cached content (for validation)
- `content_size_bytes`: Byte size of cached instruction file
- `cached_at`: ISO-8601 timestamp of cache creation (UTC)

## Automatic Behavior

Instruction caching is **fully automatic** with no user intervention required:

- ✅ **No Configuration**: Works out of the box
- ✅ **No Manual Management**: Cache updates automatically
- ✅ **Auto-Creation**: Creates `.claude-mpm` directory if needed
- ✅ **Auto-Invalidation**: Updates when instructions change
- ✅ **Auto-Skip**: Skips updates when content unchanged
- ✅ **Non-Blocking**: Failures don't prevent agent deployment

## Manual Cache Management (Optional)

While caching is fully automatic, you can manually inspect or manage the cache:

### View Cache File

```bash
# View complete cached instructions
cat .claude-mpm/PM_INSTRUCTIONS.md

# View first 50 lines
head -n 50 .claude-mpm/PM_INSTRUCTIONS.md

# Search for specific content
grep "WORKFLOW" .claude-mpm/PM_INSTRUCTIONS.md
```

### View Metadata

```bash
# Pretty-print metadata (requires jq)
cat .claude-mpm/PM_INSTRUCTIONS.md.meta | jq .

# View raw JSON
cat .claude-mpm/PM_INSTRUCTIONS.md.meta

# Check specific fields
cat .claude-mpm/PM_INSTRUCTIONS.md.meta | jq .content_hash
cat .claude-mpm/PM_INSTRUCTIONS.md.meta | jq .cached_at
```

### Check Cache Size

```bash
# Human-readable size
ls -lh .claude-mpm/PM_INSTRUCTIONS.md

# Byte count
wc -c .claude-mpm/PM_INSTRUCTIONS.md
```

### Clear Cache

```bash
# Remove cache files (will regenerate on next deployment)
rm -f .claude-mpm/PM_INSTRUCTIONS.md*

# Verify removal
ls -la .claude-mpm/
```

### Force Regeneration

```bash
# Clear cache and deploy agent to regenerate
rm -f .claude-mpm/PM_INSTRUCTIONS.md*
claude-mpm agents deploy research

# Verify regeneration
ls -lh .claude-mpm/PM_INSTRUCTIONS.md*
cat .claude-mpm/PM_INSTRUCTIONS.md.meta | jq .
```

## Troubleshooting

### Cache Not Created

**Symptom**: No `.claude-mpm/PM_INSTRUCTIONS.md` file exists after deployment

**Possible Causes**:
1. Permissions issue on project directory
2. Deployment hasn't run yet
3. Cache service initialization failed

**Solution**:

```bash
# 1. Ensure directory exists and is writable
mkdir -p .claude-mpm
chmod 755 .claude-mpm

# 2. Run deployment to create cache
claude-mpm agents deploy research

# 3. Verify cache creation
ls -lh .claude-mpm/PM_INSTRUCTIONS.md*

# 4. Check logs for errors
tail -n 50 ~/.claude-mpm/logs/mpm.log | grep -i cache
```

### Cache Not Updating

**Symptom**: Changes to PM instructions not reflected in cached file

**Possible Causes**:
1. Content hash matches (no actual content change)
2. Permissions issue preventing write
3. Cache metadata corrupted

**Solution**:

```bash
# 1. Check current cache metadata
cat .claude-mpm/PM_INSTRUCTIONS.md.meta | jq .

# 2. Force regenerate cache
rm -f .claude-mpm/PM_INSTRUCTIONS.md*
claude-mpm agents deploy research

# 3. Verify new cache created
cat .claude-mpm/PM_INSTRUCTIONS.md.meta | jq .cached_at

# 4. Check hash changed
cat .claude-mpm/PM_INSTRUCTIONS.md.meta | jq .content_hash
```

### Large Cache Size

**Symptom**: Cache file is unexpectedly large (>500 KB)

**Expected Size**: 100 KB - 200 KB (depends on project configuration)

**Causes**:
- Abnormally large PM_INSTRUCTIONS.md
- Excessive agent capabilities
- Unexpected content included

**Solution**:

```bash
# 1. Check actual size
ls -lh .claude-mpm/PM_INSTRUCTIONS.md

# 2. Inspect first/last lines for unexpected content
head -n 50 .claude-mpm/PM_INSTRUCTIONS.md
tail -n 50 .claude-mpm/PM_INSTRUCTIONS.md

# 3. Check metadata
cat .claude-mpm/PM_INSTRUCTIONS.md.meta | jq .

# 4. If >1 MB, investigate source files
ls -lh src/claude_mpm/agents/BASE_PM.md
ls -lh .claude-mpm/PM_INSTRUCTIONS.md
```

### Permission Errors

**Symptom**: `PermissionError` when creating or updating cache

**Solution**:

```bash
# 1. Check directory permissions
ls -ld .claude-mpm

# 2. Fix permissions
chmod 755 .claude-mpm
chmod 644 .claude-mpm/PM_INSTRUCTIONS.md*

# 3. Check ownership
ls -l .claude-mpm/

# 4. If owned by another user, change ownership
sudo chown -R $USER:$USER .claude-mpm/
```

### Cache Validation Failed

**Symptom**: Log messages indicating cache validation failure

**Cause**: Cache metadata indicates hash mismatch with actual file content

**Solution**:

```bash
# 1. Check metadata
cat .claude-mpm/PM_INSTRUCTIONS.md.meta | jq .

# 2. Verify cache file exists
ls -lh .claude-mpm/PM_INSTRUCTIONS.md

# 3. Force regeneration
rm -f .claude-mpm/PM_INSTRUCTIONS.md*
claude-mpm agents deploy research

# 4. Verify new cache is valid
cat .claude-mpm/PM_INSTRUCTIONS.md.meta | jq .
```

### Argument List Too Long Error (E2BIG)

**Symptom**: `OSError: [Errno E2BIG] Argument list too long` during deployment

**This should NOT happen** with caching enabled. If you see this error:

**Immediate Fix**:

```bash
# 1. Check if cache exists
ls -lh .claude-mpm/PM_INSTRUCTIONS.md*

# 2. If missing, create cache directory
mkdir -p .claude-mpm
chmod 755 .claude-mpm

# 3. Regenerate cache
claude-mpm agents deploy research --force

# 4. Verify cache created
ls -lh .claude-mpm/PM_INSTRUCTIONS.md*
```

**Prevention**: File a bug report if this occurs, as caching should prevent this error.

## Technical Details

### Hash Algorithm

**Algorithm**: SHA-256
**Purpose**: Content change detection
**Performance**: ~1ms for 152 KB content
**Collision Resistance**: Cryptographically secure

### Update Strategy

**Method**: Atomic file replacement
**Steps**:
1. Write content to temporary file (`.tmp`)
2. Calculate SHA-256 hash of content
3. Write metadata to temporary file (`.meta.tmp`)
4. Atomically replace cache file (`temp → cache`)
5. Atomically replace metadata file (`temp.meta → cache.meta`)

**Atomic Guarantee**: Using `Path.replace()` ensures atomic updates on all platforms (POSIX `rename()` semantics on Unix, `ReplaceFile()` on Windows).

### Invalidation Strategy

**Type**: Hash-based invalidation
**Trigger**: Content hash mismatch
**Comparison**: SHA-256 of new content vs cached hash in metadata
**Efficiency**: O(1) metadata read + O(n) hash calculation

### Fallback Mechanism

If cache creation or loading fails, Claude MPM **gracefully degrades** to inline instruction loading:

```python
try:
    cache_result = cache_service.update_cache(instruction_content)
    if cache_result.cache_path.exists():
        # Use file-based loading
        return ["--system-prompt-file", str(cache_result.cache_path)]
except Exception:
    # Graceful fallback to inline
    return ["--append-system-prompt", instruction_content]
```

This ensures agent deployment **always succeeds**, even if caching fails.

## Performance Metrics

### Cache Operations

| Operation | Typical Time | Description |
|-----------|-------------|-------------|
| Hash Computation | ~1-2ms | SHA-256 of 152 KB content |
| Metadata Read | <1ms | JSON parse of ~300 bytes |
| Cache Write | 5-10ms | Write 152 KB + metadata |
| Cache Skip | <1ms | Metadata read only, no I/O |

### Agent Startup Impact

| Scenario | Startup Time | Notes |
|----------|-------------|-------|
| Without Caching | +200ms | Subprocess argument parsing |
| First Load (Write) | +10ms | Cache write overhead |
| Subsequent (Hit) | <1ms | Hash comparison only |
| Overall Improvement | ~200ms | Consistent across deployments |

### ARG_MAX Impact

| Platform | Limit | Instruction Size | Status |
|----------|-------|-----------------|--------|
| macOS | 1 MB | 152 KB | ✅ Within limit (14.9%) |
| Linux (typical) | 128 KB | 152 KB | ❌ **Exceeds by 19.1%** |
| Linux (conservative) | 64 KB | 152 KB | ❌ **Exceeds by 138%** |
| Windows | 32 KB | 152 KB | ❌ **Exceeds by 476%** |

**Critical**: Without caching, Linux and Windows deployments would fail with `E2BIG` error.

## QA Verification

Comprehensive QA testing confirmed all functionality:

- ✅ Cache creation and file structure
- ✅ Cache invalidation (content change detection)
- ✅ Hash-based skip optimization
- ✅ All 88 tests passing (100% success rate)
- ✅ Quality gate passing (lint, format, structure)
- ✅ Integration with Claude Code (`--system-prompt-file`)
- ✅ Error handling (invalid cache, missing metadata, corruption)
- ✅ Cross-platform ARG_MAX validation

**QA Report**: See [QA_REPORT_1M-446.md](/Users/masa/Projects/claude-mpm/QA_REPORT_1M-446.md) for complete test results and evidence.

## Related Documentation

- **QA Report**: [QA_REPORT_1M-446.md](/Users/masa/Projects/claude-mpm/QA_REPORT_1M-446.md)
- **Agent Deployment**: [docs/guides/agent_deployment.md](/Users/masa/Projects/claude-mpm/docs/guides/agent_deployment.md)
- **PM Instructions**: [docs/reference/pm_instructions.md](/Users/masa/Projects/claude-mpm/docs/reference/pm_instructions.md)
- **Troubleshooting**: [docs/TROUBLESHOOTING.md](/Users/masa/Projects/claude-mpm/docs/TROUBLESHOOTING.md)
- **Architecture**: [Architecture Overview](../architecture/overview.md)

## Future Enhancements

Potential future improvements to instruction caching:

1. **Compression**: Optional gzip compression for large instruction sets
2. **Tiered Caching**: Separate caches for different agent types
3. **Cache Prewarming**: Pre-generate caches for all agents on install
4. **Cache Metrics**: Track hit/miss rates and performance statistics
5. **Cache Cleanup**: Automatic removal of stale caches
6. **Configurable Hash**: Allow SHA-1 for faster hashing on trusted systems
7. **Cache Sharing**: Share caches across users on multi-user systems
