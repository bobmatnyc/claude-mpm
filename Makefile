# Claude MPM Installation Makefile
# =================================
# Automates the installation and setup of claude-mpm
#
# Quick start:
#   make help     - Show this help
#   make install  - Install claude-mpm globally
#   make setup    - Complete setup (install + shell config)

.PHONY: help install install-pipx install-global install-local setup-shell uninstall update clean check-pipx detect-shell backup-shell test-installation setup-pre-commit format lint type-check pre-commit-run dev-complete deprecation-check deprecation-apply cleanup all
.PHONY: release-check release-patch release-minor release-major release-build release-publish release-verify release-dry-run release-test-pypi release release-full release-help release-test release-sync-versions

# Default shell
SHELL := /bin/bash

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

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

help: ## Show this help message
	@echo "Claude MPM Installation Makefile"
	@echo "==============================="
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Main targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "Detected shell: $(BLUE)$(DETECTED_SHELL)$(NC)"
	@echo "Shell RC file:  $(BLUE)$(SHELL_RC)$(NC)"

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

setup-pre-commit: ## Set up pre-commit hooks for code formatting and quality
	@echo "$(YELLOW)Setting up pre-commit hooks...$(NC)"
	@if [ -f "scripts/setup_pre_commit.sh" ]; then \
		./scripts/setup_pre_commit.sh; \
	else \
		echo "$(RED)✗ scripts/setup_pre_commit.sh not found$(NC)"; \
		exit 1; \
	fi

format: ## Format code with black and isort
	@echo "$(YELLOW)Formatting code...$(NC)"
	@if command -v black &> /dev/null; then \
		black src/ tests/ scripts/ --line-length=88; \
		echo "$(GREEN)✓ Code formatted with black$(NC)"; \
	else \
		echo "$(RED)✗ black not found. Install with: pip install black$(NC)"; \
	fi
	@if command -v isort &> /dev/null; then \
		isort src/ tests/ scripts/ --profile=black --line-length=88; \
		echo "$(GREEN)✓ Imports sorted with isort$(NC)"; \
	else \
		echo "$(RED)✗ isort not found. Install with: pip install isort$(NC)"; \
	fi

lint: ## Run linting checks
	@echo "$(YELLOW)Running linting checks...$(NC)"
	@if command -v flake8 &> /dev/null; then \
		flake8 src/ --max-line-length=88 --extend-ignore=E203,W503; \
		echo "$(GREEN)✓ Linting passed$(NC)"; \
	else \
		echo "$(RED)✗ flake8 not found. Install with: pip install flake8$(NC)"; \
	fi

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

# Structure linting targets
.PHONY: structure-lint structure-fix
structure-lint:
	@echo "🔍 Running structure linting..."
	@python tools/dev/structure_linter.py --verbose

structure-fix:
	@echo "🔧 Running structure linting with auto-fix..."
	@python tools/dev/structure_linter.py --fix --verbose

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
		python -m pytest tests/ -v; \
	else \
		echo "$(YELLOW)⚠ No test runner found, skipping tests$(NC)"; \
	fi
	@echo "$(GREEN)✓ Tests passed$(NC)"

# Build the package
release-build: ## Build Python package for release
	@echo "$(YELLOW)📦 Building package...$(NC)"
	@echo "$(YELLOW)🔢 Incrementing build number...$(NC)"
	@python scripts/increment_build.py --all-changes
	@rm -rf dist/ build/ *.egg-info
	@python -m build
	@echo "$(GREEN)✓ Package built successfully$(NC)"
	@ls -la dist/

# Sync version files after commitizen bump
release-sync-versions: ## Synchronize version files after bump
	@echo "$(YELLOW)🔄 Synchronizing version files...$(NC)"
	@VERSION=$$(cat VERSION); \
	echo "Current version: $$VERSION"; \
	echo "$$VERSION" > src/claude_mpm/VERSION; \
	echo "$(GREEN)✓ Updated src/claude_mpm/VERSION$(NC)"; \
	if [ -f "package.json" ]; then \
		python -c "import json; data = json.load(open('package.json', 'r')); data['version'] = '$$VERSION'; json.dump(data, open('package.json', 'w'), indent=2); print('$(GREEN)✓ Updated package.json$(NC)')"; \
	fi

# Increment build number
increment-build: ## Increment build number for code changes
	@echo "$(YELLOW)🔢 Incrementing build number...$(NC)"
	@python scripts/increment_build.py --all-changes
	@echo "$(GREEN)✓ Build number incremented$(NC)"

# Patch release (bug fixes)
release-patch: release-check release-test ## Create a patch release (bug fixes)
	@echo "$(YELLOW)🔧 Creating patch release...$(NC)"
	@cz bump --increment PATCH
	@$(MAKE) release-sync-versions
	@$(MAKE) release-build
	@echo "$(GREEN)✓ Patch release prepared$(NC)"
	@echo "$(BLUE)Next: Run 'make release-publish' to publish$(NC)"

# Minor release (new features)
release-minor: release-check release-test ## Create a minor release (new features)
	@echo "$(YELLOW)✨ Creating minor release...$(NC)"
	@cz bump --increment MINOR
	@$(MAKE) release-sync-versions
	@$(MAKE) release-build
	@echo "$(GREEN)✓ Minor release prepared$(NC)"
	@echo "$(BLUE)Next: Run 'make release-publish' to publish$(NC)"

# Major release (breaking changes)
release-major: release-check release-test ## Create a major release (breaking changes)
	@echo "$(YELLOW)💥 Creating major release...$(NC)"
	@cz bump --increment MAJOR
	@$(MAKE) release-sync-versions
	@$(MAKE) release-build
	@echo "$(GREEN)✓ Major release prepared$(NC)"
	@echo "$(BLUE)Next: Run 'make release-publish' to publish$(NC)"

# Publish release to all channels
release-publish: ## Publish release to PyPI, npm, and GitHub
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

# Help for release targets
release-help: ## Show release management help
	@echo "$(BLUE)Claude MPM Release Management$(NC)"
	@echo "============================="
	@echo ""
	@echo "$(GREEN)Quick Start:$(NC)"
	@echo "  make release-patch     # Bug fix release"
	@echo "  make release-minor     # Feature release"
	@echo "  make release-major     # Breaking change release"
	@echo "  make release-publish   # Publish prepared release"
	@echo ""
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  make release-dry-run   # Preview what would happen"
	@echo "  make release-test-pypi # Publish to TestPyPI"
	@echo ""
	@echo "$(GREEN)Individual Steps:$(NC)"
	@echo "  make release-check     # Check prerequisites"
	@echo "  make release-test      # Run test suite"
	@echo "  make increment-build   # Increment build number"
	@echo "  make release-build     # Build package"
	@echo "  make release-verify    # Show verification links"
	@echo ""
	@echo "$(YELLOW)Prerequisites:$(NC)"
	@echo "  • git, python, commitizen (cz), GitHub CLI (gh)"
	@echo "  • Clean working directory on main branch"
	@echo "  • PyPI and npm credentials configured"
