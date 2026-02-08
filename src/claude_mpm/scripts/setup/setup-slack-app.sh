#!/bin/bash
#
# setup-slack-app.sh - Interactive setup script for Slack integration
#
# This script helps configure the Slack bot for Claude MPM by:
# - Checking dependencies
# - Collecting and validating Slack tokens
# - Saving configuration
# - Testing the connection
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default env file
ENV_FILE="${PROJECT_ROOT}/.env.local"

usage() {
    cat << USAGE
Usage: $(basename "$0") [OPTIONS]

Interactive setup script for Claude MPM Slack integration.

OPTIONS:
    -h, --help          Show this help message
    -f, --file FILE     Specify custom .env file (default: .env.local)
    -e, --export        Export tokens to current shell instead of saving to file
    -t, --test-only     Only test existing connection (skip setup)
    -q, --quiet         Minimal output

DESCRIPTION:
    This script guides you through setting up the Slack integration for
    Claude MPM. It will:

    1. Check for the slack-bolt Python dependency
    2. Prompt for your Slack Bot Token (xoxb-...)
    3. Prompt for your Slack App Token (xapp-...)
    4. Validate both tokens have correct prefixes
    5. Save tokens to .env.local (or export to shell)
    6. Test the connection with a simple Slack API call

EXAMPLES:
    # Interactive setup with defaults
    ./setup-slack-app.sh

    # Save to custom env file
    ./setup-slack-app.sh -f .env.slack

    # Export to current shell
    ./setup-slack-app.sh --export

    # Test existing configuration
    ./setup-slack-app.sh --test-only

PREREQUISITES:
    - Python 3.8+
    - slack-bolt package (pip install slack-bolt)
    - Slack app created at api.slack.com with Socket Mode enabled

For detailed setup instructions, see: docs/SLACK_SETUP.md

USAGE
    exit 0
}

log_info() {
    if [[ "$QUIET" != "true" ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

log_success() {
    if [[ "$QUIET" != "true" ]]; then
        echo -e "${GREEN}[OK]${NC} $1"
    fi
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    log_info "Checking dependencies..."

    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi
    log_success "Python 3 found: $(python3 --version)"

    # Check slack-bolt
    if python3 -c "import slack_bolt" 2>/dev/null; then
        log_success "slack-bolt package is installed"
    else
        log_warn "slack-bolt package is not installed"
        echo ""
        read -p "Would you like to install slack-bolt now? [y/N] " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Installing slack-bolt..."
            pip install slack-bolt
            log_success "slack-bolt installed successfully"
        else
            log_error "slack-bolt is required. Install with: pip install slack-bolt"
            exit 1
        fi
    fi

    # Check curl for API testing
    if ! command -v curl &> /dev/null; then
        log_warn "curl not found - connection test will be skipped"
        return 1
    fi

    return 0
}

validate_bot_token() {
    local token="$1"
    if [[ ! "$token" =~ ^xoxb- ]]; then
        log_error "Invalid Bot Token format. Must start with 'xoxb-'"
        return 1
    fi
    if [[ ${#token} -lt 50 ]]; then
        log_warn "Bot Token seems too short. Please verify it's complete."
    fi
    return 0
}

validate_app_token() {
    local token="$1"
    if [[ ! "$token" =~ ^xapp- ]]; then
        log_error "Invalid App Token format. Must start with 'xapp-'"
        return 1
    fi
    if [[ ${#token} -lt 50 ]]; then
        log_warn "App Token seems too short. Please verify it's complete."
    fi
    return 0
}

prompt_for_tokens() {
    echo ""
    echo -e "${BLUE}=== Slack Token Configuration ===${NC}"
    echo ""
    echo "You'll need two tokens from your Slack app:"
    echo "  1. Bot Token (xoxb-...) - OAuth & Permissions > Bot User OAuth Token"
    echo "  2. App Token (xapp-...) - Basic Information > App-Level Tokens"
    echo ""
    echo "For detailed instructions, see: docs/SLACK_SETUP.md"
    echo ""

    # Prompt for Bot Token
    while true; do
        read -p "Enter your Slack Bot Token (xoxb-...): " -r SLACK_BOT_TOKEN
        if validate_bot_token "$SLACK_BOT_TOKEN"; then
            log_success "Bot Token format validated"
            break
        fi
        echo "Please try again."
    done

    echo ""

    # Prompt for App Token
    while true; do
        read -p "Enter your Slack App Token (xapp-...): " -r SLACK_APP_TOKEN
        if validate_app_token "$SLACK_APP_TOKEN"; then
            log_success "App Token format validated"
            break
        fi
        echo "Please try again."
    done

    echo ""
}

save_to_env_file() {
    log_info "Saving tokens to $ENV_FILE..."

    # Backup existing file if it exists
    if [[ -f "$ENV_FILE" ]]; then
        cp "$ENV_FILE" "${ENV_FILE}.backup"
        log_info "Backed up existing file to ${ENV_FILE}.backup"

        # Remove existing Slack tokens
        grep -v "^SLACK_BOT_TOKEN=" "$ENV_FILE" | grep -v "^SLACK_APP_TOKEN=" > "${ENV_FILE}.tmp" || true
        mv "${ENV_FILE}.tmp" "$ENV_FILE"
    fi

    # Append new tokens
    echo "" >> "$ENV_FILE"
    echo "# Slack Integration (added by setup-slack-app.sh)" >> "$ENV_FILE"
    echo "SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}" >> "$ENV_FILE"
    echo "SLACK_APP_TOKEN=${SLACK_APP_TOKEN}" >> "$ENV_FILE"

    log_success "Tokens saved to $ENV_FILE"
    echo ""
    echo "To load these tokens in your shell, run:"
    echo "  source $ENV_FILE"
}

export_to_shell() {
    echo ""
    echo "Run the following commands to export tokens to your current shell:"
    echo ""
    echo "  export SLACK_BOT_TOKEN='${SLACK_BOT_TOKEN}'"
    echo "  export SLACK_APP_TOKEN='${SLACK_APP_TOKEN}'"
    echo ""
    echo "Or copy this one-liner:"
    echo ""
    echo "  export SLACK_BOT_TOKEN='${SLACK_BOT_TOKEN}' SLACK_APP_TOKEN='${SLACK_APP_TOKEN}'"
    echo ""
}

test_connection() {
    local token="${1:-$SLACK_BOT_TOKEN}"

    if [[ -z "$token" ]]; then
        # Try to load from env file
        if [[ -f "$ENV_FILE" ]]; then
            source "$ENV_FILE"
            token="$SLACK_BOT_TOKEN"
        fi
    fi

    if [[ -z "$token" ]]; then
        log_error "No Bot Token available for testing"
        return 1
    fi

    log_info "Testing Slack API connection..."

    # Test auth.test endpoint
    response=$(curl -s -X POST "https://slack.com/api/auth.test" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" 2>/dev/null)

    if [[ -z "$response" ]]; then
        log_error "No response from Slack API (check your network connection)"
        return 1
    fi

    # Check if response contains "ok":true
    if echo "$response" | grep -q '"ok":true'; then
        # Extract bot name and team
        bot_name=$(echo "$response" | grep -o '"user":"[^"]*"' | cut -d'"' -f4)
        team=$(echo "$response" | grep -o '"team":"[^"]*"' | cut -d'"' -f4)

        log_success "Connection successful!"
        echo ""
        echo "  Bot Name: $bot_name"
        echo "  Team: $team"
        echo ""
        return 0
    else
        error=$(echo "$response" | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
        log_error "API test failed: $error"

        case "$error" in
            "invalid_auth")
                echo "  The Bot Token is invalid or has been revoked."
                ;;
            "token_revoked")
                echo "  The token has been revoked. Generate a new one."
                ;;
            "account_inactive")
                echo "  The Slack workspace or app is inactive."
                ;;
            *)
                echo "  Check your token and try again."
                ;;
        esac
        return 1
    fi
}

# Parse arguments
EXPORT_MODE=false
TEST_ONLY=false
QUIET=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -f|--file)
            ENV_FILE="$2"
            shift 2
            ;;
        -e|--export)
            EXPORT_MODE=true
            shift
            ;;
        -t|--test-only)
            TEST_ONLY=true
            shift
            ;;
        -q|--quiet)
            QUIET=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Main execution
main() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   Claude MPM - Slack Integration Setup   ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
    echo ""

    # Test-only mode
    if [[ "$TEST_ONLY" == "true" ]]; then
        test_connection
        exit $?
    fi

    # Check dependencies
    check_dependencies

    # Prompt for tokens
    prompt_for_tokens

    # Save or export
    if [[ "$EXPORT_MODE" == "true" ]]; then
        export_to_shell
    else
        save_to_env_file
    fi

    # Test connection
    echo ""
    read -p "Would you like to test the connection now? [Y/n] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        test_connection
    fi

    echo ""
    log_success "Setup complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Ensure your Slack app has the required OAuth scopes"
    echo "  2. Register slash commands in your Slack app settings"
    echo "  3. Run the bot: python -m claude_mpm.slack_bot"
    echo ""
    echo "For detailed instructions, see: docs/SLACK_SETUP.md"
    echo ""
}

main
