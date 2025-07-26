# Claude MPM Project Guidelines

This document provides guidelines for working with the claude-mpm project.

## Project Overview

Claude MPM (Multi-Agent Project Manager) is a framework for Claude that enables multi-agent workflows and extensible capabilities.

## Key Resources

- 📁 **Project Structure**: See [docs/STRUCTURE.md](docs/STRUCTURE.md) for file organization
- 🧪 **Quality Assurance**: See [docs/QA.md](docs/QA.md) for testing guidelines
- 🚀 **Deployment**: See [docs/DEPLOY.md](docs/DEPLOY.md) for versioning and deployment
- 📊 **Logging**: See [docs/LOGGING.md](docs/LOGGING.md) for comprehensive logging guide
- 🔢 **Versioning**: See [docs/VERSIONING.md](docs/VERSIONING.md) for version management

## Validation Rules

### MANDATORY: File Creation Rules
- **NEVER** create files in the project root directory
- **ALWAYS** validate path before file creation:
  ```
  ✅ /scripts/new_script.py
  ✅ /tests/test_feature.py
  ✅ /src/claude_mpm/new_module.py
  ❌ /new_file.py
  ❌ ./random_script.sh
  ```

### MANDATORY: Import Rules
- **ALWAYS** use full package imports:
  ```python
  ✅ from claude_mpm.agents import BaseAgent
  ❌ from agents import BaseAgent
  ```

### MANDATORY: Testing Rules
- **MUST** run tests after any of these changes:
  - Agent profile modifications
  - Hook system changes
  - Service layer updates
  - CLI command changes
- **VALIDATION**: If tests fail, DO NOT proceed with deployment

### FORBIDDEN: Security Rules
- **NEVER** commit credentials or API keys
- **NEVER** log sensitive information
- **NEVER** disable security validations
- **NEVER** execute untrusted code without validation

## Development Guidelines

### Before Making Changes

1. **Validate Structure Compliance**:
   ```
   RULE: Scripts → /scripts/
   RULE: Tests → /tests/
   RULE: Python modules → /src/claude_mpm/
   ```

2. **Pre-Change Validation Checklist**:
   - [ ] Virtual environment activated
   - [ ] Latest main branch pulled
   - [ ] No uncommitted changes
   - [ ] Tests passing on main

3. **Change Validation**:
   - [ ] Imports use full package name
   - [ ] New files in correct directories
   - [ ] Tests added for new features
   - [ ] Documentation updated

### Testing Requirements

**MANDATORY Testing Sequence**:
```bash
# 1. Pre-change validation
./scripts/run_e2e_tests.sh || exit 1

# 2. Make your changes

# 3. Post-change validation
./scripts/run_e2e_tests.sh || exit 1
./scripts/run_all_tests.sh || exit 1

# 4. Only proceed if ALL tests pass
```

### Agent Development Rules

**VALIDATION**: Every agent MUST have:
- [ ] Unique agent_id
- [ ] Valid description (10-100 chars)
- [ ] At least one tool in tools array
- [ ] Valid prompt template
- [ ] Test coverage > 80%

**FORBIDDEN**: Agents MUST NOT:
- Access files outside project directory
- Execute system commands without validation
- Modify core framework files
- Bypass hook system

### Hook System Rules

**MANDATORY**: All hooks MUST:
- Return within 5 seconds
- Handle errors gracefully
- Log all actions
- Be idempotent

**VALIDATION**: Hook registration requires:
```python
# Valid hook structure
hook = {
    "name": str,  # Required, unique
    "type": Literal["pre", "post"],  # Required
    "target": str,  # Required, valid target
    "handler": Callable,  # Required
    "priority": int,  # Optional, 0-100
}
```

## Validation Enforcement

### Automated Validation
The following validations run automatically:
1. **Pre-commit**: File path validation, import checking
2. **Pre-push**: Full test suite, security scan
3. **CI/CD**: Complete validation pipeline

### Manual Validation Required
You MUST manually validate:
1. **Breaking Changes**: Run full regression test
2. **New Dependencies**: Security audit required
3. **Agent Modifications**: Test in isolation first
4. **Production Deployment**: Staging validation required

## Quick Start

```bash
# Validate environment first
./scripts/validate_environment.sh || exit 1

# Interactive mode
./claude-mpm

# Non-interactive mode
./claude-mpm run -i "Your prompt here" --non-interactive
```

## Common Issues & Validations

### Import Errors
**VALIDATION**: Before reporting import errors:
```bash
# Check virtual environment
which python | grep -q "venv" || echo "ERROR: Not in virtual environment"

# Validate PYTHONPATH
echo $PYTHONPATH | grep -q "src" || echo "ERROR: PYTHONPATH missing src/"

# Test import
python -c "import claude_mpm" || echo "ERROR: Package not installed"
```

### Hook Service Errors
**VALIDATION**: Check ports before starting:
```bash
# Validate port availability
for port in {8080..8099}; do
    lsof -i :$port > /dev/null 2>&1 || { echo "Port $port available"; break; }
done
```

## Contributing

### Validation Gates
Your contribution MUST pass these gates:
1. ✅ Structure validation (automated)
2. ✅ Import validation (automated)
3. ✅ Test coverage > 80% (automated)
4. ✅ Security scan clean (automated)
5. ✅ Documentation complete (manual review)
6. ✅ Breaking change assessment (manual review)

### Commit Message Validation
**MANDATORY Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**VALID Types**: feat, fix, docs, style, refactor, test, chore
**VALIDATION**: Commits rejected if format invalid

## Deployment

### Pre-Deployment Validation
**MANDATORY**: Run full validation suite:
```bash
./scripts/pre_deployment_validation.sh || {
    echo "DEPLOYMENT BLOCKED: Validation failed"
    exit 1
}
```

### Deployment Rules
1. **NEVER** deploy on Fridays
2. **ALWAYS** deploy to staging first
3. **MUST** have rollback plan
4. **REQUIRE** 2-person deployment approval

## Validation Errors Reference

### Error Codes
- `VAL001`: File in wrong directory
- `VAL002`: Invalid import format
- `VAL003`: Missing test coverage
- `VAL004`: Security validation failed
- `VAL005`: Hook timeout exceeded
- `VAL006`: Agent validation failed

### Error Resolution
Each error includes:
1. Specific validation that failed
2. Example of correct implementation
3. Command to auto-fix (if available)
4. Documentation reference

---
**ENFORCEMENT**: These rules are automatically validated. Violations will block commits, builds, and deployments.