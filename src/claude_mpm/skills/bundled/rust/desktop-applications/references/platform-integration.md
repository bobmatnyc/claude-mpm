# Platform Integration

Comprehensive guide to integrating with native platform features across Windows, macOS, and Linux in Rust desktop applications.

## File System Access

### File Dialogs

```rust
use tauri::api::dialog::{FileDialogBuilder, MessageDialogBuilder, MessageDialogKind};

#[tauri::command]
async fn open_file_dialog() -> Result<Option<String>, String> {
    let path = FileDialogBuilder::new()
        .add_filter("Text Files", &["txt", "md"])
        .add_filter("All Files", &["*"])
        .set_title("Select a file")
        .pick_file();

    Ok(path.map(|p| p.to_string_lossy().to_string()))
}

#[tauri::command]
async fn open_folder_dialog() -> Result<Option<String>, String> {
    let path = FileDialogBuilder::new()
        .set_title("Select a folder")
        .pick_folder();

    Ok(path.map(|p| p.to_string_lossy().to_string()))
}

#[tauri::command]
async fn save_file_dialog() -> Result<Option<String>, String> {
    let path = FileDialogBuilder::new()
        .add_filter("JSON Files", &["json"])
        .set_file_name("untitled.json")
        .save_file();

    Ok(path.map(|p| p.to_string_lossy().to_string()))
}

#[tauri::command]
async fn show_message(title: String, message: String) -> Result<(), String> {
    MessageDialogBuilder::new(title, message)
        .kind(MessageDialogKind::Info)
        .show();

    Ok(())
}

#[tauri::command]
async fn confirm_dialog(title: String, message: String) -> Result<bool, String> {
    let confirmed = MessageDialogBuilder::new(title, message)
        .kind(MessageDialogKind::Warning)
        .buttons(tauri::api::dialog::MessageDialogButtons::OkCancel)
        .show();

    Ok(confirmed)
}
```

### Safe File System Operations

```rust
use std::path::{Path, PathBuf};
use std::fs;

// Validate file paths to prevent directory traversal
fn validate_path(path: &str, base_dir: &Path) -> Result<PathBuf, String> {
    let path = Path::new(path);

    // Canonicalize to resolve .. and symlinks
    let canonical = path
        .canonicalize()
        .map_err(|_| "Invalid path".to_string())?;

    // Ensure path is within base directory
    if !canonical.starts_with(base_dir) {
        return Err("Path outside allowed directory".to_string());
    }

    Ok(canonical)
}

#[tauri::command]
async fn read_file_safe(app: tauri::AppHandle, relative_path: String) -> Result<String, String> {
    let app_dir = app
        .path()
        .app_data_dir()
        .map_err(|e| e.to_string())?;

    let file_path = validate_path(&relative_path, &app_dir)?;

    fs::read_to_string(file_path).map_err(|e| e.to_string())
}

#[tauri::command]
async fn write_file_safe(
    app: tauri::AppHandle,
    relative_path: String,
    content: String,
) -> Result<(), String> {
    let app_dir = app
        .path()
        .app_data_dir()
        .map_err(|e| e.to_string())?;

    // Ensure directory exists
    fs::create_dir_all(&app_dir).map_err(|e| e.to_string())?;

    let file_path = app_dir.join(&relative_path);

    // Security check
    let canonical = file_path
        .canonicalize()
        .or_else(|_| {
            // File doesn't exist yet, validate parent
            file_path
                .parent()
                .ok_or("Invalid path")?
                .canonicalize()
                .map(|p| p.join(file_path.file_name().unwrap()))
        })
        .map_err(|_| "Invalid path".to_string())?;

    if !canonical.starts_with(&app_dir) {
        return Err("Path outside allowed directory".to_string());
    }

    fs::write(canonical, content).map_err(|e| e.to_string())
}
```

### File Watching

```rust
use notify::{Watcher, RecursiveMode, Event};
use std::sync::mpsc::channel;
use std::time::Duration;

struct FileWatcher {
    watcher: notify::RecommendedWatcher,
}

impl FileWatcher {
    fn new(app_handle: tauri::AppHandle) -> Result<Self, String> {
        let (tx, rx) = channel();

        let mut watcher = notify::recommended_watcher(tx)
            .map_err(|e| e.to_string())?;

        // Spawn task to handle events
        tokio::spawn(async move {
            while let Ok(event) = rx.recv() {
                if let Ok(Event { kind, paths, .. }) = event {
                    let _ = app_handle.emit("file-changed", FileChangeEvent {
                        kind: format!("{:?}", kind),
                        paths: paths.iter().map(|p| p.to_string_lossy().to_string()).collect(),
                    });
                }
            }
        });

        Ok(Self { watcher })
    }

    fn watch(&mut self, path: &str) -> Result<(), String> {
        self.watcher
            .watch(Path::new(path), RecursiveMode::Recursive)
            .map_err(|e| e.to_string())
    }

    fn unwatch(&mut self, path: &str) -> Result<(), String> {
        self.watcher
            .unwatch(Path::new(path))
            .map_err(|e| e.to_string())
    }
}

#[derive(Clone, serde::Serialize)]
struct FileChangeEvent {
    kind: String,
    paths: Vec<String>,
}

#[tauri::command]
fn watch_directory(
    watcher: tauri::State<FileWatcher>,
    path: String,
) -> Result<(), String> {
    watcher.inner().lock().unwrap().watch(&path)
}
```

## System Tray Integration

### Cross-Platform System Tray

```rust
use tauri::{
    menu::{Menu, MenuItem, Submenu},
    tray::{TrayIconBuilder, TrayIconEvent},
    Manager, Runtime,
};

fn create_tray<R: Runtime>(app: &tauri::AppHandle<R>) -> Result<(), Box<dyn std::error::Error>> {
    // Create menu items
    let show_item = MenuItem::with_id(app, "show", "Show Window", true, None::<&str>)?;
    let hide_item = MenuItem::with_id(app, "hide", "Hide Window", true, None::<&str>)?;
    let quit_item = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;

    // Create submenu
    let settings_menu = Submenu::with_items(
        app,
        "Settings",
        true,
        &[
            &MenuItem::with_id(app, "preferences", "Preferences", true, None::<&str>)?,
            &MenuItem::with_id(app, "about", "About", true, None::<&str>)?,
        ],
    )?;

    // Create menu
    let menu = Menu::with_items(app, &[&show_item, &hide_item, &settings_menu, &quit_item])?;

    // Build tray icon
    let _tray = TrayIconBuilder::new()
        .icon(app.default_window_icon().unwrap().clone())
        .menu(&menu)
        .tooltip("My Application")
        .on_menu_event(|app, event| match event.id.as_ref() {
            "show" => {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
            "hide" => {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.hide();
                }
            }
            "quit" => {
                app.exit(0);
            }
            "preferences" => {
                // Open preferences window
                println!("Open preferences");
            }
            "about" => {
                // Show about dialog
                println!("Show about dialog");
            }
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click { .. } = event {
                // Handle tray icon click
                let app = tray.app_handle();
                if let Some(window) = app.get_webview_window("main") {
                    if window.is_visible().unwrap_or(false) {
                        let _ = window.hide();
                    } else {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                }
            }
        })
        .build(app)?;

    Ok(())
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            create_tray(app.handle())?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### Dynamic Tray Menu Updates

```rust
use std::sync::Mutex;

struct TrayState {
    is_recording: Mutex<bool>,
}

#[tauri::command]
fn toggle_recording(
    app: tauri::AppHandle,
    state: tauri::State<TrayState>,
) -> Result<(), String> {
    let mut is_recording = state.is_recording.lock().unwrap();
    *is_recording = !*is_recording;

    // Update tray menu
    let tray = app.tray_by_id("main").ok_or("Tray not found")?;

    let menu_item = tray
        .get_item("toggle_recording")
        .ok_or("Menu item not found")?;

    menu_item
        .set_text(if *is_recording {
            "Stop Recording"
        } else {
            "Start Recording"
        })
        .map_err(|e| e.to_string())?;

    Ok(())
}
```

## Native Notifications

### Cross-Platform Notifications

```rust
use tauri::Notification;

#[tauri::command]
fn send_notification(
    app: tauri::AppHandle,
    title: String,
    body: String,
) -> Result<(), String> {
    Notification::new(&app.config().identifier)
        .title(title)
        .body(body)
        .icon("icon")
        .show()
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn send_notification_with_action(
    app: tauri::AppHandle,
    title: String,
    body: String,
) -> Result<(), String> {
    // Note: Actions are platform-dependent
    #[cfg(target_os = "macos")]
    {
        Notification::new(&app.config().identifier)
            .title(title)
            .body(body)
            .sound("default")
            .show()
            .map_err(|e| e.to_string())
    }

    #[cfg(not(target_os = "macos"))]
    {
        Notification::new(&app.config().identifier)
            .title(title)
            .body(body)
            .show()
            .map_err(|e| e.to_string())
    }
}
```

### Notification with User Interaction

```rust
use tauri::{Emitter, Manager};

#[tauri::command]
async fn send_interactive_notification(
    app: tauri::AppHandle,
    title: String,
    body: String,
) -> Result<(), String> {
    // Send notification
    Notification::new(&app.config().identifier)
        .title(&title)
        .body(&body)
        .show()
        .map_err(|e| e.to_string())?;

    // Listen for notification clicks (platform-dependent)
    // This is a simplified example; real implementation needs platform-specific code

    Ok(())
}
```

## Auto-Updates

### Tauri Updater Integration

```rust
use tauri_plugin_updater::UpdaterExt;

#[tauri::command]
async fn check_for_updates(app: tauri::AppHandle) -> Result<Option<String>, String> {
    let update = app
        .updater()
        .check()
        .await
        .map_err(|e| e.to_string())?;

    if let Some(update) = update {
        Ok(Some(format!(
            "Update available: {} (current: {})",
            update.version,
            update.current_version
        )))
    } else {
        Ok(None)
    }
}

#[tauri::command]
async fn install_update(app: tauri::AppHandle) -> Result<(), String> {
    let update = app
        .updater()
        .check()
        .await
        .map_err(|e| e.to_string())?;

    if let Some(update) = update {
        // Download and install
        update
            .download_and_install(
                |chunk_length, content_length| {
                    println!(
                        "Downloaded {} of {:?}",
                        chunk_length,
                        content_length
                    );
                },
                || {
                    println!("Download finished");
                },
            )
            .await
            .map_err(|e| e.to_string())?;

        // Restart app
        app.restart();
    }

    Ok(())
}

// Setup auto-update check
fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .setup(|app| {
            let handle = app.handle().clone();

            // Check for updates on startup
            tauri::async_runtime::spawn(async move {
                tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;

                if let Ok(Some(update)) = handle.updater().check().await {
                    println!("Update available: {}", update.version);

                    // Emit event to frontend
                    let _ = handle.emit("update-available", &update.version);
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

## Deep Linking / Custom URL Schemes

### Register URL Scheme

**tauri.conf.json:**
```json
{
  "bundle": {
    "macOS": {
      "associatedDomains": ["myapp://"],
      "category": "public.app-category.developer-tools"
    },
    "windows": {
      "webviewInstallMode": {
        "type": "downloadBootstrapper"
      },
      "protocols": [
        {
          "name": "myapp",
          "schemes": ["myapp"]
        }
      ]
    }
  }
}
```

### Handle Deep Links

```rust
use tauri::{Emitter, Manager};

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // Register URL handler
            app.listen_any("deep-link://", |event| {
                println!("Received deep link: {:?}", event.payload());
            });

            Ok(())
        })
        .plugin(tauri_plugin_deep_link::init())
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[tauri::command]
fn handle_url(app: tauri::AppHandle, url: String) -> Result<(), String> {
    println!("Handling URL: {}", url);

    // Parse URL and navigate
    if url.starts_with("myapp://open/") {
        let file = url.strip_prefix("myapp://open/").unwrap();
        app.emit("open-file", file).map_err(|e| e.to_string())?;
    }

    Ok(())
}
```

## Platform-Specific Features

### Windows

```rust
#[cfg(target_os = "windows")]
mod windows {
    use winapi::um::winuser::{MessageBoxW, MB_OK};
    use std::ffi::OsStr;
    use std::os::windows::ffi::OsStrExt;

    pub fn show_native_message_box(title: &str, message: &str) {
        let title_wide: Vec<u16> = OsStr::new(title)
            .encode_wide()
            .chain(std::iter::once(0))
            .collect();

        let message_wide: Vec<u16> = OsStr::new(message)
            .encode_wide()
            .chain(std::iter::once(0))
            .collect();

        unsafe {
            MessageBoxW(
                std::ptr::null_mut(),
                message_wide.as_ptr(),
                title_wide.as_ptr(),
                MB_OK,
            );
        }
    }

    // Windows Registry access
    use winreg::enums::*;
    use winreg::RegKey;

    pub fn read_registry_value(key_path: &str, value_name: &str) -> Option<String> {
        let hklm = RegKey::predef(HKEY_CURRENT_USER);
        let key = hklm.open_subkey(key_path).ok()?;
        key.get_value(value_name).ok()
    }

    pub fn write_registry_value(
        key_path: &str,
        value_name: &str,
        value: &str,
    ) -> Result<(), std::io::Error> {
        let hklm = RegKey::predef(HKEY_CURRENT_USER);
        let (key, _) = hklm.create_subkey(key_path)?;
        key.set_value(value_name, &value)?;
        Ok(())
    }
}

#[tauri::command]
#[cfg(target_os = "windows")]
fn windows_specific_feature() -> Result<String, String> {
    windows::show_native_message_box("Title", "Message");

    let value = windows::read_registry_value(
        "Software\\MyApp",
        "Setting1",
    )
    .unwrap_or_default();

    Ok(value)
}
```

### macOS

```rust
#[cfg(target_os = "macos")]
mod macos {
    use cocoa::base::nil;
    use cocoa::foundation::NSString;
    use objc::{class, msg_send, sel, sel_impl};

    pub fn set_dock_badge(label: &str) {
        unsafe {
            let app = cocoa::appkit::NSApp();
            let dock_tile: cocoa::base::id = msg_send![app, dockTile];

            let badge_label = NSString::alloc(nil).init_str(label);
            let _: () = msg_send![dock_tile, setBadgeLabel: badge_label];
        }
    }

    pub fn clear_dock_badge() {
        unsafe {
            let app = cocoa::appkit::NSApp();
            let dock_tile: cocoa::base::id = msg_send![app, dockTile];
            let _: () = msg_send![dock_tile, setBadgeLabel: nil];
        }
    }

    // Access macOS services
    use std::process::Command;

    pub fn trigger_notification_center(title: &str, message: &str) {
        let script = format!(
            r#"display notification "{}" with title "{}""#,
            message, title
        );

        Command::new("osascript")
            .arg("-e")
            .arg(script)
            .output()
            .ok();
    }
}

#[tauri::command]
#[cfg(target_os = "macos")]
fn macos_specific_feature(badge: String) -> Result<(), String> {
    macos::set_dock_badge(&badge);
    Ok(())
}

#[tauri::command]
#[cfg(target_os = "macos")]
fn clear_badge() -> Result<(), String> {
    macos::clear_dock_badge();
    Ok(())
}
```

### Linux

```rust
#[cfg(target_os = "linux")]
mod linux {
    use std::process::Command;

    pub fn send_desktop_notification(title: &str, message: &str) -> Result<(), String> {
        Command::new("notify-send")
            .arg(title)
            .arg(message)
            .output()
            .map_err(|e| e.to_string())?;

        Ok(())
    }

    // D-Bus integration
    use dbus::blocking::Connection;
    use std::time::Duration;

    pub fn get_desktop_environment() -> Result<String, Box<dyn std::error::Error>> {
        let conn = Connection::new_session()?;
        let proxy = conn.with_proxy(
            "org.freedesktop.portal.Desktop",
            "/org/freedesktop/portal/desktop",
            Duration::from_millis(5000),
        );

        // Query desktop environment
        // This is a simplified example
        Ok("Unknown".to_string())
    }
}

#[tauri::command]
#[cfg(target_os = "linux")]
fn linux_specific_feature(title: String, message: String) -> Result<(), String> {
    linux::send_desktop_notification(&title, &message)
}
```

## Permissions and Security

### Scope Configuration

```rust
use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // Configure file system scope
            let scope = app.fs_scope();

            // Allow access to specific directories
            let app_data_dir = app.path().app_data_dir()?;
            scope.allow_directory(&app_data_dir, true)?;

            let documents_dir = app.path().document_dir()?;
            scope.allow_directory(&documents_dir, false)?;

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### Runtime Permission Checks

```rust
use tauri::Manager;

#[tauri::command]
fn read_file_with_permission(
    app: tauri::AppHandle,
    path: String,
) -> Result<String, String> {
    let scope = app.fs_scope();

    // Check if path is allowed
    if !scope.is_allowed(&path) {
        return Err("Access denied: path not in scope".to_string());
    }

    std::fs::read_to_string(&path).map_err(|e| e.to_string())
}

#[tauri::command]
fn request_file_access(
    app: tauri::AppHandle,
    path: String,
) -> Result<(), String> {
    let scope = app.fs_scope();

    // Request access (user must approve via dialog)
    scope
        .allow_file(&path)
        .map_err(|e| e.to_string())?;

    Ok(())
}
```

These platform integration patterns enable full access to native OS features while maintaining cross-platform compatibility and security.
