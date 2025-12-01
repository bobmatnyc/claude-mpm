# Python Guidelines

## Code Style

- **PEP 8**: Follow Python Enhancement Proposal 8 for code formatting
- **Type Hints**: Use type annotations for function parameters and return values
- **Docstrings**: Write comprehensive docstrings for modules, classes, and functions
- **Black**: Use Black for automatic code formatting

## Project Structure

```
project/
├── src/               # Source code
│   └── package/       # Main package
├── tests/             # Test files
├── docs/              # Documentation
├── requirements.txt   # Dependencies
├── setup.py          # Package configuration
└── README.md         # Project overview
```

## Best Practices

- **Virtual Environments**: Always use virtual environments (venv, conda)
- **Dependency Management**: Pin exact versions in requirements.txt
- **Testing**: Use pytest for testing, aim for 80%+ coverage
- **Linting**: Use pylint, flake8, or ruff for code quality checks

## Common Patterns

- **Context Managers**: Use `with` statements for resource management
- **Comprehensions**: Prefer list/dict comprehensions over loops when clear
- **Generators**: Use generators for memory-efficient iteration
- **f-strings**: Use f-strings for string formatting

## Error Handling

- Use specific exceptions, not bare `except`
- Fail fast: validate inputs early
- Provide helpful error messages
- Log exceptions with context
