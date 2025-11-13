---
name: tauri-event-system
description: Advanced Tauri event patterns for bidirectional communication, streaming data, window-to-window messaging, and custom event handling
version: 1.0.0
category: development
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Advanced event patterns: bidirectional events, streaming, window messaging, custom payloads, listener management"
    when_to_use: "When implementing real-time updates, progress tracking, inter-window communication, or streaming data"
    quick_start: "1. Backend emits with window.emit() 2. Frontend listens with listen() 3. Clean up with unlisten() 4. Use typed payloads"
context_limit: 500
tags:
  - tauri
  - events
  - ipc
  - streaming
  - real-time
requires_tools: []
---

# Tauri Advanced Event System

## Event Fundamentals

### Backend → Frontend Events

**Basic event emission**:
```rust
use tauri::Window;

#[tauri::command]
async fn start_download(
    url: String,
    window: Window,
) -> Result<(), String> {
    window.emit("download-started", url)
        .map_err(|e| e.to_string())?;

    // Perform download...

    window.emit("download-complete", "Success")
        .map_err(|e| e.to_string())
}
```

**Frontend listener**:
```typescript
import { listen, UnlistenFn } from '@tauri-apps/api/event';

const unlisten = await listen<string>('download-started', (event) => {
    console.log('Download started:', event.payload);
});

// Clean up when done
unlisten();
```

## Structured Event Payloads

### Typed Events with Serde

**Backend**:
```rust
use serde::Serialize;

#[derive(Serialize, Clone)]
struct ProgressEvent {
    current: usize,
    total: usize,
    percentage: f64,
    message: String,
    speed_mbps: Option<f64>,
}

#[tauri::command]
async fn download_file(
    url: String,
    window: Window,
) -> Result<(), String> {
    let total_size = get_file_size(&url).await?;

    for chunk in 0..total_size {
        // Download chunk...

        let progress = ProgressEvent {
            current: chunk,
            total: total_size,
            percentage: (chunk as f64 / total_size as f64) * 100.0,
            message: format!("Downloading... {}/{}", chunk, total_size),
            speed_mbps: Some(calculate_speed()),
        };

        window.emit("download-progress", progress)
            .map_err(|e| e.to_string())?;
    }

    Ok(())
}
```

**Frontend**:
```typescript
interface ProgressEvent {
    current: number;
    total: number;
    percentage: number;
    message: string;
    speed_mbps?: number;
}

const unlisten = await listen<ProgressEvent>('download-progress', (event) => {
    const { current, total, percentage, message, speed_mbps } = event.payload;

    updateProgressBar(percentage);
    updateStatus(message);

    if (speed_mbps) {
        updateSpeed(speed_mbps);
    }
});
```

### Complex Event Payloads

```rust
#[derive(Serialize, Clone)]
#[serde(tag = "type", content = "data")]
enum AppEvent {
    UserLoggedIn { user_id: String, username: String },
    UserLoggedOut { user_id: String },
    DataSynced { items_count: usize, timestamp: String },
    ErrorOccurred { code: String, message: String, recoverable: bool },
}

#[tauri::command]
async fn perform_login(
    username: String,
    password: String,
    window: Window,
) -> Result<String, String> {
    let user = authenticate(&username, &password).await?;

    // Emit structured event
    window.emit("app-event", AppEvent::UserLoggedIn {
        user_id: user.id.clone(),
        username: user.username.clone(),
    }).map_err(|e| e.to_string())?;

    Ok(user.id)
}
```

**Frontend**:
```typescript
type AppEvent =
    | { type: 'UserLoggedIn'; data: { user_id: string; username: string } }
    | { type: 'UserLoggedOut'; data: { user_id: string } }
    | { type: 'DataSynced'; data: { items_count: number; timestamp: string } }
    | { type: 'ErrorOccurred'; data: { code: string; message: string; recoverable: boolean } };

listen<AppEvent>('app-event', (event) => {
    const appEvent = event.payload;

    switch (appEvent.type) {
        case 'UserLoggedIn':
            handleLogin(appEvent.data.user_id, appEvent.data.username);
            break;
        case 'UserLoggedOut':
            handleLogout(appEvent.data.user_id);
            break;
        case 'DataSynced':
            showSyncSuccess(appEvent.data.items_count);
            break;
        case 'ErrorOccurred':
            handleError(appEvent.data);
            break;
    }
});
```

## Streaming Data Patterns

### Real-Time Data Stream

```rust
#[tauri::command]
async fn stream_sensor_data(
    sensor_id: String,
    window: Window,
) -> Result<(), String> {
    let mut interval = tokio::time::interval(Duration::from_millis(100));

    for _ in 0..100 {
        interval.tick().await;

        let reading = read_sensor(&sensor_id).await?;

        window.emit("sensor-reading", reading)
            .map_err(|e| e.to_string())?;
    }

    window.emit("sensor-stream-ended", sensor_id)
        .map_err(|e| e.to_string())
}
```

**Frontend with React**:
```typescript
import { useEffect, useState } from 'react';
import { listen } from '@tauri-apps/api/event';

interface SensorReading {
    value: number;
    timestamp: number;
    unit: string;
}

function SensorMonitor() {
    const [readings, setReadings] = useState<SensorReading[]>([]);

    useEffect(() => {
        let unlisten: UnlistenFn | undefined;

        listen<SensorReading>('sensor-reading', (event) => {
            setReadings(prev => [...prev.slice(-99), event.payload]);
        }).then(fn => unlisten = fn);

        return () => unlisten?.();
    }, []);

    return (
        <div>
            {readings.map((r, i) => (
                <div key={i}>{r.value} {r.unit}</div>
            ))}
        </div>
    );
}
```

### Buffered Streaming

```rust
#[tauri::command]
async fn stream_logs(
    log_file: String,
    window: Window,
) -> Result<(), String> {
    use tokio::io::{AsyncBufReadExt, BufReader};
    use tokio::fs::File;

    let file = File::open(log_file).await
        .map_err(|e| e.to_string())?;

    let reader = BufReader::new(file);
    let mut lines = reader.lines();

    let mut buffer = Vec::new();

    while let Some(line) = lines.next_line().await
        .map_err(|e| e.to_string())? {

        buffer.push(line);

        // Send in batches of 10 lines
        if buffer.len() >= 10 {
            window.emit("log-batch", buffer.clone())
                .map_err(|e| e.to_string())?;
            buffer.clear();
        }
    }

    // Send remaining lines
    if !buffer.is_empty() {
        window.emit("log-batch", buffer)
            .map_err(|e| e.to_string())?;
    }

    Ok(())
}
```

## Multi-Window Communication

### Broadcasting to All Windows

```rust
use tauri::{AppHandle, Manager};

#[tauri::command]
async fn broadcast_message(
    message: String,
    app: AppHandle,
) -> Result<(), String> {
    // Emit to ALL windows
    app.emit_all("broadcast", message)
        .map_err(|e| e.to_string())
}
```

### Targeted Window Messaging

```rust
#[tauri::command]
async fn send_to_window(
    target_window: String,
    message: String,
    app: AppHandle,
) -> Result<(), String> {
    // Get specific window
    if let Some(window) = app.get_window(&target_window) {
        window.emit("private-message", message)
            .map_err(|e| e.to_string())?;
        Ok(())
    } else {
        Err(format!("Window '{}' not found", target_window))
    }
}
```

### Window-to-Window via Backend

**Window A (sender)**:
```typescript
import { invoke } from '@tauri-apps/api/core';

async function sendToSettings(data: any) {
    await invoke('relay_to_settings', { data });
}
```

**Backend relay**:
```rust
#[tauri::command]
async fn relay_to_settings(
    data: serde_json::Value,
    app: AppHandle,
) -> Result<(), String> {
    if let Some(settings_window) = app.get_window("settings") {
        settings_window.emit("data-update", data)
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}
```

**Window B (receiver - settings)**:
```typescript
import { listen } from '@tauri-apps/api/event';

useEffect(() => {
    let unlisten: UnlistenFn | undefined;

    listen('data-update', (event) => {
        console.log('Received from main window:', event.payload);
        updateSettings(event.payload);
    }).then(fn => unlisten = fn);

    return () => unlisten?.();
}, []);
```

## Frontend → Backend Events

### Custom Frontend Events

```typescript
import { emit } from '@tauri-apps/api/event';

// Frontend emits event
await emit('user-action', {
    action: 'button-click',
    button_id: 'save-button',
    timestamp: Date.now()
});
```

**Backend listener**:
```rust
use tauri::{Manager, Listener};

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let app_handle = app.handle();

            // Listen for frontend events
            app_handle.listen_global("user-action", move |event| {
                if let Some(payload) = event.payload() {
                    println!("User action: {}", payload);
                    // Process event...
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

## Advanced Listener Management

### React Hook for Events

```typescript
import { useEffect, useState } from 'react';
import { listen, UnlistenFn } from '@tauri-apps/api/event';

function useEvent<T>(eventName: string): T | null {
    const [payload, setPayload] = useState<T | null>(null);

    useEffect(() => {
        let unlisten: UnlistenFn | undefined;

        listen<T>(eventName, (event) => {
            setPayload(event.payload);
        }).then(fn => unlisten = fn);

        return () => unlisten?.();
    }, [eventName]);

    return payload;
}

// Usage
function ProgressDisplay() {
    const progress = useEvent<ProgressEvent>('download-progress');

    if (!progress) return null;

    return (
        <div>
            Progress: {progress.percentage.toFixed(2)}%
        </div>
    );
}
```

### Event Queue Pattern

```typescript
import { listen } from '@tauri-apps/api/event';

class EventQueue<T> {
    private queue: T[] = [];
    private unlisten?: UnlistenFn;

    async start(eventName: string) {
        this.unlisten = await listen<T>(eventName, (event) => {
            this.queue.push(event.payload);
        });
    }

    dequeue(): T | undefined {
        return this.queue.shift();
    }

    clear() {
        this.queue = [];
    }

    stop() {
        this.unlisten?.();
    }

    get length() {
        return this.queue.length;
    }
}

// Usage
const progressQueue = new EventQueue<ProgressEvent>();
await progressQueue.start('download-progress');

// Process queue periodically
setInterval(() => {
    while (progressQueue.length > 0) {
        const event = progressQueue.dequeue();
        processProgress(event);
    }
}, 100);
```

### One-Time Events

```typescript
import { once } from '@tauri-apps/api/event';

// Listen for event only once
await once<string>('initialization-complete', (event) => {
    console.log('App initialized:', event.payload);
    startApp();
});
```

## Error Handling in Events

### Safe Event Emission

```rust
async fn emit_safe(window: &Window, event: &str, payload: impl Serialize) -> Result<(), String> {
    window.emit(event, payload)
        .map_err(|e| {
            eprintln!("Failed to emit event '{}': {}", event, e);
            e.to_string()
        })
}

#[tauri::command]
async fn process_with_events(
    window: Window,
) -> Result<(), String> {
    emit_safe(&window, "processing-started", "Starting...")
        .await?;

    // Process...

    emit_safe(&window, "processing-complete", "Done!")
        .await?;

    Ok(())
}
```

## Performance Considerations

### Throttling Events

```rust
use std::time::{Duration, Instant};

#[tauri::command]
async fn high_frequency_updates(
    window: Window,
) -> Result<(), String> {
    let mut last_emit = Instant::now();
    let throttle_duration = Duration::from_millis(100);

    for i in 0..10000 {
        let value = compute_value(i);

        // Only emit every 100ms
        if last_emit.elapsed() >= throttle_duration {
            window.emit("update", value)
                .map_err(|e| e.to_string())?;
            last_emit = Instant::now();
        }
    }

    Ok(())
}
```

### Batching Events

```rust
#[tauri::command]
async fn batch_updates(
    window: Window,
) -> Result<(), String> {
    let mut batch = Vec::new();

    for item in process_items() {
        batch.push(item);

        // Emit in batches of 50
        if batch.len() >= 50 {
            window.emit("batch-update", batch.clone())
                .map_err(|e| e.to_string())?;
            batch.clear();
        }
    }

    // Emit remaining items
    if !batch.is_empty() {
        window.emit("batch-update", batch)
            .map_err(|e| e.to_string())?;
    }

    Ok(())
}
```

## Best Practices

1. **Always clean up listeners** - Use `unlisten()` to prevent memory leaks
2. **Type event payloads** - Define interfaces for type safety
3. **Use structured events** - Tagged unions for multiple event types
4. **Throttle high-frequency events** - Prevent overwhelming frontend
5. **Batch when possible** - Reduce serialization overhead
6. **Handle errors gracefully** - Log failed emissions, don't crash
7. **Use once() for one-time events** - Initialization, completion signals
8. **Namespace event names** - Use prefixes like "download:", "user:", "system:"

## Common Pitfalls

❌ **Forgetting to unlisten**:
```typescript
// WRONG - memory leak
function Component() {
    listen('my-event', handler);  // Never cleaned up!
}

// CORRECT
function Component() {
    useEffect(() => {
        let unlisten: UnlistenFn | undefined;
        listen('my-event', handler).then(fn => unlisten = fn);
        return () => unlisten?.();
    }, []);
}
```

❌ **Not handling serialization errors**:
```rust
// WRONG - struct can't serialize
#[derive(Clone)]  // Missing Serialize!
struct Event { }

window.emit("event", Event {});  // Runtime error!

// CORRECT
#[derive(Serialize, Clone)]
struct Event { }
```

❌ **Emitting too frequently**:
```rust
// WRONG - 10000 events in quick succession
for i in 0..10000 {
    window.emit("update", i);  // Overwhelming!
}

// CORRECT - throttle or batch
```

## Summary

- **Events are async** - Backend → Frontend communication
- **Always type payloads** - Use serde::Serialize + TypeScript interfaces
- **Clean up listeners** - Call `unlisten()` in cleanup
- **Throttle/batch** - High-frequency events need rate limiting
- **Use structured payloads** - Tagged unions for multiple event types
- **Window targeting** - `emit()` for specific, `emit_all()` for broadcast
- **Frontend events** - Use `emit()` from frontend, listen in backend setup
