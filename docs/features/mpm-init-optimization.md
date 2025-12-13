# MPM-Init CLAUDE.md Optimization

## Overview

The `/mpm-init` update mode now includes an **automatic optimization step** that uses the **prompt-engineer** agent to optimize CLAUDE.md for conciseness, clarity, and token efficiency after knowledge extraction is complete.

## Feature Details

### Workflow

When running `/mpm-init` in update mode on an initialized project:

1. ✅ **Detect initialized project** (`.claude-mpm/` exists)
2. ✅ **Extract knowledge** from git history, session logs, and memory files
3. ✅ **Update CLAUDE.md** via Agentic Coder Optimizer agent
4. 🆕 **Optimize CLAUDE.md** via Prompt Engineer agent ← NEW STEP

### Optimization Goals

The prompt-engineer agent optimizes CLAUDE.md for:

1. **Conciseness**: Remove redundancy, consolidate similar instructions
2. **Clarity**: Improve structure, use clear headings and hierarchy
3. **Token Efficiency**: Reduce token count by 20-30% while preserving meaning
4. **Prompt Engineering Best Practices**: Apply Claude-specific optimizations

### Critical Information Preservation

The optimization process **preserves all critical information**:

- ✅ All 🔴 CRITICAL items (security, data handling, core business rules)
- ✅ All 🟡 IMPORTANT items (key workflows, architectural decisions)
- ✅ Essential 🟢 STANDARD instructions
- ✅ Logical organization and priority markers

### Safety Features

#### Automatic Backup

Before optimization, the system:
1. Creates an automatic backup using `ArchiveManager`
2. Stores backup with reason: `"Before prompt-engineer optimization"`
3. Restores from backup automatically if optimization fails

#### Error Handling

The optimization step is **non-blocking**:
- If backup creation fails → skip optimization with warning
- If optimization fails → restore from backup automatically
- If any error occurs → log error, show warning, continue

## User Experience

### Console Output

```
✓ Detected initialized project - activating enhanced update mode
✓ Analyzing git history (last 90 days)...
  - Found 12 architectural decisions
  - Detected 8 workflow patterns
✓ Analyzing session logs...
  - Found 15 learning entries
✓ Analyzing memory files...
  - Found 23 accumulated insights
✓ Knowledge extraction complete - building enhanced prompt

[Delegating to Agentic Coder Optimizer...]
✓ Update complete

✓ Optimizing CLAUDE.md with prompt-engineer...
  - Original: 4,500 tokens (estimated)
  - Backup created: .claude-mpm/archives/CLAUDE.md.2025-12-13T10-30-45.bak
  - Optimized: 3,200 tokens (29% reduction)
✓ CLAUDE.md optimization complete
```

### Token Estimation

Token counts are **estimated** using a simple heuristic:
- **Formula**: `len(text) // 4` (approximately 4 characters per token)
- **Purpose**: Display progress and reduction percentage
- **Accuracy**: Rough estimate, sufficient for user feedback

## Implementation Details

### Files Modified

1. **`src/claude_mpm/cli/commands/mpm_init/core.py`**:
   - `_handle_update_post_processing()`: Added optimization call
   - `_optimize_claude_md_with_prompt_engineer()`: New method for optimization
   - `_estimate_tokens()`: Token counting helper

2. **`src/claude_mpm/cli/commands/mpm_init/prompts.py`**:
   - `build_prompt_engineer_optimization_prompt()`: New prompt builder

### Delegation Pattern

The optimization follows the same delegation pattern as Agentic Coder Optimizer:

```python
# Build prompt with optimization instructions
prompt = prompts.build_prompt_engineer_optimization_prompt(
    content=claude_md_content,
    estimated_tokens=token_count
)

# Run through subprocess (same as initialization)
result = self._run_initialization(
    prompt,
    verbose=False,
    update_mode=True
)
```

### Prompt Structure

The optimization prompt includes:

1. **Delegation header**: "Please delegate this task to the Prompt Engineer agent:"
2. **Current statistics**: Token count, target reduction
3. **Optimization goals**: Redundancy removal, language tightening, structure improvement
4. **Preservation rules**: Keep all CRITICAL and IMPORTANT content
5. **Quality criteria**: Clear checklist of success factors
6. **Current content**: Full CLAUDE.md to optimize

## Configuration

### Optional Flag (Future Enhancement)

A `--skip-optimize` flag could be added to skip optimization:

```bash
mpm-init --update --skip-optimize
```

Currently, optimization runs automatically on all update mode operations.

### Disable via Environment Variable (Future)

```bash
CLAUDE_MPM_SKIP_OPTIMIZE=1 mpm-init --update
```

## Performance

### Token Count Reduction

Expected results based on prompt-engineer capabilities:
- **Target**: 20-30% reduction
- **Typical**: 25% reduction (e.g., 4,500 → 3,375 tokens)
- **Range**: 15-40% depending on content redundancy

### Execution Time

- **Backup creation**: <100ms
- **Optimization**: 5-15 seconds (depends on CLAUDE.md size and API latency)
- **Total overhead**: ~5-20 seconds added to update workflow

## Testing

### Manual Testing

```bash
# 1. Create test project
mkdir /tmp/test-project
cd /tmp/test-project

# 2. Initialize
mpm-init

# 3. Make changes and commit
git init
echo "# Test" > README.md
git add . && git commit -m "Initial commit"

# 4. Create .claude-mpm directory
mkdir .claude-mpm

# 5. Run update mode (triggers optimization)
mpm-init --update

# 6. Verify backup exists
ls -la .claude-mpm/archives/

# 7. Check token reduction in output
```

### Verification Checklist

- [ ] Backup created before optimization
- [ ] Token count reduction displayed
- [ ] CRITICAL instructions preserved
- [ ] IMPORTANT instructions preserved
- [ ] Priority markers intact (🔴 🟡 🟢 ⚪)
- [ ] Structure remains logical
- [ ] No loss of essential information

## Future Enhancements

### 1. Skip Optimization Flag

Add CLI flag to skip optimization:

```python
def initialize_project(
    self,
    # ... existing params ...
    skip_optimize: bool = False,
) -> Dict:
    # ...
```

### 2. Diff Display

Show before/after diff for review:

```python
from difflib import unified_diff

diff = unified_diff(
    original_content.splitlines(),
    optimized_content.splitlines(),
    lineterm=''
)
print('\n'.join(diff))
```

### 3. Interactive Approval

Prompt user to approve changes:

```python
self.console.print("[yellow]Review optimization changes?[/yellow]")
if Confirm.ask("Apply optimization?"):
    # Apply changes
else:
    # Restore backup
```

### 4. Optimization Metrics

Track and display detailed metrics:
- Sections removed/consolidated
- Redundant phrases eliminated
- Structural improvements made
- Token savings by section

## Related Documentation

- [Agentic Coder Optimizer](../agents/agentic-coder-optimizer.md)
- [Prompt Engineer Agent](../agents/prompt-engineer.md)
- [Knowledge Extraction](./knowledge-extraction.md)
- [Archive Manager](../services/archive-manager.md)

## Changelog

### 2025-12-13
- **Added**: Automatic CLAUDE.md optimization with prompt-engineer
- **Added**: Token counting and reduction metrics
- **Added**: Automatic backup before optimization
- **Added**: Graceful error handling and recovery
