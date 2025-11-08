# State Management

Comprehensive guide to managing application state in Rust desktop applications, from simple local state to complex async operations and multi-window synchronization.

## State Management Strategies

### Local State (Single Component)

Simplest form - state lives within a single component or module.

```rust
// egui example
struct MyApp {
    counter: i32,
    text: String,
    selected: Option<usize>,
}

impl eframe::App for MyApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.label(format!("Counter: {}", self.counter));

            if ui.button("Increment").clicked() {
                self.counter += 1;
            }

            ui.text_edit_singleline(&mut self.text);
        });
    }
}
```

**Tauri example:**
```rust
use std::sync::Mutex;

struct AppState {
    counter: Mutex<i32>,
}

#[tauri::command]
fn increment(state: tauri::State<AppState>) -> i32 {
    let mut counter = state.counter.lock().unwrap();
    *counter += 1;
    *counter
}

#[tauri::command]
fn get_counter(state: tauri::State<AppState>) -> i32 {
    *state.counter.lock().unwrap()
}

fn main() {
    tauri::Builder::default()
        .manage(AppState {
            counter: Mutex::new(0),
        })
        .invoke_handler(tauri::generate_handler![increment, get_counter])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### Shared State with Arc<Mutex<T>>

Thread-safe shared state for multi-threaded applications.

```rust
use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct SharedState {
    data: Arc<Mutex<AppData>>,
}

struct AppData {
    users: Vec<User>,
    settings: Settings,
}

impl SharedState {
    fn new() -> Self {
        Self {
            data: Arc::new(Mutex::new(AppData {
                users: Vec::new(),
                settings: Settings::default(),
            })),
        }
    }

    fn add_user(&self, user: User) {
        let mut data = self.data.lock().unwrap();
        data.users.push(user);
    }

    fn get_users(&self) -> Vec<User> {
        let data = self.data.lock().unwrap();
        data.users.clone()
    }
}

// Tauri commands
#[tauri::command]
fn add_user(state: tauri::State<SharedState>, name: String, email: String) {
    let user = User {
        id: generate_id(),
        name,
        email,
    };
    state.add_user(user);
}

#[tauri::command]
fn get_users(state: tauri::State<SharedState>) -> Vec<User> {
    state.get_users()
}
```

### RwLock for Read-Heavy Workloads

Better performance when reads outnumber writes.

```rust
use std::sync::{Arc, RwLock};

struct AppState {
    cache: Arc<RwLock<HashMap<String, String>>>,
}

impl AppState {
    fn new() -> Self {
        Self {
            cache: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    // Multiple readers can access simultaneously
    fn get(&self, key: &str) -> Option<String> {
        let cache = self.cache.read().unwrap();
        cache.get(key).cloned()
    }

    // Exclusive write access
    fn set(&self, key: String, value: String) {
        let mut cache = self.cache.write().unwrap();
        cache.insert(key, value);
    }

    // Bulk read operation
    fn get_all(&self) -> HashMap<String, String> {
        let cache = self.cache.read().unwrap();
        cache.clone()
    }
}

#[tauri::command]
fn cache_get(state: tauri::State<AppState>, key: String) -> Option<String> {
    state.get(&key)
}

#[tauri::command]
fn cache_set(state: tauri::State<AppState>, key: String, value: String) {
    state.set(key, value);
}
```

## Async Runtime Integration

### Tokio Integration with Tauri

```rust
use tokio::sync::RwLock as TokioRwLock;
use std::sync::Arc;

struct AsyncState {
    data: Arc<TokioRwLock<AppData>>,
}

#[derive(Clone)]
struct AppData {
    items: Vec<Item>,
    loading: bool,
}

impl AsyncState {
    fn new() -> Self {
        Self {
            data: Arc::new(TokioRwLock::new(AppData {
                items: Vec::new(),
                loading: false,
            })),
        }
    }

    async fn fetch_items(&self) -> Result<Vec<Item>, String> {
        // Set loading state
        {
            let mut data = self.data.write().await;
            data.loading = true;
        }

        // Perform async operation
        let items = fetch_from_api().await.map_err(|e| e.to_string())?;

        // Update state
        {
            let mut data = self.data.write().await;
            data.items = items.clone();
            data.loading = false;
        }

        Ok(items)
    }

    async fn get_items(&self) -> Vec<Item> {
        let data = self.data.read().await;
        data.items.clone()
    }

    async fn is_loading(&self) -> bool {
        let data = self.data.read().await;
        data.loading
    }
}

#[tauri::command]
async fn fetch_items(state: tauri::State<'_, AsyncState>) -> Result<Vec<Item>, String> {
    state.fetch_items().await
}

#[tauri::command]
async fn get_items(state: tauri::State<'_, AsyncState>) -> Vec<Item> {
    state.get_items().await
}

async fn fetch_from_api() -> Result<Vec<Item>, Box<dyn std::error::Error>> {
    use reqwest;

    let response = reqwest::get("https://api.example.com/items")
        .await?
        .json::<Vec<Item>>()
        .await?;

    Ok(response)
}
```

### Background Tasks and Channels

```rust
use tokio::sync::mpsc;
use tokio::time::{interval, Duration};

struct BackgroundWorker {
    tx: mpsc::UnboundedSender<WorkerMessage>,
}

enum WorkerMessage {
    ProcessData(String),
    Stop,
}

impl BackgroundWorker {
    fn new(app_handle: tauri::AppHandle) -> Self {
        let (tx, mut rx) = mpsc::unbounded_channel();

        tokio::spawn(async move {
            let mut ticker = interval(Duration::from_secs(1));

            loop {
                tokio::select! {
                    _ = ticker.tick() => {
                        // Periodic task
                        let _ = app_handle.emit("tick", "Periodic update");
                    }
                    Some(msg) = rx.recv() => {
                        match msg {
                            WorkerMessage::ProcessData(data) => {
                                // Process data
                                println!("Processing: {}", data);
                                let _ = app_handle.emit("data-processed", data);
                            }
                            WorkerMessage::Stop => {
                                println!("Stopping worker");
                                break;
                            }
                        }
                    }
                }
            }
        });

        Self { tx }
    }

    fn send(&self, msg: WorkerMessage) {
        let _ = self.tx.send(msg);
    }
}

#[tauri::command]
fn process_data(worker: tauri::State<BackgroundWorker>, data: String) {
    worker.send(WorkerMessage::ProcessData(data));
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let worker = BackgroundWorker::new(app.handle());
            app.manage(worker);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![process_data])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

## Message Passing Patterns

### Command-Query Separation

```rust
use tokio::sync::mpsc;

// Commands (modify state)
enum Command {
    AddUser { name: String, email: String },
    RemoveUser { id: u64 },
    UpdateSettings { key: String, value: String },
}

// Queries (read state)
enum Query {
    GetUser { id: u64, response: oneshot::Sender<Option<User>> },
    GetAllUsers { response: oneshot::Sender<Vec<User>> },
    GetSettings { response: oneshot::Sender<Settings> },
}

struct StateManager {
    command_tx: mpsc::UnboundedSender<Command>,
    query_tx: mpsc::UnboundedSender<Query>,
}

impl StateManager {
    fn new() -> Self {
        let (command_tx, mut command_rx) = mpsc::unbounded_channel();
        let (query_tx, mut query_rx) = mpsc::unbounded_channel();

        // State lives in this task
        tokio::spawn(async move {
            let mut state = AppState::new();

            loop {
                tokio::select! {
                    Some(cmd) = command_rx.recv() => {
                        match cmd {
                            Command::AddUser { name, email } => {
                                state.add_user(User { id: generate_id(), name, email });
                            }
                            Command::RemoveUser { id } => {
                                state.remove_user(id);
                            }
                            Command::UpdateSettings { key, value } => {
                                state.update_setting(key, value);
                            }
                        }
                    }
                    Some(query) = query_rx.recv() => {
                        match query {
                            Query::GetUser { id, response } => {
                                let _ = response.send(state.get_user(id));
                            }
                            Query::GetAllUsers { response } => {
                                let _ = response.send(state.get_all_users());
                            }
                            Query::GetSettings { response } => {
                                let _ = response.send(state.get_settings());
                            }
                        }
                    }
                }
            }
        });

        Self { command_tx, query_tx }
    }

    fn send_command(&self, cmd: Command) {
        let _ = self.command_tx.send(cmd);
    }

    async fn query_user(&self, id: u64) -> Option<User> {
        let (tx, rx) = oneshot::channel();
        let _ = self.query_tx.send(Query::GetUser { id, response: tx });
        rx.await.unwrap()
    }

    async fn query_all_users(&self) -> Vec<User> {
        let (tx, rx) = oneshot::channel();
        let _ = self.query_tx.send(Query::GetAllUsers { response: tx });
        rx.await.unwrap()
    }
}

// Tauri commands
#[tauri::command]
fn add_user(manager: tauri::State<StateManager>, name: String, email: String) {
    manager.send_command(Command::AddUser { name, email });
}

#[tauri::command]
async fn get_user(manager: tauri::State<'_, StateManager>, id: u64) -> Option<User> {
    manager.query_user(id).await
}
```

### Actor Pattern

```rust
use tokio::sync::mpsc;

trait Actor {
    type Message;

    fn handle(&mut self, msg: Self::Message);
}

struct ActorHandle<M> {
    tx: mpsc::UnboundedSender<M>,
}

impl<M: Send + 'static> ActorHandle<M> {
    fn new<A>(mut actor: A) -> Self
    where
        A: Actor<Message = M> + Send + 'static,
    {
        let (tx, mut rx) = mpsc::unbounded_channel();

        tokio::spawn(async move {
            while let Some(msg) = rx.recv().await {
                actor.handle(msg);
            }
        });

        Self { tx }
    }

    fn send(&self, msg: M) {
        let _ = self.tx.send(msg);
    }
}

// Example actor
struct UserActor {
    users: HashMap<u64, User>,
}

enum UserMessage {
    Add(User),
    Remove(u64),
    Get { id: u64, response: oneshot::Sender<Option<User>> },
}

impl Actor for UserActor {
    type Message = UserMessage;

    fn handle(&mut self, msg: Self::Message) {
        match msg {
            UserMessage::Add(user) => {
                self.users.insert(user.id, user);
            }
            UserMessage::Remove(id) => {
                self.users.remove(&id);
            }
            UserMessage::Get { id, response } => {
                let user = self.users.get(&id).cloned();
                let _ = response.send(user);
            }
        }
    }
}

// Usage
fn setup_actors() -> ActorHandle<UserMessage> {
    let actor = UserActor {
        users: HashMap::new(),
    };
    ActorHandle::new(actor)
}
```

## Reactive State Patterns

### Observable State with Signals

```rust
use std::sync::{Arc, Mutex};
use std::collections::HashMap;

type Listener<T> = Box<dyn Fn(&T) + Send + Sync>;

struct Signal<T: Clone> {
    value: Arc<Mutex<T>>,
    listeners: Arc<Mutex<Vec<Listener<T>>>>,
}

impl<T: Clone + Send + Sync + 'static> Signal<T> {
    fn new(initial: T) -> Self {
        Self {
            value: Arc::new(Mutex::new(initial)),
            listeners: Arc::new(Mutex::new(Vec::new())),
        }
    }

    fn get(&self) -> T {
        self.value.lock().unwrap().clone()
    }

    fn set(&self, new_value: T) {
        {
            let mut value = self.value.lock().unwrap();
            *value = new_value.clone();
        }

        // Notify listeners
        let listeners = self.listeners.lock().unwrap();
        for listener in listeners.iter() {
            listener(&new_value);
        }
    }

    fn update<F>(&self, f: F)
    where
        F: FnOnce(&mut T),
    {
        let new_value = {
            let mut value = self.value.lock().unwrap();
            f(&mut value);
            value.clone()
        };

        // Notify listeners
        let listeners = self.listeners.lock().unwrap();
        for listener in listeners.iter() {
            listener(&new_value);
        }
    }

    fn subscribe<F>(&self, listener: F)
    where
        F: Fn(&T) + Send + Sync + 'static,
    {
        let mut listeners = self.listeners.lock().unwrap();
        listeners.push(Box::new(listener));
    }
}

// Example usage
struct AppState {
    counter: Signal<i32>,
    username: Signal<String>,
}

impl AppState {
    fn new() -> Self {
        Self {
            counter: Signal::new(0),
            username: Signal::new(String::from("Guest")),
        }
    }
}

fn setup_state(app_handle: tauri::AppHandle) -> AppState {
    let state = AppState::new();

    // Subscribe to changes
    let handle = app_handle.clone();
    state.counter.subscribe(move |value| {
        let _ = handle.emit("counter-changed", value);
    });

    let handle = app_handle.clone();
    state.username.subscribe(move |value| {
        let _ = handle.emit("username-changed", value);
    });

    state
}

#[tauri::command]
fn increment_counter(state: tauri::State<AppState>) {
    state.counter.update(|c| *c += 1);
}

#[tauri::command]
fn set_username(state: tauri::State<AppState>, name: String) {
    state.username.set(name);
}

#[tauri::command]
fn get_counter(state: tauri::State<AppState>) -> i32 {
    state.counter.get()
}
```

### Computed Values

```rust
struct Computed<T, F>
where
    T: Clone,
    F: Fn() -> T,
{
    compute: F,
    cached: Arc<Mutex<Option<T>>>,
}

impl<T: Clone, F: Fn() -> T> Computed<T, F> {
    fn new(compute: F) -> Self {
        Self {
            compute,
            cached: Arc::new(Mutex::new(None)),
        }
    }

    fn get(&self) -> T {
        let mut cached = self.cached.lock().unwrap();

        if let Some(value) = cached.as_ref() {
            value.clone()
        } else {
            let value = (self.compute)();
            *cached = Some(value.clone());
            value
        }
    }

    fn invalidate(&self) {
        let mut cached = self.cached.lock().unwrap();
        *cached = None;
    }
}

// Example
struct TodoState {
    todos: Signal<Vec<Todo>>,
    completed_count: Computed<usize, Box<dyn Fn() -> usize + Send + Sync>>,
}

impl TodoState {
    fn new() -> Self {
        let todos = Signal::new(Vec::new());
        let todos_clone = todos.clone();

        let completed_count = Computed::new(Box::new(move || {
            todos_clone
                .get()
                .iter()
                .filter(|t| t.completed)
                .count()
        }));

        Self {
            todos,
            completed_count,
        }
    }

    fn add_todo(&self, todo: Todo) {
        self.todos.update(|todos| todos.push(todo));
        self.completed_count.invalidate();
    }

    fn toggle_todo(&self, id: u64) {
        self.todos.update(|todos| {
            if let Some(todo) = todos.iter_mut().find(|t| t.id == id) {
                todo.completed = !todo.completed;
            }
        });
        self.completed_count.invalidate();
    }

    fn get_completed_count(&self) -> usize {
        self.completed_count.get()
    }
}
```

## Persistence

### File-Based Persistence

```rust
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Serialize, Deserialize, Clone)]
struct AppSettings {
    theme: String,
    language: String,
    window_size: (u32, u32),
}

struct PersistedState {
    settings: Signal<AppSettings>,
    config_path: PathBuf,
}

impl PersistedState {
    fn new(config_path: PathBuf) -> Self {
        let settings = Self::load_settings(&config_path)
            .unwrap_or_else(|_| AppSettings::default());

        let state = Self {
            settings: Signal::new(settings),
            config_path,
        };

        // Auto-save on changes
        let config_path = state.config_path.clone();
        state.settings.subscribe(move |settings| {
            let _ = Self::save_settings(&config_path, settings);
        });

        state
    }

    fn load_settings(path: &PathBuf) -> Result<AppSettings, Box<dyn std::error::Error>> {
        let content = std::fs::read_to_string(path)?;
        let settings = serde_json::from_str(&content)?;
        Ok(settings)
    }

    fn save_settings(path: &PathBuf, settings: &AppSettings) -> Result<(), Box<dyn std::error::Error>> {
        let content = serde_json::to_string_pretty(settings)?;
        std::fs::write(path, content)?;
        Ok(())
    }

    fn update_settings<F>(&self, f: F)
    where
        F: FnOnce(&mut AppSettings),
    {
        self.settings.update(f);
    }
}

#[tauri::command]
fn update_theme(state: tauri::State<PersistedState>, theme: String) {
    state.update_settings(|s| s.theme = theme);
}

#[tauri::command]
fn get_settings(state: tauri::State<PersistedState>) -> AppSettings {
    state.settings.get()
}
```

### Database Integration with sqlx

```rust
use sqlx::{SqlitePool, FromRow};

#[derive(FromRow, Serialize, Clone)]
struct Note {
    id: i64,
    title: String,
    content: String,
    created_at: String,
}

struct DatabaseState {
    pool: SqlitePool,
}

impl DatabaseState {
    async fn new(database_url: &str) -> Result<Self, sqlx::Error> {
        let pool = SqlitePool::connect(database_url).await?;

        // Run migrations
        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            "#,
        )
        .execute(&pool)
        .await?;

        Ok(Self { pool })
    }

    async fn create_note(&self, title: String, content: String) -> Result<Note, sqlx::Error> {
        let note = sqlx::query_as::<_, Note>(
            "INSERT INTO notes (title, content) VALUES (?, ?) RETURNING *",
        )
        .bind(title)
        .bind(content)
        .fetch_one(&self.pool)
        .await?;

        Ok(note)
    }

    async fn get_all_notes(&self) -> Result<Vec<Note>, sqlx::Error> {
        sqlx::query_as::<_, Note>("SELECT * FROM notes ORDER BY created_at DESC")
            .fetch_all(&self.pool)
            .await
    }

    async fn update_note(&self, id: i64, title: String, content: String) -> Result<(), sqlx::Error> {
        sqlx::query("UPDATE notes SET title = ?, content = ? WHERE id = ?")
            .bind(title)
            .bind(content)
            .bind(id)
            .execute(&self.pool)
            .await?;

        Ok(())
    }

    async fn delete_note(&self, id: i64) -> Result<(), sqlx::Error> {
        sqlx::query("DELETE FROM notes WHERE id = ?")
            .bind(id)
            .execute(&self.pool)
            .await?;

        Ok(())
    }
}

#[tauri::command]
async fn create_note(
    state: tauri::State<'_, DatabaseState>,
    title: String,
    content: String,
) -> Result<Note, String> {
    state
        .create_note(title, content)
        .await
        .map_err(|e| e.to_string())
}

#[tauri::command]
async fn get_all_notes(state: tauri::State<'_, DatabaseState>) -> Result<Vec<Note>, String> {
    state.get_all_notes().await.map_err(|e| e.to_string())
}
```

## Multi-Window State Sharing

```rust
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Clone)]
struct SharedAppState {
    data: Arc<RwLock<GlobalData>>,
}

struct GlobalData {
    current_user: Option<User>,
    notifications: Vec<Notification>,
}

impl SharedAppState {
    fn new() -> Self {
        Self {
            data: Arc::new(RwLock::new(GlobalData {
                current_user: None,
                notifications: Vec::new(),
            })),
        }
    }

    async fn set_user(&self, user: User) {
        let mut data = self.data.write().await;
        data.current_user = Some(user);
    }

    async fn add_notification(&self, notification: Notification) {
        let mut data = self.data.write().await;
        data.notifications.push(notification);
    }

    async fn get_user(&self) -> Option<User> {
        let data = self.data.read().await;
        data.current_user.clone()
    }
}

// Broadcast state changes to all windows
use tauri::{Emitter, Manager};

#[tauri::command]
async fn login_user(
    app: tauri::AppHandle,
    state: tauri::State<'_, SharedAppState>,
    username: String,
) -> Result<(), String> {
    let user = User {
        id: 1,
        name: username,
        email: "user@example.com".to_string(),
    };

    state.set_user(user.clone()).await;

    // Notify all windows
    app.emit("user-logged-in", &user).map_err(|e| e.to_string())?;

    Ok(())
}

// Open new window with shared state
#[tauri::command]
fn open_settings_window(app: tauri::AppHandle) -> Result<(), String> {
    tauri::WebviewWindowBuilder::new(
        &app,
        "settings",
        tauri::WebviewUrl::App("settings.html".into()),
    )
    .title("Settings")
    .build()
    .map_err(|e| e.to_string())?;

    Ok(())
}
```

These state management patterns provide flexibility for applications of all sizes - from simple local state to complex distributed state with persistence and multi-window synchronization.
