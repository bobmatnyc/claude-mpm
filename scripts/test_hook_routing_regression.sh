#!/usr/bin/env bash
# Run hook routing regression test to verify the fix

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Running Hook Routing Regression Test${NC}"
echo "====================================="
echo
echo -e "${YELLOW}WHY: This test prevents regression of the hook routing fix that changed${NC}"
echo -e "${YELLOW}     from exact string matching (type == 'hook') to prefix matching${NC}"
echo -e "${YELLOW}     (type.startswith('hook.')). This ensures hook events like${NC}" 
echo -e "${YELLOW}     'hook.user_prompt' are properly routed to HookEventHandler.${NC}"
echo

# Change to project root
cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

echo -e "${BLUE}Running regression tests...${NC}"
echo

# Run the regression test with detailed output
python -m pytest tests/socketio/test_hook_routing_regression.py \
    -v \
    --tb=short \
    -m "regression" \
    --no-header

# Capture exit code
REGRESSION_EXIT=$?

echo
echo -e "${BLUE}Running integration tests...${NC}"
echo

# Run the integration test
python -m pytest tests/socketio/test_hook_routing_regression.py \
    -v \
    --tb=short \
    -m "integration" \
    --no-header

# Capture exit code  
INTEGRATION_EXIT=$?

echo
echo -e "${BLUE}Test Summary${NC}"
echo "============"

if [ $REGRESSION_EXIT -eq 0 ]; then
    echo -e "${GREEN}✓ Regression tests passed - Hook routing logic is working correctly${NC}"
else
    echo -e "${RED}✗ Regression tests failed - Hook routing logic may be broken${NC}"
fi

if [ $INTEGRATION_EXIT -eq 0 ]; then
    echo -e "${GREEN}✓ Integration tests passed - Hook handlers work with real instances${NC}"
else
    echo -e "${RED}✗ Integration tests failed - Hook handler integration may be broken${NC}"
fi

# Overall result
if [ $REGRESSION_EXIT -eq 0 ] && [ $INTEGRATION_EXIT -eq 0 ]; then
    echo
    echo -e "${GREEN}🎉 All hook routing tests passed! The fix is working correctly.${NC}"
    echo -e "${GREEN}   Hook events like 'hook.user_prompt' will be routed to HookEventHandler.${NC}"
    exit 0
else
    echo
    echo -e "${RED}❌ Some hook routing tests failed! Please investigate.${NC}"
    exit 1
fi