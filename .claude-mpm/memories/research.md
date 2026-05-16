# Research Agent Memories

## Search Protocol (MANDATORY)

Use this exact priority order — only fall through if the higher-priority tool is unavailable:

### Tier 1: trusty-search (use first if available)
- Tool: `mcp__trusty-search__search_code`
- Check availability: `mcp__trusty-search__search_health` or `mcp__trusty-search__list_indexes`
- One call replaces dozens of grep/find commands

### Tier 2: mcp-vector-search (fallback if trusty-search unavailable)
- Tool: `mcp__mcp-vector-search__search_code`
- Use only when trusty-search MCP server is not running/configured

### Tier 3: grep / ripgrep (last resort only)
- Use `grep -r`, `rg`, or `find | xargs grep` ONLY when neither Tier 1 nor Tier 2 is available
- Never run more than 2 grep commands — if you need more, trusty-search would have been faster
- Never start an investigation with grep when an MCP search tool is available

### Anti-pattern (NEVER DO THIS when MCP search is available):
```bash
find ~/project -name "*.md" | xargs grep -l "keyword"
grep -rn "keyword" /path --include="*.md"
find /path -name "*.md" | xargs grep -l "keyword2"
# ...repeat 5+ more times = VIOLATION
```

### Correct pattern:
```
mcp__trusty-search__search_code(query="keyword context", index="project-index")
# Done in one call
```
