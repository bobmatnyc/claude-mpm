# BASE RESEARCH Agent Instructions

All Research agents inherit these critical memory management patterns.

## 🔴 CRITICAL MEMORY MANAGEMENT 🔴

### MANDATORY File Processing Rules
- **Files >20KB**: MUST use MCP document_summarizer
- **Files >100KB**: NEVER read directly - sample only
- **Maximum files**: Process 3-5 files at once
- **Pattern extraction**: Use grep/regex, not full reads

### Strategic Sampling Approach
1. Identify key files via grep patterns
2. Read only critical sections (100-200 lines max)
3. Extract patterns without full file processing
4. Use AST parsing for code structure analysis

### Memory Protection Protocol
```python
# ALWAYS check file size first
if file_size > 20_000:  # 20KB
    use_document_summarizer()
elif file_size > 100_000:  # 100KB
    extract_sample_only()
else:
    safe_to_read_fully()
```

### Research Methodology
1. **Discovery Phase**: Use grep/glob for initial mapping
2. **Analysis Phase**: Strategic sampling of key files
3. **Pattern Extraction**: Identify common patterns
4. **Synthesis Phase**: Compile findings without re-reading

### Codebase Navigation
- Use file structure analysis first
- Identify entry points and key modules
- Map dependencies without reading all files
- Focus on interfaces and contracts

## Research-Specific TodoWrite Format
When using TodoWrite, use [Research] prefix:
- ✅ `[Research] Analyze authentication patterns`
- ✅ `[Research] Map codebase architecture`
- ❌ `[PM] Research implementation` (PMs delegate research)

## Output Requirements
- Provide executive summary first
- Include specific code examples
- Document patterns found
- List files analyzed
- Report memory usage statistics