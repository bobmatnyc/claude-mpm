#!/bin/bash
# Build Dashboard Assets
# This script builds the dashboard JavaScript assets using Vite

set -e

echo "🔨 Building Claude MPM Dashboard Assets..."

# Check if we're in the project root
if [ ! -f "vite.config.js" ]; then
    echo "❌ Error: vite.config.js not found. Please run this script from the project root."
    exit 1
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "⚠️  Warning: Node.js not found. Skipping dashboard build."
    echo "   The dashboard will use individual script files instead of optimized bundles."
    exit 0
fi

# Check if npm is available
if ! command -v npm &> /dev/null; then
    echo "⚠️  Warning: npm not found. Skipping dashboard build."
    echo "   The dashboard will use individual script files instead of optimized bundles."
    exit 0
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
fi

# Build the dashboard assets
echo "🏗️  Building dashboard assets with Vite..."
npm run build

# Check if build was successful
if [ -d "src/claude_mpm/dashboard/static/dist" ]; then
    echo "✅ Dashboard assets built successfully!"
    echo "   Built files are in: src/claude_mpm/dashboard/static/dist/"
else
    echo "❌ Build failed - dist directory not found"
    exit 1
fi

echo "🎉 Dashboard build complete!"
