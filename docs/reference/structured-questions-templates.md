# Structured Questions Template Catalog

Complete reference of available question templates and when to use them.

## Table of Contents

1. [Template Overview](#template-overview)
2. [PR Strategy Templates](#pr-strategy-templates)
3. [Project Initialization Templates](#project-initialization-templates)
4. [Ticket Management Templates](#ticket-management-templates)
5. [Template Customization](#template-customization)
6. [Creating Custom Templates](#creating-custom-templates)

## Template Overview

Templates provide pre-built, context-aware questions for common workflows. Each template:

- **Adapts based on context**: Only asks relevant questions
- **Validates inputs**: Ensures proper parameters provided
- **Follows best practices**: Industry-standard options and descriptions
- **Simplifies integration**: Ready-to-use in agent code

### Template Categories

| Category | Templates | Use Case |
|----------|-----------|----------|
| **PR Strategy** | PRWorkflowTemplate, PRSizeTemplate, PRReviewTemplate | Pull request workflows and preferences |
| **Project Init** | ProjectTypeTemplate, DevelopmentWorkflowTemplate, FrameworkTemplate | New project setup and configuration |
| **Ticket Management** | TicketPrioritizationTemplate, TicketScopeTemplate, TicketDependencyTemplate | Sprint planning and ticket execution |

---

## PR Strategy Templates

### PRWorkflowTemplate

**Purpose**: Gather PR workflow preferences (main-based vs stacked, draft mode, auto-merge)

**Location**: `claude_mpm.templates.questions.pr_strategy.PRWorkflowTemplate`

#### Context Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `num_tickets` | int | 1 | Number of tickets being worked on |
| `has_ci` | bool | False | Whether CI/CD is configured |

#### Questions Asked

The template conditionally asks 1-3 questions based on context:

1. **PR Strategy** (header: "PR Strategy")
   - **When**: Only if `num_tickets > 1`
   - **Question**: "How should we organize the pull requests?"
   - **Options**:
     - "Main-based PRs" - Each ticket gets its own PR against main (parallel work)
     - "Stacked PRs" - PRs build on each other sequentially (ticket-1 → ticket-2 → ticket-3)

2. **Draft PRs** (header: "Draft PRs")
   - **When**: Always asked
   - **Question**: "Should PRs be created as drafts initially?"
   - **Options**:
     - "Yes, as drafts" - Create as draft PRs, mark ready when implementation complete
     - "No, ready for review" - Create as regular PRs ready for immediate review

3. **Auto-merge** (header: "Auto-merge")
   - **When**: Only if `has_ci == True`
   - **Question**: "Should PRs auto-merge after CI passes and approval?"
   - **Options**:
     - "Enable auto-merge" - PRs merge automatically after CI passes and approval
     - "Manual merge only" - PRs require manual merge even after approval

#### Usage Example

```python
from claude_mpm.templates.questions.pr_strategy import PRWorkflowTemplate
from claude_mpm.utils.structured_questions import ResponseParser

# Context: 3 tickets, CI configured
template = PRWorkflowTemplate(num_tickets=3, has_ci=True)
params = template.to_params()

# Use with AskUserQuestion tool
# ... get response ...

# Parse response
parser = ResponseParser(template.build())
answers = parser.parse(response)

pr_strategy = answers.get("PR Strategy")  # "Main-based PRs" or "Stacked PRs"
draft_mode = answers.get("Draft PRs") == "Yes, as drafts"
auto_merge = answers.get("Auto-merge") == "Enable auto-merge"
```

#### Context Decision Logic

```python
# Single ticket, no CI → Only asks about draft preference
template = PRWorkflowTemplate(num_tickets=1, has_ci=False)
# Questions: Draft PRs only

# Multiple tickets, no CI → Asks about strategy and draft
template = PRWorkflowTemplate(num_tickets=3, has_ci=False)
# Questions: PR Strategy, Draft PRs

# Multiple tickets, CI configured → Asks all questions
template = PRWorkflowTemplate(num_tickets=3, has_ci=True)
# Questions: PR Strategy, Draft PRs, Auto-merge
```

---

### PRSizeTemplate

**Purpose**: Gather preferences about PR size and splitting large changes

**Location**: `claude_mpm.templates.questions.pr_strategy.PRSizeTemplate`

#### Context Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `estimated_changes` | int | 0 | Estimated lines of code changed |

#### Questions Asked

1. **PR Size** (header: "PR Size")
   - **When**: Only if `estimated_changes > 300`
   - **Question**: "This feature involves significant changes. How should we split it?"
   - **Options**:
     - "Single large PR" - Keep all changes together in one comprehensive PR
     - "Split by component" - Create separate PRs for each major component
     - "Split by feature" - Create separate PRs for each sub-feature

2. **Commits** (header: "Commits") - **Fallback**
   - **When**: If `estimated_changes <= 300`
   - **Question**: "How should commits be organized?"
   - **Options**:
     - "Atomic commits" - Many small, focused commits (one per logical change)
     - "Feature commits" - Fewer, larger commits (one per feature/component)

#### Usage Example

```python
from claude_mpm.templates.questions.pr_strategy import PRSizeTemplate

# Large feature (600 LOC)
template = PRSizeTemplate(estimated_changes=600)
params = template.to_params()

# Parse response
answers = parser.parse(response)
split_strategy = answers.get("PR Size")  # "Single large PR", "Split by component", etc.
```

---

### PRReviewTemplate

**Purpose**: Gather PR review and approval preferences

**Location**: `claude_mpm.templates.questions.pr_strategy.PRReviewTemplate`

#### Context Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `team_size` | int | 1 | Number of team members available for review |
| `is_critical` | bool | False | Whether changes are critical/sensitive |

#### Questions Asked

1. **Approvals** (header: "Approvals")
   - **When**: Only if `team_size > 1`
   - **Question**: "How many approvals should be required before merging?"
   - **Options**:
     - "1 approval" - Single approval sufficient (faster iteration)
     - "2 approvals" - Two approvals required (more thorough review)

2. **Review When** (header: "Review When")
   - **When**: Always asked
   - **Question**: "When should review be requested?"
   - **Options**:
     - "After implementation" - Request review only when all code is complete
     - "Early feedback" - Request early review for approach validation

#### Usage Example

```python
from claude_mpm.templates.questions.pr_strategy import PRReviewTemplate

# Team of 5, critical changes
template = PRReviewTemplate(team_size=5, is_critical=True)
params = template.to_params()

answers = parser.parse(response)
num_approvals = 1 if answers.get("Approvals") == "1 approval" else 2
review_timing = answers.get("Review When")
```

---

## Project Initialization Templates

### ProjectTypeTemplate

**Purpose**: Determine project type and primary language during initialization

**Location**: `claude_mpm.templates.questions.project_init.ProjectTypeTemplate`

#### Context Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `existing_files` | bool | False | Whether project has existing files |
| `detected_language` | str \| None | None | Auto-detected language from existing files |

#### Questions Asked

1. **Project Type** (header: "Project Type")
   - **When**: Always asked
   - **Question**: "What type of project is this?"
   - **Options**:
     - "Web Application" - Full-stack web app with frontend and backend
     - "API Service" - Backend API or microservice
     - "Library/Package" - Reusable library or package for distribution
     - "CLI Tool" - Command-line application or tool

2. **Language** (header: "Language")
   - **When**: Only if `detected_language is None`
   - **Question**: "What is the primary programming language?"
   - **Options**:
     - "Python" - Python 3.8+ for backend, scripts, or data processing
     - "JavaScript/TypeScript" - JavaScript or TypeScript for Node.js or full-stack
     - "Go" - Go for high-performance services and tools
     - "Rust" - Rust for systems programming and performance-critical code

#### Usage Example

```python
from claude_mpm.templates.questions.project_init import ProjectTypeTemplate

# New project, no existing code
template = ProjectTypeTemplate(existing_files=False)
# Asks: Project Type + Language

# Existing Python project
template = ProjectTypeTemplate(existing_files=True, detected_language="Python")
# Asks: Project Type only (language already detected)

answers = parser.parse(response)
project_type = answers.get("Project Type")
language = answers.get("Language") or "Python"  # Use detected if not asked
```

---

### DevelopmentWorkflowTemplate

**Purpose**: Gather development workflow preferences (testing, CI/CD)

**Location**: `claude_mpm.templates.questions.project_init.DevelopmentWorkflowTemplate`

#### Context Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_type` | str \| None | None | Type of project (from ProjectTypeTemplate) |
| `language` | str \| None | None | Primary language (from ProjectTypeTemplate) |

#### Questions Asked

1. **Testing** (header: "Testing")
   - **When**: Always asked
   - **Question**: Varies by language
   - **Python Options**:
     - "pytest" - Modern, feature-rich testing with fixtures and plugins
     - "unittest" - Python's built-in testing framework (standard library)
   - **JavaScript/TypeScript Options**:
     - "Jest" - Popular, batteries-included testing framework
     - "Vitest" - Fast, modern testing with native ESM support
   - **Generic Options** (other languages):
     - "High coverage (80%+)" - Comprehensive testing with strict coverage requirements
     - "Moderate coverage (60%+)" - Good testing balance between speed and thoroughness

2. **CI/CD** (header: "CI/CD")
   - **When**: Always asked
   - **Question**: "Should we set up CI/CD from the start?"
   - **Options**:
     - "Yes, with GitHub Actions" - Automated testing and deployment using GitHub Actions
     - "Yes, with GitLab CI" - Automated testing and deployment using GitLab CI
     - "Not yet" - Set up CI/CD later when project is more mature

#### Usage Example

```python
from claude_mpm.templates.questions.project_init import DevelopmentWorkflowTemplate

# Python API service
template = DevelopmentWorkflowTemplate(
    project_type="API Service",
    language="Python"
)

answers = parser.parse(response)
testing_framework = answers.get("Testing")  # "pytest" or "unittest"
ci_cd = answers.get("CI/CD")  # "Yes, with GitHub Actions", etc.
```

---

### FrameworkTemplate

**Purpose**: Select frameworks and databases based on project type and language

**Location**: `claude_mpm.templates.questions.project_init.FrameworkTemplate`

#### Context Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_type` | str \| None | None | Type of project |
| `language` | str \| None | None | Primary language |

#### Questions Asked

Questions vary significantly based on context:

**Python Web/API Projects:**

1. **Framework** (header: "Framework")
   - **When**: Python + (Web or API)
   - **Question**: "Which Python web framework should we use?"
   - **Options**:
     - "FastAPI" - Modern, fast framework with automatic API documentation
     - "Flask" - Lightweight, flexible micro-framework
     - "Django" - Full-featured framework with batteries included

**JavaScript/TypeScript Web Projects:**

1. **Framework** (header: "Framework")
   - **When**: JS/TS + Web
   - **Question**: "Which frontend framework should we use?"
   - **Options**:
     - "React" - Popular, component-based UI library with large ecosystem
     - "Vue" - Progressive framework with gentle learning curve
     - "Next.js" - React framework with SSR, routing, and optimization
     - "Svelte" - Compiled framework with minimal runtime overhead

**All Web/API Projects:**

2. **Database** (header: "Database")
   - **When**: Web or API project type
   - **Question**: "What database should we use?"
   - **Options**:
     - "PostgreSQL" - Robust relational database with advanced features
     - "MongoDB" - Flexible NoSQL document database
     - "SQLite" - Lightweight embedded database (good for prototypes)
     - "Redis" - In-memory data store for caching and real-time features

**Fallback (other projects):**

1. **Tooling** (header: "Tooling")
   - **When**: No specific framework questions applicable
   - **Question**: "What development tools should we prioritize?"
   - **Options**:
     - "Code quality" - Linters, formatters, and static analysis tools
     - "Testing" - Comprehensive testing framework and coverage tools
     - "Documentation" - API docs, code docs, and documentation generators

#### Usage Example

```python
from claude_mpm.templates.questions.project_init import FrameworkTemplate

# Python web application
template = FrameworkTemplate(
    project_type="Web Application",
    language="Python"
)

answers = parser.parse(response)
framework = answers.get("Framework")  # "FastAPI", "Flask", or "Django"
database = answers.get("Database")    # "PostgreSQL", "MongoDB", etc.
```

---

## Ticket Management Templates

### TicketPrioritizationTemplate

**Purpose**: Determine ticket execution order and prioritization strategy

**Location**: `claude_mpm.templates.questions.ticket_mgmt.TicketPrioritizationTemplate`

#### Context Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `num_tickets` | int | 1 | Number of tickets to prioritize |
| `has_dependencies` | bool | False | Whether tickets have interdependencies |
| `team_size` | int | 1 | Number of engineers available |

#### Questions Asked

1. **Dependencies/Priority** (header varies)
   - **When**: `num_tickets > 1`
   - **If `has_dependencies == True`**:
     - Header: "Dependencies"
     - Question: "How should we handle ticket dependencies?"
     - Options:
       - "Sequential execution" - Complete tickets in dependency order (foundational work first)
       - "Parallel where possible" - Work on independent tickets in parallel, sequential for dependent ones
   - **If `has_dependencies == False`**:
     - Header: "Priority"
     - Question: "How should we prioritize the tickets?"
     - Options:
       - "User-visible first" - Prioritize features that directly impact users
       - "Infrastructure first" - Build foundational components before user-facing features
       - "Quick wins first" - Start with easiest tickets to build momentum
       - "High risk first" - Tackle uncertain/risky tickets early to derisk project

2. **Execution** (header: "Execution")
   - **When**: `num_tickets > 1` and `team_size >= 1`
   - **Question**: "How should tickets be executed?"
   - **Options**:
     - "One at a time" - Complete each ticket fully before starting the next
     - "Parallel execution" - Work on multiple tickets simultaneously when possible

3. **Criteria** (header: "Criteria") - **Fallback**
   - **When**: Single ticket or no other questions applicable
   - **Question**: "What should be the ticket completion criteria?"
   - **Options**:
     - "Implementation only" - Code implementation complete, basic functionality working
     - "Implementation + tests" - Code complete with passing unit tests

#### Usage Example

```python
from claude_mpm.templates.questions.ticket_mgmt import TicketPrioritizationTemplate

# 5 tickets, dependencies exist, solo developer
template = TicketPrioritizationTemplate(
    num_tickets=5,
    has_dependencies=True,
    team_size=1
)

answers = parser.parse(response)
dep_strategy = answers.get("Dependencies")  # "Sequential execution" or "Parallel where possible"
exec_strategy = answers.get("Execution")    # "One at a time" or "Parallel execution"
```

---

### TicketScopeTemplate

**Purpose**: Define testing and documentation requirements for tickets

**Location**: `claude_mpm.templates.questions.ticket_mgmt.TicketScopeTemplate`

#### Context Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ticket_type` | str | "feature" | Type of ticket (feature, bug, refactor) |
| `is_user_facing` | bool | False | Whether ticket affects end users |
| `project_maturity` | str | "development" | Project stage (prototype, development, production) |

#### Questions Asked

1. **Testing** (header: "Testing")
   - **When**: Always asked
   - **If `project_maturity == "production"` or `is_user_facing == True`**:
     - Question: "What testing is required for this ticket?"
     - Options:
       - "Comprehensive" - Unit tests, integration tests, and e2e tests required
       - "Standard" - Unit tests and integration tests for critical paths
       - "Basic" - Unit tests for core functionality only
   - **Otherwise**:
     - Question: "What testing is required for this ticket?"
     - Options:
       - "Unit tests" - Unit tests covering core functionality
       - "Integration tests" - Integration tests for component interactions
       - "Manual testing" - Manual verification sufficient for now

2. **Docs** (header: "Docs")
   - **When**: `is_user_facing == True` or `ticket_type == "feature"`
   - **Question**: "What documentation is needed?"
   - **Options**:
     - "Full documentation" - API docs, user guide, and code comments
     - "API docs only" - Document public interfaces and usage examples
     - "Code comments" - Inline comments for complex logic only
     - "None" - Code is self-documenting, no additional docs needed

#### Usage Example

```python
from claude_mpm.templates.questions.ticket_mgmt import TicketScopeTemplate

# User-facing production feature
template = TicketScopeTemplate(
    ticket_type="feature",
    is_user_facing=True,
    project_maturity="production"
)

answers = parser.parse(response)
testing_level = answers.get("Testing")  # "Comprehensive", "Standard", "Basic"
docs_level = answers.get("Docs")        # "Full documentation", "API docs only", etc.
```

---

### TicketDependencyTemplate

**Purpose**: Handle ticket dependencies and blocking issues

**Location**: `claude_mpm.templates.questions.ticket_mgmt.TicketDependencyTemplate`

#### Context Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `blocked_tickets` | int | 0 | Number of tickets currently blocked |
| `blocking_type` | str \| None | None | Type of blocker (technical, external, approval) |

#### Questions Asked

1. **Blockers** (header: "Blockers")
   - **When**: `blocked_tickets > 0`
   - **If `blocking_type == "external"`**:
     - Question: "How should we handle external dependencies?"
     - Options:
       - "Wait for unblock" - Pause blocked tickets until external dependency resolves
       - "Mock and continue" - Create mocks/stubs to continue development
       - "Work around" - Find alternative implementation to avoid dependency
   - **Otherwise**:
     - Question: "How should we handle blocked tickets?"
     - Options:
       - "Resolve blockers first" - Prioritize unblocking tickets before continuing
       - "Parallel work" - Work on unblocked tickets while resolving blockers

2. **Dependencies** (header: "Dependencies") - **Fallback**
   - **When**: No specific blockers
   - **Question**: "How should we manage ticket dependencies?"
   - **Options**:
     - "Strict ordering" - Maintain strict dependency order, wait for prerequisites
     - "Flexible approach" - Start dependent work in parallel with preparation work

#### Usage Example

```python
from claude_mpm.templates.questions.ticket_mgmt import TicketDependencyTemplate

# 2 tickets blocked by external API
template = TicketDependencyTemplate(
    blocked_tickets=2,
    blocking_type="external"
)

answers = parser.parse(response)
blocker_strategy = answers.get("Blockers")  # "Wait for unblock", "Mock and continue", etc.
```

---

## Template Customization

### Extending Existing Templates

You can extend existing templates to add custom logic:

```python
from claude_mpm.templates.questions.pr_strategy import PRWorkflowTemplate
from claude_mpm.utils.structured_questions import QuestionBuilder, QuestionSet

class CustomPRTemplate(PRWorkflowTemplate):
    def build(self) -> QuestionSet:
        # Get base questions
        base_questions = super().build()

        # Add custom question
        custom_question = (
            QuestionBuilder()
            .ask("Should we notify the team in Slack?")
            .header("Notify")
            .add_option("Yes", "Post PR links to #dev channel")
            .add_option("No", "Silent PR creation")
            .build()
        )

        # Combine and return
        base_questions.add(custom_question)
        return base_questions
```

### Overriding Context Logic

```python
from claude_mpm.templates.questions.base import ConditionalTemplate
from claude_mpm.utils.structured_questions import QuestionBuilder, QuestionSet

class CustomConditionalTemplate(ConditionalTemplate):
    def should_include_question(self, question_id: str) -> bool:
        # Custom logic
        if question_id == "advanced":
            return self.get_context("user_level") == "expert"
        return True

    def build(self) -> QuestionSet:
        questions = []

        if self.should_include_question("basic"):
            # Add basic question
            pass

        if self.should_include_question("advanced"):
            # Add advanced question
            pass

        return QuestionSet(questions)
```

---

## Creating Custom Templates

### Basic Custom Template

```python
from claude_mpm.templates.questions.base import QuestionTemplate
from claude_mpm.utils.structured_questions import QuestionBuilder, QuestionSet

class DeploymentTemplate(QuestionTemplate):
    """Template for deployment preferences."""

    def build(self) -> QuestionSet:
        cloud_question = (
            QuestionBuilder()
            .ask("Which cloud provider should we deploy to?")
            .header("Cloud")
            .add_option("AWS", "Amazon Web Services with EC2/ECS")
            .add_option("GCP", "Google Cloud Platform with Cloud Run")
            .add_option("Azure", "Microsoft Azure with App Service")
            .add_option("Vercel", "Vercel for serverless Next.js apps")
            .build()
        )

        return QuestionSet([cloud_question])
```

### Context-Aware Custom Template

```python
from claude_mpm.templates.questions.base import ConditionalTemplate
from claude_mpm.utils.structured_questions import QuestionBuilder, QuestionSet

class SecurityTemplate(ConditionalTemplate):
    """Template for security-related questions."""

    def __init__(self, is_public: bool = False, handles_pii: bool = False, **context):
        super().__init__(
            is_public=is_public,
            handles_pii=handles_pii,
            **context
        )

    def build(self) -> QuestionSet:
        questions = []

        # Always ask about authentication
        auth_question = (
            QuestionBuilder()
            .ask("What authentication method should we use?")
            .header("Auth")
            .add_option("OAuth2", "Standard OAuth2 with third-party providers")
            .add_option("JWT", "JSON Web Tokens for stateless auth")
            .add_option("Session", "Traditional session-based authentication")
            .build()
        )
        questions.append(auth_question)

        # Only ask about encryption if handling PII
        if self.get_context("handles_pii", False):
            encryption_question = (
                QuestionBuilder()
                .ask("What level of data encryption is required?")
                .header("Encryption")
                .add_option("At rest + in transit", "Encrypt data both stored and transmitted")
                .add_option("In transit only", "Encrypt only during transmission (HTTPS)")
                .build()
            )
            questions.append(encryption_question)

        return QuestionSet(questions)
```

### Multi-Select Custom Template

```python
from claude_mpm.templates.questions.base import QuestionTemplate
from claude_mpm.utils.structured_questions import QuestionBuilder, QuestionSet

class FeatureSelectionTemplate(QuestionTemplate):
    """Template for selecting multiple features to implement."""

    def build(self) -> QuestionSet:
        features_question = (
            QuestionBuilder()
            .ask("Which features should we prioritize? (Select all that apply)")
            .header("Features")
            .add_option("Auth", "User authentication and authorization")
            .add_option("Search", "Full-text search functionality")
            .add_option("Analytics", "Usage analytics and reporting")
            .add_option("Export", "Data export in multiple formats")
            .multi_select(enabled=True)  # Enable multi-select
            .build()
        )

        return QuestionSet([features_question])
```

---

## Related Documentation

- **[User Guide](../guides/structured-questions.md)** - User-friendly overview and examples
- **[API Reference](structured-questions-api.md)** - Complete API documentation
- **[Integration Guide](../developer/integrating-structured-questions.md)** - How to use templates in agents
- **[Design Document](../design/structured-questions-design.md)** - Architecture and design decisions

---

**For Complete Code Examples**: See [EXAMPLES.md](../../src/claude_mpm/templates/questions/EXAMPLES.md) for integration patterns and workflows.
