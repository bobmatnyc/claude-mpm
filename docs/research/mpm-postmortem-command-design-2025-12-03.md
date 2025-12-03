# `/mpm-postmortem` Command Architecture Design

**Research Date:** 2025-12-03
**Researcher:** Claude Code (Research Agent)
**Status:** Design Proposal

## Executive Summary

This document defines the architecture for a new `/mpm-postmortem` slash command that performs automated post-session analysis of error logs to suggest improvements to scripts, skills, and agent instructions. The command will analyze session logs, categorize errors by source, and generate improvement proposals with the option to automatically fix local issues or create PRs for agent improvements.

**Key Features:**
- Automatic error collection from session logs
- Intelligent categorization (script/skill/agent/user code)
- Root cause analysis with improvement suggestions
- Automated fixes for scripts and skills
- PR creation workflow for agent improvements
- Dry-run mode for safety

**Token Budget:** ~5,000 tokens for analysis + ~3,000 tokens per improvement suggestion

---

## 1. Command Hierarchy & Placement

### 1.1 Slash Command Location

**File:** `src/claude_mpm/commands/mpm-postmortem.md`

**Command Structure:**
```yaml
---
namespace: mpm/system
command: postmortem
aliases: [mpm-postmortem]
migration_target: /mpm/system:postmortem
category: system
deprecated_aliases: []
description: Analyze session error logs and suggest improvements
---
```

### 1.2 CLI Implementation

**File:** `src/claude_mpm/cli/commands/postmortem.py`

The command follows the established pattern:
- Click command decorator
- Option parsing (--session, --type, --auto-fix, --dry-run)
- Delegation to service layer
- Rich console output

### 1.3 Service Layer

**File:** `src/claude_mpm/services/diagnostics/postmortem_service.py`

Core analysis logic:
- Error log collection
- Pattern matching and categorization
- Improvement suggestion generation
- Fix application coordination

---

## 2. Error Log Sources

### 2.1 Log Directory Structure

Based on codebase analysis, MPM stores logs in `.claude-mpm/logs/`:

```
.claude-mpm/logs/
├── mpm/              # MPM command logs (mpm_YYYYMMDD_HHMMSS.log)
├── startup/          # Startup logs (startup-YYYY-MM-DD-HH-MM-SS.log)
├── sessions/         # Session-specific logs
├── prompts/          # Prompt logs (agent requests/responses)
└── system/           # System-level logs
```

### 2.2 Session Identification

**Session ID Source:** `src/claude_mpm/services/session_manager.py`
- Uses `SessionManager` to track active sessions
- Session IDs are UUIDs stored in `~/.claude-mpm/sessions/active_sessions.json`
- Each session has metadata: created_at, last_used, use_count, agents_run, context

**Session Boundary Detection:**
- Current session: Retrieved from `SessionManager.get_session_by_id()`
- Session timeout: 30 minutes of inactivity (default)
- Session context types: "default" (interactive), "orchestration" (PM delegation)

### 2.3 Error Log Format

Based on `LogManager` implementation:

**MPM Logs** (`.claude-mpm/logs/mpm/mpm_YYYYMMDD_HHMMSS.log`):
```
[2025-12-03T14:09:01.123456+00:00] [ERROR] Agent deployment failed: FileNotFoundError
[2025-12-03T14:09:02.234567+00:00] [WARNING] Hook execution timeout: pre_tool_use
```

**Startup Logs** (`.claude-mpm/logs/startup/startup-YYYY-MM-DD-HH-MM-SS.log`):
- Contains agent deployment errors
- MCP configuration issues
- Memory loading failures
- Port binding conflicts

**Prompt Logs** (`.claude-mpm/logs/prompts/*.md` or `.json`):
```json
{
  "timestamp": "2025-12-03T14:09:03.345678+00:00",
  "type": "agent",
  "content": "...",
  "metadata": {
    "agent": "research",
    "error": "Tool execution failed: grep pattern invalid"
  },
  "session_id": "abc-def-123"
}
```

### 2.4 Error Classification Levels

**Error Severity** (from `ErrorHandler`):
- `DEBUG`: Diagnostic information (ignored by postmortem)
- `INFO`: Informational messages (ignored by postmortem)
- `WARNING`: Non-critical issues (analyzed if repeated)
- `ERROR`: Operation failures (always analyzed)
- `CRITICAL`: System failures (always analyzed)

**Error Types to Analyze:**
1. **Script Failures**: Shell command errors, syntax errors
2. **Skill Issues**: Skill loading failures, execution errors
3. **Agent Problems**: Instruction interpretation errors, tool misuse
4. **Infrastructure**: MCP failures, port conflicts, permission issues

---

## 3. Analysis Workflow

### 3.1 Error Collection Algorithm

```python
class PostmortemService:
    def collect_session_errors(self, session_id: str) -> List[ErrorRecord]:
        """
        Collect all errors from a session across multiple log sources.

        Steps:
        1. Query SessionManager for session metadata
        2. Calculate session time range (created_at to last_used)
        3. Scan logs in parallel:
           - MPM logs filtered by timestamp
           - Startup logs if session is recent (< 1 hour old)
           - Prompt logs filtered by session_id
        4. Parse log entries with regex patterns
        5. Deduplicate similar errors (within 5 seconds)
        6. Return structured ErrorRecord list
        """
```

**ErrorRecord Structure:**
```python
@dataclass
class ErrorRecord:
    timestamp: datetime
    severity: ErrorSeverity
    source: str  # "mpm", "startup", "agent_prompt", "hook"
    error_type: str  # "FileNotFoundError", "CommandFailed", etc.
    message: str
    context: Dict[str, Any]  # Stack trace, agent name, file path
    log_file: Path
    line_number: int
```

### 3.2 Error Categorization

**Category Detection Flow:**

```
Error Record
    |
    v
Check error_type and context
    |
    +-- Contains ".claude/agents/"? --> AGENT
    |
    +-- Contains ".claude/skills/"? --> SKILL
    |
    +-- Contains "scripts/"? --> SCRIPT
    |
    +-- Contains ".claude-mpm/" --> INFRASTRUCTURE
    |
    +-- Contains project files? --> USER_CODE
    |
    +-- Default --> OTHER
```

**Category Definitions:**

1. **SCRIPT**: Errors in user scripts or CLI commands
   - Detection: File path contains `scripts/`, shell command failures
   - Examples: `bash script.sh` failed, Python script syntax error

2. **SKILL**: Errors in Claude Code skills
   - Detection: File path contains `.claude/skills/`, skill loading failures
   - Examples: Skill not found, skill execution timeout

3. **AGENT**: Errors in MPM agent instructions
   - Detection: File path contains `.claude/agents/`, agent-specific failures
   - Examples: Agent tool misuse, instruction ambiguity

4. **INFRASTRUCTURE**: MPM system errors
   - Detection: MCP failures, port conflicts, permission issues
   - Examples: WebSocket port in use, memory loading error

5. **USER_CODE**: Errors in project code
   - Detection: File paths outside MPM directories
   - Examples: Test failures, build errors

### 3.3 Root Cause Analysis

**Pattern Matching for Common Issues:**

```python
ERROR_PATTERNS = {
    # Script Issues
    r"command not found": {
        "category": "SCRIPT",
        "root_cause": "Missing executable or command",
        "fix": "Install missing command or fix PATH"
    },
    r"syntax error.*\.sh": {
        "category": "SCRIPT",
        "root_cause": "Shell script syntax error",
        "fix": "Run shellcheck and fix syntax issues"
    },

    # Skill Issues
    r"Skill.*not found": {
        "category": "SKILL",
        "root_cause": "Skill not deployed or misconfigured",
        "fix": "Deploy skill or check skill manifest"
    },
    r"Skill.*execution timeout": {
        "category": "SKILL",
        "root_cause": "Skill operation took too long",
        "fix": "Optimize skill logic or increase timeout"
    },

    # Agent Issues
    r"Agent.*tool.*failed": {
        "category": "AGENT",
        "root_cause": "Agent misused tool or invalid parameters",
        "fix": "Update agent instructions with correct tool usage"
    },
    r"Agent.*insufficient context": {
        "category": "AGENT",
        "root_cause": "Agent instructions lack necessary context",
        "fix": "Add missing context to agent instructions"
    },

    # Infrastructure Issues
    r"Port \d+ .*in use": {
        "category": "INFRASTRUCTURE",
        "root_cause": "WebSocket port already bound",
        "fix": "Kill process on port or use --websocket-port"
    },
    r"Permission denied": {
        "category": "INFRASTRUCTURE",
        "root_cause": "File permission issue",
        "fix": "Check file permissions with ls -la"
    }
}
```

**Analysis Steps:**
1. Match error message against patterns
2. Extract file paths, line numbers, command names from context
3. Check if error is repeated (appears >2 times in session)
4. Correlate with recent changes (git diff if available)
5. Generate improvement suggestions with confidence scores

### 3.4 Improvement Suggestion Generation

**Suggestion Structure:**

```python
@dataclass
class ImprovementSuggestion:
    error_record: ErrorRecord
    category: str  # SCRIPT, SKILL, AGENT, INFRASTRUCTURE, USER_CODE
    root_cause: str
    suggested_fix: str
    affected_files: List[Path]
    confidence: float  # 0.0-1.0
    auto_fixable: bool
    fix_type: str  # "local", "pr", "manual"

    # For PRs
    pr_title: Optional[str] = None
    pr_body: Optional[str] = None
    pr_branch: Optional[str] = None
```

**Confidence Scoring:**

```python
def calculate_confidence(error_record: ErrorRecord, pattern_match: bool) -> float:
    confidence = 0.5  # Base confidence

    if pattern_match:
        confidence += 0.3  # Known error pattern

    if error_record.count > 2:
        confidence += 0.1  # Repeated error

    if error_record.context.get("stack_trace"):
        confidence += 0.1  # Has detailed context

    return min(confidence, 1.0)
```

---

## 4. Improvement Actions

### 4.1 Action Classification

**Decision Tree:**

```
Improvement Suggestion
    |
    v
Is category SCRIPT or SKILL?
    |-- YES --> Can fix locally
    |           |-- auto_fix=True --> Apply fix
    |           |-- auto_fix=False --> Preview fix
    |
    |-- NO --> Is category AGENT?
            |-- YES --> Check if from remote cache
            |           |-- Is git repo? --> Create PR workflow
            |           |-- Not git repo? --> Manual suggestion
            |
            |-- NO --> Is category USER_CODE?
                    |-- YES --> Suggest fix only (don't modify)
                    |
                    |-- NO --> INFRASTRUCTURE: Provide manual steps
```

### 4.2 Local Fix Application (Scripts & Skills)

**Script Fixes:**

```python
class ScriptFixer:
    def fix_command_not_found(self, error: ErrorRecord) -> bool:
        """
        Fix 'command not found' errors by:
        1. Detecting missing command from error message
        2. Checking if it's installable via common package managers
        3. Generating install script or updating PATH
        """
        command = extract_command_name(error.message)

        # Check common package managers
        if command in KNOWN_COMMANDS:
            install_cmd = KNOWN_COMMANDS[command]
            return self._add_install_step(error.context["file"], install_cmd)

        # Suggest PATH fix
        return self._suggest_path_addition(command)

    def fix_syntax_error(self, error: ErrorRecord) -> bool:
        """
        Fix shell script syntax errors by:
        1. Running shellcheck for detailed diagnostics
        2. Applying auto-fixable issues (quote variables, etc.)
        3. Reporting remaining issues to user
        """
        script_path = error.context["file"]
        shellcheck_result = run_shellcheck(script_path)

        for issue in shellcheck_result:
            if issue.auto_fixable:
                apply_fix(script_path, issue)

        return True
```

**Skill Fixes:**

```python
class SkillFixer:
    def fix_skill_not_found(self, error: ErrorRecord) -> bool:
        """
        Fix skill not found errors by:
        1. Checking if skill exists in skill repository
        2. Deploying skill if found
        3. Suggesting alternative skills if not found
        """
        skill_name = extract_skill_name(error.message)

        # Check if skill is available
        skill_repo = SkillRepository()
        if skill_repo.exists(skill_name):
            return skill_repo.deploy(skill_name)

        # Suggest similar skills
        similar = skill_repo.find_similar(skill_name)
        self.logger.info(f"Skill '{skill_name}' not found. Similar: {similar}")
        return False

    def fix_execution_timeout(self, error: ErrorRecord) -> bool:
        """
        Fix skill execution timeout by:
        1. Analyzing skill config for timeout settings
        2. Increasing timeout if reasonable
        3. Suggesting skill optimization
        """
        skill_path = error.context["skill_path"]
        config = load_skill_config(skill_path)

        current_timeout = config.get("timeout", 30)
        new_timeout = min(current_timeout * 2, 300)  # Max 5 minutes

        config["timeout"] = new_timeout
        save_skill_config(skill_path, config)

        return True
```

**Verification After Fix:**

```python
def verify_fix(fix_result: FixResult) -> bool:
    """
    Verify that fix actually resolved the issue.

    Steps:
    1. Re-run failed command/operation
    2. Check for same error pattern
    3. Return success/failure
    """
    if fix_result.category == "SCRIPT":
        # Re-run script
        result = subprocess.run(fix_result.command, capture_output=True)
        return result.returncode == 0

    elif fix_result.category == "SKILL":
        # Re-test skill
        from claude_mpm.services.skills import SkillManager
        manager = SkillManager()
        return manager.test_skill(fix_result.skill_name)

    return False
```

### 4.3 Agent Improvement PR Workflow

**PR Creation Flow:**

```
Agent Error Detected
    |
    v
Check if agent is from cache
    |-- ~/.claude-mpm/cache/remote-agents/*/agents/*.md
    |
    v
Verify git repository
    |-- CacheGitManager.is_git_repo()
    |-- Check remote URL contains "claude-mpm-agents"
    |
    v
Create improvement branch
    |-- Branch name: "improve/{agent-name}-{issue-summary}"
    |-- Example: "improve/research-error-handling"
    |
    v
Generate improvement
    |-- Analyze error context
    |-- Draft instruction improvements
    |-- Add error handling examples
    |
    v
Commit changes
    |-- Message: "feat(agent): improve {agent} {description}"
    |-- Include error context in commit body
    |
    v
Create PR
    |-- Use GitHubCLIService.create_pr()
    |-- PR title: "feat({agent}): {improvement-summary}"
    |-- PR body: Detailed rationale with error examples
    |
    v
Notify user
    |-- Display PR URL
    |-- Explain what was changed
```

**PR Template:**

```markdown
## Problem

This PR addresses the following error observed during session {session_id}:

```
{error_message}
```

**Error Context:**
- Timestamp: {timestamp}
- Session: {session_id}
- Agent: {agent_name}
- Tool: {tool_name}
- Error Type: {error_type}

## Root Cause

{root_cause_analysis}

## Proposed Solution

{improvement_description}

**Changes:**
1. {change_1}
2. {change_2}

## Testing

- [ ] Tested improvement in local environment
- [ ] Verified error no longer occurs
- [ ] Checked for regression in other scenarios

## Generated By

This PR was automatically generated by Claude MPM `/mpm-postmortem` command.

Session: {session_id}
Timestamp: {timestamp}
```

**Implementation:**

```python
class AgentImprovementService:
    def create_agent_improvement_pr(
        self,
        suggestion: ImprovementSuggestion,
        session_id: str
    ) -> Tuple[bool, str]:
        """
        Create PR for agent improvement.

        Returns:
            (success, pr_url_or_error_message)
        """
        # 1. Verify agent is from remote cache
        agent_path = suggestion.affected_files[0]
        if not self._is_remote_agent(agent_path):
            return False, "Agent is not from remote cache"

        # 2. Initialize git managers
        cache_manager = CacheGitManager(agent_path.parent.parent)
        github_service = GitHubCLIService()

        if not cache_manager.is_git_repo():
            return False, "Agent cache is not a git repository"

        # 3. Check authentication
        if not github_service.is_authenticated():
            return False, github_service.get_installation_instructions()

        # 4. Create improvement branch
        branch_name = f"improve/{suggestion.agent_name}-{suggestion.issue_slug}"
        success = cache_manager.create_branch(branch_name)
        if not success:
            return False, "Failed to create branch"

        # 5. Apply improvements to agent file
        self._apply_agent_improvements(agent_path, suggestion)

        # 6. Commit changes
        commit_msg = self._generate_commit_message(suggestion, session_id)
        cache_manager.commit(commit_msg, [agent_path])

        # 7. Push branch
        cache_manager.push(branch_name)

        # 8. Create PR
        pr_body = self._generate_pr_body(suggestion, session_id)
        pr_url = github_service.create_pr(
            title=suggestion.pr_title,
            body=pr_body,
            base="main",
            head=branch_name
        )

        return True, pr_url

    def _apply_agent_improvements(
        self,
        agent_path: Path,
        suggestion: ImprovementSuggestion
    ) -> None:
        """
        Apply improvements to agent markdown file.

        Improvements might include:
        - Adding error handling examples
        - Clarifying ambiguous instructions
        - Adding tool usage examples
        - Updating context requirements
        """
        agent_content = agent_path.read_text()

        # Parse agent markdown (frontmatter + content)
        frontmatter, instructions = parse_agent_file(agent_content)

        # Apply improvements based on error type
        if suggestion.error_type == "tool_misuse":
            instructions = self._add_tool_examples(instructions, suggestion)
        elif suggestion.error_type == "insufficient_context":
            instructions = self._add_context_guidance(instructions, suggestion)
        elif suggestion.error_type == "ambiguous_instruction":
            instructions = self._clarify_instructions(instructions, suggestion)

        # Reconstruct agent file
        improved_content = format_agent_file(frontmatter, instructions)
        agent_path.write_text(improved_content)
```

### 4.4 User Code Suggestions (Non-Modifying)

For errors in user code, provide suggestions without modifying:

```python
class UserCodeAnalyzer:
    def suggest_improvements(self, error: ErrorRecord) -> Dict[str, Any]:
        """
        Analyze user code errors and provide suggestions.

        Returns suggestions in structured format:
        - Problem description
        - Suggested fix
        - Example code (if applicable)
        - Related documentation links
        """
        return {
            "problem": self._describe_problem(error),
            "suggestion": self._generate_suggestion(error),
            "example": self._provide_example(error),
            "documentation": self._find_relevant_docs(error),
            "auto_fixable": False  # Never auto-fix user code
        }
```

---

## 5. Command Interface Design

### 5.1 Command Syntax

```bash
# Basic usage - analyze current session
/mpm-postmortem

# Analyze specific session
/mpm-postmortem --session <session_id>

# Filter by category
/mpm-postmortem --type scripts,skills,agents

# Dry-run mode (preview fixes without applying)
/mpm-postmortem --dry-run

# Auto-fix local issues (scripts, skills)
/mpm-postmortem --auto-fix

# Create PRs for agent improvements
/mpm-postmortem --create-prs

# Combine options
/mpm-postmortem --type agents --create-prs --dry-run
```

### 5.2 Option Definitions

**`--session <session_id>`**
- Type: String (UUID)
- Default: Current session (from SessionManager)
- Purpose: Analyze specific session instead of current

**`--type <categories>`**
- Type: Comma-separated list
- Choices: scripts, skills, agents, infrastructure, user_code, all
- Default: all
- Purpose: Filter errors by category

**`--auto-fix`**
- Type: Flag (boolean)
- Default: False
- Purpose: Automatically apply fixes to scripts and skills
- Safety: Only fixes SCRIPT and SKILL categories

**`--create-prs`**
- Type: Flag (boolean)
- Default: False
- Purpose: Create PRs for agent improvements
- Requires: Git authentication, write access to agent repo

**`--dry-run`**
- Type: Flag (boolean)
- Default: False (but recommended to use)
- Purpose: Preview changes without applying
- Effect: Shows what would be done without modifying files

**`--output <format>`**
- Type: Choice
- Choices: table, json, markdown
- Default: table
- Purpose: Format output for different use cases

**`--min-confidence <float>`**
- Type: Float (0.0-1.0)
- Default: 0.6
- Purpose: Filter suggestions by confidence score

### 5.3 Output Format

**Table Format (Default):**

```
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Category     ┃ Error Type   ┃ Occurrences  ┃ Confidence   ┃ Fix Type     ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ SCRIPT       │ CommandFailed│ 3            │ 0.85         │ auto-fix     │
│ AGENT        │ ToolMisuse   │ 5            │ 0.90         │ pr-required  │
│ SKILL        │ NotFound     │ 1            │ 0.75         │ auto-fix     │
└──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘

Analysis Summary:
- Total errors: 9
- Auto-fixable: 4 (SCRIPT: 3, SKILL: 1)
- PR required: 5 (AGENT: 5)
- Manual intervention: 0

Recommendations:
1. ✅ Fixed 3 script errors (auto-fix enabled)
2. 📝 Created PR for agent improvements: https://github.com/bobmatnyc/claude-mpm-agents/pull/123
3. ⚠️  1 skill needs deployment: 'data-analysis'

Next Steps:
- Review PR: https://github.com/bobmatnyc/claude-mpm-agents/pull/123
- Deploy missing skill: /mpm-skills deploy data-analysis
```

**JSON Format:**

```json
{
  "session_id": "abc-def-123",
  "analysis_timestamp": "2025-12-03T14:30:00Z",
  "summary": {
    "total_errors": 9,
    "by_category": {
      "SCRIPT": 3,
      "AGENT": 5,
      "SKILL": 1
    },
    "auto_fixed": 4,
    "pr_created": 1,
    "manual_required": 0
  },
  "suggestions": [
    {
      "id": "suggestion-1",
      "category": "SCRIPT",
      "error_type": "CommandNotFound",
      "root_cause": "Missing executable: shellcheck",
      "confidence": 0.85,
      "fix_type": "auto-fix",
      "status": "fixed",
      "affected_files": ["scripts/lint.sh"]
    }
  ],
  "pull_requests": [
    {
      "agent": "research",
      "title": "feat(research): improve error handling for grep tool",
      "url": "https://github.com/bobmatnyc/claude-mpm-agents/pull/123",
      "branch": "improve/research-grep-handling"
    }
  ]
}
```

---

## 6. Integration Points

### 6.1 Session Management System

**Integration with `SessionManager`:**

```python
from claude_mpm.services.session_manager import SessionManager

class PostmortemService:
    def __init__(self):
        self.session_manager = SessionManager()

    def get_current_session(self) -> Optional[str]:
        """Get current session ID from SessionManager."""
        return self.session_manager.get_last_interactive_session()

    def get_session_timerange(self, session_id: str) -> Tuple[datetime, datetime]:
        """Get session start and end times."""
        session_data = self.session_manager.get_session_by_id(session_id)
        if not session_data:
            raise ValueError(f"Session not found: {session_id}")

        start_time = datetime.fromisoformat(session_data["created_at"])
        end_time = datetime.fromisoformat(session_data["last_used"])

        return start_time, end_time
```

### 6.2 Error Tracking System

**Integration with `ErrorHandler` and `HookErrorMemory`:**

```python
from claude_mpm.core.error_handler import ErrorHandler
from claude_mpm.core.hook_error_memory import HookErrorMemory

class PostmortemService:
    def collect_tracked_errors(self, session_id: str) -> List[ErrorRecord]:
        """
        Collect errors from existing error tracking systems.

        Sources:
        1. ErrorHandler global instance (in-memory errors)
        2. HookErrorMemory (.claude-mpm/hook_errors.json)
        3. Log files (filesystem-based)
        """
        errors = []

        # 1. Get errors from ErrorHandler
        error_handler = ErrorHandler()
        handler_errors = error_handler.get_error_history(limit=100)
        errors.extend(self._convert_handler_errors(handler_errors))

        # 2. Get errors from HookErrorMemory
        hook_memory = HookErrorMemory()
        hook_errors = hook_memory.get_error_summary()
        errors.extend(self._convert_hook_errors(hook_errors))

        # 3. Get errors from log files
        log_errors = self._parse_log_files(session_id)
        errors.extend(log_errors)

        return errors
```

### 6.3 Git Operations

**Integration with `CacheGitManager` and `GitHubCLIService`:**

```python
from claude_mpm.services.agents.cache_git_manager import CacheGitManager
from claude_mpm.services.github.github_cli_service import GitHubCLIService

class AgentImprovementService:
    def __init__(self):
        cache_path = Path.home() / ".claude-mpm/cache/remote-agents"
        self.git_manager = CacheGitManager(cache_path)
        self.github_service = GitHubCLIService()

    def can_create_pr(self) -> Tuple[bool, str]:
        """
        Check if PR creation is possible.

        Returns:
            (can_create, reason_if_not)
        """
        if not self.git_manager.is_git_repo():
            return False, "Agent cache is not a git repository"

        if not self.github_service.is_gh_installed():
            return False, self.github_service.get_installation_instructions()

        if not self.github_service.is_authenticated():
            return False, "GitHub CLI not authenticated. Run: gh auth login"

        return True, "Ready to create PRs"
```

### 6.4 Agent Cache Management

**Integration with agent deployment system:**

```python
from claude_mpm.services.agents.remote_agent_discovery_service import (
    RemoteAgentDiscoveryService
)

class AgentAnalyzer:
    def __init__(self):
        self.discovery_service = RemoteAgentDiscoveryService()

    def is_remote_agent(self, agent_path: Path) -> bool:
        """Check if agent is from remote cache."""
        cache_dir = Path.home() / ".claude-mpm/cache/remote-agents"
        return str(agent_path).startswith(str(cache_dir))

    def get_agent_metadata(self, agent_path: Path) -> Dict[str, Any]:
        """Get agent metadata from discovery service."""
        agents = self.discovery_service.discover_agents()
        agent_name = agent_path.stem

        for agent in agents:
            if agent["name"] == agent_name:
                return agent

        return {}
```

---

## 7. File Structure and Implementation Plan

### 7.1 File Organization

```
src/claude_mpm/
├── commands/
│   └── mpm-postmortem.md                    # Slash command definition
│
├── cli/commands/
│   └── postmortem.py                         # CLI command implementation
│
├── services/
│   └── diagnostics/
│       ├── postmortem_service.py             # Core service
│       ├── error_collector.py                # Log parsing and error collection
│       ├── error_categorizer.py              # Error categorization logic
│       ├── improvement_analyzer.py           # Root cause analysis
│       ├── fixers/
│       │   ├── __init__.py
│       │   ├── script_fixer.py               # Script fix application
│       │   ├── skill_fixer.py                # Skill fix application
│       │   └── agent_improver.py             # Agent improvement PR creation
│       └── models/
│           ├── error_record.py               # ErrorRecord dataclass
│           └── improvement_suggestion.py     # ImprovementSuggestion dataclass
│
└── utils/
    └── log_parser.py                         # Log file parsing utilities
```

### 7.2 Implementation Phases

**Phase 1: Core Infrastructure (Week 1)**
- [ ] Create command file: `mpm-postmortem.md`
- [ ] Implement CLI command: `postmortem.py`
- [ ] Create service skeleton: `postmortem_service.py`
- [ ] Define data models: `error_record.py`, `improvement_suggestion.py`
- [ ] Implement log parsing: `log_parser.py`, `error_collector.py`

**Phase 2: Error Analysis (Week 2)**
- [ ] Implement error categorization: `error_categorizer.py`
- [ ] Build pattern matching for common errors
- [ ] Implement root cause analysis: `improvement_analyzer.py`
- [ ] Add confidence scoring algorithm
- [ ] Write unit tests for analysis logic

**Phase 3: Fix Application (Week 3)**
- [ ] Implement script fixer: `script_fixer.py`
- [ ] Implement skill fixer: `skill_fixer.py`
- [ ] Add verification logic for applied fixes
- [ ] Implement dry-run mode
- [ ] Write integration tests

**Phase 4: PR Workflow (Week 4)**
- [ ] Implement agent improver: `agent_improver.py`
- [ ] Integrate with `CacheGitManager`
- [ ] Integrate with `GitHubCLIService`
- [ ] Create PR template generator
- [ ] Add authentication checks
- [ ] Write end-to-end tests

**Phase 5: Polish & Documentation (Week 5)**
- [ ] Add rich console output
- [ ] Implement JSON and markdown output formats
- [ ] Write user documentation
- [ ] Add command examples
- [ ] Create troubleshooting guide
- [ ] Beta testing with real sessions

### 7.3 Key Classes

**PostmortemService (Main Orchestrator):**

```python
class PostmortemService:
    """
    Main service for postmortem analysis.

    Orchestrates:
    - Error collection from logs
    - Error categorization and analysis
    - Improvement suggestion generation
    - Fix application coordination
    """

    def __init__(self):
        self.error_collector = ErrorCollector()
        self.categorizer = ErrorCategorizer()
        self.analyzer = ImprovementAnalyzer()
        self.script_fixer = ScriptFixer()
        self.skill_fixer = SkillFixer()
        self.agent_improver = AgentImprover()

    def analyze_session(
        self,
        session_id: Optional[str] = None,
        categories: Optional[List[str]] = None,
        auto_fix: bool = False,
        create_prs: bool = False,
        dry_run: bool = False
    ) -> PostmortemResult:
        """
        Perform postmortem analysis on session errors.

        Returns:
            PostmortemResult with summary and suggestions
        """
```

**ErrorCollector:**

```python
class ErrorCollector:
    """
    Collects errors from multiple log sources.

    Responsibilities:
    - Parse log files with timestamp filtering
    - Deduplicate similar errors
    - Correlate errors across sources
    - Build structured ErrorRecord list
    """

    def collect_session_errors(
        self,
        session_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[ErrorRecord]:
        """Collect all errors within session timeframe."""
```

**ErrorCategorizer:**

```python
class ErrorCategorizer:
    """
    Categorizes errors by source type.

    Responsibilities:
    - File path analysis
    - Error type detection
    - Context extraction
    - Category assignment
    """

    def categorize(self, error: ErrorRecord) -> str:
        """Determine error category (SCRIPT/SKILL/AGENT/etc.)."""
```

**ImprovementAnalyzer:**

```python
class ImprovementAnalyzer:
    """
    Analyzes errors and generates improvement suggestions.

    Responsibilities:
    - Pattern matching against known issues
    - Root cause identification
    - Confidence scoring
    - Suggestion generation
    """

    def analyze(
        self,
        errors: List[ErrorRecord]
    ) -> List[ImprovementSuggestion]:
        """Generate improvement suggestions from errors."""
```

---

## 8. Risk Assessment and Safeguards

### 8.1 Safety Mechanisms

**Dry-Run by Default:**
- Command should suggest `--dry-run` on first use
- Show clear diff of proposed changes
- Require explicit `--auto-fix` flag

**Multi-Level Confirmation:**
```
┌─ Postmortem Analysis Complete ─────────────────────────────┐
│                                                             │
│ Found 3 auto-fixable issues:                                │
│   • scripts/lint.sh: Install shellcheck                     │
│   • .claude/skills/data-analysis: Deploy skill              │
│   • scripts/deploy.sh: Fix syntax error at line 42          │
│                                                             │
│ Apply fixes? [y/N]:                                         │
│                                                             │
│ Found 2 agent improvements requiring PRs:                   │
│   • research: Improve grep error handling                   │
│   • pm: Clarify delegation instructions                     │
│                                                             │
│ Create PRs? [y/N]:                                          │
└─────────────────────────────────────────────────────────────┘
```

**Rollback Support:**
```python
class FixApplicator:
    def apply_fix(self, suggestion: ImprovementSuggestion) -> bool:
        """
        Apply fix with rollback support.

        Steps:
        1. Create backup of files
        2. Apply changes
        3. Verify fix
        4. If verification fails, rollback
        """
        backup = self._create_backup(suggestion.affected_files)

        try:
            self._apply_changes(suggestion)

            if not self._verify_fix(suggestion):
                self._rollback(backup)
                return False

            return True

        except Exception as e:
            self._rollback(backup)
            raise
```

### 8.2 Potential Risks

**Risk 1: False Positives in Error Detection**
- **Mitigation:** Confidence scoring + manual review for low-confidence suggestions
- **Safeguard:** `--min-confidence` flag to filter suggestions

**Risk 2: Breaking Changes from Auto-Fixes**
- **Mitigation:** Comprehensive testing before applying fixes
- **Safeguard:** Dry-run mode, backups, rollback support

**Risk 3: Unauthorized PR Creation**
- **Mitigation:** Check GitHub authentication before operations
- **Safeguard:** Require explicit `--create-prs` flag, confirm before push

**Risk 4: Large PR Volume**
- **Mitigation:** Batch similar improvements into single PR
- **Safeguard:** Limit to 5 PRs per session, suggest manual review

**Risk 5: Log File Size**
- **Mitigation:** Stream processing for large files, limit to session timeframe
- **Safeguard:** Warn if log files >10MB, offer to filter by time

**Risk 6: Session ID Confusion**
- **Mitigation:** Display session metadata before analysis
- **Safeguard:** Confirm session ID if user-provided doesn't match current

### 8.3 Error Handling

**Graceful Degradation:**

```python
def analyze_session(self, session_id: str) -> PostmortemResult:
    """
    Analyze session with graceful error handling.

    If any component fails:
    1. Log detailed error
    2. Continue with remaining analysis
    3. Report partial results to user
    4. Include error in final report
    """
    result = PostmortemResult()

    try:
        errors = self.collect_errors(session_id)
        result.errors_collected = len(errors)
    except Exception as e:
        logger.error(f"Error collection failed: {e}")
        result.add_warning("Error collection partial or incomplete")
        errors = []  # Continue with empty list

    try:
        suggestions = self.analyze_errors(errors)
        result.suggestions = suggestions
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        result.add_error("Analysis failed, no suggestions generated")

    return result
```

**User Communication:**

```
⚠️  Warning: Some log files were inaccessible
    - /Users/user/.claude-mpm/logs/prompts/agent_20251203.json: Permission denied
    - Analysis may be incomplete

✓ Successfully analyzed:
    - MPM logs: 3 files
    - Startup logs: 1 file
    - Session logs: 2 files

ℹ️  Continuing with partial analysis...
```

---

## 9. Performance Considerations

### 9.1 Expected Performance

**Analysis Time Estimates:**

| Operation                  | Time (Typical) | Time (Large) |
|---------------------------|----------------|--------------|
| Session error collection  | 500ms          | 2s           |
| Log file parsing          | 100ms/file     | 500ms/file   |
| Error categorization      | 50ms/error     | 50ms/error   |
| Root cause analysis       | 200ms/error    | 500ms/error  |
| Suggestion generation     | 100ms/error    | 300ms/error  |
| Total (10 errors)         | ~3s            | ~8s          |

**Memory Usage:**

- Base: ~50MB (service initialization)
- Per error record: ~5KB
- Per log file: ~10MB (streaming, not all in memory)
- Total (typical session): ~100MB

### 9.2 Optimization Strategies

**Parallel Processing:**

```python
import concurrent.futures

class ErrorCollector:
    def collect_from_multiple_logs(
        self,
        log_files: List[Path],
        session_id: str
    ) -> List[ErrorRecord]:
        """
        Parse log files in parallel using ThreadPoolExecutor.
        """
        errors = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_file = {
                executor.submit(self._parse_log_file, f, session_id): f
                for f in log_files
            }

            for future in concurrent.futures.as_completed(future_to_file):
                try:
                    file_errors = future.result()
                    errors.extend(file_errors)
                except Exception as e:
                    logger.error(f"Failed to parse {future_to_file[future]}: {e}")

        return errors
```

**Caching:**

```python
from functools import lru_cache

class ImprovementAnalyzer:
    @lru_cache(maxsize=128)
    def _match_error_pattern(self, error_message: str) -> Optional[Pattern]:
        """
        Cache pattern matching results.

        Many errors have similar messages, caching reduces
        regex operations by ~70%.
        """
        for pattern, metadata in self.ERROR_PATTERNS:
            if re.search(pattern, error_message):
                return (pattern, metadata)
        return None
```

**Streaming for Large Files:**

```python
def parse_large_log_file(self, file_path: Path) -> Iterator[ErrorRecord]:
    """
    Stream log file line-by-line instead of loading entirely.

    Memory usage: O(1) instead of O(n) where n = file size
    """
    with file_path.open('r') as f:
        for line in f:
            if error_record := self._parse_log_line(line):
                yield error_record
```

---

## 10. Testing Strategy

### 10.1 Unit Tests

**Test Coverage Areas:**

1. **Log Parsing:**
   - Test parsing of each log format (MPM, startup, prompts)
   - Test timestamp filtering
   - Test malformed log handling

2. **Error Categorization:**
   - Test each category detection rule
   - Test edge cases (ambiguous paths)
   - Test multi-category scenarios

3. **Root Cause Analysis:**
   - Test pattern matching accuracy
   - Test confidence scoring
   - Test suggestion generation

4. **Fix Application:**
   - Test script fixes (mock file operations)
   - Test skill fixes (mock SkillManager)
   - Test rollback mechanism

### 10.2 Integration Tests

**Test Scenarios:**

1. **End-to-End Postmortem:**
   ```python
   def test_complete_postmortem_workflow():
       # Setup: Create mock session with errors
       session_id = create_mock_session_with_errors()

       # Execute: Run postmortem
       service = PostmortemService()
       result = service.analyze_session(
           session_id=session_id,
           auto_fix=True,
           dry_run=False
       )

       # Assert: Verify fixes were applied
       assert result.errors_collected > 0
       assert result.suggestions_generated > 0
       assert result.fixes_applied > 0
   ```

2. **PR Creation Workflow:**
   ```python
   def test_agent_improvement_pr_creation():
       # Setup: Mock git repo and GitHub CLI
       setup_mock_git_repo()
       setup_mock_gh_cli()

       # Execute: Create PR
       improver = AgentImprover()
       success, pr_url = improver.create_pr(mock_suggestion)

       # Assert: Verify PR was created
       assert success
       assert "github.com" in pr_url
   ```

### 10.3 Manual Testing Checklist

- [ ] Run with no errors (verify graceful handling)
- [ ] Run with script errors (verify auto-fix)
- [ ] Run with skill errors (verify deployment)
- [ ] Run with agent errors (verify PR creation)
- [ ] Test dry-run mode (verify no modifications)
- [ ] Test with invalid session ID (verify error message)
- [ ] Test with unauthenticated GitHub (verify helpful message)
- [ ] Test with large log files (verify performance)

---

## 11. Documentation Requirements

### 11.1 User Documentation

**Command Help (`/mpm-postmortem --help`):**

```
Usage: /mpm-postmortem [OPTIONS]

Analyze session error logs and suggest improvements to scripts, skills, and
agent instructions.

Options:
  --session TEXT           Session ID to analyze (default: current)
  --type TEXT             Filter by category: scripts,skills,agents,all
  --auto-fix              Automatically apply fixes (scripts/skills only)
  --create-prs            Create PRs for agent improvements
  --dry-run               Preview changes without applying
  --output [table|json|markdown]
                          Output format (default: table)
  --min-confidence FLOAT  Minimum confidence for suggestions (default: 0.6)
  --help                  Show this message and exit

Examples:
  # Analyze current session (dry-run recommended)
  /mpm-postmortem --dry-run

  # Auto-fix script and skill issues
  /mpm-postmortem --auto-fix

  # Create PRs for agent improvements
  /mpm-postmortem --type agents --create-prs

  # Full analysis with auto-fix and PRs
  /mpm-postmortem --auto-fix --create-prs

Safety:
  - Always review dry-run output first
  - Fixes are backed up and can be rolled back
  - PRs require GitHub authentication and explicit --create-prs flag

Documentation:
  https://github.com/bobmatnyc/claude-mpm/docs/commands/mpm-postmortem.md
```

**README Section:**

```markdown
## `/mpm-postmortem` - Automated Session Analysis

Analyze errors from your Claude MPM session and get automated fixes or
improvement suggestions.

### What It Does

After a development session, `/mpm-postmortem` analyzes all errors that
occurred and:

1. **Scripts:** Fixes missing commands, syntax errors
2. **Skills:** Deploys missing skills, fixes configurations
3. **Agents:** Creates PRs with instruction improvements
4. **User Code:** Provides suggestions (never auto-modifies)

### Quick Start

```bash
# 1. Dry-run to see what would be fixed
/mpm-postmortem --dry-run

# 2. Apply fixes if they look good
/mpm-postmortem --auto-fix

# 3. Create PRs for agent improvements (requires GitHub auth)
/mpm-postmortem --create-prs
```

### Safety Features

- **Dry-run mode:** See changes before applying
- **Backups:** All modifications are backed up
- **Rollback:** Failed fixes are automatically reverted
- **Confirmation:** Prompts before creating PRs
```

### 11.2 Developer Documentation

**Architecture Documentation:**

```markdown
## Postmortem Service Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     PostmortemService                       │
│                   (Orchestrator/Facade)                     │
└─────────────────────────────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
│ ErrorCollector   │ │ Categorizer  │ │ FixApplicator    │
│                  │ │              │ │                  │
│ - Log parsing    │ │ - Pattern    │ │ - ScriptFixer    │
│ - Deduplication  │ │   matching   │ │ - SkillFixer     │
│ - Correlation    │ │ - Context    │ │ - AgentImprover  │
└──────────────────┘ └──────────────┘ └──────────────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │ ImprovementSuggestion │
                  │                  │
                  │ - Error record   │
                  │ - Root cause     │
                  │ - Confidence     │
                  │ - Fix type       │
                  └──────────────────┘
```

### Data Flow

1. **Collection Phase:** Scan logs → Parse entries → Build ErrorRecords
2. **Analysis Phase:** Match patterns → Determine categories → Score confidence
3. **Suggestion Phase:** Generate fixes → Prioritize by confidence
4. **Application Phase:** Apply fixes → Verify → Report results

### Extension Points

To add new error patterns:

```python
# In error_categorizer.py
ERROR_PATTERNS[r"your pattern"] = {
    "category": "SCRIPT",
    "root_cause": "Description",
    "fix": "Suggested fix"
}
```

To add new fix types:

```python
# Create new fixer in fixers/
class YourFixer:
    def can_fix(self, suggestion: ImprovementSuggestion) -> bool:
        return suggestion.category == "YOUR_CATEGORY"

    def apply_fix(self, suggestion: ImprovementSuggestion) -> bool:
        # Implementation
        pass
```
```

---

## 12. Future Enhancements

### 12.1 Phase 2 Features (Post-MVP)

**Machine Learning Integration:**
- Train classifier on error patterns
- Improve confidence scoring with historical data
- Suggest fixes based on similar past errors

**Pattern Learning:**
- Store successful fixes in knowledge base
- Learn from user corrections
- Suggest project-specific patterns

**Proactive Monitoring:**
- Real-time error detection during session
- Suggest fixes immediately when errors occur
- Background analysis while working

**Team Collaboration:**
- Share error patterns across team
- Collaborative fix review
- Team-wide improvement metrics

### 12.2 Advanced Analysis

**Dependency Analysis:**
- Detect cascading failures
- Identify root cause in chain of errors
- Suggest fixing root cause first

**Trend Detection:**
- Identify recurring issues over time
- Alert when error frequency increases
- Generate monthly improvement reports

**Integration with CI/CD:**
- Run postmortem on CI failures
- Create issues automatically
- Link to failed builds

---

## 13. Success Metrics

### 13.1 Key Performance Indicators

**Adoption Metrics:**
- Usage frequency (runs per week)
- Adoption rate (% of users who try it)
- Retention rate (% who use it regularly)

**Effectiveness Metrics:**
- Auto-fix success rate (% of fixes that work)
- PR acceptance rate (% of agent PRs merged)
- Time saved (errors fixed vs manual time)

**Quality Metrics:**
- False positive rate (bad suggestions)
- Confidence score accuracy
- User satisfaction (survey)

### 13.2 Target Goals (6 Months Post-Launch)

- **Adoption:** 60% of active MPM users
- **Auto-fix Success:** 80% of attempted fixes work
- **PR Acceptance:** 70% of agent PRs merged
- **Time Saved:** Average 15 minutes per session
- **User Satisfaction:** 4.2/5.0 rating

---

## 14. Appendices

### 14.1 Example Session Log

**`.claude-mpm/logs/mpm/mpm_20251203_143000.log`:**

```
[2025-12-03T14:30:15.123456+00:00] [INFO] Session started: abc-def-123
[2025-12-03T14:30:20.234567+00:00] [ERROR] Agent deployment failed: FileNotFoundError: .claude/agents/research.md
[2025-12-03T14:30:25.345678+00:00] [ERROR] Script execution failed: scripts/lint.sh: command not found: shellcheck
[2025-12-03T14:30:30.456789+00:00] [WARNING] Skill not found: data-analysis
[2025-12-03T14:31:15.567890+00:00] [ERROR] Agent tool misuse: research agent used grep with invalid regex pattern
[2025-12-03T14:32:00.678901+00:00] [INFO] Session ended: abc-def-123
```

### 14.2 Example PR Description

**Title:** `feat(research): improve grep tool error handling`

**Body:**

```markdown
## Problem

During session `abc-def-123`, the research agent encountered multiple failures
when using the grep tool with regex patterns:

```
[ERROR] Grep tool failed: invalid regex pattern '\d{3)-\d{4}'
        Missing closing bracket in pattern
```

**Error Context:**
- Session: abc-def-123
- Timestamp: 2025-12-03T14:31:15Z
- Agent: research
- Tool: grep
- Error Type: InvalidRegexPattern
- Occurrences: 5 times in session

## Root Cause

The research agent's instructions don't include:
1. Regex validation guidance
2. Error recovery procedures
3. Examples of correct regex escaping

This leads to repeated tool failures and wasted context tokens.

## Proposed Solution

This PR adds:

1. **Regex Validation Section:**
   - Common regex pitfalls
   - Escaping special characters
   - Testing patterns before use

2. **Error Recovery Guidance:**
   - What to do when grep fails
   - How to simplify patterns
   - When to use literal search instead

3. **Examples:**
   - Phone number patterns: `\d{3}-\d{4}`
   - Email patterns: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`
   - URL patterns: `https?://[^\s]+`

## Testing

- [x] Tested with problematic pattern from session
- [x] Verified error message is now helpful
- [x] Checked for regressions in other grep usage
- [x] Validated regex examples work correctly

## Generated By

This PR was automatically generated by Claude MPM `/mpm-postmortem` command.

**Session:** abc-def-123
**Timestamp:** 2025-12-03T14:35:00Z
**Analysis Confidence:** 0.92
**Error Occurrences:** 5

---

**Reviewer Notes:**
- This improvement directly addresses production errors
- Changes are conservative (documentation only)
- Similar patterns may benefit other agents
```

### 14.3 Error Pattern Database (Starter Set)

```python
ERROR_PATTERNS = {
    # Script Errors
    r"command not found: (\w+)": {
        "category": "SCRIPT",
        "root_cause": "Missing executable: {1}",
        "fix": "Install {1} or add to PATH",
        "confidence": 0.90,
        "auto_fixable": True
    },
    r"syntax error.*line (\d+)": {
        "category": "SCRIPT",
        "root_cause": "Shell script syntax error at line {1}",
        "fix": "Run shellcheck and fix syntax",
        "confidence": 0.85,
        "auto_fixable": True
    },

    # Skill Errors
    r"Skill '(\w+)' not found": {
        "category": "SKILL",
        "root_cause": "Skill {1} not deployed",
        "fix": "Deploy skill: /mpm-skills deploy {1}",
        "confidence": 0.95,
        "auto_fixable": True
    },
    r"Skill.*timeout after (\d+)s": {
        "category": "SKILL",
        "root_cause": "Skill execution timeout ({1}s)",
        "fix": "Increase timeout or optimize skill",
        "confidence": 0.75,
        "auto_fixable": True
    },

    # Agent Errors
    r"Agent.*invalid.*parameter.*'(\w+)'": {
        "category": "AGENT",
        "root_cause": "Agent provided invalid parameter: {1}",
        "fix": "Update agent instructions with correct parameters",
        "confidence": 0.88,
        "auto_fixable": False,  # Requires PR
        "pr_required": True
    },
    r"Agent.*grep.*invalid regex": {
        "category": "AGENT",
        "root_cause": "Agent used invalid regex pattern",
        "fix": "Add regex validation guidance to agent",
        "confidence": 0.92,
        "auto_fixable": False,
        "pr_required": True
    },

    # Infrastructure Errors
    r"Port (\d+) already in use": {
        "category": "INFRASTRUCTURE",
        "root_cause": "Port {1} conflict",
        "fix": "Kill process on port {1} or use different port",
        "confidence": 0.95,
        "auto_fixable": False
    },
    r"Permission denied: (.+)": {
        "category": "INFRASTRUCTURE",
        "root_cause": "File permission error: {1}",
        "fix": "Fix permissions: chmod u+w {1}",
        "confidence": 0.80,
        "auto_fixable": False
    }
}
```

---

## 15. Conclusion

The `/mpm-postmortem` command provides automated post-session analysis to improve MPM's reliability and reduce friction from repeated errors. By analyzing session logs, categorizing errors, and providing automated fixes or PRs, it creates a feedback loop that continuously improves the system.

**Key Strengths:**
1. **Automated:** Minimal manual intervention required
2. **Safe:** Dry-run, backups, rollback support
3. **Intelligent:** Pattern matching with confidence scoring
4. **Integrated:** Leverages existing MPM infrastructure
5. **Collaborative:** PR workflow enables community improvements

**Implementation Priority:**
1. Core log parsing and error collection (Phase 1)
2. Script and skill auto-fixes (Phase 2-3)
3. Agent improvement PRs (Phase 4)
4. Polish and documentation (Phase 5)

**Estimated Development Time:** 5 weeks (1 developer)

**Token Budget per Analysis:** ~8,000 tokens
- Error collection: ~2,000 tokens
- Analysis: ~3,000 tokens
- Suggestion generation: ~3,000 tokens

**Risk Level:** Medium (mitigated by dry-run, backups, manual review)

---

**Document Status:** Draft for Review
**Next Steps:**
1. Review with PM agent for feasibility
2. Get feedback on PR workflow approach
3. Create implementation tickets
4. Start Phase 1 development

**Contact:** Research Agent
**Date:** 2025-12-03
