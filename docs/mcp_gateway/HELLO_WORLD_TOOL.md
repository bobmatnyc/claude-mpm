# Hello World Tool Documentation

## Overview

The Hello World Tool is a comprehensive testing and validation tool for the MCP Gateway system. It provides multiple greeting variations to thoroughly test all MCP capabilities including async operations, input validation, error handling, and multi-language support.

**Part of ISS-0036: Hello World Tool - Testing and Validation Tool**

## Features

- **Simple Greeting**: Basic "Hello World!" functionality
- **Personalized Greeting**: Name-based customization
- **Time-based Greeting**: Dynamic greetings based on time of day
- **Multi-language Support**: Greetings in 25+ languages
- **System Info Greeting**: Integration with system information
- **Async Testing**: Validates async operation support
- **Error Simulation**: Tests error handling capabilities

## Installation

The Hello World Tool is automatically available when the MCP Gateway is running. No additional installation is required.

## Tool Schema

### Input Parameters

```json
{
  "mode": {
    "type": "string",
    "enum": ["simple", "personalized", "time_based", "multi_language", "system_info", "async_test", "error_test"],
    "description": "The greeting mode to use",
    "default": "simple"
  },
  "name": {
    "type": "string",
    "description": "Name for personalized greeting",
    "minLength": 1,
    "maxLength": 100
  },
  "language": {
    "type": "string",
    "description": "Language for multi-language greeting",
    "enum": ["english", "spanish", "french", "german", "italian", "japanese", "chinese", ...],
    "default": "english"
  },
  "delay_ms": {
    "type": "number",
    "description": "Delay in milliseconds for async test",
    "minimum": 0,
    "maximum": 5000,
    "default": 1000
  },
  "uppercase": {
    "type": "boolean",
    "description": "Convert greeting to uppercase",
    "default": false
  },
  "repeat": {
    "type": "number",
    "description": "Number of times to repeat the greeting",
    "minimum": 1,
    "maximum": 10,
    "default": 1
  },
  "include_metadata": {
    "type": "boolean",
    "description": "Include detailed metadata in response",
    "default": true
  }
}
```

### Output Schema

```json
{
  "greeting": "string",
  "mode": "string",
  "timestamp": "string (ISO 8601)",
  "metadata": {
    "tool_version": "string",
    "execution_environment": {
      "platform": "string",
      "python_version": "string",
      "processor": "string"
    },
    "parameters_used": "object",
    "execution_time_ms": "number"
  }
}
```

## Usage Examples

### Simple Greeting

```python
invocation = MCPToolInvocation(
    tool_name="hello_world",
    parameters={"mode": "simple"}
)
result = await registry.invoke_tool(invocation)
# Output: {"greeting": "Hello World!", "mode": "simple", ...}
```

### Personalized Greeting

```python
invocation = MCPToolInvocation(
    tool_name="hello_world",
    parameters={
        "mode": "personalized",
        "name": "Alice"
    }
)
result = await registry.invoke_tool(invocation)
# Output: {"greeting": "Hello, Alice! Welcome to the MCP Gateway.", ...}
```

### Time-based Greeting

```python
invocation = MCPToolInvocation(
    tool_name="hello_world",
    parameters={"mode": "time_based"}
)
result = await registry.invoke_tool(invocation)
# Output (morning): {"greeting": "Good morning! It's 09:30 AM.", ...}
# Output (evening): {"greeting": "Good evening! It's 07:45 PM.", ...}
```

### Multi-language Greeting

```python
# Spanish greeting with name
invocation = MCPToolInvocation(
    tool_name="hello_world",
    parameters={
        "mode": "multi_language",
        "language": "spanish",
        "name": "Carlos"
    }
)
result = await registry.invoke_tool(invocation)
# Output: {"greeting": "Hola, Carlos!", ...}

# Japanese greeting
invocation = MCPToolInvocation(
    tool_name="hello_world",
    parameters={
        "mode": "multi_language",
        "language": "japanese"
    }
)
result = await registry.invoke_tool(invocation)
# Output: {"greeting": "こんにちは, World!", ...}
```

### System Info Greeting

```python
invocation = MCPToolInvocation(
    tool_name="hello_world",
    parameters={"mode": "system_info"}
)
result = await registry.invoke_tool(invocation)
# Output: {"greeting": "Hello from Darwin on MacBook-Pro! Running Python 3.11.5 with MCP Gateway.", ...}
```

### Async Testing

```python
invocation = MCPToolInvocation(
    tool_name="hello_world",
    parameters={
        "mode": "async_test",
        "delay_ms": 500
    }
)
result = await registry.invoke_tool(invocation)
# Output (after 500ms): {"greeting": "Hello World! (after 500ms async delay)", ...}
```

### Combined Features

```python
# Uppercase, repeated greeting with metadata
invocation = MCPToolInvocation(
    tool_name="hello_world",
    parameters={
        "mode": "personalized",
        "name": "Developer",
        "uppercase": true,
        "repeat": 3,
        "include_metadata": true
    }
)
result = await registry.invoke_tool(invocation)
# Output: {
#   "greeting": "HELLO, DEVELOPER! WELCOME TO THE MCP GATEWAY. HELLO, DEVELOPER! WELCOME TO THE MCP GATEWAY. HELLO, DEVELOPER! WELCOME TO THE MCP GATEWAY.",
#   "mode": "personalized",
#   "timestamp": "2025-08-15T12:00:00.000Z",
#   "metadata": {
#     "tool_version": "1.0.0",
#     "execution_environment": {...},
#     "parameters_used": {...},
#     "execution_time_ms": 2.5
#   }
# }
```

## Supported Languages

The multi-language mode supports the following languages:

- **European**: English, Spanish, French, German, Italian, Portuguese, Dutch, Polish, Swedish, Norwegian, Danish, Finnish, Greek, Turkish
- **Asian**: Japanese, Chinese, Korean, Thai, Vietnamese, Indonesian, Malay, Hindi
- **Middle Eastern**: Arabic, Hebrew
- **Slavic**: Russian

## Error Handling

The tool includes comprehensive error handling for various scenarios:

### Validation Errors
- Missing required parameters
- Invalid parameter types
- Out-of-range values
- Invalid name formats

### Runtime Errors
- Simulated runtime errors for testing
- Graceful handling of unexpected exceptions

### Example Error Response

```python
# Missing name for personalized greeting
invocation = MCPToolInvocation(
    tool_name="hello_world",
    parameters={"mode": "personalized"}
)
result = await registry.invoke_tool(invocation)
# Output: {
#   "success": false,
#   "error": "Parameter validation failed",
#   "execution_time": 0.001
# }
```

## Testing

### Unit Tests

Run the comprehensive unit test suite:

```bash
pytest tests/services/test_hello_world_tool.py -v
```

### Integration Testing

Test the tool with the MCP Gateway:

```bash
python scripts/test_hello_world_tool.py --verbose
```

### Performance Benchmark

Run performance benchmarks:

```bash
python scripts/test_hello_world_tool.py --benchmark
```

## Metrics and Analytics

The Hello World Tool tracks various metrics:

- **Total invocations**: Number of times the tool has been called
- **Success rate**: Percentage of successful invocations
- **Average execution time**: Mean time to generate greetings
- **Mode usage**: Distribution of greeting modes used
- **Error tracking**: Types and frequency of errors

Access analytics via:

```python
analytics = hello_tool.get_analytics()
print(f"Total greetings: {analytics['total_greetings']}")
print(f"Modes used: {analytics['modes_used']}")
print(f"Average execution time: {analytics['average_execution_time']}s")
```

## Development

### Extending the Tool

To add a new greeting mode:

1. Add the mode to the input schema enum
2. Implement the greeting method
3. Add case in the `invoke` method
4. Add tests for the new mode

### Example: Adding a Weather Greeting

```python
async def _weather_greeting(self, location: str) -> str:
    """Generate a greeting with weather information."""
    # Implementation here
    weather = await fetch_weather(location)
    return f"Hello! It's {weather.temp}°C and {weather.condition} in {location}."
```

## Troubleshooting

### Common Issues

1. **Tool not found in registry**
   - Ensure the MCP Gateway is running
   - Check that the tool is properly registered

2. **Validation errors**
   - Verify parameter names and types match the schema
   - Check required parameters are provided

3. **Timeout errors**
   - Increase timeout values for async operations
   - Check network connectivity for system info mode

## Version History

- **1.0.0** (2025-08-15): Initial release with comprehensive greeting modes

## References

- [MCP Gateway Documentation](../MCP_GATEWAY.md)
- [MCP Protocol Specification](https://modelcontextprotocol.org)
- [ISS-0036 Ticket](../../tickets/issues/ISS-0036.md)