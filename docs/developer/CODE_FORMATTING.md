# Code Formatting and Quality Guidelines

This document outlines the code formatting and quality standards for the claude-mpm project.

## Overview

The project uses automated code formatting and quality checks to maintain consistent code style across all contributions. This is enforced through pre-commit hooks that run automatically before each commit.

## Tools Used

### Code Formatting
- **Black**: Python code formatter with line length of 88 characters
- **isort**: Import statement organizer, configured to work with Black

### Code Quality
- **flake8**: Python linting for style and error checking
- **mypy**: Static type checking for Python
- **bandit**: Security vulnerability scanner

### Pre-commit Hooks
- **pre-commit**: Manages and runs all formatting and quality checks automatically

## Setup

### Quick Setup
For new developers, run the complete development setup:

```bash
make dev-complete
```

This will:
1. Install claude-mpm in development mode
2. Set up shell configuration
3. Install and configure pre-commit hooks

### Manual Setup
If you prefer to set up components individually:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
make setup-pre-commit

# Or run the setup script directly
./scripts/setup_pre_commit.sh
```

## Configuration

### Black Configuration
Located in `pyproject.toml`:
```toml
[tool.black]
line-length = 88
target-version = ["py38"]
```

### isort Configuration
Located in `pyproject.toml`:
```toml
[tool.isort]
profile = "black"
line_length = 88
```

### flake8 Configuration
Configured in `.pre-commit-config.yaml`:
- Max line length: 88
- Ignored errors: E203 (whitespace before ':'), W503 (line break before binary operator)

### mypy Configuration
Located in `mypy.ini` with module-specific settings for different strictness levels.

## Usage

### Automatic Formatting (Recommended)
Pre-commit hooks will automatically run when you commit:

```bash
git add .
git commit -m "Your commit message"
# Hooks run automatically and may modify files
# If files are modified, you'll need to add and commit again
```

### Manual Commands

#### Format Code
```bash
# Format all code
make format

# Or run tools individually
black src/ tests/ scripts/ --line-length=88
isort src/ tests/ scripts/ --profile=black --line-length=88
```

#### Run Linting
```bash
# Run all linting checks
make lint

# Or run flake8 directly
flake8 src/ --max-line-length=88 --extend-ignore=E203,W503
```

#### Type Checking
```bash
# Run type checking
make type-check

# Or run mypy directly
mypy src/ --config-file=mypy.ini
```

#### Run All Pre-commit Checks
```bash
# Run all pre-commit hooks on all files
make pre-commit-run

# Or use pre-commit directly
pre-commit run --all-files
```

## IDE Integration

### VS Code
Install these extensions for the best experience:
- Python (ms-python.python)
- Black Formatter (ms-python.black-formatter)
- isort (ms-python.isort)
- Flake8 (ms-python.flake8)
- Pylance (ms-python.pylance) for type checking

Add to your VS Code settings.json:
```json
{
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=88"],
    "python.sortImports.args": ["--profile=black", "--line-length=88"],
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

### PyCharm
1. Install the Black plugin
2. Configure Black as the formatter in Settings > Tools > External Tools
3. Enable "Reformat code" and "Optimize imports" on commit

## Troubleshooting

### Pre-commit Hooks Failing
If pre-commit hooks fail:

1. **Formatting Issues**: The hooks will automatically fix most formatting issues. Review the changes and commit again.

2. **Linting Errors**: Fix the reported issues manually, then commit again.

3. **Type Checking Errors**: Add type annotations or fix type-related issues.

### Skipping Hooks (Not Recommended)
In rare cases, you may need to skip hooks:
```bash
git commit --no-verify -m "Emergency fix"
```

### Updating Pre-commit Hooks
```bash
pre-commit autoupdate
```

## Best Practices

1. **Run formatting before committing**: Use `make format` to ensure your code is properly formatted.

2. **Fix linting issues promptly**: Don't ignore flake8 warnings; they often indicate real issues.

3. **Add type annotations**: Help mypy by adding type annotations to new functions and methods.

4. **Test your changes**: Run `make pre-commit-run` before pushing to catch issues early.

5. **Keep dependencies updated**: Regularly update formatting tools to get the latest improvements.

## Contributing

When contributing to the project:

1. Ensure your development environment is set up with `make dev-complete`
2. All code must pass pre-commit hooks before being accepted
3. Follow the existing code style and patterns
4. Add type annotations for new code
5. Update documentation when adding new features

## Support

If you encounter issues with the formatting setup:

1. Check that all dependencies are installed: `pip install -e ".[dev]"`
2. Reinstall pre-commit hooks: `pre-commit install --overwrite`
3. Run the setup script again: `./scripts/setup_pre_commit.sh`
4. Check the project's GitHub issues for known problems
