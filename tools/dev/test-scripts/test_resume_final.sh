#!/bin/bash
# Final integration test for --resume flag implementation

set -e

echo "============================================================"
echo "Final Integration Test for --resume Flag"
echo "============================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Testing various --resume flag scenarios..."
echo ""

# Test 1: Check bash wrapper recognizes --resume
echo "Test 1: Bash wrapper recognition"
if grep -q '"--resume"' "$SCRIPT_DIR/claude-mpm" && grep -q 'MPM_FLAGS=' "$SCRIPT_DIR/claude-mpm"; then
    echo -e "${GREEN}✓${NC} Bash wrapper includes --resume in MPM_FLAGS"
else
    echo -e "${RED}✗${NC} Bash wrapper missing --resume in MPM_FLAGS"
    exit 1
fi

# Test 2: Python tests
echo ""
echo "Test 2: Python unit tests"
cd "$PROJECT_ROOT"
if python "$SCRIPT_DIR/test_resume_flag_fix.py" >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Python unit tests pass"
else
    echo -e "${RED}✗${NC} Python unit tests failed (running with output for debugging)"
    python "$SCRIPT_DIR/test_resume_flag_fix.py"
    exit 1
fi

# Test 3: Command building tests
echo ""
echo "Test 3: Command building tests"
if python "$SCRIPT_DIR/test_resume_command_build.py" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Command building tests pass"
else
    echo -e "${RED}✗${NC} Command building tests failed"
    exit 1
fi

# Test 4: Dry run with --resume (check if it would build the right command)
echo ""
echo "Test 4: Dry run command construction"
# We'll use Python to simulate command construction
python -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/src')
from claude_mpm.cli.parser import create_parser
from claude_mpm.cli import _ensure_run_attributes
from claude_mpm.cli.commands.run import filter_claude_mpm_args

parser = create_parser()

# Test claude-mpm --resume
args = parser.parse_args(['--resume'])
_ensure_run_attributes(args)
if '--resume' in args.claude_args:
    print('✓ claude-mpm --resume: Command would include --resume')
else:
    print('✗ claude-mpm --resume: Command missing --resume')
    sys.exit(1)

# Test claude-mpm run --resume
args = parser.parse_args(['run', '--resume'])
raw_claude_args = getattr(args, 'claude_args', []) or []
if getattr(args, 'resume', False):
    if '--resume' not in raw_claude_args:
        raw_claude_args = ['--resume'] + raw_claude_args
claude_args = filter_claude_mpm_args(raw_claude_args)
if '--resume' in claude_args:
    print('✓ claude-mpm run --resume: Command would include --resume')
else:
    print('✗ claude-mpm run --resume: Command missing --resume')
    sys.exit(1)
" || exit 1

echo ""
echo "============================================================"
echo -e "${GREEN}✅ ALL INTEGRATION TESTS PASSED!${NC}"
echo "============================================================"
echo ""
echo "The --resume flag implementation is complete and working."
echo ""
echo "Usage examples:"
echo "  • claude-mpm --resume"
echo "  • claude-mpm run --resume"
echo "  • claude-mpm --resume -- --model opus"
echo "  • claude-mpm run --resume -- --model sonnet"
echo ""
echo "The --resume flag will be properly passed to Claude Code"
echo "to resume the last conversation."
echo ""
