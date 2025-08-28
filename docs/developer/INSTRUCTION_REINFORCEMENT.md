# Instruction Reinforcement Hook System

## Overview

The Instruction Reinforcement Hook system is designed to combat PM (Project Manager) instruction drift during long conversations by periodically injecting reminder messages into TodoWrite operations. This system provides a non-intrusive way to reinforce PM instructions and maintain proper delegation behavior.

## Problem Statement

During extended conversations, PM agents can drift from their original instructions, often manifesting as:

- Direct usage of implementation tools (Edit, Write, Bash) instead of delegation
- Forgetting their orchestration role and attempting hands-on implementation
- Loss of focus on project coordination and planning responsibilities

The Instruction Reinforcement Hook addresses this by periodically reminding the PM of their core responsibilities through strategically injected todo items.

## Architecture

### Core Components

1. **InstructionReinforcementHook** (`src/claude_mpm/core/instruction_reinforcement_hook.py`)
   - Main hook implementation
   - Tracks TodoWrite call count
   - Injects reminders at configurable intervals
   - Provides metrics and monitoring

2. **PMHookInterceptor Integration** (`src/claude_mpm/core/pm_hook_interceptor.py`)
   - Integrates reinforcement hook with existing PM hook system
   - Transparently modifies TodoWrite parameters
   - Maintains compatibility with existing hook events

### Flow Diagram

```
PM Agent → TodoWrite Call → PMHookInterceptor → InstructionReinforcementHook
                                ↓
                           Check if injection needed
                                ↓
                           Inject reminder (if interval reached)
                                ↓
                           Continue with normal TodoWrite processing
```

## Configuration

### Default Configuration

```python
{
    "enabled": True,
    "test_mode": True,
    "injection_interval": 5,
    "test_messages": [
        "[TEST-REMINDER] This is an injected instruction reminder",
        "[PM-INSTRUCTION] Remember to delegate all work to agents", 
        "[PM-INSTRUCTION] Do not use Edit, Write, or Bash tools directly",
        "[PM-INSTRUCTION] Your role is orchestration and coordination"
    ]
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `true` | Whether the hook is active |
| `test_mode` | boolean | `true` | Use test messages vs production messages |
| `injection_interval` | integer | `5` | Number of TodoWrite calls between injections |
| `test_messages` | array | See above | Custom test messages to rotate through |

### Integration Configuration

The hook is configured through the PMHookInterceptor:

```python
from claude_mpm.core.pm_hook_interceptor import get_pm_hook_interceptor

config = {
    "enabled": True,
    "test_mode": False,  # Use production messages
    "injection_interval": 3,
}

interceptor = get_pm_hook_interceptor(instruction_reinforcement_config=config)
```

## Usage

### Basic Usage

The hook operates transparently once integrated with PMHookInterceptor:

```python
# Initialize with configuration
interceptor = get_pm_hook_interceptor({
    "enabled": True,
    "injection_interval": 5
})

# Wrap TodoWrite function
wrapped_todowrite = interceptor.intercept_todowrite(original_todowrite)

# Normal usage - hook operates transparently
wrapped_todowrite(todos=[...])
```

### Metrics and Monitoring

```python
# Get current metrics
metrics = interceptor.get_instruction_reinforcement_metrics()
print(f"Calls: {metrics['call_count']}")
print(f"Injections: {metrics['injection_count']}")
print(f"Rate: {metrics['injection_rate']:.2%}")

# Reset counters
interceptor.reset_instruction_reinforcement_counters()
```

### Direct Hook Usage

```python
from claude_mpm.core.instruction_reinforcement_hook import InstructionReinforcementHook

hook = InstructionReinforcementHook({
    "injection_interval": 3,
    "test_mode": True
})

# Intercept TodoWrite parameters
params = {"todos": [...]}
modified_params = hook.intercept_todowrite(params)
```

## Message Types

### Test Messages (test_mode=True)

- `[TEST-REMINDER] This is an injected instruction reminder`
- `[PM-INSTRUCTION] Remember to delegate all work to agents`
- `[PM-INSTRUCTION] Do not use Edit, Write, or Bash tools directly`
- `[PM-INSTRUCTION] Your role is orchestration and coordination`

### Production Messages (test_mode=False)

- `[PM-INSTRUCTION] Remember to delegate implementation tasks to appropriate agents`
- `[PM-INSTRUCTION] Use Task tool to delegate work - avoid direct Edit/Write/Bash usage`
- `[PM-INSTRUCTION] Your role is orchestration and project coordination`
- `[PM-INSTRUCTION] Focus on planning and delegation, not direct implementation`

## Implementation Details

### Thread Safety

The hook implementation is thread-safe using Python's `threading.Lock`:

```python
with self._lock:
    self.call_count += 1
    if self.should_inject():
        # Inject reminder
```

### Error Handling

The hook includes comprehensive error handling:

- Returns original parameters on any error
- Logs errors without breaking TodoWrite functionality
- Graceful degradation when disabled

### Memory Efficiency

- Minimal memory footprint
- Simple counters and configuration storage
- No persistent state beyond current session

## Testing

### Integration Tests

Run the integration test suite:

```bash
python test_instruction_reinforcement_integration.py
```

### Manual Testing

```python
# Create test configuration
config = {
    "enabled": True,
    "test_mode": True,
    "injection_interval": 2,
}

# Test basic functionality
hook = InstructionReinforcementHook(config)

# Test multiple calls
for i in range(5):
    params = {"todos": [{"content": f"Task {i}", "status": "pending", "activeForm": "Working"}]}
    result = hook.intercept_todowrite(params)
    print(f"Call {i+1}: {len(result['todos'])} todos")
```

## Monitoring and Metrics

### Available Metrics

```python
{
    "call_count": 10,           # Total TodoWrite calls processed
    "injection_count": 2,       # Total reminders injected
    "injection_rate": 0.2,      # Ratio of injections to calls
    "next_injection_in": 3,     # Calls until next injection
    "enabled": true,            # Whether hook is enabled
    "test_mode": true,          # Message mode
    "injection_interval": 5,    # Configured interval
    "timestamp": "2025-08-28T04:25:15.081632"
}
```

### Performance Impact

- Minimal overhead per TodoWrite call
- O(1) complexity for injection logic
- No disk I/O or network operations
- Thread-safe but non-blocking

## Best Practices

### Configuration

1. **Start Conservative**: Use higher intervals (5-7) initially
2. **Monitor Effectiveness**: Track metrics to assess impact
3. **Adjust Based on Usage**: Lower intervals for problematic sessions
4. **Test Mode First**: Always test with test_mode=True initially

### Integration

1. **Initialize Early**: Configure during PM agent initialization
2. **Use Global Interceptor**: Leverage the singleton pattern
3. **Monitor Metrics**: Regular checks on injection effectiveness
4. **Graceful Degradation**: Ensure system works if hook fails

### Message Customization

1. **Clear and Direct**: Messages should be unambiguous
2. **Actionable**: Include specific guidance
3. **Rotate Messages**: Use multiple messages to avoid habituation
4. **Context Appropriate**: Different messages for different scenarios

## Troubleshooting

### Common Issues

1. **Hook Not Firing**
   - Check `enabled` configuration
   - Verify injection_interval setting
   - Ensure PMHookInterceptor is properly initialized

2. **Wrong Message Type**
   - Check `test_mode` configuration
   - Verify message customization

3. **Performance Issues**
   - Monitor metrics for excessive injection rates
   - Consider increasing injection_interval

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("instruction_reinforcement_hook").setLevel(logging.DEBUG)
logging.getLogger("pm_hook_interceptor").setLevel(logging.DEBUG)
```

### Verification

```python
# Verify hook is working
interceptor = get_pm_hook_interceptor()
metrics = interceptor.get_instruction_reinforcement_metrics()
print(f"Hook operational: {metrics['enabled']}")
print(f"Total processed: {metrics['call_count']}")
```

## Future Enhancements

### Planned Features

1. **Adaptive Intervals**: Adjust interval based on PM behavior patterns
2. **Context-Aware Messages**: Different messages based on project context
3. **Escalation System**: Increase injection frequency on repeated violations
4. **Dashboard Integration**: Real-time monitoring via web interface
5. **A/B Testing**: Compare effectiveness of different message strategies

### Configuration Extensions

1. **Time-Based Intervals**: Inject based on time rather than call count
2. **Conditional Logic**: Inject based on specific patterns or events
3. **Message Pools**: Multiple message sets for different scenarios
4. **User Customization**: Allow users to define custom reminder messages

## Security Considerations

- **Input Validation**: All configuration inputs are validated
- **No External Dependencies**: Self-contained implementation
- **No Persistent Storage**: No sensitive data stored
- **Safe Defaults**: Conservative defaults prevent disruption

## Conclusion

The Instruction Reinforcement Hook system provides a robust, configurable solution for maintaining PM instruction adherence during long conversations. Its integration with the existing PMHookInterceptor ensures seamless operation while providing comprehensive monitoring and configuration options.