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

# Shared GitHub identity enforcement (prevents pushing under the wrong account).
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/lib/gh_identity.sh
. "$SCRIPT_DIR/lib/gh_identity.sh"

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

# Extract the sdist URL + sha256 from a PyPI version-JSON payload, in a single
# JSON parse, emitting "<url>\t<sha256>" on stdout.
#
# Why: PyPI's `<pkg>/<version>/json` endpoint becomes resolvable (HTTP 200) as
# soon as the FIRST distribution file is published. During CI release the wheels
# are uploaded before the sdist (observed ~8s gap for v6.5.16), so a naive
# "version exists" gate races ahead of the sdist and the extraction finds only
# `bdist_wheel` entries in urls[] — the historical "Failed to extract package
# URL" failure. Distinguishing "no sdist yet" (exit 3, retryable) from malformed
# JSON (exit 1) lets the caller poll instead of hard-failing.
# What: Parses stdin JSON; prints "url<TAB>sha256" for the sole sdist entry.
# Exit: 0 found; 3 valid JSON but no sdist present yet (retryable); 1 parse error.
# Test: Pipe v6.5.16 JSON -> prints the .tar.gz url + 64-char sha256, exit 0;
#       pipe wheels-only JSON -> exit 3; pipe "{}" -> exit 3; pipe "x" -> exit 1.
extract_sdist_info() {
    python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(1)  # malformed/empty response — not a "missing sdist" condition
for u in data.get("urls", []):
    if u.get("packagetype") == "sdist":
        try:
            print("%s\t%s" % (u["url"], u["digests"]["sha256"]))
        except (KeyError, TypeError):
            sys.exit(1)
        sys.exit(0)
sys.exit(3)  # JSON parsed but the sdist is not indexed yet — retryable
'
}

# Poll PyPI until the sdist (not just any file) for $version is available, then
# capture its URL + sha256 into PACKAGE_URL / PACKAGE_SHA256.
#
# Why: Replaces the old two-step "wait for HTTP 200, then immediately extract"
# flow that raced the wheel-before-sdist publish order (issue #652). Gating on
# the sdist's presence — with a bounded retry — is the actual readiness signal
# the formula update needs, and folding extraction into the same loop removes
# the second, unguarded query that produced "Failed to extract package URL".
# What: Retries with linear backoff; on success exports PACKAGE_URL/SHA256.
# Test: Run against an existing version -> exports a *.tar.gz url + sha256;
#       run against a never-published version -> fails after max_attempts with
#       an endpoint-qualified error and a copy-pasteable manual fallback.
fetch_pypi_info() {
    local version="$1"
    local pypi_url="https://pypi.org/pypi/${PYPI_PACKAGE}/${version}/json"
    # CI builds + publishes the sdist after the wheels, so allow a generous,
    # bounded window. Linear backoff: cumulative wait ~ 3*(1+2+...+20) ≈ 10 min.
    local max_attempts=20
    local attempt=1
    local wait_time=3
    local pypi_json result rc

    log INFO "Waiting for PyPI sdist to be available for ${version}..."
    log INFO "  Endpoint: ${pypi_url}"

    while [ "$attempt" -le "$max_attempts" ]; do
        if pypi_json=$(curl -sf "$pypi_url" 2>/dev/null); then
            # Capture stdout and exit code without tripping `set -e`.
            result=$(printf '%s' "$pypi_json" | extract_sdist_info) && rc=0 || rc=$?

            if [ "$rc" -eq 0 ]; then
                PACKAGE_URL="${result%%$'\t'*}"
                PACKAGE_SHA256="${result##*$'\t'}"
                export PACKAGE_URL PACKAGE_SHA256
                log SUCCESS "Package URL: ${PACKAGE_URL}"
                log SUCCESS "SHA256: ${PACKAGE_SHA256}"
                return 0
            elif [ "$rc" -eq 3 ]; then
                log WARNING "sdist not yet indexed for ${version} (attempt ${attempt}/${max_attempts}); wheels may have published first"
            else
                log WARNING "Unexpected PyPI JSON response for ${version} (attempt ${attempt}/${max_attempts})"
            fi
        else
            log WARNING "PyPI version JSON not yet available for ${version} (attempt ${attempt}/${max_attempts})"
        fi

        sleep $((wait_time * attempt))
        attempt=$((attempt + 1))
    done

    log ERROR "No sdist found for ${PYPI_PACKAGE} ${version} after ${max_attempts} attempts."
    log ERROR "  Queried: ${pypi_url}"
    log ERROR "  The sdist is likely still building/publishing in CI (release-wheels.yml)."
    log ERROR "  Once available, re-run the tap update manually:"
    log ERROR "    ./scripts/update_homebrew_tap.sh ${version} --auto-push"
    return 1
}

clone_or_update_tap_repo() {
    log INFO "Setting up Homebrew tap repository..."

    # clone/pull/push run through gh_git, which injects the required account's
    # token via a one-shot GIT_ASKPASS helper at runtime. Clone uses the bare
    # $TAP_REPO URL (no embedded token), which sets `origin`; subsequent pull/push
    # use the `origin` remote so the tracking branch updates. The token never
    # appears in argv, `git remote -v`, reflog, or any log.

    if [ -d "$TAP_DIR" ]; then
        log INFO "Updating existing tap repository..."
        cd "$TAP_DIR"

        # Check if git repository is valid
        if ! git rev-parse --git-dir > /dev/null 2>&1; then
            log WARNING "Found corrupt git repository at ${TAP_DIR}"
            log INFO "Removing corrupt directory and re-cloning..."
            cd /
            rm -rf "$TAP_DIR"

            # Clone fresh repository
            log INFO "Cloning tap repository..."
            if ! gh_git clone "$TAP_REPO" "$TAP_DIR"; then
                log ERROR "Failed to clone tap repository"
                log ERROR "Check network connectivity and GitHub access"
                return 1
            fi
            cd "$TAP_DIR"
            log SUCCESS "Tap repository ready at: ${TAP_DIR}"
            return 0
        fi

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

        # Pull via the `origin` remote (set by clone) so the tracking branch is
        # updated and GIT_ASKPASS supplies credentials against origin's URL.
        if ! gh_git pull origin main; then
            log WARNING "Failed to pull latest changes, continuing with current state"
        fi
    else
        log INFO "Cloning tap repository..."
        if ! gh_git clone "$TAP_REPO" "$TAP_DIR"; then
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

    # Update URL — anchor to exactly 2 leading spaces so we only match the top-level
    # formula `url` field, NOT the `url` lines inside `resource` stanzas (4 spaces).
    if ! sed -i.bak "s|^  url \".*\"|  url \"${PACKAGE_URL}\"|" "$formula_path"; then
        log ERROR "Failed to update formula URL"
        mv "$backup_file" "$formula_path"
        return 1
    fi

    # Update SHA256 — same anchoring: match only the top-level sha256 (2 spaces indent),
    # not sha256 lines inside resource blocks (4 spaces indent).
    if ! sed -i.bak "s|^  sha256 \".*\"|  sha256 \"${PACKAGE_SHA256}\"|" "$formula_path"; then
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

Co-Authored-By: Claude MPM <https://github.com/bobmatnyc/claude-mpm>"

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

    # Pushes go through gh_git, which authenticates as the required account by
    # injecting its token via a one-shot GIT_ASKPASS helper. We push to the
    # `origin` remote (set at clone time); the token never lands in argv,
    # reflog, or logs.

    # Push confirmation (unless auto-push is enabled)
    if [ "$AUTO_PUSH" = false ]; then
        echo ""
        echo -e "${YELLOW}Ready to push changes to GitHub${NC}"
        echo "Repository: homebrew-tools"
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

    # Push commits via the `origin` remote (consistent with the pull above and the
    # manual-fallback hints), so GIT_ASKPASS authenticates against origin's URL.
    if ! gh_git push origin main; then
        log ERROR "Failed to push to GitHub"
        log ERROR "Manual push required: cd ${TAP_DIR} && git push origin main"
        return 1
    fi
    log SUCCESS "Changes pushed to GitHub"

    # Create and push tag
    log INFO "Creating tag v${version}..."
    if git tag -a "v${version}" -m "Release v${version}"; then
        if gh_git push origin "v${version}"; then
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

    # Step 0: Verify GitHub identity before any push-capable work.
    # Aborts loudly if the active identity is not the required account, so a
    # release never pushes the tap under the wrong (e.g. bob-duetto) credential.
    if [ "$DRY_RUN" = false ]; then
        if ! gh_assert_identity; then
            log ERROR "Aborting Homebrew tap update: wrong GitHub identity (see error above)."
            return 2
        fi
    fi

    # Step 1: Validate version format
    if ! validate_version "$VERSION"; then
        exit_code=$?
        log ERROR "Version validation failed"
        return $exit_code
    fi

    # Step 2: Wait for the PyPI sdist, then capture its URL + SHA256.
    # The readiness poll and extraction are now a single sdist-aware loop
    # (issue #652), so this no longer races the wheel-before-sdist publish order.
    if ! fetch_pypi_info "$VERSION"; then
        log ERROR "Failed to fetch PyPI sdist information"
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
    log INFO "  brew tap bobmatnyc/tools"
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
