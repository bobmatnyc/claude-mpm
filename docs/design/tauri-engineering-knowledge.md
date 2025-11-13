# Tauri Engineering Knowledge Base
## Comprehensive Reference for Tauri Development Patterns and Best Practices

---

## Table of Contents

1. [Core Architecture](#core-architecture)
2. [Command Patterns](#command-patterns)
3. [IPC Communication](#ipc-communication)
4. [State Management](#state-management)
5. [Security & Permissions](#security--permissions)
6. [Window Management](#window-management)
7. [File System Operations](#file-system-operations)
8. [Frontend Integration](#frontend-integration)
9. [Error Handling](#error-handling)
10. [Async Patterns](#async-patterns)
11. [Testing Strategies](#testing-strategies)
12. [Build & Deployment](#build--deployment)
13. [Performance Optimization](#performance-optimization)
14. [Common Pitfalls](#common-pitfalls)

---

## Core Architecture

### Project Structure Convention

```
my-tauri-app/
├── src/                      # Frontend code
│   ├── components/
│   ├── hooks/
│   ├── services/            # API wrappers for Tauri commands
│   └── main.tsx
├── src-tauri/               # Rust backend
│   ├── src/
│   │   ├── main.rs         # Entry point
│   │   ├── commands/       # Command modules
│   │   │   ├── mod.rs
│   │   │   ├── files.rs
│   │   │   └── system.rs
│   │   ├── state.rs        # Application state
│   │   └── error.rs        # Custom error types
│   ├── Cargo.toml
│   ├── tauri.conf.json     # Tauri configuration
│   ├── build.rs            # Build script
│   └── icons/              # App icons
├── package.json
└── README.md
```

**Key Principle:** Keep frontend and backend strictly separated. Frontend in `src/`, backend in `src-tauri/`.

### The Tauri Runtime Model

```
┌────────────────────────────────────────────┐
│           Frontend (Webview)               │
│     React/Vue/Svelte/Vanilla JS            │
│                                            │
│   invoke('command', args) → Promise<T>    │
└──────────────────┬─────────────────────────┘
                   │ IPC Bridge
                   │ (JSON serialization)
┌──────────────────┴─────────────────────────┐
│           Rust Backend                     │
│                                            │
│   #[tauri::command]                        │
│   async fn command(args) -> Result<T>     │
│                                            │
│   • State management                       │
│   • File system access                     │
│   • System APIs                            │
│   • Native functionality                   │
└────────────────────────────────────────────┘
```

**Critical Understanding:**
- Frontend runs in a webview (Chromium-based on most platforms)
- Backend is a native Rust process
- Communication is **serialized** (must be JSON-compatible)
- Communication is **async** (always returns promises)

---

## Command Patterns

### Basic Command Structure

```rust
// ❌ WRONG - Synchronous, no error handling
#[tauri::command]
fn bad_command(input: String) -> String {
    do_something(input)
}

// ✅ CORRECT - Async, proper error handling
#[tauri::command]
async fn good_command(input: String) -> Result<String, String> {
    do_something(input)
        .await
        .map_err(|e| e.to_string())
}
```

**Rules:**
1. Always use `async fn` for commands (even if not doing async work)
2. Always return `Result<T, E>` where `E: Display`
3. Convert errors to `String` for frontend compatibility
4. Use `#[tauri::command]` attribute macro

### Command Registration

```rust
// src-tauri/src/main.rs
fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            // List all commands here
            read_file,
            write_file,
            get_config,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

**Important:** Every command must be registered in `generate_handler![]` or it won't be accessible from frontend.

### Command Parameter Patterns

```rust
// Simple parameters
#[tauri::command]
async fn simple(name: String, age: u32) -> Result<String, String> {
    Ok(format!("{} is {} years old", name, age))
}

// Struct parameters (must derive Deserialize)
#[derive(serde::Deserialize)]
struct UserInput {
    name: String,
    email: String,
}

#[tauri::command]
async fn with_struct(input: UserInput) -> Result<String, String> {
    Ok(format!("User: {}", input.name))
}

// Optional parameters
#[tauri::command]
async fn optional_params(
    required: String,
    optional: Option<String>,
) -> Result<String, String> {
    match optional {
        Some(val) => Ok(format!("{} - {}", required, val)),
        None => Ok(required),
    }
}

// State parameter (special)
#[tauri::command]
async fn with_state(
    state: tauri::State<'_, AppState>,
) -> Result<String, String> {
    let data = state.data.lock().await;
    Ok(data.clone())
}

// Window parameter (special)
#[tauri::command]
async fn with_window(
    window: tauri::Window,
) -> Result<(), String> {
    window.emit("my-event", "payload")
        .map_err(|e| e.to_string())
}

// App handle parameter (special)
#[tauri::command]
async fn with_app(
    app: tauri::AppHandle,
) -> Result<(), String> {
    // Can create new windows, access state, etc.
    Ok(())
}
```

**Special Parameters (injected by Tauri):**
- `tauri::State<'_, T>` - Application state
- `tauri::Window` - Current window
- `tauri::AppHandle` - Application handle
- These are NOT passed from frontend - Tauri injects them

---

## IPC Communication

### Frontend: Invoking Commands

```typescript
import { invoke } from '@tauri-apps/api/core';

// ✅ CORRECT - Typed, with error handling
async function callCommand() {
    try {
        const result = await invoke<string>('my_command', {
            arg1: 'value',
            arg2: 42,
        });
        console.log('Success:', result);
    } catch (error) {
        console.error('Error:', error);
    }
}

// ❌ WRONG - No type annotation
const result = await invoke('my_command', { arg: 'value' });
// result is 'unknown' type

// ❌ WRONG - Wrong argument structure
await invoke('my_command', 'value');  // Args must be object
```

**Rules:**
1. Always type the return value: `invoke<ReturnType>`
2. Always use try-catch or .catch()
3. Arguments must be an object with keys matching Rust parameter names
4. Argument names are converted from camelCase to snake_case automatically

### Event System (Backend → Frontend)

```rust
// Backend: Emit events
#[tauri::command]
async fn start_process(window: tauri::Window) -> Result<(), String> {
    for i in 0..10 {
        // Emit progress updates
        window.emit("progress", i)
            .map_err(|e| e.to_string())?;
        
        tokio::time::sleep(Duration::from_secs(1)).await;
    }
    
    window.emit("complete", "Done!")
        .map_err(|e| e.to_string())
}
```

```typescript
// Frontend: Listen for events
import { listen } from '@tauri-apps/api/event';

// Set up listener
const unlisten = await listen<number>('progress', (event) => {
    console.log('Progress:', event.payload);
});

// Clean up when done
unlisten();

// One-time listener
import { once } from '@tauri-apps/api/event';
await once<string>('complete', (event) => {
    console.log('Complete:', event.payload);
});
```

**Event Patterns:**
- Use for long-running operations
- Use for streaming data
- Use for status updates
- Always clean up listeners with `unlisten()`

### Event Payloads

```rust
// Simple payload
window.emit("event-name", "string payload")?;

// Struct payload (must derive Serialize)
#[derive(serde::Serialize, Clone)]
struct ProgressData {
    current: usize,
    total: usize,
    message: String,
}

window.emit("progress", ProgressData {
    current: 5,
    total: 10,
    message: "Processing...".into(),
})?;
```

```typescript
interface ProgressData {
    current: number;
    total: number;
    message: string;
}

listen<ProgressData>('progress', (event) => {
    const { current, total, message } = event.payload;
    console.log(`${current}/${total}: ${message}`);
});
```

---

## State Management

### Defining Application State

```rust
// src-tauri/src/state.rs
use std::sync::Arc;
use tokio::sync::Mutex;

pub struct AppState {
    pub database: Arc<Mutex<Database>>,
    pub config: Arc<Mutex<Config>>,
    pub cache: Arc<dashmap::DashMap<String, String>>,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            database: Arc::new(Mutex::new(Database::new())),
            config: Arc::new(Mutex::new(Config::default())),
            cache: Arc::new(dashmap::DashMap::new()),
        }
    }
}
```

**State Container Choices:**
- `Arc<Mutex<T>>` - For infrequent writes, occasional reads
- `Arc<RwLock<T>>` - For frequent reads, rare writes
- `Arc<DashMap<K, V>>` - For concurrent HashMap operations
- Plain types if immutable after initialization

### Registering State

```rust
// src-tauri/src/main.rs
fn main() {
    let state = AppState::new();
    
    tauri::Builder::default()
        .manage(state)  // Register state
        .invoke_handler(tauri::generate_handler![
            get_data,
            update_data,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### Accessing State in Commands

```rust
#[tauri::command]
async fn get_data(
    state: tauri::State<'_, AppState>
) -> Result<String, String> {
    let data = state.database.lock().await;
    Ok(data.get_value())
}

#[tauri::command]
async fn update_data(
    value: String,
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    let mut data = state.database.lock().await;
    data.set_value(value);
    Ok(())
}

// Using DashMap (lock-free)
#[tauri::command]
async fn get_cache_value(
    key: String,
    state: tauri::State<'_, AppState>,
) -> Result<Option<String>, String> {
    Ok(state.cache.get(&key).map(|v| v.clone()))
}
```

**Critical Rules:**
1. `State<'_, T>` is injected by Tauri - don't pass from frontend
2. Always use proper async lock guards
3. Don't hold locks across await points
4. Prefer DashMap for high-concurrency scenarios

### Anti-Pattern: Global Static State

```rust
// ❌ WRONG - Global mutable state
static mut GLOBAL_STATE: Option<AppState> = None;

// ✅ CORRECT - Use Tauri's state management
// Register with .manage() and access via State<'_, T>
```

---

## Security & Permissions

### Allowlist Configuration

```json
// src-tauri/tauri.conf.json
{
  "tauri": {
    "allowlist": {
      "all": false,  // NEVER set to true in production
      "fs": {
        "all": false,
        "readFile": true,
        "writeFile": true,
        "scope": [
          "$APPDATA/*",
          "$APPDATA/**/*",
          "$HOME/Documents/*"
        ]
      },
      "shell": {
        "all": false,
        "execute": true,
        "scope": [
          {
            "name": "python",
            "cmd": "python3",
            "args": true
          }
        ]
      },
      "http": {
        "all": false,
        "request": true,
        "scope": [
          "https://api.example.com/*"
        ]
      },
      "dialog": {
        "all": false,
        "open": true,
        "save": true
      }
    }
  }
}
```

**Security Principles:**
1. **Least Privilege**: Only enable what you need
2. **Scope Everything**: Use `scope` arrays to limit access
3. **Never `all: true`**: Explicitly enable features

### Path Validation

```rust
use tauri::api::path::{resolve_path, BaseDirectory};

#[tauri::command]
async fn read_app_file(
    filename: String,
    app: tauri::AppHandle,
) -> Result<String, String> {
    // ✅ CORRECT - Validate and scope paths
    let app_dir = app.path_resolver()
        .app_data_dir()
        .ok_or("Failed to get app data dir")?;
    
    // Prevent path traversal
    let safe_path = app_dir.join(&filename);
    if !safe_path.starts_with(&app_dir) {
        return Err("Invalid path".to_string());
    }
    
    tokio::fs::read_to_string(safe_path)
        .await
        .map_err(|e| e.to_string())
}

// ❌ WRONG - Arbitrary path access
#[tauri::command]
async fn read_file_unsafe(path: String) -> Result<String, String> {
    // User can pass ANY path, including /etc/passwd
    tokio::fs::read_to_string(path)
        .await
        .map_err(|e| e.to_string())
}
```

### Input Validation

```rust
#[tauri::command]
async fn execute_query(query: String) -> Result<Vec<String>, String> {
    // ✅ CORRECT - Validate input
    if query.len() > 1000 {
        return Err("Query too long".to_string());
    }
    
    if query.contains(';') {
        return Err("Invalid character in query".to_string());
    }
    
    // Proceed with validated input
    execute_safe_query(&query).await
}
```

### CSP Configuration

```json
// src-tauri/tauri.conf.json
{
  "tauri": {
    "security": {
      "csp": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:"
    }
  }
}
```

---

## Window Management

### Creating Windows

```rust
use tauri::{Manager, WindowBuilder, WindowUrl};

#[tauri::command]
async fn open_settings(app: tauri::AppHandle) -> Result<(), String> {
    let window = WindowBuilder::new(
        &app,
        "settings",  // Unique label
        WindowUrl::App("settings.html".into())
    )
    .title("Settings")
    .inner_size(800.0, 600.0)
    .resizable(true)
    .build()
    .map_err(|e| e.to_string())?;
    
    Ok(())
}
```

### Window Communication

```rust
// Send message to specific window
#[tauri::command]
async fn notify_main_window(
    app: tauri::AppHandle,
    message: String,
) -> Result<(), String> {
    if let Some(window) = app.get_window("main") {
        window.emit("notification", message)
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}

// Broadcast to all windows
#[tauri::command]
async fn broadcast_update(
    app: tauri::AppHandle,
    data: String,
) -> Result<(), String> {
    app.emit_all("update", data)
        .map_err(|e| e.to_string())
}
```

### Window Labels Convention

```rust
// Good naming conventions for window labels
const MAIN_WINDOW: &str = "main";
const SETTINGS_WINDOW: &str = "settings";
const ABOUT_WINDOW: &str = "about";

// Use constants to avoid typos
fn get_main_window(app: &tauri::AppHandle) -> Option<tauri::Window> {
    app.get_window(MAIN_WINDOW)
}
```

### Multi-Window State

```rust
#[tauri::command]
async fn get_current_window_data(
    window: tauri::Window,
    state: tauri::State<'_, AppState>,
) -> Result<WindowData, String> {
    let label = window.label();
    
    // Get window-specific data from state
    let data = state.window_data
        .lock()
        .await
        .get(label)
        .cloned()
        .ok_or("Window data not found")?;
    
    Ok(data)
}
```

---

## File System Operations

### Path Helpers

```rust
use tauri::api::path::{
    app_data_dir,
    app_config_dir,
    app_cache_dir,
};

#[tauri::command]
async fn get_app_paths(
    config: tauri::Config,
) -> Result<PathInfo, String> {
    let app_data = app_data_dir(&config)
        .ok_or("Failed to get app data dir")?;
    
    let app_config = app_config_dir(&config)
        .ok_or("Failed to get config dir")?;
    
    Ok(PathInfo {
        app_data: app_data.to_string_lossy().to_string(),
        app_config: app_config.to_string_lossy().to_string(),
    })
}
```

### Safe File Operations

```rust
use tokio::fs;
use std::path::PathBuf;

#[tauri::command]
async fn save_document(
    filename: String,
    content: String,
    app: tauri::AppHandle,
) -> Result<(), String> {
    // Get safe directory
    let app_data = app.path_resolver()
        .app_data_dir()
        .ok_or("Failed to get app data dir")?;
    
    // Ensure directory exists
    fs::create_dir_all(&app_data)
        .await
        .map_err(|e| e.to_string())?;
    
    // Construct safe path
    let file_path = app_data.join(&filename);
    
    // Validate it's still within app_data
    if !file_path.starts_with(&app_data) {
        return Err("Invalid file path".to_string());
    }
    
    // Write file
    fs::write(file_path, content)
        .await
        .map_err(|e| e.to_string())?;
    
    Ok(())
}
```

### File Dialog

```rust
use tauri::api::dialog::{blocking::FileDialogBuilder, MessageDialogBuilder};

#[tauri::command]
async fn select_file() -> Result<Option<String>, String> {
    // Use blocking dialog in async context
    let result = tokio::task::spawn_blocking(|| {
        FileDialogBuilder::new()
            .add_filter("Text Files", &["txt", "md"])
            .pick_file()
    })
    .await
    .map_err(|e| e.to_string())?;
    
    Ok(result.map(|p| p.to_string_lossy().to_string()))
}

#[tauri::command]
async fn save_file_dialog(
    default_name: String
) -> Result<Option<String>, String> {
    let result = tokio::task::spawn_blocking(move || {
        FileDialogBuilder::new()
            .set_file_name(&default_name)
            .save_file()
    })
    .await
    .map_err(|e| e.to_string())?;
    
    Ok(result.map(|p| p.to_string_lossy().to_string()))
}
```

---

## Frontend Integration

### TypeScript Service Layer Pattern

```typescript
// src/services/api.ts
import { invoke } from '@tauri-apps/api/core';

// Define return types
interface Document {
    id: string;
    title: string;
    content: string;
}

// Create service class
export class DocumentService {
    async getDocument(id: string): Promise<Document> {
        return await invoke<Document>('get_document', { id });
    }
    
    async saveDocument(doc: Document): Promise<void> {
        await invoke('save_document', { doc });
    }
    
    async listDocuments(): Promise<Document[]> {
        return await invoke<Document[]>('list_documents');
    }
}

// Export singleton
export const documentService = new DocumentService();
```

```typescript
// src/components/DocumentViewer.tsx
import { documentService } from '../services/api';

function DocumentViewer({ id }: { id: string }) {
    const [doc, setDoc] = useState<Document | null>(null);
    const [error, setError] = useState<string | null>(null);
    
    useEffect(() => {
        documentService.getDocument(id)
            .then(setDoc)
            .catch(err => setError(err.toString()));
    }, [id]);
    
    if (error) return <div>Error: {error}</div>;
    if (!doc) return <div>Loading...</div>;
    
    return <div>{doc.content}</div>;
}
```

### React Hook Pattern

```typescript
// src/hooks/useTauriCommand.ts
import { invoke } from '@tauri-apps/api/core';
import { useState, useEffect } from 'react';

export function useTauriCommand<T>(
    command: string,
    args?: Record<string, unknown>
) {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);
    
    useEffect(() => {
        invoke<T>(command, args)
            .then(setData)
            .catch(setError)
            .finally(() => setLoading(false));
    }, [command, JSON.stringify(args)]);
    
    return { data, loading, error };
}

// Usage
function MyComponent() {
    const { data, loading, error } = useTauriCommand<string>(
        'get_message',
        { userId: '123' }
    );
    
    if (loading) return <div>Loading...</div>;
    if (error) return <div>Error: {error.message}</div>;
    
    return <div>{data}</div>;
}
```

### Event Listener Hook

```typescript
// src/hooks/useTauriEvent.ts
import { listen, UnlistenFn } from '@tauri-apps/api/event';
import { useEffect, useState } from 'react';

export function useTauriEvent<T>(eventName: string) {
    const [payload, setPayload] = useState<T | null>(null);
    
    useEffect(() => {
        let unlisten: UnlistenFn | undefined;
        
        listen<T>(eventName, (event) => {
            setPayload(event.payload);
        }).then(fn => {
            unlisten = fn;
        });
        
        return () => {
            unlisten?.();
        };
    }, [eventName]);
    
    return payload;
}

// Usage
function ProgressDisplay() {
    const progress = useTauriEvent<number>('progress');
    
    return (
        <div>
            {progress !== null && `Progress: ${progress}%`}
        </div>
    );
}
```

---

## Error Handling

### Custom Error Types

```rust
// src-tauri/src/error.rs
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("File not found: {0}")]
    FileNotFound(String),
    
    #[error("Invalid input: {0}")]
    InvalidInput(String),
    
    #[error("Database error: {0}")]
    DatabaseError(#[from] sqlx::Error),
    
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
    
    #[error("Serialization error: {0}")]
    SerdeError(#[from] serde_json::Error),
}

// Convert to String for Tauri commands
impl From<AppError> for String {
    fn from(error: AppError) -> Self {
        error.to_string()
    }
}
```

```rust
// Usage in commands
#[tauri::command]
async fn load_config(path: String) -> Result<Config, String> {
    let config = read_config(&path).await?;  // AppError auto-converts
    Ok(config)
}

async fn read_config(path: &str) -> Result<Config, AppError> {
    let content = tokio::fs::read_to_string(path)
        .await
        .map_err(|_| AppError::FileNotFound(path.to_string()))?;
    
    let config: Config = serde_json::from_str(&content)?;
    Ok(config)
}
```

### Frontend Error Handling

```typescript
// Type-safe error handling
type TauriError = string;

async function handleCommand() {
    try {
        const result = await invoke<string>('my_command');
        console.log('Success:', result);
    } catch (error) {
        const errorMessage = error as TauriError;
        
        // Parse error types
        if (errorMessage.includes('File not found')) {
            showNotification('File not found', 'error');
        } else if (errorMessage.includes('Invalid input')) {
            showNotification('Invalid input', 'warning');
        } else {
            showNotification('Unknown error', 'error');
        }
    }
}
```

### Structured Error Returns

```rust
// Return structured errors instead of strings
#[derive(serde::Serialize)]
pub struct CommandError {
    code: String,
    message: String,
    details: Option<serde_json::Value>,
}

#[tauri::command]
async fn complex_operation() -> Result<String, CommandError> {
    perform_operation().await.map_err(|e| CommandError {
        code: "OPERATION_FAILED".to_string(),
        message: e.to_string(),
        details: Some(json!({ "timestamp": chrono::Utc::now() })),
    })
}
```

```typescript
interface CommandError {
    code: string;
    message: string;
    details?: any;
}

try {
    await invoke('complex_operation');
} catch (error) {
    const err = error as CommandError;
    console.error(`Error ${err.code}: ${err.message}`);
}
```

---

## Async Patterns

### Long-Running Operations

```rust
use tokio::time::{sleep, Duration};

#[tauri::command]
async fn long_operation(
    window: tauri::Window,
) -> Result<String, String> {
    for i in 0..100 {
        // Do some work
        sleep(Duration::from_millis(100)).await;
        
        // Send progress updates
        window.emit("progress", i)
            .map_err(|e| e.to_string())?;
    }
    
    Ok("Complete".to_string())
}
```

### Spawning Background Tasks

```rust
#[tauri::command]
async fn start_background_task(
    app: tauri::AppHandle,
) -> Result<(), String> {
    // Spawn task that outlives the command
    tokio::spawn(async move {
        loop {
            // Do background work
            tokio::time::sleep(Duration::from_secs(60)).await;
            
            // Send periodic updates
            if let Some(window) = app.get_window("main") {
                let _ = window.emit("background-update", "Still running");
            }
        }
    });
    
    Ok(())  // Return immediately
}
```

### Cancellation Pattern

```rust
use tokio::sync::mpsc;

pub struct TaskHandle {
    cancel_tx: mpsc::Sender<()>,
}

#[tauri::command]
async fn start_cancellable_task(
    state: tauri::State<'_, AppState>,
) -> Result<String, String> {
    let (cancel_tx, mut cancel_rx) = mpsc::channel::<()>(1);
    let task_id = uuid::Uuid::new_v4().to_string();
    
    // Store task handle
    state.tasks.lock().await.insert(
        task_id.clone(),
        TaskHandle { cancel_tx }
    );
    
    // Spawn task
    tokio::spawn(async move {
        loop {
            tokio::select! {
                _ = cancel_rx.recv() => {
                    // Task cancelled
                    break;
                }
                _ = do_work() => {
                    // Continue working
                }
            }
        }
    });
    
    Ok(task_id)
}

#[tauri::command]
async fn cancel_task(
    task_id: String,
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    let mut tasks = state.tasks.lock().await;
    if let Some(handle) = tasks.remove(&task_id) {
        let _ = handle.cancel_tx.send(()).await;
    }
    Ok(())
}
```

---

## Testing Strategies

### Unit Testing Commands

```rust
// src-tauri/src/commands/files.rs
#[tauri::command]
pub async fn read_file_content(path: String) -> Result<String, String> {
    tokio::fs::read_to_string(path)
        .await
        .map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio;
    
    #[tokio::test]
    async fn test_read_file_content() {
        // Create temp file
        let temp_dir = std::env::temp_dir();
        let test_file = temp_dir.join("test.txt");
        tokio::fs::write(&test_file, "test content").await.unwrap();
        
        // Test command
        let result = read_file_content(
            test_file.to_string_lossy().to_string()
        ).await;
        
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), "test content");
        
        // Cleanup
        tokio::fs::remove_file(test_file).await.unwrap();
    }
}
```

### Integration Testing with tauri-driver

```rust
// tests/integration_test.rs
#[cfg(test)]
mod tests {
    use tauri::test::{mock_builder, MockRuntime};
    
    #[test]
    fn test_command_integration() {
        let app = mock_builder()
            .invoke_handler(tauri::generate_handler![
                crate::commands::get_message
            ])
            .build(MockRuntime::default())
            .expect("failed to build app");
        
        // Test command invocation
        let window = app.get_window("main").unwrap();
        // ... test interactions
    }
}
```

### Frontend Testing

```typescript
// src/services/__tests__/api.test.ts
import { mockIPC } from '@tauri-apps/api/mocks';

describe('DocumentService', () => {
    beforeEach(() => {
        mockIPC((cmd, args) => {
            if (cmd === 'get_document') {
                return Promise.resolve({
                    id: args.id,
                    title: 'Test Doc',
                    content: 'Test content'
                });
            }
        });
    });
    
    it('should fetch document', async () => {
        const doc = await documentService.getDocument('123');
        expect(doc.title).toBe('Test Doc');
    });
});
```

---

## Build & Deployment

### Build Configuration

```json
// src-tauri/tauri.conf.json
{
  "build": {
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build",
    "devPath": "http://localhost:5173",
    "distDir": "../dist"
  },
  "package": {
    "productName": "MyApp",
    "version": "0.1.0"
  },
  "tauri": {
    "bundle": {
      "active": true,
      "targets": ["app", "dmg", "deb"],
      "identifier": "com.mycompany.myapp",
      "icon": [
        "icons/32x32.png",
        "icons/128x128.png",
        "icons/icon.icns",
        "icons/icon.ico"
      ]
    }
  }
}
```

### Build Commands

```bash
# Development
npm run tauri dev

# Production build
npm run tauri build

# Build for specific target
npm run tauri build -- --target x86_64-apple-darwin

# Debug build (smaller, faster compile)
npm run tauri build -- --debug
```

### Release Process

```toml
# src-tauri/Cargo.toml
[profile.release]
opt-level = "z"     # Optimize for size
lto = true          # Link-time optimization
codegen-units = 1   # Better optimization
panic = "abort"     # Smaller binary
strip = true        # Remove debug symbols
```

### Code Signing (macOS)

```bash
# Set signing identity in tauri.conf.json
{
  "tauri": {
    "bundle": {
      "macOS": {
        "signingIdentity": "Developer ID Application: Your Name (TEAMID)"
      }
    }
  }
}
```

### Updater Configuration

```json
// src-tauri/tauri.conf.json
{
  "tauri": {
    "updater": {
      "active": true,
      "endpoints": [
        "https://releases.myapp.com/{{target}}/{{current_version}}"
      ],
      "dialog": true,
      "pubkey": "YOUR_PUBLIC_KEY_HERE"
    }
  }
}
```

```rust
// Check for updates programmatically
use tauri::Manager;

#[tauri::command]
async fn check_for_updates(app: tauri::AppHandle) -> Result<(), String> {
    let update = app.updater()
        .check()
        .await
        .map_err(|e| e.to_string())?;
    
    if update.is_update_available() {
        update.download_and_install()
            .await
            .map_err(|e| e.to_string())?;
    }
    
    Ok(())
}
```

---

## Performance Optimization

### Minimize Serialization Overhead

```rust
// ❌ SLOW - Large data structure
#[tauri::command]
async fn get_all_data() -> Result<Vec<LargeStruct>, String> {
    // Returns MB of data to serialize
    Ok(get_huge_dataset())
}

// ✅ FAST - Pagination
#[tauri::command]
async fn get_data_page(
    page: usize,
    page_size: usize,
) -> Result<Vec<LargeStruct>, String> {
    Ok(get_dataset_page(page, page_size))
}

// ✅ FAST - Stream via events
#[tauri::command]
async fn stream_data(window: tauri::Window) -> Result<(), String> {
    for chunk in get_data_chunks() {
        window.emit("data-chunk", chunk)
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}
```

### Batch Operations

```rust
// ❌ SLOW - Multiple IPC calls
// Frontend calling read_file 100 times

// ✅ FAST - Single batched call
#[tauri::command]
async fn read_files(paths: Vec<String>) -> Result<Vec<FileContent>, String> {
    let mut results = Vec::new();
    
    for path in paths {
        match tokio::fs::read_to_string(&path).await {
            Ok(content) => results.push(FileContent {
                path,
                content,
                error: None,
            }),
            Err(e) => results.push(FileContent {
                path,
                content: String::new(),
                error: Some(e.to_string()),
            }),
        }
    }
    
    Ok(results)
}
```

### Caching

```rust
use std::sync::Arc;
use tokio::sync::RwLock;
use std::collections::HashMap;

pub struct Cache {
    data: Arc<RwLock<HashMap<String, CachedValue>>>,
}

#[tauri::command]
async fn get_expensive_data(
    key: String,
    state: tauri::State<'_, AppState>,
) -> Result<String, String> {
    // Check cache first
    {
        let cache = state.cache.data.read().await;
        if let Some(cached) = cache.get(&key) {
            if !cached.is_expired() {
                return Ok(cached.value.clone());
            }
        }
    }
    
    // Compute expensive value
    let value = compute_expensive_value(&key).await?;
    
    // Update cache
    {
        let mut cache = state.cache.data.write().await;
        cache.insert(key, CachedValue::new(value.clone()));
    }
    
    Ok(value)
}
```

---

## Common Pitfalls

### 1. Forgetting Async

```rust
// ❌ WRONG - Blocking operation in command
#[tauri::command]
fn read_file(path: String) -> Result<String, String> {
    std::fs::read_to_string(path)  // Blocks entire thread
        .map_err(|e| e.to_string())
}

// ✅ CORRECT - Async operation
#[tauri::command]
async fn read_file(path: String) -> Result<String, String> {
    tokio::fs::read_to_string(path)  // Non-blocking
        .await
        .map_err(|e| e.to_string())
}
```

### 2. Incorrect Error Types

```rust
// ❌ WRONG - Can't serialize std::io::Error
#[tauri::command]
async fn bad_error() -> Result<String, std::io::Error> {
    tokio::fs::read_to_string("file.txt").await
}

// ✅ CORRECT - Convert to String
#[tauri::command]
async fn good_error() -> Result<String, String> {
    tokio::fs::read_to_string("file.txt")
        .await
        .map_err(|e| e.to_string())
}
```

### 3. Holding Locks Across Await

```rust
// ❌ WRONG - Lock held across await point
#[tauri::command]
async fn bad_lock(state: tauri::State<'_, AppState>) -> Result<(), String> {
    let mut data = state.data.lock().await;
    expensive_async_operation().await?;  // Lock still held!
    data.update();
    Ok(())
}

// ✅ CORRECT - Release lock before await
#[tauri::command]
async fn good_lock(state: tauri::State<'_, AppState>) -> Result<(), String> {
    let result = expensive_async_operation().await?;
    
    {
        let mut data = state.data.lock().await;
        data.update_with(result);
    }  // Lock released here
    
    Ok(())
}
```

### 4. Case Sensitivity in Invoke

```typescript
// ❌ WRONG - JavaScript camelCase
await invoke('myCommand', { myArg: 'value' });

// ✅ CORRECT - Rust snake_case
await invoke('my_command', { my_arg: 'value' });

// Or use correct Rust function name
await invoke('my_command', { myArg: 'value' });
```

### 5. Not Cleaning Up Event Listeners

```typescript
// ❌ WRONG - Memory leak
function Component() {
    listen('my-event', (event) => {
        console.log(event);
    });
    
    return <div>Component</div>;
}

// ✅ CORRECT - Cleanup on unmount
function Component() {
    useEffect(() => {
        let unlisten: UnlistenFn | undefined;
        
        listen('my-event', (event) => {
            console.log(event);
        }).then(fn => unlisten = fn);
        
        return () => unlisten?.();
    }, []);
    
    return <div>Component</div>;
}
```

### 6. Path Traversal Vulnerabilities

```rust
// ❌ WRONG - Path traversal attack possible
#[tauri::command]
async fn read_app_file(filename: String, app: tauri::AppHandle) -> Result<String, String> {
    let app_dir = app.path_resolver().app_data_dir().unwrap();
    let path = app_dir.join(filename);  // filename could be "../../../etc/passwd"
    tokio::fs::read_to_string(path).await.map_err(|e| e.to_string())
}

// ✅ CORRECT - Validate path
#[tauri::command]
async fn read_app_file(filename: String, app: tauri::AppHandle) -> Result<String, String> {
    let app_dir = app.path_resolver().app_data_dir().unwrap();
    let path = app_dir.join(&filename);
    
    // Ensure path is still within app_dir
    if !path.starts_with(&app_dir) {
        return Err("Invalid path".to_string());
    }
    
    tokio::fs::read_to_string(path).await.map_err(|e| e.to_string())
}
```

### 7. Not Using .manage() for State

```rust
// ❌ WRONG - Can't access state
fn main() {
    let state = AppState::new();
    // Forgot to register state!
    
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![get_data])
        .run(tauri::generate_context!())
        .expect("error");
}

// ✅ CORRECT - Register state
fn main() {
    tauri::Builder::default()
        .manage(AppState::new())  // Register here
        .invoke_handler(tauri::generate_handler![get_data])
        .run(tauri::generate_context!())
        .expect("error");
}
```

---

## Best Practices Summary

### Do's ✅

1. **Always use async fn for commands**
2. **Return Result<T, String> from commands**
3. **Validate and sanitize all user input**
4. **Use State<'_, T> for shared state**
5. **Emit events for long-running operations**
6. **Type all frontend invoke calls**
7. **Clean up event listeners in React/Vue components**
8. **Use scoped allowlists in tauri.conf.json**
9. **Validate file paths to prevent traversal**
10. **Test commands with unit tests**
11. **Use service layer pattern in frontend**
12. **Convert errors to String for IPC**
13. **Use tokio::spawn for background tasks**
14. **Batch operations when possible**

### Don'ts ❌

1. **Don't use blocking operations in commands**
2. **Don't hold locks across await points**
3. **Don't enable `all: true` in allowlists**
4. **Don't pass arbitrary paths from frontend**
5. **Don't forget to register commands in generate_handler![]**
6. **Don't forget to .manage() your state**
7. **Don't return non-serializable error types**
8. **Don't leak event listeners**
9. **Don't use global mutable static state**
10. **Don't serialize huge data structures**

---

## Quick Reference

### Command Template

```rust
#[tauri::command]
async fn command_name(
    // Regular parameters
    param1: String,
    param2: u32,
    // Special injected parameters
    state: tauri::State<'_, AppState>,
    window: tauri::Window,
    app: tauri::AppHandle,
) -> Result<ReturnType, String> {
    // Implementation
    Ok(result)
}
```

### Frontend Service Template

```typescript
import { invoke } from '@tauri-apps/api/core';

export class MyService {
    async myMethod(param: string): Promise<ResultType> {
        return await invoke<ResultType>('command_name', { param });
    }
}
```

### State Template

```rust
pub struct AppState {
    pub data: Arc<Mutex<DataType>>,
}

// In main.rs
fn main() {
    tauri::Builder::default()
        .manage(AppState::new())
        .run(tauri::generate_context!())
        .expect("error");
}
```

---

This knowledge base represents the accumulated expertise of building production Tauri applications. Following these patterns will result in secure, performant, and maintainable desktop applications.
