# Delegation Detector Hook Integration

## Overview

The delegation detector is now integrated into the hook handler pipeline, automatically scanning PM responses for delegation anti-patterns and creating autotodos.

## How It Works

### 1. Hook Event Flow

```
AssistantResponse Event
    ↓
handle_assistant_response()
    ↓
_scan_for_delegation_patterns()
    ↓
Detect patterns → Create autotodos
```

### 2. Integration Point

The delegation scanner is integrated into the `AssistantResponse` event handler:

**File**: `src/claude_mpm/hooks/claude_hooks/event_handlers.py`

```python
def handle_assistant_response(self, event):
    """Handle assistant response events.

    - Tracks responses for logging
    - Scans for delegation anti-patterns
    - Creates autotodos when patterns are detected
    """
    # Track the response
    # ... (existing tracking code)

    # Scan for delegation patterns
    try:
        self._scan_for_delegation_patterns(event)
    except Exception as e:
        if DEBUG:
            print(f"Delegation scanning error: {e}", file=sys.stderr)
```

### 3. Pattern Detection

The `_scan_for_delegation_patterns()` method:

1. Extracts the response text from the event
2. Uses the `DelegationDetector` to scan for patterns
3. Creates autotodos in the event log for each detection

**Example patterns detected**:
- "Make sure to add .env.local to your .gitignore"
- "You'll need to run npm install"
- "Please run the tests manually"

### 4. Autotodo Creation

When a pattern is detected, an autotodo is created with:

```python
{
    "event_type": "autotodo.delegation",
    "payload": {
        "content": "[Delegation] Verify: add .env.local to your .gitignore",
        "activeForm": "Delegating: add .env.local...",
        "metadata": {
            "pattern_type": "Verify",
            "original_text": "Make sure to add .env.local to your .gitignore",
            "action": "add .env.local to your .gitignore",
            "source": "delegation_detector"
        },
        "session_id": "...",
        "timestamp": "..."
    },
    "status": "pending"
}
```

### 5. Event Log Storage

Autotodos are stored in the event log at `.claude-mpm/event_log.json`:

```json
[
  {
    "id": "2026-01-07T23:20:00.000Z",
    "timestamp": "2026-01-07T23:20:00.000Z",
    "event_type": "autotodo.delegation",
    "payload": { ... },
    "status": "pending"
  }
]
```

## Usage

### Automatic Scanning

No configuration needed - delegation scanning happens automatically for all assistant responses.

### Viewing Autotodos

Use the `autotodos` CLI command:

```bash
# List all pending delegation autotodos
mpm autotodos list --type delegation

# List all autotodos
mpm autotodos list

# Clear resolved autotodos
mpm autotodos clear
```

### Configuration

The hook runs automatically when:
- `AssistantResponse` events are triggered
- The response contains text
- `DelegationDetector` and `EventLog` services are available

### Disabling

To disable delegation scanning, set environment variable:

```bash
export CLAUDE_MPM_HOOK_DEBUG=false
```

Or modify the hook handler to skip the scan.

## Architecture

### Components

1. **DelegationDetector** (`src/claude_mpm/services/delegation_detector.py`)
   - Pattern detection logic
   - Todo formatting
   - Extensible pattern list

2. **EventLog** (`src/claude_mpm/services/event_log.py`)
   - Persistent event storage
   - Event filtering and querying
   - Status management (pending/resolved)

3. **Hook Handler** (`src/claude_mpm/hooks/claude_hooks/hook_handler.py`)
   - Event routing
   - Hook execution
   - Error handling

4. **Event Handlers** (`src/claude_mpm/hooks/claude_hooks/event_handlers.py`)
   - AssistantResponse handler
   - Delegation scanner integration
   - Autotodo creation

### Data Flow

```
PM Response
    ↓
Hook Handler (receives AssistantResponse event)
    ↓
Event Handlers (handle_assistant_response)
    ↓
Delegation Detector (detect patterns)
    ↓
Event Log (store autotodos)
    ↓
Autotodos CLI (read and display)
```

## Testing

Tests are located in `tests/hooks/claude_hooks/test_hook_handler_events.py`:

```bash
# Run delegation scanning tests
python -m pytest tests/hooks/claude_hooks/test_hook_handler_events.py::TestDelegationScanning -v
```

Test coverage:
- ✅ Detects delegation patterns
- ✅ Creates autotodos with correct format
- ✅ Handles empty responses
- ✅ Handles responses without patterns

## Benefits

1. **Automatic Detection**: No manual work needed to identify delegation anti-patterns
2. **Actionable Todos**: PM sees autotodos and can delegate properly
3. **Event-Driven**: Decoupled architecture enables future extensions
4. **Persistent**: Autotodos stored in event log for later processing
5. **Simple**: Minimal configuration and complexity

## Future Enhancements

Potential improvements:
- Add more delegation patterns
- Integrate with dashboard for real-time notifications
- Support pattern customization per project
- Add ML-based pattern detection
- Create autotodos with suggested agent assignments
