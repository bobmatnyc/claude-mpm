---
name: svelte
description: Svelte 5 - Reactive UI framework with compiler magic, Runes API, SvelteKit full-stack framework, SSR/SSG, minimal JavaScript
version: 1.0.0
category: toolchain
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Compiler-first reactive UI: $state/$derived/$effect Runes, SvelteKit SSR/SSG, minimal bundle, write less code"
    when_to_use: "Interactive UIs, dashboards, SPAs, static sites, full-stack apps with performance focus and developer ergonomics"
    quick_start: "1. npm create svelte@latest 2. Use $state() for reactive state 3. Use $derived() for computed 4. Deploy with adapters"
context_limit: 85
tags:
  - svelte
  - svelte5
  - sveltekit
  - runes
  - reactivity
  - ssr
  - ssg
  - compiler
  - performance
  - frontend
requires_tools: []
---

# Svelte 5 - Compiler-First Reactive Framework

## Overview

Svelte is a **compiler-based** reactive UI framework that shifts work from runtime to build time. Unlike React/Vue, Svelte compiles components to highly optimized vanilla JavaScript with minimal overhead. **Svelte 5** introduces Runes API for explicit, fine-grained reactivity.

**Key Features**:
- **Runes API**: $state, $derived, $effect for explicit reactivity
- **Zero runtime overhead**: Compiles to vanilla JS
- **Built-in state management**: No external libraries needed
- **SvelteKit**: Full-stack framework with SSR/SSG/SPA
- **Write less code**: Simple, readable component syntax
- **Exceptional performance**: Small bundles, fast runtime

**Installation**:
```bash
# Create new SvelteKit project
npm create svelte@latest my-app
cd my-app
npm install
npm run dev

# Or Svelte only (no SvelteKit)
npm create vite@latest my-app -- --template svelte-ts
```

## Svelte 5 Runes API (Modern Approach)

### State Management with $state

```svelte
<script lang="ts">
  // Reactive state - automatically tracks changes
  let count = $state(0);
  let user = $state({ name: 'Alice', age: 30 });

  // Arrays and objects are deeply reactive
  let todos = $state<Todo[]>([]);

  function addTodo(text: string) {
    todos.push({ id: Date.now(), text, done: false });
    // No need for todos = [...todos] like React!
  }

  function increment() {
    count++; // Triggers reactivity
  }
</script>

<button onclick={increment}>
  Clicked {count} times
</button>
```

### Computed Values with $derived

```svelte
<script lang="ts">
  let firstName = $state('John');
  let lastName = $state('Doe');

  // Automatically updates when dependencies change
  let fullName = $derived(`${firstName} ${lastName}`);
  let greeting = $derived(`Hello, ${fullName}!`);

  // Complex derivations
  let items = $state([1, 2, 3, 4, 5]);
  let total = $derived(items.reduce((sum, n) => sum + n, 0));
  let average = $derived(total / items.length);
</script>

<p>{greeting}</p>
<p>Average: {average.toFixed(2)}</p>
```

### Side Effects with $effect

```svelte
<script lang="ts">
  let count = $state(0);
  let logs = $state<string[]>([]);

  // Runs when dependencies change
  $effect(() => {
    console.log(`Count is now: ${count}`);
    logs.push(`Count changed to ${count}`);

    // Optional cleanup function
    return () => {
      console.log('Cleaning up previous effect');
    };
  });

  // Effect with external subscriptions
  $effect(() => {
    const interval = setInterval(() => {
      count++;
    }, 1000);

    return () => clearInterval(interval);
  });
</script>
```

### Component Props with $props

```svelte
<script lang="ts">
  interface Props {
    title: string;
    count?: number;
    onUpdate?: (value: number) => void;
  }

  // Type-safe props with defaults
  let { title, count = 0, onUpdate } = $props<Props>();

  // Props are read-only, but can derive from them
  let displayTitle = $derived(title.toUpperCase());
</script>

<h1>{displayTitle}</h1>
<p>Count: {count}</p>
<button onclick={() => onUpdate?.(count + 1)}>
  Increment
</button>
```

### Two-Way Binding with $bindable

```svelte
<!-- Child: SearchInput.svelte -->
<script lang="ts">
  interface Props {
    value: string;
    placeholder?: string;
  }

  // Allows parent to bind to this prop
  let { value = $bindable(''), placeholder = 'Search...' } = $props<Props>();
</script>

<input bind:value {placeholder} type="search" />

<!-- Parent.svelte -->
<script lang="ts">
  import SearchInput from './SearchInput.svelte';

  let query = $state('');
  let results = $derived(query ? search(query) : []);
</script>

<SearchInput bind:value={query} />
<p>Found {results.length} results for "{query}"</p>
```

## Component Patterns

### Basic Component Structure

```svelte
<!-- Counter.svelte -->
<script lang="ts">
  let count = $state(0);
  let doubled = $derived(count * 2);

  function increment() {
    count++;
  }

  function decrement() {
    count--;
  }
</script>

<div class="counter">
  <button onclick={decrement}>-</button>
  <span>Count: {count} (Doubled: {doubled})</span>
  <button onclick={increment}>+</button>
</div>

<style>
  .counter {
    display: flex;
    gap: 1rem;
    align-items: center;
  }

  button {
    padding: 0.5rem 1rem;
    font-size: 1.2rem;
  }
</style>
```

### Conditional Rendering

```svelte
<script lang="ts">
  let loggedIn = $state(false);
  let user = $state<User | null>(null);
  let loading = $state(true);
</script>

{#if loading}
  <p>Loading...</p>
{:else if loggedIn && user}
  <p>Welcome, {user.name}!</p>
{:else}
  <p>Please log in</p>
{/if}
```

### Lists and Keyed Each Blocks

```svelte
<script lang="ts">
  interface Todo {
    id: number;
    text: string;
    done: boolean;
  }

  let todos = $state<Todo[]>([
    { id: 1, text: 'Learn Svelte', done: true },
    { id: 2, text: 'Build app', done: false }
  ]);

  function toggle(id: number) {
    const todo = todos.find(t => t.id === id);
    if (todo) todo.done = !todo.done;
  }
</script>

<ul>
  {#each todos as todo (todo.id)}
    <li class:done={todo.done}>
      <input
        type="checkbox"
        checked={todo.done}
        onchange={() => toggle(todo.id)}
      />
      {todo.text}
    </li>
  {/each}
</ul>

<style>
  .done {
    text-decoration: line-through;
    opacity: 0.6;
  }
</style>
```

## SvelteKit Framework

### Project Structure

```
my-app/
├── src/
│   ├── routes/
│   │   ├── +page.svelte          # Home page
│   │   ├── +page.ts              # Universal load
│   │   ├── +page.server.ts       # Server load
│   │   ├── +layout.svelte        # Shared layout
│   │   ├── about/
│   │   │   └── +page.svelte      # /about
│   │   └── blog/
│   │       ├── +page.svelte      # /blog
│   │       └── [slug]/
│   │           └── +page.svelte  # /blog/my-post
│   ├── lib/
│   │   ├── components/
│   │   ├── stores/
│   │   └── utils/
│   └── app.html
├── static/                        # Static assets
└── svelte.config.js
```

### Load Functions (Data Fetching)

```typescript
// src/routes/blog/[slug]/+page.ts
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
  const response = await fetch(`/api/posts/${params.slug}`);
  const post = await response.json();

  return {
    post
  };
};
```

```svelte
<!-- src/routes/blog/[slug]/+page.svelte -->
<script lang="ts">
  import type { PageData } from './$types';

  let { data } = $props<{ data: PageData }>();
</script>

<article>
  <h1>{data.post.title}</h1>
  <div>{@html data.post.content}</div>
</article>
```

### Server-Only Load Functions

```typescript
// src/routes/admin/+page.server.ts
import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
  if (!locals.user?.isAdmin) {
    throw redirect(303, '/login');
  }

  const users = await db.users.findMany();

  return {
    users
  };
};
```

### Form Actions

```typescript
// src/routes/login/+page.server.ts
import { fail, redirect } from '@sveltejs/kit';
import type { Actions } from './$types';
import { z } from 'zod';

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8)
});

export const actions = {
  default: async ({ request, cookies }) => {
    const formData = await request.formData();
    const data = Object.fromEntries(formData);

    const result = schema.safeParse(data);
    if (!result.success) {
      return fail(400, {
        errors: result.error.flatten().fieldErrors
      });
    }

    const user = await authenticateUser(result.data);
    if (!user) {
      return fail(401, { message: 'Invalid credentials' });
    }

    cookies.set('session', user.sessionToken, { path: '/' });
    throw redirect(303, '/dashboard');
  }
} satisfies Actions;
```

```svelte
<!-- src/routes/login/+page.svelte -->
<script lang="ts">
  import type { ActionData } from './$types';

  let { form } = $props<{ form?: ActionData }>();
</script>

<form method="POST">
  <input name="email" type="email" required />
  {#if form?.errors?.email}
    <span class="error">{form.errors.email[0]}</span>
  {/if}

  <input name="password" type="password" required />
  {#if form?.errors?.password}
    <span class="error">{form.errors.password[0]}</span>
  {/if}

  {#if form?.message}
    <p class="error">{form.message}</p>
  {/if}

  <button type="submit">Log In</button>
</form>
```

## State Management Patterns

### Runes-Based Store (Modern)

```typescript
// src/lib/stores/cart.svelte.ts
interface CartItem {
  id: number;
  name: string;
  price: number;
  quantity: number;
}

function createCart() {
  let items = $state<CartItem[]>([]);

  let total = $derived(
    items.reduce((sum, item) => sum + item.price * item.quantity, 0)
  );

  let itemCount = $derived(
    items.reduce((sum, item) => sum + item.quantity, 0)
  );

  return {
    get items() { return items; },
    get total() { return total; },
    get itemCount() { return itemCount; },

    addItem(item: Omit<CartItem, 'quantity'>) {
      const existing = items.find(i => i.id === item.id);
      if (existing) {
        existing.quantity++;
      } else {
        items.push({ ...item, quantity: 1 });
      }
    },

    removeItem(id: number) {
      items = items.filter(i => i.id !== id);
    },

    clear() {
      items = [];
    }
  };
}

export const cart = createCart();
```

```svelte
<!-- Usage -->
<script lang="ts">
  import { cart } from '$lib/stores/cart.svelte';
</script>

<div>
  <p>Items: {cart.itemCount}</p>
  <p>Total: ${cart.total.toFixed(2)}</p>

  <button onclick={() => cart.addItem({ id: 1, name: 'Widget', price: 9.99 })}>
    Add Widget
  </button>
</div>
```

### Legacy Svelte Store (Svelte 4 Style)

```typescript
// src/lib/stores/user.ts
import { writable, derived } from 'svelte/store';

interface User {
  id: number;
  name: string;
  email: string;
}

function createUserStore() {
  const { subscribe, set, update } = writable<User | null>(null);

  return {
    subscribe,
    login: (user: User) => set(user),
    logout: () => set(null),
    updateName: (name: string) => update(u => u ? { ...u, name } : null)
  };
}

export const user = createUserStore();

// Derived store
export const isLoggedIn = derived(user, $user => $user !== null);
```

```svelte
<!-- Usage with $ prefix -->
<script lang="ts">
  import { user, isLoggedIn } from '$lib/stores/user';
</script>

{#if $isLoggedIn}
  <p>Welcome, {$user?.name}!</p>
{:else}
  <p>Please log in</p>
{/if}
```

## Animations and Transitions

### Built-in Transitions

```svelte
<script lang="ts">
  import { fade, slide, fly, scale } from 'svelte/transition';
  import { quintOut } from 'svelte/easing';

  let visible = $state(true);
</script>

<button onclick={() => visible = !visible}>
  Toggle
</button>

{#if visible}
  <div transition:fade={{ duration: 300 }}>
    Fades in and out
  </div>

  <div transition:slide={{ duration: 300 }}>
    Slides in and out
  </div>

  <div transition:fly={{ y: 200, duration: 500, easing: quintOut }}>
    Flies in from bottom
  </div>
{/if}
```

### Custom Transitions

```typescript
// src/lib/transitions.ts
export function blur(node: HTMLElement, { duration = 300 }) {
  return {
    duration,
    css: (t: number) => `
      opacity: ${t};
      filter: blur(${(1 - t) * 10}px);
    `
  };
}
```

```svelte
<script lang="ts">
  import { blur } from '$lib/transitions';
  let show = $state(true);
</script>

{#if show}
  <div transition:blur={{ duration: 500 }}>
    Custom blur transition
  </div>
{/if}
```

### Animate Directive (FLIP Animations)

```svelte
<script lang="ts">
  import { flip } from 'svelte/animate';
  import { quintOut } from 'svelte/easing';

  let items = $state([1, 2, 3, 4, 5]);

  function shuffle() {
    items = items.sort(() => Math.random() - 0.5);
  }
</script>

<button onclick={shuffle}>Shuffle</button>

<ul>
  {#each items as item (item)}
    <li animate:flip={{ duration: 500, easing: quintOut }}>
      {item}
    </li>
  {/each}
</ul>
```

## Advanced Features

### Actions (Element Behaviors)

```typescript
// src/lib/actions.ts
export function clickOutside(node: HTMLElement, callback: () => void) {
  const handleClick = (event: MouseEvent) => {
    if (!node.contains(event.target as Node)) {
      callback();
    }
  };

  document.addEventListener('click', handleClick, true);

  return {
    destroy() {
      document.removeEventListener('click', handleClick, true);
    }
  };
}
```

```svelte
<script lang="ts">
  import { clickOutside } from '$lib/actions';

  let showMenu = $state(false);
</script>

<button onclick={() => showMenu = !showMenu}>
  Menu
</button>

{#if showMenu}
  <div
    class="menu"
    use:clickOutside={() => showMenu = false}
  >
    <ul>
      <li>Item 1</li>
      <li>Item 2</li>
    </ul>
  </div>
{/if}
```

### Slots and Component Composition

```svelte
<!-- Card.svelte -->
<script lang="ts">
  let { title } = $props<{ title?: string }>();
</script>

<div class="card">
  <header>
    {#if title}
      <h2>{title}</h2>
    {:else}
      <slot name="header">Default Header</slot>
    {/if}
  </header>

  <main>
    <slot>Default content</slot>
  </main>

  <footer>
    <slot name="footer" />
  </footer>
</div>

<!-- Usage -->
<Card title="My Card">
  <p>This is the main content</p>

  <div slot="footer">
    <button>Action</button>
  </div>
</Card>
```

### Special Elements

```svelte
<script lang="ts">
  let Component = $state<typeof import('./A.svelte').default | typeof import('./B.svelte').default>(A);
  let tag = $state<'div' | 'span'>('div');
</script>

<!-- Dynamic component -->
<svelte:component this={Component} />

<!-- Dynamic HTML element -->
<svelte:element this={tag}>
  Content
</svelte:element>

<!-- Window events -->
<svelte:window
  onresize={() => console.log('Window resized')}
  onkeydown={(e) => console.log(e.key)}
/>

<!-- Document head -->
<svelte:head>
  <title>My Page</title>
  <meta name="description" content="Description" />
</svelte:head>
```

## Migration from React/Vue

### React to Svelte 5

| React | Svelte 5 | Notes |
|-------|----------|-------|
| `useState(0)` | `$state(0)` | Direct state |
| `useMemo(() => x * 2, [x])` | `$derived(x * 2)` | Auto-tracked |
| `useEffect(() => {...}, [x])` | `$effect(() => {...})` | Auto deps |
| `props.name` | `let { name } = $props()` | Destructure |
| `{show && <div />}` | `{#if show}<div />{/if}` | Explicit |

### Vue 3 to Svelte 5

| Vue 3 | Svelte 5 | Notes |
|-------|----------|-------|
| `ref(0)` | `$state(0)` | Direct state |
| `computed(() => x * 2)` | `$derived(x * 2)` | Similar |
| `watch(() => x, ...)` | `$effect(() => {...})` | Auto-tracked |
| `defineProps<{ name: string }>()` | `let { name } = $props<Props>()` | Type-safe |
| `v-if="show"` | `{#if show}` | Block syntax |

## Performance Best Practices

1. **Use $derived over $effect** when only computed values are needed
2. **Avoid unnecessary $effect** - only for side effects, not computations
3. **Leverage compiler optimizations** - Svelte does most work at build time
4. **Use keyed each blocks** - `{#each items as item (item.id)}`
5. **Lazy load components** - `const Component = await import('./Heavy.svelte')`
6. **SSR for initial load** - Use SvelteKit's SSR capabilities
7. **Optimize bundles** - Use adapters for deployment targets

## Testing

### Unit Tests with Vitest

```typescript
// Counter.test.ts
import { render, fireEvent } from '@testing-library/svelte';
import { expect, test } from 'vitest';
import Counter from './Counter.svelte';

test('increments counter on click', async () => {
  const { getByText } = render(Counter);

  const button = getByText('+');
  await fireEvent.click(button);

  expect(getByText(/Count: 1/)).toBeInTheDocument();
});
```

### E2E with Playwright

```typescript
// tests/login.test.ts
import { expect, test } from '@playwright/test';

test('user can log in', async ({ page }) => {
  await page.goto('/login');

  await page.fill('input[name="email"]', 'user@example.com');
  await page.fill('input[name="password"]', 'password123');
  await page.click('button[type="submit"]');

  await expect(page).toHaveURL('/dashboard');
  await expect(page.locator('text=Welcome')).toBeVisible();
});
```

## Deployment

### Adapters

```javascript
// svelte.config.js
import adapter from '@sveltejs/adapter-vercel'; // or adapter-node, adapter-static

export default {
  kit: {
    adapter: adapter()
  }
};
```

**Available Adapters**:
- `adapter-auto`: Auto-detect platform
- `adapter-vercel`: Vercel deployment
- `adapter-node`: Node.js server
- `adapter-static`: Static site generation
- `adapter-cloudflare`: Cloudflare Pages/Workers
- `adapter-netlify`: Netlify deployment

## Resources

- **Svelte Docs**: https://svelte.dev/docs
- **SvelteKit Docs**: https://kit.svelte.dev/docs
- **Svelte 5 Runes**: https://svelte-5-preview.vercel.app/docs/runes
- **Tutorial**: https://learn.svelte.dev
- **REPL**: https://svelte.dev/repl

## Summary

- **Svelte 5** uses Runes API ($state, $derived, $effect) for explicit reactivity
- **Compiler-first** - shifts work to build time for minimal runtime overhead
- **SvelteKit** provides full-stack capabilities with SSR/SSG/SPA modes
- **Write less code** - simpler syntax than React/Vue
- **Exceptional performance** - small bundles, fast runtime
- **Migration-friendly** - Svelte 4 and 5 can coexist
- **Type-safe** - First-class TypeScript support
