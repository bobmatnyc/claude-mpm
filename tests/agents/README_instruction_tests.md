# Agent Instruction Loading Tests

This directory contains comprehensive unit tests for the agent instruction loading functionality in Claude MPM.

## Test Coverage

### `test_instruction_loading.py`
Tests the core instruction loading functionality including:

1. **Basic Instruction Loading**
   - Loading agent prompts with base instruction injection
   - Handling missing agents with proper error messages
   - Empty/missing instruction handling

2. **Caching Behavior**
   - Instruction caching with correct TTL (3600 seconds)
   - Cache hit/miss tracking
   - Force reload functionality to bypass cache
   - Cache invalidation for specific agents

3. **Special Cases**
   - Unicode and special character handling (emojis, CJK, Cyrillic)
   - Newlines, tabs, and various quote types
   - Mathematical symbols and currency symbols
   - Whitespace-only instructions

4. **Template Selection**
   - Dynamic template selection based on complexity scores
   - MINIMAL template for scores ≤ 30
   - STANDARD template for scores 31-70
   - FULL template for scores > 70
   - Test mode forcing FULL template

5. **Model Selection**
   - Basic model selection from agent capabilities
   - Dynamic model selection based on task complexity
   - Environment variable overrides (global and per-agent)
   - Complexity-based model recommendations

6. **Test Mode Handling**
   - Removal of test-specific instructions when not in test mode
   - Inclusion of test protocols when CLAUDE_PM_TEST_MODE is set
   - Proper section parsing and removal

7. **Legacy Compatibility**
   - Backward compatibility with get_*_agent_prompt() functions
   - Proper return format handling (string vs tuple with model info)

8. **Error Resilience**
   - Handling of malformed JSON files
   - Invalid agent configurations
   - File system errors

### `test_agent_loader.py`
Tests the AgentLoader class functionality including:
- Agent discovery and registration
- Schema validation
- Metrics collection
- Agent listing and metadata retrieval

## Running the Tests

```bash
# Run all instruction loading tests
python -m pytest tests/agents/test_instruction_loading.py -v

# Run a specific test
python -m pytest tests/agents/test_instruction_loading.py::TestInstructionLoadingCore::test_instruction_caching_behavior -v

# Run with coverage
python -m pytest tests/agents/test_instruction_loading.py --cov=claude_mpm.agents --cov-report=html
```

## Key Testing Patterns

1. **Mock Usage**: Heavy use of mocking to avoid file system dependencies
2. **Environment Isolation**: Each test cleans up environment variables
3. **Cache Management**: Tests clear caches before and after to ensure isolation
4. **Comprehensive Coverage**: Tests cover happy paths, edge cases, and error conditions

## Notes

- Tests use simplified mocking to avoid complex path manipulation
- Focus on behavior rather than implementation details
- All tests are designed to run independently without side effects