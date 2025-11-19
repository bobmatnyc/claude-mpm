# Structured Questions Integration Examples

This document provides concrete examples of how to use the structured questions framework in PM agent workflows.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [PR Workflow Examples](#pr-workflow-examples)
3. [Project Initialization Examples](#project-initialization-examples)
4. [Ticket Management Examples](#ticket-management-examples)
5. [Custom Questions](#custom-questions)
6. [Best Practices](#best-practices)

## Basic Usage

### Minimal Example

```python
from claude_mpm.utils.structured_questions import QuestionBuilder, QuestionSet

# Build a simple question
question = (
    QuestionBuilder()
    .ask("Which testing approach should we use?")
    .header("Testing")
    .add_option("TDD", "Test-driven development with tests first")
    .add_option("TAD", "Test after development, implementation first")
    .build()
)

# Create question set and get parameters
question_set = QuestionSet([question])
params = question_set.to_ask_user_question_params()

# Use params with AskUserQuestion tool
# ...response from tool...

# Parse response
from claude_mpm.utils.structured_questions import ResponseParser
parser = ResponseParser(question_set)
answers = parser.parse(response)
testing_approach = answers.get("Testing")  # "TDD" or "TAD"
```

## PR Workflow Examples

### Example 1: Single Ticket PR Workflow

When user requests a single PR:

```python
from claude_mpm.templates.questions.pr_strategy import PRWorkflowTemplate

# Only 1 ticket, no CI
template = PRWorkflowTemplate(num_tickets=1, has_ci=False)
params = template.to_params()

# This will ONLY ask about draft PR preference
# (skips workflow question since num_tickets=1)
# (skips auto-merge question since has_ci=False)
```

**Expected Questions:**
- "Should PRs be created as drafts initially?" (Draft PRs)

### Example 2: Multiple Tickets with CI

When user requests PRs for multiple tickets with CI configured:

```python
from claude_mpm.templates.questions.pr_strategy import PRWorkflowTemplate

# Check if CI exists (PM reads .github/workflows/ or .gitlab-ci.yml)
has_ci = True  # Found .github/workflows/ci.yml

# 3 tickets, CI configured
template = PRWorkflowTemplate(num_tickets=3, has_ci=True)
params = template.to_params()

# Use AskUserQuestion tool with params
# ... get response ...

# Parse answers
from claude_mpm.utils.structured_questions import ResponseParser
parser = ResponseParser(template.build())
answers = parser.parse(response)

# Extract user preferences
pr_strategy = answers.get("PR Strategy")      # "Main-based PRs" or "Stacked PRs"
draft_mode = answers.get("Draft PRs")         # "Yes, as drafts" or "No, ready for review"
auto_merge = answers.get("Auto-merge")        # "Enable auto-merge" or "Manual merge only"

# Delegate to version-control with preferences
delegation_params = {
    "stacked": pr_strategy == "Stacked PRs",
    "draft": draft_mode == "Yes, as drafts",
    "auto_merge": auto_merge == "Enable auto-merge",
    "tickets": ["MPM-101", "MPM-102", "MPM-103"]
}
```

**Expected Questions:**
1. "How should we organize the pull requests?" (PR Strategy)
2. "Should PRs be created as drafts initially?" (Draft PRs)
3. "Should PRs auto-merge after CI passes and approval?" (Auto-merge)

### Example 3: PR Size Management

For large feature PRs:

```python
from claude_mpm.templates.questions.pr_strategy import PRSizeTemplate

# Estimated 600 LOC changes
template = PRSizeTemplate(estimated_changes=600)
params = template.to_params()

# Parse response
answers = parser.parse(response)
split_strategy = answers.get("PR Size")  # "Single large PR", "Split by component", etc.
```

## Project Initialization Examples

### Example 4: New Project Setup

During `/mpm-init` command:

```python
from claude_mpm.templates.questions.project_init import (
    ProjectTypeTemplate,
    DevelopmentWorkflowTemplate,
    FrameworkTemplate
)

# Step 1: Ask about project type
project_template = ProjectTypeTemplate(existing_files=False)
params1 = project_template.to_params()
# ... get response ...
answers1 = parser1.parse(response1)
project_type = answers1.get("Project Type")  # "Web Application", "API Service", etc.
language = answers1.get("Language")  # "Python", "JavaScript/TypeScript", etc.

# Step 2: Ask about development workflow
workflow_template = DevelopmentWorkflowTemplate(
    project_type=project_type,
    language=language
)
params2 = workflow_template.to_params()
# ... get response ...
answers2 = parser2.parse(response2)
testing_framework = answers2.get("Testing")  # "pytest", "unittest", "Jest", etc.
cicd_choice = answers2.get("CI/CD")  # "Yes, with GitHub Actions", etc.

# Step 3: Ask about frameworks (conditional)
framework_template = FrameworkTemplate(
    project_type=project_type,
    language=language
)
params3 = framework_template.to_params()
# ... get response ...
answers3 = parser3.parse(response3)
framework = answers3.get("Framework")  # "FastAPI", "Flask", "Django", etc.
database = answers3.get("Database")    # "PostgreSQL", "MongoDB", etc.

# Use all answers to configure project
project_config = {
    "type": project_type,
    "language": language,
    "testing": testing_framework,
    "ci_cd": cicd_choice,
    "framework": framework,
    "database": database
}
```

### Example 5: Existing Project Detection

When project has existing files:

```python
from claude_mpm.templates.questions.project_init import ProjectTypeTemplate

# PM detected Python files
detected_language = "Python"

# Only ask about project type, skip language question
template = ProjectTypeTemplate(
    existing_files=True,
    detected_language=detected_language
)
params = template.to_params()

# Will only ask: "What type of project is this?"
# Skips language question since it was detected
```

## Ticket Management Examples

### Example 6: Sprint Planning with Dependencies

Planning a sprint with 5 dependent tickets:

```python
from claude_mpm.templates.questions.ticket_mgmt import TicketPrioritizationTemplate

# 5 tickets, some depend on others, solo developer
template = TicketPrioritizationTemplate(
    num_tickets=5,
    has_dependencies=True,
    team_size=1
)
params = template.to_params()

# Parse response
answers = parser.parse(response)
dep_strategy = answers.get("Dependencies")  # "Sequential execution" or "Parallel where possible"
exec_strategy = answers.get("Execution")    # "One at a time" or "Parallel execution"

# Use answers to create execution plan
if dep_strategy == "Sequential execution":
    # Order tickets by dependency chain
    execution_order = ["MPM-101", "MPM-102", "MPM-103", "MPM-104", "MPM-105"]
else:
    # Identify independent tickets for parallel work
    parallel_tickets = ["MPM-101", "MPM-103"]  # Independent
    sequential_tickets = ["MPM-102", "MPM-104", "MPM-105"]  # Dependent
```

### Example 7: Production Feature Scope

Defining scope for user-facing production feature:

```python
from claude_mpm.templates.questions.ticket_mgmt import TicketScopeTemplate

# User-facing feature for production
template = TicketScopeTemplate(
    ticket_type="feature",
    is_user_facing=True,
    project_maturity="production"
)
params = template.to_params()

# Parse response
answers = parser.parse(response)
testing_level = answers.get("Testing")  # "Comprehensive", "Standard", "Basic"
docs_level = answers.get("Docs")        # "Full documentation", "API docs only", etc.

# Define completeness criteria
completion_criteria = {
    "testing": testing_level,
    "documentation": docs_level,
    "code_review": True,  # Always required for production
    "ci_passing": True    # Always required for production
}
```

### Example 8: Handling Blockers

Managing blocked tickets:

```python
from claude_mpm.templates.questions.ticket_mgmt import TicketDependencyTemplate

# 2 tickets blocked by external API dependency
template = TicketDependencyTemplate(
    blocked_tickets=2,
    blocking_type="external"
)
params = template.to_params()

# Parse response
answers = parser.parse(response)
blocker_strategy = answers.get("Blockers")  # "Wait for unblock", "Mock and continue", etc.

# Adjust sprint plan based on strategy
if blocker_strategy == "Mock and continue":
    # Create mock API, continue development
    plan = "Create mock API responses, implement features, swap for real API later"
elif blocker_strategy == "Wait for unblock":
    # Work on other tickets first
    plan = "Deprioritize blocked tickets, focus on unblocked work"
```

## Custom Questions

### Example 9: Custom Deployment Question

Creating a custom question for specific use case:

```python
from claude_mpm.utils.structured_questions import QuestionBuilder, QuestionSet

# Build custom deployment question
deployment_question = (
    QuestionBuilder()
    .ask("Which cloud provider should we deploy to?")
    .header("Cloud")
    .add_option("AWS", "Amazon Web Services with EC2/ECS")
    .add_option("GCP", "Google Cloud Platform with Cloud Run")
    .add_option("Azure", "Microsoft Azure with App Service")
    .add_option("Vercel", "Vercel for serverless Next.js apps")
    .build()
)

region_question = (
    QuestionBuilder()
    .ask("Which region should be the primary deployment?")
    .header("Region")
    .add_option("us-east-1", "US East (Virginia) - lowest latency for East Coast")
    .add_option("us-west-2", "US West (Oregon) - lowest latency for West Coast")
    .add_option("eu-west-1", "EU West (Ireland) - GDPR compliant, EU users")
    .build()
)

# Combine into question set
question_set = QuestionSet([deployment_question, region_question])
params = question_set.to_ask_user_question_params()
```

### Example 10: Multi-Select Question

Using multi-select for selecting multiple features:

```python
from claude_mpm.utils.structured_questions import QuestionBuilder

# User can select multiple features to implement
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

question_set = QuestionSet([features_question])
params = question_set.to_ask_user_question_params()

# Parse multi-select response
answers = parser.parse(response)
selected_features = answers.get("Features")  # List: ["Auth", "Search", "Analytics"]

# Create tickets for each selected feature
for feature in selected_features:
    # Create ticket for feature
    pass
```

## Best Practices

### 1. Context-Aware Questions

Always provide relevant context to templates:

```python
# ✅ GOOD: Provide context for relevant questions
template = PRWorkflowTemplate(
    num_tickets=len(tickets),
    has_ci=check_for_ci_config()  # Actually check for CI
)

# ❌ BAD: Hardcoded or missing context
template = PRWorkflowTemplate(num_tickets=1, has_ci=True)  # Wrong if 3 tickets
```

### 2. Parse Before Using

Always parse responses before using answers:

```python
# ✅ GOOD: Parse and validate
parser = ResponseParser(question_set)
answers = parser.parse(response)
if answers.get("Testing") == "Comprehensive":
    # Use validated answer

# ❌ BAD: Direct access without parsing
testing_choice = response["answers"]["Testing"]  # May not exist or be invalid
```

### 3. Handle Optional Answers

Not all questions may be answered:

```python
# ✅ GOOD: Check if answered
if parser.was_answered(answers, "Auto-merge"):
    auto_merge = answers.get("Auto-merge") == "Enable auto-merge"
else:
    auto_merge = False  # Default if not answered

# ❌ BAD: Assume always answered
auto_merge = answers["Auto-merge"] == "Enable auto-merge"  # May KeyError
```

### 4. Use Templates When Available

Don't recreate common questions:

```python
# ✅ GOOD: Use existing template
from claude_mpm.templates.questions.pr_strategy import PRWorkflowTemplate
template = PRWorkflowTemplate(num_tickets=3)

# ❌ BAD: Recreate common question
question = QuestionBuilder().ask("Main-based or stacked PRs?")...  # Template exists
```

### 5. Validate Context

Ensure context values are valid:

```python
# ✅ GOOD: Validate before creating template
num_tickets = max(1, len(tickets))  # Ensure >= 1
template = TicketPrioritizationTemplate(num_tickets=num_tickets)

# ❌ BAD: Invalid context
template = TicketPrioritizationTemplate(num_tickets=0)  # May cause issues
```

## Complete Workflow Example

Here's a complete PM workflow using structured questions:

```python
from claude_mpm.templates.questions.pr_strategy import PRWorkflowTemplate
from claude_mpm.utils.structured_questions import ResponseParser

# User requests: "Create PRs for MPM-101, MPM-102, MPM-103"

# Step 1: Gather context
tickets = ["MPM-101", "MPM-102", "MPM-103"]
num_tickets = len(tickets)
has_ci = check_for_ci_files()  # Check .github/workflows/

# Step 2: Build and ask questions
template = PRWorkflowTemplate(num_tickets=num_tickets, has_ci=has_ci)
params = template.to_params()
# ... use AskUserQuestion tool with params ...

# Step 3: Parse response
parser = ResponseParser(template.build())
answers = parser.parse(response)

# Step 4: Extract preferences
pr_strategy = answers.get("PR Strategy")  # "Main-based PRs" or "Stacked PRs"
draft_mode = answers.get("Draft PRs") == "Yes, as drafts"
auto_merge = answers.get("Auto-merge") == "Enable auto-merge" if has_ci else False

# Step 5: Delegate to version-control agent
delegation_task = {
    "action": "create_prs",
    "tickets": tickets,
    "strategy": "stacked" if pr_strategy == "Stacked PRs" else "main-based",
    "draft": draft_mode,
    "auto_merge": auto_merge,
}

# Delegate to version-control agent with structured parameters
# Task tool with delegation_task
```

## Error Handling

Handle validation errors gracefully:

```python
from claude_mpm.utils.structured_questions import QuestionValidationError

try:
    question = (
        QuestionBuilder()
        .ask("Invalid question without question mark")  # Missing '?'
        .header("Test")
        .add_option("A", "Option A")
        .add_option("B", "Option B")
        .build()
    )
except QuestionValidationError as e:
    # Handle validation error
    print(f"Question validation failed: {e}")
    # Fix and retry or use fallback
```

## Summary

Structured questions provide:
- **Type Safety**: Validated at construction time
- **Consistency**: Reusable templates for common workflows
- **Context-Awareness**: Questions adapt based on situation
- **Better UX**: Clear, well-formatted questions for users
- **Maintainability**: Centralized question logic

Use templates for common cases, build custom questions for specific needs, and always validate responses before use.
