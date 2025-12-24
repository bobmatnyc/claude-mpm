# PM Instructions Loading System - Root Cause Analysis

## Executive Summary

**Incident**: PM instructions were silently loading stale content (v0006) instead of current source (v0007), causing PM behavioral regression.

**Root Cause**: Stale `PM_INSTRUCTIONS_DEPLOYED.md` file bypassing source file updates due to deployment cache invalidation failure.

**Impact**: Silent failure - no errors raised, PM received incorrect instructions for entire session.

**Severity**: P0 - Core functionality broke silently without detection.

---

## System Architecture

### Instruction Assembly Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    STARTUP SEQUENCE                         │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────┐
    │  ClaudeRunner.__init__()                     │
    │  Location: src/claude_mpm/core/claude_runner.py:187-191
    └──────────────────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────┐
    │  SystemInstructionsService.load_system_instructions()
    │  Location: src/claude_mpm/services/system_instructions_service.py:41-93
    └──────────────────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────┐
    │  FrameworkLoader.get_framework_instructions() │
    │  Location: src/claude_mpm/core/framework_loader.py:318-331
    └──────────────────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────┐
    │  InstructionLoader._load_filesystem_framework_instructions()
    │  Location: src/claude_mpm/core/framework/loaders/instruction_loader.py:90-143
    │                                              │
    │  PRIORITY 1: PM_INSTRUCTIONS_DEPLOYED.md ✅  │
    │  PRIORITY 2: PM_INSTRUCTIONS.md (source)  ❌ NEVER REACHED
    │  PRIORITY 3: INSTRUCTIONS.md (legacy)     ❌ NEVER REACHED
    └──────────────────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────┐
    │  ContentFormatter.format_full_framework()    │
    │  Assembles: BASE_PM + PM_INSTRUCTIONS +      │
    │             WORKFLOW + capabilities + context│
    └──────────────────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────┐
    │  InteractiveSession._build_command()         │
    │  Location: src/claude_mpm/core/interactive_session.py:419-480
    └──────────────────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────┐
    │  InstructionCacheService.update_cache()      │
    │  Location: src/claude_mpm/services/instructions/instruction_cache_service.py:89-166
    │                                              │
    │  Writes to: .claude-mpm/PM_INSTRUCTIONS.md  │
    │  Cache validation: SHA-256 hash             │
    └──────────────────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────┐
    │  Claude Code Launch                          │
    │  Uses: --system-prompt-file PM_INSTRUCTIONS.md
    └──────────────────────────────────────────────┘
```

### Three Critical Files

| File | Purpose | Update Mechanism | Current State |
|------|---------|------------------|---------------|
| **Source**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md` | Single source of truth | Git commits | ✅ v0007 (Dec 22 23:59) |
| **Deployed**: `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md` | Merged PM+WORKFLOW+MEMORY | `SystemInstructionsDeployer` | ❌ v0006 (Dec 22 16:39) STALE |
| **Cache**: `.claude-mpm/PM_INSTRUCTIONS.md` | Full assembled instructions | `InstructionCacheService` | ⚠️  v0006 (Dec 23 19:05) FROM STALE DEPLOYED |

---

## Root Cause Analysis

### The Failure Chain

1. **Source Updated** (Dec 22 23:59)
   - Commit `40e5dd60`: "refactor(pm): consolidate instructions + fix deepeval tests"
   - Source file updated to v0007
   - File mtime: `2025-12-22 23:59:23`

2. **Deployment Skipped** (Timestamp-based cache invalidation failure)
   ```python
   # system_instructions_deployer.py:82-89
   if (
       not force_rebuild
       and target_file.exists()
       and target_file.stat().st_mtime >= latest_mtime  # BUG: This check failed
   ):
       results["skipped"].append("PM_INSTRUCTIONS_DEPLOYED.md")
       self.logger.debug("PM_INSTRUCTIONS_DEPLOYED.md up to date")
   ```
   - Deployed file mtime: `2025-12-22 16:39:42` (OLDER than source!)
   - Check: `16:39:42 >= 23:59:23` → **FALSE**
   - Expected: Should have redeployed
   - **Actual**: Deployment was SKIPPED (never triggered after git commit)

3. **Stale Content Loaded** (Priority system design flaw)
   ```python
   # instruction_loader.py:94-112
   # PRIORITY 1: Deployed file (FOUND - stale v0006)
   deployed_path = self.current_dir / ".claude-mpm" / "PM_INSTRUCTIONS_DEPLOYED.md"
   if deployed_path.exists():
       loaded_content = self.file_loader.try_load_file(deployed_path, ...)
       if loaded_content:
           content["framework_instructions"] = loaded_content
           return  # ⚠️ EARLY RETURN - Source file never checked

   # PRIORITY 2: Source file (v0007) - NEVER REACHED ❌
   # PRIORITY 3: Legacy file - NEVER REACHED ❌
   ```

4. **Cache Updated With Stale Content** (Dec 23 19:05)
   ```python
   # interactive_session.py:438-439
   cache_result = cache_service.update_cache(
       instruction_content=system_prompt  # Contains v0006 from stale deployed file
   )
   ```
   - Cache hash: `f8429cfbd8a7a49f92b1204a93fbc461e1155425b10b34a1b5867558466a85f5`
   - Cache size: 118,725 bytes (assembled with v0006 PM_INSTRUCTIONS)

5. **Claude Code Receives Wrong Instructions**
   - Reads: `.claude-mpm/PM_INSTRUCTIONS.md` (cached v0006)
   - Expected: v0007 with delegation principles
   - Actual: v0006 with "ABSOLUTE PM LAW" rhetoric

---

## Cache Write Points Analysis

### Single Cache Writer (Good)

**Location**: `src/claude_mpm/core/interactive_session.py:438-439`

```python
cache_service = InstructionCacheService(project_root=project_root)
cache_result = cache_service.update_cache(instruction_content=system_prompt)
```

**Verdict**: ✅ **NO RACE CONDITIONS**
- Only ONE code path writes the cache
- Sequential execution (no parallel writes)
- Hash-based validation prevents partial writes

### Cache Invalidation Strategy

**Current**: SHA-256 hash comparison
```python
# instruction_cache_service.py:131-139
content_hash = self._calculate_hash_from_content(instruction_content)
if not force and self.is_cache_valid(instruction_content):
    return {"updated": False, "reason": "cache_valid"}
```

**Problem**: Hash-based validation is **correct**, but it's fed **stale content** from upstream.

---

## Deployment Cache Analysis

### Deployment Writer

**Location**: `src/claude_mpm/services/agents/deployment/system_instructions_deployer.py:78-95`

```python
# Check if update needed
if (
    not force_rebuild
    and target_file.exists()
    and target_file.stat().st_mtime >= latest_mtime
):
    results["skipped"].append("PM_INSTRUCTIONS_DEPLOYED.md")
    self.logger.debug("PM_INSTRUCTIONS_DEPLOYED.md up to date")
else:
    target_file.write_text("\n\n".join(merged_content))
```

**Timestamp-based Validation Issues**:

1. **File System Granularity**
   - Filesystem timestamps have ~1 second granularity
   - Rapid successive writes within same second may not update mtime
   - Not deterministic across filesystems (ext4, APFS, NTFS differ)

2. **No Content Validation**
   - Only checks mtime, not actual content
   - If deployment somehow gets newer timestamp with old content, check passes
   - No checksum or version validation

3. **No Deployment Trigger After Git Operations**
   - Git checkout/pull updates source file mtime
   - Deployment service not automatically invoked after git operations
   - Manual deployment required: `claude-mpm agents deploy PM`

---

## Why "System instructions" Placeholder Never Appeared

**Mystery Solved**: The string "System instructions" exists in:

1. **Fallback Messages** (never executed):
   ```python
   # system_instructions_service.py:85-86, 91-92
   "# System Instructions\n\nNo specific system instructions found."
   "# System Instructions\n\nError loading system instructions."
   ```

2. **Comments/Documentation**:
   - `claude_runner.py:648`: "Create the complete system prompt including instructions"
   - `cli/startup.py`: "NOTE: System instructions (PM_INSTRUCTIONS.md, ...)"

**Why it wasn't used**: The deployed file DID exist (stale v0006), so the system successfully loaded content - it was just the WRONG content.

**The real corruption**: Not a placeholder, but **outdated real content** passing all validation checks.

---

## Failure Mode Analysis

### Silent Failure Characteristics

| Component | Failure Mode | Detection | Impact |
|-----------|-------------|-----------|---------|
| **InstructionLoader** | Returns stale content | None | Loads v0006 instead of v0007 |
| **InstructionCacheService** | Caches stale content | SHA-256 matches stale input | Perpetuates staleness |
| **SystemInstructionsDeployer** | Skips deployment | None (timestamp check passes incorrectly) | Deployed file never updates |
| **FrameworkLoader** | Trusts deployed file | None | No version validation |
| **ClaudeRunner** | Receives wrong instructions | None | PM gets incorrect behavior rules |

**CRITICAL**: **ZERO ERROR MESSAGES** - System operated "successfully" with corrupted state.

---

## Recommended Safeguards

### 1. Content-Hash Validation for Deployed File

**Problem**: Timestamp-based validation failed to detect staleness.

**Solution**: Add content hash validation to deployment check:

```python
# system_instructions_deployer.py:81-89 (ENHANCED)
def _calculate_content_hash(self, content: str) -> str:
    import hashlib
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def _should_redeploy(
    self, target_file: Path, merged_content: str, latest_mtime: float
) -> bool:
    """Check if deployment needed using both timestamp AND content hash."""
    if not target_file.exists():
        return True  # Deploy if doesn't exist

    # Timestamp check (fast path)
    if target_file.stat().st_mtime < latest_mtime:
        return True  # Deploy if source is newer

    # Content hash check (verification)
    current_content = target_file.read_text()
    current_hash = self._calculate_content_hash(current_content)
    new_hash = self._calculate_content_hash(merged_content)

    if current_hash != new_hash:
        self.logger.warning(
            f"Deployed file timestamp suggests up-to-date, but content hash differs. "
            f"Redeploying. (mtime: {target_file.stat().st_mtime} vs {latest_mtime})"
        )
        return True

    return False  # Skip deployment (truly up-to-date)
```

**Benefits**:
- Catches timestamp anomalies
- Deterministic content validation
- Self-healing on staleness detection

### 2. Version Header Validation

**Problem**: No validation that loaded version matches expected version.

**Solution**: Extract and validate version headers:

```python
# instruction_loader.py:104-112 (ENHANCED)
def _validate_instruction_version(self, content: str, file_path: Path) -> bool:
    """Validate instruction version against expected version."""
    import re

    # Extract version from content
    version_match = re.search(r'<!-- PM_INSTRUCTIONS_VERSION: (\d+) -->', content)
    if not version_match:
        self.logger.warning(f"No version header found in {file_path}")
        return False

    loaded_version = int(version_match.group(1))

    # Get expected version from source file
    source_path = self.framework_path / "src" / "claude_mpm" / "agents" / "PM_INSTRUCTIONS.md"
    if source_path.exists():
        source_content = source_path.read_text()
        source_match = re.search(r'<!-- PM_INSTRUCTIONS_VERSION: (\d+) -->', source_content)
        if source_match:
            expected_version = int(source_match.group(1))

            if loaded_version < expected_version:
                self.logger.error(
                    f"Deployed file version {loaded_version} is OLDER than source version {expected_version}. "
                    f"Deployed file: {file_path}. Falling back to source file."
                )
                return False

    return True

# Updated load logic with version validation:
if deployed_path.exists():
    loaded_content = self.file_loader.try_load_file(deployed_path, ...)
    if loaded_content:
        if self._validate_instruction_version(loaded_content, deployed_path):
            content["framework_instructions"] = loaded_content
            return  # Only return if version is valid
        else:
            self.logger.warning("Deployed file failed version validation, using source")
            # Fall through to source file loading
```

**Benefits**:
- Catches version mismatches automatically
- Forces re-deployment on version regression
- Provides clear error messages for diagnosis

### 3. Startup Instruction Validation Check

**Problem**: No verification that loaded instructions are correct before session starts.

**Solution**: Add validation check in ClaudeRunner initialization:

```python
# claude_runner.py:185-191 (ENHANCED)
def _validate_loaded_instructions(self) -> bool:
    """Validate that loaded instructions match expected version and content."""
    if not self.system_instructions:
        self.logger.error("No system instructions loaded")
        return False

    # Extract version from loaded instructions
    import re
    version_match = re.search(
        r'<!-- PM_INSTRUCTIONS_VERSION: (\d+) -->',
        self.system_instructions
    )

    if not version_match:
        self.logger.warning("Loaded instructions missing version header")
        return True  # Continue but warn

    loaded_version = int(version_match.group(1))

    # Get expected version from source
    from claude_mpm.config.paths import paths
    source_path = paths.agents_dir / "PM_INSTRUCTIONS.md"

    if source_path.exists():
        source_content = source_path.read_text()
        source_match = re.search(r'<!-- PM_INSTRUCTIONS_VERSION: (\d+) -->', source_content)

        if source_match:
            expected_version = int(source_match.group(1))

            if loaded_version < expected_version:
                self.logger.error(
                    f"❌ CRITICAL: Loaded instructions version {loaded_version} < expected {expected_version}. "
                    f"Run 'claude-mpm agents deploy PM --force-rebuild' to fix."
                )
                print(
                    f"\n⚠️  WARNING: PM instructions are STALE (v{loaded_version}, expected v{expected_version})\n"
                    f"    Run: claude-mpm agents deploy PM --force-rebuild\n"
                )
                # Continue anyway for now, but flag the issue
                return False

            self.logger.info(f"✓ Instructions validated: v{loaded_version} (latest)")

    return True

# Add validation call after loading
if self.system_instructions_service:
    self.system_instructions = self.system_instructions_service.load_system_instructions()
    if not self._validate_loaded_instructions():
        self.logger.warning("Loaded instructions may be stale")
```

**Benefits**:
- User-visible warning on startup
- Provides fix command
- Logs error for diagnostics
- Non-blocking (allows session to continue)

### 4. Post-Deployment Verification

**Problem**: Deployment completes without verifying correct content was written.

**Solution**: Add verification step after deployment:

```python
# system_instructions_deployer.py:94-109 (ENHANCED)
# Write merged content
target_file.write_text("\n\n".join(merged_content))

# VERIFY deployment succeeded
written_content = target_file.read_text()
expected_hash = self._calculate_content_hash("\n\n".join(merged_content))
actual_hash = self._calculate_content_hash(written_content)

if expected_hash != actual_hash:
    error_msg = (
        f"Deployment verification FAILED: Content hash mismatch. "
        f"Expected: {expected_hash[:8]}..., Actual: {actual_hash[:8]}..."
    )
    self.logger.error(error_msg)
    results["errors"].append(error_msg)
    # Remove corrupted file to force re-deployment next time
    target_file.unlink()
    return
else:
    self.logger.debug(f"Deployment verified: {expected_hash[:8]}...")

# Track deployment (only if verification passed)
deployment_info = {
    "name": "PM_INSTRUCTIONS_DEPLOYED.md",
    "template": ", ".join(source_files),
    "target": str(target_file),
    "content_hash": expected_hash[:16],  # Include hash in tracking
}
```

**Benefits**:
- Catches write failures immediately
- Prevents corrupted deployments from persisting
- Self-healing (removes bad file)

### 5. Automatic Deployment Trigger on Source Changes

**Problem**: Source file updated via git, but deployment not triggered.

**Solution**: Add git hook or file watcher:

**Option A: Git Post-Merge Hook**

```bash
#!/bin/bash
# .git/hooks/post-merge

# Check if PM_INSTRUCTIONS.md was updated
if git diff-tree -r --name-only --no-commit-id ORIG_HEAD HEAD | grep -q "src/claude_mpm/agents/PM_INSTRUCTIONS.md"; then
    echo "PM_INSTRUCTIONS.md updated - redeploying..."
    claude-mpm agents deploy PM --force-rebuild
fi
```

**Option B: File Watcher Service**

```python
# services/file_watcher_service.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path

class InstructionFileWatcher(FileSystemEventHandler):
    """Watch for changes to PM instruction source files."""

    def __init__(self, deployment_service):
        self.deployment_service = deployment_service
        self.source_files = [
            "src/claude_mpm/agents/PM_INSTRUCTIONS.md",
            "src/claude_mpm/agents/WORKFLOW.md",
            "src/claude_mpm/agents/MEMORY.md",
        ]

    def on_modified(self, event):
        """Triggered when source file is modified."""
        if not event.is_directory:
            rel_path = Path(event.src_path).relative_to(Path.cwd())
            if str(rel_path) in self.source_files:
                self.logger.info(f"Source file changed: {rel_path}")
                self.deployment_service.deploy_system_instructions(
                    target_dir=Path.cwd() / ".claude-mpm",
                    force_rebuild=True,
                    results={}
                )
```

**Benefits**:
- Automatic synchronization
- Eliminates manual deployment step
- Prevents staleness from persisting

### 6. Cache Metadata Enhancement

**Problem**: Cache metadata doesn't track source version.

**Solution**: Include version info in cache metadata:

```python
# instruction_cache_service.py:359-374 (ENHANCED)
def _write_metadata(self, content_hash: str, content_size: int, instruction_version: Optional[str] = None) -> None:
    """Write cache metadata with version tracking."""
    metadata = {
        "version": self.CACHE_VERSION,
        "content_type": "assembled_instruction",
        "components": [
            "BASE_PM.md",
            "PM_INSTRUCTIONS.md",
            "WORKFLOW.md",
            "agent_capabilities",
            "temporal_context",
        ],
        "content_hash": content_hash,
        "content_size_bytes": content_size,
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "instruction_version": instruction_version,  # NEW: Track PM_INSTRUCTIONS version
        "source_file_mtime": None,  # NEW: Track source file modification time
    }

    # Extract version from cache content if available
    try:
        cache_content = self.cache_file.read_text()
        version_match = re.search(r'<!-- PM_INSTRUCTIONS_VERSION: (\d+) -->', cache_content)
        if version_match:
            metadata["instruction_version"] = version_match.group(1)

        # Get source file mtime
        from claude_mpm.config.paths import paths
        source_path = paths.agents_dir / "PM_INSTRUCTIONS.md"
        if source_path.exists():
            metadata["source_file_mtime"] = source_path.stat().st_mtime
    except Exception as e:
        self.logger.debug(f"Could not extract metadata: {e}")

    self.meta_file.write_text(json.dumps(metadata, indent=2))
```

**Benefits**:
- Traceable version history
- Can detect version drift
- Better debugging information

---

## Integration Test Specification

### Test 1: Source File Update Detection

**Objective**: Verify deployment cache invalidates when source file is updated.

```python
def test_deployment_invalidation_on_source_update():
    """Test that deployment file is regenerated when source is updated."""

    # SETUP: Deploy with version 0006
    source_file = Path("src/claude_mpm/agents/PM_INSTRUCTIONS.md")
    deployed_file = Path(".claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md")

    # Create source with v0006
    source_file.write_text(
        "<!-- PM_INSTRUCTIONS_VERSION: 0006 -->\n"
        "# PM Instructions v0006\n"
    )

    # Deploy
    deployer = SystemInstructionsDeployer(logger, Path.cwd())
    results = {"deployed": [], "updated": [], "skipped": [], "errors": []}
    deployer.deploy_system_instructions(
        target_dir=Path(".claude-mpm"),
        force_rebuild=False,
        results=results
    )

    # Verify deployment
    assert deployed_file.exists()
    assert "0006" in deployed_file.read_text()

    # Wait to ensure different mtime
    time.sleep(1.1)

    # UPDATE: Change source to v0007
    source_file.write_text(
        "<!-- PM_INSTRUCTIONS_VERSION: 0007 -->\n"
        "# PM Instructions v0007\n"
    )

    # DEPLOY AGAIN (should detect change)
    results = {"deployed": [], "updated": [], "skipped": [], "errors": []}
    deployer.deploy_system_instructions(
        target_dir=Path(".claude-mpm"),
        force_rebuild=False,
        results=results
    )

    # VERIFY: Deployed file was updated
    assert deployed_file.exists()
    content = deployed_file.read_text()
    assert "0007" in content, "Deployed file should have v0007"
    assert "0006" not in content, "Deployed file should NOT have v0006"

    # Verify results tracked update (not skip)
    assert len(results["updated"]) > 0 or len(results["deployed"]) > 0, \
        "Deployment should have updated or deployed, not skipped"
    assert "PM_INSTRUCTIONS_DEPLOYED.md" not in results["skipped"], \
        "Deployment should NOT have been skipped"
```

### Test 2: Version Validation on Load

**Objective**: Verify loader detects and rejects stale deployed files.

```python
def test_instruction_loader_version_validation():
    """Test that loader validates version and falls back to source on staleness."""

    # SETUP: Create stale deployed file (v0006)
    source_file = Path("src/claude_mpm/agents/PM_INSTRUCTIONS.md")
    deployed_file = Path(".claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md")

    # Source has v0007
    source_file.write_text(
        "<!-- PM_INSTRUCTIONS_VERSION: 0007 -->\n"
        "# PM Instructions v0007\n"
    )

    # Deployed has stale v0006
    deployed_file.parent.mkdir(parents=True, exist_ok=True)
    deployed_file.write_text(
        "<!-- PM_INSTRUCTIONS_VERSION: 0006 -->\n"
        "# PM Instructions v0006 (STALE)\n"
    )

    # LOAD instructions
    loader = InstructionLoader(framework_path=Path.cwd())
    content = {}
    loader.load_framework_instructions(content)

    # VERIFY: Should have loaded v0007 from source (not stale v0006 from deployed)
    assert "framework_instructions" in content
    loaded = content["framework_instructions"]

    assert "0007" in loaded, "Should load v0007 from source"
    assert "STALE" not in loaded, "Should NOT load stale deployed file"
    assert "0006" not in loaded, "Should reject v0006"
```

### Test 3: Cache Content Integrity

**Objective**: Verify cache receives correct assembled content.

```python
def test_cache_content_integrity():
    """Test that cache receives correct assembled content, not stale."""

    # SETUP: Fresh source file
    source_file = Path("src/claude_mpm/agents/PM_INSTRUCTIONS.md")
    source_file.write_text(
        "<!-- PM_INSTRUCTIONS_VERSION: 0007 -->\n"
        "# PM Instructions v0007\n"
    )

    # LOAD via full stack (simulating real startup)
    from claude_mpm.core.framework_loader import FrameworkLoader
    from claude_mpm.services.instructions.instruction_cache_service import InstructionCacheService

    loader = FrameworkLoader(framework_path=Path.cwd())
    assembled_instructions = loader.get_framework_instructions()

    # UPDATE cache
    cache_service = InstructionCacheService(project_root=Path.cwd())
    result = cache_service.update_cache(instruction_content=assembled_instructions)

    # VERIFY: Cache contains v0007
    cache_file = Path(".claude-mpm/PM_INSTRUCTIONS.md")
    assert cache_file.exists()

    cached_content = cache_file.read_text()
    assert "0007" in cached_content, "Cache should contain v0007"
    assert "0006" not in cached_content, "Cache should NOT contain v0006"

    # Verify metadata
    meta_file = Path(".claude-mpm/PM_INSTRUCTIONS.md.meta")
    assert meta_file.exists()

    import json
    metadata = json.loads(meta_file.read_text())
    assert "instruction_version" in metadata, "Metadata should track version"
    assert metadata["instruction_version"] == "0007", "Metadata version should be 0007"
```

### Test 4: Startup Validation Warning

**Objective**: Verify ClaudeRunner warns on version mismatch.

```python
def test_startup_validation_warning(caplog):
    """Test that ClaudeRunner warns when loaded instructions are stale."""

    # SETUP: Deploy stale version
    deployed_file = Path(".claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md")
    deployed_file.parent.mkdir(parents=True, exist_ok=True)
    deployed_file.write_text(
        "<!-- PM_INSTRUCTIONS_VERSION: 0006 -->\n"
        "# PM Instructions v0006 (STALE)\n"
    )

    # Source has newer version
    source_file = Path("src/claude_mpm/agents/PM_INSTRUCTIONS.md")
    source_file.write_text(
        "<!-- PM_INSTRUCTIONS_VERSION: 0007 -->\n"
        "# PM Instructions v0007\n"
    )

    # INITIALIZE ClaudeRunner (should trigger validation)
    with caplog.at_level(logging.ERROR):
        runner = ClaudeRunner()

    # VERIFY: Warning was logged
    assert any(
        "CRITICAL: Loaded instructions version" in record.message
        for record in caplog.records
    ), "Should log critical error for stale instructions"

    assert any(
        "expected v0007" in record.message.lower()
        for record in caplog.records
    ), "Should mention expected version"
```

### Test 5: End-to-End Instruction Flow

**Objective**: Verify full flow from source update to Claude Code launch.

```python
def test_end_to_end_instruction_flow():
    """Test complete flow: source update → deployment → cache → CLI args."""

    # STEP 1: Update source file
    source_file = Path("src/claude_mpm/agents/PM_INSTRUCTIONS.md")
    source_file.write_text(
        "<!-- PM_INSTRUCTIONS_VERSION: 0007 -->\n"
        "# PM Instructions v0007\n"
        "Test content for E2E flow.\n"
    )

    # STEP 2: Deploy (should create deployed file)
    deployer = SystemInstructionsDeployer(logger, Path.cwd())
    results = {"deployed": [], "updated": [], "skipped": [], "errors": []}
    deployer.deploy_system_instructions(
        target_dir=Path(".claude-mpm"),
        force_rebuild=True,
        results=results
    )

    assert Path(".claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md").exists()

    # STEP 3: Load via FrameworkLoader
    from claude_mpm.core.framework_loader import FrameworkLoader
    loader = FrameworkLoader(framework_path=Path.cwd())
    assembled = loader.get_framework_instructions()

    assert "Test content for E2E flow" in assembled

    # STEP 4: Update cache
    from claude_mpm.services.instructions.instruction_cache_service import InstructionCacheService
    cache_service = InstructionCacheService(project_root=Path.cwd())
    cache_result = cache_service.update_cache(instruction_content=assembled)

    assert cache_result["updated"] == True

    # STEP 5: Verify cache file content
    cache_file = Path(".claude-mpm/PM_INSTRUCTIONS.md")
    cached_content = cache_file.read_text()

    assert "Test content for E2E flow" in cached_content
    assert "0007" in cached_content

    # STEP 6: Simulate CLI args generation
    from claude_mpm.core.interactive_session import InteractiveSession
    from claude_mpm.core.claude_runner import ClaudeRunner

    runner = ClaudeRunner()
    session = InteractiveSession(runner)

    # Build command (would normally launch Claude)
    cmd = session._build_command(test_mode=True)

    # VERIFY: Command includes cache file
    assert any("--system-prompt-file" in arg for arg in cmd), \
        "Command should use --system-prompt-file"

    assert any(str(cache_file) in arg for arg in cmd), \
        f"Command should reference cache file: {cache_file}"
```

---

## Immediate Fixes Required

### 1. Force Redeploy Now

```bash
# Immediate fix to restore v0007
claude-mpm agents deploy PM --force-rebuild
```

### 2. Invalidate Stale Cache

```bash
# Clear corrupted cache
rm .claude-mpm/PM_INSTRUCTIONS.md .claude-mpm/PM_INSTRUCTIONS.md.meta
```

### 3. Verify Correct Version Loaded

```bash
# Check deployed version
grep "PM_INSTRUCTIONS_VERSION" .claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md

# Check cache version (after restart)
grep "PM_INSTRUCTIONS_VERSION" .claude-mpm/PM_INSTRUCTIONS.md
```

---

## Long-Term Improvements

### 1. Monitoring & Alerting

**Add Healthcheck Endpoint**:
```python
@app.route("/api/health/instructions")
def check_instructions_health():
    """Health check for instruction version consistency."""
    from claude_mpm.config.paths import paths

    source_path = paths.agents_dir / "PM_INSTRUCTIONS.md"
    deployed_path = Path.cwd() / ".claude-mpm" / "PM_INSTRUCTIONS_DEPLOYED.md"
    cache_path = Path.cwd() / ".claude-mpm" / "PM_INSTRUCTIONS.md"

    versions = {}

    for name, path in [("source", source_path), ("deployed", deployed_path), ("cache", cache_path)]:
        if path.exists():
            content = path.read_text()
            match = re.search(r'<!-- PM_INSTRUCTIONS_VERSION: (\d+) -->', content)
            versions[name] = int(match.group(1)) if match else None
        else:
            versions[name] = None

    # Check consistency
    all_versions = [v for v in versions.values() if v is not None]
    if all_versions and len(set(all_versions)) > 1:
        return {
            "status": "unhealthy",
            "message": "Version mismatch detected",
            "versions": versions,
            "fix": "Run: claude-mpm agents deploy PM --force-rebuild"
        }, 500

    return {"status": "healthy", "versions": versions}, 200
```

### 2. CI/CD Integration

**Pre-commit Hook**:
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: check-pm-instructions-version
        name: Check PM Instructions Version
        entry: python scripts/check_pm_version.py
        language: python
        files: src/claude_mpm/agents/PM_INSTRUCTIONS.md
        pass_filenames: false
```

**GitHub Action**:
```yaml
# .github/workflows/validate-instructions.yml
name: Validate PM Instructions

on:
  push:
    paths:
      - 'src/claude_mpm/agents/PM_INSTRUCTIONS.md'
      - 'src/claude_mpm/agents/WORKFLOW.md'
      - 'src/claude_mpm/agents/MEMORY.md'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check version incremented
        run: |
          # Extract current version
          CURRENT=$(grep -oP 'PM_INSTRUCTIONS_VERSION: \K\d+' src/claude_mpm/agents/PM_INSTRUCTIONS.md)

          # Extract previous version from main
          git fetch origin main
          PREVIOUS=$(git show origin/main:src/claude_mpm/agents/PM_INSTRUCTIONS.md | grep -oP 'PM_INSTRUCTIONS_VERSION: \K\d+' || echo "0")

          if [ "$CURRENT" -le "$PREVIOUS" ]; then
            echo "ERROR: PM_INSTRUCTIONS version not incremented ($CURRENT <= $PREVIOUS)"
            exit 1
          fi

          echo "✓ Version incremented: $PREVIOUS → $CURRENT"
```

### 3. Self-Healing Mechanism

**Automatic Recovery**:
```python
# services/instruction_health_service.py
class InstructionHealthService:
    """Monitor and auto-heal instruction staleness."""

    def check_and_heal(self) -> bool:
        """Check instruction health and auto-heal if needed."""
        versions = self._get_all_versions()

        if self._is_stale(versions):
            self.logger.warning(
                f"Stale instructions detected: {versions}. Attempting auto-heal..."
            )

            # Trigger re-deployment
            from claude_mpm.services.agents.deployment import SystemInstructionsDeployer
            deployer = SystemInstructionsDeployer(self.logger, Path.cwd())
            results = {"deployed": [], "updated": [], "skipped": [], "errors": []}
            deployer.deploy_system_instructions(
                target_dir=Path(".claude-mpm"),
                force_rebuild=True,
                results=results
            )

            # Invalidate cache
            cache_service = InstructionCacheService(project_root=Path.cwd())
            cache_service.invalidate_cache()

            # Verify fix
            new_versions = self._get_all_versions()
            if not self._is_stale(new_versions):
                self.logger.info("✓ Auto-heal successful")
                return True
            else:
                self.logger.error("❌ Auto-heal failed")
                return False

        return True  # Healthy
```

---

## Conclusion

### What Broke

1. **Source file updated** (v0006 → v0007) via git commit
2. **Deployment never triggered** after git operation
3. **Stale deployed file** (v0006) remained from previous deployment
4. **InstructionLoader priority** loaded stale deployed file (PRIORITY 1)
5. **Source file never checked** (PRIORITY 2 never reached)
6. **Cache updated** with stale content from deployed file
7. **Claude Code received** wrong instructions (v0006 instead of v0007)

### How to Prevent

1. ✅ **Content-hash validation** for deployment (not just timestamp)
2. ✅ **Version header validation** in loader (reject stale files)
3. ✅ **Startup validation check** with user-visible warnings
4. ✅ **Post-deployment verification** (checksum validation)
5. ✅ **Auto-deployment triggers** (git hooks or file watchers)
6. ✅ **Enhanced cache metadata** (track source version)
7. ✅ **Monitoring & healthchecks** (detect drift)
8. ✅ **Integration tests** (catch regressions)
9. ✅ **Self-healing** (automatic recovery)

### Key Lesson

**Silent failures are the most dangerous**. This system:
- ✅ Had proper validation mechanisms
- ✅ Used hash-based cache invalidation
- ✅ Logged operations appropriately
- ❌ **BUT**: Trusted file existence checks without content validation
- ❌ **AND**: Had no version drift detection

**The fix**: Add version validation as a second line of defense when timestamp checks may be unreliable.

---

## References

**Relevant Files**:
- Source: `src/claude_mpm/agents/PM_INSTRUCTIONS.md`
- Deployed: `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md`
- Cache: `.claude-mpm/PM_INSTRUCTIONS.md`
- InstructionLoader: `src/claude_mpm/core/framework/loaders/instruction_loader.py`
- SystemInstructionsDeployer: `src/claude_mpm/services/agents/deployment/system_instructions_deployer.py`
- InstructionCacheService: `src/claude_mpm/services/instructions/instruction_cache_service.py`

**Related Commits**:
- `40e5dd60`: "refactor(pm): consolidate instructions + fix deepeval tests" (Dec 23, 2025)
- Last deployed: Dec 22, 2025 16:39

**Incident Timeline**:
- Dec 22 16:39: Last successful deployment (v0006)
- Dec 22 23:59: Source updated to v0007 via git commit
- Dec 23 00:03: Commit merged to main
- Dec 23 19:05: Cache updated with stale v0006 from deployed file
- Dec 23 (present): PM receiving wrong instructions (v0006)
