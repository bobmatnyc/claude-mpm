---
name: toolchains-typescript-core
description: "TypeScript 5.6+ core patterns for minimalism, efficiency, type safety, and performance"
version: "2.0.0"
category: toolchains-typescript
tags: [typescript, patterns, performance, minimalism, type-safety]
effort: medium
---

# TypeScript Core Patterns

Modern TypeScript development patterns for 5.6+ targeting minimal code, maximum type safety, and optimal bundle performance.

## Quick Start

**New project:** Start with tsconfig baseline below → Enable `strict` + `noUncheckedIndexedAccess` → Use Zod for runtime validation at boundaries → Vitest for testing.

**Existing project:** Enable `strict: false` initially → Replace `any` with `unknown` → Add `noUncheckedIndexedAccess` → Incrementally tighten.

## tsconfig Baseline (2025)

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "skipLibCheck": true,
    "declaration": true,
    "declarationMap": true
  }
}
```

## Minimalism Patterns

- Use `satisfies` to validate types without widening: `const routes = {...} satisfies Record<string, Route>`
- Use `as const` for literal type inference on objects and arrays — eliminates separate type definitions
- Prefer utility types (`Pick`, `Omit`, `Partial`, `Required`, `Record`) over manual type duplication
- Discriminated unions over type guards — let the compiler narrow automatically via `switch`/`if`
- Template literal types for compile-time string validation: `` type Route = `/api/${string}` ``
- `Readonly<T>` and `ReadonlyArray<T>` for immutable data — prevents accidental mutation
- Let TypeScript infer return types for internal functions — annotate only public API boundaries

## Efficiency / Bundle Optimization

- `import type { Foo }` with `verbatimModuleSyntax` — ensures type imports are erased at compile time
- Avoid barrel files (`index.ts` re-exports) — they prevent tree-shaking and slow builds
- `sideEffects: false` in `package.json` — enables aggressive dead code elimination
- Dynamic `import()` for code splitting — load heavy modules on demand, not at startup
- ESM output (`"module": "NodeNext"`) — enables tree-shaking across the entire dependency graph
- Avoid runtime type checks in hot paths — validate once at boundaries, trust types internally
- Keep generic type depth shallow (≤3 levels) — deep generics slow the compiler and confuse developers

## Code Reuse

- Generic constraints: `<T extends { id: string }>` — just enough constraint, no more
- Conditional types with `infer`: `type Unwrap<T> = T extends Promise<infer U> ? U : T`
- Mapped types with `as` clause for key transformation: `{ [K in keyof T as `on${Capitalize<K>}`]: ... }`
- Module augmentation for extending third-party types without forking
- Branded/nominal types for type-safe IDs: `type UserId = string & { __brand: 'UserId' }`
- Shared utility types: `Brand<T,B>`, `DeepPartial<T>`, `Prettify<T>` in a project `types/` directory
- `NoInfer<T>` (TS 5.4+) — prevents unwanted type parameter inference in function arguments

## Modern TypeScript (5.4-5.7)

- **`NoInfer<T>`** (5.4) — control where type inference happens in overloaded/generic functions
- **`using` declarations** (5.2+) — automatic resource cleanup via `[Symbol.dispose]`
- **`--noCheck`** (5.6) — emit-only builds, skip type checking for faster CI artifact generation
- **`--rewriteRelativeImportExtensions`** (5.7) — enables direct `.ts` execution without build step
- **`--target es2024`** — unlocks `Object.groupBy`, `Promise.withResolvers`, `Map.groupBy` in type system
- Stricter truthy/nullish checks (5.6) — catches `Boolean(0)` and `x ?? fallback` pitfalls
- Improved never-initialized variable checks — compiler detects variables used before assignment

## React Performance (brief)

- `React.memo` only when profiler shows unnecessary re-renders — not as a default
- `useDeferredValue` paired with memo for expensive renders during state transitions
- `useTransition` for non-urgent state updates to keep UI responsive
- React 19 Compiler auto-optimizes — reduces need for manual `useCallback`/`useMemo`
- Virtualize long lists (>100 items) with `@tanstack/virtual` or `react-window`

## Testing

- **Vitest** as default test runner — Vite-native, faster than Jest, same API
- Type-level tests with `expectTypeOf` in `*.test-d.ts` files — catches type regressions
- `vitest --typecheck` runs type tests alongside unit tests in one pass
- Type-safe mocks with `vi.fn<(args: Params) => Return>()` — no `any` leakage
- Zod schemas at runtime boundaries (API input, env vars) — `z.infer<typeof Schema>` for types
- Snapshot testing for complex object shapes — `toMatchInlineSnapshot()` for small outputs

## Anti-Patterns

- ❌ `any` type — use `unknown` and narrow, or `as const satisfies` for complex literals
- ❌ `async` in `.forEach()` — iterations don't await; use `for...of` with `await` or `Promise.all`
- ❌ Over-typing: writing types the compiler already infers — adds noise, increases maintenance
- ❌ Unnecessary classes — prefer plain functions and objects; classes only for stateful abstractions
- ❌ Type assertions (`as Type`) — masks errors; prefer type guards or `satisfies`
- ❌ Duplicated/derived state — compute from source of truth, don't sync separate state copies
