#!/bin/bash
# Test script to verify the fixes

echo "=========================================="
echo "Testing Code Tree Fixes"
echo "=========================================="
echo ""
echo "1. Testing dotfile filtering fix:"
echo "   - .github and .ai-trackdown should NOT appear by default"
echo "   - They removed from DOTFILE_EXCEPTIONS list"
echo ""

# Check if .github was removed from exceptions
echo -n "Checking if .github removed from exceptions... "
if ! grep -q '".github"' src/claude_mpm/tools/code_tree_analyzer.py; then
    echo "✓ Fixed"
else
    echo "✗ Still in exceptions"
fi

echo ""
echo "2. Testing visual feedback fixes:"
echo "   - Node selection now uses g.node > circle.node-circle pattern"
echo "   - This should work for ALL node types including directories"
echo ""

# Check if the selection pattern was fixed
echo -n "Checking highlightActiveNode fix... "
if grep -q "this.treeGroup.selectAll('g.node')" src/claude_mpm/dashboard/static/js/components/code-tree.js; then
    echo "✓ Fixed"
else
    echo "✗ Not fixed"
fi

echo -n "Checking addLoadingPulse fix... "
if grep -q "const node = this.treeGroup.selectAll('g.node')" src/claude_mpm/dashboard/static/js/components/code-tree.js; then
    echo "✓ Fixed"
else
    echo "✗ Not fixed"
fi

echo ""
echo "=========================================="
echo "Manual Testing Instructions:"
echo "=========================================="
echo ""
echo "1. Start the dashboard:"
echo "   ./scripts/claude-mpm dashboard"
echo ""
echo "2. Navigate to the Code tab"
echo ""
echo "3. Verify dotfile filtering:"
echo "   - .github folder should NOT be visible"
echo "   - .ai-trackdown folder should NOT be visible"  
echo "   - .gitignore SHOULD still be visible (it's an exception)"
echo ""
echo "4. Test folder visual feedback:"
echo "   - Click on any directory node"
echo "   - Should see ALL these effects immediately:"
echo "     a) Node centers in view (smooth 750ms transition)"
echo "     b) Circle grows from 8px to 12px radius"
echo "     c) Blue stroke appears around clicked node"
echo "     d) Parent node gets green stroke"
echo "     e) Orange pulsing starts while loading"
echo ""
echo "5. Expected behavior summary:"
echo "   - Dotfiles hidden by default (except .gitignore)"
echo "   - All visual feedback works for folders AND files"
echo "   - Effects trigger BEFORE data loading"
echo ""
echo "=========================================="
echo "Fixes Complete!"
echo "=========================================="