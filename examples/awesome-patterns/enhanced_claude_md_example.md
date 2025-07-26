# Enhanced CLAUDE.md Example

This example shows how to structure a CLAUDE.md file following awesome-claude-code best practices.

## 🔴 AGENT INSTRUCTIONS

**IMPORTANT**: As an agent, you MUST read and follow ALL guidelines in this document BEFORE executing any task. DO NOT skip or ignore any part of these standards.

### Critical Rules
1. ALWAYS validate with real data before writing tests
2. NEVER mock core functionality
3. ALWAYS track ALL validation failures (don't stop at first failure)
4. If validation fails 3+ times, use external research tools
5. NEVER print "All Tests Passed" unless verified

## Project Structure
```
project_name/
├── src/
│   └── claude_mpm/
│       ├── agents/         # Agent definitions
│       ├── commands/       # Slash commands
│       ├── hooks/          # Hook system
│       └── services/       # Business logic
├── tests/                  # All tests here
├── scripts/                # All scripts here
└── docs/                   # Documentation
```

## Module Requirements
- **Size**: Maximum 500 lines per file
- **Documentation**: Every file needs purpose, usage, examples
- **Validation**: Main block with real data testing

## Validation Requirements

### Required Validation Pattern
```python
if __name__ == "__main__":
    import sys
    
    # Track ALL failures
    all_validation_failures = []
    total_tests = 0
    
    # Test 1: Basic functionality
    total_tests += 1
    result = process_data("real input")
    expected = {"key": "expected value"}
    if result != expected:
        all_validation_failures.append(f"Test 1: Expected {expected}, got {result}")
    
    # Test 2: Edge cases
    total_tests += 1
    # ... more tests ...
    
    # Final result - CONDITIONAL success
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        sys.exit(0)
```

## Development Priority
1. **Working Code** - Functionality first
2. **Validation** - Verify with real data
3. **Readability** - Clear, maintainable code
4. **Style** - Fix linting only after validation passes

## Architecture Principles
- **Function-First**: Prefer functions over classes
- **Type Hints**: Use for clarity
- **NO Conditional Imports**: Import directly, handle errors during use
- **Async**: Only asyncio.run() in main block

## Standard Components
- **Logging**: Always use loguru
- **CLI**: Use typer for commands
- **Testing**: pytest with real data

## 🔴 COMPLIANCE CHECK

Before completing any task, verify:
1. ✓ All files have documentation headers
2. ✓ Each module has working validation
3. ✓ Type hints used properly
4. ✓ Functionality validated before linting
5. ✓ No asyncio.run() inside functions
6. ✓ Files under 500 lines
7. ✓ External research conducted if 3+ failures
8. ✓ No unconditional success messages
9. ✓ ALL failures tracked and reported
10. ✓ Exit codes set properly (0=success, 1=failure)

## Quick Reference

### Common Commands
```bash
# Run with validation
uv run script.py

# Run slash command
./claude-mpm run "/commit"

# Validate instructions
./claude-mpm validate-instructions
```

### Import Rules
```python
# CORRECT - Direct imports
import tiktoken  # Required dependency

# INCORRECT - Conditional imports
try:
    import tiktoken
except ImportError:
    TIKTOKEN_AVAILABLE = False
```

## Agent-Specific Guidelines

### For Documentation Agent
- Focus on clarity and completeness
- Include examples for all APIs
- Maintain consistent formatting

### For Engineer Agent
- Implement validation first
- Use type hints effectively
- Keep modules focused

### For QA Agent
- Test with real data only
- Track all test failures
- Report comprehensive results

## External Resources
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Type Hints Guide](https://docs.python.org/3/library/typing.html)
- [Loguru Documentation](https://github.com/Delgan/loguru)