# Agent Deployment System Migration Research

**Research Date**: 2025-11-30
**Ticket**: 1M-382 - Migrate Agent System to Git-Based Markdown Repository
**Researcher**: Research Agent
**Status**: Complete

---

## Executive Summary

This research analyzes the current 4-tier agent deployment system in Claude MPM and provides a comprehensive plan for migrating to a new single-tier, Git-based architecture. The current system's complexity (PROJECT → REMOTE → USER → SYSTEM priority) will be simplified to a single-tier model where all agents come from Git repositories, with `.claude/agents/` as the only deployment target.

### Key Findings

1. **Current System Complexity**: Multi-source discovery with 4-tier precedence requires ~2,000 LOC across 8+ service classes
2. **Core Components to Preserve**: AgentVersionManager, AgentTemplateBuilder, AgentFormatConverter, GitSourceSyncService (with enhancements)
3. **Breaking Changes**: 4-tier precedence, project/user agent directories, multi-source deployment service
4. **Migration Path**: 4-phase implementation with backward compatibility bridge in Phase 1

---

## Table of Contents

1. [Current Architecture Analysis](#1-current-architecture-analysis)
2. [Component Inventory](#2-component-inventory)
3. [Breaking Changes](#3-breaking-changes)
4. [New Architecture Design](#4-new-architecture-design)
5. [Implementation Plan](#5-implementation-plan)
6. [Migration Strategy](#6-migration-strategy)
7. [Toolchain Detection Design](#7-toolchain-detection-design)
8. [Test Strategy](#8-test-strategy)
9. [Risk Assessment](#9-risk-assessment)

---

## 1. Current Architecture Analysis

### 1.1 System Overview

**Current Implementation**: 4-Tier Agent Discovery and Deployment

```
┌─────────────────────────────────────────────────────────────┐
│                    Current Architecture                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Tier 1: PROJECT (.claude-mpm/agents/)                      │
│  Tier 2: REMOTE  (~/.claude-mpm/cache/remote-agents/)       │
│  Tier 3: USER    (~/.claude-mpm/agents/) [DEPRECATED]       │
│  Tier 4: SYSTEM  (src/claude_mpm/agents/templates/)         │
│                                                               │
│  Priority: PROJECT > REMOTE > USER > SYSTEM                  │
│                                                               │
│  Deployment Target: .claude/agents/                          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Key Components

#### Primary Services

1. **AgentDeploymentService** (`agent_deployment.py` - 901 lines)
   - Main orchestrator for agent deployment
   - Manages deployment lifecycle, versioning, validation
   - Integrates with MultiSourceAgentDeploymentService
   - **Status**: Core logic preserved, orchestration refactored

2. **MultiSourceAgentDeploymentService** (`multi_source_deployment_service.py` - 1,134 lines)
   - Implements 4-tier agent discovery
   - Version comparison across sources
   - Outdated agent cleanup
   - **Status**: TO BE REPLACED - complexity unnecessary in single-tier

3. **GitSourceSyncService** (`sources/git_source_sync_service.py` - 663 lines)
   - ETag-based HTTP caching for GitHub raw files
   - SQLite state tracking with AgentSyncState
   - Incremental sync with SHA-256 content hashing
   - **Status**: ENHANCE for multi-repository support

4. **RemoteAgentDiscoveryService** (`remote_agent_discovery_service.py`)
   - Converts Markdown agents to JSON format
   - Parses YAML frontmatter and routing configuration
   - **Status**: ENHANCE for direct Markdown deployment

### 1.3 Discovery Flow

**Current Flow (4-Tier)**:
```
1. AgentDeploymentService.deploy_agents()
   ↓
2. MultiSourceAgentDeploymentService.discover_agents_from_all_sources()
   ↓
3. For each tier (PROJECT, REMOTE, USER, SYSTEM):
   - AgentDiscoveryService.list_available_agents() [JSON templates]
   - RemoteAgentDiscoveryService.discover_remote_agents() [Markdown → JSON]
   ↓
4. MultiSourceAgentDeploymentService.select_highest_version_agents()
   - Version comparison across all sources
   - Priority tiebreaker: PROJECT > REMOTE > USER > SYSTEM
   ↓
5. MultiSourceAgentDeploymentService.cleanup_outdated_user_agents()
   - Remove superseded user agents
   ↓
6. Deploy selected agents to .claude/agents/
```

### 1.4 Version Management

**Version Format**: Semantic versioning (major.minor.patch)

**Comparison Logic** (AgentVersionManager):
- Parse version strings to tuples: "2.1.0" → (2, 1, 0)
- Lexicographic comparison
- Support for serial versions (legacy): "45" → (0, 0, 45)

**ETag-based Caching** (GitSourceSyncService):
- HTTP 304 Not Modified checks
- SQLite tracking: file path → content SHA-256 hash
- Incremental updates only when remote content changes

### 1.5 Configuration System

**Current Config Structure**:
```yaml
agent_deployment:
  deploy_system_agents: true
  deploy_local_agents: true
  deploy_user_agents: true  # DEPRECATED
  prefer_local_over_system: true
  version_comparison: true
  enabled_agents: []
  disabled_agents: []
  cleanup_outdated_user_agents: true
  exclusion_patterns: []

agent_sync:
  enabled: true
  sources:
    - url: "https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main/agents"
      cache_dir: "~/.claude-mpm/cache/remote-agents"
```

**AgentConfig** (`config/agent_config.py`):
- Environment variable overrides
- Per-project configuration files
- Tier precedence modes (STRICT, OVERRIDE, MERGE)
- Hot reload support

---

## 2. Component Inventory

### 2.1 Components to Remove

#### High Priority (Blocking Single-Tier)

1. **MultiSourceAgentDeploymentService** - 1,134 lines
   - Reason: 4-tier discovery no longer needed
   - Impact: Core deployment flow changes
   - Dependencies: AgentDeploymentService, CLI commands
   - Migration: Replace with GitSourceManager

2. **4-Tier Directory Structure**
   - PROJECT: `.claude-mpm/agents/` (preserve for migration only)
   - USER: `~/.claude-mpm/agents/` (DEPRECATED, remove in v5.0)
   - REMOTE: `~/.claude-mpm/cache/remote-agents/` (refactor to repo-based)
   - SYSTEM: `src/claude_mpm/agents/templates/` (migrate to default repo)

3. **Tier Precedence Logic**
   - `AgentDeploymentService._should_use_multi_source_deployment()`
   - `AgentDeploymentService._get_multi_source_templates()`
   - Priority resolution across tiers
   - Migration: Single source (Git) with repository priority

#### Medium Priority (Feature Deprecations)

4. **User-Level Agent Support**
   - `MultiSourceAgentDeploymentService.cleanup_outdated_user_agents()`
   - Migration command: `claude-mpm agents migrate-to-project`
   - Warning logs for deprecated directories

5. **Project-Local Agents**
   - `.claude-mpm/agents/` directory support
   - Local template manager functionality
   - Migration: User-maintained Git repositories

### 2.2 Components to Enhance

#### GitSourceSyncService Enhancements

**Current Capabilities**:
- Single repository sync
- ETag-based HTTP caching
- Hardcoded agent list
- Cache to `~/.claude-mpm/cache/remote-agents/`

**Required Enhancements**:
1. **Multi-Repository Support**
   ```python
   class GitSourceManager:
       """Manages multiple Git-based agent repositories."""

       def __init__(self):
           self.repositories = []  # List of GitRepository instances
           self.default_repo = "bobmatnyc/claude-mpm-agents"

       def add_repository(
           self,
           owner: str,
           repo: str,
           subdirectory: str = "agents",
           branch: str = "main",
           enabled: bool = True,
           priority: int = 100  # Lower = higher priority
       ):
           """Add a repository to be synced."""

       def sync_all_repositories(self) -> Dict[str, Any]:
           """Sync all enabled repositories."""
   ```

2. **Subdirectory Path Support**
   - Allow specifying subdirectory within repository
   - Example: `monorepo/agents/backend/` or `agents/`
   - Cache structure: `~/.claude-mpm/cache/{owner}/{repo}/{subdirectory}/`

3. **Manifest File Discovery**
   - Replace hardcoded agent list
   - Support `agents.json` manifest in repository root
   - Fallback: Discover `*.md` files in directory

4. **Custom-Only Mode**
   - Disable system repository
   - Only sync user-configured repositories
   - Configuration: `agent_sync.use_default_repo: false`

#### RemoteAgentDiscoveryService Enhancements

**Current**: Markdown → JSON conversion for deployment

**Required Enhancements**:
1. **Direct Markdown Deployment**
   - Deploy Markdown files directly to `.claude/agents/`
   - Skip JSON conversion step
   - Validate Markdown frontmatter structure

2. **Dependency Loading**
   - Parse `dependencies` field from frontmatter
   - Load required dependencies before deployment
   - Support: Python packages, system tools, MCP servers

3. **Domain Authority Injection**
   - Parse `domains` field from frontmatter
   - Inject domain-specific instructions at deployment time
   - Support: file patterns, URL patterns, expertise areas

### 2.3 Components to Preserve

#### Core Deployment Logic

1. **AgentVersionManager** - Version parsing and comparison
2. **AgentTemplateBuilder** - YAML/Markdown generation
3. **AgentFormatConverter** - Format conversion utilities
4. **AgentValidator** - Frontmatter validation
5. **AgentFileSystemManager** - File I/O operations
6. **AgentEnvironmentManager** - Environment variable setup
7. **SingleAgentDeployer** - Individual agent deployment
8. **DeploymentResultsManager** - Metrics and reporting

#### CLI Infrastructure

1. **AgentsCommand** (`cli/commands/agents.py`)
   - Main CLI entry point
   - Subcommand routing
   - **Changes Required**: Update for new repository commands

2. **AgentsParser** (`cli/parsers/agents_parser.py`)
   - Argument parsing
   - **Changes Required**: Add repository management subcommands

---

## 3. Breaking Changes

### 3.1 API Changes

#### Removed Methods

```python
# AgentDeploymentService
- _should_use_multi_source_deployment(deployment_mode: str) -> bool
- _get_multi_source_templates(...) -> Tuple[List[Path], Dict[str, str], Dict[str, Any]]

# MultiSourceAgentDeploymentService (entire class removed)
- discover_agents_from_all_sources(...) -> Dict[str, List[Dict[str, Any]]]
- select_highest_version_agents(...) -> Dict[str, Dict[str, Any]]
- get_agents_for_deployment(...) -> Tuple[Dict[str, Path], Dict[str, str], Dict[str, Any]]
- cleanup_outdated_user_agents(...) -> Dict[str, Any]
- compare_deployed_versions(...) -> Dict[str, Any]
```

#### Changed Methods

```python
# AgentDeploymentService.deploy_agents()
# Before (4-tier):
def deploy_agents(
    target_dir: Optional[Path] = None,
    force_rebuild: bool = False,
    deployment_mode: str = "update",  # "update" or "project"
    config: Optional[Config] = None,
    use_async: bool = False
) -> Dict[str, Any]

# After (single-tier):
def deploy_agents(
    target_dir: Optional[Path] = None,
    force_rebuild: bool = False,
    repositories: Optional[List[str]] = None,  # NEW: Repo filter
    config: Optional[Config] = None,
    use_async: bool = False
) -> Dict[str, Any]
```

### 3.2 Configuration Changes

#### Removed Configuration

```yaml
# .claude-mpm/configuration.yaml
agent_deployment:
  deploy_local_agents: true      # REMOVED
  deploy_user_agents: true       # REMOVED
  prefer_local_over_system: true # REMOVED
  cleanup_outdated_user_agents: true  # REMOVED
```

#### New Configuration

```yaml
# .claude-mpm/configuration.yaml
agent_repositories:
  use_default_repo: true  # bobmatnyc/claude-mpm-agents
  repositories:
    - owner: "bobmatnyc"
      repo: "claude-mpm-agents"
      subdirectory: "agents"
      branch: "main"
      enabled: true
      priority: 100  # Default repo priority

    - owner: "my-org"
      repo: "custom-agents"
      subdirectory: "agents/backend"
      branch: "main"
      enabled: true
      priority: 50  # Higher priority (lower number)

  # Minimal mode: Deploy only core 6 agents
  minimal_mode: false
  minimal_agents:
    - engineer
    - documentation
    - qa
    - research
    - ops
    - ticketing

  # Auto-configure mode: Detect toolchain and select agents
  auto_configure: false
  auto_configure_rules:
    python:
      frameworks:
        django: ["engineer-python-django", "ops-python"]
        flask: ["engineer-python-flask", "ops-python"]
        fastapi: ["engineer-python-fastapi", "ops-python"]
    javascript:
      frameworks:
        react: ["engineer-react", "ops-nodejs"]
        nextjs: ["engineer-nextjs", "ops-nodejs"]
        vue: ["engineer-vue", "ops-nodejs"]
```

### 3.3 Directory Structure Changes

#### Before (4-Tier)

```
~/.claude-mpm/
├── agents/                      # USER tier (DEPRECATED)
│   ├── custom_agent.json
│   └── custom_agent.md
├── cache/
│   └── remote-agents/           # REMOTE tier
│       ├── research.md
│       └── engineer.md
└── .etag-cache.json             # HTTP ETags

.claude-mpm/                     # Project-local
├── agents/                      # PROJECT tier
│   ├── custom_project_agent.json
│   └── custom_project_agent.md
└── configuration.yaml

src/claude_mpm/
└── agents/
    └── templates/               # SYSTEM tier
        ├── research.json
        └── engineer.json
```

#### After (Single-Tier)

```
~/.claude-mpm/
└── cache/
    └── remote-agents/
        ├── bobmatnyc/
        │   └── claude-mpm-agents/
        │       └── agents/              # Default repo
        │           ├── research.md
        │           └── engineer.md
        └── my-org/
            └── custom-agents/
                └── agents/
                    └── backend/         # Subdirectory support
                        └── custom.md

.claude/agents/                          # Single deployment target
├── research.md                          # From default repo
├── engineer.md                          # From default repo
└── custom.md                            # From custom repo
```

### 3.4 CLI Command Changes

#### Removed Commands

```bash
# No longer needed with single-tier
claude-mpm agents list --by-tier
claude-mpm agents migrate-to-project  # One-time migration only
```

#### New Commands

```bash
# Repository management
claude-mpm agents repo list
claude-mpm agents repo add <owner>/<repo> [--subdirectory PATH] [--priority NUM]
claude-mpm agents repo remove <owner>/<repo>
claude-mpm agents repo enable <owner>/<repo>
claude-mpm agents repo disable <owner>/<repo>
claude-mpm agents repo sync [<owner>/<repo>]  # Sync specific or all repos

# Agent selection
claude-mpm agents browse  # Browse all available agents from all repos
claude-mpm agents select  # Interactive selection from available agents
claude-mpm agents preview <agent-name>  # Preview agent details before deployment

# Minimal mode
claude-mpm agents deploy --minimal  # Deploy only 6 core agents

# Auto-configure mode
claude-mpm agents deploy --auto-configure  # Detect toolchain and deploy matching agents
claude-mpm agents detect-toolchain  # Show detected languages/frameworks
```

---

## 4. New Architecture Design

### 4.1 System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                      New Single-Tier Architecture                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Sources: Git Repositories (priority-based)                       │
│  ├─ Default: bobmatnyc/claude-mpm-agents (priority: 100)         │
│  ├─ Custom:  my-org/custom-agents        (priority: 50)          │
│  └─ Custom:  user/specialized-agents     (priority: 75)          │
│                                                                    │
│  Cache: ~/.claude-mpm/cache/{owner}/{repo}/{subdirectory}/        │
│                                                                    │
│  Deployment Target: .claude/agents/ (single destination)          │
│                                                                    │
│  Agent Format: Markdown with YAML frontmatter                     │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 Component Architecture

#### GitSourceManager

```python
@dataclass
class GitRepository:
    """Configuration for a Git-based agent repository."""
    owner: str
    repo: str
    subdirectory: str = "agents"
    branch: str = "main"
    enabled: bool = True
    priority: int = 100  # Lower = higher priority
    url_template: str = "https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{subdirectory}/{filename}"
    cache_dir: Optional[Path] = None

    def get_cache_path(self) -> Path:
        """Get cache directory for this repository."""
        if self.cache_dir:
            return self.cache_dir
        return Path.home() / ".claude-mpm" / "cache" / "remote-agents" / self.owner / self.repo / self.subdirectory


class GitSourceManager:
    """Manages multiple Git-based agent repositories with priority resolution."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.repositories: List[GitRepository] = []
        self.sync_state = AgentSyncState()
        self._load_configuration(config)

    def _load_configuration(self, config: Optional[Dict[str, Any]]):
        """Load repositories from configuration."""
        if config and config.get("agent_repositories", {}).get("use_default_repo", True):
            # Add default repository
            self.add_repository(
                owner="bobmatnyc",
                repo="claude-mpm-agents",
                subdirectory="agents",
                priority=100
            )

        # Add custom repositories
        for repo_config in config.get("agent_repositories", {}).get("repositories", []):
            self.add_repository(**repo_config)

    def add_repository(
        self,
        owner: str,
        repo: str,
        subdirectory: str = "agents",
        branch: str = "main",
        enabled: bool = True,
        priority: int = 100
    ) -> GitRepository:
        """Add a repository to be synced."""
        git_repo = GitRepository(
            owner=owner,
            repo=repo,
            subdirectory=subdirectory,
            branch=branch,
            enabled=enabled,
            priority=priority
        )

        # Register in sync state
        source_id = f"{owner}/{repo}/{subdirectory}"
        self.sync_state.register_source(
            source_id=source_id,
            url=git_repo.url_template.format(
                owner=owner,
                repo=repo,
                branch=branch,
                subdirectory=subdirectory,
                filename=""
            ),
            enabled=enabled
        )

        self.repositories.append(git_repo)
        logger.info(f"Added repository: {source_id} (priority: {priority})")
        return git_repo

    def sync_all_repositories(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Sync all enabled repositories."""
        results = {
            "repositories": [],
            "total_synced": 0,
            "total_cached": 0,
            "total_failed": 0,
            "errors": []
        }

        for repo in sorted(self.repositories, key=lambda r: r.priority):
            if not repo.enabled:
                continue

            try:
                sync_service = GitSourceSyncService(
                    source_url=repo.url_template.format(
                        owner=repo.owner,
                        repo=repo.repo,
                        branch=repo.branch,
                        subdirectory=repo.subdirectory,
                        filename=""
                    ),
                    cache_dir=repo.get_cache_path(),
                    source_id=f"{repo.owner}/{repo.repo}/{repo.subdirectory}"
                )

                repo_results = sync_service.sync_agents(force_refresh=force_refresh)

                results["repositories"].append({
                    "repository": f"{repo.owner}/{repo.repo}",
                    "subdirectory": repo.subdirectory,
                    "priority": repo.priority,
                    "synced": repo_results["total_downloaded"],
                    "cached": repo_results["cache_hits"],
                    "failed": len(repo_results["failed"])
                })

                results["total_synced"] += repo_results["total_downloaded"]
                results["total_cached"] += repo_results["cache_hits"]
                results["total_failed"] += len(repo_results["failed"])

            except Exception as e:
                error_msg = f"Failed to sync {repo.owner}/{repo.repo}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                results["total_failed"] += 1

        return results

    def discover_available_agents(self) -> Dict[str, AgentMetadata]:
        """Discover all available agents from all repositories."""
        agents_by_name = {}

        for repo in sorted(self.repositories, key=lambda r: r.priority):
            if not repo.enabled:
                continue

            cache_dir = repo.get_cache_path()
            if not cache_dir.exists():
                continue

            discovery = RemoteAgentDiscoveryService(cache_dir)
            repo_agents = discovery.discover_remote_agents()

            for agent_data in repo_agents:
                agent_name = agent_data["name"]

                # Priority resolution: Lower priority number = higher precedence
                if agent_name not in agents_by_name:
                    agents_by_name[agent_name] = {
                        "data": agent_data,
                        "repository": f"{repo.owner}/{repo.repo}",
                        "priority": repo.priority,
                        "path": agent_data["path"]
                    }
                elif repo.priority < agents_by_name[agent_name]["priority"]:
                    # This repo has higher priority (lower number)
                    logger.info(
                        f"Agent '{agent_name}' overridden by {repo.owner}/{repo.repo} "
                        f"(priority {repo.priority} > {agents_by_name[agent_name]['priority']})"
                    )
                    agents_by_name[agent_name] = {
                        "data": agent_data,
                        "repository": f"{repo.owner}/{repo.repo}",
                        "priority": repo.priority,
                        "path": agent_data["path"]
                    }

        return agents_by_name
```

#### SingleTierDeploymentService

```python
class SingleTierDeploymentService:
    """Simplified deployment service for single-tier Git-based agents."""

    def __init__(self, config: Optional[Config] = None):
        self.git_source_manager = GitSourceManager(config.to_dict() if config else None)
        self.template_builder = AgentTemplateBuilder()
        self.version_manager = AgentVersionManager()
        self.validator = AgentValidator()

    def deploy_agents(
        self,
        target_dir: Optional[Path] = None,
        force_rebuild: bool = False,
        repositories: Optional[List[str]] = None,
        agents: Optional[List[str]] = None,
        config: Optional[Config] = None,
        use_async: bool = False
    ) -> Dict[str, Any]:
        """Deploy agents from Git repositories to target directory."""

        # Determine target directory
        if not target_dir:
            target_dir = Path.home() / ".claude" / "agents"
        target_dir.mkdir(parents=True, exist_ok=True)

        # Sync repositories
        sync_results = self.git_source_manager.sync_all_repositories(
            force_refresh=force_rebuild
        )

        # Discover available agents
        available_agents = self.git_source_manager.discover_available_agents()

        # Filter by repository if specified
        if repositories:
            available_agents = {
                name: meta for name, meta in available_agents.items()
                if meta["repository"] in repositories
            }

        # Filter by agent names if specified
        if agents:
            available_agents = {
                name: meta for name, meta in available_agents.items()
                if name in agents
            }

        # Deploy each agent
        results = {
            "deployed": [],
            "updated": [],
            "skipped": [],
            "errors": [],
            "total": len(available_agents)
        }

        for agent_name, agent_meta in available_agents.items():
            try:
                deployed_file = target_dir / f"{agent_name}.md"

                # Check if update needed
                if not force_rebuild and deployed_file.exists():
                    # Version comparison
                    deployed_version = self._extract_deployed_version(deployed_file)
                    new_version = agent_meta["data"].get("version", "0.0.0")

                    if self.version_manager.compare_versions(
                        self.version_manager.parse_version(new_version),
                        deployed_version
                    ) <= 0:
                        results["skipped"].append(agent_name)
                        continue

                # Deploy agent
                shutil.copy2(Path(agent_meta["path"]), deployed_file)

                if deployed_file.exists() and deployed_file.stat().st_mtime > 0:
                    if agent_name in results["skipped"]:
                        results["updated"].append(agent_name)
                    else:
                        results["deployed"].append(agent_name)
                else:
                    results["deployed"].append(agent_name)

            except Exception as e:
                error_msg = f"Failed to deploy {agent_name}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        return results
```

### 4.3 Deployment Flow

**New Flow (Single-Tier)**:
```
1. User: claude-mpm agents deploy
   ↓
2. SingleTierDeploymentService.deploy_agents()
   ↓
3. GitSourceManager.sync_all_repositories()
   ├─ For each enabled repository (priority order):
   │  ├─ GitSourceSyncService.sync_agents()
   │  │  ├─ Check manifest or discover *.md files
   │  │  ├─ Fetch with ETag (HTTP 304 caching)
   │  │  └─ Save to cache: ~/.claude-mpm/cache/{owner}/{repo}/{subdir}/
   │  └─ AgentSyncState.track_file() (SHA-256 hash)
   ↓
4. GitSourceManager.discover_available_agents()
   ├─ For each repository (priority order):
   │  ├─ RemoteAgentDiscoveryService.discover_remote_agents()
   │  │  ├─ Find *.md files in cache
   │  │  ├─ Parse YAML frontmatter
   │  │  └─ Extract metadata
   │  └─ Priority resolution (lower number = higher precedence)
   ↓
5. For each agent:
   ├─ Check version vs. deployed
   ├─ Copy Markdown file to .claude/agents/
   └─ Track deployment result
   ↓
6. Return deployment results
```

---

## 5. Implementation Plan

### Phase 1: Foundation and GitSourceManager (Week 1-2)

**Ticket**: `1M-382-phase1-git-source-manager`

#### 1.1 Create GitRepository Dataclass

**File**: `src/claude_mpm/services/agents/sources/git_repository.py`

```python
@dataclass
class GitRepository:
    """Configuration for a Git-based agent repository."""
    owner: str
    repo: str
    subdirectory: str = "agents"
    branch: str = "main"
    enabled: bool = True
    priority: int = 100
    url_template: str = field(default="https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{subdirectory}/{filename}")
    cache_dir: Optional[Path] = None

    def __post_init__(self):
        """Validate configuration on initialization."""
        if not self.owner or not self.repo:
            raise ValueError("owner and repo are required")
        if self.priority < 0:
            raise ValueError("priority must be non-negative")

    def get_source_id(self) -> str:
        """Get unique identifier for this repository."""
        return f"{self.owner}/{self.repo}/{self.subdirectory}"

    def get_cache_path(self) -> Path:
        """Get cache directory for this repository."""
        if self.cache_dir:
            return self.cache_dir
        home = Path.home()
        return home / ".claude-mpm" / "cache" / "remote-agents" / self.owner / self.repo / self.subdirectory

    def get_agent_url(self, filename: str) -> str:
        """Get URL for a specific agent file."""
        return self.url_template.format(
            owner=self.owner,
            repo=self.repo,
            branch=self.branch,
            subdirectory=self.subdirectory,
            filename=filename
        )
```

#### 1.2 Implement GitSourceManager

**File**: `src/claude_mpm/services/agents/sources/git_source_manager.py`

**Features**:
- Load repositories from configuration
- Add/remove/enable/disable repositories
- Sync all repositories with priority handling
- Discover agents from all repositories
- Priority-based agent resolution

**Tests**:
- `tests/unit/services/agents/sources/test_git_source_manager.py`
- `tests/integration/services/agents/test_git_source_manager_integration.py`

#### 1.3 Enhance GitSourceSyncService

**Changes Required**:

1. **Manifest File Support**:
```python
def _get_agent_list(self) -> List[str]:
    """Get list of agent filenames to sync."""
    # Check for manifest file
    manifest_url = f"{self.source_url}/agents.json"
    try:
        response = self.session.get(manifest_url, timeout=10)
        if response.status_code == 200:
            manifest = response.json()
            return manifest.get("agents", [])
    except Exception as e:
        logger.debug(f"No manifest file found, using fallback: {e}")

    # Fallback: Return hardcoded list or discover
    return self._discover_agent_files()

def _discover_agent_files(self) -> List[str]:
    """Discover agent files by listing directory (requires GitHub API)."""
    # Note: This would require GitHub API which has rate limits
    # For now, return hardcoded list
    return [
        "research.md",
        "engineer.md",
        # ...
    ]
```

2. **Subdirectory Path Support**:
```python
def __init__(
    self,
    source_url: str,
    cache_dir: Optional[Path] = None,
    source_id: str = "github-remote",
    subdirectory: str = ""  # NEW
):
    # Append subdirectory to source_url if provided
    if subdirectory:
        self.source_url = f"{source_url.rstrip('/')}/{subdirectory.strip('/')}"
    else:
        self.source_url = source_url.rstrip("/")
```

#### 1.4 Backward Compatibility Bridge

**Purpose**: Allow existing 4-tier users to continue working during migration

**Implementation**:
```python
class LegacyAgentBridge:
    """Bridges old 4-tier system to new single-tier for backward compatibility."""

    @staticmethod
    def detect_legacy_agents() -> Dict[str, List[Path]]:
        """Detect agents in legacy directories."""
        legacy_agents = {
            "project": [],
            "user": [],
            "system": []
        }

        # Check PROJECT tier
        project_dir = Path.cwd() / ".claude-mpm" / "agents"
        if project_dir.exists():
            legacy_agents["project"] = list(project_dir.glob("*.json")) + list(project_dir.glob("*.md"))

        # Check USER tier (deprecated)
        user_dir = Path.home() / ".claude-mpm" / "agents"
        if user_dir.exists():
            legacy_agents["user"] = list(user_dir.glob("*.json")) + list(user_dir.glob("*.md"))

        # Check SYSTEM tier
        from claude_mpm.config.paths import paths
        system_dir = paths.agents_dir / "templates"
        if system_dir.exists():
            legacy_agents["system"] = list(system_dir.glob("*.json"))

        return legacy_agents

    @staticmethod
    def show_migration_warning(legacy_agents: Dict[str, List[Path]]):
        """Show warning about legacy agents found."""
        total = sum(len(agents) for agents in legacy_agents.values())
        if total == 0:
            return

        logger.warning(
            f"\n"
            f"⚠️  MIGRATION NOTICE: {total} legacy agent(s) detected\n"
            f"\n"
            f"   The 4-tier agent system is deprecated. Please migrate to Git-based agents:\n"
            f"\n"
            f"   1. Review your custom agents:\n"
        )

        if legacy_agents["project"]:
            logger.warning(f"      - Project agents: {len(legacy_agents['project'])} in .claude-mpm/agents/")
        if legacy_agents["user"]:
            logger.warning(f"      - User agents: {len(legacy_agents['user'])} in ~/.claude-mpm/agents/")

        logger.warning(
            f"\n"
            f"   2. Migration options:\n"
            f"      a) Create a Git repository for your custom agents\n"
            f"      b) Add to your team's agent repository\n"
            f"      c) Configure private repository: claude-mpm agents repo add <owner>/<repo>\n"
            f"\n"
            f"   3. Legacy support ends: v5.0.0 (tentative: Q2 2025)\n"
            f"\n"
            f"   Learn more: https://docs.claude-mpm.dev/agents/migration-guide\n"
        )
```

#### 1.5 Configuration Schema

**File**: `.claude-mpm/configuration.yaml`

```yaml
# Agent repository configuration
agent_repositories:
  # Enable/disable default repository
  use_default_repo: true

  # Repository list (priority-based, lower number = higher priority)
  repositories:
    - owner: "bobmatnyc"
      repo: "claude-mpm-agents"
      subdirectory: "agents"
      branch: "main"
      enabled: true
      priority: 100  # Default priority

    # Example: Custom repository
    # - owner: "my-org"
    #   repo: "custom-agents"
    #   subdirectory: "agents/backend"
    #   branch: "main"
    #   enabled: true
    #   priority: 50  # Higher priority (deployed preferentially)
```

**Validation**:
- Priority must be non-negative integer
- owner, repo, branch must be non-empty strings
- subdirectory defaults to "agents" if not specified
- Warn if multiple repositories have same priority

---

### Phase 2: Single-Tier Deployment Service (Week 3-4)

**Ticket**: `1M-382-phase2-deployment-service`

#### 2.1 Implement SingleTierDeploymentService

**File**: `src/claude_mpm/services/agents/deployment/single_tier_deployment_service.py`

**Core Methods**:

1. **deploy_agents()** - Main deployment orchestration
2. **_sync_repositories()** - Sync all configured repositories
3. **_discover_available_agents()** - Discover from all repos with priority
4. **_deploy_single_agent()** - Deploy one agent to target
5. **_check_version_needs_update()** - Version comparison logic

#### 2.2 Refactor AgentDeploymentService

**Strategy**: Gradual migration with feature flags

```python
class AgentDeploymentService:
    """Agent deployment service with single-tier and legacy support."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

        # Feature flag: Enable single-tier mode
        self.use_single_tier = self.config.get(
            "agent_deployment.use_single_tier_mode",
            default=True
        )

        if self.use_single_tier:
            self.deployment_service = SingleTierDeploymentService(config)
        else:
            # Legacy 4-tier mode (deprecated)
            logger.warning("Using legacy 4-tier deployment mode (deprecated)")
            # ... existing multi-tier logic

    def deploy_agents(self, **kwargs) -> Dict[str, Any]:
        """Deploy agents using configured deployment mode."""
        if self.use_single_tier:
            return self.deployment_service.deploy_agents(**kwargs)
        else:
            # Legacy mode
            return self._legacy_deploy_agents(**kwargs)
```

#### 2.3 Update CLI Commands

**File**: `src/claude_mpm/cli/commands/agents.py`

**Changes**:

1. **Repository Management Commands**:
```python
def _repo_list(self, args) -> CommandResult:
    """List configured agent repositories."""
    # Implementation

def _repo_add(self, args) -> CommandResult:
    """Add a new agent repository."""
    # Implementation

def _repo_remove(self, args) -> CommandResult:
    """Remove a repository."""
    # Implementation

def _repo_sync(self, args) -> CommandResult:
    """Sync specific or all repositories."""
    # Implementation
```

2. **Update Existing Deploy Command**:
```python
def _deploy_agents(self, args, force=False) -> CommandResult:
    """Deploy agents using single-tier system."""
    try:
        # New parameters
        repositories = getattr(args, "repositories", None)
        agents = getattr(args, "agents", None)

        # Use SingleTierDeploymentService
        result = self.deployment_service.deploy_agents(
            force_rebuild=force,
            repositories=repositories,
            agents=agents
        )

        # Format and display results
        # ...
    except Exception as e:
        return CommandResult.error_result(f"Deployment failed: {e}")
```

#### 2.4 Tests

**Unit Tests**:
- `tests/unit/services/agents/deployment/test_single_tier_deployment_service.py`
- Test agent discovery with multiple repos
- Test priority resolution
- Test version comparison
- Test deployment success/failure cases

**Integration Tests**:
- `tests/integration/services/agents/test_single_tier_deployment_integration.py`
- Test full deployment flow
- Test with mock Git repositories
- Test configuration loading
- Test CLI command integration

---

### Phase 3: Minimal & Auto-Configure Modes (Week 5-6)

**Ticket**: `1M-382-phase3-agent-selection`

#### 3.1 Minimal Mode Implementation

**Purpose**: Deploy only 6 core agents for minimal installations

**Core Agents**:
1. engineer - Code implementation
2. documentation - Documentation writing
3. qa - Testing and quality assurance
4. research - Codebase research and analysis
5. ops - Operations and deployment
6. ticketing - Ticket management integration

**Implementation**:

```python
class MinimalModeDeployer:
    """Handles minimal agent deployment (6 core agents only)."""

    MINIMAL_AGENTS = [
        "engineer",
        "documentation",
        "qa",
        "research",
        "ops",
        "ticketing"
    ]

    def deploy_minimal_agents(
        self,
        target_dir: Path,
        repositories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Deploy only core agents."""
        # Filter available agents to minimal set
        available_agents = self.git_source_manager.discover_available_agents()

        minimal_agents = {
            name: meta for name, meta in available_agents.items()
            if name in self.MINIMAL_AGENTS
        }

        # Validate all core agents are available
        missing = set(self.MINIMAL_AGENTS) - set(minimal_agents.keys())
        if missing:
            logger.warning(f"Core agents missing from repositories: {missing}")

        # Deploy
        return self._deploy_agent_set(minimal_agents, target_dir)
```

**CLI Command**:
```bash
claude-mpm agents deploy --minimal
```

#### 3.2 Toolchain Detection Service

**File**: `src/claude_mpm/services/agents/toolchain_detector.py`

**Purpose**: Detect project languages, frameworks, and tools

**Detection Strategies**:

1. **File Pattern Detection**:
```python
LANGUAGE_PATTERNS = {
    "python": {
        "files": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
        "extensions": [".py"],
        "min_files": 3
    },
    "javascript": {
        "files": ["package.json", "package-lock.json", "yarn.lock"],
        "extensions": [".js", ".jsx"],
        "min_files": 5
    },
    "typescript": {
        "files": ["tsconfig.json", "package.json"],
        "extensions": [".ts", ".tsx"],
        "min_files": 3
    },
    "rust": {
        "files": ["Cargo.toml", "Cargo.lock"],
        "extensions": [".rs"],
        "min_files": 2
    },
    "go": {
        "files": ["go.mod", "go.sum"],
        "extensions": [".go"],
        "min_files": 2
    }
}
```

2. **Framework Detection**:
```python
FRAMEWORK_PATTERNS = {
    "python": {
        "django": {
            "dependencies": ["django"],
            "files": ["manage.py", "settings.py"]
        },
        "flask": {
            "dependencies": ["flask"],
            "files": ["app.py"]
        },
        "fastapi": {
            "dependencies": ["fastapi"],
            "files": ["main.py"]
        }
    },
    "javascript": {
        "react": {
            "dependencies": ["react"],
            "files": ["src/App.jsx", "public/index.html"]
        },
        "nextjs": {
            "dependencies": ["next"],
            "files": ["next.config.js", "pages/_app.js"]
        },
        "vue": {
            "dependencies": ["vue"],
            "files": ["vue.config.js", "src/App.vue"]
        }
    },
    "typescript": {
        "react": {
            "dependencies": ["react", "@types/react"],
            "files": ["src/App.tsx"]
        },
        "nextjs": {
            "dependencies": ["next"],
            "files": ["next.config.ts", "pages/_app.tsx"]
        }
    }
}
```

3. **Build Tool Detection**:
```python
BUILD_TOOL_PATTERNS = {
    "python": {
        "poetry": "pyproject.toml + [tool.poetry]",
        "pipenv": "Pipfile",
        "pip": "requirements.txt"
    },
    "javascript": {
        "npm": "package-lock.json",
        "yarn": "yarn.lock",
        "pnpm": "pnpm-lock.yaml"
    },
    "rust": {
        "cargo": "Cargo.toml"
    }
}
```

**Detection Method**:

```python
class ToolchainDetector:
    """Detects project toolchain from file patterns and dependencies."""

    def detect_toolchain(self, project_dir: Path) -> ToolchainProfile:
        """Detect languages, frameworks, and build tools."""
        profile = ToolchainProfile()

        # 1. Detect languages
        profile.languages = self._detect_languages(project_dir)

        # 2. Detect frameworks for each language
        for language in profile.languages:
            frameworks = self._detect_frameworks(project_dir, language)
            profile.frameworks[language] = frameworks

        # 3. Detect build tools
        profile.build_tools = self._detect_build_tools(project_dir)

        # 4. Detect infrastructure
        profile.infrastructure = self._detect_infrastructure(project_dir)

        return profile

    def _detect_languages(self, project_dir: Path) -> List[str]:
        """Detect programming languages used."""
        detected = []

        for language, patterns in LANGUAGE_PATTERNS.items():
            score = 0

            # Check for indicator files
            for indicator_file in patterns["files"]:
                if (project_dir / indicator_file).exists():
                    score += 10

            # Count files with extensions
            file_count = sum(
                1 for ext in patterns["extensions"]
                for _ in project_dir.rglob(f"*{ext}")
            )

            if file_count >= patterns["min_files"]:
                score += file_count

            if score >= 10:
                detected.append(language)
                logger.info(f"Detected language: {language} (score: {score})")

        return detected
```

#### 3.3 Agent Recommender Service

**File**: `src/claude_mpm/services/agents/recommender.py` (already exists)

**Enhancement**: Add framework-specific recommendations

```python
AGENT_RECOMMENDATIONS = {
    "python": {
        "base": ["engineer-python", "ops-python"],
        "frameworks": {
            "django": ["engineer-python-django", "ops-python-web"],
            "flask": ["engineer-python-flask", "ops-python-web"],
            "fastapi": ["engineer-python-fastapi", "ops-python-api"]
        }
    },
    "javascript": {
        "base": ["engineer-javascript", "ops-nodejs"],
        "frameworks": {
            "react": ["engineer-react", "ops-frontend"],
            "nextjs": ["engineer-nextjs", "ops-fullstack"],
            "vue": ["engineer-vue", "ops-frontend"]
        }
    },
    "typescript": {
        "base": ["engineer-typescript", "ops-nodejs"],
        "frameworks": {
            "react": ["engineer-react-typescript", "ops-frontend"],
            "nextjs": ["engineer-nextjs-typescript", "ops-fullstack"]
        }
    },
    "rust": {
        "base": ["engineer-rust", "ops-rust"]
    },
    "go": {
        "base": ["engineer-go", "ops-go"]
    }
}

class AgentRecommender:
    """Recommends agents based on toolchain profile."""

    def recommend_agents(self, profile: ToolchainProfile) -> List[AgentRecommendation]:
        """Generate agent recommendations from toolchain profile."""
        recommendations = []

        # Always recommend core agents
        recommendations.extend(self._get_core_recommendations())

        # Add language-specific agents
        for language in profile.languages:
            lang_recs = self._get_language_recommendations(language, profile)
            recommendations.extend(lang_recs)

        # Add framework-specific agents
        for language, frameworks in profile.frameworks.items():
            for framework in frameworks:
                framework_recs = self._get_framework_recommendations(language, framework)
                recommendations.extend(framework_recs)

        # Deduplicate and prioritize
        return self._deduplicate_recommendations(recommendations)
```

#### 3.4 Auto-Configure CLI

**Command**:
```bash
# Detect and display toolchain
claude-mpm agents detect-toolchain

# Show recommended agents without deploying
claude-mpm agents recommend

# Deploy recommended agents
claude-mpm agents deploy --auto-configure
```

**Interactive Flow**:
```
$ claude-mpm agents deploy --auto-configure

🔍 Detecting project toolchain...

Detected:
  Languages:    Python, JavaScript
  Frameworks:   Django, React
  Build Tools:  Poetry, npm
  Infrastructure: Docker, GitHub Actions

📋 Recommended Agents:
  Core (6):        engineer, documentation, qa, research, ops, ticketing
  Python (2):      engineer-python-django, ops-python-web
  JavaScript (2):  engineer-react, ops-frontend

  Total: 12 agents

Deploy these agents? [Y/n]: y

✅ Deploying 12 agents...
   ✓ engineer (v2.5.0)
   ✓ documentation (v2.3.1)
   ...

✅ Deployment complete! 12 agents deployed to .claude/agents/
```

---

### Phase 4: Agent Selection UI (Week 7-8)

**Ticket**: `1M-382-phase4-selection-ui`

#### 4.1 Browse Command

**Purpose**: Interactive browsing of available agents from all repositories

```bash
claude-mpm agents browse
```

**Implementation**:

```python
class AgentBrowserUI:
    """Interactive UI for browsing available agents."""

    def browse_agents(self):
        """Launch interactive agent browser."""
        available_agents = self.git_source_manager.discover_available_agents()

        # Group by repository
        by_repo = {}
        for name, meta in available_agents.items():
            repo = meta["repository"]
            if repo not in by_repo:
                by_repo[repo] = []
            by_repo[repo].append((name, meta))

        # Interactive menu
        print("📚 Available Agents\n")
        for repo in sorted(by_repo.keys()):
            print(f"\n{repo} ({len(by_repo[repo])} agents):")
            for name, meta in by_repo[repo]:
                version = meta["data"].get("version", "unknown")
                description = meta["data"].get("description", "")
                print(f"  • {name} (v{version})")
                print(f"    {description[:70]}...")
```

#### 4.2 Select Command

**Purpose**: Interactive agent selection with preview

```bash
claude-mpm agents select
```

**Flow**:
1. Show all available agents grouped by category
2. Allow multi-select with checkboxes
3. Show agent details on hover/selection
4. Preview deployment before confirming
5. Deploy selected agents

#### 4.3 Preview Command

**Purpose**: Preview agent details before deployment

```bash
claude-mpm agents preview <agent-name>
```

**Output**:
```
Agent: engineer-python-django
Version: 2.5.0
Repository: bobmatnyc/claude-mpm-agents
Priority: 100

Description:
  Django web framework specialist for Python projects.
  Expertise in Django ORM, views, templates, and REST framework.

Specializations:
  - Django models and migrations
  - Django REST Framework APIs
  - Celery task queues
  - Django testing patterns

Dependencies:
  Python Packages:
    - django>=4.0
    - djangorestframework>=3.14

  System Tools:
    - postgresql-client
    - redis-tools

Routing:
  Keywords: django, python, web, orm, migrations
  Paths: **/models.py, **/views.py, **/urls.py
  Priority: 90

Size: 15.2 KB
Last Updated: 2025-11-25
```

---

## 6. Migration Strategy

### 6.1 User Communication

**Timeline**:
- **v4.27.0** (Dec 2024): Announce deprecation, single-tier available with feature flag
- **v4.30.0** (Jan 2025): Single-tier becomes default, legacy mode with warnings
- **v5.0.0** (Q2 2025): Legacy mode removed, single-tier only

**Announcement Channels**:
- Release notes
- Documentation site banner
- In-app warnings
- CLI deprecation messages
- GitHub discussions

**Migration Guide URL**: `https://docs.claude-mpm.dev/agents/migration-guide`

### 6.2 Deprecation Warnings

**Phase 1 Warnings (v4.27.0)**:
```
⚠️  NOTICE: 4-tier agent system will be deprecated in v5.0.0

    The new single-tier Git-based system is now available.
    To enable: Set agent_deployment.use_single_tier_mode: true

    Learn more: https://docs.claude-mpm.dev/agents/migration-guide
```

**Phase 2 Warnings (v4.30.0)**:
```
⚠️  WARNING: Legacy 4-tier mode is deprecated

    Single-tier mode is now the default.
    Legacy support ends in v5.0.0 (tentative: Q2 2025)

    Found legacy agents:
      - 3 project agents in .claude-mpm/agents/
      - 2 user agents in ~/.claude-mpm/agents/

    Migration: claude-mpm agents migrate --help
    Learn more: https://docs.claude-mpm.dev/agents/migration-guide
```

### 6.3 Migration Tools

#### One-Time Migration Command

```bash
# Check what would be migrated
claude-mpm agents migrate --check

# Migrate legacy agents to Git repository template
claude-mpm agents migrate --to-git-template

# Export legacy agents as Markdown
claude-mpm agents migrate --export ./my-agents/
```

**Implementation**:

```python
class LegacyAgentMigrator:
    """Migrates legacy agents to Git-based system."""

    def check_migration(self) -> Dict[str, Any]:
        """Check what legacy agents exist."""
        legacy = LegacyAgentBridge.detect_legacy_agents()
        return {
            "project_agents": len(legacy["project"]),
            "user_agents": len(legacy["user"]),
            "total": sum(len(agents) for agents in legacy.values()),
            "details": legacy
        }

    def export_to_markdown(self, output_dir: Path) -> Dict[str, Any]:
        """Export legacy agents as Markdown files."""
        legacy = LegacyAgentBridge.detect_legacy_agents()
        results = {"exported": [], "errors": []}

        output_dir.mkdir(parents=True, exist_ok=True)

        for tier, agent_files in legacy.items():
            for agent_file in agent_files:
                try:
                    # Convert JSON to Markdown
                    md_content = self._convert_to_markdown(agent_file)

                    # Write to output directory
                    output_file = output_dir / f"{agent_file.stem}.md"
                    output_file.write_text(md_content)

                    results["exported"].append(str(output_file))

                except Exception as e:
                    results["errors"].append({
                        "file": str(agent_file),
                        "error": str(e)
                    })

        return results

    def create_git_template(self, output_dir: Path) -> Dict[str, Any]:
        """Create a Git repository template from legacy agents."""
        # Export agents
        export_results = self.export_to_markdown(output_dir)

        # Create repository structure
        (output_dir / "agents").mkdir(exist_ok=True)

        # Move exported agents to agents/ subdirectory
        for exported_file in export_results["exported"]:
            src = Path(exported_file)
            dst = output_dir / "agents" / src.name
            src.rename(dst)

        # Create agents.json manifest
        manifest = {
            "version": "1.0",
            "agents": [
                f.name for f in (output_dir / "agents").glob("*.md")
            ]
        }
        (output_dir / "agents" / "agents.json").write_text(
            json.dumps(manifest, indent=2)
        )

        # Create README
        readme = self._create_readme_template()
        (output_dir / "README.md").write_text(readme)

        # Initialize git repository
        subprocess.run(["git", "init"], cwd=output_dir, check=True)
        subprocess.run(["git", "add", "."], cwd=output_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit: Migrated agents"],
            cwd=output_dir,
            check=True
        )

        return {
            "repository": str(output_dir),
            "agents": len(manifest["agents"]),
            "next_steps": [
                "1. Review agents in ./agents/ directory",
                "2. Create GitHub repository",
                "3. Push: git remote add origin <url> && git push -u origin main",
                "4. Configure: claude-mpm agents repo add <owner>/<repo>"
            ]
        }
```

### 6.4 Backward Compatibility Timeline

**v4.27.0 - v4.29.x** (Dec 2024 - Jan 2025):
- ✅ Both modes supported
- ✅ Feature flag: `agent_deployment.use_single_tier_mode`
- ✅ Default: Legacy mode (4-tier)
- ✅ Warnings: Info-level about future deprecation

**v4.30.0 - v4.99.x** (Feb 2025 - Q2 2025):
- ✅ Both modes supported
- ✅ Default: Single-tier mode
- ⚠️ Warnings: Warning-level about deprecation
- 📢 Migration tools available

**v5.0.0+** (Q2 2025):
- ❌ Legacy mode removed
- ✅ Single-tier only
- 🚫 Project/user agent directories no longer supported

---

## 7. Toolchain Detection Design

### 7.1 Detection Strategy

**Three-Level Detection**:

1. **Language Detection** (High Confidence)
   - Presence of package manager files
   - Minimum file count threshold
   - File extension analysis

2. **Framework Detection** (Medium Confidence)
   - Dependency analysis (package.json, requirements.txt, etc.)
   - Framework-specific file patterns
   - Configuration file detection

3. **Tool Detection** (Low Confidence)
   - Build tool indicators
   - CI/CD configuration
   - Infrastructure-as-code files

### 7.2 File Pattern Mapping

**Complete Mapping Table**:

| Language | Indicator Files | Extensions | Min Files | Confidence |
|----------|----------------|------------|-----------|------------|
| Python | pyproject.toml, setup.py, requirements.txt | .py | 3 | High |
| JavaScript | package.json, package-lock.json | .js, .jsx | 5 | High |
| TypeScript | tsconfig.json | .ts, .tsx | 3 | High |
| Rust | Cargo.toml | .rs | 2 | High |
| Go | go.mod | .go | 2 | High |
| Java | pom.xml, build.gradle | .java | 5 | High |
| C# | *.csproj, *.sln | .cs | 3 | High |
| Ruby | Gemfile | .rb | 3 | High |
| PHP | composer.json | .php | 5 | Medium |

### 7.3 Framework Detection Rules

**Python Frameworks**:
```python
PYTHON_FRAMEWORKS = {
    "django": {
        "dependencies": ["django"],
        "files": ["manage.py", "**/settings.py"],
        "score_threshold": 20
    },
    "flask": {
        "dependencies": ["flask"],
        "files": ["app.py", "wsgi.py"],
        "score_threshold": 15
    },
    "fastapi": {
        "dependencies": ["fastapi", "uvicorn"],
        "files": ["main.py"],
        "score_threshold": 15
    },
    "pyramid": {
        "dependencies": ["pyramid"],
        "files": ["development.ini"],
        "score_threshold": 15
    }
}
```

**JavaScript/TypeScript Frameworks**:
```python
JS_FRAMEWORKS = {
    "react": {
        "dependencies": ["react", "react-dom"],
        "files": ["src/App.jsx", "src/App.tsx", "public/index.html"],
        "score_threshold": 20
    },
    "nextjs": {
        "dependencies": ["next"],
        "files": ["next.config.js", "pages/_app.js"],
        "score_threshold": 25
    },
    "vue": {
        "dependencies": ["vue"],
        "files": ["vue.config.js", "src/App.vue"],
        "score_threshold": 20
    },
    "angular": {
        "dependencies": ["@angular/core"],
        "files": ["angular.json", "src/app/app.module.ts"],
        "score_threshold": 25
    },
    "svelte": {
        "dependencies": ["svelte"],
        "files": ["svelte.config.js", "src/App.svelte"],
        "score_threshold": 20
    }
}
```

### 7.4 Agent Selection Rules

**Mapping**: Detected Technology → Recommended Agent

```python
AGENT_SELECTION_RULES = {
    "core": {
        "always_recommend": ["engineer", "documentation", "qa", "research", "ops", "ticketing"]
    },
    "language_specific": {
        "python": {
            "base": ["engineer-python"],
            "frameworks": {
                "django": ["engineer-python-django", "ops-python-web"],
                "flask": ["engineer-python-flask", "ops-python-web"],
                "fastapi": ["engineer-python-fastapi", "ops-python-api"]
            }
        },
        "javascript": {
            "base": ["engineer-javascript"],
            "frameworks": {
                "react": ["engineer-react", "ops-frontend"],
                "nextjs": ["engineer-nextjs", "ops-fullstack"],
                "vue": ["engineer-vue", "ops-frontend"],
                "angular": ["engineer-angular", "ops-frontend"]
            }
        },
        "typescript": {
            "base": ["engineer-typescript"],
            "frameworks": {
                "react": ["engineer-react-typescript"],
                "nextjs": ["engineer-nextjs-typescript"]
            }
        },
        "rust": {
            "base": ["engineer-rust", "ops-rust"]
        },
        "go": {
            "base": ["engineer-go", "ops-go"]
        }
    },
    "infrastructure": {
        "docker": ["ops-docker"],
        "kubernetes": ["ops-kubernetes"],
        "terraform": ["ops-terraform"],
        "github_actions": ["ops-cicd-github"]
    }
}
```

---

## 8. Test Strategy

### 8.1 Unit Tests

**Coverage Target**: 85%+

#### GitSourceManager Tests
```python
# tests/unit/services/agents/sources/test_git_source_manager.py

def test_add_repository():
    """Test adding a repository."""

def test_repository_priority_resolution():
    """Test that lower priority number = higher precedence."""

def test_discover_agents_with_priority():
    """Test agent discovery with priority override."""

def test_sync_all_repositories():
    """Test syncing multiple repositories."""
```

#### SingleTierDeploymentService Tests
```python
# tests/unit/services/agents/deployment/test_single_tier_deployment_service.py

def test_deploy_agents_success():
    """Test successful deployment."""

def test_deploy_with_repository_filter():
    """Test filtering by repository."""

def test_deploy_with_agent_filter():
    """Test filtering by agent names."""

def test_version_comparison():
    """Test version-based skip logic."""
```

### 8.2 Integration Tests

**Focus**: End-to-end deployment flows

```python
# tests/integration/services/agents/test_single_tier_integration.py

def test_full_deployment_flow():
    """Test complete deployment: sync → discover → deploy."""

def test_multi_repository_deployment():
    """Test deployment from multiple repositories."""

def test_priority_override():
    """Test that higher priority repo wins for same agent."""

def test_minimal_mode():
    """Test deploying only 6 core agents."""

def test_auto_configure_mode():
    """Test toolchain detection and agent recommendation."""
```

### 8.3 CLI Tests

**Focus**: User interaction flows

```python
# tests/integration/cli/test_agents_cli.py

def test_agents_deploy_command():
    """Test: claude-mpm agents deploy"""

def test_agents_repo_add_command():
    """Test: claude-mpm agents repo add owner/repo"""

def test_agents_browse_command():
    """Test: claude-mpm agents browse"""

def test_agents_select_command():
    """Test: claude-mpm agents select"""
```

### 8.4 Edge Cases

**Critical Edge Cases to Test**:

1. **Network Failures**
   - GitHub unavailable
   - Timeout during sync
   - Partial sync (some files succeed, others fail)

2. **Cache Corruption**
   - Corrupted Markdown files
   - Missing cache directories
   - Mismatched content hashes

3. **Configuration Errors**
   - Invalid repository URL
   - Missing subdirectory
   - Conflicting priorities

4. **Version Conflicts**
   - Same agent in multiple repos with different versions
   - Agent version downgrade scenario
   - Missing version metadata

5. **Migration Scenarios**
   - Existing 4-tier agents present
   - Mixed JSON and Markdown agents
   - User agents in deprecated location

---

## 9. Risk Assessment

### 9.1 High-Risk Areas

#### 1. Breaking Existing User Workflows

**Risk**: Users with custom agents in `.claude-mpm/agents/` lose functionality

**Mitigation**:
- Phase 1: Backward compatibility bridge
- Clear deprecation warnings
- Migration tools provided
- Extended timeline (v4.27 → v5.0)

**Contingency**:
- Extend legacy support if migration adoption is low
- Provide manual migration assistance
- Document rollback procedures

#### 2. Git Repository Availability

**Risk**: Network failures prevent agent deployment

**Mitigation**:
- ETag-based caching (continue working offline with cached agents)
- Graceful degradation (deploy from cache if sync fails)
- Multiple repository support (fallback to alternative sources)

**Contingency**:
- Local repository cloning option
- Offline mode with pre-cached agents
- Bundle default agents with package

### 9.2 Medium-Risk Areas

#### 3. Configuration Complexity

**Risk**: Multi-repository configuration confuses users

**Mitigation**:
- Sensible defaults (bobmatnyc/claude-mpm-agents enabled by default)
- Clear documentation
- Interactive configuration wizard
- Configuration validation with helpful error messages

#### 4. Agent Discovery Performance

**Risk**: Discovering agents from multiple repositories is slow

**Mitigation**:
- Async/parallel repository syncing
- Incremental updates with ETag caching
- Manifest files to avoid file discovery

**Performance Target**:
- First sync: <10 seconds for 10 agents
- Subsequent syncs: <2 seconds with caching

### 9.3 Low-Risk Areas

#### 5. Markdown Parsing Errors

**Risk**: Invalid Markdown frontmatter breaks deployment

**Mitigation**:
- Validation on sync (fail fast)
- Clear error messages with file path
- Schema validation for frontmatter
- Fallback to default values for optional fields

#### 6. Version Comparison Issues

**Risk**: Version comparison logic has edge cases

**Mitigation**:
- Comprehensive test suite
- Support for semantic versioning (major.minor.patch)
- Fallback for non-standard versions
- Logging for version resolution decisions

---

## 10. Success Metrics

### 10.1 Implementation Metrics

**Phase Completion**:
- Phase 1: Foundation (Weeks 1-2)
- Phase 2: Deployment Service (Weeks 3-4)
- Phase 3: Selection Modes (Weeks 5-6)
- Phase 4: Selection UI (Weeks 7-8)

**Code Quality**:
- Test coverage: ≥85%
- All critical paths tested
- Integration tests passing
- No regressions in existing functionality

### 10.2 User Adoption Metrics

**Migration Success**:
- % of users who migrate within 3 months: Target 70%
- % of users with legacy agents remaining: Target <30% at v5.0.0 launch

**Performance Improvements**:
- Agent sync time: <2 seconds (cached)
- Deployment time: <5 seconds (10 agents)
- CLI response time: <500ms

**User Satisfaction**:
- Reduction in GitHub issues related to agent deployment
- Positive feedback on simplified architecture
- Increased adoption of custom agent repositories

---

## 11. Appendix

### 11.1 File Inventory

**Files to Create**:
1. `src/claude_mpm/services/agents/sources/git_repository.py` - GitRepository dataclass
2. `src/claude_mpm/services/agents/sources/git_source_manager.py` - GitSourceManager
3. `src/claude_mpm/services/agents/deployment/single_tier_deployment_service.py` - New deployment service
4. `src/claude_mpm/services/agents/deployment/legacy_agent_bridge.py` - Backward compatibility
5. `src/claude_mpm/services/agents/toolchain_detector.py` - Toolchain detection
6. `src/claude_mpm/services/agents/minimal_mode_deployer.py` - Minimal mode
7. `src/claude_mpm/services/agents/auto_configure_service.py` - Auto-configuration
8. `src/claude_mpm/cli/commands/agents_repo.py` - Repository management CLI
9. `src/claude_mpm/cli/commands/agents_browse.py` - Agent browsing UI
10. `docs/migration/agent-system-v5-migration-guide.md` - User migration guide

**Files to Modify**:
1. `src/claude_mpm/services/agents/deployment/agent_deployment.py` - Add single-tier mode
2. `src/claude_mpm/services/agents/sources/git_source_sync_service.py` - Enhance for multi-repo
3. `src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py` - Direct Markdown support
4. `src/claude_mpm/cli/commands/agents.py` - Add new subcommands
5. `src/claude_mpm/cli/parsers/agents_parser.py` - Add new arguments
6. `src/claude_mpm/config/agent_config.py` - Update configuration schema

**Files to Remove** (v5.0.0):
1. `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py`
2. Legacy migration commands (after v5.0.0)

### 11.2 Configuration Examples

**Minimal Configuration** (Uses defaults):
```yaml
# Use defaults - no configuration needed
# Default repo: bobmatnyc/claude-mpm-agents
```

**Custom Repository**:
```yaml
agent_repositories:
  use_default_repo: true
  repositories:
    - owner: "my-company"
      repo: "internal-agents"
      subdirectory: "agents/backend"
      branch: "production"
      enabled: true
      priority: 50  # Higher priority than default
```

**Custom-Only Mode** (No default repo):
```yaml
agent_repositories:
  use_default_repo: false
  repositories:
    - owner: "my-company"
      repo: "all-agents"
      subdirectory: "agents"
      branch: "main"
      enabled: true
      priority: 100
```

### 11.3 Agent Manifest Format

**agents.json** (Repository root or agents/ subdirectory):
```json
{
  "version": "1.0",
  "repository": {
    "owner": "bobmatnyc",
    "repo": "claude-mpm-agents",
    "subdirectory": "agents"
  },
  "agents": [
    "research.md",
    "engineer.md",
    "qa.md",
    "documentation.md",
    "security.md",
    "ops.md",
    "ticketing.md",
    "product_owner.md",
    "version_control.md",
    "project_organizer.md"
  ],
  "categories": {
    "core": ["research", "engineer", "qa", "documentation", "ops", "ticketing"],
    "specialized": ["security", "product_owner", "version_control", "project_organizer"]
  }
}
```

### 11.4 Agent Markdown Format

**Example**: `engineer.md`
```markdown
---
name: Engineer Agent
version: 2.5.0
model: claude-sonnet-4
description: Software engineering specialist for code implementation and architecture
routing:
  keywords:
    - code
    - implement
    - function
    - class
    - bug fix
  paths:
    - "**/*.py"
    - "**/*.js"
    - "**/*.ts"
  priority: 90
dependencies:
  python:
    - requests>=2.31.0
    - pytest>=7.4.0
  system:
    - git
    - docker
domains:
  - pattern: "**/*.py"
    authority: "python"
  - pattern: "**/*.js"
    authority: "javascript"
---

# Engineer Agent Instructions

You are a software engineering specialist focused on code implementation...

## Core Capabilities

1. **Code Implementation**
   - Write clean, maintainable code
   - Follow language-specific best practices
   ...
```

---

## 12. Conclusion

This research provides a comprehensive plan for migrating Claude MPM's agent deployment system from a complex 4-tier architecture to a simplified single-tier, Git-based system. The phased approach ensures backward compatibility during the transition while delivering immediate value through improved configuration, performance, and user experience.

**Key Benefits**:
1. ✅ Simplified architecture (4 tiers → 1 tier)
2. ✅ Git-based agent source (version control, collaboration)
3. ✅ Multi-repository support (priority-based)
4. ✅ Minimal and auto-configure modes
5. ✅ Improved performance (ETag caching, incremental sync)
6. ✅ Better user experience (agent browsing, selection, preview)

**Next Steps**:
1. Review and approve implementation plan
2. Create Phase 1 tickets in ticketing system
3. Begin implementation with GitSourceManager
4. User testing and feedback collection
5. Iterate based on user feedback

**Success Criteria**:
- All phases completed within 8 weeks
- Test coverage ≥85%
- Zero regressions in existing functionality
- Positive user feedback on simplified architecture
- 70% migration rate within 3 months of v5.0.0 release

---

**Research Complete**: 2025-11-30
**Status**: Ready for Implementation
**Recommendation**: Proceed with Phase 1 (Foundation) immediately
