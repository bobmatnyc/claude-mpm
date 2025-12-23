#!/usr/bin/env bash
set -e

# Script to sync agent files from claude-mpm to bobmatnyc/claude-mpm-agents
#
# Usage:
#   ./scripts/push_to_agents_repo.sh [version] [options]
#
# Options:
#   --dry-run          Preview changes without committing or pushing
#   --yes, -y          Skip confirmation prompt (auto-confirm)
#   --repo-path PATH   Use existing local clone instead of temp clone
#
# Examples:
#   ./scripts/push_to_agents_repo.sh --dry-run
#   ./scripts/push_to_agents_repo.sh --yes
#   ./scripts/push_to_agents_repo.sh 5.4.23 --dry-run
#
# See: scripts/README-push-to-agents-repo.md for full documentation

AGENTS_REPO_URL="https://github.com/bobmatnyc/claude-mpm-agents.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
DRY_RUN=false
AUTO_YES=false
VERSION=""
AGENTS_REPO_PATH=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --yes|-y)
            AUTO_YES=true
            shift
            ;;
        --repo-path)
            AGENTS_REPO_PATH="$2"
            shift 2
            ;;
        *)
            if [[ -z "$VERSION" ]]; then
                VERSION="$1"
            fi
            shift
            ;;
    esac
done

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to extract version from pyproject.toml
get_version_from_pyproject() {
    if [[ -f "$PROJECT_ROOT/pyproject.toml" ]]; then
        version=$(grep -E '^version = ' "$PROJECT_ROOT/pyproject.toml" | head -1 | sed -E 's/version = "(.*)"/\1/')
        echo "$version"
    else
        print_error "pyproject.toml not found"
        exit 1
    fi
}

# Get version
if [[ -z "$VERSION" ]]; then
    VERSION=$(get_version_from_pyproject)
    print_info "Using version from pyproject.toml: $VERSION"
else
    print_info "Using provided version: $VERSION"
fi

# Validate version format
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    print_error "Invalid version format: $VERSION (expected: X.Y.Z)"
    exit 1
fi

# Define file mappings as parallel arrays (compatible with bash 3.2)
SOURCE_FILES=(
    "src/claude_mpm/agents/BASE_AGENT.md"
    "src/claude_mpm/agents/PM_INSTRUCTIONS.md"
    "src/claude_mpm/agents/BASE_ENGINEER.md"
    "src/claude_mpm/agents/CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md"
)

DEST_FILES=(
    "agents/BASE-AGENT.md"
    "templates/PM-INSTRUCTIONS.md"
    "templates/BASE-ENGINEER.md"
    "templates/CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md"
)

# Verify source files exist
print_info "Verifying source files..."
for src_file in "${SOURCE_FILES[@]}"; do
    if [[ ! -f "$PROJECT_ROOT/$src_file" ]]; then
        print_error "Source file not found: $src_file"
        exit 1
    fi
    print_success "Found: $src_file"
done

# Setup temporary directory for agents repo
if [[ -z "$AGENTS_REPO_PATH" ]]; then
    TEMP_DIR=$(mktemp -d)
    AGENTS_REPO_PATH="$TEMP_DIR/claude-mpm-agents"
    CLEANUP_TEMP=true

    print_info "Cloning agents repository to temporary location..."
    git clone "$AGENTS_REPO_URL" "$AGENTS_REPO_PATH" 2>&1 | grep -v "Cloning into" || true
    print_success "Repository cloned to: $AGENTS_REPO_PATH"
else
    CLEANUP_TEMP=false
    print_info "Using existing repository at: $AGENTS_REPO_PATH"

    # Verify it's a git repo
    if [[ ! -d "$AGENTS_REPO_PATH/.git" ]]; then
        print_error "Not a git repository: $AGENTS_REPO_PATH"
        exit 1
    fi

    # Pull latest changes
    print_info "Pulling latest changes..."
    cd "$AGENTS_REPO_PATH"
    git pull
    cd "$PROJECT_ROOT"
fi

# Cleanup function
cleanup() {
    if [[ "$CLEANUP_TEMP" == true && -d "$TEMP_DIR" ]]; then
        print_info "Cleaning up temporary directory..."
        rm -rf "$TEMP_DIR"
    fi
}

# Register cleanup on exit
trap cleanup EXIT

# Create destination directories if they don't exist
print_info "Creating destination directories..."
mkdir -p "$AGENTS_REPO_PATH/agents"
mkdir -p "$AGENTS_REPO_PATH/templates"

# Copy files and track changes
print_info "Copying files..."
HAS_CHANGES=false

# Loop through parallel arrays
for i in "${!SOURCE_FILES[@]}"; do
    src_file="${SOURCE_FILES[$i]}"
    dest_file="${DEST_FILES[$i]}"
    src_path="$PROJECT_ROOT/$src_file"
    dest_path="$AGENTS_REPO_PATH/$dest_file"

    print_info "Copying: $src_file -> $dest_file"

    # Check if destination exists and if content differs
    if [[ -f "$dest_path" ]]; then
        if ! diff -q "$src_path" "$dest_path" > /dev/null 2>&1; then
            HAS_CHANGES=true
            print_warning "File differs: $dest_file"
        fi
    else
        HAS_CHANGES=true
        print_warning "New file: $dest_file"
    fi

    # Copy the file
    cp "$src_path" "$dest_path"
done

print_success "All files copied"

# Change to agents repo directory
cd "$AGENTS_REPO_PATH"

# Check for changes
if ! git diff --quiet || ! git diff --cached --quiet || [[ -n $(git ls-files --others --exclude-standard) ]]; then
    HAS_CHANGES=true
fi

if [[ "$HAS_CHANGES" == false ]]; then
    print_info "No changes detected. Nothing to commit."
    exit 0
fi

# Show diff
print_info "Changes to be committed:"
echo ""
git diff --color=always
echo ""

# Show status
print_info "Git status:"
git status --short
echo ""

# Dry run check
if [[ "$DRY_RUN" == true ]]; then
    print_warning "DRY RUN MODE - No changes will be committed or pushed"
    exit 0
fi

# Confirm before committing
if [[ "$AUTO_YES" != true ]]; then
    echo -e "${YELLOW}Commit and push these changes for version $VERSION?${NC}"
    read -p "Continue? (y/N): " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Aborted by user"
        exit 0
    fi
else
    print_info "Auto-confirming due to --yes flag"
fi

# Stage all changes
print_info "Staging changes..."
git add agents/ templates/

# Commit changes
COMMIT_MSG="Sync agent files from claude-mpm v$VERSION

Updated files:
$(for dest in "${DEST_FILES[@]}"; do echo "- $dest"; done)

Source: https://github.com/bobmatnyc/claude-mpm/releases/tag/v$VERSION"

print_info "Committing changes..."
git commit -m "$COMMIT_MSG"

# Push changes
print_info "Pushing to remote..."
git push origin main

print_success "Successfully synced files to agents repository!"
print_info "Commit message:"
echo ""
echo "$COMMIT_MSG"
echo ""

# Return to original directory
cd "$PROJECT_ROOT"
