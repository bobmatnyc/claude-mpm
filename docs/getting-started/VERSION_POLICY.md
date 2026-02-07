# PM Instructions Version Policy

## Version Format
```markdown
<!-- PM_INSTRUCTIONS_VERSION: XXXX -->
```
- 4-digit zero-padded version (e.g., 0001, 0007, 0042)
- Must be on first line of PM_INSTRUCTIONS.md
- Increment for ANY content change

## Version Increment Rules

### When to Increment
- ✅ Any edit to PM_INSTRUCTIONS.md content
- ✅ Agent role changes
- ✅ Workflow updates
- ✅ Memory category changes
- ✅ New sections or instructions
- ✅ Typo fixes or clarifications

### How to Increment
1. Find current version: `grep PM_INSTRUCTIONS_VERSION src/claude_mpm/agents/PM_INSTRUCTIONS.md`
2. Increment by 1: v0007 → v0008
3. Update first line: `<!-- PM_INSTRUCTIONS_VERSION: 0008 -->`
4. Commit with message: `chore: bump PM instructions to v0008`

## Version Validation

### Loader Behavior
The instruction loader validates versions:
```python
if deployed_version < source_version:
    # Reject stale deployed file
    # Use source file instead
    logger.warning(f"Deployed v{deployed} is stale, source is v{source}")
```

### Deployed File Lifecycle
1. **Development**: Source file (`src/claude_mpm/agents/PM_INSTRUCTIONS.md`) used directly
2. **Deploy**: `mpm deploy` merges PM_INSTRUCTIONS + WORKFLOW + MEMORY → `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md`
3. **Production**: Deployed file used IF `deployed_version >= source_version`
4. **Stale Deployed**: Source file used automatically with warning

## Checking Versions

### Quick Check
```bash
# Source version
grep PM_INSTRUCTIONS_VERSION src/claude_mpm/agents/PM_INSTRUCTIONS.md

# Deployed version (if exists)
grep PM_INSTRUCTIONS_VERSION .claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md

# Which version is PM loading?
python3 -c "
from pathlib import Path
from src.claude_mpm.core.framework.loaders.instruction_loader import InstructionLoader
import re

loader = InstructionLoader(framework_path=Path.cwd())
content = {}
loader.load_framework_instructions(content)

match = re.search(r'PM_INSTRUCTIONS_VERSION:\s*(\d+)', content.get('framework_instructions', ''))
print(f'PM loading version: v{match.group(1)}' if match else 'Version not found')
"
```

### Version Validation Test
```bash
python3 -c "
from pathlib import Path
import re

source = Path('src/claude_mpm/agents/PM_INSTRUCTIONS.md').read_text()
deployed = Path('.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md')

source_v = int(re.search(r'PM_INSTRUCTIONS_VERSION:\s*(\d+)', source).group(1))

if deployed.exists():
    deployed_v = int(re.search(r'PM_INSTRUCTIONS_VERSION:\s*(\d+)', deployed.read_text()).group(1))
    status = '✓ OK' if deployed_v >= source_v else '✗ STALE'
    print(f'Source: v{source_v:04d}')
    print(f'Deployed: v{deployed_v:04d} {status}')
else:
    print(f'Source: v{source_v:04d}')
    print('Deployed: NOT FOUND (will use source)')
"
```

## Force Redeploy

If deployed version is stale:
```bash
# Remove stale deployed file
rm -f .claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md

# Trigger redeploy
mpm deploy
```

Or just start PM (it will use source automatically):
```bash
mpm pm start  # Uses source v0007 if deployed is v0006
```

## Best Practices

1. **Always increment version** when editing PM_INSTRUCTIONS.md
2. **Check version before commit**: `grep PM_INSTRUCTIONS_VERSION src/claude_mpm/agents/PM_INSTRUCTIONS.md`
3. **Redeploy after version bump**: `mpm deploy` to update deployed file
4. **Monitor logs** for version warnings during PM startup

## Example Workflow

```bash
# 1. Edit PM_INSTRUCTIONS.md
vim src/claude_mpm/agents/PM_INSTRUCTIONS.md

# 2. Increment version (v0007 → v0008)
sed -i '' 's/PM_INSTRUCTIONS_VERSION: 0007/PM_INSTRUCTIONS_VERSION: 0008/' \
  src/claude_mpm/agents/PM_INSTRUCTIONS.md

# 3. Verify version
grep PM_INSTRUCTIONS_VERSION src/claude_mpm/agents/PM_INSTRUCTIONS.md
# Output: <!-- PM_INSTRUCTIONS_VERSION: 0008 -->

# 4. Commit
git add src/claude_mpm/agents/PM_INSTRUCTIONS.md
git commit -m "feat: enhance PM delegation logic (v0008)"

# 5. Redeploy
mpm deploy
```

---

**Purpose**: Prevent stale PM instructions from being loaded silently
**Status**: Active since 2025-12-23
**Related**: FIX_SUMMARY_PM_INSTRUCTIONS_VERSION_VALIDATION.md
