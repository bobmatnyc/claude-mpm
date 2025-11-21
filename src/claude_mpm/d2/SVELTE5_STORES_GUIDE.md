# Svelte 5 Store Architecture Guide

## Quick Decision Tree

```
Do you need reactive state?
│
├─ YES → Is it used inside a component <script> block?
│        │
│        ├─ YES → Use Svelte 5 Runes ✅
│        │        let count = $state(0)
│        │        let doubled = $derived(count * 2)
│        │
│        └─ NO → Is it at module level / shared between components?
│                 │
│                 └─ YES → Use Traditional Stores ✅
│                          const count = writable(0)
│                          const doubled = derived(count, $count => $count * 2)
│
└─ NO → Use regular JavaScript variables
```

## Pattern 1: Component-Local State (Use Runes)

```svelte
<!-- Component.svelte -->
<script>
  // ✅ CORRECT - Runes in component context
  let count = $state(0);
  let doubled = $derived(count * 2);

  $effect(() => {
    console.log(`Count is now ${count}`);
  });
</script>

<button onclick={() => count++}>
  {count} / {doubled}
</button>
```

## Pattern 2: Module-Level Stores (Use Traditional Stores)

```javascript
// stores/counter.js
import { writable, derived } from 'svelte/store';

// ✅ CORRECT - Traditional stores for module-level state
function createCounterStore() {
  const count = writable(0);
  const doubled = derived(count, $count => $count * 2);

  return {
    count: { subscribe: count.subscribe },
    doubled: { subscribe: doubled.subscribe },
    increment: () => count.update(n => n + 1),
    reset: () => count.set(0)
  };
}

export const counterStore = createCounterStore();
```

```svelte
<!-- Component.svelte -->
<script>
  import { counterStore } from './stores/counter.js';

  // Use $ auto-subscription
</script>

<button onclick={() => counterStore.increment()}>
  {$counterStore.count} / {$counterStore.doubled}
</button>
```

## Pattern 3: Props (Use $props)

```svelte
<!-- Child.svelte -->
<script>
  // ✅ CORRECT - $props for component props
  let { value, onUpdate } = $props();
</script>

<input bind:value oninput={() => onUpdate(value)} />
```

## Common Mistakes

### ❌ WRONG: Runes at Module Level

```javascript
// stores/counter.svelte.js
// ❌ This will cause effect_orphan error!
function createCounterStore() {
  let count = $state(0);  // ❌ Rune outside component
  // ...
}

export const counterStore = createCounterStore(); // ❌ Called at module load
```

### ❌ WRONG: Traditional Stores in Components

```svelte
<script>
  import { writable } from 'svelte/store';

  // ❌ Unnecessary complexity for component-local state
  const count = writable(0);
</script>

<button onclick={() => count.update(n => n + 1)}>
  {$count}
</button>
```

### ✅ CORRECT: Runes in Components

```svelte
<script>
  // ✅ Simple and idiomatic
  let count = $state(0);
</script>

<button onclick={() => count++}>
  {count}
</button>
```

## Migration Checklist

When converting Svelte 4 → Svelte 5:

### Component-Local State
- [ ] `export let prop` → `let { prop } = $props()`
- [ ] `$: derived = compute(x)` → `let derived = $derived(compute(x))`
- [ ] `$: { effect() }` → `$effect(() => { effect() })`

### Module-Level Stores
- [ ] Keep using `writable`, `derived`, `readable`
- [ ] Update components to use `$` auto-subscription
- [ ] Add `.subscribe` exposure in store API

### File Naming
- [ ] Component stores using runes: `Component.svelte` (not `.svelte.js`)
- [ ] Module stores: `store.js` (not `.svelte.js`)

## Debugging Tips

### Error: `effect_orphan`
**Cause**: Runes used outside component context
**Fix**: Use traditional stores for module-level state

### Error: Cannot access `$store` before initialization
**Cause**: Missing `$` prefix on store subscription
**Fix**: Use `$storeName.property` in templates

### Store not updating UI
**Cause**: Forgetting to use `.set()` or `.update()`
**Fix**: Always mutate stores with `.set()` / `.update()`, never directly

## Performance Comparison

| Pattern | Bundle Impact | Reactivity | Use Case |
|---------|---------------|------------|----------|
| Runes | Minimal | Fine-grained | Component-local |
| Traditional Stores | Small | Observable | Shared state |
| Context API | None | Manual | Dependency injection |

## Further Reading

- Svelte 5 Runes: https://svelte.dev/docs/svelte/$state
- Svelte Stores: https://svelte.dev/docs/svelte-store
- Migration Guide: https://svelte-5-preview.vercel.app/docs/v5-migration-guide

---

**Remember**: Runes are for components, stores are for modules.
