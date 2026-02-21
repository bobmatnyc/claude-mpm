# Auto-Configuration: Main Branch CLI Code Path

**Date**: 2026-02-21
**Branch**: `main`
**Scope**: Complete CLI auto-configuration pipeline analysis

---

## 1. Entry Points

### 1.1 CLI Binary Entry Point

The CLI is registered as a console script in `pyproject.toml:103-104`:

```python
[project.scripts]
claude-mpm = "claude_mpm.cli:main"
```

### 1.2 Command Registration (Parser)

The `auto-configure` subcommand is registered in:

**File**: `src/claude_mpm/cli/parsers/base_parser.py:447-452`
```python
try:
    from .auto_configure_parser import add_auto_configure_subparser
    add_auto_configure_subparser(subparsers)
except ImportError:
    pass
```

**File**: `src/claude_mpm/cli/parsers/auto_configure_parser.py:21-120`

Parser function: `add_auto_configure_subparser(subparsers)`

CLI arguments:
| Argument | Type | Default | Description |
|---|---|---|---|
| `--preview` / `--dry-run` | flag | False | Show what would be configured |
| `--yes` / `-y` | flag | False | Skip confirmation, auto-deploy |
| `--agents-only` | flag | False | Configure agents only |
| `--skills-only` | flag | False | Configure skills only |
| `--min-confidence` | float | 0.5 | Minimum confidence threshold |
| `--project-path` | Path | cwd | Project path to analyze |

Usage examples:
```bash
claude-mpm auto-configure                          # Interactive
claude-mpm auto-configure --preview                # Preview only
claude-mpm auto-configure --yes                    # Auto-approve
claude-mpm auto-configure --min-confidence 0.9     # High confidence
claude-mpm auto-configure --json                   # JSON output
claude-mpm auto-configure --project-path /path     # Custom path
```

### 1.3 Command Executor

**File**: `src/claude_mpm/cli/executor.py:205-213`
```python
# Handle auto-configure command with lazy import
if command == "auto-configure":
    from .commands.auto_configure import AutoConfigureCommand
    cmd = AutoConfigureCommand()
    result = cmd.run(args)
    return result.exit_code if result else 0
```

The command is also listed in the valid commands set at `executor.py:420`:
```python
all_commands = [
    ...
    "auto-configure",
    ...
]
```

---

## 2. Core Logic: The CLI Command

### 2.1 AutoConfigureCommand

**File**: `src/claude_mpm/cli/commands/auto_configure.py:99-1052`

Class: `AutoConfigureCommand(BaseCommand)`

This is the main orchestrator for the CLI auto-config path. It:

1. Lazily initializes service dependencies (DI pattern)
2. Orchestrates both agent AND skill configuration
3. Handles Rich terminal output (with fallback to plain text)
4. Manages user confirmation (y/n/s)
5. Handles archival of unused agents

#### Key Properties (Lazy-Loaded Dependencies)

**`auto_config_manager`** (lines 118-147):
```python
@property
def auto_config_manager(self) -> AutoConfigManagerService:
    if self._auto_config_manager is None:
        toolchain_analyzer = ToolchainAnalyzerService()
        agent_registry = AgentRegistry()
        agent_recommender = AgentRecommenderService()
        agent_deployment = AgentDeploymentService()  # optional

        self._auto_config_manager = AutoConfigManagerService(
            toolchain_analyzer=toolchain_analyzer,
            agent_recommender=agent_recommender,
            agent_registry=agent_registry,
            agent_deployment=agent_deployment,
        )
    return self._auto_config_manager
```

**`skills_deployer`** (lines 149-156):
```python
@property
def skills_deployer(self):
    if self._skills_deployer is None:
        from ...services.skills_deployer import SkillsDeployerService
        self._skills_deployer = SkillsDeployerService()
    return self._skills_deployer
```

#### Key Methods

| Method | Lines | Purpose |
|---|---|---|
| `run(args)` | 176-243 | Entry point - validates, branches to preview/full |
| `_run_preview(...)` | 245-300 | Preview mode: analyze + display, no deploy |
| `_run_full_configuration(...)` | 302-405 | Full mode: analyze + confirm + deploy |
| `_display_preview(...)` | 407-505 | Rich terminal display of preview |
| `_display_preview_plain(...)` | 507-552 | Plain text fallback for preview |
| `_confirm_deployment(...)` | 554-607 | Interactive y/n/s confirmation |
| `_display_result(...)` | 609-694 | Rich display of deployment result |
| `_recommend_skills(agent_preview)` | 875-898 | Map agents → skills via AGENT_SKILL_MAPPING |
| `_deploy_skills(skills)` | 900-915 | Deploy skills via SkillsDeployerService |
| `_review_project_agents(preview)` | 917-958 | Review existing agents for archival |
| `_archive_agents(agents)` | 960-973 | Archive unused agents |
| `_show_restart_notification(...)` | 1016-1052 | Show restart reminder |

---

## 3. Configuration Flow (Data Pipeline)

### 3.1 High-Level Flow

```
User runs: claude-mpm auto-configure [--preview] [--yes] [--min-confidence N]
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  AutoConfigureCommand.run(args)                                  │
│  (src/claude_mpm/cli/commands/auto_configure.py:176)            │
└──────────────┬──────────────────────────────────────────────────┘
               │
    ┌──────────▼──────────────┐
    │  Validate Arguments      │
    │  (project_path, etc.)    │
    └──────────┬──────────────┘
               │
    ┌──────────▼──────────────┐
    │  Determine Mode:         │
    │  --preview → _run_preview│
    │  else → _run_full_config │
    └──────────┬──────────────┘
               │
    ┌──────────▼───────────────────────────────────────────────────┐
    │  STEP 1: Analyze Project Toolchain                           │
    │  AutoConfigManagerService.preview_configuration()             │
    │    └→ ToolchainAnalyzerService.analyze_toolchain(project_path)│
    │       ├→ PythonDetectionStrategy.detect_language()            │
    │       ├→ NodeJSDetectionStrategy.detect_language()            │
    │       ├→ RustDetectionStrategy.detect_language()              │
    │       ├→ GoDetectionStrategy.detect_language()                │
    │       ├→ detect_frameworks() (each strategy)                  │
    │       ├→ _detect_build_tools()                                │
    │       ├→ _detect_package_managers()                           │
    │       ├→ _detect_development_tools()                          │
    │       └→ detect_deployment_target()                           │
    │    Returns: ToolchainAnalysis                                 │
    │                                                               │
    │    └→ AgentRecommenderService.recommend_agents(toolchain)     │
    │       ├→ Load agent_capabilities.yaml                         │
    │       ├→ match_score() per agent (language/framework/deploy)  │
    │       ├→ Filter by min_confidence                             │
    │       ├→ Sort by confidence descending                        │
    │       └→ Returns: List[AgentRecommendation]                   │
    │                                                               │
    │    └→ validate_configuration(recommendations)                 │
    │       ├→ Check agent existence                                │
    │       ├→ Check confidence thresholds                          │
    │       ├→ Check role conflicts                                 │
    │       └→ Returns: ValidationResult                            │
    │                                                               │
    │    Returns: ConfigurationPreview                              │
    └──────────┬───────────────────────────────────────────────────┘
               │
    ┌──────────▼───────────────────────────────────────────────────┐
    │  STEP 2: Review Existing Agents                              │
    │  _review_project_agents(agent_preview)                       │
    │    └→ RemoteAgentDiscoveryService.discover_remote_agents()   │
    │    └→ AgentReviewService.review_project_agents()             │
    │       Categorizes: managed / outdated / custom / unused      │
    └──────────┬───────────────────────────────────────────────────┘
               │
    ┌──────────▼───────────────────────────────────────────────────┐
    │  STEP 3: Recommend Skills                                    │
    │  _recommend_skills(agent_preview)                            │
    │    └→ Import AGENT_SKILL_MAPPING from skills_wizard.py       │
    │    └→ For each recommended agent:                            │
    │       map agent_id → skill list                              │
    │    Returns: List[str] (skill names)                          │
    └──────────┬───────────────────────────────────────────────────┘
               │
    ┌──────────▼──────────────┐
    │  Display Preview         │
    │  (Rich table or JSON)    │
    └──────────┬──────────────┘
               │ (if not --preview)
    ┌──────────▼──────────────┐
    │  User Confirmation       │
    │  "Deploy N agent(s)      │
    │   and M skill(s)?"       │
    │  (y/n/s)                 │
    └──────────┬──────────────┘
               │ (if yes)
    ┌──────────▼───────────────────────────────────────────────────┐
    │  STEP 4: Archive Unused Agents                               │
    │  AgentReviewService.archive_agents()                         │
    │  → Moves to .claude/agents/unused/                           │
    └──────────┬───────────────────────────────────────────────────┘
               │
    ┌──────────▼───────────────────────────────────────────────────┐
    │  STEP 5: Deploy Agents                                       │
    │  AutoConfigManagerService.auto_configure()                   │
    │  (async via asyncio.run())                                   │
    │    └→ _deploy_agents() per recommendation                    │
    │    └→ _rollback_deployment() on failure                      │
    │    └→ _save_configuration() to .claude-mpm/auto-config.yaml  │
    └──────────┬───────────────────────────────────────────────────┘
               │
    ┌──────────▼───────────────────────────────────────────────────┐
    │  STEP 6: Deploy Skills                                       │
    │  SkillsDeployerService.deploy_skills(skill_names)            │
    │    → Downloads from GitHub, deploys to ~/.claude/skills/     │
    └──────────┬───────────────────────────────────────────────────┘
               │
    ┌──────────▼──────────────┐
    │  Display Results         │
    │  + Restart Notification  │
    └─────────────────────────┘
```

### 3.2 Detailed Step Analysis

#### Step 1: Toolchain Analysis (`ToolchainAnalyzerService`)

**File**: `src/claude_mpm/services/project/toolchain_analyzer.py:39-583`

**Design Pattern**: Strategy Pattern with pluggable detection strategies

**Method**: `analyze_toolchain(project_path: Path) -> ToolchainAnalysis`

Registered strategies (line 82-87):
```python
def _register_default_strategies(self):
    self.register_strategy("nodejs", NodeJSDetectionStrategy())
    self.register_strategy("python", PythonDetectionStrategy())
    self.register_strategy("rust", RustDetectionStrategy())
    self.register_strategy("go", GoDetectionStrategy())
```

Detection steps (lines 113-192):
1. `detect_language(project_path)` - Runs all strategies, picks highest confidence
2. `detect_frameworks(project_path)` - Aggregates from all strategies, deduplicates
3. `_detect_build_tools(project_path)` - Checks for webpack, vite, make, gradle, etc.
4. `_detect_package_managers(project_path)` - Checks for npm, yarn, pip, poetry, etc.
5. `_detect_development_tools(project_path)` - Docker, k8s, terraform, git, eslint, etc.
6. `detect_deployment_target(project_path)` - Docker, k8s, Vercel, AWS, Terraform, GCP

Caching: 5-minute TTL per project path, max 100 entries.

#### Step 2: Agent Recommendation (`AgentRecommenderService`)

**File**: `src/claude_mpm/services/agents/recommender.py:31-684`

**Design**: Configuration-driven matching using `agent_capabilities.yaml`

**Method**: `recommend_agents(toolchain: ToolchainAnalysis, constraints: dict) -> List[AgentRecommendation]`

**Scoring Algorithm** (lines 357-446):
```
match_score = (language_score * 0.5) + (framework_score * 0.3) + (deployment_score * 0.2)

# Boosts:
if language_only:  match_score += 0.15
final_score = match_score * (0.5 + 0.5 * confidence_weight)
if framework_match > 0.5: final_score += 0.15
if deployment_match > 0.5: final_score += 0.10
```

**Language alias resolution** (lines 52-62):
```python
LANGUAGE_ALIASES = {
    "node.js": ["javascript", "typescript"],
    "nodejs": ["javascript", "typescript"],
    "cpython": ["python"],
    "jvm": ["java", "kotlin", "scala"],
    ...
}
```

**Default fallback** (lines 250-291): When no agents score above threshold, applies default configuration from YAML with a default confidence of 0.7.

#### Step 3: Skill Recommendation

Two independent mechanisms exist:

**Mechanism A: AGENT_SKILL_MAPPING** (used by CLI auto-configure)

**File**: `src/claude_mpm/cli/interactive/skills_wizard.py:17-74`

Simple dict mapping agent IDs to skill lists:
```python
AGENT_SKILL_MAPPING = {
    "engineer": ["test-driven-development", "systematic-debugging", "code-review", ...],
    "python-engineer": [...] + ["async-testing"],
    "typescript-engineer": [...] + ["async-testing"],
    "react-engineer": [...] + ["performance-profiling"],
    "ops": ["docker-containerization", "database-migration", "security-scanning", ...],
    "qa": ["test-driven-development", "systematic-debugging", "async-testing", ...],
    ...
}
```

Called by `AutoConfigureCommand._recommend_skills()` at line 875-898.

**Mechanism B: SkillRecommendationEngine** (standalone engine, not used by CLI auto-configure)

**File**: `src/claude_mpm/services/skills/skill_recommendation_engine.py:57-386`

- Uses `TechnologyStack` dataclass (from `project_inspector.py`)
- Scores skills by relevance (language * 0.4, framework * 0.5, tools * 0.3, databases * 0.3)
- Loads skills manifest from `~/.claude-mpm/cache/skills/system/manifest.json`
- Has priority patterns: CRITICAL, HIGH, MEDIUM, LOW
- Filters already-deployed skills

**Note**: The CLI auto-configure command uses Mechanism A (simple dict mapping), NOT Mechanism B (the more sophisticated engine).

---

## 4. Key Files Map

### Core Pipeline Files

| File | Role | Key Functions |
|---|---|---|
| `cli/parsers/auto_configure_parser.py` | CLI argument parsing | `add_auto_configure_subparser()` |
| `cli/commands/auto_configure.py` | CLI command orchestrator | `AutoConfigureCommand.run()`, `_run_preview()`, `_run_full_configuration()` |
| `cli/executor.py:205-213` | Command dispatch | Lazy imports `AutoConfigureCommand` |
| `services/agents/auto_config_manager.py` | Facade service | `AutoConfigManagerService.auto_configure()`, `preview_configuration()`, `validate_configuration()` |
| `services/project/toolchain_analyzer.py` | Toolchain analysis | `ToolchainAnalyzerService.analyze_toolchain()` |
| `services/project/detection_strategies.py` | Detection strategies | `PythonDetectionStrategy`, `NodeJSDetectionStrategy`, `RustDetectionStrategy`, `GoDetectionStrategy` |
| `services/agents/recommender.py` | Agent scoring + matching | `AgentRecommenderService.recommend_agents()`, `match_score()` |
| `config/agent_capabilities.yaml` | Agent capabilities config | Agent definitions, scoring weights, default config |
| `services/agents/observers.py` | Progress tracking | `IDeploymentObserver`, `NullObserver` |

### Supporting Files

| File | Role | Key Functions |
|---|---|---|
| `services/core/models/toolchain.py` | Toolchain data models | `ToolchainAnalysis`, `LanguageDetection`, `Framework`, `DeploymentTarget`, etc. |
| `services/core/models/agent_config.py` | Agent data models | `AgentRecommendation`, `ConfigurationPreview`, `ConfigurationResult`, `ValidationResult` |
| `services/agents/agent_recommendation_service.py` | Alternative recommender | `AgentRecommendationService.get_recommended_agents()` |
| `services/agents/toolchain_detector.py` | Legacy/simple detector | `ToolchainDetector.detect_toolchain()`, `recommend_agents()` |
| `cli/interactive/skills_wizard.py` | Agent-skill mapping | `AGENT_SKILL_MAPPING` dict |
| `services/skills_deployer.py` | Skill deployment | `SkillsDeployerService.deploy_skills()` |
| `services/skills/skill_recommendation_engine.py` | Skill scoring engine | `SkillRecommendationEngine.recommend_skills()` |
| `services/skills/project_inspector.py` | Alt tech stack detection | `ProjectInspector`, `TechnologyStack` |
| `services/agents/agent_review_service.py` | Agent review/archival | `AgentReviewService.review_project_agents()`, `archive_agents()` |

---

## 5. Data Structures

### 5.1 ToolchainAnalysis (output of detection)

**File**: `services/core/models/toolchain.py:212-389`

```python
@dataclass
class ToolchainAnalysis:
    project_path: Path
    language_detection: LanguageDetection    # Primary + secondary languages
    frameworks: List[Framework]              # Detected frameworks
    deployment_target: Optional[DeploymentTarget]  # Docker/K8s/Vercel/etc.
    build_tools: List[ToolchainComponent]    # webpack, vite, make, etc.
    package_managers: List[ToolchainComponent]  # npm, pip, poetry, etc.
    development_tools: List[ToolchainComponent]  # git, pre-commit, eslint, etc.
    overall_confidence: ConfidenceLevel      # HIGH/MEDIUM/LOW/VERY_LOW
    analysis_timestamp: Optional[float]
    metadata: Dict[str, Any]
```

Key properties:
- `.primary_language` → str (e.g., "Python")
- `.all_languages` → List[str] (e.g., ["Python", "TypeScript"])
- `.components` → List[ComponentView] (unified flat list for display)
- `.web_frameworks` → List[Framework]
- `.requires_devops_agent` → bool

### 5.2 LanguageDetection

**File**: `services/core/models/toolchain.py:86-134`

```python
@dataclass(frozen=True)
class LanguageDetection:
    primary_language: str                     # "Python", "Node.js", "Rust", "Go"
    primary_version: Optional[str]            # "3.12", "20.0"
    primary_confidence: ConfidenceLevel       # HIGH/MEDIUM/LOW/VERY_LOW
    secondary_languages: List[ToolchainComponent]
    language_percentages: Dict[str, float]    # {"Python": 85.0, "JavaScript": 15.0}
```

### 5.3 AgentRecommendation

**File**: `services/core/models/agent_config.py:94-176`

```python
@dataclass
class AgentRecommendation:
    agent_id: str                             # "python_engineer"
    agent_name: str                           # "Python Engineer"
    confidence_score: float                   # 0.0-1.0
    match_reasons: List[str]                  # ["Primary language match: Python"]
    concerns: List[str]                       # ["Moderate confidence..."]
    capabilities: Optional[AgentCapabilities]
    deployment_priority: int                  # 1=highest, 4=lowest
    configuration_hints: Dict[str, Any]
    metadata: Dict[str, Any]
```

Properties: `.confidence`, `.reasoning`, `.is_high_confidence`, `.has_concerns`

### 5.4 ConfigurationPreview

**File**: `services/core/models/agent_config.py:348-402`

```python
@dataclass
class ConfigurationPreview:
    recommendations: List[AgentRecommendation]
    validation_result: Optional[ValidationResult]
    detected_toolchain: Optional[ToolchainAnalysis]
    estimated_deployment_time: float
    would_deploy: List[str]
    would_skip: List[str]
    requires_confirmation: bool
    metadata: Dict[str, Any]
```

### 5.5 ConfigurationResult

**File**: `services/core/models/agent_config.py:179-239`

```python
@dataclass
class ConfigurationResult:
    status: OperationResult                   # SUCCESS/WARNING/FAILED/ERROR/CANCELLED
    deployed_agents: List[str]
    failed_agents: List[str]
    validation_warnings: List[str]
    validation_errors: List[str]
    recommendations: List[AgentRecommendation]
    message: str
    metadata: Dict[str, Any]
```

### 5.6 TechnologyStack (Skills Engine)

**File**: `services/skills/project_inspector.py:25-41`

```python
@dataclass
class TechnologyStack:
    languages: Dict[str, float]   # {"python": 0.95, "javascript": 0.3}
    frameworks: Dict[str, float]  # {"fastapi": 0.9, "pytest": 0.85}
    tools: Dict[str, float]       # {"docker": 0.9, "make": 0.8}
    databases: Dict[str, float]   # {"postgresql": 0.7}
```

### 5.7 SkillRecommendation (Skills Engine)

**File**: `services/skills/skill_recommendation_engine.py:34-54`

```python
@dataclass
class SkillRecommendation:
    skill_name: str
    skill_id: str
    priority: SkillPriority         # CRITICAL/HIGH/MEDIUM/LOW
    relevance_score: float
    category: str
    toolchain: Optional[str]
    framework: Optional[str]
    tags: List[str]
    justification: str
    matched_technologies: List[str]
```

---

## 6. User Interaction

### 6.1 Preview Mode (`--preview`)

1. Shows Rich table of detected toolchain components with confidence bars
2. Shows recommended agents with confidence percentages
3. Shows validation issues (warnings/errors)
4. Shows recommended skills
5. No deployment occurs

### 6.2 Full Configuration (interactive)

1. Shows preview (same as above)
2. Prompts: `"Deploy N agent(s) and M skill(s)?"`
3. Options: `y` (proceed), `n` (cancel), `s` (select - TODO: not implemented)
4. On confirmation:
   - Archives unused agents to `.claude/agents/unused/`
   - Deploys agents with Rich progress bars
   - Deploys skills via GitHub download
   - Shows result summary
   - Shows restart notification

### 6.3 Non-Interactive Mode (`--yes`)

- Skips confirmation prompt
- Auto-deploys all recommendations

### 6.4 JSON Output (`--json`)

- Outputs structured JSON for scripting
- Preview JSON includes: detected_toolchain, recommendations, validation
- Result JSON includes: status, deployed_agents, failed_agents, errors

---

## 7. Parallel/Duplicate Systems

### 7.1 Two Toolchain Detectors

| System | File | Used By |
|---|---|---|
| `ToolchainDetector` (legacy) | `services/agents/toolchain_detector.py` | Not used by auto-configure directly |
| `ToolchainAnalyzerService` (modern) | `services/project/toolchain_analyzer.py` | Used by auto-configure pipeline |

The legacy `ToolchainDetector` is simpler (returns dict), while the modern `ToolchainAnalyzerService` uses Strategy pattern (returns `ToolchainAnalysis` dataclass).

### 7.2 Two Agent Recommenders

| System | File | Used By |
|---|---|---|
| `AgentRecommendationService` | `services/agents/agent_recommendation_service.py` | Interactive configure wizard |
| `AgentRecommenderService` | `services/agents/recommender.py` | Auto-configure pipeline |

Both exist but serve different contexts. The auto-configure pipeline uses `AgentRecommenderService` (YAML-config driven with scoring algorithm).

### 7.3 Two Skill Recommendation Systems

| System | File | Used By |
|---|---|---|
| `AGENT_SKILL_MAPPING` dict | `cli/interactive/skills_wizard.py` | CLI auto-configure (simple mapping) |
| `SkillRecommendationEngine` | `services/skills/skill_recommendation_engine.py` | Not used by auto-configure |

The CLI auto-configure uses the simple dict mapping. The sophisticated `SkillRecommendationEngine` with scoring exists but is NOT wired into the auto-configure pipeline.

### 7.4 Two Tech Stack Detectors

| System | File | Used By |
|---|---|---|
| `ToolchainAnalyzerService` | `services/project/toolchain_analyzer.py` | Auto-configure pipeline |
| `ProjectInspector` | `services/skills/project_inspector.py` | SkillRecommendationEngine |

Different data models: `ToolchainAnalysis` vs `TechnologyStack`.

---

## 8. Configuration Files Read/Written

### Read
| File | Purpose |
|---|---|
| `config/agent_capabilities.yaml` | Agent definitions, scoring weights, capabilities |
| `~/.claude-mpm/cache/agents/` | Managed agent cache |
| `~/.claude-mpm/cache/skills/system/manifest.json` | Skills manifest |
| `.claude/agents/*.md` | Existing project agents |
| Project dependency files | `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, etc. |

### Written
| File | Purpose |
|---|---|
| `.claude-mpm/auto-config.yaml` | Saved auto-config metadata (toolchain snapshot, deployed agents, overrides) |
| `.claude/agents/` | Deployed agent markdown files |
| `.claude/agents/unused/` | Archived unused agents |
| `~/.claude/skills/` | Deployed skill files |

---

## 9. Key Design Patterns

1. **Facade Pattern**: `AutoConfigManagerService` orchestrates toolchain_analyzer + recommender + registry + deployment
2. **Strategy Pattern**: `ToolchainAnalyzerService` with pluggable `IToolchainDetectionStrategy` implementations
3. **Observer Pattern**: `IDeploymentObserver` → `NullObserver` / `RichProgressObserver` for progress tracking
4. **Lazy Loading**: All dependencies lazy-loaded via `@property` in `AutoConfigureCommand`
5. **Command Pattern**: `AutoConfigureCommand(BaseCommand)` with `run(args)` → `CommandResult`
6. **Configuration-Driven**: Agent capabilities and scoring defined in YAML, not code

---

## 10. Scoring Weight Configuration

From `agent_capabilities.yaml`:

```yaml
recommendation_rules:
  scoring_weights:
    language_match: 0.5      # 50% weight for language
    framework_match: 0.3     # 30% weight for framework
    deployment_match: 0.2    # 20% weight for deployment
  framework_priority_boost: 0.15
  deployment_match_boost: 0.1
  min_confidence_threshold: 0.5
```

Per-agent `confidence_weight` values in YAML (e.g., python_engineer: 0.9, typescript_engineer: 0.85).

---

## 11. Summary of Key Findings

### What Works Well
- Clean separation of concerns with well-defined service interfaces
- Comprehensive data models with validation
- Strategy pattern enables easy language extension
- Both preview and full deploy modes
- Agent review/archival system protects custom agents
- Rich terminal UI with plain-text fallback

### Notable Gaps/TODOs
- `_deploy_single_agent()` is a stub (`asyncio.sleep(0.1)`) - actual deployment delegates elsewhere
- `_rollback_deployment()` is a stub (just logs)
- Interactive selection (`s` option) is not implemented
- `SkillRecommendationEngine` (sophisticated) is NOT used by auto-configure; instead uses simple dict mapping
- Two parallel tech stack detection systems exist (`ToolchainAnalyzerService` vs `ProjectInspector`)
- Two parallel recommender services exist
- No Java, Ruby, PHP, C#, Swift, Kotlin detection strategies (only Python, Node.js, Rust, Go)
