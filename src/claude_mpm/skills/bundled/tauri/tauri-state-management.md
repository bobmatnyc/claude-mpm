---
name: tauri-state-management
description: Advanced state management in Tauri using Arc, Mutex, RwLock, DashMap for concurrent access patterns and complex state architectures
version: 1.0.0
category: development
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Advanced Tauri state patterns: Arc/Mutex, RwLock for read-heavy, DashMap for lock-free maps, multi-state management"
    when_to_use: "When managing complex shared state, high-concurrency scenarios, or multiple independent state containers"
    quick_start: "1. Choose container (Mutex/RwLock/DashMap) 2. Define state struct 3. Register with .manage() 4. Access via State<'_, T>"
context_limit: 600
tags:
  - tauri
  - state
  - concurrency
  - arc
  - mutex
  - rwlock
  - dashmap
requires_tools: []
---

# Tauri Advanced State Management

## State Container Patterns

### Arc<Mutex<T>> - Basic Exclusive Access

Best for: Infrequent writes, occasional reads, simple synchronization

```rust
use std::sync::Arc;
use tokio::sync::Mutex;

pub struct AppState {
    pub database: Arc<Mutex<Database>>,
    pub config: Arc<Mutex<Config>>,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            database: Arc::new(Mutex::new(Database::new())),
            config: Arc::new(Mutex::new(Config::default())),
        }
    }
}

#[tauri::command]
async fn update_config(
    key: String,
    value: String,
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    let mut config = state.config.lock().await;
    config.set(&key, value);
    Ok(())
}

#[tauri::command]
async fn get_config_value(
    key: String,
    state: tauri::State<'_, AppState>,
) -> Result<Option<String>, String> {
    let config = state.config.lock().await;
    Ok(config.get(&key).cloned())
}
```

**Key Points**:
- `Arc` enables shared ownership across async tasks
- `Mutex` provides exclusive access (one writer OR one reader at a time)
- Use tokio's `Mutex` (not std) for async contexts
- Always `.await` on lock acquisition

### Arc<RwLock<T>> - Read-Heavy Workloads

Best for: Frequent reads, rare writes, read-dominant patterns

```rust
use std::sync::Arc;
use tokio::sync::RwLock;

pub struct CacheState {
    pub cache: Arc<RwLock<HashMap<String, CachedData>>>,
    pub stats: Arc<RwLock<CacheStats>>,
}

#[tauri::command]
async fn get_cached_data(
    key: String,
    state: tauri::State<'_, CacheState>,
) -> Result<Option<CachedData>, String> {
    // Read lock - multiple concurrent readers allowed
    let cache = state.cache.read().await;
    Ok(cache.get(&key).cloned())
}

#[tauri::command]
async fn update_cache(
    key: String,
    data: CachedData,
    state: tauri::State<'_, CacheState>,
) -> Result<(), String> {
    // Write lock - exclusive access
    let mut cache = state.cache.write().await;
    cache.insert(key, data);
    Ok(())
}

#[tauri::command]
async fn get_stats(
    state: tauri::State<'_, CacheState>,
) -> Result<CacheStats, String> {
    // Read lock doesn't block other readers
    let stats = state.stats.read().await;
    Ok(stats.clone())
}
```

**Key Points**:
- `read()` allows multiple concurrent readers
- `write()` requires exclusive access
- Perfect for caches, configuration, read-heavy data
- Readers don't block other readers

### Arc<DashMap<K, V>> - Lock-Free Concurrent Map

Best for: High-concurrency, frequent map operations, no lock contention

```rust
use std::sync::Arc;
use dashmap::DashMap;

pub struct SessionState {
    pub sessions: Arc<DashMap<String, Session>>,
    pub active_connections: Arc<DashMap<String, Connection>>,
}

impl SessionState {
    pub fn new() -> Self {
        Self {
            sessions: Arc::new(DashMap::new()),
            active_connections: Arc::new(DashMap::new()),
        }
    }
}

#[tauri::command]
async fn create_session(
    session_id: String,
    state: tauri::State<'_, SessionState>,
) -> Result<(), String> {
    // No explicit locking needed
    state.sessions.insert(
        session_id.clone(),
        Session::new(session_id)
    );
    Ok(())
}

#[tauri::command]
async fn get_session(
    session_id: String,
    state: tauri::State<'_, SessionState>,
) -> Result<Option<Session>, String> {
    // Returns Option without holding lock
    Ok(state.sessions.get(&session_id)
        .map(|entry| entry.value().clone()))
}

#[tauri::command]
async fn remove_session(
    session_id: String,
    state: tauri::State<'_, SessionState>,
) -> Result<(), String> {
    state.sessions.remove(&session_id);
    Ok(())
}

#[tauri::command]
async fn list_active_sessions(
    state: tauri::State<'_, SessionState>,
) -> Result<Vec<String>, String> {
    // Iterate without holding global lock
    Ok(state.sessions.iter()
        .map(|entry| entry.key().clone())
        .collect())
}
```

**Key Points**:
- No explicit `.lock()` needed
- Lock-free concurrent operations
- Better performance under high concurrency
- Use for session management, caches, registries

**Add to Cargo.toml**:
```toml
[dependencies]
dashmap = "6.0"
```

## Complex State Architectures

### Multi-State Pattern

```rust
// Separate concerns into different state containers
pub struct DatabaseState {
    pub pool: Arc<Mutex<DbPool>>,
    pub migrations: Arc<Mutex<MigrationTracker>>,
}

pub struct UIState {
    pub theme: Arc<RwLock<Theme>>,
    pub preferences: Arc<RwLock<Preferences>>,
    pub window_states: Arc<DashMap<String, WindowState>>,
}

pub struct AuthState {
    pub sessions: Arc<DashMap<String, Session>>,
    pub tokens: Arc<RwLock<TokenManager>>,
}

// Register all states
fn main() {
    tauri::Builder::default()
        .manage(DatabaseState::new())
        .manage(UIState::new())
        .manage(AuthState::new())
        .invoke_handler(tauri::generate_handler![
            /* commands */
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

// Access multiple states in one command
#[tauri::command]
async fn authenticated_query(
    query: String,
    session_id: String,
    db_state: tauri::State<'_, DatabaseState>,
    auth_state: tauri::State<'_, AuthState>,
) -> Result<Vec<Row>, String> {
    // Validate session
    let session = auth_state.sessions.get(&session_id)
        .ok_or("Invalid session")?;

    // Execute query
    let pool = db_state.pool.lock().await;
    pool.query(&query).await
        .map_err(|e| e.to_string())
}
```

### Nested State with Interior Mutability

```rust
use std::sync::Arc;
use tokio::sync::RwLock;

pub struct User {
    pub id: String,
    pub name: String,
    pub last_active: Arc<RwLock<SystemTime>>,
}

pub struct AppState {
    pub users: Arc<DashMap<String, User>>,
}

#[tauri::command]
async fn update_user_activity(
    user_id: String,
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    // Get user from DashMap
    if let Some(user_entry) = state.users.get(&user_id) {
        // Update nested RwLock without locking entire map
        let mut last_active = user_entry.last_active.write().await;
        *last_active = SystemTime::now();
    }
    Ok(())
}
```

## Advanced Patterns

### State with Cleanup

```rust
pub struct ResourceState {
    pub connections: Arc<DashMap<String, Connection>>,
}

impl ResourceState {
    pub async fn cleanup_expired(&self) {
        let now = SystemTime::now();
        self.connections.retain(|_k, v| {
            !v.is_expired(now)
        });
    }
}

// Background cleanup task
#[tauri::command]
async fn start_cleanup_task(
    state: tauri::State<'_, ResourceState>,
) -> Result<(), String> {
    let state_clone = state.inner().clone();

    tokio::spawn(async move {
        loop {
            tokio::time::sleep(Duration::from_secs(60)).await;
            state_clone.cleanup_expired().await;
        }
    });

    Ok(())
}
```

### State Initialization with Dependencies

```rust
pub struct AppState {
    pub db: Arc<Mutex<Database>>,
    pub cache: Arc<RwLock<Cache>>,
}

impl AppState {
    pub async fn new(config: &Config) -> Result<Self, String> {
        // Initialize with dependencies
        let db = Database::connect(&config.db_url)
            .await
            .map_err(|e| e.to_string())?;

        let cache = Cache::with_capacity(config.cache_size);

        Ok(Self {
            db: Arc::new(Mutex::new(db)),
            cache: Arc::new(RwLock::new(cache)),
        })
    }
}

// In main.rs
fn main() {
    let config = Config::load().expect("Failed to load config");

    let runtime = tokio::runtime::Runtime::new()
        .expect("Failed to create runtime");

    let state = runtime.block_on(async {
        AppState::new(&config).await
            .expect("Failed to initialize state")
    });

    tauri::Builder::default()
        .manage(state)
        .invoke_handler(tauri::generate_handler![/* commands */])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### Transactional State Updates

```rust
#[tauri::command]
async fn transfer_funds(
    from_account: String,
    to_account: String,
    amount: f64,
    state: tauri::State<'_, BankState>,
) -> Result<(), String> {
    // Lock both accounts to prevent race conditions
    let mut accounts = state.accounts.write().await;

    let from_balance = accounts.get_mut(&from_account)
        .ok_or("Source account not found")?;

    if *from_balance < amount {
        return Err("Insufficient funds".to_string());
    }

    *from_balance -= amount;

    let to_balance = accounts.get_mut(&to_account)
        .ok_or("Destination account not found")?;

    *to_balance += amount;

    // Both updates succeed or both fail (atomic)
    Ok(())
}
```

## Lock Management Best Practices

### ❌ Holding Locks Across Await Points

```rust
// WRONG - Lock held across await (potential deadlock)
#[tauri::command]
async fn bad_pattern(
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    let mut data = state.data.lock().await;
    // Lock is held here
    expensive_async_operation().await?;  // Deadlock risk!
    data.update();
    Ok(())
}

// CORRECT - Release lock before await
#[tauri::command]
async fn good_pattern(
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    let result = expensive_async_operation().await?;

    {
        let mut data = state.data.lock().await;
        data.update_with(result);
    }  // Lock released here

    Ok(())
}
```

### ✅ Minimizing Lock Scope

```rust
#[tauri::command]
async fn optimized_read(
    key: String,
    state: tauri::State<'_, AppState>,
) -> Result<String, String> {
    // Clone only what you need, release lock immediately
    let value = {
        let cache = state.cache.read().await;
        cache.get(&key).cloned()
    };  // Lock released here

    match value {
        Some(v) => Ok(v),
        None => {
            // Compute without holding lock
            let computed = compute_value(&key).await?;

            // Lock only for insertion
            {
                let mut cache = state.cache.write().await;
                cache.insert(key, computed.clone());
            }

            Ok(computed)
        }
    }
}
```

### ✅ Using Try-Lock for Non-Blocking

```rust
use tokio::sync::Mutex;

#[tauri::command]
async fn try_update(
    state: tauri::State<'_, AppState>,
) -> Result<String, String> {
    // Try to acquire lock without blocking
    match state.data.try_lock() {
        Ok(mut data) => {
            data.update();
            Ok("Updated".to_string())
        }
        Err(_) => {
            // Lock is held, don't wait
            Ok("Busy, try again later".to_string())
        }
    }
}
```

## Decision Matrix

| Use Case | Container | Reason |
|----------|-----------|--------|
| Simple shared data | `Arc<Mutex<T>>` | Easy, works for everything |
| Frequent reads, rare writes | `Arc<RwLock<T>>` | Concurrent readers |
| High-concurrency map | `Arc<DashMap<K,V>>` | Lock-free operations |
| Session management | `Arc<DashMap<K,V>>` | Concurrent access |
| Configuration cache | `Arc<RwLock<T>>` | Many readers, few writers |
| Database connection | `Arc<Mutex<T>>` | Exclusive access needed |
| Active connections | `Arc<DashMap<K,V>>` | High concurrency |
| User preferences | `Arc<RwLock<T>>` | Read-heavy |

## Performance Considerations

### Benchmarking State Access

```rust
use std::time::Instant;

#[tauri::command]
async fn benchmark_state_access(
    iterations: usize,
    state: tauri::State<'_, AppState>,
) -> Result<BenchmarkResults, String> {
    let start = Instant::now();

    for _ in 0..iterations {
        let _data = state.data.read().await;
        // Simulate work
    }

    let duration = start.elapsed();

    Ok(BenchmarkResults {
        iterations,
        total_ms: duration.as_millis(),
        avg_us: duration.as_micros() / iterations as u128,
    })
}
```

## Common Pitfalls

❌ **Using std::sync::Mutex in async code**:
```rust
use std::sync::Mutex;  // WRONG for async

// Use tokio's Mutex instead
use tokio::sync::Mutex;  // CORRECT for async
```

❌ **Not using Arc for shared state**:
```rust
// WRONG - Mutex alone doesn't provide shared ownership
pub struct AppState {
    data: Mutex<Data>,  // Can't clone/share
}

// CORRECT - Arc enables shared ownership
pub struct AppState {
    data: Arc<Mutex<Data>>,  // Can clone Arc, share across tasks
}
```

❌ **Forgetting to .await lock acquisition**:
```rust
// WRONG - forgot .await
let data = state.data.lock();  // Returns Future, not MutexGuard

// CORRECT
let data = state.data.lock().await;
```

## Summary

- **`Arc<Mutex<T>>`** - General purpose, exclusive access
- **`Arc<RwLock<T>>`** - Read-heavy workloads, concurrent readers
- **`Arc<DashMap<K,V>>`** - Lock-free maps, high concurrency
- **Minimize lock scope** - Hold locks for shortest time possible
- **Don't hold locks across await** - Deadlock risk
- **Use multiple states** - Separate concerns for better granularity
- **Always use tokio's Mutex/RwLock** - Not std's version in async
