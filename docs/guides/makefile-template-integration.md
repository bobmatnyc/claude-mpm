# Python Project Template Integration Guide

The [python-project-template](https://github.com/bobmatnyc/python-project-template) provides a reusable, modular Makefile system extracted from claude-mpm's production codebase.

## Table of Contents

- [Overview](#overview)
- [Quick Start: New Projects](#quick-start-new-projects)
- [Updating Existing Projects](#updating-existing-projects)
- [Template Updates](#template-updates)
- [Customization Guide](#customization-guide)
- [Available Targets Reference](#available-targets-reference)
- [Environment-Aware Builds](#environment-aware-builds)
- [Troubleshooting](#troubleshooting)
- [Links and Resources](#links-and-resources)

## Overview

This Copier-based template gives you:
- **5 modular Makefile components** (941 lines, 41 targets)
- **Ruff-only linting** (10-200x faster than Black+Flake8+isort)
- **ENV-aware builds** (development/staging/production)
- **Parallel testing** (pytest-xdist for 3-4x speedup)
- **Release automation** (semantic versioning, PyPI publishing)
- **Update support** (template changes propagate via `copier update`)

### Why Use This Template?

**For New Projects:**
- Get claude-mpm's production-tested Makefile system instantly
- Skip the tedious setup of quality tools and workflows
- Start with battle-tested release automation
- Benefit from ongoing template improvements

**For Existing Projects:**
- Modernize your build system with proven patterns
- Replace slow linters with Ruff (10-200x faster)
- Add parallel testing for faster CI/CD
- Standardize workflows across multiple projects

### What You Get

```
your-project/
├── Makefile                 # Main entry point
├── .makefiles/             # Modular components
│   ├── common.mk           # Core infrastructure (colors, ENV system)
│   ├── quality.mk          # Linting, formatting, type checking
│   ├── testing.mk          # Test execution, coverage
│   ├── deps.mk             # Dependency management
│   └── release.mk          # Versioning, building, publishing
├── pyproject.toml          # Ruff configuration
├── pytest.ini              # Test configuration
└── .copier-answers.yml     # Template version tracking
```

## Quick Start: New Projects

### Prerequisites

```bash
# Install Copier
pip install copier
# or
pipx install copier
```

### Create New Project

```bash
# Generate project from template
copier copy gh:bobmatnyc/python-project-template my-new-project

# Answer template questions:
# - Project name: My Awesome Project
# - Python version: 3.11
# - Include testing: Yes
# - Include release automation: Yes
# - GitHub username: yourusername

cd my-new-project
```

### Verify Setup

```bash
# See available Make targets
make help

# Run quality checks
make quality

# Run tests
make test

# Install in development mode
make install
```

### First Commit

```bash
git init
git add .
git commit -m "feat: initialize project from python-project-template"
```

## Updating Existing Projects

### Option 1: Full Template Migration (Recommended)

**Best for:** Projects willing to adopt the full template system.

```bash
cd your-existing-project

# Backup current Makefile
cp Makefile Makefile.backup

# Apply template
copier copy --force gh:bobmatnyc/python-project-template .

# Answer questions to match your project settings

# Review changes
git diff Makefile
git diff pyproject.toml

# Merge any custom targets from Makefile.backup
# Then commit the changes
git add Makefile .makefiles/ pyproject.toml
git commit -m "feat: migrate to python-project-template Makefile system"
```

**Migration Checklist:**
- [ ] Back up current Makefile
- [ ] Run `copier copy --force`
- [ ] Review and merge custom targets
- [ ] Update pyproject.toml with Ruff config
- [ ] Test all Make targets: `make help`
- [ ] Run quality checks: `make quality`
- [ ] Verify tests pass: `make test`
- [ ] Commit changes

### Option 2: Selective Module Integration

**Best for:** Projects that want specific components only.

```bash
# Create .makefiles directory
mkdir -p .makefiles

# Download specific modules (choose what you need)
curl -o .makefiles/common.mk https://raw.githubusercontent.com/bobmatnyc/python-project-template/main/template/.makefiles/common.mk
curl -o .makefiles/quality.mk https://raw.githubusercontent.com/bobmatnyc/python-project-template/main/template/.makefiles/quality.mk
curl -o .makefiles/testing.mk https://raw.githubusercontent.com/bobmatnyc/python-project-template/main/template/.makefiles/testing.mk

# Include in your Makefile (at the top)
cat >> Makefile << 'EOF'

# Include reusable modules
-include .makefiles/common.mk
-include .makefiles/quality.mk
-include .makefiles/testing.mk
EOF
```

**Module Dependencies:**
- `common.mk` - Required by all other modules (provides core infrastructure)
- `quality.mk` - Requires `common.mk`
- `testing.mk` - Requires `common.mk`
- `deps.mk` - Requires `common.mk`
- `release.mk` - Requires `common.mk`, `quality.mk`, `deps.mk`

### Option 3: Manual Cherry-Picking

**Best for:** Projects that want specific targets only.

```bash
# Download a single module
curl -o .makefiles/quality.mk https://raw.githubusercontent.com/bobmatnyc/python-project-template/main/template/.makefiles/quality.mk

# Extract specific targets into your Makefile
# Example: Copy just the lint-fix target
```

**Recommended Targets to Cherry-Pick:**
- `lint-fix` - Auto-fix linting issues
- `test` - Parallel test execution
- `quality` - Comprehensive quality gate
- `pre-publish` - Pre-release validation

## Template Updates

When the template receives updates, you can pull them into your project:

```bash
cd your-project

# Update from template
copier update

# Review changes
git diff

# Commit updated files
git add .
git commit -m "chore: update from python-project-template"
```

### Automate Updates with GitHub Actions

Create `.github/workflows/update-template.yml`:

```yaml
name: Update Template
on:
  schedule:
    - cron: '0 0 1 * *'  # Monthly on the 1st
  workflow_dispatch:      # Manual trigger

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Copier
        run: pipx install copier

      - name: Update from template
        run: copier update --force --trust

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          title: "chore: update from python-project-template"
          body: |
            Automated update from python-project-template.

            Please review changes before merging.
          branch: chore/update-template
          commit-message: "chore: update from python-project-template"
```

### Version Pinning

Pin to a specific template version:

```yaml
# .copier-answers.yml
_commit: v1.0.0  # Pin to tag/commit
_src_path: gh:bobmatnyc/python-project-template
```

## Customization Guide

### Override Variables

Variables are defined in `common.mk`. Override them in your main `Makefile`:

```makefile
# Makefile
-include .makefiles/common.mk

# Override default variables
SRC_DIR := lib           # instead of src/
TESTS_DIR := test        # instead of tests/
PYTHON := python3.12     # specific version
PACKAGE_NAME := mypackage

# Override ENV-specific settings
ifeq ($(ENV),production)
    PYTEST_ARGS := -n 4 --maxfail=1  # custom production settings
endif
```

**Common Overrides:**
```makefile
SRC_DIR := lib                    # Source directory
TESTS_DIR := test                 # Test directory
PYTHON := python3.12              # Python interpreter
PYTEST_ARGS := -v --tb=short      # Pytest arguments
RUFF_ARGS := --fix                # Ruff arguments
PACKAGE_NAME := my_package        # Package name
```

### Add Project-Specific Targets

Add custom targets after the module includes:

```makefile
# Makefile (after all includes)

.PHONY: custom-deploy custom-seed custom-docs

custom-deploy: pre-publish ## Deploy to staging
	@echo "$(BLUE)Deploying to staging...$(RESET)"
	./scripts/deploy.sh staging

custom-seed: ## Seed development database
	@echo "$(BLUE)Seeding database...$(RESET)"
	python scripts/seed_db.py

custom-docs: ## Build documentation
	@echo "$(BLUE)Building docs...$(RESET)"
	cd docs && make html
```

**Best Practices:**
- Use `.PHONY` for non-file targets
- Add `##` comments for `make help` display
- Use color variables from `common.mk`: `$(BLUE)`, `$(GREEN)`, `$(RED)`, `$(RESET)`
- Chain with existing targets: `custom-deploy: pre-publish`

### Customize Quality Checks

```makefile
# Override specific quality targets
lint-mypy:
	mypy $(SRC_DIR) --ignore-missing-imports --exclude=tests/

# Add custom pre-commit checks
pre-publish: quality custom-security-scan

custom-security-scan:
	@echo "$(BLUE)Running security scan...$(RESET)"
	bandit -r $(SRC_DIR)
	safety check
```

### Customize Test Execution

```makefile
# Override test target
test-unit:
	$(PYTHON) -m pytest $(TESTS_DIR)/unit $(PYTEST_ARGS)

test-integration:
	$(PYTHON) -m pytest $(TESTS_DIR)/integration $(PYTEST_ARGS) --no-cov

# Add custom test suites
test-smoke:
	$(PYTHON) -m pytest $(TESTS_DIR) -m smoke --maxfail=1
```

### Add ENV-Specific Behavior

```makefile
# Add production-specific checks
ifeq ($(ENV),production)
pre-publish: quality security-scan

security-scan:
	bandit -r $(SRC_DIR)
	safety check --full-report
endif
```

## Available Targets Reference

### Quality Targets (quality.mk)

| Target | Description | ENV-Aware |
|--------|-------------|-----------|
| `make lint-ruff` | Run Ruff linter | ✅ |
| `make lint-fix` | Auto-fix with Ruff | ✅ |
| `make lint-mypy` | Type checking with mypy | ✅ |
| `make quality` | All quality checks | ✅ |
| `make pre-publish` | Pre-release quality gate | ✅ |

**Usage:**
```bash
# Development - verbose output
make lint-fix

# Production - strict mode
ENV=production make quality
```

### Testing Targets (testing.mk)

| Target | Description | ENV-Aware |
|--------|-------------|-----------|
| `make test` | Run tests (parallel by default) | ✅ |
| `make test-serial` | Single-threaded tests | ✅ |
| `make test-coverage` | With coverage report | ✅ |
| `make test-unit` | Unit tests only | ❌ |
| `make test-integration` | Integration tests | ❌ |

**Usage:**
```bash
# Fast parallel testing
make test

# Serial execution (for debugging)
make test-serial

# Coverage report
make test-coverage
```

### Dependency Targets (deps.mk)

| Target | Description | ENV-Aware |
|--------|-------------|-----------|
| `make install` | Development installation | ❌ |
| `make lock-deps` | Update lock files | ❌ |
| `make lock-check` | Verify lock sync | ❌ |
| `make lock-install` | Install from lock | ❌ |

**Usage:**
```bash
# Install in development mode
make install

# Update dependencies
make lock-deps

# Verify lock files are in sync
make lock-check
```

### Release Targets (release.mk)

| Target | Description | ENV-Aware |
|--------|-------------|-----------|
| `make patch` | Bump patch version | ❌ |
| `make minor` | Bump minor version | ❌ |
| `make major` | Bump major version | ❌ |
| `make release-build` | Build packages | ✅ |
| `make release-publish` | Publish to PyPI | ✅ |

**Usage:**
```bash
# Bump version and create tag
make patch  # 1.0.0 -> 1.0.1

# Build distribution packages
make release-build

# Publish to PyPI
ENV=production make release-publish
```

### Common Targets (common.mk)

| Target | Description |
|--------|-------------|
| `make help` | Show all targets with descriptions |
| `make clean` | Remove build artifacts |
| `make clean-pyc` | Remove Python cache files |
| `make clean-test` | Remove test artifacts |

**Provides:**
- Color variables: `$(BLUE)`, `$(GREEN)`, `$(RED)`, `$(YELLOW)`, `$(RESET)`
- ENV system: `development`, `staging`, `production`
- Common variables: `PYTHON`, `SRC_DIR`, `TESTS_DIR`
- Utility functions: `@echo`, error handling

## Environment-Aware Builds

The template supports three environments with different behavior:

### Development (Default)

```bash
make test
# or
ENV=development make test
```

**Characteristics:**
- Verbose output
- Detailed error messages
- All warnings shown
- Development dependencies included
- Fast feedback for iteration

### Staging

```bash
ENV=staging make test
```

**Characteristics:**
- Balanced verbosity
- Important warnings only
- Performance similar to production
- Used for pre-release validation

### Production

```bash
ENV=production make quality
ENV=production make release-build
```

**Characteristics:**
- Minimal output
- Strict mode (warnings as errors)
- Optimized performance
- Production dependencies only
- Security-focused

### ENV-Specific Configuration

```makefile
ifeq ($(ENV),development)
    PYTEST_ARGS := -v --tb=long
    RUFF_ARGS := --verbose
endif

ifeq ($(ENV),staging)
    PYTEST_ARGS := -v --tb=short
    RUFF_ARGS :=
endif

ifeq ($(ENV),production)
    PYTEST_ARGS := -q --tb=line --maxfail=1
    RUFF_ARGS := --quiet
endif
```

## Troubleshooting

### Issue: Copier not found

**Error:**
```
bash: copier: command not found
```

**Solution:**
```bash
pip install copier
# or
pipx install copier
```

### Issue: Make targets not found after update

**Error:**
```
make: *** No rule to make target 'quality'.  Stop.
```

**Solution:**
```bash
# Ensure includes are at the top of Makefile
head Makefile

# Should see:
# -include .makefiles/common.mk
# -include .makefiles/quality.mk

# If missing, add them:
cat > Makefile << 'EOF'
-include .makefiles/common.mk
-include .makefiles/quality.mk
-include .makefiles/testing.mk

# ... your custom targets ...
EOF
```

### Issue: Permission denied on scripts

**Error:**
```
bash: ./scripts/deploy.sh: Permission denied
```

**Solution:**
```bash
chmod +x scripts/*.sh
chmod +x scripts/*.py
```

### Issue: Ruff not installed

**Error:**
```
make: ruff: Command not found
```

**Solution:**
```bash
pip install ruff
# or add to pyproject.toml:
# [tool.poetry.dependencies]
# ruff = "^0.8.0"
```

### Issue: Parallel tests failing

**Error:**
```
pytest: error: unrecognized arguments: -n 4
```

**Solution:**
```bash
# Install pytest-xdist
pip install pytest-xdist

# Or use serial tests
make test-serial
```

### Issue: Module includes failing silently

**Symptom:** Make targets missing, no errors shown.

**Cause:** The `-include` directive fails silently if files don't exist.

**Solution:**
```bash
# Check if .makefiles directory exists
ls -la .makefiles/

# Re-download missing modules
curl -o .makefiles/quality.mk https://raw.githubusercontent.com/bobmatnyc/python-project-template/main/template/.makefiles/quality.mk

# Or reapply template
copier update
```

### Issue: ENV variable not working

**Symptom:** ENV-specific behavior not triggering.

**Debugging:**
```makefile
# Add to Makefile for debugging
debug-env:
	@echo "ENV: $(ENV)"
	@echo "PYTEST_ARGS: $(PYTEST_ARGS)"
```

**Solution:**
```bash
# Set ENV before make command
ENV=production make quality

# Check ENV in Makefile
make debug-env
```

## Links and Resources

### Template & Documentation
- **Template Repository**: https://github.com/bobmatnyc/python-project-template
- **Claude MPM** (source project): https://github.com/bobmatnyc/claude-mpm
- **Copier Documentation**: https://copier.readthedocs.io/

### Tools & Dependencies
- **Ruff Linter**: https://docs.astral.sh/ruff/
- **pytest-xdist**: https://pytest-xdist.readthedocs.io/
- **GNU Make Manual**: https://www.gnu.org/software/make/manual/

### Related Guides
- **[Contributing Guide](../../CONTRIBUTING.md)** - Claude MPM contribution guidelines
- **[Release Documentation](../reference/DEPLOY.md)** - Complete release workflow

## Example Projects Using Template

### Production Projects
- **claude-mpm** - Multi-agent project manager (source of template)
  - Repository: https://github.com/bobmatnyc/claude-mpm
  - 941 lines, 41 targets, battle-tested in production

### Community Projects
Want to add your project here? Submit a PR!

## Contributing to Template

Found a bug or have an improvement for the template?

### Report Issues
- **Bug Reports**: https://github.com/bobmatnyc/python-project-template/issues
- **Feature Requests**: https://github.com/bobmatnyc/python-project-template/issues

### Submit Improvements

1. **Fork the template**:
   ```bash
   git clone https://github.com/bobmatnyc/python-project-template
   cd python-project-template
   ```

2. **Create a branch**:
   ```bash
   git checkout -b feature/my-improvement
   ```

3. **Test your changes**:
   ```bash
   # Test template generation
   copier copy . /tmp/test-project
   cd /tmp/test-project
   make help
   make quality
   ```

4. **Submit PR**:
   - Clear description of improvement
   - Test results
   - Rationale for changes

### Template Development Guidelines
- Keep modules independent
- Maintain backward compatibility
- Document all variables
- Add examples for new features
- Test with multiple Python versions

## Version History

### v1.0.0 (2025-11-21) - Initial Release
- **5 modular .mk files**: common, quality, testing, deps, release
- **41 make targets**: Comprehensive development workflow
- **Ruff-only linting**: 10-200x faster than Black+Flake8+isort
- **ENV-aware builds**: development, staging, production
- **Parallel testing**: pytest-xdist integration for 3-4x speedup
- **Copier template**: Reusable, updatable project template
- **Release automation**: Semantic versioning, PyPI publishing

### Roadmap
- [ ] CI/CD templates (GitHub Actions, GitLab CI)
- [ ] Docker integration
- [ ] Pre-commit hooks configuration
- [ ] Multi-language support (JS, Go, Rust)
- [ ] Cloud deployment targets (AWS, GCP, Azure)

---

**Questions or Issues?**

- **Template Issues**: https://github.com/bobmatnyc/python-project-template/issues
- **Integration Help**: https://github.com/bobmatnyc/claude-mpm/discussions
- **Claude MPM Issues**: https://github.com/bobmatnyc/claude-mpm/issues

**Quick Tip**: Most integration questions are answered in the [Customization Guide](#customization-guide) and [Troubleshooting](#troubleshooting) sections above!
