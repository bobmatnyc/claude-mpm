#!/usr/bin/env bash
#
# Test script for new agent management commands
# This demonstrates the enhanced agent management functionality

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Testing Enhanced Agent Management Commands${NC}"
echo "=========================================="
echo

echo -e "${GREEN}1. Testing 'agents list --by-tier'${NC}"
echo "Shows agents grouped by precedence tier (PROJECT > USER > SYSTEM)"
./claude-mpm agents list --by-tier | head -30
echo

echo -e "${GREEN}2. Testing 'agents view <agent_name>'${NC}"
echo "Shows detailed information about the 'engineer' agent"
./claude-mpm agents view engineer | head -40
echo

echo -e "${GREEN}3. Testing 'agents fix --dry-run'${NC}"
echo "Preview frontmatter fixes for the 'engineer' agent"
./claude-mpm agents fix engineer --dry-run
echo

echo -e "${GREEN}4. Testing 'agents fix --all --dry-run'${NC}"
echo "Preview frontmatter fixes for all agents"
./claude-mpm agents fix --all --dry-run | head -50
echo

echo -e "${BLUE}All tests completed successfully!${NC}"
echo
echo -e "${YELLOW}Available new commands:${NC}"
echo "  • claude-mpm agents list --by-tier    # Show agents by precedence tier"
echo "  • claude-mpm agents view <name>       # View detailed agent information"
echo "  • claude-mpm agents fix <name>        # Fix agent frontmatter issues"
echo "  • claude-mpm agents fix --all         # Fix all agents' frontmatter"
echo
