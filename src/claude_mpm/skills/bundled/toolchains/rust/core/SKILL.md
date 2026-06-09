---
name: toolchains-rust-core
description: "Rust 2024 edition core patterns: idiomatic code, error handling, traits/generics, macros, async/concurrency, testing, and project architecture"
version: "2.0.0"
category: toolchains-rust
tags: [rust, patterns, performance, minimalism, efficiency, safety, async, testing, architecture]
effort: medium
---

# Rust 2024 Core Patterns

## Quick Start

```toml
# Cargo.toml - essential stack
[dependencies]
tokio = { version = "1", features = ["full"] }
thiserror = "2"
anyhow = "2"
serde = { version = "1", features = ["derive"] }
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }

[dev-dependencies]
rstest = "0.22"
proptest = "1"
mockall = "0.13"
insta = "1"
criterion = { version = "0.5", features = ["html_reports"] }
```

```bash
cargo add tokio --features full && cargo add thiserror anyhow serde --features serde/derive
cargo clippy -- -D warnings   # enforce in CI
cargo test                    # unit + integration + doctests
cargo test --doc              # doctests only
```

---

## Idiomatic Patterns

- **Builder pattern**: Use consuming `self` methods; finish with `build() -> Result<T, E>` for validated construction.
- **Newtype pattern**: `struct UserId(u64)` gives type safety at zero cost; add `impl From<u64> for UserId`.
- **From/Into**: Implement `From<T>` only — `Into<T>` is blanket-provided; accept `impl Into<T>` in function params.
- **Derive by default**: `#[derive(Debug, Clone, PartialEq, Eq, Hash)]` on domain types; add `serde` only when needed.
- **Type state**: Encode state machines as generic marker types — invalid transitions become compile errors, not panics.
- **Borrowed params**: Accept `&str` not `&String`, `&[T]` not `&Vec<T>`, `impl AsRef<Path>` not `&PathBuf`.
- **Default for config**: `Config { field: value, ..Default::default() }` — audit all fields when adding new ones.
- **RAII guards**: Use `Drop` for resource cleanup; wrap locks, file handles, and connections in guard types.
- **`Cow<'_, str>`**: Return `Cow<'_, str>` when sometimes borrowing, sometimes owning — avoids unnecessary clones.
- **Zero-cost abstractions**: Iterator chains compile to identical (often better) machine code than manual loops.
- **Stack vs heap**: Default to stack; use `Box` only for trait objects, recursive types, or large data escaping scope.

---

## Error Handling

### thiserror (libraries)

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum UserError {
    #[error("user {id} not found")]
    NotFound { id: u64 },

    #[error("invalid email: {0}")]
    InvalidEmail(String),

    #[error("database error")]
    Database(#[from] sqlx::Error),

    #[error("serialization failed")]
    Serialization(#[from] serde_json::Error),
}
```

Rules:
- Libraries expose typed error enums — callers can pattern-match variants.
- Never use `String` or `Box<dyn Error>` in public library API.
- `#[from]` generates `From<SourceError>` — use `?` to propagate automatically.
- `#[source]` exposes the underlying error via `Error::source()` without auto-`From`.

### anyhow (applications / CLIs)

```rust
use anyhow::{Context, Result};

fn load_config(path: &Path) -> Result<Config> {
    let text = std::fs::read_to_string(path)
        .with_context(|| format!("reading config from {}", path.display()))?;
    let config: Config = toml::from_str(&text)
        .context("parsing config as TOML")?;
    Ok(config)
}

fn main() -> Result<()> {
    let config = load_config(Path::new("config.toml"))?;
    run(config)
}
```

Rules:
- `anyhow::Result<T>` in `main()`, CLI handlers, and top-level application code.
- Chain context with `.context("what we were doing")` at each call site.
- Never use `anyhow` in public library APIs — wrap and convert at the boundary.

### Error conversion at library/app boundary

```rust
// In application code: convert library error to anyhow
let user = user_service.get(id)
    .await
    .map_err(|e| anyhow::anyhow!("get user {id}: {e}"))?;

// Or implement From in your app error type
impl From<UserError> for AppError { ... }
```

---

## Traits and Generics

### Small, focused traits

```rust
// Prefer small traits over large catch-all interfaces
trait Fetch {
    async fn fetch(&self, url: &str) -> Result<Bytes, FetchError>;
}

trait Store {
    async fn store(&self, key: &str, value: &[u8]) -> Result<(), StoreError>;
}

// Compose with supertraits
trait Cache: Fetch + Store + Send + Sync {}
```

### Trait objects vs generics

```rust
// Generics: compile-time dispatch, monomorphized, no heap alloc
fn process<F: Fetch>(fetcher: &F) -> Result<()> { ... }

// Trait objects: runtime dispatch, heap alloc, heterogeneous collections
fn process_dyn(fetcher: &dyn Fetch) -> Result<()> { ... }
fn process_arc(fetcher: Arc<dyn Fetch>) -> Result<()> { ... }

// Rule: default to generics; use dyn Trait for:
// - Heterogeneous collections (Vec<Box<dyn Trait>>)
// - Runtime polymorphism (DI containers, plugin systems)
// - Avoiding monomorphization bloat in large codebases
```

### Associated types vs generics

```rust
// Associated type: one implementation per type (Iterator pattern)
trait Parser {
    type Output;
    fn parse(&self, input: &str) -> Result<Self::Output, ParseError>;
}

// Generic parameter: multiple implementations per type
trait Convert<T> {
    fn convert(&self) -> T;
}
// allows: impl Convert<String> for MyType AND impl Convert<u64> for MyType
```

### Generic bounds and where clauses

```rust
// Inline bounds for simple cases
fn clone_and_display<T: Clone + Display>(value: &T) { ... }

// Where clause for complex cases (preferred for readability)
fn process<T, E>(items: &[T]) -> Result<Vec<String>, E>
where
    T: Display + Send + 'static,
    E: std::error::Error + From<fmt::Error>,
{ ... }
```

### Blanket implementations

```rust
// Provide default impl for all qualifying types
trait Summarize {
    fn summary(&self) -> String;
}

impl<T: Display> Summarize for T {
    fn summary(&self) -> String {
        format!("{}", self)
    }
}
```

### Extension traits (adding methods to foreign types)

```rust
trait IteratorExt: Iterator {
    fn take_while_inclusive<P>(self, predicate: P) -> TakeWhileInclusive<Self, P>
    where
        P: FnMut(&Self::Item) -> bool,
        Self: Sized;
}

impl<I: Iterator> IteratorExt for I {
    fn take_while_inclusive<P>(self, predicate: P) -> TakeWhileInclusive<Self, P>
    where P: FnMut(&Self::Item) -> bool, Self: Sized {
        TakeWhileInclusive { iter: self, predicate, done: false }
    }
}
```

### Sealed traits (prevent external implementation)

```rust
mod private {
    pub trait Sealed {}
}

pub trait MyTrait: private::Sealed {
    fn method(&self);
}

// Only types you impl private::Sealed for can impl MyTrait
impl private::Sealed for MyType {}
impl MyTrait for MyType { fn method(&self) {} }
```

### Generic Associated Types (GATs)

```rust
// Stable since Rust 1.65 — enables lifetime-parameterized associated types
trait Lender {
    type Item<'a> where Self: 'a;
    fn lend(&mut self) -> Self::Item<'_>;
}
```

---

## Macros

### Declarative macros (`macro_rules!`)

```rust
// Pattern matching on token trees
macro_rules! hashmap {
    ($($key:expr => $val:expr),* $(,)?) => {{
        let mut map = std::collections::HashMap::new();
        $(map.insert($key, $val);)*
        map
    }};
}

let m = hashmap!{ "a" => 1, "b" => 2 };

// Repeat patterns
macro_rules! impl_from_str {
    ($($t:ty),+) => {
        $(impl std::str::FromStr for $t {
            type Err = ParseError;
            fn from_str(s: &str) -> Result<Self, Self::Err> {
                s.parse::<u64>().map(Self).map_err(Into::into)
            }
        })+
    };
}
```

### Procedural macros (derive)

```rust
// Custom derive — separate crate required (e.g., my-macros-derive)
use proc_macro::TokenStream;
use quote::quote;
use syn::{parse_macro_input, DeriveInput};

#[proc_macro_derive(Builder)]
pub fn derive_builder(input: TokenStream) -> TokenStream {
    let ast = parse_macro_input!(input as DeriveInput);
    let name = &ast.ident;
    let expanded = quote! {
        impl #name {
            pub fn builder() -> #nameBuilder { Default::default() }
        }
    };
    expanded.into()
}
```

Rules:
- Use declarative macros for simple repetition; proc macros for derive and attribute macros.
- Document macro hygiene: `$crate::` prefix for items referenced inside the macro.
- Prefer `derive_more` and `strum` crates over writing your own derive macros.
- Test macros via `trybuild` to verify compile-time error messages.

---

## Async / Concurrency Patterns

### Tokio fundamentals

```rust
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Tokio only — async-std is effectively unmaintained as of 2026
    run().await
}

// Async closures (Rust 2024)
let handler = async |req: Request| -> Result<Response> {
    process(req).await
};
```

### Structured concurrency

```rust
use tokio::{join, select};

// Concurrent execution (all complete)
let (users, orders) = join!(fetch_users(), fetch_orders());

// Racing (first to complete wins)
select! {
    result = fetch_with_primary() => result,
    result = fetch_with_fallback() => result,
    _ = tokio::time::sleep(Duration::from_secs(5)) => Err(TimeoutError),
}

// Dynamic task groups
use tokio::task::JoinSet;

let mut set = JoinSet::new();
for id in ids {
    set.spawn(async move { fetch_item(id).await });
}
while let Some(result) = set.join_next().await {
    handle(result??);
}
```

### Shared state patterns

```rust
// Arc<Mutex<T>> for mutable shared state
let state: Arc<Mutex<HashMap<u64, User>>> = Arc::new(Mutex::new(HashMap::new()));
let state_clone = Arc::clone(&state);

tokio::spawn(async move {
    let mut guard = state_clone.lock().await;  // tokio::sync::Mutex
    guard.insert(1, user);
});

// RwLock for read-heavy workloads
let cache: Arc<RwLock<HashMap<String, Value>>> = Arc::new(RwLock::new(HashMap::new()));
let val = cache.read().await.get("key").cloned();

// Atomics for simple flags/counters — no mutex overhead
use std::sync::atomic::{AtomicU64, Ordering};
let counter = Arc::new(AtomicU64::new(0));
counter.fetch_add(1, Ordering::SeqCst);
```

### Actor pattern (message-passing concurrency)

```rust
use tokio::sync::mpsc;

enum Command {
    Get { key: String, reply: tokio::sync::oneshot::Sender<Option<String>> },
    Set { key: String, value: String },
    Shutdown,
}

struct CacheActor {
    store: HashMap<String, String>,
    rx: mpsc::Receiver<Command>,
}

impl CacheActor {
    async fn run(mut self) {
        while let Some(cmd) = self.rx.recv().await {
            match cmd {
                Command::Get { key, reply } => {
                    let _ = reply.send(self.store.get(&key).cloned());
                }
                Command::Set { key, value } => {
                    self.store.insert(key, value);
                }
                Command::Shutdown => break,
            }
        }
    }
}

// Handle is cheaply cloneable — clone per task/thread
#[derive(Clone)]
struct CacheHandle(mpsc::Sender<Command>);

impl CacheHandle {
    async fn get(&self, key: String) -> Option<String> {
        let (tx, rx) = tokio::sync::oneshot::channel();
        self.0.send(Command::Get { key, reply: tx }).await.ok()?;
        rx.await.ok()?
    }

    async fn set(&self, key: String, value: String) {
        let _ = self.0.send(Command::Set { key, value }).await;
    }
}
```

### Cancellation safety

```rust
// RAII cleanup: use Drop for cancellation handling
struct Guard {
    resource: Resource,
}

impl Drop for Guard {
    fn drop(&mut self) {
        // Always runs, even if task is cancelled
        self.resource.cleanup();
    }
}

// Avoid holding mutable state across .await points
// BAD:
let mut locked = mutex.lock().await;
do_io().await;  // lock held across await — deadlock risk
drop(locked);

// GOOD:
{
    let mut locked = mutex.lock().await;
    update_state(&mut locked);
}  // lock released before await
do_io().await;
```

### CPU-bound work

```rust
// Never block the async executor
let result = tokio::task::spawn_blocking(|| {
    // CPU-intensive or blocking sync code here
    heavy_computation()
})
.await?;

// Rayon for data-parallel CPU work
use rayon::prelude::*;
let result: Vec<_> = data.par_iter().map(|x| transform(x)).collect();
```

### Async write durability

```rust
// Buffered tokio::File opened via OpenOptions MUST be flushed before a reader runs.
let mut f = tokio::fs::OpenOptions::new()
    .create(true).write(true).truncate(true)
    .open(path).await?;
f.write_all(&bytes).await?;
f.flush().await?;   // REQUIRED — without this, a concurrent reader may see truncated/empty data
```

Rules:
- After `tokio::fs::File::write_all()`, call `flush().await` before any reader runs or you return — otherwise silent read-after-write race / data loss.
- `tokio::fs::File` defers writes to a blocking thread pool — `flush().await` ensures all queued writes have completed before a reader runs (it is NOT a userspace `BufWriter`). The free fn `tokio::fs::write()` is a single open/write/close. Sync `std::fs::File` has no Rust-layer userspace buffer, so writes reach the OS page cache on return — but crash/power-loss durability still requires `sync_all()`/`sync_data()`; drop alone does not fsync.

### HTTP client construction

```rust
// Never reqwest::Client::new() in a service — no application-level timeout; a slow upstream can block a worker for the OS TCP timeout (minutes).
let client = reqwest::ClientBuilder::new()
    .timeout(Duration::from_secs(30))
    .connect_timeout(Duration::from_secs(5))
    .build()?;
```

Rules:
- Never construct `reqwest::Client::new()` in a service — a timeout-free client has no application-level timeout, so a slow upstream can block a worker for the OS TCP timeout duration (minutes).
- Always set both a request `timeout` and a `connect_timeout`; build once and clone (the inner pool is shared).

---

## Testing Best Practices

### Test placement

```rust
// Unit tests: same file, cfg(test) module
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic_operation() {
        // Arrange
        let sut = MyStruct::new(42);
        // Act
        let result = sut.compute();
        // Assert
        assert_eq!(result, 84);
    }
}

// Integration tests: tests/ directory, no cfg(test) needed
// tests/integration_test.rs
use my_crate::Api;

#[tokio::test]
async fn full_roundtrip() {
    let api = Api::start_test_server().await;
    // ...
}
```

### rstest — parametrized and fixture-based tests

```rust
use rstest::*;

#[fixture]
fn database() -> TestDb {
    TestDb::in_memory()
}

#[rstest]
#[case("valid@email.com", true)]
#[case("not-an-email", false)]
#[case("", false)]
fn test_email_validation(#[case] input: &str, #[case] expected: bool) {
    assert_eq!(is_valid_email(input), expected);
}

#[rstest]
async fn test_with_fixture(database: TestDb) {
    let repo = UserRepository::new(database);
    assert!(repo.find(999).await.unwrap().is_none());
}
```

### proptest — property-based testing

```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn roundtrip_serialization(s in "\\PC*") {
        let encoded = encode(&s);
        let decoded = decode(&encoded).unwrap();
        prop_assert_eq!(s, decoded);
    }

    #[test]
    fn sort_is_idempotent(mut v in prop::collection::vec(any::<i32>(), 0..100)) {
        v.sort();
        let sorted_once = v.clone();
        v.sort();
        prop_assert_eq!(sorted_once, v);
    }
}
```

### insta — snapshot testing

```rust
use insta::assert_snapshot;

#[test]
fn test_error_message() {
    let err = UserError::NotFound { id: 42 };
    assert_snapshot!(err.to_string());
    // First run writes snapshot; subsequent runs compare
    // Review with: cargo insta review
}

#[test]
fn test_json_output() {
    let user = User { id: 1, name: "Alice".into() };
    insta::assert_json_snapshot!(user, @r###"
    {
      "id": 1,
      "name": "Alice"
    }
    "###);
}
```

### mockall — mock trait implementations

```rust
use mockall::{automock, predicate::*};

#[cfg_attr(test, automock)]
trait EmailService: Send + Sync {
    async fn send(&self, to: &str, body: &str) -> Result<(), EmailError>;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_sends_welcome_email() {
        let mut mock = MockEmailService::new();
        mock.expect_send()
            .with(eq("user@example.com"), contains("Welcome"))
            .times(1)
            .returning(|_, _| Ok(()));

        let service = UserService::new(Arc::new(mock));
        service.register("user@example.com").await.unwrap();
    }
}
```

### Async tests and multi-threaded scenarios

```rust
// Single-threaded (default)
#[tokio::test]
async fn test_basic_async() { ... }

// Multi-threaded runtime for testing concurrent behavior
#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn test_concurrent_writes() { ... }
```

### Doc tests

```rust
/// Parses a user ID from a string.
///
/// # Examples
///
/// ```
/// use my_crate::UserId;
///
/// let id = UserId::parse("42").unwrap();
/// assert_eq!(id.value(), 42);
/// ```
///
/// ```should_panic
/// use my_crate::UserId;
/// UserId::parse("not-a-number").unwrap(); // panics
/// ```
pub fn parse(s: &str) -> Result<UserId, ParseError> { ... }
```

### Fuzzing

```rust
// Cargo.toml in fuzz/ directory
// [dependencies]
// libfuzzer-sys = "0.4"

// fuzz/fuzz_targets/parse_input.rs
#![no_main]
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    if let Ok(s) = std::str::from_utf8(data) {
        let _ = my_crate::parse(s);  // Must not panic
    }
});
// Run: cargo fuzz run parse_input
```

---

## Architecture Best Practices

### Workspace layout

```
my-project/
├── Cargo.toml                  # [workspace] members = [...]
├── crates/
│   ├── domain/                 # Core types, traits, no I/O deps
│   │   └── src/lib.rs
│   ├── infrastructure/         # DB, HTTP clients, external APIs
│   │   └── src/lib.rs
│   ├── application/            # Business logic, orchestration
│   │   └── src/lib.rs
│   └── api/                    # HTTP layer (axum/actix-web)
│       └── src/
│           ├── lib.rs
│           └── main.rs
└── tests/
    └── integration/
```

Rules:
- `domain` must not depend on `infrastructure` — only pure types and traits.
- `application` depends on `domain` traits, not `infrastructure` concretions.
- `infrastructure` implements `domain` traits; injected at startup in `main`.
- Compile-time enforcement of layering: wrong imports = compiler error.

### Workspace discipline

```toml
# Root Cargo.toml — declare shared deps and policy ONCE
[workspace.package]
rust-version = "1.91"   # MSRV floor, set by the most-constrained transitive dep

[workspace.dependencies]
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
```

```toml
# Member Cargo.toml — reference, never re-pin
[package]
edition = "2021"        # bump to "2024" ONLY if this crate needs async closures or other 2024-gated features

[dependencies]
tokio = { workspace = true }
serde = { workspace = true }
```

Rules:
- Declare every shared external crate once in `[workspace.dependencies]`; members reference `dep = { workspace = true }`. Never pin locally if it is already in the workspace table — local pins drift and force duplicate compiles.
- MSRV (`rust-version` in `[workspace.package]`) is the floor imposed by the most-constrained TRANSITIVE dependency (e.g. a cloud SDK forcing a newer toolchain), not just the language features your code uses. Verify with `cargo msrv` or by auditing transitive `rust-version`.
- Per-crate edition policy: `edition = "2024"` only for crates that need async closures (`async || {}`) or other 2024-gated features; others stay `2021`. Note let-chains stabilized in Rust 1.88 and work in edition 2021 too, so they are not a reason to upgrade. Check the crate's own `Cargo.toml`, and verify with `cargo check` before upgrading.
- Cross-crate change protocol: edit lib → `cargo check` workspace-wide → `cargo test -p <lib>` → `cargo test -p <each consumer>` → commit all touched `Cargo.toml` together.

### Feature flags

```toml
[features]
default = ["tokio-runtime"]
tokio-runtime = ["dep:tokio"]
async-std-runtime = ["dep:async-std"]
serde = ["dep:serde", "dep:serde_json"]
tracing = ["dep:tracing"]

# Optional dependencies (activated by feature)
[dependencies]
tokio = { version = "1", optional = true }
serde = { version = "1", optional = true }
```

```rust
// Guard feature-specific code
#[cfg(feature = "serde")]
impl Serialize for MyType { ... }

#[cfg(feature = "tracing")]
tracing::info!("processing item");
```

```toml
# Library-and-binary crate: gate the HTTP stack so library consumers don't pull it in.
[features]
default = ["http-server"]          # binary builds stay backward-compatible
http-server = ["dep:axum", "dep:tower-http"]

[dependencies]
axum = { version = "0.7", optional = true }
tower-http = { version = "0.6", optional = true }

[[bin]]
name = "serverd"
required-features = ["http-server"]
```

Rules:
- If a crate is consumed as a library (not only built as a binary), mark `axum`/`tower-http` `optional = true`, gate them behind an `http-server` (or `axum-server`) feature, set `default = ["http-server"]` for backward-compatible binary builds, and add `required-features = ["http-server"]` on `[[bin]]` stanzas. Prevents forcing the full HTTP stack onto library consumers.

### Module layout

```rust
// lib.rs: re-export public API cleanly
pub use self::user::{User, UserId, UserError};
pub use self::service::UserService;

mod user;      // user.rs or user/mod.rs
mod service;   // service.rs

// Keep one public type per file for complex types
// Internal modules use pub(crate) / pub(super) liberally
```

### Shared state patterns

```rust
// AppState: clone-on-use (cheap because Arc internals)
#[derive(Clone)]
struct AppState {
    users: Arc<dyn UserRepository>,
    cache: Arc<dyn Cache>,
    config: Arc<Config>,   // immutable after startup
}

// Pass via axum/actix State extractor, not global statics
// Never use lazy_static or once_cell for mutable service state
```

### Graceful shutdown

```rust
use tokio::signal;

async fn run() -> anyhow::Result<()> {
    let (shutdown_tx, shutdown_rx) = tokio::sync::broadcast::channel(1);

    let server = tokio::spawn(serve(shutdown_rx));

    // Wait for Ctrl+C or SIGTERM
    signal::ctrl_c().await?;
    let _ = shutdown_tx.send(());

    server.await??;
    Ok(())
}

async fn serve(mut shutdown: tokio::sync::broadcast::Receiver<()>) {
    loop {
        tokio::select! {
            _ = accept_connection() => { /* handle */ }
            _ = shutdown.recv() => break,
        }
    }
}
```

#### Production graceful shutdown

```rust
// Prefer axum's built-in drain — finishes in-flight requests before exit.
axum::serve(listener, app)
    .with_graceful_shutdown(shutdown_signal())
    .await?;

async fn shutdown_signal() {
    let ctrl_c = async { signal::ctrl_c().await.expect("install SIGINT handler"); };
    #[cfg(unix)]
    let term = async {
        signal::unix::signal(signal::unix::SignalKind::terminate())
            .expect("install SIGTERM handler").recv().await;
    };
    #[cfg(not(unix))]
    let term = std::future::pending::<()>();
    tokio::select! { _ = ctrl_c => {}, _ = term => {} }
}
```

Rules:
- Prefer `axum::serve(listener, app).with_graceful_shutdown(shutdown_signal())` where `shutdown_signal()` awaits BOTH SIGTERM and SIGINT (cfg-gated Unix/non-Unix). Draining in-flight requests lets storage fsync complete before exit.
- Ops: systemd `KillSignal=SIGTERM` + `TimeoutStopSec=120` (must exceed the fsync window on networked filesystems, e.g. EBS/EFS); on macOS use `launchctl bootout` (SIGTERM + drain), NOT `launchctl kickstart -k` (SIGKILL truncates in-flight writes).
- Clients/bridges reconnect with exponential backoff (200ms → 30s cap) so daemon restarts are transparent.

---

## Performance

- **Avoid cloning**: Restructure to use references or `Cow` before reaching for `.clone()`.
- **`SmallVec<[T; N]>`**: Use for vectors usually small; improves cache locality.
- **Arena allocation**: `bumpalo` for batch-allocating many short-lived objects.
- **Capacity hints**: `String::with_capacity(n)`, `Vec::with_capacity(n)` when final size is predictable.
- **Criterion benchmarks**: `cargo bench` gives statistical benchmarking with warmup.
- **Flamegraph profiling**: `[profile.release] debug = true` then `cargo flamegraph`.
- **LTO for binaries**: `lto = "thin"` + `codegen-units = 1` in release profile.
- **Measure first**: Profile before optimizing any non-obvious path.

---

## Why/What/Test Doc Pattern

```rust
/// Resolves the daemon's data directory, honouring an env override.
///
/// Why:  launchd/systemd strip $HOME, so dirs::* can return None at boot.
/// What: env override → dirs::data_local_dir() → passwd (getpwuid) fallback.
/// Test: tests/paths.rs::resolves_under_empty_env (covers the None branch).
pub fn data_dir() -> anyhow::Result<PathBuf> { ... }
```

Rules:
- Every public `fn`/`struct`/`trait`/`mod` carries three doc-comment lines — `Why:` (the problem it solves), `What:` (mechanics), `Test:` (where coverage lives, or why untestable).
- Clippy cannot enforce intent; this is how future readers reconstruct design without git archaeology.

---

## Safety

- **Minimize unsafe**: Keep `unsafe` blocks as small as possible; wrap in safe abstractions.
- **Safety comments**: Every `unsafe` block requires `// SAFETY:` explaining invariants.
- **Rust 2024 `unsafe fn`**: Function bodies are no longer implicitly unsafe.
- **`unsafe extern` blocks**: Rust 2024 requires `unsafe extern "C" { ... }`.
- **`Send + Sync`**: Auto-implemented when all fields qualify; verify with `static_assertions`.
- **Interior mutability**: `Cell<T>` for `Copy`, `RefCell<T>` single-threaded, `Mutex<T>` multi-threaded.

---

## Anti-Patterns to Avoid

- **Excessive cloning**: Do not clone to satisfy the borrow checker — restructure, use references, or `Cow`.
- **Blocking in async**: Never call `std::fs::read`, `std::net`, or `thread::sleep` in async; use `tokio::` equivalents.
- **Unflushed async writes**: A buffered `tokio::File` write without `flush().await` is a read-after-write data-loss race.
- **Timeout-free HTTP client**: `reqwest::Client::new()` in a service hangs forever on a slow upstream — always `ClientBuilder` with timeouts.
- **Bare `unwrap()` in production**: Replace with `?`, `.unwrap_or_default()`, `.expect("invariant: reason")`.
- **Stringly-typed errors**: No `String` or `Box<dyn Error>` in library APIs — define typed enums with `thiserror`.
- **Half-initialized objects**: Never expose constructors that leave fields unset — use builder pattern.
- **`Deref` for inheritance**: Do not implement `Deref` to simulate OOP — use trait composition.
- **`env::set_var` without `unsafe`**: In Rust 2024, `set_var`/`remove_var` are `unsafe`.
- **Clippy silencing**: `cargo clippy -- -D warnings` in CI; use `#[allow]` with justification, never blanket silencing.
- **Global state for DI**: Do not use `lazy_static`/`once_cell` for mutable services — constructor inject.

---

## Rust Daemon & Supervised-Process Patterns

A daemon launched by `launchd`/`systemd` runs in a stripped environment with aggressive respawn policies. The patterns below assume that supervisor and cross-reference the production graceful-shutdown guidance under Architecture Best Practices.

### Path resolution under supervision

```rust
/// Resolve the data directory: env override → dirs → passwd fallback.
///
/// Why:  under posix_spawn (launchd/systemd) NSFileManager/HOME may be
///       uninitialised, so dirs::data_local_dir() can return None.
/// What: validated env override wins; otherwise dirs, then getpwuid($HOME).
/// Test: tests/paths.rs::env_empty_falls_back_to_passwd.
pub fn data_dir() -> anyhow::Result<PathBuf> {
    if let Ok(raw) = std::env::var("APP_DATA_DIR") {
        let trimmed = raw.trim();
        anyhow::ensure!(!trimmed.is_empty(), "APP_DATA_DIR is empty");
        let p = PathBuf::from(trimmed);
        anyhow::ensure!(p.is_absolute(), "APP_DATA_DIR must be absolute: {p:?}");
        anyhow::ensure!(p != Path::new("/"), "APP_DATA_DIR must not be root");
        return Ok(p);
    }
    let dir = dirs::data_local_dir()        // may be None under a supervisor
        .or_else(passwd_home_data_dir)      // getpwuid() fallback — mandatory
        .ok_or_else(|| anyhow::anyhow!("cannot resolve data dir"))?;
    tracing::info!(path = %dir.display(), "resolved data dir");  // log every boot
    Ok(dir)
}
```

Rules:
- Resolve the data dir as env override → `dirs::data_local_dir()` → `$HOME`/passwd (getpwuid) fallback. The passwd fallback is mandatory: under `posix_spawn`, `dirs::*` can return `None` because HOME/NSFileManager is not initialised.
- Validate any env override is absolute (`anyhow::ensure!(p.is_absolute())`); reject empty/whitespace/relative/root.
- Log the resolved path at INFO on every boot — first thing you check when a supervised daemon "loses" its data.

### File-descriptor limits

```ini
# systemd unit
[Service]
LimitNOFILE=8192
```
```xml
<!-- launchd plist -->
<key>SoftResourceLimits</key>  <dict><key>NumberOfFiles</key><integer>8192</integer></dict>
<key>HardResourceLimits</key>  <dict><key>NumberOfFiles</key><integer>8192</integer></dict>
```

Rules:
- Set `LimitNOFILE=8192` (systemd) / `SoftResourceLimits`+`HardResourceLimits` `NumberOfFiles: 8192` (launchd). The macOS launchd default is 256 — a daemon holding many DB files (e.g. N stores × 3 files) hits EMFILE.
- Combined with `KeepAlive`/`Restart=always`, an EMFILE crash becomes a respawn storm. Expose `open_fds` + `fd_soft_limit` in the `/health` response for early warning.

### Single-instance guard

```rust
// On startup, probe the recorded health address before binding.
if let Ok(resp) = http_get(&recorded_health_url).await {
    if resp.is_healthy() {
        tracing::info!("healthy incumbent already running; exiting");
        std::process::exit(0);   // NOT an error — stops supervisor respawn storm
    }
}
bind_and_serve(addr).await
```

Rules:
- On startup probe the recorded health address; if a healthy incumbent answers, `std::process::exit(0)` instead of binding. This stops launchd/systemd respawn storms without external intervention (a second instance exiting cleanly is success, not failure).
- `std::process::exit` skips destructors, so flush any buffered logs/tracing (e.g. a non-blocking `tracing-appender` worker guard) before calling it — or place the guard before subscriber/buffer init — otherwise the "exiting" line may never be written.

### MCP stdio framing

```rust
// stdio JSON-RPC server: stdout is the protocol channel — keep it pristine.
loop {
    let line = match read_line(&mut stdin).await? {
        Some(l) => l,
        None => std::process::exit(0),  // EOF — exit so idle reqwest pool tasks don't pin the runtime
    };
    let resp = handle(&line).await;
    write_framed(&mut stdout, &resp).await?;   // ONLY protocol frames go to stdout
}
```

Rules:
- In a stdio JSON-RPC server, ALL logs go to stderr — a stray `println!` corrupts the protocol framing. Route `tracing` to stderr explicitly.
- The stdio serve loop must call `std::process::exit(0)` on stdin EOF; otherwise `reqwest` idle-pool background tasks keep the tokio runtime alive and orphaned workers accumulate across client restarts.

---

## Rust Embedded Storage Discipline

Patterns for embedded key/value and document stores (redb / sled / SQLite) with `bincode`/`serde` payloads. The recurring failure mode is a binary upgrade that comes up "healthy but empty" — these rules make degradation impossible without an explicit, recoverable decision.

### Graceful format-upgrade handling

```rust
// Classify EVERY open/create error before deciding what to do.
fn open_or_recreate(path: &Path) -> anyhow::Result<Db> {
    match Db::open(path) {
        Ok(db) => Ok(db),
        Err(e) if is_format_error(&e) => {     // UpgradeRequired / RepairAborted / Corrupted
            run_migration_or_warn(path)?;      // prefer data-preserving migration
            recreate(path)                     // destructive ONLY for format breaks
        }
        Err(e) if is_lock_error(&e) => Err(e.into()),   // DatabaseAlreadyOpen — NEVER recreate
        Err(e) => Err(e.into()),                        // transient I/O — NEVER recreate
    }
}
```

Rules:
- At EVERY open/create site classify errors: `UpgradeRequired`/`RepairAborted`/`Corrupted` = incompatible on-disk format; `DatabaseAlreadyOpen` = lock contention; everything else = transient I/O.
- Destructive recreate ONLY on format errors — NEVER on lock or I/O errors (a lock error means another instance owns live data; an I/O error is transient).
- Ship a data-preserving migration tool for format breaks. A binary upgrade must never silently degrade to "healthy but empty".

### Atomic swap for durable rebuilds

```rust
// Reindex/compaction/migration writes to staging; swap only on validated success.
let staging = root.join("index.staging");
build_into(&staging)?;
anyhow::ensure!(record_count(&staging)? > 0, "rebuild produced 0 records — Failed, not Ready");
fs::rename(&staging, root.join("index.live"))?;   // atomic swap
// On any failure/empty/abort: discard staging, leave previous live data intact.
```

Rules:
- Any reindex/compaction/migration writes to a STAGING location and swaps atomically only on success; on failure/empty/abort, discard the staged copy and leave the previous live data intact.
- Validate non-empty before marking ready — a pipeline that walked files but produced zero records is `Failed`, not `Ready` (the false-green antipattern).

### Root-relative path storage

```rust
// Store paths relative to a canonical root — survives moves, remounts, cross-platform copies.
let root = root.canonicalize()?;                  // so strip_prefix reliably yields relative
let rel = abs_path.strip_prefix(&root)?.to_path_buf();
store.put(key, &rel)?;                            // persist relative, never absolute
```

Rules:
- Store file paths relative to a known root, never absolute — survives data-dir moves, remounts, and cross-platform copies. Canonicalize the root so `strip_prefix` reliably yields a relative path.
- Provide an idempotent, schema-versioned migration that detects and rewrites legacy absolute paths on warm boot.
