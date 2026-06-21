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

# Shared GitHub identity enforcement (prevents pushing under the wrong account).
# shellcheck source=scripts/lib/gh_identity.sh
. "$SCRIPT_DIR/lib/gh_identity.sh"
AGENTS_REPO="$HOME/.claude-mpm/cache/agents/bobmatnyc/claude-mpm-agents"
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

    # Step 0b: Remove known cache artefacts from the working tree so that
    # git pull does not fail with "Your local changes would be overwritten".
    # This is a conservative clean: only well-known untracked cache files are
    # removed; tracked files and any other untracked files are left alone.
    # (fix #882 — skills sync used to leave .etag_cache.json in the clone tree)
    print_message "$YELLOW" "Step 0b: Removing stale cache artefacts from working tree..."
    UNTRACKED_ETAG=$(git status --porcelain 2>/dev/null | grep '^\?\?' | grep '\.etag_cache\.json' || true)
    if [ -n "$UNTRACKED_ETAG" ]; then
        print_message "$YELLOW" "  Found untracked .etag_cache.json file(s), removing..."
        # Delete every untracked .etag_cache.json file (safe: only untracked copies)
        find . -name '.etag_cache.json' -not -path './.git/*' -exec rm -f {} + 2>/dev/null || true
        print_message "$GREEN" "  ✓ Stale ETag cache artefacts removed"
    else
        print_message "$GREEN" "  ✓ No stale cache artefacts found"
    fi

    # Step 1: Stash any uncommitted changes (excludes untracked and ignored files)
    # Use git status --porcelain and filter to lines that indicate tracked changes
    # (modified, deleted, renamed, copied, added to index — but not purely untracked
    # '??' lines or ignored '!!' lines). This avoids false-positive stashes when only
    # cache files like .etag_cache.json are present as untracked files.
    print_message "$YELLOW" "Step 1: Checking for uncommitted changes..."
    TRACKED_CHANGES=$(git status --porcelain 2>/dev/null | grep -v '^??' | grep -v '^!!' || true)
    if [ -n "$TRACKED_CHANGES" ]; then
        print_message "$YELLOW" "  Found uncommitted tracked changes, stashing..."
        execute_cmd "git stash push -m 'Auto-stash before sync for v$VERSION'"
        STASHED=true
    else
        print_message "$GREEN" "  ✓ No uncommitted tracked changes"
        STASHED=false
    fi

    # Step 2: Pull and merge from remote
    print_message "$YELLOW" "Step 2: Pulling latest from remote..."

    # Check if remote branch exists
    if git ls-remote --heads origin "$CURRENT_BRANCH" | grep -q "$CURRENT_BRANCH"; then
        # Remote branch exists, pull with rebase.
        # If the pull fails due to residual untracked files (e.g. older versions
        # wrote cache files before fix #882), fall back to fetch + reset to
        # origin which is always safe for a read-only cache clone.
        if execute_cmd "git pull --rebase origin $CURRENT_BRANCH"; then
            print_message "$GREEN" "  ✓ Successfully pulled from origin/$CURRENT_BRANCH"
        else
            print_message "$YELLOW" "  ✗ Pull --rebase failed; attempting fetch + reset fallback..."
            # Fetch is already done in Step 0; just hard-reset to origin.
            # This discards any untracked artefacts that blocked the pull and
            # is safe because this clone is a read-only cache (tracked content
            # is always recoverable from origin).
            if execute_cmd "git reset --hard origin/$CURRENT_BRANCH"; then
                print_message "$GREEN" "  ✓ Recovered via fetch+reset to origin/$CURRENT_BRANCH"
            else
                print_message "$RED" "  ✗ Fetch+reset fallback also failed"
                if [ "$STASHED" = true ]; then
                    print_message "$YELLOW" "  Attempting to restore stashed changes..."
                    execute_cmd "git stash pop"
                fi
                return 1
            fi
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

🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude MPM <https://github.com/bobmatnyc/claude-mpm>"

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
            # Confirm push — honour non-interactive / automation mode
            print_message "$YELLOW" "  About to push to origin/$CURRENT_BRANCH"
            if [ "${CLAUDE_MPM_ASSUME_YES:-}" = "1" ] || [ -n "${CI:-}" ]; then
                print_message "$GREEN" "  Auto-confirming push (CLAUDE_MPM_ASSUME_YES/CI set)"
                REPLY="y"
            elif [ ! -t 0 ]; then
                print_message "$RED" "  ✗ stdin is not a TTY and CLAUDE_MPM_ASSUME_YES is not set."
                print_message "$RED" "    Re-run with: CLAUDE_MPM_ASSUME_YES=1 make release-publish"
                return 1
            else
                read -p "  Continue? [y/N]: " -n 1 -r
                echo ""
            fi

            if [[ $REPLY =~ ^[Yy]$ ]]; then
                # Push as the required account by injecting its token via a one-shot
                # GIT_ASKPASS helper (gh_git_push). The bare `origin` remote is used
                # as-is; the token is never embedded in the URL or argv, so it cannot
                # leak into the command log below, reflog, or /proc/<pid>/cmdline.
                print_message "$BLUE" "  Running: git push origin $CURRENT_BRANCH (authenticated)"
                if gh_git_push origin "$CURRENT_BRANCH"; then
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

# Preflight: refuse to run if the active GitHub identity is not the required one.
# Run this BEFORE printing any banner/headers so a wrong identity aborts cleanly
# without emitting misleading "starting sync" output, and never reaches a push.
if [ "$DRY_RUN" = false ]; then
    print_message "$YELLOW" "Verifying GitHub identity before sync..."
    if ! gh_assert_identity; then
        print_message "$RED" "✗ Aborting sync: wrong GitHub identity (see error above)."
        exit 1
    fi
    echo ""
fi

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
