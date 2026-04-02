---
name: toolchains-python-core
description: "Python 3.12+ core patterns for minimalism, efficiency, code reuse, and performance"
version: "1.0.0"
category: toolchains-python
tags: [python, patterns, performance, minimalism, efficiency]
effort: medium
---

# Python Core Patterns

Modern Python development patterns targeting 3.12-3.13+ for minimal, efficient, reusable, and performant code.

## Quick Start

**New code:** Use `@dataclass(slots=True)` for data classes, PEP 695 generics (`def first[T](...)`), `Protocol` for structural typing, `TaskGroup` for async concurrency.

**Performance:** Profile first with `py-spy` or `scalene`. Use generators for single-pass iteration, `set` for membership tests, connection pooling for I/O.

## Minimalism Patterns

- Use walrus operator (`:=`) in while-loops and comprehension filters to eliminate duplicate calls — avoid in deeply nested expressions
- Prefer `match/case` over if-elif chains for structural/type dispatch; powerful with dataclass destructuring
- Use `@dataclass(frozen=True)` for value objects, `@dataclass(slots=True)` for memory savings (~200 bytes/instance)
- Use `NamedTuple` for lightweight immutable records; `dataclass` when you need defaults, mutability, or methods
- Always use `field(default_factory=list)` for mutable defaults — never `def f(items=[])`
- Prefer `dict.get(key, default)` over `if key in dict` for simple lookups
- Use `contextlib.suppress(Exception)` instead of empty `try/except/pass`

## Efficiency Patterns

- Generator expressions for single-pass iteration; list comprehensions for building lists (20-30% faster than loops)
- `__slots__` or `@dataclass(slots=True)` reduces per-instance memory by 200+ bytes
- `set` for membership testing (O(1) vs O(n) for lists), `frozenset` for hashable sets
- `str.join()` over `+=` for string building; f-strings over `.format()` (fastest string formatting)
- `itertools` for composable lazy iteration: `chain`, `islice`, `groupby`, `batched` (3.12+)
- `memoryview` for zero-copy binary slicing on large buffers
- `@functools.lru_cache` / `@functools.cache` (3.9+) for memoization of pure functions
- `collections.deque` for O(1) append/pop from both ends; `defaultdict` to avoid key existence checks
- Batch database operations — use `executemany()` or bulk inserts, never N+1 loops

## Code Reuse

- **Protocol over ABC** when you want structural typing without inheritance — duck typing with type safety
- **ABC** when you need shared implementation or runtime `isinstance()` enforcement
- Composition over inheritance; `functools.partial` for specialization without subclassing
- `functools.cached_property` for one-time expensive computed attributes (thread-safe in 3.12+)
- Small, single-responsibility Protocols composed together beat large interfaces
- Use `typing.overload` for functions with type-dependent return signatures
- Extract shared logic into standalone functions, not base classes — flat is better than nested

## Modern Python (3.12-3.13)

- **PEP 695 generics** (3.12+): `def first[T](lst: list[T]) -> T:` replaces `TypeVar` boilerplate (60% reduction)
- **`type` statement** (3.12+): `type Vector = list[float]` replaces `TypeAlias`
- **`TypeIs`** (3.13) preferred over `TypeGuard` — narrows both branches of conditional
- **`TaskGroup`** (3.11+) replaces `asyncio.gather()` — structured concurrency with auto-cancellation on failure
- **`except*`** (3.11+) for handling `ExceptionGroup` from concurrent failures
- Never swallow `CancelledError`; call `task.result()` outside the `async with` block
- `tomllib` in stdlib (3.11+) for TOML parsing — no external dependency needed
- `ReadOnly` TypedDict items (3.13) for immutable typed dict fields

## Performance

- **Profile first**: `cProfile` for call counts, `py-spy`/`scalene` for line-level profiling, `tracemalloc` for memory leaks
- `TaskGroup` for structured async I/O concurrency; `ProcessPoolExecutor` for CPU-bound offloading
- Connection pooling mandatory for databases and HTTP — never open/close per request
- Eager-load related data to prevent N+1 queries; use `selectinload()` in SQLAlchemy
- `uvloop` for 2-4x async event loop throughput (drop-in replacement for asyncio loop)
- Pre-allocate collections when size is known: `list(range(n))`, `bytearray(n)`
- Avoid `global` lookups in tight loops — assign to local variable first
- **Free-threaded mode** (3.13t) shows ~80% improvement for multi-threaded CPU tasks — experimental, not for production

## Type Safety

- `mypy --strict` for new projects; gradual adoption with `--disallow-untyped-defs` for existing
- `Protocol` for structural subtyping — don't force users to inherit from your base class
- `ParamSpec` + `Concatenate` for typing decorators that modify function signatures
- `Self` type (3.11+) for fluent method chaining returns
- `TypedDict` for typed dictionaries with known keys; `Unpack` for kwargs typing
- Run mypy in CI with zero tolerance for type errors on new code

## Anti-Patterns

- ❌ Mutable default arguments: `def f(items=[])` — shared across calls
- ❌ Bare `except:` — catches `KeyboardInterrupt`, `SystemExit`; use `except Exception:`
- ❌ `eval()` / `exec()` on untrusted input — injection vulnerability
- ❌ Inconsistent return types: sometimes `None`, sometimes value — use `Optional[T]` explicitly
- ❌ `isinstance()` chains instead of polymorphism or `match/case`
- ❌ Ignoring `with` statements for file/connection/lock resources
- ❌ Cargo-cult patterns: `@property` getters that just return an attribute
- ❌ LBYL (Look Before You Leap) — prefer EAFP (Easier to Ask Forgiveness)
