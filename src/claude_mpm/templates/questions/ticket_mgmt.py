"""Ticket management question templates.

This module provides templates for gathering user preferences about ticket
prioritization, scope, and management during sprint planning and execution.

Templates:
- TicketPrioritizationTemplate: How to order/prioritize tickets
- TicketScopeTemplate: Testing and documentation requirements per ticket
- TicketDependencyTemplate: How to handle ticket dependencies

These templates help PM make informed decisions about ticket execution order
and completeness criteria.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from claude_mpm.templates.questions.base import ConditionalTemplate
from claude_mpm.utils.structured_questions import QuestionBuilder, QuestionSet

if TYPE_CHECKING:
    from claude_mpm.utils.structured_questions import StructuredQuestion


class TicketPrioritizationTemplate(ConditionalTemplate):
    """Template for ticket prioritization decisions.

    Asks about:
    - How to order tickets (priority-based, dependency-based, etc.)
    - Whether to work serially or in parallel
    - How to handle blockers

    Context Parameters:
        num_tickets (int): Number of tickets to prioritize
        has_dependencies (bool): Whether tickets have interdependencies
        team_size (int): Number of engineers available

    Example:
        >>> template = TicketPrioritizationTemplate(
        ...     num_tickets=5,
        ...     has_dependencies=True,
        ...     team_size=1
        ... )
        >>> question_set = template.build()
    """

    def __init__(
        self,
        num_tickets: int = 1,
        has_dependencies: bool = False,
        team_size: int = 1,
        **context,
    ):
        """Initialize ticket prioritization template.

        Args:
            num_tickets: Number of tickets to manage
            has_dependencies: Whether tickets depend on each other
            team_size: Number of engineers available
            **context: Additional context values
        """
        super().__init__(
            num_tickets=num_tickets,
            has_dependencies=has_dependencies,
            team_size=team_size,
            **context,
        )

    def build(self) -> QuestionSet:
        """Build ticket prioritization questions.

        Returns:
            QuestionSet with prioritization questions
        """
        num_tickets = self.get_context("num_tickets", 1)
        has_dependencies = self.get_context("has_dependencies", False)
        team_size = self.get_context("team_size", 1)

        questions: list[StructuredQuestion] = []

        # Question 1: Prioritization strategy (only if multiple tickets)
        if num_tickets > 1:
            if has_dependencies:
                priority_question = (
                    QuestionBuilder()
                    .ask("How should we handle ticket dependencies?")
                    .header("Dependencies")
                    .add_option(
                        "Sequential execution",
                        "Complete tickets in dependency order (foundational work first)",
                    )
                    .add_option(
                        "Parallel where possible",
                        "Work on independent tickets in parallel, sequential for dependent ones",
                    )
                    .build()
                )
            else:
                priority_question = (
                    QuestionBuilder()
                    .ask("How should we prioritize the tickets?")
                    .header("Priority")
                    .add_option(
                        "User-visible first",
                        "Prioritize features that directly impact users",
                    )
                    .add_option(
                        "Infrastructure first",
                        "Build foundational components before user-facing features",
                    )
                    .add_option(
                        "Quick wins first",
                        "Start with easiest tickets to build momentum",
                    )
                    .add_option(
                        "High risk first",
                        "Tackle uncertain/risky tickets early to derisk project",
                    )
                    .build()
                )
            questions.append(priority_question)

        # Question 2: Execution strategy (only if multiple tickets and team)
        if num_tickets > 1 and team_size >= 1:
            execution_question = (
                QuestionBuilder()
                .ask("How should tickets be executed?")
                .header("Execution")
                .add_option(
                    "One at a time",
                    "Complete each ticket fully before starting the next",
                )
                .add_option(
                    "Parallel execution",
                    "Work on multiple tickets simultaneously when possible",
                )
                .build()
            )
            questions.append(execution_question)

        # Fallback for single ticket or default case
        if not questions:
            scope_question = (
                QuestionBuilder()
                .ask("What should be the ticket completion criteria?")
                .header("Criteria")
                .add_option(
                    "Implementation only",
                    "Code implementation complete, basic functionality working",
                )
                .add_option(
                    "Implementation + tests",
                    "Code complete with passing unit tests",
                )
                .build()
            )
            questions.append(scope_question)

        return QuestionSet(questions)


class TicketScopeTemplate(ConditionalTemplate):
    """Template for ticket scope and completeness requirements.

    Asks about:
    - Testing requirements (unit, integration, e2e)
    - Documentation requirements
    - Code review requirements
    - Definition of done

    Context Parameters:
        ticket_type (str): Type of ticket (feature, bug, refactor)
        is_user_facing (bool): Whether ticket affects end users
        project_maturity (str): Project stage (prototype, beta, production)

    Example:
        >>> template = TicketScopeTemplate(
        ...     ticket_type="feature",
        ...     is_user_facing=True,
        ...     project_maturity="production"
        ... )
        >>> question_set = template.build()
    """

    def __init__(
        self,
        ticket_type: str | None = "feature",
        is_user_facing: bool = False,
        project_maturity: str = "development",
        **context,
    ):
        """Initialize ticket scope template.

        Args:
            ticket_type: Type of ticket (feature, bug, refactor, etc.)
            is_user_facing: Whether changes affect end users
            project_maturity: Stage of project (prototype, development, production)
            **context: Additional context values
        """
        super().__init__(
            ticket_type=ticket_type,
            is_user_facing=is_user_facing,
            project_maturity=project_maturity,
            **context,
        )

    def build(self) -> QuestionSet:
        """Build ticket scope questions.

        Returns:
            QuestionSet with scope questions
        """
        ticket_type = self.get_context("ticket_type", "feature")
        is_user_facing = self.get_context("is_user_facing", False)
        project_maturity = self.get_context("project_maturity", "development")

        questions: list[StructuredQuestion] = []

        # Question 1: Testing requirements
        if project_maturity == "production" or is_user_facing:
            testing_question = (
                QuestionBuilder()
                .ask("What testing is required for this ticket?")
                .header("Testing")
                .add_option(
                    "Comprehensive",
                    "Unit tests, integration tests, and e2e tests required",
                )
                .add_option(
                    "Standard",
                    "Unit tests and integration tests for critical paths",
                )
                .add_option(
                    "Basic",
                    "Unit tests for core functionality only",
                )
                .build()
            )
        else:
            testing_question = (
                QuestionBuilder()
                .ask("What testing is required for this ticket?")
                .header("Testing")
                .add_option(
                    "Unit tests",
                    "Unit tests covering core functionality",
                )
                .add_option(
                    "Integration tests",
                    "Integration tests for component interactions",
                )
                .add_option(
                    "Manual testing",
                    "Manual verification sufficient for now",
                )
                .build()
            )
        questions.append(testing_question)

        # Question 2: Documentation requirements
        if is_user_facing or ticket_type == "feature":
            docs_question = (
                QuestionBuilder()
                .ask("What documentation is needed?")
                .header("Docs")
                .add_option(
                    "Full documentation",
                    "API docs, user guide, and code comments",
                )
                .add_option(
                    "API docs only",
                    "Document public interfaces and usage examples",
                )
                .add_option(
                    "Code comments",
                    "Inline comments for complex logic only",
                )
                .add_option(
                    "None",
                    "Code is self-documenting, no additional docs needed",
                )
                .build()
            )
            questions.append(docs_question)

        return QuestionSet(questions)


class TicketDependencyTemplate(ConditionalTemplate):
    """Template for handling ticket dependencies and blocking issues.

    Asks about:
    - How to handle blocked tickets
    - Whether to wait or work around dependencies
    - Parallel work strategies

    Context Parameters:
        blocked_tickets (int): Number of tickets currently blocked
        blocking_type (str): Type of blocker (technical, external, approval)

    Example:
        >>> template = TicketDependencyTemplate(
        ...     blocked_tickets=2,
        ...     blocking_type="external"
        ... )
        >>> question_set = template.build()
    """

    def __init__(
        self,
        blocked_tickets: int = 0,
        blocking_type: str | None = None,
        **context,
    ):
        """Initialize ticket dependency template.

        Args:
            blocked_tickets: Number of blocked tickets
            blocking_type: Type of blocker (technical, external, approval, etc.)
            **context: Additional context values
        """
        super().__init__(
            blocked_tickets=blocked_tickets, blocking_type=blocking_type, **context
        )

    def build(self) -> QuestionSet:
        """Build dependency handling questions.

        Returns:
            QuestionSet with dependency questions
        """
        blocked_tickets = self.get_context("blocked_tickets", 0)
        blocking_type = self.get_context("blocking_type")

        questions: list[StructuredQuestion] = []

        # Question about handling blockers
        if blocked_tickets > 0:
            if blocking_type == "external":
                blocker_question = (
                    QuestionBuilder()
                    .ask("How should we handle external dependencies?")
                    .header("Blockers")
                    .add_option(
                        "Wait for unblock",
                        "Pause blocked tickets until external dependency resolves",
                    )
                    .add_option(
                        "Mock and continue",
                        "Create mocks/stubs to continue development",
                    )
                    .add_option(
                        "Work around",
                        "Find alternative implementation to avoid dependency",
                    )
                    .build()
                )
            else:
                blocker_question = (
                    QuestionBuilder()
                    .ask("How should we handle blocked tickets?")
                    .header("Blockers")
                    .add_option(
                        "Resolve blockers first",
                        "Prioritize unblocking tickets before continuing",
                    )
                    .add_option(
                        "Parallel work",
                        "Work on unblocked tickets while resolving blockers",
                    )
                    .build()
                )
            questions.append(blocker_question)

        # Default question if no specific blockers
        if not questions:
            dependency_question = (
                QuestionBuilder()
                .ask("How should we manage ticket dependencies?")
                .header("Dependencies")
                .add_option(
                    "Strict ordering",
                    "Maintain strict dependency order, wait for prerequisites",
                )
                .add_option(
                    "Flexible approach",
                    "Start dependent work in parallel with preparation work",
                )
                .build()
            )
            questions.append(dependency_question)

        return QuestionSet(questions)
