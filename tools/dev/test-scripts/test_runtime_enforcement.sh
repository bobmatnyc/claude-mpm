#!/bin/bash
# Test runtime enforcement of output style

echo "===================================="
echo "RUNTIME OUTPUT STYLE ENFORCEMENT TEST"
echo "===================================="

# Save original settings
echo -e "\n1. Saving original settings..."
cp ~/.claude/settings.json ~/.claude/settings.json.backup 2>/dev/null || echo "   No existing settings to backup"

# Check initial state
echo -e "\n2. Initial state:"
current_style=$(cat ~/.claude/settings.json 2>/dev/null | jq -r '.activeOutputStyle' || echo "none")
echo "   Current style: $current_style"

# Test 1: Change style manually and see if it gets enforced
echo -e "\n3. Test: Manual style change"
echo "   Changing style to 'default'..."
jq '.activeOutputStyle = "default"' ~/.claude/settings.json > ~/.claude/settings.json.tmp && mv ~/.claude/settings.json.tmp ~/.claude/settings.json

# Run the test script to trigger enforcement
echo "   Running enforcement check..."
python -c "
import sys
sys.path.insert(0, 'src')
from claude_mpm.core.output_style_manager import OutputStyleManager
m = OutputStyleManager()
m.enforce_style_periodically(force_check=True)
" 2>/dev/null

# Check result
new_style=$(cat ~/.claude/settings.json | jq -r '.activeOutputStyle')
echo "   Style after enforcement: $new_style"

if [ "$new_style" = "claude-mpm" ]; then
    echo "   ✅ PASS: Style was enforced back to claude-mpm"
else
    echo "   ❌ FAIL: Style was not enforced (is: $new_style)"
fi

# Test 2: Multiple changes
echo -e "\n4. Test: Multiple style changes"
styles=("minimal" "verbose" "default")
for style in "${styles[@]}"; do
    echo "   Changing to '$style'..."
    jq ".activeOutputStyle = \"$style\"" ~/.claude/settings.json > ~/.claude/settings.json.tmp && mv ~/.claude/settings.json.tmp ~/.claude/settings.json

    python -c "
import sys
sys.path.insert(0, 'src')
from claude_mpm.core.output_style_manager import OutputStyleManager
m = OutputStyleManager()
m.enforce_style_periodically(force_check=True)
" 2>/dev/null

    result=$(cat ~/.claude/settings.json | jq -r '.activeOutputStyle')
    if [ "$result" = "claude-mpm" ]; then
        echo "   ✅ Enforced: $style → claude-mpm"
    else
        echo "   ❌ Failed: $style → $result"
    fi
done

# Test 3: Check logging
echo -e "\n5. Test: Enforcement logging"
python -c "
import sys
sys.path.insert(0, 'src')
from claude_mpm.core.output_style_manager import OutputStyleManager

# Change style
import json
from pathlib import Path
settings_file = Path.home() / '.claude' / 'settings.json'
settings = json.loads(settings_file.read_text())
settings['activeOutputStyle'] = 'verbose'
settings_file.write_text(json.dumps(settings, indent=2))

# Create manager and check logging
m = OutputStyleManager()
print('   Enforcement status with changed style:')
m.log_enforcement_status()
print()
print('   Performing enforcement...')
m.enforce_style_periodically(force_check=True)
print()
print('   Status after enforcement:')
m.log_enforcement_status()
" 2>&1 | grep -E "(✅|⚠️|ℹ️)" | sed 's/^/   /'

# Restore original settings
echo -e "\n6. Cleanup:"
if [ -f ~/.claude/settings.json.backup ]; then
    mv ~/.claude/settings.json.backup ~/.claude/settings.json
    echo "   Restored original settings"
else
    echo "   No backup to restore"
fi

echo -e "\n===================================="
echo "TEST COMPLETED"
echo "===================================="
