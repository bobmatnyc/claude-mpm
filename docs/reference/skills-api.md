# Skills System API Reference

Technical reference for Claude MPM's Skills System architecture, components, and APIs.

**Status:** Active

## Table of Contents

- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Configuration Schema](#configuration-schema)
- [Skill Metadata Schema](#skill-metadata-schema)
- [Integration Points](#integration-points)
- [Developer Guide](#developer-guide)

## Architecture

### System Overview

The Skills System is a **single-tier, Git-based discovery framework** that extends agent capabilities through external skill repositories. It reuses infrastructure from the agent synchronization system for Git operations.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Components                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  SkillSourceConfiguration                                 │  │
│  │  - Manages skill_sources.yaml                            │  │
│  │  - CRUD operations for sources                           │  │
│  │  - Priority conflict detection                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  GitSkillSourceManager                                    │  │
│  │  - Orchestrates multi-repository sync                    │  │
│  │  - Applies priority resolution                           │  │
│  │  - Provides unified skill catalog                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                       │
│          ┌───────────────┴───────────────┐                      │
│          ▼                                ▼                      │
│  ┌──────────────────┐           ┌──────────────────┐           │
│  │ GitSourceSync    │           │ SkillDiscovery   │           │
│  │ Service          │           │ Service          │           │
│  │ (Reused from     │           │ - Scan *.md      │           │
│  │  agent system)   │           │ - Parse YAML     │           │
│  │ - ETag caching   │           │ - Validate       │           │
│  │ - Incremental    │           │ - Extract meta   │           │
│  └──────────────────┘           └──────────────────┘           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

#### SkillSourceConfiguration (`config/skill_sources.py`)

**Purpose**: Manages skill source configuration file (YAML).

**Responsibilities:**
- Load/save configuration from `~/.claude-mpm/config/skill_sources.yaml`
- CRUD operations for skill sources
- Priority conflict detection
- Default system source management

**Key Methods:**
- `load()` - Load all sources from configuration
- `save(sources)` - Save sources to configuration
- `add_source(source)` - Add new source
- `remove_source(id)` - Remove source by ID
- `get_enabled_sources()` - Get enabled sources sorted by priority
- `validate_priority_conflicts()` - Check for priority duplicates

**Design Pattern**: Configuration as Code (YAML as single source of truth)

#### GitSkillSourceManager (`services/skills/git_skill_source_manager.py`)

**Purpose**: Orchestrates multi-repository skill synchronization and discovery.

**Responsibilities:**
- Sync multiple Git repositories
- Apply priority-based conflict resolution
- Provide unified skill catalog
- Coordinate sync and discovery services

**Key Methods:**
- `sync_all_sources(force)` - Sync all enabled sources
- `sync_source(id, force)` - Sync specific source
- `get_all_skills()` - Get all skills with priority resolution
- `get_skills_by_source(id)` - Get skills from specific source

**Design Pattern**: Orchestrator with Dependency Injection

#### GitSourceSyncService (`services/agents/sources/git_source_sync_service.py`)

**Purpose**: ETag-based Git repository synchronization (shared with agent system).

**Responsibilities:**
- Download files from Git repositories via HTTP
- ETag-based conditional requests (HTTP 304)
- SHA-256 content hash verification
- SQLite state tracking for sync history

**Key Features:**
- ~95% bandwidth reduction via caching
- First sync: 500-800ms, subsequent: 100-200ms
- Graceful degradation (works offline with cache)

**Note**: This component is **reused from the agent synchronization system** to avoid code duplication.

#### SkillDiscoveryService (`services/skills/skill_discovery_service.py`)

**Purpose**: Discover and parse skill files from local cache.

**Responsibilities:**
- Scan cache directories for `*.md` files
- Parse YAML frontmatter
- Validate metadata (required fields)
- Extract skill content and metadata
- Build skill catalog

**Key Methods:**
- `discover_skills()` - Scan and parse all skills in cache
- `parse_skill_file(path)` - Parse single skill file
- `validate_metadata(metadata)` - Validate YAML frontmatter

### Data Flow

**1. Configuration Load:**
```python
config = SkillSourceConfiguration()
sources = config.load()  # Loads from skill_sources.yaml
enabled = config.get_enabled_sources()  # Sorted by priority
```

**2. Repository Sync:**
```python
manager = GitSkillSourceManager(config)
results = manager.sync_all_sources()
# For each source:
#   - Builds raw GitHub URL
#   - Uses GitSourceSyncService for ETag-based sync
#   - Downloads changed files to cache
```

**3. Skill Discovery:**
```python
skills = manager.get_all_skills()
# For each source:
#   - SkillDiscoveryService scans cache
#   - Parses YAML frontmatter
#   - Validates metadata
#   - Tags with source metadata (id, priority)
```

**4. Priority Resolution:**
```python
# Groups skills by skill_id
# For each group:
#   - Sorts by priority (ascending)
#   - Selects skill with lowest priority number
# Returns deduplicated list
```

### Directory Structure

```
~/.claude-mpm/
├── config/
│   └── skill_sources.yaml           # Configuration file
├── cache/
│   └── skills/                       # Cache root
│       ├── system/                   # System repository cache
│       │   ├── code-review.md
│       │   ├── tdd-workflow.md
│       │   └── debugging.md
│       └── custom/                   # Custom repository cache
│           └── api-standards.md
└── state/
    └── skill_sync.db                 # SQLite sync state (future)
```

### Design Decisions

#### Decision: Reuse GitSourceSyncService

**Rationale**: The agent synchronization system already implements robust ETag-based caching and incremental updates. Rather than duplicating this logic, we compose it for skills.

**Trade-offs:**
- ✅ Code reuse (DRY principle)
- ✅ Proven infrastructure
- ✅ Consistent caching behavior
- ⚠️ Couples skills to agent sync implementation
- ⚠️ Agent-specific naming in logs/errors

**Alternative Considered**: Create separate SkillSyncService
- Rejected: Unnecessary duplication
- Future: Could refactor to GenericGitSyncService if more use cases emerge

#### Decision: Single-Tier Architecture

**Rationale**: Skills are simpler than agents (no hierarchical deployment). Single-tier Git-based discovery is sufficient.

**Trade-offs:**
- ✅ Simpler mental model
- ✅ Easier to implement and maintain
- ✅ Direct Git repository mapping
- ⚠️ Less flexible than multi-tier
- ⚠️ All skills come from Git (no local-only skills yet)

**Future Enhancement**: Could add local skill directory support if needed.

#### Decision: Priority-Based Conflict Resolution

**Rationale**: Allow organizations to override system skills while maintaining defaults.

**Trade-offs:**
- ✅ Flexible customization
- ✅ Predictable resolution (lowest priority wins)
- ✅ Supports multiple use cases (system + org + team)
- ⚠️ Requires understanding priority numbers
- ⚠️ Conflicts only logged as warnings

**Alternative Considered**: Last-wins or error on conflict
- Rejected: Less flexible, forces users to manage conflicts manually

## API Reference

### SkillSourceConfiguration Class

**Location**: `claude_mpm.config.skill_sources`

#### Constructor

```python
SkillSourceConfiguration(config_path: Optional[Path] = None)
```

**Parameters:**
- `config_path` (Path, optional): Path to configuration file. Defaults to `~/.claude-mpm/config/skill_sources.yaml`

**Returns**: SkillSourceConfiguration instance

**Example:**
```python
from claude_mpm.config.skill_sources import SkillSourceConfiguration

# Use default path
config = SkillSourceConfiguration()

# Use custom path
config = SkillSourceConfiguration(Path("/custom/path/skill_sources.yaml"))
```

#### load()

```python
def load() -> List[SkillSource]
```

**Description**: Load skill sources from configuration file.

**Returns**: List of SkillSource instances

**Behavior:**
- Returns default system source if file doesn't exist
- Validates all sources during loading
- Logs warnings for invalid sources (skips them)
- Never raises exceptions (returns defaults on error)

**Example:**
```python
config = SkillSourceConfiguration()
sources = config.load()

for source in sources:
    print(f"{source.id}: {source.url} (priority: {source.priority})")
```

#### save()

```python
def save(sources: List[SkillSource]) -> None
```

**Description**: Save skill sources to configuration file.

**Parameters:**
- `sources` (List[SkillSource]): Sources to save

**Raises:**
- `ValueError`: If sources list is empty or contains invalid sources
- `Exception`: If file write fails

**Behavior:**
- Validates all sources before saving
- Creates parent directory if needed
- Writes atomically (temp file + rename)

**Example:**
```python
from claude_mpm.config.skill_sources import SkillSource, SkillSourceConfiguration

config = SkillSourceConfiguration()
sources = config.load()

# Add new source
sources.append(SkillSource(
    id="custom",
    type="git",
    url="https://github.com/myorg/skills",
    priority=100
))

config.save(sources)
```

#### add_source()

```python
def add_source(source: SkillSource) -> None
```

**Description**: Add a new skill source (convenience method).

**Parameters:**
- `source` (SkillSource): Source to add

**Raises:**
- `ValueError`: If source ID already exists

**Behavior:**
- Loads current sources
- Validates new source
- Checks for duplicate IDs (fails)
- Checks for priority conflicts (warns)
- Saves updated sources

**Example:**
```python
from claude_mpm.config.skill_sources import SkillSource, SkillSourceConfiguration

config = SkillSourceConfiguration()

source = SkillSource(
    id="team",
    type="git",
    url="https://github.com/myteam/skills",
    branch="main",
    priority=50,
    enabled=True
)

config.add_source(source)
```

#### remove_source()

```python
def remove_source(source_id: str) -> bool
```

**Description**: Remove a skill source by ID.

**Parameters:**
- `source_id` (str): ID of source to remove

**Returns**: True if removed, False if not found

**Example:**
```python
config = SkillSourceConfiguration()

if config.remove_source("custom"):
    print("Removed successfully")
else:
    print("Source not found")
```

#### get_source()

```python
def get_source(source_id: str) -> Optional[SkillSource]
```

**Description**: Get a specific skill source by ID.

**Parameters:**
- `source_id` (str): ID of source to retrieve

**Returns**: SkillSource if found, None otherwise

**Example:**
```python
config = SkillSourceConfiguration()
source = config.get_source("system")

if source:
    print(f"URL: {source.url}")
    print(f"Priority: {source.priority}")
```

#### update_source()

```python
def update_source(source_id: str, **updates) -> None
```

**Description**: Update an existing skill source.

**Parameters:**
- `source_id` (str): ID of source to update
- `**updates`: Fields to update (url, branch, priority, enabled)

**Raises:**
- `ValueError`: If source not found or updates are invalid

**Example:**
```python
config = SkillSourceConfiguration()

# Disable a source
config.update_source("experimental", enabled=False)

# Change priority
config.update_source("custom", priority=200)

# Update multiple fields
config.update_source("team", priority=50, branch="develop")
```

#### get_enabled_sources()

```python
def get_enabled_sources() -> List[SkillSource]
```

**Description**: Get all enabled skill sources sorted by priority.

**Returns**: List of enabled SkillSource instances (ascending priority)

**Sorting**: Lower priority number first (highest precedence)

**Example:**
```python
config = SkillSourceConfiguration()
enabled = config.get_enabled_sources()

for source in enabled:
    print(f"{source.id} (priority: {source.priority})")
# Output:
# system (priority: 0)
# team (priority: 50)
# custom (priority: 100)
```

#### validate_priority_conflicts()

```python
def validate_priority_conflicts() -> List[str]
```

**Description**: Check for priority conflicts between sources.

**Returns**: List of warning messages (empty if no conflicts)

**Behavior:**
- Conflicts occur when multiple enabled sources have same priority
- Returns warnings, not errors (conflicts are allowed)

**Example:**
```python
config = SkillSourceConfiguration()
warnings = config.validate_priority_conflicts()

for warning in warnings:
    print(f"Warning: {warning}")
# Output:
# Warning: Priority 100 used by multiple sources: team, custom
```

### GitSkillSourceManager Class

**Location**: `claude_mpm.services.skills.git_skill_source_manager`

#### Constructor

```python
GitSkillSourceManager(
    config: SkillSourceConfiguration,
    cache_dir: Optional[Path] = None,
    sync_service: Optional[GitSourceSyncService] = None
)
```

**Parameters:**
- `config` (SkillSourceConfiguration): Skill source configuration
- `cache_dir` (Path, optional): Cache directory. Defaults to `~/.claude-mpm/cache/skills/`
- `sync_service` (GitSourceSyncService, optional): Injected sync service (for testing)

**Example:**
```python
from claude_mpm.config.skill_sources import SkillSourceConfiguration
from claude_mpm.services.skills.git_skill_source_manager import GitSkillSourceManager

config = SkillSourceConfiguration()
manager = GitSkillSourceManager(config)
```

#### sync_all_sources()

```python
def sync_all_sources(force: bool = False) -> Dict[str, Any]
```

**Description**: Sync all enabled skill sources.

**Parameters:**
- `force` (bool): Force re-download even if cached

**Returns**: Dict with sync results:
```python
{
    "synced_count": int,      # Number of successfully synced sources
    "failed_count": int,      # Number of failed sources
    "sources": {              # Per-source results
        "source_id": {
            "synced": bool,
            "files_updated": int,
            "skills_discovered": int,
            "error": str      # If failed
        }
    },
    "timestamp": str          # ISO 8601 timestamp
}
```

**Behavior:**
- Syncs sources in priority order (lowest first)
- Individual failures don't stop overall sync
- Non-blocking errors logged

**Example:**
```python
manager = GitSkillSourceManager(config)
results = manager.sync_all_sources()

print(f"Synced: {results['synced_count']}")
print(f"Failed: {results['failed_count']}")

for source_id, result in results['sources'].items():
    if result.get('synced'):
        print(f"{source_id}: {result['skills_discovered']} skills")
    else:
        print(f"{source_id}: ERROR - {result.get('error')}")
```

#### sync_source()

```python
def sync_source(source_id: str, force: bool = False) -> Dict[str, Any]
```

**Description**: Sync a specific skill source.

**Parameters:**
- `source_id` (str): ID of source to sync
- `force` (bool): Force re-download

**Returns**: Sync result dict:
```python
{
    "synced": bool,
    "files_updated": int,     # Files downloaded/updated
    "files_cached": int,      # Files served from cache (HTTP 304)
    "skills_discovered": int,
    "timestamp": str,
    "error": str              # If failed
}
```

**Raises:**
- `ValueError`: If source_id not found

**Example:**
```python
manager = GitSkillSourceManager(config)

# Sync specific source
result = manager.sync_source("system")

if result['synced']:
    print(f"Updated {result['files_updated']} files")
    print(f"Discovered {result['skills_discovered']} skills")
else:
    print(f"Error: {result['error']}")
```

#### get_all_skills()

```python
def get_all_skills() -> List[Dict[str, Any]]
```

**Description**: Get all skills from all sources with priority resolution.

**Returns**: List of resolved skill dicts:
```python
[
    {
        "skill_id": str,
        "name": str,
        "description": str,
        "version": str,
        "tags": List[str],
        "agent_types": List[str],
        "content": str,           # Full skill content (Markdown)
        "source_id": str,         # Which source provided this skill
        "source_priority": int,   # Priority of source
        "source_file": str        # Path to cached file
    },
    ...
]
```

**Priority Resolution:**
1. Load skills from all enabled sources
2. Group by skill_id
3. For each group, select skill with lowest priority
4. Return deduplicated list

**Example:**
```python
manager = GitSkillSourceManager(config)
skills = manager.get_all_skills()

for skill in skills:
    print(f"{skill['name']} (from {skill['source_id']}, priority {skill['source_priority']})")

# Check for overrides
skill_ids = {}
for skill in skills:
    skill_id = skill['skill_id']
    if skill_id in skill_ids:
        print(f"CONFLICT: {skill_id} appears multiple times")
    skill_ids[skill_id] = skill['source_id']
```

#### get_skills_by_source()

```python
def get_skills_by_source(source_id: str) -> List[Dict[str, Any]]
```

**Description**: Get skills from a specific source (no priority resolution).

**Parameters:**
- `source_id` (str): ID of source to query

**Returns**: List of skill dicts from that source

**Example:**
```python
manager = GitSkillSourceManager(config)

# Get only system skills
system_skills = manager.get_skills_by_source("system")
print(f"System provides {len(system_skills)} skills")

# Get only custom skills
custom_skills = manager.get_skills_by_source("custom")
print(f"Custom provides {len(custom_skills)} skills")
```

### SkillSource Dataclass

**Location**: `claude_mpm.config.skill_sources`

#### Fields

```python
@dataclass
class SkillSource:
    id: str                  # Unique identifier
    type: str                # Source type ("git")
    url: str                 # Full Git repository URL
    branch: str = "main"     # Git branch
    priority: int = 100      # Priority (lower = higher precedence)
    enabled: bool = True     # Whether to sync this source
```

#### validate()

```python
def validate() -> List[str]
```

**Description**: Validate skill source configuration.

**Returns**: List of validation error messages (empty if valid)

**Validation Rules:**
- ID: Not empty, alphanumeric + hyphens/underscores
- Type: Must be "git"
- URL: Must be HTTPS GitHub URL with owner/repo
- Branch: Not empty
- Priority: 0-1000 (warning if >1000)

**Example:**
```python
from claude_mpm.config.skill_sources import SkillSource

source = SkillSource(
    id="invalid id",  # Spaces not allowed
    type="git",
    url="https://github.com/owner/repo"
)

errors = source.validate()
print(errors)
# Output: ["Source ID must be alphanumeric (with hyphens/underscores), got: invalid id"]
```

## Configuration Schema

### skill_sources.yaml

**Location**: `~/.claude-mpm/config/skill_sources.yaml`

**Schema:**

```yaml
sources:
  - id: string              # Required: Unique identifier
    type: string            # Required: "git" (only supported type)
    url: string             # Required: HTTPS GitHub URL
    branch: string          # Optional: Git branch (default: "main")
    priority: integer       # Optional: Priority 0-1000 (default: 100)
    enabled: boolean        # Optional: Sync this source? (default: true)
```

**Constraints:**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `id` | string | Yes | Alphanumeric + hyphens/underscores, unique |
| `type` | string | Yes | Must be "git" |
| `url` | string | Yes | HTTPS, github.com, includes owner/repo |
| `branch` | string | No | Non-empty (default: "main") |
| `priority` | integer | No | 0-1000 recommended (default: 100) |
| `enabled` | boolean | No | true or false (default: true) |

**Example:**

```yaml
sources:
  # System repository (highest priority)
  - id: system
    type: git
    url: https://github.com/bobmatnyc/claude-mpm-skills
    branch: main
    priority: 0
    enabled: true

  # Organization repository
  - id: org-standards
    type: git
    url: https://github.com/myorg/coding-standards
    branch: main
    priority: 50
    enabled: true

  # Experimental repository (disabled)
  - id: experimental
    type: git
    url: https://github.com/myorg/experimental-skills
    branch: develop
    priority: 200
    enabled: false
```

## Skill Metadata Schema

### YAML Frontmatter

**Location**: First section of `*.md` skill files, delimited by `---`

**Schema:**

```yaml
---
skill_id: string          # Required: Unique identifier (kebab-case)
name: string              # Required: Human-readable name
description: string       # Required: Brief description (1-2 sentences)
version: string           # Optional: Semantic version (e.g., "1.0.0")
tags: [string]            # Optional: Categorization tags
agent_types: [string]     # Optional: Which agents can use this
author: string            # Optional: Skill creator
license: string           # Optional: License type
dependencies: [string]    # Optional: Required skills/tools
last_updated: string      # Optional: ISO 8601 date
---
```

**Required Fields:**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `skill_id` | string | Unique identifier | `"code-review-checklist"` |
| `name` | string | Display name | `"Code Review Checklist"` |
| `description` | string | Brief description | `"Systematic code review for quality assurance"` |

**Optional Fields:**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `version` | string | Semantic version | `"2.0.0"` |
| `tags` | list[string] | Categories | `["quality", "review"]` |
| `agent_types` | list[string] | Target agents | `["code", "research"]` |
| `author` | string | Creator | `"Engineering Team"` |
| `license` | string | License | `"MIT"` |
| `dependencies` | list[string] | Requirements | `["pytest", "black"]` |
| `last_updated` | string | Update date | `"2025-11-30"` |

**Example Skill File:**

```markdown
---
skill_id: python-testing
name: Python Testing Standards
description: Comprehensive Python testing guidelines with pytest
version: "1.0.0"
tags:
  - python
  - testing
  - quality-assurance
agent_types:
  - code
  - documentation
author: Platform Team
license: MIT
dependencies:
  - pytest
  - pytest-cov
last_updated: "2025-11-30"
---

# Python Testing Standards

[Skill content goes here...]
```

## Integration Points

### CLI Commands Integration

**Location**: `claude_mpm.cli.commands.skill_source`

**Commands Implemented:**

| Command | Function | Description |
|---------|----------|-------------|
| `skill-source list` | `list_sources()` | List configured sources |
| `skill-source add` | `add_source()` | Add new source |
| `skill-source remove` | `remove_source()` | Remove source |
| `skill-source show` | `show_source()` | Show source details |
| `skill-source update` | `update_sources()` | Sync sources |
| `skill-source enable` | `enable_source()` | Enable disabled source |
| `skill-source disable` | `disable_source()` | Disable source |

**CLI → API Mapping:**

```python
# skill-source add
def add_source(url, branch, priority, disabled):
    config = SkillSourceConfiguration()
    source = SkillSource(
        id=generate_id_from_url(url),
        type="git",
        url=url,
        branch=branch or "main",
        priority=priority or 100,
        enabled=not disabled
    )
    config.add_source(source)

# skill-source update
def update_sources(source_id):
    config = SkillSourceConfiguration()
    manager = GitSkillSourceManager(config)
    if source_id:
        result = manager.sync_source(source_id)
    else:
        result = manager.sync_all_sources()
```

### Doctor Diagnostics Integration

**Location**: `claude_mpm.services.diagnostics.checks.skill_sources_check`

**Diagnostic Class**: `SkillSourcesCheck`

**8 Checks Performed:**

1. **Configuration File Exists**
   - Verifies `~/.claude-mpm/config/skill_sources.yaml` exists
   - Status: ERROR if missing, SUCCESS if present

2. **Configuration Valid YAML**
   - Parses YAML syntax
   - Validates structure (has "sources" key)
   - Status: ERROR if invalid, SUCCESS if valid

3. **Sources Configured**
   - At least one source in configuration
   - Status: WARNING if none, SUCCESS if >0

4. **System Repository Accessible**
   - HTTP HEAD request to system repository
   - Only checked if system source enabled
   - Status: WARNING if unreachable, SUCCESS if 200 OK

5. **Enabled Sources Reachable**
   - HTTP HEAD request to all enabled sources
   - Non-blocking (continues on individual failures)
   - Status: WARNING if any unreachable, SUCCESS if all OK

6. **Cache Directory Healthy**
   - Verifies `~/.claude-mpm/cache/skills/` exists and is writable
   - Status: ERROR if missing/unwritable, SUCCESS if OK

7. **Priority Conflicts**
   - Checks for duplicate priorities among enabled sources
   - Status: WARNING if conflicts, SUCCESS if unique

8. **Skills Discovered**
   - Runs discovery on all cached sources
   - Counts total skills found
   - Status: WARNING if 0 skills, SUCCESS if >0

**Integration Example:**

```python
from claude_mpm.services.diagnostics.checks.skill_sources_check import SkillSourcesCheck

check = SkillSourcesCheck(verbose=True)

if check.should_run():
    result = check.run()
    print(f"Status: {result.status}")
    print(f"Message: {result.message}")
    print(f"Details: {result.details}")

    if result.sub_results:
        for sub in result.sub_results:
            print(f"  {sub.category}: {sub.status}")
```

### Agent System Integration

**Future Enhancement**: Agents can reference skills in their instructions.

**Proposed API:**

```python
# In agent template
from claude_mpm.services.skills.git_skill_source_manager import GitSkillSourceManager

# Load skill
manager = GitSkillSourceManager(config)
skills = manager.get_all_skills()

# Find specific skill
code_review_skill = next(
    (s for s in skills if s['skill_id'] == 'code-review-checklist'),
    None
)

if code_review_skill:
    # Use skill content in agent instructions
    instructions += code_review_skill['content']
```

**Note**: This integration is planned for future releases.

## Developer Guide

### Contributing Skills

**1. Create Skill Repository**

```bash
# Initialize Git repository
mkdir my-skills
cd my-skills
git init

# Create skill file
cat > python-testing.md << 'EOF'
---
skill_id: python-testing
name: Python Testing Standards
description: Comprehensive Python testing guidelines
version: "1.0.0"
tags:
  - python
  - testing
agent_types:
  - code
---

# Python Testing Standards

[Your content here...]
EOF

# Commit and push
git add .
git commit -m "Add Python testing skill"
git remote add origin https://github.com/yourusername/my-skills
git push -u origin main
```

**2. Test Locally**

```bash
# Add repository to Claude MPM
claude-mpm skill-source add https://github.com/yourusername/my-skills --priority 100

# Sync
claude-mpm skill-source update

# Verify
claude-mpm doctor
```

**3. Distribute to Team**

```bash
# Team members add repository
claude-mpm skill-source add https://github.com/yourusername/my-skills --priority 100
claude-mpm skill-source update
```

### Testing Skills Locally

**Option 1: Direct Cache Placement**

```bash
# Manually place skill in cache
mkdir -p ~/.claude-mpm/cache/skills/test/
cp my-skill.md ~/.claude-mpm/cache/skills/test/

# Skills will be discovered on next Claude MPM startup
```

**Option 2: Local Git Repository**

```bash
# Create local Git server (requires Python http.server or similar)
# Or use file:// URLs (not recommended for production)

# Add local repository
claude-mpm skill-source add file:///path/to/local/skills --priority 100

# Sync
claude-mpm skill-source update
```

**Option 3: Unit Testing**

```python
import pytest
from pathlib import Path
from claude_mpm.services.skills.skill_discovery_service import SkillDiscoveryService

def test_skill_discovery():
    """Test skill discovery with fixture."""
    # Create temporary skill file
    temp_dir = Path("/tmp/test-skills")
    temp_dir.mkdir(exist_ok=True)

    skill_file = temp_dir / "test-skill.md"
    skill_file.write_text("""---
skill_id: test-skill
name: Test Skill
description: Test skill for unit testing
---

# Test Skill Content
""")

    # Run discovery
    discovery = SkillDiscoveryService(temp_dir)
    skills = discovery.discover_skills()

    # Verify
    assert len(skills) == 1
    assert skills[0]['skill_id'] == 'test-skill'
    assert skills[0]['name'] == 'Test Skill'

    # Cleanup
    skill_file.unlink()
    temp_dir.rmdir()
```

### Version Management

**Recommended Versioning:**

```yaml
# Semantic Versioning (MAJOR.MINOR.PATCH)
version: "1.0.0"  # Initial release
version: "1.1.0"  # Added new section (backward compatible)
version: "1.1.1"  # Fixed typo (patch)
version: "2.0.0"  # Changed skill structure (breaking)
```

**Changelog in README:**

```markdown
# Changelog

## v2.0.0 (2025-12-01)
- BREAKING: Restructured checklist format
- Added security section
- Removed deprecated performance checks

## v1.1.0 (2025-11-30)
- Added documentation section
- Improved testing guidelines

## v1.0.0 (2025-11-15)
- Initial release
```

### Best Practices

**1. Skill Naming:**
- Use kebab-case for `skill_id`
- Be descriptive and specific
- Avoid generic names ("review" → "code-review-checklist")

**2. Description Writing:**
- Keep under 2 sentences
- Focus on purpose, not implementation
- Answer: "When would I use this?"

**3. Tagging Strategy:**
- Use 3-5 tags per skill
- Mix general and specific tags
- Example: `["python", "testing", "pytest", "quality"]`

**4. Content Structure:**
- Start with overview
- Use consistent heading levels
- Include examples
- Add troubleshooting section

**5. Maintenance:**
- Update `last_updated` field
- Maintain changelog
- Version bumps for significant changes
- Test changes before pushing

---

## Related Documentation

- **[Skills System User Guide](../guides/skills-system.md)** - User-facing documentation
- **[Agent Synchronization Guide](../guides/agent-synchronization.md)** - Similar Git-based system
- **[Doctor Command Reference](./cli-doctor.md)** - Diagnostics documentation

---

**Last Updated**: 2025-11-30
**Version**: 1.0.0
