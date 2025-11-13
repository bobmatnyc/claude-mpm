---
name: tauri-async-patterns
description: Advanced async patterns in Tauri including long-running tasks, background work, cancellation, and concurrent operations
version: 1.0.0
category: development
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Async mastery: long-running operations with progress, background tasks, cancellation patterns, concurrent processing"
    when_to_use: "Implementing downloads, file processing, background sync, or any long-running async operations"
    quick_start: "1. Use tokio::spawn for background work 2. Emit progress events 3. Implement cancellation with channels 4. Handle graceful shutdown"
context_limit: 500
tags:
  - tauri
  - async
  - tokio
  - concurrency
  - background-tasks
requires_tools: []
---

# Tauri Async Patterns

## Long-Running Operations with Progress

```rust
use tokio::time::{sleep, Duration};

#[tauri::command]
async fn long_download(
    url: String,
    window: tauri::Window,
) -> Result<String, String> {
    let total_chunks = 100;

    for chunk in 0..total_chunks {
        // Simulate download
        sleep(Duration::from_millis(50)).await;

        // Emit progress
        window.emit("download-progress", serde_json::json!({
            "current": chunk + 1,
            "total": total_chunks,
            "percentage": ((chunk + 1) as f64 / total_chunks as f64) * 100.0
        })).map_err(|e| e.to_string())?;
    }

    window.emit("download-complete", url.clone())
        .map_err(|e| e.to_string())?;

    Ok(format!("Downloaded: {}", url))
}
```

## Background Tasks

### Spawning Background Work

```rust
#[tauri::command]
async fn start_background_sync(
    app: tauri::AppHandle,
) -> Result<(), String> {
    // Spawn task that outlives command
    tokio::spawn(async move {
        loop {
            // Perform sync
            match perform_sync().await {
                Ok(_) => {
                    if let Some(window) = app.get_window("main") {
                        let _ = window.emit("sync-complete", ());
                    }
                }
                Err(e) => {
                    log::error!("Sync failed: {}", e);
                }
            }

            // Wait before next sync
            tokio::time::sleep(Duration::from_secs(300)).await;
        }
    });

    Ok(())
}
```

### Task Management State

```rust
use std::sync::Arc;
use tokio::sync::Mutex;
use std::collections::HashMap;

pub struct TaskManager {
    tasks: Arc<Mutex<HashMap<String, TaskHandle>>>,
}

struct TaskHandle {
    cancel_tx: tokio::sync::mpsc::Sender<()>,
    status: Arc<Mutex<TaskStatus>>,
}

#[derive(Clone)]
enum TaskStatus {
    Running,
    Completed,
    Cancelled,
    Failed(String),
}

impl TaskManager {
    pub async fn spawn_task<F>(&self, id: String, task: F) -> String
    where
        F: Future<Output = Result<(), String>> + Send + 'static,
    {
        let (cancel_tx, mut cancel_rx) = tokio::sync::mpsc::channel::<()>(1);
        let status = Arc::new(Mutex::new(TaskStatus::Running));
        let status_clone = status.clone();

        tokio::spawn(async move {
            tokio::select! {
                result = task => {
                    let mut s = status_clone.lock().await;
                    *s = match result {
                        Ok(_) => TaskStatus::Completed,
                        Err(e) => TaskStatus::Failed(e),
                    };
                }
                _ = cancel_rx.recv() => {
                    let mut s = status_clone.lock().await;
                    *s = TaskStatus::Cancelled;
                }
            }
        });

        self.tasks.lock().await.insert(id.clone(), TaskHandle {
            cancel_tx,
            status,
        });

        id
    }

    pub async fn cancel_task(&self, id: &str) -> Result<(), String> {
        let mut tasks = self.tasks.lock().await;
        if let Some(handle) = tasks.remove(id) {
            handle.cancel_tx.send(()).await.ok();
            Ok(())
        } else {
            Err(format!("Task '{}' not found", id))
        }
    }

    pub async fn get_status(&self, id: &str) -> Option<TaskStatus> {
        let tasks = self.tasks.lock().await;
        if let Some(handle) = tasks.get(id) {
            Some(handle.status.lock().await.clone())
        } else {
            None
        }
    }
}
```

## Cancellation Patterns

### Using tokio::select! for Cancellation

```rust
#[tauri::command]
async fn cancellable_operation(
    state: tauri::State<'_, TaskManager>,
) -> Result<String, String> {
    let task_id = uuid::Uuid::new_v4().to_string();

    state.spawn_task(task_id.clone(), async move {
        for i in 0..1000 {
            // Check if cancelled via select!
            tokio::time::sleep(Duration::from_millis(10)).await;

            // Do work
            process_item(i).await?;
        }

        Ok(())
    }).await;

    Ok(task_id)
}

#[tauri::command]
async fn cancel_operation(
    task_id: String,
    state: tauri::State<'_, TaskManager>,
) -> Result<(), String> {
    state.cancel_task(&task_id).await
}
```

### Manual Cancellation Token

```rust
use std::sync::atomic::{AtomicBool, Ordering};

#[tauri::command]
async fn start_with_token(
    state: tauri::State<'_, AppState>,
    window: tauri::Window,
) -> Result<String, String> {
    let task_id = uuid::Uuid::new_v4().to_string();
    let cancel_flag = Arc::new(AtomicBool::new(false));

    // Store cancel flag
    state.cancel_flags.insert(task_id.clone(), cancel_flag.clone());

    let task_id_clone = task_id.clone();
    tokio::spawn(async move {
        for i in 0..1000 {
            // Check cancellation
            if cancel_flag.load(Ordering::Relaxed) {
                window.emit("task-cancelled", task_id_clone).ok();
                break;
            }

            // Do work
            process_item(i).await.ok();
        }
    });

    Ok(task_id)
}

#[tauri::command]
fn cancel_with_token(
    task_id: String,
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    if let Some(flag) = state.cancel_flags.get(&task_id) {
        flag.store(true, Ordering::Relaxed);
        Ok(())
    } else {
        Err("Task not found".to_string())
    }
}
```

## Concurrent Operations

### Parallel Processing

```rust
use futures::stream::{self, StreamExt};

#[tauri::command]
async fn process_files_parallel(
    files: Vec<String>,
    window: tauri::Window,
) -> Result<Vec<String>, String> {
    let results = stream::iter(files)
        .map(|file| {
            let window = window.clone();
            async move {
                let result = process_file(&file).await;

                window.emit("file-processed", file.clone()).ok();

                result
            }
        })
        .buffer_unordered(4)  // Process 4 at a time
        .collect::<Vec<_>>()
        .await;

    let successes: Vec<String> = results
        .into_iter()
        .filter_map(|r| r.ok())
        .collect();

    Ok(successes)
}
```

### Bounded Concurrency

```rust
use tokio::sync::Semaphore;

#[tauri::command]
async fn batch_download(
    urls: Vec<String>,
    max_concurrent: usize,
) -> Result<Vec<String>, String> {
    let semaphore = Arc::new(Semaphore::new(max_concurrent));
    let mut handles = Vec::new();

    for url in urls {
        let permit = semaphore.clone().acquire_owned().await.unwrap();

        let handle = tokio::spawn(async move {
            let result = download_file(&url).await;
            drop(permit);  // Release permit
            result
        });

        handles.push(handle);
    }

    let results = futures::future::join_all(handles).await;

    Ok(results.into_iter()
        .filter_map(|r| r.ok().and_then(|r| r.ok()))
        .collect())
}
```

## Stream Processing

```rust
use tokio::io::{AsyncBufReadExt, BufReader};

#[tauri::command]
async fn stream_log_file(
    filepath: String,
    window: tauri::Window,
) -> Result<(), String> {
    let file = tokio::fs::File::open(filepath)
        .await
        .map_err(|e| e.to_string())?;

    let reader = BufReader::new(file);
    let mut lines = reader.lines();

    while let Some(line) = lines.next_line()
        .await
        .map_err(|e| e.to_string())? {

        window.emit("log-line", line)
            .map_err(|e| e.to_string())?;

        // Throttle to avoid overwhelming frontend
        tokio::time::sleep(Duration::from_millis(10)).await;
    }

    window.emit("log-complete", ())
        .map_err(|e| e.to_string())?;

    Ok(())
}
```

## Timeout Patterns

```rust
use tokio::time::timeout;

#[tauri::command]
async fn operation_with_timeout(
    duration_secs: u64,
) -> Result<String, String> {
    let operation = async {
        long_running_task().await
    };

    match timeout(Duration::from_secs(duration_secs), operation).await {
        Ok(Ok(result)) => Ok(result),
        Ok(Err(e)) => Err(format!("Operation failed: {}", e)),
        Err(_) => Err("Operation timed out".to_string()),
    }
}
```

## Graceful Shutdown

```rust
use tokio::sync::broadcast;

pub struct ShutdownManager {
    shutdown_tx: broadcast::Sender<()>,
}

impl ShutdownManager {
    pub fn new() -> Self {
        let (shutdown_tx, _) = broadcast::channel(1);
        Self { shutdown_tx }
    }

    pub fn subscribe(&self) -> broadcast::Receiver<()> {
        self.shutdown_tx.subscribe()
    }

    pub fn shutdown(&self) {
        let _ = self.shutdown_tx.send(());
    }
}

#[tauri::command]
async fn start_service(
    state: tauri::State<'_, ShutdownManager>,
) -> Result<(), String> {
    let mut shutdown_rx = state.subscribe();

    tokio::spawn(async move {
        loop {
            tokio::select! {
                _ = tokio::time::sleep(Duration::from_secs(1)) => {
                    // Do work
                    perform_service_work().await;
                }
                _ = shutdown_rx.recv() => {
                    log::info!("Service shutting down");
                    cleanup().await;
                    break;
                }
            }
        }
    });

    Ok(())
}
```

## Best Practices

1. **Always emit progress** - For operations >1 second
2. **Implement cancellation** - For long-running tasks
3. **Use tokio::spawn** - For true background work
4. **Limit concurrency** - Use Semaphore for bounded parallelism
5. **Add timeouts** - Prevent hung operations
6. **Handle graceful shutdown** - Clean up resources
7. **Throttle events** - Don't overwhelm frontend with updates
8. **Use select!** - For cancellation and timeouts
9. **Store task handles** - Enable management and cancellation
10. **Test async paths** - Verify cancellation and timeouts work

## Common Pitfalls

❌ **Blocking async runtime**:
```rust
// WRONG
std::thread::sleep(Duration::from_secs(1));

// CORRECT
tokio::time::sleep(Duration::from_secs(1)).await;
```

❌ **Forgetting to spawn**:
```rust
// WRONG - command waits for completion
async fn start_background() {
    background_work().await;  // Blocks command
}

// CORRECT - spawn to background
async fn start_background() {
    tokio::spawn(async {
        background_work().await;
    });
}
```

❌ **No cancellation mechanism**:
```rust
// WRONG - can't stop once started
tokio::spawn(async {
    loop {
        work().await;
        sleep(Duration::from_secs(1)).await;
    }
});

// CORRECT - cancellable
let (tx, mut rx) = tokio::sync::mpsc::channel(1);
tokio::spawn(async move {
    loop {
        tokio::select! {
            _ = work() => {}
            _ = rx.recv() => break,
        }
    }
});
```

## Summary

- **tokio::spawn** for background tasks
- **tokio::select!** for cancellation
- **Progress events** for long operations
- **Semaphore** for bounded concurrency
- **timeout()** to prevent hung operations
- **broadcast** for shutdown signals
- **Stream processing** for large data
- **Task management** with cancel tokens
- **Graceful cleanup** on shutdown
