# Tauri Framework

Complete guide to building desktop applications with Tauri 2.x - the modern alternative to Electron with web UI + Rust backend.

## Architecture Overview

### What is Tauri?

Tauri is a framework for building desktop applications using web technologies for the frontend (HTML, CSS, JavaScript) and Rust for the backend. Unlike Electron which bundles Chromium and Node.js (~100MB+), Tauri uses the OS's native webview (WebKit on macOS, WebView2 on Windows, WebKitGTK on Linux) resulting in 3-5MB bundles.

**Core Architecture:**
```
┌─────────────────────────────────────────┐
│  Frontend (Web)                         │
│  React/Vue/Svelte/Vanilla               │
│  ├─ UI Rendering                        │
│  ├─ User Interactions                   │
│  └─ invoke() calls to backend           │
└──────────────┬──────────────────────────┘
               │ IPC (JSON)
┌──────────────▼──────────────────────────┐
│  Tauri Core (Rust)                      │
│  ├─ Command Handlers                    │
│  ├─ Event System                        │
│  ├─ State Management                    │
│  └─ Plugin System                       │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Native OS APIs                         │
│  ├─ File System                         │
│  ├─ Shell/Process                       │
│  ├─ HTTP Client                         │
│  ├─ System Tray                         │
│  └─ Notifications                       │
└─────────────────────────────────────────┘
```

### Project Structure

```
my-tauri-app/
├─ src-tauri/              # Rust backend
│  ├─ src/
│  │  ├─ main.rs          # Entry point, command registration
│  │  ├─ commands/        # Command modules
│  │  ├─ state/           # Application state
│  │  └─ lib.rs           # Optional library code
│  ├─ Cargo.toml          # Rust dependencies
│  ├─ tauri.conf.json     # Tauri configuration
│  ├─ icons/              # App icons
│  └─ capabilities/       # Security capabilities (v2)
├─ src/                   # Frontend source
│  ├─ App.tsx            # Main React/Vue component
│  ├─ components/
│  ├─ styles/
│  └─ main.tsx           # Frontend entry
├─ package.json          # Node dependencies
└─ vite.config.ts        # Vite configuration
```

## Setup and Installation

### Prerequisites

```bash
# Rust toolchain (rustup.rs)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Node.js (for frontend tooling)
# Install via nvm, fnm, or nodejs.org

# Platform-specific requirements:
# Windows: WebView2, Visual Studio Build Tools
# macOS: Xcode Command Line Tools
# Linux: webkit2gtk, build-essential
```

### Create New Tauri Project

```bash
# Install Tauri CLI
cargo install tauri-cli --version "^2.0.0"

# Create project with wizard
cargo create-tauri-app

# Or with specific frontend:
npm create tauri-app@latest
# Select: Package manager (npm/yarn/pnpm)
#         Frontend framework (React/Vue/Svelte/Vanilla)
#         TypeScript (recommended: Yes)
```

### Development Workflow

```bash
# Start development server (hot reload)
cargo tauri dev
# Opens app window + watches for changes
# Frontend: Vite HMR
# Backend: Cargo watch (rebuild on .rs changes)

# Build for production
cargo tauri build
# Creates optimized bundle in src-tauri/target/release/bundle/

# Run frontend only (testing UI)
npm run dev
```

## IPC Communication

### Commands (Frontend → Backend)

Commands are Rust functions exposed to the frontend via `#[tauri::command]`.

**Basic Command:**
```rust
// src-tauri/src/main.rs
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}!", name)
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![greet])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

**Frontend Usage:**
```typescript
// src/App.tsx
import { invoke } from '@tauri-apps/api/core';

async function handleGreet() {
    const message = await invoke<string>('greet', { name: 'World' });
    console.log(message); // "Hello, World!"
}
```

### Advanced Commands with State

```rust
use tauri::State;
use std::sync::Mutex;

struct AppState {
    counter: Mutex<i32>,
}

#[tauri::command]
fn increment_counter(state: State<AppState>) -> i32 {
    let mut counter = state.counter.lock().unwrap();
    *counter += 1;
    *counter
}

#[tauri::command]
fn get_counter(state: State<AppState>) -> i32 {
    *state.counter.lock().unwrap()
}

fn main() {
    tauri::Builder::default()
        .manage(AppState {
            counter: Mutex::new(0),
        })
        .invoke_handler(tauri::generate_handler![
            increment_counter,
            get_counter
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

**Frontend:**
```typescript
import { invoke } from '@tauri-apps/api/core';

const count = await invoke<number>('increment_counter');
const current = await invoke<number>('get_counter');
```

### Async Commands with Tokio

```rust
use tokio::time::{sleep, Duration};

#[tauri::command]
async fn fetch_data(url: String) -> Result<String, String> {
    let client = reqwest::Client::new();
    let response = client
        .get(&url)
        .send()
        .await
        .map_err(|e| e.to_string())?;

    response.text().await.map_err(|e| e.to_string())
}

#[tauri::command]
async fn long_running_task() -> Result<String, String> {
    sleep(Duration::from_secs(5)).await;
    Ok("Task completed".to_string())
}
```

### Error Handling

```rust
use serde::{Serialize, Deserialize};

#[derive(Debug, Serialize, Deserialize)]
struct ApiError {
    message: String,
    code: u32,
}

impl std::fmt::Display for ApiError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "{}", self.message)
    }
}

#[tauri::command]
fn risky_operation(value: i32) -> Result<String, ApiError> {
    if value < 0 {
        return Err(ApiError {
            message: "Value must be positive".to_string(),
            code: 400,
        });
    }
    Ok(format!("Success: {}", value))
}
```

**Frontend Error Handling:**
```typescript
try {
    const result = await invoke<string>('risky_operation', { value: -1 });
} catch (error) {
    console.error('Command failed:', error);
    // error is serialized ApiError
}
```

### Events (Backend → Frontend)

Events enable pushing data from backend to frontend.

**Backend Emit:**
```rust
use tauri::{Emitter, Manager};

#[tauri::command]
async fn start_monitoring(app: tauri::AppHandle) {
    tokio::spawn(async move {
        loop {
            tokio::time::sleep(Duration::from_secs(1)).await;
            app.emit("status-update", "Running").unwrap();
        }
    });
}
```

**Frontend Listen:**
```typescript
import { listen } from '@tauri-apps/api/event';

const unlisten = await listen<string>('status-update', (event) => {
    console.log('Status:', event.payload);
});

// Later: cleanup
unlisten();
```

## Native API Access

### File System

```rust
use tauri::api::dialog::blocking::FileDialogBuilder;
use std::fs;

#[tauri::command]
fn open_file_dialog() -> Option<String> {
    FileDialogBuilder::new().pick_file()
        .map(|path| path.to_string_lossy().to_string())
}

#[tauri::command]
fn read_file_content(path: String) -> Result<String, String> {
    fs::read_to_string(path).map_err(|e| e.to_string())
}

#[tauri::command]
fn write_file_content(path: String, content: String) -> Result<(), String> {
    fs::write(path, content).map_err(|e| e.to_string())
}
```

**Frontend:**
```typescript
import { invoke } from '@tauri-apps/api/core';

async function openFile() {
    const path = await invoke<string | null>('open_file_dialog');
    if (path) {
        const content = await invoke<string>('read_file_content', { path });
        console.log(content);
    }
}
```

### System Tray

```rust
use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    Manager,
};

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&quit])?;

            let _tray = TrayIconBuilder::new()
                .menu(&menu)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .build(app)?;

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### Notifications

```rust
use tauri::Notification;

#[tauri::command]
fn send_notification(app: tauri::AppHandle, message: String) -> Result<(), String> {
    Notification::new(&app.config().identifier)
        .title("My App")
        .body(message)
        .show()
        .map_err(|e| e.to_string())
}
```

### Shell/Process Execution

```rust
use tauri::api::process::{Command, CommandEvent};

#[tauri::command]
async fn run_command(program: String, args: Vec<String>) -> Result<String, String> {
    let (mut rx, _child) = Command::new(program)
        .args(args)
        .spawn()
        .map_err(|e| e.to_string())?;

    let mut output = String::new();
    while let Some(event) = rx.recv().await {
        match event {
            CommandEvent::Stdout(line) => output.push_str(&line),
            CommandEvent::Stderr(line) => output.push_str(&line),
            CommandEvent::Terminated(_) => break,
            _ => {}
        }
    }
    Ok(output)
}
```

## Configuration

### tauri.conf.json

```json
{
  "$schema": "../node_modules/@tauri-apps/cli/schema.json",
  "productName": "My App",
  "version": "1.0.0",
  "identifier": "com.mycompany.myapp",
  "build": {
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build",
    "devUrl": "http://localhost:5173",
    "frontendDist": "../dist"
  },
  "app": {
    "windows": [
      {
        "title": "My App",
        "width": 1200,
        "height": 800,
        "resizable": true,
        "fullscreen": false,
        "minWidth": 800,
        "minHeight": 600
      }
    ],
    "security": {
      "csp": "default-src 'self'; img-src 'self' https: data:;"
    }
  },
  "bundle": {
    "active": true,
    "targets": "all",
    "icon": [
      "icons/32x32.png",
      "icons/128x128.png",
      "icons/icon.icns",
      "icons/icon.ico"
    ],
    "macOS": {
      "minimumSystemVersion": "10.13"
    },
    "windows": {
      "webviewInstallMode": {
        "type": "downloadBootstrapper"
      }
    }
  }
}
```

### Security Configuration

**Content Security Policy (CSP):**
```json
{
  "app": {
    "security": {
      "csp": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' https: data:; connect-src 'self' https://api.myapp.com"
    }
  }
}
```

**Capabilities (Tauri v2):**
```json
// src-tauri/capabilities/default.json
{
  "identifier": "default",
  "description": "Default capabilities",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "fs:allow-read-text-file",
    "fs:allow-write-text-file",
    "dialog:allow-open",
    "dialog:allow-save",
    "shell:allow-execute"
  ]
}
```

## Advanced Patterns

### Window Management

```rust
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};

#[tauri::command]
async fn open_new_window(app: tauri::AppHandle) -> Result<(), String> {
    WebviewWindowBuilder::new(
        &app,
        "new-window",
        WebviewUrl::App("index.html".into())
    )
    .title("New Window")
    .inner_size(800.0, 600.0)
    .build()
    .map_err(|e| e.to_string())?;

    Ok(())
}

#[tauri::command]
fn close_window(window: tauri::Window) -> Result<(), String> {
    window.close().map_err(|e| e.to_string())
}
```

### Custom Protocol

```rust
use tauri::{http::ResponseBuilder, Manager};

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            app.handle().plugin(
                tauri_plugin_localhost::Builder::new()
                    .build(),
            )?;
            Ok(())
        })
        .register_uri_scheme_protocol("myapp", |_app, request| {
            // Handle custom myapp:// protocol
            ResponseBuilder::new()
                .status(200)
                .body(b"Custom protocol response".to_vec())
                .map_err(Into::into)
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### Plugin Development

```rust
use tauri::{plugin::Plugin, Runtime};

pub struct MyPlugin<R: Runtime> {
    _marker: std::marker::PhantomData<R>,
}

impl<R: Runtime> Plugin<R> for MyPlugin<R> {
    fn name(&self) -> &'static str {
        "my-plugin"
    }

    fn initialize(&mut self, app: &tauri::AppHandle<R>, _config: serde_json::Value) -> tauri::plugin::Result<()> {
        // Initialize plugin
        Ok(())
    }
}

// Usage in main.rs
fn main() {
    tauri::Builder::default()
        .plugin(MyPlugin { _marker: std::marker::PhantomData })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

## Performance Optimization

### Bundle Size Reduction

**Cargo.toml optimizations:**
```toml
[profile.release]
opt-level = "z"     # Optimize for size
lto = true          # Link-time optimization
codegen-units = 1   # Better optimization
panic = "abort"     # Remove panic unwinding code
strip = true        # Strip symbols
```

### Lazy Loading

```typescript
// Frontend: Code splitting
const HeavyComponent = lazy(() => import('./HeavyComponent'));

// Backend: Lazy state initialization
use once_cell::sync::Lazy;
static EXPENSIVE_RESOURCE: Lazy<ExpensiveType> = Lazy::new(|| {
    // Initialize only when first accessed
    ExpensiveType::new()
});
```

### Debouncing IPC Calls

```typescript
import { debounce } from 'lodash';

const debouncedSearch = debounce(async (query: string) => {
    const results = await invoke('search', { query });
    setResults(results);
}, 300);
```

## Build and Distribution

### Build Commands

```bash
# Development build
cargo tauri dev

# Production build (current platform)
cargo tauri build

# Build with debug info
cargo tauri build --debug

# Specific bundle type
cargo tauri build --bundles deb,appimage  # Linux
cargo tauri build --bundles dmg,app       # macOS
cargo tauri build --bundles msi,nsis      # Windows
```

### Code Signing

**macOS:**
```bash
# Sign app
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Your Name" \
  target/release/bundle/macos/MyApp.app

# Notarize
xcrun notarytool submit target/release/bundle/dmg/MyApp.dmg \
  --apple-id "your@email.com" \
  --password "app-specific-password" \
  --team-id "TEAMID"
```

**Windows:**
```powershell
# Sign with signtool.exe
signtool sign /tr http://timestamp.digicert.com /td sha256 `
  /fd sha256 /a "target\release\MyApp.exe"
```

### Auto-Updates

```rust
// Install tauri-plugin-updater
use tauri_plugin_updater::UpdaterExt;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_updater::init())
        .setup(|app| {
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let update = handle.updater().check().await;
                // Handle update
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

## Production Examples

### File Manager Command
```rust
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Serialize, Deserialize)]
struct FileEntry {
    name: String,
    path: String,
    is_dir: bool,
    size: u64,
}

#[tauri::command]
fn list_directory(path: String) -> Result<Vec<FileEntry>, String> {
    let dir_path = PathBuf::from(path);

    if !dir_path.exists() {
        return Err("Directory does not exist".to_string());
    }

    let mut entries = Vec::new();

    for entry in fs::read_dir(dir_path).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let metadata = entry.metadata().map_err(|e| e.to_string())?;

        entries.push(FileEntry {
            name: entry.file_name().to_string_lossy().to_string(),
            path: entry.path().to_string_lossy().to_string(),
            is_dir: metadata.is_dir(),
            size: metadata.len(),
        });
    }

    Ok(entries)
}
```

### Database Integration
```rust
use sqlx::{SqlitePool, FromRow};
use tauri::State;

#[derive(FromRow, Serialize)]
struct User {
    id: i64,
    name: String,
    email: String,
}

struct DbState {
    pool: SqlitePool,
}

#[tauri::command]
async fn get_users(state: State<'_, DbState>) -> Result<Vec<User>, String> {
    sqlx::query_as::<_, User>("SELECT id, name, email FROM users")
        .fetch_all(&state.pool)
        .await
        .map_err(|e| e.to_string())
}

#[tokio::main]
async fn main() {
    let pool = SqlitePool::connect("sqlite://app.db")
        .await
        .expect("Failed to connect to database");

    tauri::Builder::default()
        .manage(DbState { pool })
        .invoke_handler(tauri::generate_handler![get_users])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

## Debugging

```bash
# Enable Rust backtraces
RUST_BACKTRACE=1 cargo tauri dev

# Open DevTools
# macOS/Linux: Cmd/Ctrl + Shift + I
# Or programmatically:
```

```rust
#[cfg(debug_assertions)]
window.open_devtools();
```

**Console logging from Rust:**
```rust
println!("Debug: {:?}", value);  // Appears in terminal
```

**Frontend console:**
```typescript
console.log('Frontend log');  // Appears in DevTools
```

This comprehensive guide covers Tauri fundamentals through advanced patterns. Combine with architecture-patterns.md for structure, state-management.md for complex state, and platform-integration.md for OS-specific features.
