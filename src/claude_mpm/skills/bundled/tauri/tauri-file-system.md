---
name: tauri-file-system
description: Safe file system operations in Tauri including path validation, file dialogs, directory operations, and secure file access patterns
version: 1.0.0
category: development
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Secure file operations: path validation, scoped access, file dialogs, directory management, safe read/write patterns"
    when_to_use: "When implementing file operations, document management, or any file system access in Tauri apps"
    quick_start: "1. Configure fs allowlist 2. Validate paths 3. Use app directories 4. Implement dialogs 5. Handle errors"
context_limit: 600
tags:
  - tauri
  - filesystem
  - security
  - file-operations
  - path-validation
requires_tools: []
---

# Tauri File System Operations

## Security Configuration

### Allowlist Setup

```json
// src-tauri/tauri.conf.json
{
  "tauri": {
    "allowlist": {
      "fs": {
        "all": false,
        "readFile": true,
        "writeFile": true,
        "readDir": true,
        "createDir": true,
        "removeFile": true,
        "removeDir": true,
        "renameFile": true,
        "exists": true,
        "scope": [
          "$APPDATA/**",
          "$DOCUMENT/**",
          "$DOWNLOAD/**",
          "$HOME/Documents/**"
        ]
      }
    }
  }
}
```

**Path Variables**:
- `$APPDATA` - Application data directory
- `$DOCUMENT` - User documents directory
- `$DOWNLOAD` - User downloads directory
- `$HOME` - User home directory
- `$TEMP` - Temporary directory

## Safe Path Handling

### Path Validation Pattern

```rust
use std::path::{Path, PathBuf};

fn validate_path(base_dir: &Path, user_path: &str) -> Result<PathBuf, String> {
    // Resolve the path
    let full_path = base_dir.join(user_path);

    // Canonicalize to resolve .. and symlinks
    let canonical = full_path.canonicalize()
        .map_err(|e| format!("Invalid path: {}", e))?;

    // CRITICAL: Ensure path is within base directory
    if !canonical.starts_with(base_dir) {
        return Err("Path traversal attempt detected".to_string());
    }

    Ok(canonical)
}

#[tauri::command]
async fn read_app_file(
    filename: String,
    app: tauri::AppHandle,
) -> Result<String, String> {
    let app_dir = app.path_resolver()
        .app_data_dir()
        .ok_or("Failed to get app data dir")?;

    let safe_path = validate_path(&app_dir, &filename)?;

    tokio::fs::read_to_string(safe_path)
        .await
        .map_err(|e| e.to_string())
}
```

### App Directory Helpers

```rust
use tauri::Manager;

#[tauri::command]
async fn get_app_paths(app: tauri::AppHandle) -> Result<AppPaths, String> {
    let resolver = app.path_resolver();

    Ok(AppPaths {
        app_data: resolver.app_data_dir()
            .map(|p| p.to_string_lossy().to_string()),
        app_config: resolver.app_config_dir()
            .map(|p| p.to_string_lossy().to_string()),
        app_cache: resolver.app_cache_dir()
            .map(|p| p.to_string_lossy().to_string()),
        app_log: resolver.app_log_dir()
            .map(|p| p.to_string_lossy().to_string()),
    })
}

#[derive(serde::Serialize)]
struct AppPaths {
    app_data: Option<String>,
    app_config: Option<String>,
    app_cache: Option<String>,
    app_log: Option<String>,
}
```

## File Operations

### Reading Files

```rust
use tokio::fs;

#[tauri::command]
async fn read_document(
    filename: String,
    app: tauri::AppHandle,
) -> Result<String, String> {
    let app_data = app.path_resolver()
        .app_data_dir()
        .ok_or("Failed to get app data dir")?;

    let file_path = validate_path(&app_data, &filename)?;

    // Check if file exists
    if !file_path.exists() {
        return Err(format!("File not found: {}", filename));
    }

    // Read file
    fs::read_to_string(file_path)
        .await
        .map_err(|e| format!("Failed to read file: {}", e))
}

#[tauri::command]
async fn read_binary_file(
    filename: String,
    app: tauri::AppHandle,
) -> Result<Vec<u8>, String> {
    let app_data = app.path_resolver()
        .app_data_dir()
        .ok_or("Failed to get app data dir")?;

    let file_path = validate_path(&app_data, &filename)?;

    fs::read(file_path)
        .await
        .map_err(|e| e.to_string())
}
```

### Writing Files

```rust
#[tauri::command]
async fn save_document(
    filename: String,
    content: String,
    app: tauri::AppHandle,
) -> Result<(), String> {
    let app_data = app.path_resolver()
        .app_data_dir()
        .ok_or("Failed to get app data dir")?;

    // Ensure directory exists
    fs::create_dir_all(&app_data)
        .await
        .map_err(|e| format!("Failed to create directory: {}", e))?;

    let file_path = validate_path(&app_data, &filename)?;

    // Write file
    fs::write(file_path, content)
        .await
        .map_err(|e| format!("Failed to write file: {}", e))
}

#[tauri::command]
async fn append_to_file(
    filename: String,
    content: String,
    app: tauri::AppHandle,
) -> Result<(), String> {
    use tokio::io::AsyncWriteExt;

    let app_data = app.path_resolver()
        .app_data_dir()
        .ok_or("Failed to get app data dir")?;

    let file_path = validate_path(&app_data, &filename)?;

    let mut file = fs::OpenOptions::new()
        .append(true)
        .create(true)
        .open(file_path)
        .await
        .map_err(|e| e.to_string())?;

    file.write_all(content.as_bytes())
        .await
        .map_err(|e| e.to_string())?;

    Ok(())
}
```

## Directory Operations

### Listing Directories

```rust
#[derive(serde::Serialize)]
struct FileEntry {
    name: String,
    path: String,
    is_dir: bool,
    size: u64,
    modified: Option<u64>,
}

#[tauri::command]
async fn list_directory(
    directory: String,
    app: tauri::AppHandle,
) -> Result<Vec<FileEntry>, String> {
    let app_data = app.path_resolver()
        .app_data_dir()
        .ok_or("Failed to get app data dir")?;

    let dir_path = validate_path(&app_data, &directory)?;

    let mut entries = Vec::new();
    let mut read_dir = fs::read_dir(dir_path)
        .await
        .map_err(|e| e.to_string())?;

    while let Some(entry) = read_dir.next_entry()
        .await
        .map_err(|e| e.to_string())? {

        let metadata = entry.metadata()
            .await
            .map_err(|e| e.to_string())?;

        let modified = metadata.modified()
            .ok()
            .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
            .map(|d| d.as_secs());

        entries.push(FileEntry {
            name: entry.file_name().to_string_lossy().to_string(),
            path: entry.path().to_string_lossy().to_string(),
            is_dir: metadata.is_dir(),
            size: metadata.len(),
            modified,
        });
    }

    Ok(entries)
}
```

### Creating Directories

```rust
#[tauri::command]
async fn create_directory(
    directory: String,
    app: tauri::AppHandle,
) -> Result<(), String> {
    let app_data = app.path_resolver()
        .app_data_dir()
        .ok_or("Failed to get app data dir")?;

    let dir_path = validate_path(&app_data, &directory)?;

    fs::create_dir_all(dir_path)
        .await
        .map_err(|e| format!("Failed to create directory: {}", e))
}

#[tauri::command]
async fn remove_directory(
    directory: String,
    recursive: bool,
    app: tauri::AppHandle,
) -> Result<(), String> {
    let app_data = app.path_resolver()
        .app_data_dir()
        .ok_or("Failed to get app data dir")?;

    let dir_path = validate_path(&app_data, &directory)?;

    if recursive {
        fs::remove_dir_all(dir_path)
            .await
            .map_err(|e| e.to_string())
    } else {
        fs::remove_dir(dir_path)
            .await
            .map_err(|e| e.to_string())
    }
}
```

## File Dialogs

### Open File Dialog

```rust
use tauri::api::dialog::FileDialogBuilder;

#[tauri::command]
async fn select_file() -> Result<Option<String>, String> {
    let result = tokio::task::spawn_blocking(|| {
        FileDialogBuilder::new()
            .add_filter("Text Files", &["txt", "md", "json"])
            .add_filter("All Files", &["*"])
            .set_title("Select a file")
            .pick_file()
    })
    .await
    .map_err(|e| e.to_string())?;

    Ok(result.map(|p| p.to_string_lossy().to_string()))
}

#[tauri::command]
async fn select_multiple_files() -> Result<Vec<String>, String> {
    let result = tokio::task::spawn_blocking(|| {
        FileDialogBuilder::new()
            .add_filter("Documents", &["txt", "pdf", "doc", "docx"])
            .pick_files()
    })
    .await
    .map_err(|e| e.to_string())?;

    Ok(result.map(|files| {
        files.iter()
            .map(|p| p.to_string_lossy().to_string())
            .collect()
    }).unwrap_or_default())
}
```

### Save File Dialog

```rust
#[tauri::command]
async fn save_file_dialog(
    default_name: String,
    content: String,
) -> Result<Option<String>, String> {
    let path = tokio::task::spawn_blocking(move || {
        FileDialogBuilder::new()
            .set_file_name(&default_name)
            .add_filter("Text Files", &["txt"])
            .save_file()
    })
    .await
    .map_err(|e| e.to_string())?;

    if let Some(file_path) = path {
        tokio::fs::write(&file_path, content)
            .await
            .map_err(|e| e.to_string())?;

        Ok(Some(file_path.to_string_lossy().to_string()))
    } else {
        Ok(None)
    }
}
```

### Folder Selection Dialog

```rust
#[tauri::command]
async fn select_folder() -> Result<Option<String>, String> {
    let result = tokio::task::spawn_blocking(|| {
        FileDialogBuilder::new()
            .set_title("Select a folder")
            .pick_folder()
    })
    .await
    .map_err(|e| e.to_string())?;

    Ok(result.map(|p| p.to_string_lossy().to_string()))
}
```

## Advanced File Operations

### File Watching

```rust
use notify::{Watcher, RecursiveMode, Event};

#[tauri::command]
async fn watch_file(
    filepath: String,
    window: tauri::Window,
    app: tauri::AppHandle,
) -> Result<(), String> {
    let app_data = app.path_resolver()
        .app_data_dir()
        .ok_or("Failed to get app data dir")?;

    let safe_path = validate_path(&app_data, &filepath)?;

    let (tx, mut rx) = tokio::sync::mpsc::channel(100);

    // Create watcher
    let mut watcher = notify::recommended_watcher(move |res: Result<Event, _>| {
        if let Ok(event) = res {
            let _ = tx.blocking_send(event);
        }
    }).map_err(|e| e.to_string())?;

    watcher.watch(&safe_path, RecursiveMode::NonRecursive)
        .map_err(|e| e.to_string())?;

    // Spawn task to handle events
    tokio::spawn(async move {
        while let Some(event) = rx.recv().await {
            let _ = window.emit("file-changed", event);
        }
    });

    Ok(())
}
```

### Atomic File Operations

```rust
use tokio::fs;
use uuid::Uuid;

#[tauri::command]
async fn atomic_write(
    filename: String,
    content: String,
    app: tauri::AppHandle,
) -> Result<(), String> {
    let app_data = app.path_resolver()
        .app_data_dir()
        .ok_or("Failed to get app data dir")?;

    let target_path = validate_path(&app_data, &filename)?;

    // Write to temporary file
    let temp_filename = format!("{}.tmp.{}", filename, Uuid::new_v4());
    let temp_path = validate_path(&app_data, &temp_filename)?;

    fs::write(&temp_path, content)
        .await
        .map_err(|e| format!("Failed to write temp file: {}", e))?;

    // Atomic rename
    fs::rename(temp_path, target_path)
        .await
        .map_err(|e| format!("Failed to rename file: {}", e))?;

    Ok(())
}
```

### Batch File Operations

```rust
#[derive(serde::Deserialize)]
struct BatchOperation {
    operation: String,  // "copy", "move", "delete"
    source: String,
    destination: Option<String>,
}

#[tauri::command]
async fn batch_file_operations(
    operations: Vec<BatchOperation>,
    app: tauri::AppHandle,
) -> Result<Vec<String>, String> {
    let app_data = app.path_resolver()
        .app_data_dir()
        .ok_or("Failed to get app data dir")?;

    let mut results = Vec::new();

    for op in operations {
        let source_path = validate_path(&app_data, &op.source)?;

        let result = match op.operation.as_str() {
            "copy" => {
                if let Some(dest) = op.destination {
                    let dest_path = validate_path(&app_data, &dest)?;
                    fs::copy(source_path, dest_path)
                        .await
                        .map(|_| "Success".to_string())
                        .map_err(|e| e.to_string())
                } else {
                    Err("Missing destination".to_string())
                }
            }
            "move" => {
                if let Some(dest) = op.destination {
                    let dest_path = validate_path(&app_data, &dest)?;
                    fs::rename(source_path, dest_path)
                        .await
                        .map(|_| "Success".to_string())
                        .map_err(|e| e.to_string())
                } else {
                    Err("Missing destination".to_string())
                }
            }
            "delete" => {
                fs::remove_file(source_path)
                    .await
                    .map(|_| "Success".to_string())
                    .map_err(|e| e.to_string())
            }
            _ => Err(format!("Unknown operation: {}", op.operation))
        };

        results.push(result.unwrap_or_else(|e| format!("Error: {}", e)));
    }

    Ok(results)
}
```

## Frontend Integration

### File Service Pattern

```typescript
import { invoke } from '@tauri-apps/api/core';

export class FileService {
    async readFile(filename: string): Promise<string> {
        return await invoke<string>('read_document', { filename });
    }

    async saveFile(filename: string, content: string): Promise<void> {
        await invoke('save_document', { filename, content });
    }

    async listFiles(directory: string): Promise<FileEntry[]> {
        return await invoke<FileEntry[]>('list_directory', { directory });
    }

    async selectFile(): Promise<string | null> {
        return await invoke<string | null>('select_file');
    }

    async saveFileDialog(
        defaultName: string,
        content: string
    ): Promise<string | null> {
        return await invoke<string | null>('save_file_dialog', {
            defaultName,
            content
        });
    }
}

export const fileService = new FileService();
```

## Best Practices

1. **Always validate paths** - Use `validate_path()` for all user inputs
2. **Use app directories** - Never hardcode paths, use path resolver
3. **Configure scopes strictly** - Only allow necessary directories
4. **Handle errors gracefully** - Provide meaningful error messages
5. **Use atomic writes** - For critical data, write to temp then rename
6. **Spawn blocking for dialogs** - File dialogs block thread
7. **Check file existence** - Before read/write operations
8. **Use relative paths** - Store relative to app directories
9. **Implement proper cleanup** - Remove temp files
10. **Test path traversal** - Ensure security with `../` attacks

## Security Checklist

- [ ] Allowlist configured with minimal permissions
- [ ] All paths validated with `starts_with()` check
- [ ] No hardcoded absolute paths
- [ ] User input paths go through `validate_path()`
- [ ] Scopes defined in tauri.conf.json
- [ ] File operations use tokio::fs (async)
- [ ] Error messages don't leak path information
- [ ] Temporary files cleaned up
- [ ] Symlink attacks prevented with canonicalize()

## Common Pitfalls

❌ **Not validating paths**:
```rust
// WRONG - path traversal vulnerability
#[tauri::command]
async fn read_file_unsafe(path: String) -> Result<String, String> {
    tokio::fs::read_to_string(path).await.map_err(|e| e.to_string())
}

// CORRECT - validate first
#[tauri::command]
async fn read_file_safe(
    filename: String,
    app: tauri::AppHandle,
) -> Result<String, String> {
    let app_dir = app.path_resolver().app_data_dir().unwrap();
    let safe_path = validate_path(&app_dir, &filename)?;
    tokio::fs::read_to_string(safe_path).await.map_err(|e| e.to_string())
}
```

❌ **Using blocking fs in async**:
```rust
// WRONG - blocks async runtime
std::fs::read_to_string(path)?;

// CORRECT - use tokio::fs
tokio::fs::read_to_string(path).await?;
```

❌ **Not using spawn_blocking for dialogs**:
```rust
// WRONG - blocks async runtime
FileDialogBuilder::new().pick_file();

// CORRECT - spawn blocking
tokio::task::spawn_blocking(|| {
    FileDialogBuilder::new().pick_file()
}).await?
```

## Summary

- **Always validate paths** - Prevent path traversal attacks
- **Use app directories** - Via path resolver, not hardcoded
- **Configure allowlist** - Minimum necessary permissions
- **Async file operations** - Use tokio::fs, not std::fs
- **File dialogs** - Spawn in blocking context
- **Error handling** - Provide user-friendly messages
- **Atomic operations** - Write to temp, then rename
- **Security first** - Validate, scope, sanitize all inputs
