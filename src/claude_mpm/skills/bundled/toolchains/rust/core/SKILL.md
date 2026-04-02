---
name: toolchains-rust-core
description: "Rust 2024 edition core patterns for minimalism, efficiency, code reuse, and performance"
version: "1.0.0"
category: toolchains-rust
tags: [rust, patterns, performance, minimalism, efficiency, safety]
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

[dev-dependencies]
proptest = "1"
mockall = "0.13"
insta = "1"
criterion = "0.5"
```

```bash
cargo add tokio --features full && cargo add thiserror anyhow
cargo clippy -- -D warnings   # enforce in CI
cargo test                    # unit + integration + doctests
```

## Minimalism Patterns

- **Builder pattern**: Use consuming `self` methods; finish with `build() -> Result<T, E>` for validated construction.
- **Newtype pattern**: `struct UserId(u64)` gives type safety at zero cost; add `impl From<u64> for UserId`.
- **From/Into**: Implement `From<T>` only -- `Into<T>` is blanket-provided; accept `impl Into<T>` in function params.
- **Derive by default**: `#[derive(Debug, Clone, PartialEq, Eq, Hash)]` on domain types; add `serde` only when needed.
- **Type state**: Encode state machines as generic marker types -- invalid transitions become compile errors, not panics.
- **Borrowed params**: Accept `&str` not `&String`, `&[T]` not `&Vec<T>`, `impl AsRef<Path>` not `&PathBuf`.
- **Default for config**: `Config { field: value, ..Default::default() }` -- audit all fields when adding new ones.
- **RAII guards**: Use `Drop` for resource cleanup; wrap locks, file handles, and connections in guard types.

## Efficiency

- **Zero-cost abstractions**: Iterator chains compile to identical (often better) machine code than manual loops.
- **Stack vs heap**: Default to stack; use `Box` only for trait objects, recursive types, or large data escaping scope.
- **`Cow<'_, str>`**: Return `Cow<'_, str>` when sometimes borrowing, sometimes owning -- avoids unnecessary clones.
- **`SmallVec<[T; N]>`**: Use for vectors usually small (N known at design time); improves cache locality.
- **Arena allocation**: Use `bumpalo` for batch-allocating many short-lived objects; eliminates per-object overhead.
- **Capacity hints**: `String::with_capacity(n)`, `Vec::with_capacity(n)` when final size is predictable.
- **Iterators over indexing**: `.iter()` / `.iter_mut()` eliminate bounds checks and enable autovectorization.
- **`#[inline]`**: Annotate small hot-path functions in library crates; LTO handles application binaries.

## Code Reuse

- **Trait composition**: Build from small traits (`Readable`, `Writable`); combine with supertraits (`trait ReadWrite: Readable + Writable`).
- **Blanket impls**: `impl<T: Display> MyTrait for T` provides default behavior for all qualifying types.
- **Extension traits**: Add methods to foreign types via `trait IteratorExt: Iterator` with a blanket impl.
- **GATs**: Use Generic Associated Types (stable since 1.65) for lending iterators and lifetime-parameterized associated types.
- **`derive_more`**: Use `derive_more` crate to reduce boilerplate for `Display`, `From`, `Into`, `Constructor`.
- **Static vs dynamic dispatch**: Default to generics (`impl Trait`); use `dyn Trait` only for heterogeneous collections or runtime polymorphism.
- **Module layout**: One public type per file for complex types; re-export cleanly via `lib.rs`.
- **Sealed traits**: Use sealed trait pattern to prevent external implementations while keeping the trait public as a bound.

## Modern Async (Tokio)

- **Tokio only**: Tokio is the ecosystem standard; async-std is effectively unmaintained as of 2026.
- **Async closures**: Use `async || { ... }` (Rust 2024); `Future` and `IntoFuture` are in the prelude -- no imports needed.
- **`thiserror` for libraries**: `#[derive(thiserror::Error, Debug)]` with `#[error("...")]` and `#[from]` for conversions.
- **`anyhow` for applications**: `anyhow::Result<T>` in `main()` and CLI code; chain context with `.context("what we were doing")`.
- **Never `anyhow` in library public APIs**: Libraries must return concrete error types so callers can pattern-match variants.
- **Tower middleware**: Compose timeout, retry, rate-limiting as Tower `Layer`s via `ServiceBuilder::new().layer(...).service(svc)`.
- **Structured concurrency**: `tokio::join!` for concurrent execution, `tokio::select!` for racing, `JoinSet` for dynamic task groups.
- **Cancellation safety**: Use RAII drop guards for cleanup; avoid holding mutable state across `.await` points.
- **`spawn_blocking`**: Wrap CPU-bound or synchronous I/O in `tokio::task::spawn_blocking`; never block the async executor.

## Performance

- **Avoid cloning**: Restructure to use references or `Cow` before reaching for `.clone()`; clone only when ownership transfer is required.
- **Fused iterator pipelines**: `.filter().map().flat_map()` chains compile to a single loop with no intermediate allocations.
- **Rayon for parallelism**: Replace `.iter()` with `.par_iter()` for CPU-bound data; always benchmark -- Rayon has overhead on small workloads.
- **Criterion benchmarks**: `cargo bench` with `criterion` gives statistical benchmarking with warmup and outlier detection.
- **Flamegraph profiling**: `[profile.release] debug = true` then `cargo flamegraph`; identify hotspots before optimizing.
- **LTO for binaries**: `lto = "thin"` in release profile enables cross-crate inlining; `codegen-units = 1` for maximum optimization.
- **PGO**: For maximum throughput, use profile-guided optimization: instrument, run representative workload, recompile with profile data.
- **Measure first**: Readable code is correct code -- profile before optimizing any non-obvious path.

## Safety

- **Minimize unsafe**: Keep `unsafe` blocks as small as possible; wrap in safe abstractions with documented invariants.
- **Safety comments**: Every `unsafe` block requires `// SAFETY:` explaining why invariants hold (`clippy::undocumented_unsafe_blocks`).
- **Rust 2024 `unsafe fn`**: Function bodies are no longer implicitly unsafe -- wrap operations in explicit `unsafe {}` blocks.
- **`unsafe extern` blocks**: Rust 2024 requires `unsafe extern "C" { ... }` -- makes FFI boundaries explicit.
- **Pin/Unpin**: `Pin<P>` prevents moving the pointee; required for self-referential types and futures; most types are `Unpin`.
- **`Send + Sync`**: `Send` = safe to transfer between threads; `Sync` = safe to share references; auto-implemented when all fields qualify.
- **Interior mutability**: `Cell<T>` for `Copy` types, `RefCell<T>` for single-threaded, `Mutex<T>`/`RwLock<T>` for multi-threaded.
- **Atomics over mutexes**: `AtomicBool`, `AtomicUsize` for simple flags and counters; `Ordering::SeqCst` by default until you have proof otherwise.

## Testing

- **Test placement**: `#[cfg(test)] mod tests` in the same file for unit tests; `tests/` directory for integration tests.
- **`proptest` for invariants**: `proptest!` macro with strategy-based generation; use `prop_assert!` for rich failure output.
- **`mockall` for traits**: `#[cfg_attr(test, mockall::automock)]` generates mock implementations at test compile time only.
- **Async tests**: `#[tokio::test]` for async; `#[tokio::test(flavor = "multi_thread")]` when testing concurrent behavior.
- **Doc tests**: ```` ```rust ```` blocks in doc comments run with `cargo test`; use `# ` prefix to hide setup boilerplate.
- **Test builders**: `TestUserBuilder::default().with_role(Role::Admin).build()` -- override only the fields relevant to each case.
- **Snapshot testing**: Use `insta` for serialized output and error messages; review diffs with `cargo insta review`.
- **Fuzzing**: `cargo-fuzz` with `libFuzzer` for security-critical parsers; define targets in `fuzz/fuzz_targets/`.

## Anti-Patterns to Avoid

- **Excessive cloning**: Do not clone to satisfy the borrow checker -- restructure, use references, or reach for `Cow`.
- **Blocking in async**: Never call `std::fs`, `std::net`, or `std::thread::sleep` in async functions; use `tokio::fs`, `tokio::net`, `tokio::time::sleep`.
- **Bare `unwrap()` in production**: Replace with `?`, `.unwrap_or_default()`, `.expect("invariant: reason")`, or pattern matching.
- **Stringly-typed errors**: Do not use `String` or `Box<dyn Error>` in library public APIs -- define typed enums with `thiserror`.
- **Half-initialized objects**: Never expose constructors that leave fields unset; use builder pattern or require all fields upfront.
- **`Deref` for inheritance**: Do not implement `Deref` to simulate OOP -- use trait composition and delegation; `Deref` is for smart pointers.
- **`env::set_var` without `unsafe`**: In Rust 2024, `set_var`/`remove_var` are `unsafe` -- wrap in `unsafe {}` with thread-safety comment.
- **Clippy silencing**: `cargo clippy -- -D warnings` in CI; use `#[allow(clippy::rule)]` with justification, never blanket silencing.
