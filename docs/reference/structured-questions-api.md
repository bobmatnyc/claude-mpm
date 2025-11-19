# Structured Questions API Reference

Complete API documentation for the structured questions framework.

## Table of Contents

1. [Core Classes](#core-classes)
2. [Question Building](#question-building)
3. [Response Parsing](#response-parsing)
4. [Template System](#template-system)
5. [Validation](#validation)
6. [Type Signatures](#type-signatures)

## Core Classes

### QuestionOption

Represents a single option in a structured question.

**Location:** `claude_mpm.utils.structured_questions.QuestionOption`

#### Constructor

```python
QuestionOption(label: str, description: str)
```

**Parameters:**
- `label` (str): Display text shown to user (1-5 words recommended, max 50 chars)
- `description` (str): Explanation of what this option means or implies

**Raises:**
- `QuestionValidationError`: If label or description is empty or label exceeds 50 characters

**Example:**
```python
from claude_mpm.utils.structured_questions import QuestionOption

option = QuestionOption(
    label="PostgreSQL",
    description="Robust, feature-rich relational database"
)
```

#### Methods

##### `to_dict() -> dict[str, str]`

Convert option to AskUserQuestion tool format.

**Returns:**
- Dictionary with keys `label` and `description`

**Example:**
```python
option = QuestionOption("FastAPI", "Modern async web framework")
print(option.to_dict())
# {'label': 'FastAPI', 'description': 'Modern async web framework'}
```

---

### StructuredQuestion

Represents a single structured question with validation.

**Location:** `claude_mpm.utils.structured_questions.StructuredQuestion`

#### Constructor

```python
StructuredQuestion(
    question: str,
    header: str,
    options: list[QuestionOption],
    multi_select: bool = False
)
```

**Parameters:**
- `question` (str): The complete question text (must end with '?')
- `header` (str): Short label displayed as chip/tag (max 12 chars)
- `options` (list[QuestionOption]): List of 2-4 QuestionOption objects
- `multi_select` (bool): Whether user can select multiple options (default: False)

**Raises:**
- `QuestionValidationError`: If validation fails:
  - Question text is empty or doesn't end with '?'
  - Header is empty or exceeds 12 characters
  - Options list has fewer than 2 or more than 4 options
  - Options are not QuestionOption instances

**Example:**
```python
from claude_mpm.utils.structured_questions import (
    StructuredQuestion,
    QuestionOption
)

question = StructuredQuestion(
    question="Which database should we use?",
    header="Database",
    options=[
        QuestionOption("PostgreSQL", "Relational database"),
        QuestionOption("MongoDB", "NoSQL document database")
    ],
    multi_select=False
)
```

#### Methods

##### `to_dict() -> dict[str, Any]`

Convert question to AskUserQuestion tool format.

**Returns:**
- Dictionary with keys: `question`, `header`, `options`, `multiSelect`

**Example:**
```python
question_dict = question.to_dict()
# {
#     'question': 'Which database should we use?',
#     'header': 'Database',
#     'options': [
#         {'label': 'PostgreSQL', 'description': 'Relational database'},
#         {'label': 'MongoDB', 'description': 'NoSQL document database'}
#     ],
#     'multiSelect': False
# }
```

---

### QuestionSet

Collection of structured questions for a single AskUserQuestion call.

**Location:** `claude_mpm.utils.structured_questions.QuestionSet`

#### Constructor

```python
QuestionSet(questions: list[StructuredQuestion] = [])
```

**Parameters:**
- `questions` (list[StructuredQuestion]): List of 1-4 StructuredQuestion objects (default: empty list)

**Raises:**
- `QuestionValidationError`: If validation fails:
  - Questions list is empty
  - Questions list has more than 4 questions
  - Items are not StructuredQuestion instances

**Example:**
```python
from claude_mpm.utils.structured_questions import QuestionSet

question_set = QuestionSet([question1, question2])
```

#### Methods

##### `add(question: StructuredQuestion) -> QuestionSet`

Add a question to the set.

**Parameters:**
- `question` (StructuredQuestion): Question to add

**Returns:**
- Self for method chaining

**Raises:**
- `QuestionValidationError`: If adding would exceed 4 questions

**Example:**
```python
question_set = QuestionSet()
question_set.add(question1).add(question2)
```

##### `to_ask_user_question_params() -> dict[str, Any]`

Convert question set to AskUserQuestion tool parameters.

**Returns:**
- Dictionary suitable for AskUserQuestion tool parameters

**Example:**
```python
params = question_set.to_ask_user_question_params()
# Use with AskUserQuestion tool
# tool.invoke(params)
```

##### `execute(response: dict[str, Any] | None = None, use_fallback_if_needed: bool = True) -> ParsedResponse`

Execute questions with automatic fallback on AskUserQuestion failure.

**This is the recommended method for executing questions.** It provides graceful degradation when the AskUserQuestion tool fails or returns empty/invalid responses, automatically falling back to text-based questions.

**Parameters:**
- `response` (dict[str, Any] | None): Response from AskUserQuestion tool (optional)
- `use_fallback_if_needed` (bool): Auto-fallback if AskUserQuestion fails (default: True)

**Returns:**
- `ParsedResponse` object with user answers

**Raises:**
- `QuestionValidationError`: If response is None and fallback is disabled

**Fallback Trigger Conditions:**

The method automatically detects AskUserQuestion failures by checking for:
- Empty or missing response
- Missing "answers" key in response
- Empty answers dictionary
- Fake/placeholder responses (e.g., all answers are "." or "")

**Example:**
```python
# Basic usage (recommended)
question_set = QuestionSet([question])

# Option 1: With AskUserQuestion response
response = {"answers": {"Database": "PostgreSQL"}}
parsed = question_set.execute(response)
db = parsed.get("Database")  # "PostgreSQL"

# Option 2: With failed/empty response (triggers fallback)
response = {"answers": {}}
parsed = question_set.execute(response)  # Falls back to text input
db = parsed.get("Database")

# Option 3: Disable fallback (raises error on failure)
try:
    parsed = question_set.execute(response, use_fallback_if_needed=False)
except QuestionValidationError:
    # Handle error
    pass
```

**Text Fallback Format:**

When fallback is triggered, users see:

```
============================================================
📋 USER INPUT REQUIRED
(AskUserQuestion tool unavailable - using text fallback)
============================================================

=== Question 1 of 2 ===
[Database] Which database should we use?

Options:
1. PostgreSQL - Robust relational database
2. MongoDB - Flexible NoSQL database

Your answer:
```

**Supported Input Formats (Fallback Mode):**

Single-select:
- Numeric: `1`, `2`, `3`, `4`
- Exact label: `PostgreSQL`, `MongoDB`
- Partial match: `postgres`, `mongo` (case-insensitive)
- Custom answer: Any text not matching options

Multi-select:
- Comma-separated numbers: `1,2,3`
- Comma-separated labels: `PostgreSQL, MongoDB`
- Mixed: `1, MongoDB, Custom DB`

---

## Question Building

### QuestionBuilder

Fluent API for building StructuredQuestion objects.

**Location:** `claude_mpm.utils.structured_questions.QuestionBuilder`

#### Constructor

```python
QuestionBuilder()
```

Initializes builder with empty state.

**Example:**
```python
from claude_mpm.utils.structured_questions import QuestionBuilder

builder = QuestionBuilder()
```

#### Methods

##### `ask(question: str) -> QuestionBuilder`

Set the question text.

**Parameters:**
- `question` (str): The question text (should end with '?')

**Returns:**
- Self for method chaining

**Example:**
```python
builder.ask("Which testing framework?")
```

##### `header(header: str) -> QuestionBuilder`

Set the header label.

**Parameters:**
- `header` (str): Short label (max 12 chars)

**Returns:**
- Self for method chaining

**Example:**
```python
builder.header("Testing")
```

##### `add_option(label: str, description: str) -> QuestionBuilder`

Add an option to the question.

**Parameters:**
- `label` (str): Display text for the option
- `description` (str): Explanation of the option

**Returns:**
- Self for method chaining

**Example:**
```python
builder.add_option("pytest", "Python's most popular testing framework")
```

##### `with_options(options: list[QuestionOption]) -> QuestionBuilder`

Set all options at once.

**Parameters:**
- `options` (list[QuestionOption]): List of QuestionOption objects

**Returns:**
- Self for method chaining

**Example:**
```python
options = [
    QuestionOption("Option 1", "Description 1"),
    QuestionOption("Option 2", "Description 2")
]
builder.with_options(options)
```

##### `multi_select(enabled: bool = True) -> QuestionBuilder`

Enable or disable multi-select mode.

**Parameters:**
- `enabled` (bool): Whether to allow multiple selections (default: True)

**Returns:**
- Self for method chaining

**Example:**
```python
builder.multi_select(enabled=True)
```

##### `build() -> StructuredQuestion`

Build and validate the StructuredQuestion.

**Returns:**
- Validated StructuredQuestion instance

**Raises:**
- `QuestionValidationError`: If validation fails or required fields missing

**Example:**
```python
question = (
    QuestionBuilder()
    .ask("Which framework?")
    .header("Framework")
    .add_option("FastAPI", "Modern async framework")
    .add_option("Flask", "Lightweight WSGI framework")
    .build()
)
```

---

## Response Parsing

### ParsedResponse

Wrapper for parsed question responses with convenient accessor methods.

**Location:** `claude_mpm.utils.structured_questions.ParsedResponse`

**This is the recommended interface for accessing user answers.** It provides a clean, consistent API for both AskUserQuestion and text fallback responses.

#### Constructor

```python
ParsedResponse(question_set: QuestionSet, answers: dict[str, str | list[str]])
```

**Parameters:**
- `question_set` (QuestionSet): The QuestionSet that was executed
- `answers` (dict[str, str | list[str]]): Parsed answers dictionary

**Note:** Typically you won't construct this directly - use `QuestionSet.execute()` instead.

**Example:**
```python
# Recommended: Use execute() which returns ParsedResponse
parsed = question_set.execute(response)

# Direct construction (not recommended)
from claude_mpm.utils.structured_questions import ParsedResponse
parsed = ParsedResponse(question_set, {"Database": "PostgreSQL"})
```

#### Methods

##### `get(header: str, default: Any = None) -> str | list[str] | Any`

Get answer for a specific question by header.

**Parameters:**
- `header` (str): Question header to look up
- `default` (Any): Default value if not answered (default: None)

**Returns:**
- Selected option label(s), custom answer, or default value
- For single-select: Returns `str`
- For multi-select: Returns `list[str]`

**Example:**
```python
parsed = question_set.execute(response)

# Single-select question
database = parsed.get("Database")  # "PostgreSQL"
database = parsed.get("Database", "SQLite")  # "SQLite" if not answered

# Multi-select question
features = parsed.get("Features")  # ["Auth", "Search", "Analytics"]
features = parsed.get("Features", [])  # [] if not answered
```

##### `was_answered(header: str) -> bool`

Check if a question was answered.

**Parameters:**
- `header` (str): Question header to check

**Returns:**
- True if question was answered, False otherwise

**Example:**
```python
if parsed.was_answered("Database"):
    database = parsed.get("Database")
    print(f"User selected: {database}")
else:
    print("Database question was not answered")
```

##### `get_all() -> dict[str, str | list[str]]`

Get all answers as a dictionary.

**Returns:**
- Dictionary mapping question headers to selected option labels

**Example:**
```python
parsed = question_set.execute(response)
all_answers = parsed.get_all()
# {
#     'Database': 'PostgreSQL',
#     'Features': ['Auth', 'Search'],
#     'Testing': 'pytest'
# }

for header, answer in all_answers.items():
    print(f"{header}: {answer}")
```

---

### ResponseParser (Legacy)

Parses and validates responses from AskUserQuestion tool.

**Location:** `claude_mpm.utils.structured_questions.ResponseParser`

#### Constructor

```python
ResponseParser(question_set: QuestionSet)
```

**Parameters:**
- `question_set` (QuestionSet): The QuestionSet that was sent to AskUserQuestion

**Example:**
```python
from claude_mpm.utils.structured_questions import ResponseParser

parser = ResponseParser(question_set)
```

#### Methods

##### `parse(response: dict[str, Any]) -> dict[str, str | list[str]]`

Parse AskUserQuestion response into header → answer mapping.

**Parameters:**
- `response` (dict[str, Any]): Raw response from AskUserQuestion tool
  - Expected format: `{"answers": {"header": "label", ...}}`

**Returns:**
- Dictionary mapping question headers to selected option labels
- For multi-select questions, values are lists of labels
- For single-select questions, values are strings

**Raises:**
- `QuestionValidationError`: If response format is invalid:
  - Response is not a dictionary
  - Response doesn't contain 'answers' key
  - Answer format doesn't match question type

**Example:**
```python
response = {
    "answers": {
        "Database": "PostgreSQL",
        "Features": ["Auth", "Search", "Analytics"]
    }
}

parsed = parser.parse(response)
# {
#     'Database': 'PostgreSQL',
#     'Features': ['Auth', 'Search', 'Analytics']
# }
```

##### `get_answer(parsed_answers: dict[str, str | list[str]], header: str) -> str | list[str] | None`

Get answer for a specific question by header.

**Parameters:**
- `parsed_answers` (dict): Result from `parse()`
- `header` (str): Question header to look up

**Returns:**
- Selected option label(s) or None if not answered

**Example:**
```python
database = parser.get_answer(parsed_answers, "Database")
# 'PostgreSQL'

features = parser.get_answer(parsed_answers, "Features")
# ['Auth', 'Search', 'Analytics']

missing = parser.get_answer(parsed_answers, "NonExistent")
# None
```

##### `was_answered(parsed_answers: dict[str, str | list[str]], header: str) -> bool`

Check if a question was answered.

**Parameters:**
- `parsed_answers` (dict): Result from `parse()`
- `header` (str): Question header to check

**Returns:**
- True if question was answered, False otherwise

**Example:**
```python
if parser.was_answered(parsed_answers, "Database"):
    database = parser.get_answer(parsed_answers, "Database")
else:
    database = "PostgreSQL"  # Default
```

---

## Template System

### QuestionTemplate

Abstract base class for question templates.

**Location:** `claude_mpm.templates.questions.base.QuestionTemplate`

#### Methods

##### `build() -> QuestionSet` (Abstract)

Build and return a QuestionSet.

**Returns:**
- QuestionSet ready for use with AskUserQuestion tool

**Raises:**
- `QuestionValidationError`: If question construction fails

**Example:**
```python
from claude_mpm.templates.questions.base import QuestionTemplate
from claude_mpm.utils.structured_questions import QuestionSet, QuestionBuilder

class MyTemplate(QuestionTemplate):
    def build(self) -> QuestionSet:
        question = (
            QuestionBuilder()
            .ask("Which option?")
            .header("Option")
            .add_option("A", "Option A")
            .add_option("B", "Option B")
            .build()
        )
        return QuestionSet([question])
```

##### `to_params() -> dict[str, Any]`

Build question set and convert to AskUserQuestion parameters.

**Returns:**
- Dictionary suitable for AskUserQuestion tool

**Example:**
```python
template = MyTemplate()
params = template.to_params()
# Use with AskUserQuestion tool
```

---

### ConditionalTemplate

Template that adjusts questions based on context.

**Location:** `claude_mpm.templates.questions.base.ConditionalTemplate`

Extends: `QuestionTemplate`

#### Constructor

```python
ConditionalTemplate(**context: Any)
```

**Parameters:**
- `**context` (Any): Arbitrary context values used to determine questions

**Example:**
```python
template = ConditionalTemplate(
    num_tickets=3,
    has_ci=True,
    project_type="web"
)
```

#### Attributes

- `context` (dict[str, Any]): Dictionary of context values

#### Methods

##### `get_context(key: str, default: Any = None) -> Any`

Get a context value.

**Parameters:**
- `key` (str): Context key to retrieve
- `default` (Any): Default value if key not found (default: None)

**Returns:**
- Context value or default

**Example:**
```python
num_tickets = template.get_context("num_tickets", 1)
```

##### `has_context(key: str) -> bool`

Check if context key exists.

**Parameters:**
- `key` (str): Context key to check

**Returns:**
- True if key exists in context, False otherwise

**Example:**
```python
if template.has_context("has_ci"):
    # CI context provided
    pass
```

##### `should_include_question(question_id: str) -> bool`

Determine if a question should be included based on context.

**Parameters:**
- `question_id` (str): Identifier for the question being considered

**Returns:**
- True if question should be included, False otherwise

**Example:**
```python
class PRWorkflowTemplate(ConditionalTemplate):
    def should_include_question(self, question_id: str) -> bool:
        if question_id == "auto_merge":
            return self.get_context("has_ci", False)
        return True
```

##### `build() -> QuestionSet` (Abstract)

Build QuestionSet based on context.

**Returns:**
- QuestionSet with questions appropriate for the context

---

### MultiStepTemplate

Template for multi-step question workflows.

**Location:** `claude_mpm.templates.questions.base.MultiStepTemplate`

Extends: `QuestionTemplate`

#### Constructor

```python
MultiStepTemplate()
```

#### Attributes

- `_current_step` (int): Current step number (0-indexed)
- `_answers` (dict[str, Any]): Stored answers from previous steps

#### Methods

##### `set_answers(step: int, answers: dict[str, Any]) -> None`

Record answers from a previous step.

**Parameters:**
- `step` (int): Step number (0-indexed)
- `answers` (dict): Parsed answers from ResponseParser

**Example:**
```python
template.set_answers(0, parsed_answers)
```

##### `get_answers(step: int) -> dict[str, Any] | None`

Get answers from a previous step.

**Parameters:**
- `step` (int): Step number (0-indexed)

**Returns:**
- Answers dictionary or None if step not completed

**Example:**
```python
step0_answers = template.get_answers(0)
```

##### `build_step(step: int) -> QuestionSet` (Abstract)

Build questions for a specific step.

**Parameters:**
- `step` (int): Step number (0-indexed)

**Returns:**
- QuestionSet for the specified step

##### `build() -> QuestionSet`

Build questions for the current step.

**Returns:**
- QuestionSet for current step

##### `advance_step() -> None`

Move to the next step.

**Example:**
```python
template.advance_step()  # Move from step 0 to step 1
```

##### `current_step` (Property)

Get current step number.

**Returns:**
- Current step number (int)

**Example:**
```python
step = template.current_step  # 0, 1, 2, etc.
```

##### `is_complete() -> bool` (Abstract)

Check if all steps are complete.

**Returns:**
- True if workflow is complete, False otherwise

---

## Validation

### QuestionValidationError

Exception raised when question validation fails.

**Location:** `claude_mpm.utils.structured_questions.QuestionValidationError`

Extends: `Exception`

**Common Causes:**

1. **Question text validation:**
   - Empty question text
   - Question doesn't end with '?'

2. **Header validation:**
   - Empty header
   - Header exceeds 12 characters

3. **Options validation:**
   - Fewer than 2 options
   - More than 4 options
   - Empty option label or description
   - Option label exceeds 50 characters

4. **Question set validation:**
   - Empty question set
   - More than 4 questions in set

5. **Response parsing:**
   - Invalid response format
   - Answer type doesn't match question type

**Example:**
```python
from claude_mpm.utils.structured_questions import (
    QuestionBuilder,
    QuestionValidationError
)

try:
    question = (
        QuestionBuilder()
        .ask("Invalid question without question mark")
        .header("Test")
        .add_option("A", "Option A")
        .build()
    )
except QuestionValidationError as e:
    print(f"Validation failed: {e}")
    # "Question should end with '?': Invalid question without question mark"
```

---

## Type Signatures

### Complete Type Signatures

```python
from typing import Any

# Core classes
class QuestionOption:
    label: str
    description: str

    def __init__(self, label: str, description: str) -> None: ...
    def to_dict(self) -> dict[str, str]: ...

class StructuredQuestion:
    question: str
    header: str
    options: list[QuestionOption]
    multi_select: bool

    def __init__(
        self,
        question: str,
        header: str,
        options: list[QuestionOption],
        multi_select: bool = False
    ) -> None: ...
    def to_dict(self) -> dict[str, Any]: ...

class QuestionSet:
    questions: list[StructuredQuestion]

    def __init__(self, questions: list[StructuredQuestion] = []) -> None: ...
    def add(self, question: StructuredQuestion) -> QuestionSet: ...
    def to_ask_user_question_params(self) -> dict[str, Any]: ...
    def execute(
        self,
        response: dict[str, Any] | None = None,
        use_fallback_if_needed: bool = True,
    ) -> ParsedResponse: ...

# Builder
class QuestionBuilder:
    def __init__(self) -> None: ...
    def ask(self, question: str) -> QuestionBuilder: ...
    def header(self, header: str) -> QuestionBuilder: ...
    def add_option(self, label: str, description: str) -> QuestionBuilder: ...
    def with_options(self, options: list[QuestionOption]) -> QuestionBuilder: ...
    def multi_select(self, enabled: bool = True) -> QuestionBuilder: ...
    def build(self) -> StructuredQuestion: ...

# Response objects
class ParsedResponse:
    def __init__(self, question_set: QuestionSet, answers: dict[str, str | list[str]]) -> None: ...
    def get(self, header: str, default: Any = None) -> str | list[str] | Any: ...
    def was_answered(self, header: str) -> bool: ...
    def get_all(self) -> dict[str, str | list[str]]: ...

# Legacy parser (prefer ParsedResponse)
class ResponseParser:
    def __init__(self, question_set: QuestionSet) -> None: ...
    def parse(self, response: dict[str, Any]) -> dict[str, str | list[str]]: ...
    def get_answer(
        self,
        parsed_answers: dict[str, str | list[str]],
        header: str
    ) -> str | list[str] | None: ...
    def was_answered(
        self,
        parsed_answers: dict[str, str | list[str]],
        header: str
    ) -> bool: ...

# Templates
class QuestionTemplate(ABC):
    @abstractmethod
    def build(self) -> QuestionSet: ...
    def to_params(self) -> dict[str, Any]: ...

class ConditionalTemplate(QuestionTemplate):
    context: dict[str, Any]

    def __init__(self, **context: Any) -> None: ...
    def get_context(self, key: str, default: Any = None) -> Any: ...
    def has_context(self, key: str) -> bool: ...
    def should_include_question(self, question_id: str) -> bool: ...

class MultiStepTemplate(QuestionTemplate):
    _current_step: int
    _answers: dict[str, Any]

    def __init__(self) -> None: ...
    def set_answers(self, step: int, answers: dict[str, Any]) -> None: ...
    def get_answers(self, step: int) -> dict[str, Any] | None: ...
    @abstractmethod
    def build_step(self, step: int) -> QuestionSet: ...
    def advance_step(self) -> None: ...
    @property
    def current_step(self) -> int: ...
    @abstractmethod
    def is_complete(self) -> bool: ...

# Exception
class QuestionValidationError(Exception):
    pass
```

---

## Related Documentation

- **[User Guide](../guides/structured-questions.md)** - User-friendly overview and common use cases
- **[Template Catalog](structured-questions-templates.md)** - Complete list of available templates
- **[Integration Guide](../developer/integrating-structured-questions.md)** - How to use in custom agents
- **[Design Document](../design/structured-questions-design.md)** - Architecture and design decisions

---

**For More Examples**: See [EXAMPLES.md](../../src/claude_mpm/templates/questions/EXAMPLES.md) for integration patterns and complete workflows.
