#!/usr/bin/env python3
"""
Postmortem Analysis Service
============================

Analyzes session errors and suggests improvements across different code categories:
- Scripts: Test and fix in place
- Skills: Update skill files
- MPM Agents: Prepare PRs for remote repository
- User Code: Suggest only (no modification)

WHY: After a session with errors, we want to systematically analyze what went wrong,
categorize the issues, and take appropriate actions to prevent similar issues in
future sessions.

DESIGN DECISION: Leverages existing FailureTracker for error collection, adds
categorization by source (script/skill/agent/user), and provides action-specific
handling based on category.

Integration points:
- FailureTracker: Source of error data from session
- DiagnosticRunner: Validation of fixes
- Git cache: Agent improvement PR creation
- SessionManager: Session identification and context
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from claude_mpm.core.logging_utils import get_logger
from claude_mpm.services.memory.failure_tracker import FailureEvent, get_failure_tracker

logger = get_logger(__name__)


class ErrorCategory(Enum):
    """Categories for error source classification."""

    SCRIPT = "script"  # Framework scripts (.py files in scripts/)
    SKILL = "skill"  # Skill files (.md in skills/)
    AGENT = "agent"  # Agent instruction files (.md in agents/)
    USER_CODE = "user_code"  # User's project code
    UNKNOWN = "unknown"  # Unable to categorize


class ActionType(Enum):
    """Types of improvement actions."""

    AUTO_FIX = "auto_fix"  # Automatically fix and test
    UPDATE_FILE = "update_file"  # Update configuration/instruction file
    CREATE_PR = "create_pr"  # Create PR for agent improvements
    SUGGEST = "suggest"  # Provide suggestion only
    NONE = "none"  # No action available


@dataclass
class ErrorAnalysis:
    """Analysis result for a single error.

    Attributes:
        failure_event: The original failure event
        category: Error category (script/skill/agent/user)
        root_cause: Identified root cause description
        affected_file: File path if determinable
        action_type: Recommended action type
        fix_suggestion: Specific fix recommendation
        priority: Priority level (critical/high/medium/low)
        auto_fixable: Whether this can be automatically fixed
    """

    failure_event: FailureEvent
    category: ErrorCategory
    root_cause: str
    affected_file: Optional[Path] = None
    action_type: ActionType = ActionType.NONE
    fix_suggestion: str = ""
    priority: str = "medium"
    auto_fixable: bool = False
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class ImprovementAction:
    """Represents an action to take based on error analysis.

    Attributes:
        action_type: Type of action (auto_fix/update_file/create_pr/suggest)
        error_analysis: The error analysis this addresses
        description: Human-readable description
        commands: Shell commands to execute (for auto_fix)
        file_changes: Proposed file modifications
        pr_branch: Branch name for PR (if create_pr)
        pr_title: PR title (if create_pr)
        pr_body: PR description (if create_pr)
        status: Action status (pending/completed/failed)
    """

    action_type: ActionType
    error_analysis: ErrorAnalysis
    description: str
    commands: List[str] = field(default_factory=list)
    file_changes: Dict[str, str] = field(default_factory=dict)
    pr_branch: Optional[str] = None
    pr_title: Optional[str] = None
    pr_body: Optional[str] = None
    status: str = "pending"
    error_message: Optional[str] = None


@dataclass
class PostmortemReport:
    """Complete postmortem analysis report.

    Attributes:
        session_id: Session identifier
        start_time: Session start time
        duration_seconds: Session duration
        total_errors: Total error count
        analyses: List of error analyses
        actions: List of improvement actions
        stats: Summary statistics
    """

    session_id: str
    start_time: datetime
    duration_seconds: float
    total_errors: int
    analyses: List[ErrorAnalysis] = field(default_factory=list)
    actions: List[ImprovementAction] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)

    def get_actions_by_type(self, action_type: ActionType) -> List[ImprovementAction]:
        """Get all actions of a specific type.

        Args:
            action_type: Action type to filter by

        Returns:
            List of matching actions
        """
        return [a for a in self.actions if a.action_type == action_type]

    def get_analyses_by_category(self, category: ErrorCategory) -> List[ErrorAnalysis]:
        """Get all analyses for a specific category.

        Args:
            category: Error category to filter by

        Returns:
            List of matching analyses
        """
        return [a for a in self.analyses if a.category == category]


class PostmortemService:
    """Service for analyzing session errors and generating improvement actions.

    WHY: Provides structured analysis of session failures with categorization
    and action recommendations based on error source and type.

    DESIGN DECISION: Leverages existing FailureTracker for data, focuses on
    categorization and actionable improvements rather than raw error collection.
    """

    # File path patterns for categorization
    SCRIPT_PATTERNS = [
        r"scripts/",
        r"claude_mpm/scripts/",
        r"src/claude_mpm/scripts/",
    ]

    SKILL_PATTERNS = [
        r"\.claude/skills/",
        r"skills/",
        r"\.md$.*skill",
    ]

    AGENT_PATTERNS = [
        r"\.claude/agents/",
        r"agents/",
        r"\.md$.*agent",
    ]

    def __init__(self):
        """Initialize the postmortem service."""
        self.tracker = get_failure_tracker()
        self.logger = logger

    def analyze_session(self, session_id: Optional[str] = None) -> PostmortemReport:
        """Analyze errors from current or specified session.

        WHY: Main entry point for postmortem analysis. Collects failures from
        the tracker, categorizes them, and generates improvement actions.

        Args:
            session_id: Optional session ID (uses tracker's session if None)

        Returns:
            Complete postmortem report with analyses and actions
        """
        # Get session info
        from claude_mpm.services.session_manager import get_session_manager

        session_mgr = get_session_manager()
        session_id = session_id or session_mgr.get_session_id()
        start_time = session_mgr._session_start_time
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        # Get all failures (both fixed and unfixed)
        failures = self.tracker.failures

        # Analyze each failure
        analyses = []
        for failure in failures:
            analysis = self._analyze_failure(failure)
            analyses.append(analysis)

        # Generate improvement actions
        actions = self._generate_actions(analyses)

        # Calculate statistics
        stats = self._calculate_stats(analyses, actions)

        # Create report
        report = PostmortemReport(
            session_id=session_id,
            start_time=start_time,
            duration_seconds=duration,
            total_errors=len(failures),
            analyses=analyses,
            actions=actions,
            stats=stats,
        )

        self.logger.info(
            f"Postmortem analysis complete: {len(failures)} errors, "
            f"{len(actions)} actions generated"
        )

        return report

    def _analyze_failure(self, failure: FailureEvent) -> ErrorAnalysis:
        """Analyze a single failure event.

        WHY: Determines error category, root cause, affected file, and
        recommended action based on failure context and error patterns.

        Args:
            failure: Failure event to analyze

        Returns:
            ErrorAnalysis with categorization and recommendations
        """
        # Extract file path if available
        affected_file = self._extract_file_path(failure)

        # Categorize error source
        category = self._categorize_error(failure, affected_file)

        # Determine root cause
        root_cause = self._determine_root_cause(failure)

        # Determine action type based on category
        action_type = self._determine_action_type(category, failure)

        # Generate fix suggestion
        fix_suggestion = self._generate_fix_suggestion(failure, category)

        # Determine priority
        priority = self._calculate_priority(failure)

        # Check if auto-fixable
        auto_fixable = self._is_auto_fixable(failure, category)

        return ErrorAnalysis(
            failure_event=failure,
            category=category,
            root_cause=root_cause,
            affected_file=affected_file,
            action_type=action_type,
            fix_suggestion=fix_suggestion,
            priority=priority,
            auto_fixable=auto_fixable,
            metadata={
                "error_type": failure.context.get("error_type", "unknown"),
                "task_type": failure.task_type,
                "tool": failure.tool_name,
            },
        )

    def _extract_file_path(self, failure: FailureEvent) -> Optional[Path]:
        """Extract file path from failure context or error message.

        Args:
            failure: Failure event

        Returns:
            Path object if file found, None otherwise
        """
        # Check context first
        if "file" in failure.context:
            return Path(failure.context["file"])

        # Try to extract from error message
        # Pattern: "File \"path/to/file.py\", line X"
        file_pattern = r'File "([^"]+)"'
        match = re.search(file_pattern, failure.error_message)
        if match:
            return Path(match.group(1))

        # Pattern: path/to/file.py:line:col
        path_pattern = r"([/\w\-_.]+\.(?:py|md|js|ts|json|yaml)):(\d+)"
        match = re.search(path_pattern, failure.error_message)
        if match:
            return Path(match.group(1))

        return None

    def _categorize_error(
        self, failure: FailureEvent, file_path: Optional[Path]
    ) -> ErrorCategory:
        """Categorize error by source (script/skill/agent/user).

        Args:
            failure: Failure event
            file_path: Extracted file path

        Returns:
            ErrorCategory enum value
        """
        if not file_path:
            # Try to infer from context
            if "agent_type" in failure.context:
                return ErrorCategory.AGENT
            return ErrorCategory.UNKNOWN

        file_str = str(file_path)

        # Check script patterns
        if any(re.search(pattern, file_str) for pattern in self.SCRIPT_PATTERNS):
            return ErrorCategory.SCRIPT

        # Check skill patterns
        if any(re.search(pattern, file_str) for pattern in self.SKILL_PATTERNS):
            return ErrorCategory.SKILL

        # Check agent patterns
        if any(re.search(pattern, file_str) for pattern in self.AGENT_PATTERNS):
            return ErrorCategory.AGENT

        # Check if in framework source (claude_mpm)
        if "claude_mpm" in file_str and "scripts" not in file_str:
            return ErrorCategory.SCRIPT

        # Default to user code
        return ErrorCategory.USER_CODE

    def _determine_root_cause(self, failure: FailureEvent) -> str:
        """Determine root cause from failure event.

        Args:
            failure: Failure event

        Returns:
            Root cause description
        """
        error_type = failure.context.get("error_type", "unknown")
        error_msg = failure.error_message

        # Map error types to root causes
        cause_map = {
            "syntax-error": "Syntax error in code",
            "type-error": "Type mismatch or invalid operation",
            "import-error": "Missing or incorrect import",
            "module-not-found": "Missing dependency or module",
            "file-not-found": "File path incorrect or file missing",
            "test-failure": "Test assertion failed",
            "command-error": "Command execution failed",
        }

        base_cause = cause_map.get(error_type, "Execution failure")

        # Add specific error message snippet
        error_snippet = error_msg[:80] + "..." if len(error_msg) > 80 else error_msg
        return f"{base_cause}: {error_snippet}"

    def _determine_action_type(
        self, category: ErrorCategory, failure: FailureEvent
    ) -> ActionType:
        """Determine recommended action type based on category.

        Args:
            category: Error category
            failure: Failure event

        Returns:
            ActionType enum value
        """
        if category == ErrorCategory.SCRIPT:
            # Scripts can be auto-fixed and tested
            return ActionType.AUTO_FIX

        if category == ErrorCategory.SKILL:
            # Skills should be updated in place
            return ActionType.UPDATE_FILE

        if category == ErrorCategory.AGENT:
            # Agents should trigger PR to remote repo
            return ActionType.CREATE_PR

        if category == ErrorCategory.USER_CODE:
            # User code: suggest only, don't modify
            return ActionType.SUGGEST

        return ActionType.NONE

    def _generate_fix_suggestion(
        self, failure: FailureEvent, category: ErrorCategory
    ) -> str:
        """Generate specific fix suggestion based on error type.

        Args:
            failure: Failure event
            category: Error category

        Returns:
            Fix suggestion string
        """
        error_type = failure.context.get("error_type", "unknown")

        # Category-specific suggestion templates
        if category == ErrorCategory.SCRIPT:
            return self._generate_script_fix_suggestion(failure, error_type)

        if category == ErrorCategory.SKILL:
            return self._generate_skill_fix_suggestion(failure, error_type)

        if category == ErrorCategory.AGENT:
            return self._generate_agent_fix_suggestion(failure, error_type)

        if category == ErrorCategory.USER_CODE:
            return self._generate_user_code_suggestion(failure, error_type)

        return "Review error log and apply appropriate fix"

    def _generate_script_fix_suggestion(
        self, failure: FailureEvent, error_type: str
    ) -> str:
        """Generate fix suggestion for script errors."""
        suggestions = {
            "import-error": "Add missing import or verify module is installed",
            "type-error": "Fix type validation or add proper type checking",
            "syntax-error": "Correct syntax error in Python code",
            "file-not-found": "Verify file paths and add existence checks",
        }
        return suggestions.get(error_type, "Test script in isolation and apply fix")

    def _generate_skill_fix_suggestion(
        self, failure: FailureEvent, error_type: str
    ) -> str:
        """Generate fix suggestion for skill errors."""
        return (
            "Update skill instructions to clarify error-prone section or "
            "add validation step to prevent similar failures"
        )

    def _generate_agent_fix_suggestion(
        self, failure: FailureEvent, error_type: str
    ) -> str:
        """Generate fix suggestion for agent errors."""
        return (
            "Improve agent instructions to handle this case correctly. "
            "Consider adding examples or explicit error handling guidance"
        )

    def _generate_user_code_suggestion(
        self, failure: FailureEvent, error_type: str
    ) -> str:
        """Generate suggestion for user code errors."""
        suggestions = {
            "syntax-error": "Fix syntax error in your code",
            "type-error": "Check types and ensure valid operations",
            "import-error": "Verify import paths and installed packages",
            "test-failure": "Review test assertions and fix failing test",
        }
        return suggestions.get(
            error_type, "Review error and apply appropriate fix to your code"
        )

    def _calculate_priority(self, failure: FailureEvent) -> str:
        """Calculate priority level for error.

        Args:
            failure: Failure event

        Returns:
            Priority string (critical/high/medium/low)
        """
        error_type = failure.context.get("error_type", "unknown")

        # Critical errors
        if error_type in ("syntax-error", "import-error", "module-not-found"):
            return "critical"

        # High priority errors
        if error_type in ("type-error", "test-failure"):
            return "high"

        # Medium priority (default)
        return "medium"

    def _is_auto_fixable(self, failure: FailureEvent, category: ErrorCategory) -> bool:
        """Determine if error can be automatically fixed.

        Args:
            failure: Failure event
            category: Error category

        Returns:
            True if auto-fixable
        """
        # Only scripts are auto-fixable in MVP
        if category != ErrorCategory.SCRIPT:
            return False

        error_type = failure.context.get("error_type", "unknown")

        # Simple error types that can be fixed
        auto_fixable_types = [
            "import-error",  # Add missing import
            "file-not-found",  # Fix path or add check
        ]

        return error_type in auto_fixable_types

    def _generate_actions(
        self, analyses: List[ErrorAnalysis]
    ) -> List[ImprovementAction]:
        """Generate improvement actions from error analyses.

        Args:
            analyses: List of error analyses

        Returns:
            List of improvement actions
        """
        actions = []

        for analysis in analyses:
            if analysis.action_type == ActionType.NONE:
                continue

            action = self._create_action(analysis)
            if action:
                actions.append(action)

        return actions

    def _create_action(self, analysis: ErrorAnalysis) -> Optional[ImprovementAction]:
        """Create specific action based on analysis.

        Args:
            analysis: Error analysis

        Returns:
            ImprovementAction or None
        """
        if analysis.action_type == ActionType.AUTO_FIX:
            return self._create_auto_fix_action(analysis)

        if analysis.action_type == ActionType.UPDATE_FILE:
            return self._create_update_file_action(analysis)

        if analysis.action_type == ActionType.CREATE_PR:
            return self._create_pr_action(analysis)

        if analysis.action_type == ActionType.SUGGEST:
            return self._create_suggestion_action(analysis)

        return None

    def _create_auto_fix_action(self, analysis: ErrorAnalysis) -> ImprovementAction:
        """Create auto-fix action for script errors.

        Args:
            analysis: Error analysis

        Returns:
            ImprovementAction for auto-fixing
        """
        description = f"Auto-fix {analysis.affected_file}: {analysis.fix_suggestion}"

        # Generate test commands
        commands = []
        if analysis.affected_file:
            # Add syntax check
            commands.append(f"python -m py_compile {analysis.affected_file}")

            # Add basic import test
            commands.append(f"python -c 'import {analysis.affected_file.stem}'")

        return ImprovementAction(
            action_type=ActionType.AUTO_FIX,
            error_analysis=analysis,
            description=description,
            commands=commands,
        )

    def _create_update_file_action(self, analysis: ErrorAnalysis) -> ImprovementAction:
        """Create update file action for skills.

        Args:
            analysis: Error analysis

        Returns:
            ImprovementAction for file update
        """
        description = f"Update {analysis.affected_file}: {analysis.fix_suggestion}"

        return ImprovementAction(
            action_type=ActionType.UPDATE_FILE,
            error_analysis=analysis,
            description=description,
        )

    def _create_pr_action(self, analysis: ErrorAnalysis) -> ImprovementAction:
        """Create PR action for agent improvements.

        Args:
            analysis: Error analysis

        Returns:
            ImprovementAction for PR creation
        """
        # Generate PR details
        agent_name = (
            analysis.affected_file.stem if analysis.affected_file else "unknown"
        )
        branch_name = f"fix/{agent_name}-{datetime.now(timezone.utc):%Y%m%d}"

        pr_title = f"Fix: {agent_name} - {analysis.failure_event.task_type} error"

        pr_body = f"""## Problem

{analysis.root_cause}

## Error Log

```
{analysis.failure_event.error_message}
```

## Proposed Improvement

{analysis.fix_suggestion}

## Context

- Task Type: {analysis.failure_event.task_type}
- Tool: {analysis.failure_event.tool_name}
- Error Type: {analysis.metadata.get("error_type", "unknown")}

## Testing

- [ ] Test agent with similar input
- [ ] Verify improvement addresses root cause
- [ ] Check for regression in existing functionality
"""

        description = f"Create PR for {agent_name} improvement"

        return ImprovementAction(
            action_type=ActionType.CREATE_PR,
            error_analysis=analysis,
            description=description,
            pr_branch=branch_name,
            pr_title=pr_title,
            pr_body=pr_body,
        )

    def _create_suggestion_action(self, analysis: ErrorAnalysis) -> ImprovementAction:
        """Create suggestion action for user code.

        Args:
            analysis: Error analysis

        Returns:
            ImprovementAction with suggestion
        """
        description = (
            f"Suggestion for {analysis.affected_file}: {analysis.fix_suggestion}"
        )

        return ImprovementAction(
            action_type=ActionType.SUGGEST,
            error_analysis=analysis,
            description=description,
        )

    def _calculate_stats(
        self, analyses: List[ErrorAnalysis], actions: List[ImprovementAction]
    ) -> Dict[str, int]:
        """Calculate summary statistics.

        Args:
            analyses: List of error analyses
            actions: List of improvement actions

        Returns:
            Statistics dictionary
        """
        stats = {
            "total_errors": len(analyses),
            "script_errors": len(
                [a for a in analyses if a.category == ErrorCategory.SCRIPT]
            ),
            "skill_errors": len(
                [a for a in analyses if a.category == ErrorCategory.SKILL]
            ),
            "agent_errors": len(
                [a for a in analyses if a.category == ErrorCategory.AGENT]
            ),
            "user_code_errors": len(
                [a for a in analyses if a.category == ErrorCategory.USER_CODE]
            ),
            "auto_fixable": len([a for a in analyses if a.auto_fixable]),
            "critical_priority": len([a for a in analyses if a.priority == "critical"]),
            "high_priority": len([a for a in analyses if a.priority == "high"]),
            "total_actions": len(actions),
            "auto_fix_actions": len(
                [a for a in actions if a.action_type == ActionType.AUTO_FIX]
            ),
            "pr_actions": len(
                [a for a in actions if a.action_type == ActionType.CREATE_PR]
            ),
        }

        return {
            "total_errors": stats["total_errors"],
            "by_category": stats["by_category"],
            "high_priority": stats["high_priority"],
            "total_actions": stats["total_actions"],
            "auto_fix_actions": stats["auto_fix_actions"],
            "pr_actions": stats["pr_actions"],
        }


# Singleton instance
_service_instance: Optional[PostmortemService] = None


def get_postmortem_service() -> PostmortemService:
    """Get or create singleton PostmortemService instance.

    Returns:
        PostmortemService instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = PostmortemService()
    return _service_instance
