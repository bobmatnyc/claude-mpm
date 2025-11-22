# Skills Configuration Integration Analysis

**Research Date:** 2025-11-22
**Purpose:** Analyze integration of skills setup into claude-mpm configurator with auto-discovery
**Status:** Complete

---

## Executive Summary

The claude-mpm configurator (`claude-mpm configure`) currently has a basic skills menu (option 2) that provides limited functionality. This analysis provides a comprehensive plan to enhance skills configuration with:

1. **Auto-discovery** based on detected toolchain (Python, TypeScript, Rust, Go, etc.)
2. **Collection management** for multiple skill repositories
3. **Interactive deployment** with progress feedback
4. **Intelligent recommendations** based on project analysis

**Key Finding:** All necessary infrastructure exists. Integration requires connecting:
- `ToolchainAnalyzerService` (toolchain detection)
- `SkillsDeployerService` (collection management & deployment)
- `SkillsConfig` (configuration persistence)
- `ConfigureCommand` (TUI menu integration)

---

## 1. Current Configurator Implementation

### File Locations

**Main Command:**
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py` (826 lines)

**Supporting Modules:**
- `configure_navigation.py` - Navigation, header, main menu (168 lines)
- `configure_agent_display.py` - Agent table rendering
- `configure_behavior_manager.py` - Behavior file management
- `configure_hook_manager.py` - Claude Code hooks
- `configure_models.py` - Data models
- `configure_persistence.py` - Import/export
- `configure_startup_manager.py` - Startup configuration
- `configure_template_editor.py` - Agent template editing
- `configure_validators.py` - Input validation

**Skills Integration:**
- `skills_wizard.py` - Interactive skills selection wizard (492 lines)

### Current Main Menu Structure

```
Main Menu:
[1] Agent Management         - Enable/disable agents and customize settings
[2] Skills Management        - Configure skills for agents ← CURRENT (Limited)
[3] Template Editing         - Edit agent JSON templates
[4] Behavior Files          - Manage identity and workflow configurations
[5] Startup Configuration   - Configure MCP services and agents to start
[6] Switch Scope            - Current: project/user
[7] Version Info            - Display MPM and Claude versions
[l] Save & Launch           - Save all changes and start Claude MPM
[q] Quit                    - Exit without launching
```

**Current Skills Management (Option 2):**

Location: `configure.py` lines 478-623 (`_manage_skills()` method)

```
Skills Management Options:
[1] View Available Skills         - List bundled skills only
[2] Configure Skills for Agents   - SkillsWizard interactive mapping
[3] View Current Skill Mappings   - Show agent→skills relationships
[4] Auto-Link Skills to Agents    - Auto-link based on agent type
[b] Back to Main Menu
```

**Limitations:**
- ❌ No collection management (add/remove repositories)
- ❌ No deployment capabilities (download from GitHub)
- ❌ No toolchain auto-discovery
- ❌ No progress feedback during operations
- ❌ Only shows bundled skills (no external collections)
- ❌ No update functionality for collections

---

## 2. Existing Skills Infrastructure

### SkillsDeployerService

**Location:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/skills_deployer.py` (956 lines)

**Key Features:**
- ✅ Multi-collection support via git clone/pull
- ✅ GitHub repository download and update
- ✅ Manifest parsing (supports legacy and new structures)
- ✅ Toolchain filtering
- ✅ Category filtering
- ✅ Deployment to `~/.claude/skills/`
- ✅ Claude Code restart detection
- ✅ Security validation (path traversal prevention)

**API Methods:**

```python
# Collection Management
list_collections() -> Dict  # List all configured collections
add_collection(name, url, priority) -> Dict
remove_collection(name) -> Dict
enable_collection(name) -> Dict
disable_collection(name) -> Dict
set_default_collection(name) -> Dict

# Deployment Operations
deploy_skills(collection, toolchain, categories, force) -> Dict
list_available_skills(collection) -> Dict
check_deployed_skills() -> Dict
remove_skills(skill_names) -> Dict
```

**Deployment Result Structure:**
```python
{
    "deployed_count": 5,
    "skipped_count": 2,
    "errors": [],
    "deployed_skills": ["test-driven-development", "systematic-debugging", ...],
    "restart_required": True,
    "restart_instructions": "⚠️ Claude Code is currently running...",
    "collection": "claude-mpm"
}
```

### SkillsConfig

**Location:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/skills_config.py` (548 lines)

**Purpose:** Manage collection configurations in `~/.claude-mpm/config.json`

**Configuration Structure:**
```json
{
    "skills": {
        "collections": {
            "claude-mpm": {
                "url": "https://github.com/bobmatnyc/claude-mpm-skills",
                "enabled": true,
                "priority": 1,
                "last_update": "2025-11-21T15:30:00Z"
            },
            "obra-superpowers": {
                "url": "https://github.com/obra/superpowers",
                "enabled": true,
                "priority": 2,
                "last_update": null
            }
        },
        "default_collection": "claude-mpm"
    }
}
```

**API Methods:**
```python
get_collections() -> Dict
get_enabled_collections() -> Dict
get_collections_by_priority(enabled_only=True) -> List[Tuple]
get_collection(name) -> Optional[Dict]
add_collection(name, url, priority, enabled) -> Dict
remove_collection(name) -> Dict
update_collection(name, updates) -> Dict
enable_collection(name) -> Dict
disable_collection(name) -> Dict
get_default_collection() -> str
set_default_collection(name) -> Dict
update_collection_timestamp(name) -> Dict
validate_collection_config(config) -> List[str]
```

### ToolchainAnalyzerService

**Location:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/project/toolchain_analyzer.py`

**Purpose:** Detect project toolchain for intelligent agent recommendations

**Detection Strategies:**
- `NodeJSDetectionStrategy` - package.json, node_modules, tsconfig.json
- `PythonDetectionStrategy` - requirements.txt, setup.py, pyproject.toml, Poetry, pipenv
- `RustDetectionStrategy` - Cargo.toml, Cargo.lock
- `GoDetectionStrategy` - go.mod, go.sum

**API Methods:**
```python
analyze(project_path: Path) -> ToolchainAnalysis
detect_toolchains(project_path: Path) -> List[ToolchainComponent]
get_deployment_targets(analysis: ToolchainAnalysis) -> List[DeploymentTarget]
```

**Output Structure:**
```python
ToolchainAnalysis(
    languages=[LanguageDetection(name="python", version="3.11", confidence=HIGH)],
    frameworks=[Framework(name="fastapi", version="0.104.1")],
    deployment_targets=[DeploymentTarget.DOCKER, DeploymentTarget.KUBERNETES],
    confidence=HIGH
)
```

---

## 3. Proposed Skills Configuration Menu

### Enhanced Menu Structure

```
Main Menu:
[1] Agent Management
[2] Skills Configuration       ← ENHANCED
[3] Template Editing
[4] Behavior Files
[5] Startup Configuration
[6] Switch Scope
[7] Version Info
[l] Save & Launch
[q] Quit

Skills Configuration Submenu:
┌─────────────────────────────────────────────────────────────────┐
│ 📦 Skills Configuration                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Collection Management:                                          │
│   [1] List Available Collections                               │
│   [2] Add New Collection (GitHub URL)                          │
│   [3] Update All Collections (git pull)                        │
│   [4] Remove Collection                                         │
│   [5] Set Default Collection                                    │
│                                                                 │
│ Deployment:                                                     │
│   [6] Auto-Discover & Deploy (Recommended) ⭐                  │
│   [7] Deploy from Collection                                    │
│   [8] Deploy Specific Skills                                    │
│   [9] View Deployed Skills                                      │
│   [10] Remove Deployed Skills                                   │
│                                                                 │
│ Agent Mapping:                                                  │
│   [11] View Skill Mappings (Agent → Skills)                    │
│   [12] Configure Skills for Agents (SkillsWizard)              │
│   [13] Auto-Link Skills to Agents                              │
│                                                                 │
│ [b] Back to Main Menu                                           │
└─────────────────────────────────────────────────────────────────┘
```

### Auto-Discovery Flow (Option 6)

**User Experience:**

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔍 Auto-Discovery & Deployment                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Step 1: Analyzing project toolchain...                         │
│   ✓ Detected: Python 3.11 (FastAPI, pytest)                   │
│   ✓ Detected: TypeScript (React, Next.js)                     │
│   ✓ Detected: Docker deployment target                         │
│                                                                 │
│ Step 2: Recommending skills...                                 │
│   📦 Collection: claude-mpm (priority 1)                       │
│      • test-driven-development                                  │
│      • systematic-debugging                                     │
│      • code-review                                              │
│      • async-testing (Python-specific)                         │
│                                                                 │
│   📦 Collection: obra-superpowers (priority 2)                 │
│      • using-git-worktrees                                      │
│      • finishing-a-development-branch                           │
│                                                                 │
│ Step 3: Deploy recommendations?                                │
│   [y] Yes, deploy all (7 skills)                              │
│   [c] Customize selection                                       │
│   [n] Cancel                                                    │
│                                                                 │
│ → y                                                             │
│                                                                 │
│ Step 4: Deploying skills...                                    │
│   ⏳ Updating collection 'claude-mpm'...                       │
│   ✓ Collection updated (git pull)                              │
│   ⏳ Deploying 5 skills from claude-mpm...                     │
│   ✓ test-driven-development deployed                           │
│   ✓ systematic-debugging deployed                              │
│   ✓ code-review deployed                                        │
│   ✓ async-testing deployed                                      │
│   ⚠ docker-containerization skipped (already deployed)        │
│                                                                 │
│   ⏳ Updating collection 'obra-superpowers'...                 │
│   ✓ Collection updated (git pull)                              │
│   ⏳ Deploying 2 skills from obra-superpowers...               │
│   ✓ using-git-worktrees deployed                               │
│   ✓ finishing-a-development-branch deployed                    │
│                                                                 │
│ ✅ Deployment Complete!                                         │
│    • Deployed: 6 skills                                         │
│    • Skipped: 1 skill (already deployed)                       │
│    • Errors: 0                                                  │
│                                                                 │
│ ⚠️  Claude Code Restart Required                               │
│    Skills are only loaded at STARTUP.                          │
│    Please restart Claude Code for new skills to be available.  │
│                                                                 │
│ Press Enter to continue...                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Auto-Discovery Algorithm

### Detection → Recommendation Mapping

**Data Structure:**

```python
TOOLCHAIN_SKILL_MAPPING = {
    # Universal skills (all projects)
    "universal": [
        "systematic-debugging",
        "code-review",
        "test-driven-development",
    ],

    # Language-specific
    "python": [
        "async-testing",
        "pytest-best-practices",
        "python-type-hints",
    ],

    "typescript": [
        "async-testing",
        "react-performance",
        "nextjs-routing",
    ],

    "rust": [
        "cargo-best-practices",
        "async-rust",
        "error-handling-patterns",
    ],

    "go": [
        "goroutine-patterns",
        "go-testing",
        "error-wrapping",
    ],

    # Framework-specific
    "fastapi": [
        "api-testing",
        "openapi-documentation",
    ],

    "react": [
        "component-testing",
        "react-hooks-patterns",
    ],

    "nextjs": [
        "server-components",
        "app-router-patterns",
    ],

    # Deployment targets
    "docker": [
        "docker-containerization",
        "multi-stage-builds",
    ],

    "kubernetes": [
        "k8s-deployment",
        "helm-charts",
    ],
}
```

**Algorithm:**

```python
def auto_discover_skills(project_path: Path) -> List[SkillRecommendation]:
    """Auto-discover recommended skills based on project toolchain.

    Returns:
        List of recommended skills with metadata and collection info
    """
    # Step 1: Analyze project toolchain
    analyzer = ToolchainAnalyzerService()
    analysis = analyzer.analyze(project_path)

    # Step 2: Build recommendation set
    recommendations = []

    # Add universal skills
    recommendations.extend(_get_universal_skills())

    # Add language-specific skills
    for lang_detection in analysis.languages:
        lang_name = lang_detection.name.lower()
        if lang_name in TOOLCHAIN_SKILL_MAPPING:
            recommendations.extend(
                _get_skills_for_toolchain(lang_name, lang_detection.confidence)
            )

    # Add framework-specific skills
    for framework in analysis.frameworks:
        fw_name = framework.name.lower()
        if fw_name in TOOLCHAIN_SKILL_MAPPING:
            recommendations.extend(
                _get_skills_for_toolchain(fw_name, ConfidenceLevel.HIGH)
            )

    # Add deployment target skills
    for target in analysis.deployment_targets:
        target_name = target.value.lower()
        if target_name in TOOLCHAIN_SKILL_MAPPING:
            recommendations.extend(
                _get_skills_for_toolchain(target_name, ConfidenceLevel.MEDIUM)
            )

    # Step 3: Resolve skills across collections (priority-based)
    deployer = SkillsDeployerService()
    resolved = _resolve_skills_from_collections(
        recommendations,
        deployer.list_collections()
    )

    # Step 4: Remove duplicates and rank by confidence
    final_recommendations = _deduplicate_and_rank(resolved)

    return final_recommendations


def _resolve_skills_from_collections(
    skill_names: List[str],
    collections_data: Dict
) -> List[SkillRecommendation]:
    """Find skills in collections based on priority.

    Priority-based resolution:
    1. Check each collection in priority order (lower = higher priority)
    2. First collection with the skill wins
    3. Track which collection provides which skill

    Args:
        skill_names: List of desired skill names
        collections_data: Dict from list_collections()

    Returns:
        List of SkillRecommendation with collection metadata
    """
    deployer = SkillsDeployerService()
    collections_by_priority = collections_data['collections']

    # Sort by priority
    sorted_collections = sorted(
        collections_by_priority.items(),
        key=lambda x: x[1].get('priority', 999)
    )

    recommendations = []
    found_skills = set()

    # For each skill, find in highest priority collection
    for skill_name in skill_names:
        if skill_name in found_skills:
            continue

        for coll_name, coll_config in sorted_collections:
            if not coll_config.get('enabled', True):
                continue

            # Check if skill exists in this collection
            available = deployer.list_available_skills(coll_name)
            skill_exists = any(
                s['name'] == skill_name
                for s in available.get('skills', [])
            )

            if skill_exists:
                recommendations.append(
                    SkillRecommendation(
                        name=skill_name,
                        collection=coll_name,
                        collection_url=coll_config['url'],
                        priority=coll_config['priority'],
                        confidence=ConfidenceLevel.HIGH
                    )
                )
                found_skills.add(skill_name)
                break  # Found in highest priority collection

    return recommendations
```

---

## 5. Implementation Requirements

### New Files to Create

**1. `configure_skills_manager.py`** (new module)

```python
"""Skills management for configure command.

WHY: Separate skills configuration logic from main configure command.
Handles collection management, deployment, and auto-discovery.

DESIGN DECISIONS:
- Uses SkillsDeployerService for all deployment operations
- Integrates ToolchainAnalyzerService for auto-discovery
- Provides Rich-based TUI with progress feedback
- Handles errors gracefully with actionable messages
"""

class SkillsManager:
    """Manage skills configuration in TUI."""

    def __init__(self, console: Console, project_dir: Path):
        self.console = console
        self.project_dir = project_dir
        self.deployer = SkillsDeployerService()
        self.analyzer = ToolchainAnalyzerService()

    def manage_skills(self) -> None:
        """Main skills management interface."""
        # Display skills submenu loop

    def auto_discover_and_deploy(self) -> None:
        """Auto-discover toolchain and deploy recommended skills."""
        # Step 1: Analyze toolchain
        # Step 2: Generate recommendations
        # Step 3: Display preview
        # Step 4: Confirm deployment
        # Step 5: Deploy with progress
        # Step 6: Show results and restart warning

    def list_collections(self) -> None:
        """Display all configured collections."""

    def add_collection(self) -> None:
        """Add new GitHub collection."""

    def update_collections(self) -> None:
        """Update all collections (git pull)."""

    def remove_collection(self) -> None:
        """Remove a collection."""

    def deploy_from_collection(self) -> None:
        """Deploy skills from specific collection."""

    def view_deployed_skills(self) -> None:
        """Show currently deployed skills."""

    def remove_deployed_skills(self) -> None:
        """Remove deployed skills."""
```

### Modified Files

**1. `configure.py`**

```python
# Import new manager
from .configure_skills_manager import SkillsManager

class ConfigureCommand(BaseCommand):
    def __init__(self):
        # ... existing code ...
        self._skills_manager = None

    @property
    def skills_manager(self) -> SkillsManager:
        """Lazy-initialize skills manager."""
        if self._skills_manager is None:
            self._skills_manager = SkillsManager(
                self.console,
                self.project_dir
            )
        return self._skills_manager

    def _manage_skills(self) -> None:
        """Skills management interface - ENHANCED."""
        self.skills_manager.manage_skills()
```

**2. `configure_navigation.py`**

```python
# Update menu text for option 2
def show_main_menu(self) -> str:
    menu_items = [
        ("1", "Agent Management", "Enable/disable agents and customize settings"),
        ("2", "Skills Configuration", "Manage collections, deploy skills, auto-discover"),  # ← UPDATED
        ("3", "Template Editing", "Edit agent JSON templates"),
        # ... rest unchanged ...
    ]
```

---

## 6. User Experience Mockups

### Collection Management

```
┌─────────────────────────────────────────────────────────────────┐
│ 📦 Available Skill Collections                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ID  Name                 Priority  Enabled  Last Update         │
│ ──  ───────────────────  ────────  ───────  ─────────────────  │
│ ⭐  claude-mpm           1         ✓        2025-11-22 15:30   │
│     obra-superpowers     2         ✓        2025-11-20 10:15   │
│     custom-skills        3         ✗        Never              │
│                                                                 │
│ Legend:                                                         │
│   ⭐ = Default collection                                       │
│   ✓ = Enabled                                                  │
│   ✗ = Disabled                                                 │
│                                                                 │
│ Options:                                                        │
│   [a] Add new collection                                        │
│   [u] Update all (git pull)                                     │
│   [e] Enable/disable collection                                 │
│   [d] Set default collection                                    │
│   [r] Remove collection                                         │
│   [b] Back                                                      │
└─────────────────────────────────────────────────────────────────┘
```

### Deployment Progress

```
┌─────────────────────────────────────────────────────────────────┐
│ 🚀 Deploying Skills                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Collection: claude-mpm                                          │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% (5/5)    │
│ ✓ test-driven-development                                      │
│ ✓ systematic-debugging                                          │
│ ✓ code-review                                                   │
│ ✓ async-testing                                                 │
│ ⚠ docker-containerization (skipped - already deployed)        │
│                                                                 │
│ Collection: obra-superpowers                                    │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% (2/2)    │
│ ✓ using-git-worktrees                                           │
│ ✓ finishing-a-development-branch                                │
│                                                                 │
│ Summary:                                                        │
│   ✓ Deployed: 6 skills                                         │
│   ⚠ Skipped: 1 skill                                           │
│   ✗ Errors: 0                                                  │
│                                                                 │
│ Next Steps:                                                     │
│   1. Restart Claude Code to load new skills                    │
│   2. Configure skill mappings for agents (option 12)           │
│                                                                 │
│ Press Enter to continue...                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Error Handling Strategies

### Network Errors

```python
try:
    deployer.deploy_skills(collection="claude-mpm")
except Exception as e:
    self.console.print(Panel(
        f"[red]✗ Failed to deploy skills[/red]\n\n"
        f"Error: {e}\n\n"
        f"Troubleshooting:\n"
        f"  • Check internet connection\n"
        f"  • Verify GitHub repository is accessible\n"
        f"  • Check if git is installed: git --version\n"
        f"  • Try updating collection manually:\n"
        f"    cd ~/.claude/skills/claude-mpm && git pull",
        title="Deployment Error",
        border_style="red"
    ))
```

### Git Errors

```python
try:
    deployer.deploy_skills(collection="obra-superpowers")
except subprocess.CalledProcessError as e:
    self.console.print(Panel(
        f"[red]✗ Git operation failed[/red]\n\n"
        f"Command: {e.cmd}\n"
        f"Exit code: {e.returncode}\n"
        f"Error: {e.stderr}\n\n"
        f"Solutions:\n"
        f"  • Remove collection and re-add:\n"
        f"    rm -rf ~/.claude/skills/obra-superpowers\n"
        f"    claude-mpm skills collection add obra-superpowers <URL>\n"
        f"  • Check git configuration:\n"
        f"    git config --list",
        title="Git Error",
        border_style="red"
    ))
```

### Collection Not Found

```python
try:
    deployer.deploy_skills(collection="nonexistent")
except ValueError as e:
    self.console.print(Panel(
        f"[yellow]⚠ Collection not found[/yellow]\n\n"
        f"Error: {e}\n\n"
        f"Available collections:\n"
        + "\n".join(f"  • {name}" for name in deployer.list_collections()["collections"]) +
        f"\n\nTo add a new collection:\n"
        f"  Select option [1] → Add New Collection",
        title="Collection Error",
        border_style="yellow"
    ))
```

---

## 8. Code Examples

### Integration with Configurator

```python
# In configure.py - _manage_skills() method

def _manage_skills(self) -> None:
    """Skills management interface - ENHANCED."""
    from ...services.skills_deployer import SkillsDeployerService
    from ...services.project.toolchain_analyzer import ToolchainAnalyzerService

    deployer = SkillsDeployerService()
    analyzer = ToolchainAnalyzerService()

    while True:
        self.console.clear()
        self._display_header()

        self.console.print("\n[bold]📦 Skills Configuration[/bold]\n")

        # Display collections summary
        collections = deployer.list_collections()
        self.console.print(f"Configured collections: {collections['total_count']}")
        self.console.print(f"Enabled collections: {collections['enabled_count']}")

        deployed = deployer.check_deployed_skills()
        self.console.print(f"Deployed skills: {deployed['deployed_count']}\n")

        # Menu
        self.console.print("[bold]Collection Management:[/bold]")
        self.console.print("  [1] List Available Collections")
        self.console.print("  [2] Add New Collection")
        self.console.print("  [3] Update All Collections")
        self.console.print("  [4] Remove Collection")
        self.console.print("  [5] Set Default Collection\n")

        self.console.print("[bold]Deployment:[/bold]")
        self.console.print("  [6] Auto-Discover & Deploy ⭐")
        self.console.print("  [7] Deploy from Collection")
        self.console.print("  [8] Deploy Specific Skills")
        self.console.print("  [9] View Deployed Skills")
        self.console.print("  [10] Remove Deployed Skills\n")

        self.console.print("[bold]Agent Mapping:[/bold]")
        self.console.print("  [11] View Skill Mappings")
        self.console.print("  [12] Configure Skills for Agents")
        self.console.print("  [13] Auto-Link Skills to Agents\n")

        self.console.print("  [b] Back to Main Menu\n")

        choice = Prompt.ask("[bold blue]Select an option[/bold blue]", default="b")

        if choice == "b":
            break
        elif choice == "1":
            self._skills_list_collections(deployer)
        elif choice == "2":
            self._skills_add_collection(deployer)
        elif choice == "6":
            self._skills_auto_discover(deployer, analyzer)
        # ... handle other options ...
```

### Auto-Discovery Implementation

```python
def _skills_auto_discover(
    self,
    deployer: SkillsDeployerService,
    analyzer: ToolchainAnalyzerService
) -> None:
    """Auto-discover and deploy recommended skills."""

    self.console.clear()
    self._display_header()

    self.console.print("\n[bold]🔍 Auto-Discovery & Deployment[/bold]\n")

    # Step 1: Analyze toolchain
    self.console.print("Step 1: Analyzing project toolchain...")

    with self.console.status("[cyan]Analyzing...", spinner="dots"):
        analysis = analyzer.analyze(self.project_dir)

    # Display detection results
    for lang in analysis.languages:
        self.console.print(f"  ✓ Detected: {lang.name} {lang.version or ''} "
                          f"(confidence: {lang.confidence.value})")

    for framework in analysis.frameworks:
        self.console.print(f"  ✓ Framework: {framework.name} {framework.version or ''}")

    for target in analysis.deployment_targets:
        self.console.print(f"  ✓ Deployment: {target.value}")

    self.console.print()

    # Step 2: Generate recommendations
    self.console.print("Step 2: Generating skill recommendations...")
    recommendations = self._generate_skill_recommendations(analysis, deployer)

    if not recommendations:
        self.console.print("[yellow]No skill recommendations found.[/yellow]")
        Prompt.ask("\nPress Enter to continue")
        return

    # Step 3: Display recommendations grouped by collection
    self.console.print()
    collections_dict = {}
    for rec in recommendations:
        if rec.collection not in collections_dict:
            collections_dict[rec.collection] = []
        collections_dict[rec.collection].append(rec)

    for coll_name, skills in collections_dict.items():
        coll_data = deployer.skills_config.get_collection(coll_name)
        priority = coll_data.get('priority', 99) if coll_data else 99

        self.console.print(f"📦 Collection: {coll_name} (priority {priority})")
        for skill in skills:
            self.console.print(f"   • {skill.name}")
        self.console.print()

    # Step 4: Confirm deployment
    total_skills = len(recommendations)
    confirm = Prompt.ask(
        f"\nDeploy {total_skills} recommended skills?",
        choices=["y", "c", "n"],
        default="y"
    )

    if confirm == "n":
        self.console.print("[yellow]Deployment cancelled.[/yellow]")
        Prompt.ask("\nPress Enter to continue")
        return

    if confirm == "c":
        # Let user customize selection
        recommendations = self._customize_skill_selection(recommendations)
        if not recommendations:
            self.console.print("[yellow]No skills selected.[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

    # Step 5: Deploy skills
    self.console.print("\n[bold]Step 3: Deploying skills...[/bold]\n")

    results = []
    for coll_name, skills in collections_dict.items():
        skill_names = [s.name for s in skills if s in recommendations]

        if not skill_names:
            continue

        self.console.print(f"⏳ Deploying from collection '{coll_name}'...")

        try:
            # Deploy skills from this collection
            result = deployer.deploy_skills(
                collection=coll_name,
                # Note: deploy_skills doesn't filter by skill names yet
                # This would require enhancement to SkillsDeployerService
            )

            results.append((coll_name, result))

            # Show individual results
            for skill_name in result['deployed_skills']:
                self.console.print(f"  ✓ {skill_name} deployed")

            for skill_name in result['skipped_skills']:
                self.console.print(f"  ⚠ {skill_name} skipped (already deployed)")

            for error in result['errors']:
                self.console.print(f"  ✗ Error: {error}")

            self.console.print()

        except Exception as e:
            self.console.print(f"[red]✗ Failed to deploy from {coll_name}: {e}[/red]\n")
            results.append((coll_name, {"errors": [str(e)]}))

    # Step 6: Display summary
    total_deployed = sum(r.get('deployed_count', 0) for _, r in results)
    total_skipped = sum(r.get('skipped_count', 0) for _, r in results)
    total_errors = sum(len(r.get('errors', [])) for _, r in results)

    self.console.print(Panel(
        f"[bold green]✅ Deployment Complete![/bold green]\n\n"
        f"  • Deployed: {total_deployed} skills\n"
        f"  • Skipped: {total_skipped} skills\n"
        f"  • Errors: {total_errors}\n\n"
        f"{'⚠️  Claude Code Restart Required' if total_deployed > 0 else ''}\n"
        f"{'Skills are only loaded at STARTUP.' if total_deployed > 0 else ''}\n"
        f"{'Please restart Claude Code for new skills to be available.' if total_deployed > 0 else ''}",
        title="Deployment Summary",
        border_style="green"
    ))

    Prompt.ask("\nPress Enter to continue")


def _generate_skill_recommendations(
    self,
    analysis: ToolchainAnalysis,
    deployer: SkillsDeployerService
) -> List[SkillRecommendation]:
    """Generate skill recommendations based on toolchain analysis."""

    # Implementation from algorithm section
    # This would use TOOLCHAIN_SKILL_MAPPING and resolve across collections

    recommendations = []

    # Add universal skills
    universal_skills = ["systematic-debugging", "code-review", "test-driven-development"]

    # Add language-specific skills
    language_skills = {
        "python": ["async-testing"],
        "typescript": ["async-testing"],
        "rust": ["cargo-best-practices"],
        "go": ["goroutine-patterns"],
    }

    for lang in analysis.languages:
        if lang.name.lower() in language_skills:
            universal_skills.extend(language_skills[lang.name.lower()])

    # Resolve skills from collections
    collections_data = deployer.list_collections()

    for skill_name in set(universal_skills):  # Deduplicate
        # Find skill in collections by priority
        for coll_name, coll_config in sorted(
            collections_data['collections'].items(),
            key=lambda x: x[1].get('priority', 999)
        ):
            if not coll_config.get('enabled', True):
                continue

            # Check if skill exists in collection
            available = deployer.list_available_skills(coll_name)
            skill_exists = any(
                s['name'] == skill_name
                for s in available.get('skills', [])
            )

            if skill_exists:
                recommendations.append(
                    SkillRecommendation(
                        name=skill_name,
                        collection=coll_name,
                        collection_url=coll_config['url'],
                        priority=coll_config['priority'],
                        confidence=ConfidenceLevel.HIGH
                    )
                )
                break

    return recommendations
```

---

## 9. Testing Strategy

### Unit Tests

**Test File:** `tests/cli/commands/test_configure_skills.py`

```python
def test_skills_list_collections(console_mock, deployer_mock):
    """Test listing available collections."""
    # Mock deployer.list_collections()
    # Verify table rendering
    # Verify enabled/disabled display

def test_skills_add_collection(console_mock, deployer_mock):
    """Test adding new collection."""
    # Mock user input (name, URL, priority)
    # Verify deployer.add_collection called
    # Verify success message

def test_skills_auto_discover(console_mock, deployer_mock, analyzer_mock):
    """Test auto-discovery workflow."""
    # Mock analyzer.analyze() to return Python + TypeScript
    # Mock deployer.list_available_skills()
    # Verify recommendations displayed
    # Mock user confirmation
    # Verify deployer.deploy_skills called

def test_skills_auto_discover_no_recommendations(console_mock, analyzer_mock):
    """Test auto-discovery with no matching skills."""
    # Mock analyzer to return unknown toolchain
    # Verify "No recommendations" message

def test_skills_deployment_error_handling(console_mock, deployer_mock):
    """Test error handling during deployment."""
    # Mock deployer.deploy_skills to raise exception
    # Verify error panel displayed
    # Verify troubleshooting suggestions
```

### Integration Tests

**Test File:** `tests/integration/test_skills_configurator_e2e.py`

```python
def test_full_auto_discovery_workflow(tmp_path):
    """Test end-to-end auto-discovery workflow."""
    # Setup: Create project with Python files
    # Run: Auto-discovery
    # Verify: Python skills recommended and deployed

def test_collection_management_workflow(tmp_path):
    """Test collection add/remove/update workflow."""
    # Add collection
    # List collections
    # Update collection
    # Remove collection

def test_deployment_with_multiple_collections(tmp_path):
    """Test deploying from multiple collections."""
    # Setup: Configure 2 collections with different priorities
    # Deploy: Skills from both collections
    # Verify: Priority-based resolution
```

---

## 10. Documentation Requirements

### User Guide Update

**File:** `docs/guides/skills-configuration.md`

```markdown
# Skills Configuration Guide

## Quick Start

1. Run configurator:
   ```bash
   claude-mpm configure
   ```

2. Select option `[2] Skills Configuration`

3. Choose `[6] Auto-Discover & Deploy` for automatic setup

## Auto-Discovery

The configurator automatically detects your project's toolchain and recommends
relevant skills from configured collections.

### Supported Toolchains

- **Python**: pytest, async-testing, type-hints
- **TypeScript**: React, Next.js, async-testing
- **Rust**: Cargo best practices, async patterns
- **Go**: Goroutines, testing, error handling
- **Docker**: Containerization, multi-stage builds

### Manual Configuration

For fine-grained control:

1. **List Collections**: View all configured skill repositories
2. **Add Collection**: Add custom GitHub repository
3. **Deploy from Collection**: Choose specific collection
4. **Deploy Specific Skills**: Select individual skills

## Collection Management

### Adding Collections

```bash
[2] Skills Configuration → [2] Add New Collection

Enter collection name: my-custom-skills
Enter GitHub URL: https://github.com/username/my-skills
Enter priority (1-99): 10
```

### Priority System

Lower number = higher priority (checked first for skill resolution)

- Priority 1: claude-mpm (default)
- Priority 2: obra-superpowers
- Priority 3+: Custom collections

### Updating Collections

```bash
[2] Skills Configuration → [3] Update All Collections
```

Runs `git pull` in all collection directories.

## Troubleshooting

### "Collection not found" Error

**Solution:** Add the collection first:
```bash
[2] Skills Configuration → [2] Add New Collection
```

### "Git operation failed" Error

**Solution:** Remove and re-add collection:
```bash
rm -rf ~/.claude/skills/collection-name
[2] Skills Configuration → [2] Add New Collection
```

### Skills Not Appearing in Claude Code

**Cause:** Skills are only loaded at startup.

**Solution:** Restart Claude Code:
1. Close all Claude Code windows
2. Quit Claude Code (Cmd+Q / Alt+F4)
3. Re-launch Claude Code
```

---

## 11. Implementation Checklist

### Phase 1: Core Infrastructure (Week 1)

- [ ] Create `configure_skills_manager.py` module
- [ ] Implement `SkillsManager` class with basic menu
- [ ] Add collection listing functionality
- [ ] Add collection add/remove functionality
- [ ] Update `configure.py` to use `SkillsManager`
- [ ] Update menu text in `configure_navigation.py`

### Phase 2: Auto-Discovery (Week 2)

- [ ] Create `TOOLCHAIN_SKILL_MAPPING` data structure
- [ ] Implement `auto_discover_skills()` algorithm
- [ ] Implement `_generate_skill_recommendations()`
- [ ] Add toolchain analysis display
- [ ] Add recommendation preview
- [ ] Add customization workflow

### Phase 3: Deployment Integration (Week 2)

- [ ] Integrate `SkillsDeployerService`
- [ ] Add deployment progress display (Rich progress bars)
- [ ] Add error handling and retry logic
- [ ] Add Claude Code restart detection
- [ ] Implement deployment result summary

### Phase 4: Enhanced Features (Week 3)

- [ ] Add collection update (git pull) functionality
- [ ] Add deployed skills viewer
- [ ] Add skill removal functionality
- [ ] Add default collection management
- [ ] Integrate with existing SkillsWizard for agent mapping

### Phase 5: Testing & Documentation (Week 3-4)

- [ ] Write unit tests for `SkillsManager`
- [ ] Write integration tests for workflows
- [ ] Update user documentation
- [ ] Add inline code documentation
- [ ] Create troubleshooting guide
- [ ] Test on multiple platforms (macOS, Linux, Windows)

### Phase 6: Polish & Release (Week 4)

- [ ] Add keyboard shortcuts
- [ ] Improve error messages
- [ ] Add confirmation prompts
- [ ] Add undo/rollback for deployments
- [ ] Final QA testing
- [ ] Release notes

---

## 12. Risks & Mitigations

### Risk 1: Network Connectivity

**Impact:** Auto-discovery fails if GitHub unavailable

**Mitigation:**
- Cache manifest locally after first download
- Graceful degradation to cached data
- Clear error messages with offline mode option

### Risk 2: Git Operation Failures

**Impact:** Collection updates fail due to conflicts

**Mitigation:**
- Implement conflict detection
- Offer "force update" (git reset --hard origin/main)
- Provide manual resolution instructions

### Risk 3: Skill Name Conflicts

**Impact:** Different collections may have same skill name

**Mitigation:**
- Priority-based resolution (already implemented)
- Display collection source in UI
- Allow user override during deployment

### Risk 4: Large Manifests

**Impact:** Slow loading with many skills

**Mitigation:**
- Implement manifest caching
- Lazy-load skill details
- Progress indicators for long operations

### Risk 5: Claude Code Restart Burden

**Impact:** Users must restart frequently during testing

**Mitigation:**
- Batch deployments to minimize restarts
- Clear messaging about restart requirement
- Consider hot-reload mechanism (future enhancement)

---

## 13. Future Enhancements

### V2: Advanced Features

1. **Skill Preview**
   - Display SKILL.md content before deployment
   - Show examples and usage

2. **Skill Dependencies**
   - Auto-deploy dependent skills
   - Dependency graph visualization

3. **Skill Search**
   - Full-text search across all collections
   - Filter by category, toolchain, tags

4. **Skill Ratings**
   - Community ratings/reviews
   - Usage statistics

5. **Custom Skill Creation**
   - Wizard for creating new skills
   - Template generation
   - GitHub publishing workflow

### V3: Enterprise Features

1. **Private Collections**
   - Support for private GitHub repos
   - Authentication integration
   - Corporate skill libraries

2. **Skill Versioning**
   - Pin specific skill versions
   - Changelog tracking
   - Rollback capability

3. **Team Sharing**
   - Share collection configurations
   - Team-wide skill deployments
   - Permission management

---

## Conclusion

This analysis provides a comprehensive roadmap for integrating skills configuration into the claude-mpm configurator with intelligent auto-discovery. The implementation leverages existing infrastructure (`SkillsDeployerService`, `SkillsConfig`, `ToolchainAnalyzerService`) and enhances the user experience with:

✅ **Auto-discovery** based on project toolchain
✅ **Multi-collection** support with priority-based resolution
✅ **Interactive deployment** with progress feedback
✅ **Comprehensive error handling** with actionable messages
✅ **Seamless integration** with existing configurator architecture

**Estimated Development Time:** 3-4 weeks
**Priority:** High (enables core skills functionality)
**Dependencies:** None (all services already implemented)

**Next Steps:**
1. Review and approve design
2. Create Phase 1 implementation ticket
3. Begin development of `configure_skills_manager.py`
