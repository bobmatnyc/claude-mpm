# Structured Questions Guide

User-friendly guide to understanding and using the structured questions framework in Claude MPM.

## Table of Contents

1. [Overview](#overview)
2. [Fallback Behavior](#fallback-behavior)
3. [When to Use Structured Questions](#when-to-use-structured-questions)
4. [Quick Start](#quick-start)
5. [Common Use Cases](#common-use-cases)
6. [Understanding Question Types](#understanding-question-types)
7. [Troubleshooting](#troubleshooting)
8. [FAQ](#faq)
9. [Related Documentation](#related-documentation)

## Overview

Structured questions provide a consistent, type-safe way for Claude MPM agents (especially the PM agent) to gather user preferences and make decisions about project workflows.

**What are structured questions?**

Instead of agents making assumptions or asking open-ended questions in conversation, structured questions present clear, multiple-choice options that:

- **Provide context**: Each option explains what it means and its implications
- **Enforce consistency**: Questions follow a standard format
- **Enable validation**: Responses are validated before processing
- **Support complex workflows**: Multiple related questions can be asked together

**Key Benefits:**

- **Better UX**: Clear options instead of freeform text
- **Fewer mistakes**: Validated inputs reduce errors
- **Consistent experience**: Same question format everywhere
- **Context-aware**: Questions adapt based on your project state

## Fallback Behavior

**Questions always work, even when the UI fails!**

The structured questions framework includes automatic fallback to text-based questions when the visual question UI (`AskUserQuestion` tool) is unavailable or broken. This ensures you can always answer questions and make progress, regardless of technical issues.

### What This Means for You

- **No interruptions**: Questions work even if Claude Code has bugs
- **Same experience**: Text-based fallback provides the same options
- **Flexible input**: Multiple ways to provide answers (see below)
- **Automatic detection**: System handles fallback transparently

### When Fallback Activates

Fallback automatically activates when:

- The `AskUserQuestion` tool is unavailable
- The tool returns empty or invalid responses
- Technical errors prevent the visual UI from working

**You don't need to do anything** - the system handles this automatically!

### Text-Based Fallback Format

When fallback mode is active, you'll see questions like this:

```
============================================================
📋 USER INPUT REQUIRED
(AskUserQuestion tool unavailable - using text fallback)
============================================================

=== Question 1 of 2 ===
[PR Strategy] How should we organize the pull requests?

Options:
1. Main-based PRs - Each ticket gets its own PR against main (parallel work)
2. Stacked PRs - PRs build on each other sequentially (ticket-1 → ticket-2 → ticket-3)

Your answer: 1

=== Question 2 of 2 ===
[Draft PRs] Should PRs be created as drafts?

Options:
1. Yes, as drafts - Create PRs in draft mode for early review
2. No, ready for review - Create PRs ready for immediate review

Your answer: Yes, as drafts
```

### How to Answer (Fallback Mode)

You have **multiple ways** to provide answers in fallback mode:

#### Single-Select Questions

**Option 1: Use numbers**
```
Your answer: 1
```

**Option 2: Use exact label**
```
Your answer: Main-based PRs
```

**Option 3: Use partial match** (case-insensitive)
```
Your answer: main-based
Your answer: stacked
```

**Option 4: Provide custom answer**
```
Your answer: Feature-branch workflow
```

#### Multi-Select Questions

**Comma-separated numbers:**
```
Your answer: 1,2,3
```

**Comma-separated labels:**
```
Your answer: Auth, Search, Analytics
```

**Mixed format:**
```
Your answer: 1, MongoDB, Custom Option
```

### Visual UI Mode (When Available)

When the visual UI works, you'll see interactive question cards instead:

```
PR Strategy: How should we organize the pull requests?
  ○ Main-based PRs - Each ticket gets its own PR against main (parallel work)
  ○ Stacked PRs - PRs build on each other sequentially (ticket-1 → ticket-2 → ticket-3)
```

**No configuration needed** - the system automatically uses the best available method!

## When to Use Structured Questions

Structured questions are ideal when:

### ✅ Use Structured Questions When:

- **Choosing between defined options**: "Should we use main-based or stacked PRs?"
- **Gathering workflow preferences**: "Create PRs as drafts or ready for review?"
- **Making strategic decisions**: "Which testing framework should we use?"
- **Selecting from multiple features**: "Which features should we prioritize?" (multi-select)

### ❌ Don't Use Structured Questions When:

- **Asking for freeform input**: Ticket descriptions, commit messages, etc.
- **Only one obvious choice exists**: No need to ask if context is clear
- **User has already provided the information**: Don't ask unnecessarily
- **The question requires custom text**: Names, URLs, descriptions

## Quick Start

### Example 1: Simple Single Question

When PM needs to know your PR workflow preference:

**What You See:**
```
PR Strategy: How should we organize the pull requests?
  ○ Main-based PRs - Each ticket gets its own PR against main (parallel work)
  ○ Stacked PRs - PRs build on each other sequentially (ticket-1 → ticket-2 → ticket-3)
```

**Behind the Scenes:**
```python
from claude_mpm.templates.questions.pr_strategy import PRWorkflowTemplate

# PM detects you have 3 tickets and asks about strategy
template = PRWorkflowTemplate(num_tickets=3, has_ci=True)
# Generates appropriate questions based on context
```

### Example 2: Multiple Related Questions

When initializing a new project:

**What You See:**
```
Project Type: What type of project is this?
  ○ Web Application - Full-stack web app with frontend and backend
  ○ API Service - REST/GraphQL API backend service
  ○ CLI Tool - Command-line application
  ○ Library - Reusable code library/package

Language: Which programming language?
  ○ Python - Python 3.8+
  ○ JavaScript/TypeScript - Node.js or browser
  ○ Go - Go programming language
  ○ Rust - Systems programming with Rust
```

**Behind the Scenes:**
```python
from claude_mpm.templates.questions.project_init import ProjectTypeTemplate

# PM detects new project without existing code
template = ProjectTypeTemplate(existing_files=False)
# Asks both project type and language
```

## Common Use Cases

### Use Case 1: PR Workflow Strategy

**When:** User requests "Create PRs for MPM-101, MPM-102, MPM-103"

**Questions Asked:**
1. **PR Strategy**: Main-based vs Stacked PRs (only if multiple tickets)
2. **Draft PRs**: Create as drafts or ready for review
3. **Auto-merge**: Enable auto-merge after CI passes (only if CI configured)

**Why Context Matters:**
- Single ticket → Skip strategy question (only one PR)
- No CI configured → Skip auto-merge question (not applicable)

**Example:**
```python
# 3 tickets, CI configured
template = PRWorkflowTemplate(num_tickets=3, has_ci=True)
# Asks all 3 questions

# 1 ticket, no CI
template = PRWorkflowTemplate(num_tickets=1, has_ci=False)
# Asks only draft preference question
```

### Use Case 2: Project Initialization

**When:** User runs `/mpm-init` or requests "Initialize new project"

**Questions Asked:**
1. **Project Type**: Web app, API, CLI, library
2. **Language**: Python, JavaScript/TypeScript, Go, Rust
3. **Testing Framework**: pytest, Jest, etc. (language-specific)
4. **CI/CD**: GitHub Actions, GitLab CI, none

**Why Context Matters:**
- Existing files detected → Skip language question (auto-detected)
- Project type affects framework options (web frameworks for web apps)

**Example:**
```python
# New project, no existing code
template = ProjectTypeTemplate(existing_files=False)
# Asks both type and language

# Existing Python project
template = ProjectTypeTemplate(
    existing_files=True,
    detected_language="Python"
)
# Asks only project type (language already detected)
```

### Use Case 3: Ticket Prioritization

**When:** User requests "Prioritize sprint tickets for MPM-101 through MPM-105"

**Questions Asked:**
1. **Dependencies**: Handle dependencies sequentially or in parallel
2. **Execution Strategy**: One at a time or parallel (if team size > 1)
3. **Blockers**: How to handle blocked tickets

**Why Context Matters:**
- Dependencies detected → Ask about dependency strategy
- Team size affects parallel execution options
- Blockers detected → Ask about mitigation strategy

**Example:**
```python
# 5 tickets, dependencies exist, solo developer
template = TicketPrioritizationTemplate(
    num_tickets=5,
    has_dependencies=True,
    team_size=1
)
# Asks about dependencies, execution order
# Skips parallel execution (solo developer)
```

### Use Case 4: Feature Scope Definition

**When:** Creating user-facing production feature

**Questions Asked:**
1. **Testing Level**: Comprehensive, standard, or basic testing
2. **Documentation**: Full docs, API docs only, or inline comments
3. **Code Review**: Required reviewers and approval threshold

**Why Context Matters:**
- Production → Higher testing requirements
- User-facing → Documentation more important
- Internal tool → Lighter requirements acceptable

**Example:**
```python
# User-facing production feature
template = TicketScopeTemplate(
    ticket_type="feature",
    is_user_facing=True,
    project_maturity="production"
)
# Suggests comprehensive testing, full documentation

# Internal development tool
template = TicketScopeTemplate(
    ticket_type="feature",
    is_user_facing=False,
    project_maturity="development"
)
# Suggests standard testing, API docs only
```

## Understanding Question Types

### Single-Select Questions

Most questions allow selecting ONE option:

```
Testing: Which testing framework should we use?
  ○ pytest - Python's most popular testing framework
  ● unittest - Python's built-in testing framework  ← Selected
  ○ nose2 - Extends unittest with plugins
```

### Multi-Select Questions

Some questions allow selecting MULTIPLE options:

```
Features: Which features should we prioritize? (Select all that apply)
  ☑ Authentication - User authentication and authorization
  ☐ Search - Full-text search functionality
  ☑ Analytics - Usage analytics and reporting
  ☑ Export - Data export in multiple formats
```

**Use cases for multi-select:**
- Selecting multiple features to implement
- Choosing multiple testing strategies
- Picking multiple deployment targets

### Question Headers

Each question has a short header (max 12 characters) displayed as a tag/chip:

```
PR Strategy: How should we organize the pull requests?
^^^^^^^^^^^
   Header (identifies the question)
```

Headers are used to:
- Quickly identify questions
- Reference answers (e.g., `answers.get("PR Strategy")`)
- Group related questions

### Option Descriptions

Every option includes a description explaining what it means:

```
○ Main-based PRs - Each ticket gets its own PR against main (parallel work)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                   Description (explains implications)
```

Good descriptions:
- **Explain what the option means**: "Test-driven development with tests first"
- **Clarify implications**: "PRs merge automatically after CI passes and approval"
- **Highlight trade-offs**: "Slower setup but more flexibility"

## Troubleshooting

### Issue: Questions Don't Match My Project

**Symptom:** PM asks about CI auto-merge but you don't have CI configured

**Cause:** PM incorrectly detected CI configuration

**Solution:**
1. Verify CI detection: Check if `.github/workflows/` or `.gitlab-ci.yml` exists
2. Provide feedback: "We don't have CI configured yet"
3. PM will adjust questions for future interactions

### Issue: Getting Asked Same Questions Repeatedly

**Symptom:** PM asks about PR strategy every time you create PRs

**Cause:** Preferences aren't being persisted (feature limitation)

**Workaround:**
1. Answer questions consistently
2. Future enhancement: Preference persistence planned

### Issue: Want to Change Answer After Submitting

**Symptom:** Selected wrong option, want to change answer

**Solution:**
1. Let PM know: "Actually, I prefer stacked PRs instead"
2. PM can re-ask the question if needed
3. Or PM can proceed with your corrected preference

### Issue: Questions Too Generic for My Use Case

**Symptom:** Standard templates don't cover your specific workflow

**Solution:**
1. Request custom questions: "Can we add an option for feature-branch workflow?"
2. Provide freeform guidance: "Use feature branches with team review"
3. Developer: Create custom template (see [Integration Guide](../developer/integrating-structured-questions.md))

## FAQ

### Q: Can I skip questions?

**A:** Most questions have default behavior if not answered. However, critical questions (like PR strategy with multiple tickets) should be answered for best results.

### Q: How does PM decide which questions to ask?

**A:** PM analyzes context (number of tickets, CI configuration, project type, etc.) and only asks relevant questions. See [Template Catalog](../reference/structured-questions-templates.md) for details.

### Q: Can I provide freeform text instead of selecting an option?

**A:** Yes! Each question includes an "Other" option where you can provide custom text. PM will use your custom input.

### Q: What happens if I select "Other" and provide custom text?

**A:** PM will incorporate your custom input into its decision-making. For example, if you specify "rebase-merge workflow", PM will use that instead of standard options.

### Q: Can questions be asked in batches?

**A:** Yes! Related questions are grouped together (up to 4 questions at once) to minimize interruptions.

### Q: How do multi-select questions work?

**A:** For multi-select questions, you can check multiple options. All selected options will be used (e.g., selecting "Auth", "Search", "Analytics" will create tickets for all three features).

### Q: Are my answers saved for future sessions?

**A:** Currently, answers are session-specific. Future enhancement: Persistent user preferences planned.

### Q: Can I see what questions will be asked before starting?

**A:** Not directly, but question sets are predictable based on context. See [Template Catalog](../reference/structured-questions-templates.md) for examples.

### Q: What happens if the visual question UI is broken?

**A:** The system automatically falls back to text-based questions! You'll see questions in your terminal/console and can answer using numbers, labels, or custom text. See [Fallback Behavior](#fallback-behavior) for details.

### Q: How do I know if fallback mode is active?

**A:** You'll see a banner at the top of questions: "AskUserQuestion tool unavailable - using text fallback". The questions work the same way - just with text input instead of visual selection.

### Q: Can I force fallback mode?

**A:** Fallback mode is automatic and cannot be manually controlled. It only activates when the visual UI fails. This ensures maximum reliability.

## Related Documentation

### For Users:
- **[FAQ](FAQ.md)** - General Claude MPM frequently asked questions
- **[User Guide](../user/user-guide.md)** - Complete user documentation
- **[Troubleshooting](../user/troubleshooting.md)** - Common issues and solutions

### For Developers:
- **[Integration Guide](../developer/integrating-structured-questions.md)** - Add structured questions to custom agents
- **[API Reference](../reference/structured-questions-api.md)** - Complete API documentation
- **[Template Catalog](../reference/structured-questions-templates.md)** - Available question templates

### Technical Details:
- **[Design Document](../design/structured-questions-design.md)** - Architecture and design decisions
- **[Template Examples](../../src/claude_mpm/templates/questions/EXAMPLES.md)** - Code examples and integration patterns

---

**Quick Tip**: Questions are designed to be context-aware. The more context PM has (number of tickets, project type, CI configuration), the more relevant the questions will be!
