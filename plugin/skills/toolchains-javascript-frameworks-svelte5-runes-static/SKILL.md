---
name: svelte5-runes-static
description: Svelte 5 runes + SvelteKit adapter-static (SSG/SSR) patterns for hydration-safe state, store bridges, and reactivity that survives prerendering
version: 1.0.0
category: toolchain
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Hydration-safe Svelte 5 runes patterns for SvelteKit adapter-static (SSG/SSR)"
    when_to_use: "When using Svelte 5 runes with SvelteKit prerendering/adapter-static and encountering frozen state, hydration mismatches, or store bridge issues"
    quick_start: "1. Keep global state in writable()/derived() 2. Bridge store → $state in $effect() 3. Use $derived() for computations 4. Guard client-only code with browser"
context_limit: 150
tags:
  - svelte
  - svelte5
  - sveltekit
  - runes
  - adapter-static
  - ssr
  - ssg
  - hydration
  - stores
  - reactivity
  - prerendering
  - typescript
requires_tools: []
---

# Svelte 5 Runes with adapter-static (SvelteKit)

## Overview

Build static-first SvelteKit applications with Svelte 5 runes without breaking hydration. Apply these patterns when using `adapter-static` (prerendering) and combining global stores with component-local runes.

## Related Skills

- `svelte` (Svelte 5 runes core patterns)
- `sveltekit` (adapters, deployment, SSR/SSG patterns)
- `typescript-core` (TypeScript patterns and validation)
- `vitest` (unit testing patterns)

## Core Expertise

Building static-first Svelte 5 applications using runes mode with proper state management patterns that survive prerendering and hydration.

## Critical Compatibility Rules

### ❌ NEVER: Runes in Module Scope with adapter-static

**Problem**: Runes don't hydrate properly after static prerendering
```typescript
// ❌ BROKEN - State becomes frozen after SSG
export function createStore() {
  let state = $state({ count: 0 });
  return {
    get count() { return state.count; },
    increment: () => { state.count++; }
  };
}
```

**Why it fails**:
- `adapter-static` prerenders components to HTML
- Runes in module scope don't serialize/deserialize
- State becomes inert/frozen after hydration
- Reactivity completely breaks

**Solution**: Use traditional `writable()` stores for global state
```typescript
// ✅ WORKS - Traditional stores hydrate correctly
import { writable } from 'svelte/store';

export function createStore() {
  const count = writable(0);
  return {
    count,
    increment: () => count.update(n => n + 1)
  };
}
```

### ❌ NEVER: $ Auto-subscription Inside $derived

**Problem**: Runes mode disables `$` auto-subscription syntax
```typescript
// ❌ BROKEN - Can't use $ inside $derived
let filtered = $derived($events.filter(e => e.type === 'info'));
//                      ^^^^^^^ Error: $ not available in runes mode
```

**Solution**: Subscribe in `$effect()` → update `$state()` → use in `$derived()`
```typescript
// ✅ WORKS - Manual subscription pattern
import { type Writable } from 'svelte/store';

let events = $state<Event[]>([]);

$effect(() => {
  const unsub = eventsStore.subscribe(value => {
    events = value;
  });
  return unsub;
});

let filtered = $derived(events.filter(e => e.type === 'info'));
```

### ❌ NEVER: Store Factory with Getters

**Problem**: Getters don't establish reactive connections
```typescript
// ❌ BROKEN - Getter pattern breaks reactivity
export function createSocketStore() {
  const socket = writable<Socket | null>(null);
  return {
    get socket() { return socket; }, // ❌ Not reactive
    connect: () => { /* ... */ }
  };
}
```

**Solution**: Export stores directly
```typescript
// ✅ WORKS - Direct store exports
export function createSocketStore() {
  const socket = writable<Socket | null>(null);
  const isConnected = derived(socket, $s => $s?.connected ?? false);

  return {
    socket,          // ✅ Direct store reference
    isConnected,     // ✅ Direct derived reference
    connect: () => { /* ... */ }
  };
}
```

## Recommended Hybrid Pattern

### Global State: Traditional Stores

Use `writable()`/`derived()` for state that needs to survive SSG/SSR:

```typescript
// stores/globalState.ts
import { writable, derived } from 'svelte/store';

export const user = writable<User | null>(null);
export const theme = writable<'light' | 'dark'>('light');
export const isAuthenticated = derived(user, $u => $u !== null);
```

### Component State: Svelte 5 Runes

Use runes for component-local state and logic:

```typescript
<script lang="ts">
import { user } from '$lib/stores/globalState';

// Props with runes
let {
  initialCount = 0,
  onUpdate = () => {}
}: {
  initialCount?: number;
  onUpdate?: (count: number) => void;
} = $props();

// Bridge: Store → Rune State
let currentUser = $state<User | null>(null);
$effect(() => {
  const unsub = user.subscribe(u => {
    currentUser = u;
  });
  return unsub;
});

// Component-local state
let count = $state(initialCount);
let doubled = $derived(count * 2);

// Effects
$effect(() => {
  if (count > 10) {
    onUpdate(count);
  }
});

function increment() {
  count++;
}
</script>

<button onclick={increment}>
  {currentUser?.name ?? 'Guest'}: {count} (×2 = {doubled})
</button>
```

## Complete Bridge Pattern

### Store → Rune → Derived Chain

```typescript
<script lang="ts">
import { type Writable } from 'svelte/store';

// 1. Import global stores (traditional)
const { events: eventsStore, filters: filtersStore } = myGlobalStore;

// 2. Bridge to rune state
let events = $state<Event[]>([]);
let activeFilters = $state<string[]>([]);

$effect(() => {
  const unsubEvents = eventsStore.subscribe(v => { events = v; });
  const unsubFilters = filtersStore.subscribe(v => { activeFilters = v; });

  return () => {
    unsubEvents();
    unsubFilters();
  };
});

// 3. Derived computations (pure runes)
let filtered = $derived(
  events.filter(e =>
    activeFilters.length === 0 ||
    activeFilters.includes(e.category)
  )
);

let count = $derived(filtered.length);
let hasEvents = $derived(count > 0);
</script>

{#if hasEvents}
  <p>Found {count} events</p>
  {#each filtered as event}
    <EventCard {event} />
  {/each}
{:else}
  <p>No events match filters</p>
{/if}
```

## SSG/SSR Considerations

### Prerender-Safe Patterns

```typescript
// ✅ Safe for prerendering
export const load = async ({ fetch }) => {
  const data = await fetch('/api/data').then(r => r.json());
  return { data };
};
```

```svelte
<script lang="ts">
import { browser } from '$app/environment';

let { data } = $props();

// ✅ Client-only initialization
$effect(() => {
  if (browser) {
    // WebSocket, localStorage, etc.
    initializeClientOnlyFeatures();
  }
});
</script>
```

### Hydration Mismatch Prevention

```typescript
// ✅ Avoid hydration mismatches
let timestamp = $state<number | null>(null);

$effect(() => {
  if (browser) {
    timestamp = Date.now(); // Only set on client
  }
});
```

```svelte
<!-- ✅ Conditional rendering for client-only content -->
{#if browser}
  <LiveClock />
{:else}
  <p>Loading clock...</p>
{/if}
```

## TypeScript Integration

### Typed Props with Runes

```typescript
<script lang="ts">
import type { Snippet } from 'svelte';

interface Props {
  title: string;
  count?: number;
  items: Array<{ id: string; name: string }>;
  onSelect?: (id: string) => void;
  children?: Snippet;
}

let {
  title,
  count = 0,
  items,
  onSelect = () => {},
  children
}: Props = $props();

let selected = $state<string | null>(null);
let filteredItems = $derived(
  items.filter(item =>
    selected === null || item.id === selected
  )
);
</script>

<h2>{title} ({count})</h2>

{#each filteredItems as item}
  <button onclick={() => onSelect(item.id)}>
    {item.name}
  </button>
{/each}

{@render children?.()}
```

### Typed Store Bridges

```typescript
<script lang="ts">
import type { Writable, Readable } from 'svelte/store';

interface StoreShape {
  data: Writable<string[]>;
  status: Readable<'loading' | 'ready' | 'error'>;
}

const stores: StoreShape = getMyStores();

let data = $state<string[]>([]);
let status = $state<'loading' | 'ready' | 'error'>('loading');

$effect(() => {
  const unsubData = stores.data.subscribe(v => { data = v; });
  const unsubStatus = stores.status.subscribe(v => { status = v; });
  return () => {
    unsubData();
    unsubStatus();
  };
});

let isEmpty = $derived(data.length === 0);
let isReady = $derived(status === 'ready');
</script>
```

## Common Patterns

### Bindable Component State

```typescript
<script lang="ts">
let {
  value = $bindable(''),
  disabled = false
}: {
  value?: string;
  disabled?: boolean;
} = $props();

let focused = $state(false);
let charCount = $derived(value.length);
let isValid = $derived(charCount >= 3 && charCount <= 100);
</script>

<input
  bind:value
  {disabled}
  onfocus={() => { focused = true; }}
  onblur={() => { focused = false; }}
  class:focused
  class:invalid={!isValid}
/>
<p>{charCount}/100</p>
```

### Form State Management

```typescript
<script lang="ts">
interface FormData {
  email: string;
  password: string;
}

let formData = $state<FormData>({
  email: '',
  password: ''
});

let errors = $state<Partial<Record<keyof FormData, string>>>({});

let isValid = $derived(
  formData.email.includes('@') &&
  formData.password.length >= 8
);

let canSubmit = $derived(
  isValid && Object.keys(errors).length === 0
);

function validate(field: keyof FormData) {
  if (field === 'email' && !formData.email.includes('@')) {
    errors.email = 'Invalid email';
  } else if (field === 'password' && formData.password.length < 8) {
    errors.password = 'Password too short';
  } else {
    delete errors[field];
  }
}

async function handleSubmit() {
  if (!canSubmit) return;

  // Submit logic
  const result = await submitForm(formData);

  if (result.ok) {
    // Success
  } else {
    errors = result.errors;
  }
}
</script>

<form onsubmit={handleSubmit}>
  <input
    type="email"
    bind:value={formData.email}
    onblur={() => validate('email')}
  />
  {#if errors.email}
    <span class="error">{errors.email}</span>
  {/if}

  <input
    type="password"
    bind:value={formData.password}
    onblur={() => validate('password')}
  />
  {#if errors.password}
    <span class="error">{errors.password}</span>
  {/if}

  <button type="submit" disabled={!canSubmit}>
    Submit
  </button>
</form>
```

### Debounced Search

```typescript
<script lang="ts">
import { writable, derived } from 'svelte/store';

const searchQuery = writable('');

// Traditional derived store with debounce
const debouncedQuery = derived(
  searchQuery,
  ($query, set) => {
    const timeout = setTimeout(() => set($query), 300);
    return () => clearTimeout(timeout);
  },
  '' // initial value
);

// Bridge to rune state
let query = $state('');
let debouncedValue = $state('');

$effect(() => {
  searchQuery.set(query);
});

$effect(() => {
  const unsub = debouncedQuery.subscribe(v => {
    debouncedValue = v;
  });
  return unsub;
});

// Use in derived
let results = $derived(
  debouncedValue.length >= 3
    ? performSearch(debouncedValue)
    : []
);
</script>

<input
  type="search"
  bind:value={query}
  placeholder="Search..."
/>

{#each results as result}
  <SearchResult {result} />
{/each}
```

## Migration Checklist

When migrating from Svelte 4 to Svelte 5 with adapter-static:

- [ ] Replace component-level `$:` with `$derived()`
- [ ] Replace `export let prop` with `let { prop } = $props()`
- [ ] Keep global stores as `writable()`/`derived()`
- [ ] Add bridge pattern for store → rune state
- [ ] Replace `$store` syntax with manual subscription in `$effect()`
- [ ] Test prerendering with `npm run build`
- [ ] Verify hydration works correctly
- [ ] Check for hydration mismatches in console
- [ ] Ensure client-only code is guarded with `browser` check

## Testing Patterns

### Unit Testing Runes

```typescript
import { mount } from 'svelte';
import { tick } from 'svelte';
import { describe, it, expect } from 'vitest';
import Counter from './Counter.svelte';

describe('Counter', () => {
  it('increments count', async () => {
    const { component } = mount(Counter, {
      target: document.body,
      props: { initialCount: 0 }
    });

    const button = document.querySelector('button');
    button?.click();

    await tick();

    expect(button?.textContent).toContain('1');
  });
});
```

### Testing Store Bridges

```typescript
import { get } from 'svelte/store';
import { tick } from 'svelte';
import { describe, it, expect } from 'vitest';
import { createMyStore } from './myStore';

describe('Store Bridge', () => {
  it('syncs store to rune state', async () => {
    const store = createMyStore();

    store.data.set(['item1', 'item2']);

    await tick();

    expect(get(store.data)).toEqual(['item1', 'item2']);
  });
});
```

## Performance Considerations

### Avoid Unnecessary Reactivity

```typescript
// ❌ Over-reactive
let items = $state([1, 2, 3, 4, 5]);
let doubled = $derived(items.map(x => x * 2));
let tripled = $derived(items.map(x => x * 3));
let quadrupled = $derived(items.map(x => x * 4));

// ✅ Compute only what's needed
let items = $state([1, 2, 3, 4, 5]);
let transformedItems = $derived(
  mode === 'double' ? items.map(x => x * 2) :
  mode === 'triple' ? items.map(x => x * 3) :
  items.map(x => x * 4)
);
```

### Memoize Expensive Computations

```typescript
// Traditional derived store for expensive computations
const expensiveComputation = derived(
  [source1, source2],
  ([$s1, $s2]) => {
    // Expensive calculation
    return complexAlgorithm($s1, $s2);
  }
);

// Bridge to rune
let result = $state(null);
$effect(() => {
  const unsub = expensiveComputation.subscribe(v => { result = v; });
  return unsub;
});
```

## Troubleshooting

### Symptom: State doesn't update after hydration

**Cause**: Runes in module scope with adapter-static

**Fix**: Use traditional `writable()` stores for global state

### Symptom: "$ is not defined" error in $derived

**Cause**: Trying to use `$store` syntax in runes mode

**Fix**: Use bridge pattern with `$effect()` subscription

### Symptom: "Cannot read property of undefined" after SSG

**Cause**: Store factory with getters instead of direct exports

**Fix**: Export stores directly, not wrapped in getters

### Symptom: Hydration mismatch warnings

**Cause**: Client-only state rendered during SSR

**Fix**: Guard with `browser` check or use `{#if browser}`

## Decision Framework

**Use Traditional Stores When:**
- State needs to survive SSG/SSR prerendering
- State is global/shared across components
- State needs to be serialized/deserialized
- Working with adapter-static

**Use Runes When:**
- State is component-local
- Building reactive UI logic
- Working with props and component lifecycle
- Creating derived computations from local state

**Use Bridge Pattern When:**
- Need to combine global stores with component runes
- Want derived computations from store values
- Building complex reactive chains

## Related Skills

- **toolchains-javascript-frameworks-svelte**: Base Svelte patterns
- **toolchains-typescript-core**: TypeScript integration
- **toolchains-ui-styling-tailwind**: Styling Svelte components
- **toolchains-javascript-testing-vitest**: Testing Svelte 5

## References

- [Svelte 5 Runes Documentation](https://svelte.dev/docs/svelte/what-are-runes)
- [SvelteKit adapter-static](https://kit.svelte.dev/docs/adapter-static)
- [Svelte Stores](https://svelte.dev/docs/svelte-store)
