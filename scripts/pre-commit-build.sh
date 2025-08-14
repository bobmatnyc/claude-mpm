#!/bin/bash
#
# Git pre-commit hook for claude-mpm build tracking
#
# WHY: Automatically increment build numbers when code changes are committed.
# This ensures every code change gets a unique build number for tracking.
#
# DESIGN DECISION: Only increments for actual code changes (Python files in src/,
# shell scripts in scripts/), not for documentation or configuration changes.
# This prevents build number inflation from non-code commits.
#
# Installation:
#   cp scripts/pre-commit-build.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
#
# Or use the install script:
#   ./scripts/install_git_hook.sh

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Determine project root (parent of .git directory)
if [ -d "$SCRIPT_DIR/../../.git" ]; then
    # Hook is in .git/hooks/
    PROJECT_ROOT="$SCRIPT_DIR/../.."
elif [ -d "$SCRIPT_DIR/../.git" ]; then
    # Script is in scripts/ directory (for testing)
    PROJECT_ROOT="$SCRIPT_DIR/.."
else
    echo "Error: Could not determine project root" >&2
    exit 1
fi

# Change to project root
cd "$PROJECT_ROOT" || exit 1

# Check if increment_build.py exists
INCREMENT_SCRIPT="scripts/increment_build.py"
if [ ! -f "$INCREMENT_SCRIPT" ]; then
    echo "Warning: Build increment script not found at $INCREMENT_SCRIPT" >&2
    echo "Continuing with commit..." >&2
    exit 0
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Warning: python3 not found, cannot increment build number" >&2
    echo "Continuing with commit..." >&2
    exit 0
fi

# Check if there are code changes that require a build increment
echo "Checking for code changes..."
if python3 "$INCREMENT_SCRIPT" --check-only --staged-only; then
    # Code changes detected, increment the build number
    echo "Code changes detected, incrementing build number..."
    python3 "$INCREMENT_SCRIPT" --staged-only
    
    # Add the BUILDVERSION file to the commit if it was updated
    if [ -f "BUILDVERSION" ]; then
        git add BUILDVERSION
        echo "BUILDVERSION file added to commit"
    fi
else
    # No code changes, no need to increment
    echo "No code changes detected, build number unchanged"
fi

# Continue with the commit
exit 0