# Agent Count Discrepancy Investigation

**Date**: 2025-12-15
**Investigator**: Research Agent
**Issue**: Deployment shows "82-87 agents" but count appears inflated due to duplicate files

---

## Executive Summary

The agent count discrepancy is caused by the Git Tree API discovery method (`_discover_agents_via_tree_api`) counting BOTH the `agents/` directory (46 files) AND the `dist/agents/` directory (41 files) as deployable agents. The `dist/` directory contains build artifacts that should be excluded from agent discovery.

**Root Cause**: Missing exclusion filter for `dist/` directory in agent discovery logic
**Impact**: Inflated agent counts (87 vs actual 46) and potential duplicate deployments
**Severity**: Medium - causes confusion but not data loss

---

## Investigation Findings

### 1. Actual Agent Counts

**Cache Directory Breakdown** (`~/.claude-mpm/cache/remote-agents/`):

| Location | Count | Type |
|----------|-------|------|
| `bobmatnyc/claude-mpm-agents/agents/` | **46** | ✅ Source agents (correct) |
| `bobmatnyc/claude-mpm-agents/dist/agents/` | **41** | ❌ Build artifacts (should exclude) |
| Top-level directories (documentation/, universal/, qa/, etc.) | 19 | ✅ Flat structure agents (legacy) |
| **Total discovered by Tree API** | **87** | ❌ Includes duplicates |
| **Expected count (without dist/)** | **46** | ✅ Actual unique agents |

**Source Templates** (`src/claude_mpm/agents/templates/`):
- JSON templates: 39 files
- Markdown templates: 17 files
- Total: 56 template files (framework development artifacts)

### 2. Code Location - Discovery Logic

**File**: `src/claude_mpm/services/agents/sources/git_source_sync_service.py`

**Method**: `_discover_agents_via_tree_api()` (lines 763-867)

**Current Filter Logic** (line 860-864):
```python
# Filter for .md or .json files, exclude README and .gitignore
if (
    relative_path.endswith(".md") or relative_path.endswith(".json")
) and relative_path not in ["README.md", ".gitignore"]:
    agent_files.append(relative_path)
```

**Problem**: This filter does NOT exclude `dist/` directory paths.

**Example Discovered Paths**:
- ✅ `engineer/core/engineer.md` (correct)
- ✅ `research.md` (correct)
- ❌ `dist/agents/engineer.md` (build artifact - should exclude)
- ❌ `dist/agents/research.md` (build artifact - should exclude)

### 3. Configuration Analysis

**Agent Source Configuration** (`src/claude_mpm/config/agent_sources.py`):
```python
default_repo = GitRepository(
    url="https://github.com/bobmatnyc/claude-mpm-agents",
    subdirectory="agents",  # ← Intended to limit to agents/ directory
    enabled=True,
    priority=100,
)
```

**Issue**: The `subdirectory="agents"` configuration is intended to restrict discovery to the `agents/` directory, but the Tree API implementation uses this as a PREFIX filter (line 851-852), which matches BOTH:
- `agents/` (intended)
- `dist/agents/` (unintended - should exclude)

**Relevant Code** (line 850-858):
```python
# Filter for files in base_path (e.g., "agents/")
if base_path and not path.startswith(base_path + "/"):
    continue

# Remove base_path prefix for relative paths
if base_path:
    relative_path = path[len(base_path) + 1 :]
else:
    relative_path = path
```

This logic only checks if the path STARTS with `agents/`, but `dist/agents/file.md` also contains `agents/` in its path after stripping the base path.

### 4. Repository Structure

**bobmatnyc/claude-mpm-agents repository**:
```
.
├── agents/               ← Source directory (46 .md files)
│   ├── engineer/
│   ├── qa/
│   ├── research.md
│   └── ...
├── dist/                 ← Build output directory
│   └── agents/          ← Build artifacts (41 .md files) ❌ SHOULD EXCLUDE
│       ├── engineer.md
│       ├── research.md
│       └── ...
├── templates/            ← Agent templates (not counted)
├── docs/                 ← Documentation (not counted)
└── README.md
```

**Why `dist/` exists**: The `dist/` directory appears to be a build output directory for processed/compiled agents. These are deployment artifacts, not source files.

---

## Root Cause Analysis

### Primary Issue: Inadequate Path Filtering

The `_discover_agents_via_tree_api()` method uses GitHub's Git Tree API to recursively discover all files in the repository. The filtering logic has two problems:

1. **Base Path Prefix Matching** (line 851-852):
   - Current: `if base_path and not path.startswith(base_path + "/")`
   - Matches: `agents/file.md` ✅ AND `dist/agents/file.md` ❌
   - Should match: ONLY `agents/` at repository root

2. **No Exclusion Patterns**:
   - Missing: Exclusion list for build directories (`dist/`, `build/`, `.cache/`, etc.)
   - Missing: Path depth validation (ensure `agents/` is at root, not nested)

### Why This Went Unnoticed

1. **Deployment Still Works**: Even with inflated counts, agents deploy correctly (duplicates are overwritten or skipped)
2. **Progress Display**: Users see "82/87 agents" in progress bars but assume it's correct
3. **No Validation**: No assertion checking expected vs actual agent counts

---

## Reproduction Steps

1. **Check Current Count**:
   ```bash
   find ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/ -name "*.md" -type f | wc -l
   # Output: 46 (correct)

   find ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/dist/agents/ -name "*.md" -type f | wc -l
   # Output: 41 (build artifacts - should not count)
   ```

2. **Trigger Deployment**:
   ```bash
   cd /path/to/claude-mpm-project
   mpm-agents-deploy
   # Watch progress bar: Shows "Syncing 82-87 agents" (inflated count)
   ```

3. **Verify Discovery Logic**:
   - Add debug logging to `_discover_agents_via_tree_api()` line 866
   - Print each discovered path to see `dist/agents/*` files included

---

## Recommended Fix

### Option 1: Exact Base Path Matching (Recommended)

**File**: `src/claude_mpm/services/agents/sources/git_source_sync_service.py`
**Location**: Lines 850-864 in `_discover_agents_via_tree_api()`

**Current Code**:
```python
# Filter for files in base_path (e.g., "agents/")
if base_path and not path.startswith(base_path + "/"):
    continue
```

**Proposed Fix**:
```python
# Filter for files in base_path (e.g., "agents/")
# Ensure path starts with base_path at repository root (exact match)
if base_path:
    if not path.startswith(base_path + "/"):
        continue
    # Additional check: path should not contain excluded directories
    path_parts = path.split("/")
    if any(excluded in path_parts for excluded in ["dist", "build", ".cache", "node_modules"]):
        continue
```

**Rationale**:
- Maintains backward compatibility with existing `base_path` logic
- Adds explicit exclusion list for common build/cache directories
- Handles nested excluded directories (e.g., `agents/dist/` also excluded)

### Option 2: Add Exclusion Configuration

Add `exclude_patterns` to `GitRepository` dataclass:

**File**: `src/claude_mpm/models/git_repository.py`

```python
@dataclass
class GitRepository:
    url: str
    subdirectory: str = ""
    enabled: bool = True
    priority: int = 100
    exclude_patterns: List[str] = field(default_factory=lambda: ["dist/**", "build/**", ".cache/**"])
```

**Rationale**:
- More flexible and configurable
- Allows per-repository exclusion patterns
- Requires more implementation work (pattern matching logic)

### Option 3: Repository-Side Fix (bobmatnyc/claude-mpm-agents)

Move `dist/` outside the repository or add to `.gitignore`:

**Action**: Update `bobmatnyc/claude-mpm-agents` repository:
```bash
# Add dist/ to .gitignore
echo "dist/" >> .gitignore
git rm -r --cached dist/
git commit -m "chore: exclude dist/ from version control"
```

**Rationale**:
- Cleanest solution (build artifacts shouldn't be in git)
- Fixes issue at source without code changes
- Requires upstream repository modification

---

## Impact Assessment

### User Impact
- **Confusion**: Users see inflated agent counts (82-87 vs actual 46)
- **Performance**: Minimal - duplicates are handled during deployment (skipped or overwritten)
- **Correctness**: Deployed agents are correct (no functional issue)

### System Impact
- **Network**: Extra API calls and bandwidth for duplicate files
- **Disk**: Duplicate files in cache directory (41 extra files × ~5KB = ~200KB wasted)
- **Progress Display**: Misleading progress bars showing inflated totals

### Severity: **Medium**
- Not a critical bug (deployments work correctly)
- Causes user confusion and wasted resources
- Easy to fix with targeted code change

---

## Testing Plan

After implementing fix:

1. **Unit Test**: Add test case for `_discover_agents_via_tree_api()`:
   ```python
   def test_discover_agents_excludes_dist_directory():
       service = GitSourceSyncService(...)
       agents = service._discover_agents_via_tree_api("bobmatnyc", "claude-mpm-agents", "main", "agents")

       # Assert no dist/ paths included
       assert not any("dist/" in agent_path for agent_path in agents)

       # Assert correct count (46 agents, not 87)
       assert len(agents) == 46
   ```

2. **Integration Test**: Deploy agents and verify count:
   ```bash
   mpm-agents-deploy --verbose
   # Expected output: "Syncing 46 agents" (not 82-87)
   ```

3. **Regression Test**: Ensure existing agents still deploy correctly:
   ```bash
   mpm-agents-deploy
   claude-code --agents list
   # Verify all expected agents are present
   ```

---

## Related Issues

- **GitHub Issue**: (To be created) "Agent discovery counts build artifacts in dist/ directory"
- **Documentation**: Update agent source configuration docs to explain exclusion patterns
- **Changelog Entry**: "fix(agents): exclude dist/ directory from agent discovery, reducing count from 87 to 46"

---

## References

### Files Modified (Proposed)
1. `src/claude_mpm/services/agents/sources/git_source_sync_service.py` (lines 850-864)
2. `tests/services/agents/sources/test_git_source_sync_service.py` (new test cases)

### Files Analyzed
1. `src/claude_mpm/services/agents/sources/git_source_sync_service.py` - Discovery logic
2. `src/claude_mpm/config/agent_sources.py` - Configuration defaults
3. `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/` - Cached repository structure

### Key Metrics
- **Current Count (with bug)**: 87 agents discovered
- **Expected Count (after fix)**: 46 agents discovered
- **Reduction**: 47% fewer files processed
- **Files Affected**: 41 duplicate build artifacts

---

## Conclusion

The agent count discrepancy (82-87 vs expected 46) is caused by the Git Tree API discovery logic counting build artifacts in the `dist/agents/` directory alongside source files in `agents/`. The fix is straightforward: add exclusion logic for common build directories (`dist/`, `build/`, etc.) to the path filtering in `_discover_agents_via_tree_api()`.

**Recommended Action**: Implement Option 1 (Exact Base Path Matching) with exclusion list for immediate fix, then consider Option 3 (repository-side cleanup) for long-term maintainability.

**Priority**: Medium (non-critical but should be fixed in next patch release)

---

**Investigation Complete**: 2025-12-15
**Research Document**: `/Users/masa/Projects/claude-mpm/docs/research/agent-count-discrepancy-2025-12-15.md`
