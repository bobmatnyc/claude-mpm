#!/bin/bash
# Script to verify claude-mpm installation using Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=================================="
echo "Claude-MPM Installation Verifier"
echo "=================================="
echo ""

# Parse command line arguments
REBUILD=false
INTERACTIVE=false
TEST_SUITE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --rebuild|-r)
            REBUILD=true
            shift
            ;;
        --interactive|-i)
            INTERACTIVE=true
            shift
            ;;
        --test|-t)
            TEST_SUITE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -r, --rebuild      Force rebuild of Docker image"
            echo "  -i, --interactive  Run interactive shell after verification"
            echo "  -t, --test        Run test suite after verification"
            echo "  -h, --help        Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

cd "$SCRIPT_DIR"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    echo "Please install Docker from https://www.docker.com/get-started"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null && ! docker-compose --version &> /dev/null; then
    echo "Error: Docker Compose is not installed"
    echo "Please install Docker Compose"
    exit 1
fi

# Determine docker-compose command
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

echo "Using Docker Compose command: $COMPOSE_CMD"
echo ""

# Build if needed
if [ "$REBUILD" = true ]; then
    echo "Rebuilding Docker image..."
    $COMPOSE_CMD build --no-cache claude-mpm-clean
    echo ""
fi

# Run verification
echo "Running installation verification..."
echo "=================================="
$COMPOSE_CMD up --no-deps claude-mpm-clean

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "=================================="
    echo "✅ Installation verification PASSED"
    echo "=================================="
else
    echo ""
    echo "=================================="
    echo "❌ Installation verification FAILED"
    echo "=================================="
    echo "Check the logs above for details"
    exit 1
fi

# Run test suite if requested
if [ "$TEST_SUITE" = true ]; then
    echo ""
    echo "Running test suite..."
    echo "=================================="
    $COMPOSE_CMD --profile test up --no-deps claude-mpm-test
fi

# Start interactive session if requested
if [ "$INTERACTIVE" = true ]; then
    echo ""
    echo "Starting interactive session..."
    echo "=================================="
    $COMPOSE_CMD --profile interactive run --rm claude-mpm-interactive
fi

# Cleanup
echo ""
echo "Cleaning up containers..."
$COMPOSE_CMD down

echo ""
echo "Verification complete!"