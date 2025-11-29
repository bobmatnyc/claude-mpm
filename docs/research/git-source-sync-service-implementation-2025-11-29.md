# GitSourceSyncService Implementation Research

**Research Date:** 2025-11-29
**Ticket:** 1M-387 - Implement GitSourceSyncService with single-source support
**Parent Epic:** 1M-382 - Migrate Agent System to Git-Based Markdown Repository
**Researcher:** Claude Research Agent

---

## Executive Summary

This research provides comprehensive technical guidance for implementing `GitSourceSyncService`, a new service to sync agent templates from a remote Git repository (initially GitHub). The service will download agent markdown files from `https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main/{file}.md`, cache them locally, and integrate with the existing multi-source agent deployment system.

**Key Findings:**
- ✅ `requests` library already available (v2.25.0+) - no new dependencies needed
- ✅ Existing GitHub API integration patterns found in `scripts/download_skills_api.py`
- ✅ Multi-source deployment infrastructure exists and is mature
- ✅ Cache directory structure defined via `UnifiedPathManager`
- ✅ Clear integration point: Add as fourth source to `MultiSourceAgentDeploymentService`

**Recommended Implementation Path:**
1. Create `src/claude_mpm/services/agents/sources/git_source_sync_service.py`
2. Use `requests` library with ETag caching for efficient downloads
3. Cache downloaded agents in `~/.claude-mpm/cache/remote-agents/`
4. Integrate with existing `MultiSourceAgentDeploymentService` as new source tier
5. Store sync metadata in `~/.claude-mpm/config/git-sources.json`

---

## 1. Current Agent System Architecture

### 1.1 Agent Template Storage

**Current Structure:**
```
/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/
├── research.json          # JSON templates (legacy format)
├── engineer.json
├── qa.json
└── ... (39 total agent templates)
```

**Key Characteristics:**
- **Format:** JSON templates with schema version 1.3.0
- **Version:** Agents have `agent_version` (e.g., "4.9.0") and `template_version` (e.g., "2.9.0")
- **Metadata:** Each template includes `agent_id`, `metadata`, `capabilities`, `instructions`
- **Base Agent:** `base_agent.json` contains shared configuration for all agents

**Template Structure Example (research.json):**
```json
{
  "schema_version": "1.3.0",
  "agent_id": "research-agent",
  "agent_version": "4.9.0",
  "template_version": "2.9.0",
  "metadata": {
    "name": "Research Agent",
    "description": "...",
    "category": "analysis"
  },
  "capabilities": {
    "tools": ["*"],
    "features": ["vector_search", "ticketing"]
  },
  "instructions": "..."
}
```

### 1.2 Agent Loading Flow

**Discovery → Build → Deploy Pipeline:**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. DISCOVERY PHASE                                          │
│    AgentDiscoveryService.list_available_agents()            │
│    • Scans templates directory for *.json files             │
│    • Extracts agent metadata (name, version, description)   │
│    • Returns list of available agents                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. VERSION CHECKING                                         │
│    AgentVersionManager.compare_versions()                   │
│    • Compares template version with deployed version        │
│    • Determines if update needed                            │
│    • Tracks version history                                 │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. TEMPLATE BUILDING                                        │
│    AgentTemplateBuilder.build_agent_markdown()              │
│    • Loads JSON template                                    │
│    • Merges with base_agent.json                            │
│    • Converts to Markdown format with YAML frontmatter     │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. DEPLOYMENT                                               │
│    AgentDeploymentService.deploy_agents()                   │
│    • Writes agent .md files to ~/.claude/agents/            │
│    • Updates deployment metadata                            │
│    • Tracks deployment results                              │
└─────────────────────────────────────────────────────────────┘
```

**Key Files:**
- **Discovery:** `src/claude_mpm/services/agents/deployment/agent_discovery_service.py`
- **Deployment:** `src/claude_mpm/services/agents/deployment/agent_deployment.py`
- **Template Building:** `src/claude_mpm/services/agents/deployment/agent_template_builder.py`
- **Version Management:** `src/claude_mpm/services/agents/deployment/agent_version_manager.py`

### 1.3 Multi-Source Agent System

**Architecture Breakthrough:** The system already supports multiple agent sources!

**Current Sources (3 tiers):**
```python
# From MultiSourceAgentDeploymentService.discover_agents_from_all_sources()

sources = [
    ("system", system_templates_dir),      # /src/claude_mpm/agents/templates/
    ("project", project_agents_dir),       # .claude-mpm/agents/
    ("user", user_agents_dir),            # ~/.claude-mpm/agents/
]
```

**Version Precedence Logic:**
```python
# Service compares versions across all sources
# Deploys HIGHEST version regardless of source tier
# Example: If user agent v2.0.0 > system agent v1.5.0 → deploy user agent
```

**Integration Point for GitSourceSyncService:**
```python
sources = [
    ("system", system_templates_dir),
    ("project", project_agents_dir),
    ("user", user_agents_dir),
    ("remote-git", remote_git_cache_dir),  # ← NEW: Add as 4th source
]
```

**File:** `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py`

---

## 2. Existing GitHub Integration Patterns

### 2.1 GitHub API Client Implementation

**Reference Implementation:** `scripts/download_skills_api.py`

**Key Patterns Found:**

```python
class GitHubAPIDownloader:
    def __init__(self, github_token: Optional[str] = None) -> None:
        """Initialize downloader with optional GitHub token."""
        self.github_token: Optional[str] = github_token
        self.session: requests.Session = requests.Session()
        if github_token:
            self.session.headers["Authorization"] = f"token {github_token}"
        self.session.headers["Accept"] = "application/vnd.github.v3+json"
        self.rate_limit_remaining: Optional[int] = None
        self.rate_limit_reset: Optional[int] = None

    def download_file(self, owner: str, repo: str, path: str, branch: str = "main") -> Optional[bytes]:
        """Download a single file from GitHub."""
        self.wait_for_rate_limit()

        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": branch}

        response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)

        # Update rate limit info
        self.rate_limit_remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
        self.rate_limit_reset = int(response.headers.get("X-RateLimit-Reset", 0))

        response.raise_for_status()
        data = response.json()

        # Decode base64 content
        if "content" in data:
            return base64.b64decode(data["content"])
```

**Rate Limiting:**
```python
def wait_for_rate_limit(self) -> None:
    """Wait if rate limit is exhausted."""
    if self.rate_limit_remaining is not None and self.rate_limit_remaining < 5:
        if self.rate_limit_reset:
            wait_time = self.rate_limit_reset - time.time()
            if wait_time > 0:
                logger.warning(f"Rate limit low ({self.rate_limit_remaining} remaining). "
                              f"Waiting {int(wait_time)}s...")
                time.sleep(wait_time + 1)
```

### 2.2 GitHub Token Validation

**Reference:** `src/claude_mpm/core/api_validator.py`

```python
def _validate_github_token(self, token: str) -> bool:
    """Validate GitHub personal access token."""
    try:
        response = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=10,
        )

        if response.status_code == 401:
            self.errors.append("❌ GitHub token is invalid (401 Unauthorized)")
            return False
        if response.status_code == 403:
            self.errors.append("❌ GitHub token lacks required permissions (403 Forbidden)")
            return False
        if response.status_code == 200:
            self.logger.debug("✅ GitHub token validated successfully")
            return True
```

### 2.3 HTTP Library: requests

**Already Available:** `requests>=2.25.0` (from pyproject.toml)

**No Additional Dependencies Required!**

```toml
dependencies = [
    "requests>=2.25.0",
    "aiohttp>=3.9.0",  # Already available for async operations
    # ... other deps
]
```

**Decision:** Use `requests` for synchronous operations (simpler, proven pattern in codebase)

---

## 3. Technical Implementation Guidance

### 3.1 Service Architecture

**Recommended Location:**
```
src/claude_mpm/services/agents/sources/
├── __init__.py
├── git_source_sync_service.py       ← NEW: Main service
├── git_source_config.py             ← NEW: Configuration model
└── git_source_cache_manager.py      ← NEW: Cache management
```

**Service Design:**

```python
# Proposed API Design

class GitSourceSyncService:
    """Service for syncing agent templates from remote Git repositories.

    Features:
    - Downloads agent .md files from GitHub raw URLs
    - Caches files locally with ETag support
    - Integrates with multi-source deployment system
    - Handles network errors gracefully
    """

    def __init__(
        self,
        source_url: str,
        cache_dir: Optional[Path] = None,
        github_token: Optional[str] = None,
    ):
        """Initialize Git source sync service.

        Args:
            source_url: Base URL for raw files (e.g., https://raw.githubusercontent.com/owner/repo/main)
            cache_dir: Local cache directory (defaults to ~/.claude-mpm/cache/remote-agents/)
            github_token: Optional GitHub token for private repos or higher rate limits
        """
        pass

    def sync_agents(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Sync agents from remote Git repository.

        Args:
            force_refresh: Force download even if cache is fresh

        Returns:
            Dictionary with sync results:
            - downloaded: List of downloaded agents
            - cached: List of agents served from cache
            - failed: List of failed downloads
            - etags: Mapping of file to ETag for next sync
        """
        pass

    def get_cached_agents_dir(self) -> Path:
        """Get directory containing cached agent files.

        Returns:
            Path to cache directory for integration with MultiSourceAgentDeploymentService
        """
        pass

    def check_for_updates(self) -> List[str]:
        """Check which agents have updates without downloading.

        Uses ETag headers to efficiently check for changes.

        Returns:
            List of agent names with available updates
        """
        pass
```

### 3.2 Cache Directory Structure

**Recommended Structure:**
```
~/.claude-mpm/
├── cache/
│   └── remote-agents/
│       ├── github-bobmatnyc-claude-mpm-agents/    # Source identifier
│       │   ├── research.md                         # Cached agent files
│       │   ├── engineer.md
│       │   ├── qa.md
│       │   └── .etags.json                        # ETag cache
│       └── .sync-metadata.json                    # Last sync timestamps
├── config/
│   └── git-sources.json                           # Git source configuration
```

**ETag Cache Structure (.etags.json):**
```json
{
  "research.md": {
    "etag": "\"abc123def456\"",
    "last_modified": "2025-11-29T10:30:00Z",
    "file_size": 52340
  },
  "engineer.md": {
    "etag": "\"xyz789uvw\"",
    "last_modified": "2025-11-28T14:20:00Z",
    "file_size": 48230
  }
}
```

**Sync Metadata (.sync-metadata.json):**
```json
{
  "sources": {
    "github-bobmatnyc-claude-mpm-agents": {
      "url": "https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main",
      "last_sync": "2025-11-29T15:45:00Z",
      "sync_count": 42,
      "agent_count": 12,
      "last_error": null
    }
  }
}
```

### 3.3 ETag Implementation

**HTTP Request with ETag:**
```python
def download_agent_with_etag(
    self,
    agent_name: str,
    cached_etag: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """Download agent file with ETag support.

    Args:
        agent_name: Name of agent (e.g., "research")
        cached_etag: ETag from previous download

    Returns:
        Tuple of (content, new_etag) or (None, cached_etag) if not modified
    """
    url = f"{self.source_url}/{agent_name}.md"
    headers = {}

    if cached_etag:
        headers["If-None-Match"] = cached_etag

    response = self.session.get(url, headers=headers, timeout=30)

    if response.status_code == 304:
        # Not modified - use cached version
        self.logger.debug(f"Agent {agent_name} not modified (304)")
        return None, cached_etag

    if response.status_code == 200:
        # New content available
        new_etag = response.headers.get("ETag")
        content = response.text
        self.logger.info(f"Downloaded updated agent {agent_name} (ETag: {new_etag})")
        return content, new_etag

    response.raise_for_status()
```

**Benefits:**
- ✅ Efficient: Only downloads changed files
- ✅ Bandwidth-friendly: 304 responses are tiny
- ✅ Fast: No parsing needed for unchanged files
- ✅ Standard: GitHub raw URLs support ETags

### 3.4 Configuration Integration

**Git Source Configuration (git-sources.json):**
```json
{
  "sources": [
    {
      "id": "claude-mpm-agents",
      "enabled": true,
      "url": "https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main",
      "branch": "main",
      "sync_interval_hours": 24,
      "require_token": false,
      "priority": 100
    }
  ],
  "global_settings": {
    "auto_sync_on_startup": false,
    "cache_ttl_hours": 168,
    "network_timeout_seconds": 30
  }
}
```

**Loading Configuration:**
```python
from claude_mpm.core.config import Config
from claude_mpm.core.unified_paths import get_path_manager

class GitSourceConfig:
    """Configuration for Git source sync."""

    def __init__(self):
        self.config = Config()
        self.path_manager = get_path_manager()

        # Load from ~/.claude-mpm/config/git-sources.json
        config_path = self.path_manager.get_config_dir("user") / "git-sources.json"

        if config_path.exists():
            with config_path.open() as f:
                self.data = json.load(f)
        else:
            self.data = self._get_default_config()
            self._save_config(config_path)
```

### 3.5 Error Handling Strategy

**Error Categories:**

1. **Network Errors:**
```python
try:
    response = self.session.get(url, timeout=30)
except requests.exceptions.Timeout:
    self.logger.warning(f"Timeout downloading {agent_name}, using cache")
    return self._load_from_cache(agent_name)
except requests.exceptions.ConnectionError:
    self.logger.error(f"Connection error for {agent_name}, offline mode")
    return self._load_from_cache(agent_name)
```

2. **HTTP Errors:**
```python
if response.status_code == 404:
    self.logger.warning(f"Agent {agent_name} not found in remote repository")
    # Remove from cache if exists
    self._remove_from_cache(agent_name)
    return None
elif response.status_code == 403:
    self.logger.error(f"Access forbidden - check GitHub token permissions")
    return self._load_from_cache(agent_name)
```

3. **Cache Fallback:**
```python
def _load_from_cache(self, agent_name: str) -> Optional[str]:
    """Load agent from cache when network unavailable."""
    cache_file = self.cache_dir / f"{agent_name}.md"

    if cache_file.exists():
        self.logger.info(f"Using cached version of {agent_name}")
        return cache_file.read_text()

    self.logger.error(f"No cached version available for {agent_name}")
    return None
```

**Graceful Degradation:**
- ✅ Network down → Use cached versions
- ✅ 404 → Remove from cache, skip deployment
- ✅ Rate limited → Wait and retry
- ✅ Parse error → Log and skip, don't fail entire sync

---

## 4. Integration Points

### 4.1 Integration with MultiSourceAgentDeploymentService

**Current Code Location:**
```
src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py
```

**Modification Required:**

```python
# BEFORE (current 3-source system):
sources = [
    ("system", system_templates_dir),
    ("project", project_agents_dir),
    ("user", user_agents_dir),
]

# AFTER (4-source system with Git sync):
sources = [
    ("system", system_templates_dir),
    ("project", project_agents_dir),
    ("user", user_agents_dir),
    ("remote-git", self._get_remote_git_cache_dir()),  # NEW
]

def _get_remote_git_cache_dir(self) -> Optional[Path]:
    """Get remote Git cache directory if sync is enabled.

    Returns:
        Path to cached remote agents or None if sync disabled
    """
    from claude_mpm.services.agents.sources import GitSourceSyncService

    config = Config()
    git_sync_config = config.get("git_sync", {})

    if not git_sync_config.get("enabled", False):
        return None

    # Check if we should sync now
    sync_service = GitSourceSyncService(
        source_url=git_sync_config.get("source_url"),
        github_token=os.getenv("GITHUB_TOKEN"),
    )

    # Sync if needed (with caching to avoid repeated syncs)
    if self._should_sync(sync_service):
        sync_service.sync_agents()

    return sync_service.get_cached_agents_dir()
```

**Agent Discovery Flow (Updated):**

```
User runs: claude-mpm agents deploy

    ↓

AgentDeploymentService.deploy_agents()
    │
    ├─→ MultiSourceAgentDeploymentService.discover_agents_from_all_sources()
    │       │
    │       ├─→ Scan: src/claude_mpm/agents/templates/     (SYSTEM tier)
    │       ├─→ Scan: .claude-mpm/agents/                  (PROJECT tier)
    │       ├─→ Scan: ~/.claude-mpm/agents/                (USER tier)
    │       └─→ Scan: ~/.claude-mpm/cache/remote-agents/   (REMOTE-GIT tier) ← NEW
    │
    ├─→ Compare versions across all 4 sources
    │
    ├─→ Select highest version for each agent
    │
    └─→ Deploy to ~/.claude/agents/
```

### 4.2 CLI Integration

**New Command:**
```bash
# Sync agents from remote Git repository
claude-mpm agents sync [--force] [--source <source-id>]

# Check for updates without downloading
claude-mpm agents sync --check-only

# Configure Git sync
claude-mpm agents config git-sync --enable --url <github-url>
```

**CLI Handler Location:**
```
src/claude_mpm/cli/commands/agents.py  (extend existing agent commands)
```

**Example Implementation:**
```python
@click.command("sync")
@click.option("--force", is_flag=True, help="Force refresh even if cache is fresh")
@click.option("--check-only", is_flag=True, help="Check for updates without downloading")
def sync_agents(force: bool, check_only: bool):
    """Sync agents from remote Git repository."""
    from claude_mpm.services.agents.sources import GitSourceSyncService

    config = Config()
    git_config = config.get("git_sync", {})

    if not git_config.get("enabled", False):
        click.echo("❌ Git sync is not enabled. Run: claude-mpm agents config git-sync --enable")
        return

    sync_service = GitSourceSyncService(
        source_url=git_config.get("source_url"),
        github_token=os.getenv("GITHUB_TOKEN"),
    )

    if check_only:
        updates = sync_service.check_for_updates()
        if updates:
            click.echo(f"✨ {len(updates)} agents have updates:")
            for agent in updates:
                click.echo(f"  - {agent}")
        else:
            click.echo("✅ All agents are up to date")
    else:
        results = sync_service.sync_agents(force_refresh=force)
        click.echo(f"✅ Synced {len(results['downloaded'])} agents")
        if results['cached']:
            click.echo(f"⚡ {len(results['cached'])} agents served from cache")
        if results['failed']:
            click.echo(f"⚠️  {len(results['failed'])} agents failed to sync")
```

### 4.3 Startup Integration (Optional)

**Auto-sync on startup (if configured):**

```python
# Location: src/claude_mpm/cli/startup.py

def check_git_sync_on_startup():
    """Check and sync Git agents if enabled."""
    from claude_mpm.core.config import Config
    from claude_mpm.services.agents.sources import GitSourceSyncService

    config = Config()
    git_config = config.get("git_sync", {})

    if not git_config.get("auto_sync_on_startup", False):
        return

    try:
        sync_service = GitSourceSyncService(
            source_url=git_config.get("source_url"),
            github_token=os.getenv("GITHUB_TOKEN"),
        )

        # Background sync (non-blocking)
        import threading
        sync_thread = threading.Thread(
            target=sync_service.sync_agents,
            daemon=True
        )
        sync_thread.start()

    except Exception as e:
        logger.debug(f"Git sync failed on startup (non-critical): {e}")
```

---

## 5. Implementation Recommendations

### 5.1 Development Phases

**Phase 1: Core Service (1M-387 - Current Ticket)**
- ✅ Create `GitSourceSyncService` class
- ✅ Implement single GitHub source sync
- ✅ Add ETag-based caching
- ✅ Basic error handling with cache fallback
- ✅ Unit tests for sync logic

**Phase 2: Integration (Follow-up Ticket)**
- ✅ Integrate with `MultiSourceAgentDeploymentService`
- ✅ Add CLI commands (`claude-mpm agents sync`)
- ✅ Configuration management
- ✅ Integration tests

**Phase 3: Advanced Features (Future)**
- ✅ Multiple Git sources support
- ✅ Auto-sync on schedule
- ✅ Private repository support
- ✅ Conflict resolution UI

### 5.2 File Structure

**Recommended Files to Create:**

```
src/claude_mpm/services/agents/sources/
├── __init__.py                          # Export GitSourceSyncService
├── git_source_sync_service.py           # Main service (200-300 lines)
├── git_source_config.py                 # Configuration model (100 lines)
├── git_source_cache_manager.py          # Cache & ETag management (150 lines)
└── exceptions.py                        # Custom exceptions

tests/services/agents/sources/
├── test_git_source_sync_service.py      # Main service tests
├── test_git_source_cache_manager.py     # Cache tests
└── fixtures/
    └── sample_agents/                   # Test agent files
```

### 5.3 Testing Strategy

**Unit Tests:**
```python
# tests/services/agents/sources/test_git_source_sync_service.py

def test_sync_agents_with_etag_cache(tmp_path):
    """Test that ETag caching prevents unnecessary downloads."""
    service = GitSourceSyncService(
        source_url="https://raw.githubusercontent.com/test/repo/main",
        cache_dir=tmp_path
    )

    # First sync - should download
    with mock.patch('requests.Session.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "# Research Agent\n..."
        mock_get.return_value.headers = {"ETag": '"abc123"'}

        results = service.sync_agents()
        assert len(results['downloaded']) == 1
        assert mock_get.call_count == 1

    # Second sync - should use ETag, get 304
    with mock.patch('requests.Session.get') as mock_get:
        mock_get.return_value.status_code = 304

        results = service.sync_agents()
        assert len(results['cached']) == 1
        assert mock_get.call_args[1]['headers']['If-None-Match'] == '"abc123"'

def test_network_error_fallback_to_cache(tmp_path):
    """Test graceful degradation when network unavailable."""
    # Pre-populate cache
    cache_file = tmp_path / "research.md"
    cache_file.write_text("# Cached Agent")

    service = GitSourceSyncService(
        source_url="https://raw.githubusercontent.com/test/repo/main",
        cache_dir=tmp_path
    )

    # Simulate network error
    with mock.patch('requests.Session.get', side_effect=requests.exceptions.ConnectionError):
        results = service.sync_agents()
        assert len(results['cached']) == 1
        assert len(results['failed']) == 0  # Used cache, not failed
```

**Integration Tests:**
```python
# tests/integration/test_multi_source_with_git_sync.py

def test_git_source_integrated_with_multi_source_deployment():
    """Test that Git synced agents integrate with multi-source system."""
    # Setup: Create mock Git cache
    # Act: Run multi-source discovery
    # Assert: Git-sourced agents discovered and version-compared
```

### 5.4 Dependencies

**No New Dependencies Required!**

**Already Available:**
- ✅ `requests>=2.25.0` - HTTP client
- ✅ `python-dotenv>=0.19.0` - Environment variable loading
- ✅ `pyyaml>=6.0` - YAML parsing
- ✅ `pathlib` - Path manipulation (stdlib)
- ✅ `json` - JSON parsing (stdlib)

**Optional (for future enhancements):**
- `aiohttp>=3.9.0` - Already available for async operations
- `httpx` - Alternative HTTP client (not needed currently)

---

## 6. Configuration Schema

### 6.1 Git Sync Configuration

**File:** `~/.claude-mpm/config/git-sources.json`

```json
{
  "$schema": "https://github.com/bobmatnyc/claude-mpm/schemas/git-sources-v1.json",
  "version": "1.0.0",
  "sources": [
    {
      "id": "claude-mpm-agents",
      "enabled": true,
      "url": "https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main",
      "branch": "main",
      "description": "Official Claude MPM agents repository",
      "sync_interval_hours": 24,
      "require_token": false,
      "priority": 100,
      "auto_sync": false,
      "metadata": {
        "owner": "bobmatnyc",
        "repo": "claude-mpm-agents",
        "type": "public"
      }
    }
  ],
  "global_settings": {
    "auto_sync_on_startup": false,
    "auto_sync_on_deploy": true,
    "cache_ttl_hours": 168,
    "network_timeout_seconds": 30,
    "max_retries": 3,
    "retry_delay_seconds": 5
  }
}
```

### 6.2 Environment Variables

**GitHub Token (Optional):**
```bash
# For private repositories or higher rate limits (5000/hour vs 60/hour)
export GITHUB_TOKEN="ghp_your_token_here"

# Alternative name (for compatibility)
export GH_TOKEN="ghp_your_token_here"
```

**Configuration Override:**
```bash
# Override default Git sync URL
export CLAUDE_MPM_GIT_SYNC_URL="https://raw.githubusercontent.com/custom/repo/main"

# Disable Git sync temporarily
export CLAUDE_MPM_GIT_SYNC_ENABLED="false"
```

---

## 7. Architecture Diagrams

### 7.1 Current Multi-Source System

```
┌──────────────────────────────────────────────────────────────────┐
│                    Agent Deployment Pipeline                      │
└──────────────────────────────────────────────────────────────────┘

SOURCES (3 tiers):                    DEPLOYMENT TARGET:

┌────────────────────┐
│ SYSTEM TIER        │
│ templates/*.json   │────┐
└────────────────────┘    │
                          │
┌────────────────────┐    │         ┌──────────────────────┐
│ PROJECT TIER       │    │         │  Version Comparison  │
│ .claude-mpm/agents/│────┼────────▶│  Select Highest Ver. │
└────────────────────┘    │         └──────────────────────┘
                          │                    │
┌────────────────────┐    │                    ▼
│ USER TIER          │    │         ┌──────────────────────┐
│ ~/.claude-mpm/     │────┘         │  Build & Deploy      │
│     agents/        │              │  ~/.claude/agents/   │
└────────────────────┘              └──────────────────────┘
```

### 7.2 Proposed System with Git Sync

```
┌──────────────────────────────────────────────────────────────────┐
│            Agent Deployment with Git Sync Pipeline               │
└──────────────────────────────────────────────────────────────────┘

SOURCES (4 tiers):                    SYNC PROCESS:

┌────────────────────┐
│ SYSTEM TIER        │
│ templates/*.json   │────┐
└────────────────────┘    │
                          │
┌────────────────────┐    │
│ PROJECT TIER       │    │
│ .claude-mpm/agents/│────┤
└────────────────────┘    │         ┌──────────────────────┐
                          │         │  GitSourceSyncSvc    │
┌────────────────────┐    │         │  - Check ETags       │
│ USER TIER          │    ├────────▶│  - Download Updates  │──┐
│ ~/.claude-mpm/     │    │         │  - Cache Locally     │  │
│     agents/        │    │         └──────────────────────┘  │
└────────────────────┘    │                    │              │
                          │                    ▼              │
┌────────────────────┐    │         ┌──────────────────────┐  │
│ REMOTE-GIT TIER    │    │         │  Cache Directory     │  │
│ ~/.claude-mpm/     │◀───┼─────────│  remote-agents/      │◀─┘
│  cache/remote-     │    │         └──────────────────────┘
│  agents/           │────┘
└────────────────────┘                       │
                                             ▼
                          ┌──────────────────────────────────┐
                          │  Multi-Source Version Comparison │
                          │  Select Highest Version          │
                          └──────────────────────────────────┘
                                             │
                                             ▼
                          ┌──────────────────────────────────┐
                          │  Build & Deploy                  │
                          │  ~/.claude/agents/               │
                          └──────────────────────────────────┘

REMOTE REPOSITORY:

┌─────────────────────────────────────────────┐
│  GitHub: claude-mpm-agents                  │
│  https://github.com/bobmatnyc/              │
│         claude-mpm-agents                   │
│                                             │
│  main/                                      │
│  ├── research.md                            │
│  ├── engineer.md                            │
│  ├── qa.md                                  │
│  └── ...                                    │
└─────────────────────────────────────────────┘
         │                    ▲
         │ Raw URL Download   │ ETag Check
         ▼                    │
┌─────────────────────────────────────────────┐
│  Raw Content API                            │
│  https://raw.githubusercontent.com/         │
│         bobmatnyc/claude-mpm-agents/main/   │
│         {agent}.md                          │
└─────────────────────────────────────────────┘
```

### 7.3 ETag Caching Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                      ETag Sync Workflow                          │
└──────────────────────────────────────────────────────────────────┘

FIRST SYNC (No Cache):

  User: claude-mpm agents sync
    │
    ▼
  GitSourceSyncService.sync_agents()
    │
    ├──▶ Read .etags.json ────▶ (empty or doesn't exist)
    │
    ├──▶ HTTP GET https://raw.../research.md
    │      Headers: (none)
    │
    ◀──── 200 OK
           Headers: ETag: "abc123"
           Body: # Research Agent...
    │
    ├──▶ Save to cache/remote-agents/research.md
    │
    └──▶ Update .etags.json:
           {"research.md": {"etag": "abc123", ...}}


SUBSEQUENT SYNC (With Cache):

  User: claude-mpm agents sync
    │
    ▼
  GitSourceSyncService.sync_agents()
    │
    ├──▶ Read .etags.json ────▶ {"research.md": {"etag": "abc123"}}
    │
    ├──▶ HTTP GET https://raw.../research.md
    │      Headers: If-None-Match: "abc123"
    │
    ◀──── 304 Not Modified
           Headers: ETag: "abc123"
           Body: (empty)
    │
    └──▶ Use cached version
         (no download, no disk write)


UPDATE AVAILABLE:

  User: claude-mpm agents sync
    │
    ▼
  GitSourceSyncService.sync_agents()
    │
    ├──▶ Read .etags.json ────▶ {"research.md": {"etag": "abc123"}}
    │
    ├──▶ HTTP GET https://raw.../research.md
    │      Headers: If-None-Match: "abc123"
    │
    ◀──── 200 OK
           Headers: ETag: "xyz789"  ← NEW ETAG
           Body: # Research Agent (UPDATED)...
    │
    ├──▶ Save to cache/remote-agents/research.md (overwrite)
    │
    └──▶ Update .etags.json:
           {"research.md": {"etag": "xyz789", ...}}
```

---

## 8. Security Considerations

### 8.1 GitHub Token Handling

**Best Practices:**
- ✅ Read from environment variable (`GITHUB_TOKEN` or `GH_TOKEN`)
- ✅ Never log token values
- ✅ Support optional token (works without token for public repos)
- ✅ Validate token before use
- ❌ Never store token in configuration files
- ❌ Never commit token to version control

**Token Validation:**
```python
def validate_github_token(token: str) -> bool:
    """Validate GitHub token before use."""
    try:
        response = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {token}"},
            timeout=10,
        )
        return response.status_code == 200
    except Exception:
        return False
```

### 8.2 Content Validation

**Downloaded Content Checks:**
```python
def validate_agent_content(content: str) -> bool:
    """Validate downloaded agent file is legitimate."""
    # Check 1: Not empty
    if not content or len(content) < 100:
        return False

    # Check 2: Contains expected frontmatter
    if not content.startswith("---"):
        return False

    # Check 3: Has agent_id field
    if "agent_id:" not in content:
        return False

    # Check 4: Not suspiciously large (DOS protection)
    if len(content) > 1_000_000:  # 1MB limit
        logger.warning(f"Agent content exceeds size limit: {len(content)} bytes")
        return False

    return True
```

### 8.3 Path Traversal Protection

**Cache Path Sanitization:**
```python
def sanitize_agent_name(agent_name: str) -> str:
    """Sanitize agent name to prevent path traversal."""
    # Remove any path separators
    agent_name = agent_name.replace("/", "").replace("\\", "")

    # Remove parent directory references
    agent_name = agent_name.replace("..", "")

    # Only allow alphanumeric, dash, underscore
    import re
    agent_name = re.sub(r'[^a-zA-Z0-9_-]', '', agent_name)

    return agent_name
```

---

## 9. Performance Considerations

### 9.1 Network Efficiency

**Optimization Strategies:**

1. **ETag Caching:** Reduces bandwidth by 95%+ for unchanged files
2. **Parallel Downloads:** Download multiple agents concurrently
3. **Compression:** Use `Accept-Encoding: gzip` header
4. **Connection Pooling:** Reuse `requests.Session` for all downloads

**Estimated Performance:**
- First sync (10 agents): ~5-10 seconds
- Subsequent sync (no changes): ~1-2 seconds (ETag checks only)
- Partial update (2 of 10 changed): ~2-3 seconds

### 9.2 Memory Usage

**Memory Footprint:**
- Per agent file: ~50KB (average markdown file)
- 10 agents: ~500KB in memory during sync
- Cache on disk: ~500KB - 1MB total

**Optimization:**
- Stream large files instead of loading into memory
- Process agents one at a time (sequential)
- Clear session after sync completes

### 9.3 Disk Space

**Cache Size:**
```
~/.claude-mpm/cache/remote-agents/
├── github-bobmatnyc-claude-mpm-agents/  (~1MB)
│   ├── research.md                      (50KB)
│   ├── engineer.md                      (45KB)
│   ├── ... (8 more agents)              (400KB)
│   ├── .etags.json                      (5KB)
└── .sync-metadata.json                  (2KB)

Total: ~1MB per Git source
```

**Cache Cleanup:**
```python
def cleanup_old_cache(max_age_days: int = 30):
    """Remove cached agents older than specified days."""
    cutoff_time = time.time() - (max_age_days * 86400)

    for cache_file in self.cache_dir.glob("*.md"):
        if cache_file.stat().st_mtime < cutoff_time:
            cache_file.unlink()
            logger.info(f"Removed stale cache: {cache_file.name}")
```

---

## 10. Monitoring and Observability

### 10.1 Logging Strategy

**Log Levels:**

```python
# INFO level - User-facing operations
logger.info(f"Syncing agents from {self.source_url}")
logger.info(f"Downloaded 3 agents, 7 from cache")

# DEBUG level - Technical details
logger.debug(f"ETag check for research.md: {etag}")
logger.debug(f"HTTP 304 Not Modified for engineer.md")

# WARNING level - Non-critical issues
logger.warning(f"Agent {name} not found (404), removing from cache")
logger.warning(f"Rate limit low ({remaining} remaining), waiting...")

# ERROR level - Failures with fallback
logger.error(f"Network error downloading {name}, using cached version")
logger.error(f"Invalid agent content for {name}, skipping")
```

### 10.2 Metrics Collection

**Key Metrics:**

```python
class GitSyncMetrics:
    """Metrics for Git sync operations."""

    def __init__(self):
        self.sync_count = 0
        self.download_count = 0
        self.cache_hit_count = 0
        self.error_count = 0
        self.total_bytes_downloaded = 0
        self.sync_duration_ms = []

    def record_sync(self, results: Dict[str, Any], duration_ms: float):
        """Record sync operation metrics."""
        self.sync_count += 1
        self.download_count += len(results['downloaded'])
        self.cache_hit_count += len(results['cached'])
        self.error_count += len(results['failed'])
        self.sync_duration_ms.append(duration_ms)

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            "total_syncs": self.sync_count,
            "cache_hit_rate": self.cache_hit_count / max(1, self.sync_count),
            "average_duration_ms": sum(self.sync_duration_ms) / max(1, len(self.sync_duration_ms)),
            "error_rate": self.error_count / max(1, self.download_count),
        }
```

### 10.3 Health Checks

**Sync Health Status:**

```python
def get_sync_health(self) -> Dict[str, Any]:
    """Check sync health status."""
    metadata = self._load_sync_metadata()

    last_sync = metadata.get("last_sync")
    if not last_sync:
        return {"status": "never_synced", "healthy": False}

    # Check how long since last sync
    last_sync_time = datetime.fromisoformat(last_sync)
    hours_since_sync = (datetime.now() - last_sync_time).total_seconds() / 3600

    if hours_since_sync > 72:  # 3 days
        return {"status": "stale", "healthy": False, "hours_since_sync": hours_since_sync}

    if metadata.get("last_error"):
        return {"status": "errors", "healthy": False, "error": metadata["last_error"]}

    return {"status": "healthy", "healthy": True, "hours_since_sync": hours_since_sync}
```

---

## 11. Future Enhancements

### 11.1 Multi-Source Support (Phase 2)

**Support multiple Git sources:**

```python
# git-sources.json
{
  "sources": [
    {
      "id": "official-claude-mpm",
      "url": "https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main",
      "priority": 100,
      "enabled": true
    },
    {
      "id": "company-custom-agents",
      "url": "https://raw.githubusercontent.com/company/agents/main",
      "priority": 200,
      "enabled": true,
      "require_token": true
    },
    {
      "id": "community-agents",
      "url": "https://raw.githubusercontent.com/community/agents/main",
      "priority": 50,
      "enabled": false
    }
  ]
}
```

### 11.2 Differential Updates

**Download only changed agents:**

```python
def get_agent_listing(self) -> List[str]:
    """Get list of available agents from repository."""
    # Option 1: Read from manifest file (agents.json)
    manifest_url = f"{self.source_url}/agents.json"
    response = self.session.get(manifest_url)
    manifest = response.json()
    return manifest["agents"]

    # Option 2: Use GitHub API to list directory contents
    # (requires API key, subject to rate limits)
```

### 11.3 Conflict Resolution

**Handle version conflicts:**

```python
def resolve_version_conflict(
    self,
    local_agent: Dict[str, Any],
    remote_agent: Dict[str, Any]
) -> str:
    """Resolve version conflict between local and remote agent.

    Returns:
        "local", "remote", or "prompt"
    """
    local_ver = local_agent.get("version")
    remote_ver = remote_agent.get("version")

    if local_ver == remote_ver:
        # Same version - check timestamps
        if remote_agent["modified"] > local_agent["modified"]:
            return "remote"
        return "local"

    # Different versions - let user decide
    return "prompt"
```

### 11.4 Signed Commits Verification

**GPG signature verification:**

```python
def verify_agent_signature(content: str, signature: str) -> bool:
    """Verify GPG signature of agent content."""
    import gnupg

    gpg = gnupg.GPG()
    verified = gpg.verify_data(signature, content.encode())

    if verified.valid:
        logger.info(f"Agent signature verified: {verified.key_id}")
        return True

    logger.warning(f"Agent signature invalid or missing")
    return False
```

---

## 12. Example Usage Scenarios

### Scenario 1: Initial Setup

```bash
# Step 1: Enable Git sync
claude-mpm agents config git-sync \
  --enable \
  --url https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main

# Step 2: Perform first sync
claude-mpm agents sync
# Output:
# ✨ Syncing agents from Git repository...
# ⬇️  Downloaded: research.md
# ⬇️  Downloaded: engineer.md
# ⬇️  Downloaded: qa.md
# ✅ Synced 10 agents successfully

# Step 3: Deploy agents (includes Git-synced agents)
claude-mpm agents deploy
# Output:
# 📦 Deploying agents from 4 sources...
# ✅ Deployed 10 agents to ~/.claude/agents/
```

### Scenario 2: Daily Updates

```bash
# Check for updates
claude-mpm agents sync --check-only
# Output:
# ✨ Checking for agent updates...
# 📝 research.md has an update (v4.9.0 → v4.10.0)
# 📝 engineer.md has an update (v3.5.0 → v3.6.0)
# ✅ 2 agents have updates

# Download updates
claude-mpm agents sync
# Output:
# ⬇️  Downloaded: research.md (v4.10.0)
# ⬇️  Downloaded: engineer.md (v3.6.0)
# ⚡ 8 agents served from cache (no changes)
# ✅ Sync complete

# Deploy updated agents
claude-mpm agents deploy
# Output:
# 📦 Updated 2 agents
# ⏭️  Skipped 8 agents (no version change)
```

### Scenario 3: Offline Mode

```bash
# Network is down, but cache exists
claude-mpm agents deploy
# Output:
# ⚠️  Could not connect to Git repository
# 📦 Using cached agents from previous sync
# ✅ Deployed 10 agents from cache
```

### Scenario 4: Private Repository

```bash
# Set GitHub token
export GITHUB_TOKEN="ghp_your_token_here"

# Configure private repo
claude-mpm agents config git-sync \
  --enable \
  --url https://raw.githubusercontent.com/company/private-agents/main \
  --require-token

# Sync private agents
claude-mpm agents sync
# Output:
# 🔐 Authenticating with GitHub token...
# ✅ Token validated
# ⬇️  Downloaded 5 private agents
```

---

## 13. Testing Checklist

### Unit Tests

- [ ] `test_sync_agents_first_time()` - Initial sync downloads all agents
- [ ] `test_sync_agents_with_etag()` - ETag prevents re-download
- [ ] `test_sync_agents_with_updates()` - Detects and downloads changes
- [ ] `test_network_error_fallback()` - Uses cache when network down
- [ ] `test_invalid_agent_content()` - Skips malformed agents
- [ ] `test_rate_limit_handling()` - Waits when rate limited
- [ ] `test_github_token_auth()` - Token authentication works
- [ ] `test_cache_path_sanitization()` - Prevents path traversal
- [ ] `test_concurrent_sync_calls()` - Thread-safe sync operations

### Integration Tests

- [ ] `test_multi_source_with_git()` - Git source integrates with multi-source system
- [ ] `test_version_precedence()` - Higher version Git agent overrides system agent
- [ ] `test_cli_sync_command()` - CLI sync command works end-to-end
- [ ] `test_deploy_with_git_sync()` - Deployment includes Git-synced agents
- [ ] `test_config_management()` - Configuration loads and saves correctly

### Manual Testing

- [ ] Test with real GitHub repository
- [ ] Test with slow network (add artificial delay)
- [ ] Test with network disconnect mid-sync
- [ ] Test with invalid GitHub URL
- [ ] Test with expired GitHub token
- [ ] Test cache cleanup after 30 days
- [ ] Test sync metrics collection

---

## 14. Risk Assessment

### Low Risk ✅

- **Using `requests` library:** Mature, well-tested library already in use
- **ETag caching:** Standard HTTP feature, widely supported
- **Multi-source integration:** Existing infrastructure is robust
- **Cache fallback:** Graceful degradation protects against failures

### Medium Risk ⚠️

- **Network errors:** Mitigated by cache fallback and retry logic
- **GitHub rate limits:** Mitigated by ETag caching and token support
- **Cache corruption:** Mitigated by validation checks and re-download

### High Risk ❌

- **None identified** - Implementation follows existing patterns

### Mitigation Strategies

1. **Network Failures:**
   - Always attempt cache fallback
   - Log errors but don't fail deployment
   - Provide clear user messaging

2. **Rate Limiting:**
   - Use ETag headers to minimize requests
   - Support GitHub token for 5000 req/hour
   - Implement exponential backoff

3. **Security:**
   - Validate all downloaded content
   - Sanitize file paths
   - Never log tokens
   - Support optional token authentication

---

## 15. Success Criteria

### Functional Requirements ✅

- [ ] Download agent .md files from GitHub raw URLs
- [ ] Cache downloaded files locally
- [ ] Use ETag headers to avoid re-downloading unchanged files
- [ ] Integrate with `MultiSourceAgentDeploymentService`
- [ ] Gracefully handle network errors with cache fallback
- [ ] Support optional GitHub token for private repos

### Performance Requirements ✅

- [ ] First sync completes in < 10 seconds (10 agents)
- [ ] Subsequent sync (no changes) completes in < 2 seconds
- [ ] Cache hit rate > 90% for unchanged agents
- [ ] Memory usage < 10MB during sync

### Quality Requirements ✅

- [ ] Unit test coverage > 85%
- [ ] Integration tests pass
- [ ] No new external dependencies required
- [ ] Code follows existing patterns and style
- [ ] Documentation complete

---

## 16. References

### Code Files Analyzed

1. **Agent Loading:**
   - `src/claude_mpm/core/framework/loaders/agent_loader.py`
   - `src/claude_mpm/services/agents/deployment/agent_deployment.py`
   - `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py`

2. **GitHub Integration:**
   - `scripts/download_skills_api.py` (GitHubAPIDownloader class)
   - `src/claude_mpm/core/api_validator.py` (_validate_github_token method)

3. **Configuration:**
   - `src/claude_mpm/core/config.py`
   - `src/claude_mpm/core/unified_paths.py`

4. **Agent Templates:**
   - `src/claude_mpm/agents/templates/*.json` (39 agent templates)
   - `src/claude_mpm/agents/base_agent.json`

### External Resources

- **GitHub Raw URL Format:** `https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}`
- **HTTP ETag Specification:** [RFC 7232](https://tools.ietf.org/html/rfc7232)
- **GitHub API Rate Limits:** [GitHub Docs](https://docs.github.com/en/rest/overview/rate-limits-for-the-rest-api)
- **requests Library:** [Documentation](https://requests.readthedocs.io/)

---

## Appendix A: Proposed GitSourceSyncService API

```python
"""Git Source Sync Service for Claude MPM.

Syncs agent templates from remote Git repositories (GitHub).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import requests
from datetime import datetime

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.core.config import Config
from claude_mpm.core.unified_paths import get_path_manager


class GitSourceSyncService:
    """Service for syncing agent templates from Git repositories."""

    def __init__(
        self,
        source_url: str,
        cache_dir: Optional[Path] = None,
        github_token: Optional[str] = None,
    ):
        """Initialize Git source sync service.

        Args:
            source_url: Base URL for raw files
            cache_dir: Local cache directory
            github_token: Optional GitHub token
        """
        self.logger = get_logger(__name__)
        self.source_url = source_url.rstrip('/')
        self.github_token = github_token

        # Setup cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            path_manager = get_path_manager()
            self.cache_dir = path_manager.get_cache_dir("user") / "remote-agents"

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Setup HTTP session
        self.session = requests.Session()
        if github_token:
            self.session.headers["Authorization"] = f"token {github_token}"
        self.session.headers["Accept"] = "text/plain"

        # ETag cache
        self.etag_cache_file = self.cache_dir / ".etags.json"
        self.etags = self._load_etags()

    def sync_agents(
        self,
        agent_names: Optional[List[str]] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Sync agents from remote Git repository.

        Args:
            agent_names: Specific agents to sync (None = all)
            force_refresh: Force download even if cache is fresh

        Returns:
            Dictionary with sync results
        """
        results = {
            "downloaded": [],
            "cached": [],
            "failed": [],
            "etags": {},
        }

        # Determine which agents to sync
        if not agent_names:
            agent_names = self._get_default_agent_list()

        for agent_name in agent_names:
            try:
                content, etag = self._sync_single_agent(
                    agent_name,
                    force_refresh=force_refresh
                )

                if content:  # New download
                    results["downloaded"].append(agent_name)
                else:  # Served from cache
                    results["cached"].append(agent_name)

                if etag:
                    results["etags"][agent_name] = etag

            except Exception as e:
                self.logger.error(f"Failed to sync {agent_name}: {e}")
                results["failed"].append(agent_name)

        # Save ETags for next sync
        self._save_etags(results["etags"])

        return results

    def get_cached_agents_dir(self) -> Path:
        """Get directory containing cached agent files."""
        return self.cache_dir

    def check_for_updates(self) -> List[str]:
        """Check which agents have updates without downloading."""
        # Implementation: Use HEAD requests with ETags
        pass

    def _sync_single_agent(
        self,
        agent_name: str,
        force_refresh: bool = False
    ) -> Tuple[Optional[str], Optional[str]]:
        """Sync a single agent file.

        Returns:
            Tuple of (content, etag) where content is None if cached
        """
        url = f"{self.source_url}/{agent_name}.md"
        headers = {}

        # Check cache for ETag
        cached_etag = self.etags.get(agent_name)
        if cached_etag and not force_refresh:
            headers["If-None-Match"] = cached_etag

        try:
            response = self.session.get(url, headers=headers, timeout=30)

            if response.status_code == 304:
                # Not modified - use cached version
                self.logger.debug(f"Agent {agent_name} not modified (304)")
                return None, cached_etag

            if response.status_code == 200:
                # New content available
                content = response.text
                new_etag = response.headers.get("ETag")

                # Validate content
                if self._validate_agent_content(content):
                    # Save to cache
                    cache_file = self.cache_dir / f"{agent_name}.md"
                    cache_file.write_text(content)

                    self.logger.info(f"Downloaded {agent_name} (ETag: {new_etag})")
                    return content, new_etag
                else:
                    self.logger.error(f"Invalid content for {agent_name}")
                    return None, None

            response.raise_for_status()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error for {agent_name}: {e}")
            # Try to use cached version
            cache_file = self.cache_dir / f"{agent_name}.md"
            if cache_file.exists():
                self.logger.info(f"Using cached version of {agent_name}")
                return None, cached_etag
            raise

        return None, None

    def _validate_agent_content(self, content: str) -> bool:
        """Validate agent file content."""
        if not content or len(content) < 100:
            return False
        if not content.startswith("---"):
            return False
        if "agent_id:" not in content:
            return False
        if len(content) > 1_000_000:  # 1MB limit
            return False
        return True

    def _load_etags(self) -> Dict[str, str]:
        """Load ETag cache from disk."""
        if self.etag_cache_file.exists():
            with self.etag_cache_file.open() as f:
                return json.load(f)
        return {}

    def _save_etags(self, etags: Dict[str, str]):
        """Save ETag cache to disk."""
        self.etags.update(etags)
        with self.etag_cache_file.open('w') as f:
            json.dump(self.etags, f, indent=2)

    def _get_default_agent_list(self) -> List[str]:
        """Get default list of agents to sync."""
        # For now, use hardcoded list
        # Future: Read from manifest file
        return [
            "research",
            "engineer",
            "qa",
            "documentation",
            "security",
            "ops",
            "ticketing",
            "product_owner",
            "version_control",
            "project_organizer",
        ]
```

---

## Appendix B: Multi-Source Integration Example

```python
# Modification to MultiSourceAgentDeploymentService

def discover_agents_from_all_sources(
    self,
    system_templates_dir: Optional[Path] = None,
    project_agents_dir: Optional[Path] = None,
    user_agents_dir: Optional[Path] = None,
    working_directory: Optional[Path] = None,
    enable_git_sync: bool = True,  # NEW PARAMETER
) -> Dict[str, List[Dict[str, Any]]]:
    """Discover agents from all available sources including Git sync."""

    agents_by_name = {}

    # Existing source discovery (system, project, user)
    # ... existing code ...

    # NEW: Git sync source
    if enable_git_sync:
        git_sync_dir = self._sync_git_agents()
        if git_sync_dir:
            sources.append(("remote-git", git_sync_dir))

    # Rest of discovery logic
    # ... existing code ...

    return agents_by_name

def _sync_git_agents(self) -> Optional[Path]:
    """Sync agents from Git and return cache directory."""
    try:
        from claude_mpm.core.config import Config
        from claude_mpm.services.agents.sources import GitSourceSyncService

        config = Config()
        git_config = config.get("git_sync", {})

        if not git_config.get("enabled", False):
            return None

        sync_service = GitSourceSyncService(
            source_url=git_config.get("source_url"),
            github_token=os.getenv("GITHUB_TOKEN"),
        )

        # Check if sync is needed
        if self._should_sync(sync_service):
            results = sync_service.sync_agents()
            self.logger.info(
                f"Git sync: {len(results['downloaded'])} downloaded, "
                f"{len(results['cached'])} cached"
            )

        return sync_service.get_cached_agents_dir()

    except Exception as e:
        self.logger.warning(f"Git sync failed: {e}, using cached agents")
        # Return cache dir even on sync failure
        return Path.home() / ".claude-mpm" / "cache" / "remote-agents"

def _should_sync(self, sync_service: GitSourceSyncService) -> bool:
    """Check if sync is needed based on time since last sync."""
    # Check timestamp of last sync
    metadata_file = sync_service.cache_dir / ".sync-metadata.json"

    if not metadata_file.exists():
        return True  # Never synced before

    with metadata_file.open() as f:
        metadata = json.load(f)

    last_sync = metadata.get("last_sync")
    if not last_sync:
        return True

    # Parse timestamp
    last_sync_time = datetime.fromisoformat(last_sync)
    hours_since_sync = (datetime.now() - last_sync_time).total_seconds() / 3600

    # Sync if > 24 hours
    sync_interval = Config().get("git_sync", {}).get("sync_interval_hours", 24)
    return hours_since_sync >= sync_interval
```

---

**End of Research Document**

**Next Steps:**
1. Review this research document
2. Create subtasks for implementation phases
3. Begin Phase 1: Core `GitSourceSyncService` implementation
4. Write unit tests
5. Integrate with multi-source deployment
6. Add CLI commands
7. Update documentation

**Research Completion Date:** 2025-11-29
**Estimated Implementation Time:** 8-12 hours (Phase 1 only)
