---
name: toolchains-golang-core
description: "Go 1.22+ core patterns for minimalism, efficiency, code reuse, and performance"
version: "1.0.0"
category: toolchains-golang
tags: [golang, go, patterns, performance, minimalism, efficiency]
effort: medium
---

# Go Core Patterns

## Quick Start

- Accept interfaces, return structs — small interfaces at the consumer site
- Pre-allocate slices/maps with `make([]T, 0, n)` / `make(map[K]V, n)`
- Wrap errors with `%w`; check with `errors.Is` / `errors.As`
- Always run `go test -race ./...` in CI
- Profile with `go tool pprof` before optimizing anything

---

## Minimalism Patterns

- **Accept interfaces, return structs** — narrow interface params improve testability; concrete return types preserve extensibility
- **Define interfaces at the consumer** — the calling package defines what it needs; avoid coupling interface to implementation
- **Keep interfaces small** — 1-2 methods; compose with embedding: `type ReadWriter interface { Reader; Writer }`
- **Functional options for constructors** — `func WithTimeout(d time.Duration) Option` returns a closure; keeps `New*` signatures stable
- **Unexported option fields** — export `With*` functions, keep struct fields private; one construction path, predictable outcome
- **Constructor naming** — `NewServer(opts ...Option) *Server`; the injection point for interface-typed dependencies
- **Avoid `init()` side effects** — prefer explicit initialization in `main()` or constructors; `init()` hides execution order

---

## Efficiency Patterns

- **Pre-allocate slices** — `make([]T, 0, n)` eliminates grow-copy cycles; reduces GC pressure ~30%
- **Pre-allocate maps** — `make(map[K]V, n)` avoids rehashing; over-estimate rather than under-estimate
- **`strings.Builder` over `+`** — internal `[]byte` buffer; call `b.Grow(n)` to pre-size before writing
- **`sync.Pool` for short-lived objects** — reuse buffers, byte slices, response structs; always reset before returning to pool
- **Avoid `any` / `interface{}` in hot paths** — boxing causes heap allocation and dynamic dispatch; use concrete types or generics
- **`strconv` over `fmt.Sprintf` in hot paths** — `fmt` arguments escape to heap; `strconv.Itoa`, `AppendInt` stay on stack
- **Value receivers for small immutable types** — no pointer indirection; both `T` and `*T` satisfy value-receiver methods
- **Pointer receivers for large structs or mutation** — avoids copying; be consistent within a type (all pointer or all value)
- **Return values not pointers for small types** — keeps allocation on stack; reduces GC pressure in tight loops
- **Move loop-invariant work outside loops** — constant calculations inside hot loops multiply with iteration count

---

## Code Reuse

- **Generics: `any` for store/pass only** — no operations needed; suitable for containers like `Stack[T any]`
- **Generics: `comparable` for equality** — required for map keys, sets, `Contains()`; `any` does not satisfy `comparable`
- **Generics: `constraints.Ordered` for comparisons** — covers int, float, string; needed for sort, min, max helpers
- **Generics: prefer function params over method constraints** — pass `cmp func(T, T) int` rather than requiring a `Compare` method
- **Generics: start concrete, genericize on duplication** — add type params only when the same logic repeats for multiple types
- **Embed structs for implementation reuse** — promoted fields and methods; override selectively; avoid deep embedding chains
- **Domain packages over layer packages** — `internal/user/`, `internal/order/` not `internal/handlers/`, `internal/services/`
- **No catch-all `utils` packages** — every package has a focused purpose; move helpers into the domain that owns them

---

## Modern Go (1.22-1.23)

- **Range over integers (1.22)** — `for i := range 10` replaces `for i := 0; i < 10; i++`
- **Loop variable fix (1.22)** — each iteration creates new variables; closure capture bugs eliminated
- **Enhanced `ServeMux` (1.22)** — `"GET /items/{id}"` registers method + wildcard; `r.PathValue("id")` extracts segments
- **Wildcard catch-all (1.22)** — `"/files/{path...}"` matches remaining path; must appear at end of pattern
- **`Request.Pattern` (1.23)** — matched pattern available on the request for logging and observability
- **Range over function iterators (1.23)** — `func(func(K, V) bool)` as range expressions; stable in 1.23
- **`iter` package (1.23)** — `iter.Seq[V]` and `iter.Seq2[K, V]` standard types; foundation for custom iterators
- **`slices` / `maps` iterators (1.23)** — `slices.All`, `slices.Collect`; `maps.Keys`, `maps.Values`, `maps.Collect`
- **`unique` package (1.23)** — canonical interning of comparable values; deduplication and memory savings
- **`slog` for structured logging** — JSON handler in prod, text in dev; `slog.SetDefault` bridges legacy `log.Printf` calls
- **Contextual log fields** — pass `request_id`, `user_id`, `trace_id` via `slog.With()` to correlate log lines
- **`LogValuer` for sensitive types** — redact PII; skips expensive computation when log level is disabled

---

## Performance

- **Profile first** — `go tool pprof` for CPU, heap, mutex, goroutine; never optimize without measurement data
- **`inuse_space` for leak detection** — `alloc_space` is lifetime total; `inuse_space` is currently retained memory
- **Escape analysis** — `go build -gcflags="-m"` shows heap escapes; target hot-path allocations
- **Returning pointers causes escape** — local variable outlives function; prefer return-by-value for small types
- **Closures in hot loops allocate** — avoid closures in tight loops; pass values as explicit function arguments
- **Struct field ordering** — largest to smallest reduces padding; use `fieldalignment` linter to verify
- **Avoid false sharing** — pad cache lines between fields accessed by different goroutines in concurrent structs
- **Size channels deliberately** — unbuffered for synchronization; buffered with known capacity for decoupling; never unbounded
- **`errgroup` for fan-out** — `golang.org/x/sync/errgroup` propagates first error and waits for all goroutines; replaces manual `WaitGroup` + error channel
- **Context cancellation** — pass cancellable `context.Context`; check `ctx.Done()` in goroutine loops to prevent leaks

---

## Testing

- **Table-driven + `t.Run`** — named subtests allow selective execution with `-run TestFoo/case_name`
- **Parallel subtests** — `t.Parallel()` inside `t.Run` reduces suite runtime ~30-40%; ensure no shared mutable state
- **`testify/require` for setup, `assert` for checks** — `require` stops immediately on failure; `assert` continues and collects failures
- **`httptest.NewServer`** — real HTTP on localhost; tests full request/response cycle without mocking transport
- **Fuzz testing** — `f.Add(seed)` then `f.Fuzz(func(t *testing.T, s string){...})`; run with `-fuzz` flag and `-fuzztime` in CI
- **`testcontainers-go`** — spin up real Postgres, Redis, or any Docker image during integration tests
- **`goleak.VerifyNone(t)`** — fails if goroutines survive after test completes; catches goroutine leaks early
- **Always `-race`** — `go test -race ./...` in CI; required for all concurrent code
- **`t.Cleanup`** — registered functions run LIFO after test; prefer over manual `defer` teardown

---

## Error Handling

- **Wrap with `%w`** — `fmt.Errorf("load config: %w", err)` preserves chain for `errors.Is` / `errors.As`
- **`errors.Is` for sentinel checks** — traverses wrapping chain; replaces direct `err == ErrNotFound` comparison
- **`errors.As` for typed extraction** — `var e *APIError; errors.As(err, &e)` pulls typed error from any depth
- **Sentinel errors as package vars** — `var ErrNotFound = errors.New("not found")`; exported for expected recoverable conditions
- **Custom error types for rich context** — implement `Error() string` and `Unwrap() error`; carry HTTP status, codes, metadata
- **Handle errors immediately** — `if err != nil` right after the call; early return; no deep nesting
- **`errors.Join` for concurrent errors** — since Go 1.20; collect multiple goroutine errors into one returned value
- **Panic only for programmer errors** — nil map write, index out of bounds; never panic for expected runtime failures in libraries
- **Recover at goroutine boundaries** — `defer func() { if r := recover(); r != nil { log... } }()` prevents cascade crashes

---

## Anti-Patterns

- **Goroutine leak: unclosed channel** — `range` over a channel blocks forever if sender never closes; always close from the sender
- **Goroutine leak: unbuffered send, no receiver** — goroutine blocks permanently; use buffered channel or `select` with `ctx.Done()`
- **Goroutine leak: early return without draining** — buffer results or use `select` with context so goroutines can exit
- **`time.Sleep` for synchronization** — use `sync.WaitGroup`, channels, or `context`; Sleep is a race condition
- **Copying `sync.Mutex` / `sync.WaitGroup`** — always pass by pointer; copying creates an independent, incorrect lock
- **`init()` with side effects** — database connections, file reads, HTTP calls in `init()` make testing and reuse impossible
- **Naked returns in long functions** — named returns with bare `return` obscure flow in functions longer than ~5 lines
- **`utils` / `common` / `helpers` packages** — signals unclear ownership; split into domain-specific packages instead
