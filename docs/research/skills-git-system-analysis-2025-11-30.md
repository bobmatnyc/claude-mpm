# Skills Management System Architecture Analysis

**Research Date:** 2025-11-30
**Ticket:** 1M-430 - Implement Single-Tier Git-Based Skills System
**Researcher:** Research Agent
**Status:** Complete

## Executive Summary

This research analyzes the existing agent system architecture to guide implementation of a parallel skills management system. The agent system successfully implements Git-based multi-repository orchestration with priority resolution, ETag caching, and comprehensive CLI tooling. The skills system can mirror this architecture with adaptations for Claude Code skills format (Markdown with YAML frontmatter).

**Key Findings:**
- Agent system architecture is well-designed and directly applicable to skills
- Skills already use compatible format (Markdown with YAML frontmatter)
- No CLI source commands exist for skills yet (must be created from scratch)
- Implementation can closely follow agent system patterns with minor adaptations

## 1. Agent System Architecture Analysis

### 1.1 Configuration Management

**File:** `src/claude_mpm/config/agent_sources.py`

#### Configuration Structure

```yaml
# ~/.claude-mpm/config/agent_sources.yaml
disable_system_repo: false
repositories:
  - url: https://github.com/owner/repo
    subdirectory: agents
    enabled: true
    priority: 100
```

#### Key Components

**AgentSourceConfiguration Class:**
- **Purpose:** Load/save YAML configuration, manage repository lifecycle
- **Methods:**
  - `load(config_path)` - Parse YAML and instantiate GitRepository objects
  - `save(config_path)` - Serialize configuration to YAML
  - `get_system_repo()` - Return default system repository if not disabled
  - `get_enabled_repositories()` - Return sorted list (by priority)
  - `add_repository(repo)` - Add new repository
  - `remove_repository(identifier)` - Remove by identifier
  - `validate()` - Check for duplicate identifiers, invalid priorities

**Configuration Validation:**
- No duplicate repository identifiers
- All repositories pass individual validation
- Priority values are reasonable (warning if >1000)

### 1.2 Git Repository Model

**File:** `src/claude_mpm/models/git_repository.py`

#### GitRepository Dataclass

```python
@dataclass
class GitRepository:
    url: str                        # GitHub HTTPS URL
    subdirectory: Optional[str]     # Path within repo
    enabled: bool = True            # Active/inactive
    priority: int = 100             # Lower = higher precedence
    last_synced: Optional[datetime] # Timestamp
    etag: Optional[str]             # HTTP ETag for caching
```

#### Key Properties

**cache_path:**
- Structure: `~/.claude-mpm/cache/remote-agents/{owner}/{repo}/{subdirectory}/`
- Automatically creates directory structure from URL parsing

**identifier:**
- Format: `{owner}/{repo}/{subdirectory}` or `{owner}/{repo}`
- Used for lookups and conflict detection

**validate():**
- URL not empty
- HTTP/HTTPS protocol
- GitHub domain (currently enforced)
- Owner/repo path structure
- Priority non-negative
- Subdirectory is relative path

### 1.3 Git Orchestration

**File:** `src/claude_mpm/services/agents/git_source_manager.py`

#### GitSourceManager Class

**Responsibilities:**
- Multi-repository sync coordination
- Agent discovery from cached repositories
- Priority-based resolution orchestration

**Key Methods:**

**sync_repository(repo, force=False):**
1. Parse GitHub URL to build raw content URL
2. Initialize GitSourceSyncService for repository
3. Call `sync_agents(force_refresh=force)`
4. Discover agents using RemoteAgentDiscoveryService
5. Return comprehensive sync results

**sync_all_repositories(repos, force=False):**
- Sort repositories by priority (lower first)
- Skip disabled repositories
- Individual failures don't block overall sync
- Return results dict mapping identifier → sync result

**list_cached_agents(repo_identifier=None):**
- Scan cache directory structure
- Apply optional repository filter
- Use RemoteAgentDiscoveryService for each directory
- Return list of agent metadata dicts

### 1.4 ETag-Based Sync Service

**File:** `src/claude_mpm/services/agents/sources/git_source_sync_service.py`

#### GitSourceSyncService Class

**Design Decision:** Use `raw.githubusercontent.com` URLs instead of Git API
- **Rationale:** Bypass API rate limits (60/hour unauthenticated)
- **Trade-off:** Can't list files, must know agent filenames

#### Sync Algorithm

**Phase 1: Discover Agents**
- Fetch `_index.txt` from repository (agent filename listing)
- Parse to get list of agent markdown files

**Phase 2: ETag-Based Download**
1. Check for cached file and `.meta.json` with ETag
2. Send HTTP request with `If-None-Match: {etag}` header
3. If 304 Not Modified: Skip download (cache hit)
4. If 200 OK: Download file, compute SHA-256, save metadata
5. Save `.meta.json` with ETag and content hash

**Metadata Format (.meta.json):**
```json
{
  "content_hash": "abc123...",  // SHA-256 of content
  "etag": "W/\"abc123\"",         // HTTP ETag
  "last_modified": "2025-11-30T10:00:00Z"
}
```

### 1.5 Discovery Service

**File:** `src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py`

#### RemoteAgentDiscoveryService Class

**Purpose:** Parse Markdown agents and convert to JSON template format

#### Parsing Strategy

**Input Format (Markdown with sections):**
```markdown
# Agent Name

Description paragraph

## Configuration
- Model: sonnet
- Priority: 100

## Routing
- Keywords: keyword1, keyword2
- Paths: /path1/, /path2/
```

**Output Format (JSON template):**
```python
{
    "agent_id": "agent-name",
    "metadata": {
        "name": "Agent Name",
        "description": "Description paragraph",
        "version": "{SHA-256}",
        "author": "remote",
        "category": "agent"
    },
    "model": "sonnet",
    "source": "remote",
    "version": "{SHA-256}",
    "routing": {
        "keywords": ["keyword1", "keyword2"],
        "paths": ["/path1/", "/path2/"],
        "priority": 100
    }
}
```

#### Key Methods

**discover_remote_agents():**
- Scan `*.md` files in directory
- Parse each with `_parse_markdown_agent()`
- Return list of agent dicts

**_parse_markdown_agent(md_file):**
- Extract name from first `# Heading`
- Extract description (first paragraph after heading)
- Parse Configuration section for model and priority
- Parse Routing section for keywords and paths
- Load version from `.meta.json` file
- Generate agent_id from name (lowercase, hyphenated)

**_get_agent_version(md_file):**
- Look for corresponding `.md.meta.json` file
- Extract `content_hash` (SHA-256) as version
- Return "unknown" if metadata not found

### 1.6 CLI Commands

**File:** `src/claude_mpm/cli/parsers/source_parser.py`

#### Command Structure

```bash
claude-mpm source <subcommand>
```

#### Available Subcommands

**add:**
- Arguments: `url`, `--subdirectory`, `--priority`, `--disabled`
- Adds repository to configuration

**remove:**
- Arguments: `identifier`
- Removes repository from configuration

**list:**
- Arguments: `--all` (show disabled)
- Lists configured repositories

**enable/disable:**
- Arguments: `identifier`
- Toggle repository enabled state

**disable-system:**
- Arguments: `--enable` (to re-enable)
- Toggle default system repository

**sync:**
- Arguments: `--force`, `[identifier]`
- Sync all or specific repository

### 1.7 Doctor Integration

**File:** `src/claude_mpm/services/diagnostics/checks/agent_sources_check.py`

#### AgentSourcesCheck Class

**8 Health Checks:**

1. **Configuration File Exists** - Check `~/.claude-mpm/config/agent_sources.yaml`
2. **Configuration Valid YAML** - Parse and validate structure
3. **Sources Configured** - At least one source (enabled or disabled)
4. **System Repository Accessible** - HTTP HEAD request succeeds
5. **Enabled Sources Reachable** - HTTP HEAD for each repository
6. **Cache Directory Healthy** - Exists, is directory, writable
7. **Priority Conflicts** - Multiple repos with same priority
8. **Agents Discovered** - Can load agents from sources

**Fix Suggestions:**
- Configuration file missing → `claude-mpm source add {default-url}`
- Invalid YAML → `claude-mpm config validate`
- All sources unreachable → "Check URLs and network"
- Cache not writable → `chmod -R u+w {cache-dir}`
- No agents discovered → `claude-mpm source sync`

## 2. Claude Code Skills Analysis

### 2.1 Skills Format

**File:** `src/claude_mpm/skills/bundled/main/skill-creator/SKILL.md`

#### Current Skills Structure

**Format:** Markdown with YAML frontmatter

**Frontmatter Fields:**
```yaml
---
name: skill-creator
description: Guide for creating effective skills
license: Complete terms in LICENSE.txt
progressive_disclosure:
  entry_point:
    summary: "Create modular skills..."
    when_to_use: "When users want to create..."
    quick_start: "1. Understand skill 2. Plan..."
  references:
    - skill-structure.md
    - creation-workflow.md
---
```

**Content Structure:**
```markdown
# Skill Name

## Overview
...

## When to Use This Skill
...

## Core Principles
...
```

### 2.2 Skills Registry

**File:** `src/claude_mpm/skills/registry.py`

#### SkillsRegistry Class

**Three-Tier Loading:**
1. **Bundled Skills:** `src/claude_mpm/skills/bundled/*.md`
2. **User Skills:** `~/.claude/skills/*.md` (overrides bundled)
3. **Project Skills:** `.claude-mpm/skills/*.md` (highest priority)

#### Skill Dataclass

```python
@dataclass
class Skill:
    name: str              # Skill identifier
    path: Path             # File path
    content: str           # Full markdown content
    source: str            # 'bundled', 'user', or 'project'
    version: str           # From frontmatter or default "0.1.0"
    skill_id: str          # From frontmatter or name
    description: str       # From frontmatter or extracted
    agent_types: List[str] # Which agents can use
    updated_at: str        # ISO timestamp
    tags: List[str]        # Categories/keywords
```

#### Frontmatter Parsing

**Method:** `_parse_skill_frontmatter(content)`
- Regex match: `^---\n(.*?)\n---\n(.*)$`
- Parse YAML block with `yaml.safe_load()`
- Extract: `skill_version`, `skill_id`, `description`, `updated_at`, `tags`

### 2.3 Skills Manager

**File:** `src/claude_mpm/skills/skill_manager.py`

#### SkillManager Class

**Responsibilities:**
- Load agent-to-skill mappings from JSON templates
- Get skills for specific agent type
- Enhance agent prompts with skill content
- Add/remove skills from agent mappings

**Key Feature:** Skills can be injected into agent prompts as appendices

### 2.4 Existing CLI Commands

**File:** `src/claude_mpm/cli/commands/skills.py`

**Current Commands:**
- `claude-mpm skills list` - List bundled/user/project skills
- `claude-mpm skills show <name>` - Display skill content
- `claude-mpm skills deploy <path>` - Deploy skill to user tier

**Missing:** No source management commands for skills (no `skill-source` command group)

## 3. Agent vs Skills Comparison

### 3.1 Similarities

| Aspect | Agents | Skills |
|--------|--------|--------|
| **Format** | Markdown with sections | Markdown with YAML frontmatter |
| **Storage** | Git repositories | Git repositories (planned) |
| **Caching** | `~/.claude-mpm/cache/remote-agents/` | Will be `~/.claude-mpm/cache/remote-skills/` |
| **Config** | `~/.claude-mpm/config/agent_sources.yaml` | Will be `~/.claude-mpm/config/skill_sources.yaml` |
| **Priority** | Lower number = higher precedence | Same pattern |
| **Discovery** | Scan `*.md` files | Same pattern |
| **Version** | SHA-256 hash from metadata | Same approach |
| **ETag** | HTTP caching for efficiency | Same mechanism |

### 3.2 Key Differences

| Aspect | Agents | Skills |
|--------|--------|--------|
| **Deployment Target** | `~/.claude/agents/` (Claude Code) | `~/.claude/skills/` (Claude Code) |
| **Metadata Format** | Parsed sections (##) | YAML frontmatter |
| **Content Structure** | Freeform markdown | Structured with progressive disclosure |
| **ID Generation** | From heading → kebab-case | From frontmatter `name` field |
| **Description** | First paragraph after heading | From frontmatter `description` |
| **Routing** | Keywords/paths/priority | Agent types and tags |
| **Dependencies** | None | Can reference other skills |
| **Bundled Resources** | No | Yes (scripts/, references/, assets/) |

### 3.3 Implementation Adaptations

**Configuration:** Nearly identical
- Change: `agent_sources.yaml` → `skill_sources.yaml`
- Change: `disable_system_repo` → `disable_system_repo`
- Change: Default URL to skills repository

**Git Model:** No changes needed
- GitRepository class can be reused as-is
- Validation logic identical

**Sync Service:** Minor adaptations
- Change: Look for `_index.txt` of skill files
- Change: Cache to `~/.claude-mpm/cache/remote-skills/`
- ETag logic identical

**Discovery Service:** Significant adaptation
- Change: Parse YAML frontmatter instead of markdown sections
- Change: Extract different metadata fields
- Change: Handle bundled resources (scripts/, references/, assets/)
- Change: skill_id from frontmatter, not generated

**CLI Commands:** Copy and adapt
- Command group: `source` → `skill-source`
- Help text: "agent" → "skill"
- Default URL: agents repo → skills repo
- Logic: Nearly identical

**Doctor Check:** Copy and adapt
- Check name: `AgentSourcesCheck` → `SkillSourcesCheck`
- Category: "Agent Sources" → "Skill Sources"
- Discovery: Use skills discovery service
- Messages: Update terminology

## 4. Adaptation Plan

### 4.1 New Files to Create

**Configuration:**
- `src/claude_mpm/config/skill_sources.py` - SkillSourceConfiguration class
  - Copy from `agent_sources.py`
  - Change: Default system repo URL
  - Change: Config file path

**Git Orchestration:**
- `src/claude_mpm/services/skills/git_skill_source_manager.py` - GitSkillSourceManager
  - Copy from `git_source_manager.py`
  - Change: Cache path to `remote-skills/`
  - Change: Use SkillDiscoveryService
  - Logic: Nearly identical

**Sync Service:**
- Reuse `src/claude_mpm/services/agents/sources/git_source_sync_service.py` as-is
  - Generic enough to handle both agents and skills
  - Only needs different cache_dir parameter

**Discovery:**
- `src/claude_mpm/services/skills/skill_discovery_service.py` - SkillDiscoveryService
  - New implementation (not copy)
  - Parse YAML frontmatter
  - Extract: name, description, version, tags, agent_types
  - Handle bundled resources directories
  - Return Skill dataclass format

**CLI Parser:**
- `src/claude_mpm/cli/parsers/skill_source_parser.py` - CLI command definitions
  - Copy from `source_parser.py`
  - Change: Command name to `skill-source`
  - Change: Help text terminology
  - Change: Default repository URL

**CLI Commands:**
- `src/claude_mpm/cli/commands/skill_sources.py` - Command implementations
  - Copy from equivalent agent source command file
  - Change: Use SkillSourceConfiguration
  - Change: Use GitSkillSourceManager
  - Change: Output messages

**Doctor Check:**
- `src/claude_mpm/services/diagnostics/checks/skill_sources_check.py` - Health checks
  - Copy from `agent_sources_check.py`
  - Change: Class name and category
  - Change: Configuration path
  - Change: Use skill discovery service
  - 8 checks: Identical logic pattern

### 4.2 Files to Reuse

**Models:**
- `src/claude_mpm/models/git_repository.py` - GitRepository dataclass
  - Use as-is, no changes needed

**Sync Service:**
- `src/claude_mpm/services/agents/sources/git_source_sync_service.py`
  - Generic enough to handle both use cases
  - Pass different cache_dir parameter

**ETag Manager:**
- `src/claude_mpm/services/agents/sources/etag_manager.py` (if exists)
  - HTTP caching logic is generic

### 4.3 Integration Points

**CLI Registration:**
- Update `src/claude_mpm/cli/executor.py` to register `skill-source` commands
- Add parser in argument parsing setup

**Doctor Registration:**
- Update `src/claude_mpm/services/diagnostics/diagnostic_runner.py`
- Add SkillSourcesCheck to available checks
- Support `--checks skill-sources` filter

**Skills Registry Integration:**
- Update `src/claude_mpm/skills/registry.py`
- Add fourth tier: "remote" skills from Git sources
- Load order: bundled → user → project → remote (or remote has its own priority)

## 5. Implementation Checklist

### Phase 1: Core Infrastructure (Week 1)

**Configuration Management:**
- [ ] Create `src/claude_mpm/config/skill_sources.py`
  - [ ] Copy AgentSourceConfiguration → SkillSourceConfiguration
  - [ ] Update config path: `skill_sources.yaml`
  - [ ] Update default system repo URL
  - [ ] Add unit tests (copy from agent_sources tests)

**Git Orchestration:**
- [ ] Create `src/claude_mpm/services/skills/git_skill_source_manager.py`
  - [ ] Copy GitSourceManager → GitSkillSourceManager
  - [ ] Update cache path: `remote-skills/`
  - [ ] Update to use SkillDiscoveryService
  - [ ] Add unit tests

**Skill Discovery:**
- [ ] Create `src/claude_mpm/services/skills/skill_discovery_service.py`
  - [ ] Implement YAML frontmatter parsing
  - [ ] Extract metadata fields (name, description, version, tags)
  - [ ] Handle bundled resources detection
  - [ ] Return Skill dataclass format
  - [ ] Unit tests for various skill formats

**Integration Tests:**
- [ ] Test configuration load/save cycle
- [ ] Test Git sync with mocked HTTP
- [ ] Test skill discovery from cache
- [ ] Test priority resolution

### Phase 2: CLI Integration (Week 2)

**CLI Parser:**
- [ ] Create `src/claude_mpm/cli/parsers/skill_source_parser.py`
  - [ ] Copy from source_parser.py
  - [ ] Update command name: `skill-source`
  - [ ] Update help text
  - [ ] Update default URLs

**CLI Commands:**
- [ ] Create `src/claude_mpm/cli/commands/skill_sources.py`
  - [ ] Implement `skill-source add`
  - [ ] Implement `skill-source remove`
  - [ ] Implement `skill-source list`
  - [ ] Implement `skill-source enable/disable`
  - [ ] Implement `skill-source sync`
  - [ ] Add error handling and user feedback

**CLI Registration:**
- [ ] Update `src/claude_mpm/cli/executor.py`
  - [ ] Register skill-source commands
  - [ ] Add to command routing

**Integration Tests:**
- [ ] Test `skill-source add` creates configuration
- [ ] Test `skill-source list` displays sources
- [ ] Test `skill-source sync` downloads skills
- [ ] Test error cases (invalid URL, network failure)

### Phase 3: Doctor Integration (Week 3)

**Doctor Check:**
- [ ] Create `src/claude_mpm/services/diagnostics/checks/skill_sources_check.py`
  - [ ] Implement 8 health checks (copy pattern)
  - [ ] Update for skill-specific paths
  - [ ] Add fix command suggestions

**Doctor Registration:**
- [ ] Update `src/claude_mpm/services/diagnostics/diagnostic_runner.py`
  - [ ] Import SkillSourcesCheck
  - [ ] Add to checks registry
  - [ ] Support `--checks skill-sources` filter

**Testing:**
- [ ] Test each of 8 health checks individually
- [ ] Test doctor command with `--checks skill-sources`
- [ ] Test verbose output
- [ ] Test fix command suggestions

### Phase 4: Documentation & Polish (Week 4)

**User Documentation:**
- [ ] Create `docs/user-guide/skill-sources.md`
  - [ ] What are skill sources
  - [ ] How to add custom repositories
  - [ ] Priority resolution explanation
  - [ ] Troubleshooting common issues

**CLI Reference:**
- [ ] Update `docs/reference/cli-commands.md`
  - [ ] Document all `skill-source` subcommands
  - [ ] Add examples for each command
  - [ ] Document configuration format

**Developer Documentation:**
- [ ] Create `docs/architecture/skill-sources-system.md`
  - [ ] Architecture overview
  - [ ] Component responsibilities
  - [ ] Integration points
  - [ ] Extension guide

**Examples:**
- [ ] Create example skill source repository
  - [ ] README with structure guidelines
  - [ ] Sample skills
  - [ ] `_index.txt` listing

**Migration Guide:**
- [ ] Document any breaking changes (unlikely)
  - [ ] How to migrate existing skills
  - [ ] Configuration changes required

### Phase 5: Testing & Release

**Comprehensive Testing:**
- [ ] Unit test coverage >80%
- [ ] Integration test coverage for critical paths
- [ ] Manual testing of all CLI commands
- [ ] Test with real GitHub repository
- [ ] Test with slow/unreachable repositories
- [ ] Test cache invalidation

**Code Quality:**
- [ ] Run linters: `make lint-fix`
- [ ] Run quality gate: `make quality`
- [ ] Fix all mypy type errors
- [ ] Update docstrings
- [ ] Add type hints

**Release Preparation:**
- [ ] Update CHANGELOG.md
- [ ] Version bump (minor version)
- [ ] Create release notes
- [ ] Tag release
- [ ] Deploy to PyPI

## 6. Risk Assessment

### 6.1 Technical Risks

**Risk: Skills format incompatibility**
- **Likelihood:** Low
- **Impact:** High
- **Mitigation:** Skills already use compatible Markdown + YAML format
- **Contingency:** Adapt discovery service to handle variations

**Risk: ETag caching issues**
- **Likelihood:** Low
- **Impact:** Medium
- **Mitigation:** ETag logic proven in agent system
- **Contingency:** Add force refresh option (`--force`)

**Risk: Priority resolution conflicts**
- **Likelihood:** Medium
- **Impact:** Low
- **Mitigation:** Copy proven priority algorithm from agents
- **Contingency:** Doctor check detects conflicts, users can adjust

**Risk: Bundled resources handling**
- **Likelihood:** Medium
- **Impact:** Medium
- **Mitigation:** Skills already support bundled resources locally
- **Contingency:** Initially sync only SKILL.md, add resources in Phase 2

### 6.2 Integration Risks

**Risk: CLI command naming conflicts**
- **Likelihood:** Low
- **Impact:** Low
- **Mitigation:** Use `skill-source` (not `skills source`) for clarity
- **Contingency:** Rename if conflicts arise

**Risk: Cache directory permissions**
- **Likelihood:** Low
- **Impact:** Medium
- **Mitigation:** Doctor check verifies cache writable
- **Contingency:** Clear error messages, chmod fix suggestion

**Risk: GitHub rate limiting**
- **Likelihood:** Low
- **Impact:** Low
- **Mitigation:** Use raw.githubusercontent.com (no API limits)
- **Contingency:** Add retry logic with exponential backoff

### 6.3 User Experience Risks

**Risk: Configuration complexity**
- **Likelihood:** Medium
- **Impact:** Medium
- **Mitigation:** Start with sane defaults (system repo enabled)
- **Contingency:** Add configuration wizard

**Risk: Unclear error messages**
- **Likelihood:** Medium
- **Impact:** Medium
- **Mitigation:** Copy error handling patterns from agent system
- **Contingency:** Iterate based on user feedback

**Risk: Performance with many skills**
- **Likelihood:** Low
- **Impact:** Low
- **Mitigation:** Skills loading is lazy (only when needed)
- **Contingency:** Add skill loading metrics, optimize if needed

### 6.4 Migration Risks

**Risk: Existing skills disruption**
- **Likelihood:** Low
- **Impact:** High
- **Mitigation:** New system is additive, doesn't touch existing tiers
- **Contingency:** Provide rollback mechanism

**Risk: Configuration file conflicts**
- **Likelihood:** Very Low
- **Impact:** Low
- **Mitigation:** Use separate file (`skill_sources.yaml`)
- **Contingency:** Validate before overwriting

## 7. Code Examples

### 7.1 SkillSourceConfiguration

```python
"""Configuration for skill sources (Git repositories)."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml
from src.claude_mpm.models.git_repository import GitRepository

@dataclass
class SkillSourceConfiguration:
    """Configuration for skill sources.

    Manages Git repositories containing skill markdown files.
    Supports system repository and multiple custom repositories
    with priority-based resolution.
    """

    disable_system_repo: bool = False
    repositories: list[GitRepository] = field(default_factory=list)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "SkillSourceConfiguration":
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = Path.home() / ".claude-mpm" / "config" / "skill_sources.yaml"

        if not config_path.exists():
            return cls()  # Return defaults

        with open(config_path) as f:
            data = yaml.safe_load(f)

        repositories = [
            GitRepository(
                url=repo_data["url"],
                subdirectory=repo_data.get("subdirectory"),
                enabled=repo_data.get("enabled", True),
                priority=repo_data.get("priority", 100),
            )
            for repo_data in data.get("repositories", [])
        ]

        return cls(
            disable_system_repo=data.get("disable_system_repo", False),
            repositories=repositories
        )

    def save(self, config_path: Optional[Path] = None) -> None:
        """Save configuration to YAML file."""
        if config_path is None:
            config_path = Path.home() / ".claude-mpm" / "config" / "skill_sources.yaml"

        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "disable_system_repo": self.disable_system_repo,
            "repositories": [
                {
                    "url": repo.url,
                    "subdirectory": repo.subdirectory,
                    "enabled": repo.enabled,
                    "priority": repo.priority,
                }
                for repo in self.repositories
            ],
        }

        with open(config_path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    def get_system_repo(self) -> Optional[GitRepository]:
        """Get system repository if not disabled."""
        if self.disable_system_repo:
            return None

        return GitRepository(
            url="https://github.com/bobmatnyc/claude-mpm-skills",
            subdirectory="skills",
            enabled=True,
            priority=0,  # Highest priority
        )

    def get_enabled_repositories(self) -> list[GitRepository]:
        """Get all enabled repositories sorted by priority."""
        repos = []

        system_repo = self.get_system_repo()
        if system_repo:
            repos.append(system_repo)

        repos.extend([r for r in self.repositories if r.enabled])

        # Sort by priority (lower = higher precedence)
        return sorted(repos, key=lambda r: r.priority)
```

### 7.2 SkillDiscoveryService

```python
"""Service for discovering and loading skills from Git cache."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from claude_mpm.skills.registry import Skill

class SkillDiscoveryService:
    """Discovers and loads skills from cached Git repositories.

    Skills are stored as Markdown files with YAML frontmatter:

    ---
    name: skill-name
    description: Skill description
    skill_version: 1.0.0
    tags: [tag1, tag2]
    ---

    # Skill Content
    """

    def __init__(self, cache_dir: Path):
        """Initialize skill discovery service.

        Args:
            cache_dir: Directory containing cached skill files
        """
        self.cache_dir = cache_dir

    def discover_skills(self) -> List[Skill]:
        """Discover all skills in cache directory.

        Returns:
            List of Skill objects
        """
        skills = []

        if not self.cache_dir.exists():
            return skills

        for skill_file in self.cache_dir.glob("**/SKILL.md"):
            try:
                skill = self._parse_skill_file(skill_file)
                if skill:
                    skills.append(skill)
            except Exception as e:
                logger.warning(f"Failed to parse skill {skill_file}: {e}")

        return skills

    def _parse_skill_file(self, skill_file: Path) -> Optional[Skill]:
        """Parse skill file and return Skill object."""
        content = skill_file.read_text(encoding="utf-8")

        # Parse YAML frontmatter
        frontmatter = self._parse_frontmatter(content)

        # Extract required fields
        name = frontmatter.get("name")
        if not name:
            # Fallback to directory name
            name = skill_file.parent.name

        description = frontmatter.get("description", "")
        version = frontmatter.get("skill_version", "0.1.0")
        skill_id = frontmatter.get("skill_id", name)
        tags = frontmatter.get("tags", [])
        agent_types = frontmatter.get("agent_types", [])

        # Get version from metadata file
        meta_version = self._get_version_from_metadata(skill_file)
        if meta_version:
            version = meta_version

        return Skill(
            name=name,
            path=skill_file,
            content=content,
            source="remote",
            version=version,
            skill_id=skill_id,
            description=description,
            agent_types=agent_types,
            tags=tags,
        )

    def _parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """Parse YAML frontmatter from skill content."""
        if not content.startswith("---"):
            return {}

        match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
        if not match:
            return {}

        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return {}

    def _get_version_from_metadata(self, skill_file: Path) -> Optional[str]:
        """Get version from .meta.json file."""
        meta_file = skill_file.with_suffix(".md.meta.json")

        if not meta_file.exists():
            return None

        try:
            import json
            meta_data = json.loads(meta_file.read_text())
            return meta_data.get("content_hash", "unknown")
        except Exception:
            return None
```

### 7.3 CLI Command Implementation

```python
"""CLI commands for skill source management."""

from pathlib import Path
from rich.console import Console
from rich.table import Table

from src.claude_mpm.config.skill_sources import SkillSourceConfiguration
from src.claude_mpm.models.git_repository import GitRepository
from src.claude_mpm.services.skills.git_skill_source_manager import GitSkillSourceManager

console = Console()

def handle_skill_source_add(args):
    """Add a new skill source repository."""
    config = SkillSourceConfiguration.load()

    # Create repository
    repo = GitRepository(
        url=args.url,
        subdirectory=args.subdirectory,
        enabled=not args.disabled,
        priority=args.priority,
    )

    # Validate repository
    errors = repo.validate()
    if errors:
        console.print(f"[red]Invalid repository configuration:[/red]")
        for error in errors:
            console.print(f"  - {error}")
        return 1

    # Check for duplicates
    if any(r.identifier == repo.identifier for r in config.repositories):
        console.print(f"[yellow]Repository already exists: {repo.identifier}[/yellow]")
        return 1

    # Add and save
    config.add_repository(repo)
    config.save()

    console.print(f"[green]✓[/green] Added skill source: {repo.identifier}")
    console.print(f"  Priority: {repo.priority}")
    console.print(f"  Enabled: {repo.enabled}")
    console.print("\nRun 'claude-mpm skill-source sync' to download skills")

    return 0

def handle_skill_source_list(args):
    """List configured skill sources."""
    config = SkillSourceConfiguration.load()

    table = Table(title="Skill Sources")
    table.add_column("Identifier", style="cyan")
    table.add_column("URL")
    table.add_column("Priority", justify="right")
    table.add_column("Status")

    # System repository
    system_repo = config.get_system_repo()
    if system_repo and (args.show_all or system_repo.enabled):
        status = "✓ Enabled" if system_repo.enabled else "✗ Disabled"
        table.add_row(
            "system",
            system_repo.url,
            str(system_repo.priority),
            status
        )

    # Custom repositories
    repos = config.repositories if args.show_all else [r for r in config.repositories if r.enabled]
    for repo in sorted(repos, key=lambda r: r.priority):
        status = "✓ Enabled" if repo.enabled else "✗ Disabled"
        table.add_row(
            repo.identifier,
            repo.url,
            str(repo.priority),
            status
        )

    console.print(table)
    return 0

def handle_skill_source_sync(args):
    """Sync skill sources from Git."""
    config = SkillSourceConfiguration.load()
    manager = GitSkillSourceManager()

    repos = config.get_enabled_repositories()

    if args.identifier:
        # Sync specific repository
        repos = [r for r in repos if r.identifier == args.identifier]
        if not repos:
            console.print(f"[red]Repository not found: {args.identifier}[/red]")
            return 1

    with console.status(f"Syncing {len(repos)} source(s)..."):
        results = manager.sync_all_repositories(repos, force=args.force)

    # Display results
    for repo_id, result in results.items():
        if result.get("synced"):
            files_updated = result.get("files_updated", 0)
            files_cached = result.get("files_cached", 0)
            skills = result.get("agents_discovered", [])  # "agents" from reused code

            console.print(f"[green]✓[/green] {repo_id}")
            console.print(f"  Downloaded: {files_updated}, Cached: {files_cached}")
            console.print(f"  Skills: {len(skills)}")
        else:
            error = result.get("error", "Unknown error")
            console.print(f"[red]✗[/red] {repo_id}: {error}")

    return 0
```

## 8. Success Metrics

**Implementation Success:**
- [ ] All 5 phases complete
- [ ] Test coverage >80%
- [ ] All quality checks pass (`make quality`)
- [ ] Documentation complete

**Functional Success:**
- [ ] Skills can be added from Git repositories
- [ ] Priority resolution works correctly
- [ ] ETag caching reduces network usage
- [ ] CLI commands are intuitive
- [ ] Doctor checks catch issues

**User Experience Success:**
- [ ] Users can add custom skill repositories without documentation
- [ ] Error messages are clear and actionable
- [ ] Sync is fast (ETag caching effective)
- [ ] Configuration is easy to understand

## 9. Related Work

**Ticket References:**
- **1M-382:** Single-tier agent system (reference implementation)
- **1M-430:** This implementation (skills system)

**Repositories:**
- **System Agent Repo:** https://github.com/bobmatnyc/claude-mpm-agents
- **System Skills Repo:** https://github.com/bobmatnyc/claude-mpm-skills (to be created)

**Documentation:**
- Agent system architecture: `docs/architecture/single-tier-agents.md`
- Skills architecture: `docs/architecture/skills-system.md` (to be created)

## 10. Recommendations

### 10.1 Implementation Priority

**Highest Priority:**
1. Configuration management (SkillSourceConfiguration)
2. Git orchestration (GitSkillSourceManager)
3. Skill discovery (SkillDiscoveryService)
4. CLI commands (skill-source add/list/sync)

**Medium Priority:**
5. Doctor integration (SkillSourcesCheck)
6. Integration tests
7. User documentation

**Lower Priority:**
8. Advanced features (skill dependencies, version constraints)
9. Performance optimizations
10. Migration tools

### 10.2 Implementation Approach

**Week 1: Core Infrastructure**
- Focus on configuration and Git sync
- Get basic skill discovery working
- Unit tests for core components

**Week 2: CLI Integration**
- Implement all subcommands
- Add rich user feedback
- Integration tests

**Week 3: Doctor & Polish**
- Add health checks
- Improve error messages
- Documentation

**Week 4: Release**
- Comprehensive testing
- User acceptance testing
- Deploy

### 10.3 Future Enhancements

**Post-MVP Features:**
- Skill dependency resolution
- Version constraints (require skill X >= 1.0.0)
- Skill collections (meta-packages)
- Skill marketplace integration
- Automatic skill updates
- Skill usage analytics

## Conclusion

The agent system architecture provides an excellent foundation for implementing skill source management. The patterns are proven, well-tested, and directly applicable to skills with minor adaptations. Implementation can proceed confidently by mirroring the agent system structure while adapting for YAML frontmatter parsing and bundled resources handling.

**Key Takeaways:**
1. Agent system architecture is production-ready and reusable
2. Skills format is compatible (Markdown + YAML frontmatter)
3. Implementation is straightforward (copy → adapt → test)
4. Risks are low, mostly around user experience
5. 4-week timeline is achievable with clear milestones

**Next Steps:**
1. Review this research with stakeholders
2. Create Phase 1 implementation branch
3. Start with SkillSourceConfiguration class
4. Follow implementation checklist sequentially
5. Track progress in ticket 1M-430
