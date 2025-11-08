# Architecture Patterns

Desktop-specific architectural patterns for building maintainable, scalable Rust applications with clear separation of concerns.

## Core Architectural Patterns

### MVC (Model-View-Controller)

Traditional pattern adapted for desktop applications.

```rust
// Model - Application state and business logic
mod model {
    use serde::{Deserialize, Serialize};

    #[derive(Clone, Debug, Serialize, Deserialize)]
    pub struct User {
        pub id: u64,
        pub name: String,
        pub email: String,
    }

    #[derive(Clone, Debug)]
    pub struct UserModel {
        users: Vec<User>,
    }

    impl UserModel {
        pub fn new() -> Self {
            Self { users: Vec::new() }
        }

        pub fn add_user(&mut self, user: User) {
            self.users.push(user);
        }

        pub fn remove_user(&mut self, id: u64) {
            self.users.retain(|u| u.id != id);
        }

        pub fn get_users(&self) -> &[User] {
            &self.users
        }

        pub fn find_user(&self, id: u64) -> Option<&User> {
            self.users.iter().find(|u| u.id == id)
        }
    }
}

// Controller - Handles user input and updates model
mod controller {
    use super::model::{User, UserModel};

    pub struct UserController {
        model: UserModel,
    }

    impl UserController {
        pub fn new(model: UserModel) -> Self {
            Self { model }
        }

        pub fn create_user(&mut self, name: String, email: String) -> Result<(), String> {
            // Validation
            if name.is_empty() {
                return Err("Name cannot be empty".to_string());
            }

            let id = self.model.get_users().len() as u64 + 1;
            let user = User { id, name, email };

            self.model.add_user(user);
            Ok(())
        }

        pub fn delete_user(&mut self, id: u64) -> Result<(), String> {
            if self.model.find_user(id).is_none() {
                return Err("User not found".to_string());
            }

            self.model.remove_user(id);
            Ok(())
        }

        pub fn get_model(&self) -> &UserModel {
            &self.model
        }
    }
}

// View - UI rendering (Tauri example)
#[tauri::command]
fn get_users(controller: tauri::State<UserController>) -> Vec<User> {
    controller.get_model().get_users().to_vec()
}

#[tauri::command]
fn create_user(
    controller: tauri::State<UserController>,
    name: String,
    email: String,
) -> Result<(), String> {
    controller.inner().lock().unwrap().create_user(name, email)
}
```

### MVVM (Model-View-ViewModel)

Better for reactive UIs with two-way data binding.

```rust
use std::sync::{Arc, Mutex};
use tokio::sync::broadcast;

// Model - Business data
#[derive(Clone, Debug)]
pub struct TodoItem {
    pub id: u64,
    pub title: String,
    pub completed: bool,
}

pub struct TodoModel {
    items: Vec<TodoItem>,
    next_id: u64,
}

impl TodoModel {
    pub fn new() -> Self {
        Self {
            items: Vec::new(),
            next_id: 1,
        }
    }

    pub fn add_item(&mut self, title: String) -> TodoItem {
        let item = TodoItem {
            id: self.next_id,
            title,
            completed: false,
        };
        self.next_id += 1;
        self.items.push(item.clone());
        item
    }

    pub fn toggle_item(&mut self, id: u64) -> Option<bool> {
        self.items
            .iter_mut()
            .find(|item| item.id == id)
            .map(|item| {
                item.completed = !item.completed;
                item.completed
            })
    }

    pub fn get_items(&self) -> &[TodoItem] {
        &self.items
    }
}

// ViewModel - Presentation logic and state
pub struct TodoViewModel {
    model: Arc<Mutex<TodoModel>>,
    change_notifier: broadcast::Sender<ViewModelEvent>,
}

#[derive(Clone, Debug)]
pub enum ViewModelEvent {
    ItemAdded(TodoItem),
    ItemToggled(u64, bool),
    ItemsChanged,
}

impl TodoViewModel {
    pub fn new() -> Self {
        let (tx, _rx) = broadcast::channel(100);
        Self {
            model: Arc::new(Mutex::new(TodoModel::new())),
            change_notifier: tx,
        }
    }

    pub fn add_todo(&self, title: String) -> Result<(), String> {
        if title.trim().is_empty() {
            return Err("Title cannot be empty".to_string());
        }

        let mut model = self.model.lock().unwrap();
        let item = model.add_item(title);
        drop(model);

        let _ = self.change_notifier.send(ViewModelEvent::ItemAdded(item));
        Ok(())
    }

    pub fn toggle_todo(&self, id: u64) -> Result<(), String> {
        let mut model = self.model.lock().unwrap();
        let completed = model
            .toggle_item(id)
            .ok_or("Item not found".to_string())?;
        drop(model);

        let _ = self
            .change_notifier
            .send(ViewModelEvent::ItemToggled(id, completed));
        Ok(())
    }

    pub fn get_todos(&self) -> Vec<TodoItem> {
        self.model.lock().unwrap().get_items().to_vec()
    }

    pub fn subscribe(&self) -> broadcast::Receiver<ViewModelEvent> {
        self.change_notifier.subscribe()
    }
}

// View - Tauri commands
#[tauri::command]
async fn add_todo(viewmodel: tauri::State<'_, TodoViewModel>, title: String) -> Result<(), String> {
    viewmodel.add_todo(title)
}

#[tauri::command]
async fn toggle_todo(viewmodel: tauri::State<'_, TodoViewModel>, id: u64) -> Result<(), String> {
    viewmodel.toggle_todo(id)
}

#[tauri::command]
async fn get_todos(viewmodel: tauri::State<'_, TodoViewModel>) -> Vec<TodoItem> {
    viewmodel.get_todos()
}

// Setup with change notifications
fn main() {
    let viewmodel = TodoViewModel::new();
    let mut rx = viewmodel.subscribe();

    // Background task to push updates to frontend
    tokio::spawn(async move {
        while let Ok(event) = rx.recv().await {
            // Emit event to frontend
            println!("ViewModel changed: {:?}", event);
        }
    });

    tauri::Builder::default()
        .manage(viewmodel)
        .invoke_handler(tauri::generate_handler![add_todo, toggle_todo, get_todos])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### Command Pattern

Encapsulate actions as objects for undo/redo functionality.

```rust
use std::fmt;

// Command trait
pub trait Command: fmt::Debug {
    fn execute(&mut self, app: &mut Application) -> Result<(), String>;
    fn undo(&mut self, app: &mut Application) -> Result<(), String>;
    fn description(&self) -> String;
}

// Application state
pub struct Application {
    pub text: String,
    pub cursor: usize,
}

// Concrete commands
#[derive(Debug)]
pub struct InsertTextCommand {
    text: String,
    position: usize,
}

impl Command for InsertTextCommand {
    fn execute(&mut self, app: &mut Application) -> Result<(), String> {
        app.text.insert_str(self.position, &self.text);
        app.cursor = self.position + self.text.len();
        Ok(())
    }

    fn undo(&mut self, app: &mut Application) -> Result<(), String> {
        let start = self.position;
        let end = self.position + self.text.len();
        app.text.drain(start..end);
        app.cursor = self.position;
        Ok(())
    }

    fn description(&self) -> String {
        format!("Insert '{}'", self.text)
    }
}

#[derive(Debug)]
pub struct DeleteTextCommand {
    deleted_text: String,
    position: usize,
    length: usize,
}

impl Command for DeleteTextCommand {
    fn execute(&mut self, app: &mut Application) -> Result<(), String> {
        let start = self.position;
        let end = self.position + self.length;
        self.deleted_text = app.text.drain(start..end).collect();
        app.cursor = self.position;
        Ok(())
    }

    fn undo(&mut self, app: &mut Application) -> Result<(), String> {
        app.text.insert_str(self.position, &self.deleted_text);
        app.cursor = self.position + self.deleted_text.len();
        Ok(())
    }

    fn description(&self) -> String {
        format!("Delete {} characters", self.length)
    }
}

// Command manager with undo/redo
pub struct CommandManager {
    history: Vec<Box<dyn Command>>,
    current: usize,
}

impl CommandManager {
    pub fn new() -> Self {
        Self {
            history: Vec::new(),
            current: 0,
        }
    }

    pub fn execute(&mut self, mut command: Box<dyn Command>, app: &mut Application) -> Result<(), String> {
        command.execute(app)?;

        // Clear redo history
        self.history.truncate(self.current);
        self.history.push(command);
        self.current += 1;

        Ok(())
    }

    pub fn undo(&mut self, app: &mut Application) -> Result<(), String> {
        if self.current == 0 {
            return Err("Nothing to undo".to_string());
        }

        self.current -= 1;
        self.history[self.current].undo(app)?;
        Ok(())
    }

    pub fn redo(&mut self, app: &mut Application) -> Result<(), String> {
        if self.current >= self.history.len() {
            return Err("Nothing to redo".to_string());
        }

        self.history[self.current].execute(app)?;
        self.current += 1;
        Ok(())
    }

    pub fn can_undo(&self) -> bool {
        self.current > 0
    }

    pub fn can_redo(&self) -> bool {
        self.current < self.history.len()
    }

    pub fn get_history(&self) -> Vec<String> {
        self.history
            .iter()
            .take(self.current)
            .map(|cmd| cmd.description())
            .collect()
    }
}

// Tauri integration
use std::sync::Mutex;

struct AppState {
    app: Mutex<Application>,
    commands: Mutex<CommandManager>,
}

#[tauri::command]
fn insert_text(state: tauri::State<AppState>, text: String, position: usize) -> Result<(), String> {
    let mut app = state.app.lock().unwrap();
    let mut commands = state.commands.lock().unwrap();

    let command = Box::new(InsertTextCommand { text, position });
    commands.execute(command, &mut app)
}

#[tauri::command]
fn undo(state: tauri::State<AppState>) -> Result<(), String> {
    let mut app = state.app.lock().unwrap();
    let mut commands = state.commands.lock().unwrap();
    commands.undo(&mut app)
}

#[tauri::command]
fn redo(state: tauri::State<AppState>) -> Result<(), String> {
    let mut app = state.app.lock().unwrap();
    let mut commands = state.commands.lock().unwrap();
    commands.redo(&mut app)
}
```

## Event-Driven Architecture

### Event Bus Pattern

```rust
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use tokio::sync::mpsc;

// Event types
#[derive(Clone, Debug)]
pub enum AppEvent {
    UserLoggedIn { user_id: u64, username: String },
    FileOpened { path: String },
    DataChanged { entity: String, id: u64 },
    ErrorOccurred { message: String },
}

// Event handler trait
pub trait EventHandler: Send + Sync {
    fn handle(&self, event: &AppEvent);
}

// Event bus
pub struct EventBus {
    handlers: Arc<Mutex<HashMap<String, Vec<Arc<dyn EventHandler>>>>>,
    sender: mpsc::UnboundedSender<AppEvent>,
}

impl EventBus {
    pub fn new() -> Self {
        let handlers = Arc::new(Mutex::new(HashMap::new()));
        let handlers_clone = handlers.clone();

        let (sender, mut receiver) = mpsc::unbounded_channel();

        // Background task to dispatch events
        tokio::spawn(async move {
            while let Some(event) = receiver.recv().await {
                let event_type = format!("{:?}", event).split('{').next().unwrap().trim().to_string();
                let handlers = handlers_clone.lock().unwrap();

                if let Some(handlers_list) = handlers.get(&event_type) {
                    for handler in handlers_list {
                        handler.handle(&event);
                    }
                }
            }
        });

        Self { handlers, sender }
    }

    pub fn subscribe(&self, event_type: &str, handler: Arc<dyn EventHandler>) {
        let mut handlers = self.handlers.lock().unwrap();
        handlers
            .entry(event_type.to_string())
            .or_insert_with(Vec::new)
            .push(handler);
    }

    pub fn publish(&self, event: AppEvent) {
        let _ = self.sender.send(event);
    }
}

// Example handlers
struct LoggingHandler;

impl EventHandler for LoggingHandler {
    fn handle(&self, event: &AppEvent) {
        println!("[LOG] Event: {:?}", event);
    }
}

struct AnalyticsHandler;

impl EventHandler for AnalyticsHandler {
    fn handle(&self, event: &AppEvent) {
        // Send to analytics service
        println!("[ANALYTICS] Tracking: {:?}", event);
    }
}

// Usage
fn setup_event_bus() -> EventBus {
    let event_bus = EventBus::new();

    event_bus.subscribe("UserLoggedIn", Arc::new(LoggingHandler));
    event_bus.subscribe("UserLoggedIn", Arc::new(AnalyticsHandler));

    event_bus
}

#[tauri::command]
fn login_user(
    event_bus: tauri::State<EventBus>,
    user_id: u64,
    username: String,
) -> Result<(), String> {
    // Perform login logic...

    event_bus.publish(AppEvent::UserLoggedIn { user_id, username });

    Ok(())
}
```

## Plugin System

### Dynamic Plugin Architecture

```rust
use std::collections::HashMap;
use std::sync::Arc;

// Plugin trait
pub trait Plugin: Send + Sync {
    fn name(&self) -> &str;
    fn version(&self) -> &str;
    fn initialize(&mut self, context: &PluginContext) -> Result<(), String>;
    fn shutdown(&mut self) -> Result<(), String>;
    fn execute(&self, command: &str, args: Vec<String>) -> Result<String, String>;
}

// Plugin context (shared resources)
pub struct PluginContext {
    pub app_name: String,
    pub config_dir: String,
}

// Plugin manager
pub struct PluginManager {
    plugins: HashMap<String, Box<dyn Plugin>>,
    context: Arc<PluginContext>,
}

impl PluginManager {
    pub fn new(context: PluginContext) -> Self {
        Self {
            plugins: HashMap::new(),
            context: Arc::new(context),
        }
    }

    pub fn register(&mut self, mut plugin: Box<dyn Plugin>) -> Result<(), String> {
        let name = plugin.name().to_string();

        plugin.initialize(&self.context)?;
        self.plugins.insert(name.clone(), plugin);

        println!("Plugin registered: {}", name);
        Ok(())
    }

    pub fn execute(
        &self,
        plugin_name: &str,
        command: &str,
        args: Vec<String>,
    ) -> Result<String, String> {
        self.plugins
            .get(plugin_name)
            .ok_or_else(|| format!("Plugin '{}' not found", plugin_name))?
            .execute(command, args)
    }

    pub fn list_plugins(&self) -> Vec<(String, String)> {
        self.plugins
            .values()
            .map(|p| (p.name().to_string(), p.version().to_string()))
            .collect()
    }

    pub fn shutdown_all(&mut self) -> Result<(), String> {
        for (name, plugin) in self.plugins.iter_mut() {
            plugin.shutdown().map_err(|e| {
                format!("Failed to shutdown plugin '{}': {}", name, e)
            })?;
        }
        Ok(())
    }
}

// Example plugin
struct MarkdownPlugin {
    enabled: bool,
}

impl Plugin for MarkdownPlugin {
    fn name(&self) -> &str {
        "markdown"
    }

    fn version(&self) -> &str {
        "1.0.0"
    }

    fn initialize(&mut self, _context: &PluginContext) -> Result<(), String> {
        self.enabled = true;
        println!("Markdown plugin initialized");
        Ok(())
    }

    fn shutdown(&mut self) -> Result<(), String> {
        self.enabled = false;
        println!("Markdown plugin shutdown");
        Ok(())
    }

    fn execute(&self, command: &str, args: Vec<String>) -> Result<String, String> {
        if !self.enabled {
            return Err("Plugin not enabled".to_string());
        }

        match command {
            "render" => {
                if args.is_empty() {
                    return Err("No markdown text provided".to_string());
                }
                // Simplified markdown rendering
                Ok(format!("<html>{}</html>", args[0]))
            }
            _ => Err(format!("Unknown command: {}", command)),
        }
    }
}

// Tauri integration
#[tauri::command]
fn execute_plugin(
    manager: tauri::State<PluginManager>,
    plugin: String,
    command: String,
    args: Vec<String>,
) -> Result<String, String> {
    manager.execute(&plugin, &command, args)
}

#[tauri::command]
fn list_plugins(manager: tauri::State<PluginManager>) -> Vec<(String, String)> {
    manager.list_plugins()
}
```

## Resource Management

### Resource Pool Pattern

```rust
use std::sync::{Arc, Mutex};
use std::collections::VecDeque;

pub struct ResourcePool<T> {
    resources: Arc<Mutex<VecDeque<T>>>,
    factory: Arc<dyn Fn() -> T + Send + Sync>,
    max_size: usize,
}

impl<T: Send + 'static> ResourcePool<T> {
    pub fn new<F>(factory: F, max_size: usize) -> Self
    where
        F: Fn() -> T + Send + Sync + 'static,
    {
        Self {
            resources: Arc::new(Mutex::new(VecDeque::new())),
            factory: Arc::new(factory),
            max_size,
        }
    }

    pub fn acquire(&self) -> PooledResource<T> {
        let resource = {
            let mut pool = self.resources.lock().unwrap();
            pool.pop_front().unwrap_or_else(|| (self.factory)())
        };

        PooledResource {
            resource: Some(resource),
            pool: self.resources.clone(),
            max_size: self.max_size,
        }
    }

    pub fn size(&self) -> usize {
        self.resources.lock().unwrap().len()
    }
}

pub struct PooledResource<T> {
    resource: Option<T>,
    pool: Arc<Mutex<VecDeque<T>>>,
    max_size: usize,
}

impl<T> PooledResource<T> {
    pub fn get(&self) -> &T {
        self.resource.as_ref().unwrap()
    }

    pub fn get_mut(&mut self) -> &mut T {
        self.resource.as_mut().unwrap()
    }
}

impl<T> Drop for PooledResource<T> {
    fn drop(&mut self) {
        if let Some(resource) = self.resource.take() {
            let mut pool = self.pool.lock().unwrap();
            if pool.len() < self.max_size {
                pool.push_back(resource);
            }
        }
    }
}

// Example: Database connection pool
use sqlx::{SqlitePool, SqliteConnection};

pub struct DatabasePool {
    pool: ResourcePool<SqliteConnection>,
}

impl DatabasePool {
    pub async fn new(database_url: &str, max_size: usize) -> Self {
        let url = database_url.to_string();
        Self {
            pool: ResourcePool::new(
                move || {
                    // This would need to be async in real implementation
                    unimplemented!("Use sqlx::SqlitePool instead")
                },
                max_size,
            ),
        }
    }
}
```

## Error Handling Strategies

### Application-Level Error Types

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("Not found: {0}")]
    NotFound(String),

    #[error("Validation error: {0}")]
    Validation(String),

    #[error("Permission denied: {0}")]
    PermissionDenied(String),

    #[error("Internal error: {0}")]
    Internal(String),
}

// Convert to Tauri-compatible error
impl From<AppError> for String {
    fn from(error: AppError) -> Self {
        error.to_string()
    }
}

// Result type alias
pub type AppResult<T> = Result<T, AppError>;

// Usage in commands
#[tauri::command]
async fn save_data(data: String) -> Result<(), String> {
    perform_save(&data)
        .await
        .map_err(|e: AppError| e.to_string())
}

async fn perform_save(data: &str) -> AppResult<()> {
    // Validation
    if data.is_empty() {
        return Err(AppError::Validation("Data cannot be empty".to_string()));
    }

    // IO operation
    std::fs::write("data.txt", data)?;

    Ok(())
}
```

### Error Recovery Pattern

```rust
use std::time::Duration;
use tokio::time::sleep;

pub struct RetryPolicy {
    max_attempts: u32,
    delay: Duration,
    exponential_backoff: bool,
}

impl RetryPolicy {
    pub fn new(max_attempts: u32, delay: Duration) -> Self {
        Self {
            max_attempts,
            delay,
            exponential_backoff: false,
        }
    }

    pub fn with_exponential_backoff(mut self) -> Self {
        self.exponential_backoff = true;
        self
    }

    pub async fn execute<F, T, E>(&self, mut operation: F) -> Result<T, E>
    where
        F: FnMut() -> Result<T, E>,
        E: std::fmt::Display,
    {
        let mut attempt = 0;
        let mut delay = self.delay;

        loop {
            attempt += 1;

            match operation() {
                Ok(result) => return Ok(result),
                Err(error) => {
                    if attempt >= self.max_attempts {
                        println!("Operation failed after {} attempts", attempt);
                        return Err(error);
                    }

                    println!(
                        "Attempt {} failed: {}. Retrying in {:?}...",
                        attempt, error, delay
                    );

                    sleep(delay).await;

                    if self.exponential_backoff {
                        delay *= 2;
                    }
                }
            }
        }
    }
}

// Usage
async fn fetch_with_retry(url: &str) -> Result<String, String> {
    let policy = RetryPolicy::new(3, Duration::from_secs(1))
        .with_exponential_backoff();

    policy
        .execute(|| {
            // Attempt operation
            Ok("data".to_string())
        })
        .await
}
```

These patterns provide a solid foundation for building maintainable desktop applications. Choose and combine based on application complexity and requirements.
