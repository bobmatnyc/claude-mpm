# Slash Command Structure and Deployment Model Research

**Research Date:** 2025-11-29
**Project:** Claude MPM
**Context:** Investigation for implementing `/mpm-ticket` slash command
**Ticket:** N/A (exploratory research)

## Executive Summary

Claude MPM uses a **markdown-based slash command system** that deploys command files to `~/.claude/commands/` during startup. Commands are simple markdown files that Claude Code reads directly - there's no complex routing mechanism in the slash commands themselves. Instead, commands instruct Claude to execute CLI commands like `claude-mpm mpm-init` which then handle the actual logic through Python parsers and command handlers.

**Key Finding:** Slash commands are **documentation files**, not executable code. They tell Claude what CLI command to run and how to interpret arguments.

---

## 1. File Locations and Naming Conventions

### Source Directory (Framework)
```
/Users/masa/Projects/claude-mpm/src/claude_mpm/commands/
├── mpm.md                        # Main MPM command index
├── mpm-init.md                   # Initialization command
├── mpm-status.md                 # Status display
├── mpm-tickets.md                # Ticket management (existing)
├── mpm-doctor.md                 # Diagnostics
├── mpm-config.md                 # Configuration
├── mpm-resume.md                 # Resume sessions
├── mpm-version.md                # Version info
├── mpm-monitor.md                # Monitoring
├── mpm-organize.md               # Organization
├── mpm-agents.md                 # Agent management
├── mpm-agents-detect.md          # Agent detection
├── mpm-agents-recommend.md       # Agent recommendations
├── mpm-auto-configure.md         # Auto-configuration
├── mpm-help.md                   # Help system
└── __init__.py
```

### Deployed Directory (User)
```
~/.claude/commands/
├── mpm.md
├── mpm-init.md
├── mpm-status.md
├── mpm-tickets.md
├── mpm-doctor.md
├── mpm-config.md
├── mpm-resume.md
├── mpm-version.md
├── mpm-monitor.md
├── mpm-organize.md
├── mpm-agents.md
├── mpm-agents-detect.md
├── mpm-agents-recommend.md
├── mpm-auto-configure.md
└── mpm-help.md
```

### Naming Convention
- **Pattern:** `mpm-<command-name>.md`
- **Main command:** `mpm.md` (entry point)
- **Subcommands:** `mpm-<action>.md` (e.g., `mpm-init`, `mpm-status`)
- **Multi-level:** `mpm-<category>-<action>.md` (e.g., `mpm-agents-detect`)

---

## 2. Command File Structure

### Markdown Format (Example from `mpm-status.md`)

```markdown
# Show claude-mpm status and environment

Display the current status of Claude MPM including environment information,
active services, and system health.

## Usage

```
/mpm-status
```

## Description

This slash command delegates to the **PM agent** to gather and display
comprehensive status information about your Claude MPM environment.

## Implementation

This slash command delegates to the **PM agent** to collect status information.

When you run `/mpm-status`, the PM will:
1. Check Claude MPM version and installation
2. Verify Python environment and dependencies
3. Query active services (WebSocket server, Hook Service, Monitor)
4. Report memory system status
5. Check agent deployment status
6. Summarize current configuration

## Information Displayed

The PM agent will gather and present:

- **Claude MPM Version**: Current version and build number
- **Python Environment**: Python version, virtual environment status
- **Active Services**:
  - WebSocket server status and port
  - Hook service status
  - Monitor/dashboard status
- **Memory Usage**: Agent memory files and sizes
- **Agent Deployment**: Deployed agents and their locations
- **Configuration**: Key configuration settings
- **Project Info**: Current project directory and git status

## Expected Output

```
Claude MPM Status Report
========================

Version: v4.5.15
Python: 3.11.13
Environment: Mamba (claude-mpm)

Services:
  ✓ WebSocket Server: Running (port 8765)
  ✓ Hook Service: Active
  ✓ Monitor: Running (port 3000)

Agents Deployed: 5
  - PM (Core)
  - Engineer
  - Prompt-Engineer
  - Tester
  - Project-Organizer

Memory Files: 3 (2.4 MB)
Configuration: Valid

Project: /Users/masa/Projects/my-project
Git Status: Clean (main branch)
```

## Related Commands

- `/mpm-doctor`: Diagnose issues and run health checks
- `/mpm-config`: View or modify configuration
- `/mpm-agents`: List and manage deployed agents
```

### Key Structure Elements

1. **Title (H1)**: Brief description of command purpose
2. **Usage Section**: Shows command syntax with examples
3. **Description**: Explains what the command does
4. **Implementation**: Details how it works (PM delegation, CLI execution)
5. **Information/Features**: Lists what the command provides
6. **Examples**: Concrete usage examples
7. **Expected Output**: Sample output format
8. **Related Commands**: Cross-references

---

## 3. Argument Handling Pattern

### Simple Arguments (mpm-init example)

Commands can accept positional arguments that map to CLI flags:

**Slash Command:**
```
/mpm-init update
```

**Documented Mapping:**
```markdown
## Implementation

**IMPORTANT**: This slash command accepts an optional `update` argument.

**Argument Processing**:
- When you type `/mpm-init update`, Claude executes `claude-mpm mpm-init --quick-update`
- When you type `/mpm-init` (no argument), Claude executes standard mode
- The slash command handler automatically maps the `update` argument to the `--quick-update` flag
```

**Actual CLI Execution:**
```bash
claude-mpm mpm-init --quick-update
```

### Subcommand Pattern (mpm-init context)

**Slash Command:**
```
/mpm-init context --days 14
```

**CLI Execution:**
```bash
claude-mpm mpm-init context --days 14
```

**Documentation Pattern:**
```markdown
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
```

### Important Pattern Discovery

**Slash commands DON'T execute code directly.** They are:
1. **Documentation** that tells Claude what CLI command to run
2. **Instructions** on how to interpret arguments
3. **Context** about what the command does

The actual routing happens in:
- **CLI Parsers:** `/src/claude_mpm/cli/parsers/<command>_parser.py`
- **Command Handlers:** `/src/claude_mpm/cli/commands/<command>.py`

---

## 4. Deployment Mechanism

### Service: CommandDeploymentService

**Location:** `/src/claude_mpm/services/command_deployment_service.py`

**Core Functionality:**
```python
class CommandDeploymentService(BaseService):
    def __init__(self):
        super().__init__(name="command_deployment")

        # Source: Package resource path
        self.source_dir = get_package_resource_path("commands")
        # Or fallback: Path(__file__).parent.parent / "commands"

        # Target: User's home directory
        self.target_dir = Path.home() / ".claude" / "commands"

    def deploy_commands(self, force: bool = False) -> Dict[str, Any]:
        """Deploy MPM slash commands to user's Claude configuration."""
        # 1. Check source directory exists
        # 2. Create target directory if needed
        # 3. Get all .md files from source
        # 4. Copy each file to target (with timestamp check)
        # 5. Skip if target is newer (unless force=True)
        # 6. Return deployment results
```

### Deployment Trigger

**Startup Deployment:**
```python
# In /src/claude_mpm/cli/commands/run.py
from ...services.command_deployment_service import deploy_commands_on_startup

# During startup:
deploy_commands_on_startup(force=False)
```

**Characteristics:**
- **Automatic:** Deploys on `claude-mpm run` startup
- **Non-blocking:** Failures logged but don't stop startup
- **Smart:** Only updates files if source is newer
- **Isolated:** Creates `~/.claude/commands/` if missing

### Manual Deployment

```python
# Convenience function
def deploy_commands_on_startup(force: bool = False) -> None:
    service = CommandDeploymentService()
    result = service.deploy_commands(force=force)

    if result["deployed"]:
        logger.info(f"MPM commands deployed: {', '.join(result['deployed'])}")
```

---

## 5. Existing Command Examples

### Example 1: mpm-tickets (Direct CLI with MCP fallback)

**File:** `src/claude_mpm/commands/mpm-tickets.md`

**Pattern:**
```markdown
# mpm-tickets

Create and manage tickets using mcp-ticketer MCP server (primary) or
aitrackdown CLI (fallback)

## Usage

Use this command to create and manage tickets (epics, issues, tasks)
through intelligent MCP-first integration with automatic CLI fallback.

## Integration Methods

### PRIMARY: mcp-ticketer MCP Server (Preferred)

When available, ticketing operations use the mcp-ticketer MCP server for:
- Unified interface across ticketing backends (Jira, GitHub, Linear)
- Better error handling and validation
- Automatic backend detection

**MCP Tools**:
- `mcp__mcp-ticketer__create_ticket` - Create epics, issues, tasks
- `mcp__mcp-ticketer__list_tickets` - List tickets with filters
- `mcp__mcp-ticketer__get_ticket` - View ticket details

### SECONDARY: aitrackdown CLI (Fallback)

When mcp-ticketer is not available, operations fall back to aitrackdown CLI.

## Commands

```bash
# Create an epic
aitrackdown create epic "Title" --description "Description"

# Create an issue
aitrackdown create issue "Title" --description "Description"
```
```

**Key Insight:** This command documents BOTH MCP tools and CLI fallback patterns.

### Example 2: mpm-init (Complex routing with subcommands)

**File:** `src/claude_mpm/commands/mpm-init.md`

**Pattern:**
```markdown
# /mpm-init [update]

Initialize or intelligently update your project for optimal use with
Claude Code and Claude MPM using the Agentic Coder Optimizer agent.

## Usage

```
/mpm-init                      # Auto-detects and offers update or create
/mpm-init update               # Lightweight update based on recent git activity
/mpm-init context              # Intelligent context analysis from git history
/mpm-init context --days 14    # Analyze last 14 days of git history
/mpm-init resume               # Resume from stop event logs (NEW)
```

## Implementation

**IMPORTANT**: This slash command accepts an optional `update` argument.

**Argument Processing**:
- When you type `/mpm-init update`, Claude executes `claude-mpm mpm-init --quick-update`
- When you type `/mpm-init` (no argument), Claude executes standard mode

This command routes between different modes:

### Context Analysis Commands

**`/mpm-init context` - Delegates to PM**:
```bash
claude-mpm mpm-init context --days 7
```

**`/mpm-init catchup` - Direct CLI execution**:
```bash
claude-mpm mpm-init catchup
```
```

**Key Features:**
- Optional positional argument (`update`)
- Multiple subcommands (`context`, `catchup`, `resume`)
- Flag arguments (`--days`, `--quick-update`)
- Different delegation patterns (PM vs direct CLI)

---

## 6. Integration Points

### How Slash Commands Interact with Agents

**Pattern 1: PM Delegation**
```markdown
## Implementation

This slash command delegates to the **PM agent** to collect status information.

When you run `/mpm-status`, the PM will:
1. Check Claude MPM version and installation
2. Verify Python environment and dependencies
3. Query active services
```

**What this means:**
- Slash command instructs Claude to delegate to PM
- PM agent has instructions to handle `/mpm-status`
- PM executes `claude-mpm <command>` or uses MCP tools

**Pattern 2: Direct CLI Execution**
```markdown
**`/mpm-init catchup` - Direct CLI execution**:
```bash
claude-mpm mpm-init catchup
```

This executes directly via CLI without agent delegation.
```

**What this means:**
- Slash command tells Claude to run CLI directly
- No PM delegation
- Output displayed to user

### How Commands Access Project Context

**Not applicable - commands are documentation only.**

Actual context access happens in:
1. **CLI command handlers:** Read from project files, git, config
2. **MCP tools:** Access project state via MCP server
3. **PM agent:** Has project context from CLAUDE.md and memory

### Error Handling Approach

**Documentation-level:**
```markdown
## Tips

- **MCP-first**: Prefer mcp-ticketer MCP tools when available
- **Automatic fallback**: System gracefully falls back to aitrackdown CLI
- **Check availability**: Detection happens automatically
```

**Actual error handling:**
- In CLI command handlers (try/except, validation)
- In MCP tool responses
- In PM agent logic

---

## 7. CLI Backend Architecture

### Parser Structure

**Location:** `/src/claude_mpm/cli/parsers/`

**Example: tickets_parser.py**
```python
def add_tickets_subparser(subparsers) -> argparse.ArgumentParser:
    """Add the tickets subparser with all ticket management commands."""

    tickets_parser = subparsers.add_parser(
        CLICommands.TICKETS.value,
        help="Manage tickets and tracking"
    )

    tickets_subparsers = tickets_parser.add_subparsers(
        dest="tickets_command",
        help="Ticket commands",
        metavar="SUBCOMMAND"
    )

    # Create ticket subcommand
    create_ticket_parser = tickets_subparsers.add_parser(
        TicketCommands.CREATE.value,
        help="Create a new ticket"
    )
    create_ticket_parser.add_argument("title", help="Ticket title")
    create_ticket_parser.add_argument(
        "-t", "--type",
        default="task",
        choices=["task", "bug", "feature", "issue", "epic"],
        help="Ticket type (default: task)"
    )
    # ... more arguments
```

### Command Handler Structure

**Location:** `/src/claude_mpm/cli/commands/`

**Example: tickets.py**
```python
class TicketsCommand(BaseCommand):
    def __init__(self):
        super().__init__("tickets")
        self.crud_service = TicketCRUDService()
        self.formatter = TicketFormatterService()
        self.validator = TicketValidationService()

    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments."""
        if not hasattr(args, "tickets_command"):
            return "No tickets subcommand specified"
        return None

    def run(self, args) -> CommandResult:
        """Execute the tickets command."""
        command_map = {
            TicketCommands.CREATE.value: self._create_ticket,
            TicketCommands.LIST.value: self._list_tickets,
            TicketCommands.VIEW.value: self._view_ticket,
            # ... more commands
        }
        return command_map[args.tickets_command](args)

    def _create_ticket(self, args) -> CommandResult:
        """Create a new ticket using the CRUD service."""
        result = self.crud_service.create_ticket(
            title=args.title,
            ticket_type=args.type,
            priority=args.priority,
            description=args.description,
            tags=args.tags
        )
        # Format and return result
```

### MPM Init Handler Structure

**Location:** `/src/claude_mpm/cli/commands/mpm_init_handler.py`

```python
def manage_mpm_init(args):
    """Handle mpm-init command execution."""
    from .mpm_init.core import MPMInitCommand

    # Handle context subcommands
    subcommand = getattr(args, "subcommand", None)

    if subcommand in ("context", "resume"):
        # Show deprecation warning for 'resume'
        if subcommand == "resume":
            console.print("[yellow]Warning: 'resume' is deprecated[/yellow]")

        project_path = Path(args.project_path) if hasattr(args, "project_path") else Path.cwd()
        command = MPMInitCommand(project_path)

        result = command.handle_context(
            session_id=getattr(args, "session_id", None),
            days=getattr(args, "days", 7)
        )

        return 0 if result.get("status") == OperationResult.SUCCESS else 1

    if subcommand == "pause":
        # Handle pause subcommand
        pause_manager = SessionPauseManager(project_path)
        session_id = pause_manager.create_pause_session(...)
        return 0
```

---

## 8. Recommendations for `/mpm-ticket`

### Option 1: Standalone Command (Recommended)

**Create:** `src/claude_mpm/commands/mpm-ticket.md`

**Rationale:**
- Clear, focused purpose
- Easy to discover (`/mpm-ticket` vs `/mpm-tickets ticket`)
- Follows pattern of other single-purpose commands

**Structure:**
```markdown
# /mpm-ticket [ticket-id]

Quick ticket operations - create, view, update, or transition tickets

## Usage

```
/mpm-ticket                          # Interactive ticket creation
/mpm-ticket ISS-123                  # View ticket details
/mpm-ticket ISS-123 in-progress      # Transition ticket
/mpm-ticket create "Fix bug"         # Create new ticket
```

## Description

This slash command provides quick access to common ticket operations through
the PM agent, using mcp-ticketer MCP tools when available.

## Implementation

This slash command delegates to the **PM agent** for ticket operations.

The PM will:
1. Detect if mcp-ticketer MCP tools are available
2. Use MCP tools for primary operations (preferred)
3. Fall back to aitrackdown CLI if MCP unavailable
4. Format and present results

## Commands

### View Ticket
```
/mpm-ticket ISS-123
```
Displays ticket details using `mcp__mcp-ticketer__ticket_read`.

### Create Ticket
```
/mpm-ticket create "Bug: Login fails"
/mpm-ticket create "Bug: Login fails" --priority high
```
Creates ticket using `mcp__mcp-ticketer__ticket_create`.

### Transition Ticket
```
/mpm-ticket ISS-123 in-progress
/mpm-ticket ISS-123 done
```
Updates ticket state using `mcp__mcp-ticketer__ticket_transition`.

### Update Ticket
```
/mpm-ticket ISS-123 update --priority high
/mpm-ticket ISS-123 assign user@example.com
```

## MCP Tools Used

- `mcp__mcp-ticketer__ticket_read` - View ticket details
- `mcp__mcp-ticketer__ticket_create` - Create new ticket
- `mcp__mcp-ticketer__ticket_update` - Update ticket fields
- `mcp__mcp-ticketer__ticket_transition` - Change ticket state
- `mcp__mcp-ticketer__ticket_assign` - Assign ticket to user

## Fallback Behavior

When MCP tools unavailable, falls back to:
```bash
aitrackdown show ISS-123
aitrackdown create issue "Title" --priority high
aitrackdown transition ISS-123 in-progress
```

## Related Commands

- `/mpm-tickets`: Full ticket management interface
- `/mpm-status`: Check ticket system status
```

### Option 2: Extension to Existing mpm-tickets

**Modify:** `src/claude_mpm/commands/mpm-tickets.md`

**Add section:**
```markdown
## Quick Operations (Alternative Syntax)

For common operations, you can use the shorter `/mpm-ticket` command:

```
/mpm-ticket ISS-123              # View ticket
/mpm-ticket create "Title"       # Create ticket
/mpm-ticket ISS-123 done         # Transition ticket
```

This delegates to the same MCP tools but with simplified syntax.
```

**Rationale:**
- Consolidates ticket commands
- Avoids command proliferation
- User must remember two commands instead of one

**Downside:**
- Less discoverable
- Requires explanation of relationship

### Recommended Approach: Option 1

**Why:**
1. **Discoverability:** `/mpm-ticket` is more intuitive than remembering it's shorthand for `/mpm-tickets`
2. **Focused:** Each command has clear, distinct purpose
3. **Pattern consistency:** Similar to `mpm-status`, `mpm-doctor` (single-purpose commands)
4. **Implementation simplicity:** Standalone markdown file easier to maintain
5. **User experience:** Quick commands should be quick to type AND discover

---

## 9. Implementation Checklist for `/mpm-ticket`

### File Creation
- [ ] Create `src/claude_mpm/commands/mpm-ticket.md`
- [ ] Follow structure pattern from `mpm-status.md`
- [ ] Document MCP tools used
- [ ] Include fallback CLI commands
- [ ] Add usage examples
- [ ] Include expected output samples

### Deployment
- [ ] File automatically deployed on next `claude-mpm run`
- [ ] OR manually deploy: `CommandDeploymentService().deploy_commands(force=True)`
- [ ] Verify file appears in `~/.claude/commands/mpm-ticket.md`

### Documentation Integration
- [ ] Update `mpm.md` to list `/mpm-ticket` command
- [ ] Add to `mpm-help.md` command index
- [ ] Cross-reference in `mpm-tickets.md`

### Testing
- [ ] Test file deployment
- [ ] Test Claude's interpretation of markdown
- [ ] Test argument parsing (if any)
- [ ] Test MCP tool integration
- [ ] Test fallback behavior

### No Backend Code Required
- [ ] **Important:** No Python code needed for slash command
- [ ] PM agent handles delegation via existing MCP tools
- [ ] CLI backend (`claude-mpm tickets`) already exists
- [ ] All logic already implemented in services

---

## 10. Key Insights

### What Slash Commands ARE
✅ **Markdown documentation files**
✅ **Instructions for Claude on what CLI to execute**
✅ **Context about command purpose and usage**
✅ **Examples and expected outputs**

### What Slash Commands ARE NOT
❌ **Executable code**
❌ **Argument parsers**
❌ **Business logic**
❌ **Error handlers**

### Critical Pattern
```
User types: /mpm-status
     ↓
Claude reads: ~/.claude/commands/mpm-status.md
     ↓
Claude interprets: "This delegates to PM agent"
     ↓
Claude delegates: @pm "Show MPM status"
     ↓
PM executes: claude-mpm status OR uses MCP tools
     ↓
PM returns: Formatted status output
```

### For `/mpm-ticket`
```
User types: /mpm-ticket ISS-123
     ↓
Claude reads: ~/.claude/commands/mpm-ticket.md
     ↓
Claude interprets: "View ticket using mcp__mcp-ticketer__ticket_read"
     ↓
Claude delegates: @pm "View ticket ISS-123"
     ↓
PM uses: mcp__mcp-ticketer__ticket_read(ticket_id="ISS-123")
     ↓
PM returns: Formatted ticket details
```

---

## 11. File Paths Summary

### Evidence Files
| File | Purpose | Evidence |
|------|---------|----------|
| `src/claude_mpm/commands/*.md` | Source slash command files | 16 files found |
| `~/.claude/commands/*.md` | Deployed slash command files | 15 files deployed |
| `src/claude_mpm/services/command_deployment_service.py` | Deployment service | Lines 1-182 |
| `src/claude_mpm/cli/commands/tickets.py` | Tickets CLI handler | Lines 1-547 |
| `src/claude_mpm/cli/parsers/tickets_parser.py` | Tickets argument parser | Lines 1-150+ |
| `src/claude_mpm/cli/commands/mpm_init_handler.py` | MPM init handler | Lines 1-100+ |

### Example Code Snippets

**Deployment Service (command_deployment_service.py:42-114):**
```python
def deploy_commands(self, force: bool = False) -> Dict[str, Any]:
    """Deploy MPM slash commands to user's Claude configuration."""
    # Create target directory
    self.target_dir.mkdir(parents=True, exist_ok=True)

    # Get all .md files
    command_files = list(self.source_dir.glob("*.md"))

    # Deploy each file
    for source_file in command_files:
        target_file = self.target_dir / source_file.name

        # Skip if target is newer (unless force)
        if target_file.exists() and not force and \
           source_file.stat().st_mtime <= target_file.stat().st_mtime:
            continue

        # Copy file
        shutil.copy2(source_file, target_file)
        result["deployed"].append(source_file.name)
```

**Startup Deployment (run.py:referenced in grep):**
```python
from ...services.command_deployment_service import deploy_commands_on_startup

deploy_commands_on_startup(force=False)
logger.debug(f"Failed to deploy MPM commands (non-critical): {e}")
```

**Tickets CLI Handler (tickets.py:56-76):**
```python
def run(self, args) -> CommandResult:
    """Execute the tickets command."""
    command_map = {
        TicketCommands.CREATE.value: self._create_ticket,
        TicketCommands.LIST.value: self._list_tickets,
        TicketCommands.VIEW.value: self._view_ticket,
        TicketCommands.UPDATE.value: self._update_ticket,
        TicketCommands.CLOSE.value: self._close_ticket,
        TicketCommands.DELETE.value: self._delete_ticket,
        TicketCommands.SEARCH.value: self._search_tickets,
        TicketCommands.COMMENT.value: self._add_comment,
        TicketCommands.WORKFLOW.value: self._update_workflow,
    }

    if args.tickets_command in command_map:
        return command_map[args.tickets_command](args)
```

---

## Conclusion

Implementing `/mpm-ticket` requires:
1. **Single markdown file:** `src/claude_mpm/commands/mpm-ticket.md`
2. **No Python code:** All backend already exists
3. **Clear documentation:** Usage, MCP tools, examples, fallback
4. **Automatic deployment:** On next `claude-mpm run` or manual trigger

**Next Steps:**
1. Draft `mpm-ticket.md` content
2. Review with team
3. Deploy to source directory
4. Test with Claude Code
5. Update related documentation

**Total Implementation Effort:** 1-2 hours (mostly writing documentation)
