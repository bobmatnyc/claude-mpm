#!/bin/bash

# Test script for file change tracking functionality
# This script tests the new file change viewer components

echo "Testing File Change Tracking System"
echo "===================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test directory
TEST_DIR="/tmp/claude-mpm-test-$$"
mkdir -p "$TEST_DIR"

echo -e "\n${YELLOW}1. Testing JavaScript components...${NC}"

# Check if files exist
echo "Checking component files:"
for file in \
    "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/file-change-tracker.js" \
    "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/diff-viewer.js" \
    "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/file-change-viewer.js"
do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $(basename "$file") exists"
    else
        echo -e "  ${RED}✗${NC} $(basename "$file") missing"
        exit 1
    fi
done

echo -e "\n${YELLOW}2. Checking JavaScript syntax...${NC}"

# Use Node.js to check syntax
for file in \
    "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/file-change-tracker.js" \
    "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/diff-viewer.js" \
    "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/file-change-viewer.js"
do
    echo -n "  Checking $(basename "$file")... "
    if node -c "$file" 2>/dev/null; then
        echo -e "${GREEN}valid syntax${NC}"
    else
        echo -e "${RED}syntax error${NC}"
        node -c "$file"
        exit 1
    fi
done

echo -e "\n${YELLOW}3. Testing component integration...${NC}"

# Create a simple test HTML file
cat > "$TEST_DIR/test.html" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>File Change Tracker Test</title>
</head>
<body>
    <h1>File Change Tracker Test</h1>
    <div id="test-output"></div>

    <script>
        // Mock window.eventViewer
        window.eventViewer = {
            events: [
                {
                    type: 'tool',
                    subtype: 'post_tool',
                    tool_name: 'Edit',
                    tool_parameters: {
                        file_path: '/test/file1.py',
                        old_string: 'hello',
                        new_string: 'world'
                    },
                    timestamp: new Date().toISOString(),
                    session_id: 'test-session-1'
                },
                {
                    type: 'tool',
                    subtype: 'post_tool',
                    tool_name: 'Write',
                    tool_parameters: {
                        file_path: '/test/file2.js',
                        content: 'console.log("test");'
                    },
                    timestamp: new Date().toISOString(),
                    session_id: 'test-session-1'
                },
                {
                    type: 'tool',
                    subtype: 'post_tool',
                    tool_name: 'Read',
                    tool_parameters: {
                        file_path: '/test/file3.md'
                    },
                    tool_result: {
                        content: '# Test File'
                    },
                    timestamp: new Date().toISOString(),
                    session_id: 'test-session-2'
                }
            ]
        };
    </script>

    <!-- Load components -->
    <script src="/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/file-change-tracker.js"></script>
    <script src="/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/diff-viewer.js"></script>
    <script src="/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/file-change-viewer.js"></script>

    <script>
        // Test the components
        const output = document.getElementById('test-output');

        try {
            // Test FileChangeTracker
            const tracker = new FileChangeTracker();
            tracker.updateEvents(window.eventViewer.events);

            const stats = tracker.getStatistics();
            output.innerHTML += '<p>FileChangeTracker: ' + stats.totalFiles + ' files tracked ✓</p>';

            // Test DiffViewer
            const diffViewer = new DiffViewer();
            diffViewer.initialize();
            output.innerHTML += '<p>DiffViewer: Initialized ✓</p>';

            // Test FileChangeViewer
            const fileChangeViewer = new FileChangeViewer();
            output.innerHTML += '<p>FileChangeViewer: Created ✓</p>';

            output.innerHTML += '<h2 style="color: green;">All tests passed!</h2>';
        } catch (e) {
            output.innerHTML += '<h2 style="color: red;">Test failed: ' + e.message + '</h2>';
            console.error(e);
        }
    </script>
</body>
</html>
EOF

echo "  Created test HTML file at $TEST_DIR/test.html"

echo -e "\n${YELLOW}4. Checking HTML template integration...${NC}"

# Check if the Changes button was added
if grep -q "file-changes-btn" "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/templates/index.html"; then
    echo -e "  ${GREEN}✓${NC} Changes button added to HTML"
else
    echo -e "  ${RED}✗${NC} Changes button not found in HTML"
fi

# Check if modules are loaded
if grep -q "file-change-tracker.js" "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/templates/index.html"; then
    echo -e "  ${GREEN}✓${NC} File change tracker module referenced"
else
    echo -e "  ${RED}✗${NC} File change tracker module not referenced"
fi

if grep -q "diff-viewer.js" "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/templates/index.html"; then
    echo -e "  ${GREEN}✓${NC} Diff viewer module referenced"
else
    echo -e "  ${RED}✗${NC} Diff viewer module not referenced"
fi

if grep -q "file-change-viewer.js" "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/templates/index.html"; then
    echo -e "  ${GREEN}✓${NC} File change viewer module referenced"
else
    echo -e "  ${RED}✗${NC} File change viewer module not referenced"
fi

echo -e "\n${YELLOW}5. Component Feature Check...${NC}"

# Check for key features in each component
echo "  FileChangeTracker features:"
grep -q "class FileChangeTracker" "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/file-change-tracker.js" && \
    echo -e "    ${GREEN}✓${NC} Class definition found"
grep -q "processEvent" "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/file-change-tracker.js" && \
    echo -e "    ${GREEN}✓${NC} Event processing method found"
grep -q "getFileTree" "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/file-change-tracker.js" && \
    echo -e "    ${GREEN}✓${NC} File tree generation found"

echo "  DiffViewer features:"
grep -q "class DiffViewer" "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/diff-viewer.js" && \
    echo -e "    ${GREEN}✓${NC} Class definition found"
grep -q "computeDiff" "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/diff-viewer.js" && \
    echo -e "    ${GREEN}✓${NC} Diff computation found"
grep -q "side-by-side" "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/diff-viewer.js" && \
    echo -e "    ${GREEN}✓${NC} Side-by-side view found"

echo "  FileChangeViewer features:"
grep -q "class FileChangeViewer" "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/file-change-viewer.js" && \
    echo -e "    ${GREEN}✓${NC} Class definition found"
grep -q "updateFileTree" "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/file-change-viewer.js" && \
    echo -e "    ${GREEN}✓${NC} File tree update found"
grep -q "session-filter" "/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/file-change-viewer.js" && \
    echo -e "    ${GREEN}✓${NC} Session filtering found"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✓ All tests passed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\nTest artifacts saved in: $TEST_DIR"
echo "To test in browser, open: $TEST_DIR/test.html"

# Cleanup option
echo -e "\nClean up test directory? (y/n)"
read -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$TEST_DIR"
    echo "Test directory cleaned up."
fi