# Structured Questions Framework - Design Document

**Status**: Implemented
**Version**: 1.0.0
**Last Updated**: 2025-11-19

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Design Goals](#design-goals)
4. [Architecture](#architecture)
5. [Design Decisions](#design-decisions)
6. [Alternative Approaches](#alternative-approaches)
7. [Implementation Details](#implementation-details)
8. [Future Enhancements](#future-enhancements)

---

## Overview

The structured questions framework provides a type-safe, validated approach to building structured questions for use with Claude's AskUserQuestion tool. It enables agents (particularly PM) to gather user input in a structured, consistent way rather than relying on freeform conversation or making assumptions.

### Key Components

- **Core Classes**: `QuestionOption`, `StructuredQuestion`, `QuestionSet`
- **Builder API**: `QuestionBuilder` for fluent question construction
- **Response Parsing**: `ResponseParser` for extracting and validating answers
- **Template System**: Abstract base classes for reusable question patterns
- **Pre-built Templates**: PR strategy, project initialization, ticket management

### Design Principles

1. **Type Safety**: Full type hints, validation at construction time
2. **Fluent API**: Chainable methods for ease of use
3. **Validation First**: Fail fast with clear error messages
4. **Immutability**: Question structures are immutable after creation
5. **Context Awareness**: Templates adapt based on runtime context

---

## Problem Statement

### The Challenge

Before structured questions, PM agent faced several issues when gathering user preferences:

#### 1. **Assumption-Based Decisions**

```python
# ❌ BEFORE: PM makes assumptions
def create_prs(tickets):
    # PM assumes: main-based PRs, ready for review, no auto-merge
    for ticket in tickets:
        create_pr(ticket, base="main", draft=False)
```

**Problems**:
- No user input on workflow preferences
- One-size-fits-all approach doesn't match team workflows
- No way to express preferences like stacked PRs or draft mode

#### 2. **Freeform Conversation**

```python
# ❌ BEFORE: Unclear conversation
"Should we use stacked PRs or main-based PRs? Also, do you want drafts?"
# User might answer: "stacked" or "use stacking" or "stack them"
# Parsing freeform text is unreliable
```

**Problems**:
- Ambiguous user responses
- No standard format for parsing
- Difficult to handle multiple preferences
- Inconsistent UX

#### 3. **Manual Question Construction**

```python
# ❌ BEFORE: Manual AskUserQuestion params
params = {
    "questions": [
        {
            "question": "Which PR strategy",  # Missing '?'
            "header": "PR_STRATEGY",  # Inconsistent format
            "options": [
                {"label": "Main", "description": ""},  # Empty description
                {"label": "Stacked", "description": ""},
            ],
            "multiSelect": False
        }
    ]
}
```

**Problems**:
- No validation (missing '?', empty descriptions)
- Inconsistent formatting
- Easy to make mistakes
- No reusability

---

## Design Goals

### Primary Goals

1. **Type Safety**
   - Full type hints for all classes and methods
   - Catch errors at construction time, not runtime
   - Clear type signatures for better IDE support

2. **Validation**
   - Validate question text ends with '?'
   - Validate header length (max 12 chars)
   - Validate option count (2-4 options)
   - Validate all required fields present

3. **Reusability**
   - Template system for common question patterns
   - Share templates across agents
   - Avoid duplicating question logic

4. **Context Awareness**
   - Questions adapt based on project state
   - Only ask relevant questions
   - Skip questions when context makes them unnecessary

5. **Ease of Use**
   - Fluent API for building questions
   - Simple response parsing
   - Clear error messages

### Non-Goals

- **Not a conversational AI**: This is for structured choices, not open-ended conversation
- **Not a form builder**: Limited to Claude's AskUserQuestion constraints (max 4 questions, 2-4 options each)
- **Not a state machine**: Sequential questions are possible but not the primary focus
- **Not persistent**: No preference storage (future enhancement)

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent Code                              │
│  (PM, Version-Control, Custom Agents)                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ├──> Use Templates
                          │    ┌─────────────────────────────┐
                          │    │   Template System           │
                          │    │  - QuestionTemplate (ABC)   │
                          │    │  - ConditionalTemplate      │
                          │    │  - MultiStepTemplate        │
                          │    └──────────┬──────────────────┘
                          │               │
                          │               ├──> PR Strategy Templates
                          │               ├──> Project Init Templates
                          │               └──> Ticket Mgmt Templates
                          │
                          ├──> Build Questions
                          │    ┌─────────────────────────────┐
                          │    │   Builder API               │
                          │    │  - QuestionBuilder          │
                          │    │    .ask()                   │
                          │    │    .header()                │
                          │    │    .add_option()            │
                          │    │    .build()                 │
                          │    └──────────┬──────────────────┘
                          │               │
                          │               v
                          │    ┌─────────────────────────────┐
                          │    │   Core Classes              │
                          │    │  - QuestionOption           │
                          │    │  - StructuredQuestion       │
                          │    │  - QuestionSet              │
                          │    └──────────┬──────────────────┘
                          │               │
                          v               v
                 ┌────────────────────────────────────┐
                 │    AskUserQuestion Tool            │
                 │  (Claude's built-in tool)          │
                 └────────────────┬───────────────────┘
                                  │
                                  v
                          ┌───────────────┐
                          │     User      │
                          │  (Selects)    │
                          └───────┬───────┘
                                  │
                                  v
                 ┌────────────────────────────────────┐
                 │    Response Parser                 │
                 │  - parse(response)                 │
                 │  - get_answer(header)              │
                 │  - was_answered(header)            │
                 └────────────────────────────────────┘
```

### Data Flow

1. **Question Construction**:
   ```
   QuestionBuilder → StructuredQuestion → QuestionSet → AskUserQuestion params
   ```

2. **Template Construction**:
   ```
   Template (with context) → build() → QuestionSet → AskUserQuestion params
   ```

3. **Response Processing**:
   ```
   AskUserQuestion response → ResponseParser → Parsed answers dict
   ```

### Class Hierarchy

```
QuestionTemplate (ABC)
├── ConditionalTemplate
│   ├── PRWorkflowTemplate
│   ├── PRSizeTemplate
│   ├── PRReviewTemplate
│   ├── ProjectTypeTemplate
│   ├── DevelopmentWorkflowTemplate
│   ├── FrameworkTemplate
│   ├── TicketPrioritizationTemplate
│   ├── TicketScopeTemplate
│   └── TicketDependencyTemplate
└── MultiStepTemplate
    └── (Future: Multi-step workflows)
```

---

## Design Decisions

### Decision 1: Immutable Question Structures

**Choice**: Questions are immutable (frozen dataclasses) after construction

**Rationale**:
- Prevents accidental modification after validation
- Thread-safe (if needed in future)
- Clear separation between construction and usage
- Validation happens once at construction time

**Trade-offs**:
- ❌ Can't modify questions after building
- ✅ No risk of invalid state
- ✅ Clear lifecycle: build → validate → use

**Alternative Considered**: Mutable questions with validation on every change
- Rejected: Too complex, validation overhead on every modification

---

### Decision 2: Fluent Builder API

**Choice**: Use method chaining for question construction

```python
question = (
    QuestionBuilder()
    .ask("Question text?")
    .header("Header")
    .add_option("A", "Description A")
    .add_option("B", "Description B")
    .build()
)
```

**Rationale**:
- Readable, self-documenting code
- IDE autocomplete support
- Clear construction flow
- Familiar pattern (used in many libraries)

**Trade-offs**:
- ❌ Slightly more verbose than dict literals
- ✅ Type-safe, validated construction
- ✅ Better error messages
- ✅ Consistent API across all questions

**Alternative Considered**: Direct instantiation with dict params
- Rejected: No validation, error-prone, poor IDE support

---

### Decision 3: Template System with Conditional Logic

**Choice**: Templates use context to determine which questions to ask

```python
class PRWorkflowTemplate(ConditionalTemplate):
    def __init__(self, num_tickets: int, has_ci: bool):
        super().__init__(num_tickets=num_tickets, has_ci=has_ci)

    def should_include_question(self, question_id: str) -> bool:
        if question_id == "workflow":
            return self.get_context("num_tickets") > 1
        if question_id == "auto_merge":
            return self.get_context("has_ci")
        return True
```

**Rationale**:
- Avoid asking irrelevant questions
- Better UX (fewer, more relevant questions)
- DRY principle (reusable logic)
- Context-aware behavior

**Trade-offs**:
- ❌ Slightly more complex than static questions
- ✅ Much better UX
- ✅ Reusable across workflows
- ✅ Easy to extend

**Alternative Considered**: Always ask all questions
- Rejected: Poor UX, users annoyed by irrelevant questions

---

### Decision 4: Validation at Construction Time

**Choice**: Validate all constraints when building questions, not when using them

**Rationale**:
- Fail fast with clear errors
- Catch mistakes during development
- No surprise errors during production use
- Better developer experience

**Trade-offs**:
- ✅ Errors caught early
- ✅ Clear error messages
- ❌ Slightly slower construction (negligible)

**Alternative Considered**: Lazy validation at usage time
- Rejected: Errors appear far from mistake, harder to debug

---

### Decision 5: Separate Response Parser

**Choice**: Dedicated `ResponseParser` class instead of methods on `QuestionSet`

**Rationale**:
- Single Responsibility Principle
- Parser can reference original questions for validation
- Clear separation of concerns
- Easier to test independently

**Trade-offs**:
- ❌ Requires creating parser instance
- ✅ Cleaner API
- ✅ Better testability
- ✅ Explicit parsing step

**Alternative Considered**: `QuestionSet.parse(response)` method
- Rejected: Mixes construction and parsing concerns

---

### Decision 6: Pre-built Templates in `templates/questions/`

**Choice**: Bundle common templates in package, organized by domain

```
templates/
└── questions/
    ├── base.py           # Abstract base classes
    ├── pr_strategy.py    # PR workflow templates
    ├── project_init.py   # Project setup templates
    └── ticket_mgmt.py    # Ticket management templates
```

**Rationale**:
- Common workflows already solved
- Consistent UX across use cases
- Easy to discover and use
- Clear organization by domain

**Trade-offs**:
- ✅ Reduces duplication
- ✅ Consistent question style
- ✅ Easy to maintain
- ❌ Additional code to maintain

**Alternative Considered**: Document patterns, let users implement
- Rejected: Too much duplication, inconsistent quality

---

## Alternative Approaches

### Alternative 1: JSON/YAML Configuration Files

**Approach**: Store questions in JSON/YAML files

```yaml
# questions/pr_strategy.yaml
questions:
  - question: "How should we organize pull requests?"
    header: "PR Strategy"
    options:
      - label: "Main-based PRs"
        description: "Each ticket gets its own PR"
      - label: "Stacked PRs"
        description: "PRs build on each other"
```

**Pros**:
- Non-programmers can edit questions
- Easy to version control
- Clear separation of data and logic

**Cons**:
- No type safety
- No validation until runtime
- Harder to make context-aware
- No IDE support
- Adds file I/O overhead

**Why Rejected**: Type safety and context awareness more important than editability

---

### Alternative 2: Decorator-Based Question Registration

**Approach**: Use decorators to register questions

```python
@question(header="Testing")
def testing_framework(context):
    return {
        "question": "Which testing framework?",
        "options": [
            {"label": "pytest", "description": "Modern framework"},
            {"label": "unittest", "description": "Built-in framework"}
        ]
    }
```

**Pros**:
- Pythonic pattern
- Easy to discover questions
- Clear registration

**Cons**:
- Less obvious construction flow
- Harder to validate
- More magic/implicit behavior
- Decorator complexity

**Why Rejected**: Fluent builder is more explicit and type-safe

---

### Alternative 3: Question DSL

**Approach**: Create domain-specific language for questions

```python
with QuestionSet() as qs:
    qs.question("Which framework?") \
      .header("Framework") \
      .option("FastAPI", "Modern async framework") \
      .option("Flask", "Lightweight framework")
```

**Pros**:
- Very concise
- Context manager pattern
- Automatic validation on exit

**Cons**:
- Unusual pattern in Python
- Less clear than builder
- Context manager overhead
- Harder to debug

**Why Rejected**: Builder pattern more familiar and explicit

---

## Implementation Details

### File Structure

```
src/claude_mpm/
├── utils/
│   └── structured_questions.py       # Core classes (12KB)
│       ├── QuestionOption
│       ├── StructuredQuestion
│       ├── QuestionSet
│       ├── QuestionBuilder
│       └── ResponseParser
│
└── templates/
    └── questions/
        ├── __init__.py               # Exports all templates
        ├── EXAMPLES.md               # Usage examples (15KB)
        ├── base.py                   # Abstract base classes (6KB)
        │   ├── QuestionTemplate
        │   ├── ConditionalTemplate
        │   └── MultiStepTemplate
        ├── pr_strategy.py            # PR templates (11KB)
        │   ├── PRWorkflowTemplate
        │   ├── PRSizeTemplate
        │   └── PRReviewTemplate
        ├── project_init.py           # Project init templates (13KB)
        │   ├── ProjectTypeTemplate
        │   ├── DevelopmentWorkflowTemplate
        │   └── FrameworkTemplate
        └── ticket_mgmt.py            # Ticket templates (14KB)
            ├── TicketPrioritizationTemplate
            ├── TicketScopeTemplate
            └── TicketDependencyTemplate
```

### Core Validation Rules

1. **Question Text**:
   - Must be non-empty
   - Must end with '?'
   - Should be clear and specific

2. **Header**:
   - Must be non-empty
   - Max 12 characters
   - Should be short, descriptive tag

3. **Options**:
   - Minimum 2 options
   - Maximum 4 options
   - Each must have non-empty label and description
   - Label max 50 characters

4. **Question Set**:
   - Minimum 1 question
   - Maximum 4 questions
   - All must be StructuredQuestion instances

### Performance Considerations

- **Construction**: O(n) where n is number of options (typically 2-4)
- **Validation**: O(1) for each field check
- **Parsing**: O(n) where n is number of questions (max 4)
- **Memory**: Negligible (~1KB per question set)

**Optimization**: No optimization needed, all operations are fast

---

## Future Enhancements

### 1. Persistent Preferences

**Goal**: Remember user preferences across sessions

```python
# User selects "Main-based PRs" once
# Future sessions automatically use that preference
# Or ask: "Use same as last time (Main-based PRs)?"
```

**Implementation**:
- Store preferences in project config
- Check preferences before asking questions
- Allow overriding stored preferences

**Status**: Planned for future release

---

### 2. Multi-Step Question Workflows

**Goal**: Support workflows where later questions depend on earlier answers

```python
# Step 1: Ask about deployment target
answers1 = ask_deployment_target()

# Step 2: Ask AWS-specific or GCP-specific questions based on step 1
if answers1["Deploy To"] == "AWS":
    answers2 = ask_aws_configuration()
else:
    answers2 = ask_gcp_configuration()
```

**Implementation**:
- `MultiStepTemplate` base class (already stubbed)
- State management for tracking current step
- Answer persistence between steps

**Status**: Infrastructure ready, not yet used in templates

---

### 3. Question Analytics

**Goal**: Track which questions are asked most, which options selected

```python
# Analytics data
{
    "PR Strategy": {
        "asked": 150,
        "answers": {
            "Main-based PRs": 120,
            "Stacked PRs": 30
        }
    }
}
```

**Implementation**:
- Optional telemetry when parsing responses
- Aggregate statistics
- Help improve default choices

**Status**: Future consideration

---

### 4. Conditional Option Display

**Goal**: Show/hide options based on context

```python
# Only show "Auto-merge" option if CI detected
if has_ci:
    options.append(auto_merge_option)
```

**Implementation**:
- Already possible at template level
- Could enhance QuestionBuilder with conditional logic

**Status**: Achievable with current design, documentation needed

---

### 5. Question Validation Helper

**Goal**: Validate questions are well-formed for good UX

```python
# Check: Are descriptions informative?
# Check: Are options distinct?
# Check: Is question clear?
validator = QuestionValidator(question)
suggestions = validator.suggest_improvements()
```

**Implementation**:
- Heuristic checks for common issues
- Suggest better descriptions
- Flag unclear options

**Status**: Nice-to-have, low priority

---

## Migration Path

### For Existing Code

No migration needed - structured questions are opt-in:

```python
# OLD: Still works
response = ask_user("Do you want stacked PRs?")

# NEW: Use structured questions for better UX
template = PRWorkflowTemplate(num_tickets=3)
response = ask_user_question(template.to_params())
```

### For Future Features

Structured questions will be preferred for:
- All PM agent decisions
- Configuration wizards
- Interactive setup flows
- User preference gathering

---

## Related Documentation

- **[User Guide](../guides/structured-questions.md)** - User-friendly overview
- **[API Reference](../reference/structured-questions-api.md)** - Complete API documentation
- **[Template Catalog](../reference/structured-questions-templates.md)** - Available templates
- **[Integration Guide](../developer/integrating-structured-questions.md)** - How to use in agents

---

## Appendix: Design Meeting Notes

### Key Requirements from PM Agent Use Cases

1. **PR Workflow**: Need to ask about main-based vs stacked PRs
2. **Project Init**: Need to ask about language, framework, testing
3. **Ticket Planning**: Need to ask about prioritization, scope

### Constraints from AskUserQuestion Tool

- Max 4 questions per call
- Each question: 2-4 options
- Each option: label + description
- Support multi-select mode
- Header max 12 characters

### Implementation Timeline

- **Week 1**: Core classes and builder API
- **Week 2**: Template system and base classes
- **Week 3**: PR strategy templates
- **Week 4**: Project init and ticket mgmt templates
- **Week 5**: Documentation and examples

---

**Document Status**: Complete
**Implementation Status**: ✅ Fully implemented
**Next Review**: When adding new template categories
