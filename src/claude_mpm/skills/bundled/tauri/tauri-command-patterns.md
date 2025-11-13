---
name: tauri-command-patterns
description: Advanced Tauri command patterns including complex parameters, special injected parameters, struct handling, and command organization
version: 1.0.0
category: development
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Advanced command patterns for Tauri: complex parameters, special injections, struct handling, and modular organization"
    when_to_use: "When commands need complex data structures, multiple special parameters, or organized command modules"
    quick_start: "1. Define struct with serde::Deserialize 2. Use special parameters (State/Window/AppHandle) 3. Organize commands in modules 4. Handle optional parameters"
context_limit: 600
tags:
  - tauri
  - commands
  - ipc
  - parameters
  - rust
requires_tools: []
---

# Tauri Advanced Command Patterns

## Complex Parameter Handling

### Struct Parameters

Commands can accept complex data structures that automatically deserialize from JSON:

```rust
use serde::Deserialize;

#[derive(Deserialize)]
struct UserInput {
    name: String,
    email: String,
    age: Option<u32>,
    preferences: Vec<String>,
}

#[tauri::command]
async fn create_user(input: UserInput) -> Result<String, String> {
    // Validate
    if input.name.is_empty() {
        return Err("Name cannot be empty".to_string());
    }

    // Process
    let user_id = save_user(&input).await?;

    Ok(format!("User created with ID: {}", user_id))
}
```

**Frontend usage**:
```typescript
const result = await invoke<string>('create_user', {
    input: {
        name: 'John Doe',
        email: 'john@example.com',
        age: 30,
        preferences: ['dark-mode', 'notifications']
    }
});
```

### Nested Structures

```rust
#[derive(Deserialize)]
struct Address {
    street: String,
    city: String,
    zip: String,
}

#[derive(Deserialize)]
struct UserProfile {
    name: String,
    email: String,
    address: Address,
    tags: HashMap<String, String>,
}

#[tauri::command]
async fn update_profile(profile: UserProfile) -> Result<(), String> {
    // Full nested structure automatically deserialized
    validate_address(&profile.address)?;
    save_profile(profile).await
}
```

### Optional Parameters

```rust
#[tauri::command]
async fn search_users(
    query: String,
    limit: Option<usize>,
    offset: Option<usize>,
) -> Result<Vec<User>, String> {
    let limit = limit.unwrap_or(10);
    let offset = offset.unwrap_or(0);

    perform_search(&query, limit, offset).await
}
```

**Frontend**:
```typescript
// All optional params
await invoke('search_users', { query: 'john' });

// Some optional params
await invoke('search_users', {
    query: 'john',
    limit: 20
});

// All params
await invoke('search_users', {
    query: 'john',
    limit: 20,
    offset: 10
});
```

## Special Injected Parameters

### State Injection

```rust
use tauri::State;

#[tauri::command]
async fn get_user_count(
    state: State<'_, AppState>
) -> Result<usize, String> {
    let db = state.database.lock().await;
    Ok(db.count_users())
}

// Multiple state parameters
#[tauri::command]
async fn complex_operation(
    input: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    // State is NOT passed from frontend
    let config = state.config.lock().await;
    process_with_config(&input, &config).await
}
```

### Window Parameter

```rust
use tauri::Window;

#[tauri::command]
async fn long_task(
    window: Window,
) -> Result<(), String> {
    for i in 0..100 {
        // Emit progress to THIS window
        window.emit("progress", i)
            .map_err(|e| e.to_string())?;

        tokio::time::sleep(Duration::from_millis(100)).await;
    }
    Ok(())
}

// Get window properties
#[tauri::command]
async fn get_window_info(
    window: Window,
) -> Result<WindowInfo, String> {
    Ok(WindowInfo {
        label: window.label().to_string(),
        title: window.title().map_err(|e| e.to_string())?,
        is_visible: window.is_visible().map_err(|e| e.to_string())?,
    })
}
```

### AppHandle Parameter

```rust
use tauri::{AppHandle, Manager};

#[tauri::command]
async fn create_new_window(
    name: String,
    app: AppHandle,
) -> Result<(), String> {
    use tauri::{WindowBuilder, WindowUrl};

    WindowBuilder::new(
        &app,
        name,
        WindowUrl::App("index.html".into())
    )
    .title("New Window")
    .build()
    .map_err(|e| e.to_string())?;

    Ok(())
}

// Access all windows
#[tauri::command]
async fn broadcast_message(
    message: String,
    app: AppHandle,
) -> Result<(), String> {
    app.emit_all("broadcast", message)
        .map_err(|e| e.to_string())
}
```

### Combining Special and Regular Parameters

```rust
#[tauri::command]
async fn save_document(
    // Regular parameters (from frontend)
    filename: String,
    content: String,
    // Special parameters (injected by Tauri)
    state: State<'_, AppState>,
    window: Window,
    app: AppHandle,
) -> Result<(), String> {
    // Validate
    if filename.is_empty() {
        return Err("Filename required".to_string());
    }

    // Get safe path
    let app_data = app.path_resolver()
        .app_data_dir()
        .ok_or("Failed to get app data dir")?;

    let file_path = app_data.join(&filename);

    // Save
    tokio::fs::write(&file_path, content)
        .await
        .map_err(|e| e.to_string())?;

    // Update state
    {
        let mut docs = state.documents.lock().await;
        docs.insert(filename.clone(), file_path);
    }

    // Notify window
    window.emit("document-saved", filename)
        .map_err(|e| e.to_string())?;

    Ok(())
}
```

**Frontend** (only passes regular parameters):
```typescript
await invoke('save_document', {
    filename: 'notes.txt',
    content: 'My content'
    // State, Window, AppHandle NOT passed - Tauri injects them
});
```

## Command Organization

### Modular Command Structure

```
src-tauri/src/
├── main.rs
├── commands/
│   ├── mod.rs
│   ├── files.rs
│   ├── database.rs
│   └── system.rs
└── state.rs
```

**commands/mod.rs**:
```rust
pub mod files;
pub mod database;
pub mod system;

// Re-export all commands
pub use files::*;
pub use database::*;
pub use system::*;
```

**commands/files.rs**:
```rust
use tauri::{AppHandle, State};
use crate::state::AppState;

#[tauri::command]
pub async fn read_file(
    path: String,
    app: AppHandle,
) -> Result<String, String> {
    // Implementation
}

#[tauri::command]
pub async fn write_file(
    path: String,
    content: String,
    app: AppHandle,
) -> Result<(), String> {
    // Implementation
}

#[tauri::command]
pub async fn list_files(
    directory: String,
    state: State<'_, AppState>,
) -> Result<Vec<String>, String> {
    // Implementation
}
```

**main.rs** registration:
```rust
mod commands;
mod state;

use commands::*;

fn main() {
    tauri::Builder::default()
        .manage(state::AppState::new())
        .invoke_handler(tauri::generate_handler![
            // File commands
            read_file,
            write_file,
            list_files,
            // Database commands
            query_database,
            insert_record,
            // System commands
            get_system_info,
            check_permissions,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### Grouped Command Namespaces

```rust
// Group related commands with prefixes
#[tauri::command]
async fn file_read(path: String) -> Result<String, String> { }

#[tauri::command]
async fn file_write(path: String, content: String) -> Result<(), String> { }

#[tauri::command]
async fn file_delete(path: String) -> Result<(), String> { }

#[tauri::command]
async fn db_query(sql: String) -> Result<Vec<Row>, String> { }

#[tauri::command]
async fn db_insert(table: String, data: HashMap<String, String>) -> Result<(), String> { }
```

**Frontend service wrappers**:
```typescript
// src/services/fileService.ts
export const fileService = {
    read: (path: string) => invoke<string>('file_read', { path }),
    write: (path: string, content: string) => invoke('file_write', { path, content }),
    delete: (path: string) => invoke('file_delete', { path }),
};

// src/services/dbService.ts
export const dbService = {
    query: (sql: string) => invoke<Row[]>('db_query', { sql }),
    insert: (table: string, data: Record<string, string>) =>
        invoke('db_insert', { table, data }),
};
```

## Advanced Parameter Patterns

### Generic Return Types

```rust
use serde::Serialize;

#[derive(Serialize)]
struct ApiResponse<T> {
    success: bool,
    data: Option<T>,
    error: Option<String>,
}

#[tauri::command]
async fn fetch_user(id: u64) -> Result<ApiResponse<User>, String> {
    match get_user(id).await {
        Ok(user) => Ok(ApiResponse {
            success: true,
            data: Some(user),
            error: None,
        }),
        Err(e) => Ok(ApiResponse {
            success: false,
            data: None,
            error: Some(e.to_string()),
        }),
    }
}
```

### Enum Parameters

```rust
use serde::Deserialize;

#[derive(Deserialize)]
#[serde(rename_all = "lowercase")]
enum SortOrder {
    Asc,
    Desc,
}

#[derive(Deserialize)]
struct QueryOptions {
    limit: usize,
    offset: usize,
    sort: SortOrder,
}

#[tauri::command]
async fn query_items(
    query: String,
    options: QueryOptions,
) -> Result<Vec<Item>, String> {
    let results = search(&query).await?;

    let sorted = match options.sort {
        SortOrder::Asc => results.sort_by_key(|i| i.date),
        SortOrder::Desc => results.sort_by_key(|i| std::cmp::Reverse(i.date)),
    };

    Ok(sorted.into_iter()
        .skip(options.offset)
        .take(options.limit)
        .collect())
}
```

**Frontend**:
```typescript
const results = await invoke<Item[]>('query_items', {
    query: 'search term',
    options: {
        limit: 20,
        offset: 0,
        sort: 'asc' // or 'desc'
    }
});
```

## Best Practices

1. **Use structs for complex data** - Better type safety and validation
2. **Validate early** - Check parameters before expensive operations
3. **Group related commands** - Use prefixes or modules
4. **Document parameters** - Use doc comments for clarity
5. **Handle optionals explicitly** - Use `unwrap_or` or `ok_or`
6. **Type special parameters last** - Convention: regular params, then State, Window, AppHandle
7. **Use meaningful error messages** - Help frontend developers debug

## Common Pitfalls

❌ **Passing special parameters from frontend**:
```typescript
// WRONG - State/Window/AppHandle are injected, not passed
await invoke('my_command', { state: someState }); // Error!
```

❌ **Forgetting serde::Deserialize**:
```rust
// WRONG - struct won't deserialize
struct MyInput {
    name: String,
}

// CORRECT
#[derive(serde::Deserialize)]
struct MyInput {
    name: String,
}
```

❌ **Incorrect parameter order**:
```rust
// WRONG - special parameters should come after regular ones
#[tauri::command]
async fn bad(
    state: State<'_, AppState>,
    input: String,  // Regular param after special
) -> Result<(), String> { }

// CORRECT
#[tauri::command]
async fn good(
    input: String,  // Regular params first
    state: State<'_, AppState>,  // Special params last
) -> Result<(), String> { }
```

## Summary

- **Structs** enable complex, validated parameters
- **Special parameters** (State/Window/AppHandle) are injected by Tauri
- **Optional parameters** use `Option<T>` with defaults
- **Organize commands** in modules for maintainability
- **Always validate** parameters before processing
- **Regular parameters come first**, special parameters last
