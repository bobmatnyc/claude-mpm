---
name: tauri-performance
description: Performance optimization for Tauri apps including serialization, batching, caching, lazy loading, and profiling techniques
version: 1.0.0
category: development
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Performance optimization: minimize serialization, batch commands, implement caching, lazy load resources, profile bottlenecks"
    when_to_use: "Optimizing Tauri app performance, reducing IPC overhead, improving responsiveness, or debugging performance issues"
    quick_start: "1. Batch IPC calls 2. Cache frequently accessed data 3. Stream large data 4. Lazy load resources 5. Profile with DevTools"
context_limit: 600
tags:
  - tauri
  - performance
  - optimization
  - profiling
  - caching
requires_tools: []
---

# Tauri Performance Optimization

## IPC Optimization

### Minimize Serialization Overhead

**Problem**: Each IPC call serializes data across the boundary

```rust
// ❌ BAD - multiple IPC calls
#[tauri::command]
async fn get_file_name(path: String) -> Result<String, String> { /* ... */ }

#[tauri::command]
async fn get_file_size(path: String) -> Result<u64, String> { /* ... */ }

// Frontend makes 3 separate calls
const name = await invoke('get_file_name', { path });
const size = await invoke('get_file_size', { path });
const modified = await invoke('get_file_modified', { path });
```

**Solution**: Batch data in single call

```rust
// ✅ GOOD - single IPC call
#[derive(serde::Serialize)]
pub struct FileInfo {
    name: String,
    size: u64,
    modified: u64,
    is_dir: bool,
}

#[tauri::command]
async fn get_file_info(path: String) -> Result<FileInfo, String> {
    let metadata = tokio::fs::metadata(&path)
        .await
        .map_err(|e| e.to_string())?;

    Ok(FileInfo {
        name: Path::new(&path)
            .file_name()
            .unwrap()
            .to_string_lossy()
            .to_string(),
        size: metadata.len(),
        modified: metadata.modified()
            .unwrap()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs(),
        is_dir: metadata.is_dir(),
    })
}

// Frontend makes 1 call
const info = await invoke('get_file_info', { path });
```

### Batch Operations

```rust
// ❌ BAD - N IPC calls
for file in files {
    await invoke('process_file', { file });
}

// ✅ GOOD - 1 IPC call
#[tauri::command]
async fn process_files_batch(files: Vec<String>) -> Result<Vec<ProcessResult>, String> {
    let mut results = Vec::new();

    for file in files {
        let result = process_file_internal(&file).await;
        results.push(result);
    }

    Ok(results)
}

await invoke('process_files_batch', { files });
```

### Stream Large Data

```rust
use futures::stream::{self, StreamExt};

#[tauri::command]
async fn load_large_dataset(
    window: tauri::Window,
) -> Result<(), String> {
    let data = fetch_large_dataset().await?;

    // Stream in chunks instead of single payload
    let chunks: Vec<_> = data.chunks(1000).collect();

    for (index, chunk) in chunks.iter().enumerate() {
        window.emit("data-chunk", serde_json::json!({
            "index": index,
            "data": chunk,
            "total": chunks.len()
        })).map_err(|e| e.to_string())?;

        // Small delay to prevent overwhelming frontend
        tokio::time::sleep(Duration::from_millis(10)).await;
    }

    window.emit("data-complete", ()).map_err(|e| e.to_string())?;

    Ok(())
}
```

**Frontend streaming handler**:
```typescript
let allData: DataItem[] = [];

await listen('data-chunk', (event: { index: number; data: DataItem[]; total: number }) => {
    allData = allData.concat(event.data);
    updateProgress(event.index, event.total);
});

await listen('data-complete', () => {
    renderData(allData);
});

await invoke('load_large_dataset');
```

## Caching Strategies

### In-Memory Cache

```rust
use std::sync::Arc;
use dashmap::DashMap;
use std::time::{SystemTime, Duration};

pub struct CachedValue<T> {
    value: T,
    expires_at: SystemTime,
}

pub struct Cache<T> {
    store: Arc<DashMap<String, CachedValue<T>>>,
    ttl: Duration,
}

impl<T: Clone> Cache<T> {
    pub fn new(ttl_secs: u64) -> Self {
        Self {
            store: Arc::new(DashMap::new()),
            ttl: Duration::from_secs(ttl_secs),
        }
    }

    pub fn get(&self, key: &str) -> Option<T> {
        self.store.get(key).and_then(|entry| {
            if SystemTime::now() < entry.expires_at {
                Some(entry.value.clone())
            } else {
                self.store.remove(key);
                None
            }
        })
    }

    pub fn set(&self, key: String, value: T) {
        self.store.insert(key, CachedValue {
            value,
            expires_at: SystemTime::now() + self.ttl,
        });
    }

    pub fn clear(&self) {
        self.store.clear();
    }
}

// Usage in app state
pub struct AppState {
    file_cache: Cache<String>,
}

#[tauri::command]
async fn read_file_cached(
    path: String,
    state: tauri::State<'_, AppState>,
) -> Result<String, String> {
    // Check cache first
    if let Some(content) = state.file_cache.get(&path) {
        return Ok(content);
    }

    // Cache miss - read from disk
    let content = tokio::fs::read_to_string(&path)
        .await
        .map_err(|e| e.to_string())?;

    // Store in cache
    state.file_cache.set(path, content.clone());

    Ok(content)
}
```

### LRU Cache

```rust
use lru::LruCache;
use std::sync::Arc;
use tokio::sync::Mutex;
use std::num::NonZeroUsize;

pub struct AppState {
    lru_cache: Arc<Mutex<LruCache<String, Vec<u8>>>>,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            lru_cache: Arc::new(Mutex::new(
                LruCache::new(NonZeroUsize::new(100).unwrap())
            )),
        }
    }
}

#[tauri::command]
async fn get_data_with_lru(
    key: String,
    state: tauri::State<'_, AppState>,
) -> Result<Vec<u8>, String> {
    let mut cache = state.lru_cache.lock().await;

    if let Some(data) = cache.get(&key) {
        return Ok(data.clone());
    }

    // Cache miss
    drop(cache);  // Release lock before expensive operation

    let data = fetch_expensive_data(&key).await?;

    let mut cache = state.lru_cache.lock().await;
    cache.put(key, data.clone());

    Ok(data)
}
```

### Persistent Cache

```rust
use sled::Db;

pub struct AppState {
    disk_cache: Db,
}

impl AppState {
    pub fn new() -> Result<Self, String> {
        let cache = sled::open("cache.db")
            .map_err(|e| e.to_string())?;

        Ok(Self {
            disk_cache: cache,
        })
    }
}

#[tauri::command]
async fn get_cached_data(
    key: String,
    state: tauri::State<'_, AppState>,
) -> Result<Option<String>, String> {
    let data = state.disk_cache
        .get(key.as_bytes())
        .map_err(|e| e.to_string())?;

    Ok(data.map(|bytes| String::from_utf8_lossy(&bytes).to_string()))
}

#[tauri::command]
async fn set_cached_data(
    key: String,
    value: String,
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    state.disk_cache
        .insert(key.as_bytes(), value.as_bytes())
        .map_err(|e| e.to_string())?;

    Ok(())
}
```

## Lazy Loading

### Lazy Component Loading

```typescript
// React lazy loading
import { lazy, Suspense } from 'react';

const HeavyComponent = lazy(() => import('./HeavyComponent'));

function App() {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <HeavyComponent />
        </Suspense>
    );
}
```

### Lazy Data Loading

```rust
#[tauri::command]
async fn get_preview(path: String) -> Result<PreviewData, String> {
    // Return lightweight preview first
    let preview = PreviewData {
        name: get_filename(&path),
        size: get_filesize(&path).await?,
        thumbnail: None,  // Don't load heavy data yet
    };

    Ok(preview)
}

#[tauri::command]
async fn get_full_data(path: String) -> Result<FullData, String> {
    // Load heavy data only when requested
    let content = tokio::fs::read(&path)
        .await
        .map_err(|e| e.to_string())?;

    let thumbnail = generate_thumbnail(&content)?;

    Ok(FullData {
        content,
        thumbnail: Some(thumbnail),
    })
}
```

**Frontend**:
```typescript
// Load preview immediately
const preview = await invoke('get_preview', { path });
showPreview(preview);

// Load full data on demand
button.onclick = async () => {
    const fullData = await invoke('get_full_data', { path });
    showFullData(fullData);
};
```

## Database Optimization

### Connection Pooling

```rust
use sqlx::{Pool, Sqlite, SqlitePool};

pub struct AppState {
    db_pool: Pool<Sqlite>,
}

impl AppState {
    pub async fn new() -> Result<Self, sqlx::Error> {
        let pool = SqlitePool::connect("sqlite://data.db").await?;

        Ok(Self { db_pool: pool })
    }
}

#[tauri::command]
async fn query_users(
    state: tauri::State<'_, AppState>,
) -> Result<Vec<User>, String> {
    let users = sqlx::query_as::<_, User>("SELECT * FROM users")
        .fetch_all(&state.db_pool)
        .await
        .map_err(|e| e.to_string())?;

    Ok(users)
}
```

### Prepared Statements

```rust
use sqlx::{Sqlite, Statement};

pub struct PreparedStatements {
    get_user: Statement<'static, Sqlite>,
    insert_user: Statement<'static, Sqlite>,
}

impl PreparedStatements {
    pub async fn new(pool: &Pool<Sqlite>) -> Result<Self, sqlx::Error> {
        Ok(Self {
            get_user: pool.prepare("SELECT * FROM users WHERE id = ?").await?,
            insert_user: pool.prepare("INSERT INTO users (name, email) VALUES (?, ?)").await?,
        })
    }
}

// Use prepared statements for repeated queries
```

## Async Performance

### Concurrent Operations

```rust
use futures::future::join_all;

#[tauri::command]
async fn load_multiple_files(paths: Vec<String>) -> Result<Vec<FileData>, String> {
    let tasks = paths.into_iter().map(|path| async move {
        tokio::fs::read_to_string(&path)
            .await
            .map(|content| FileData { path, content })
    });

    let results = join_all(tasks).await;

    let data: Vec<FileData> = results
        .into_iter()
        .filter_map(|r| r.ok())
        .collect();

    Ok(data)
}
```

### Parallel Processing with Rayon

```rust
use rayon::prelude::*;

#[tauri::command]
async fn process_large_dataset(data: Vec<Item>) -> Result<Vec<ProcessedItem>, String> {
    // Move to blocking thread pool for CPU-intensive work
    let processed = tokio::task::spawn_blocking(move || {
        data.par_iter()
            .map(|item| process_item(item))
            .collect::<Vec<_>>()
    })
    .await
    .map_err(|e| e.to_string())?;

    Ok(processed)
}
```

## Profiling and Debugging

### Backend Profiling

```rust
use std::time::Instant;

#[tauri::command]
async fn profiled_operation() -> Result<String, String> {
    let start = Instant::now();

    let result = expensive_operation().await?;

    let duration = start.elapsed();
    log::info!("Operation took {:?}", duration);

    Ok(result)
}
```

### Conditional Logging

```rust
#[cfg(debug_assertions)]
macro_rules! debug_time {
    ($label:expr, $code:block) => {{
        let start = std::time::Instant::now();
        let result = $code;
        let duration = start.elapsed();
        log::debug!("{} took {:?}", $label, duration);
        result
    }};
}

#[cfg(not(debug_assertions))]
macro_rules! debug_time {
    ($label:expr, $code:block) => {
        $code
    };
}

#[tauri::command]
async fn operation() -> Result<String, String> {
    let result = debug_time!("Database query", {
        query_database().await
    })?;

    Ok(result)
}
```

### Frontend Performance Monitoring

```typescript
// Performance marks
performance.mark('command-start');
const result = await invoke('heavy_command');
performance.mark('command-end');

performance.measure('command-duration', 'command-start', 'command-end');

const measure = performance.getEntriesByName('command-duration')[0];
console.log(`Command took ${measure.duration}ms`);
```

## Memory Optimization

### Avoid Cloning

```rust
// ❌ BAD - unnecessary clone
#[tauri::command]
async fn process_data(data: String) -> Result<String, String> {
    let processed = data.clone();  // Unnecessary
    Ok(processed.to_uppercase())
}

// ✅ GOOD - consume owned value
#[tauri::command]
async fn process_data(data: String) -> Result<String, String> {
    Ok(data.to_uppercase())  // Takes ownership
}
```

### Use References Where Possible

```rust
async fn internal_processing(data: &str) -> String {
    data.to_uppercase()
}

#[tauri::command]
async fn process(data: String) -> Result<String, String> {
    Ok(internal_processing(&data))
}
```

### Drop Large Allocations Early

```rust
#[tauri::command]
async fn process_file(path: String) -> Result<String, String> {
    let large_buffer = tokio::fs::read(&path)
        .await
        .map_err(|e| e.to_string())?;

    let summary = compute_summary(&large_buffer);

    drop(large_buffer);  // Free memory before waiting

    tokio::time::sleep(Duration::from_secs(1)).await;

    Ok(summary)
}
```

## Best Practices

1. **Batch IPC calls** - Minimize serialization overhead
2. **Cache aggressively** - In-memory, LRU, or persistent
3. **Stream large data** - Chunk payloads instead of single large payload
4. **Lazy load** - Only fetch data when needed
5. **Use connection pools** - For database access
6. **Concurrent operations** - Use join_all for parallel async
7. **CPU-bound work** - Move to spawn_blocking or rayon
8. **Profile regularly** - Identify bottlenecks with timing
9. **Minimize cloning** - Use references or consume owned values
10. **Drop early** - Free large allocations as soon as possible

## Common Pitfalls

❌ **Too many small IPC calls**:
```typescript
// WRONG - 100 IPC calls
for (const file of files) {
    await invoke('process_file', { file });
}

// CORRECT - 1 IPC call
await invoke('process_files_batch', { files });
```

❌ **Not caching expensive operations**:
```rust
// WRONG - recomputes every time
#[tauri::command]
async fn get_config() -> Config {
    parse_config().await  // Expensive every call
}

// CORRECT - cache result
lazy_static! {
    static ref CONFIG: Mutex<Option<Config>> = Mutex::new(None);
}
```

❌ **Blocking async runtime**:
```rust
// WRONG - blocks async executor
#[tauri::command]
async fn cpu_intensive() -> String {
    expensive_cpu_work()  // Blocks entire runtime
}

// CORRECT - move to blocking thread
#[tauri::command]
async fn cpu_intensive() -> String {
    tokio::task::spawn_blocking(|| expensive_cpu_work())
        .await
        .unwrap()
}
```

## Summary

- **Batch IPC calls** to minimize serialization overhead
- **Cache frequently accessed data** with TTL, LRU, or persistent
- **Stream large datasets** in chunks to prevent memory spikes
- **Lazy load resources** only when needed
- **Connection pooling** for database efficiency
- **Concurrent async** with join_all for parallel operations
- **CPU-bound work** on spawn_blocking or rayon
- **Profile performance** to identify bottlenecks
- **Minimize cloning** and drop large allocations early
- **Frontend monitoring** with Performance API
