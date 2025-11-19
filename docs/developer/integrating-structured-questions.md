# Integrating Structured Questions

Guide for adding structured questions to custom agents and workflows.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Integration Patterns](#integration-patterns)
3. [Using Templates](#using-templates)
4. [Creating Custom Templates](#creating-custom-templates)
5. [Testing Structured Questions](#testing-structured-questions)
6. [Best Practices](#best-practices)
7. [Common Patterns](#common-patterns)

## Quick Start

### Basic Integration

Add structured questions to any agent in 3 steps:

**Step 1: Import Required Classes**

```python
from claude_mpm.utils.structured_questions import (
    QuestionBuilder,
    QuestionSet,
    ResponseParser
)
```

**Step 2: Build Questions**

```python
# Build a question
question = (
    QuestionBuilder()
    .ask("Which testing framework should we use?")
    .header("Testing")
    .add_option("pytest", "Modern Python testing framework")
    .add_option("unittest", "Built-in Python testing")
    .build()
)

# Create question set
question_set = QuestionSet([question])
```

**Step 3: Execute Questions (Recommended - New API)**

```python
# In your agent code - try AskUserQuestion, fallback on failure
params = question_set.to_ask_user_question_params()
response = self.ask_user_question(params)

# Execute with automatic fallback
parsed = question_set.execute(response)
testing_choice = parsed.get("Testing")  # "pytest" or "unittest"
```

**Alternative: Legacy API (Still Supported)**

```python
# Old approach - manual parsing
params = question_set.to_ask_user_question_params()
response = self.ask_user_question(params)

parser = ResponseParser(question_set)
answers = parser.parse(response)
testing_choice = answers.get("Testing")  # "pytest" or "unittest"
```

**Key Differences:**

- **New API (`execute()`)**: Automatic fallback, cleaner syntax, returns `ParsedResponse`
- **Legacy API (`ResponseParser`)**: Manual fallback handling, more verbose, still fully supported

---

## Integration Patterns

### Pattern 1: Simple Question in Agent Method (New API)

```python
class MyAgent:
    def choose_deployment_target(self):
        """Ask user about deployment target."""
        # Build question
        question = (
            QuestionBuilder()
            .ask("Where should we deploy this application?")
            .header("Deploy To")
            .add_option("AWS", "Amazon Web Services")
            .add_option("GCP", "Google Cloud Platform")
            .add_option("Azure", "Microsoft Azure")
            .build()
        )

        # Create question set
        question_set = QuestionSet([question])

        # Get params and ask user
        params = question_set.to_ask_user_question_params()
        response = self.ask_user_question(params)

        # Execute with automatic fallback
        parsed = question_set.execute(response)
        deployment_target = parsed.get("Deploy To")

        return deployment_target
```

**Old Pattern (Still Works):**

```python
class MyAgent:
    def choose_deployment_target(self):
        """Ask user about deployment target."""
        question = (
            QuestionBuilder()
            .ask("Where should we deploy this application?")
            .header("Deploy To")
            .add_option("AWS", "Amazon Web Services")
            .add_option("GCP", "Google Cloud Platform")
            .add_option("Azure", "Microsoft Azure")
            .build()
        )

        question_set = QuestionSet([question])
        params = question_set.to_ask_user_question_params()
        response = self.ask_user_question(params)

        # Manual parsing (no automatic fallback)
        parser = ResponseParser(question_set)
        answers = parser.parse(response)
        deployment_target = answers.get("Deploy To")

        return deployment_target
```

### Pattern 2: Using Existing Templates (New API)

```python
from claude_mpm.templates.questions.pr_strategy import PRWorkflowTemplate

class VersionControlAgent:
    def get_pr_preferences(self, num_tickets: int, has_ci: bool):
        """Get PR workflow preferences from user."""
        # Use existing template
        template = PRWorkflowTemplate(
            num_tickets=num_tickets,
            has_ci=has_ci
        )

        # Get params and ask user
        params = template.to_params()
        response = self.ask_user_question(params)

        # Execute with automatic fallback
        question_set = template.build()
        parsed = question_set.execute(response)

        # Extract preferences
        pr_strategy = parsed.get("PR Strategy")
        draft_mode = parsed.get("Draft PRs") == "Yes, as drafts"
        auto_merge = parsed.get("Auto-merge") == "Enable auto-merge"

        return {
            "strategy": "stacked" if pr_strategy == "Stacked PRs" else "main-based",
            "draft": draft_mode,
            "auto_merge": auto_merge
        }
```

**Old Pattern (Still Works):**

```python
from claude_mpm.templates.questions.pr_strategy import PRWorkflowTemplate

class VersionControlAgent:
    def get_pr_preferences(self, num_tickets: int, has_ci: bool):
        """Get PR workflow preferences from user."""
        template = PRWorkflowTemplate(
            num_tickets=num_tickets,
            has_ci=has_ci
        )

        params = template.to_params()
        response = self.ask_user_question(params)

        # Manual parsing
        parser = ResponseParser(template.build())
        answers = parser.parse(response)

        pr_strategy = answers.get("PR Strategy")
        draft_mode = answers.get("Draft PRs") == "Yes, as drafts"
        auto_merge = answers.get("Auto-merge") == "Enable auto-merge"

        return {
            "strategy": "stacked" if pr_strategy == "Stacked PRs" else "main-based",
            "draft": draft_mode,
            "auto_merge": auto_merge
        }
```

### Pattern 3: Multiple Related Questions

```python
class ProjectSetupAgent:
    def gather_project_info(self):
        """Gather complete project setup information."""
        questions = []

        # Question 1: Project type
        type_question = (
            QuestionBuilder()
            .ask("What type of project is this?")
            .header("Type")
            .add_option("Web App", "Full-stack web application")
            .add_option("API", "Backend API service")
            .add_option("Library", "Reusable library/package")
            .build()
        )
        questions.append(type_question)

        # Question 2: Language
        lang_question = (
            QuestionBuilder()
            .ask("Which programming language?")
            .header("Language")
            .add_option("Python", "Python 3.8+")
            .add_option("TypeScript", "TypeScript/JavaScript")
            .add_option("Go", "Go programming language")
            .build()
        )
        questions.append(lang_question)

        # Question 3: Testing
        test_question = (
            QuestionBuilder()
            .ask("What testing approach?")
            .header("Testing")
            .add_option("TDD", "Test-driven development")
            .add_option("TAD", "Test after development")
            .build()
        )
        questions.append(test_question)

        # Create question set (max 4 questions)
        question_set = QuestionSet(questions)
        params = question_set.to_ask_user_question_params()

        # Ask user
        response = self.ask_user_question(params)

        # Parse all answers
        parser = ResponseParser(question_set)
        answers = parser.parse(response)

        return {
            "project_type": answers.get("Type"),
            "language": answers.get("Language"),
            "testing_approach": answers.get("Testing")
        }
```

### Pattern 4: Conditional Questions Based on Context

```python
class DeploymentAgent:
    def gather_deployment_config(self, project_type: str, has_database: bool):
        """Gather deployment config with context-aware questions."""
        questions = []

        # Always ask about cloud provider
        cloud_question = (
            QuestionBuilder()
            .ask("Which cloud provider?")
            .header("Cloud")
            .add_option("AWS", "Amazon Web Services")
            .add_option("GCP", "Google Cloud Platform")
            .build()
        )
        questions.append(cloud_question)

        # Only ask about database hosting if project has database
        if has_database:
            db_question = (
                QuestionBuilder()
                .ask("How should we host the database?")
                .header("DB Hosting")
                .add_option("Managed", "Cloud-managed database service")
                .add_option("Self-hosted", "Self-managed database instance")
                .build()
            )
            questions.append(db_question)

        # Ask about scaling for web apps
        if project_type == "Web App":
            scaling_question = (
                QuestionBuilder()
                .ask("What scaling strategy?")
                .header("Scaling")
                .add_option("Auto-scale", "Automatic scaling based on load")
                .add_option("Fixed", "Fixed number of instances")
                .build()
            )
            questions.append(scaling_question)

        # Create and use question set
        question_set = QuestionSet(questions)
        params = question_set.to_ask_user_question_params()
        response = self.ask_user_question(params)

        parser = ResponseParser(question_set)
        return parser.parse(response)
```

---

## Using Templates

### Available Templates

Templates provide pre-built, context-aware questions:

```python
# PR Strategy
from claude_mpm.templates.questions.pr_strategy import (
    PRWorkflowTemplate,
    PRSizeTemplate,
    PRReviewTemplate
)

# Project Initialization
from claude_mpm.templates.questions.project_init import (
    ProjectTypeTemplate,
    DevelopmentWorkflowTemplate,
    FrameworkTemplate
)

# Ticket Management
from claude_mpm.templates.questions.ticket_mgmt import (
    TicketPrioritizationTemplate,
    TicketScopeTemplate,
    TicketDependencyTemplate
)
```

### Using a Template

```python
def use_pr_workflow_template(self, num_tickets: int):
    """Use PRWorkflowTemplate in agent."""
    # Detect CI configuration
    has_ci = self.check_for_ci_config()

    # Create template with context
    template = PRWorkflowTemplate(
        num_tickets=num_tickets,
        has_ci=has_ci
    )

    # Get parameters for AskUserQuestion
    params = template.to_params()

    # Ask user
    response = self.ask_user_question(params)

    # Parse response
    parser = ResponseParser(template.build())
    answers = parser.parse(response)

    return answers
```

### Template Context Detection

```python
class PMAgent:
    def create_prs_for_tickets(self, tickets: list[str]):
        """Create PRs with user preferences."""
        # Detect context
        num_tickets = len(tickets)
        has_ci = self.detect_ci_configuration()

        # Use template with detected context
        template = PRWorkflowTemplate(
            num_tickets=num_tickets,
            has_ci=has_ci
        )

        # Template automatically adjusts questions based on context
        params = template.to_params()
        response = self.ask_user_question(params)

        # Parse and use preferences
        parser = ResponseParser(template.build())
        preferences = parser.parse(response)

        # Delegate to version-control with preferences
        self.delegate_to_version_control(tickets, preferences)

    def detect_ci_configuration(self) -> bool:
        """Detect if CI/CD is configured."""
        import os
        # Check for common CI config files
        ci_files = [
            ".github/workflows/",
            ".gitlab-ci.yml",
            ".circleci/config.yml",
            "azure-pipelines.yml"
        ]
        return any(os.path.exists(f) for f in ci_files)
```

---

## Creating Custom Templates

### Simple Template

```python
from claude_mpm.templates.questions.base import QuestionTemplate
from claude_mpm.utils.structured_questions import (
    QuestionBuilder,
    QuestionSet
)

class DatabaseMigrationTemplate(QuestionTemplate):
    """Template for database migration preferences."""

    def build(self) -> QuestionSet:
        """Build database migration questions."""
        migration_question = (
            QuestionBuilder()
            .ask("How should we handle database migrations?")
            .header("Migrations")
            .add_option(
                "Alembic",
                "Use Alembic for automatic schema migrations"
            )
            .add_option(
                "Raw SQL",
                "Write manual SQL migration scripts"
            )
            .add_option(
                "ORM only",
                "Use ORM migrations without separate tool"
            )
            .build()
        )

        return QuestionSet([migration_question])
```

### Context-Aware Template

```python
from claude_mpm.templates.questions.base import ConditionalTemplate
from claude_mpm.utils.structured_questions import (
    QuestionBuilder,
    QuestionSet
)

class SecurityTemplate(ConditionalTemplate):
    """Template for security configuration."""

    def __init__(
        self,
        is_public: bool = False,
        handles_pii: bool = False,
        **context
    ):
        """Initialize security template.

        Args:
            is_public: Whether application is publicly accessible
            handles_pii: Whether application handles PII data
            **context: Additional context
        """
        super().__init__(
            is_public=is_public,
            handles_pii=handles_pii,
            **context
        )

    def build(self) -> QuestionSet:
        """Build security questions based on context."""
        questions = []

        # Always ask about authentication
        auth_question = (
            QuestionBuilder()
            .ask("What authentication method?")
            .header("Auth")
            .add_option("OAuth2", "OAuth2 with third-party providers")
            .add_option("JWT", "JWT tokens for stateless auth")
            .add_option("Session", "Session-based authentication")
            .build()
        )
        questions.append(auth_question)

        # Ask about rate limiting if public
        if self.get_context("is_public", False):
            rate_limit_question = (
                QuestionBuilder()
                .ask("Should we implement rate limiting?")
                .header("Rate Limit")
                .add_option("Yes, strict", "Strict rate limits (100 req/min)")
                .add_option("Yes, relaxed", "Relaxed rate limits (1000 req/min)")
                .add_option("No", "No rate limiting")
                .build()
            )
            questions.append(rate_limit_question)

        # Ask about encryption if handling PII
        if self.get_context("handles_pii", False):
            encryption_question = (
                QuestionBuilder()
                .ask("What level of data encryption?")
                .header("Encryption")
                .add_option(
                    "At rest + in transit",
                    "Encrypt data both stored and transmitted"
                )
                .add_option(
                    "In transit only",
                    "Encrypt only during transmission (HTTPS)"
                )
                .build()
            )
            questions.append(encryption_question)

        return QuestionSet(questions)
```

### Using Custom Template

```python
class SecurityAgent:
    def configure_security(self, app_config: dict):
        """Configure security based on application requirements."""
        # Create template with context
        template = SecurityTemplate(
            is_public=app_config.get("public", False),
            handles_pii=app_config.get("has_user_data", False)
        )

        # Get params and ask user
        params = template.to_params()
        response = self.ask_user_question(params)

        # Parse answers
        parser = ResponseParser(template.build())
        answers = parser.parse(response)

        # Apply security configuration
        auth_method = answers.get("Auth")
        rate_limit = answers.get("Rate Limit")  # May be None
        encryption = answers.get("Encryption")  # May be None

        return {
            "authentication": auth_method,
            "rate_limiting": rate_limit,
            "encryption": encryption
        }
```

---

## Testing Structured Questions

### Unit Testing Questions

```python
import pytest
from claude_mpm.utils.structured_questions import (
    QuestionBuilder,
    QuestionSet,
    QuestionValidationError,
    ResponseParser
)

def test_question_builder():
    """Test building a question."""
    question = (
        QuestionBuilder()
        .ask("Which framework?")
        .header("Framework")
        .add_option("FastAPI", "Modern async framework")
        .add_option("Flask", "Lightweight framework")
        .build()
    )

    assert question.question == "Which framework?"
    assert question.header == "Framework"
    assert len(question.options) == 2
    assert question.multi_select is False

def test_question_validation():
    """Test question validation."""
    with pytest.raises(QuestionValidationError, match="end with '\\?'"):
        QuestionBuilder().ask("No question mark").header("Test").build()

    with pytest.raises(QuestionValidationError, match="too long"):
        QuestionBuilder().ask("Test?").header("VeryLongHeader").build()

def test_response_parsing():
    """Test parsing AskUserQuestion responses."""
    question = (
        QuestionBuilder()
        .ask("Choose option?")
        .header("Choice")
        .add_option("A", "Option A")
        .add_option("B", "Option B")
        .build()
    )

    question_set = QuestionSet([question])
    parser = ResponseParser(question_set)

    # Test valid response
    response = {"answers": {"Choice": "A"}}
    answers = parser.parse(response)
    assert answers["Choice"] == "A"

    # Test missing answer
    response = {"answers": {}}
    answers = parser.parse(response)
    assert "Choice" not in answers
```

### Testing Templates

```python
def test_pr_workflow_template():
    """Test PRWorkflowTemplate context awareness."""
    from claude_mpm.templates.questions.pr_strategy import PRWorkflowTemplate

    # Single ticket, no CI
    template = PRWorkflowTemplate(num_tickets=1, has_ci=False)
    question_set = template.build()
    # Should only ask about draft preference
    assert len(question_set.questions) == 1
    assert question_set.questions[0].header == "Draft PRs"

    # Multiple tickets, CI configured
    template = PRWorkflowTemplate(num_tickets=3, has_ci=True)
    question_set = template.build()
    # Should ask all three questions
    assert len(question_set.questions) == 3
    headers = [q.header for q in question_set.questions]
    assert "PR Strategy" in headers
    assert "Draft PRs" in headers
    assert "Auto-merge" in headers

def test_custom_template():
    """Test custom template."""
    class TestTemplate(QuestionTemplate):
        def build(self) -> QuestionSet:
            q = QuestionBuilder().ask("Test?").header("Test").add_option("A", "A").add_option("B", "B").build()
            return QuestionSet([q])

    template = TestTemplate()
    question_set = template.build()
    assert len(question_set.questions) == 1
    assert question_set.questions[0].header == "Test"
```

### Integration Testing

```python
def test_agent_integration():
    """Test structured questions in agent workflow."""
    class TestAgent:
        def ask_user_question(self, params):
            # Simulate tool response
            return {"answers": {"Testing": "pytest"}}

        def choose_testing_framework(self):
            question = (
                QuestionBuilder()
                .ask("Which testing framework?")
                .header("Testing")
                .add_option("pytest", "Modern framework")
                .add_option("unittest", "Built-in framework")
                .build()
            )

            question_set = QuestionSet([question])
            params = question_set.to_ask_user_question_params()
            response = self.ask_user_question(params)

            parser = ResponseParser(question_set)
            answers = parser.parse(response)
            return answers.get("Testing")

    agent = TestAgent()
    result = agent.choose_testing_framework()
    assert result == "pytest"
```

---

## Best Practices

### 1. Use execute() for Automatic Fallback

```python
# ✅ GOOD: New API with automatic fallback
parsed = question_set.execute(response)
db = parsed.get("Database")

# ⚠️ ACCEPTABLE: Old API (but no automatic fallback)
parser = ResponseParser(question_set)
answers = parser.parse(response)
db = answers.get("Database")

# ❌ BAD: Disabling fallback without good reason
parsed = question_set.execute(response, use_fallback_if_needed=False)
```

**Why?** The new `execute()` API provides automatic fallback when AskUserQuestion fails, ensuring users can always answer questions even if Claude Code has bugs.

### 2. Handle Fallback Gracefully

```python
# ✅ GOOD: Works with both UI and text fallback
parsed = question_set.execute(response)
if parsed.was_answered("Database"):
    database = parsed.get("Database")
    self.configure_database(database)
else:
    # Use default if user skipped question
    database = "PostgreSQL"

# ❌ BAD: Assumes UI always works
database = response["answers"]["Database"]  # May fail if fallback triggered
```

### 3. Test Both Fallback Modes

```python
def test_with_ui_response():
    """Test when AskUserQuestion works."""
    response = {"answers": {"Database": "PostgreSQL"}}
    parsed = question_set.execute(response)
    assert parsed.get("Database") == "PostgreSQL"

def test_with_fallback():
    """Test fallback behavior."""
    # Empty response triggers fallback
    response = {"answers": {}}
    # In tests, disable fallback or mock input
    with mock.patch('builtins.input', return_value='1'):
        parsed = question_set.execute(response)
        assert parsed.get("Database") is not None
```

### 4. Always Validate Context

```python
# ✅ GOOD: Validate context before using
def use_template(self, num_tickets: int):
    if num_tickets < 1:
        raise ValueError("num_tickets must be >= 1")

    template = PRWorkflowTemplate(num_tickets=num_tickets)
    # ...

# ❌ BAD: No validation
def use_template(self, num_tickets: int):
    template = PRWorkflowTemplate(num_tickets=num_tickets)  # May fail
```

### 5. Handle Optional Answers

```python
# ✅ GOOD: Check if answer exists (new API)
parsed = question_set.execute(response)

if parsed.was_answered("Auto-merge"):
    auto_merge = parsed.get("Auto-merge") == "Enable auto-merge"
else:
    auto_merge = False  # Default value

# ⚠️ ACCEPTABLE: Old API
parser = ResponseParser(question_set)
answers = parser.parse(response)
if parser.was_answered(answers, "Auto-merge"):
    auto_merge = answers.get("Auto-merge") == "Enable auto-merge"

# ❌ BAD: Assume answer exists
auto_merge = answers["Auto-merge"] == "Enable auto-merge"  # May KeyError
```

### 6. Use Templates When Available

```python
# ✅ GOOD: Use existing template
from claude_mpm.templates.questions.pr_strategy import PRWorkflowTemplate
template = PRWorkflowTemplate(num_tickets=3)

# ❌ BAD: Recreate common question
question = QuestionBuilder().ask("Main-based or stacked PRs?")...
```

### 7. Limit Questions per Set

```python
# ✅ GOOD: Max 4 questions
questions = [q1, q2, q3, q4]
question_set = QuestionSet(questions)

# ❌ BAD: Too many questions
questions = [q1, q2, q3, q4, q5]  # Will raise QuestionValidationError
```

### 8. Provide Clear Descriptions

```python
# ✅ GOOD: Clear, informative descriptions
.add_option(
    "FastAPI",
    "Modern async framework with automatic API documentation and type safety"
)

# ❌ BAD: Vague descriptions
.add_option("FastAPI", "A framework")
```

### 9. Use Appropriate Headers

```python
# ✅ GOOD: Short, clear header (max 12 chars)
.header("Framework")
.header("Testing")
.header("CI/CD")

# ❌ BAD: Too long or unclear
.header("FrameworkChoice")  # Too long (15 chars)
.header("Q1")  # Unclear
```

---

## Common Patterns

### Pattern: Multi-Step Workflow

```python
class ProjectInitAgent:
    def initialize_project(self):
        """Multi-step project initialization."""
        # Step 1: Project type and language
        type_answers = self.ask_project_type()

        # Step 2: Development workflow (uses answers from step 1)
        workflow_answers = self.ask_development_workflow(
            language=type_answers.get("Language")
        )

        # Step 3: Framework selection (uses answers from steps 1 and 2)
        framework_answers = self.ask_frameworks(
            project_type=type_answers.get("Project Type"),
            language=type_answers.get("Language")
        )

        # Combine all answers
        return {
            **type_answers,
            **workflow_answers,
            **framework_answers
        }
```

### Pattern: Conditional Follow-up Questions

```python
def configure_deployment(self):
    """Ask deployment questions with conditional follow-ups."""
    # Ask about cloud provider
    cloud_answer = self.ask_cloud_provider()

    # Follow-up questions based on answer
    if cloud_answer == "AWS":
        # Ask AWS-specific questions
        return self.ask_aws_configuration()
    elif cloud_answer == "GCP":
        # Ask GCP-specific questions
        return self.ask_gcp_configuration()
    else:
        # Generic configuration
        return self.ask_generic_configuration()
```

### Pattern: Multi-Select for Features

```python
def select_features_to_implement(self):
    """Let user select multiple features."""
    features_question = (
        QuestionBuilder()
        .ask("Which features should we implement? (Select all)")
        .header("Features")
        .add_option("Auth", "User authentication")
        .add_option("Search", "Full-text search")
        .add_option("Analytics", "Usage analytics")
        .add_option("Export", "Data export")
        .multi_select(enabled=True)
        .build()
    )

    question_set = QuestionSet([features_question])
    params = question_set.to_ask_user_question_params()
    response = self.ask_user_question(params)

    parser = ResponseParser(question_set)
    answers = parser.parse(response)

    selected_features = answers.get("Features")  # List of selected options
    return selected_features  # ["Auth", "Search", "Analytics"]
```

---

## Migration Guide

### Migrating to execute() API

The new `execute()` API provides automatic fallback and a cleaner interface. Here's how to migrate:

#### Before (Old API)

```python
from claude_mpm.utils.structured_questions import (
    QuestionBuilder,
    QuestionSet,
    ResponseParser
)

# Build questions
question = QuestionBuilder().ask("Question?").header("Q").add_option("A", "A").add_option("B", "B").build()
question_set = QuestionSet([question])

# Get params and ask user
params = question_set.to_ask_user_question_params()
response = self.ask_user_question(params)

# Parse manually
parser = ResponseParser(question_set)
answers = parser.parse(response)

# Access answers
choice = answers.get("Q")
if "Q" in answers:
    # Use answer
    pass
```

#### After (New API)

```python
from claude_mpm.utils.structured_questions import (
    QuestionBuilder,
    QuestionSet
)

# Build questions (same as before)
question = QuestionBuilder().ask("Question?").header("Q").add_option("A", "A").add_option("B", "B").build()
question_set = QuestionSet([question])

# Get params and ask user (same as before)
params = question_set.to_ask_user_question_params()
response = self.ask_user_question(params)

# Execute with automatic fallback
parsed = question_set.execute(response)

# Access answers (cleaner API)
choice = parsed.get("Q")
if parsed.was_answered("Q"):
    # Use answer
    pass
```

#### Key Changes

**Imports:**
- Remove `ResponseParser` import (no longer needed)
- Keep `QuestionBuilder` and `QuestionSet`

**Response Handling:**
```python
# Old
parser = ResponseParser(question_set)
answers = parser.parse(response)
value = answers.get("Header")
exists = "Header" in answers

# New
parsed = question_set.execute(response)
value = parsed.get("Header")
exists = parsed.was_answered("Header")
```

**Benefits of Migration:**

1. **Automatic fallback**: Questions work even when AskUserQuestion fails
2. **Cleaner syntax**: No need to construct `ResponseParser`
3. **Better API**: `parsed.get()` vs `answers.get()`, `parsed.was_answered()` vs `"Header" in answers`
4. **Same functionality**: All existing features still work

**Backward Compatibility:**

The old `ResponseParser` API is **fully supported** and will continue to work. Migration is **optional but recommended** for new code.

### Testing Fallback Behavior

When writing tests for code using `execute()`:

```python
import pytest
from unittest import mock

def test_with_successful_response():
    """Test normal AskUserQuestion response."""
    response = {"answers": {"Database": "PostgreSQL"}}
    parsed = question_set.execute(response)
    assert parsed.get("Database") == "PostgreSQL"

def test_with_failed_response_fallback():
    """Test automatic fallback when AskUserQuestion fails."""
    # Empty response triggers fallback
    response = {"answers": {}}

    # Mock user input for fallback
    with mock.patch('builtins.input', return_value='1'):
        parsed = question_set.execute(response)
        # Verify fallback worked
        assert parsed.was_answered("Database")

def test_with_fallback_disabled():
    """Test error when fallback is disabled."""
    response = {"answers": {}}

    with pytest.raises(QuestionValidationError):
        parsed = question_set.execute(response, use_fallback_if_needed=False)
```

### Handling Custom Answers

Both APIs support custom answers (when user selects "Other"):

```python
# Old API
parser = ResponseParser(question_set)
answers = parser.parse(response)
database = answers.get("Database")
if database not in ["PostgreSQL", "MongoDB"]:
    # Custom answer
    print(f"Custom database: {database}")

# New API
parsed = question_set.execute(response)
database = parsed.get("Database")
if database not in ["PostgreSQL", "MongoDB"]:
    # Custom answer
    print(f"Custom database: {database}")
```

---

## Related Documentation

- **[User Guide](../guides/structured-questions.md)** - User-facing documentation
- **[API Reference](../reference/structured-questions-api.md)** - Complete API documentation
- **[Template Catalog](../reference/structured-questions-templates.md)** - Available templates
- **[Design Document](../design/structured-questions-design.md)** - Architecture decisions

---

**For Complete Examples**: See [EXAMPLES.md](../../src/claude_mpm/templates/questions/EXAMPLES.md) for full integration examples and workflows.
