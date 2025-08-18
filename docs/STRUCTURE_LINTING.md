# Structure Linting System

The Claude MPM project includes a comprehensive structure linting system to enforce project organization standards and prevent violations of documented file placement guidelines.

## Overview

The structure linting system automatically validates that files are placed in the correct directories according to the project's documented structure requirements in [STRUCTURE.md](STRUCTURE.md).

### Key Features

- **Automated validation** of file placement rules
- **Auto-fix capability** for common violations
- **Pre-commit hook integration** to prevent violations from being committed
- **CI/CD integration** for continuous validation
- **IDE integration** with VS Code tasks
- **Multiple interfaces** (CLI, Make targets, Git hooks)

## Structure Rules

The linter enforces the following rules:

### 1. Python Scripts in Root
- **Rule**: Python scripts must not be placed in the project root directory
- **Exception**: `setup.py` is allowed in the root
- **Auto-fix**: Moves scripts to `/scripts/` directory

### 2. Shell Scripts in Root
- **Rule**: Shell scripts (`.sh`, `.bash`) must not be placed in the project root
- **Auto-fix**: Moves scripts to `/scripts/` directory

### 3. Test Files Placement
- **Rule**: Test files (`test_*.py`, `*_test.py`) must be in the `/tests/` directory
- **Auto-fix**: Moves test files to `/tests/` directory

### 4. Changelog Requirements
- **Rule**: Project must have a `CHANGELOG.md` file
- **Format**: Must follow [Keep a Changelog](https://keepachangelog.com) format
- **Required Sections**:
  - `[Unreleased]` section at the top for upcoming changes
  - Standard subsections: `Added`, `Changed`, `Fixed`, `Removed`
  - Comparison links at the bottom for version navigation
- **Auto-fix**: Not available (manual editing required)

### 5. Version Consistency
- **Rule**: Version numbers must be consistent across all version files
- **Checked Files**:
  - `VERSION` - Primary version source
  - `package.json` - NPM package version
  - `pyproject.toml` - Commitizen configuration version
  - `CHANGELOG.md` - Version entries
- **Auto-fix**: Not available (manual synchronization required)

## Usage

### Command Line Interface

```bash
# Run structure linting
python tools/dev/structure_linter.py --verbose

# Auto-fix violations
python tools/dev/structure_linter.py --fix --verbose

# Output results as JSON
python tools/dev/structure_linter.py --json

# Lint specific path
python tools/dev/structure_linter.py /path/to/check
```

### Make Targets

```bash
# Run structure linting
make structure-lint

# Run with auto-fix
make structure-fix
```

### VS Code Integration

1. Open Command Palette (`Ctrl+Shift+P`)
2. Type "Tasks: Run Task"
3. Select either:
   - "Structure Lint" - Run validation only
   - "Structure Lint & Fix" - Run with auto-fix

## Installation

### Automatic Installation

Run the installation script to set up all integrations:

```bash
./scripts/install_structure_linting.sh
```

This installs:
- Pre-commit hook
- GitHub Actions workflow
- VS Code tasks
- Makefile targets

### Manual Installation

#### Pre-commit Hook

```bash
# Copy the pre-commit hook
cp tools/dev/hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

#### GitHub Actions

The workflow file is automatically created at `.github/workflows/structure-lint.yml`.

## Configuration

### Customizing Rules

To modify or add structure rules, edit `tools/dev/structure_linter.py`:

```python
def _load_rules(self) -> List[StructureRule]:
    """Load structure validation rules."""
    return [
        StructureRule(
            name="custom_rule",
            pattern=r".*\.ext$",
            allowed_locations=[],
            forbidden_locations=["."],
            description="Custom rule description"
        ),
        # ... other rules
    ]
```

### Ignoring Files

Files are automatically ignored based on patterns in the `_should_ignore()` method:

- `.git/` directory
- Virtual environments (`venv/`, `.venv/`)
- Build artifacts (`dist/`, `build/`, `__pycache__/`)
- IDE files (`.DS_Store`)

## Integration Points

### Pre-commit Hook

The pre-commit hook runs automatically before each commit and:
- Validates all staged files
- Blocks commits if violations are found
- Provides clear error messages and fix suggestions

### GitHub Actions

The CI workflow runs on:
- Push to `main` and `develop` branches
- Pull requests to `main` and `develop` branches

### Development Workflow

1. **During Development**: Use VS Code tasks or Make targets for quick validation
2. **Before Commit**: Pre-commit hook automatically validates
3. **In CI/CD**: GitHub Actions provides final validation

## Troubleshooting

### Common Issues

#### "Structure linter not found"
Ensure the linter script exists and is executable:
```bash
chmod +x tools/dev/structure_linter.py
```

#### "Permission denied" on pre-commit hook
Make the hook executable:
```bash
chmod +x .git/hooks/pre-commit
```

#### Auto-fix not working
Check that the target directory exists and is writable:
```bash
mkdir -p tests scripts
```

### Bypassing the Hook (Emergency)

If you need to bypass the pre-commit hook temporarily:
```bash
git commit --no-verify -m "Emergency commit"
```

**Note**: This should only be used in emergencies as it bypasses structure validation.

## Examples

### Successful Validation

```bash
$ python tools/dev/structure_linter.py --verbose
Linting project structure from: /path/to/project
✅ No structure violations found
```

### Violations Found

```bash
$ python tools/dev/structure_linter.py --verbose
🚨 Found 5 structure violations:

📋 Python Scripts In Root (1 violations):
  ❌ my_script.py
     Python script 'my_script.py' should not be in project root

📋 Test Files Misplaced (1 violations):
  ❌ scripts/test_something.py
     Test file 'test_something.py' should be in /tests/ directory
     💡 Suggested: tests

📋 Missing Unreleased Section (1 violations):
  ❌ CHANGELOG.md
     CHANGELOG.md missing [Unreleased] section

📋 Version Mismatch (1 violations):
  ❌ version_files
     Version mismatch across files: {'VERSION': '4.0.3', 'package.json': '4.0.2'}

📋 Missing Comparison Links (1 violations):
  ❌ CHANGELOG.md
     CHANGELOG.md missing comparison links for versions
```

### Auto-fix Results

```bash
$ python tools/dev/structure_linter.py --fix --verbose
Attempting to fix 2 violations...
✅ Fixed: my_script.py
✅ Fixed: scripts/test_something.py
Fixed 2/2 violations
```

## Best Practices

1. **Run linting frequently** during development
2. **Use auto-fix** for simple violations
3. **Review changes** after auto-fix to ensure correctness
4. **Keep structure documentation updated** when adding new rules
5. **Test the linter** after making changes to rules

## Related Documentation

- [STRUCTURE.md](STRUCTURE.md) - Project structure requirements
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guidelines
- [README.md](../README.md) - Project overview
