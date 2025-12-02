"""Structured question templates for common PM workflows.

This package provides reusable question templates that PM agents can use to gather
user input in a structured way. Templates are pre-configured QuestionSet objects
that can be customized based on context.

Available Templates:
- PR Strategy: Questions about PR workflow, draft preferences, auto-merge
- Project Initialization: Questions about project type, language, frameworks
- Ticket Management: Questions about ticket prioritization and scope

Example Usage:
    >>> from claude_mpm.templates.questions.pr_strategy import PRWorkflowTemplate
    >>> template = PRWorkflowTemplate(num_tickets=3)
    >>> question_set = template.build()
    >>> params = question_set.to_ask_user_question_params()
"""

from claude_mpm.templates.questions.base import ConditionalTemplate, QuestionTemplate
from claude_mpm.templates.questions.pr_strategy import PRWorkflowTemplate
from claude_mpm.templates.questions.project_init import (
    DevelopmentWorkflowTemplate,
    ProjectTypeTemplate,
)
from claude_mpm.templates.questions.ticket_mgmt import (
    TicketPrioritizationTemplate,
    TicketScopeTemplate,
)

__all__ = [
    "ConditionalTemplate",
    "DevelopmentWorkflowTemplate",
    "PRWorkflowTemplate",
    "ProjectTypeTemplate",
    "QuestionTemplate",
    "TicketPrioritizationTemplate",
    "TicketScopeTemplate",
]
