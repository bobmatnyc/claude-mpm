# Linting Configuration Guide

## Quick Start with Make Commands (RECOMMENDED)

Claude MPM provides integrated Make commands for all linting operations. These are the recommended approach for development:

```bash
# Auto-fix what can be fixed automatically
make lint-fix            # Fix formatting, imports, style issues

# Run all quality checks
make quality             # Complete linting suite (alias for lint-all)
make lint-all           # Complete linting suite

# Pre-release quality gate
make pre-publish         # Quality checks + tests + validations
```

**Individual linters (for debugging):**
```bash
make lint-ruff          # Fast comprehensive linter
make lint-black         # Code formatting check
make lint-isort         # Import sorting check
make lint-flake8        # Python style checker
make lint-mypy          # Type checking (informational)
make lint-structure     # Project structure compliance
```

**Quality workflow:**
```bash
# 1. Make changes
vim src/claude_mpm/some_file.py

# 2. Fix issues automatically
make lint-fix

# 3. Check remaining issues
make quality

# 4. Fix manual issues, repeat steps 2-3 until clean
```

See [docs/reference/DEPLOY.md](../reference/DEPLOY.md#quality-gates) for complete quality gate documentation.

## Overview

Claude MPM uses multiple linting tools to catch code quality issues, with a special focus on preventing duplicate import bugs that can cause `UnboundLocalError` and `NameError` issues.

## Tools Configured

### 1. **Ruff** (Primary Linter)
- **Purpose**: Fast, comprehensive Python linter that catches duplicate imports
- **Config Files**: `.ruff.toml`, `pyproject.toml`
- **Key Rules**:
  - `F811`: Redefinition of unused name (catches duplicate imports!)
  - `F821`: Undefined name (catches scope issues)
  - `F823`: Local variable referenced before assignment
  - `F401`: Unused imports

### 2. **Flake8** (Secondary Linter)
- **Purpose**: Traditional Python linter with extensive plugin ecosystem
- **Config File**: `.flake8`
- **Key Rules**:
  - `F811`: Redefinition of unused name from line N
  - `F401`: Module imported but unused
  - `F403`: Star imports
  - `E402`: Module level import not at top of file

### 3. **Pylint** (Duplicate Code Detection)
- **Purpose**: Advanced static analysis including duplicate code detection
- **Config**: `pyproject.toml` `[tool.pylint]` section
- **Key Features**:
  - `duplicate-code`: Finds duplicated code blocks
  - `reimported`: Catches reimported modules
  - `import-self`: Detects modules importing themselves

### 4. **Black** (Code Formatter)
- **Purpose**: Automatic code formatting
- **Config**: `pyproject.toml` `[tool.black]` section

### 5. **isort** (Import Sorter)
- **Purpose**: Sorts and organizes imports
- **Config**: `pyproject.toml` `[tool.isort]` section

## Running Linting

### Quick Check (Recommended)
```bash
# Use Make commands (NEW RECOMMENDED APPROACH)
make quality              # Run all quality checks
make lint-fix            # Auto-fix issues first
```

### Legacy Script (Advanced)
```bash
# Traditional script approach
./scripts/run_lint.sh
```

### Individual Tools (Advanced)

**Use Make commands instead (recommended):**
```bash
make lint-ruff          # Fast comprehensive linter
make lint-flake8        # Traditional linter  
make lint-black         # Code formatting check
make lint-isort         # Import sorting check
```

**Manual tool invocation (for debugging):**
```bash
# Ruff (fastest, most comprehensive)
ruff check src/

# Flake8 (traditional linter)
flake8 src/

# Pylint (duplicate detection)
pylint src/claude_mpm --errors-only --enable=duplicate-code,reimported

# Format check
black --check src/
isort --check-only src/
```

### Auto-fix Issues

**Recommended approach:**
```bash
# Fix everything automatically with Make
make lint-fix            # Auto-fix all fixable issues
```

**Manual approach (advanced):**
```bash
# Auto-fix with ruff
ruff check --fix src/

# Auto-format with black
black src/

# Auto-sort imports
isort src/
```

## Pre-commit Hooks

The project uses pre-commit hooks to catch issues before committing:

```bash
# Install pre-commit hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Skip hooks temporarily (not recommended)
git commit --no-verify
```

## The Duplicate Import Bug

### What It Is
When the same module is imported at both module level and function level, Python treats them as different variables in different scopes, causing `UnboundLocalError`:

```python
# BAD: This causes UnboundLocalError
import sys

def get_info():
    import sys  # Duplicate import - creates local variable!
    return sys.platform  # Error: local variable 'sys' referenced before assignment
```

### How We Catch It
Our linting configuration specifically catches this with:
- **Ruff**: Rule `F811` - "Redefinition of unused name"
- **Flake8**: Rule `F811` - "redefinition of unused 'module' from line N"

### Example Output
```
scripts/example.py:5:12: F811 Redefinition of unused `sys` from line 1
```

## Common Issues and Solutions

### Issue: "Redefinition of unused name"
**Cause**: Duplicate imports in different scopes
**Solution**: Remove the duplicate import from the function

### Issue: "Module imported but unused"
**Cause**: Import not used in the code
**Solution**: Remove the unused import or use it

### Issue: "Star imports"
**Cause**: Using `from module import *`
**Solution**: Import specific items: `from module import specific_item`

### Issue: "Module level import not at top of file"
**Cause**: Imports after other code
**Solution**: Move all imports to the top of the file

## CI/CD Integration

Add to your CI pipeline:

```yaml
# GitHub Actions example
- name: Lint with ruff
  run: |
    pip install ruff
    ruff check src/

- name: Check formatting
  run: |
    pip install black isort
    black --check src/
    isort --check-only src/
```

## Best Practices

1. **Use Make commands**: `make lint-fix` → `make quality` → `make pre-publish`
2. **Run linting before committing**: Use `make quality` or pre-commit hooks
3. **Fix issues immediately**: Don't let linting errors accumulate
4. **Use auto-fixers**: Start with `make lint-fix` to fix what can be automated
5. **Keep configs in sync**: Ensure all config files use the same rules
6. **Document exceptions**: If you must disable a rule, document why
7. **Quality gates**: Use `make pre-publish` before releases

## Troubleshooting

### Linter Not Catching Issues
1. Ensure virtual environment is activated
2. Install all linting tools: `pip install ruff flake8 pylint black isort`
3. Check config files exist and are properly formatted

### Too Many False Positives
1. Review and adjust rules in config files
2. Use per-file ignores for special cases
3. Consider using `# noqa` comments sparingly for specific lines

### Performance Issues
1. Use ruff as primary linter (it's much faster)
2. Run linters in parallel
3. Cache results where possible

## References

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [Pylint Documentation](https://pylint.readthedocs.io/)
- [Black Documentation](https://black.readthedocs.io/)
- [isort Documentation](https://pycqa.github.io/isort/)