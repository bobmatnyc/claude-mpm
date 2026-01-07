# Claude-MPM Startup: Agent and Skill Loading Analysis

**Research Date:** 2025-12-28
**Researcher:** Research Agent
**Purpose:** Understand agent and skill loading mechanisms for profile-based filtering integration

---

## Executive Summary

Claude-MPM loads agents and skills during startup through a multi-phase initialization process. Agents are discovered from a unified registry system and deployed to `.claude/agents/`, while skills follow a similar pattern deploying to `.claude/skills/`. The best integration point for profile-based filtering is in the **deployment phase** (not discovery phase) using the existing `configuration.yaml` filtering mechanisms.

**Key Finding:** Profile filtering should be implemented at the **agent/skill deployment level** by extending the existing `agent_deployment.excluded_agents` configuration pattern.

---

## 1. Agent Loading Architecture

### 1.1 Discovery vs. Deployment

Claude-MPM separates agent management into two distinct phases:

1. **Discovery Phase**: Find all available agents from various sources
2. **Deployment Phase**: Deploy selected agents to `.claude/agents/` where Claude Code can discover them

```
┌─────────────────────────────────────────────────────────────┐
│                    DISCOVERY PHASE                          │
│  (Find all available agents from all sources)               │
│                                                              │
│  Sources:                                                    │
│  • ~/.claude-mpm/cache/agents/ (git cache from GitHub)      │
│  • Built-in agents from package                             │
│  • Project-specific agents                                  │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ Unified Agent Registry
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   DEPLOYMENT PHASE                          │
│  (Deploy selected agents to Claude Code discovery path)     │
│                                                              │
│  Filter using:                                               │
│  • excluded_agents list                                      │
│  • filter_non_mpm_agents flag                               │
│  • mpm_author_patterns                                       │
│                                                              │
│  Deploy to: .claude/agents/                                 │
└─────────────────────────────────────────────────────────────┘
```

**Why This Separation Matters for Profile Filtering:**
- Discovery: Should remain comprehensive (find everything available)
- Deployment: Perfect place for filtering (deploy only profile-specific agents)

### 1.2 Startup Flow for Agents

**File:** `src/claude_mpm/cli/startup.py`

```python
def run_background_services():
    """Initialize all background services on startup."""

    # 1. Sync remote agent sources (lines 389-704)
    sync_remote_agents_on_startup()

    # 2. Display agent summary (lines 937-1019)
    show_agent_summary()
```

**Phase 1: Remote Agent Sync** (`sync_remote_agents_on_startup()` - lines 389-704)

```python
def sync_remote_agents_on_startup():
    """Synchronize agent templates from remote sources."""

    # Step 1: Sync files from Git sources to cache
    result = sync_agents_on_startup()  # Downloads to ~/.claude-mpm/cache/agents/

    # Step 2: Deploy agents from cache to .claude/agents/
    deployment_service = AgentDeploymentService()
    deployment_result = deployment_service.deploy_agents(
        target_dir=Path.cwd() / ".claude" / "agents",
        force_rebuild=False,
        deployment_mode="update"
    )

    # Step 3: Cleanup orphaned agents
    _cleanup_orphaned_agents(deploy_target, deployed_filenames)
```

**Key Discovery Points:**

1. **Git Source Manager** handles remote sync
   - Location: `src/claude_mpm/services/agents/git_source_manager.py`
   - Downloads agents to: `~/.claude-mpm/cache/agents/`

2. **AgentDeploymentService** handles deployment
   - Location: `src/claude_mpm/services/agents/deployment/agent_deployment.py`
   - Deploys agents to: `.claude/agents/` (project-level)
   - **This is the filtering integration point**

3. **Orphan Cleanup** removes stale agents
   - Only removes claude-mpm managed agents (checks frontmatter ownership)
   - Preserves user-created agents

### 1.3 Agent Discovery System

**File:** `src/claude_mpm/core/agent_registry.py`

The agent registry is a **compatibility wrapper** around the unified agent registry:

```python
class SimpleAgentRegistry:
    """Compatibility wrapper for simple agent registry."""

    def __init__(self, framework_path: Optional[Path] = None):
        self.framework_path = framework_path
        self._unified_registry = get_agent_registry()  # Unified system
        self.agents = {}
        self._discover_agents()

    def _discover_agents(self):
        """Discover agents using the unified registry."""
        unified_agents = self._unified_registry.discover_agents()

        # Convert to old format for compatibility
        self.agents = {
            name: {
                "name": unified_metadata.name,
                "type": unified_metadata.agent_type.value,
                "path": unified_metadata.path,
                # ... more metadata
            }
            for name, unified_metadata in unified_agents.items()
        }
```

**Data Structure Used:**

```python
# Internal registry structure (unified_agent_registry.py)
{
    "agent_name": UnifiedAgentMetadata(
        name="agent_name",
        agent_type=AgentType.ENGINEER,  # Enum
        tier=AgentTier.SYSTEM,          # Enum: SYSTEM, USER, PROJECT
        path="/path/to/agent.md",
        last_modified=1234567890.0,
        specializations=["coding", "architecture"],
        description="Agent description"
    )
}
```

### 1.4 Agent Loader Integration

**File:** `src/claude_mpm/agents/agent_loader.py`

```python
class AgentLoader:
    """Simplified Agent Loader - Clean interface to agent registry."""

    def __init__(self):
        # Initialize the agent registry
        self.registry = get_agent_registry()

        # Load agents through registry
        self.registry.load_agents()

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve agent configuration by ID."""
        return self.registry.get_agent(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        """Get summary list of all available agents."""
        return self.registry.list_agents()
```

**Agent Prompt Loading:**

```python
def get_agent_prompt(agent_name: str,
                     force_reload: bool = False,
                     return_model_info: bool = False,
                     **kwargs) -> Union[str, Tuple[str, str, Dict]]:
    """Get agent prompt with optional dynamic model selection."""

    # 1. Normalize agent name
    normalizer = AgentNameNormalizer()
    actual_agent_id = normalizer.normalize(agent_name)

    # 2. Load from registry
    loader = _get_loader()
    prompt = loader.get_agent_prompt(actual_agent_id, force_reload)

    # 3. Analyze task complexity (optional)
    # 4. Select optimal model (optional)
    # 5. Return prompt (with or without model info)

    return prompt
```

---

## 2. Skill Loading Architecture

### 2.1 Skill Loading Flow

**File:** `src/claude_mpm/cli/startup.py`

```python
def run_background_services():
    """Initialize all background services on startup."""

    # Skills deployment order (precedence: remote > bundled)
    deploy_bundled_skills()              # Base layer (lines 148-205)
    sync_remote_skills_on_startup()      # Override layer (lines 707-934)
    discover_and_link_runtime_skills()   # Discovery layer (lines 208-233)
    show_skill_summary()                 # Summary display (lines 1021-1089)
    verify_and_show_pm_skills()          # PM skills verification (lines 1092-1128)
```

**Phase 1: Bundled Skills Deployment** (lines 148-205)

```python
def deploy_bundled_skills():
    """Deploy bundled Claude Code skills on startup."""

    # Check auto_deploy configuration
    config = config_loader.load_config()
    skills_config = config.get("skills", {})
    if not skills_config.get("auto_deploy", True):
        return  # Auto-deploy disabled

    # Import and run skills deployment
    skills_service = SkillsService()
    deployment_result = skills_service.deploy_bundled_skills()

    # Log results
    if deployment_result.get("deployed"):
        deployed_count = len(deployment_result["deployed"])
        print(f"✓ Bundled skills ready ({deployed_count} deployed)")
```

**Phase 2: Remote Skills Sync** (lines 707-934)

```python
def sync_remote_skills_on_startup():
    """Synchronize skill templates from remote sources on startup."""

    # 1. Sync files from Git sources
    manager = GitSkillSourceManager(config)
    results = manager.sync_all_sources(force=False, progress_callback=sync_progress.update)

    # 2. Scan agents for skill requirements → save to configuration.yaml
    agents_dir = Path.cwd() / ".claude" / "agents"
    agent_skills = get_required_skills_from_agents(agents_dir)
    save_agent_skills_to_config(list(agent_skills), project_config_path)

    # 3. Resolve which skills to deploy (user_defined vs agent_referenced)
    skills_to_deploy, skill_source = get_skills_to_deploy(project_config_path)

    # 4. Deploy resolved skills to .claude/skills/
    deployment_result = manager.deploy_skills(
        target_dir=Path.cwd() / ".claude" / "skills",
        force=False,
        skill_filter=set(skills_to_deploy) if skills_to_deploy else None
    )
```

**Critical Insight: Skill Selection Logic**

Skills are filtered based on `configuration.yaml`:

```yaml
skills:
  # User-defined list (manual override)
  user_defined: []

  # Agent-referenced skills (auto-discovered from agents)
  agent_referenced:
    - toolchains-python-frameworks-django
    - toolchains-typescript-core
    # ... 100+ skills
```

**Selection Priority:**
1. If `user_defined` is non-empty → deploy only those skills
2. If `user_defined` is empty → deploy `agent_referenced` skills

**This is the perfect pattern for profile-based filtering!**

### 2.2 Skill Discovery System

**File:** `src/claude_mpm/skills/skill_manager.py`

```python
class SkillManager:
    """Manages skills and their integration with agents."""

    def __init__(self):
        self.registry = get_registry()
        self.agent_skill_mapping: Dict[str, List[str]] = {}
        self._load_agent_mappings()

    def _load_agent_mappings(self):
        """Load skill mappings from agent templates."""
        agent_templates_dir = Path(__file__).parent.parent / "agents" / "templates"

        for template_file in agent_templates_dir.glob("*.json"):
            agent_data = json.load(template_file)
            agent_id = agent_data.get("agent_id")
            skills = agent_data.get("skills", [])

            if skills:
                self.agent_skill_mapping[agent_id] = skills
```

**Data Structure:**

```python
# Agent-to-skill mapping
{
    "engineer": ["python-skills", "typescript-skills"],
    "qa": ["testing-skills", "playwright-skills"],
    "research": ["analysis-skills", "documentation-skills"]
}

# Skill registry (from registry.py)
{
    "skill_name": Skill(
        name="skill_name",
        path=Path("/path/to/skill"),
        content="skill instructions",
        source="bundled|remote|pm",
        version="1.0.0",
        skill_id="skill_name",
        description="Skill description",
        agent_types=["engineer", "qa"]  # Which agents can use this skill
    )
}
```

### 2.3 Agent-Skill Integration

```python
def get_agent_skills(self, agent_type: str) -> List[Skill]:
    """Get all skills for an agent (bundled + discovered + PM skills)."""

    # 1. Get skills from mapping
    skill_names = self.agent_skill_mapping.get(agent_type, [])
    skills = [self.registry.get_skill(name) for name in skill_names]

    # 2. Include skills with no agent restriction
    additional_skills = self.registry.get_skills_for_agent(agent_type)

    # 3. Add PM skills for PM agent only
    if agent_type.lower() in ('pm', 'project-manager'):
        pm_skill_dicts = self._get_pm_skills()
        # Convert to Skill objects and append
```

---

## 3. Configuration Loading System

### 3.1 Configuration File Location

**Primary Config:** `.claude-mpm/configuration.yaml` (project-level)

**Search Paths:**
```python
# From ConfigLoader (src/claude_mpm/core/shared/config_loader.py)
MAIN_CONFIG_PATTERN = ConfigPattern(
    filenames=[
        "claude-mpm.yaml",
        "claude-mpm.yml",
        ".claude-mpm.yaml",
        ".claude-mpm.yml",
        "config.yaml",
        "config.yml"
    ],
    search_paths=[
        "~/.config/claude-mpm",  # User-level
        ".",                      # Project root
        "./config",               # Config directory
        "/etc/claude-mpm"         # System-level
    ]
)
```

### 3.2 Configuration Loading Flow

```python
class ConfigLoader:
    """Centralized configuration loading utility."""

    def load_config(self, pattern: ConfigPattern,
                    cache_key: Optional[str] = None,
                    force_reload: bool = False) -> Config:
        """Load configuration using a pattern."""

        # 1. Check cache
        if not force_reload and cache_key in self._cache:
            return self._cache[cache_key]

        # 2. Start with defaults
        config_data = pattern.defaults.copy() if pattern.defaults else {}

        # 3. Load from files
        config_file = self._find_config_file(pattern)
        if config_file:
            file_config = self._load_config_file(config_file)
            config_data.update(file_config)

        # 4. Load from environment variables
        if pattern.env_prefix:
            env_config = self._load_env_config(pattern.env_prefix)
            config_data.update(env_config)

        # 5. Create and cache Config instance
        config = Config(config_data)
        self._cache[cache_key] = config

        return config
```

**Priority Order:**
1. Defaults (hardcoded in code)
2. Configuration file (YAML/JSON)
3. Environment variables (highest priority)

### 3.3 Existing Filtering Mechanisms

**Agent Deployment Filtering** (from `configuration.yaml`):

```yaml
agent_deployment:
  case_sensitive: false
  exclude_dependencies: false
  excluded_agents: []              # ← Profile filtering could extend this
  filter_non_mpm_agents: true
  mpm_author_patterns:
    - "claude mpm"
    - "claude-mpm"
    - "anthropic"
```

**Skill Deployment Filtering** (from `configuration.yaml`):

```yaml
skills:
  user_defined: []                 # ← Profile filtering could extend this
  agent_referenced:                # ← Auto-discovered from agents
    - toolchains-python-frameworks-django
    - toolchains-typescript-core
    # ... 100+ skills
```

**Key Insight:** Both systems already support filtering lists in configuration. Profile-based filtering should follow this pattern.

---

## 4. Integration Points for Profile Filtering

### 4.1 Recommended Integration Point: Deployment Phase

**Why Deployment (not Discovery)?**

1. **Discovery should remain comprehensive**
   - Users need to see what's available
   - Commands like `agent-manager list` should show all options
   - Filtering at discovery breaks introspection

2. **Deployment is where selection happens**
   - Already has filtering mechanisms (`excluded_agents`, `user_defined` skills)
   - Controls what Claude Code actually sees
   - Matches user mental model ("I'm using Python profile")

3. **Configuration system is ready**
   - `configuration.yaml` is loaded at startup
   - Supports lists and filtering
   - Environment variable override available

### 4.2 Proposed Configuration Schema

**Add to `configuration.yaml`:**

```yaml
profiles:
  # Currently active profile (can be overridden by env var)
  active: "python-fullstack"

  # Profile definitions
  definitions:
    python-fullstack:
      agents:
        include:
          - engineer
          - python-engineer
          - qa
          - documentation
        exclude: []
      skills:
        include_patterns:
          - "toolchains-python-*"
          - "universal-*"
          - "toolchains-typescript-*"  # For frontend
        exclude_patterns:
          - "*-java-*"
          - "*-golang-*"

    typescript-frontend:
      agents:
        include:
          - engineer
          - typescript-engineer
          - react-engineer
          - qa
        exclude: []
      skills:
        include_patterns:
          - "toolchains-typescript-*"
          - "toolchains-javascript-*"
          - "universal-*"
        exclude_patterns:
          - "*-python-*"
          - "*-java-*"

    minimal:
      agents:
        include:
          - engineer
          - qa
          - documentation
        exclude: []
      skills:
        include_patterns:
          - "universal-*"
        exclude_patterns:
          - "toolchains-*"  # Only universal skills

# Environment variable override:
# CLAUDE_MPM_PROFILE=typescript-frontend
```

### 4.3 Implementation Locations

**File Modifications Required:**

1. **Agent Deployment Service**
   - File: `src/claude_mpm/services/agents/deployment/agent_deployment.py`
   - Method: `deploy_agents()`
   - Add: Profile-based filtering after line 200 (deployment pipeline)

2. **Skill Deployment Service**
   - File: `src/claude_mpm/services/skills/git_skill_source_manager.py`
   - Method: `deploy_skills()`
   - Add: Profile-based filtering using existing `skill_filter` parameter

3. **Configuration Loader**
   - File: `src/claude_mpm/core/shared/config_loader.py`
   - Add: `load_profile_config()` method
   - Add: Profile resolution logic (active profile + env override)

4. **Startup Integration**
   - File: `src/claude_mpm/cli/startup.py`
   - Methods: `sync_remote_agents_on_startup()` and `sync_remote_skills_on_startup()`
   - Add: Profile config loading and passing to deployment services

### 4.4 Implementation Pseudocode

```python
# In startup.py - sync_remote_agents_on_startup()
def sync_remote_agents_on_startup():
    """Synchronize agent templates with profile filtering."""

    # Load profile configuration
    config_loader = ConfigLoader()
    profile_config = config_loader.load_profile_config()
    active_profile = profile_config.get_active_profile()

    # Get profile agent filter
    agent_filter = active_profile.get_agent_filter() if active_profile else None

    # Deploy with filtering
    deployment_service = AgentDeploymentService()
    deployment_result = deployment_service.deploy_agents(
        target_dir=Path.cwd() / ".claude" / "agents",
        force_rebuild=False,
        deployment_mode="update",
        profile_filter=agent_filter  # NEW PARAMETER
    )

# In agent_deployment.py - deploy_agents()
def deploy_agents(self, target_dir: Path,
                  force_rebuild: bool = False,
                  deployment_mode: str = "update",
                  profile_filter: Optional[ProfileFilter] = None) -> Dict[str, Any]:
    """Deploy agents with optional profile filtering."""

    # Existing deployment logic...
    agents_to_deploy = self.discovery_service.discover_agents()

    # NEW: Apply profile filtering
    if profile_filter:
        agents_to_deploy = profile_filter.filter_agents(agents_to_deploy)

    # Continue with deployment...
    for agent in agents_to_deploy:
        self.single_agent_deployer.deploy_agent(agent, target_dir)
```

---

## 5. Data Structures Summary

### 5.1 Agent Data Structures

```python
# Unified Agent Metadata (core/unified_agent_registry.py)
@dataclass
class UnifiedAgentMetadata:
    name: str                      # e.g., "engineer"
    agent_type: AgentType          # Enum: ENGINEER, QA, RESEARCH, etc.
    tier: AgentTier                # Enum: SYSTEM, USER, PROJECT
    path: str                      # File path to agent definition
    last_modified: float           # Timestamp
    specializations: List[str]     # e.g., ["coding", "architecture"]
    description: str               # Human-readable description

# Agent Configuration (from JSON templates)
{
    "agent_id": "engineer",
    "version": "2.0.0",
    "metadata": {
        "name": "Software Engineer",
        "description": "...",
        "category": "engineering"
    },
    "capabilities": {
        "model": "claude-sonnet-4-20250514",
        "tools": ["Read", "Write", "Edit", "Bash"],
        "has_project_memory": true
    },
    "skills": [
        "python-skills",
        "typescript-skills"
    ],
    "instructions": "Agent prompt text here..."
}
```

### 5.2 Skill Data Structures

```python
# Skill Object (skills/registry.py)
@dataclass
class Skill:
    name: str                      # e.g., "python-skills"
    path: Path                     # Path to skill directory
    content: str                   # Skill instructions/content
    source: str                    # "bundled"|"remote"|"pm"
    version: str                   # Semantic version
    skill_id: str                  # Unique identifier
    description: str               # Human-readable description
    agent_types: List[str]         # Agents that can use this skill

# Skill Configuration (from configuration.yaml)
{
    "skills": {
        "user_defined": [],        # Manual skill selection
        "agent_referenced": [      # Auto-discovered from agents
            "toolchains-python-frameworks-django",
            "toolchains-typescript-core"
        ]
    }
}
```

### 5.3 Configuration Data Structure

```python
# Configuration.yaml Structure
{
    "agent_deployment": {
        "excluded_agents": [],              # Agents to exclude
        "filter_non_mpm_agents": true,
        "mpm_author_patterns": [...]
    },
    "skills": {
        "user_defined": [],                 # Manual skill override
        "agent_referenced": [...]           # Auto-discovered skills
    },
    # NEW: Profile configuration
    "profiles": {
        "active": "python-fullstack",
        "definitions": {
            "python-fullstack": {
                "agents": {
                    "include": ["engineer", "python-engineer"],
                    "exclude": []
                },
                "skills": {
                    "include_patterns": ["toolchains-python-*"],
                    "exclude_patterns": ["*-java-*"]
                }
            }
        }
    }
}
```

---

## 6. Recommendations

### 6.1 Profile Filtering Architecture

**Recommended Approach:**

1. **Add profile configuration to `configuration.yaml`**
   - Follows existing configuration patterns
   - Supports environment variable override
   - Allows per-project profile customization

2. **Extend deployment services with profile filtering**
   - Agent deployment: Filter in `AgentDeploymentService.deploy_agents()`
   - Skill deployment: Filter in `GitSkillSourceManager.deploy_skills()`
   - Use existing `skill_filter` parameter for skills
   - Add new `profile_filter` parameter for agents

3. **Maintain discovery integrity**
   - Discovery should still find all agents/skills
   - Filtering happens at deployment (what gets activated)
   - `agent-manager list --all` can bypass profile filter

4. **Support dynamic profile switching**
   - Environment variable: `CLAUDE_MPM_PROFILE=typescript-frontend`
   - CLI command: `claude-mpm profile set typescript-frontend`
   - Configuration file: `profiles.active: typescript-frontend`

### 6.2 Implementation Priorities

**Phase 1: Foundation**
1. Add profile configuration schema to `configuration.yaml`
2. Create profile loader in `ConfigLoader`
3. Add profile filtering to agent deployment
4. Add profile filtering to skill deployment

**Phase 2: User Experience**
1. Add CLI commands for profile management
2. Add profile status to startup summary
3. Add `--profile` flag to deployment commands
4. Document profile configuration

**Phase 3: Advanced Features**
1. Profile inheritance (extend base profiles)
2. Profile validation (check agent/skill availability)
3. Profile templates (common configurations)
4. Profile auto-detection (detect stack from project files)

### 6.3 Alternative Approaches (Not Recommended)

**Why not filter at discovery?**
- Breaks introspection (can't see what's available)
- Complicates registry management
- Harder to debug and troubleshoot

**Why not use separate agent directories per profile?**
- More complex directory management
- Harder to switch profiles
- Wastes disk space with duplicates

**Why not use environment variables only?**
- Less user-friendly than configuration file
- No profile inheritance or composition
- Harder to share profiles across team

---

## 7. Key Files Reference

### 7.1 Agent Loading

| File Path | Purpose | Key Functions |
|-----------|---------|---------------|
| `src/claude_mpm/cli/startup.py` | Startup orchestration | `sync_remote_agents_on_startup()`, `show_agent_summary()` |
| `src/claude_mpm/core/agent_registry.py` | Agent registry (compatibility wrapper) | `SimpleAgentRegistry`, `discover_agents()` |
| `src/claude_mpm/agents/agent_loader.py` | Agent loader interface | `AgentLoader`, `get_agent_prompt()` |
| `src/claude_mpm/services/agents/deployment/agent_deployment.py` | Agent deployment service | `AgentDeploymentService.deploy_agents()` |
| `src/claude_mpm/services/agents/git_source_manager.py` | Remote agent sync | `GitSourceManager.sync_all_sources()` |

### 7.2 Skill Loading

| File Path | Purpose | Key Functions |
|-----------|---------|---------------|
| `src/claude_mpm/cli/startup.py` | Skill deployment orchestration | `sync_remote_skills_on_startup()`, `deploy_bundled_skills()` |
| `src/claude_mpm/skills/skill_manager.py` | Skill manager | `SkillManager.get_agent_skills()` |
| `src/claude_mpm/services/skills/git_skill_source_manager.py` | Remote skill sync | `GitSkillSourceManager.deploy_skills()` |
| `src/claude_mpm/services/skills/selective_skill_deployer.py` | Skill filtering | `get_skills_to_deploy()`, `get_required_skills_from_agents()` |

### 7.3 Configuration

| File Path | Purpose | Key Functions |
|-----------|---------|---------------|
| `src/claude_mpm/core/shared/config_loader.py` | Configuration loading | `ConfigLoader.load_config()`, `load_main_config()` |
| `.claude-mpm/configuration.yaml` | Project configuration | Agent/skill filtering settings |

---

## 8. Next Steps

### 8.1 For Profile Implementation

1. **Review existing filtering mechanisms**
   - Study `excluded_agents` implementation in `agent_deployment.py`
   - Study `skill_filter` implementation in `git_skill_source_manager.py`
   - Understand `user_defined` vs `agent_referenced` skill selection

2. **Design profile configuration schema**
   - Define profile structure in YAML
   - Design include/exclude patterns for agents
   - Design include/exclude patterns for skills
   - Plan environment variable override mechanism

3. **Implement profile loading**
   - Extend `ConfigLoader` with profile support
   - Add profile resolution logic (active + override)
   - Add profile validation

4. **Integrate with deployment**
   - Modify `AgentDeploymentService.deploy_agents()`
   - Modify `GitSkillSourceManager.deploy_skills()`
   - Add profile filtering logic
   - Preserve backward compatibility (no profile = deploy all)

### 8.2 Testing Considerations

1. **Verify deployment filtering works**
   - Profile with only Python agents → only Python agents deployed
   - Profile with pattern-based skills → correct skills deployed
   - No profile configured → all agents/skills deployed (backward compat)

2. **Verify discovery remains intact**
   - `agent-manager list` shows all available agents
   - Cache still contains all agents
   - Deployment only affects `.claude/agents/` directory

3. **Verify profile switching**
   - Switch from Python to TypeScript profile
   - Verify old agents removed and new agents deployed
   - Verify skill changes propagate correctly

---

## Appendix A: Startup Call Stack

```
main() [cli/__init__.py]
  ├─ setup_early_environment()
  ├─ run_background_services()
  │   ├─ sync_hooks_on_startup()
  │   ├─ initialize_project_registry()
  │   ├─ check_mcp_auto_configuration()
  │   ├─ verify_mcp_gateway_startup()
  │   ├─ check_for_updates_async()
  │   ├─ sync_remote_agents_on_startup()           ← AGENTS LOADED HERE
  │   │   ├─ sync_agents_on_startup()
  │   │   │   └─ GitSourceManager.sync_all_sources()
  │   │   ├─ AgentDeploymentService.deploy_agents()
  │   │   │   ├─ AgentDiscoveryService.discover_agents()
  │   │   │   ├─ AgentTemplateBuilder.build_yaml()
  │   │   │   └─ AgentFileSystemManager.write_agent_file()
  │   │   └─ _cleanup_orphaned_agents()
  │   ├─ show_agent_summary()
  │   ├─ deploy_bundled_skills()                   ← BUNDLED SKILLS
  │   │   └─ SkillsService.deploy_bundled_skills()
  │   ├─ sync_remote_skills_on_startup()           ← REMOTE SKILLS
  │   │   ├─ GitSkillSourceManager.sync_all_sources()
  │   │   ├─ get_required_skills_from_agents()
  │   │   ├─ save_agent_skills_to_config()
  │   │   ├─ get_skills_to_deploy()                ← SKILL FILTERING
  │   │   └─ GitSkillSourceManager.deploy_skills()
  │   ├─ discover_and_link_runtime_skills()
  │   ├─ show_skill_summary()
  │   ├─ verify_and_show_pm_skills()
  │   └─ deploy_output_style_on_startup()
  └─ [Continue with command execution]
```

---

## Appendix B: Configuration File Example

**Location:** `.claude-mpm/configuration.yaml`

```yaml
# Agent deployment configuration
agent_deployment:
  case_sensitive: false
  exclude_dependencies: false
  excluded_agents: []              # Currently deployed agents to exclude
  filter_non_mpm_agents: true
  mpm_author_patterns:
    - "claude mpm"
    - "claude-mpm"
    - "anthropic"

# Skill deployment configuration
skills:
  user_defined: []                 # Manual skill override (empty = use agent_referenced)
  agent_referenced:                # Auto-discovered from agent templates
    - toolchains-python-frameworks-django
    - toolchains-typescript-core
    - universal-debugging-systematic-debugging
    # ... 100+ skills

# NEW: Profile-based filtering (proposed)
profiles:
  active: "python-fullstack"       # Current active profile

  definitions:
    python-fullstack:
      agents:
        include:
          - engineer
          - python-engineer
          - qa
          - documentation
        exclude: []
      skills:
        include_patterns:
          - "toolchains-python-*"
          - "universal-*"
        exclude_patterns:
          - "*-java-*"
          - "*-golang-*"

    typescript-frontend:
      agents:
        include:
          - engineer
          - typescript-engineer
          - react-engineer
          - nextjs-engineer
          - qa
        exclude: []
      skills:
        include_patterns:
          - "toolchains-typescript-*"
          - "toolchains-javascript-*"
          - "toolchains-nextjs-*"
          - "universal-*"
        exclude_patterns:
          - "*-python-*"
```

---

## Glossary

**Agent Discovery**: Process of finding all available agents from various sources (cache, package, project)

**Agent Deployment**: Process of deploying selected agents to `.claude/agents/` where Claude Code can discover them

**Agent Tier**: Classification of agents (SYSTEM=built-in, USER=user-level, PROJECT=project-specific)

**Skill Registry**: Central registry of all available skills with metadata

**Agent-Skill Mapping**: Configuration defining which skills are available to which agents

**Profile Filtering**: Proposed system to filter agents/skills based on development profile (Python, TypeScript, etc.)

**Configuration.yaml**: Project-level configuration file in `.claude-mpm/` directory

**Git Source Manager**: Service that syncs agents/skills from remote Git repositories

**Unified Agent Registry**: Core registry system that manages agent metadata and discovery

---

**End of Research Document**
