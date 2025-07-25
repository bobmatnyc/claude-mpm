# Import Standards for Claude MPM

This document describes the import standards for the claude-mpm project and how to properly set up your development environment.

## Import Standards

All imports in the claude-mpm codebase must follow these standards:

### 1. Use Absolute Imports

All imports should use absolute imports from the `claude_mpm` package:

```python
# Good
from claude_mpm.core.logger import get_logger
from claude_mpm.services.agent_management_service import AgentManager

# Bad - relative imports
from ..core.logger import get_logger
from .agent_management_service import AgentManager
```

### 2. No Try/Except Import Blocks

Avoid using try/except blocks for imports. The package should be properly installed:

```python
# Good
from claude_mpm.core.logger import get_logger

# Bad
try:
    from ..core.logger import get_logger
except ImportError:
    from core.logger import get_logger
```

### 3. Special Cases

For `__init__.py` files at the package root:

```python
# In src/claude_mpm/__init__.py
from claude_mpm._version import __version__
from claude_mpm.core.simple_runner import SimpleClaudeRunner
```

## Development Environment Setup

### 1. Install in Development Mode

Always install the package in development mode to ensure imports work correctly:

```bash
# From the project root
pip install -e .
```

This creates a link to your development directory, allowing imports to work properly.

### 2. PYTHONPATH Configuration

If you need to run scripts directly without installation, set PYTHONPATH:

```bash
# Add to your shell profile (.bashrc, .zshrc, etc.)
export PYTHONPATH="${PYTHONPATH}:/path/to/claude-mpm/src"

# Or set it for a single command
PYTHONPATH=/path/to/claude-mpm/src python scripts/some_script.py
```

### 3. Virtual Environment

Always use a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows

# Install the package
pip install -e .
```

### 4. IDE Configuration

#### VS Code

Add to `.vscode/settings.json`:

```json
{
    "python.analysis.extraPaths": ["./src"],
    "python.autoComplete.extraPaths": ["./src"]
}
```

#### PyCharm

1. Right-click on the `src` directory
2. Mark Directory as > Sources Root

## Migration Tools

To migrate existing code to the new import standards:

### Automated Migration

Use the provided migration script:

```bash
# Dry run to see what would change
python scripts/fix_all_imports.py --dry-run

# Apply changes
python scripts/fix_all_imports.py
```

### Manual Migration

For files that need manual attention:

1. Replace relative imports:
   - `from ..module import` → `from claude_mpm.module import`
   - `from .module import` → `from claude_mpm.current_package.module import`

2. Remove try/except import blocks:
   - Keep only the `claude_mpm` import
   - Remove the fallback import

3. Test the imports:
   ```bash
   python -c "from claude_mpm.module import Class"
   ```

## Common Issues and Solutions

### ImportError: No module named 'claude_mpm'

**Solution**: Install the package in development mode:
```bash
pip install -e .
```

### ImportError: attempted relative import with no known parent package

**Solution**: Convert to absolute imports:
```python
# Change this
from ..core.logger import get_logger

# To this
from claude_mpm.core.logger import get_logger
```

### Module imports work in IDE but not when running

**Solution**: Ensure PYTHONPATH includes the src directory:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

## Testing Imports

After making import changes:

1. Run the import verification script:
   ```bash
   python scripts/verify_imports.py
   ```

2. Run the test suite:
   ```bash
   pytest
   ```

3. Try importing in a Python shell:
   ```python
   >>> from claude_mpm.core.logger import get_logger
   >>> from claude_mpm.services.agent_management_service import AgentManager
   ```

## Benefits of Absolute Imports

1. **Clarity**: It's immediately clear where modules come from
2. **Refactoring**: Moving files doesn't break imports in other modules
3. **Testing**: Tests can import modules consistently
4. **IDE Support**: Better autocomplete and navigation
5. **Package Distribution**: Works correctly when installed via pip

## Enforcement

- All new code must use absolute imports
- PR reviews should check for proper import usage
- CI/CD pipeline includes import verification
- Use `flake8` or `pylint` rules to enforce standards