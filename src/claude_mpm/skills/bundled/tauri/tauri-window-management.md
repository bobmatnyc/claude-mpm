---
name: tauri-window-management
description: Advanced window management in Tauri including multi-window apps, window creation, communication, lifecycle, and window-specific state
version: 1.0.0
category: development
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Multi-window management: creation, communication, lifecycle, window-specific state, modals, and inter-window messaging"
    when_to_use: "Building apps with multiple windows, settings dialogs, modal windows, or complex window layouts"
    quick_start: "1. Create windows with WindowBuilder 2. Use window labels 3. Emit events between windows 4. Manage window state"
context_limit: 600
tags:
  - tauri
  - windows
  - multi-window
  - window-management
  - modals
requires_tools: []
---

# Tauri Window Management

## Window Creation

### Basic Window Creation

```rust
use tauri::{Manager, WindowBuilder, WindowUrl};

#[tauri::command]
async fn open_settings(app: tauri::AppHandle) -> Result<(), String> {
    // Check if window already exists
    if app.get_window("settings").is_some() {
        return Err("Settings window already open".to_string());
    }

    WindowBuilder::new(
        &app,
        "settings",  // Unique window label
        WindowUrl::App("settings.html".into())
    )
    .title("Settings")
    .inner_size(800.0, 600.0)
    .resizable(true)
    .center()
    .build()
    .map_err(|e| e.to_string())?;

    Ok(())
}
```

### Advanced Window Configuration

```rust
#[tauri::command]
async fn create_editor_window(
    filepath: String,
    app: tauri::AppHandle,
) -> Result<String, String> {
    use tauri::WindowBuilder;

    let window_label = format!("editor-{}", uuid::Uuid::new_v4());

    let window = WindowBuilder::new(
        &app,
        window_label.clone(),
        WindowUrl::App("editor.html".into())
    )
    .title(format!("Editing: {}", filepath))
    .inner_size(1200.0, 800.0)
    .min_inner_size(400.0, 300.0)
    .resizable(true)
    .decorations(true)
    .always_on_top(false)
    .skip_taskbar(false)
    .visible(false)  // Start hidden, show after load
    .center()
    .build()
    .map_err(|e| e.to_string())?;

    // Store filepath in window config
    window.set_title(&format!("Editing: {}", filepath))
        .map_err(|e| e.to_string())?;

    // Show window after creation
    window.show().map_err(|e| e.to_string())?;

    Ok(window_label)
}
```

### Modal/Dialog Windows

```rust
#[tauri::command]
async fn open_modal_dialog(
    app: tauri::AppHandle,
    parent_label: String,
) -> Result<(), String> {
    let parent = app.get_window(&parent_label)
        .ok_or("Parent window not found")?;

    WindowBuilder::new(
        &app,
        "modal-dialog",
        WindowUrl::App("dialog.html".into())
    )
    .title("Confirm Action")
    .inner_size(400.0, 200.0)
    .resizable(false)
    .decorations(true)
    .always_on_top(true)  // Stay on top
    .skip_taskbar(true)   // Don't show in taskbar
    .center()
    .parent_window(parent.hwnd().map_err(|e| e.to_string())?)
    .build()
    .map_err(|e| e.to_string())?;

    Ok(())
}
```

## Window Communication

### Targeted Window Messaging

```rust
#[tauri::command]
async fn send_to_window(
    target_label: String,
    message: String,
    app: tauri::AppHandle,
) -> Result<(), String> {
    if let Some(window) = app.get_window(&target_label) {
        window.emit("message", message)
            .map_err(|e| e.to_string())?;
        Ok(())
    } else {
        Err(format!("Window '{}' not found", target_label))
    }
}

#[tauri::command]
async fn broadcast_to_all(
    message: String,
    app: tauri::AppHandle,
) -> Result<(), String> {
    app.emit_all("broadcast", message)
        .map_err(|e| e.to_string())
}
```

### Window-to-Window Relay

```rust
#[derive(serde::Deserialize)]
struct WindowMessage {
    target: String,
    payload: serde_json::Value,
}

#[tauri::command]
async fn relay_message(
    msg: WindowMessage,
    app: tauri::AppHandle,
) -> Result<(), String> {
    if let Some(target_window) = app.get_window(&msg.target) {
        target_window.emit("relay", msg.payload)
            .map_err(|e| e.to_string())?;
        Ok(())
    } else {
        Err(format!("Target window '{}' not found", msg.target))
    }
}
```

**Frontend sender**:
```typescript
import { invoke } from '@tauri-apps/api/core';

async function sendToWindow(target: string, data: any) {
    await invoke('relay_message', {
        msg: {
            target,
            payload: data
        }
    });
}
```

**Frontend receiver**:
```typescript
import { listen } from '@tauri-apps/api/event';

listen('relay', (event) => {
    console.log('Received from another window:', event.payload);
});
```

## Window Lifecycle

### Window Close Handling

```rust
use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .on_window_event(|event| {
            match event.event() {
                tauri::WindowEvent::CloseRequested { api, .. } => {
                    let window = event.window();

                    // Prevent close and show confirmation
                    api.prevent_close();

                    // Emit event to frontend for confirmation
                    window.emit("close-requested", ()).unwrap();
                }
                tauri::WindowEvent::Destroyed => {
                    println!("Window {} destroyed", event.window().label());
                }
                _ => {}
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

**Frontend close confirmation**:
```typescript
import { listen } from '@tauri-apps/api/event';
import { getCurrent } from '@tauri-apps/api/window';

listen('close-requested', async () => {
    const confirmed = confirm('Are you sure you want to close?');

    if (confirmed) {
        const window = getCurrent();
        await window.close();
    }
});
```

### Window Focus Management

```rust
#[tauri::command]
async fn focus_window(
    label: String,
    app: tauri::AppHandle,
) -> Result<(), String> {
    if let Some(window) = app.get_window(&label) {
        window.set_focus().map_err(|e| e.to_string())?;
        Ok(())
    } else {
        Err(format!("Window '{}' not found", label))
    }
}

#[tauri::command]
async fn minimize_window(
    label: String,
    app: tauri::AppHandle,
) -> Result<(), String> {
    if let Some(window) = app.get_window(&label) {
        window.minimize().map_err(|e| e.to_string())?;
        Ok(())
    } else {
        Err("Window not found".to_string())
    }
}

#[tauri::command]
async fn maximize_window(
    label: String,
    app: tauri::AppHandle,
) -> Result<(), String> {
    if let Some(window) = app.get_window(&label) {
        window.maximize().map_err(|e| e.to_string())?;
        Ok(())
    } else {
        Err("Window not found".to_string())
    }
}
```

## Window-Specific State

### Per-Window Data Management

```rust
use std::sync::Arc;
use dashmap::DashMap;

pub struct WindowData {
    pub filepath: Option<String>,
    pub modified: bool,
    pub cursor_position: (usize, usize),
}

pub struct AppState {
    pub window_data: Arc<DashMap<String, WindowData>>,
}

#[tauri::command]
async fn set_window_data(
    window: tauri::Window,
    filepath: String,
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    let label = window.label().to_string();

    state.window_data.insert(label, WindowData {
        filepath: Some(filepath),
        modified: false,
        cursor_position: (0, 0),
    });

    Ok(())
}

#[tauri::command]
async fn get_window_data(
    window: tauri::Window,
    state: tauri::State<'_, AppState>,
) -> Result<Option<WindowData>, String> {
    let label = window.label();

    Ok(state.window_data.get(label)
        .map(|entry| entry.value().clone()))
}

#[tauri::command]
async fn mark_window_modified(
    window: tauri::Window,
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    let label = window.label();

    if let Some(mut entry) = state.window_data.get_mut(label) {
        entry.modified = true;

        // Update window title to show modified
        window.set_title(&format!("{}*", entry.filepath.as_deref().unwrap_or("Untitled")))
            .map_err(|e| e.to_string())?;
    }

    Ok(())
}
```

## Window Management Patterns

### Window Registry

```rust
use std::collections::HashMap;

pub struct WindowRegistry {
    windows: Arc<Mutex<HashMap<String, WindowMetadata>>>,
}

#[derive(Clone)]
struct WindowMetadata {
    label: String,
    window_type: WindowType,
    created_at: SystemTime,
    parent: Option<String>,
}

#[derive(Clone)]
enum WindowType {
    Main,
    Editor,
    Settings,
    Dialog,
}

impl WindowRegistry {
    pub async fn register(&self, label: String, window_type: WindowType) {
        let mut windows = self.windows.lock().await;
        windows.insert(label.clone(), WindowMetadata {
            label,
            window_type,
            created_at: SystemTime::now(),
            parent: None,
        });
    }

    pub async fn unregister(&self, label: &str) {
        let mut windows = self.windows.lock().await;
        windows.remove(label);
    }

    pub async fn get_windows_by_type(&self, window_type: WindowType) -> Vec<String> {
        let windows = self.windows.lock().await;
        windows.values()
            .filter(|m| matches!(m.window_type, window_type))
            .map(|m| m.label.clone())
            .collect()
    }
}
```

### Single Instance Window Pattern

```rust
use std::sync::Arc;
use tokio::sync::Mutex;

pub struct SingletonWindows {
    settings: Arc<Mutex<Option<String>>>,
    about: Arc<Mutex<Option<String>>>,
}

#[tauri::command]
async fn open_settings_singleton(
    app: tauri::AppHandle,
    state: tauri::State<'_, SingletonWindows>,
) -> Result<(), String> {
    let mut settings_lock = state.settings.lock().await;

    // Check if window already exists
    if let Some(label) = settings_lock.as_ref() {
        if let Some(window) = app.get_window(label) {
            // Focus existing window
            window.set_focus().map_err(|e| e.to_string())?;
            return Ok(());
        }
    }

    // Create new window
    let label = "settings".to_string();
    WindowBuilder::new(
        &app,
        label.clone(),
        WindowUrl::App("settings.html".into())
    )
    .title("Settings")
    .build()
    .map_err(|e| e.to_string())?;

    *settings_lock = Some(label);

    Ok(())
}
```

## Frontend Window API

### Getting Current Window

```typescript
import { getCurrent, Window } from '@tauri-apps/api/window';

const currentWindow = getCurrent();
console.log('Current window label:', currentWindow.label);

// Window operations
await currentWindow.minimize();
await currentWindow.maximize();
await currentWindow.setTitle('New Title');
await currentWindow.close();
```

### Creating Windows from Frontend

```typescript
import { WebviewWindow } from '@tauri-apps/api/window';

async function createNewEditor() {
    const webview = new WebviewWindow('editor-1', {
        url: 'editor.html',
        title: 'Editor',
        width: 800,
        height: 600,
        center: true,
    });

    // Wait for window to load
    await webview.once('tauri://created', () => {
        console.log('Window created');
    });

    await webview.once('tauri://error', (e) => {
        console.error('Window creation error:', e);
    });
}
```

### Window Events

```typescript
import { getCurrent } from '@tauri-apps/api/window';

const window = getCurrent();

// Listen for window events
await window.listen('tauri://focus', () => {
    console.log('Window focused');
});

await window.listen('tauri://blur', () => {
    console.log('Window lost focus');
});

await window.listen('tauri://resize', (event) => {
    console.log('Window resized:', event.payload);
});
```

## Best Practices

1. **Use unique window labels** - Prevents collisions
2. **Check window existence** - Before creating duplicates
3. **Clean up window state** - When windows close
4. **Focus existing windows** - Instead of creating duplicates
5. **Use parent windows** - For modal dialogs
6. **Handle close requests** - Prevent data loss
7. **Emit events for communication** - Not direct window access
8. **Store window-specific data** - In centralized state
9. **Use skip_taskbar for dialogs** - Better UX
10. **Center dialogs** - Always center modal windows

## Common Patterns

### Settings Window Pattern

```rust
#[tauri::command]
async fn toggle_settings(app: tauri::AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_window("settings") {
        // Close if open
        window.close().map_err(|e| e.to_string())?;
    } else {
        // Open if closed
        WindowBuilder::new(&app, "settings", WindowUrl::App("settings.html".into()))
            .title("Settings")
            .inner_size(600.0, 400.0)
            .center()
            .build()
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}
```

### Multi-Document Interface (MDI)

```rust
use std::sync::atomic::{AtomicUsize, Ordering};

static EDITOR_COUNTER: AtomicUsize = AtomicUsize::new(0);

#[tauri::command]
async fn new_document(app: tauri::AppHandle) -> Result<String, String> {
    let id = EDITOR_COUNTER.fetch_add(1, Ordering::SeqCst);
    let label = format!("editor-{}", id);

    WindowBuilder::new(
        &app,
        label.clone(),
        WindowUrl::App("editor.html".into())
    )
    .title(format!("Untitled {}", id))
    .inner_size(800.0, 600.0)
    .build()
    .map_err(|e| e.to_string())?;

    Ok(label)
}
```

## Common Pitfalls

❌ **Creating duplicate windows without checking**:
```rust
// WRONG - may create multiple settings windows
WindowBuilder::new(&app, "settings", url).build()?;

// CORRECT - check first
if app.get_window("settings").is_none() {
    WindowBuilder::new(&app, "settings", url).build()?;
}
```

❌ **Not cleaning up window state**:
```rust
// WRONG - state persists after window closes

// CORRECT - clean up in on_window_event
.on_window_event(|event| {
    if let tauri::WindowEvent::Destroyed = event.event() {
        let label = event.window().label();
        // Clean up window-specific state
    }
})
```

❌ **Forgetting to show hidden windows**:
```rust
// WRONG - window created but invisible
let window = WindowBuilder::new(&app, label, url)
    .visible(false)
    .build()?;
// User sees nothing!

// CORRECT - show after creation
window.show()?;
```

## Summary

- **WindowBuilder** creates new windows with configuration
- **Window labels** must be unique identifiers
- **get_window()** retrieves existing window by label
- **emit()** sends events to specific windows
- **emit_all()** broadcasts to all windows
- **Window lifecycle** handled via on_window_event
- **Window-specific state** stored in DashMap with label as key
- **Singleton pattern** prevents duplicate utility windows
- **Modal dialogs** use parent_window and always_on_top
- **Frontend API** provides window control from JavaScript
