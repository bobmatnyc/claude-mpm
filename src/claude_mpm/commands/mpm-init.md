# /mpm-init [update]

Initialize or intelligently update your project for optimal use with Claude Code and Claude MPM using the Agentic Coder Optimizer agent.

## Usage

```
/mpm-init                      # Auto-detects and offers update or create
/mpm-init update               # Lightweight update based on recent git activity
/mpm-init context              # Intelligent context analysis from git history
/mpm-init context --days 14    # Analyze last 14 days of git history
/mpm-init resume               # Resume from stop event logs (NEW)
/mpm-init resume --list        # List all sessions from logs
/mpm-init resume --session-id ID  # Resume specific session
/mpm-init catchup              # Quick commit history display (no analysis)
/mpm-init --review             # Review project state without changes
/mpm-init --update             # Full update of existing CLAUDE.md
/mpm-init --organize           # Organize project structure
/mpm-init --force              # Force recreate from scratch
/mpm-init --project-type web --framework react
/mpm-init --ast-analysis --comprehensive
```

## Description

This command has two primary modes:
- **Project initialization/updates**: Delegates to the Agentic Coder Optimizer agent for documentation, tooling, and workflow setup
- **Context analysis** (context/catchup): Provides intelligent project context from git history for resuming work

**Resume Modes**: The command provides two resume capabilities:
- `/mpm-init resume`: Reads stop event logs from `.claude-mpm/responses/` to help resume work
- `/mpm-init context`: Analyzes git history for intelligent work resumption (delegates to Research agent)

**Quick Update Mode**: Running `/mpm-init update` performs a lightweight update focused on recent git activity. It analyzes recent commits, generates an activity report, and updates documentation with minimal changes. Perfect for quick refreshes after development sprints.

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

## Context Analysis

**Purpose**: Provide intelligent project context for resuming work by analyzing git history.

### Commands

#### `/mpm-init context` (Primary)
```bash
/mpm-init context                  # Analyze last 7 days of git history
/mpm-init context --days 14        # Analyze last 14 days
```

Analyzes recent git commits to identify:
- **Active work streams**: What was being worked on (themes from commit patterns)
- **Intent and motivation**: Why this work matters (from commit messages)
- **Risks and blockers**: What needs attention (stalled work, conflicts, anti-patterns)
- **Recommended next actions**: What to work on next (logical continuations)

**How it works**:
1. Parses git history (default: last 7 days)
2. PM delegates to Research agent with structured prompt
3. Research analyzes work streams, intent, risks, recommendations
4. PM presents intelligent summary for seamless work resumption

**NOT session state**: This does NOT save/restore conversation state like Claude Code. Instead, it reconstructs project context from git history using conventional commits and commit message analysis.

#### `/mpm-init resume` (Stop Event Logs)
```bash
/mpm-init resume                    # Show latest session from logs
/mpm-init resume --list             # List all sessions
/mpm-init resume --session-id ID    # Resume specific session
/mpm-init resume --last 5           # Show last 5 sessions
```

Reads from stop event logs to help resume work from previous sessions:

**Data Sources** (two-tier strategy):
1. **Resume logs** (preferred): `.claude-mpm/resume-logs/*.md` - Structured 10k-token summaries
2. **Response logs** (fallback): `.claude-mpm/responses/*.json` - Raw conversation stop events

**What it shows**:
- When session ended (time ago)
- What was being worked on (request)
- Tasks completed (from PM responses)
- Files modified (from PM tracking)
- Next steps (from PM recommendations)
- Stop reason (why session ended)
- Token usage (context consumption)
- Git context (branch, working directory)

**How it works**:
1. Scans response logs in `.claude-mpm/responses/`
2. Groups by `session_id`
3. Parses PM response JSON for context
4. Extracts tasks, files, next steps from PM summaries
5. Displays comprehensive resume context

**Use Cases**:
- Resume work after context threshold pause
- Review what was accomplished in previous session
- Understand why session stopped (max_tokens, end_turn, etc.)
- See exact files and tasks from last session

**Difference from `context`**:
- **resume**: Reads actual stop event logs (what PM logged)
- **context**: Analyzes git commits (what was committed)

### `/mpm-init catchup` (Simple Git History)
```bash
/mpm-init catchup
```

Quick display of last 25 commits across all branches. No analysis - just raw git log output with authors and dates. Use this for quick "what happened recently?" checks.

**Distinction**:
- **catchup**: Quick commit history (instant, no analysis)
- **context**: Intelligent work resumption (10-30s, deep analysis)

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

### Quick Update (Lightweight)
```bash
/mpm-init update
```
Fast update based on recent 30-day git activity. Generates activity report and updates docs with minimal changes.

**Note**: Typing `/mpm-init update` executes `claude-mpm mpm-init --quick-update` automatically.

### Context Analysis (Intelligent Resumption)

Get intelligent context for resuming work based on git history analysis:

**Standard Context Analysis:**
```bash
/mpm-init context              # Analyze last 7 days (default)
/mpm-init context --days 14    # Analyze last 14 days
/mpm-init context --days 30    # Analyze last 30 days
```

This provides intelligent analysis including:
- **Work stream identification** from commit patterns
- **Intent analysis** (why work was done)
- **Risk detection** (stalled work, conflicts, etc.)
- **Recommended next actions** for seamless continuation

**How it works:**
1. Parses git history (7 days default)
2. PM delegates to Research agent with structured prompt
3. Research agent provides deep analysis
4. PM presents intelligent summary

**NOT session state**: This reconstructs context from git history, not saved conversation state.

**Backward Compatibility:**
```bash
/mpm-init resume               # Still works but deprecated
```

The old `resume` command redirects to `context` with a deprecation warning.

### Resume from Stop Event Logs

Display context from previous sessions using stop event logs:

```bash
/mpm-init resume                    # Show latest session
/mpm-init resume --list             # List all available sessions
/mpm-init resume --session-id abc123  # Resume specific session
/mpm-init resume --last 10          # Show last 10 sessions
```

Shows comprehensive context including:
- What was being worked on
- Tasks completed (from PM tracking)
- Files modified
- Next steps recommended
- Stop reason (context limit, completion, etc.)
- Token usage
- Time elapsed since session

**Example Output:**
```
================================================================================
📋 Resume Context - Session from 2 hours ago
================================================================================

Session ID: 20251104_143000
Ended: 2024-11-04 14:30 (2 hours ago)
Stop Reason: Context threshold reached (70%)
Token Usage: 140,000 / 200,000 (70%)

Working on:
  "Implementing auto-pause and resume functionality"

✅ Completed:
  • Researched stop event logging system
  • Found response logs in .claude-mpm/responses/
  • Identified two-tier resume strategy

📝 Files Modified:
  • src/claude_mpm/services/cli/resume_service.py (new)
  • src/claude_mpm/cli/commands/mpm_init/ (refactored into package)

🎯 Next Steps:
  • Implement ResumeService class
  • Add resume subcommand to mpm-init
  • Test with real response logs

Git Context:
  Branch: main
  Working Directory: /Users/masa/Projects/claude-mpm
================================================================================
```

**Use Cases:**
- Resume after hitting context limit
- Review what was accomplished in last session
- See exact next steps recommended by PM
- Understand why session stopped

### Quick Git History (Catchup)

Display recent commit history without analysis:

```bash
/mpm-init catchup
```

Shows:
- Last 25 commits from all branches
- Author attribution and timestamps
- Contributor activity summary

Use this for quick "what happened recently?" checks. For intelligent analysis, use `context` instead.

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

**IMPORTANT**: This slash command accepts an optional `update` argument for quick updates.

**Argument Processing**:
- When you type `/mpm-init update`, Claude executes `claude-mpm mpm-init --quick-update`
- When you type `/mpm-init` (no argument), Claude executes standard mode
- The slash command handler automatically maps the `update` argument to the `--quick-update` flag

This command routes between different modes:

### Context Analysis Commands

**IMPORTANT**: Context analysis commands (`/mpm-init context`, `/mpm-init catchup`) have distinct behaviors:

**`/mpm-init context` - Delegates to PM**:
```bash
claude-mpm mpm-init context --days 7
```

This command delegates work to the PM framework:
1. Parses git history (7 days default)
2. PM constructs structured Research delegation prompt
3. PM presents prompt for Research agent to analyze
4. Research identifies work streams, intent, risks, recommendations
5. PM synthesizes for user

This is intelligent analysis requiring Research agent expertise.

**How the PM delegates to Research:**
The PM creates a delegation prompt that asks Research to analyze:
- **Work Stream Identification**: Groups related commits into themes
- **Intent Analysis**: Infers why work was done from commit messages
- **Risk Detection**: Identifies stalled work, conflicts, and blockers
- **Recommended Actions**: Suggests logical next steps for continuation

**`/mpm-init catchup` - Direct CLI execution**:
```bash
claude-mpm mpm-init catchup
```

This executes directly via CLI without agent delegation:
- Displays last 25 commits from all branches
- Shows authors, dates, commit messages
- Instant output (no analysis)

This is a simple git log display utility.

---

### Project Initialization/Update Commands

**IMPORTANT**: Standard initialization and update commands delegate to the Agentic Coder Optimizer agent.

**Quick Update Mode** (`/mpm-init update`):
```bash
claude-mpm mpm-init --quick-update
```
This triggers a lightweight update that analyzes recent git activity (30 days) and generates an activity report.

**Standard Mode** (`/mpm-init`):
```bash
claude-mpm mpm-init [options]
```
This triggers the full initialization or smart update flow.

The command delegates to the Agentic Coder Optimizer agent which:
1. Analyzes your project structure
2. Creates comprehensive documentation
3. Establishes single-path workflows
4. Configures development tools
5. Sets up memory systems
6. Performs AST analysis (if enabled)
7. Organizes everything with priority rankings

**Quick Update Mode** performs:
1. Git history analysis (last 30 days)
2. Recent activity report generation
3. Lightweight documentation updates
4. Change summary for PM memory

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

### For Quick Update Mode (`/mpm-init update`)
- ✅ **Activity Report**: Summary of recent 30-day git activity
- ✅ **Recent Commits**: List of commits with authors and dates
- ✅ **Changed Files**: Files with most modifications
- ✅ **Active Branches**: Current and recent branch activity
- ✅ **Lightweight Doc Updates**: Append activity notes to CLAUDE.md
- ✅ **PM Memory Update**: Recommendations for project manager
- ✅ **Quick Check**: Verify CLAUDE.md freshness without full regeneration

## Notes

- **Quick Update vs Full Update**: Use `/mpm-init update` for fast activity-based updates (30 days), or `/mpm-init --update` for comprehensive doc refresh
- **Resume Strategies**:
  - **`/mpm-init resume`**: Read stop event logs (what PM tracked in last session)
  - **`/mpm-init context`**: Analyze git history (intelligent work stream analysis via Research)
  - **`/mpm-init catchup`**: Quick commit history display (no analysis)
- **Stop Event Logs**: Response logs in `.claude-mpm/responses/` contain PM summaries with tasks, files, and next steps
- **Two-Tier Resume**: Prefers structured resume logs (`.claude-mpm/resume-logs/`), falls back to response logs
- **Smart Mode**: Automatically detects existing CLAUDE.md and offers update vs recreate
- **Safe Updates**: Previous versions always archived before updating
- **Custom Content**: Your project-specific sections are preserved by default
- **Git Integration**: Analyzes recent commits to understand project evolution and provide work context
- **Backward Compatibility**: All existing `resume` commands redirect to `context` with deprecation warning
- **Argument Processing**: The slash command processes the `update` argument and routes to `--quick-update` flag
- **Agent Delegation**:
  - Project initialization and updates use the Agentic Coder Optimizer agent
  - Context analysis (`context`) delegates to PM, who coordinates with Research agent
  - Simple git history (`catchup`) executes directly via CLI without agent delegation
- **NOT Session State**: Context analysis reconstructs project understanding from git history, not saved conversation state
- AST analysis is enabled by default for comprehensive documentation
- Priority rankings help AI agents focus on critical instructions first
- The holistic review ensures documentation quality and completeness
- All documentation is optimized for AI agent understanding

## Related Commands

- `/mpm-status`: Check current project setup status
- `/mpm-agents`: Manage specialized agents
- `/mpm-config`: Configure Claude MPM settings
- `/mpm-doctor`: Diagnose and fix issues