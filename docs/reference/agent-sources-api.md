# Agent Sources API Reference

Technical reference for the single-tier agent system APIs and data models.

## Table of Contents

- [Overview](#overview)
- [Data Models](#data-models)
- [Services](#services)
- [Configuration](#configuration)
- [File Structure](#file-structure)
- [Caching System](#caching-system)
- [Priority Resolution](#priority-resolution)

## Overview

The single-tier agent system is built on three core components:

1. **Data Models**: `GitRepository`, `AgentSourceConfiguration`
2. **Services**: `GitSourceManager`, `SingleTierDeploymentService`, `AgentSelectionService`
3. **Configuration**: YAML-based repository management

**Architecture Diagram**:

```
┌──────────────────────────────────────────────────────────────┐
│                     Application Layer                         │
│  CLI Commands (source, agents deploy-*)                      │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                   Service Layer                               │
│  ┌────────────────────┐  ┌─────────────────────────────┐    │
│  │AgentSelectionService│  │SingleTierDeploymentService │    │
│  │- deploy_minimal()  │  │- sync_all_sources()        │    │
│  │- deploy_auto()     │  │- deploy_all_agents()       │    │
│  └─────────┬──────────┘  └──────────┬──────────────────┘    │
│            │                         │                        │
│            │  ┌──────────────────────▼────────────────┐      │
│            └─►│     GitSourceManager                  │      │
│               │- sync_repository()                    │      │
│               │- sync_all_repositories()              │      │
│               │- list_cached_agents()                 │      │
│               └──────────┬────────────────────────────┘      │
└──────────────────────────┼───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    Data Layer                                 │
│  ┌────────────────────┐  ┌─────────────────────────────┐    │
│  │ GitRepository      │  │ AgentSourceConfiguration    │    │
│  │ - url              │  │ - disable_system_repo       │    │
│  │ - subdirectory     │  │ - repositories: [GitRepo]   │    │
│  │ - priority         │  │ - load()/save()             │    │
│  │ - cache_path       │  └─────────────────────────────┘    │
│  └────────────────────┘                                      │
└──────────────────────────────────────────────────────────────┘
```

## Data Models

### GitRepository

Represents a Git repository configuration for agent sources.

**Module**: `src.claude_mpm.models.git_repository`

**Class Definition**:

```python
@dataclass
class GitRepository:
    """Represents a Git repository configuration for agent sources."""

    url: str
    subdirectory: Optional[str] = None
    enabled: bool = True
    priority: int = 100
    last_synced: Optional[datetime] = None
    etag: Optional[str] = None
```

#### Attributes

**`url`** (str, required)
- Full GitHub repository URL
- Format: `https://github.com/owner/repo`
- Must use `http://` or `https://` protocol
- Must be a GitHub URL (github.com domain)

**`subdirectory`** (Optional[str], default: `None`)
- Optional subdirectory within repository
- Format: Relative path without leading slash
- Example: `agents`, `tools/agents`, `backend/agents`
- Must be relative path (not absolute)

**`enabled`** (bool, default: `True`)
- Whether this repository should be synced and used
- If `False`, repository is ignored during sync/deploy
- Use to temporarily disable sources

**`priority`** (int, default: `100`)
- Priority for agent resolution (lower = higher precedence)
- Range: 0-1000 (values > 1000 trigger warning)
- Default system repository has priority 100
- Used to resolve conflicts when multiple sources provide same agent

**`last_synced`** (Optional[datetime], default: `None`)
- Timestamp of last successful sync
- Set automatically by `GitSourceManager`
- ISO 8601 format with timezone
- Used for staleness detection

**`etag`** (Optional[str], default: `None`)
- HTTP ETag from last sync
- Used for conditional requests (304 Not Modified)
- Reduces bandwidth by ~95% after first sync
- Managed automatically by sync service

#### Properties

**`cache_path`** → `Path`

Returns cache directory path for this repository.

**Cache Structure**: `~/.claude-mpm/cache/remote-agents/{owner}/{repo}/{subdirectory}/`

```python
repo = GitRepository(
    url="https://github.com/bobmatnyc/claude-mpm-agents",
    subdirectory="agents"
)
print(repo.cache_path)
# Output: /Users/user/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents
```

**`identifier`** → `str`

Returns unique identifier for this repository.

**Format**: `{owner}/{repo}/{subdirectory}` or `{owner}/{repo}`

```python
repo = GitRepository(
    url="https://github.com/owner/repo",
    subdirectory="agents"
)
print(repo.identifier)
# Output: owner/repo/agents
```

#### Methods

**`validate()`** → `list[str]`

Validates repository configuration.

**Returns**: List of validation error messages (empty if valid)

**Validation Checks**:
- URL is not empty
- URL is valid HTTP/HTTPS format
- URL is a GitHub repository
- Priority is non-negative
- Priority is reasonable (<= 1000)
- Subdirectory is relative path (not absolute)
- Subdirectory doesn't start with `/`

```python
repo = GitRepository(url="https://github.com/owner/repo", priority=-10)
errors = repo.validate()
print(errors)
# Output: ['Priority must be non-negative (0 or greater)']
```

**`_parse_github_url(url: str)`** → `tuple[str, str]`

Parses GitHub URL to extract owner and repository name.

**Args**:
- `url`: GitHub repository URL

**Returns**: Tuple of `(owner, repository_name)`

```python
repo = GitRepository(url="https://github.com/owner/repo")
owner, repo_name = repo._parse_github_url(repo.url)
print(f"{owner}/{repo_name}")
# Output: owner/repo
```

### AgentSourceConfiguration

Configuration for agent sources (Git repositories).

**Module**: `src.claude_mpm.config.agent_sources`

**Class Definition**:

```python
@dataclass
class AgentSourceConfiguration:
    """Configuration for agent sources."""

    disable_system_repo: bool = False
    repositories: list[GitRepository] = field(default_factory=list)
```

#### Attributes

**`disable_system_repo`** (bool, default: `False`)
- If `True`, don't include default system repository
- System repo: `https://github.com/bobmatnyc/claude-mpm-agents/agents`
- Requires at least one custom repository if disabled
- Use for custom-only or private agent setups

**`repositories`** (list[GitRepository], default: `[]`)
- List of custom Git repositories
- Can be empty (system repo will be used)
- Each repository is a `GitRepository` instance
- Order doesn't matter (priority determines precedence)

#### Class Methods

**`load(config_path: Optional[Path] = None)`** → `AgentSourceConfiguration`

Loads configuration from YAML file.

**Args**:
- `config_path`: Path to YAML configuration file (default: `~/.claude-mpm/config/agent_sources.yaml`)

**Returns**: `AgentSourceConfiguration` instance

**Behavior**:
- If file doesn't exist, returns default configuration
- If file is empty, returns default configuration
- Parses YAML and creates `GitRepository` instances
- Logs warnings for invalid data

```python
config = AgentSourceConfiguration.load()
print(f"System repo: {'disabled' if config.disable_system_repo else 'enabled'}")
print(f"Custom repos: {len(config.repositories)}")
```

#### Instance Methods

**`save(config_path: Optional[Path] = None)`** → `None`

Saves configuration to YAML file.

**Args**:
- `config_path`: Path to YAML configuration file (default: `~/.claude-mpm/config/agent_sources.yaml`)

**Side Effects**:
- Creates parent directories if needed
- Overwrites existing file
- Logs success/failure

```python
config = AgentSourceConfiguration()
repo = GitRepository(url="https://github.com/company/agents", priority=50)
config.add_repository(repo)
config.save()
```

**YAML Output Format**:
```yaml
disable_system_repo: false
repositories:
  - url: https://github.com/company/agents
    subdirectory: null
    enabled: true
    priority: 50
```

**`get_system_repo()`** → `Optional[GitRepository]`

Gets system repository if not disabled.

**Returns**: `GitRepository` for system repo, or `None` if disabled

**System Repository Details**:
- URL: `https://github.com/bobmatnyc/claude-mpm-agents`
- Subdirectory: `agents`
- Priority: `100`
- Always enabled (if not disabled)

```python
config = AgentSourceConfiguration()
system_repo = config.get_system_repo()
if system_repo:
    print(f"System repo: {system_repo.identifier}")
    # Output: System repo: bobmatnyc/claude-mpm-agents/agents
```

**`get_enabled_repositories()`** → `list[GitRepository]`

Gets all enabled repositories sorted by priority.

**Returns**: List of enabled `GitRepository` instances, sorted by priority (ascending)

**Behavior**:
- Includes system repository if not disabled
- Filters out disabled custom repositories
- Sorts by priority (lower number = higher precedence)
- Used by `GitSourceManager` for sync operations

```python
config = AgentSourceConfiguration.load()
repos = config.get_enabled_repositories()
for repo in repos:
    print(f"{repo.identifier} (priority: {repo.priority})")
# Output:
# company/critical-agents (priority: 10)
# company/custom-agents (priority: 50)
# bobmatnyc/claude-mpm-agents/agents (priority: 100)
```

**`add_repository(repo: GitRepository)`** → `None`

Adds a new repository.

**Args**:
- `repo`: `GitRepository` instance to add

**Side Effects**:
- Appends repository to `repositories` list
- Logs addition
- **Does not save to disk** (call `save()` separately)

```python
config = AgentSourceConfiguration()
repo = GitRepository(
    url="https://github.com/company/agents",
    priority=50
)
config.add_repository(repo)
config.save()  # Persist to disk
```

**`remove_repository(identifier: str)`** → `bool`

Removes repository by identifier.

**Args**:
- `identifier`: Repository identifier (e.g., `owner/repo` or `owner/repo/subdirectory`)

**Returns**: `True` if repository was removed, `False` if not found

**Side Effects**:
- Removes repository from `repositories` list
- Logs removal or warning
- **Does not save to disk** (call `save()` separately)

```python
config = AgentSourceConfiguration.load()
removed = config.remove_repository("company/agents")
if removed:
    config.save()  # Persist to disk
```

**`validate()`** → `list[str]`

Validates configuration.

**Returns**: List of validation error messages (empty if valid)

**Validation Checks**:
- All repositories pass validation
- No duplicate repository identifiers
- Priority values are reasonable

```python
config = AgentSourceConfiguration.load()
errors = config.validate()
if errors:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")
```

## Services

### GitSourceManager

Manages Git repository sources for agents.

**Module**: `src.claude_mpm.services.agents.git_source_manager`

**Class Definition**:

```python
class GitSourceManager:
    """Manages Git repository sources for agents."""

    def __init__(self, cache_root: Optional[Path] = None):
        """Initialize Git source manager."""
```

#### Constructor

**`__init__(cache_root: Optional[Path] = None)`**

**Args**:
- `cache_root`: Root directory for repository caches (default: `~/.claude-mpm/cache/remote-agents/`)

**Side Effects**:
- Creates cache root directory if it doesn't exist
- Logs initialization

```python
manager = GitSourceManager()
# Uses default: ~/.claude-mpm/cache/remote-agents/

manager = GitSourceManager(cache_root=Path("/custom/cache"))
# Uses custom cache location
```

#### Methods

**`sync_repository(repo: GitRepository, force: bool = False)`** → `Dict[str, Any]`

Syncs a single repository from Git.

**Args**:
- `repo`: `GitRepository` to sync
- `force`: Force sync even if cache is fresh (bypasses ETag)

**Returns**: Dictionary with sync results:

```python
{
    "synced": bool,              # Overall success
    "files_updated": int,        # Files downloaded
    "files_added": int,          # New files
    "files_removed": int,        # Deleted files (not yet implemented)
    "files_cached": int,         # Cache hits (304 Not Modified)
    "agents_discovered": [str],  # Agent names found
    "timestamp": str,            # ISO 8601 timestamp
    "error": str                 # Error message (if failed)
}
```

**Process**:
1. Builds raw GitHub content URL from repository URL and subdirectory
2. Creates `GitSourceSyncService` with ETag caching
3. Syncs agents using HTTP conditional requests
4. Discovers agents in cached directory
5. Returns sync results with metadata

**Example**:
```python
repo = GitRepository(url="https://github.com/owner/repo")
result = manager.sync_repository(repo)

if result["synced"]:
    print(f"Synced {result['files_updated']} files")
    print(f"Discovered agents: {', '.join(result['agents_discovered'])}")
else:
    print(f"Sync failed: {result['error']}")
```

**`sync_all_repositories(repos: List[GitRepository], force: bool = False)`** → `Dict[str, Dict[str, Any]]`

Syncs multiple repositories.

**Args**:
- `repos`: List of repositories to sync
- `force`: Force sync even if cache is fresh

**Returns**: Dictionary mapping repository identifier to sync results

```python
{
    "owner/repo/subdir": {
        "synced": True,
        "files_updated": 5,
        ...
    },
    "owner/repo2": {
        "synced": False,
        "error": "Network timeout"
    }
}
```

**Behavior**:
- Sorts repositories by priority (lower first)
- Skips disabled repositories
- Individual failures don't stop overall sync
- Logs progress and summary

**Example**:
```python
repos = [
    GitRepository(url="https://github.com/owner/repo1", priority=100),
    GitRepository(url="https://github.com/owner/repo2", priority=50)
]

results = manager.sync_all_repositories(repos)

for repo_id, result in results.items():
    status = '✓' if result['synced'] else '✗'
    print(f"{status} {repo_id}")
```

**`list_cached_agents(repo_identifier: Optional[str] = None)`** → `List[Dict[str, Any]]`

Lists all cached agents, optionally filtered by repository.

**Args**:
- `repo_identifier`: Optional repository filter (e.g., `owner/repo/agents`)

**Returns**: List of agent metadata dictionaries:

```python
[
    {
        "name": "engineer",
        "version": "2.5.0",
        "path": "/cache/owner/repo/agents/engineer.md",
        "repository": "owner/repo/agents",
        "metadata": {
            "name": "Engineer",
            "version": "2.5.0",
            ...
        }
    }
]
```

**Behavior**:
- If `repo_identifier` specified, only scans that repository
- Otherwise, scans all cached repositories
- Uses `RemoteAgentDiscoveryService` to parse agent metadata
- Returns empty list if cache doesn't exist

**Example**:
```python
# List all cached agents
agents = manager.list_cached_agents()
for agent in agents:
    print(f"{agent['name']} v{agent['version']} from {agent['repository']}")

# List agents from specific repository
agents = manager.list_cached_agents("bobmatnyc/claude-mpm-agents/agents")
```

**`get_agent_path(agent_name: str, repo_identifier: Optional[str] = None)`** → `Optional[Path]`

Gets cached path for a specific agent.

**Args**:
- `agent_name`: Agent name (without `.md` extension)
- `repo_identifier`: Optional repository filter

**Returns**: Path to cached agent file, or `None` if not found

**Example**:
```python
path = manager.get_agent_path("engineer")
if path:
    print(f"Found: {path}")
    with open(path) as f:
        content = f.read()
```

### SingleTierDeploymentService

Service for single-tier agent deployment.

**Module**: `src.claude_mpm.services.agents.single_tier_deployment_service`

**Key Methods** (simplified interface):

**`sync_all_sources()`** → `Dict[str, Any]`

Syncs all enabled agent sources.

**Returns**: Sync results summary

```python
{
    "total_sources": 2,
    "sources_synced": 2,
    "sources_failed": 0,
    "total_agents_available": 17,
    "results": {
        "owner/repo": {...}
    }
}
```

**`deploy_all_agents(dry_run: bool = False)`** → `Dict[str, Any]`

Deploys all available agents to `.claude/agents/`.

**Args**:
- `dry_run`: Preview without actually deploying

**Returns**: Deployment results

```python
{
    "deployed": 17,
    "failed": 0,
    "skipped": 0,
    "agents": ["engineer", "documentation", ...]
}
```

**`deploy_agent(agent_name: str, source: Optional[str] = None)`** → `bool`

Deploys specific agent.

**Args**:
- `agent_name`: Agent name to deploy
- `source`: Optional source repository filter

**Returns**: `True` if deployed successfully

### AgentSelectionService

Service for agent selection modes (minimal and auto-configure).

**Module**: `src.claude_mpm.services.agents.agent_selection_service`

**Key Methods**:

**`deploy_minimal_configuration(dry_run: bool = False)`** → `Dict[str, Any]`

Deploys minimal configuration (6 core agents).

**Minimal Agents**:
1. `engineer` - General implementation
2. `documentation` - Documentation creation
3. `qa` - Quality assurance
4. `research` - Codebase analysis
5. `ops` - Deployment operations
6. `ticketing` - Ticket management

**Returns**: Deployment results

```python
{
    "mode": "minimal",
    "deployed_count": 6,
    "deployed_agents": ["engineer", "documentation", ...],
    "failed": [],
    "skipped": []
}
```

**`deploy_auto_configure(project_path: Path, dry_run: bool = False)`** → `Dict[str, Any]`

Auto-detects toolchain and deploys matching agents.

**Args**:
- `project_path`: Project directory to analyze
- `dry_run`: Preview without deploying

**Returns**: Deployment results with toolchain info

```python
{
    "mode": "auto-configure",
    "toolchain": {
        "languages": ["Python", "JavaScript"],
        "frameworks": ["FastAPI", "React"],
        "build_tools": ["Make", "Docker"]
    },
    "recommended_agents": ["engineer", "python-engineer", "react-engineer", ...],
    "deployed_count": 11,
    "deployed_agents": [...],
    "core_agents": ["engineer", "documentation", ...],
    "specialized_agents": ["python-engineer", "react-engineer", ...]
}
```

### ToolchainDetector

Detects project toolchain for auto-configure mode.

**Module**: `src.claude_mpm.services.agents.toolchain_detector`

**Key Methods**:

**`detect(project_path: Path)`** → `Dict[str, List[str]]`

Detects project toolchain.

**Returns**: Dictionary with detected toolchain

```python
{
    "languages": ["Python", "JavaScript"],
    "frameworks": ["FastAPI", "React"],
    "build_tools": ["Make", "Docker", "npm"]
}
```

## Configuration

### Configuration File Format

**Location**: `~/.claude-mpm/config/agent_sources.yaml`

**Schema**:

```yaml
# Disable default system repository (optional)
disable_system_repo: boolean  # Default: false

# List of custom repositories (optional)
repositories:
  - url: string               # Required: GitHub repository URL
    subdirectory: string      # Optional: Subdirectory within repo
    enabled: boolean          # Optional: Default true
    priority: integer         # Optional: Default 100
```

**Full Example**:

```yaml
# Use custom agents only (no system repo)
disable_system_repo: false

repositories:
  # Critical agents (highest precedence)
  - url: https://github.com/company/critical-agents
    subdirectory: null
    enabled: true
    priority: 10

  # Custom agents (high precedence)
  - url: https://github.com/company/custom-agents
    subdirectory: agents
    enabled: true
    priority: 50

  # Monorepo subdirectory
  - url: https://github.com/company/monorepo
    subdirectory: tools/claude-agents
    enabled: true
    priority: 90

  # Community contributions (low precedence)
  - url: https://github.com/community/contrib-agents
    subdirectory: null
    enabled: false
    priority: 150
```

### Default Configuration

If no configuration file exists, these defaults are used:

```python
{
    "disable_system_repo": False,
    "repositories": []
}
```

This results in:
- System repository enabled (priority 100)
- No custom repositories
- All agents deployed from system repository

## File Structure

### Cache Directory Structure

```
~/.claude-mpm/cache/remote-agents/
├── {owner}/
│   └── {repo}/
│       ├── {subdirectory}/   (if specified)
│       │   ├── agent1.md
│       │   ├── agent2.md
│       │   └── ...
│       └── agent.md          (if no subdirectory)
└── ...
```

**Example**:

```
~/.claude-mpm/cache/remote-agents/
├── bobmatnyc/
│   └── claude-mpm-agents/
│       └── agents/
│           ├── engineer.md
│           ├── documentation.md
│           ├── qa.md
│           └── ...
└── company/
    ├── agents/
    │   ├── custom-agent.md
    │   └── internal-tool.md
    └── monorepo/
        └── tools/
            └── agents/
                ├── backend-engineer.md
                └── ops-agent.md
```

### Deployment Directory Structure

```
.claude/agents/
├── engineer.md
├── documentation.md
├── qa.md
├── research.md
├── ops.md
└── ...
```

**Notes**:
- Single deployment location (project-level)
- Agents are Markdown files
- Priority determines which version when conflicts occur
- No tier-based subdirectories (flat structure)

## Caching System

### ETag-Based HTTP Caching

The system uses ETags for efficient incremental sync:

**First Sync** (Cache Miss):
```
1. Request: GET https://raw.githubusercontent.com/owner/repo/main/agents/engineer.md
2. Response: 200 OK
   ETag: "abc123..."
   Content: [agent markdown]
3. Store: engineer.md → cache
4. Record: ETag "abc123..."
```

**Subsequent Sync** (Cache Hit):
```
1. Request: GET https://raw.githubusercontent.com/owner/repo/main/agents/engineer.md
   If-None-Match: "abc123..."
2. Response: 304 Not Modified
   ETag: "abc123..."
3. Action: Use cached version (no download)
```

**Subsequent Sync** (Content Changed):
```
1. Request: GET https://raw.githubusercontent.com/owner/repo/main/agents/engineer.md
   If-None-Match: "abc123..."
2. Response: 200 OK
   ETag: "def456..."
   Content: [updated agent markdown]
3. Store: engineer.md → cache (overwrite)
4. Record: ETag "def456..." (update)
```

### Cache Invalidation

**Automatic**:
- ETag mismatch triggers re-download
- GitHub manages ETags (content-based)
- No manual invalidation needed

**Manual**:
```bash
# Force re-download (bypass ETag)
claude-mpm source sync --force

# Clear entire cache
rm -rf ~/.claude-mpm/cache/remote-agents/

# Clear specific repository
rm -rf ~/.claude-mpm/cache/remote-agents/owner/repo/
```

### Cache Performance

**Bandwidth Savings**:
- First sync: ~200KB for 48 agents
- Subsequent syncs: ~2-5KB (HTTP headers only)
- Reduction: ~95-98%

**Time Savings**:
- First sync: 500-800ms
- Subsequent syncs: 100-200ms
- Speedup: ~4-5x

## Priority Resolution

### Algorithm

When multiple sources provide the same agent:

1. **Filter enabled repositories**
2. **Sort by priority** (ascending: lower number = higher precedence)
3. **For each agent name**:
   - Find all sources providing this agent
   - Select agent from source with **lowest priority number**
   - If tie, select first in sorted order (stable sort)
4. **Deploy selected agents**

**Pseudocode**:

```python
def resolve_agent_conflicts(sources: List[GitRepository]) -> Dict[str, Path]:
    """Resolve agent conflicts using priority."""

    # Step 1: Filter enabled
    enabled_sources = [s for s in sources if s.enabled]

    # Step 2: Sort by priority
    sorted_sources = sorted(enabled_sources, key=lambda s: s.priority)

    # Step 3: Collect agents
    agents = {}  # agent_name → (source, path)

    for source in sorted_sources:
        for agent in discover_agents(source):
            agent_name = agent.name

            # First occurrence wins (lowest priority)
            if agent_name not in agents:
                agents[agent_name] = (source, agent.path)

    return agents
```

### Examples

**Example 1: Simple Override**

```yaml
repositories:
  - url: github.com/company/custom
    priority: 50
  # System repo has priority 100
```

Both provide `engineer.md`:
- Company version (priority 50) **WINS**
- System version (priority 100) skipped

**Example 2: Multiple Sources**

```yaml
repositories:
  - url: github.com/company/critical
    priority: 10
  - url: github.com/company/custom
    priority: 50
  # System repo: priority 100
  - url: github.com/community/contrib
    priority: 150
```

Agent `engineer.md` in all four sources:
- Critical version (priority 10) **WINS**
- Custom, system, community versions skipped

Agent `custom-agent.md` only in custom source:
- Custom version (priority 50) **WINS** (only source)

Agent `contrib-tool.md` only in community source:
- Community version (priority 150) **WINS** (only source)

**Example 3: Tie Breaking**

```yaml
repositories:
  - url: github.com/company/repo1
    priority: 100
  - url: github.com/company/repo2
    priority: 100
```

Both provide `engineer.md` with same priority:
- Repo1 version **WINS** (first in configuration order)
- Repo2 version skipped

### Priority Best Practices

**Recommended Priority Ranges**:

```
0-49:   Critical overrides (highest precedence)
        - Company-specific implementations
        - Security-vetted versions
        - Compliance-approved agents

50-99:  High priority custom agents
        - Team-specific agents
        - Internal tools
        - Tested custom implementations

100:    System repository (default)
        - Bobmatnyc/claude-mpm-agents
        - Well-tested agents
        - Standard functionality

101-150: Supplementary agents
         - Community contributions
         - Experimental agents
         - Optional features

151+:   Low priority fallbacks
        - Deprecated agents
        - Alternative implementations
        - Backup versions
```

**Anti-Patterns**:

❌ **All same priority**: Hard to understand precedence
```yaml
repositories:
  - url: A, priority: 100
  - url: B, priority: 100
  - url: C, priority: 100
```

❌ **Priority gaps**: Wasted range
```yaml
repositories:
  - url: A, priority: 10
  - url: B, priority: 500
  - url: C, priority: 900
```

✅ **Clear priority tiers**: Easy to understand
```yaml
repositories:
  - url: critical, priority: 10
  - url: custom, priority: 50
  - url: system, priority: 100  # Automatic
  - url: contrib, priority: 150
```

## Related Documentation

- **[Single-Tier Agent System Guide](../guides/single-tier-agent-system.md)** - User guide
- **[Single-Tier Design](../architecture/single-tier-design.md)** - Architecture deep-dive
- **[Agent Synchronization Guide](../guides/agent-synchronization.md)** - Sync mechanism details
- **[Configuration Reference](configuration.md)** - Complete configuration options
