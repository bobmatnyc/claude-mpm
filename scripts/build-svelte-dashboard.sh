#!/bin/bash
# Build Svelte dashboard and deploy to static directory
#
# WHY: Automates the Svelte dashboard build process and ensures
# the build output is in the correct location for the Python server.
#
# USAGE: ./scripts/build-svelte-dashboard.sh

set -e  # Exit on error

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SVELTE_DIR="$PROJECT_ROOT/src/claude_mpm/dashboard-svelte"
BUILD_OUTPUT="$PROJECT_ROOT/src/claude_mpm/dashboard/static/svelte-build"

echo "🔨 Building Svelte dashboard..."
echo "   Source: $SVELTE_DIR"
echo "   Output: $BUILD_OUTPUT"
echo ""

cd "$SVELTE_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Build the Svelte app
echo "🏗️  Building Svelte app..."
npm run build

echo ""
echo "✅ Svelte dashboard built successfully!"
echo ""
echo "📍 Build output location: $BUILD_OUTPUT"
echo ""
echo "🚀 To serve the dashboard:"
echo "   1. Start the Socket.IO server: claude-mpm monitor start"
echo "   2. Open browser to: http://localhost:8765/svelte"
echo ""
echo "📊 Dashboard routes:"
echo "   • /          → Legacy HTML dashboard"
echo "   • /svelte    → New Svelte dashboard"
echo "   • /dashboard → Full dashboard template"
echo ""
