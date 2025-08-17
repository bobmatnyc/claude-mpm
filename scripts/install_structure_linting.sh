#!/bin/bash
# Install structure linting hooks and CI integration for Claude MPM

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="$PROJECT_ROOT/.git/hooks"
STRUCTURE_LINTER="$PROJECT_ROOT/tools/dev/structure_linter.py"

echo "🔧 Installing Claude MPM Structure Linting..."

# Ensure the structure linter exists and is executable
if [[ ! -f "$STRUCTURE_LINTER" ]]; then
    echo "❌ Error: Structure linter not found at $STRUCTURE_LINTER"
    exit 1
fi

chmod +x "$STRUCTURE_LINTER"

# Create pre-commit hook
echo "📝 Creating pre-commit hook..."
cat > "$HOOKS_DIR/pre-commit" << 'EOF'
#!/bin/bash
# Claude MPM Structure Linting Pre-commit Hook

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
STRUCTURE_LINTER="$PROJECT_ROOT/tools/dev/structure_linter.py"

echo "🔍 Running structure linting..."

# Run structure linter
if ! python "$STRUCTURE_LINTER" --verbose; then
    echo ""
    echo "❌ Structure violations found!"
    echo "💡 Run 'python tools/dev/structure_linter.py --fix' to automatically fix violations"
    echo "   or manually move files to comply with project structure guidelines"
    echo ""
    echo "📖 See docs/STRUCTURE.md for project structure requirements"
    exit 1
fi

echo "✅ Structure linting passed"
EOF

chmod +x "$HOOKS_DIR/pre-commit"

# Create GitHub Actions workflow
echo "🚀 Creating GitHub Actions workflow..."
mkdir -p "$PROJECT_ROOT/.github/workflows"

cat > "$PROJECT_ROOT/.github/workflows/structure-lint.yml" << 'EOF'
name: Structure Linting

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  structure-lint:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        # Install minimal dependencies needed for structure linter
        pip install pathlib
        
    - name: Run structure linting
      run: |
        python tools/dev/structure_linter.py --verbose
        
    - name: Check for violations
      if: failure()
      run: |
        echo "❌ Structure violations detected!"
        echo "💡 Run 'python tools/dev/structure_linter.py --fix' locally to fix violations"
        echo "📖 See docs/STRUCTURE.md for project structure requirements"
        exit 1
EOF

# Create VS Code task for structure linting
echo "🔧 Creating VS Code task..."
mkdir -p "$PROJECT_ROOT/.vscode"

# Check if tasks.json exists and update it, or create new one
TASKS_FILE="$PROJECT_ROOT/.vscode/tasks.json"
if [[ -f "$TASKS_FILE" ]]; then
    echo "📝 Adding structure linting task to existing VS Code tasks..."
    # Create backup
    cp "$TASKS_FILE" "$TASKS_FILE.backup"
    
    # Add structure linting task (simplified approach - manual edit recommended)
    echo "⚠️  Please manually add the following task to .vscode/tasks.json:"
    echo ""
    cat << 'EOF'
{
    "label": "Structure Lint",
    "type": "shell",
    "command": "python",
    "args": ["tools/dev/structure_linter.py", "--verbose"],
    "group": "test",
    "presentation": {
        "echo": true,
        "reveal": "always",
        "focus": false,
        "panel": "shared"
    },
    "problemMatcher": []
},
{
    "label": "Structure Lint & Fix",
    "type": "shell", 
    "command": "python",
    "args": ["tools/dev/structure_linter.py", "--fix", "--verbose"],
    "group": "test",
    "presentation": {
        "echo": true,
        "reveal": "always",
        "focus": false,
        "panel": "shared"
    },
    "problemMatcher": []
}
EOF
else
    echo "📝 Creating new VS Code tasks.json..."
    cat > "$TASKS_FILE" << 'EOF'
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Structure Lint",
            "type": "shell",
            "command": "python",
            "args": ["tools/dev/structure_linter.py", "--verbose"],
            "group": "test",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            },
            "problemMatcher": []
        },
        {
            "label": "Structure Lint & Fix",
            "type": "shell",
            "command": "python", 
            "args": ["tools/dev/structure_linter.py", "--fix", "--verbose"],
            "group": "test",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            },
            "problemMatcher": []
        }
    ]
}
EOF
fi

# Create Makefile target
echo "🔨 Adding Makefile targets..."
MAKEFILE="$PROJECT_ROOT/Makefile"

if [[ -f "$MAKEFILE" ]]; then
    echo "📝 Adding structure linting targets to existing Makefile..."
    if ! grep -q "structure-lint:" "$MAKEFILE"; then
        cat >> "$MAKEFILE" << 'EOF'

# Structure linting targets
.PHONY: structure-lint structure-fix
structure-lint:
	@echo "🔍 Running structure linting..."
	@python tools/dev/structure_linter.py --verbose

structure-fix:
	@echo "🔧 Running structure linting with auto-fix..."
	@python tools/dev/structure_linter.py --fix --verbose
EOF
    fi
else
    echo "📝 Creating new Makefile with structure linting targets..."
    cat > "$MAKEFILE" << 'EOF'
# Claude MPM Makefile

.PHONY: help structure-lint structure-fix

help:
	@echo "Available targets:"
	@echo "  structure-lint  - Run structure linting"
	@echo "  structure-fix   - Run structure linting with auto-fix"

structure-lint:
	@echo "🔍 Running structure linting..."
	@python tools/dev/structure_linter.py --verbose

structure-fix:
	@echo "🔧 Running structure linting with auto-fix..."
	@python tools/dev/structure_linter.py --fix --verbose
EOF
fi

echo ""
echo "✅ Structure linting installation complete!"
echo ""
echo "📋 What was installed:"
echo "  ✅ Pre-commit hook (.git/hooks/pre-commit)"
echo "  ✅ GitHub Actions workflow (.github/workflows/structure-lint.yml)"
echo "  ✅ VS Code tasks (.vscode/tasks.json)"
echo "  ✅ Makefile targets (structure-lint, structure-fix)"
echo ""
echo "🚀 Usage:"
echo "  • Run linting: python tools/dev/structure_linter.py --verbose"
echo "  • Auto-fix violations: python tools/dev/structure_linter.py --fix"
echo "  • Make targets: make structure-lint, make structure-fix"
echo "  • VS Code: Ctrl+Shift+P → 'Tasks: Run Task' → 'Structure Lint'"
echo ""
echo "📖 For more information, see docs/STRUCTURE.md"
