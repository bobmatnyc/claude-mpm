"""Project initialization question templates.

This module provides templates for gathering information during project setup,
including project type, language, frameworks, and development workflow preferences.

Templates:
- ProjectTypeTemplate: Project type and primary language selection
- DevelopmentWorkflowTemplate: Testing, CI/CD, and development preferences
- FrameworkTemplate: Framework and library selection

These templates help PM gather necessary context during /mpm-init or new project setup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from claude_mpm.templates.questions.base import ConditionalTemplate
from claude_mpm.utils.structured_questions import QuestionBuilder, QuestionSet

if TYPE_CHECKING:
    from claude_mpm.utils.structured_questions import StructuredQuestion


class ProjectTypeTemplate(ConditionalTemplate):
    """Template for project type and language selection.

    Asks about:
    - Project type (web app, API, library, etc.)
    - Primary programming language
    - Target deployment environment (optional, based on type)

    Context Parameters:
        existing_files (bool): Whether project has existing files
        detected_language (str): Auto-detected language if any

    Example:
        >>> template = ProjectTypeTemplate(existing_files=False)
        >>> question_set = template.build()
    """

    def __init__(
        self,
        existing_files: bool = False,
        detected_language: str | None = None,
        **context,
    ):
        """Initialize project type template.

        Args:
            existing_files: Whether project directory has existing files
            detected_language: Language auto-detected from existing files
            **context: Additional context values
        """
        super().__init__(
            existing_files=existing_files,
            detected_language=detected_language,
            **context,
        )

    def build(self) -> QuestionSet:
        """Build project type questions.

        Returns:
            QuestionSet with project type questions
        """
        detected_language = self.get_context("detected_language")

        questions: list[StructuredQuestion] = []

        # Question 1: Project type
        type_question = (
            QuestionBuilder()
            .ask("What type of project is this?")
            .header("Project Type")
            .add_option(
                "Web Application",
                "Full-stack web app with frontend and backend",
            )
            .add_option(
                "API Service",
                "Backend API or microservice",
            )
            .add_option(
                "Library/Package",
                "Reusable library or package for distribution",
            )
            .add_option(
                "CLI Tool",
                "Command-line application or tool",
            )
            .build()
        )
        questions.append(type_question)

        # Question 2: Primary language (only if not detected)
        if not detected_language:
            language_question = (
                QuestionBuilder()
                .ask("What is the primary programming language?")
                .header("Language")
                .add_option(
                    "Python",
                    "Python 3.8+ for backend, scripts, or data processing",
                )
                .add_option(
                    "JavaScript/TypeScript",
                    "JavaScript or TypeScript for Node.js or full-stack",
                )
                .add_option(
                    "Go",
                    "Go for high-performance services and tools",
                )
                .add_option(
                    "Rust",
                    "Rust for systems programming and performance-critical code",
                )
                .build()
            )
            questions.append(language_question)

        return QuestionSet(questions)


class DevelopmentWorkflowTemplate(ConditionalTemplate):
    """Template for development workflow preferences.

    Asks about:
    - Testing framework and coverage requirements
    - CI/CD setup preferences
    - Code quality tools
    - Documentation approach

    Context Parameters:
        project_type (str): Type of project (from ProjectTypeTemplate)
        language (str): Primary language (affects tool choices)

    Example:
        >>> template = DevelopmentWorkflowTemplate(
        ...     project_type="API Service",
        ...     language="Python"
        ... )
        >>> question_set = template.build()
    """

    def __init__(
        self,
        project_type: str | None = None,
        language: str | None = None,
        **context,
    ):
        """Initialize development workflow template.

        Args:
            project_type: Type of project being set up
            language: Primary programming language
            **context: Additional context values
        """
        super().__init__(project_type=project_type, language=language, **context)

    def build(self) -> QuestionSet:
        """Build development workflow questions.

        Returns:
            QuestionSet with workflow questions
        """
        language = self.get_context("language", "").lower()

        questions: list[StructuredQuestion] = []

        # Question 1: Testing approach
        if "python" in language:
            testing_question = (
                QuestionBuilder()
                .ask("What testing framework should we use?")
                .header("Testing")
                .add_option(
                    "pytest",
                    "Modern, feature-rich testing with fixtures and plugins",
                )
                .add_option(
                    "unittest",
                    "Python's built-in testing framework (standard library)",
                )
                .build()
            )
        elif "javascript" in language or "typescript" in language:
            testing_question = (
                QuestionBuilder()
                .ask("What testing framework should we use?")
                .header("Testing")
                .add_option(
                    "Jest",
                    "Popular, batteries-included testing framework",
                )
                .add_option(
                    "Vitest",
                    "Fast, modern testing with native ESM support",
                )
                .build()
            )
        else:
            # Generic testing question
            testing_question = (
                QuestionBuilder()
                .ask("What level of test coverage should we target?")
                .header("Testing")
                .add_option(
                    "High coverage (80%+)",
                    "Comprehensive testing with strict coverage requirements",
                )
                .add_option(
                    "Moderate coverage (60%+)",
                    "Good testing balance between speed and thoroughness",
                )
                .build()
            )
        questions.append(testing_question)

        # Question 2: CI/CD setup
        cicd_question = (
            QuestionBuilder()
            .ask("Should we set up CI/CD from the start?")
            .header("CI/CD")
            .add_option(
                "Yes, with GitHub Actions",
                "Automated testing and deployment using GitHub Actions",
            )
            .add_option(
                "Yes, with GitLab CI",
                "Automated testing and deployment using GitLab CI",
            )
            .add_option(
                "Not yet",
                "Set up CI/CD later when project is more mature",
            )
            .build()
        )
        questions.append(cicd_question)

        return QuestionSet(questions)


class FrameworkTemplate(ConditionalTemplate):
    """Template for framework and library selection.

    Asks about specific frameworks based on project type and language.

    Context Parameters:
        project_type (str): Type of project
        language (str): Primary language

    Example:
        >>> template = FrameworkTemplate(
        ...     project_type="Web Application",
        ...     language="Python"
        ... )
        >>> question_set = template.build()
    """

    def __init__(
        self,
        project_type: str | None = None,
        language: str | None = None,
        **context,
    ):
        """Initialize framework template.

        Args:
            project_type: Type of project being set up
            language: Primary programming language
            **context: Additional context values
        """
        super().__init__(project_type=project_type, language=language, **context)

    def build(self) -> QuestionSet:
        """Build framework selection questions.

        Returns:
            QuestionSet with framework questions
        """
        language = self.get_context("language", "").lower()
        project_type = self.get_context("project_type", "").lower()

        questions: list[StructuredQuestion] = []

        # Python web frameworks
        if "python" in language and ("web" in project_type or "api" in project_type):
            framework_question = (
                QuestionBuilder()
                .ask("Which Python web framework should we use?")
                .header("Framework")
                .add_option(
                    "FastAPI",
                    "Modern, fast framework with automatic API documentation",
                )
                .add_option(
                    "Flask",
                    "Lightweight, flexible micro-framework",
                )
                .add_option(
                    "Django",
                    "Full-featured framework with batteries included",
                )
                .build()
            )
            questions.append(framework_question)

        # JavaScript/TypeScript frameworks
        elif (
            "javascript" in language or "typescript" in language
        ) and "web" in project_type:
            framework_question = (
                QuestionBuilder()
                .ask("Which frontend framework should we use?")
                .header("Framework")
                .add_option(
                    "React",
                    "Popular, component-based UI library with large ecosystem",
                )
                .add_option(
                    "Vue",
                    "Progressive framework with gentle learning curve",
                )
                .add_option(
                    "Next.js",
                    "React framework with SSR, routing, and optimization",
                )
                .add_option(
                    "Svelte",
                    "Compiled framework with minimal runtime overhead",
                )
                .build()
            )
            questions.append(framework_question)

        # Database selection for API/web projects
        if "api" in project_type or "web" in project_type:
            database_question = (
                QuestionBuilder()
                .ask("What database should we use?")
                .header("Database")
                .add_option(
                    "PostgreSQL",
                    "Robust relational database with advanced features",
                )
                .add_option(
                    "MongoDB",
                    "Flexible NoSQL document database",
                )
                .add_option(
                    "SQLite",
                    "Lightweight embedded database (good for prototypes)",
                )
                .add_option(
                    "Redis",
                    "In-memory data store for caching and real-time features",
                )
                .build()
            )
            questions.append(database_question)

        # Fallback if no specific framework questions
        if not questions:
            tooling_question = (
                QuestionBuilder()
                .ask("What development tools should we prioritize?")
                .header("Tooling")
                .add_option(
                    "Code quality",
                    "Linters, formatters, and static analysis tools",
                )
                .add_option(
                    "Testing",
                    "Comprehensive testing framework and coverage tools",
                )
                .add_option(
                    "Documentation",
                    "API docs, code docs, and documentation generators",
                )
                .build()
            )
            questions.append(tooling_question)

        return QuestionSet(questions)
