# Claude MPM Installation Makefile
# =================================
# Automates the installation and setup of claude-mpm
#
# Quick start:
#   make help     - Show this help
#   make install  - Install claude-mpm globally
#   make setup    - Complete setup (install + shell config)

.PHONY: help install install-pipx install-global install-local setup-shell uninstall update clean check-pipx detect-shell backup-shell test-installation all

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

# Quick targets
quick: setup ## Alias for complete setup
quick-dev: setup-dev ## Alias for complete development setup