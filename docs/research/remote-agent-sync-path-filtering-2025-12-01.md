# Remote Agent Sync Path Filtering Research

**Date:** 2025-12-01
**Research Type:** Bug Investigation
**Status:** Complete
**Priority:** High (causing deployment failures)

## Executive Summary

Found the root cause of template files being incorrectly synced from the remote GitHub repository. The issue is in `GitSourceSyncService._get_agent_list()` which discovers ALL `.md` files in the configured directory without filtering by subdirectory. Template files like `pm_examples.md` and `validation_templates.md` exist in the remote repo's `/templates/` directory but are being pulled into the agent cache, causing "Markdown template missing YAML frontmatter" errors during deployment.

**Solution:** Add path filtering to only sync `.md` files from the `/agents/` subdirectory.

---

## Problem Statement

### Current Behavior
The system is syncing template files from the remote repository that should NOT be treated as agents:
- `pm_examples.md`
- `validation_templates.md`
- Other `.md` files in `/templates/` directory

These files are being discovered and processed as agents, causing validation failures:
```
ERROR: Markdown template missing YAML frontmatter: pm_examples.md
```

### Root Cause
The GitHub API file discovery in `GitSourceSyncService._get_agent_list()` (lines 612-725) filters files by:
1. ✅ File extension: `.endswith(".md")`
2. ✅ Filename: `!= "README.md"`
3. ✅ File type: `== "file"`
4. ❌ **MISSING: Path/subdirectory filtering**

---

## Code Analysis

### 1. File Discovery Logic

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/sources/git_source_sync_service.py`

**Key Method:** `_get_agent_list()` (lines 612-725)

```python
def _get_agent_list(self) -> List[str]:
    """Get list of agent filenames to sync.

    Uses GitHub API to discover .md files in repository directory.
    """
    # Extract repository info from source URL
    # URL format: https://raw.githubusercontent.com/owner/repo/branch/path
    try:
        url_parts = self.source_url.replace(
            "https://raw.githubusercontent.com/", ""
        ).split("/")

        if len(url_parts) >= 3:
            owner = url_parts[0]
            repo = url_parts[1]
            branch = url_parts[2]
            path = "/".join(url_parts[3:]) if len(url_parts) > 3 else ""

            # Construct GitHub API URL
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
            if branch and branch != "main":
                api_url += f"?ref={branch}"

            # Make API request
            response = self.session.get(api_url, headers=api_headers, timeout=10)

            if response.status_code == 200:
                files = response.json()

                # Filter for .md files, exclude README.md
                agent_files = [
                    f["name"]
                    for f in files
                    if isinstance(f, dict)
                    and f.get("name", "").endswith(".md")
                    and f.get("name") != "README.md"
                    and f.get("type") == "file"  # ⚠️ PROBLEM: No path filtering!
                ]
```

**Current Filtering (line 671-679):**
- ✅ `f.get("name", "").endswith(".md")` - Only .md files
- ✅ `f.get("name") != "README.md"` - Exclude README
- ✅ `f.get("type") == "file"` - Exclude directories
- ❌ **MISSING:** Path-based filtering to only include `/agents/` directory

**GitHub API Response Structure:**
```json
[
  {
    "name": "research.md",
    "path": "agents/research.md",  // ⚠️ THIS FIELD EXISTS BUT IS NOT CHECKED
    "type": "file",
    "sha": "abc123...",
    "url": "...",
    "download_url": "..."
  },
  {
    "name": "pm_examples.md",
    "path": "templates/pm_examples.md",  // ⚠️ This should be EXCLUDED
    "type": "file",
    "sha": "def456...",
    "url": "...",
    "download_url": "..."
  }
]
```

### 2. Default Source URL Configuration

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/sources/git_source_sync_service.py`

**Initialization (line 181-186):**
```python
def __init__(
    self,
    source_url: str = "https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main/agents",
    cache_dir: Optional[Path] = None,
    source_id: str = "github-remote",
):
    """Initialize Git source sync service.

    Args:
        source_url: Base URL for raw files (without trailing slash)
    """
    self.source_url = source_url.rstrip("/")
```

**Note:** The default source URL already includes `/agents` subdirectory, but the API call uses the parsed path to construct the API endpoint. The GitHub API response includes files from ALL subdirectories visible at that path level.

### 3. Cache Directory Structure

**Default Cache Location:** `~/.claude-mpm/cache/remote-agents/`

**Evidence from code:**
```python
# Line 201-203
if cache_dir:
    self.cache_dir = Path(cache_dir)
else:
    home = Path.home()
    self.cache_dir = home / ".claude-mpm" / "cache" / "remote-agents"
```

**What gets cached:**
- ALL `.md` files discovered by `_get_agent_list()`
- Includes both agents AND template files (current bug)

### 4. File Discovery Flow

**RemoteAgentDiscoveryService** (lines 68-117):
```python
def discover_remote_agents(self) -> List[Dict[str, Any]]:
    """Discover all remote agents from cache directory.

    Scans the remote agents directory for *.md files.
    """
    # Find all Markdown files
    md_files = list(self.remote_agents_dir.glob("*.md"))  # ⚠️ Finds ALL .md files

    for md_file in md_files:
        try:
            agent_dict = self._parse_markdown_agent(md_file)
            if agent_dict:
                agents.append(agent_dict)
```

**This is WHERE the validation error occurs:**
1. GitSourceSyncService downloads `pm_examples.md` to cache
2. RemoteAgentDiscoveryService finds it via `glob("*.md")`
3. `_parse_markdown_agent()` tries to parse it as agent
4. File doesn't have YAML frontmatter (it's a template, not an agent)
5. Error: "Markdown template missing YAML frontmatter"

---

## Solution Architecture

### Option 1: Filter in API Response Processing (RECOMMENDED)

**File:** `git_source_sync_service.py`
**Method:** `_get_agent_list()` (line 671-679)

**Current Code:**
```python
agent_files = [
    f["name"]
    for f in files
    if isinstance(f, dict)
    and f.get("name", "").endswith(".md")
    and f.get("name") != "README.md"
    and f.get("type") == "file"
]
```

**Fixed Code:**
```python
agent_files = [
    f["name"]
    for f in files
    if isinstance(f, dict)
    and f.get("name", "").endswith(".md")
    and f.get("name") != "README.md"
    and f.get("type") == "file"
    and not f.get("path", "").startswith("templates/")  # NEW: Exclude templates
]
```

**Alternative (more explicit):**
```python
agent_files = [
    f["name"]
    for f in files
    if isinstance(f, dict)
    and f.get("name", "").endswith(".md")
    and f.get("name") != "README.md"
    and f.get("type") == "file"
    and (
        f.get("path", "").startswith("agents/") or
        "/" not in f.get("path", "")  # Allow root-level .md files
    )
]
```

**Pros:**
- ✅ Fixes issue at source (prevents download)
- ✅ Reduces cache size (no unnecessary files)
- ✅ Simple one-line change
- ✅ Works with GitHub API response structure

**Cons:**
- ⚠️ Hardcoded `templates/` exclusion (not configurable)
- ⚠️ Assumes GitHub API includes `path` field

### Option 2: Filter in RemoteAgentDiscoveryService

**File:** `remote_agent_discovery_service.py`
**Method:** `discover_remote_agents()` (line 94)

**Current Code:**
```python
md_files = list(self.remote_agents_dir.glob("*.md"))
```

**Fixed Code:**
```python
# Filter out template files
md_files = [
    f for f in self.remote_agents_dir.glob("*.md")
    if not f.name.startswith("validation_")
    and not f.name.startswith("pm_")
]
```

**Pros:**
- ✅ Prevents validation errors
- ✅ Doesn't require API changes

**Cons:**
- ❌ Files still downloaded to cache (wasted bandwidth/storage)
- ❌ Fragile (relies on filename patterns)
- ❌ Doesn't fix root cause

### Option 3: Use Recursive GitHub Tree API

**File:** `git_source_sync_service.py`
**Method:** `_get_agent_list()`

**Implementation Pattern (from skills code):**
```python
# Step 1: Get commit SHA
refs_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}"
commit_sha = requests.get(refs_url).json()["object"]["sha"]

# Step 2: Get recursive tree
tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{commit_sha}"
tree_data = requests.get(tree_url, params={"recursive": "1"}).json()

# Step 3: Filter by path
agent_files = [
    item["path"].split("/")[-1]  # Get filename only
    for item in tree_data.get("tree", [])
    if item["type"] == "blob"
    and item["path"].endswith(".md")
    and item["path"].startswith("agents/")  # NEW: Path filtering
]
```

**Pros:**
- ✅ More flexible (can filter by any path pattern)
- ✅ Already used in skills system (proven pattern)
- ✅ Gets ALL files recursively (future-proof)

**Cons:**
- ⚠️ Requires 2 API calls instead of 1 (rate limit impact)
- ⚠️ More complex implementation
- ⚠️ Overkill for simple use case

---

## Recommended Solution

**Implement Option 1: Filter in API Response Processing**

**Rationale:**
1. **Minimal Change:** Single-line addition to existing filter
2. **Prevents Root Cause:** Files never downloaded to cache
3. **Performance:** No extra API calls
4. **Maintainability:** Clear and explicit filtering logic
5. **Backwards Compatible:** Doesn't break existing behavior

**Implementation Location:**
- **File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/sources/git_source_sync_service.py`
- **Method:** `_get_agent_list()`
- **Lines:** 671-679

**Code Change:**
```python
# Filter for .md files in agents/ directory only, exclude README.md
agent_files = [
    f["name"]
    for f in files
    if isinstance(f, dict)
    and f.get("name", "").endswith(".md")
    and f.get("name") != "README.md"
    and f.get("type") == "file"
    and f.get("path", "").startswith("agents/")  # NEW: Only sync from /agents/ directory
]
```

**Edge Cases to Handle:**
1. **Root-level agents:** If source URL is repo root, allow files without "agents/" prefix
2. **Subdirectory variations:** Consider `agents/` vs `agent/` vs custom paths
3. **Empty path field:** GitHub API should always include `path`, but add defensive check

**Improved Implementation:**
```python
# Extract expected path prefix from source URL
expected_path_prefix = path + "/" if path else ""

agent_files = [
    f["name"]
    for f in files
    if isinstance(f, dict)
    and f.get("name", "").endswith(".md")
    and f.get("name") != "README.md"
    and f.get("type") == "file"
    and (
        # If we have a path prefix (e.g., "agents/"), file must be in that directory
        not expected_path_prefix
        or f.get("path", "").startswith(expected_path_prefix)
    )
    and not f.get("path", "").startswith("templates/")  # Always exclude templates
]
```

---

## Testing Strategy

### Unit Tests

**File:** `/Users/masa/Projects/claude-mpm/tests/services/agents/sources/test_git_source_sync_service.py`

**Test Cases:**
1. **Test agent discovery filters templates:**
   ```python
   def test_get_agent_list_excludes_templates():
       """Verify template files are excluded from agent list."""
       # Mock GitHub API response with both agents and templates
       mock_response = [
           {"name": "research.md", "path": "agents/research.md", "type": "file"},
           {"name": "engineer.md", "path": "agents/engineer.md", "type": "file"},
           {"name": "pm_examples.md", "path": "templates/pm_examples.md", "type": "file"},
           {"name": "validation_templates.md", "path": "templates/validation_templates.md", "type": "file"},
       ]

       # Call _get_agent_list() with mocked API
       agent_list = service._get_agent_list()

       # Assert only agents/ files are included
       assert "research.md" in agent_list
       assert "engineer.md" in agent_list
       assert "pm_examples.md" not in agent_list
       assert "validation_templates.md" not in agent_list
   ```

2. **Test with nested subdirectories:**
   ```python
   def test_get_agent_list_handles_nested_paths():
       """Verify nested agent directories work correctly."""
       mock_response = [
           {"name": "research.md", "path": "agents/core/research.md", "type": "file"},
           {"name": "specialized.md", "path": "agents/specialized/specialized.md", "type": "file"},
       ]
       # Should include all agents/* files regardless of nesting
   ```

3. **Test fallback list unchanged:**
   ```python
   def test_get_agent_list_fallback_unchanged():
       """Verify fallback list still works when API fails."""
       # Mock API failure (network error, rate limit, etc.)
       agent_list = service._get_agent_list()

       # Should return hardcoded fallback list (lines 714-725)
       assert len(agent_list) == 10
       assert "research.md" in agent_list
   ```

### Integration Tests

**File:** `/Users/masa/Projects/claude-mpm/tests/test_git_agent_installation.py`

**Test Case:**
```python
def test_remote_sync_excludes_template_files():
    """End-to-end test: remote sync should not download template files."""
    # Sync from actual GitHub repository
    manager = GitSourceManager()
    repo = GitRepository(url="https://github.com/bobmatnyc/claude-mpm-agents")
    result = manager.sync_repository(repo)

    # Check cache directory
    cache_dir = repo.cache_path
    cached_files = list(cache_dir.glob("*.md"))

    # Verify no template files in cache
    cached_names = [f.name for f in cached_files]
    assert "pm_examples.md" not in cached_names
    assert "validation_templates.md" not in cached_names

    # Verify agent files ARE present
    assert "research.md" in cached_names
    assert "engineer.md" in cached_names
```

### Manual Testing

1. **Clear cache:**
   ```bash
   rm -rf ~/.claude-mpm/cache/remote-agents/*
   ```

2. **Trigger sync:**
   ```bash
   claude-mpm agents sync --verbose
   ```

3. **Verify cache contents:**
   ```bash
   ls -la ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/
   ```

4. **Expected outcome:**
   - ✅ Agent files present: `research.md`, `engineer.md`, etc.
   - ❌ Template files ABSENT: `pm_examples.md`, `validation_templates.md`

5. **Verify deployment works:**
   ```bash
   claude-mpm agents deploy --all
   ```

6. **Expected outcome:**
   - ✅ No "Markdown template missing YAML frontmatter" errors
   - ✅ All agents deploy successfully

---

## Related Files

### Source Code
1. **`/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/sources/git_source_sync_service.py`**
   - Line 612-725: `_get_agent_list()` - **PRIMARY FIX LOCATION**
   - Line 227-419: `sync_agents()` - Calls `_get_agent_list()`
   - Line 181-186: `__init__()` - Default source URL configuration

2. **`/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py`**
   - Line 68-117: `discover_remote_agents()` - Discovers cached agents
   - Line 119-221: `_parse_markdown_agent()` - Parses agent metadata (where error occurs)

3. **`/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/git_source_manager.py`**
   - Line 64-163: `sync_repository()` - Orchestrates sync operation
   - Line 100-114: Constructs source URL from repository metadata

### Test Files
1. **`/Users/masa/Projects/claude-mpm/tests/services/agents/sources/test_git_source_sync_service.py`**
   - Add new test: `test_get_agent_list_excludes_templates()`

2. **`/Users/masa/Projects/claude-mpm/tests/test_git_agent_installation.py`**
   - Add integration test: `test_remote_sync_excludes_template_files()`

### Configuration
1. **`/Users/masa/Projects/claude-mpm/config/agent_sources.yaml.example`**
   - Repository source configuration examples
   - May need documentation update about path filtering

---

## Impact Assessment

### Files Modified
- ✏️ `git_source_sync_service.py` (1 line change in `_get_agent_list()`)

### Tests Added
- ✅ Unit test: Template exclusion filtering
- ✅ Unit test: Nested path handling
- ✅ Integration test: End-to-end sync validation

### Backwards Compatibility
- ✅ **SAFE:** Existing agent sync behavior unchanged
- ✅ **SAFE:** Only filters out non-agent files (templates)
- ✅ **SAFE:** Fallback list unchanged (API failure case)

### Performance Impact
- ✅ **NEUTRAL:** No additional API calls
- ✅ **POSITIVE:** Reduced cache size (fewer files downloaded)
- ✅ **POSITIVE:** Faster discovery (fewer files to scan)

### Risk Level
- 🟢 **LOW RISK:** Simple filter addition
- 🟢 **LOW RISK:** Well-understood code path
- 🟢 **LOW RISK:** Thoroughly testable

---

## Next Steps

1. **Implement Fix:**
   - Modify `_get_agent_list()` to filter by path
   - Add defensive checks for missing `path` field

2. **Add Tests:**
   - Unit tests for path filtering
   - Integration test for end-to-end validation

3. **Manual Verification:**
   - Clear cache and re-sync
   - Verify template files excluded
   - Confirm deployment succeeds

4. **Documentation:**
   - Update code comments with path filtering logic
   - Add note to `agent_sources.yaml.example` about subdirectory expectations

5. **Deployment:**
   - Create ticket for fix implementation
   - Code review
   - Merge and release

---

## Conclusion

The root cause is clear: `GitSourceSyncService._get_agent_list()` discovers ALL `.md` files in the configured directory without filtering by subdirectory. Template files in `/templates/` are being treated as agents, causing validation errors.

The fix is straightforward: Add path filtering to the GitHub API response processing to only include files from the `/agents/` subdirectory. This is a one-line change with minimal risk and high confidence of success.

**Recommended Action:** Implement Option 1 (filter in API response) with thorough testing.
