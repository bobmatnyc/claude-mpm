# ============================================================================
# Meta Information
# ============================================================================
# Claude MPM Installation Makefile
# =================================
# Automates the installation and setup of claude-mpm
#
# Quick start:
#   make help     - Show this help
#   make install  - Install claude-mpm globally
#   make setup    - Complete setup (install + shell config)

# ============================================================================
# PHONY Target Declarations
# ============================================================================
.PHONY: help install install-pipx install-global install-local setup-shell uninstall update clean check-pipx detect-shell backup-shell test-installation setup-pre-commit format lint type-check pre-commit-run dev-complete deprecation-check deprecation-apply cleanup all deploy-commands
.PHONY: lock-deps lock-update lock-check lock-install lock-export lock-info
.PHONY: release-check release-patch release-minor release-major release-build release-publish release-verify release-dry-run release-test-pypi release release-full release-help release-test
.PHONY: release-build-current release-publish-current
.PHONY: auto-patch auto-minor auto-major auto-build auto-help sync-versions
.PHONY: update-homebrew-tap update-homebrew-tap-dry-run
.PHONY: quality-ci build-metadata build-info-json
.PHONY: env-info env-set-dev env-set-staging env-set-prod
.PHONY: migrate-agents-v5 migrate-agents-v5-dry-run
.PHONY: agents-cache-status agents-cache-pull agents-cache-commit agents-cache-push agents-cache-sync deploy-agents

# ============================================================================
# Shell Configuration (Strict Mode)
# ============================================================================
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

# ============================================================================
# Configuration Variables
# ============================================================================
# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Environment configuration
ENV ?= development
export ENV

# Environment-specific settings
ifeq ($(ENV),production)
    PYTEST_ARGS := -n auto -v --tb=short --strict-markers
    BUILD_FLAGS := --no-isolation
else ifeq ($(ENV),staging)
    PYTEST_ARGS := -n auto -v --tb=line
    BUILD_FLAGS :=
else
    # development (default)
    PYTEST_ARGS := -n auto -v --tb=long
    BUILD_FLAGS :=
endif

# Build directories and Python executable
BUILD_DIR := build
DIST_DIR := dist
PYTHON := python3

# Detect user's shell
DETECTED_SHELL := $(shell echo $$SHELL | grep -o '[^/]*$$')
ifeq ($(DETECTED_SHELL),zsh)
    SHELL_RC := ~/.zshrc
else ifeq ($(DETECTED_SHELL),bash)
    SHELL_RC := ~/.bashrc
else
    SHELL_RC := ~/.bashrc
    $(warning Unknown shell: $(DETECTED_SHELL), defaulting to bash)
endif

# Shell wrapper function
define SHELL_WRAPPER
# Claude MPM wrapper - checks project-specific first, falls back to global
claude-mpm() {
    if [ -f ".venv/bin/claude-mpm" ]; then
        .venv/bin/claude-mpm "$$@"
    elif [ -f "venv/bin/claude-mpm" ]; then
        venv/bin/claude-mpm "$$@"
    else
        command claude-mpm "$$@"
    fi
}

# Convenient aliases
alias cmpm='claude-mpm'
alias cmt='claude-mpm tickets'
endef
export SHELL_WRAPPER

# Default target
all: setup

# ============================================================================
# Help System
# ============================================================================

help: ## Show this help message
	@echo "Claude MPM Installation Makefile"
	@echo "==============================="
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "$(BLUE)Quick Commands:$(NC)"
	@echo "  $(GREEN)make quality$(NC)        - Run all quality checks"
	@echo "  $(GREEN)make lint-fix$(NC)       - Auto-fix code issues"
	@echo "  $(GREEN)make pre-publish$(NC)    - Pre-release quality gate"
	@echo "  $(GREEN)make safe-release-build$(NC) - Build with quality checks"
	@echo ""
	@echo "$(BLUE)All Available Targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-24s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "Detected shell: $(BLUE)$(DETECTED_SHELL)$(NC)"
	@echo "Shell RC file:  $(BLUE)$(SHELL_RC)$(NC)"

# ============================================================================
# Installation Targets
# ============================================================================

check-pipx: ## Check if pipx is installed
	@if ! command -v pipx &> /dev/null; then \
		echo "$(RED)✗ pipx is not installed$(NC)"; \
		exit 1; \
	else \
		echo "$(GREEN)✓ pipx is installed$(NC)"; \
	fi

install-pipx: ## Install pipx if not already installed
	@if ! command -v pipx &> /dev/null; then \
		echo "$(YELLOW)Installing pipx...$(NC)"; \
		if command -v brew &> /dev/null; then \
			brew install pipx && pipx ensurepath; \
		elif command -v apt-get &> /dev/null; then \
			sudo apt update && sudo apt install -y pipx && pipx ensurepath; \
		elif command -v dnf &> /dev/null; then \
			sudo dnf install -y pipx && pipx ensurepath; \
		else \
			python3 -m pip install --user pipx && python3 -m pipx ensurepath; \
		fi; \
		echo "$(GREEN)✓ pipx installed successfully$(NC)"; \
		echo "$(YELLOW)Note: You may need to restart your shell or run 'source $(SHELL_RC)'$(NC)"; \
	else \
		echo "$(GREEN)✓ pipx is already installed$(NC)"; \
	fi

install-global: check-pipx ## Install claude-mpm globally from PyPI using pipx
	@echo "$(YELLOW)Installing claude-mpm globally from PyPI...$(NC)"
	@pipx install claude-mpm
	@echo "$(GREEN)✓ claude-mpm installed globally$(NC)"

install-local: check-pipx ## Install claude-mpm from current directory (development)
	@echo "$(YELLOW)Installing claude-mpm from local source...$(NC)"
	@pipx install --editable .
	@echo "$(GREEN)✓ claude-mpm installed from local source$(NC)"

install: install-pipx install-global ## Install pipx and claude-mpm globally

install-dev: install-pipx install-local ## Install pipx and claude-mpm from local source

# ============================================================================
# Dependency Management
# ============================================================================
#
# Workflow for updating dependencies:
#   1. make lock-check         - Verify current lock state
#   2. make lock-update        - Update to latest compatible versions
#   3. make test               - Test with updated deps
#   4. git diff poetry.lock    - Review changes
#   5. git add poetry.lock     - Commit if tests pass
#
# For reproducible installs:
#   make lock-install          - Install exact versions from lock file
#
# For CI/CD integration:
#   make lock-check            - Fail if lock file is outdated
#   make lock-export           - Generate requirements.txt for Docker
# ============================================================================

.PHONY: lock-deps lock-update lock-check lock-install lock-export lock-info

lock-deps: ## Lock dependencies without updating (poetry.lock)
	@echo "$(YELLOW)🔒 Locking dependencies...$(NC)"
	@if command -v poetry >/dev/null 2>&1; then \
		poetry lock --no-update; \
		echo "$(GREEN)✓ Dependencies locked in poetry.lock$(NC)"; \
	else \
		echo "$(RED)✗ Poetry not found. Install: pip install poetry$(NC)"; \
		exit 1; \
	fi

lock-update: ## Update all dependencies to latest compatible versions
	@echo "$(YELLOW)⬆️  Updating dependencies...$(NC)"
	@if command -v poetry >/dev/null 2>&1; then \
		poetry update; \
		echo "$(GREEN)✓ Dependencies updated$(NC)"; \
		echo "$(YELLOW)📋 Review changes with: git diff poetry.lock$(NC)"; \
	else \
		echo "$(RED)✗ Poetry not found. Install: pip install poetry$(NC)"; \
		exit 1; \
	fi

lock-check: ## Check if poetry.lock is up to date with pyproject.toml
	@echo "$(YELLOW)🔍 Checking lock file consistency...$(NC)"
	@if command -v poetry >/dev/null 2>&1; then \
		poetry check; \
		poetry lock --check; \
		echo "$(GREEN)✓ Lock file is up to date$(NC)"; \
	else \
		echo "$(RED)✗ Poetry not found. Install: pip install poetry$(NC)"; \
		exit 1; \
	fi

lock-install: ## Install dependencies from lock file (reproducible)
	@echo "$(YELLOW)📦 Installing from lock file...$(NC)"
	@if command -v poetry >/dev/null 2>&1; then \
		poetry install --sync; \
		echo "$(GREEN)✓ Dependencies installed from poetry.lock$(NC)"; \
	else \
		echo "$(RED)✗ Poetry not found. Install: pip install poetry$(NC)"; \
		exit 1; \
	fi

lock-export: ## Export locked dependencies to requirements.txt format
	@echo "$(YELLOW)📤 Exporting dependencies...$(NC)"
	@if command -v poetry >/dev/null 2>&1; then \
		poetry export -f requirements.txt --output requirements.txt --without-hashes; \
		poetry export -f requirements.txt --output requirements-dev.txt --with dev --without-hashes; \
		echo "$(GREEN)✓ Exported to requirements.txt and requirements-dev.txt$(NC)"; \
	else \
		echo "$(RED)✗ Poetry not found. Install: pip install poetry$(NC)"; \
		exit 1; \
	fi

lock-info: ## Display dependency lock information
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@echo "$(BLUE)Dependency Lock Information$(NC)"
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@if [ -f poetry.lock ]; then \
		echo "$(GREEN)✓ poetry.lock exists$(NC)"; \
		echo ""; \
		echo "Lock file modified: $$(stat -f %Sm -t '%Y-%m-%d %H:%M:%S' poetry.lock 2>/dev/null || stat -c %y poetry.lock 2>/dev/null || echo 'unknown')"; \
		echo "Lock file size: $$(du -h poetry.lock | cut -f1)"; \
		echo ""; \
		if command -v poetry >/dev/null 2>&1; then \
			echo "$(YELLOW)Direct dependencies:$(NC)"; \
			poetry show --tree --only main | head -20; \
		fi; \
	else \
		echo "$(RED)✗ poetry.lock not found$(NC)"; \
		echo "$(YELLOW)  Run: make lock-deps$(NC)"; \
	fi

# ============================================================================
# Development Setup
# ============================================================================

detect-shell: ## Detect user's shell
	@echo "Detected shell: $(BLUE)$(DETECTED_SHELL)$(NC)"
	@echo "Shell RC file:  $(BLUE)$(SHELL_RC)$(NC)"

backup-shell: ## Backup shell configuration file
	@if [ -f "$(SHELL_RC)" ]; then \
		backup_file="$(SHELL_RC).backup.$$(date +%Y%m%d_%H%M%S)"; \
		cp "$(SHELL_RC)" "$$backup_file"; \
		echo "$(GREEN)✓ Backed up $(SHELL_RC) to $$backup_file$(NC)"; \
	else \
		echo "$(YELLOW)⚠ No $(SHELL_RC) found, will create new one$(NC)"; \
	fi

setup-shell: backup-shell ## Add claude-mpm wrapper function to shell RC file
	@echo "$(YELLOW)Setting up shell wrapper in $(SHELL_RC)...$(NC)"
	@if grep -q "claude-mpm()" "$(SHELL_RC)" 2>/dev/null; then \
		echo "$(YELLOW)⚠ claude-mpm wrapper already exists in $(SHELL_RC)$(NC)"; \
	else \
		echo "" >> "$(SHELL_RC)"; \
		echo "$$SHELL_WRAPPER" >> "$(SHELL_RC)"; \
		echo "$(GREEN)✓ Added claude-mpm wrapper to $(SHELL_RC)$(NC)"; \
		echo "$(YELLOW)Run 'source $(SHELL_RC)' to activate or restart your shell$(NC)"; \
	fi

setup: install setup-shell ## Complete setup (install + shell configuration)
	@echo ""
	@echo "$(GREEN)✓ Claude MPM setup complete!$(NC)"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Run: $(BLUE)source $(SHELL_RC)$(NC)"
	@echo "  2. Test: $(BLUE)claude-mpm --version$(NC)"
	@echo "  3. Use: $(BLUE)claude-mpm$(NC) or $(BLUE)cmpm$(NC)"

setup-dev: install-dev setup-shell ## Complete development setup (local install + shell configuration)
	@echo ""
	@echo "$(GREEN)✓ Claude MPM development setup complete!$(NC)"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Run: $(BLUE)source $(SHELL_RC)$(NC)"
	@echo "  2. Test: $(BLUE)claude-mpm --version$(NC)"
	@echo "  3. Use: $(BLUE)claude-mpm$(NC) or $(BLUE)cmpm$(NC)"

# ============================================================================
# Utility & Cleanup
# ============================================================================

env-info: ## Display current environment configuration
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@echo "$(BLUE)Environment Configuration$(NC)"
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@echo "Environment: $(ENV)"
	@echo "Python: $$(python --version 2>&1)"
	@echo "Version: $$(cat VERSION 2>/dev/null || echo 'unknown')"
	@echo "Build: $$(cat BUILD_NUMBER 2>/dev/null || echo 'unknown')"
	@echo ""
	@echo "$(YELLOW)Environment-Specific Settings:$(NC)"
	@echo "Pytest Args: $(PYTEST_ARGS)"
	@echo "Build Flags: $(BUILD_FLAGS)"
	@echo ""
	@echo "$(GREEN)To change environment:$(NC)"
	@echo "  make ENV=production <target>"
	@echo "  make env-set-prod"

env-set-dev: ## Set environment to development
	@echo "ENV=development" > .env.make
	@echo "$(GREEN)✓ Environment set to development$(NC)"
	@echo "$(YELLOW)Note: Source .env.make or restart your shell$(NC)"

env-set-staging: ## Set environment to staging
	@echo "ENV=staging" > .env.make
	@echo "$(GREEN)✓ Environment set to staging$(NC)"
	@echo "$(YELLOW)Note: Source .env.make or restart your shell$(NC)"

env-set-prod: ## Set environment to production
	@echo "ENV=production" > .env.make
	@echo "$(GREEN)✓ Environment set to production$(NC)"
	@echo "$(YELLOW)Note: Source .env.make or restart your shell$(NC)"

uninstall: ## Uninstall claude-mpm
	@echo "$(YELLOW)Uninstalling claude-mpm...$(NC)"
	@if pipx list | grep -q claude-mpm; then \
		pipx uninstall claude-mpm; \
		echo "$(GREEN)✓ claude-mpm uninstalled$(NC)"; \
	else \
		echo "$(YELLOW)⚠ claude-mpm is not installed via pipx$(NC)"; \
	fi
	@echo ""
	@echo "$(YELLOW)Note: Shell wrapper function remains in $(SHELL_RC)$(NC)"
	@echo "Remove manually if desired, or keep for future installations"

update: check-pipx ## Update claude-mpm to latest version
	@echo "$(YELLOW)Updating claude-mpm...$(NC)"
	@if pipx list | grep -q claude-mpm; then \
		pipx upgrade claude-mpm; \
		echo "$(GREEN)✓ claude-mpm updated$(NC)"; \
	else \
		echo "$(RED)✗ claude-mpm is not installed via pipx$(NC)"; \
		echo "$(YELLOW)Run 'make install' first$(NC)"; \
		exit 1; \
	fi

reinstall: uninstall install ## Reinstall claude-mpm (uninstall + install)

clean: ## Clean up backup files
	@echo "$(YELLOW)Cleaning up backup files...$(NC)"
	@count=$$(ls -la ~ | grep -c "$(notdir $(SHELL_RC)).backup"); \
	if [ "$$count" -gt 0 ]; then \
		echo "Found $$count backup file(s)"; \
		ls -la ~ | grep "$(notdir $(SHELL_RC)).backup"; \
		read -p "Delete all backup files? [y/N] " -n 1 -r; \
		echo ""; \
		if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
			rm -f ~/$(notdir $(SHELL_RC)).backup.*; \
			echo "$(GREEN)✓ Backup files deleted$(NC)"; \
		else \
			echo "$(YELLOW)Backup files kept$(NC)"; \
		fi; \
	else \
		echo "$(GREEN)✓ No backup files found$(NC)"; \
	fi

test-installation: ## Test claude-mpm installation
	@echo "$(YELLOW)Testing claude-mpm installation...$(NC)"
	@echo ""
	@if command -v claude-mpm &> /dev/null; then \
		echo "$(GREEN)✓ claude-mpm command found$(NC)"; \
		echo "  Version: $$(claude-mpm --version 2>&1 | head -n1)"; \
		echo "  Location: $$(which claude-mpm)"; \
	else \
		echo "$(RED)✗ claude-mpm command not found$(NC)"; \
		exit 1; \
	fi
	@echo ""
	@if type claude-mpm 2>/dev/null | grep -q "function"; then \
		echo "$(GREEN)✓ Shell wrapper function is active$(NC)"; \
	else \
		echo "$(YELLOW)⚠ Shell wrapper function not active$(NC)"; \
		echo "  Run: source $(SHELL_RC)"; \
	fi
	@echo ""
	@if command -v cmpm &> /dev/null; then \
		echo "$(GREEN)✓ Alias 'cmpm' is available$(NC)"; \
	else \
		echo "$(YELLOW)⚠ Alias 'cmpm' not available$(NC)"; \
	fi
	@if command -v cmt &> /dev/null; then \
		echo "$(GREEN)✓ Alias 'cmt' is available$(NC)"; \
	else \
		echo "$(YELLOW)⚠ Alias 'cmt' not available$(NC)"; \
	fi

info: ## Show installation information
	@echo "Claude MPM Installation Information"
	@echo "==================================="
	@echo ""
	@echo "System Information:"
	@echo "  OS: $$(uname -s)"
	@echo "  Shell: $(DETECTED_SHELL)"
	@echo "  Shell RC: $(SHELL_RC)"
	@echo ""
	@echo "Python Information:"
	@echo "  Python: $$(python3 --version)"
	@echo "  Pip: $$(pip3 --version | cut -d' ' -f2)"
	@echo ""
	@echo "Pipx Information:"
	@if command -v pipx &> /dev/null; then \
		echo "  Pipx: $$(pipx --version)"; \
		echo "  Pipx home: $$(pipx environment | grep PIPX_HOME | cut -d'=' -f2)"; \
		echo "  Pipx bin: $$(pipx environment | grep PIPX_BIN_DIR | cut -d'=' -f2)"; \
	else \
		echo "  Pipx: $(RED)Not installed$(NC)"; \
	fi
	@echo ""
	@echo "Claude MPM Status:"
	@if pipx list 2>/dev/null | grep -q claude-mpm; then \
		echo "  Installation: $(GREEN)Installed via pipx$(NC)"; \
		pipx list | grep -A3 claude-mpm | sed 's/^/  /'; \
	else \
		echo "  Installation: $(RED)Not installed$(NC)"; \
	fi

# Development targets
dev-install: install-dev ## Alias for install-dev
dev-setup: setup-dev ## Alias for setup-dev

deploy-commands: ## Force deploy commands to ~/.claude/commands/ for testing
	@echo "$(YELLOW)Deploying commands for local testing...$(NC)"
	@python -c "from claude_mpm.services.command_deployment_service import deploy_commands_on_startup; deploy_commands_on_startup(force=True); print('$(GREEN)✅ Commands deployed to ~/.claude/commands/$(NC)')"

# ============================================================================
# Pre-commit Hooks
# ============================================================================

setup-pre-commit: ## Set up pre-commit hooks for code formatting and quality
	@echo "$(YELLOW)Setting up pre-commit hooks...$(NC)"
	@if [ -f "scripts/setup_pre_commit.sh" ]; then \
		./scripts/setup_pre_commit.sh; \
	else \
		echo "$(RED)✗ scripts/setup_pre_commit.sh not found$(NC)"; \
		exit 1; \
	fi

format: ## Format code with ruff (DEPRECATED: Use lint-fix)
	@echo "$(YELLOW)⚠️  DEPRECATED: Use 'make lint-fix' instead$(NC)"
	@$(MAKE) lint-fix

lint: ## Run linting checks with ruff (DEPRECATED: Use quality)
	@echo "$(YELLOW)⚠️  DEPRECATED: Use 'make quality' instead$(NC)"
	@$(MAKE) quality

type-check: ## Run type checking with mypy
	@echo "$(YELLOW)Running type checks...$(NC)"
	@if command -v mypy &> /dev/null; then \
		mypy src/ --config-file=mypy.ini; \
		echo "$(GREEN)✓ Type checking passed$(NC)"; \
	else \
		echo "$(RED)✗ mypy not found. Install with: pip install mypy$(NC)"; \
	fi

pre-commit-run: ## Run pre-commit on all files
	@echo "$(YELLOW)Running pre-commit on all files...$(NC)"
	@if command -v pre-commit &> /dev/null; then \
		pre-commit run --all-files; \
	else \
		echo "$(RED)✗ pre-commit not found. Run 'make setup-pre-commit' first$(NC)"; \
		exit 1; \
	fi

dev-complete: setup-dev setup-pre-commit ## Complete development setup with pre-commit hooks

# ============================================================================
# Testing
# ============================================================================
# Test Execution Targets

.PHONY: test test-serial test-parallel test-fast test-coverage test-unit test-integration test-e2e

test: test-parallel ## Run tests with parallel execution (default, 3-4x faster)

test-parallel: ## Run tests in parallel using all available CPUs
	@echo "$(YELLOW)🧪 Running tests in parallel (using all CPUs)...$(NC)"
	@python -m pytest tests/ $(PYTEST_ARGS)
	@echo "$(GREEN)✓ Parallel tests completed$(NC)"

test-serial: ## Run tests serially for debugging (disables parallelization)
	@echo "$(YELLOW)🧪 Running tests serially (debugging mode)...$(NC)"
	@python -m pytest tests/ -n 0 -v
	@echo "$(GREEN)✓ Serial tests completed$(NC)"

test-fast: ## Run unit tests only in parallel (fastest)
	@echo "$(YELLOW)⚡ Running unit tests in parallel...$(NC)"
	@python -m pytest tests/ -n auto -m unit -v
	@echo "$(GREEN)✓ Unit tests completed$(NC)"

test-coverage: ## Run tests with coverage report (parallel)
	@echo "$(YELLOW)📊 Running tests with coverage...$(NC)"
	@python -m pytest tests/ -n auto --cov=src/claude_mpm --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/$(NC)"

test-unit: ## Run unit tests only
	@echo "$(YELLOW)🧪 Running unit tests...$(NC)"
	@python -m pytest tests/ -n auto -m unit -v

test-integration: ## Run integration tests only
	@echo "$(YELLOW)🧪 Running integration tests...$(NC)"
	@python -m pytest tests/integration/ -n auto -v

test-e2e: ## Run end-to-end tests only
	@echo "$(YELLOW)🧪 Running e2e tests...$(NC)"
	@python -m pytest tests/e2e/ -n auto -v

deprecation-check: ## Check for obsolete files according to deprecation policy
	@echo "$(YELLOW)Checking for obsolete files...$(NC)"
	@if [ -f "scripts/apply_deprecation_policy.py" ]; then \
		python scripts/apply_deprecation_policy.py --dry-run; \
	else \
		echo "$(RED)✗ scripts/apply_deprecation_policy.py not found$(NC)"; \
		exit 1; \
	fi

deprecation-apply: ## Apply deprecation policy (remove obsolete files)
	@echo "$(YELLOW)Applying deprecation policy...$(NC)"
	@echo "$(RED)⚠️  This will remove obsolete files. Make sure you have a backup!$(NC)"
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo ""; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		if [ -f "scripts/apply_deprecation_policy.py" ]; then \
			python scripts/apply_deprecation_policy.py; \
		else \
			echo "$(RED)✗ scripts/apply_deprecation_policy.py not found$(NC)"; \
			exit 1; \
		fi; \
	else \
		echo "$(YELLOW)Deprecation policy application cancelled$(NC)"; \
	fi

cleanup: deprecation-check ## Alias for deprecation-check

# Quick targets
quick: setup ## Alias for complete setup
quick-dev: setup-dev ## Alias for complete development setup

# ============================================================================
# Quality & Linting
# ============================================================================
# Quality Gates and Linting Targets

.PHONY: lint-all lint-ruff lint-black lint-isort lint-flake8 lint-mypy lint-structure
.PHONY: lint-fix quality pre-publish safe-release-build
.PHONY: clean-system-files clean-test-artifacts clean-debug clean-deprecated clean-pre-publish

# Individual linters
lint-ruff: ## Run ruff linter and formatter check
	@echo "$(YELLOW)🔍 Running ruff linter...$(NC)"
	@if command -v ruff &> /dev/null; then \
		ruff check src/ tests/ scripts/ || exit 1; \
		echo "$(GREEN)✓ Ruff linting passed$(NC)"; \
		echo "$(YELLOW)🔍 Checking code formatting...$(NC)"; \
		ruff format --check src/ tests/ scripts/ || exit 1; \
		echo "$(GREEN)✓ Ruff format check passed$(NC)"; \
	else \
		echo "$(RED)✗ ruff not found. Install with: pip install ruff$(NC)"; \
		exit 1; \
	fi

# DEPRECATED: Consolidated into ruff
lint-black: ## (DEPRECATED: Use lint-ruff) Check code formatting with black
	@echo "$(YELLOW)⚠️  DEPRECATED: lint-black is replaced by lint-ruff$(NC)"
	@echo "$(YELLOW)Run 'make lint-ruff' instead$(NC)"
	@exit 1

# DEPRECATED: Consolidated into ruff
lint-isort: ## (DEPRECATED: Use lint-ruff) Check import sorting with isort
	@echo "$(YELLOW)⚠️  DEPRECATED: lint-isort is replaced by lint-ruff$(NC)"
	@echo "$(YELLOW)Run 'make lint-ruff' instead$(NC)"
	@exit 1

# DEPRECATED: Consolidated into ruff
lint-flake8: ## (DEPRECATED: Use lint-ruff) Run flake8 linter
	@echo "$(YELLOW)⚠️  DEPRECATED: lint-flake8 is replaced by lint-ruff$(NC)"
	@echo "$(YELLOW)Run 'make lint-ruff' instead$(NC)"
	@exit 1

lint-mypy: ## Run mypy type checker
	@echo "$(YELLOW)🔍 Running mypy type checker...$(NC)"
	@if command -v mypy &> /dev/null; then \
		mypy src/claude_mpm --ignore-missing-imports --no-error-summary || true; \
		echo "$(YELLOW)ℹ MyPy check complete (informational)$(NC)"; \
	else \
		echo "$(YELLOW)⚠ mypy not found. Install with: pip install mypy$(NC)"; \
	fi

lint-structure: ## Check project structure compliance
	@echo "$(YELLOW)🏗️ Checking project structure...$(NC)"
	@if [ -f "tools/dev/structure_linter.py" ]; then \
		python3 tools/dev/structure_linter.py || exit 1; \
		echo "$(GREEN)✓ Structure check passed$(NC)"; \
	else \
		echo "$(RED)✗ Structure linter not found$(NC)"; \
		exit 1; \
	fi

# Comprehensive linting
lint-all: ## Run all linters (ruff + mypy + structure)
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@echo "$(BLUE)Running all quality checks...$(NC)"
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@$(MAKE) lint-ruff
	@$(MAKE) lint-structure
	@$(MAKE) lint-mypy
	@echo ""
	@echo "$(GREEN)════════════════════════════════════════$(NC)"
	@echo "$(GREEN)✅ All linting checks passed!$(NC)"
	@echo "$(GREEN)════════════════════════════════════════$(NC)"

# Auto-fix what can be fixed
lint-fix: ## Auto-fix linting issues (ruff format + ruff check --fix)
	@echo "$(YELLOW)🔧 Auto-fixing code issues with ruff...$(NC)"
	@if command -v ruff &> /dev/null; then \
		echo "$(YELLOW)Fixing linting issues...$(NC)"; \
		ruff check src/ tests/ scripts/ --fix || true; \
		echo "$(GREEN)✓ Ruff linting fixes applied$(NC)"; \
		echo "$(YELLOW)Formatting code...$(NC)"; \
		ruff format src/ tests/ scripts/ || true; \
		echo "$(GREEN)✓ Code formatted$(NC)"; \
	else \
		echo "$(RED)✗ ruff not found. Install with: pip install ruff$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Fixing structure issues...$(NC)"
	@if [ -f "tools/dev/structure_linter.py" ]; then \
		python tools/dev/structure_linter.py --fix || true; \
		echo "$(GREEN)✓ Structure fixes attempted$(NC)"; \
	fi
	@echo ""
	@echo "$(GREEN)✅ Auto-fix complete. Run 'make quality' to verify.$(NC)"

# Quality alias
quality: lint-all ## Alias for lint-all (run all quality checks)

.PHONY: quality-ci
quality-ci: ## Quality checks for CI/CD (strict, fail fast)
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@echo "$(BLUE)Running CI quality checks (strict mode)...$(NC)"
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@set -e; \
	echo "$(YELLOW)🔍 Checking lock file...$(NC)"; \
	$(MAKE) lock-check || exit 1; \
	echo "$(YELLOW)🔍 Ruff check (no fixes)...$(NC)"; \
	ruff check src/ tests/ scripts/ --no-fix; \
	echo "$(YELLOW)🔍 Type checking...$(NC)"; \
	mypy src/ --ignore-missing-imports; \
	echo "$(YELLOW)🧪 Running tests (parallel)...$(NC)"; \
	pytest tests/ -n auto -v --tb=short
	@echo ""
	@echo "$(GREEN)════════════════════════════════════════$(NC)"
	@echo "$(GREEN)✅ CI quality checks passed!$(NC)"
	@echo "$(GREEN)════════════════════════════════════════$(NC)"

# Pre-publish quality gate
pre-publish: clean-pre-publish ## Run cleanup and all quality checks before publishing (required for releases)
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@echo "$(BLUE)🚀 Pre-Publish Quality Gate$(NC)"
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 1/5: Checking working directory...$(NC)"
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "$(RED)✗ Working directory is not clean$(NC)"; \
		echo "$(YELLOW)Please commit or stash your changes first$(NC)"; \
		git status --short; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ Working directory is clean$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 2/5: Running all linters...$(NC)"
	@$(MAKE) lint-all
	@echo ""
	@echo "$(YELLOW)Step 3/5: Running tests...$(NC)"
	@if [ -f "scripts/run_all_tests.sh" ]; then \
		bash scripts/run_all_tests.sh || exit 1; \
	elif command -v pytest >/dev/null 2>&1; then \
		python -m pytest tests/ -n auto -v || exit 1; \
	else \
		echo "$(YELLOW)⚠ No test runner found, skipping tests$(NC)"; \
	fi
	@echo "$(GREEN)✓ Tests passed$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 4/5: Checking for common issues...$(NC)"
	@echo "Checking for debug prints..."
	@! grep -r "print(" src/ --include="*.py" | grep -v "#" | grep -v "logger" || \
		echo "$(YELLOW)⚠ Found print statements in code (consider using logger, but allowed for CLI/diagnostic tools)$(NC)"
	@echo "Checking for TODO/FIXME..."
	@! grep -r "TODO\|FIXME" src/ --include="*.py" | head -5 || \
		echo "$(YELLOW)⚠ Found TODO/FIXME comments (non-blocking)$(NC)"
	@echo "$(GREEN)✓ Common issues check complete$(NC)"
	@echo ""
	@echo "$(YELLOW)Step 5/5: Validating version consistency...$(NC)"
	@python scripts/check_version_consistency.py || \
		echo "$(YELLOW)⚠ Version consistency check failed (non-blocking)$(NC)"
	@echo ""
	@echo "$(GREEN)════════════════════════════════════════$(NC)"
	@echo "$(GREEN)✅ Pre-publish checks PASSED!$(NC)"
	@echo "$(GREEN)Ready for release.$(NC)"
	@echo "$(GREEN)════════════════════════════════════════$(NC)"

# Structure linting targets (kept for compatibility)
structure-lint: lint-structure ## Check project structure compliance
structure-fix: ## Fix project structure issues
	@echo "$(YELLOW)🔧 Running structure linting with auto-fix...$(NC)"
	@python tools/dev/structure_linter.py --fix --verbose

# ============================================================================
# Build Targets
# ============================================================================

.PHONY: build-metadata build-info-json build-dev build-prod

build-dev: ## Development build (fast, no checks)
	@echo "$(YELLOW)📦 Building for $(ENV) environment...$(NC)"
	@rm -rf $(DIST_DIR) $(BUILD_DIR)
	@$(PYTHON) -m build --wheel $(BUILD_FLAGS)
	@echo "$(GREEN)✓ Development build complete (ENV=$(ENV))$(NC)"

build-prod: quality ## Production build (with all checks)
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@echo "$(BLUE)🔒 Production Build (ENV=$(ENV))$(NC)"
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@if [ "$(ENV)" != "production" ] && [ "$(ENV)" != "staging" ]; then \
		echo "$(RED)✗ Production build requires ENV=production or ENV=staging$(NC)"; \
		echo "$(YELLOW)  Run: make ENV=production build-prod$(NC)"; \
		exit 1; \
	fi
	@$(MAKE) build-metadata
	@rm -rf $(DIST_DIR) $(BUILD_DIR) *.egg-info
	@$(PYTHON) -m build $(BUILD_FLAGS)
	@twine check $(DIST_DIR)/*
	@$(MAKE) build-info-json
	@echo "$(GREEN)✓ Production build complete (ENV=$(ENV))$(NC)"

build-metadata: ## Track build metadata in JSON format
	@echo "$(YELLOW)📋 Tracking build metadata...$(NC)"
	@mkdir -p $(BUILD_DIR)
	@VERSION=$$(cat VERSION); \
	BUILD_NUM=$$(cat BUILD_NUMBER); \
	COMMIT=$$(git rev-parse HEAD 2>/dev/null || echo "unknown"); \
	SHORT_COMMIT=$$(git rev-parse --short HEAD 2>/dev/null || echo "unknown"); \
	BRANCH=$$(git branch --show-current 2>/dev/null || echo "unknown"); \
	TIMESTAMP=$$(date -u +%Y-%m-%dT%H:%M:%SZ); \
	PYTHON_VER=$$(python --version 2>&1); \
	echo "{" > $(BUILD_DIR)/metadata.json; \
	echo '  "version": "'$$VERSION'",' >> $(BUILD_DIR)/metadata.json; \
	echo '  "build_number": '$$BUILD_NUM',' >> $(BUILD_DIR)/metadata.json; \
	echo '  "commit": "'$$COMMIT'",' >> $(BUILD_DIR)/metadata.json; \
	echo '  "commit_short": "'$$SHORT_COMMIT'",' >> $(BUILD_DIR)/metadata.json; \
	echo '  "branch": "'$$BRANCH'",' >> $(BUILD_DIR)/metadata.json; \
	echo '  "timestamp": "'$$TIMESTAMP'",' >> $(BUILD_DIR)/metadata.json; \
	echo '  "python_version": "'$$PYTHON_VER'",' >> $(BUILD_DIR)/metadata.json; \
	echo '  "environment": "'$${ENV:-development}'"' >> $(BUILD_DIR)/metadata.json; \
	echo "}" >> $(BUILD_DIR)/metadata.json
	@echo "$(GREEN)✓ Build metadata saved to $(BUILD_DIR)/metadata.json$(NC)"

build-info-json: build-metadata ## Display build metadata from JSON
	@if [ -f $(BUILD_DIR)/metadata.json ]; then \
		cat $(BUILD_DIR)/metadata.json; \
	else \
		echo "$(YELLOW)No build metadata found. Run 'make build-metadata' first.$(NC)"; \
	fi

# ============================================================================
# Version Management
# ============================================================================
# Release Management Targets
.PHONY: release-check release-patch release-minor release-major release-build release-publish release-verify
.PHONY: release-dry-run release-test-pypi increment-build

# Release prerequisites check
release-check: ## Check if environment is ready for release
	@echo "$(YELLOW)🔍 Checking release prerequisites...$(NC)"
	@echo "Checking required tools..."
	@command -v git >/dev/null 2>&1 || (echo "$(RED)✗ git not found$(NC)" && exit 1)
	@command -v python >/dev/null 2>&1 || (echo "$(RED)✗ python not found$(NC)" && exit 1)
	@command -v cz >/dev/null 2>&1 || (echo "$(RED)✗ commitizen not found. Install with: pip install commitizen$(NC)" && exit 1)
	@command -v gh >/dev/null 2>&1 || (echo "$(RED)✗ GitHub CLI not found. Install from: https://cli.github.com/$(NC)" && exit 1)
	@echo "$(GREEN)✓ All required tools found$(NC)"
	@echo "Checking working directory..."
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "$(RED)✗ Working directory is not clean$(NC)"; \
		git status --short; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ Working directory is clean$(NC)"
	@echo "Checking current branch..."
	@BRANCH=$$(git branch --show-current); \
	if [ "$$BRANCH" != "main" ]; then \
		echo "$(YELLOW)⚠ Currently on branch '$$BRANCH', not 'main'$(NC)"; \
		read -p "Continue anyway? [y/N]: " confirm; \
		if [ "$$confirm" != "y" ] && [ "$$confirm" != "Y" ]; then \
			echo "$(RED)Aborted$(NC)"; \
			exit 1; \
		fi; \
	else \
		echo "$(GREEN)✓ On main branch$(NC)"; \
	fi
	@echo "$(GREEN)✓ Release prerequisites check passed$(NC)"

# Run tests before release
release-test: ## Run test suite before release
	@echo "$(YELLOW)🧪 Running test suite...$(NC)"
	@if [ -f "scripts/run_all_tests.sh" ]; then \
		bash scripts/run_all_tests.sh; \
	elif command -v pytest >/dev/null 2>&1; then \
		python -m pytest tests/ -n auto -v; \
	else \
		echo "$(YELLOW)⚠ No test runner found, skipping tests$(NC)"; \
	fi
	@echo "$(GREEN)✓ Tests passed$(NC)"

# Build the package (with quality checks)
release-build: pre-publish ## Build Python package for release (runs quality checks first)
	@echo "$(YELLOW)📦 Building package...$(NC)"
	@echo "$(YELLOW)🔢 Incrementing build number...$(NC)"
	@python scripts/increment_build.py --all-changes
	@rm -rf dist/ build/ *.egg-info
	@python -m build
	@echo "$(GREEN)✓ Package built successfully$(NC)"
	@ls -la dist/

# Safe release build (explicit quality gate)
safe-release-build: ## Build release with mandatory quality checks
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@echo "$(BLUE)🔒 Safe Release Build (ENV=$(ENV))$(NC)"
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@$(MAKE) pre-publish
	@echo ""
	@echo "$(YELLOW)📦 Building package after quality checks...$(NC)"
	@echo "$(YELLOW)🔢 Incrementing build number...$(NC)"
	@$(PYTHON) scripts/increment_build.py --all-changes
	@$(MAKE) build-metadata
	@rm -rf $(DIST_DIR) $(BUILD_DIR) *.egg-info
	@$(PYTHON) -m build $(BUILD_FLAGS)
	@echo "$(GREEN)✓ Package built successfully with quality assurance (ENV=$(ENV))$(NC)"
	@ls -la $(DIST_DIR)

# ============================================================================
# Pre-Publish Cleanup Targets
# ============================================================================

clean-system-files: ## Remove system files (.DS_Store, __pycache__, *.pyc)
	@echo "$(YELLOW)🧹 Cleaning system files...$(NC)"
	@find . -name ".DS_Store" -not -path "*/venv/*" -not -path "*/.venv/*" -delete 2>/dev/null || true
	@find . -type d -name "__pycache__" -not -path "*/venv/*" -not -path "*/.venv/*" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -not -path "*/venv/*" -not -path "*/.venv/*" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ System files cleaned$(NC)"

clean-test-artifacts: ## Remove test artifacts (HTML, JSON reports in root)
	@echo "$(YELLOW)🧹 Cleaning test artifacts from root...$(NC)"
	@rm -f dashboard_test.html report_qa_test.html coverage.json 2>/dev/null || true
	@echo "$(GREEN)✓ Test artifacts cleaned$(NC)"

clean-debug: ## Remove debug scripts (requires confirmation)
	@echo "$(YELLOW)🧹 This will remove debug scripts from tools/dev/ and scripts/development/$(NC)"
	@echo "$(RED)⚠️  Debug scripts will be permanently deleted!$(NC)"
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo ""; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		find tools/dev -name "debug_*.py" -delete 2>/dev/null || true; \
		find scripts/development -name "debug_*.py" -delete 2>/dev/null || true; \
		echo "$(GREEN)✓ Debug scripts removed$(NC)"; \
	else \
		echo "$(YELLOW)Debug cleanup cancelled$(NC)"; \
	fi

clean-deprecated: ## Remove explicitly deprecated files
	@echo "$(YELLOW)🧹 Removing deprecated documentation...$(NC)"
	@rm -f src/claude_mpm/agents/INSTRUCTIONS_OLD_DEPRECATED.md 2>/dev/null || true
	@echo "$(GREEN)✓ Deprecated files removed$(NC)"

clean-pre-publish: clean-system-files clean-test-artifacts clean-deprecated ## Complete pre-publish cleanup (safe automated cleanup)
	@echo ""
	@echo "$(GREEN)════════════════════════════════════════$(NC)"
	@echo "$(GREEN)✅ Pre-publish cleanup complete!$(NC)"
	@echo "$(GREEN)════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)💡 Manual review recommended for:$(NC)"
	@echo "  • Debug scripts: make clean-debug"
	@echo "  • Test memory directory: tests/test-temp-memory/"
	@echo "  • Archived HTML tests: src/claude_mpm/dashboard/static/archive/"
	@echo ""

# Increment build number
increment-build: ## Increment build number for code changes
	@echo "$(YELLOW)🔢 Incrementing build number...$(NC)"
	@python scripts/increment_build.py --all-changes
	@echo "$(GREEN)✓ Build number incremented$(NC)"

# Patch release (bug fixes)
release-patch: release-check release-test ## Create a patch release (bug fixes)
	@echo "$(YELLOW)🔧 Creating patch release...$(NC)"
	@cz bump --increment PATCH
	@$(MAKE) release-build
	@echo "$(GREEN)✓ Patch release prepared$(NC)"
	@echo "$(BLUE)Next: Run 'make release-publish' to publish$(NC)"

# Minor release (new features)
release-minor: release-check release-test ## Create a minor release (new features)
	@echo "$(YELLOW)✨ Creating minor release...$(NC)"
	@cz bump --increment MINOR
	@$(MAKE) release-build
	@echo "$(GREEN)✓ Minor release prepared$(NC)"
	@echo "$(BLUE)Next: Run 'make release-publish' to publish$(NC)"

# Major release (breaking changes)
release-major: release-check release-test ## Create a major release (breaking changes)
	@echo "$(YELLOW)💥 Creating major release...$(NC)"
	@cz bump --increment MAJOR
	@$(MAKE) release-build
	@echo "$(GREEN)✓ Major release prepared$(NC)"
	@echo "$(BLUE)Next: Run 'make release-publish' to publish$(NC)"

# ============================================================================
# Publishing Workflow
# ============================================================================

# Publish to PyPI using .env.local credentials
publish-pypi: ## Publish package to PyPI using credentials from .env.local
	@echo "$(YELLOW)📤 Publishing to PyPI with .env.local credentials...$(NC)"
	@./scripts/publish_to_pypi.sh

# Update Homebrew tap formula (non-blocking)
update-homebrew-tap: ## Update Homebrew tap formula after PyPI publish (non-blocking)
	@echo "$(YELLOW)🍺 Updating Homebrew tap...$(NC)"
	@VERSION=$$(cat VERSION); \
	if [ -f "scripts/update_homebrew_tap.sh" ]; then \
		./scripts/update_homebrew_tap.sh "$$VERSION" || { \
			echo "$(YELLOW)⚠️  Homebrew tap update failed (non-blocking)$(NC)"; \
			echo "$(YELLOW)Manual fallback: cd homebrew-tools && ./scripts/update_formula.sh $$VERSION$(NC)"; \
		}; \
	else \
		echo "$(YELLOW)⚠️  Homebrew update script not found (skipping)$(NC)"; \
	fi

update-homebrew-tap-dry-run: ## Test Homebrew tap update without making changes
	@echo "$(YELLOW)🍺 Testing Homebrew tap update (dry run)...$(NC)"
	@VERSION=$$(cat VERSION); \
	if [ -f "scripts/update_homebrew_tap.sh" ]; then \
		./scripts/update_homebrew_tap.sh "$$VERSION" --dry-run; \
	else \
		echo "$(RED)✗ Homebrew update script not found$(NC)"; \
		exit 1; \
	fi

# Publish release to all channels
release-publish: ## Publish release to PyPI, npm, Homebrew, and GitHub
	@echo "$(YELLOW)🚀 Publishing release...$(NC)"
	@VERSION=$$(cat VERSION); \
	echo "Publishing version: $$VERSION"; \
	read -p "Continue with publishing? [y/N]: " confirm; \
	if [ "$$confirm" != "y" ] && [ "$$confirm" != "Y" ]; then \
		echo "$(RED)Publishing aborted$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)📤 Publishing to PyPI...$(NC)"
	@if command -v twine >/dev/null 2>&1; then \
		python -m twine upload dist/*; \
		echo "$(GREEN)✓ Published to PyPI$(NC)"; \
	else \
		echo "$(RED)✗ twine not found. Install with: pip install twine$(NC)"; \
		exit 1; \
	fi
	@echo ""
	@echo "$(YELLOW)🍺 Updating Homebrew tap (non-blocking)...$(NC)"
	@$(MAKE) update-homebrew-tap || echo "$(YELLOW)⚠️  Homebrew update failed, continuing with release$(NC)"
	@echo ""
	@echo "$(YELLOW)📤 Publishing to npm...$(NC)"
	@if command -v npm >/dev/null 2>&1; then \
		npm publish || echo "$(YELLOW)⚠ npm publish failed, continuing...$(NC)"; \
		echo "$(GREEN)✓ npm publish attempted$(NC)"; \
	else \
		echo "$(YELLOW)⚠ npm not found, skipping npm publish$(NC)"; \
	fi
	@echo "$(YELLOW)📤 Creating GitHub release...$(NC)"
	@VERSION=$$(cat VERSION); \
	gh release create "v$$VERSION" \
		--title "Claude MPM v$$VERSION" \
		--notes-from-tag \
		dist/* || echo "$(YELLOW)⚠ GitHub release creation failed, continuing...$(NC)"
	@echo "$(GREEN)✓ GitHub release created$(NC)"
	@$(MAKE) release-verify

# Publish to TestPyPI for testing
release-test-pypi: release-build ## Publish to TestPyPI for testing
	@echo "$(YELLOW)🧪 Publishing to TestPyPI...$(NC)"
	@if command -v twine >/dev/null 2>&1; then \
		python -m twine upload --repository testpypi dist/*; \
		echo "$(GREEN)✓ Published to TestPyPI$(NC)"; \
	else \
		echo "$(RED)✗ twine not found. Install with: pip install twine$(NC)"; \
		exit 1; \
	fi

# Verify release was successful
release-verify: ## Verify release across all channels
	@echo "$(YELLOW)🔍 Verifying release...$(NC)"
	@VERSION=$$(cat VERSION); \
	echo "Verifying version: $$VERSION"; \
	echo ""; \
	echo "$(BLUE)📦 PyPI:$(NC) https://pypi.org/project/claude-mpm/$$VERSION/"; \
	echo "$(BLUE)📦 npm:$(NC) https://www.npmjs.com/package/@bobmatnyc/claude-mpm/v/$$VERSION"; \
	echo "$(BLUE)🏷️  GitHub:$(NC) https://github.com/bobmatnyc/claude-mpm/releases/tag/v$$VERSION"; \
	echo ""; \
	echo "$(GREEN)✓ Release verification links generated$(NC)"
	@echo "$(BLUE)💡 Test installation with:$(NC)"
	@echo "  pip install claude-mpm==$$(cat VERSION)"
	@echo "  npm install -g @bobmatnyc/claude-mpm@$$(cat VERSION)"

# Dry run - show what would be done without executing
release-dry-run: ## Show what a patch release would do (dry run)
	@echo "$(YELLOW)🔍 DRY RUN: Patch release preview$(NC)"
	@echo "This would:"
	@echo "  1. Check prerequisites and working directory"
	@echo "  2. Run tests"
	@echo "  3. Bump patch version using commitizen"
	@echo "  4. Sync version files (VERSION, src/claude_mpm/VERSION, package.json)"
	@echo "  5. Build Python package"
	@echo "  6. Wait for confirmation to publish"
	@echo "  7. Publish to PyPI, npm, and create GitHub release"
	@echo "  8. Show verification links"
	@echo ""
	@echo "$(BLUE)Current version:$(NC) $$(cat VERSION)"
	@echo "$(BLUE)Next patch version would be:$(NC) $$(python -c "import semver; print(semver.VersionInfo.parse('$$(cat VERSION)').bump_patch())" 2>/dev/null || echo "unknown")"

# Complete release workflow shortcuts
release: release-patch ## Alias for patch release (most common)
release-full: release-patch release-publish ## Complete patch release with publishing

# Build current version without version bump
release-build-current: ## Build current version without version bump
	@echo "$(YELLOW)📦 Building current version...$(NC)"
	@VERSION=$$(cat VERSION); \
	echo "Building version: $$VERSION"
	@rm -rf dist/ build/ *.egg-info
	@python -m build
	@echo "$(GREEN)✓ Package built successfully$(NC)"
	@ls -la dist/

# Publish current version (if already built)
release-publish-current: ## Publish current built version
	@echo "$(YELLOW)🚀 Publishing current version...$(NC)"
	@if [ ! -d "dist" ] || [ -z "$$(ls -A dist)" ]; then \
		echo "$(RED)✗ No dist/ directory or it's empty. Run build first.$(NC)"; \
		exit 1; \
	fi
	@VERSION=$$(cat VERSION); \
	echo "Publishing version: $$VERSION"; \
	read -p "Continue with publishing? [y/N]: " confirm; \
	if [ "$$confirm" != "y" ] && [ "$$confirm" != "Y" ]; then \
		echo "$(RED)Publishing aborted$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)📤 Publishing to PyPI...$(NC)"
	@if command -v twine >/dev/null 2>&1; then \
		python -m twine upload dist/*; \
		echo "$(GREEN)✓ Published to PyPI$(NC)"; \
	else \
		echo "$(RED)✗ twine not found. Install with: pip install twine$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)📤 Publishing to npm...$(NC)"
	@if command -v npm >/dev/null 2>&1; then \
		npm publish || echo "$(YELLOW)⚠ npm publish failed, continuing...$(NC)"; \
		echo "$(GREEN)✓ npm publish attempted$(NC)"; \
	else \
		echo "$(YELLOW)⚠ npm not found, skipping npm publish$(NC)"; \
	fi
	@echo "$(YELLOW)📤 Creating GitHub release...$(NC)"
	@VERSION=$$(cat VERSION); \
	gh release create "v$$VERSION" \
		--title "Claude MPM v$$VERSION" \
		--notes-from-tag \
		dist/* || echo "$(YELLOW)⚠ GitHub release creation failed, continuing...$(NC)"
	@echo "$(GREEN)✓ GitHub release created$(NC)"
	@$(MAKE) release-verify

# Help for release targets
release-help: ## Show release management help
	@echo "$(BLUE)Claude MPM Release Management$(NC)"
	@echo "============================="
	@echo ""
	@echo "$(GREEN)Standard Release Process (Commitizen):$(NC)"
	@echo "  make release-patch     # Bug fix release (X.Y.Z+1)"
	@echo "  make release-minor     # Feature release (X.Y+1.0)"
	@echo "  make release-major     # Breaking change release (X+1.0.0)"
	@echo "  make release-publish   # Publish prepared release"
	@echo ""
	@echo "$(GREEN)Current Version Publishing:$(NC)"
	@echo "  make release-build-current    # Build current version"
	@echo "  make release-publish-current  # Publish current built version"
	@echo ""
	@echo "$(GREEN)Testing & Verification:$(NC)"
	@echo "  make release-dry-run   # Preview what would happen"
	@echo "  make release-test-pypi # Publish to TestPyPI"
	@echo "  make release-verify    # Show verification links"
	@echo ""
	@echo "$(GREEN)Individual Steps:$(NC)"
	@echo "  make release-check     # Check prerequisites"
	@echo "  make release-test      # Run test suite"
	@echo "  make increment-build   # Increment build number"
	@echo "  make release-build     # Build package"
	@echo ""
	@echo "$(GREEN)Quick Workflows:$(NC)"
	@echo "  make release           # Alias for patch release"
	@echo "  make release-full      # Complete patch release with publishing"
	@echo ""
	@echo "$(YELLOW)Prerequisites:$(NC)"
	@echo "  • git, python, commitizen (cz), GitHub CLI (gh)"
	@echo "  • Clean working directory on main branch"
	@echo "  • PyPI and npm credentials configured"
	@echo ""
	@echo "$(BLUE)Current version:$(NC) $$(cat VERSION)"
	@echo "$(BLUE)Version management:$(NC) Commitizen (conventional commits)"

# ============================================================================
# Automated Release System (Alternative to Commitizen)
# ============================================================================
# These targets use the new automated release script for streamlined releases

.PHONY: auto-patch auto-minor auto-major auto-build auto-help sync-versions

# Automated patch release
auto-patch: ## Automated patch release (alternative to commitizen)
	@echo "$(YELLOW)🔧 Creating automated patch release...$(NC)"
	python scripts/automated_release.py --patch
	@echo "$(GREEN)✓ Automated patch release completed$(NC)"

# Automated minor release
auto-minor: ## Automated minor release (alternative to commitizen)
	@echo "$(YELLOW)✨ Creating automated minor release...$(NC)"
	python scripts/automated_release.py --minor
	@echo "$(GREEN)✓ Automated minor release completed$(NC)"

# Automated major release
auto-major: ## Automated major release (alternative to commitizen)
	@echo "$(YELLOW)💥 Creating automated major release...$(NC)"
	python scripts/automated_release.py --major
	@echo "$(GREEN)✓ Automated major release completed$(NC)"

# Automated build-only release
auto-build: ## Automated build-only release (no version bump)
	@echo "$(YELLOW)📦 Creating automated build release...$(NC)"
	python scripts/automated_release.py --build
	@echo "$(GREEN)✓ Automated build release completed$(NC)"

# Sync version files
sync-versions: ## Sync version between root and package VERSION files
	@echo "$(YELLOW)🔄 Syncing version files...$(NC)"
	@VERSION=$$(cat VERSION); \
	echo "$$VERSION" > src/claude_mpm/VERSION; \
	echo "$(GREEN)✓ Synced src/claude_mpm/VERSION to $$VERSION$(NC)"

# Help for automated release system
auto-help: ## Show automated release system help
	@echo "$(BLUE)Claude MPM Automated Release System$(NC)"
	@echo "===================================="
	@echo ""
	@echo "$(GREEN)Automated Release Process:$(NC)"
	@echo "  make auto-patch        # Bug fix release (X.Y.Z+1) - fully automated"
	@echo "  make auto-minor        # Feature release (X.Y+1.0) - fully automated"
	@echo "  make auto-major        # Breaking release (X+1.0.0) - fully automated"
	@echo "  make auto-build        # Build-only release (no version bump)"
	@echo ""
	@echo "$(GREEN)Utilities:$(NC)"
	@echo "  make sync-versions     # Sync version files"
	@echo "  make auto-help         # Show this help"
	@echo ""
	@echo "$(YELLOW)Features:$(NC)"
	@echo "  • Automatic version file synchronization"
	@echo "  • Smart build number increment"
	@echo "  • Automatic CHANGELOG updates"
	@echo "  • Complete Git workflow (commit, tag, push)"
	@echo "  • PyPI publishing"
	@echo "  • Structure validation"
	@echo ""
	@echo "$(BLUE)Current version:$(NC) $$(cat VERSION)"
	@echo "$(BLUE)Build number:$(NC) $$(cat BUILD_NUMBER)"
	@echo "$(BLUE)Version management:$(NC) Automated script (scripts/automated_release.py)"

# ============================================================================
# Migration Targets
# ============================================================================

# Migrate from JSON-template agents to Git-sourced agents (v5.0)
migrate-agents-v5: ## Migrate old JSON-template agents to Git-sourced agents
	@echo "$(YELLOW)🔄 Starting v5.0 agent migration...$(NC)"
	python scripts/migrate_agents_v5.py --force
	@echo "$(GREEN)✓ Migration completed$(NC)"

# Dry run of agent migration
migrate-agents-v5-dry-run: ## Preview agent migration without making changes
	@echo "$(BLUE)🔍 Previewing v5.0 agent migration (dry run)...$(NC)"
	python scripts/migrate_agents_v5.py --dry-run
	@echo "$(GREEN)✓ Dry run completed$(NC)"

# ============================================================================
# Agent Cache Git Management
# ============================================================================
# Git workflow integration for managing agent cache at ~/.claude-mpm/cache/remote-agents/

.PHONY: agents-cache-status agents-cache-pull agents-cache-commit agents-cache-push agents-cache-sync

# Check git status of agent cache
agents-cache-status: ## Show git status of agent cache
	@echo "$(BLUE)📊 Agent cache git status:$(NC)"
	@claude-mpm agents cache-status

# Pull latest agents from remote
agents-cache-pull: ## Pull latest agents from remote repository
	@echo "$(YELLOW)🔄 Pulling latest agents from remote...$(NC)"
	@claude-mpm agents cache-pull
	@echo "$(GREEN)✓ Pull complete$(NC)"

# Commit local agent changes
agents-cache-commit: ## Commit changes to agent cache
	@echo "$(YELLOW)💾 Committing agent cache changes...$(NC)"
	@claude-mpm agents cache-commit --message "feat: update agents from local development"
	@echo "$(GREEN)✓ Changes committed$(NC)"

# Push agent changes to remote
agents-cache-push: ## Push agent changes to remote repository
	@echo "$(YELLOW)📤 Pushing agent changes to remote...$(NC)"
	@claude-mpm agents cache-push
	@echo "$(GREEN)✓ Changes pushed$(NC)"

# Full cache sync (pull, commit, push)
agents-cache-sync: ## Full agent cache sync with remote
	@echo "$(YELLOW)🔄 Syncing agent cache with remote...$(NC)"
	@claude-mpm agents cache-sync
	@echo "$(GREEN)✓ Sync complete$(NC)"

# Deploy agents with latest cache (integrates git pull)
deploy-agents: agents-cache-pull ## Deploy agents with latest changes from remote
	@echo "$(YELLOW)🚀 Deploying agents...$(NC)"
	@claude-mpm agents deploy
	@echo "$(GREEN)✓ Agents deployed$(NC)"

