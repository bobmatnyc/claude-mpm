# Memory Optimization Guidelines

## Overview

This document describes memory optimization strategies implemented in Claude MPM to prevent memory accumulation issues, particularly when processing large documentation or codebases.

## The Problem

Claude Code's process retains all file contents read during execution, leading to memory accumulation that can exceed 24GB when processing large documentation sets. This is because:

1. **File Content Retention**: Every file read using the Read tool is retained in memory
2. **No Garbage Collection**: There's no way to programmatically purge this memory
3. **Aggressive Reading Patterns**: Research agents were instructed to "ALWAYS read 5-10 actual files" and "Read COMPLETE files"
4. **Exhaustive Analysis**: Instructions mandated comprehensive analysis without limits

## The Solution

We've implemented memory-efficient practices through instruction modifications that change agent behavior without requiring code changes.

### 1. Memory-Efficient Instructions

All agent instructions now include memory management guidelines:

```markdown
<!-- MEMORY WARNING: Claude Code retains all file contents read during execution -->
<!-- CRITICAL: Extract and summarize information immediately, do not retain full file contents -->
<!-- PATTERN: Read → Extract → Summarize → Discard → Continue -->
```

### 2. Modified Research Agent Behavior

The Research agent template has been updated from memory-intensive to memory-efficient practices:

**OLD (Memory-Intensive)**:
- "ALWAYS read 5-10 actual files"
- "Read COMPLETE files"
- "NEVER conclude based on grep results alone"
- "Examine ALL search results"

**NEW (Memory-Efficient)**:
- "Extract key patterns from 3-5 representative files maximum"
- "Use grep with context (-A 10 -B 10) instead of full file reading"
- "Sample search results intelligently - first 10-20 matches are sufficient"
- "Process files sequentially to prevent memory accumulation"

### 3. File Processing Guidelines

#### Size Limits
- Skip files >1MB unless absolutely critical
- Sample large files (first 500 lines only)
- Check file size before reading

#### Processing Pattern
1. Check file size first (skip if >1MB)
2. Use grep to find relevant sections
3. Read only those sections
4. Extract key information immediately
5. Summarize findings in 2-3 sentences
6. DISCARD original content from working memory
7. Move to next file

#### What to Retain vs Discard

**DO NOT RETAIN**:
- Full file contents after analysis
- Verbose documentation text
- Redundant information across files
- Implementation details not relevant to the task
- Comments and docstrings after extracting their meaning

**ALWAYS RETAIN** (Summary Form Only):
- Key architectural decisions (1-2 sentences)
- Critical configuration values (as a list)
- Important patterns and conventions (bullet points)
- Specific answers to user questions (concise)
- Summary of findings (not raw content)

### 4. PM Delegation Guidelines

The PM now includes memory-conscious delegation practices:

**GOOD Delegation (Memory-Conscious)**:
- "Research: Find and summarize the authentication pattern used in the auth module"
- "Research: Extract the key API endpoints from the routes directory (max 10 files)"
- "Documentation: Create a 1-page summary of the database schema"

**BAD Delegation (Memory-Intensive)**:
- "Research: Read and analyze the entire codebase"
- "Research: Document every function in the project"
- "Documentation: Create comprehensive documentation for all modules"

### 5. Memory Monitoring Tools

#### Test Script
`scripts/test_memory_warning.py` - Comprehensive memory monitoring tool that:
- Tracks memory usage in real-time
- Provides warnings at various thresholds (1GB, 2GB, 5GB)
- Supports continuous monitoring mode
- Generates detailed memory reports
- Logs memory usage for analysis

Usage:
```bash
# Test memory allocations
python scripts/test_memory_warning.py --test

# Continuous monitoring
python scripts/test_memory_warning.py --continuous --interval 2

# Monitor specific process
python scripts/test_memory_warning.py --pid 12345
```

#### Cleanup Command
`claude-mpm cleanup` - Manages conversation history to prevent memory issues:
- Archives old conversations
- Reduces .claude.json file size
- Prevents memory issues with --resume flag
- Provides dry-run mode for safety

Usage:
```bash
# View cleanup options
claude-mpm cleanup --help

# Dry run to see what would be cleaned
claude-mpm cleanup --dry-run

# Clean conversations older than 30 days
claude-mpm cleanup --days 30 --max-size 500KB

# Force cleanup without confirmation
claude-mpm cleanup --force
```

## Implementation Files

### Core Memory Management
- `/src/claude_mpm/agents/memory_efficient_instructions.md` - Reusable memory-efficient guidelines
- `/src/claude_mpm/agents/BASE_PM.md` - Added memory-efficient documentation processing section
- `/src/claude_mpm/agents/INSTRUCTIONS.md` - Added memory-conscious delegation section

### Agent Templates
- `/src/claude_mpm/agents/templates/research.json` - Updated with memory-efficient practices
- Original backed up to `research_original.json.bak`

### Tools and Commands
- `/scripts/test_memory_warning.py` - Memory monitoring and testing tool
- `/src/claude_mpm/cli/commands/cleanup.py` - Cleanup command implementation

## Best Practices

### For Agent Development

1. **Use Grep Context Instead of Full Files**:
   ```bash
   # Good: Extract relevant context
   grep -A 10 -B 10 "pattern" file.py
   
   # Bad: Read entire file
   cat file.py
   ```

2. **Sample Instead of Exhaustive Reading**:
   ```bash
   # Good: Sample first 10-20 matches
   grep -l "pattern" . | head -20
   
   # Bad: Process all matches
   grep -l "pattern" . | xargs cat
   ```

3. **Sequential Processing**:
   ```python
   # Good: Process one file at a time
   for file in files[:5]:
       content = read(file)
       summary = extract_key_info(content)
       results.append(summary)
       # Content is discarded after extraction
   
   # Bad: Load all files into memory
   all_contents = [read(file) for file in files]
   ```

### For PM Delegation

1. **Specify Scope Limits**: Always include specific boundaries in delegation
2. **Request Summaries**: Ask for condensed findings, not full documentation
3. **Break Large Tasks**: Split into smaller, focused delegations
4. **Sequential Processing**: One documentation task at a time

### For Users

1. **Regular Cleanup**: Run `claude-mpm cleanup` periodically
2. **Monitor Memory**: Use `test_memory_warning.py` during long sessions
3. **Restart If Needed**: If memory exceeds 2GB, consider restarting Claude Code
4. **Use Specific Requests**: Avoid broad analysis requests that require reading many files

## Expected Outcomes

With these optimizations:

1. **Memory usage should stay under 2-3GB** even for large documentation tasks
2. **Quality of analysis maintained** through focused extraction
3. **85% confidence** achieved through strategic sampling instead of exhaustive reading
4. **Clear pattern**: Read → Extract → Summarize → Discard

## Monitoring and Maintenance

### Regular Checks
- Monitor memory usage during agent operations
- Review agent logs for memory warnings
- Run cleanup command when .claude.json exceeds 500KB

### Performance Metrics
- Target: <2GB memory usage for typical operations
- Target: <3GB memory usage for large documentation tasks
- Warning threshold: 5GB (indicates potential issue)
- Critical threshold: 10GB (requires immediate action)

## Future Improvements

Potential enhancements to further optimize memory usage:

1. **Streaming Processing**: Process files in chunks without loading entire content
2. **Automatic Cleanup**: Trigger cleanup when memory threshold is reached
3. **Smart Caching**: Cache only essential patterns, not full content
4. **Progressive Loading**: Load documentation in stages based on need
5. **Memory Profiling**: Built-in profiling for all agent operations

## Conclusion

These memory optimizations ensure Claude MPM can handle large codebases and documentation sets without exhausting system memory. The key principle is: **Extract and summarize immediately, never retain full file contents**.