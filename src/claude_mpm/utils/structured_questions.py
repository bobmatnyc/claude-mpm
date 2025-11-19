"""Structured questions framework for AskUserQuestion tool integration.

This module provides a type-safe, validated approach to building structured questions
for use with Claude's AskUserQuestion tool. It enables agents (particularly PM) to
gather user input in a structured, consistent way.

Design Principles:
- Type-safe with full type hints
- Validation at construction time
- Fluent API for ease of use
- Clear error messages
- Immutable question structures

Example Usage:
    >>> question = (
    ...     QuestionBuilder()
    ...     .ask("Which database should we use?")
    ...     .header("Database")
    ...     .add_option("PostgreSQL", "Robust, feature-rich relational database")
    ...     .add_option("MongoDB", "Flexible NoSQL document database")
    ...     .build()
    ... )
    >>> question_set = QuestionSet([question])
    >>> params = question_set.to_ask_user_question_params()
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any


class QuestionValidationError(Exception):
    """Raised when question validation fails."""


@dataclass(frozen=True)
class QuestionOption:
    """Represents a single option in a structured question.

    Attributes:
        label: Display text shown to user (1-5 words recommended)
        description: Explanation of what this option means or implies
    """

    label: str
    description: str

    def __post_init__(self) -> None:
        """Validate option constraints."""
        if not self.label or not self.label.strip():
            raise QuestionValidationError("Option label cannot be empty")
        if not self.description or not self.description.strip():
            raise QuestionValidationError("Option description cannot be empty")
        if len(self.label) > 50:
            raise QuestionValidationError(
                f"Option label too long ({len(self.label)} chars): {self.label[:30]}..."
            )

    def to_dict(self) -> dict[str, str]:
        """Convert option to AskUserQuestion format."""
        return {"label": self.label, "description": self.description}


@dataclass(frozen=True)
class StructuredQuestion:
    """Represents a single structured question with validation.

    Attributes:
        question: The complete question text (should end with '?')
        header: Short label displayed as chip/tag (max 12 chars)
        options: List of 2-4 QuestionOption objects
        multi_select: Whether user can select multiple options
    """

    question: str
    header: str
    options: list[QuestionOption]
    multi_select: bool = False

    def __post_init__(self) -> None:
        """Validate question constraints."""
        # Question text validation
        if not self.question or not self.question.strip():
            raise QuestionValidationError("Question text cannot be empty")
        if not self.question.strip().endswith("?"):
            raise QuestionValidationError(
                f"Question should end with '?': {self.question[:50]}"
            )

        # Header validation
        if not self.header or not self.header.strip():
            raise QuestionValidationError("Header cannot be empty")
        if len(self.header) > 12:
            raise QuestionValidationError(
                f"Header too long ({len(self.header)} chars, max 12): {self.header}"
            )

        # Options validation
        if not self.options:
            raise QuestionValidationError("Question must have at least 2 options")
        if len(self.options) < 2:
            raise QuestionValidationError(
                f"Question must have at least 2 options, got {len(self.options)}"
            )
        if len(self.options) > 4:
            raise QuestionValidationError(
                f"Question must have at most 4 options, got {len(self.options)}"
            )

        # Validate all options are QuestionOption instances
        if not all(isinstance(opt, QuestionOption) for opt in self.options):
            raise QuestionValidationError(
                "All options must be QuestionOption instances"
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert question to AskUserQuestion format."""
        return {
            "question": self.question,
            "header": self.header,
            "options": [opt.to_dict() for opt in self.options],
            "multiSelect": self.multi_select,
        }


class QuestionBuilder:
    """Fluent API for building StructuredQuestion objects.

    Example:
        >>> question = (
        ...     QuestionBuilder()
        ...     .ask("Which testing framework?")
        ...     .header("Testing")
        ...     .add_option("pytest", "Python's most popular testing framework")
        ...     .add_option("unittest", "Python's built-in testing framework")
        ...     .multi_select()
        ...     .build()
        ... )
    """

    def __init__(self) -> None:
        """Initialize builder with empty state."""
        self._question: str | None = None
        self._header: str | None = None
        self._options: list[QuestionOption] = []
        self._multi_select: bool = False

    def ask(self, question: str) -> QuestionBuilder:
        """Set the question text.

        Args:
            question: The question text (should end with '?')

        Returns:
            Self for method chaining
        """
        self._question = question
        return self

    def header(self, header: str) -> QuestionBuilder:
        """Set the header label.

        Args:
            header: Short label (max 12 chars)

        Returns:
            Self for method chaining
        """
        self._header = header
        return self

    def add_option(self, label: str, description: str) -> QuestionBuilder:
        """Add an option to the question.

        Args:
            label: Display text for the option
            description: Explanation of the option

        Returns:
            Self for method chaining
        """
        self._options.append(QuestionOption(label=label, description=description))
        return self

    def with_options(self, options: list[QuestionOption]) -> QuestionBuilder:
        """Set all options at once.

        Args:
            options: List of QuestionOption objects

        Returns:
            Self for method chaining
        """
        self._options = list(options)
        return self

    def multi_select(self, enabled: bool = True) -> QuestionBuilder:
        """Enable or disable multi-select mode.

        Args:
            enabled: Whether to allow multiple selections

        Returns:
            Self for method chaining
        """
        self._multi_select = enabled
        return self

    def build(self) -> StructuredQuestion:
        """Build and validate the StructuredQuestion.

        Returns:
            Validated StructuredQuestion instance

        Raises:
            QuestionValidationError: If validation fails
        """
        if self._question is None:
            raise QuestionValidationError("Question text is required (use .ask())")
        if self._header is None:
            raise QuestionValidationError("Header is required (use .header())")

        return StructuredQuestion(
            question=self._question,
            header=self._header,
            options=self._options,
            multi_select=self._multi_select,
        )


@dataclass
class QuestionSet:
    """Collection of structured questions for a single AskUserQuestion call.

    Attributes:
        questions: List of 1-4 StructuredQuestion objects
    """

    questions: list[StructuredQuestion] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate question set constraints."""
        if not self.questions:
            raise QuestionValidationError(
                "QuestionSet must contain at least 1 question"
            )
        if len(self.questions) > 4:
            raise QuestionValidationError(
                f"QuestionSet can have at most 4 questions, got {len(self.questions)}"
            )
        if not all(isinstance(q, StructuredQuestion) for q in self.questions):
            raise QuestionValidationError(
                "All questions must be StructuredQuestion instances"
            )

    def add(self, question: StructuredQuestion) -> QuestionSet:
        """Add a question to the set.

        Args:
            question: StructuredQuestion to add

        Returns:
            Self for method chaining

        Raises:
            QuestionValidationError: If adding would exceed 4 questions
        """
        if len(self.questions) >= 4:
            raise QuestionValidationError("Cannot add more than 4 questions")
        self.questions.append(question)
        return self

    def to_ask_user_question_params(self) -> dict[str, Any]:
        """Convert question set to AskUserQuestion tool parameters.

        Returns:
            Dictionary suitable for AskUserQuestion tool parameters
        """
        return {"questions": [q.to_dict() for q in self.questions]}

    def execute(
        self,
        response: dict[str, Any] | None = None,
        use_fallback_if_needed: bool = True,
    ) -> ParsedResponse:
        """Execute questions with automatic fallback on AskUserQuestion failure.

        This method provides graceful degradation when AskUserQuestion tool fails
        or returns empty/invalid responses. It will automatically fall back to
        text-based questions that display in the console.

        Args:
            response: Response from AskUserQuestion tool (if already obtained).
                     If None, assumes tool failed and uses fallback.
            use_fallback_if_needed: Auto-fallback if AskUserQuestion fails (default: True)

        Returns:
            ParsedResponse with user answers

        Example:
            >>> # When AskUserQuestion fails
            >>> response = {}  # Empty/failed response
            >>> parsed = question_set.execute(response)
            >>> # Automatically displays text-based questions
        """
        # If no response provided, use fallback immediately
        if response is None:
            if use_fallback_if_needed:
                return self._execute_text_fallback()
            raise QuestionValidationError("No response provided and fallback disabled")

        # Check if response indicates failure
        if use_fallback_if_needed and self._should_use_fallback(response):
            return self._execute_text_fallback()

        # Use standard parser for valid responses
        return ParsedResponse(self, response.get("answers", {}))

    def _should_use_fallback(self, response: dict[str, Any]) -> bool:
        """Detect if AskUserQuestion failed or returned invalid response.

        Args:
            response: Response from AskUserQuestion tool

        Returns:
            True if fallback should be used, False if response is valid
        """
        # Check for empty/missing response
        if not response or not isinstance(response, dict):
            return True

        # Check for missing answers key
        if "answers" not in response:
            return True

        answers = response.get("answers", {})

        # Check for empty answers
        if not answers or answers == {}:
            return True

        # Check for fake/placeholder responses (like ".")
        answer_values = list(answers.values())
        if answer_values == ["."] or all(v in {".", ""} for v in answer_values):
            return True

        return False

    def _execute_text_fallback(self) -> ParsedResponse:
        """Execute questions as formatted text when AskUserQuestion fails.

        Displays questions in a clear, numbered format and collects user input
        via stdin. Supports numeric selection, label matching, and custom answers.

        Returns:
            ParsedResponse with user answers
        """
        print("\n" + "=" * 60, file=sys.stderr)
        print("📋 USER INPUT REQUIRED", file=sys.stderr)
        print(
            "(AskUserQuestion tool unavailable - using text fallback)", file=sys.stderr
        )
        print("=" * 60 + "\n", file=sys.stderr)

        answers = {}
        for i, question in enumerate(self.questions, 1):
            # Display question header
            print(f"=== Question {i} of {len(self.questions)} ===", file=sys.stderr)
            print(f"[{question.header}] {question.question}\n", file=sys.stderr)

            # Display options
            print("Options:", file=sys.stderr)
            for j, opt in enumerate(question.options, 1):
                print(f"{j}. {opt.label} - {opt.description}", file=sys.stderr)

            # Show multi-select hint
            if question.multi_select:
                print(
                    "\n(You may select multiple - separate with commas)",
                    file=sys.stderr,
                )

            # Get user input
            print("\nYour answer: ", file=sys.stderr, end="")
            user_input = input().strip()

            # Parse response
            answer = self._parse_text_response(
                user_input, question.options, question.multi_select
            )

            answers[question.header] = answer
            print(file=sys.stderr)  # Blank line between questions

        print("=" * 60 + "\n", file=sys.stderr)
        return ParsedResponse(self, answers)

    def _parse_text_response(
        self,
        user_input: str,
        options: list[QuestionOption],
        multi_select: bool,
    ) -> str | list[str]:
        """Parse user's text response into option label(s).

        Supports multiple input formats:
        - Numeric: "1", "2", "3"
        - Label matching: "OAuth", "PostgreSQL"
        - Multi-select: "1,2" or "OAuth, JWT"
        - Custom answers: Any text not matching options

        Args:
            user_input: Raw user input string
            options: Available question options
            multi_select: Whether question allows multiple selections

        Returns:
            Selected option label(s) or custom answer
        """
        # Handle multi-select (comma-separated)
        if multi_select and "," in user_input:
            inputs = [x.strip() for x in user_input.split(",")]
            results = []
            for inp in inputs:
                match = self._match_single_input(inp, options)
                if match:
                    results.append(match)
                else:
                    results.append(inp)  # Include custom answer
            return results if results else [user_input]

        # Single selection
        match = self._match_single_input(user_input, options)
        if match:
            return match

        # Return custom answer
        return user_input

    def _match_single_input(
        self, input_str: str, options: list[QuestionOption]
    ) -> str | None:
        """Match a single input string to an option.

        Args:
            input_str: User input to match
            options: Available options

        Returns:
            Matched option label or None if no match
        """
        input_lower = input_str.lower().strip()

        # Handle numeric input
        if input_str.isdigit():
            idx = int(input_str) - 1
            if 0 <= idx < len(options):
                return options[idx].label

        # Exact match (case-insensitive)
        for opt in options:
            if opt.label.lower() == input_lower:
                return opt.label

        # Partial match (case-insensitive)
        for opt in options:
            if input_lower in opt.label.lower():
                return opt.label

        return None


@dataclass
class ParsedResponse:
    """Wrapper for parsed question responses with convenient accessor methods.

    Provides a clean interface for accessing user answers from both
    AskUserQuestion tool and text fallback responses.

    Attributes:
        question_set: The QuestionSet that was asked
        answers: Dictionary mapping question headers to selected labels
    """

    question_set: QuestionSet
    answers: dict[str, str | list[str]]

    def get(self, header: str) -> str | list[str] | None:
        """Get answer for a specific question by header.

        Args:
            header: Question header to look up

        Returns:
            Selected option label(s) or None if not answered
        """
        return self.answers.get(header)

    def was_answered(self, header: str) -> bool:
        """Check if a question was answered.

        Args:
            header: Question header to check

        Returns:
            True if question was answered, False otherwise
        """
        return header in self.answers

    def get_all(self) -> dict[str, str | list[str]]:
        """Get all answers as a dictionary.

        Returns:
            Dictionary mapping question headers to selected labels
        """
        return self.answers.copy()


class ResponseParser:
    """Parses and validates responses from AskUserQuestion tool.

    Note: This class is maintained for backward compatibility.
    New code should use QuestionSet.execute() which returns ParsedResponse directly.

    Example:
        >>> parser = ResponseParser(question_set)
        >>> answers = parser.parse(tool_response)
        >>> db_choice = answers.get("Database")  # Returns selected option label(s)
    """

    def __init__(self, question_set: QuestionSet) -> None:
        """Initialize parser with the question set that was asked.

        Args:
            question_set: The QuestionSet that was sent to AskUserQuestion
        """
        self.question_set = question_set

    def parse(self, response: dict[str, Any]) -> dict[str, str | list[str]]:
        """Parse AskUserQuestion response into header -> answer mapping.

        Args:
            response: Raw response from AskUserQuestion tool
                     Expected format: {"answers": {"header": "label", ...}}

        Returns:
            Dictionary mapping question headers to selected option labels
            For multi-select questions, values are lists of labels

        Raises:
            QuestionValidationError: If response format is invalid
        """
        if not isinstance(response, dict):
            raise QuestionValidationError("Response must be a dictionary")

        answers = response.get("answers", {})
        if not isinstance(answers, dict):
            raise QuestionValidationError("Response must contain 'answers' dictionary")

        parsed: dict[str, str | list[str]] = {}

        for question in self.question_set.questions:
            header = question.header
            answer = answers.get(header)

            if answer is None:
                # User didn't answer this question (optional question)
                continue

            if question.multi_select:
                # Multi-select: answer should be list or comma-separated string
                if isinstance(answer, list):
                    parsed[header] = answer
                elif isinstance(answer, str):
                    # Parse comma-separated values
                    parsed[header] = [a.strip() for a in answer.split(",") if a.strip()]
                else:
                    raise QuestionValidationError(
                        f"Multi-select answer for '{header}' must be list or string"
                    )
            # Single select: answer should be string
            elif isinstance(answer, str):
                parsed[header] = answer
            else:
                raise QuestionValidationError(
                    f"Single-select answer for '{header}' must be string"
                )

        return parsed

    def get_answer(
        self, parsed_answers: dict[str, str | list[str]], header: str
    ) -> str | list[str] | None:
        """Get answer for a specific question by header.

        Args:
            parsed_answers: Result from parse()
            header: Question header to look up

        Returns:
            Selected option label(s) or None if not answered
        """
        return parsed_answers.get(header)

    def was_answered(
        self, parsed_answers: dict[str, str | list[str]], header: str
    ) -> bool:
        """Check if a question was answered.

        Args:
            parsed_answers: Result from parse()
            header: Question header to check

        Returns:
            True if question was answered, False otherwise
        """
        return header in parsed_answers
