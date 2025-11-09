# MPM-Init Package

This package provides comprehensive project initialization and update capabilities for Claude Code and Claude MPM.

## Package Structure

```
mpm_init/
├── __init__.py         # Package initialization and exports
├── core.py            # MPMInitCommand class - main orchestrator
├── prompts.py         # Prompt building functions
├── display.py         # Display and UI helper functions
├── git_activity.py    # Git analysis and activity tracking
├── modes.py           # Operation mode handlers
└── README.md          # This file
```

## Module Responsibilities

### `__init__.py` - Package Initialization
**Purpose**: Public API exposure and lazy imports

**Exports**:
- `MPMInitCommand` - Main command class (from core.py)
- `mpm_init` - Click command group (lazy import from mpm_init_cli.py)

**Key Features**:
- Lazy import via `__getattr__` to avoid circular dependencies
- Clean public API surface
- Internal module re-exports for package-level imports

### `core.py` - MPMInitCommand Class
**Purpose**: Main orchestrator for project initialization

**Key Class**: `MPMInitCommand`

**Responsibilities**:
- Coordinate initialization workflow
- Manage service components (DocumentationManager, ProjectOrganizer, etc.)
- Build and execute delegation prompts
- Handle subprocess execution via claude-mpm CLI
- Coordinate pre/post initialization tasks

**Public Methods**:
```python
def initialize_project(
    project_type: Optional[str] = None,
    framework: Optional[str] = None,
    force: bool = False,
    verbose: bool = False,
    ast_analysis: bool = True,
    update_mode: bool = False,
    review_only: bool = False,
    organize_files: bool = False,
    preserve_custom: bool = True,
    skip_archive: bool = False,
    dry_run: bool = False,
    quick_update: bool = False,
    catchup: bool = False,
    non_interactive: bool = False,
    days: int = 30,
    export: Optional[str] = None,
) -> Dict
```

```python
def handle_context(
    session_id: Optional[str] = None,
    list_sessions: bool = False,
    days: int = 7,
) -> Dict[str, Any]
```

### `prompts.py` - Prompt Building
**Purpose**: Pure functions for generating agent delegation prompts

**Functions**:
- `build_initialization_prompt()` - Create new project initialization prompt
- `build_update_prompt()` - Update existing CLAUDE.md prompt
- `build_research_context_prompt()` - Research agent delegation for git analysis

**Design Pattern**: Pure functions with no side effects or external dependencies

**Example**:
```python
from claude_mpm.cli.commands.mpm_init import prompts

prompt = prompts.build_initialization_prompt(
    project_path=Path("/path/to/project"),
    project_type="web",
    framework="FastAPI",
    ast_analysis=True
)
```

### `display.py` - Display Functions
**Purpose**: Pure functions for console output and reporting

**Functions**:
- `display_documentation_status()` - Show doc analysis
- `display_review_report()` - Comprehensive project review
- `display_catchup()` - Recent commit history
- `display_activity_report()` - Git activity summary
- `display_results()` - Initialization results
- `show_update_plan()` - Update mode plan
- `show_initialization_plan()` - Init mode plan

**Design Pattern**: All functions accept DisplayHelper/Console as parameters (dependency injection)

**Example**:
```python
from claude_mpm.cli.commands.mpm_init import display

display.display_activity_report(display_helper, activity_report)
```

### `git_activity.py` - Git Analysis
**Purpose**: Git repository analysis and activity tracking

**Functions**:
- `catchup()` - Get recent commit history for PM context
- `generate_activity_report()` - Comprehensive activity report
- `export_activity_report()` - Export report to markdown
- `append_activity_notes()` - Append activity to CLAUDE.md
- `handle_context()` - Intelligent context for resuming work

**Use Cases**:
- Quick update mode (`--quick-update`)
- Catchup mode (`--catchup`)
- Context analysis (`/mpm-init --context`)

**Example**:
```python
from claude_mpm.cli.commands.mpm_init import git_activity

# Get recent commits
data = git_activity.catchup(project_path)

# Generate full activity report
report = git_activity.generate_activity_report(
    git_analysis, doc_analysis, days=30
)
```

### `modes.py` - Operation Mode Handlers
**Purpose**: Handle different execution modes

**Functions**:
- `prompt_update_action()` - Interactive prompt for update decisions
- `run_review_mode()` - Review project without changes
- `run_quick_update_mode()` - Lightweight git-based update
- `run_dry_run_mode()` - Show planned changes without execution
- `handle_update_post_processing()` - Post-update summary

**Modes Supported**:
- **Review Mode** (`--review-only`): Analyze project state
- **Dry-Run Mode** (`--dry-run`): Preview changes
- **Quick Update** (`--quick-update`): Fast incremental update
- **Update Mode** (`--update`): Smart merge with existing docs

**Example**:
```python
from claude_mpm.cli.commands.mpm_init import modes

result = modes.run_review_mode(
    console, display, organizer, doc_manager, analyzer
)
```

## Usage Examples

### Programmatic Usage

```python
from pathlib import Path
from claude_mpm.cli.commands.mpm_init import MPMInitCommand

# Initialize command
command = MPMInitCommand(project_path=Path("/path/to/project"))

# Create new project
result = command.initialize_project(
    project_type="web",
    framework="FastAPI",
    ast_analysis=True
)

# Update existing project
result = command.initialize_project(
    update_mode=True,
    preserve_custom=True,
    ast_analysis=True
)

# Quick update based on git activity
result = command.initialize_project(
    quick_update=True,
    days=30,
    export="auto"
)

# Review only (no changes)
result = command.initialize_project(
    review_only=True
)
```

### CLI Usage

Via the Click command group (defined in parent `mpm_init_cli.py`):

```bash
# Create new project
/mpm-init

# Update existing project
/mpm-init --update

# Review project state
/mpm-init --review-only

# Quick update with export
/mpm-init --quick-update --days 30 --export auto

# Dry-run (preview changes)
/mpm-init --dry-run

# Catchup (show recent commits)
/mpm-init --catchup

# Context analysis
/mpm-init --context --days 7
```

## Design Principles

### 1. **Separation of Concerns**
Each module has a single, clear responsibility:
- `core.py` - orchestration
- `prompts.py` - prompt building
- `display.py` - UI/output
- `git_activity.py` - git analysis
- `modes.py` - mode handling

### 2. **Pure Functions**
`prompts.py` and `display.py` contain pure functions with no side effects or global state.

### 3. **Dependency Injection**
Display functions accept `DisplayHelper` and `Console` as parameters rather than creating their own instances.

### 4. **Modular Architecture**
Easy to test, maintain, and extend individual components without touching others.

### 5. **Lazy Imports**
`__init__.py` uses `__getattr__` to avoid circular dependencies while maintaining clean API.

## Service Dependencies

The package relies on these service components:

- `DocumentationManager` - CLAUDE.md analysis and management
- `ProjectOrganizer` - Project structure validation
- `ArchiveManager` - Documentation versioning
- `EnhancedProjectAnalyzer` - Git and project state analysis
- `DisplayHelper` - Rich console output formatting

## Developer Notes

### Adding New Modes

To add a new operation mode:

1. Add mode handler function in `modes.py`:
   ```python
   def run_new_mode(console, display, ...) -> Dict:
       # Implementation
       return {"status": OperationResult.SUCCESS, "mode": "new_mode"}
   ```

2. Add mode detection in `core.py` `initialize_project()`:
   ```python
   if new_mode_flag:
       return self._run_new_mode()
   ```

3. Add CLI flag in parent `mpm_init_cli.py`

### Adding New Prompts

Add prompt builder in `prompts.py`:

```python
def build_new_prompt(project_path: Path, **kwargs) -> str:
    """Build prompt for new use case."""
    return f"""Your prompt template..."""
```

Then call from `core.py`:
```python
prompt = prompts.build_new_prompt(self.project_path, **kwargs)
```

### Adding Display Functions

Add display function in `display.py`:

```python
def display_new_report(display: DisplayHelper, data: Dict) -> None:
    """Display new report type."""
    display.display_header("NEW REPORT")
    # Rendering logic
```

### Testing Considerations

- **Unit Tests**: Test pure functions in `prompts.py` and `display.py`
- **Integration Tests**: Test `MPMInitCommand` with mocked services
- **E2E Tests**: Test via CLI commands in parent module

### File Size Tracking

Current module sizes:
- `core.py`: ~525 lines (Main orchestrator - expected to be largest)
- `prompts.py`: ~443 lines (Template generation)
- `git_activity.py`: ~427 lines (Git analysis utilities)
- `modes.py`: ~401 lines (Mode handlers)
- `display.py`: ~360 lines (Display functions)

All modules are well under the 600-line warning threshold.

## Version History

**Current Version**: Part of claude-mpm 4.20.7

**Changes from Monolithic `mpm_init.py`**:
- Split 800+ line file into 6 focused modules
- Improved testability through pure functions
- Better separation of concerns
- Easier maintenance and feature additions
- Clearer public API surface

## Related Files

- **Parent CLI**: `../mpm_init_cli.py` - Click command definitions
- **Handler**: `../mpm_init_handler.py` - Legacy compatibility handler
- **Parser**: `../../parsers/mpm_init_parser.py` - Command-line argument parsing
- **Tests**: `../../../../../tests/test_mpm_init_catchup.py` - Unit tests

## Contributing

When modifying this package:

1. Maintain pure function approach in `prompts.py` and `display.py`
2. Keep modules under 600 lines (split if approaching limit)
3. Add docstrings for all public functions
4. Update this README with new functionality
5. Add type hints to all function signatures
6. Follow existing patterns for consistency

## Support

For issues or questions:
- Check existing documentation in CLAUDE.md
- Review test files for usage examples
- Consult service component documentation
