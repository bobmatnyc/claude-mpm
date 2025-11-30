# Git Agents Deployment Architecture Analysis

**Date**: 2025-11-30
**Status**: Architecture Gap Analysis Complete
**Priority**: HIGH
**Impact**: Remote agents cached but never deployed

---

## Executive Summary

**Problem**: Remote agents are successfully synced from GitHub and cached to `~/.claude-mpm/cache/remote-agents/` but are **NEVER discovered** during agent deployment. The cached remote agents exist as a disconnected system with no integration into the deployment pipeline.

**Root Cause**: The `MultiSourceAgentDeploymentService.discover_agents_from_all_sources()` only checks 3 tiers (system, project, user) and completely ignores the remote-agents cache directory.

**Impact**:
- 10 remote agents cached but never used
- Only bundled system agents actually deployed
- No version comparison with remote sources
- Users cannot benefit from community/remote agents

**Solution Complexity**: MEDIUM (4-tier integration + user-level deprecation)

---

## 1. Current Architecture Analysis

### 1.1 Working Components ✅

#### Remote Agent Sync Pipeline
**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/sources/git_source_sync_service.py`

```python
class GitSourceSyncService:
    def __init__(self, source_url, cache_dir=None, source_id="github-remote"):
        # Default cache: ~/.claude-mpm/cache/remote-agents/
        self.cache_dir = cache_dir or Path.home() / ".claude-mpm" / "cache" / "remote-agents"
        self.sync_state = AgentSyncState()  # SQLite state tracking
        self.etag_cache = ETagCache(etag_cache_file)  # ETag-based caching
```

**Verified Cache Contents**:
```bash
$ ls -la ~/.claude-mpm/cache/remote-agents/
total 496
-rw-r--r--  13691 documentation.md
-rw-r--r--   4096 engineer.md
-rw-r--r--   9357 ops.md
-rw-r--r--  33444 product_owner.md
-rw-r--r--   9302 project_organizer.md
-rw-r--r--   8235 qa.md
-rw-r--r--  47628 research.md
-rw-r--r--  25570 security.md
-rw-r--r--  50531 ticketing.md
-rw-r--r--  19013 version_control.md
```

**Key Features Working**:
- ✅ ETag-based incremental updates (HTTP 304 Not Modified)
- ✅ SQLite state tracking (`AgentSyncState`)
- ✅ SHA-256 content hashing for integrity
- ✅ Graceful error handling (non-blocking startup)
- ✅ Sync history and metrics collection

**Startup Integration**:
**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/startup_sync.py`

```python
def sync_agents_on_startup(config: Optional[Dict[str, Any]] = None):
    """Syncs agents on Claude MPM startup (non-blocking)."""
    agent_sync_config = config.get("agent_sync", {})
    if not agent_sync_config.get("enabled", True):
        return  # Sync disabled

    for source_config in sources:
        sync_service = GitSourceSyncService(
            source_url=source_config.get("url"),
            cache_dir=cache_dir,
            source_id=source_config.get("id"),
        )
        sync_result = sync_service.sync_agents(force_refresh=False)
        # Agents cached to ~/.claude-mpm/cache/remote-agents/ ✅
```

### 1.2 Broken Components ❌

#### Agent Discovery Service - Missing 4th Tier
**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py`

```python
def discover_agents_from_all_sources(
    self,
    system_templates_dir: Optional[Path] = None,
    project_agents_dir: Optional[Path] = None,
    user_agents_dir: Optional[Path] = None,  # ❌ No remote_agents_dir parameter
    working_directory: Optional[Path] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Discover agents from all available sources.

    PROBLEM: Only discovers 3 tiers, ignores remote-agents cache!
    """
    sources = [
        ("system", system_templates_dir),    # Tier 1: Bundled system agents
        ("project", project_agents_dir),     # Tier 2: Project-specific agents
        ("user", user_agents_dir),           # Tier 3: User custom agents
        # ❌ MISSING: ("remote", remote_agents_dir)  # Tier 4: Remote GitHub agents
    ]

    for source_name, source_dir in sources:
        if source_dir and source_dir.exists():
            discovery_service = AgentDiscoveryService(source_dir)
            agents = discovery_service.list_available_agents(log_discovery=False)
            # Aggregates agents by name for version comparison
```

**Gap Analysis**:
1. ❌ No `remote_agents_dir` parameter
2. ❌ No discovery of `~/.claude-mpm/cache/remote-agents/`
3. ❌ No version comparison with remote sources
4. ❌ Remote agents never added to `agents_by_name` dict
5. ❌ `select_highest_version_agents()` never sees remote agents

#### Deployment Pipeline - No Remote Integration
**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/agents/deployment/agent_deployment.py`

```python
# Line 766: get_agents_for_deployment() call
agents_to_deploy, agent_sources, cleanup_results = (
    self.multi_source_service.get_agents_for_deployment(
        system_templates_dir=system_templates_dir,
        project_agents_dir=project_agents_dir,
        user_agents_dir=user_agents_dir,
        # ❌ MISSING: remote_agents_dir=remote_agents_dir
        working_directory=self.working_directory,
        excluded_agents=excluded_agents,
        config=config,
        cleanup_outdated=cleanup_outdated,
    )
)
```

**Result**: Cached remote agents sit unused in `~/.claude-mpm/cache/remote-agents/` forever.

---

## 2. Identified Gaps

### 2.1 Discovery Gap

**Current 3-Tier System**:
```
Tier 1: System Templates    → /src/claude_mpm/agents/templates/*.json
Tier 2: Project Agents       → .claude-mpm/agents/*.json
Tier 3: User Custom Agents   → ~/.claude-mpm/agents/*.json (deprecated)
```

**Missing 4th Tier**:
```
Tier 4: Remote Agents        → ~/.claude-mpm/cache/remote-agents/*.md ❌ NOT DISCOVERED
```

### 2.2 Version Comparison Gap

**Current Behavior**:
- System agent `research.json` v4.1.0 → Deployed ✅
- Project agent `research.json` v4.2.0 → Compared, highest deployed ✅
- User agent `research.json` v3.9.0 → Compared, cleaned up ✅
- **Remote agent `research.md` v4.3.0 → NEVER COMPARED ❌**

### 2.3 Deployment Gap

**Current Flow**:
```
1. GitSourceSyncService syncs agents → Cache
2. MultiSourceAgentDeploymentService discovers agents → Skips cache ❌
3. select_highest_version_agents() compares versions → No remote agents ❌
4. Agents deployed to ~/.claude/agents/ → Only system/project/user sources
```

**Missing Flow**:
```
2b. Discover remote-agents cache → ✅ NEEDS IMPLEMENTATION
3b. Compare remote agent versions → ✅ NEEDS IMPLEMENTATION
4b. Deploy highest version (possibly remote) → ✅ NEEDS IMPLEMENTATION
```

### 2.4 Format Inconsistency Gap

**Problem**: Remote agents are in **Markdown format** (`.md` files), but system/project agents are **JSON templates** (`.json` files).

**Current Discovery**:
```python
# AgentDiscoveryService.list_available_agents()
template_files = list(self.templates_dir.glob("*.json"))  # ❌ Only finds JSON
```

**Impact**:
- Remote agents in `.md` format are skipped
- No parser for markdown-based agent definitions
- Need format conversion or dual-format support

---

## 3. User-Level Deprecation Strategy

### 3.1 Why Deprecate ~/.claude/agents/?

**Rationale**:
1. **Confusion**: Two deployment locations (user-level and project-level) cause confusion
2. **Version Conflicts**: User agents override project agents unpredictably
3. **Portability**: Project agents (`.claude-mpm/agents/`) are portable with the project
4. **Maintenance**: Simplifies deployment logic (3 tiers → 2 tiers + remote cache)
5. **Precedent**: Remote agents cached separately, not deployed to user location

### 3.2 Deprecation Timeline

**Phase 1: Soft Deprecation (Current Release)**
- Add warning logs when user agents detected
- Documentation update: "User-level agents deprecated, use project-level"
- `claude-mpm agents deploy --user` → Warning + deprecation notice

**Phase 2: Migration Tools (Next Release)**
- `claude-mpm agents migrate-to-project` command
- Auto-detect user agents and offer migration
- Copy user agents to `.claude-mpm/agents/` with version bump

**Phase 3: Hard Deprecation (2 Releases Later)**
- User agents no longer discovered by default
- `--include-user-agents` flag to opt-in
- Removal from `discover_agents_from_all_sources()` sources list

**Phase 4: Removal (3 Releases Later)**
- Complete removal of user-level agent support
- Cleanup utility: `claude-mpm agents cleanup-deprecated`

### 3.3 Migration Path

**User Action Required**:
```bash
# Step 1: List user agents
claude-mpm agents list --source user

# Step 2: Migrate to project
claude-mpm agents migrate-to-project

# Step 3: Verify migration
claude-mpm agents list --source project
```

**Automated Migration**:
```python
def migrate_user_agents_to_project():
    """Migrate user agents from ~/.claude-mpm/agents/ to .claude-mpm/agents/."""
    user_agents_dir = Path.home() / ".claude-mpm" / "agents"
    project_agents_dir = Path.cwd() / ".claude-mpm" / "agents"

    if not user_agents_dir.exists():
        return {"status": "no_user_agents"}

    project_agents_dir.mkdir(parents=True, exist_ok=True)
    migrated = []

    for agent_file in user_agents_dir.glob("*.json"):
        # Copy to project with version bump
        dest_file = project_agents_dir / agent_file.name
        if not dest_file.exists():
            shutil.copy(agent_file, dest_file)
            migrated.append(agent_file.stem)

    return {"status": "success", "migrated": migrated}
```

---

## 4. Proposed 4th Tier Integration

### 4.1 Architecture Changes

**Updated Discovery Method**:
```python
# File: multi_source_deployment_service.py
def discover_agents_from_all_sources(
    self,
    system_templates_dir: Optional[Path] = None,
    project_agents_dir: Optional[Path] = None,
    user_agents_dir: Optional[Path] = None,
    remote_agents_dir: Optional[Path] = None,  # ✅ NEW PARAMETER
    working_directory: Optional[Path] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Discover agents from all available sources including remote cache."""

    # Determine remote agents directory if not provided
    if not remote_agents_dir:
        remote_agents_dir = Path.home() / ".claude-mpm" / "cache" / "remote-agents"
        if not remote_agents_dir.exists():
            remote_agents_dir = None  # Skip if cache doesn't exist

    # Updated sources list with 4th tier
    sources = [
        ("system", system_templates_dir),    # Tier 1: Bundled system agents
        ("project", project_agents_dir),     # Tier 2: Project-specific agents
        ("user", user_agents_dir),           # Tier 3: User custom agents (deprecated)
        ("remote", remote_agents_dir),       # Tier 4: Remote GitHub agents ✅ NEW
    ]

    for source_name, source_dir in sources:
        if source_dir and source_dir.exists():
            # Handle different formats (JSON templates vs Markdown)
            if source_name == "remote":
                discovery_service = RemoteAgentDiscoveryService(source_dir)  # ✅ NEW
            else:
                discovery_service = AgentDiscoveryService(source_dir)

            agents = discovery_service.list_available_agents(log_discovery=False)

            for agent_info in agents:
                agent_name = agent_info.get("name")
                if not agent_name:
                    continue

                # Add source information
                agent_info["source"] = source_name
                agent_info["source_dir"] = str(source_dir)

                # Initialize list if first occurrence
                if agent_name not in agents_by_name:
                    agents_by_name[agent_name] = []

                agents_by_name[agent_name].append(agent_info)

    return agents_by_name
```

### 4.2 Remote Agent Discovery Service

**New Class**: `RemoteAgentDiscoveryService`
**File**: `/src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py`

```python
class RemoteAgentDiscoveryService:
    """Discovery service for remote agents in Markdown format.

    Handles discovery and metadata extraction from cached remote agents
    stored in ~/.claude-mpm/cache/remote-agents/.
    """

    def __init__(self, remote_agents_dir: Path):
        self.logger = get_logger(__name__)
        self.remote_agents_dir = remote_agents_dir

    def list_available_agents(self, log_discovery: bool = True) -> List[Dict[str, Any]]:
        """List all available remote agents with metadata.

        Returns:
            List of agent information dictionaries with:
            - name: Agent name
            - description: Extracted from frontmatter
            - version: Extracted from frontmatter
            - file_path: Path to .md file
            - format: "markdown" (vs "json" for templates)
        """
        agents = []

        if not self.remote_agents_dir.exists():
            self.logger.warning(f"Remote agents directory does not exist: {self.remote_agents_dir}")
            return agents

        # Find all Markdown files
        agent_files = list(self.remote_agents_dir.glob("*.md"))

        for agent_file in agent_files:
            try:
                agent_info = self._extract_agent_metadata_from_markdown(agent_file)
                if agent_info:
                    agents.append(agent_info)
            except Exception as e:
                self.logger.error(f"Failed to process remote agent {agent_file.name}: {e}")
                continue

        agents.sort(key=lambda x: x.get("name", ""))

        if log_discovery:
            self.logger.info(f"Discovered {len(agents)} remote agents from cache")

        return agents

    def _extract_agent_metadata_from_markdown(self, agent_file: Path) -> Optional[Dict[str, Any]]:
        """Extract metadata from agent markdown frontmatter.

        Expected frontmatter format:
        ---
        name: Research Agent
        version: 4.3.0
        description: Expert research analyst
        author: claude-mpm-community
        ---
        """
        try:
            content = agent_file.read_text(encoding="utf-8")

            # Parse YAML frontmatter
            metadata = self._parse_frontmatter(content)

            agent_info = {
                "name": metadata.get("name", agent_file.stem),
                "description": metadata.get("description", "No description available"),
                "version": metadata.get("version", "0.0.0"),
                "author": metadata.get("author", "unknown"),
                "format": "markdown",
                "file": agent_file.name,
                "path": str(agent_file),
                "file_path": str(agent_file),
                "size": agent_file.stat().st_size,
            }

            if not agent_info["name"]:
                self.logger.warning(f"Remote agent missing name: {agent_file.name}")
                return None

            return agent_info

        except Exception as e:
            self.logger.error(f"Failed to extract metadata from {agent_file.name}: {e}")
            return None

    def _parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """Parse YAML frontmatter from markdown content.

        Args:
            content: Markdown content with frontmatter

        Returns:
            Dictionary of frontmatter metadata
        """
        import yaml

        if not content.startswith("---"):
            return {}

        # Extract frontmatter between --- delimiters
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}

        frontmatter_yaml = parts[1].strip()

        try:
            return yaml.safe_load(frontmatter_yaml) or {}
        except yaml.YAMLError as e:
            self.logger.error(f"Failed to parse frontmatter YAML: {e}")
            return {}
```

### 4.3 Version Comparison Priority

**Updated Priority Logic**:
```python
# In select_highest_version_agents()
# Priority order (when versions are equal):
# 1. remote > project > user > system (highest version wins)
# 2. If same version: project > remote > user > system (project preferred for control)

def select_highest_version_agents(
    self, agents_by_name: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Dict[str, Any]]:
    """Select highest version agent with priority tie-breaking."""

    selected_agents = {}

    for agent_name, agent_versions in agents_by_name.items():
        if not agent_versions:
            continue

        highest_version_agent = None
        highest_version_tuple = (0, 0, 0)

        for agent_info in agent_versions:
            version_str = agent_info.get("version", "0.0.0")
            version_tuple = self.version_manager.parse_version(version_str)

            version_comparison = self.version_manager.compare_versions(
                version_tuple, highest_version_tuple
            )

            if version_comparison > 0:
                # Higher version wins
                highest_version_agent = agent_info
                highest_version_tuple = version_tuple
            elif version_comparison == 0:
                # Same version - apply priority tie-breaking
                current_source = agent_info["source"]
                highest_source = highest_version_agent["source"] if highest_version_agent else None

                if self._is_higher_priority_source(current_source, highest_source):
                    highest_version_agent = agent_info

        if highest_version_agent:
            selected_agents[agent_name] = highest_version_agent
            self.logger.info(
                f"Selected agent '{agent_name}' version {highest_version_agent['version']} "
                f"from {highest_version_agent['source']} source"
            )

    return selected_agents

def _is_higher_priority_source(self, source_a: str, source_b: str) -> bool:
    """Determine if source_a has higher priority than source_b.

    Priority order (for same versions):
    1. project (highest) - Local control
    2. remote           - Community updates
    3. user (deprecated) - User customization
    4. system (lowest)  - Fallback defaults
    """
    priority = {
        "project": 4,
        "remote": 3,
        "user": 2,
        "system": 1,
    }

    return priority.get(source_a, 0) > priority.get(source_b, 0)
```

### 4.4 Deployment Integration

**Updated get_agents_for_deployment()**:
```python
# File: multi_source_deployment_service.py
def get_agents_for_deployment(
    self,
    system_templates_dir: Optional[Path] = None,
    project_agents_dir: Optional[Path] = None,
    user_agents_dir: Optional[Path] = None,
    remote_agents_dir: Optional[Path] = None,  # ✅ NEW
    working_directory: Optional[Path] = None,
    excluded_agents: Optional[List[str]] = None,
    config: Optional[Config] = None,
    cleanup_outdated: bool = True,
) -> Tuple[Dict[str, Path], Dict[str, str], Dict[str, Any]]:
    """Get highest version agents from all sources for deployment.

    Now includes remote agents from cache in version comparison.
    """
    # Discover all available agents (including remote)
    agents_by_name = self.discover_agents_from_all_sources(
        system_templates_dir=system_templates_dir,
        project_agents_dir=project_agents_dir,
        user_agents_dir=user_agents_dir,
        remote_agents_dir=remote_agents_dir,  # ✅ NEW
        working_directory=working_directory,
    )

    # Select highest version for each agent (includes remote in comparison)
    selected_agents = self.select_highest_version_agents(agents_by_name)

    # Clean up outdated user agents if enabled
    cleanup_results = {"removed": [], "preserved": [], "errors": []}
    if cleanup_outdated:
        cleanup_results = self.cleanup_outdated_user_agents(
            agents_by_name, selected_agents
        )

    # Apply exclusion filters
    # ... (existing logic)

    # Create deployment mappings
    agents_to_deploy = {}
    agent_sources = {}

    for agent_name, agent_info in selected_agents.items():
        template_path = Path(agent_info["path"])
        if template_path.exists():
            file_stem = template_path.stem
            agents_to_deploy[file_stem] = template_path
            agent_sources[file_stem] = agent_info["source"]

            # Log remote agent selection
            if agent_info["source"] == "remote":
                self.logger.info(
                    f"Selected remote agent '{agent_name}' v{agent_info['version']} "
                    f"from GitHub cache"
                )

    self.logger.info(
        f"Selected {len(agents_to_deploy)} agents for deployment "
        f"(system: {sum(1 for s in agent_sources.values() if s == 'system')}, "
        f"project: {sum(1 for s in agent_sources.values() if s == 'project')}, "
        f"user: {sum(1 for s in agent_sources.values() if s == 'user')}, "
        f"remote: {sum(1 for s in agent_sources.values() if s == 'remote')})"  # ✅ NEW
    )

    return agents_to_deploy, agent_sources, cleanup_results
```

### 4.5 Caller Update

**File**: `/src/claude_mpm/services/agents/deployment/agent_deployment.py`

```python
# Line 766: Update get_agents_for_deployment() call
agents_to_deploy, agent_sources, cleanup_results = (
    self.multi_source_service.get_agents_for_deployment(
        system_templates_dir=system_templates_dir,
        project_agents_dir=project_agents_dir,
        user_agents_dir=user_agents_dir,
        remote_agents_dir=Path.home() / ".claude-mpm" / "cache" / "remote-agents",  # ✅ NEW
        working_directory=self.working_directory,
        excluded_agents=excluded_agents,
        config=config,
        cleanup_outdated=cleanup_outdated,
    )
)
```

---

## 5. Implementation Plan

### 5.1 Code Changes Required

**Phase 1: Remote Agent Discovery (2-3 hours)**

1. **Create RemoteAgentDiscoveryService**
   - File: `/src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py`
   - Methods:
     - `list_available_agents()` - Find `.md` files
     - `_extract_agent_metadata_from_markdown()` - Parse frontmatter
     - `_parse_frontmatter()` - YAML parsing
   - Dependencies: PyYAML

2. **Update MultiSourceAgentDeploymentService**
   - File: `/src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py`
   - Changes:
     - Add `remote_agents_dir` parameter to `discover_agents_from_all_sources()`
     - Add `("remote", remote_agents_dir)` to sources list
     - Add conditional discovery: `if source_name == "remote": RemoteAgentDiscoveryService()`
     - Add `remote` count to deployment summary logs

3. **Update get_agents_for_deployment()**
   - File: Same as above
   - Changes:
     - Add `remote_agents_dir` parameter
     - Pass to `discover_agents_from_all_sources()`
     - Update deployment summary to include remote count

**Phase 2: Deployment Integration (1-2 hours)**

4. **Update AgentDeploymentService caller**
   - File: `/src/claude_mpm/services/agents/deployment/agent_deployment.py`
   - Line: 766
   - Change: Add `remote_agents_dir=Path.home() / ".claude-mpm" / "cache" / "remote-agents"`

5. **Add remote agent format handling**
   - File: `/src/claude_mpm/services/agents/deployment/agent_template_builder.py`
   - Method: `build_agent_yaml()` or new `build_from_markdown()`
   - Logic: If `format == "markdown"`, use markdown directly (no JSON template conversion)

**Phase 3: Version Priority (1 hour)**

6. **Add source priority logic**
   - File: `/src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py`
   - Method: `_is_higher_priority_source(source_a, source_b)`
   - Priority: `project > remote > user > system`
   - Update: `select_highest_version_agents()` to use priority tie-breaking

**Phase 4: User-Level Deprecation (2-3 hours)**

7. **Add deprecation warnings**
   - File: `/src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py`
   - Method: `discover_agents_from_all_sources()`
   - Logic:
     ```python
     if user_agents_dir and user_agents_dir.exists():
         user_agent_files = list(user_agents_dir.glob("*.json"))
         if user_agent_files:
             self.logger.warning(
                 f"User-level agents detected at {user_agents_dir} - "
                 f"This location is deprecated. Please migrate to project-level "
                 f"(.claude-mpm/agents/) using 'claude-mpm agents migrate-to-project'"
             )
     ```

8. **Add migration command**
   - File: `/src/claude_mpm/cli/commands/agents_commands.py`
   - Command: `@agents_group.command("migrate-to-project")`
   - Implementation: Copy user agents to project with version bump

9. **Update documentation**
   - File: `/docs/agents/DEPLOYMENT.md`
   - Add: Deprecation notice for user-level agents
   - Add: Migration guide

**Phase 5: Testing (3-4 hours)**

10. **Unit tests**
    - Test: `test_remote_agent_discovery_service.py`
    - Test: `test_multi_source_with_remote.py`
    - Test: `test_version_priority_with_remote.py`
    - Coverage: 85%+ required

11. **Integration tests**
    - Test: `test_end_to_end_remote_deployment.py`
    - Test: `test_user_agent_migration.py`
    - Scenario: Remote agent newer than system → Remote deployed
    - Scenario: Project agent newer than remote → Project deployed

**Total Estimated Effort**: 10-14 hours

### 5.2 File Structure

```
/src/claude_mpm/services/agents/
├── deployment/
│   ├── multi_source_deployment_service.py  # ✏️ UPDATE: Add remote tier
│   ├── remote_agent_discovery_service.py    # ➕ NEW: Remote discovery
│   ├── agent_discovery_service.py           # ✅ Existing
│   └── agent_deployment.py                  # ✏️ UPDATE: Pass remote_agents_dir
├── sources/
│   ├── git_source_sync_service.py           # ✅ Working (no changes)
│   └── startup_sync.py                      # ✅ Working (no changes)
└── templates/                                # ✅ System agents (no changes)

/tests/services/agents/deployment/
├── test_remote_agent_discovery_service.py   # ➕ NEW: Discovery tests
├── test_multi_source_with_remote.py         # ➕ NEW: 4-tier integration
└── test_user_agent_migration.py             # ➕ NEW: Migration tests
```

### 5.3 Configuration Changes

**Add to Config** (if needed):
```yaml
# ~/.claude-mpm/config.yaml
agent_deployment:
  remote_agents_enabled: true  # Toggle remote agent discovery
  remote_agents_cache: "~/.claude-mpm/cache/remote-agents"  # Override default
  user_agents_deprecated_warning: true  # Show deprecation warnings

agent_sync:
  enabled: true  # Already exists
  sources:
    - id: github-remote
      url: https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main/agents
      enabled: true
```

---

## 6. Testing Strategy

### 6.1 Unit Tests

**Test: Remote Agent Discovery**
```python
# tests/services/agents/deployment/test_remote_agent_discovery_service.py
def test_discover_remote_agents_from_cache(tmp_path):
    """Test discovery of cached remote agents in Markdown format."""
    remote_cache = tmp_path / ".claude-mpm" / "cache" / "remote-agents"
    remote_cache.mkdir(parents=True)

    # Create mock remote agent
    agent_content = """---
name: Research Agent
version: 4.3.0
description: Expert research analyst
author: claude-mpm-community
---

You are an expert research analyst...
"""
    (remote_cache / "research.md").write_text(agent_content)

    # Discover agents
    service = RemoteAgentDiscoveryService(remote_cache)
    agents = service.list_available_agents()

    assert len(agents) == 1
    assert agents[0]["name"] == "Research Agent"
    assert agents[0]["version"] == "4.3.0"
    assert agents[0]["format"] == "markdown"
    assert agents[0]["source"] == "remote"  # Should be added by caller
```

**Test: 4-Tier Version Comparison**
```python
# tests/services/agents/deployment/test_multi_source_with_remote.py
def test_remote_agent_wins_when_highest_version(tmp_path):
    """Test that remote agent is selected when it has the highest version."""
    # Setup: 4 tiers with different versions
    system_dir = tmp_path / "system"
    project_dir = tmp_path / "project"
    user_dir = tmp_path / "user"
    remote_dir = tmp_path / "remote"

    for d in [system_dir, project_dir, user_dir, remote_dir]:
        d.mkdir(parents=True)

    # System: v4.0.0
    create_agent_template(system_dir / "research.json", version="4.0.0")

    # Project: v4.1.0
    create_agent_template(project_dir / "research.json", version="4.1.0")

    # User: v3.9.0
    create_agent_template(user_dir / "research.json", version="3.9.0")

    # Remote: v4.3.0 (HIGHEST)
    create_remote_agent(remote_dir / "research.md", version="4.3.0")

    # Discover and select
    service = MultiSourceAgentDeploymentService()
    agents_by_name = service.discover_agents_from_all_sources(
        system_templates_dir=system_dir,
        project_agents_dir=project_dir,
        user_agents_dir=user_dir,
        remote_agents_dir=remote_dir,
    )

    selected = service.select_highest_version_agents(agents_by_name)

    assert selected["research"]["version"] == "4.3.0"
    assert selected["research"]["source"] == "remote"
```

**Test: Source Priority Tie-Breaking**
```python
def test_project_wins_when_same_version_as_remote(tmp_path):
    """Test that project agent wins over remote when versions are equal."""
    project_dir = tmp_path / "project"
    remote_dir = tmp_path / "remote"

    project_dir.mkdir(parents=True)
    remote_dir.mkdir(parents=True)

    # Both have v4.2.0
    create_agent_template(project_dir / "research.json", version="4.2.0")
    create_remote_agent(remote_dir / "research.md", version="4.2.0")

    service = MultiSourceAgentDeploymentService()
    agents_by_name = service.discover_agents_from_all_sources(
        project_agents_dir=project_dir,
        remote_agents_dir=remote_dir,
    )

    selected = service.select_highest_version_agents(agents_by_name)

    # Project should win due to priority
    assert selected["research"]["version"] == "4.2.0"
    assert selected["research"]["source"] == "project"
```

### 6.2 Integration Tests

**Test: End-to-End Remote Deployment**
```python
# tests/integration/test_end_to_end_remote_deployment.py
def test_remote_agent_deployed_to_claude_agents(tmp_path):
    """Test that remote agent is discovered, compared, and deployed."""
    # Setup directories
    system_dir = tmp_path / "system"
    remote_dir = tmp_path / ".claude-mpm" / "cache" / "remote-agents"
    deploy_dir = tmp_path / ".claude" / "agents"

    system_dir.mkdir(parents=True)
    remote_dir.mkdir(parents=True)

    # System agent: v4.0.0
    create_agent_template(system_dir / "research.json", version="4.0.0")

    # Remote agent: v4.3.0 (higher)
    create_remote_agent(remote_dir / "research.md", version="4.3.0")

    # Deploy agents
    deployment_service = AgentDeploymentService(
        templates_dir=system_dir,
        working_directory=tmp_path,
    )

    results = deployment_service.deploy_agents(target_dir=deploy_dir)

    # Verify remote agent deployed
    assert (deploy_dir / "research.md").exists()
    deployed_content = (deploy_dir / "research.md").read_text()
    assert "version: 4.3.0" in deployed_content

    # Verify results tracking
    assert "remote" in results.get("agent_sources", {}).values()
```

### 6.3 Test Coverage Goals

- **Unit Tests**: 85%+ coverage
- **Integration Tests**: Critical paths covered
- **Edge Cases**:
  - Remote cache doesn't exist → Skip gracefully
  - Remote agent missing frontmatter → Skip with warning
  - Remote agent invalid YAML → Skip with error log
  - All sources have same version → Project wins
  - Remote agent format incompatible → Fallback to system

---

## 7. Rollout Plan

### 7.1 Phase 1: Foundation (Week 1)

**Goals**:
- Remote agent discovery working
- 4-tier integration complete
- Version comparison includes remote

**Deliverables**:
- `RemoteAgentDiscoveryService` implemented
- `MultiSourceAgentDeploymentService` updated with 4th tier
- Unit tests passing (85%+ coverage)

**Validation**:
```bash
# Test remote agent discovery
claude-mpm agents list --source remote

# Expected output:
# Remote Agents (from GitHub cache):
# - research (v4.3.0)
# - engineer (v3.8.0)
# - qa (v3.5.0)
# ...
```

### 7.2 Phase 2: Deployment (Week 2)

**Goals**:
- Remote agents deployed to `.claude/agents/`
- Version priority working
- Integration tests passing

**Deliverables**:
- `AgentDeploymentService` updated with remote_agents_dir
- Format conversion (if needed) for markdown agents
- End-to-end deployment tests

**Validation**:
```bash
# Deploy agents
claude-mpm agents deploy

# Expected log output:
# [INFO] Discovered 10 remote agents from cache
# [INFO] Selected agent 'research' version 4.3.0 from remote source
# [INFO] Deployed 3 remote agents, 5 system agents, 2 project agents
```

### 7.3 Phase 3: Deprecation (Week 3)

**Goals**:
- User-level deprecation warnings
- Migration tooling ready
- Documentation updated

**Deliverables**:
- Deprecation warnings in logs
- `claude-mpm agents migrate-to-project` command
- Migration guide in docs

**Validation**:
```bash
# Trigger deprecation warning
claude-mpm agents deploy  # With user agents present

# Expected log:
# [WARNING] User-level agents detected at ~/.claude-mpm/agents/ -
#           This location is deprecated. Please migrate to project-level
#           (.claude-mpm/agents/) using 'claude-mpm agents migrate-to-project'

# Test migration
claude-mpm agents migrate-to-project

# Expected output:
# Migrated 3 user agents to project:
# - research (v3.9.0 → v4.0.0)
# - custom-qa (v1.0.0 → v1.1.0)
# - my-agent (v0.1.0 → v0.2.0)
```

### 7.4 Phase 4: Monitoring (Week 4+)

**Goals**:
- Monitor remote agent adoption
- Track deployment success rates
- Gather user feedback

**Metrics to Track**:
- % of deployments using remote agents
- Remote agent version distribution
- User agent migration rate
- Deployment errors by source

---

## 8. Migration Guide for Users

### 8.1 For Users with User-Level Agents

**Scenario**: You have custom agents in `~/.claude-mpm/agents/`

**Action Required**:
```bash
# Step 1: List your user agents
claude-mpm agents list --source user

# Step 2: Migrate to project-level
cd /path/to/your/project
claude-mpm agents migrate-to-project

# Step 3: Verify migration
claude-mpm agents list --source project

# Step 4: (Optional) Remove old user agents
rm -rf ~/.claude-mpm/agents/
```

**Timeline**:
- **Now**: Soft deprecation (warnings only)
- **2 releases later**: Hard deprecation (not discovered by default)
- **3 releases later**: Complete removal

### 8.2 For Users with No User-Level Agents

**Scenario**: You only use system/project agents

**Action Required**: ✅ **None** - Remote agents will automatically be discovered and deployed when available.

**Benefits**:
- Get latest community agent updates automatically
- Higher version remote agents override outdated system agents
- No manual intervention needed

---

## 9. Risk Analysis

### 9.1 Risks

**HIGH: Format Incompatibility**
- **Risk**: Remote agents in Markdown format may be incompatible with JSON-based deployment
- **Mitigation**:
  - Create `RemoteAgentDiscoveryService` to handle Markdown parsing
  - Test format conversion thoroughly
  - Fallback to system agent if remote agent format fails

**MEDIUM: Version Conflicts**
- **Risk**: Remote agents may have incorrect version metadata
- **Mitigation**:
  - Validate version format during discovery
  - Log version comparison decisions clearly
  - Provide `--force-source` flag to override

**MEDIUM: User Disruption**
- **Risk**: User-level deprecation may break existing workflows
- **Mitigation**:
  - Phased rollout with clear warnings
  - Automated migration tooling
  - Preserve backward compatibility for 3 releases

**LOW: Performance Degradation**
- **Risk**: 4-tier discovery may slow down deployment
- **Mitigation**:
  - Cache discovery results
  - Parallelize source discovery
  - Skip remote tier if cache doesn't exist

### 9.2 Rollback Plan

**If remote agents cause issues**:
```bash
# Disable remote agent discovery
export CLAUDE_MPM_REMOTE_AGENTS_ENABLED=false
claude-mpm agents deploy

# OR edit config
# ~/.claude-mpm/config.yaml
agent_deployment:
  remote_agents_enabled: false
```

**If user migration fails**:
```bash
# Restore user agents from backup
cp -r ~/.claude-mpm/agents.backup ~/.claude-mpm/agents

# Deploy with user agents
claude-mpm agents deploy --include-user-agents
```

---

## 10. Success Criteria

### 10.1 Functional Requirements

- ✅ Remote agents discovered from `~/.claude-mpm/cache/remote-agents/`
- ✅ Remote agents compared in 4-tier version system
- ✅ Highest version agent deployed (regardless of source)
- ✅ Source priority tie-breaking works (project > remote > user > system)
- ✅ User-level agents marked deprecated with warnings
- ✅ Migration command works for user → project migration

### 10.2 Non-Functional Requirements

- ✅ No performance regression (<5% deployment time increase)
- ✅ 85%+ test coverage for new code
- ✅ Zero breaking changes for users without user-level agents
- ✅ Clear deprecation warnings with actionable guidance
- ✅ Comprehensive documentation and migration guide

### 10.3 Acceptance Tests

1. **Remote agent deployed when highest version**
   ```bash
   # Given: Remote research.md v4.3.0, System research.json v4.0.0
   claude-mpm agents deploy
   # Then: research.md v4.3.0 deployed to .claude/agents/
   ```

2. **Project agent wins over remote when same version**
   ```bash
   # Given: Project research.json v4.2.0, Remote research.md v4.2.0
   claude-mpm agents deploy
   # Then: Project research.json v4.2.0 deployed (priority)
   ```

3. **User agent migration succeeds**
   ```bash
   # Given: User agent custom.json in ~/.claude-mpm/agents/
   claude-mpm agents migrate-to-project
   # Then: custom.json copied to .claude-mpm/agents/ with version bump
   ```

4. **Deprecation warning shown**
   ```bash
   # Given: User agents exist in ~/.claude-mpm/agents/
   claude-mpm agents deploy
   # Then: Warning logged about deprecation
   ```

---

## 11. Appendix

### 11.1 Code Snippets

**Current discover_agents_from_all_sources() (Lines 44-119)**:
```python
def discover_agents_from_all_sources(
    self,
    system_templates_dir: Optional[Path] = None,
    project_agents_dir: Optional[Path] = None,
    user_agents_dir: Optional[Path] = None,  # No remote_agents_dir ❌
    working_directory: Optional[Path] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    sources = [
        ("system", system_templates_dir),
        ("project", project_agents_dir),
        ("user", user_agents_dir),
        # Missing: ("remote", remote_agents_dir) ❌
    ]
```

**Current deployment call (Line 766)**:
```python
agents_to_deploy, agent_sources, cleanup_results = (
    self.multi_source_service.get_agents_for_deployment(
        system_templates_dir=system_templates_dir,
        project_agents_dir=project_agents_dir,
        user_agents_dir=user_agents_dir,
        # Missing: remote_agents_dir=... ❌
        working_directory=self.working_directory,
        excluded_agents=excluded_agents,
        config=config,
        cleanup_outdated=cleanup_outdated,
    )
)
```

### 11.2 Related Files

**Agent Sync System**:
- `/src/claude_mpm/services/agents/sources/git_source_sync_service.py` - Remote sync ✅
- `/src/claude_mpm/services/agents/startup_sync.py` - Startup integration ✅
- `/src/claude_mpm/services/agents/sources/agent_sync_state.py` - SQLite tracking ✅

**Agent Discovery & Deployment**:
- `/src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py` - ✏️ UPDATE
- `/src/claude_mpm/services/agents/deployment/agent_discovery_service.py` - ✅ Reference
- `/src/claude_mpm/services/agents/deployment/agent_deployment.py` - ✏️ UPDATE

**Version Management**:
- `/src/claude_mpm/services/agents/deployment/agent_version_manager.py` - ✅ Working

### 11.3 File Locations

**Remote Agent Cache**:
```
~/.claude-mpm/cache/remote-agents/
├── documentation.md (13 KB)
├── engineer.md (4 KB)
├── ops.md (9 KB)
├── product_owner.md (33 KB)
├── project_organizer.md (9 KB)
├── qa.md (8 KB)
├── research.md (47 KB) ← Example: v4.3.0 never deployed
├── security.md (25 KB)
├── ticketing.md (50 KB)
└── version_control.md (19 KB)
```

**System Agent Templates**:
```
/src/claude_mpm/agents/templates/
├── research.json ← Example: v4.1.0 currently deployed
├── engineer.json
├── qa.json
└── ...
```

**Deployment Target** (doesn't exist yet):
```
~/.claude/agents/
├── research.md ← Should be v4.3.0 from remote cache
└── ...
```

### 11.4 Key Metrics

**Cache Statistics**:
- Remote agents cached: 10
- Total cache size: 240 KB
- Last sync: 2025-11-30 10:14 (ETag-based)

**Deployment Gap**:
- Remote agents discovered: 0 ❌
- Remote agents deployed: 0 ❌
- Remote agent deployment rate: 0% ❌

**Expected After Fix**:
- Remote agents discovered: 10 ✅
- Remote agents deployed: ~5-8 (higher versions) ✅
- Remote agent deployment rate: 50-80% ✅

---

## Conclusion

The remote agent caching system is **fully functional** but **completely disconnected** from the deployment pipeline. The fix requires integrating the `~/.claude-mpm/cache/remote-agents/` directory as a **4th tier** in the agent discovery system.

**Priority**: HIGH
**Complexity**: MEDIUM
**Estimated Effort**: 10-14 hours
**Risk Level**: LOW (non-breaking change with fallbacks)

The proposed solution maintains backward compatibility, provides clear deprecation paths for user-level agents, and enables seamless remote agent deployment with proper version management.

**Next Steps**:
1. Implement `RemoteAgentDiscoveryService` for Markdown parsing
2. Update `MultiSourceAgentDeploymentService` with 4th tier
3. Add source priority tie-breaking logic
4. Integrate remote_agents_dir into deployment caller
5. Add deprecation warnings for user-level agents
6. Implement migration command
7. Comprehensive testing (unit + integration)
8. Documentation updates

---

**Research Completed**: 2025-11-30
**Document Version**: 1.0
**Author**: Claude Code Research Agent
**Status**: Ready for Implementation
