# Simple Cache Service

## Overview

The Simple Cache service (`src/claude_mpm/services/memory/cache/simple_cache.py`) provides a lightweight, general-purpose caching solution for various operations within the Claude MPM system. It offers a simpler alternative to the Shared Prompt Cache for basic caching needs.

## Purpose

**WHY**: Not all caching needs require the complexity of the Shared Prompt Cache. The Simple Cache provides a straightforward key-value store for temporary data, configuration caching, and other simple use cases.

**DESIGN DECISION**: Implements a minimal API with no dependencies, making it suitable for use in any part of the system without introducing complexity or coupling.

## Key Features

1. **Key-Value Storage**: Simple get/set operations
2. **TTL Support**: Optional time-to-live for entries
3. **Memory Efficient**: Minimal overhead per entry
4. **Thread-Safe**: Safe for concurrent access
5. **No Dependencies**: Pure Python implementation

## API Reference

### SimpleCache Class

```python
from claude_mpm.services.memory.cache.simple_cache import SimpleCache

# Initialize cache
cache = SimpleCache(max_size=500)

# Store value
cache.set("user_preference", {"theme": "dark"})

# Retrieve value
value = cache.get("user_preference")
# Returns: {"theme": "dark"}

# Store with TTL
cache.set("temp_token", "abc123", ttl=300)  # 5 minutes

# Check existence
if cache.has("user_preference"):
    process_preference(cache.get("user_preference"))

# Clear cache
cache.clear()
```

### Key Methods

#### `set(key, value, ttl=None)`
Stores a value in the cache.

**Parameters:**
- `key`: Cache key (string)
- `value`: Value to store (any serializable type)
- `ttl`: Optional time-to-live in seconds

#### `get(key, default=None)`
Retrieves a value from the cache.

**Parameters:**
- `key`: Cache key to retrieve
- `default`: Default value if key not found

**Returns:** Cached value or default

#### `has(key)`
Checks if a key exists in the cache.

**Parameters:**
- `key`: Cache key to check

**Returns:** Boolean indicating existence

#### `delete(key)`
Removes a key from the cache.

**Parameters:**
- `key`: Cache key to remove

#### `clear()`
Removes all entries from the cache.

#### `size()`
Returns the current number of cached items.

**Returns:** Integer count of items

## Use Cases

### Configuration Caching

```python
# Cache configuration to avoid repeated file reads
def get_config():
    if cache.has("app_config"):
        return cache.get("app_config")
    
    config = load_config_from_file()
    cache.set("app_config", config, ttl=600)  # 10 minutes
    return config
```

### Computation Results

```python
# Cache expensive computation results
def calculate_metrics(data):
    cache_key = f"metrics_{hash(str(data))}"
    
    result = cache.get(cache_key)
    if result is not None:
        return result
    
    result = expensive_calculation(data)
    cache.set(cache_key, result, ttl=1800)  # 30 minutes
    
    return result
```

### Session Data

```python
# Store temporary session data
def store_session(session_id, data):
    cache.set(f"session_{session_id}", data, ttl=3600)  # 1 hour

def get_session(session_id):
    return cache.get(f"session_{session_id}", default={})

def end_session(session_id):
    cache.delete(f"session_{session_id}")
```

### Rate Limiting

```python
# Simple rate limiting implementation
def check_rate_limit(user_id, limit=10):
    key = f"rate_{user_id}"
    count = cache.get(key, default=0)
    
    if count >= limit:
        return False
    
    cache.set(key, count + 1, ttl=60)  # Reset every minute
    return True
```

## Implementation Details

### Storage Structure

```python
# Internal storage format
cache_entry = {
    "value": stored_value,
    "expires_at": timestamp or None,
    "created_at": timestamp,
    "access_count": 0
}
```

### Eviction Policy

When cache reaches max_size:
1. Remove expired entries first
2. Remove least recently used (LRU)
3. Reject new entries if full and no eviction possible

### Thread Safety

```python
# All operations are thread-safe
import threading

cache = SimpleCache()

def worker(thread_id):
    for i in range(100):
        cache.set(f"thread_{thread_id}_{i}", i)
        value = cache.get(f"thread_{thread_id}_{i}")

threads = [threading.Thread(target=worker, args=(i,)) 
           for i in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

## Performance Characteristics

### Time Complexity
- **Get**: O(1) average case
- **Set**: O(1) average case
- **Delete**: O(1) average case
- **Has**: O(1) average case
- **Clear**: O(n) where n is number of entries

### Space Complexity
- **Per Entry**: ~200 bytes overhead
- **Total**: O(n) where n is max_size

### Benchmarks

```python
# Typical performance (1000 operations)
# Set: ~0.001ms per operation
# Get: ~0.0005ms per operation
# Has: ~0.0003ms per operation
```

## Configuration

```yaml
cache:
  simple:
    enabled: true
    max_size: 500
    default_ttl: null  # No default TTL
    cleanup_interval: 60  # Cleanup expired entries every 60 seconds
```

## Comparison with Shared Prompt Cache

| Feature | Simple Cache | Shared Prompt Cache |
|---------|-------------|-------------------|
| Use Case | General purpose | Prompt/memory specific |
| Complexity | Low | Medium |
| Features | Basic | Advanced |
| Memory Usage | Low | Medium |
| Performance | Very Fast | Fast |
| Persistence | No | Optional |
| Statistics | Basic | Detailed |

## Best Practices

1. **Appropriate TTLs**: Set TTLs based on data freshness requirements
2. **Key Naming**: Use consistent, descriptive key patterns
3. **Size Limits**: Set reasonable max_size to prevent memory issues
4. **Error Handling**: Always provide defaults for cache misses
5. **Cleanup**: Periodically clear expired entries

## Error Handling

```python
# Safe cache usage pattern
def safe_cache_get(key):
    try:
        return cache.get(key)
    except Exception as e:
        logger.warning(f"Cache error: {e}")
        return None

def safe_cache_set(key, value):
    try:
        cache.set(key, value)
        return True
    except Exception as e:
        logger.warning(f"Cache error: {e}")
        return False
```

## Testing

Unit tests:
- `tests/services/test_simple_cache.py`

Integration tests:
- `tests/integration/test_cache_integration.py`

## Related Services

- [Shared Prompt Cache](cache-shared.md) - Advanced caching for prompts
- [Memory Optimizer](optimizer.md) - Uses cache for optimization
- [Memory Router](router.md) - Caches routing decisions