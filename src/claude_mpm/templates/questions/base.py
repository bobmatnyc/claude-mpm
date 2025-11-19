"""Base classes for structured question templates.

This module provides abstract base classes for creating reusable question templates.
Templates encapsulate common question patterns and can be context-aware.

Design Patterns:
- Template Method: Define question structure, subclasses provide details
- Strategy: Different templates for different workflows
- Factory: Templates build QuestionSet objects
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from claude_mpm.utils.structured_questions import QuestionSet


class QuestionTemplate(ABC):
    """Abstract base class for question templates.

    Subclasses should implement the build() method to construct a QuestionSet
    based on template-specific logic and any provided context.

    Example:
        >>> class MyTemplate(QuestionTemplate):
        ...     def build(self) -> QuestionSet:
        ...         question = QuestionBuilder().ask("...").build()
        ...         return QuestionSet([question])
    """

    @abstractmethod
    def build(self) -> QuestionSet:
        """Build and return a QuestionSet.

        Returns:
            QuestionSet ready for use with AskUserQuestion tool

        Raises:
            QuestionValidationError: If question construction fails
        """

    def to_params(self) -> dict[str, Any]:
        """Build question set and convert to AskUserQuestion parameters.

        Returns:
            Dictionary suitable for AskUserQuestion tool

        Raises:
            QuestionValidationError: If question construction fails
        """
        return self.build().to_ask_user_question_params()


class ConditionalTemplate(QuestionTemplate):
    """Template that adjusts questions based on context.

    This base class provides infrastructure for templates that need to vary
    their questions based on runtime context (e.g., number of tickets,
    project type, etc.).

    Attributes:
        context: Dictionary of context values that affect question selection
    """

    def __init__(self, **context: Any) -> None:
        """Initialize with context values.

        Args:
            **context: Arbitrary context values used to determine questions
        """
        self.context = context

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value.

        Args:
            key: Context key to retrieve
            default: Default value if key not found

        Returns:
            Context value or default
        """
        return self.context.get(key, default)

    def has_context(self, key: str) -> bool:
        """Check if context key exists.

        Args:
            key: Context key to check

        Returns:
            True if key exists in context, False otherwise
        """
        return key in self.context

    def should_include_question(self, question_id: str) -> bool:
        """Determine if a question should be included based on context.

        Subclasses can override this to implement conditional logic.

        Args:
            question_id: Identifier for the question being considered

        Returns:
            True if question should be included, False otherwise
        """
        return True

    @abstractmethod
    def build(self) -> QuestionSet:
        """Build QuestionSet based on context.

        Subclasses must implement this to create context-aware questions.

        Returns:
            QuestionSet with questions appropriate for the context
        """


class MultiStepTemplate(QuestionTemplate):
    """Template for multi-step question workflows.

    Some workflows require multiple rounds of questions, where later questions
    depend on answers to earlier ones. This base class provides infrastructure
    for such workflows.

    Note: Initial implementation focuses on single-step templates. This class
    is provided for future extensibility.
    """

    def __init__(self) -> None:
        """Initialize multi-step template."""
        self._current_step = 0
        self._answers: dict[str, Any] = {}

    def set_answers(self, step: int, answers: dict[str, Any]) -> None:
        """Record answers from a previous step.

        Args:
            step: Step number (0-indexed)
            answers: Parsed answers from ResponseParser
        """
        self._answers[str(step)] = answers

    def get_answers(self, step: int) -> dict[str, Any] | None:
        """Get answers from a previous step.

        Args:
            step: Step number (0-indexed)

        Returns:
            Answers dictionary or None if step not completed
        """
        return self._answers.get(str(step))

    @abstractmethod
    def build_step(self, step: int) -> QuestionSet:
        """Build questions for a specific step.

        Args:
            step: Step number (0-indexed)

        Returns:
            QuestionSet for the specified step
        """

    def build(self) -> QuestionSet:
        """Build questions for the current step.

        Returns:
            QuestionSet for current step
        """
        return self.build_step(self._current_step)

    def advance_step(self) -> None:
        """Move to the next step."""
        self._current_step += 1

    @property
    def current_step(self) -> int:
        """Get current step number."""
        return self._current_step

    @abstractmethod
    def is_complete(self) -> bool:
        """Check if all steps are complete.

        Returns:
            True if workflow is complete, False otherwise
        """
