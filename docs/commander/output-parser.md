# Output Parser - MPM Commander Phase 2

## Overview

The Output Parser detects events in tool output and creates structured events using the EventManager. It's the second phase of the MPM Commander inbox system.

## Architecture

```
src/claude_mpm/commander/parsing/
├── __init__.py           # Module exports
├── patterns.py           # Detection patterns for all event types
├── extractor.py          # Option/context extraction utilities
└── output_parser.py      # Main OutputParser class
```

## Features

### Event Detection

Detects 5 types of events:

1. **DECISION_NEEDED** - User choices required
   - Numbered lists: `1. Option A\n2. Option B`
   - Bullet lists: `- Option A\n• Option B`
   - Inline options: `(option1/option2)`
   - Y/n prompts: `[Y/n]`, `[yes/no]`

2. **APPROVAL** - Destructive/important actions
   - Delete operations
   - Irreversible actions
   - Warnings requiring confirmation

3. **ERROR** - Failures and exceptions
   - Python tracebacks
   - Error/Exception messages
   - Common error patterns (FileNotFoundError, etc.)
   - Claude Code error indicators (✗)

4. **TASK_COMPLETE** - Completion signals
   - "Done", "Complete", "Success" messages
   - Successful operations

5. **CLARIFICATION** - Requests for more information
   - "Could you clarify..."
   - "I need more information..."

### Option Extraction

Automatically extracts options from various formats:

```python
from claude_mpm.commander.parsing import extract_options

# Numbered list
options = extract_options("""
Please choose:
1. Deploy to staging
2. Deploy to production
3. Cancel deployment
""")
# Returns: ["Deploy to staging", "Deploy to production", "Cancel deployment"]

# Y/n format
options = extract_options("Continue? [Y/n]")
# Returns: ["Y", "n"]

# Inline options
options = extract_options("Choose action (run/skip/abort)")
# Returns: ["run", "skip", "abort"]
```

### Error Context Extraction

Captures surrounding lines for error events:

```python
from claude_mpm.commander.parsing import extract_error_context

content = """
Line 1
Line 2
FileNotFoundError: config.json not found
Line 4
Line 5
"""

context = extract_error_context(content, match_start, match_end, context_lines=2)
# Returns: {
#     "surrounding_lines": ["Line 2", "Line 3", "FileNotFoundError...", "Line 4", "Line 5"],
#     "error_line_index": 2,
#     "match_line": 3
# }
```

### Action Detail Extraction

Extracts details from approval patterns:

```python
from claude_mpm.commander.parsing import extract_action_details

content = "This will delete your configuration file. This action cannot be undone"
details = extract_action_details(content, match)
# Returns: {
#     "action": "delete",
#     "target": "your configuration file",
#     "reversible": False
# }
```

### Code Block Exclusion

Prevents false positives from code examples:

```python
from claude_mpm.commander.parsing import strip_code_blocks

content = """
Here's an example:
```python
raise ValueError("This won't be detected as error")
```
Use try/except for error handling.
"""

stripped = strip_code_blocks(content)
# Code blocks replaced with [CODE_BLOCK] placeholder
```

### ANSI Stripping

Removes terminal color codes:

```python
parser = OutputParser()
clean = parser.strip_ansi("\x1b[31mError: Failed\x1b[0m")
# Returns: "Error: Failed"
```

### Deduplication

Handles overlapping matches by priority:

- Priority order: ERROR > APPROVAL > DECISION > CLARIFICATION > COMPLETION
- When patterns overlap, keeps higher priority event
- Prevents duplicate events at same position

## Usage

### Basic Usage (No Event Creation)

```python
from claude_mpm.commander.parsing import OutputParser

parser = OutputParser()

output = """
Which approach would you prefer?
1. Create new file
2. Overwrite existing
3. Skip operation
"""

results = parser.parse(
    output,
    project_id="proj_123",
    create_events=False  # Don't create events
)

for result in results:
    print(f"{result.event_type.value}: {result.title}")
    if result.options:
        print(f"Options: {result.options}")
```

### With EventManager Integration

```python
from claude_mpm.commander.parsing import OutputParser
from claude_mpm.commander.events.manager import EventManager

# Create manager and parser
manager = EventManager()
parser = OutputParser(event_manager=manager)

# Parse output and auto-create events
output = "FileNotFoundError: config.json not found"
results = parser.parse(
    output,
    project_id="proj_123",
    session_id="session_456",
    create_events=True  # Create events automatically
)

# Events are now in the inbox
inbox = manager.get_inbox()
for event in inbox:
    print(f"[{event.priority.value}] {event.title}")
```

### Handling Different Event Types

```python
# Decision event
output = "Should I proceed with deployment? (y/n)"
results = parser.parse(output, "proj_123", create_events=False)
decision = results[0]
print(f"Options: {decision.options}")  # ["y", "n"]

# Error event
output = "ValueError: Invalid input"
results = parser.parse(output, "proj_123", create_events=False)
error = results[0]
print(f"Context: {error.context}")  # Surrounding lines

# Approval event
output = "This will delete all files. Are you sure?"
results = parser.parse(output, "proj_123", create_events=False)
approval = results[0]
print(f"Action: {approval.context['action']}")  # "delete"
print(f"Reversible: {approval.context['reversible']}")  # False if "cannot be undone"
```

## Testing

```bash
# Run all parser tests
uv run pytest tests/commander/test_output_parser.py -v

# Test specific functionality
uv run pytest tests/commander/test_output_parser.py::TestExtractOptions -v
uv run pytest tests/commander/test_output_parser.py::TestOutputParser::test_detect_python_error -v
```

## Test Coverage

Comprehensive tests for:

- ✅ Option extraction (numbered, bullets, inline, Y/n)
- ✅ Error context extraction
- ✅ Action detail extraction
- ✅ Code block stripping
- ✅ ANSI escape code removal
- ✅ Decision detection (various formats)
- ✅ Approval detection
- ✅ Error detection (Python tracebacks, common errors)
- ✅ Completion detection
- ✅ Clarification detection
- ✅ Multiple event types in one output
- ✅ Overlap deduplication
- ✅ EventManager integration
- ✅ Content truncation

All 29 tests passing.

## Pattern Reference

### Decision Patterns

```python
# Questions asking for preference
"Which approach would you prefer?"
"Should I proceed with deployment?"
"Do you want me to create a backup?"

# Option lists
"Please choose:\n1. Option A\n2. Option B"
"Options:\n- Option A\n- Option B"

# Simple prompts
"Continue? (y/n)"
"Proceed? [Y/n]"
"Select an option:"
```

### Approval Patterns

```python
# Destructive actions
"This will delete your files"
"This will overwrite the database"
"This will modify system settings"

# Confirmation requests
"Are you sure you want to continue?"
"Do you want to allow this action?"

# Irreversible warnings
"This action cannot be undone"
"Warning: This will permanently delete"
"Permanently delete"
```

### Error Patterns

```python
# Python errors
"Traceback (most recent call last):"
"ValueError: Invalid input"
"FileNotFoundError: File not found"

# Generic errors
"Error: Something failed"
"Failed: Operation unsuccessful"
"FATAL: Critical error"

# Permission/access errors
"Permission denied"
"Access denied"

# Network/timeout errors
"Connection refused"
"Timeout"
"TimeoutError"

# Claude Code indicators
"✗" (error marker)
```

### Completion Patterns

```python
# Success messages
"Done."
"Complete!"
"Finished"
"Success"

# Detailed completions
"Successfully deployed to production"
"I've completed the migration"
"Task complete"
```

### Clarification Patterns

```python
# Requests for clarity
"Could you please clarify what you mean by..."
"Could you explain in more detail..."
"I need more information about..."

# Specificity requests
"What do you mean by 'optimize'?"
"Can you be more specific about..."
```

## Implementation Details

### Pattern Matching Flow

1. **Clean content**: Strip ANSI codes
2. **Prepare for matching**: Remove code blocks (replace with placeholders)
3. **Match all patterns**: Check each pattern category
4. **Extract details**: Get options, context, action details
5. **Deduplicate**: Remove overlapping matches, keep higher priority
6. **Create events**: Optionally create events via EventManager

### Priority Handling

Events have default priorities based on type:

- **ERROR**: CRITICAL
- **APPROVAL**: HIGH
- **DECISION_NEEDED**: HIGH
- **CLARIFICATION**: NORMAL
- **TASK_COMPLETE**: INFO

When events overlap, higher priority wins:
`ERROR > APPROVAL > DECISION > CLARIFICATION > COMPLETION`

### ParseResult Structure

```python
@dataclass
class ParseResult:
    event_type: EventType           # Type of event detected
    title: str                      # Short summary
    content: str                    # Matched text (max 500 chars)
    options: Optional[List[str]]    # For decisions/approvals
    context: Optional[Dict[str, Any]]  # Additional structured data
    match_start: int                # Character position start
    match_end: int                  # Character position end
```

## Next Steps (Phase 3)

1. **Output Capture** (#176)
   - Intercept tool output in real-time
   - Buffer tool streams
   - Trigger parser on output

2. **Integration** (#177)
   - Wire OutputParser into ToolExecutor
   - Handle events during tool execution
   - Present events to user

3. **Event Handling** (#178)
   - Pause execution on blocking events
   - Collect user responses
   - Resume with responses

## Related Files

- `src/claude_mpm/commander/models/events.py` - Event models
- `src/claude_mpm/commander/events/manager.py` - EventManager
- `tests/commander/test_output_parser.py` - Comprehensive tests
- `docs/planning/mpm-commander.md` - Overall architecture

## LOC Report

**Phase 2 Implementation:**

Added:
- `patterns.py`: 92 lines
- `extractor.py`: 130 lines
- `output_parser.py`: 262 lines
- `__init__.py`: 20 lines
- `test_output_parser.py`: 380 lines

Total: 884 lines added

Net change: +884 lines (all new functionality)

**Target**: Comprehensive event detection with extensive test coverage
**Achievement**: 29 tests passing, all event types covered
