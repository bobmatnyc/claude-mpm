#!/bin/bash

# Claude MPM Release Workflow Script
# This script demonstrates the release workflow with changelog management

set -e

echo "Claude MPM Release Workflow"
echo "============================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the project root
if [ ! -f "pyproject.toml" ] || [ ! -f "VERSION" ]; then
    print_error "This script must be run from the project root"
    exit 1
fi

# Parse command line arguments
COMMAND=${1:-help}

case $COMMAND in
    check)
        print_info "Checking release readiness..."
        
        # Run structure linter to check changelog and versions
        print_info "Running structure linter..."
        python tools/dev/structure_linter.py --verbose
        
        # Check for uncommitted changes
        if [ -n "$(git status --porcelain)" ]; then
            print_warning "You have uncommitted changes"
            git status --short
        else
            print_info "Working directory is clean"
        fi
        
        # Check current version
        CURRENT_VERSION=$(cat VERSION)
        print_info "Current version: $CURRENT_VERSION"
        
        # Check if version exists as a tag
        if git rev-parse "v$CURRENT_VERSION" >/dev/null 2>&1; then
            print_warning "Version v$CURRENT_VERSION already exists as a tag"
        else
            print_info "Version v$CURRENT_VERSION is not yet tagged"
        fi
        
        # Check changelog for unreleased content
        if grep -q "^## \[Unreleased\]" CHANGELOG.md; then
            print_info "CHANGELOG.md has [Unreleased] section"
            
            # Check if there's actual content in unreleased (look for list items with -)
            UNRELEASED_CONTENT=$(awk '/^## \[Unreleased\]/,/^## \[4|3|2|1|0-9]/{if(/^- /) count++} END {print count+0}' CHANGELOG.md)
            if [ "$UNRELEASED_CONTENT" -gt 0 ]; then
                print_info "Found $UNRELEASED_CONTENT items in [Unreleased] section"
            else
                print_warning "[Unreleased] section appears to be empty"
            fi
        else
            print_error "CHANGELOG.md is missing [Unreleased] section"
        fi
        ;;
        
    prepare)
        VERSION_TYPE=${2:-patch}
        print_info "Preparing release (version bump: $VERSION_TYPE)..."
        
        # Check for commitizen
        if ! command -v cz &> /dev/null; then
            print_error "Commitizen is not installed. Install with: pip install commitizen"
            exit 1
        fi
        
        print_info "Running commitizen bump..."
        echo "This will:"
        echo "  1. Bump version according to conventional commits"
        echo "  2. Update VERSION file"
        echo "  3. Update package.json"
        echo "  4. Update CHANGELOG.md"
        echo "  5. Create a commit and tag"
        echo ""
        read -p "Continue? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cz bump --$VERSION_TYPE
        else
            print_info "Release preparation cancelled"
        fi
        ;;
        
    changelog)
        print_info "Viewing current changelog entries..."
        echo ""
        echo "=== [Unreleased] Section ==="
        # Extract the Unreleased section content
        awk '/^## \[Unreleased\]/,/^## \[[0-9]/{if(/^## \[[0-9]/) exit; print}' CHANGELOG.md
        echo ""
        echo "=== Latest Release ==="
        # Get the first numbered version section
        awk '/^## \[[0-9]/,/^## \[[0-9]/{if(NR>1 && /^## \[[0-9]/) exit; if(/^## \[[0-9]/ || NF>0) print}' CHANGELOG.md | head -n 30
        ;;
        
    validate)
        print_info "Validating conventional commits..."
        
        # Get commits since last tag
        LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
        if [ -z "$LAST_TAG" ]; then
            print_warning "No tags found, checking last 10 commits"
            COMMITS=$(git log --oneline -10)
        else
            print_info "Checking commits since $LAST_TAG"
            COMMITS=$(git log --oneline $LAST_TAG..HEAD)
        fi
        
        echo "$COMMITS" | while read -r commit; do
            # Check if commit follows conventional format
            if echo "$commit" | grep -qE '^[a-f0-9]+ (feat|fix|docs|style|refactor|perf|test|chore|build|ci)(\(.+\))?: .+'; then
                echo -e "${GREEN}✓${NC} $commit"
            elif echo "$commit" | grep -qE '^[a-f0-9]+ (BREAKING CHANGE|feat!|fix!): .+'; then
                echo -e "${GREEN}✓${NC} $commit (BREAKING CHANGE)"
            else
                echo -e "${YELLOW}✗${NC} $commit (not conventional)"
            fi
        done
        ;;
        
    help|*)
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  check      - Check if the project is ready for release"
        echo "  prepare    - Prepare a new release (bump version, update changelog)"
        echo "  changelog  - View current changelog entries"
        echo "  validate   - Validate commit messages follow conventional format"
        echo "  help       - Show this help message"
        echo ""
        echo "Release Workflow:"
        echo "  1. Make changes and commit with conventional messages"
        echo "  2. Run '$0 check' to verify readiness"
        echo "  3. Run '$0 prepare [patch|minor|major]' to create release"
        echo "  4. Push changes and tags: git push && git push --tags"
        echo "  5. GitHub Actions will automatically create the release"
        ;;
esac