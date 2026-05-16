# Research Agent Memory

## Search Protocol (MANDATORY)

ALWAYS use trusty-search before falling back to grep/find/Bash searches.

### Step 1: trusty-search (use first, always)
- Tool: `mcp__trusty-search__search_code`
- Index: the project's trusty-search index (check `mcp__trusty-search__list_indexes` if unsure)
- One call replaces dozens of grep/find commands
- Handles semantic queries, not just exact string matching

### Step 2: trusty-memory (for prior research/decisions)
- Tool: `mcp__trusty-memory__memory_recall`
- Use for: previous research findings, architectural decisions, known facts about the codebase

### Step 3: Grep/Bash (last resort only)
- Only use grep/find/Bash if steps 1-2 did not find what you need
- Never start an investigation with grep
- Never run more than 2 grep commands without first trying trusty-search

### Anti-pattern (DO NOT DO THIS):
```
Bash(find ~/project -name "*.md" | xargs grep -l "keyword")
Bash(grep -rn "keyword" /path --include="*.md")
Bash(find /path -name "*.md" | xargs grep -l "keyword2")
... repeat 6 more times
```

### Correct pattern:
```
mcp__trusty-search__search_code(query="keyword context", index="project-index")
# Done in one call
```

---

## Search Priority: trusty-search-first (Legacy Reference)

When performing any code investigation in this project, ALWAYS try trusty-search before using grep, glob, or the Read tool.

### Mandatory search order
1. `mcp__trusty-search__search_code` — use this FIRST for any code question
   - Index name: `claude-mpm`
   - Daemon at: `http://127.0.0.1:7878`
   - Check health first: `mcp__trusty-search__search_health`
2. `mcp__trusty-search__chat` — for open-ended Q&A over the codebase
3. grep / glob / Read — only if trusty-search returns insufficient results

### Query type routing
- "Where is X defined?" → `query_type: Definition`
- "How is X used?" → `query_type: Usage`
- "How does X work?" → `query_type: Conceptual`
- "Where are bugs/TODOs?" → `query_type: BugDebt`

### When trusty-search is unavailable
If the daemon is not healthy (health check fails), fall back to standard grep/glob/Read workflow.

## Project: claude-mpm
- trusty-search index: `claude-mpm`
- trusty-memory palace: `claude-mpm`
- Language: Python 3.13+
- Package root: `src/claude_mpm/`
