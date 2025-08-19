# Memory Deduplication System

## Overview

Claude MPM v4.x includes an intelligent NLP-based memory deduplication system that automatically detects and removes duplicate or highly similar memory items. This prevents memory bloat and keeps agent memories clean and relevant.

## Features

### 1. Automatic Deduplication
- **Real-time deduplication**: When adding new memories, the system automatically checks for similar existing items
- **Similarity threshold**: Items with >80% similarity are considered duplicates
- **Recency preference**: When duplicates are found, the newer item replaces the older one

### 2. NLP-based Similarity Detection
- **Fuzzy matching**: Uses difflib's SequenceMatcher for lightweight NLP similarity
- **Case-insensitive**: Matches items regardless of capitalization
- **Substring detection**: Identifies when one item is contained within another
- **No heavy dependencies**: Avoids ML libraries for fast, lightweight operation

### 3. Deduplication Strategies
- **Exact match prevention**: Identical items are always deduplicated
- **Similar item replacement**: Items with >80% similarity trigger replacement
- **Section-aware**: Deduplication works within individual sections
- **Preserves diversity**: Items below similarity threshold are kept

## How It Works

### Similarity Calculation

The system uses a multi-faceted approach to calculate similarity:

```python
# Normalized comparison (case-insensitive, trimmed)
similarity = SequenceMatcher(None, str1.lower().strip(), str2.lower().strip()).ratio()

# Substring boost for contained items
if str1 in str2 or str2 in str1:
    similarity = max(similarity, 0.85)
```

### Deduplication Process

1. **New item added**: When `update_agent_memory()` is called
2. **Similarity check**: Compare with all existing items in the section
3. **Duplicate detection**: If similarity > 0.8, mark as duplicate
4. **Replacement**: Remove old item, add new item
5. **Size enforcement**: Apply section limits after deduplication

## Usage

### Automatic Deduplication

Deduplication happens automatically when using the memory manager:

```python
from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager

manager = AgentMemoryManager()

# First addition
manager.update_agent_memory(
    "engineer",
    "Coding Patterns",
    "Always use TypeScript for type safety"
)

# Similar item - will replace the first one
manager.update_agent_memory(
    "engineer",
    "Coding Patterns", 
    "Always use TypeScript for type safety in components"
)
# Result: Only the second, more detailed version is kept
```

### Manual Deduplication

Use the deduplication utility to clean existing memory files:

```bash
# Deduplicate all agent memories in current project
python scripts/deduplicate_memories.py

# Deduplicate specific agent
python scripts/deduplicate_memories.py engineer

# Dry run to see what would be removed
python scripts/deduplicate_memories.py --dry-run --verbose

# Deduplicate user-level memories
python scripts/deduplicate_memories.py --user-memories
```

### Programmatic Deduplication

```python
from claude_mpm.services.agents.memory.content_manager import MemoryContentManager

content_manager = MemoryContentManager(memory_limits)

# Deduplicate a specific section
updated_content, removed_count = content_manager.deduplicate_section(
    content, 
    "Implementation Guidelines"
)

# Check similarity between two items
similarity = content_manager._calculate_similarity(
    "Use async/await for database operations",
    "Use async/await for all database operations"
)
# Returns: 0.878 (87.8% similar - would be deduplicated)
```

## Examples

### Example 1: Exact Duplicate
```python
# First addition
"Always validate user input before processing"

# Second addition (exact duplicate)
"Always validate user input before processing"

# Result: Only one instance kept
```

### Example 2: Case Variation
```python
# First addition
"Use Redis for caching"

# Second addition (different case)
"USE REDIS FOR CACHING"

# Result: Newer version kept (similarity = 1.0)
```

### Example 3: Similar But Extended
```python
# First addition
"Handle errors with try-catch blocks"

# Second addition (extended version)
"Handle errors with try-catch blocks and proper logging"

# Result: Extended version kept (similarity > 0.8)
```

### Example 4: Different Items
```python
# First addition
"Use async/await for database operations"

# Second addition (different topic)
"Configure logging with appropriate levels"

# Result: Both kept (similarity < 0.5)
```

## Configuration

### Similarity Threshold

The default threshold is 0.8 (80% similarity). This is currently hardcoded but provides a good balance between:
- Catching actual duplicates
- Preserving meaningful variations

### Memory Limits

Deduplication respects existing memory limits:
- `max_items_per_section`: After deduplication, section limits still apply
- `max_file_size_kb`: File size limits are enforced after deduplication

## Performance

### Efficiency
- **O(n²) comparison**: Within each section for new items
- **Lightweight**: Uses Python's built-in difflib, no external ML dependencies
- **Fast**: Typical deduplication takes <100ms even for large memory files

### Memory Impact
- **Reduced file size**: Removes redundant information
- **Better token usage**: Cleaner memories mean more efficient LLM context
- **Improved relevance**: Agents work with deduplicated, focused memories

## Testing

Run the deduplication test suite:

```bash
# Run comprehensive tests
PYTHONPATH=src python tests/test_memory_deduplication.py

# Test specific functionality
python tests/test_memory_deduplication.py::test_similarity_calculation
```

## Troubleshooting

### Common Issues

1. **Items not being deduplicated**
   - Check similarity threshold (must be >0.8)
   - Verify items are in the same section
   - Check for special characters affecting similarity

2. **Too aggressive deduplication**
   - Items with >80% similarity are considered duplicates
   - Consider adding more specific details to differentiate items

3. **Performance issues**
   - Large sections (>100 items) may be slow
   - Consider section size limits in configuration

## Future Enhancements

Potential improvements for future versions:

1. **Configurable threshold**: Allow per-agent or per-section thresholds
2. **Semantic similarity**: Use embeddings for deeper semantic matching
3. **Batch deduplication**: Optimize for bulk operations
4. **Learning from feedback**: Adjust thresholds based on user corrections
5. **Cross-section deduplication**: Detect duplicates across different sections

## API Reference

### MemoryContentManager

```python
class MemoryContentManager:
    def add_item_to_section(self, content: str, section: str, new_item: str) -> str:
        """Add item with automatic deduplication."""
        
    def deduplicate_section(self, content: str, section: str) -> Tuple[str, int]:
        """Deduplicate all items in a section."""
        
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity score between two strings."""
```

### AgentMemoryManager

```python
class AgentMemoryManager:
    def update_agent_memory(self, agent_id: str, section: str, new_item: str) -> bool:
        """Update memory with automatic deduplication."""
        
    def add_learning(self, agent_id: str, learning_type: str, content: str) -> bool:
        """Add structured learning with deduplication."""
```

## Summary

The NLP-based memory deduplication system ensures that agent memories remain:
- **Clean**: No duplicate or redundant information
- **Relevant**: Most recent learnings are preserved
- **Efficient**: Optimal use of memory space and LLM context
- **Maintainable**: Automatic cleanup without manual intervention

This feature is essential for long-running projects where agents accumulate memories over time, preventing memory bloat while preserving valuable learnings.