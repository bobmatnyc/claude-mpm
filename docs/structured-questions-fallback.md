# Structured Questions Fallback Mechanism

## Overview

The structured questions framework now includes automatic fallback to text-based questions when the `AskUserQuestion` tool fails or returns invalid responses. This ensures users always see questions and can provide answers, even when the structured UI is unavailable.

## How It Works

The framework automatically detects when `AskUserQuestion` fails by checking for:
- Empty or missing responses
- Invalid response format
- Fake/placeholder responses (e.g., ".")

When detected, it seamlessly falls back to text-based questions displayed in the console.

## Usage

### Basic Usage (Recommended)

```python
from claude_mpm.utils.structured_questions import QuestionBuilder, QuestionSet

# Build your questions
question = (
    QuestionBuilder()
    .ask("Which database should we use?")
    .header("Database")
    .add_option("PostgreSQL", "Robust relational database")
    .add_option("MongoDB", "Flexible NoSQL database")
    .build()
)

question_set = QuestionSet([question])

# Execute with automatic fallback (recommended)
# This will use AskUserQuestion if available, fallback to text otherwise
response = {}  # Simulate failed AskUserQuestion response
parsed = question_set.execute(response)

# Access answers
db_choice = parsed.get("Database")
print(f"Selected database: {db_choice}")
```

### Using with AskUserQuestion Tool

```python
# In PM agent template or similar
question_set = QuestionSet([question])

# Try AskUserQuestion first
ask_user_params = question_set.to_ask_user_question_params()
# ... call AskUserQuestion tool ...
response = tool_response  # Response from AskUserQuestion

# Execute handles both success and failure cases
parsed = question_set.execute(response)
answers = parsed.get_all()
```

### Disabling Fallback (Advanced)

```python
# Only use when you explicitly want to fail if AskUserQuestion doesn't work
try:
    parsed = question_set.execute(response, use_fallback_if_needed=False)
except QuestionValidationError:
    # Handle failure
    pass
```

## Fallback Text Format

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

Your answer: 1

=== Question 2 of 2 ===
...
```

## Response Parsing

The fallback supports multiple input formats:

### Single Select
- **Numeric**: `1`, `2`, `3`, `4`
- **Exact label**: `PostgreSQL`, `MongoDB`
- **Partial match**: `postgres`, `mongo` (case-insensitive)
- **Custom answer**: Any text not matching options

### Multi-Select
- **Comma-separated numbers**: `1,2,3`
- **Comma-separated labels**: `PostgreSQL, MongoDB`
- **Mixed**: `1, MongoDB, Custom DB`

## ParsedResponse API

The `execute()` method returns a `ParsedResponse` object with convenient methods:

```python
parsed = question_set.execute(response)

# Get single answer
db = parsed.get("Database")  # Returns str or list[str]

# Check if answered
if parsed.was_answered("Database"):
    print("User selected:", parsed.get("Database"))

# Get all answers
all_answers = parsed.get_all()  # Returns dict
```

## Backward Compatibility

The existing `ResponseParser` API still works:

```python
# Old way (still supported)
parser = ResponseParser(question_set)
answers = parser.parse(response)
db = parser.get_answer(answers, "Database")

# New way (recommended)
parsed = question_set.execute(response)
db = parsed.get("Database")
```

## Best Practices

1. **Always use fallback by default**: Only disable for specific testing scenarios
2. **Test both paths**: Ensure your code works with both structured and text responses
3. **Use ParsedResponse**: The new API is cleaner than ResponseParser
4. **Handle custom answers**: Users can provide text not in your options list

## Error Handling

```python
from claude_mpm.utils.structured_questions import QuestionValidationError

try:
    parsed = question_set.execute(response)
except QuestionValidationError as e:
    # Only raised when:
    # 1. response is None and fallback is disabled
    # 2. Invalid question structure (caught at build time)
    print(f"Question error: {e}")
```

## Testing

When writing tests, you can simulate both success and failure cases:

```python
def test_with_valid_response():
    """Test when AskUserQuestion works."""
    response = {"answers": {"Database": "PostgreSQL"}}
    parsed = question_set.execute(response)
    assert parsed.get("Database") == "PostgreSQL"

def test_with_failed_response():
    """Test when AskUserQuestion fails."""
    # Fallback will be triggered for interactive input
    # In tests, mock or disable fallback
    response = {"answers": {}}
    parsed = question_set.execute(response, use_fallback_if_needed=False)
    assert parsed.get("Database") is None
```

## Implementation Details

### Failure Detection Logic

The framework detects failures by checking:

```python
def _should_use_fallback(response):
    # Empty or non-dict response
    if not response or not isinstance(response, dict):
        return True

    # Missing answers key
    if "answers" not in response:
        return True

    # Empty answers
    if not response.get("answers"):
        return True

    # Fake responses (e.g., ".")
    answer_values = list(response["answers"].values())
    if all(v in {".", ""} for v in answer_values):
        return True

    return False
```

### Text Input Parsing

The framework intelligently matches user input:

1. **Numeric input**: Maps to option index (1-based)
2. **Exact match**: Case-insensitive label matching
3. **Partial match**: Substring matching in labels
4. **Fallback**: Returns raw input as custom answer

## Migration Guide

If you're using the old API:

**Before:**
```python
parser = ResponseParser(question_set)
answers = parser.parse(response)
db = answers.get("Database")
if "Database" in answers:
    # ...
```

**After:**
```python
parsed = question_set.execute(response)
db = parsed.get("Database")
if parsed.was_answered("Database"):
    # ...
```

Benefits:
- Automatic fallback handling
- Cleaner API
- Better error messages
- Consistent behavior across failure modes
