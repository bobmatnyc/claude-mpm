#!/bin/bash
set -e  # Exit on error

# Script: Sync Agent and Skills Repositories
# Description: Pull, merge, commit, and push changes for agent and skills repos
# Usage: ./scripts/sync_agent_skills_repos.sh [--dry-run]

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DRY_RUN=false
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AGENTS_REPO="$HOME/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents"
SKILLS_REPO="$HOME/.claude-mpm/cache/skills/system"
VERSION=$(cat "$PROJECT_ROOT/VERSION" 2>/dev/null || echo "unknown")

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Function: Print colored message
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function: Execute or simulate command
execute_cmd() {
    local cmd=$1
    if [ "$DRY_RUN" = true ]; then
        print_message "$BLUE" "[DRY RUN] Would execute: $cmd"
        return 0
    else
        eval "$cmd"
        return $?
    fi
}

# Function: Sync a git repository
sync_repo() {
    local repo_path=$1
    local repo_name=$2

    print_message "$BLUE" "=========================================="
    print_message "$BLUE" "  Syncing: $repo_name"
    print_message "$BLUE" "=========================================="

    # Check if repo exists
    if [ ! -d "$repo_path" ]; then
        print_message "$RED" "✗ Repository not found: $repo_path"
        return 1
    fi

    # Navigate to repo
    cd "$repo_path" || {
        print_message "$RED" "✗ Failed to navigate to: $repo_path"
        return 1
    }

    # Check if it's a git repo
    if [ ! -d ".git" ]; then
        print_message "$RED" "✗ Not a git repository: $repo_path"
        return 1
    fi

    print_message "$GREEN" "✓ Found repository at: $repo_path"

    # Get current branch
    CURRENT_BRANCH=$(git branch --show-current)
    print_message "$YELLOW" "Current branch: $CURRENT_BRANCH"

    # Step 0: Fetch and prune remote references
    print_message "$YELLOW" "Step 0: Fetching and pruning remote references..."
    execute_cmd "git fetch --prune origin"
    print_message "$GREEN" "  ✓ Remote references updated"

    # Step 1: Stash any uncommitted changes
    print_message "$YELLOW" "Step 1: Checking for uncommitted changes..."
    if ! git diff-index --quiet HEAD --; then
        print_message "$YELLOW" "  Found uncommitted changes, stashing..."
        execute_cmd "git stash push -m 'Auto-stash before sync for v$VERSION'"
        STASHED=true
    else
        print_message "$GREEN" "  ✓ No uncommitted changes"
        STASHED=false
    fi

    # Step 2: Pull and merge from remote
    print_message "$YELLOW" "Step 2: Pulling latest from remote..."

    # Check if remote branch exists
    if git ls-remote --heads origin "$CURRENT_BRANCH" | grep -q "$CURRENT_BRANCH"; then
        # Remote branch exists, pull with rebase
        if execute_cmd "git pull --rebase origin $CURRENT_BRANCH"; then
            print_message "$GREEN" "  ✓ Successfully pulled from origin/$CURRENT_BRANCH"
        else
            print_message "$RED" "  ✗ Pull failed"
            if [ "$STASHED" = true ]; then
                print_message "$YELLOW" "  Attempting to restore stashed changes..."
                execute_cmd "git stash pop"
            fi
            return 1
        fi
    else
        # Remote branch doesn't exist yet - will be created on first push
        print_message "$YELLOW" "  ℹ Remote branch doesn't exist yet (will be created on push)"
        print_message "$GREEN" "  ✓ Skipping pull for new branch"
    fi

    # Step 3: Restore stashed changes if any
    if [ "$STASHED" = true ]; then
        print_message "$YELLOW" "Step 3: Restoring stashed changes..."
        if execute_cmd "git stash pop"; then
            print_message "$GREEN" "  ✓ Stashed changes restored"
        else
            print_message "$RED" "  ✗ Failed to restore stashed changes"
            print_message "$YELLOW" "  Manual intervention required: git stash list"
            return 1
        fi
    fi

    # Step 4: Check for changes to commit
    print_message "$YELLOW" "Step 4: Checking for changes to commit..."

    # Add all tracked modified files and new files (excluding .etag_cache.json)
    if [ -n "$(git status --porcelain | grep -v '.etag_cache.json')" ]; then
        print_message "$YELLOW" "  Found changes to commit"

        # Show what will be committed
        print_message "$BLUE" "  Changes to be committed:"
        git status --short | grep -v '.etag_cache.json' | head -20

        # Add all changes except .etag_cache.json files
        execute_cmd "git add -A"
        execute_cmd "git reset -- '**/.etag_cache.json'"
        execute_cmd "git reset -- '.etag_cache.json'"

        # Create commit message
        COMMIT_MSG="chore: sync $repo_name for v$VERSION release

- Synchronized changes for release v$VERSION
- Auto-committed by sync_agent_skills_repos.sh

🤖 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude <noreply@anthropic.com>"

        # Commit changes
        if execute_cmd "git commit -m \"$COMMIT_MSG\""; then
            print_message "$GREEN" "  ✓ Changes committed"
        else
            print_message "$RED" "  ✗ Commit failed"
            return 1
        fi
    else
        print_message "$GREEN" "  ✓ No changes to commit"
    fi

    # Step 5: Push to remote
    print_message "$YELLOW" "Step 5: Pushing to remote..."

    # Check if there are commits to push
    if [ -n "$(git log origin/$CURRENT_BRANCH..$CURRENT_BRANCH 2>/dev/null)" ]; then
        print_message "$YELLOW" "  Found commits to push"

        if [ "$DRY_RUN" = true ]; then
            print_message "$BLUE" "[DRY RUN] Would push to origin/$CURRENT_BRANCH"
        else
            # Confirm push
            print_message "$YELLOW" "  About to push to origin/$CURRENT_BRANCH"
            read -p "  Continue? [y/N]: " -n 1 -r
            echo ""

            if [[ $REPLY =~ ^[Yy]$ ]]; then
                if execute_cmd "git push origin $CURRENT_BRANCH"; then
                    print_message "$GREEN" "  ✓ Successfully pushed to origin/$CURRENT_BRANCH"
                else
                    print_message "$RED" "  ✗ Push failed"
                    return 1
                fi
            else
                print_message "$YELLOW" "  Push skipped by user"
                return 1
            fi
        fi
    else
        print_message "$GREEN" "  ✓ No commits to push (already up to date)"
    fi

    print_message "$GREEN" "✅ $repo_name sync complete!"
    echo ""

    return 0
}

# Main execution
print_message "$BLUE" "=========================================="
print_message "$BLUE" "  Agent & Skills Repository Sync"
print_message "$BLUE" "  Version: $VERSION"
if [ "$DRY_RUN" = true ]; then
    print_message "$YELLOW" "  Mode: DRY RUN"
fi
print_message "$BLUE" "=========================================="
echo ""

# Track success/failure
AGENTS_SUCCESS=false
SKILLS_SUCCESS=false

# Sync agents repository
if sync_repo "$AGENTS_REPO" "claude-mpm-agents"; then
    AGENTS_SUCCESS=true
else
    print_message "$RED" "⚠️  Agent repository sync failed"
fi

# Return to project root
cd "$PROJECT_ROOT" || exit 1

# Sync skills repository
if sync_repo "$SKILLS_REPO" "claude-mpm-skills"; then
    SKILLS_SUCCESS=true
else
    print_message "$RED" "⚠️  Skills repository sync failed"
fi

# Return to project root
cd "$PROJECT_ROOT" || exit 1

# Final summary
echo ""
print_message "$BLUE" "=========================================="
print_message "$BLUE" "  Sync Summary"
print_message "$BLUE" "=========================================="

if [ "$AGENTS_SUCCESS" = true ]; then
    print_message "$GREEN" "✅ Agents: Synced successfully"
else
    print_message "$RED" "❌ Agents: Sync failed"
fi

if [ "$SKILLS_SUCCESS" = true ]; then
    print_message "$GREEN" "✅ Skills: Synced successfully"
else
    print_message "$RED" "❌ Skills: Sync failed"
fi

echo ""

# Exit with appropriate code
if [ "$AGENTS_SUCCESS" = true ] && [ "$SKILLS_SUCCESS" = true ]; then
    print_message "$GREEN" "🎉 All repositories synced successfully!"
    exit 0
elif [ "$AGENTS_SUCCESS" = true ] || [ "$SKILLS_SUCCESS" = true ]; then
    print_message "$YELLOW" "⚠️  Partial sync completed (some repositories failed)"
    exit 1
else
    print_message "$RED" "❌ All repository syncs failed"
    exit 1
fi
