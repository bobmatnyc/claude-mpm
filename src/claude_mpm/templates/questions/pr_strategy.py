"""PR Strategy question templates for PM workflow decisions.

This module provides templates for gathering user preferences about PR workflows,
including whether to use stacked PRs, draft PRs, and auto-merge settings.

Templates:
- PRWorkflowTemplate: Main PR workflow decisions (main-based vs stacked)
- DraftPRTemplate: Draft PR preferences
- AutoMergeTemplate: Auto-merge preferences

These templates are context-aware and only ask relevant questions based on the
number of tickets and project state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from claude_mpm.templates.questions.base import ConditionalTemplate
from claude_mpm.utils.structured_questions import QuestionBuilder, QuestionSet

if TYPE_CHECKING:
    from claude_mpm.utils.structured_questions import StructuredQuestion


class PRWorkflowTemplate(ConditionalTemplate):
    """Template for PR workflow strategy questions.

    Asks questions about:
    - Main-based vs stacked PRs (only if multiple tickets)
    - Draft PR preference
    - Auto-merge preference

    Context Parameters:
        num_tickets (int): Number of tickets being worked on
        has_ci (bool): Whether project has CI/CD setup (affects auto-merge question)

    Example:
        >>> template = PRWorkflowTemplate(num_tickets=3, has_ci=True)
        >>> question_set = template.build()
        >>> params = question_set.to_ask_user_question_params()
    """

    def __init__(self, num_tickets: int = 1, has_ci: bool = False, **context):
        """Initialize PR workflow template.

        Args:
            num_tickets: Number of tickets in this sprint/batch
            has_ci: Whether CI/CD is configured
            **context: Additional context values
        """
        super().__init__(num_tickets=num_tickets, has_ci=has_ci, **context)

    def should_include_question(self, question_id: str) -> bool:
        """Determine which questions to ask based on context.

        Args:
            question_id: Question identifier
                - "workflow": Main vs stacked PRs
                - "draft": Draft PR preference
                - "auto_merge": Auto-merge preference

        Returns:
            True if question should be included
        """
        num_tickets = self.get_context("num_tickets", 1)
        has_ci = self.get_context("has_ci", False)

        if question_id == "workflow":
            # Only ask about stacked vs main-based if multiple tickets
            return num_tickets > 1

        if question_id == "draft":
            # Always relevant
            return True

        if question_id == "auto_merge":
            # Only ask about auto-merge if CI is configured
            return has_ci

        return True

    def build(self) -> QuestionSet:
        """Build PR workflow questions based on context.

        Returns:
            QuestionSet with relevant PR workflow questions
        """
        questions: list[StructuredQuestion] = []

        # Question 1: PR workflow strategy (only if multiple tickets)
        if self.should_include_question("workflow"):
            workflow_question = (
                QuestionBuilder()
                .ask("How should we organize the pull requests?")
                .header("PR Strategy")
                .add_option(
                    "Main-based PRs",
                    "Each ticket gets its own PR against main branch (parallel work)",
                )
                .add_option(
                    "Stacked PRs",
                    "PRs build on each other sequentially (ticket-1 → ticket-2 → ticket-3)",
                )
                .build()
            )
            questions.append(workflow_question)

        # Question 2: Draft PR preference
        if self.should_include_question("draft"):
            draft_question = (
                QuestionBuilder()
                .ask("Should PRs be created as drafts initially?")
                .header("Draft PRs")
                .add_option(
                    "Yes, as drafts",
                    "Create as draft PRs, mark ready when implementation complete",
                )
                .add_option(
                    "No, ready for review",
                    "Create as regular PRs ready for immediate review",
                )
                .build()
            )
            questions.append(draft_question)

        # Question 3: Auto-merge preference (only if CI configured)
        if self.should_include_question("auto_merge"):
            automerge_question = (
                QuestionBuilder()
                .ask("Should PRs auto-merge after CI passes and approval?")
                .header("Auto-merge")
                .add_option(
                    "Enable auto-merge",
                    "PRs merge automatically after CI passes and approval received",
                )
                .add_option(
                    "Manual merge only",
                    "PRs require manual merge even after approval",
                )
                .build()
            )
            questions.append(automerge_question)

        if not questions:
            # Fallback: at least ask about draft preference
            questions.append(
                QuestionBuilder()
                .ask("Should PRs be created as drafts initially?")
                .header("Draft PRs")
                .add_option(
                    "Yes, as drafts",
                    "Create as draft PRs, mark ready when implementation complete",
                )
                .add_option(
                    "No, ready for review",
                    "Create as regular PRs ready for immediate review",
                )
                .build()
            )

        return QuestionSet(questions)


class PRSizeTemplate(ConditionalTemplate):
    """Template for PR size and scope preferences.

    Asks about preferred PR size and whether to split large changes.

    Context Parameters:
        estimated_changes (int): Estimated lines of code changed

    Example:
        >>> template = PRSizeTemplate(estimated_changes=500)
        >>> question_set = template.build()
    """

    def __init__(self, estimated_changes: int = 0, **context):
        """Initialize PR size template.

        Args:
            estimated_changes: Estimated LOC changes
            **context: Additional context values
        """
        super().__init__(estimated_changes=estimated_changes, **context)

    def build(self) -> QuestionSet:
        """Build PR size preference questions.

        Returns:
            QuestionSet with PR size questions
        """
        estimated_changes = self.get_context("estimated_changes", 0)

        questions: list[StructuredQuestion] = []

        # Only ask if changes are large
        if estimated_changes > 300:
            size_question = (
                QuestionBuilder()
                .ask(
                    "This feature involves significant changes. How should we split it?"
                )
                .header("PR Size")
                .add_option(
                    "Single large PR",
                    "Keep all changes together in one comprehensive PR",
                )
                .add_option(
                    "Split by component",
                    "Create separate PRs for each major component",
                )
                .add_option(
                    "Split by feature",
                    "Create separate PRs for each sub-feature",
                )
                .build()
            )
            questions.append(size_question)

        # Fallback if no size concerns
        if not questions:
            commit_question = (
                QuestionBuilder()
                .ask("How should commits be organized?")
                .header("Commits")
                .add_option(
                    "Atomic commits",
                    "Many small, focused commits (one per logical change)",
                )
                .add_option(
                    "Feature commits",
                    "Fewer, larger commits (one per feature/component)",
                )
                .build()
            )
            questions.append(commit_question)

        return QuestionSet(questions)


class PRReviewTemplate(ConditionalTemplate):
    """Template for PR review and approval preferences.

    Asks about reviewer assignment, approval requirements, and review timing.

    Context Parameters:
        team_size (int): Number of team members
        is_critical (bool): Whether this is a critical/sensitive change

    Example:
        >>> template = PRReviewTemplate(team_size=5, is_critical=True)
        >>> question_set = template.build()
    """

    def __init__(self, team_size: int = 1, is_critical: bool = False, **context):
        """Initialize PR review template.

        Args:
            team_size: Number of team members available for review
            is_critical: Whether changes are critical/sensitive
            **context: Additional context values
        """
        super().__init__(team_size=team_size, is_critical=is_critical, **context)

    def build(self) -> QuestionSet:
        """Build PR review preference questions.

        Returns:
            QuestionSet with PR review questions
        """
        team_size = self.get_context("team_size", 1)

        questions: list[StructuredQuestion] = []

        # Question about number of approvals required
        if team_size > 1:
            approval_question = (
                QuestionBuilder()
                .ask("How many approvals should be required before merging?")
                .header("Approvals")
                .add_option(
                    "1 approval",
                    "Single approval sufficient (faster iteration)",
                )
                .add_option(
                    "2 approvals",
                    "Two approvals required (more thorough review)",
                )
                .build()
            )
            questions.append(approval_question)

        # Question about review timing
        timing_question = (
            QuestionBuilder()
            .ask("When should review be requested?")
            .header("Review When")
            .add_option(
                "After implementation",
                "Request review only when all code is complete",
            )
            .add_option(
                "Early feedback",
                "Request early review for approach validation",
            )
            .build()
        )
        questions.append(timing_question)

        return QuestionSet(questions)
