# Agent Git Sources Sync Mechanism Research

**Ticket**: 1M-442 - Agent git sources configured but not syncing or loading
**Date**: 2025-11-30
**Priority**: High
**Research Type**: Architecture Analysis & Implementation Roadmap

---

## Executive Summary

The agent git sources feature is **partially implemented but non-functional**. Infrastructure exists (configuration models, repository sync service) but **critical components are missing**:

1. **No CLI commands** to trigger sync (`agents sync`, `agents source` commands don't exist)
2. **No automatic sync triggers** in agent deployment workflow
3. **Multi-source discovery** exists but **never called** from deployment pipeline
4. **Cache directories never created** because sync is never invoked

**Root Cause**: Agent system stopped at 60% implementation. Skills system (100% working) provides exact blueprint for completion.

**Solution**: Mirror skills system's architecture exactly. Add 6 missing CLI commands, integrate sync into deployment workflow, and wire up multi-source discovery.

---

## Table of Contents

1. [Current State Assessment](#current-state-assessment)
2. [Skills System Pattern (Working Reference)](#skills-system-pattern)
3. [Gap Analysis](#gap-analysis)
4. [Implementation Roadmap](#implementation-roadmap)
5. [Technical Specifications](#technical-specifications)
6. [Testing Strategy](#testing-strategy)

---

## 1. Current State Assessment

### 1.1 Existing Infrastructure

**✅ IMPLEMENTED (60% complete)**:

```
Agent Sources Infrastructure:
├── Configuration Layer
│   ├── /src/claude_mpm/config/agent_sources.py
│   │   └── AgentSourceConfiguration (load, save, validate)
│   └── /src/claude_mpm/models/git_repository.py
│       └── GitRepository (cache_path, identifier, validation)
│
├── Sync Layer
│   └── /src/claude_mpm/services/agents/git_source_manager.py
│       └── GitSourceManager
│           ├── sync_repository(repo, force) ✅
│           ├── sync_all_repositories(repos, force) ✅
│           └── list_cached_agents(repo_id) ✅
│
└── Discovery Layer
    └── /src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py
        └── RemoteAgentDiscoveryService
            ├── discover_remote_agents() ✅
            └── _parse_markdown_agent(md_file) ✅
```

**❌ MISSING (40% not implemented)**:

```
Missing Components:
├── CLI Layer
│   ├── agents sync [--force] [--source SOURCE_ID]
│   ├── agents source list
│   ├── agents source add <URL>
│   ├── agents source remove <SOURCE_ID>
│   ├── agents source enable <SOURCE_ID>
│   └── agents source disable <SOURCE_ID>
│
├── Integration Layer
│   ├── Automatic sync trigger in deployment workflow
│   ├── Multi-source discovery in AgentDiscoveryService
│   └── Priority resolution across git/system sources
│
└── Cache Initialization
    ├── ~/.claude-mpm/cache/remote-agents/ (never created)
    └── Git clone/download logic (exists but never called)
```

### 1.2 Configuration Status

**User Configuration EXISTS**:
```yaml
# ~/.claude-mpm/config/agent_sources.yaml
disable_system_repo: false
repositories:
  - url: https://github.com/bobmatnyc/claude-mpm-agents
    subdirectory: agents
    enabled: true
    priority: 10
```

**Git Cache Directories DON'T EXIST**:
```bash
$ ls ~/.claude-mpm/cache/
git-sources/      # Empty (for git clone approach)
remote-agents/    # DOESN'T EXIST (for HTTP download approach)
skills/           # EXISTS and WORKS (skills system functional)
```

**Problem**: Configuration loaded but never acted upon.

### 1.3 Agent Discovery Current State

**System Agents (Working)**:
- Source: `/src/claude_mpm/agents/templates/*.json`
- Discovery: `AgentDiscoveryService.list_available_agents()`
- Count: 55+ agents
- **ALL agents currently come from SYSTEM tier only**

**Remote Agents (Not Working)**:
- Expected source: `~/.claude-mpm/cache/remote-agents/{owner}/{repo}/{subdir}/*.md`
- Discovery: `RemoteAgentDiscoveryService.discover_remote_agents()`
- Count: **0 agents** (cache directory doesn't exist)
- **Never integrated into deployment workflow**

### 1.4 CLI Commands Current State

**Existing `agents` commands**:
```bash
claude-mpm agents list --system      ✅ Works
claude-mpm agents list --deployed    ✅ Works
claude-mpm agents deploy              ✅ Works
claude-mpm agents clean               ✅ Works
```

**Missing `agents` commands**:
```bash
claude-mpm agents sync                ❌ Doesn't exist
claude-mpm agents source list         ❌ Doesn't exist
claude-mpm agents source add          ❌ Doesn't exist
claude-mpm agents available           ❌ HANGS INDEFINITELY (bug in listing service)
```

**Why `agents available` hangs**:
```python
# /src/claude_mpm/services/agents/listing_service.py (suspected)
# Likely calls RemoteAgentDiscoveryService which waits for cache that never exists
# Needs investigation - not in scope for this research
```

---

## 2. Skills System Pattern (Working Reference)

### 2.1 Skills System Architecture

**✅ FULLY FUNCTIONAL** - Use as blueprint:

```
Skills Git Sources (WORKING):
├── Configuration
│   └── /src/claude_mpm/config/skill_sources.py
│       └── SkillSourceConfiguration
│           ├── get_system_source() → SkillSource(id="system", priority=0)
│           ├── get_enabled_sources() → [SkillSource]
│           └── save/load from ~/.claude-mpm/config/skill_sources.yaml
│
├── Sync Manager
│   └── /src/claude_mpm/services/skills/git_skill_source_manager.py
│       └── GitSkillSourceManager
│           ├── sync_all_sources(force) → {synced_count, failed_count, sources: {...}}
│           ├── sync_source(source_id, force) → {synced, files_updated, skills_discovered}
│           ├── get_all_skills() → [skill_dicts] (with priority resolution)
│           └── _apply_priority_resolution(skills_by_source) → [resolved_skills]
│
├── Discovery Service
│   └── /src/claude_mpm/services/skills/skill_discovery_service.py
│       └── SkillDiscoveryService
│           ├── discover_skills() → [skill_dicts]
│           ├── _parse_skill_file(md_file) → skill_dict
│           └── _extract_frontmatter(content) → (frontmatter, body)
│
├── CLI Commands
│   └── /src/claude_mpm/cli/commands/skill_source.py
│       ├── skill_source_command(args) → routes to handlers
│       ├── handle_add_skill_source(args)
│       ├── handle_list_skill_sources(args)
│       ├── handle_remove_skill_source(args)
│       ├── handle_update_skill_sources(args) ← TRIGGERS SYNC
│       ├── handle_enable_skill_source(args)
│       └── handle_disable_skill_source(args)
│
└── Integration Points
    ├── Skills deployment AUTOMATICALLY syncs sources first
    ├── Skills listing includes git sources with priority resolution
    └── Cache structure: ~/.claude-mpm/cache/skills/{source_id}/*.md
```

### 2.2 Skills System Sync Workflow

**How skills sync is triggered**:

```python
# Entry point: CLI command
$ claude-mpm skill-source update [--force] [source_id]

# Handler: handle_update_skill_sources()
def handle_update_skill_sources(args):
    config = SkillSourceConfiguration()
    manager = GitSkillSourceManager(config)

    if args.source_id:
        # Sync specific source
        result = manager.sync_source(args.source_id, force=args.force)
    else:
        # Sync all enabled sources
        results = manager.sync_all_sources(force=args.force)

# GitSkillSourceManager.sync_source()
def sync_source(self, source_id: str, force: bool):
    1. Get source from config
    2. Build raw GitHub URL
    3. Initialize GitSourceSyncService
    4. Call sync_service.sync_agents(force_refresh=force)
    5. Discover skills in cache with SkillDiscoveryService
    6. Return {synced, files_updated, skills_discovered}

# GitSourceSyncService.sync_agents() (shared service)
def sync_agents(self, force_refresh: bool):
    1. Fetch directory listing from raw.githubusercontent.com
    2. Download .md files with ETag caching
    3. Save to cache_dir (e.g., ~/.claude-mpm/cache/skills/system/)
    4. Return {total_downloaded, cache_hits, synced: [files]}
```

### 2.3 Skills System Priority Resolution

**How skills prioritize git vs internal sources**:

```python
# GitSkillSourceManager.get_all_skills()
def get_all_skills(self):
    sources = self.config.get_enabled_sources()  # Includes system source (priority=0)

    # Collect skills from all sources
    skills_by_source = {}
    for source in sources:
        cache_path = self._get_source_cache_path(source)
        skills = SkillDiscoveryService(cache_path).discover_skills()

        # Tag with source metadata
        for skill in skills:
            skill["source_id"] = source.id
            skill["source_priority"] = source.priority

        skills_by_source[source.id] = skills

    # Apply priority resolution
    return self._apply_priority_resolution(skills_by_source)

# Priority resolution algorithm
def _apply_priority_resolution(self, skills_by_source):
    all_skills = flatten(skills_by_source.values())

    # Group by skill_id
    skills_by_id = group_by(all_skills, key=lambda s: s["skill_id"])

    # Select skill with LOWEST priority number for each ID
    resolved = []
    for skill_id, skill_group in skills_by_id.items():
        sorted_group = sorted(skill_group, key=lambda s: s["source_priority"])
        selected_skill = sorted_group[0]  # Lowest priority = highest precedence
        resolved.append(selected_skill)

    return resolved

# Example priority resolution:
# System skill: {"skill_id": "code-review", "priority": 0}
# Custom skill: {"skill_id": "code-review", "priority": 100}
# Result: System skill wins (0 < 100)
```

### 2.4 Skills System CLI Integration

**CLI command routing**:

```python
# /src/claude_mpm/cli/main.py (argparse setup)
skill_source_parser = subparsers.add_parser("skill-source")
skill_source_subparsers = skill_source_parser.add_subparsers(dest="skill_source_command")

# Add subcommands
skill_source_subparsers.add_parser("list")
skill_source_subparsers.add_parser("add").add_argument("url")
skill_source_subparsers.add_parser("remove").add_argument("source_id")
update_parser = skill_source_subparsers.add_parser("update")
update_parser.add_argument("--force", action="store_true")
update_parser.add_argument("source_id", nargs="?")

# Handler routing
if args.command == "skill-source":
    from .cli.commands.skill_source import skill_source_command
    exit_code = skill_source_command(args)
```

---

## 3. Gap Analysis

### 3.1 Side-by-Side Comparison

| Component | Skills System (Working) | Agent System (Broken) | Status |
|-----------|------------------------|----------------------|--------|
| **Configuration** | ✅ SkillSourceConfiguration | ✅ AgentSourceConfiguration | EQUAL |
| **Repository Model** | ✅ SkillSource dataclass | ✅ GitRepository dataclass | EQUAL |
| **Sync Manager** | ✅ GitSkillSourceManager | ✅ GitSourceManager | EQUAL |
| **Discovery Service** | ✅ SkillDiscoveryService | ✅ RemoteAgentDiscoveryService | EQUAL |
| **Shared Sync Service** | ✅ GitSourceSyncService | ✅ GitSourceSyncService (same) | EQUAL |
| **CLI Commands** | ✅ skill-source {list,add,remove,update,enable,disable} | ❌ MISSING | **MISSING** |
| **CLI Integration** | ✅ Routed in main.py | ❌ MISSING | **MISSING** |
| **Auto Sync in Deployment** | ✅ Triggered automatically | ❌ MISSING | **MISSING** |
| **Multi-Source Discovery** | ✅ get_all_skills() with priority | ⚠️ EXISTS but NOT WIRED | **NOT WIRED** |
| **Cache Directory** | ✅ ~/.claude-mpm/cache/skills/ | ❌ ~/.claude-mpm/cache/remote-agents/ (doesn't exist) | **NEVER CREATED** |

### 3.2 Root Causes Identified

**Why sync is never triggered**:
1. ❌ No CLI commands to invoke sync
2. ❌ Deployment service doesn't call GitSourceManager
3. ❌ No automatic sync in `agents deploy` workflow
4. ❌ No integration in AgentDiscoveryService

**Why `agents available` hangs** (hypothesis):
1. ⚠️ AgentListingService likely calls multi-source discovery
2. ⚠️ Multi-source discovery waits for RemoteAgentDiscoveryService
3. ⚠️ RemoteAgentDiscoveryService scans non-existent cache directory
4. ⚠️ Some blocking operation (network request? infinite loop?) causes hang
5. **Needs investigation** - out of scope for this research

**Why cache directories don't exist**:
1. ❌ GitSourceManager.sync_repository() never called
2. ❌ Cache directory creation in sync service never executed
3. ❌ Configuration exists but never acted upon

### 3.3 Missing Components List

**Priority 1: CLI Commands (Mandatory)**
```bash
# Must implement these 6 commands:
claude-mpm agents sync [--force] [--source SOURCE_ID]
claude-mpm agents source list [--by-priority] [--enabled-only] [--json]
claude-mpm agents source add <URL> [--priority N] [--branch BRANCH] [--disabled]
claude-mpm agents source remove <SOURCE_ID> [--force]
claude-mpm agents source enable <SOURCE_ID>
claude-mpm agents source disable <SOURCE_ID>
```

**Priority 2: Integration Layer (Mandatory)**
```python
# Must integrate into deployment workflow:
1. AgentDeploymentService.deploy_system_agents()
   → Should sync git sources first if configured

2. AgentDiscoveryService.list_available_agents()
   → Should include git sources with multi-source discovery

3. Priority resolution in deployment
   → Git sources should override system based on priority
```

**Priority 3: CLI File Structure (Mandatory)**
```
/src/claude_mpm/cli/commands/
├── agent_source.py (NEW - mirror skill_source.py)
│   ├── agent_source_command(args)
│   ├── handle_add_agent_source(args)
│   ├── handle_list_agent_sources(args)
│   ├── handle_remove_agent_source(args)
│   ├── handle_update_agent_sources(args) ← SYNC TRIGGER
│   ├── handle_enable_agent_source(args)
│   └── handle_disable_agent_source(args)
│
└── agents.py (MODIFY - add sync command)
    └── _sync_agents(args) ← NEW METHOD
```

**Priority 4: Argparse Integration (Mandatory)**
```python
# /src/claude_mpm/cli/main.py
# Add agent-source subcommand group (mirror skill-source)

agent_source_parser = subparsers.add_parser(
    "agent-source",
    help="Manage agent source repositories"
)
agent_source_subparsers = agent_source_parser.add_subparsers(
    dest="agent_source_command"
)

# Route to handler
if args.command == "agent-source":
    from .cli.commands.agent_source import agent_source_command
    exit_code = agent_source_command(args)
```

---

## 4. Implementation Roadmap

### Phase 1: CLI Commands (Week 1)

**Files to Create**:
1. `/src/claude_mpm/cli/commands/agent_source.py`
   - Copy `/src/claude_mpm/cli/commands/skill_source.py`
   - Replace `SkillSource` → `GitRepository`
   - Replace `SkillSourceConfiguration` → `AgentSourceConfiguration`
   - Replace `GitSkillSourceManager` → `GitSourceManager`
   - Keep same CLI interface (list, add, remove, update, enable, disable)

**Files to Modify**:
2. `/src/claude_mpm/cli/main.py`
   - Add `agent-source` subparser
   - Add routing to `agent_source_command()`

3. `/src/claude_mpm/cli/commands/agents.py`
   - Add `sync` to `AgentCommands` enum
   - Add `_sync_agents(args)` method (calls GitSourceManager.sync_all_repositories())
   - Wire up in `run()` method's command_map

**Testing**:
```bash
# Manual testing sequence:
claude-mpm agent-source list                    # Should show bobmatnyc/claude-mpm-agents
claude-mpm agent-source update                  # Should sync and create cache
ls ~/.claude-mpm/cache/remote-agents/           # Should show bobmatnyc/claude-mpm-agents/agents/
claude-mpm agents sync --force                  # Should re-sync all sources
```

**Acceptance Criteria**:
- ✅ CLI commands exist and route correctly
- ✅ Sync creates cache directory structure
- ✅ Markdown files downloaded to cache
- ✅ No errors when running update command

---

### Phase 2: Deployment Integration (Week 2)

**Files to Modify**:
1. `/src/claude_mpm/services/agents/deployment/agent_deployment_service.py`
   ```python
   def deploy_system_agents(self, force: bool = False):
       # NEW: Sync git sources before deployment
       config = AgentSourceConfiguration.load()
       if config.get_enabled_repositories():
           self.logger.info("Syncing git agent sources...")
           manager = GitSourceManager()
           manager.sync_all_repositories(config.get_enabled_repositories(), force=force)

       # Existing deployment logic...
   ```

2. `/src/claude_mpm/services/agents/deployment/agent_discovery_service.py`
   ```python
   def list_available_agents(self, log_discovery: bool = True):
       # NEW: Multi-source discovery
       agents = []

       # 1. Discover system agents (existing)
       system_agents = self._discover_system_agents()
       agents.extend(system_agents)

       # 2. Discover git agents (NEW)
       git_agents = self._discover_git_agents()
       agents.extend(git_agents)

       # 3. Apply priority resolution (NEW)
       resolved_agents = self._apply_priority_resolution(agents)

       return resolved_agents

   def _discover_git_agents(self):
       """Discover agents from git sources."""
       config = AgentSourceConfiguration.load()
       manager = GitSourceManager()

       all_agents = []
       for repo in config.get_enabled_repositories():
           agents = manager.list_cached_agents(repo.identifier)
           # Tag with priority
           for agent in agents:
               agent["source"] = "git"
               agent["source_priority"] = repo.priority
           all_agents.extend(agents)

       return all_agents

   def _apply_priority_resolution(self, agents):
       """Resolve conflicts using priority (lower = higher precedence)."""
       # Group by agent_id
       agents_by_id = {}
       for agent in agents:
           agent_id = agent.get("agent_id") or agent.get("name")
           if agent_id not in agents_by_id:
               agents_by_id[agent_id] = []
           agents_by_id[agent_id].append(agent)

       # Select agent with lowest priority for each ID
       resolved = []
       for agent_id, agent_group in agents_by_id.items():
           sorted_group = sorted(agent_group, key=lambda a: a.get("source_priority", 999))
           selected = sorted_group[0]
           resolved.append(selected)

       return resolved
   ```

**Testing**:
```bash
# Integration testing sequence:
claude-mpm agent-source update                  # Sync git sources
claude-mpm agents deploy                        # Should include git agents
claude-mpm agents list --deployed              # Should show agents from git
ls ~/.claude/agents/                           # Should include remote agents
```

**Acceptance Criteria**:
- ✅ `agents deploy` automatically syncs git sources
- ✅ Deployed agents include remote agents from git
- ✅ Priority resolution works (lower priority overrides higher)
- ✅ System agents coexist with git agents

---

### Phase 3: Priority Resolution & Conflict Handling (Week 3)

**Files to Create**:
1. `/src/claude_mpm/services/agents/agent_priority_resolver.py`
   ```python
   class AgentPriorityResolver:
       """Resolves agent conflicts using priority-based selection."""

       def resolve_agents(self, agents: List[Dict]) -> List[Dict]:
           """Apply priority resolution to agent list.

           Args:
               agents: List of agent dicts with source_priority field

           Returns:
               Deduplicated list with lowest priority agent for each ID
           """
           # Group by agent_id
           agents_by_id = self._group_by_id(agents)

           # Select lowest priority for each group
           resolved = []
           for agent_id, agent_group in agents_by_id.items():
               selected = self._select_highest_precedence(agent_group)
               resolved.append(selected)

           return resolved

       def _select_highest_precedence(self, agents: List[Dict]) -> Dict:
           """Select agent with lowest priority number (highest precedence)."""
           return min(agents, key=lambda a: a.get("source_priority", 999))
   ```

**Files to Modify**:
2. `/src/claude_mpm/services/agents/deployment/multi_source_agent_discovery_service.py` (NEW)
   ```python
   class MultiSourceAgentDiscoveryService:
       """Discovers agents from multiple sources with priority resolution."""

       def __init__(self):
           self.system_discovery = AgentDiscoveryService(system_templates_dir)
           self.git_manager = GitSourceManager()
           self.priority_resolver = AgentPriorityResolver()

       def discover_all_agents(self) -> List[Dict]:
           """Discover agents from all sources with priority resolution."""
           all_agents = []

           # System agents (priority from config, default 100)
           system_agents = self.system_discovery.list_available_agents()
           for agent in system_agents:
               agent["source"] = "system"
               agent["source_priority"] = 100
           all_agents.extend(system_agents)

           # Git agents (priority from repository config)
           config = AgentSourceConfiguration.load()
           for repo in config.get_enabled_repositories():
               git_agents = self.git_manager.list_cached_agents(repo.identifier)
               for agent in git_agents:
                   agent["source"] = f"git:{repo.identifier}"
                   agent["source_priority"] = repo.priority
               all_agents.extend(git_agents)

           # Apply priority resolution
           return self.priority_resolver.resolve_agents(all_agents)
   ```

**Testing**:
```bash
# Priority resolution testing:
# Setup: Configure custom repo with priority=10 (higher precedence than system)
claude-mpm agent-source add https://github.com/custom/agents --priority 10
claude-mpm agent-source update

# Create conflicting agent in git repo (same agent_id as system agent)
# Deploy and verify custom agent overrides system agent
claude-mpm agents deploy
claude-mpm agents list --deployed | grep -A5 "agent_id_with_conflict"
# Should show custom agent (priority 10) not system agent (priority 100)
```

**Acceptance Criteria**:
- ✅ Priority resolution algorithm works correctly
- ✅ Lower priority numbers override higher priority numbers
- ✅ Conflicts logged with clear messages
- ✅ Multi-source discovery integrated into deployment

---

### Phase 4: Testing & Documentation (Week 4)

**Unit Tests to Create**:
```python
# tests/unit/cli/commands/test_agent_source.py
def test_handle_add_agent_source():
    """Test adding new agent source."""

def test_handle_update_agent_sources():
    """Test syncing agent sources."""

def test_priority_resolution():
    """Test priority-based agent selection."""

# tests/unit/services/agents/test_git_source_manager.py
def test_sync_repository():
    """Test repository sync creates cache."""

def test_list_cached_agents():
    """Test listing agents from cache."""

# tests/integration/test_agent_git_sources_workflow.py
def test_end_to_end_git_source_workflow():
    """Test complete workflow: add source → sync → deploy → verify."""
```

**Integration Tests**:
```bash
# tests/integration/test_agent_sources.sh

# 1. Add git source
claude-mpm agent-source add https://github.com/test/agents

# 2. Verify configuration
assert_file_exists ~/.claude-mpm/config/agent_sources.yaml

# 3. Sync sources
claude-mpm agent-source update

# 4. Verify cache created
assert_dir_exists ~/.claude-mpm/cache/remote-agents/test/agents/

# 5. Verify markdown files downloaded
assert_file_count ~/.claude-mpm/cache/remote-agents/test/agents/ "*.md" -gt 0

# 6. Deploy agents
claude-mpm agents deploy

# 7. Verify git agents deployed
assert_file_exists ~/.claude/agents/some-git-agent.md

# 8. Verify priority resolution
# (Test that custom agent overrides system agent)
```

**Documentation to Update**:
```markdown
# docs/reference/AGENT_SOURCES.md (NEW)

## Agent Git Sources

### Overview
Agent git sources allow loading agents from GitHub repositories...

### Configuration
Edit ~/.claude-mpm/config/agent_sources.yaml...

### CLI Commands
- claude-mpm agent-source list
- claude-mpm agent-source add <URL>
- claude-mpm agent-source update
...

### Priority Resolution
Lower priority number = higher precedence...

### Troubleshooting
- Cache not created: Run `claude-mpm agent-source update`
- Agents not loading: Check priority conflicts
...

# docs/reference/CLI.md (UPDATE)
Add agent-source commands to CLI reference...

# README.md (UPDATE)
Add git sources feature to feature list...
```

**Acceptance Criteria**:
- ✅ 90%+ test coverage for new code
- ✅ Integration tests pass end-to-end
- ✅ Documentation complete and reviewed
- ✅ Release notes prepared

---

## 5. Technical Specifications

### 5.1 Service Interfaces

**AgentSourceManager Interface** (based on GitSourceManager):

```python
class GitSourceManager:
    """Manages Git repository sources for agents."""

    def __init__(self, cache_root: Optional[Path] = None):
        """Initialize with cache directory.

        Args:
            cache_root: Root cache directory (default: ~/.claude-mpm/cache/remote-agents/)
        """
        self.cache_root = cache_root or Path.home() / ".claude-mpm" / "cache" / "remote-agents"
        self.cache_root.mkdir(parents=True, exist_ok=True)

    def sync_repository(self, repo: GitRepository, force: bool = False) -> Dict[str, Any]:
        """Sync single repository from Git.

        Args:
            repo: GitRepository to sync
            force: Force sync even if cache is fresh

        Returns:
            {
                "synced": bool,
                "etag": str,
                "files_updated": int,
                "files_added": int,
                "files_removed": int,
                "files_cached": int,
                "agents_discovered": List[str],
                "timestamp": str,
                "error": str (if failed)
            }
        """
        pass

    def sync_all_repositories(self, repos: List[GitRepository], force: bool = False) -> Dict[str, Dict]:
        """Sync multiple repositories.

        Args:
            repos: List of GitRepository to sync
            force: Force sync even if cache is fresh

        Returns:
            {
                "owner/repo/subdir": {
                    "synced": bool,
                    "files_updated": int,
                    ...
                },
                "owner/repo2": {...}
            }
        """
        pass

    def list_cached_agents(self, repo_identifier: Optional[str] = None) -> List[Dict]:
        """List all cached agents, optionally filtered by repository.

        Args:
            repo_identifier: Optional repository filter (e.g., "owner/repo/agents")

        Returns:
            [
                {
                    "name": "engineer",
                    "version": "2.5.0",
                    "path": "/cache/owner/repo/agents/engineer.md",
                    "repository": "owner/repo/agents",
                    "source_priority": 10
                }
            ]
        """
        pass
```

**CLI Handler Interface** (based on skill_source.py):

```python
# /src/claude_mpm/cli/commands/agent_source.py

def agent_source_command(args) -> int:
    """Main entry point for agent-source commands."""
    handlers = {
        "add": handle_add_agent_source,
        "list": handle_list_agent_sources,
        "remove": handle_remove_agent_source,
        "update": handle_update_agent_sources,
        "enable": handle_enable_agent_source,
        "disable": handle_disable_agent_source,
        "show": handle_show_agent_source,
    }
    handler = handlers.get(getattr(args, "agent_source_command", None))
    return handler(args) if handler else 1

def handle_add_agent_source(args) -> int:
    """Add new agent source.

    Args:
        args.url: Git repository URL
        args.priority: Priority (default: 100)
        args.branch: Branch name (default: "main")
        args.disabled: Start disabled (default: False)

    Returns:
        Exit code (0=success, 1=error)
    """
    pass

def handle_update_agent_sources(args) -> int:
    """Sync agent sources.

    Args:
        args.source_id: Optional source to sync (None=all)
        args.force: Force re-download (default: False)

    Returns:
        Exit code
    """
    config = AgentSourceConfiguration.load()
    manager = GitSourceManager()

    if args.source_id:
        result = manager.sync_source(args.source_id, force=args.force)
        print(f"✅ Synced {result['files_updated']} files")
    else:
        results = manager.sync_all_sources(force=args.force)
        print(f"✅ Synced {results['synced_count']}/{len(results['sources'])} sources")

    return 0 if result["synced"] else 1
```

### 5.2 Data Flow Diagrams

**Agent Discovery with Git Sources**:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User runs: claude-mpm agents deploy                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. AgentDeploymentService.deploy_system_agents()           │
│    ├─ Load AgentSourceConfiguration                        │
│    ├─ Check if git sources configured                      │
│    └─ If yes: GitSourceManager.sync_all_repositories()     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. GitSourceManager.sync_repository()                      │
│    ├─ Build raw GitHub URL                                 │
│    ├─ GitSourceSyncService.sync_agents()                   │
│    │  ├─ Fetch directory listing                           │
│    │  ├─ Download .md files                                │
│    │  └─ Save to ~/.claude-mpm/cache/remote-agents/        │
│    └─ RemoteAgentDiscoveryService.discover_remote_agents() │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. MultiSourceAgentDiscoveryService.discover_all_agents()  │
│    ├─ System agents (priority=100)                         │
│    ├─ Git agents (priority from config)                    │
│    └─ AgentPriorityResolver.resolve_agents()               │
│       ├─ Group by agent_id                                 │
│       ├─ Select lowest priority for each group             │
│       └─ Return deduplicated agent list                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. DeploymentService deploys resolved agent list           │
│    ├─ Convert to Markdown format                           │
│    ├─ Write to ~/.claude/agents/                           │
│    └─ Report deployment summary                            │
└─────────────────────────────────────────────────────────────┘
```

**Git Source Sync Flow**:

```
┌─────────────────────────────────────────────────────────────┐
│ User: claude-mpm agent-source update                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ CLI: handle_update_agent_sources(args)                     │
│      ├─ Load AgentSourceConfiguration                      │
│      ├─ Initialize GitSourceManager                        │
│      └─ Call sync_all_repositories()                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ GitSourceManager: For each enabled repository              │
│      ├─ Parse GitHub URL → owner/repo                      │
│      ├─ Build raw URL: raw.githubusercontent.com/...       │
│      └─ Call sync_repository(repo)                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ GitSourceSyncService: sync_agents(force_refresh)           │
│      ├─ Fetch directory listing (JSON API)                 │
│      ├─ For each .md file:                                 │
│      │  ├─ Check ETag cache                                │
│      │  ├─ Download if new/changed                         │
│      │  └─ Save to cache_dir                               │
│      └─ Return sync results                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ RemoteAgentDiscoveryService: discover_remote_agents()      │
│      ├─ Scan cache directory for *.md                      │
│      ├─ Parse YAML frontmatter                             │
│      ├─ Extract agent metadata                             │
│      └─ Return agent list                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ CLI: Display sync results                                  │
│      ├─ Files synced: N                                    │
│      ├─ Agents discovered: M                               │
│      └─ Exit code: 0 (success)                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 Error Handling Strategy

**Error Categories**:

1. **Configuration Errors**
   - Invalid GitHub URL
   - Missing repository
   - Invalid priority value
   - **Action**: Validate early, fail fast with clear message

2. **Network Errors**
   - GitHub API rate limit
   - Network timeout
   - DNS resolution failure
   - **Action**: Retry with exponential backoff, cache last good state

3. **File System Errors**
   - Permission denied on cache directory
   - Disk full
   - Corrupted cache files
   - **Action**: Create cache with fallback paths, validate integrity

4. **Discovery Errors**
   - Invalid Markdown format
   - Missing YAML frontmatter
   - Corrupted agent files
   - **Action**: Skip invalid files, log warnings, continue with valid agents

**Error Recovery Flow**:

```python
# Graceful degradation example
def sync_repository(self, repo: GitRepository, force: bool = False):
    try:
        # Attempt sync
        result = self._perform_sync(repo, force)
        return {"synced": True, **result}

    except NetworkError as e:
        # Retry with exponential backoff
        for attempt in range(3):
            time.sleep(2 ** attempt)
            try:
                result = self._perform_sync(repo, force)
                return {"synced": True, **result, "retries": attempt + 1}
            except NetworkError:
                continue

        # Use cached version if available
        cached_agents = self._load_from_cache(repo)
        if cached_agents:
            logger.warning(f"Using cached agents for {repo.identifier}")
            return {"synced": False, "cached": True, "agents": cached_agents}

        # Complete failure
        return {"synced": False, "error": str(e)}

    except FileSystemError as e:
        # Try fallback cache location
        fallback_cache = Path("/tmp/claude-mpm-cache")
        if self._try_fallback_cache(repo, fallback_cache):
            return {"synced": True, "cache_location": str(fallback_cache)}

        return {"synced": False, "error": f"Cache error: {e}"}
```

### 5.4 Cache Directory Structure

**Recommended Structure** (matching skills system):

```
~/.claude-mpm/
└── cache/
    ├── skills/                          # ✅ WORKING (skills system)
    │   ├── system/                      # Priority: 0
    │   │   ├── code-review.md
    │   │   ├── testing.md
    │   │   └── .etag.json               # ETag cache for incremental updates
    │   └── custom-source/               # Priority: 100
    │       ├── custom-skill.md
    │       └── .etag.json
    │
    └── remote-agents/                   # ❌ MISSING (to be created)
        ├── bobmatnyc/
        │   └── claude-mpm-agents/
        │       └── agents/              # Subdirectory from config
        │           ├── engineer.md
        │           ├── research.md
        │           ├── pm.md
        │           ├── .etag.json       # ETag cache
        │           └── .meta.json       # Sync metadata
        │
        └── custom-org/
            └── custom-agents/
                └── .../
```

**Cache Metadata Files**:

```json
// .etag.json (per-file ETag caching)
{
  "engineer.md": {
    "etag": "W/\"abc123\"",
    "last_modified": "2025-11-30T10:00:00Z",
    "content_hash": "sha256:..."
  }
}

// .meta.json (repository sync metadata)
{
  "repository": "bobmatnyc/claude-mpm-agents",
  "subdirectory": "agents",
  "last_sync": "2025-11-30T10:00:00Z",
  "total_files": 55,
  "etag": "W/\"repository-etag\"",
  "agent_count": 55
}
```

---

## 6. Testing Strategy

### 6.1 Unit Test Coverage

**Target Coverage**: 90%+ for new code

**Critical Test Cases**:

```python
# tests/unit/config/test_agent_sources.py
class TestAgentSourceConfiguration:
    def test_load_configuration(self):
        """Test loading agent sources from YAML."""

    def test_save_configuration(self):
        """Test saving configuration to YAML."""

    def test_get_enabled_repositories(self):
        """Test filtering enabled repositories."""

    def test_priority_sorting(self):
        """Test repositories sorted by priority."""

    def test_validate_repository(self):
        """Test repository validation rules."""

# tests/unit/services/agents/test_git_source_manager.py
class TestGitSourceManager:
    def test_sync_repository_success(self):
        """Test successful repository sync."""

    def test_sync_repository_network_error(self):
        """Test network error handling with retry."""

    def test_list_cached_agents(self):
        """Test listing cached agents."""

    def test_cache_directory_creation(self):
        """Test automatic cache directory creation."""

    def test_etag_caching(self):
        """Test ETag-based incremental updates."""

# tests/unit/services/agents/test_agent_priority_resolver.py
class TestAgentPriorityResolver:
    def test_priority_resolution_basic(self):
        """Test basic priority resolution (lower wins)."""

    def test_priority_resolution_conflicts(self):
        """Test handling of priority conflicts."""

    def test_priority_resolution_same_priority(self):
        """Test tie-breaking when priorities equal."""

# tests/unit/cli/commands/test_agent_source.py
class TestAgentSourceCommands:
    def test_add_agent_source(self):
        """Test adding new agent source."""

    def test_update_agent_sources(self):
        """Test syncing agent sources."""

    def test_list_agent_sources(self):
        """Test listing configured sources."""

    def test_remove_agent_source(self):
        """Test removing agent source."""
```

### 6.2 Integration Test Scenarios

**Scenario 1: First-Time Setup**
```bash
# Clean state
rm -rf ~/.claude-mpm/cache/remote-agents/
rm -f ~/.claude-mpm/config/agent_sources.yaml

# Add source
claude-mpm agent-source add https://github.com/bobmatnyc/claude-mpm-agents \
    --priority 10 --branch main

# Verify configuration created
assert_file_exists ~/.claude-mpm/config/agent_sources.yaml
assert_contains ~/.claude-mpm/config/agent_sources.yaml "bobmatnyc/claude-mpm-agents"

# Sync sources
claude-mpm agent-source update

# Verify cache created
assert_dir_exists ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/
assert_file_count ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/ "*.md" -gt 50

# Deploy agents
claude-mpm agents deploy

# Verify git agents deployed
assert_file_exists ~/.claude/agents/engineer.md
assert_contains ~/.claude/agents/engineer.md "# Engineer Agent"
```

**Scenario 2: Priority Resolution**
```bash
# Setup: System has 'engineer' agent (priority 100)
# Add custom repo with 'engineer' agent (priority 10 - higher precedence)

# Add custom source
claude-mpm agent-source add https://github.com/custom/agents --priority 10

# Sync
claude-mpm agent-source update

# Deploy
claude-mpm agents deploy

# Verify custom engineer wins
claude-mpm agents list --deployed | grep engineer
# Should show: engineer (source: git:custom/agents)
```

**Scenario 3: Incremental Updates (ETag Caching)**
```bash
# First sync
claude-mpm agent-source update
start_time=$(date +%s)

# Second sync (should be fast with ETag cache)
claude-mpm agent-source update
end_time=$(date +%s)
duration=$((end_time - start_time))

# Verify ETag cache used (should complete <2 seconds)
assert_less_than $duration 2

# Verify cache files not re-downloaded
assert_log_contains "Cache hits: 50+"
```

**Scenario 4: Error Recovery**
```bash
# Simulate network error
# (Use mock server or network simulation)
export HTTP_PROXY=http://invalid-proxy:9999

# Attempt sync (should fail gracefully)
claude-mpm agent-source update
assert_exit_code 1
assert_output_contains "Network error"
assert_output_contains "Using cached agents"

# Verify deployment still works with cached agents
claude-mpm agents deploy
assert_exit_code 0

# Restore network and verify recovery
unset HTTP_PROXY
claude-mpm agent-source update
assert_exit_code 0
```

### 6.3 Test Data Setup

**Mock GitHub Repository Structure**:

```
test-org/test-agents/
└── agents/
    ├── engineer.md
    │   ---
    │   name: Test Engineer
    │   description: Test engineer agent
    │   priority: 50
    │   ---
    │   # Engineer Agent
    │   ...
    │
    ├── researcher.md
    └── pm.md
```

**Test Configuration Files**:

```yaml
# tests/fixtures/agent_sources.yaml
disable_system_repo: false
repositories:
  - url: https://github.com/test-org/test-agents
    subdirectory: agents
    enabled: true
    priority: 10

  - url: https://github.com/custom-org/custom-agents
    subdirectory: null
    enabled: true
    priority: 50
```

**Mock HTTP Responses**:

```python
# tests/mocks/github_api.py
MOCK_DIRECTORY_LISTING = [
    {
        "name": "engineer.md",
        "download_url": "https://raw.githubusercontent.com/test-org/test-agents/main/agents/engineer.md",
        "type": "file",
        "size": 1024
    },
    {
        "name": "researcher.md",
        "download_url": "...",
        "type": "file",
        "size": 2048
    }
]

MOCK_AGENT_CONTENT = """---
name: Test Engineer
description: Test engineer agent
priority: 50
---

# Engineer Agent
Test instructions...
"""
```

---

## Appendix A: File Locations Reference

**Configuration Files**:
- Agent sources config: `~/.claude-mpm/config/agent_sources.yaml`
- Agent sources cache: `~/.claude-mpm/cache/remote-agents/{owner}/{repo}/{subdir}/`

**Source Code Files**:
```
/src/claude_mpm/
├── config/
│   └── agent_sources.py                # AgentSourceConfiguration
├── models/
│   └── git_repository.py               # GitRepository
├── services/
│   ├── agents/
│   │   ├── git_source_manager.py       # GitSourceManager (✅ exists)
│   │   ├── agent_priority_resolver.py  # AgentPriorityResolver (❌ to create)
│   │   ├── deployment/
│   │   │   ├── agent_discovery_service.py
│   │   │   ├── remote_agent_discovery_service.py
│   │   │   └── multi_source_agent_discovery_service.py  # ❌ to create
│   │   └── sources/
│   │       └── git_source_sync_service.py  # Shared with skills
│   └── skills/
│       └── git_skill_source_manager.py      # REFERENCE IMPLEMENTATION
└── cli/
    ├── main.py                          # Argparse routing (❌ needs update)
    └── commands/
        ├── agent_source.py              # ❌ to create (copy from skill_source.py)
        ├── agents.py                    # ❌ needs sync command
        └── skill_source.py              # ✅ REFERENCE IMPLEMENTATION
```

**Test Files to Create**:
```
/tests/
├── unit/
│   ├── config/
│   │   └── test_agent_sources.py
│   ├── services/
│   │   └── agents/
│   │       ├── test_git_source_manager.py
│   │       └── test_agent_priority_resolver.py
│   └── cli/
│       └── commands/
│           └── test_agent_source.py
├── integration/
│   ├── test_agent_git_sources_workflow.py
│   └── test_agent_priority_resolution.py
└── fixtures/
    ├── agent_sources.yaml
    └── mock_agents/
        ├── engineer.md
        └── researcher.md
```

---

## Appendix B: Skills System Reference Code

**For quick reference during implementation, key files to copy/adapt**:

1. **Configuration**: `/src/claude_mpm/config/skill_sources.py`
   - Copy to: `/src/claude_mpm/config/agent_sources.py` (✅ already exists)
   - Changes needed: None (models already aligned)

2. **Sync Manager**: `/src/claude_mpm/services/skills/git_skill_source_manager.py`
   - Reference for: `/src/claude_mpm/services/agents/git_source_manager.py` (✅ already exists)
   - Changes needed: None (logic already correct)

3. **CLI Commands**: `/src/claude_mpm/cli/commands/skill_source.py`
   - Copy to: `/src/claude_mpm/cli/commands/agent_source.py` (❌ needs creation)
   - Changes needed:
     - Replace `SkillSource` → `GitRepository`
     - Replace `SkillSourceConfiguration` → `AgentSourceConfiguration`
     - Replace `GitSkillSourceManager` → `GitSourceManager`
     - Replace `SkillDiscoveryService` → `RemoteAgentDiscoveryService`

4. **Discovery Service**: `/src/claude_mpm/services/skills/skill_discovery_service.py`
   - Reference for: `/src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py` (✅ already exists)
   - Changes needed: None (logic already correct)

**Key differences to preserve**:
- Skills: YAML frontmatter + Markdown body
- Agents: YAML frontmatter + Markdown body (same format!)
- Skills: skill_id generated from name
- Agents: agent_id from frontmatter or generated from name (same logic!)

**Conclusion**: Agent system is 60% complete. Skills system provides exact blueprint. Copy CLI commands, wire up integration, test thoroughly.
