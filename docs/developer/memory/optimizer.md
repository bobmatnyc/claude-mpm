# Memory Optimizer Service

## Overview

The Memory Optimizer service (`src/claude_mpm/services/memory/optimizer.py`) maintains memory quality and efficiency by deduplicating, consolidating, and optimizing agent memory files. It ensures memories remain relevant, concise, and performant.

## Purpose

**WHY**: Over time, agent memories can accumulate redundant information, grow too large, or contain outdated learnings. The optimizer maintains memory health for optimal agent performance.

**DESIGN DECISION**: Uses rule-based optimization rather than AI-driven compression to maintain predictability and allow manual review of optimization decisions.

## Key Responsibilities

1. **Deduplication**: Remove duplicate or similar memory entries
2. **Consolidation**: Merge related memories into cohesive insights
3. **Size Management**: Keep memory files within optimal size limits
4. **Quality Maintenance**: Remove outdated or low-value memories
5. **Performance Optimization**: Structure memories for fast retrieval

## API Reference

### MemoryOptimizer Class

```python
from claude_mpm.services.memory.optimizer import MemoryOptimizer

# Initialize optimizer
optimizer = MemoryOptimizer(config)

# Optimize specific agent memory
result = optimizer.optimize_agent_memory(
    agent_id="engineer",
    memory_content=current_memory
)
# Returns: {
#     "optimized_content": "...",
#     "removed_entries": 12,
#     "consolidated_entries": 8,
#     "size_reduction": "45%"
# }

# Analyze memory quality
quality = optimizer.analyze_memory_quality(memory_content)
# Returns quality metrics and recommendations
```

### Key Methods

#### `optimize_agent_memory(agent_id, memory_content, options=None)`
Optimizes memory content for a specific agent.

**Parameters:**
- `agent_id`: Target agent identifier
- `memory_content`: Current memory content
- `options`: Optimization options (aggressive, conservative, etc.)

**Returns:** Dictionary with optimized content and statistics

#### `deduplicate_memories(memory_content)`
Removes duplicate and near-duplicate entries.

**Parameters:**
- `memory_content`: Memory content to deduplicate

**Returns:** Deduplicated content with removal statistics

#### `consolidate_memories(memory_content)`
Merges related memories into unified insights.

**Parameters:**
- `memory_content`: Memory content to consolidate

**Returns:** Consolidated content with merge statistics

#### `analyze_memory_quality(memory_content)`
Analyzes memory quality and provides recommendations.

**Parameters:**
- `memory_content`: Memory content to analyze

**Returns:** Quality metrics and improvement suggestions

## Optimization Strategies

### Deduplication Strategy

1. **Exact Match**: Remove identical memory entries
2. **Similarity Detection**: Identify near-duplicates using fuzzy matching
3. **Semantic Grouping**: Group similar concepts
4. **Timestamp Priority**: Keep most recent version of duplicates
5. **Source Tracking**: Maintain provenance information

### Consolidation Rules

**Pattern Consolidation**:
```
Before:
- "Use async/await for API calls"
- "API calls should be asynchronous"
- "Implement async patterns for external calls"

After:
- "Use async/await pattern for all API and external service calls"
```

**Insight Merging**:
```
Before:
- "Cache database queries"
- "Redis improves query performance"
- "Use caching for expensive operations"

After:
- "Implement Redis caching for expensive database queries and operations"
```

### Size Optimization

1. **Remove Verbose Descriptions**: Convert to concise insights
2. **Extract Patterns**: Replace repetitive examples with patterns
3. **Compress Sections**: Merge sparse sections
4. **Archive Old Memories**: Move outdated memories to archive
5. **Prioritize Recent**: Keep recent learnings, archive old ones

## Optimization Profiles

### Conservative Profile
- Minimal changes
- Only exact duplicates removed
- Preserves all unique insights
- Suitable for critical memories

### Balanced Profile (Default)
- Moderate deduplication
- Smart consolidation
- Maintains important details
- Good for regular maintenance

### Aggressive Profile
- Maximum compression
- Aggressive consolidation
- Removes low-value entries
- For size-critical situations

## Quality Metrics

### Memory Health Indicators

```python
health_metrics = {
    "size_kb": 45,           # Current size
    "entry_count": 234,      # Number of entries
    "duplicate_ratio": 0.15, # Duplicate percentage
    "avg_entry_length": 85,  # Average entry size
    "last_optimized": "2024-01-15",
    "quality_score": 0.82    # Overall quality (0-1)
}
```

### Quality Scoring

- **Uniqueness** (0-1): Ratio of unique to total entries
- **Relevance** (0-1): Age-weighted relevance score
- **Conciseness** (0-1): Brevity and clarity measure
- **Organization** (0-1): Structure and categorization quality
- **Coverage** (0-1): Topic coverage completeness

## Optimization Workflow

### Automatic Optimization

```python
# Schedule periodic optimization
scheduler.add_job(
    optimizer.optimize_all_memories,
    trigger="interval",
    days=7
)

# Triggered by size threshold
if memory_size > config.max_memory_size:
    optimizer.optimize_agent_memory(agent_id, memory)
```

### Manual Optimization

```python
# Analyze before optimizing
analysis = optimizer.analyze_memory_quality(memory)
print(f"Quality Score: {analysis['quality_score']}")
print(f"Recommendations: {analysis['recommendations']}")

# Optimize with specific options
options = {
    "profile": "balanced",
    "preserve_recent_days": 30,
    "min_similarity_threshold": 0.8
}
result = optimizer.optimize_agent_memory(
    "engineer", 
    memory,
    options
)
```

## Configuration

```yaml
memory:
  optimization:
    auto_optimize: true
    max_size_kb: 50
    min_entries: 10
    duplicate_threshold: 0.85
    consolidation_threshold: 0.7
    optimization_interval_days: 7
    profile: "balanced"
```

## Best Practices

1. **Regular Maintenance**: Run optimization weekly or bi-weekly
2. **Review Changes**: Audit optimization results periodically
3. **Backup First**: Always backup memories before aggressive optimization
4. **Monitor Quality**: Track quality metrics over time
5. **Custom Rules**: Add domain-specific optimization rules as needed

## Performance Considerations

- **Batch Processing**: Optimize multiple agents together
- **Incremental Updates**: Optimize only changed sections
- **Cache Results**: Cache optimization analysis for reuse
- **Async Processing**: Run optimization in background
- **Memory Limits**: Enforce hard limits on memory sizes

## Error Handling

- **Corruption Prevention**: Validate memory structure before/after
- **Rollback Support**: Keep backup for rollback on errors
- **Partial Optimization**: Continue on section failures
- **Logging**: Comprehensive logging of all changes

## Testing

Unit tests:
- `tests/services/test_memory_optimizer.py`

Integration tests:
- `tests/integration/test_memory_optimization.py`

Performance tests:
- `tests/performance/test_optimizer_performance.py`

## Related Services

- [Memory Builder](builder.md) - Generates initial memories
- [Memory Router](router.md) - Routes new memories
- [Cache Services](cache-shared.md) - Caches optimization results