# Shared Prompt Cache Service

## Overview

The Shared Prompt Cache service (`src/claude_mpm/services/memory/cache/shared_prompt_cache.py`) provides a centralized caching mechanism for prompt generation and memory operations, improving performance by reducing redundant computations.

## Purpose

**WHY**: Prompt generation and memory operations can be computationally expensive, especially when dealing with large memory files and complex project contexts. Caching these operations significantly improves response times.

**DESIGN DECISION**: Implements a shared cache that can be used across different services rather than service-specific caches, promoting cache reuse and reducing memory footprint.

## Key Features

1. **Prompt Caching**: Cache generated prompts for reuse
2. **Memory Caching**: Cache processed memory content
3. **TTL Management**: Automatic cache expiration
4. **LRU Eviction**: Least Recently Used eviction policy
5. **Invalidation**: Smart cache invalidation on updates

## API Reference

### SharedPromptCache Class

```python
from claude_mpm.services.memory.cache.shared_prompt_cache import SharedPromptCache

# Initialize cache
cache = SharedPromptCache(
    max_size=1000,
    ttl_seconds=3600
)

# Cache a prompt
cache.set_prompt(
    key="engineer_context_v1",
    prompt=generated_prompt,
    metadata={"agent": "engineer", "version": "1.0"}
)

# Retrieve cached prompt
cached = cache.get_prompt("engineer_context_v1")
if cached:
    prompt = cached["prompt"]
    metadata = cached["metadata"]

# Invalidate related caches
cache.invalidate_pattern("engineer_*")
```

### Key Methods

#### `set_prompt(key, prompt, metadata=None, ttl=None)`
Caches a generated prompt with optional metadata.

**Parameters:**
- `key`: Unique cache key
- `prompt`: Prompt content to cache
- `metadata`: Optional metadata about the prompt
- `ttl`: Optional TTL override (seconds)

#### `get_prompt(key)`
Retrieves a cached prompt if available and not expired.

**Parameters:**
- `key`: Cache key to retrieve

**Returns:** Dictionary with prompt and metadata, or None if not found

#### `invalidate(key)`
Invalidates a specific cache entry.

**Parameters:**
- `key`: Cache key to invalidate

#### `invalidate_pattern(pattern)`
Invalidates all cache entries matching a pattern.

**Parameters:**
- `pattern`: Glob pattern for matching keys

#### `get_stats()`
Returns cache statistics and performance metrics.

**Returns:** Dictionary with hit rate, size, evictions, etc.

## Caching Strategies

### Key Generation

```python
# Agent-specific key
key = f"{agent_id}_{context_hash}_{version}"

# Project-specific key
key = f"project_{project_id}_{memory_hash}"

# Time-based key for temporal caching
key = f"{operation}_{date}_{hour}"
```

### Cache Hierarchy

1. **L1 Cache**: In-memory for hot data (< 100ms)
2. **L2 Cache**: Disk-based for warm data (< 500ms)
3. **No Cache**: Regenerate for cold data

### Invalidation Strategies

**Time-based**:
- Default TTL: 1 hour for prompts
- Extended TTL: 24 hours for stable content
- Short TTL: 5 minutes for dynamic content

**Event-based**:
- On memory update: Invalidate agent caches
- On configuration change: Clear all caches
- On project change: Invalidate project caches

## Usage Examples

### Basic Prompt Caching

```python
# Generate expensive prompt
def generate_agent_prompt(agent_id, context):
    cache_key = f"{agent_id}_{hash(str(context))}"
    
    # Check cache first
    cached = cache.get_prompt(cache_key)
    if cached:
        return cached["prompt"]
    
    # Generate if not cached
    prompt = expensive_prompt_generation(agent_id, context)
    
    # Cache for future use
    cache.set_prompt(cache_key, prompt, ttl=3600)
    
    return prompt
```

### Memory Operation Caching

```python
# Cache processed memories
def get_processed_memory(agent_id):
    cache_key = f"memory_{agent_id}_processed"
    
    cached = cache.get_prompt(cache_key)
    if cached:
        return cached["prompt"]
    
    # Process memory
    raw_memory = load_memory(agent_id)
    processed = process_memory(raw_memory)
    
    # Cache with metadata
    cache.set_prompt(
        cache_key,
        processed,
        metadata={
            "agent": agent_id,
            "processed_at": datetime.now(),
            "size": len(processed)
        }
    )
    
    return processed
```

### Pattern-based Invalidation

```python
# Invalidate all engineer-related caches
cache.invalidate_pattern("engineer_*")
cache.invalidate_pattern("*_engineer_*")

# Invalidate project-specific caches
cache.invalidate_pattern(f"project_{project_id}_*")

# Clear all temporary caches
cache.invalidate_pattern("temp_*")
```

## Performance Optimization

### Cache Warming

```python
# Pre-populate cache on startup
def warm_cache():
    for agent_id in get_all_agents():
        context = get_default_context()
        generate_agent_prompt(agent_id, context)
```

### Batch Operations

```python
# Cache multiple items efficiently
def batch_cache_prompts(prompts):
    with cache.batch():
        for key, prompt in prompts.items():
            cache.set_prompt(key, prompt)
```

### Memory Management

```python
# Monitor cache size
stats = cache.get_stats()
if stats["memory_usage_mb"] > 100:
    cache.evict_oldest(count=100)
```

## Configuration

```yaml
cache:
  shared_prompt:
    enabled: true
    max_size: 1000
    max_memory_mb: 100
    default_ttl: 3600
    eviction_policy: "lru"
    persistence:
      enabled: false
      path: ".cache/prompts"
```

## Monitoring

### Key Metrics

- **Hit Rate**: Percentage of successful cache hits
- **Miss Rate**: Percentage of cache misses
- **Eviction Rate**: Frequency of cache evictions
- **Memory Usage**: Current memory consumption
- **Entry Count**: Number of cached items

### Performance Tracking

```python
stats = cache.get_stats()
print(f"Hit Rate: {stats['hit_rate']:.2%}")
print(f"Memory Usage: {stats['memory_usage_mb']}MB")
print(f"Total Entries: {stats['entry_count']}")
print(f"Evictions: {stats['eviction_count']}")
```

## Best Practices

1. **Consistent Keys**: Use consistent key generation strategies
2. **Appropriate TTLs**: Set TTLs based on data volatility
3. **Monitor Hit Rates**: Aim for >80% hit rate
4. **Size Limits**: Set appropriate size limits
5. **Invalidation**: Implement proper invalidation logic

## Error Handling

- **Cache Misses**: Gracefully handle and regenerate
- **Corruption**: Detect and clear corrupted entries
- **Memory Limits**: Handle out-of-memory conditions
- **Serialization**: Handle serialization errors

## Testing

Unit tests:
- `tests/services/test_shared_prompt_cache.py`

Performance tests:
- `tests/performance/test_cache_performance.py`

## Related Services

- [Simple Cache](cache-simple.md) - Basic caching implementation
- [Memory Builder](builder.md) - Generates content to cache
- [Memory Router](router.md) - Uses cache for routing decisions