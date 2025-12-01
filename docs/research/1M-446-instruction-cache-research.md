# Research: File-Based Instruction Caching for CLI Command Length Limits

**Ticket**: 1M-446
**Date**: 2025-11-30
**Researcher**: Research Agent
**Status**: Complete

## Executive Summary

**Problem**: Claude MPM fails on Linux systems when passing PM_INSTRUCTIONS.md (93KB) via `--append-system-prompt` CLI argument due to ARG_MAX limits (~131KB typical).

**Root Cause**: Linux kernel limits command-line argument length to 1/4 of stack size (minimum 131,072 bytes). PM_INSTRUCTIONS.md consumes 95,035 bytes, leaving insufficient space for other arguments and environment variables.

**Solution**: Implement file-based instruction loading using Claude Code's `--system-prompt-file` flag with hash-based cache invalidation.

**Impact**:
- ✅ Eliminates ARG_MAX limitations
- ✅ Maintains backward compatibility with macOS
- ✅ Enables future instruction growth without CLI constraints
- ⚠️ Requires Claude Code support for `--system-prompt-file` (available in print mode)

---

## 1. Linux ARG_MAX Limits

### 1.1 Current System Measurement

```bash
# macOS (current development system)
$ getconf ARG_MAX
1048576  # 1MB

# PM_INSTRUCTIONS.md size
$ wc -c src/claude_mpm/agents/PM_INSTRUCTIONS.md
95035

$ ls -lh src/claude_mpm/agents/PM_INSTRUCTIONS.md
-rw-r--r--  1 masa  staff    93K Nov 25 01:13 PM_INSTRUCTIONS.md
```

**Result**: macOS has 1MB limit, so the 93KB file fits comfortably. Linux is the problem.

### 1.2 Linux ARG_MAX Behavior (Kernel 2.6.23+)

**Formula**: `ARG_MAX = stack_size / 4`

**Minimum**: 131,072 bytes (128KB) as defined in `limits.h`

**Effective Limit Calculation**:
```
Available space = ARG_MAX - environment_size - safety_margin
                = 131,072 - env_vars - 2,048 (POSIX recommendation)
                ≈ 120KB - env_vars

PM_INSTRUCTIONS.md = 95KB
Other arguments    = ~10KB (estimated)
Environment vars   = ~10KB (typical)
Total             ≈ 115KB
```

**Verdict**: **On the edge**. Works on some systems, fails on others depending on environment size.

### 1.3 Distribution Comparison

| Distribution | ARG_MAX Behavior | Notes |
|-------------|------------------|-------|
| Ubuntu 20.04+ | `stack_size / 4` | Kernel 5.x, typically 128KB min |
| Debian 11+ | `stack_size / 4` | Kernel 5.x, typically 128KB min |
| RHEL 8+ | `stack_size / 4` | Kernel 4.18+, typically 128KB min |
| Alpine 3.x | `stack_size / 4` | Kernel 5.x, typically 128KB min |

**Key Insight**: Distribution doesn't matter - it's kernel-driven. All modern Linux distributions (kernel 2.6.23+) use the same formula.

### 1.4 Additional Linux Constraints

- **MAX_ARG_STRLEN**: 131,072 bytes per single argument (since kernel 2.6.23)
- **MAX_ARG_STRINGS**: 4,294,967,295 total arguments (2^32 - 1)

**Implication**: Even if we pass PM_INSTRUCTIONS.md as a single argument, it cannot exceed 128KB.

---

## 2. Current Implementation Analysis

### 2.1 Instruction Passing Mechanism

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/interactive_session.py`

**Lines 399-404**:
```python
# Add system instructions
from claude_mpm.core.claude_runner import create_simple_context

system_prompt = self.runner._create_system_prompt()
if system_prompt and system_prompt != create_simple_context():
    cmd.extend(["--append-system-prompt", system_prompt])
```

**Current Flow**:
1. `claude_runner.py` calls `_create_system_prompt()`
2. Delegates to `SystemInstructionsService.create_system_prompt()`
3. Loads PM_INSTRUCTIONS.md content into memory
4. Passes entire content as string via `--append-system-prompt`
5. Claude CLI receives 93KB string as inline argument

**Bottleneck**: Step 4 - inline string argument hits ARG_MAX limit on Linux.

### 2.2 Instruction Loading Chain

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/framework/loaders/instruction_loader.py`

**Lines 98-113** (PM_INSTRUCTIONS.md loading):
```python
pm_instructions_path = (
    self.framework_path / "src" / "claude_mpm" / "agents" / "PM_INSTRUCTIONS.md"
)

if pm_instructions_path.exists():
    loaded_content = self.file_loader.try_load_file(
        pm_instructions_path, "consolidated PM_INSTRUCTIONS.md"
    )
    if loaded_content:
        content["framework_instructions"] = loaded_content
```

**Key Insight**: Instructions are already loaded from file system - we're just passing them the wrong way (inline vs. file path).

---

## 3. Claude Code File Loading Capabilities

### 3.1 Available CLI Flags

**Source**: [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference)

| Flag | Purpose | Modes | File Support | Notes |
|------|---------|-------|--------------|-------|
| `--system-prompt` | Complete replacement | Interactive, Print | No | Inline string only |
| `--system-prompt-file` | Load from file | **Print mode only** | **Yes** | **This is what we need** |
| `--append-system-prompt` | Add to defaults | Interactive, Print | No | Current implementation |

### 3.2 Critical Discovery: Mode Limitation

⚠️ **CRITICAL**: `--system-prompt-file` is **print mode only**, not interactive mode.

**Implication**: We need to verify if Claude MPM runs in print mode or interactive mode.

**Action Required**:
1. Check if `interactive_session.py` uses print mode or interactive mode
2. If interactive mode: We may need to use `--system-prompt-file` in print mode or find alternative
3. Consider hybrid approach: Use file in print mode, inline in interactive if under limit

### 3.3 Usage Examples

**File-Based (Print Mode)**:
```bash
claude -p --system-prompt-file ./PM_INSTRUCTIONS.md "What is the architecture?"
```

**Current Inline Approach**:
```bash
claude --append-system-prompt "<93KB of text>" "What is the architecture?"
```

**File Path Requirements**:
- Accepts local file paths
- No special format required (plain text/markdown)
- Relative or absolute paths supported

---

## 4. Recommended Cache Invalidation Approach

### 4.1 Hash-Based Detection (RECOMMENDED)

**Algorithm**: SHA-256 hash comparison

**Rationale**:
- ✅ Accurate: Detects all content changes, even 1-byte modifications
- ✅ Reliable: Works across all file systems (no mtime issues)
- ✅ Fast: SHA-256 hashing is O(n) but highly optimized
- ✅ Portable: Python's hashlib is built-in and cross-platform

**Implementation Pseudocode**:
```python
import hashlib
from pathlib import Path

def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of file contents."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        # Read in chunks for memory efficiency
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def needs_cache_update(source_file: Path, cache_file: Path, hash_file: Path) -> bool:
    """Check if cache needs updating based on source file hash."""
    if not cache_file.exists():
        return True  # Cache doesn't exist

    if not hash_file.exists():
        return True  # Hash record missing

    # Read stored hash
    stored_hash = hash_file.read_text().strip()

    # Calculate current hash
    current_hash = calculate_file_hash(source_file)

    return stored_hash != current_hash

def update_cache(source_file: Path, cache_file: Path, hash_file: Path):
    """Update cache file and hash record."""
    # Copy source to cache
    cache_file.write_text(source_file.read_text())

    # Store new hash
    current_hash = calculate_file_hash(source_file)
    hash_file.write_text(current_hash)
```

**Performance**:
- 93KB file: ~0.1ms hash calculation time (negligible)
- Trade-off: Minimal CPU cost for 100% accuracy

### 4.2 Alternative: File Modification Time (NOT RECOMMENDED)

**Algorithm**: Compare `os.path.getmtime()`

**Problems**:
- ❌ Unreliable: `mtime` can be incorrect after `git checkout`, `rsync`, or deployments
- ❌ False positives: File touched without content change triggers rebuild
- ❌ False negatives: Content changed but `mtime` not updated (rare but possible)

**Verdict**: Avoid. Hash-based is more reliable.

### 4.3 Hybrid Approach (OVERKILL)

**Algorithm**: Check `mtime` first, then hash if needed

**Rationale**: Optimize for common case where file hasn't changed

**Reality**: Hash calculation is already so fast (~0.1ms) that optimization is unnecessary complexity.

---

## 5. Recommended Cache Storage Location

### 5.1 Option A: `.claude-mpm/cache/PM_INSTRUCTIONS.md` (RECOMMENDED)

**Structure**:
```
.claude-mpm/
├── agents/
├── cache/
│   ├── PM_INSTRUCTIONS.md      # Cached instructions
│   └── PM_INSTRUCTIONS.md.sha256  # Hash for validation
```

**Advantages**:
- ✅ Clear separation: `/cache/` explicitly indicates purpose
- ✅ Scalable: Can cache other files in future (WORKFLOW.md, MEMORY.md)
- ✅ Gitignore-friendly: `.claude-mpm/cache/` is obvious exclusion
- ✅ Clean isolation: Original sources in `/agents/`, cache in `/cache/`

**Disadvantages**:
- ⚠️ Extra directory depth

**Gitignore**:
```gitignore
.claude-mpm/cache/
```

### 5.2 Option B: `.claude-mpm/PM_INSTRUCTIONS.md` (SIMPLER)

**Structure**:
```
.claude-mpm/
├── agents/
├── PM_INSTRUCTIONS.md          # Cached instructions
└── PM_INSTRUCTIONS.md.sha256   # Hash for validation
```

**Advantages**:
- ✅ Simpler: Flat structure, fewer directories
- ✅ Direct access: Cache at predictable location

**Disadvantages**:
- ❌ Namespace collision: Mix of source templates and cache files
- ❌ Less scalable: As we add more cached files, root gets cluttered

### 5.3 Option C: `~/.cache/claude-mpm/PM_INSTRUCTIONS.md` (NOT RECOMMENDED)

**Structure**:
```
~/.cache/claude-mpm/
└── PM_INSTRUCTIONS.md
```

**Advantages**:
- ✅ XDG Base Directory compliance
- ✅ User-level isolation

**Disadvantages**:
- ❌ Project-local intent lost: Instructions should be project-specific
- ❌ Multi-project conflicts: Different projects might need different instruction versions
- ❌ Cleanup complexity: User has to remember to clean `~/.cache/`

**Verdict**: Avoid. Instructions should be project-local.

### 5.4 Final Recommendation

**Option A: `.claude-mpm/cache/`**

**Rationale**:
- Clear semantic separation
- Future-proof for caching WORKFLOW.md, MEMORY.md, agent templates
- Easy to document and explain
- Obvious gitignore pattern

---

## 6. Backward Compatibility Strategy

### 6.1 Platform Detection Approach (NOT RECOMMENDED)

**Algorithm**: `if platform.system() == "Linux": use file, else: use inline`

**Problems**:
- ❌ macOS could also hit limits with large environments
- ❌ False dichotomy: Problem is ARG_MAX, not platform
- ❌ Hard to test: Requires Linux VM for every change

### 6.2 Feature Detection Approach (RECOMMENDED)

**Algorithm**:
1. Check if `--system-prompt-file` is supported by Claude CLI
2. Prefer file-based approach if available
3. Fall back to inline if flag not recognized

**Implementation**:
```python
def supports_system_prompt_file() -> bool:
    """Check if Claude CLI supports --system-prompt-file flag."""
    try:
        result = subprocess.run(
            ["claude", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return "--system-prompt-file" in result.stdout
    except Exception:
        return False

def build_instruction_args(cache_file: Path, inline_content: str) -> list:
    """Build instruction arguments with fallback."""
    if supports_system_prompt_file() and cache_file.exists():
        # Prefer file-based approach
        return ["--system-prompt-file", str(cache_file)]
    else:
        # Fallback to inline
        return ["--append-system-prompt", inline_content]
```

**Advantages**:
- ✅ Robust: Works regardless of platform
- ✅ Future-proof: Automatically uses new features when available
- ✅ Testable: Can mock `claude --help` output

### 6.3 Hybrid Approach: Size-Based Switching

**Algorithm**:
1. Calculate total argument size
2. If under threshold (e.g., 64KB): Use inline
3. If over threshold: Use file

**Rationale**: Avoid file I/O for small instructions

**Reality**: File I/O is negligible (~1ms), and cache needs updating anyway. Adds complexity for minimal gain.

**Verdict**: Feature detection is cleaner.

### 6.4 Migration Path for Existing Users

**Scenario**: User upgrades Claude MPM from 4.26.x to 4.27.0

**Expected Behavior**:
1. First run after upgrade: Cache doesn't exist
2. Claude MPM detects missing cache
3. Creates `.claude-mpm/cache/` directory
4. Copies PM_INSTRUCTIONS.md to cache
5. Calculates and stores hash
6. Uses file-based approach if supported
7. Falls back to inline if Claude CLI doesn't support file flag

**User Impact**: Transparent. No action required.

**Breaking Changes**: None. Graceful degradation ensures compatibility.

---

## 7. Error Handling Scenarios

### 7.1 Scenario: Cache File Deleted Manually

**Trigger**: User runs `rm -rf .claude-mpm/cache/`

**Detection**: `cache_file.exists()` returns `False`

**Recovery**:
1. Log warning: "Cache missing, regenerating from source"
2. Recreate cache from source PM_INSTRUCTIONS.md
3. Continue normal operation

**Impact**: Single-run performance hit (~1ms), then back to normal

**Code**:
```python
if not cache_file.exists():
    logger.warning("Instruction cache missing, regenerating")
    update_cache(source_file, cache_file, hash_file)
```

### 7.2 Scenario: Cache File Corrupted

**Trigger**: Cache file modified externally, hash mismatch

**Detection**: `calculate_file_hash(cache_file) != stored_hash`

**Recovery**:
1. Log error: "Cache corruption detected, rebuilding"
2. Delete corrupted cache
3. Regenerate from source
4. Update hash

**Impact**: Single-run rebuild, then normal

**Code**:
```python
cache_hash = calculate_file_hash(cache_file)
if cache_hash != stored_hash:
    logger.error("Cache corruption detected, rebuilding")
    cache_file.unlink()
    update_cache(source_file, cache_file, hash_file)
```

### 7.3 Scenario: Source File Not Readable

**Trigger**: Permission denied on PM_INSTRUCTIONS.md

**Detection**: `PermissionError` during `source_file.read_text()`

**Recovery**:
1. Log error: "Cannot read PM_INSTRUCTIONS.md: permission denied"
2. Check if cache exists and is valid
3. If cache valid: Use cached version (stale but functional)
4. If cache invalid: Fail gracefully with clear error message

**Impact**: User sees actionable error message

**Code**:
```python
try:
    source_content = source_file.read_text()
except PermissionError:
    logger.error(f"Cannot read {source_file}: permission denied")
    if cache_file.exists() and is_cache_valid(cache_file, hash_file):
        logger.warning("Using stale cache due to source read error")
        return cache_file
    else:
        raise AgentDeploymentError(
            f"Cannot read PM_INSTRUCTIONS.md and cache is unavailable. "
            f"Check permissions: {source_file}"
        )
```

### 7.4 Scenario: Cache Directory Creation Fails

**Trigger**: No write permission on `.claude-mpm/`

**Detection**: `PermissionError` during `cache_dir.mkdir()`

**Recovery**:
1. Log error: "Cannot create cache directory: permission denied"
2. Fall back to inline approach
3. Warn user about potential ARG_MAX issues on Linux

**Impact**: Inline approach works on macOS, may fail on Linux

**Code**:
```python
try:
    cache_dir.mkdir(parents=True, exist_ok=True)
except PermissionError:
    logger.error("Cannot create cache directory, falling back to inline")
    return ["--append-system-prompt", inline_content]
```

### 7.5 Scenario: Claude Code Doesn't Support `--system-prompt-file`

**Trigger**: Old Claude CLI version

**Detection**: `--system-prompt-file` not in `claude --help` output

**Recovery**:
1. Log info: "Claude CLI doesn't support file-based instructions, using inline"
2. Fall back to inline approach
3. Continue normal operation

**Impact**: Works as before, no breaking change

**Code**:
```python
if not supports_system_prompt_file():
    logger.info("Claude CLI doesn't support --system-prompt-file, using inline")
    return ["--append-system-prompt", inline_content]
```

### 7.6 Scenario: Hash File Corrupted

**Trigger**: `.sha256` file contains invalid data

**Detection**: Hash string length != 64 characters

**Recovery**:
1. Log warning: "Invalid hash record, regenerating cache"
2. Recalculate hash from source
3. Update cache and hash

**Impact**: Single-run rebuild

**Code**:
```python
try:
    stored_hash = hash_file.read_text().strip()
    if len(stored_hash) != 64:
        raise ValueError("Invalid hash length")
except (ValueError, FileNotFoundError):
    logger.warning("Invalid hash record, regenerating")
    update_cache(source_file, cache_file, hash_file)
```

---

## 8. Implementation Complexity Estimate

### 8.1 Code Changes Required

**Files to Modify**:
1. `/src/claude_mpm/core/interactive_session.py` - Update CLI arg construction
2. `/src/claude_mpm/core/oneshot_session.py` - Update CLI arg construction
3. Create new `/src/claude_mpm/services/instruction_cache_service.py`
4. `/src/claude_mpm/core/framework/loaders/instruction_loader.py` - Integrate cache

**Estimated Lines of Code**:
- New cache service: ~200 lines (hash calc, cache update, validation)
- Integration: ~50 lines (call cache service, build args)
- Tests: ~300 lines (unit tests, integration tests)
- **Total**: ~550 lines

### 8.2 Testing Requirements

**Unit Tests**:
- Hash calculation accuracy
- Cache update logic
- Cache validation
- Error handling (permissions, corruption, missing files)

**Integration Tests**:
- End-to-end: Source change → cache update → Claude CLI invocation
- Platform tests: macOS and Linux
- Fallback tests: Old Claude CLI without `--system-prompt-file`

**Manual Testing**:
- ARG_MAX limit verification on Linux VM
- Performance benchmarking (cache hit vs. miss)

**Estimated Effort**: 3-4 hours development + 2 hours testing = **1 day**

### 8.3 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `--system-prompt-file` print mode only | Medium | High | Investigate interactive mode support, use `--system-prompt` as alternative |
| Cache corruption undetected | Low | Medium | Hash validation prevents this |
| Performance regression | Very Low | Low | Hash calculation is <1ms |
| Breaking change for users | Very Low | High | Graceful fallback ensures compatibility |

---

## 9. Alternative Approaches Considered

### 9.1 Compression-Based Approach

**Idea**: Gzip compress PM_INSTRUCTIONS.md before passing inline

**Analysis**:
- Compression ratio: ~60% (93KB → 37KB)
- Still counts against ARG_MAX (base64-encoded compressed data)
- Adds complexity: Compress → Base64 → Pass → Decode → Decompress
- Claude CLI doesn't support compressed inputs

**Verdict**: Not viable. Claude CLI expects plain text.

### 9.2 Environment Variable Approach

**Idea**: Pass instructions via `CLAUDE_SYSTEM_PROMPT` environment variable

**Analysis**:
- Environment variables also count against ARG_MAX
- Same 128KB limit applies
- Less explicit than CLI arguments
- Not supported by Claude CLI

**Verdict**: Not viable. No benefit over inline arguments.

### 9.3 Split Instructions Approach

**Idea**: Split PM_INSTRUCTIONS.md into chunks, pass multiple `--append-system-prompt` flags

**Analysis**:
- Complex: Need to split at logical boundaries
- Fragile: Order matters, semantic coherence required
- Still counts against ARG_MAX (sum of all chunks)
- Doesn't solve the root problem

**Verdict**: Not viable. Adds complexity without solving ARG_MAX issue.

### 9.4 Instruction Server Approach

**Idea**: Run HTTP server to serve instructions, Claude fetches via URL

**Analysis**:
- Massive overkill: Requires server, port management, lifecycle
- Security concerns: Exposing instructions over network
- Latency: Network round-trip adds delay
- Claude CLI doesn't support URL-based system prompts

**Verdict**: Not viable. Complexity far outweighs benefit.

---

## 10. Final Recommendations

### 10.1 Primary Recommendation

**Implement file-based instruction caching with the following design**:

1. **Cache Location**: `.claude-mpm/cache/PM_INSTRUCTIONS.md`
2. **Invalidation**: SHA-256 hash comparison
3. **CLI Flag**: `--system-prompt-file` (with fallback to `--append-system-prompt`)
4. **Error Handling**: Graceful degradation at each failure point
5. **Compatibility**: Feature detection, not platform detection

### 10.2 Implementation Steps

**Phase 1: Core Infrastructure** (2 hours)
1. Create `InstructionCacheService` class
2. Implement hash-based cache validation
3. Add cache directory management

**Phase 2: Integration** (2 hours)
1. Update `interactive_session.py` to use cache
2. Update `oneshot_session.py` to use cache
3. Add feature detection for `--system-prompt-file`

**Phase 3: Testing** (2 hours)
1. Write unit tests for cache service
2. Write integration tests
3. Manual Linux VM testing

**Phase 4: Documentation** (1 hour)
1. Update CONTRIBUTING.md
2. Add cache documentation to README
3. Document gitignore patterns

**Total Effort**: 7 hours (~1 day)

### 10.3 Success Criteria

- [ ] Claude MPM works on Linux systems with ARG_MAX ~128KB
- [ ] No breaking changes for macOS users
- [ ] Cache invalidation works correctly (detects all changes)
- [ ] Graceful fallback if file-based approach unavailable
- [ ] All error scenarios handled with clear messages
- [ ] Performance impact < 5ms per invocation
- [ ] Tests achieve 90%+ coverage on new code

### 10.4 Open Questions for Implementation

1. **Interactive Mode Support**: Does Claude CLI support `--system-prompt-file` in interactive mode?
   - **Action**: Test with Claude CLI: `claude --system-prompt-file test.md`
   - **Fallback**: Use `--system-prompt` with file contents if interactive mode doesn't support file flag

2. **Instruction Growth**: What's the maximum acceptable size for PM_INSTRUCTIONS.md?
   - **Current**: 93KB
   - **Recommendation**: Aim to keep under 50KB by refactoring to separate files (WORKFLOW.md, MEMORY.md)

3. **Multi-File Caching**: Should we cache WORKFLOW.md and MEMORY.md too?
   - **Recommendation**: Yes, same hash-based approach for all instruction files

---

## 11. Code References

### 11.1 Current Instruction Passing

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/interactive_session.py`
**Line**: 404
**Code**:
```python
cmd.extend(["--append-system-prompt", system_prompt])
```

### 11.2 Instruction Loading

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/framework/loaders/instruction_loader.py`
**Lines**: 98-113

### 11.3 Hash Calculation Example

```python
import hashlib
from pathlib import Path

def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of file contents.

    Args:
        file_path: Path to file to hash

    Returns:
        Hex-encoded SHA-256 hash (64 characters)

    Performance:
        - 93KB file: ~0.1ms on modern hardware
        - Memory efficient: Streams in 8KB chunks
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()
```

---

## 12. Appendix: Testing Checklist

### 12.1 Unit Tests

- [ ] `test_calculate_file_hash()` - Verify hash calculation
- [ ] `test_cache_needs_update_missing_cache()` - Cache doesn't exist
- [ ] `test_cache_needs_update_hash_mismatch()` - Source changed
- [ ] `test_cache_needs_update_no_update_needed()` - Cache valid
- [ ] `test_update_cache_creates_directory()` - Auto-create cache dir
- [ ] `test_update_cache_updates_hash()` - Hash stored correctly
- [ ] `test_supports_system_prompt_file_available()` - Feature detection
- [ ] `test_supports_system_prompt_file_unavailable()` - Fallback

### 12.2 Integration Tests

- [ ] `test_end_to_end_cache_creation()` - First run creates cache
- [ ] `test_end_to_end_cache_reuse()` - Second run uses cache
- [ ] `test_end_to_end_cache_invalidation()` - Source change triggers rebuild
- [ ] `test_end_to_end_fallback_inline()` - Works without file support
- [ ] `test_permission_error_handling()` - Graceful error on permission denied
- [ ] `test_corrupted_cache_recovery()` - Rebuilds on corruption

### 12.3 Manual Tests

- [ ] Linux VM: Verify ARG_MAX limit bypassed
- [ ] Linux VM: Test with small ARG_MAX (custom kernel)
- [ ] macOS: Verify backward compatibility
- [ ] Performance: Benchmark cache hit vs. miss time
- [ ] Stress: 1000 runs, verify no cache corruption

---

## 13. References

1. **Linux ARG_MAX Documentation**: https://www.in-ulm.de/~mascheck/various/argmax/
2. **Claude Code CLI Reference**: https://code.claude.com/docs/en/cli-reference
3. **POSIX ARG_MAX Standard**: https://pubs.opengroup.org/onlinepubs/9699919799/functions/sysconf.html
4. **Ticket 1M-446**: File-based instruction caching implementation

---

## 14. Document Metadata

**Created**: 2025-11-30
**Last Updated**: 2025-11-30
**Version**: 1.0
**Status**: Complete - Ready for Implementation
**Next Steps**: Create implementation ticket and assign to backend engineer
