# Service Layer API Catalog

> **Complete method-by-method reference for Dashboard Configuration UI**
>
> Generated: 2026-02-13
> Branch: `ui-agents-skills-config`
> Purpose: Enable REST API handler implementation directly from this documentation

---

## Table of Contents

1. [AgentDeploymentService](#1-agentdeploymentservice)
2. [SkillsDeployerService](#2-skillsdeployerservice)
3. [GitSourceManager](#3-gitsourcemanager)
4. [AutoConfigManagerService](#4-autoconfigmanagerservice)
5. [ToolchainAnalyzerService](#5-toolchainanalyzerservice)
6. [Config Singleton](#6-config-singleton)
7. [UnifiedConfig Pydantic Model](#7-unifiedconfig-pydantic-model)
8. [ConfigurationService](#8-configurationservice)
9. [SkillsConfig](#9-skillsconfig)
10. [SkillToAgentMapper](#10-skilltoagentmapper)
11. [Async Safety Summary](#11-async-safety-summary)
12. [CLI Usage Patterns](#12-cli-usage-patterns)

---

## 1. AgentDeploymentService

**File:** `src/claude_mpm/services/agents/deployment/agent_deployment.py:59`
**Inherits:** `ConfigServiceBase`, `AgentDeploymentInterface`

Manages the complete lifecycle of agent deployment: discovering templates, building YAML/MD files from JSON templates, version management, multi-source deployment, and cleanup.

### Constructor

```python
def __init__(
    self,
    templates_dir: Optional[Path] = None,
    base_agent_path: Optional[Path] = None,
    working_directory: Optional[Path] = None,
    config: Optional[Config] = None,
) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `templates_dir` | `Optional[Path]` | `paths.agents_dir / "templates"` | Directory containing agent JSON template files |
| `base_agent_path` | `Optional[Path]` | Auto-searched | Path to `base_agent.md` / `base_agent.json` |
| `working_directory` | `Optional[Path]` | `Path.cwd()` | User's working directory (for project agents) |
| `config` | `Optional[Config]` | Loads default | Configuration singleton instance |

**Side Effects:** Creates sub-services (`AgentTemplateBuilder`, `AgentVersionManager`, `AgentMetricsCollector`, `AgentEnvironmentManager`, `AgentValidator`, `BaseAgentLocator`, `DeploymentResultsManager`, `SingleAgentDeployer`, `AgentFileSystemManager`, `AgentDiscoveryService`, `MultiSourceAgentDeploymentService`, `AgentConfigurationManager`, `AgentFormatConverter`, `GitSourceManager`). Loads `AgentSourceConfiguration`.

**Async Safety:** Constructor is **synchronous**. Safe to call from sync context. For async handlers, instantiate in `asyncio.to_thread()` since it reads filesystem.

---

### `deploy_agents()`

```python
def deploy_agents(
    self,
    target_dir: Optional[Path] = None,
    force_rebuild: bool = False,
    deployment_mode: str = "update",
    config: Optional[Config] = None,
    use_async: bool = False,
) -> Dict[str, Any]
```

**Description:** Main entry point. Builds and deploys all agents by combining `base_agent.md` with JSON templates. Also syncs remote Git agent sources before deployment.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target_dir` | `Optional[Path]` | `.claude/agents/` | Target directory for agent MD files |
| `force_rebuild` | `bool` | `False` | Force rebuild even if versions match |
| `deployment_mode` | `str` | `"update"` | `"update"` (version-aware) or `"project"` (always deploy) |
| `config` | `Optional[Config]` | Default singleton | Configuration for exclusion rules |
| `use_async` | `bool` | `False` | Use async deployment (50-70% faster) |

**Returns:** `Dict[str, Any]`

```python
{
    "target_dir": Path,                # Deployment location
    "deployed": List[str],             # Newly deployed agent names
    "updated": List[str],              # Updated agent names
    "migrated": List[str],             # Agents migrated to new version format
    "converted": List[str],            # YAML files converted to MD
    "repaired": List[str],             # Agents with repaired frontmatter
    "skipped": List[str],              # Unchanged agents
    "errors": List[str],               # Deployment error messages
    "total": int,                      # Total agents processed
    "multi_source": bool,              # Whether multi-source deployment was used
    "agent_sources": Dict[str, str],   # agent_name -> source tier
    "cleanup": Dict[str, Any],         # Cleanup results (removed outdated agents)
    "remote_sources": Dict[str, Any],  # Git source sync results (if any synced)
    "metrics": {
        "duration_ms": float,
        "deployment_method": str,       # "async" or "sync"
    }
}
```

**Exceptions:**
- `AgentDeploymentError` - Custom error with deployment context (caught internally, added to `errors` list)
- Generic `Exception` - Wrapped and added to `errors` list

**Side Effects:**
- Creates/writes `.md` agent files in target directory
- Creates target directory if missing (`mkdir -p`)
- Syncs remote Git repositories (network I/O)
- Validates and repairs existing agent frontmatter
- Converts YAML agent files to MD format
- Cleans up excluded/outdated agents (file deletion)
- Updates deployment metrics

**Async Safety:** **BLOCKING** - Heavy filesystem I/O, network calls for Git sync, subprocess calls. **Must use `asyncio.to_thread()`** from async handlers.

**CLI Usage:** Called via `AgentsCommand._deploy_agents()` in `cli/commands/agents.py`:
```python
deployment_service = DeploymentServiceWrapper(AgentDeploymentService())
result = deployment_service.deploy(force=force)
```

---

### `deploy_agent()`

```python
def deploy_agent(
    self,
    agent_name: str,
    target_dir: Path,
    force_rebuild: bool = False,
) -> bool
```

**Description:** Deploy a single named agent to the specified directory.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent_name` | `str` | (required) | Name of agent to deploy (stem of template file) |
| `target_dir` | `Path` | (required) | Target directory for deployment |
| `force_rebuild` | `bool` | `False` | Force rebuild even if version is current |

**Returns:** `bool` - `True` if deployment succeeded, `False` otherwise.

**Exceptions:**
- `AgentDeploymentError` - If deployment fails (wraps generic exceptions with context)

**Side Effects:** Reads template file, writes agent MD file, filesystem I/O.

**Async Safety:** **BLOCKING** - Filesystem I/O. Use `asyncio.to_thread()`.

---

### `list_available_agents()`

```python
def list_available_agents(self) -> List[Dict[str, Any]]
```

**Description:** List all available agent templates from the templates directory.

**Returns:** `List[Dict[str, Any]]` - List of agent metadata dictionaries from `AgentDiscoveryService`.

**Side Effects:** Reads template directory (filesystem scan).

**Async Safety:** **BLOCKING** - Filesystem scan. Use `asyncio.to_thread()`.

**CLI Usage:** Called by `AgentsCommand._list_agents()`.

---

### `clean_deployment()`

```python
def clean_deployment(self, config_dir: Optional[Path] = None) -> Dict[str, Any]
```

**Description:** Remove all system-deployed agents from `.claude/` directory. User-created agents are preserved.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config_dir` | `Optional[Path]` | `working_directory / ".claude"` | Claude config directory |

**Returns:** `Dict[str, Any]` - Cleanup results (removed files, preserved files, errors).

**Side Effects:** Deletes agent files from filesystem.

**Async Safety:** **BLOCKING** - File deletion. Use `asyncio.to_thread()`.

**CLI Usage:** Called by `AgentsCommand._clean_agents()`.

---

### `verify_deployment()`

```python
def verify_deployment(self, config_dir: Optional[Path] = None) -> Dict[str, Any]
```

**Description:** Verify agent deployment and Claude configuration integrity.

**Returns:** `Dict[str, Any]` - Verification results with valid/invalid agents.

**Side Effects:** Reads filesystem only.

**Async Safety:** **BLOCKING** - Filesystem reads. Use `asyncio.to_thread()`.

---

### `validate_agent()`

```python
def validate_agent(self, agent_path: Path) -> tuple[bool, List[str]]
```

**Description:** Validate a single agent file's structure and configuration.

**Returns:** `tuple[bool, List[str]]` - `(is_valid, list_of_errors)`

**Checks:** YAML frontmatter presence, version field, required fields (`name`, `description`, `tools`).

**Side Effects:** Reads single file.

**Async Safety:** **BLOCKING** - Single file read. Use `asyncio.to_thread()`.

---

### `set_claude_environment()`

```python
def set_claude_environment(self, config_dir: Optional[Path] = None) -> Dict[str, str]
```

**Description:** Set Claude environment variables for agent discovery.

**Returns:** `Dict[str, str]` - Environment variables that were set.

**Side Effects:** Modifies `os.environ`.

**Async Safety:** Safe to call directly (in-memory operation only after path resolution).

---

### `get_deployment_metrics()` / `reset_metrics()`

```python
def get_deployment_metrics(self) -> Dict[str, Any]
def reset_metrics(self) -> None
```

**Description:** Get/reset internal deployment metrics (duration averages, success rates).

**Async Safety:** Safe (in-memory only).

---

### `get_deployment_status()`

```python
def get_deployment_status(self) -> Dict[str, Any]
```

**Description:** Get current deployment status and metrics from the metrics collector.

**Async Safety:** Safe (in-memory only).

---

### `deploy_system_instructions_explicit()`

```python
def deploy_system_instructions_explicit(
    self, target_dir: Optional[Path] = None, force_rebuild: bool = False
) -> Dict[str, Any]
```

**Description:** Explicitly deploy `INSTRUCTIONS.md`, `MEMORY.md`, `WORKFLOW.md` to `.claude/` directory. Only called when user explicitly requests it.

**Returns:** `Dict[str, Any]` - `{"deployed": [], "updated": [], "skipped": [], "errors": []}`

**Side Effects:** Creates/writes markdown files in `.claude/` directory.

**Async Safety:** **BLOCKING** - Filesystem writes. Use `asyncio.to_thread()`.

---

## 2. SkillsDeployerService

**File:** `src/claude_mpm/services/skills_deployer.py:39`
**Inherits:** `LoggerMixin`

Manages downloading skills from GitHub repositories and deploying them to Claude Code's `~/.claude/skills/` directory. Supports collection management, selective deployment, and orphan cleanup.

### Constructor

```python
def __init__(
    self,
    repo_url: Optional[str] = None,
    toolchain_analyzer: Optional[any] = None,
) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `repo_url` | `Optional[str]` | `"https://github.com/bobmatnyc/claude-mpm-skills"` | GitHub repo URL |
| `toolchain_analyzer` | `Optional[any]` | `None` | Optional `ToolchainAnalyzer` for auto-detection |

**Side Effects:** Creates `~/.claude/skills/` directory if missing. Instantiates `SkillsConfig`.

**Async Safety:** Constructor is **synchronous**, safe for sync context. Minor filesystem check (mkdir).

---

### `deploy_skills()`

```python
def deploy_skills(
    self,
    collection: Optional[str] = None,
    toolchain: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    force: bool = False,
    selective: bool = True,
    project_root: Optional[Path] = None,
    skill_names: Optional[List[str]] = None,
) -> Dict
```

**Description:** Main entry point. Downloads skills from a GitHub collection, filters by toolchain/category, applies selective filtering (agent-referenced only), deploys to `~/.claude/skills/`, and cleans orphaned skills.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `collection` | `Optional[str]` | Default collection from config | Collection name to deploy from |
| `toolchain` | `Optional[List[str]]` | `None` (all) | Filter by toolchain (e.g., `["python", "javascript"]`) |
| `categories` | `Optional[List[str]]` | `None` (all) | Filter by category (e.g., `["testing"]`) |
| `force` | `bool` | `False` | Overwrite existing skills |
| `selective` | `bool` | `True` | Only deploy skills referenced by agents |
| `project_root` | `Optional[Path]` | Auto-detected | Project root for finding agents |
| `skill_names` | `Optional[List[str]]` | `None` | Specific skill names (overrides selective) |

**Returns:**

```python
{
    "deployed_count": int,
    "skipped_count": int,
    "errors": List[str],
    "deployed_skills": List[str],
    "skipped_skills": List[str],
    "restart_required": bool,
    "restart_instructions": str,
    "collection": str,
    "selective_mode": bool,
    "total_available": int,
    "cleanup": {
        "removed_count": int,
        "removed_skills": List[str]
    }
}
```

**Side Effects:**
- Git clone/pull operations (network I/O, subprocess calls)
- Copies skill directories to `~/.claude/skills/`
- Reads `configuration.yaml` for selective filtering
- Scans deployed agents for skill references
- Updates `configuration.yaml` with agent_referenced skills
- Removes orphaned skill directories
- Checks if Claude Code process is running (subprocess: `ps aux`)
- Tracks deployed skills in `.mpm-deployed-skills.json`

**Exceptions:** Internal errors are caught and returned in `errors` list. Download failures raise to caller (caught at entry).

**Async Safety:** **BLOCKING** - Heavy network I/O (Git), filesystem I/O (copy), subprocess calls. **Must use `asyncio.to_thread()`**.

**CLI Usage:** Called by `SkillsManagementCommand._deploy_from_github()`:
```python
deployer = SkillsDeployerService()
result = deployer.deploy_skills(collection=collection, toolchain=toolchain, ...)
```

---

### `list_available_skills()`

```python
def list_available_skills(self, collection: Optional[str] = None) -> Dict
```

**Description:** List all available skills from a GitHub collection by downloading the manifest.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `collection` | `Optional[str]` | Default from config | Collection to list from |

**Returns:**

```python
{
    "total_skills": int,
    "by_category": Dict[str, List[Dict]],    # category -> skills
    "by_toolchain": Dict[str, List[Dict]],   # toolchain -> skills
    "skills": List[Dict],                     # Full skill metadata list
    "collection": str,
    "error": Optional[str]                    # Only on failure
}
```

**Side Effects:** Git clone/pull (network I/O).

**Async Safety:** **BLOCKING** - Network I/O. Use `asyncio.to_thread()`.

**CLI Usage:** Called by `SkillsManagementCommand._list_available_github_skills()`.

---

### `check_deployed_skills()`

```python
def check_deployed_skills(self) -> Dict
```

**Description:** Scan `~/.claude/skills/` for currently deployed skills.

**Returns:**

```python
{
    "deployed_count": int,
    "skills": List[{"name": str, "path": str}],
    "claude_skills_dir": str
}
```

**Side Effects:** Filesystem scan only.

**Async Safety:** **BLOCKING** - Directory iteration. Use `asyncio.to_thread()`.

**CLI Usage:** Called by `SkillsManagementCommand._check_deployed_skills()`.

---

### `remove_skills()`

```python
def remove_skills(self, skill_names: Optional[List[str]] = None) -> Dict
```

**Description:** Remove deployed skills. If `skill_names` is `None`, removes ALL skills.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skill_names` | `Optional[List[str]]` | `None` (remove all) | Specific skills to remove |

**Returns:**

```python
{
    "removed_count": int,
    "removed_skills": List[str],
    "errors": List[str]
}
```

**Side Effects:** Deletes directories from `~/.claude/skills/`. Validates path safety (no traversal). Untracks skills from deployment index.

**Async Safety:** **BLOCKING** - File deletion. Use `asyncio.to_thread()`.

**CLI Usage:** Called by `SkillsManagementCommand._remove_skills()`.

---

### Collection Management Methods

#### `list_collections()`

```python
def list_collections(self) -> Dict[str, Any]
```

**Returns:** `{"collections": Dict, "default_collection": str, "enabled_count": int, "total_count": int}`

#### `add_collection()`

```python
def add_collection(self, name: str, url: str, priority: int = 99) -> Dict[str, Any]
```

#### `remove_collection()`

```python
def remove_collection(self, name: str) -> Dict[str, Any]
```

**Side Effects:** Also removes collection directory from `~/.claude/skills/{name}`.

#### `enable_collection()` / `disable_collection()`

```python
def enable_collection(self, name: str) -> Dict[str, Any]
def disable_collection(self, name: str) -> Dict[str, Any]
```

#### `set_default_collection()`

```python
def set_default_collection(self, name: str) -> Dict[str, Any]
```

All collection methods delegate to `SkillsConfig`. **Async Safety:** Minor filesystem I/O (JSON read/write). Use `asyncio.to_thread()` for safety.

---

## 3. GitSourceManager

**File:** `src/claude_mpm/services/agents/git_source_manager.py:19`

Coordinates syncing and discovery across multiple Git repositories for agent sources. Handles ETag-based incremental updates, agent discovery from cached repos, and priority-based resolution.

### Constructor

```python
def __init__(self, cache_root: Optional[Path] = None) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cache_root` | `Optional[Path]` | `~/.claude-mpm/cache/agents/` | Root directory for repo caches |

**Side Effects:** Creates cache directory (`mkdir -p`).

---

### `sync_repository()`

```python
def sync_repository(
    self,
    repo: GitRepository,
    force: bool = False,
    show_progress: bool = True,
) -> Dict[str, Any]
```

**Description:** Sync a single Git repository. Downloads agent files using ETag-based caching, then discovers agents in the cached directory.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `repo` | `GitRepository` | (required) | Repository model to sync |
| `force` | `bool` | `False` | Force sync (bypasses ETag cache) |
| `show_progress` | `bool` | `True` | Show ASCII progress bar |

**Returns:**

```python
{
    "synced": bool,                    # Overall success
    "etag": str,                       # HTTP ETag from sync
    "files_updated": int,              # Files downloaded
    "files_added": int,                # New files
    "files_removed": int,              # Deleted files
    "files_cached": int,               # Cache hits (304)
    "agents_discovered": List[str],    # Agent names found
    "timestamp": str,                  # ISO timestamp
    "error": str                       # Error message (if failed)
}
```

**Side Effects:** Network I/O (HTTP GET from `raw.githubusercontent.com`), filesystem writes (cached agent files), stores repo metadata in `_repo_metadata`.

**Async Safety:** **BLOCKING** - Network I/O, filesystem writes. Use `asyncio.to_thread()`.

**CLI Usage:** Called via `agent_source.py` handlers:
```python
manager = GitSourceManager()
result = manager.sync_repository(repo, force=force)
```

---

### `sync_all_repositories()`

```python
def sync_all_repositories(
    self,
    repos: List[GitRepository],
    force: bool = False,
    show_progress: bool = True,
) -> Dict[str, Dict[str, Any]]
```

**Description:** Sync multiple repositories in priority order. Individual failures don't stop overall sync.

**Returns:** `Dict[str, Dict[str, Any]]` - Maps repo identifiers to their sync results.

**Async Safety:** **BLOCKING**. Use `asyncio.to_thread()`.

---

### `list_cached_agents()`

```python
def list_cached_agents(
    self, repo_identifier: Optional[str] = None
) -> List[Dict[str, Any]]
```

**Description:** List all cached agents with optional repo filter. Deduplicates by `agent_id`. Enriches with source attribution (priority, URL).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `repo_identifier` | `Optional[str]` | `None` (all repos) | Filter to specific repo (e.g., `"owner/repo/agents"`) |

**Returns:** List of agent metadata dicts with `name`, `version`, `path`, `repository`, `source`, `priority`, `source_url`.

**Side Effects:** Reads cached directories. Loads repo metadata from `AgentSourceConfiguration` if not already loaded.

**Async Safety:** **BLOCKING** - Filesystem traversal, potential config file read. Use `asyncio.to_thread()`.

**CLI Usage:** Called by `agent_source.py` for `claude-mpm agents available`.

---

### `list_cached_agents_with_filters()`

```python
def list_cached_agents_with_filters(
    self,
    repo_identifier: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]
```

**Description:** Extended listing with semantic filtering using AUTO-DEPLOY-INDEX.md.

| Filter Key | Example | Description |
|------------|---------|-------------|
| `category` | `"engineer/backend"` | Agent category path |
| `language` | `"python"` | Programming language |
| `framework` | `"react"` | Framework name |
| `platform` | `"vercel"` | Deployment platform |
| `specialization` | `"data"` | Agent specialization |

**Returns:** Filtered list of agent metadata dicts.

**Async Safety:** **BLOCKING**. Use `asyncio.to_thread()`.

**CLI Usage:** Called by `agents_discover.py` for `claude-mpm agents discover`.

---

### `get_agent_path()`

```python
def get_agent_path(
    self, agent_name: str, repo_identifier: Optional[str] = None
) -> Optional[Path]
```

**Description:** Get cached filesystem path for a specific agent by name.

**Returns:** `Optional[Path]` - Path to cached agent file, or `None`.

**Async Safety:** **BLOCKING** - Delegates to `list_cached_agents()`.

---

## 4. AutoConfigManagerService

**File:** `src/claude_mpm/services/agents/auto_config_manager.py:40`
**Inherits:** `BaseService`, `IAutoConfigManager`

Orchestrates the complete auto-configuration workflow: toolchain analysis, agent recommendation, validation, user confirmation, deployment, and rollback.

### Constructor

```python
def __init__(
    self,
    toolchain_analyzer: Optional[Any] = None,
    agent_recommender: Optional[AgentRecommenderService] = None,
    agent_registry: Optional[IAgentRegistry] = None,
    agent_deployment: Optional[Any] = None,
    config: Optional[Dict[str, Any]] = None,
    container: Optional[Any] = None,
) -> None
```

All parameters are optional - services are lazily initialized on first use.

**Side Effects:** None at construction time.

---

### `auto_configure()` (async)

```python
async def auto_configure(
    self,
    project_path: Path,
    confirmation_required: bool = True,
    dry_run: bool = False,
    min_confidence: float = 0.8,
    observer: Optional[IDeploymentObserver] = None,
) -> ConfigurationResult
```

**Description:** Full end-to-end configuration: analyze toolchain -> recommend agents -> validate -> confirm -> deploy -> verify.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_path` | `Path` | (required) | Project root directory |
| `confirmation_required` | `bool` | `True` | Require user approval before deployment |
| `dry_run` | `bool` | `False` | Preview only, no deployment |
| `min_confidence` | `float` | `0.8` | Minimum confidence score (0.0-1.0) |
| `observer` | `Optional[IDeploymentObserver]` | `NullObserver` | Progress tracking observer |

**Returns:** `ConfigurationResult` dataclass with fields:
- `status`: `OperationResult` enum (`SUCCESS`, `ERROR`, `CANCELLED`, `WARNING`, `FAILED`)
- `message`: Human-readable message
- `recommendations`: `List[AgentRecommendation]`
- `deployed_agents`: `List[str]`
- `failed_agents`: `List[str]`
- `validation_errors`: `List[str]`
- `validation_warnings`: `List[str]`
- `metadata`: `Dict[str, Any]` (includes `duration_ms`, `dry_run`, `error`, `traceback`)

**Exceptions:**
- `FileNotFoundError` - If `project_path` doesn't exist
- `ValueError` - If `min_confidence` is out of range or path is not a directory
- `PermissionError` - If unable to write to project directory

**Side Effects:**
- Filesystem scans for toolchain detection
- Agent deployment (file writes)
- Saves `auto-config.yaml` to `.claude-mpm/` directory
- Rollback on partial failure (deletes deployed agents)

**Async Safety:** This method **IS async**. Call directly from async handlers. Internally calls synchronous methods.

**CLI Usage:** Called by `AutoConfigureCommand` in `auto_configure.py`:
```python
service = AutoConfigManagerService()
result = asyncio.run(service.auto_configure(project_path, dry_run=dry_run))
```

---

### `validate_configuration()`

```python
def validate_configuration(
    self, recommendations: List[AgentRecommendation]
) -> ValidationResult
```

**Description:** Validate proposed agent configuration before deployment. Checks agent existence, confidence thresholds, role conflicts, and recommendation concerns.

**Returns:** `ValidationResult` with `is_valid`, `issues` list, `validated_agents`, `metadata`.

**Exceptions:** `ValueError` if `recommendations` list is empty.

**Side Effects:** None (read-only validation).

**Async Safety:** Safe to call directly (no I/O).

---

### `preview_configuration()`

```python
def preview_configuration(
    self, project_path: Path, min_confidence: float = 0.8
) -> ConfigurationPreview
```

**Description:** Preview what would be configured without making changes.

**Returns:** `ConfigurationPreview` with `recommendations`, `validation_result`, `detected_toolchain`, `estimated_deployment_time`, `would_deploy`, `would_skip`.

**Side Effects:** Filesystem scan for toolchain analysis (read-only).

**Async Safety:** **BLOCKING** - Uses `asyncio.get_event_loop().run_until_complete()` internally. Call from sync context or wrap in `asyncio.to_thread()`.

---

## 5. ToolchainAnalyzerService

**File:** `src/claude_mpm/services/project/toolchain_analyzer.py:39`
**Inherits:** `BaseService`, `IToolchainAnalyzer`

Analyzes project toolchains using pluggable detection strategies. Detects languages, frameworks, build tools, package managers, and deployment targets.

### Constructor

```python
def __init__(
    self,
    project_analyzer: Optional[any] = None,
    dependency_analyzer: Optional[any] = None,
    config: Optional[Dict] = None,
) -> None
```

**Side Effects:** Registers default strategies (NodeJS, Python, Rust, Go). Initializes analysis cache (5-minute TTL, max 100 entries).

---

### `analyze_toolchain()`

```python
def analyze_toolchain(self, project_path: Path) -> ToolchainAnalysis
```

**Description:** Complete toolchain analysis in a single call. Detects language, frameworks, build tools, package managers, dev tools, and deployment target.

**Returns:** `ToolchainAnalysis` dataclass with:
- `project_path`: `Path`
- `language_detection`: `LanguageDetection` (primary_language, primary_confidence, secondary_languages, language_percentages)
- `frameworks`: `List[Framework]` (name, version, framework_type, confidence)
- `deployment_target`: `Optional[DeploymentTarget]` (target_type, platform, confidence, requires_ops_agent)
- `build_tools`: `List[ToolchainComponent]`
- `package_managers`: `List[ToolchainComponent]`
- `development_tools`: `List[ToolchainComponent]`
- `overall_confidence`: `ConfidenceLevel` (HIGH, MEDIUM, LOW, VERY_LOW)
- `analysis_timestamp`: `float`
- `metadata`: `Dict` (analysis_duration_ms, strategies_used)

**Exceptions:**
- `FileNotFoundError` - If `project_path` doesn't exist
- `ValueError` - If `project_path` is not a directory

**Side Effects:** Filesystem scans (reads config files, checks for file existence). Uses internal cache.

**Async Safety:** **BLOCKING** - Filesystem scans. Use `asyncio.to_thread()`.

**CLI Usage:** Used internally by `AutoConfigManagerService`, not directly by CLI.

---

### `detect_language()`

```python
def detect_language(self, project_path: Path) -> LanguageDetection
```

**Description:** Detect primary and secondary languages. Runs all registered strategies and picks highest confidence.

**Returns:** `LanguageDetection` with `primary_language`, `primary_confidence`, `secondary_languages`, `language_percentages`.

**Async Safety:** **BLOCKING** - Filesystem scans.

---

### `detect_frameworks()`

```python
def detect_frameworks(self, project_path: Path) -> List[Framework]
```

**Description:** Detect frameworks and their versions. Deduplicates by name (case-insensitive). Sorted by confidence and popularity.

**Returns:** `List[Framework]` with `name`, `version`, `framework_type`, `confidence`, `popularity_score`.

**Async Safety:** **BLOCKING** - Filesystem scans.

---

### `detect_deployment_target()`

```python
def detect_deployment_target(self, project_path: Path) -> Optional[DeploymentTarget]
```

**Description:** Detect intended deployment environment by checking for Docker, Kubernetes, Vercel, AWS, Terraform, and GCP indicators.

**Returns:** `Optional[DeploymentTarget]` with `target_type`, `platform`, `confidence`, `requires_ops_agent`.

**Async Safety:** **BLOCKING** - Filesystem checks.

---

### `register_strategy()`

```python
def register_strategy(self, name: str, strategy: IToolchainDetectionStrategy) -> None
```

**Description:** Register a new detection strategy at runtime.

**Async Safety:** Safe (in-memory only).

---

## 6. Config Singleton

**File:** `src/claude_mpm/core/config.py:25`

Thread-safe singleton configuration manager. Loads from YAML/JSON files, environment variables, and dictionaries. Supports dot-notation access.

### Constructor

```python
def __init__(
    self,
    config: Optional[Dict[str, Any]] = None,
    config_file: Optional[Union[str, Path]] = None,
    env_prefix: str = "CLAUDE_PM_",
) -> None
```

**Singleton behavior:** Only the first `Config()` call actually initializes. Subsequent calls reuse the same instance.

**Loading priority:**
1. `config` dict parameter
2. `config_file` parameter
3. `.claude-mpm/configuration.yaml` in CWD
4. `.claude-mpm/configuration.yml` in CWD
5. Environment variables with `CLAUDE_PM_` prefix
6. Default values

---

### `get()`

```python
def get(self, key: str, default: Any = None) -> Any
```

**Description:** Get config value with dot-notation support.

```python
config.get("agent_deployment.filter_non_mpm_agents", True)
config.get("logging.level", "INFO")
```

**Async Safety:** Safe (in-memory dict lookup).

---

### `set()`

```python
def set(self, key: str, value: Any) -> None
```

**Description:** Set config value with dot-notation. Creates nested dicts as needed.

**Async Safety:** Safe (in-memory dict write) but not thread-safe for concurrent writes.

---

### `validate_configuration()`

```python
def validate_configuration(self) -> Tuple[bool, List[str], List[str]]
```

**Description:** Validate loaded configuration programmatically.

**Returns:** `(is_valid: bool, errors: List[str], warnings: List[str])`

**Async Safety:** Safe (in-memory).

**CLI Usage:** Called by `ConfigCommand._validate_config()`:
```python
config = Config()
is_valid, errors, warnings = config.validate_configuration()
```

---

### `reset_singleton()` (classmethod)

```python
@classmethod
def reset_singleton(cls) -> None
```

**Description:** Reset singleton state. Primarily for testing.

---

### `load_file()`

```python
def load_file(self, file_path: Union[str, Path], is_initial_load: bool = True) -> None
```

**Description:** Load configuration from a YAML or JSON file.

**Side Effects:** Reads file, merges into internal config dict.

**Async Safety:** **BLOCKING** - File read. Use `asyncio.to_thread()` if calling after initialization.

---

## 7. UnifiedConfig Pydantic Model

**File:** `src/claude_mpm/core/unified_config.py:286`
**Inherits:** `pydantic_settings.BaseSettings`

Type-safe configuration model with Pydantic validation and environment variable support.

### Configuration Sections

| Section | Model Class | Key Fields |
|---------|-------------|------------|
| `network` | `NetworkConfig` | `socketio_host`, `socketio_port`, `connection_timeout`, `max_retries` |
| `logging` | `LoggingConfig` | `level` (validated), `max_size_mb`, `retention_days`, `format` |
| `agents` | `AgentConfig` | `enabled: List[str]`, `required: List[str]` (7 core), `include_universal`, `auto_discover`, `precedence`, `enable_hot_reload`, `cache_ttl_seconds` |
| `skills` | `SkillConfig` | `enabled: List[str]`, `auto_detect_dependencies: bool` |
| `memory` | `MemoryConfig` | `enabled`, `auto_learning`, `default_size_kb`, `max_sections` |
| `security` | `SecurityConfig` | `enable_path_validation`, `max_file_size_mb`, `allowed_file_extensions` |
| `performance` | `PerformanceConfig` | `startup_timeout`, `hook_timeout_seconds`, `cache_max_size_mb` |
| `sessions` | `SessionConfig` | `max_age_minutes`, `cleanup_max_age_hours` |
| `development` | `DevelopmentConfig` | `debug`, `verbose`, `enable_profiling` |
| `documentation` | `DocumentationConfig` | `docs_path`, `attach_to_tickets`, `backup_locally` |

### Key Pydantic Settings

```python
class Config:
    env_prefix = "CLAUDE_MPM_"
    env_nested_delimiter = "__"
    case_sensitive = False
    validate_assignment = True
    extra = "allow"   # Backward compatibility
```

### `AgentConfig` Detail (Most Relevant for UI)

```python
class AgentConfig(BaseModel):
    enabled: List[str] = []              # Explicit agent IDs to deploy
    required: List[str] = [              # Always-deployed core agents
        "engineer", "research", "qa",
        "web-qa", "documentation", "ops", "ticketing"
    ]
    include_universal: bool = True       # Auto-include universal category agents
    auto_discover: bool = False          # Deprecated
    precedence: List[str] = ["project", "user", "system"]
    enable_hot_reload: bool = True
    cache_ttl_seconds: int = 3600
    validate_on_load: bool = True
    strict_validation: bool = False
    max_concurrent_operations: int = 10
```

### `SkillConfig` Detail

```python
class SkillConfig(BaseModel):
    enabled: List[str] = []              # Explicit skill IDs to deploy
    auto_detect_dependencies: bool = True # Auto-include agent-required skills
```

### Key Methods

#### `get_nested()` / `set_nested()`

```python
def get_nested(self, key: str, default: Any = None) -> Any
def set_nested(self, key: str, value: Any) -> None
```

Dot-notation access: `config.get_nested("agents.enabled")`.

#### `to_legacy_dict()`

```python
def to_legacy_dict(self) -> Dict[str, Any]
```

Converts to flat dictionary compatible with legacy `Config` class.

#### `is_development()` / `is_production()`

```python
def is_development(self) -> bool
def is_production(self) -> bool
```

---

## 8. ConfigurationService

**File:** `src/claude_mpm/core/unified_config.py:473`

Injectable service wrapping `UnifiedConfig` for dependency injection.

### Key Methods

```python
class ConfigurationService:
    def __init__(self, config: Optional[UnifiedConfig] = None) -> None

    @property
    def config(self) -> UnifiedConfig     # Get unified config

    def get_legacy_config(self) -> Config  # Get legacy Config wrapper

    def get(self, key: str, default: Any = None) -> Any  # Dot-notation get
    def set(self, key: str, value: Any) -> None           # Dot-notation set

    def reload(self) -> None               # Reload from sources
    def validate(self) -> bool             # Validate config (raises ConfigurationError)

    def export_to_file(self, file_path: Union[str, Path], format: str = "yaml") -> None
```

**Config File Search Order:**
1. `.claude-mpm/configuration.yaml` (CWD)
2. `.claude-mpm/configuration.yml` (CWD)
3. `~/.claude-mpm/configuration.yaml`
4. `~/.claude-mpm/configuration.yml`

**Async Safety:** `reload()` and `export_to_file()` are **BLOCKING** (file I/O). Others are safe.

---

## 9. SkillsConfig

**File:** `src/claude_mpm/services/skills_config.py:49`
**Inherits:** `LoggerMixin`

Manages skill collection configurations stored in `~/.claude-mpm/config.json` under the `"skills"` key.

### Constructor

```python
def __init__(self) -> None
```

**Side Effects:** Creates `~/.claude-mpm/config.json` with default config if missing. Ensures `"skills"` section exists.

### Methods

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_collections()` | `() -> Dict[str, Dict[str, Any]]` | All collections | Returns all collection configs |
| `get_enabled_collections()` | `() -> Dict[str, Dict[str, Any]]` | Enabled only | Filters to enabled collections |
| `get_collections_by_priority()` | `(enabled_only: bool = True) -> List[tuple[str, Dict]]` | Sorted list | Sorted by priority (lower = higher) |
| `get_default_collection()` | `() -> str` | Default name | Returns default collection name |
| `get_collection()` | `(name: str) -> Optional[Dict]` | Collection config | Single collection lookup |
| `add_collection()` | `(name: str, url: str, priority: int = 99) -> Dict` | Operation result | Add new collection |
| `remove_collection()` | `(name: str) -> Dict` | Operation result | Remove collection |
| `enable_collection()` | `(name: str) -> Dict` | Operation result | Enable disabled collection |
| `disable_collection()` | `(name: str) -> Dict` | Operation result | Disable without removing |
| `set_default_collection()` | `(name: str) -> Dict` | Operation result | Set default for deployments |
| `update_collection_timestamp()` | `(name: str) -> None` | None | Update `last_update` timestamp |

**Storage:** `~/.claude-mpm/config.json`

```json
{
    "version": "1.0",
    "skills": {
        "collections": {
            "claude-mpm": {
                "url": "https://github.com/bobmatnyc/claude-mpm-skills",
                "enabled": true,
                "priority": 1,
                "last_update": "2025-11-21T15:30:00Z"
            }
        },
        "default_collection": "claude-mpm"
    }
}
```

**Async Safety:** All methods involve file I/O (JSON read/write). Use `asyncio.to_thread()`.

---

## 10. SkillToAgentMapper

**File:** `src/claude_mpm/services/skills/skill_to_agent_mapper.py:51`

Bidirectional mapping between skill paths and agent IDs using YAML configuration.

### Constructor

```python
def __init__(self, config_path: Optional[Path] = None) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config_path` | `Optional[Path]` | `src/claude_mpm/config/skill_to_agent_mapping.yaml` | YAML config file |

**Exceptions:**
- `FileNotFoundError` - Config file not found
- `yaml.YAMLError` - Invalid YAML
- `ValueError` - Missing required sections (`skill_mappings`, `all_agents_list`)

**Side Effects:** Reads and parses YAML config file. Builds in-memory indexes.

---

### `get_agents_for_skill()`

```python
def get_agents_for_skill(self, skill_path: str) -> List[str]
```

**Description:** Forward lookup: skill path -> list of agent IDs. Falls back to pattern-based inference if no exact match.

**Example:** `get_agents_for_skill("toolchains/python/frameworks/django")` -> `["python-engineer", "data-engineer", "engineer", "api-qa"]`

**Async Safety:** Safe (in-memory lookup).

---

### `get_skills_for_agent()`

```python
def get_skills_for_agent(self, agent_id: str) -> List[str]
```

**Description:** Inverse lookup: agent ID -> list of skill paths.

**Example:** `get_skills_for_agent("python-engineer")` -> `["toolchains/python/...", ...]`

**Async Safety:** Safe (in-memory lookup).

---

### `infer_agents_from_pattern()`

```python
def infer_agents_from_pattern(self, skill_path: str) -> List[str]
```

**Description:** Pattern-based inference for unmapped skills. Matches against language, framework, and domain patterns from `inference_rules` config section.

**Async Safety:** Safe (in-memory).

---

### Other Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `get_all_mapped_skills()` | `List[str]` | All skill paths with explicit mappings (sorted) |
| `get_all_agents()` | `List[str]` | All agent IDs in mappings (sorted) |
| `is_skill_mapped(skill_path)` | `bool` | Check if skill has explicit mapping |
| `get_mapping_stats()` | `Dict[str, Any]` | Statistics (total_skills, total_agents, averages, config_version) |

All are in-memory lookups. **Async Safety:** Safe.

---

## 11. Async Safety Summary

### Safe to Call Directly from Async Handlers

| Service | Method | Reason |
|---------|--------|--------|
| `Config` | `get()`, `set()`, `validate_configuration()` | In-memory dict operations |
| `UnifiedConfig` | `get_nested()`, `set_nested()`, `is_development()` | Pydantic model access |
| `ConfigurationService` | `get()`, `set()`, `validate()` | Delegates to in-memory |
| `SkillToAgentMapper` | All `get_*` methods | In-memory index lookups |
| `AgentDeploymentService` | `get_deployment_metrics()`, `reset_metrics()`, `get_deployment_status()` | In-memory state |
| `AutoConfigManagerService` | `auto_configure()`, `validate_configuration()` | Already async / no I/O |

### MUST Use `asyncio.to_thread()` from Async Handlers

| Service | Method | Reason |
|---------|--------|--------|
| `AgentDeploymentService` | `deploy_agents()`, `deploy_agent()`, `list_available_agents()`, `clean_deployment()`, `verify_deployment()`, `validate_agent()` | Heavy filesystem I/O, Git network calls |
| `SkillsDeployerService` | `deploy_skills()`, `list_available_skills()`, `check_deployed_skills()`, `remove_skills()`, all collection methods | Git clone/pull (network + subprocess), filesystem copies |
| `GitSourceManager` | `sync_repository()`, `sync_all_repositories()`, `list_cached_agents()`, `list_cached_agents_with_filters()`, `get_agent_path()` | HTTP requests, filesystem traversal |
| `ToolchainAnalyzerService` | `analyze_toolchain()`, `detect_language()`, `detect_frameworks()`, `detect_deployment_target()` | Filesystem scans |
| `SkillsConfig` | All methods | JSON file read/write |
| `ConfigurationService` | `reload()`, `export_to_file()` | File I/O |
| `AutoConfigManagerService` | `preview_configuration()` | Uses `run_until_complete()` internally |

### Recommended Wrapper Pattern for FastAPI

```python
from asyncio import to_thread

# In your FastAPI route:
@router.post("/api/agents/deploy")
async def deploy_agents(request: DeployRequest):
    service = AgentDeploymentService()
    result = await to_thread(
        service.deploy_agents,
        force_rebuild=request.force,
        deployment_mode=request.mode,
    )
    return result

@router.get("/api/config")
async def get_config():
    config = Config()
    # Safe to call directly - in-memory
    return config.validate_configuration()
```

---

## 12. CLI Usage Patterns

### How CLI Commands Instantiate Services

All CLI commands use **lazy-loaded properties** for service instantiation:

```python
# From cli/commands/agents.py
class AgentsCommand(AgentCommand):
    @property
    def deployment_service(self):
        if self._deployment_service is None:
            base_service = AgentDeploymentService()
            self._deployment_service = DeploymentServiceWrapper(base_service)
        return self._deployment_service

# From cli/commands/skills.py
class SkillsManagementCommand(BaseCommand):
    @property
    def skills_deployer(self) -> SkillsDeployerService:
        if self._skills_deployer is None:
            self._skills_deployer = SkillsDeployerService()
        return self._skills_deployer
```

### CLI Command to Service Method Mapping

| CLI Command | Service | Method |
|-------------|---------|--------|
| `claude-mpm agents` | `AgentDeploymentService` | `get_deployment_metrics()` via wrapper |
| `claude-mpm agents list` | `AgentListingService` | Wraps `list_available_agents()` |
| `claude-mpm agents deploy` | `AgentDeploymentService` | `deploy_agents(force_rebuild=False)` |
| `claude-mpm agents force-deploy` | `AgentDeploymentService` | `deploy_agents(force_rebuild=True)` |
| `claude-mpm agents clean` | `AgentDeploymentService` | `clean_deployment()` |
| `claude-mpm agents view <name>` | `AgentDeploymentService` | Template file read |
| `claude-mpm agents available` | `GitSourceManager` | `list_cached_agents()` |
| `claude-mpm agents discover` | `GitSourceManager` | `list_cached_agents_with_filters()` |
| `claude-mpm agents configure` | Config files | Direct YAML editing |
| `claude-mpm skills list` | `SkillsService` | `discover_bundled_skills()` |
| `claude-mpm skills deploy` | `GitSkillSourceManager` | `sync_all_sources()` + `deploy_skills_to_project()` |
| `claude-mpm skills deploy-github` | `SkillsDeployerService` | `deploy_skills()` |
| `claude-mpm skills list-available` | `SkillsDeployerService` | `list_available_skills()` |
| `claude-mpm skills check-deployed` | `SkillsDeployerService` | `check_deployed_skills()` |
| `claude-mpm skills remove` | `SkillsDeployerService` | `remove_skills()` |
| `claude-mpm skills collection list` | `SkillsDeployerService` | `list_collections()` |
| `claude-mpm skills collection add` | `SkillsDeployerService` | `add_collection()` |
| `claude-mpm skills collection remove` | `SkillsDeployerService` | `remove_collection()` |
| `claude-mpm config validate` | `Config` | `validate_configuration()` |
| `claude-mpm config view` | `Config` | `get()` / direct dict access |
| `claude-mpm config auto` | `AutoConfigManagerService` | `auto_configure()` / `preview_configuration()` |
| `claude-mpm agent-source add` | `GitSourceManager` | `sync_repository()` |
| `claude-mpm agent-source list` | `AgentSourceConfiguration` | `list_sources()` |
| `claude-mpm agent-source update` | `GitSourceManager` | `sync_all_repositories()` |
| `claude-mpm skill-source add` | `GitSkillSourceManager` | `sync_source()` |
| `claude-mpm skill-source list` | `SkillSourceConfiguration` | `list_sources()` |

### Configuration Files Touched by Services

| File | Service(s) | Operations |
|------|-----------|------------|
| `.claude-mpm/configuration.yaml` | `Config`, `SkillsDeployerService` (selective mode) | Read, validate |
| `~/.claude-mpm/config.json` | `SkillsConfig` | Read, write (collections) |
| `~/.claude-mpm/cache/agents/` | `GitSourceManager` | Read, write (cached agent files) |
| `~/.claude/skills/` | `SkillsDeployerService` | Read, write (deployed skills) |
| `.claude/agents/` | `AgentDeploymentService` | Read, write (deployed agent MD files) |
| `.claude-mpm/auto-config.yaml` | `AutoConfigManagerService` | Write (after successful auto-config) |
| `src/claude_mpm/config/skill_to_agent_mapping.yaml` | `SkillToAgentMapper` | Read-only |

---

*End of Service Layer API Catalog*
