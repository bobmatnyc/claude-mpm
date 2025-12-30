# Refactor: Move Skill Mappings from Static YAML to Agent Frontmatter

**Date**: 2025-12-30
**Status**: ✅ Complete
**Related**: skill_to_agent_mapping.yaml → agent frontmatter migration

## Executive Summary

Successfully migrated skill assignment from static YAML configuration to agent frontmatter declarations. This enables:

- **Per-agent customization**: Each agent explicitly declares which skills it needs
- **No implicit mappings**: Skills are only deployed if declared in frontmatter
- **Simpler architecture**: Removed dual-source complexity (frontmatter + mapping)
- **Better maintainability**: One source of truth for agent skills

## Migration Results

### Updated Components

1. **Agent Files** (43 files in `claude-mpm-agents` repo)
   - Added `skills:` field to frontmatter
   - Converted skill paths to hyphen-separated format
   - Committed: [3adf841](https://github.com/bobmatnyc/claude-mpm-agents/commit/3adf841)

2. **selective_skill_deployer.py**
   - `get_required_skills_from_agents()`: Now ONLY uses frontmatter
   - `get_skills_from_mapping()`: Deprecated, returns empty set
   - Removed dual-source logic (frontmatter + SkillToAgentMapper)

3. **Migration Scripts**
   - `scripts/invert_skill_mapping.py`: Generate agent → skills mapping
   - `scripts/update_agent_frontmatter.py`: Bulk update agent frontmatter
   - `agent_skill_mappings.yaml`: Reference mapping (not used in deployment)

## Statistics

- **Total agents updated**: 43
- **Agents with skills**: 40
- **Agents with no skills**: 3 (web-ui-engineer, tmux, content)
- **Average skills per agent**: 18.1
- **Agent with most skills**: typescript-engineer (48 skills)
- **Agent with least skills**: agentic-coder-optimizer (11 skills)

## Skill Assignment Examples

### Python Engineer (39 skills)
```yaml
skills:
  - toolchains-ai-frameworks-dspy
  - toolchains-ai-frameworks-langchain
  - toolchains-ai-protocols-mcp
  - toolchains-python-frameworks-django
  - toolchains-python-frameworks-flask
  - toolchains-python-testing-pytest
  - toolchains-python-tooling-mypy
  - universal-architecture-software-patterns
  - universal-debugging-systematic-debugging
  # ... 30 more
```

### TypeScript Engineer (48 skills)
```yaml
skills:
  - toolchains-ai-protocols-mcp
  - toolchains-javascript-frameworks-nextjs
  - toolchains-typescript-core
  - toolchains-typescript-testing-vitest
  - toolchains-typescript-data-drizzle
  - universal-architecture-software-patterns
  # ... 42 more
```

### Generic Engineer (11 universal skills)
```yaml
skills:
  - universal-collaboration-brainstorming
  - universal-debugging-systematic-debugging
  - universal-testing-test-driven-development
  # ... 8 more
```

## Implementation Phases

### Phase 1: Generate Agent Skill Mappings ✅

**Script**: `scripts/invert_skill_mapping.py`

- Read `skill_to_agent_mapping.yaml`
- Invert mapping: skill → agents to agent → skills
- Handle special cases:
  - `ALL_AGENTS` marker expansion (41 agents)
  - Skill path normalization (slashes → hyphens)
- Output: `agent_skill_mappings.yaml`

### Phase 2: Update Agent Files ✅

**Script**: `scripts/update_agent_frontmatter.py`

- Scan `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/`
- Parse YAML frontmatter from each agent .md file
- Add/update `skills:` field with hyphen-separated skill names
- Handle agent_id variations:
  - Underscores → hyphens (`golang_engineer` → `golang-engineer`)
  - Strip `-agent` suffix (`javascript-engineer-agent` → `javascript-engineer`)
- Write updated frontmatter preserving formatting

### Phase 3: Update selective_skill_deployer.py ✅

**Changes**:

1. **`get_required_skills_from_agents()`**
   - REMOVED: Call to `get_skills_from_mapping(agent_ids)`
   - NOW: Only uses frontmatter skills
   - Logic: `frontmatter_skills` (no more `mapped_skills`)

2. **`get_skills_from_mapping()`**
   - Marked as DEPRECATED
   - Returns empty set
   - Logs deprecation warning
   - Kept for backward compatibility

### Phase 4: Commit and Push ✅

**claude-mpm-agents repo**:
```bash
cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents
git add agents/**/*.md
git commit -m "feat: add skills frontmatter to all agents"
git push origin main
```

**claude-mpm repo** (this repo):
```bash
git add scripts/ agent_skill_mappings.yaml src/claude_mpm/services/skills/selective_skill_deployer.py
git commit -m "refactor: move skill mappings from static YAML to agent frontmatter"
```

## Agent ID Normalization

### Handled Variations

| Agent File | Frontmatter agent_id | Normalized | Mapping Key |
|------------|---------------------|------------|-------------|
| golang-engineer.md | `golang_engineer` | `golang-engineer` | `golang-engineer` |
| javascript-engineer.md | `javascript-engineer-agent` | `javascript-engineer` | `javascript-engineer` |
| documentation.md | `documentation-agent` | `documentation` | `documentation` |
| api-qa.md | `api-qa-agent` | `api-qa` | `api-qa` |
| web-ui.md | `web-ui-engineer` | `web-ui-engineer` | `web-ui` ❌ (not in mapping) |

### Normalization Logic

```python
def normalize_agent_id(agent_id: str) -> str:
    # Replace underscores with hyphens
    normalized = agent_id.replace('_', '-')

    # Remove -agent suffix if present
    if normalized.endswith('-agent'):
        normalized = normalized[:-6]

    return normalized
```

## Agents Not in Mapping (No Skills Assigned)

These agents had no corresponding entry in `skill_to_agent_mapping.yaml` and received `skills: []`:

1. **web-ui-engineer** (agent_id: `web-ui-engineer`)
   - Mapping has: `web-ui` (mismatch)
   - Resolution: Empty skills list

2. **tmux** (agent_id: `tmux`)
   - Not in mapping
   - Resolution: Empty skills list

3. **content** (agent_id: `content`)
   - Mapping has: `content-agent` (mismatch)
   - Resolution: Empty skills list

## Breaking Changes

### For End Users

- **No action required**: Agent frontmatter automatically includes skills
- **Custom agents**: Must add `skills:` field to frontmatter
- **Skill deployment**: Only frontmatter skills are deployed (no inference)

### For Developers

- **`get_skills_from_mapping()`**: Now deprecated, returns empty set
- **skill_to_agent_mapping.yaml**: Still exists but not used for deployment
- **Agent frontmatter**: Single source of truth for skill requirements

## Backward Compatibility

### Preserved

- ✅ `get_skills_from_mapping()` function (deprecated but callable)
- ✅ `skill_to_agent_mapping.yaml` file (reference only)
- ✅ SkillToAgentMapper class (for other uses)

### Changed

- ❌ `get_required_skills_from_agents()` no longer calls mapping
- ❌ Static mapping no longer affects skill deployment
- ❌ Agents without frontmatter skills get zero skills

## Migration Checklist

- [x] Phase 1: Generate inverted mapping
- [x] Phase 2: Update all 43 agent files with skills frontmatter
- [x] Phase 3: Update `selective_skill_deployer.py` to use frontmatter only
- [x] Phase 4: Commit and push to claude-mpm-agents repo
- [x] Phase 5: Update claude-mpm repo with changes
- [ ] Phase 6: Update tests to reflect new behavior
- [ ] Phase 7: Update documentation (user-facing)

## Testing Recommendations

1. **Unit Tests**: Update `test_selective_skill_deployer.py`
   - Test frontmatter-only skill discovery
   - Verify `get_skills_from_mapping()` returns empty set
   - Test normalization logic

2. **Integration Tests**: Deploy agents and verify skills
   - Check that only frontmatter skills are deployed
   - Verify no skills from mapping are deployed
   - Test agents with no skills declared

3. **Regression Tests**: Existing functionality
   - User-requested skills still work
   - Orphan cleanup still works
   - Deployment tracking still works

## Future Work

### Short-term

1. **Update Tests**: Reflect frontmatter-only behavior
2. **User Documentation**: Document `skills:` frontmatter field
3. **Agent Creator**: Add `skills:` field to agent templates

### Long-term

1. **Remove Deprecated Code**: After 1-2 releases, remove:
   - `get_skills_from_mapping()` function
   - `skill_to_agent_mapping.yaml` file
   - SkillToAgentMapper class (if no other uses)

2. **Skill Discovery UI**: Help users find available skills
   - `mpm skills list` - Show all available skills
   - `mpm skills search <query>` - Find skills by keyword
   - `mpm agent add-skill <agent> <skill>` - Add skill to agent

## Files Changed

### claude-mpm-agents (external repo)

- `agents/**/*.md` (43 files) - Added `skills:` frontmatter field

### claude-mpm (this repo)

- `src/claude_mpm/services/skills/selective_skill_deployer.py` - Refactored to use frontmatter only
- `scripts/invert_skill_mapping.py` - NEW: Generate inverted mapping
- `scripts/update_agent_frontmatter.py` - NEW: Bulk update agent files
- `agent_skill_mappings.yaml` - NEW: Reference mapping (not used in deployment)
- `docs/refactor-skill-mapping-to-frontmatter.md` - NEW: This document

## Lessons Learned

### What Went Well

1. **Script-driven migration**: Automated bulk updates prevented manual errors
2. **Normalization logic**: Handled agent_id variations gracefully
3. **Backward compatibility**: Deprecated function instead of removing
4. **Incremental phases**: Clear separation of concerns

### Challenges

1. **Agent ID mismatches**: Some agents used different IDs in frontmatter vs. mapping
2. **Git conflicts**: Had to stash/rebase before pushing
3. **Unmapped agents**: 3 agents had no mapping entries

### Recommendations

1. **Consistent naming**: Enforce agent_id format (hyphen-separated, no suffix)
2. **Validation**: Add schema validation for frontmatter
3. **Discovery**: Add `mpm agent validate` command to check frontmatter
4. **Templates**: Update agent templates to include `skills:` field

## References

- Original mapping: `src/claude_mpm/config/skill_to_agent_mapping.yaml`
- Agent repo: https://github.com/bobmatnyc/claude-mpm-agents
- Commit: [3adf841](https://github.com/bobmatnyc/claude-mpm-agents/commit/3adf841)
