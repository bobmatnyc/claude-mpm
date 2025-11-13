# Environment Validation Workflows

> **Part of**: [env-manager](../SKILL.md)
> **Category**: infrastructure
> **Reading Level**: Intermediate

## Purpose

Complete validation workflows for environment variables: structure checks, completeness verification, naming conventions, and framework-specific validation patterns.

## Validation Hierarchy

### Level 1: Structure Validation (Basic)
Validates file format and syntax.

### Level 2: Semantic Validation (Intermediate)
Validates naming, completeness, framework conventions.

### Level 3: Integration Validation (Advanced)
Validates across environments, platforms, and services.

## Structure Validation

### Check 1: Valid Key-Value Format

**What to Check:**
```bash
# Valid formats:
KEY=value
KEY="value with spaces"
KEY='single quoted'
KEY=

# Invalid formats:
key=value              # lowercase
KEY = value            # spaces around =
KEY=value # comment    # inline comments (parser-dependent)
=value                 # missing key
KEY                    # missing =
```

**Validation Script:**
```python
import re
from pathlib import Path

def validate_structure(env_file: Path) -> list[str]:
    """Validate .env file structure."""
    errors = []
    valid_line_pattern = re.compile(r'^[A-Z_][A-Z0-9_]*=.*$')

    with open(env_file) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Check format
            if not valid_line_pattern.match(line):
                errors.append(f"Line {line_num}: Invalid format: {line}")

            # Check for inline comments (warning)
            if '#' in line and not line.startswith('#'):
                # Check if # is inside quotes
                key, value = line.split('=', 1)
                if '#' in value and not (value.startswith('"') or value.startswith("'")):
                    errors.append(f"Line {line_num}: WARNING: Possible inline comment: {line}")

    return errors
```

### Check 2: No Duplicate Keys

**Issue:**
```bash
# .env file
DATABASE_URL=postgres://local
DATABASE_URL=postgres://production  # Duplicate! Which wins?
```

**Validation:**
```python
def check_duplicates(env_file: Path) -> dict[str, list[int]]:
    """Find duplicate keys and their line numbers."""
    keys = {}

    with open(env_file) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if '=' in line:
                key = line.split('=', 1)[0]
                if key in keys:
                    keys[key].append(line_num)
                else:
                    keys[key] = [line_num]

    # Return only duplicates
    return {k: v for k, v in keys.items() if len(v) > 1}
```

### Check 3: Proper Quoting

**Valid Quoting Patterns:**
```bash
# No quotes needed
SIMPLE_VALUE=hello

# Quotes required for spaces
WITH_SPACES="hello world"

# Quotes required for special chars
SPECIAL_CHARS="value with = or # chars"

# Escape quotes inside quotes
ESCAPED="He said \"hello\""
ESCAPED_SINGLE='It'\''s working'
```

**Validation:**
```python
def validate_quoting(env_file: Path) -> list[str]:
    """Check for proper quoting."""
    warnings = []

    with open(env_file) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            key, value = line.split('=', 1)

            # Check for spaces without quotes
            if ' ' in value and not (value.startswith('"') or value.startswith("'")):
                warnings.append(f"Line {line_num}: Value with spaces should be quoted: {key}")

            # Check for special chars without quotes
            if any(char in value for char in ['#', '=', '$']) and not value.startswith(('"', "'")):
                warnings.append(f"Line {line_num}: Value with special chars should be quoted: {key}")

    return warnings
```

## Completeness Validation

### Compare Against .env.example

**Workflow:**
```python
def compare_env_files(env_file: Path, example_file: Path) -> dict:
    """Compare .env against .env.example."""

    def parse_keys(file_path: Path) -> set[str]:
        keys = set()
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key = line.split('=', 1)[0]
                    keys.add(key)
        return keys

    env_keys = parse_keys(env_file)
    example_keys = parse_keys(example_file)

    return {
        'missing': example_keys - env_keys,  # Required but missing
        'extra': env_keys - example_keys,    # Present but not documented
        'common': env_keys & example_keys    # Properly documented
    }
```

**Usage:**
```bash
# Find missing required variables
python validate_env.py .env --compare .env.example

# Output:
# Missing variables (in .env.example but not .env):
#   - DATABASE_URL
#   - JWT_SECRET
#   - SMTP_HOST
#
# Extra variables (in .env but not documented):
#   - DEBUG_MODE
#   - TEMP_API_KEY
```

### Check Required Variables by Environment

**Pattern:**
```python
REQUIRED_VARS = {
    'development': [
        'NODE_ENV',
        'DATABASE_URL',
        'PORT'
    ],
    'production': [
        'NODE_ENV',
        'DATABASE_URL',
        'PORT',
        'JWT_SECRET',
        'API_KEY',
        'REDIS_URL'
    ],
    'test': [
        'NODE_ENV',
        'TEST_DATABASE_URL'
    ]
}

def validate_required_vars(env_file: Path, environment: str) -> list[str]:
    """Check if all required variables are present."""
    required = REQUIRED_VARS.get(environment, [])
    present = parse_keys(env_file)

    missing = [var for var in required if var not in present]
    return missing
```

## Naming Convention Validation

### Standard Conventions

**Valid Names:**
```bash
# Standard format: UPPERCASE_WITH_UNDERSCORES
DATABASE_URL=value
API_KEY=value
MAX_CONNECTIONS=10

# Framework-specific prefixes
NEXT_PUBLIC_API_URL=value       # Next.js client-side
VITE_API_URL=value              # Vite client-side
REACT_APP_API_URL=value         # Create React App
```

**Invalid Names:**
```bash
# Bad patterns
databaseUrl=value          # camelCase
database-url=value         # kebab-case
database.url=value         # dots
123_KEY=value              # starts with number
_PRIVATE_KEY=value         # leading underscore (convention warning)
```

**Validation:**
```python
import re

def validate_naming_conventions(env_file: Path, framework: str = None) -> list[str]:
    """Validate variable naming conventions."""
    errors = []

    # Standard pattern
    standard_pattern = re.compile(r'^[A-Z][A-Z0-9_]*$')

    # Framework-specific patterns
    framework_patterns = {
        'nextjs': re.compile(r'^(NEXT_PUBLIC_|NEXT_)[A-Z0-9_]+$'),
        'vite': re.compile(r'^(VITE_)?[A-Z0-9_]+$'),
        'react': re.compile(r'^(REACT_APP_)?[A-Z0-9_]+$'),
    }

    with open(env_file) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            key = line.split('=', 1)[0]

            # Check standard pattern
            if not standard_pattern.match(key):
                errors.append(f"Line {line_num}: Invalid naming: {key} (use UPPERCASE_WITH_UNDERSCORES)")

            # Check framework-specific patterns
            if framework and framework in framework_patterns:
                pattern = framework_patterns[framework]
                if not pattern.match(key):
                    errors.append(f"Line {line_num}: {framework} convention violation: {key}")

    return errors
```

## Framework-Specific Validation

### Next.js Validation

**Rules:**
```python
def validate_nextjs_env(env_file: Path) -> list[str]:
    """Validate Next.js environment variables."""
    errors = []
    warnings = []

    with open(env_file) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            key, value = line.split('=', 1)

            # Check NEXT_PUBLIC_ prefix rules
            if key.startswith('NEXT_PUBLIC_'):
                # Warn about secrets in public vars
                if any(secret in key.lower() for secret in ['secret', 'key', 'password', 'token']):
                    errors.append(f"Line {line_num}: SECURITY: Secret in NEXT_PUBLIC_ var: {key}")

            # Check for client-side vars without NEXT_PUBLIC_
            if any(client in key.lower() for client in ['api_url', 'api_endpoint']):
                if not key.startswith('NEXT_PUBLIC_'):
                    warnings.append(f"Line {line_num}: Client-side var without NEXT_PUBLIC_: {key}")

    return errors, warnings
```

**File Precedence Check:**
```python
def check_nextjs_file_precedence(project_dir: Path) -> dict:
    """Check Next.js .env file precedence."""
    env_files = [
        '.env.local',
        '.env.development.local',
        '.env.production.local',
        '.env.development',
        '.env.production',
        '.env'
    ]

    found_files = []
    for env_file in env_files:
        if (project_dir / env_file).exists():
            found_files.append(env_file)

    # Parse and check for conflicts
    all_vars = {}
    for env_file in found_files:
        vars_in_file = parse_env_file(project_dir / env_file)
        for key, value in vars_in_file.items():
            if key in all_vars:
                all_vars[key].append((env_file, value))
            else:
                all_vars[key] = [(env_file, value)]

    # Find variables defined in multiple files
    conflicts = {k: v for k, v in all_vars.items() if len(v) > 1}

    return {
        'files_found': found_files,
        'conflicts': conflicts,
        'precedence_order': env_files
    }
```

### Express/Node.js Validation

**Standard Variables:**
```python
NODE_STANDARD_VARS = {
    'NODE_ENV': ['development', 'production', 'test'],
    'PORT': r'^\d+$',  # Must be a number
    'DATABASE_URL': r'^postgres://|mysql://|mongodb://',  # Must be valid connection string
}

def validate_nodejs_env(env_file: Path) -> list[str]:
    """Validate Node.js environment variables."""
    errors = []
    vars_dict = parse_env_file(env_file)

    for key, value in vars_dict.items():
        if key in NODE_STANDARD_VARS:
            expected = NODE_STANDARD_VARS[key]

            if isinstance(expected, list):
                # Check enumeration
                if value not in expected:
                    errors.append(f"{key}: Invalid value '{value}', expected one of {expected}")
            elif isinstance(expected, str):
                # Check regex pattern
                if not re.match(expected, value):
                    errors.append(f"{key}: Value doesn't match expected format")

    return errors
```

## Summary

**Validation Workflow:**
1. **Structure**: Valid format, no duplicates, proper quoting
2. **Completeness**: All required vars present, compare with .env.example
3. **Naming**: UPPERCASE_WITH_UNDERSCORES, framework prefixes
4. **Framework**: Next.js NEXT_PUBLIC_, file precedence
5. **Platform**: Vercel/Railway/Heroku conventions

**Key Validations:**
- ✅ Valid key-value format
- ✅ No duplicate keys
- ✅ Proper quoting for spaces/special chars
- ✅ All required variables present
- ✅ Consistent naming conventions
- ✅ Framework-specific rules followed
- ✅ No secrets in client-side vars (NEXT_PUBLIC_)

## Related References

- [Security](security.md): Secret scanning and exposure detection
- [Synchronization](synchronization.md): Platform sync validation
- [Frameworks](frameworks.md): Complete framework patterns

---
**Lines**: 285 ✓ 150-300 range
