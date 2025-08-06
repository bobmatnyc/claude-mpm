#!/usr/bin/env bash
# Integration test for MCP monitoring solution

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=================================="
echo "MCP Solution Integration Test"
echo "=================================="

# Test 1: Check scripts exist
echo "Test 1: Checking script existence..."
if [[ -f "$SCRIPT_DIR/monitor_mcp_services.py" ]] && \
   [[ -f "$SCRIPT_DIR/setup_local_mcp.sh" ]] && \
   [[ -f "$SCRIPT_DIR/../config/mcp_services.yaml" ]]; then
    echo "✅ All scripts exist"
else
    echo "❌ Missing scripts"
    exit 1
fi

# Test 2: Test monitor help
echo -e "\nTest 2: Testing monitor script..."
if python3 "$SCRIPT_DIR/monitor_mcp_services.py" --help > /dev/null 2>&1; then
    echo "✅ Monitor script is valid Python"
else
    echo "❌ Monitor script has syntax errors"
    exit 1
fi

# Test 3: Test setup script status
echo -e "\nTest 3: Testing setup script..."
if "$SCRIPT_DIR/setup_local_mcp.sh" status > /dev/null 2>&1; then
    echo "✅ Setup script runs successfully"
else
    echo "❌ Setup script failed"
    exit 1
fi

# Test 4: Check configuration is valid YAML
echo -e "\nTest 4: Testing configuration..."
if python3 -c "import yaml; yaml.safe_load(open('$SCRIPT_DIR/../config/mcp_services.yaml'))" 2>/dev/null; then
    echo "✅ Configuration is valid YAML"
else
    echo "❌ Configuration is invalid"
    exit 1
fi

# Test 5: Test monitor with dry run
echo -e "\nTest 5: Testing monitor dry run..."
if python3 "$SCRIPT_DIR/monitor_mcp_services.py" --status 2>&1 | grep -q "MCP Service Status"; then
    echo "✅ Monitor status check works"
else
    echo "❌ Monitor status check failed"
    exit 1
fi

echo -e "\n=================================="
echo "Integration Test Complete"
echo "Result: PASS - All tests passed"
echo "=================================="
echo ""
echo "The MCP monitoring solution is validated and ready to use."
echo ""
echo "To start monitoring:"
echo "  ./scripts/setup_local_mcp.sh setup    # Initial setup"
echo "  ./scripts/setup_local_mcp.sh start    # Start monitoring"
echo ""
echo "To monitor services directly:"
echo "  python3 ./scripts/monitor_mcp_services.py"
echo ""