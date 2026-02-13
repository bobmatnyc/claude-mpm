# Data Models, Schemas & Business Rules Matrix

**Research Task**: Document complete data structures and every business rule/constraint for the Claude MPM Dashboard Configuration UI.

**Date**: 2026-02-13
**Analyst**: Data Models & Business Rules Analyst (Task #5)

---

## Table of Contents

1. [Configuration File Schemas](#1-configuration-file-schemas)
2. [Pydantic Data Models](#2-pydantic-data-models)
3. [Agent Metadata Model](#3-agent-metadata-model)
4. [Skill Metadata Model](#4-skill-metadata-model)
5. [Git Source Models](#5-git-source-models)
6. [Collection Model](#6-collection-model)
7. [Business Rules Matrix](#7-business-rules-matrix)
8. [Validation Constants & Limits](#8-validation-constants--limits)

---

## 1. Configuration File Schemas

### 1.1 `configuration.yaml` — Primary Configuration File

**Location**: `.claude-mpm/configuration.yaml` (project-level) or `~/.claude-mpm/configuration.yaml` (user-level)
**Load Order**: Project config found first wins (`ConfigurationService._load_default_config()`)

**Source**: `src/claude_mpm/core/unified_config.py:493-510`

```
Search paths (in order):
  1. {CWD}/.claude-mpm/configuration.yaml
  2. {CWD}/.claude-mpm/configuration.yml
  3. ~/.claude-mpm/configuration.yaml
  4. ~/.claude-mpm/configuration.yml
```

**Full Schema** (from actual file + Pydantic model):

| Section | Key | Type | Default | Constraints | Description |
|---------|-----|------|---------|-------------|-------------|
| (root) | `version` | string | `"1.0"` | — | Config schema version |
| (root) | `environment` | string | `"production"` | enum: `development`, `testing`, `production` | Runtime environment |
| `agent_deployment` | `case_sensitive` | bool | `false` | — | Agent name case sensitivity |
| `agent_deployment` | `exclude_dependencies` | bool | `false` | — | Skip deploying dependencies |
| `agent_deployment` | `excluded_agents` | list[str] | `[]` | — | Agents to skip during deploy |
| `agent_deployment` | `filter_non_mpm_agents` | bool | `true` | — | Only deploy MPM-authored agents |
| `agent_deployment` | `mpm_author_patterns` | list[str] | `["claude mpm", "claude-mpm", "anthropic"]` | — | Patterns to identify MPM agents |
| `agent_sync` | `enabled` | bool | `true` | — | Enable remote agent sync |
| `agent_sync` | `cache_dir` | string | `~/.claude-mpm/cache/agents` | path | Local cache directory |
| `agent_sync` | `sources` | list[object] | see below | — | Remote agent sources |
| `agent_sync.sources[]` | `id` | string | — | required | Source identifier |
| `agent_sync.sources[]` | `url` | string | — | required, GitHub URL | Agent download URL |
| `agent_sync.sources[]` | `enabled` | bool | `true` | — | Source active flag |
| `agent_sync.sources[]` | `priority` | int | `100` | 0-1000 | Resolution priority |
| `agent_sync` | `sync_interval` | string | `"startup"` | — | When to sync |
| `skills` | `agent_referenced` | list[str] | `[]` | — | Skills required by deployed agents |
| `skills` | `user_defined` | list[str] | `[]` | — | Skills explicitly requested by user |
| `memory` | `enabled` | bool | `true` | — | Enable memory system |
| `memory` | `auto_learning` | bool | `true` | — | Auto-extract learnings |
| `memory.limits` | `default_size_kb` | int | `80` | >=1 | Per-file size limit |
| `memory.limits` | `max_sections` | int | `10` | >=1 | Sections per memory file |
| `memory.limits` | `max_items_per_section` | int | `15` | >=1 | Items per section |
| `memory.limits` | `max_line_length` | int | `120` | >=1 | Max chars per line |
| `memory.agent_overrides` | `{agent_id}` | object | — | — | Per-agent memory settings |
| `dashboard_server` | `host` | string | `"localhost"` | — | Dashboard bind address |
| `dashboard_server` | `port` | int | `8767` | 1024-65535 | Dashboard port |
| `monitor_server` | `host` | string | `"localhost"` | — | Monitor bind address |
| `monitor_server` | `port` | int | `8765` | 1024-65535 | Monitor port |
| `debug` | — | bool | `false` | — | Debug mode |
| `verbose` | — | bool | `false` | — | Verbose logging |

### 1.2 `agent_sources.yaml` — Agent Repository Configuration

**Location**: `~/.claude-mpm/config/agent_sources.yaml`
**Source**: `src/claude_mpm/config/agent_sources.py`
**Model**: `AgentSourceConfiguration` (dataclass)

```yaml
# Full schema
disable_system_repo: true     # bool, default True (changed from False in v4.5.0)
repositories:
  - url: "https://github.com/owner/repo"     # required, GitHub URL
    subdirectory: "agents"                     # optional, relative path
    enabled: true                              # bool, default true
    priority: 100                              # int, 0-1000, lower = higher precedence
```

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `disable_system_repo` | bool | `true` | — | Skip built-in templates, use git sources |
| `repositories` | list[GitRepository] | `[]` | — | Custom repositories |
| `repositories[].url` | string | — | **required**, must be `https://github.com/*`, must have `owner/repo` path | GitHub repository URL |
| `repositories[].subdirectory` | string | `null` | must be relative path, no leading `/` | Subdirectory within repo |
| `repositories[].enabled` | bool | `true` | — | Whether to sync this repo |
| `repositories[].priority` | int | `100` | >=0, recommended <=1000 | Resolution priority |

**Default Configuration** (auto-created if file missing):

```yaml
disable_system_repo: true
repositories:
  - url: https://github.com/bobmatnyc/claude-mpm-agents
    subdirectory: agents
    enabled: true
    priority: 100
```

### 1.3 `skill_sources.yaml` — Skill Repository Configuration

**Location**: `~/.claude-mpm/config/skill_sources.yaml`
**Source**: `src/claude_mpm/config/skill_sources.py`
**Model**: `SkillSourceConfiguration` + `SkillSource` (dataclass)

```yaml
# Full schema
sources:
  - id: "system"              # required, alphanumeric + hyphens/underscores
    type: "git"                # required, only "git" supported
    url: "https://github.com/owner/repo"  # required, GitHub URL
    branch: "main"             # string, default "main"
    priority: 0                # int, 0-1000
    enabled: true              # bool, default true
    token: null                # optional, "$ENV_VAR" or direct token
```

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `sources[].id` | string | — | **required**, alphanumeric + `-`/`_`, not empty | Unique source identifier |
| `sources[].type` | string | — | **required**, must be `"git"` | Source type |
| `sources[].url` | string | — | **required**, http/https, must be github.com, must have owner/repo | Repository URL |
| `sources[].branch` | string | `"main"` | not empty | Git branch |
| `sources[].priority` | int | `100` | >=0, <=1000 | Priority (lower = higher precedence) |
| `sources[].enabled` | bool | `true` | — | Whether source is active |
| `sources[].token` | string | `null` | optional, `$ENV_VAR` or direct token | Auth token |

**Default Sources** (auto-created if file missing):

| ID | URL | Priority | Purpose |
|----|-----|----------|---------|
| `system` | `https://github.com/bobmatnyc/claude-mpm-skills` | 0 | MPM curated skills |
| `anthropic-official` | `https://github.com/anthropics/skills` | 1 | Official Anthropic skills |

**Priority System**:
- `0`: Reserved for system repository (highest precedence)
- `1-99`: High priority custom sources
- `100-999`: Normal priority custom sources
- `1000+`: Low priority custom sources

---

## 2. Pydantic Data Models

### 2.1 `UnifiedConfig` — Master Configuration Model

**Source**: `src/claude_mpm/core/unified_config.py:286-334`
**Base Class**: `pydantic_settings.BaseSettings`
**Env Prefix**: `CLAUDE_MPM_`
**Env Nested Delimiter**: `__`

```
UnifiedConfig (BaseSettings)
├── version: str = "1.0"
├── environment: str = "production"  # enum: development|testing|production
├── network: NetworkConfig
├── logging: LoggingConfig
├── agents: AgentConfig
├── skills: SkillConfig
├── memory: MemoryConfig
├── security: SecurityConfig
├── performance: PerformanceConfig
├── sessions: SessionConfig
├── development: DevelopmentConfig
├── documentation: DocumentationConfig
├── base_path: Optional[Path] = None
├── config_path: Optional[Path] = None
└── extra_settings: Dict[str, Any] = {}
```

**Pydantic Config**:
- `env_prefix = "CLAUDE_MPM_"`
- `env_nested_delimiter = "__"`
- `case_sensitive = False`
- `validate_assignment = True`
- `extra = "allow"` (backward compatibility)

### 2.2 `NetworkConfig`

| Field | Type | Default | Constraints |
|-------|------|---------|-------------|
| `socketio_host` | str | `"localhost"` | — |
| `socketio_port` | int | `8765` | `ge=1024, le=65535` |
| `socketio_port_range` | List[int] | `[8765, 8775]` | — |
| `connection_timeout` | int | `30` | `ge=1` |
| `max_retries` | int | `3` | `ge=0` |

### 2.3 `LoggingConfig`

| Field | Type | Default | Constraints | Validator |
|-------|------|---------|-------------|-----------|
| `level` | str | `"INFO"` | enum: `DEBUG, INFO, WARNING, ERROR, CRITICAL` | `validate_log_level` (auto-uppercases) |
| `max_size_mb` | int | `100` | `ge=1` | — |
| `retention_days` | int | `30` | `ge=1` | — |
| `format` | str | `"json"` | — | — |
| `enable_file_logging` | bool | `True` | — | — |
| `enable_console_logging` | bool | `True` | — | — |

### 2.4 `AgentConfig` (Pydantic — in UnifiedConfig)

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `enabled` | List[str] | `[]` | — | Explicit list of agent IDs to deploy |
| `required` | List[str] | see below | — | Core agents always deployed |
| `include_universal` | bool | `True` | — | Auto-include universal agents |
| `auto_discover` | bool | `False` | — | Enable auto-discovery (deprecated) |
| `precedence` | List[str] | `["project", "user", "system"]` | — | Agent tier precedence |
| `enable_hot_reload` | bool | `True` | — | Hot reload agents |
| `cache_ttl_seconds` | int | `3600` | `ge=0` | Cache TTL |
| `validate_on_load` | bool | `True` | — | Validate agents on load |
| `strict_validation` | bool | `False` | — | Strict validation mode |
| `max_concurrent_operations` | int | `10` | `ge=1` | Max concurrent agent operations |

**Default Required (Core) Agents** (7 agents):

```python
["engineer", "research", "qa", "web-qa", "documentation", "ops", "ticketing"]
```

### 2.5 `SkillConfig` (Pydantic — in UnifiedConfig)

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `enabled` | List[str] | `[]` | — | Explicit skill IDs to deploy |
| `auto_detect_dependencies` | bool | `True` | — | Auto-include agent-required skills |

### 2.6 `MemoryConfig`

| Field | Type | Default | Constraints |
|-------|------|---------|-------------|
| `enabled` | bool | `True` | — |
| `auto_learning` | bool | `True` | — |
| `default_size_kb` | int | `80` | `ge=1` |
| `max_sections` | int | `10` | `ge=1` |
| `max_items_per_section` | int | `15` | `ge=1` |
| `max_line_length` | int | `120` | `ge=1` |
| `claude_json_warning_threshold_kb` | int | `500` | `ge=1` |

### 2.7 `SecurityConfig`

| Field | Type | Default | Constraints |
|-------|------|---------|-------------|
| `enable_path_validation` | bool | `True` | — |
| `max_file_size_mb` | int | `10` | `ge=1` |
| `allowed_file_extensions` | List[str] | `[".md", ".txt", ".json", ".yaml", ".yml", ".py"]` | — |
| `enable_sandbox_mode` | bool | `False` | — |

### 2.8 `PerformanceConfig`

| Field | Type | Default | Constraints |
|-------|------|---------|-------------|
| `startup_timeout` | int | `60` | `ge=1` |
| `graceful_shutdown_timeout` | int | `30` | `ge=1` |
| `max_memory_usage_mb` | int | `1024` | `ge=128` |
| `enable_metrics` | bool | `True` | — |
| `metrics_interval_seconds` | int | `60` | `ge=1` |
| `hook_timeout_seconds` | int | `5` | `ge=1` |
| `session_timeout_seconds` | int | `30` | `ge=1` |
| `agent_load_timeout_seconds` | int | `10` | `ge=1` |
| `max_restarts` | int | `3` | `ge=0` |
| `max_recovery_attempts` | int | `3` | `ge=0` |
| `cache_max_size_mb` | float | `100` | `ge=1` |
| `cache_max_entries` | int | `10000` | `ge=1` |
| `cache_default_ttl_seconds` | int | `300` | `ge=1` |
| `health_check_interval_seconds` | float | `0.1` | `ge=0.01` |
| `batch_window_ms` | int | `100` | `ge=1` |
| `polling_interval_seconds` | float | `1.0` | `ge=0.1` |

### 2.9 `SessionConfig`

| Field | Type | Default | Constraints |
|-------|------|---------|-------------|
| `max_age_minutes` | int | `30` | `ge=1` |
| `cleanup_max_age_hours` | int | `24` | `ge=1` |
| `archive_old_sessions` | bool | `True` | — |
| `session_timeout_minutes` | int | `60` | `ge=1` |

### 2.10 `DevelopmentConfig`

| Field | Type | Default | Constraints |
|-------|------|---------|-------------|
| `debug` | bool | `False` | — |
| `verbose` | bool | `False` | — |
| `enable_profiling` | bool | `False` | — |
| `hot_reload_enabled` | bool | `True` | — |
| `mock_external_services` | bool | `False` | — |

### 2.11 `DocumentationConfig`

| Field | Type | Default | Constraints |
|-------|------|---------|-------------|
| `docs_path` | str | `"docs/research/"` | relative path |
| `attach_to_tickets` | bool | `True` | — |
| `backup_locally` | bool | `True` | — |
| `enable_ticket_detection` | bool | `True` | — |

---

## 3. Agent Metadata Model

### 3.1 Agent Template JSON Structure

**Location**: `src/claude_mpm/agents/templates/archive/*.json`
**Source**: `engineer.json` (representative example)

```json
{
  "name": "Engineer Agent",
  "description": "Clean architecture specialist...",
  "schema_version": "1.3.0",
  "agent_id": "engineer",
  "agent_version": "3.9.1",
  "template_version": "2.3.0",
  "template_changelog": [...],
  "agent_type": "engineer",
  "skills": ["test-driven-development", "systematic-debugging", ...],
  "metadata": {
    "name": "...",
    "description": "...",
    "category": "engineering",
    "tags": ["engineering", "SOLID-principles", ...],
    "author": "Claude MPM Team",
    "created_at": "2025-07-27T03:45:51.472561Z",
    "updated_at": "2025-08-25T15:30:00.000000Z",
    "color": "blue"
  },
  "capabilities": {
    "model": "sonnet",
    "tools": ["Read", "Write", "Edit", "MultiEdit", "Bash", "Grep", "Glob", "LS", ...],
    "resource_tier": "intensive",
    "max_tokens": 12288,
    "temperature": 0.2,
    "timeout": 1200,
    "memory_limit": 6144,
    "cpu_limit": 80,
    "network_access": true,
    "file_access": {"read_paths": ["./"], "write_paths": ["./"]}
  },
  "instructions": "...",
  "knowledge": {...},
  "dependencies": {"python": [...], "system": [...], "optional": false},
  "memory_routing": {
    "description": "...",
    "categories": [...],
    "keywords": [...]
  },
  "interactions": {
    "input_format": {"required_fields": ["task"], "optional_fields": [...]},
    "output_format": {"structure": "markdown", "includes": [...]},
    "handoff_agents": ["qa", "security", "documentation"],
    "triggers": []
  },
  "testing": {
    "test_cases": [...],
    "performance_benchmarks": {"response_time": 300, "token_usage": 8192, "success_rate": 0.95}
  }
}
```

### 3.2 Agent Frontmatter Schema (Deployed .md files)

**Source**: `src/claude_mpm/schemas/frontmatter_schema.json`

| Field | Type | Required | Constraints | Default |
|-------|------|----------|-------------|---------|
| `name` | string | **yes** | Pattern: `^[a-z][a-z0-9_-]*$`, length: 1-50 | — |
| `description` | string | **yes** | Length: 10-200 | — |
| `version` | string | **yes** | Pattern: `^\d+\.\d+\.\d+$` (semver) | — |
| `model` | string | **yes** | Enum: `opus`, `sonnet`, `haiku` | — |
| `author` | string | no | Length: 1-100 | — |
| `tools` | array[string] | no | Unique items, enum values (see below) | — |
| `tags` | array[string] | no | Pattern: `^[a-z][a-z0-9-]*$`, unique items | — |
| `category` | string | no | Enum: `engineering`, `research`, `quality`, `operations`, `specialized` | — |
| `max_tokens` | integer | no | Min: 1000, Max: 200000 | 8192 |
| `temperature` | number | no | Min: 0, Max: 1 | 0.7 |
| `resource_tier` | string | no | Enum: `basic`, `standard`, `intensive`, `lightweight` | — |
| `dependencies` | array[string] | no | — | — |
| `capabilities` | array[string] | no | — | — |
| `base_version` | string | no | Pattern: `^\d+\.\d+\.\d+$` | — |
| `collection_id` | string | no | Format: `owner/repo-name` | — |
| `source_path` | string | no | Relative path in repo | — |
| `canonical_id` | string | no | Format: `collection_id:agent_id` or `legacy:filename` | — |

**Valid Tools** (from schema):
```
Read, Write, Edit, MultiEdit, Grep, Glob, LS, Bash,
WebSearch, WebFetch, NotebookRead, NotebookEdit, TodoWrite, ExitPlanMode,
git, docker, kubectl, terraform, aws, gcloud, azure
```

**Valid Models**: `opus`, `sonnet`, `haiku`

**Additional Properties**: `true` (schema allows extra fields for extensibility)

### 3.3 `SystemAgentConfig` — Runtime Agent Config

**Source**: `src/claude_mpm/agents/system_agent_config.py:37-59`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent_type` | str | — | Agent type identifier |
| `agent_name` | str | — | Human-readable name |
| `description` | str | — | Agent description |
| `default_model` | str | — | Default model ID |
| `capabilities` | List[str] | `[]` | Capability list |
| `specializations` | List[str] | `[]` | Specialization tags |
| `performance_requirements` | Dict | `{}` | Performance needs |
| `model_preferences` | Dict | `{}` | Model preference config |
| `enabled` | bool | `True` | Whether agent is enabled |
| `priority` | int | `100` | Priority (lower = higher) |

**Pre-configured System Agents** (from `SystemAgentConfigManager._initialize_system_agents()`):

| Agent Type | Name | Default Model | Priority |
|------------|------|---------------|----------|
| `orchestrator` | Project Orchestrator | opus | 1 |
| `architecture` | Software Architect | opus | 5 |
| `engineer` | Software Engineer | opus | 10 |
| `documentation` | Documentation Agent | sonnet | 20 |
| `qa` | Quality Assurance Agent | sonnet | 30 |
| `security` | Security Agent | sonnet | 35 |
| `research` | Research Agent | sonnet | 40 |
| `data_engineer` | Data Engineer Agent | sonnet | 45 |
| `ops` | Operations Agent | sonnet | 50 |
| `version_control` | Version Control Agent | sonnet | 55 |

---

## 4. Skill Metadata Model

### 4.1 Skill Deployment Modes

**Source**: `.claude-mpm/configuration.yaml` `skills` section

Skills are tracked in two lists:

| List | Key | Description | Precedence |
|------|-----|-------------|------------|
| `user_defined` | `skills.user_defined` | Explicitly requested by user via UI/CLI | **Higher** — always deployed |
| `agent_referenced` | `skills.agent_referenced` | Auto-discovered from agent frontmatter `skills:` field | **Lower** — deployed based on agent needs |

**Precedence Rule**: `user_defined` overrides `agent_referenced`. If a skill is in `user_defined`, it is deployed regardless of whether any agent references it. `agent_referenced` skills are auto-populated by scanning deployed agents' frontmatter.

### 4.2 Skill Frontmatter

Skills are Markdown files with YAML frontmatter. Key fields include:
- `name` / `id` — Skill identifier
- `description` — What the skill provides
- `triggers` — Activation patterns
- `categories` / `tags` — Grouping information

### 4.3 Core Skills Sets

**Source**: `src/claude_mpm/services/skills/selective_skill_deployer.py:56-111`

**PM_CORE_SKILLS** (10 skills — always deployed for PM agent):
```
mpm-delegation-patterns, mpm-verification-protocols, mpm-tool-usage-guide,
mpm-git-file-tracking, mpm-pr-workflow, mpm-ticketing-integration,
mpm-teaching-mode, mpm-bug-reporting, mpm-circuit-breaker-enforcement,
mpm-session-management
```

**CORE_SKILLS** (27 skills — deployed when agent mapping returns >60 skills):
```
universal-debugging-systematic-debugging, universal-testing-test-driven-development,
universal-architecture-software-patterns, toolchains-typescript-core,
toolchains-python-core, ... (see selective_skill_deployer.py:72-111)
```

---

## 5. Git Source Models

### 5.1 `GitRepository` (Agent Sources)

**Source**: `src/claude_mpm/models/git_repository.py`

| Field | Type | Default | Constraints |
|-------|------|---------|-------------|
| `url` | str | — | **required**, http/https, must be github.com, must have owner/repo path |
| `subdirectory` | str | `None` | Must be relative path, no leading `/` |
| `enabled` | bool | `True` | — |
| `priority` | int | `100` | >=0, <=1000 recommended |
| `last_synced` | Optional[datetime] | `None` | Auto-set on sync |
| `etag` | Optional[str] | `None` | HTTP ETag for incremental updates |

**Computed Properties**:
- `cache_path`: `~/.claude-mpm/cache/agents/{owner}/{repo}/{subdirectory}/`
- `identifier`: `{owner}/{repo}/{subdirectory}` or `{owner}/{repo}`

### 5.2 `SkillSource` (Skill Sources)

**Source**: `src/claude_mpm/config/skill_sources.py:47-174`

| Field | Type | Default | Constraints |
|-------|------|---------|-------------|
| `id` | str | — | **required**, alphanumeric + hyphens/underscores |
| `type` | str | — | **required**, only `"git"` supported |
| `url` | str | — | **required**, http/https, must be github.com, must have owner/repo |
| `branch` | str | `"main"` | not empty |
| `priority` | int | `100` | >=0, <=1000 |
| `enabled` | bool | `True` | — |
| `token` | Optional[str] | `None` | `$ENV_VAR` reference or direct token |

**Token Resolution Priority**:
1. `source.token` (if set)
2. `$GITHUB_TOKEN` env var
3. `$GH_TOKEN` env var

---

## 6. Collection Model

### 6.1 Skill Collections

**Source**: `src/claude_mpm/services/skills_config.py`
**Storage**: `~/.claude-mpm/config.json` under `skills.collections`

```json
{
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

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `url` | str | — | **required**, must start with `https://github.com/` | GitHub repo URL |
| `enabled` | bool | `true` | — | Whether collection is active |
| `priority` | int | `99` | >=1, integer | Priority (lower = higher) |
| `last_update` | str | `null` | ISO 8601 datetime | Last sync timestamp |

**Default Collection**: `"claude-mpm"` (URL: `https://github.com/bobmatnyc/claude-mpm-skills`)

---

## 7. Business Rules Matrix

### BR-01: Core Agents Cannot Be Undeployed

| Aspect | Detail |
|--------|--------|
| **Rule** | The 7 required/core agents are always deployed when the system initializes |
| **Source** | `UnifiedConfig.agents.required` (`src/claude_mpm/core/unified_config.py:78-88`) |
| **Core Agents** | `engineer`, `research`, `qa`, `web-qa`, `documentation`, `ops`, `ticketing` |
| **Enforcement** | The `required` field has a default factory; the diagnostic check (`agent_check.py:156`) warns if `research.md`, `engineer.md`, `qa.md`, `documentation.md` are missing |
| **UI Implication** | Core agents should be shown as "always deployed" / non-removable in the UI. Users can add agents to the `enabled` list but cannot remove core agents from `required` |

### BR-02: Agent ID Uniqueness Across Sources

| Aspect | Detail |
|--------|--------|
| **Rule** | Agent IDs (filenames) must be unique within the deployed `.claude/agents/` directory |
| **Source** | `AgentSourceConfiguration.validate()` checks for duplicate repository identifiers; deployment writes to a single target directory |
| **Conflict Resolution** | Agent precedence order is: `project > user > system` (configurable via `agents.precedence`). If two sources provide the same agent ID, the higher-precedence source wins |
| **UI Implication** | Show agent source origin; warn on ID conflicts |

### BR-03: Skill Deployment Mode Precedence

| Aspect | Detail |
|--------|--------|
| **Rule** | `user_defined` skills override `agent_referenced` skills |
| **Source** | `configuration.yaml` `skills` section; `selective_skill_deployer.py` |
| **Behavior** | Skills in `user_defined` are ALWAYS deployed. Skills in `agent_referenced` are deployed only when required by deployed agents. Combined set = `user_defined ∪ agent_referenced` |
| **Auto-Population** | If `agent_referenced` is empty, the system scans deployed agent frontmatter to populate it (`skills_deployer.py:215-232`) |
| **Orphan Cleanup** | Skills deployed by MPM but no longer referenced by agents are cleaned up (`selective_skill_deployer.py:348`) |
| **UI Implication** | Two distinct lists in the UI; user_defined has explicit add/remove; agent_referenced is auto-managed |

### BR-04: Git Source Priority Resolution

| Aspect | Detail |
|--------|--------|
| **Rule** | Lower priority number = higher precedence. When multiple sources provide the same agent/skill ID, the highest-precedence source wins |
| **Scale** | `0-1000` (recommended range) |
| **Agent Sources** | Priority `100` is the default for custom repos. System repo is `100` |
| **Skill Sources** | Priority `0` = system repo, `1` = Anthropic official, `100` = custom |
| **Conflict Handling** | Priority conflicts (same priority, multiple sources) generate warnings but are allowed. Resolution is deterministic by source order |
| **UI Implication** | Priority picker with 0-1000 range; visual warning on conflicts |

### BR-05: Required Fields & Type Validation

| Aspect | Detail |
|--------|--------|
| **Agent Frontmatter** | Required: `name` (str), `description` (str), `version` (str), `model` (str). Also validated but not strictly required by all paths: `author` (str), `tools` (list) |
| **Skill Source** | Required: `id`, `type`, `url` |
| **Agent Source** | Required: `url` (per GitRepository) |
| **Configuration YAML** | No fields are strictly required; Pydantic defaults cover all fields |
| **UI Implication** | Form validation must enforce required fields with proper type checks |

### BR-06: Version Compatibility

| Aspect | Detail |
|--------|--------|
| **Rule** | Version fields must follow semantic versioning: `^\d+\.\d+\.\d+$` |
| **Auto-Correction** | FrontmatterValidator auto-corrects: `1.0` → `1.0.0`, `v1.0.0` → `1.0.0` |
| **Schema Version** | Agent templates have `schema_version` (currently `1.3.0`) |
| **Config Version** | `configuration.yaml` has `version: "1.0"` |
| **Migration** | `ConfigMigration` class supports version-to-version migration via BFS path finding |
| **UI Implication** | Version inputs should auto-format and validate semver |

### BR-07: Maximum Limits

| Aspect | Limit | Source |
|--------|-------|--------|
| Agent name length | 1-50 chars | `frontmatter_schema.json` |
| Agent description length | 10-200 chars | `frontmatter_schema.json` |
| Author field length | 1-100 chars | `FrontmatterValidator._validate_author_field` |
| Max tokens | 1,000-200,000 | `frontmatter_schema.json` |
| Temperature | 0-1 | `frontmatter_schema.json` |
| SocketIO port | 1024-65535 | `NetworkConfig` Pydantic constraints |
| Max file size | 10 MB | `SecurityConfig.max_file_size_mb` |
| Max memory usage | 128-∞ MB (default 1024) | `PerformanceConfig` |
| Cache max entries | >=1 (default 10,000) | `PerformanceConfig` |
| Cache max size | >=1 MB (default 100) | `PerformanceConfig` |
| Priority range (sources) | 0-1000 | `SkillSource.validate()`, `GitRepository.validate()` |
| Memory default size | >=1 KB (default 80) | `MemoryConfig` |
| Max sections per memory file | >=1 (default 10) | `MemoryConfig` |
| Session max age | >=1 min (default 30) | `SessionConfig` |
| Connection timeout | >=1 sec (default 30) | `NetworkConfig` |
| Max concurrent agent ops | >=1 (default 10) | `AgentConfig` |
| Correction max file size | 10 MB | `correction_max_file_size_mb` in config |

### BR-08: Naming Conventions & Restrictions

| Entity | Pattern | Source |
|--------|---------|--------|
| Agent `name` | `^[a-z][a-z0-9_-]*$` (kebab-case or snake_case, start with letter) | `frontmatter_schema.json` |
| Agent tags | `^[a-z][a-z0-9-]*$` (lowercase, alphanumeric with hyphens) | `frontmatter_schema.json` |
| Skill source `id` | Alphanumeric + hyphens + underscores | `SkillSource.validate()` |
| Model tier | `opus`, `sonnet`, `haiku` (normalized from full model IDs) | `FrontmatterValidator.VALID_MODELS` |
| Tool names | PascalCase standard names (e.g., `Read`, `WebSearch`) | `FrontmatterValidator.VALID_TOOLS` |
| Collection `canonical_id` | `collection_id:agent_id` or `legacy:filename` | `FrontmatterValidator._validate_collection_fields` |
| Collection `collection_id` | `owner/repo-name` format | `FrontmatterValidator._validate_collection_fields` |

### BR-09: File Path Conventions

| Path | Purpose | Level |
|------|---------|-------|
| `.claude-mpm/configuration.yaml` | Primary configuration | Project |
| `~/.claude-mpm/configuration.yaml` | User-level configuration | User |
| `~/.claude-mpm/config/agent_sources.yaml` | Agent git source config | User |
| `~/.claude-mpm/config/skill_sources.yaml` | Skill git source config | User |
| `~/.claude-mpm/config.json` | Skill collections config | User |
| `.claude/agents/*.md` | Deployed agent files | Project |
| `~/.claude/agents/*.md` | User-level deployed agents | User |
| `~/.claude-mpm/cache/agents/{owner}/{repo}/` | Agent cache from git | User |
| `.claude-mpm/logs/mpm/` | MPM log directory | Project |
| `.claude-mpm/session/` | Session data | Project |

### BR-10: Concurrent Operation Safety

| Aspect | Detail |
|--------|--------|
| **File Writes** | Skill sources use atomic writes (write to `.yaml.tmp`, then `rename()`) — `skill_sources.py:353-357` |
| **Agent Deployment** | Deployment is idempotent — safe to run multiple times (`agent_deployment.py:13`) |
| **Config Reads** | Config files are read from disk on each request (no in-memory lock) |
| **Collection Updates** | No file locking; last write wins for `config.json` |
| **Skill Deploy Index** | `.mpm-deployed-skills.json` tracks deployed skills; updated after each operation |
| **UI Implication** | The dashboard should use optimistic locking or last-write-wins. Two browser tabs could potentially conflict. Consider adding file-level ETags or timestamps for conflict detection |

### BR-11: Default Collection Protection

| Aspect | Detail |
|--------|--------|
| **Rule** | The default collection cannot be removed or disabled |
| **Source** | `SkillsConfig.remove_collection()` raises `ValueError` if name == default; `disable_collection()` also raises `ValueError` |
| **Resolution** | Must set a different default first, then remove/disable the old one |
| **UI Implication** | Default collection should have a visual indicator; remove/disable buttons should be disabled or show an error |

### BR-12: Model Normalization

| Aspect | Detail |
|--------|--------|
| **Rule** | Full model IDs are normalized to tier names: `claude-3-5-sonnet-20241022` → `sonnet` |
| **Source** | `FrontmatterValidator._normalize_model()` uses `ModelTier.normalize()` |
| **Mappings** | Defined in `frontmatter_schema.json#definitions/model_mappings` |
| **UI Implication** | Model selector should show tier names (`opus`, `sonnet`, `haiku`), not full model IDs |

### BR-13: Agent Precedence Mode

| Mode | Behavior | Source |
|------|----------|--------|
| `STRICT` | PROJECT > USER > SYSTEM, no fallback | `AgentPrecedenceMode.STRICT` |
| `OVERRIDE` | PROJECT > USER > SYSTEM, with fallback (default) | `AgentPrecedenceMode.OVERRIDE` |
| `MERGE` | Merge agents from all tiers | `AgentPrecedenceMode.MERGE` |

### BR-14: Skill Auto-Population from Agents

| Aspect | Detail |
|--------|--------|
| **Rule** | If `agent_referenced` is empty in configuration, the system scans deployed agent `.md` files' frontmatter `skills:` field and populates the list |
| **Source** | `skills_deployer.py:215-232`, `selective_skill_deployer.py:297` |
| **Formats** | Legacy: `skills: [a, b, c]`; New: `skills: {required: [...], optional: [...]}` |
| **UI Implication** | The UI should show agent_referenced as "auto-managed" and indicate which agent requires each skill |

### BR-15: Environment Variable Overrides

| Aspect | Detail |
|--------|--------|
| **Rule** | Environment variables with prefix `CLAUDE_MPM_` override configuration file values |
| **Nesting** | Double underscore `__` separates nested keys (e.g., `CLAUDE_MPM_NETWORK__SOCKETIO_PORT=9000`) |
| **Priority** | Env vars > config file > defaults |
| **Agent-Specific** | `CLAUDE_MPM_PROJECT_AGENTS_DIR`, `CLAUDE_MPM_USER_AGENTS_DIR`, `CLAUDE_MPM_SYSTEM_AGENTS_DIR`, `CLAUDE_MPM_AGENT_SEARCH_PATH` |
| **UI Implication** | Dashboard should indicate when a value is overridden by an environment variable |

---

## 8. Validation Constants & Limits

### 8.1 Agent Frontmatter Validation Summary

```
Required Fields: name, description, version, model
Agent Name: ^[a-z][a-z0-9_-]*$, 1-50 chars
Description: 10-200 chars
Version: ^\d+\.\d+\.\d+$ (semver)
Model: enum(opus, sonnet, haiku)
Author: string, 1-100 chars
Tools: array of valid tool names, unique items
Tags: array of ^[a-z][a-z0-9-]*$, unique items
Category: enum(engineering, research, quality, operations, specialized)
Resource Tier: enum(basic, standard, intensive, lightweight)
Max Tokens: 1000-200000 (default 8192)
Temperature: 0-1 (default 0.7)
```

### 8.2 Source Validation Summary

```
Agent Source URL: required, https://github.com/{owner}/{repo}
Agent Source Priority: >=0, <=1000
Agent Source Subdirectory: relative path only

Skill Source ID: required, alphanumeric + hyphens/underscores
Skill Source Type: must be "git"
Skill Source URL: required, https://github.com/{owner}/{repo}
Skill Source Branch: non-empty string
Skill Source Priority: >=0, <=1000
```

### 8.3 Collection Validation Summary

```
Collection URL: required, must start with https://github.com/
Collection Enabled: boolean
Collection Priority: integer >= 1
Collection Name: must be unique (checked on add)
Default Collection: cannot be removed or disabled
```

### 8.4 Port Assignments (Default)

| Service | Port | Source |
|---------|------|--------|
| Monitor Server | 8765 | `ConfigConstants.DEFAULT_VALUES` |
| Commander | 8766 | `ConfigConstants.DEFAULT_VALUES` |
| Dashboard Server | 8767 | `ConfigConstants.DEFAULT_VALUES` |
| SocketIO Server | 8768 | `ConfigConstants.DEFAULT_VALUES` |
| Port Range Start | 8765 | `ConfigConstants.DEFAULT_VALUES` |
| Port Range End | 8785 | `ConfigConstants.DEFAULT_VALUES` |

---

## Key Observations for UI Implementation

1. **Dual Config Systems**: The codebase has both a Pydantic `UnifiedConfig` model AND a flat YAML `configuration.yaml` with many extra keys not in the Pydantic model. The YAML file is the operational truth; the Pydantic model provides validation for a subset.

2. **Three Config Locations**: Agent sources (`agent_sources.yaml`), skill sources (`skill_sources.yaml`), and skill collections (`config.json`) are separate files. The UI should present a unified view.

3. **No File Locking**: Configuration files have no locking mechanism. The UI should implement optimistic concurrency control (read timestamp, check before write).

4. **Atomic Writes**: Only skill sources use atomic writes (temp file + rename). The UI's backend API should standardize this pattern for all config writes.

5. **Model Normalization**: The system normalizes ~12 different model ID formats to 3 tiers. The UI should only present the tier names.

6. **Skills Are Auto-Managed**: The `agent_referenced` list is auto-populated. The UI should clearly distinguish between user-controlled skills and system-managed skills.

7. **Environment Override Visibility**: Values can be overridden by env vars. The UI should detect and display these overrides with appropriate visual indicators.
