#!/bin/bash

# Vercel Setup Verification Script
# This script verifies that the Vercel CLI is properly installed and configured
# for use with the claude-mpm Vercel Ops Agent

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "success")
            echo -e "${GREEN}✓${NC} $message"
            ;;
        "error")
            echo -e "${RED}✗${NC} $message"
            ;;
        "warning")
            echo -e "${YELLOW}⚠${NC} $message"
            ;;
        "info")
            echo -e "${BLUE}ℹ${NC} $message"
            ;;
    esac
}

# Function to check command existence
check_command() {
    local cmd=$1
    if command -v $cmd &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Header
echo "======================================"
echo "Vercel Setup Verification for Claude MPM"
echo "======================================"
echo ""

# Track overall status
VERIFICATION_PASSED=true

# 1. Check Node.js installation
print_status "info" "Checking Node.js installation..."
if check_command node; then
    NODE_VERSION=$(node --version)
    REQUIRED_VERSION="18.0.0"

    # Extract major version
    MAJOR_VERSION=$(echo $NODE_VERSION | cut -d'.' -f1 | sed 's/v//')

    if [ "$MAJOR_VERSION" -ge 18 ]; then
        print_status "success" "Node.js $NODE_VERSION installed (>= v18.0.0 required)"
    else
        print_status "error" "Node.js $NODE_VERSION is too old (>= v18.0.0 required)"
        VERIFICATION_PASSED=false
    fi
else
    print_status "error" "Node.js is not installed"
    echo "  Please install Node.js >= 18.0.0 from https://nodejs.org/"
    VERIFICATION_PASSED=false
fi

# 2. Check npm installation
print_status "info" "Checking npm installation..."
if check_command npm; then
    NPM_VERSION=$(npm --version)
    print_status "success" "npm $NPM_VERSION installed"
else
    print_status "error" "npm is not installed"
    VERIFICATION_PASSED=false
fi

# 3. Check Vercel CLI installation
print_status "info" "Checking Vercel CLI installation..."
if check_command vercel; then
    VERCEL_VERSION=$(vercel --version 2>/dev/null | head -n1)
    print_status "success" "Vercel CLI installed: $VERCEL_VERSION"
else
    print_status "warning" "Vercel CLI is not installed"
    echo "  Installing Vercel CLI globally..."

    if npm install -g vercel@latest; then
        print_status "success" "Vercel CLI installed successfully"
    else
        print_status "error" "Failed to install Vercel CLI"
        echo "  Please run: npm install -g vercel@latest"
        VERIFICATION_PASSED=false
    fi
fi

# 4. Check Vercel authentication
print_status "info" "Checking Vercel authentication..."
if vercel whoami &> /dev/null; then
    VERCEL_USER=$(vercel whoami 2>/dev/null)
    print_status "success" "Authenticated as: $VERCEL_USER"
else
    print_status "warning" "Not authenticated with Vercel"
    echo "  Please run: vercel login"
    echo "  This will open your browser for authentication"
    VERIFICATION_PASSED=false
fi

# 5. Check for Vercel project configuration
print_status "info" "Checking for Vercel project configuration..."
if [ -f ".vercel/project.json" ]; then
    PROJECT_ID=$(cat .vercel/project.json 2>/dev/null | grep -o '"projectId":"[^"]*' | cut -d'"' -f4)
    if [ ! -z "$PROJECT_ID" ]; then
        print_status "success" "Vercel project configured: $PROJECT_ID"
    else
        print_status "warning" "Vercel project file exists but no project ID found"
    fi
elif [ -f "vercel.json" ]; then
    print_status "info" "Found vercel.json configuration file"
else
    print_status "info" "No Vercel project configured in this directory"
    echo "  Run 'vercel' to link or create a project"
fi

# 6. Check for common configuration files
print_status "info" "Checking for configuration files..."

CONFIG_FILES=(
    "vercel.json"
    ".vercelignore"
    "next.config.js"
    "package.json"
)

for file in "${CONFIG_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_status "success" "Found: $file"
    fi
done

# 7. Test Vercel CLI functionality
print_status "info" "Testing Vercel CLI functionality..."

# Test listing projects (if authenticated)
if vercel whoami &> /dev/null; then
    if vercel project ls &> /dev/null; then
        print_status "success" "Can list Vercel projects"
    else
        print_status "warning" "Unable to list projects (may need team selection)"
    fi
fi

# 8. Check environment variables
print_status "info" "Checking for Vercel environment variables..."

ENV_VARS=(
    "VERCEL_TOKEN"
    "VERCEL_ORG_ID"
    "VERCEL_PROJECT_ID"
)

for var in "${ENV_VARS[@]}"; do
    if [ ! -z "${!var}" ]; then
        print_status "success" "Found environment variable: $var"
    fi
done

# 9. Check Git installation (required for Vercel)
print_status "info" "Checking Git installation..."
if check_command git; then
    GIT_VERSION=$(git --version)
    print_status "success" "$GIT_VERSION"

    # Check if current directory is a git repository
    if git rev-parse --git-dir > /dev/null 2>&1; then
        CURRENT_BRANCH=$(git branch --show-current)
        print_status "success" "Git repository detected (branch: $CURRENT_BRANCH)"
    else
        print_status "info" "Current directory is not a Git repository"
    fi
else
    print_status "error" "Git is not installed"
    VERIFICATION_PASSED=false
fi

# 10. Test basic deployment capability (dry run)
print_status "info" "Checking deployment capability..."

# Create a temporary test file if no deployable content exists
TEMP_TEST_FILE=""
if [ ! -f "package.json" ] && [ ! -f "index.html" ]; then
    TEMP_TEST_FILE="vercel-test-$(date +%s).html"
    echo "<h1>Vercel Test</h1>" > "$TEMP_TEST_FILE"
    print_status "info" "Created temporary test file: $TEMP_TEST_FILE"
fi

# Check if we can run a build (without actually deploying)
if vercel build --help &> /dev/null; then
    print_status "success" "Vercel build command available"
else
    print_status "warning" "Vercel build command not available (older CLI version?)"
fi

# Clean up temporary test file
if [ ! -z "$TEMP_TEST_FILE" ] && [ -f "$TEMP_TEST_FILE" ]; then
    rm "$TEMP_TEST_FILE"
    print_status "info" "Cleaned up temporary test file"
fi

# Summary
echo ""
echo "======================================"
echo "Verification Summary"
echo "======================================"

if [ "$VERIFICATION_PASSED" = true ]; then
    print_status "success" "All critical checks passed!"
    echo ""
    echo "The Vercel Ops Agent is ready to use with the following capabilities:"
    echo "  • Deploy applications to Vercel"
    echo "  • Manage environment variables"
    echo "  • Configure custom domains"
    echo "  • Monitor deployments"
    echo "  • Implement rolling releases"
    echo ""
    echo "To deploy with the Vercel Ops Agent, use:"
    echo "  claude-mpm delegate vercel-ops-agent 'Deploy to production'"
else
    print_status "error" "Some critical checks failed"
    echo ""
    echo "Please address the issues above before using the Vercel Ops Agent."
    echo "For more information, visit: https://vercel.com/docs/cli"
    exit 1
fi

# Optional: Show useful commands
echo ""
echo "Useful Vercel CLI commands:"
echo "  vercel          - Deploy to preview"
echo "  vercel --prod   - Deploy to production"
echo "  vercel env ls   - List environment variables"
echo "  vercel logs     - View deployment logs"
echo "  vercel rollback - Rollback to previous deployment"
echo ""

# Check for advanced features (informational only)
print_status "info" "Advanced Features Check:"

# Check for team configuration
if [ -f ".vercel/project.json" ]; then
    if grep -q "orgId" .vercel/project.json 2>/dev/null; then
        print_status "info" "Team/Organization configured"
    fi
fi

# Check for GitHub integration
if [ -d ".git" ] && [ -f ".github/workflows" ]; then
    print_status "info" "GitHub Actions workflows detected"
fi

# Check for monorepo setup
if [ -f "lerna.json" ] || [ -f "pnpm-workspace.yaml" ] || [ -f "rush.json" ]; then
    print_status "info" "Monorepo configuration detected"
fi

echo ""
print_status "success" "Vercel setup verification complete!"
