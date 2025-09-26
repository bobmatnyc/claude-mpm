# /mpm-init

Initialize or intelligently update your project for optimal use with Claude Code and Claude MPM using the Agentic Coder Optimizer agent.

## Usage

```
/mpm-init                      # Auto-detects and offers update or create
/mpm-init --review             # Review project state without changes
/mpm-init --update             # Update existing CLAUDE.md
/mpm-init --organize           # Organize project structure
/mpm-init --force              # Force recreate from scratch
/mpm-init --project-type web --framework react
/mpm-init --ast-analysis --comprehensive
```

## Description

This command delegates to the Agentic Coder Optimizer agent to establish clear, single-path project standards for documentation, tooling, and workflows.

**Smart Update Mode**: When CLAUDE.md exists, the command automatically offers to update rather than recreate, preserving your custom content while refreshing standard sections. Previous versions are archived in `docs/_archive/` for safety.

## Features

- **📚 Comprehensive CLAUDE.md**: Creates AI-optimized project documentation
- **🎯 Priority-based Organization**: Ranks instructions by importance (🔴🟡🟢⚪)
- **🔍 AST Analysis**: Deep code structure analysis for enhanced documentation
- **🚀 Single-path Workflows**: Establishes ONE way to do ANYTHING
- **🧠 Memory System**: Initializes project knowledge retention
- **🔧 Tool Configuration**: Sets up linting, formatting, testing
- **📝 Holistic Review**: Final organization and validation pass

## Options

### Mode Options
- `--review`: Review project state without making changes
- `--update`: Update existing CLAUDE.md instead of recreating
- `--force`: Force reinitialization even if project is already configured

### Configuration Options
- `--project-type [type]`: Specify project type (web, api, cli, library, etc.)
- `--framework [name]`: Specify framework (react, vue, django, fastapi, etc.)
- `--ast-analysis`: Enable AST analysis for enhanced documentation (default: enabled)
- `--no-ast-analysis`: Disable AST analysis for faster initialization
- `--comprehensive`: Create comprehensive setup including CI/CD and deployment
- `--minimal`: Create minimal configuration (CLAUDE.md only)

### Organization Options
- `--organize`: Organize misplaced files into proper directories
- `--preserve-custom`: Preserve custom sections when updating (default)
- `--no-preserve-custom`: Don't preserve custom sections
- `--skip-archive`: Skip archiving existing files before updating

## What This Command Does

### Auto-Detection (NEW)
When run without flags and CLAUDE.md exists:
1. Analyzes existing documentation
2. Shows current status (size, sections, priority markers)
3. Offers options:
   - Update (smart merge)
   - Recreate (fresh start)
   - Review (analysis only)
   - Cancel

### 1. Project Analysis
- Scans project structure and existing configurations
- Identifies project type, language, and frameworks
- Checks for existing documentation and tooling

### 2. CLAUDE.md Creation/Update
The command creates a well-organized CLAUDE.md with:

```markdown
## 🎯 Priority Index
### 🔴 CRITICAL Instructions
- Security rules, data handling, core business logic

### 🟡 IMPORTANT Instructions  
- Key workflows, architecture decisions

### 🟢 STANDARD Instructions
- Common operations, coding standards

### ⚪ OPTIONAL Instructions
- Nice-to-have features, future enhancements
```

### 3. Single-Path Standards
- ONE command for building: `make build`
- ONE command for testing: `make test`
- ONE command for deployment: `make deploy`
- Clear documentation of THE way to do things

### 4. AST Analysis (Optional)
When enabled, performs:
- Code structure extraction (classes, functions, methods)
- API documentation generation
- Architecture diagram creation
- Function signature and dependency mapping
- Creates DEVELOPER.md with technical details
- Adds CODE_STRUCTURE.md with AST insights

### 5. Tool Configuration
- Linting setup and configuration
- Code formatting standards
- Testing framework setup
- Pre-commit hooks if needed

### 6. Memory System
- Creates `.claude-mpm/memories/` directory
- Initializes memory files for project knowledge
- Documents memory usage patterns

### 7. Holistic Organization (Final Step)
After all tasks, performs a comprehensive review:
- Reorganizes content by priority
- Validates completeness
- Ensures single-path principle
- Adds meta-instructions for maintenance

### 8. Update Mode Features (NEW)
When updating existing documentation:
- **Smart Merging**: Intelligently merges new content with existing
- **Custom Preservation**: Keeps your project-specific sections
- **Automatic Archival**: Backs up previous version to `docs/_archive/`
- **Conflict Resolution**: Removes duplicate or contradictory information
- **Change Tracking**: Shows what was updated after completion

## Examples

### Smart Auto-Detection (Recommended)
```bash
/mpm-init
```
Analyzes project and offers appropriate action (create/update/review).

### Review Project State
```bash
/mpm-init --review
```
Analyzes project structure, documentation, and git history without changes.

### Update Existing Documentation
```bash
/mpm-init --update
```
Updates CLAUDE.md while preserving custom sections.

### Organize Project Structure
```bash
/mpm-init --organize --update
```
Organizes misplaced files AND updates documentation.

### Web Project with React
```bash
/mpm-init --project-type web --framework react
```
Initializes with web-specific configurations and React patterns.

### Force Fresh Start
```bash
/mpm-init --force --comprehensive
```
Overwrites everything with comprehensive setup.

### Fast Mode (No AST)
```bash
/mpm-init --no-ast-analysis --minimal
```
Quick initialization without code analysis.

## Implementation

This command executes:
```bash
claude-mpm mpm-init [options]
```

The command delegates to the Agentic Coder Optimizer agent which:
1. Analyzes your project structure
2. Creates comprehensive documentation
3. Establishes single-path workflows
4. Configures development tools
5. Sets up memory systems
6. Performs AST analysis (if enabled)
7. Organizes everything with priority rankings

## Expected Output

### For New Projects
- ✅ **CLAUDE.md**: Main AI agent documentation with priority rankings
- ✅ **Project structure**: Standard directories created (tmp/, scripts/, docs/)
- ✅ **Single-path workflows**: Clear commands for all operations
- ✅ **Tool configurations**: Linting, formatting, testing setup
- ✅ **Memory system**: Initialized for knowledge retention
- ✅ **Developer docs**: Technical documentation (with AST analysis)
- ✅ **Priority organization**: Instructions ranked by importance

### For Existing Projects (Update Mode)
- ✅ **Updated CLAUDE.md**: Refreshed with latest standards
- ✅ **Preserved content**: Your custom sections maintained
- ✅ **Archive created**: Previous version in `docs/_archive/`
- ✅ **Structure verified**: Missing directories created
- ✅ **Files organized**: Misplaced files moved (if --organize)
- ✅ **Change summary**: Report of what was updated

## Notes

- **Smart Mode**: Automatically detects existing CLAUDE.md and offers update vs recreate
- **Safe Updates**: Previous versions always archived before updating
- **Custom Content**: Your project-specific sections are preserved by default
- **Git Integration**: Analyzes recent commits to understand project evolution
- The command uses the Agentic Coder Optimizer agent for implementation
- AST analysis is enabled by default for comprehensive documentation
- Priority rankings help AI agents focus on critical instructions first
- The holistic review ensures documentation quality and completeness
- All documentation is optimized for AI agent understanding

## Related Commands

- `/mpm-status`: Check current project setup status
- `/mpm-agents`: Manage specialized agents
- `/mpm-config`: Configure Claude MPM settings
- `/mpm-doctor`: Diagnose and fix issues