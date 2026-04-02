---
name: toolchains-java-core
description: "Java 21+ core patterns for minimalism, efficiency, code reuse, and performance"
version: "1.0.0"
category: toolchains-java
tags: [java, patterns, performance, minimalism, efficiency, virtual-threads]
effort: medium
---

# Java Core Patterns

Modern Java development patterns targeting 21+ LTS for minimal, efficient, reusable, and performant code.

## Quick Start

**New code:** Use records for DTOs/value objects, sealed classes + pattern matching for type-safe dispatch, virtual threads for I/O-bound concurrency, `SequencedCollection` for ordered access.

**Performance:** Profile first with JFR/async-profiler. Use JMH for benchmarks, Generational ZGC for low-latency, Stream API for declarative data transforms.

## Minimalism Patterns

- Use `record` for immutable data carriers — eliminates boilerplate (equals, hashCode, toString, accessors)
- Prefer `switch` expressions over if-elif chains; leverage pattern matching with `instanceof` to collapse cast+check
- Use `sealed` classes/interfaces to restrict type hierarchies — compiler verifies exhaustiveness in switch
- Use `var` for local variables when type is obvious from RHS — improves readability, not a replacement for field types
- Unnamed variables (`_`) for unused bindings in patterns, catch blocks, and lambdas (Java 22+)
- Prefer `Optional` return types over nullable returns — never use `Optional` as field or parameter type
- Use text blocks (`"""`) for multi-line strings — SQL, JSON, HTML templates
- Guard clauses (`when`) in switch patterns eliminate nested if-conditions inside cases

## Efficiency Patterns

- Stream API for declarative collection transforms; prefer `toList()` (Java 16+) over `collect(Collectors.toList())`
- `SequencedCollection` (Java 21) for `getFirst()`/`getLast()`/`reversed()` — replaces index-based access hacks
- `Map.of()`, `List.of()`, `Set.of()` for immutable collections — avoid `Collections.unmodifiableX()` wrappers
- `String.formatted()` or `"".formatted()` over `String.format()` for readability
- Pre-size `ArrayList` and `HashMap` when capacity is known — avoids rehashing/reallocation
- Use `EnumMap`/`EnumSet` for enum-keyed collections — array-backed, faster than HashMap
- `StringBuilder` for string concatenation in loops; single expressions use `+` (JIT optimizes)
- Batch JDBC operations with `addBatch()`/`executeBatch()` — never N+1 queries

## Code Reuse

- **Sealed interfaces** for closed type hierarchies — records as implementations for algebraic data types
- **Composition over inheritance** — inject dependencies via constructor, use interfaces for contracts
- **Default methods** on interfaces for shared behavior without abstract classes
- **Records as value objects** — immutable, compact, pattern-matchable domain types
- **Service interfaces** with single responsibility — small contracts, easy to mock in tests
- Extract shared logic to static utility methods or dedicated service classes, not base classes
- `Function`, `Predicate`, `Supplier` functional interfaces for composable behavior

## Modern Java (21-23)

- **Records** (Java 16+, finalized): Immutable data carriers with auto-generated accessors, equals, hashCode, toString
- **Sealed classes** (Java 17+): `sealed interface Shape permits Circle, Rect` — exhaustive pattern matching
- **Pattern matching for switch** (Java 21): Type patterns, record patterns, guard clauses (`when`), null handling
- **Virtual threads** (Java 21): `Thread.ofVirtual().start()` or `Executors.newVirtualThreadPerTaskExecutor()` — millions of threads
- **Structured concurrency** (preview): `StructuredTaskScope` for grouped subtask lifecycle — fork/join/throwIfFailed
- **Scoped values** (preview): Immutable context propagation replacing ThreadLocal patterns
- **Sequenced collections** (Java 21): `SequencedCollection`, `SequencedSet`, `SequencedMap` with defined encounter order
- **Unnamed patterns** (Java 22): `_` for unused variables in patterns, catches, lambdas
- **Foreign Function & Memory API** (Java 22, finalized): Native interop replacing JNI

## Performance

- **Profile first**: JFR (Java Flight Recorder) for production profiling, async-profiler for low-overhead sampling, JMH for microbenchmarks
- **Generational ZGC** (Java 21): Sub-millisecond pauses regardless of heap size; tune `SoftMaxHeapSize` for predictable RSS
- **Shenandoah GC**: Low-latency alternative; `ShenandoahGCHeuristics=adaptive` for containerized workloads
- **G1 GC** (default): Best general-purpose choice; ZGC/Shenandoah for ultra-low-latency requirements
- **Virtual threads for I/O**: Replace thread pools for I/O-bound work — avoid `synchronized` blocks (causes pinning)
- Use `ReentrantLock` instead of `synchronized` with virtual threads to prevent carrier thread pinning
- **JIT optimization**: `-XX:+TieredCompilation` for startup/peak balance; warm up JVM before benchmarking
- Avoid autoboxing in hot loops — use primitive specializations (`IntStream`, `LongStream`, `mapToInt`)
- Minimize object allocation in hot paths — reuse builders, use primitive arrays where possible

## Testing

- **JUnit 5**: `@ParameterizedTest` with `@MethodSource`/`@CsvSource` for data-driven tests; `assertAll()` for grouped assertions
- **Mockito**: `@ExtendWith(MockitoExtension.class)` — mock external dependencies only, never the class under test
- **AssertJ**: Fluent assertions — `assertThat(result).isNotNull().hasSize(3).contains("expected")`
- **Testcontainers**: Real databases/queues in Docker — use fixed image tags (e.g., `postgres:15`), proper cleanup
- **jqwik**: Property-based testing for edge-case discovery with generated inputs
- **ArchUnit**: Architecture tests — enforce layer boundaries, dependency rules, naming conventions
- Test naming: `shouldReturnUser_whenValidIdIsGiven()` — behavior-focused, not method-focused
- Integration tests with `@SpringBootTest` + `@Testcontainers` for full-stack validation

## Anti-Patterns

- Mutable default arguments: `Collections.emptyList()` returned then modified — use `List.of()` (truly immutable)
- Raw types: `List` instead of `List<String>` — loses type safety, produces unchecked warnings
- Checked exceptions for control flow — use unchecked exceptions or `Optional` for expected absent values
- `synchronized` with virtual threads — causes carrier thread pinning, use `ReentrantLock`
- Overusing inheritance — prefer composition and sealed interfaces for type hierarchies
- `null` returns from methods — use `Optional<T>` for values that may be absent
- Ignoring try-with-resources — always use `try (var resource = ...)` for `AutoCloseable` resources
- God classes with multiple responsibilities — decompose into focused services with single responsibility
- Catching `Exception` or `Throwable` — catch specific exceptions, let unexpected ones propagate
