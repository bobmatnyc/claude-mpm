---
name: toolchains-javascript-core
description: "JavaScript ES2024+ and Node.js 22+ core patterns for minimalism, efficiency, code reuse, and performance"
version: "1.0.0"
category: toolchains-javascript
tags: [javascript, nodejs, patterns, performance, minimalism, efficiency]
effort: medium
---

# JavaScript Core Patterns (ES2024+ / Node.js 22+)

## Quick Start

- `const` by default, `let` only for reassignment, never `var`
- Optional chaining `?.` and nullish coalescing `??` over manual null guards
- ESM `import`/`export` exclusively — treat `require` as legacy
- `structuredClone()` over `JSON.parse(JSON.stringify())`
- `node:` prefix for all built-in modules: `import fs from 'node:fs'`

## Minimalism Patterns

- Use `?.` for nested property access; use `??` for defaults (not `||` — it falsely triggers on `0`, `""`, `false`)
- Destructure at point of use to reduce intermediate variables and clarify intent
- Use rest parameters `...args` over `arguments`; use spread over `Object.assign` or `concat`
- Declare private class fields with `#prefix`; never use underscore conventions to simulate privacy
- Use `using` declarations for explicit resource management — resources with `[Symbol.dispose]()` auto-cleanup on scope exit
- Use `await using` for async resources (`[Symbol.asyncDispose]()`); eliminates try/finally for streams and connections
- Use `DisposableStack` / `AsyncDisposableStack` when resource acquisition is conditional or multiple disposables need aggregation

## Efficiency Patterns

- Attach event listeners on a parent element (event delegation); use `event.target.closest()` to identify source
- Batch DOM mutations into a `DocumentFragment` before appending to the live DOM
- Use `requestAnimationFrame` for all visual/DOM updates; never modify DOM in `setTimeout` for animations
- Use `requestIdleCallback` (or `scheduler.postTask({ priority: 'background' })`) for non-urgent background work
- Use `IntersectionObserver` for lazy loading, infinite scroll, and visibility detection — never poll scroll position
- Call `observer.unobserve(el)` or `observer.disconnect()` when observation is no longer needed
- Use `AbortController` to batch-remove multiple event listeners with a single `abort()` call on cleanup
- Use `WeakMap` to associate metadata with DOM elements; entries auto-clean when elements are garbage-collected

## Code Reuse

- Use ESM `import`/`export` exclusively; use dynamic `import()` for code splitting and lazy-loading
- Build reusable UI with Web Components (Custom Elements + Shadow DOM + HTML Templates) — framework-agnostic
- Name custom elements in kebab-case with a hyphen (`my-button`) to avoid collision with native HTML tags
- Use Declarative Shadow DOM (`<template shadowrootmode="open">`) for server-rendered Web Components
- Use `:host` and CSS custom properties as the theming API for Web Components; keep internal styles encapsulated
- Use `Proxy` for cross-cutting concerns (validation, logging, access control) without modifying target objects
- Use `Reflect` methods inside Proxy traps to forward default behavior — never re-implement native semantics
- Export pure functions and compose them; prefer composition over class inheritance for business logic

## Modern JS (ES2024+ / Node.js 22+)

- `structuredClone()` — deep copy with support for `Date`, `Map`, `Set`, `ArrayBuffer`, circular refs
- `Object.groupBy()` / `Map.groupBy()` — replace reduce-based grouping patterns
- `Set` methods: `.union()`, `.intersection()`, `.difference()`, `.symmetricDifference()`, `.isSubsetOf()`
- Immutable array methods: `toSorted()`, `toReversed()`, `toSpliced()`, `with()` — no source mutation
- Iterator helpers: `.map()`, `.filter()`, `.take()`, `.drop()`, `.toArray()` directly on iterators (lazy)
- `Iterator.from(iterable)` — create iterator objects from any iterable
- `Promise.withResolvers()` — extract resolve/reject without wrapping in a constructor callback
- `Promise.try(fn)` — unify sync and async error handling into a single promise chain
- `RegExp.escape(str)` — safely interpolate user input into regular expressions
- Import attributes: `import data from './data.json' with { type: 'json' }` for type-safe module imports
- Temporal API (`Temporal.PlainDate`, `Temporal.ZonedDateTime`, `Temporal.Duration`): use `temporal-polyfill` until native support lands

## Node.js 22+ Performance Patterns

- Always use `node:` prefix: `import { readFile } from 'node:fs/promises'`
- Use `import.meta.dirname` and `import.meta.filename` instead of `__dirname`/`__filename` in ESM
- Use built-in `fetch()` for HTTP; combine with `AbortController` for timeouts and cancellation
- Use `--env-file=.env` or `process.loadEnvFile()` to load env vars; eliminates the `dotenv` dependency
- Use `--watch` for dev auto-restart instead of `nodemon`
- Use `node:test` runner for testing; eliminates Jest/Mocha for most projects
- Use Web Crypto API (`globalThis.crypto`) for cryptographic operations aligned with browser standards
- Run TypeScript directly with `node index.ts` (strip-types) for scripts and prototyping

## DOM Performance

- Batch reads then writes — never interleave reads and writes (forces layout thrashing)
- Use `IntersectionObserver` over scroll listeners; use `MutationObserver` over DOM polling
- Use `ResizeObserver` to respond to element size changes without window resize listeners
- Event delegation on parent containers scales to thousands of dynamic children at zero extra listener cost
- Virtual scrolling for long lists: render only visible items, translate with `transform: translateY`
- Prefer CSS for animation, container queries, `:has()`, and scroll-driven effects over JavaScript equivalents

## Testing

- Use `node:test` with `describe`/`it` blocks; supports nested suites and `before`/`after` hooks
- Mock with `context.mock.fn()` (spy) and `context.mock.method(obj, 'name')` for object methods
- Mock timers: `context.mock.timers.enable({ apis: ['setTimeout', 'Date'] })`; advance with `.tick(ms)`
- Coverage: `node --test --experimental-test-coverage` — no `nyc` or `c8` needed
- Watch mode: `node --test --watch` for rapid feedback
- For browser and E2E: Playwright — cross-browser, network interception, screenshot/video
- Property-based testing: fast-check for discovering edge cases in pure functions
- Vitest for projects already using Vite; Jest API-compatible with faster parallel execution

## Anti-Patterns

- Never use `var` — hoisting bugs and scope leaks that `const`/`let` prevent
- Never use `JSON.parse(JSON.stringify())` for deep cloning — use `structuredClone()`
- Never poll scroll position with `scroll` listeners — use `IntersectionObserver`
- Never import Lodash, Moment.js, jQuery, or RequireJS for new code — native ES2024+ covers core use cases
- Never use `arguments` object — use rest parameters `...args` which produce a real Array
- Never write manual null-check chains — use `?.` and `??`
- Never modify `Object.prototype` or prototypes you do not own — causes naming collisions
- Never use `eval()` — security risk and performance penalty
- Never add individual listeners to thousands of child elements — use event delegation
- Never attach closures referencing large objects to long-lived event listeners without cleanup — memory leak
