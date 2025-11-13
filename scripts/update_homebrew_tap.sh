#!/usr/bin/env bash
#
# Update Homebrew tap formula for new Claude MPM release
#
# Usage:
#   ./scripts/update_homebrew_tap.sh <version> [options]
#
# Options:
#   --dry-run              Test without making changes
#   --auto-push            Push changes automatically (no confirmation)
#   --skip-tests           Skip local formula tests
#   --regenerate-resources Regenerate dependency resource stanzas
#   --help                 Show this help message
#
# Examples:
#   ./scripts/update_homebrew_tap.sh 4.23.0
#   ./scripts/update_homebrew_tap.sh 4.23.0 --dry-run
#   ./scripts/update_homebrew_tap.sh 4.23.0 --auto-push --skip-tests
#
# Exit codes:
#   0 - Success
#   1 - Non-critical error (logged, but non-blocking)
#   2 - Critical error (should block release)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TAP_REPO="https://github.com/bobmatnyc/homebrew-claude-mpm.git"
TAP_DIR="/tmp/homebrew-claude-mpm-update"
PYPI_PACKAGE="claude-mpm"
FORMULA_FILE="Formula/claude-mpm.rb"
LOG_FILE="/tmp/homebrew-tap-update.log"

# Options
VERSION=""
DRY_RUN=false
AUTO_PUSH=false
SKIP_TESTS=false
REGEN_RESOURCES=false

# Functions
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case "$level" in
        INFO)
            echo -e "${BLUE}ℹ ${timestamp}${NC} ${message}" | tee -a "$LOG_FILE"
            ;;
        SUCCESS)
            echo -e "${GREEN}✅ ${timestamp}${NC} ${message}" | tee -a "$LOG_FILE"
            ;;
        WARNING)
            echo -e "${YELLOW}⚠️  ${timestamp}${NC} ${message}" | tee -a "$LOG_FILE"
            ;;
        ERROR)
            echo -e "${RED}❌ ${timestamp}${NC} ${message}" | tee -a "$LOG_FILE"
            ;;
    esac
}

show_help() {
    cat << EOF
Update Homebrew tap formula for new Claude MPM release

Usage:
  $(basename "$0") <version> [options]

Options:
  --dry-run              Test without making changes
  --auto-push            Push changes automatically (no confirmation)
  --skip-tests           Skip local formula tests
  --regenerate-resources Regenerate dependency resource stanzas
  --help                 Show this help message

Examples:
  $(basename "$0") 4.23.0
  $(basename "$0") 4.23.0 --dry-run
  $(basename "$0") 4.23.0 --auto-push --skip-tests

Exit codes:
  0 - Success
  1 - Non-critical error (logged, but non-blocking)
  2 - Critical error (should block release)

EOF
}

validate_version() {
    local version="$1"

    if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        log ERROR "Invalid version format: $version (expected: X.Y.Z)"
        return 2
    fi

    log INFO "Version format validated: $version"
    return 0
}

wait_for_pypi_package() {
    local version="$1"
    local max_attempts=10
    local attempt=1
    local wait_time=3

    log INFO "Waiting for PyPI package to be available..."

    while [ $attempt -le $max_attempts ]; do
        if curl -sf "https://pypi.org/pypi/${PYPI_PACKAGE}/${version}/json" > /dev/null 2>&1; then
            log SUCCESS "PyPI package found for version ${version}"
            return 0
        fi

        log WARNING "PyPI package not yet available (attempt ${attempt}/${max_attempts})"
        sleep $((wait_time * attempt))
        attempt=$((attempt + 1))
    done

    log ERROR "PyPI package not found after ${max_attempts} attempts"
    log ERROR "Manual fallback: Wait for PyPI to propagate, then run:"
    log ERROR "  cd homebrew-claude-mpm && ./scripts/update_formula.sh ${version}"
    return 1
}

fetch_pypi_info() {
    local version="$1"
    local pypi_url="https://pypi.org/pypi/${PYPI_PACKAGE}/${version}/json"
    local pypi_json
    local package_url
    local package_sha256

    log INFO "Fetching package information from PyPI..."

    if ! pypi_json=$(curl -sf "$pypi_url"); then
        log ERROR "Failed to fetch PyPI package info"
        return 1
    fi

    # Extract tarball URL and SHA256
    if ! package_url=$(echo "$pypi_json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for url_info in data.get('urls', []):
    if url_info.get('packagetype') == 'sdist':
        print(url_info['url'])
        sys.exit(0)
sys.exit(1)
" 2>/dev/null); then
        log ERROR "Failed to extract package URL from PyPI"
        return 1
    fi

    if ! package_sha256=$(echo "$pypi_json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for url_info in data.get('urls', []):
    if url_info.get('packagetype') == 'sdist':
        print(url_info['digests']['sha256'])
        sys.exit(0)
sys.exit(1)
" 2>/dev/null); then
        log ERROR "Failed to extract SHA256 from PyPI"
        return 1
    fi

    log SUCCESS "Package URL: ${package_url}"
    log SUCCESS "SHA256: ${package_sha256}"

    # Export for use by other functions
    export PACKAGE_URL="$package_url"
    export PACKAGE_SHA256="$package_sha256"

    return 0
}

clone_or_update_tap_repo() {
    log INFO "Setting up Homebrew tap repository..."

    if [ -d "$TAP_DIR" ]; then
        log INFO "Updating existing tap repository..."
        cd "$TAP_DIR"

        # Check for uncommitted changes
        if ! git diff --quiet; then
            log WARNING "Tap repository has uncommitted changes"
            git status --short

            if [ "$DRY_RUN" = false ]; then
                log ERROR "Cannot proceed with uncommitted changes"
                log ERROR "Manual cleanup required: cd ${TAP_DIR} && git status"
                return 1
            fi
        fi

        if ! git pull origin main; then
            log WARNING "Failed to pull latest changes, continuing with current state"
        fi
    else
        log INFO "Cloning tap repository..."
        if ! git clone "$TAP_REPO" "$TAP_DIR"; then
            log ERROR "Failed to clone tap repository"
            log ERROR "Check network connectivity and GitHub access"
            return 1
        fi
        cd "$TAP_DIR"
    fi

    log SUCCESS "Tap repository ready at: ${TAP_DIR}"
    return 0
}

update_formula() {
    local version="$1"
    local formula_path="${TAP_DIR}/${FORMULA_FILE}"

    log INFO "Updating formula file..."

    if [ ! -f "$formula_path" ]; then
        log ERROR "Formula file not found: ${formula_path}"
        return 2
    fi

    # Backup current formula
    local backup_file="${formula_path}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$formula_path" "$backup_file"
    log INFO "Created backup: ${backup_file}"

    if [ "$DRY_RUN" = true ]; then
        log INFO "[DRY RUN] Would update formula with:"
        log INFO "  Version: ${version}"
        log INFO "  URL: ${PACKAGE_URL}"
        log INFO "  SHA256: ${PACKAGE_SHA256}"
        return 0
    fi

    # Update URL
    if ! sed -i.bak "s|url \".*\"|url \"${PACKAGE_URL}\"|" "$formula_path"; then
        log ERROR "Failed to update formula URL"
        mv "$backup_file" "$formula_path"
        return 1
    fi

    # Update SHA256
    if ! sed -i.bak "s|sha256 \".*\"|sha256 \"${PACKAGE_SHA256}\"|" "$formula_path"; then
        log ERROR "Failed to update formula SHA256"
        mv "$backup_file" "$formula_path"
        return 1
    fi

    # Clean up sed backup files
    rm -f "${formula_path}.bak"

    log SUCCESS "Formula updated successfully"

    # Show diff
    if git diff --quiet "$formula_path"; then
        log WARNING "No changes detected in formula (already up to date?)"
    else
        log INFO "Formula changes:"
        git diff "$formula_path" | tee -a "$LOG_FILE"
    fi

    return 0
}

regenerate_resources() {
    local version="$1"
    local formula_path="${TAP_DIR}/${FORMULA_FILE}"
    local resources_script="${TAP_DIR}/scripts/generate_resources.py"

    log INFO "Regenerating dependency resources..."

    if [ ! -f "$resources_script" ]; then
        log WARNING "Resource generation script not found, skipping"
        return 0
    fi

    if [ "$DRY_RUN" = true ]; then
        log INFO "[DRY RUN] Would regenerate resources for version ${version}"
        return 0
    fi

    # This is a placeholder for resource regeneration
    # The actual implementation would need to:
    # 1. Run generate_resources.py with the new version
    # 2. Compare output with current resources
    # 3. Update formula if resources changed

    log WARNING "Resource regeneration not fully implemented yet"
    log INFO "Manual resource update may be required if dependencies changed"

    return 0
}

test_formula() {
    local formula_path="${TAP_DIR}/${FORMULA_FILE}"

    if [ "$SKIP_TESTS" = true ]; then
        log INFO "Skipping formula tests (--skip-tests specified)"
        return 0
    fi

    log INFO "Testing formula..."

    # Syntax check
    log INFO "Running Ruby syntax check..."
    if ! ruby -c "$formula_path" > /dev/null 2>&1; then
        log ERROR "Formula syntax check failed"
        return 1
    fi
    log SUCCESS "Ruby syntax check passed"

    # Homebrew audit (if brew is available)
    if command -v brew > /dev/null 2>&1; then
        log INFO "Running Homebrew audit..."
        if brew audit --strict "$formula_path" 2>&1 | tee -a "$LOG_FILE"; then
            log SUCCESS "Homebrew audit passed"
        else
            log WARNING "Homebrew audit reported warnings (non-blocking)"
        fi
    else
        log INFO "Homebrew not installed, skipping brew audit"
    fi

    return 0
}

commit_changes() {
    local version="$1"

    cd "$TAP_DIR"

    if git diff --quiet; then
        log WARNING "No changes to commit"
        return 0
    fi

    if [ "$DRY_RUN" = true ]; then
        log INFO "[DRY RUN] Would commit changes with message:"
        log INFO "  feat: update to v${version}"
        return 0
    fi

    log INFO "Committing changes..."

    git add "$FORMULA_FILE"

    # Create commit with Claude MPM branding
    git commit -m "feat: update to v${version}

🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude <noreply@anthropic.com>"

    local commit_sha
    commit_sha=$(git rev-parse HEAD)
    log SUCCESS "Changes committed: ${commit_sha}"

    return 0
}

push_changes() {
    local version="$1"

    cd "$TAP_DIR"

    if [ "$DRY_RUN" = true ]; then
        log INFO "[DRY RUN] Would push changes to GitHub and create tag v${version}"
        return 0
    fi

    # Push confirmation (unless auto-push is enabled)
    if [ "$AUTO_PUSH" = false ]; then
        echo ""
        echo -e "${YELLOW}Ready to push changes to GitHub${NC}"
        echo "Repository: homebrew-claude-mpm"
        echo "Version: v${version}"
        echo ""
        read -p "Push changes? [y/N]: " -n 1 -r
        echo ""

        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log WARNING "Push cancelled by user"
            log INFO "To push manually:"
            log INFO "  cd ${TAP_DIR}"
            log INFO "  git push origin main"
            log INFO "  git tag v${version}"
            log INFO "  git push origin v${version}"
            return 0
        fi
    fi

    log INFO "Pushing changes to GitHub..."

    # Push commits
    if ! git push origin main; then
        log ERROR "Failed to push to GitHub"
        log ERROR "Manual push required: cd ${TAP_DIR} && git push origin main"
        return 1
    fi
    log SUCCESS "Changes pushed to GitHub"

    # Create and push tag
    log INFO "Creating tag v${version}..."
    if git tag -a "v${version}" -m "Release v${version}"; then
        if git push origin "v${version}"; then
            log SUCCESS "Tag v${version} created and pushed"
        else
            log WARNING "Failed to push tag (non-critical)"
        fi
    else
        log WARNING "Tag v${version} may already exist (non-critical)"
    fi

    return 0
}

cleanup() {
    log INFO "Cleanup complete"
}

# Parse arguments
if [ $# -eq 0 ]; then
    show_help
    exit 1
fi

# Check for help flag first
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
    exit 0
fi

VERSION="$1"
shift

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            ;;
        --auto-push)
            AUTO_PUSH=true
            ;;
        --skip-tests)
            SKIP_TESTS=true
            ;;
        --regenerate-resources)
            REGEN_RESOURCES=true
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            log ERROR "Unknown option: $1"
            show_help
            exit 2
            ;;
    esac
    shift
done

# Main execution
main() {
    local exit_code=0

    # Initialize log file
    echo "=== Homebrew Tap Update Log ===" > "$LOG_FILE"
    echo "Timestamp: $(date)" >> "$LOG_FILE"
    echo "Version: ${VERSION}" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"

    log INFO "Starting Homebrew tap update for version ${VERSION}"

    if [ "$DRY_RUN" = true ]; then
        log INFO "DRY RUN MODE - No changes will be made"
    fi

    # Step 1: Validate version format
    if ! validate_version "$VERSION"; then
        exit_code=$?
        log ERROR "Version validation failed"
        return $exit_code
    fi

    # Step 2: Wait for PyPI package
    if ! wait_for_pypi_package "$VERSION"; then
        log ERROR "PyPI package not available"
        log ERROR "This is non-blocking. Manual fallback instructions above."
        return 1
    fi

    # Step 3: Fetch PyPI package info
    if ! fetch_pypi_info "$VERSION"; then
        log ERROR "Failed to fetch PyPI package information"
        return 1
    fi

    # Step 4: Clone or update tap repository
    if ! clone_or_update_tap_repo; then
        log ERROR "Failed to set up tap repository"
        return 1
    fi

    # Step 5: Update formula
    if ! update_formula "$VERSION"; then
        exit_code=$?
        log ERROR "Failed to update formula"
        return $exit_code
    fi

    # Step 6: Regenerate resources (if requested)
    if [ "$REGEN_RESOURCES" = true ]; then
        if ! regenerate_resources "$VERSION"; then
            log WARNING "Resource regeneration failed (non-critical)"
        fi
    fi

    # Step 7: Test formula
    if ! test_formula; then
        log WARNING "Formula tests failed (non-blocking)"
    fi

    # Step 8: Commit changes
    if ! commit_changes "$VERSION"; then
        log ERROR "Failed to commit changes"
        return 1
    fi

    # Step 9: Push changes
    if ! push_changes "$VERSION"; then
        log WARNING "Failed to push changes (non-blocking)"
        log WARNING "Changes are committed locally at: ${TAP_DIR}"
        return 1
    fi

    # Success!
    log SUCCESS "✅ Homebrew tap update completed successfully"
    log INFO "Formula updated to version ${VERSION}"
    log INFO "Verification:"
    log INFO "  brew tap bobmatnyc/claude-mpm"
    log INFO "  brew upgrade claude-mpm"
    log INFO "  claude-mpm --version"
    log INFO ""
    log INFO "Log file: ${LOG_FILE}"

    return 0
}

# Run main function
trap cleanup EXIT
main
exit $?
