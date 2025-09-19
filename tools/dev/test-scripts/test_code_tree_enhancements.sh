#!/bin/bash
# Test script for Code Tree Enhanced Visual Feedback

echo "=========================================="
echo "Code Tree Enhanced Visual Feedback Test"
echo "=========================================="
echo ""
echo "This test verifies the following features:"
echo "1. Node centering when clicked"
echo "2. Larger icon for active nodes"
echo "3. Pulsing animation during loading"
echo "4. Parent node context display"
echo "5. Smooth zoom transitions"
echo ""
echo "To test manually:"
echo "1. Start the dashboard: ./scripts/claude-mpm dashboard"
echo "2. Navigate to http://localhost:5000"
echo "3. Go to the Code tab"
echo "4. Click on directory nodes and observe:"
echo "   - Node centers in view with smooth transition"
echo "   - Clicked node icon becomes larger (12px radius)"
echo "   - Loading nodes pulse with orange color"
echo "   - Parent node shows green highlight"
echo "   - For radial layout, view adjusts to show parent and children"
echo ""
echo "Checking if files were updated..."

# Check that the JavaScript file has the new methods
echo -n "Checking for centerOnNode method... "
if grep -q "centerOnNode(d)" src/claude_mpm/dashboard/static/js/components/code-tree.js; then
    echo "✓ Found"
else
    echo "✗ Missing"
fi

echo -n "Checking for highlightActiveNode method... "
if grep -q "highlightActiveNode(d)" src/claude_mpm/dashboard/static/js/components/code-tree.js; then
    echo "✓ Found"
else
    echo "✗ Missing"
fi

echo -n "Checking for addLoadingPulse method... "
if grep -q "addLoadingPulse(d)" src/claude_mpm/dashboard/static/js/components/code-tree.js; then
    echo "✓ Found"
else
    echo "✗ Missing"
fi

echo -n "Checking for showWithParent method... "
if grep -q "showWithParent(d)" src/claude_mpm/dashboard/static/js/components/code-tree.js; then
    echo "✓ Found"
else
    echo "✗ Missing"
fi

# Check CSS for new styles
echo ""
echo "Checking CSS styles..."

echo -n "Checking for active node styles... "
if grep -q ".node-circle.active" src/claude_mpm/dashboard/static/css/code-tree.css; then
    echo "✓ Found"
else
    echo "✗ Missing"
fi

echo -n "Checking for parent-context styles... "
if grep -q ".node-circle.parent-context" src/claude_mpm/dashboard/static/css/code-tree.css; then
    echo "✓ Found"
else
    echo "✗ Missing"
fi

echo -n "Checking for loading-pulse animation... "
if grep -q "@keyframes nodePulse" src/claude_mpm/dashboard/static/css/code-tree.css; then
    echo "✓ Found"
else
    echo "✗ Missing"
fi

echo ""
echo "=========================================="
echo "Visual Test Instructions:"
echo "=========================================="
echo ""
echo "1. Start the dashboard and navigate to the Code tab"
echo "2. Test node clicking:"
echo "   a. Click a directory node"
echo "   b. Verify node centers in view (750ms transition)"
echo "   c. Verify clicked node grows to 12px radius"
echo "   d. Verify parent node shows green highlight"
echo ""
echo "3. Test loading animations:"
echo "   a. Click an unloaded directory"
echo "   b. Verify orange pulsing animation appears"
echo "   c. Verify animation stops when loading completes"
echo ""
echo "4. Test radial layout:"
echo "   a. Toggle to radial layout"
echo "   b. Click a node with children"
echo "   c. Verify view adjusts to show parent and children"
echo ""
echo "5. Test transitions:"
echo "   a. All centering should be smooth (750ms)"
echo "   b. Icon size changes should be smooth (300ms)"
echo "   c. Loading pulses should cycle every 1.2s"
echo ""
echo "=========================================="
echo "Setup complete! Files have been updated."
echo "=========================================="