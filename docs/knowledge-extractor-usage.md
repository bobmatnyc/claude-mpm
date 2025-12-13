# Knowledge Extractor - Enhanced /mpm-init Update Mode

## Overview

The enhanced `/mpm-init` update mode automatically detects initialized projects and extracts knowledge from multiple sources to enrich CLAUDE.md updates.

## Auto-Detection Flow

When `/mpm-init` runs on a project:

1. **Check for `.claude-mpm/` directory**
   - If exists → AUTO-DETECT initialized project → Enhanced update mode
   - If not exists → Standard initialization mode

2. **Knowledge extraction** (when auto-detected):
   ```
   ✓ Detected initialized project - activating enhanced update mode
   ✓ Analyzing git history (last 90 days)...
     - Found 15 architectural decisions
     - Detected 3 workflow patterns
   ✓ Analyzing session logs...
     - Found 8 learning entries
   ✓ Analyzing memory files...
     - Found 12 accumulated insights
   ✓ Knowledge extraction complete - building enhanced prompt
   ```

3. **Enhanced prompt generation**:
   - Combines git insights, session logs, and memory knowledge
   - Passes to Agentic Coder Optimizer agent
   - Agent intelligently merges into CLAUDE.md

## Knowledge Sources

### 1. Git History Analysis (`extract_from_git`)

**Extracts from commit messages and file stats:**
- **Architectural decisions**: "Added error handling pattern", "Migrated to async"
- **Tech stack changes**: New dependencies, framework migrations
- **Workflow patterns**: Build commands, test patterns, automation
- **Hot files**: Frequently modified files (indicates importance)

**Example output:**
```python
{
    "available": True,
    "architectural_decisions": [
        "error handling pattern",
        "async architecture",
        "service layer"
    ],
    "tech_stack_changes": [
        "pydantic",
        "fastapi",
        "pytest"
    ],
    "workflow_patterns": [
        "automated testing with pytest",
        "CI/CD deployment pipeline"
    ],
    "hot_files": [
        {"path": "src/main.py", "modifications": 45},
        {"path": "src/services/core.py", "modifications": 32}
    ]
}
```

### 2. Session Log Analysis (`extract_from_logs`)

**Parses `.claude-mpm/responses/*.json` for:**
- **PM summaries**: Completed work descriptions
- **Task arrays**: What was built/implemented
- **Stop events**: Context from session endings

**Example output:**
```python
{
    "available": True,
    "learnings": [
        {
            "source": "pm_summary",
            "timestamp": "2025-12-13_15-30",
            "content": "Implemented user authentication with JWT tokens"
        }
    ],
    "completed_tasks": [
        "Create login endpoint",
        "Add password hashing",
        "Implement token refresh"
    ],
    "common_patterns": [
        "authentication",
        "testing",
        "validation"
    ]
}
```

### 3. Memory File Analysis (`extract_from_memory`)

**Parses `.claude-mpm/memories/*.md` for:**
- **Project Architecture**: Structural patterns from agent memories
- **Implementation Guidelines**: Best practices learned by agents
- **Common Mistakes**: Pitfalls to avoid
- **Technical Context**: Current project-specific knowledge

**Example output:**
```python
{
    "available": True,
    "architectural_knowledge": [
        "[engineer] Service-oriented architecture with DI",
        "[engineer] Repository pattern for data access"
    ],
    "implementation_guidelines": [
        "[engineer] Use type hints for all functions",
        "[qa] Maintain 90%+ test coverage"
    ],
    "common_mistakes": [
        "[engineer] Avoid mutable default arguments",
        "[security] Never log secrets or credentials"
    ],
    "technical_context": [
        "[engineer] Using pydantic v2 for validation",
        "[ops] Deployment via Docker containers"
    ]
}
```

## Enhanced Prompt Structure

The `build_enhanced_update_prompt` creates a comprehensive prompt:

```markdown
ENHANCED UPDATE of existing CLAUDE.md documentation with extracted project knowledge.

## Extracted Project Knowledge

### From Git History (last 90 days):

**Architectural Patterns Detected:**
- error handling pattern
- async architecture

**Tech Stack Changes:**
- pydantic
- fastapi

**Common Workflows:**
- automated testing with pytest

**Hot Files (frequently modified):**
- src/main.py (45 changes)

### From Session Logs:

**Recent Learnings from PM Summaries:**
- [pm_summary] Implemented user authentication with JWT tokens

**Common Task Patterns:**
- authentication, testing, validation

### From Agent Memories:

**Architectural Knowledge:**
- [engineer] Service-oriented architecture with DI

**Implementation Guidelines:**
- [engineer] Use type hints for all functions

## UPDATE Tasks with Knowledge Integration:

1. Review Existing Content
2. Integrate Extracted Knowledge
   - Merge architectural decisions from git history
   - Add tech stack changes to Dependencies sections
   - Update workflow patterns in Development Guidelines
   - Incorporate session learnings
   - Merge memory insights
   - Highlight hot files as critical components
3. Smart Content Merge
4. Update Priority Organization
5. Refresh Technical Content
6. Update Code Documentation (AST analysis)
7. Final Optimization
```

## Usage Examples

### Standard Update (No .claude-mpm)
```bash
# Project WITHOUT .claude-mpm directory
cd /path/to/uninitialized-project
mpm-init --update-mode

# Uses standard update prompt (no knowledge extraction)
```

### Enhanced Update (Auto-Detected)
```bash
# Project WITH .claude-mpm directory
cd /path/to/initialized-project
mpm-init --update-mode

# AUTO-DETECTS initialized project
# Extracts knowledge from:
#   - Git history (90 days)
#   - Session logs (.claude-mpm/responses/*.json)
#   - Memory files (.claude-mpm/memories/*.md)
# Builds enhanced prompt with all insights
# Delegates to agent for intelligent merge
```

### Force Update with Knowledge Extraction
```bash
# Even on fresh initialization, update mode extracts knowledge
mpm-init --update-mode --force
```

## Implementation Details

### Files Modified

1. **`knowledge_extractor.py`** (NEW)
   - `ProjectKnowledgeExtractor` class
   - Methods: `extract_from_git()`, `extract_from_logs()`, `extract_from_memory()`
   - Helper methods for parsing commit messages, JSON logs, markdown sections

2. **`prompts.py`** (UPDATED)
   - Added `build_enhanced_update_prompt()` function
   - Combines doc analysis + extracted knowledge → comprehensive prompt

3. **`core.py`** (UPDATED)
   - Added `_is_initialized()` method to detect `.claude-mpm/`
   - Updated `_build_update_prompt()` to auto-detect and extract knowledge
   - Added console output for extraction progress

### Key Design Decisions

1. **Auto-detection over flags**:
   - No new CLI flag needed
   - Presence of `.claude-mpm/` triggers enhanced mode
   - Transparent upgrade path for existing projects

2. **Multiple knowledge sources**:
   - Git = long-term patterns and decisions
   - Logs = recent work and learnings
   - Memories = agent-accumulated wisdom

3. **Non-blocking extraction**:
   - Each source extraction is independent
   - Failures don't break the update process
   - Missing sources gracefully degrade

4. **Token-efficient output**:
   - Limits on number of items extracted (top 10-15)
   - Truncates long content (200 chars max)
   - Focuses on high-signal insights

## Testing

### Manual Testing Steps

1. **Create test project**:
   ```bash
   mkdir test-enhanced-init
   cd test-enhanced-init
   git init
   ```

2. **Run standard init**:
   ```bash
   mpm-init
   # Should create .claude-mpm directory
   ```

3. **Make some commits**:
   ```bash
   git add .
   git commit -m "feat: added authentication pattern"
   git commit -m "refactor: migrated to async architecture"
   ```

4. **Add memory content** (optional):
   ```bash
   echo "## Project Architecture\n- Service-oriented design" > .claude-mpm/memories/engineer_memories.md
   ```

5. **Run update mode**:
   ```bash
   mpm-init --update-mode
   ```

6. **Verify output**:
   ```
   ✓ Detected initialized project - activating enhanced update mode
   ✓ Analyzing git history (last 90 days)...
     - Found 2 architectural decisions
     - Detected 1 workflow patterns
   ✓ Analyzing session logs...
     - Found 0 learning entries
   ✓ Analyzing memory files...
     - Found 1 accumulated insights
   ✓ Knowledge extraction complete - building enhanced prompt
   ```

### Automated Tests

See `tests/test_knowledge_extractor.py` for unit tests:
- `test_extract_from_git_no_repo()` - Handles non-git projects
- `test_extract_from_logs_no_directory()` - Handles missing logs
- `test_extract_from_memory_no_directory()` - Handles missing memories
- `test_parse_memory_sections()` - Parses markdown sections
- `test_extract_memory_items()` - Extracts bullet points

## Future Enhancements

1. **Configurable extraction depth**:
   - CLI flag for git history days: `--knowledge-days 30`
   - Limit session log count: `--max-logs 20`

2. **Selective source extraction**:
   - `--extract-git-only` - Skip logs and memories
   - `--extract-recent-only` - Focus on last 7 days

3. **Knowledge export**:
   - `--export-knowledge report.json` - Save extraction results
   - Useful for debugging and manual review

4. **Smart filtering**:
   - Filter out noise commits (typo fixes, formatting)
   - Detect and group related work streams
   - Prioritize by recency and frequency

## Troubleshooting

### "No architectural decisions found"

**Cause**: Commit messages don't match extraction patterns

**Solution**: Ensure commit messages include keywords like:
- "add/added X pattern"
- "refactor to X"
- "migrate to X"
- "implement X architecture"

### "Session logs not found"

**Cause**: No session logs in `.claude-mpm/responses/`

**Solution**: This is normal for new projects. Session logs accumulate over time as you use `claude-mpm run`.

### "Memory files empty"

**Cause**: Agents haven't accumulated knowledge yet

**Solution**: Memory files are created and populated automatically as agents work. Give it time or manually add content.

## Best Practices

1. **Run update mode regularly**:
   - Weekly or after major feature work
   - Keeps CLAUDE.md in sync with project evolution

2. **Write descriptive commit messages**:
   - Include "why" not just "what"
   - Use architectural keywords for better extraction

3. **Review agent suggestions**:
   - Knowledge extraction is input, not gospel
   - Agent may suggest merges - review before accepting

4. **Supplement with manual edits**:
   - Add project-specific context manually
   - Update priority markers (🔴🟡🟢⚪)

## Conclusion

The enhanced `/mpm-init` update mode transforms CLAUDE.md from a static document into a **living reflection of your project's evolution**. By automatically extracting knowledge from git, logs, and memories, it ensures documentation stays current with minimal manual effort.

**Key Benefits**:
- ✓ Auto-detection (no new flags to remember)
- ✓ Multi-source knowledge synthesis
- ✓ Intelligent agent-driven merging
- ✓ Preserves custom content
- ✓ Transparent upgrade path

**Result**: CLAUDE.md becomes a continuously-updated, knowledge-enriched guide that reflects actual project patterns and decisions.
