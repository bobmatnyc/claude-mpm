---
name: sveltekit
description: SvelteKit - Full-stack Svelte framework with file-based routing, SSR/SSG, form actions, and adapters for deployment
version: 1.0.0
category: toolchain
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Full-stack Svelte framework: file-based routing, SSR/SSG/SPA, form actions, type-safe load functions, universal adapters"
    when_to_use: "Building full-stack web apps, SPAs with SSR, forms with progressive enhancement, API routes, SEO-critical sites"
    quick_start: "1. npm create svelte@latest 2. Define routes in src/routes/ 3. Use +page.svelte for pages 4. Deploy with adapters"
  token_estimate:
    entry: 80
    full: 5000
tags:
  - sveltekit
  - svelte
  - ssr
  - ssg
  - routing
  - forms
  - fullstack
  - framework
  - adapters
  - typescript
requires_tools: []
---

# SvelteKit - Full-Stack Svelte Framework

## Overview

SvelteKit is the official **full-stack framework** for Svelte, providing file-based routing, server-side rendering (SSR), static site generation (SSG), form handling with progressive enhancement, and deployment adapters for any platform.

**Key Features**:
- **File-based routing**: Automatic routes from `src/routes/` directory structure
- **Load functions**: Type-safe data fetching (`+page.ts`, `+page.server.ts`)
- **Form actions**: Native form handling with progressive enhancement
- **SSR/SSG/SPA**: Flexible rendering modes with per-route control
- **Adapters**: Deploy to Vercel, Netlify, Node.js, Cloudflare, and more
- **TypeScript-first**: Generated types from `$types` for type safety
- **Hooks**: Middleware-like `handle`, `handleError`, `handleFetch`
- **API routes**: `+server.ts` files for REST endpoints

**Installation**:
```bash
# Create new SvelteKit project
npm create svelte@latest my-app
cd my-app
npm install
npm run dev -- --open

# Templates: skeleton, demo app, library
# Choices: TypeScript, ESLint, Prettier, Playwright, Vitest
```

## Project Structure

### Standard SvelteKit Layout

```
my-sveltekit-app/
├── src/
│   ├── routes/                   # File-based routing
│   │   ├── +page.svelte         # / (home page)
│   │   ├── +page.ts             # Universal load function
│   │   ├── +page.server.ts      # Server-only load function
│   │   ├── +layout.svelte       # Shared layout
│   │   ├── +layout.ts           # Layout load function
│   │   ├── +error.svelte        # Error page
│   │   ├── about/
│   │   │   └── +page.svelte     # /about
│   │   ├── blog/
│   │   │   ├── +page.svelte     # /blog (list)
│   │   │   ├── +page.server.ts  # Load posts
│   │   │   └── [slug]/
│   │   │       ├── +page.svelte # /blog/my-post
│   │   │       └── +page.server.ts
│   │   └── api/
│   │       └── posts/
│   │           └── +server.ts   # GET /api/posts
│   ├── lib/
│   │   ├── components/
│   │   ├── server/              # Server-only utilities
│   │   │   └── database.ts
│   │   ├── stores/
│   │   └── utils/
│   ├── hooks.server.ts          # Server hooks
│   ├── hooks.client.ts          # Client hooks
│   ├── app.html                 # HTML template
│   └── app.d.ts                 # TypeScript declarations
├── static/                       # Static assets (robots.txt, favicon)
├── tests/                        # Playwright tests
├── svelte.config.js             # SvelteKit configuration
├── vite.config.ts               # Vite configuration
└── package.json
```

## File-Based Routing

### Route Conventions

**File naming determines routing**:

| File | Route | Purpose |
|------|-------|---------|
| `+page.svelte` | `/` | Page component |
| `+page.ts` | - | Universal load (client + server) |
| `+page.server.ts` | - | Server-only load |
| `+layout.svelte` | - | Shared layout |
| `+layout.ts` | - | Layout load |
| `+layout.server.ts` | - | Server layout load |
| `+server.ts` | `/api/...` | API endpoint (GET/POST/etc) |
| `+error.svelte` | - | Error boundary |

### Basic Routes

```
src/routes/
├── +page.svelte              # / (home)
├── about/
│   └── +page.svelte          # /about
├── contact/
│   └── +page.svelte          # /contact
└── pricing/
    └── +page.svelte          # /pricing
```

### Dynamic Routes

```
src/routes/
└── blog/
    ├── +page.svelte          # /blog (list)
    ├── [slug]/
    │   └── +page.svelte      # /blog/my-post
    └── [category]/
        └── [slug]/
            └── +page.svelte  # /blog/tech/my-post
```

**Access route params**:
```svelte
<!-- src/routes/blog/[slug]/+page.svelte -->
<script lang="ts">
  import type { PageData } from './$types';

  let { data } = $props<{ data: PageData }>();
</script>

<article>
  <h1>{data.post.title}</h1>
  <p>{data.post.content}</p>
</article>
```

### Optional Parameters

```
src/routes/
└── archive/
    └── [[year]]/
        └── [[month]]/
            └── +page.svelte  # /archive, /archive/2024, /archive/2024/11
```

```typescript
// src/routes/archive/[[year]]/[[month]]/+page.ts
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
  const year = params.year || new Date().getFullYear();
  const month = params.month || null;

  return {
    year,
    month,
    posts: await fetchPosts({ year, month })
  };
};
```

### Rest Parameters

```
src/routes/
└── docs/
    └── [...path]/
        └── +page.svelte      # /docs/guide/intro, /docs/api/reference
```

```typescript
// src/routes/docs/[...path]/+page.ts
export const load: PageLoad = async ({ params }) => {
  const path = params.path; // "guide/intro"
  const segments = path.split('/'); // ["guide", "intro"]

  return {
    doc: await fetchDoc(path)
  };
};
```

## Load Functions

### Universal Load (+page.ts)

Runs on both server and client. Must use `fetch` for data fetching.

```typescript
// src/routes/products/+page.ts
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params, url }) => {
  const response = await fetch('/api/products');
  const products = await response.json();

  return {
    products,
    searchQuery: url.searchParams.get('q') || ''
  };
};

// Prerendering options
export const prerender = true; // Static generation
export const ssr = false;      // Disable SSR (SPA mode)
export const csr = true;       // Enable client-side rendering
```

### Server-Only Load (+page.server.ts)

Runs only on server. Direct database access allowed.

```typescript
// src/routes/dashboard/+page.server.ts
import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { db } from '$lib/server/database';

export const load: PageServerLoad = async ({ locals, cookies }) => {
  // Check authentication
  if (!locals.user) {
    throw redirect(303, '/login');
  }

  // Direct database query (server-only)
  const stats = await db.query.stats.findFirst({
    where: eq(stats.userId, locals.user.id)
  });

  // Sensitive data stays on server
  const apiKey = process.env.SECRET_API_KEY;
  const data = await fetchPrivateData(apiKey);

  return {
    stats,
    userData: data
  };
};
```

### Streaming with Promises

```typescript
// src/routes/posts/+page.server.ts
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
  return {
    // Immediate data
    featured: await db.posts.findMany({ where: { featured: true } }),

    // Streamed data (loads async)
    recent: db.posts.findMany({ orderBy: { createdAt: 'desc' } }),
    popular: db.posts.findMany({ orderBy: { views: 'desc' } })
  };
};
```

```svelte
<!-- src/routes/posts/+page.svelte -->
<script lang="ts">
  import type { PageData } from './$types';

  let { data } = $props<{ data: PageData }>();
</script>

<h2>Featured</h2>
{#each data.featured as post}
  <article>{post.title}</article>
{/each}

<h2>Recent</h2>
{#await data.recent}
  <p>Loading recent posts...</p>
{:then posts}
  {#each posts as post}
    <article>{post.title}</article>
  {/each}
{/await}

<h2>Popular</h2>
{#await data.popular}
  <p>Loading popular posts...</p>
{:then posts}
  {#each posts as post}
    <article>{post.title}</article>
  {/each}
{/await}
```

## Layouts

### Shared Layout

```svelte
<!-- src/routes/+layout.svelte -->
<script lang="ts">
  import Header from '$lib/components/Header.svelte';
  import Footer from '$lib/components/Footer.svelte';
  import type { LayoutData } from './$types';

  let { data, children } = $props<{ data: LayoutData, children: any }>();
</script>

<div class="app">
  <Header user={data.user} />

  <main>
    {@render children()}
  </main>

  <Footer />
</div>

<style>
  .app {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }

  main {
    flex: 1;
  }
</style>
```

### Layout Load

```typescript
// src/routes/+layout.server.ts
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals }) => {
  return {
    user: locals.user || null
  };
};
```

### Nested Layouts

```
src/routes/
├── +layout.svelte              # Root layout (all pages)
├── (app)/
│   ├── +layout.svelte          # App layout (dashboard, settings)
│   ├── dashboard/
│   │   └── +page.svelte        # Uses: root + app layouts
│   └── settings/
│       └── +page.svelte
└── (marketing)/
    ├── +layout.svelte          # Marketing layout (about, pricing)
    ├── about/
    │   └── +page.svelte        # Uses: root + marketing layouts
    └── pricing/
        └── +page.svelte
```

**Layout groups with `(name)` don't affect URL structure**:
- `/dashboard` not `/(app)/dashboard`

### Breaking Out of Layouts

```svelte
<!-- src/routes/admin/+layout.svelte -->
<script>
  let { children } = $props();
</script>

<div class="admin">
  {@render children()}
</div>
```

```svelte
<!-- src/routes/admin/login/+page@.svelte -->
<!-- @ breaks out to root layout, skipping admin layout -->
<form method="POST">
  <input name="email" type="email" />
  <input name="password" type="password" />
  <button type="submit">Login</button>
</form>
```

## Form Actions

### Basic Form Actions

```typescript
// src/routes/login/+page.server.ts
import { fail, redirect } from '@sveltejs/kit';
import type { Actions } from './$types';

export const actions = {
  // Default action (form without action attribute)
  default: async ({ request, cookies }) => {
    const data = await request.formData();
    const email = data.get('email');
    const password = data.get('password');

    if (!email || !password) {
      return fail(400, { email, missing: true });
    }

    const user = await authenticateUser(email, password);
    if (!user) {
      return fail(401, { email, incorrect: true });
    }

    cookies.set('session', user.sessionToken, {
      path: '/',
      httpOnly: true,
      sameSite: 'strict',
      secure: process.env.NODE_ENV === 'production',
      maxAge: 60 * 60 * 24 * 7 // 1 week
    });

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
  <input
    name="email"
    type="email"
    value={form?.email ?? ''}
    required
  />

  <input name="password" type="password" required />

  {#if form?.missing}
    <p class="error">Please fill in all fields</p>
  {/if}

  {#if form?.incorrect}
    <p class="error">Invalid email or password</p>
  {/if}

  <button type="submit">Log in</button>
</form>
```

### Named Actions

```typescript
// src/routes/todos/+page.server.ts
import { fail } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
  return {
    todos: await db.todos.findMany()
  };
};

export const actions = {
  create: async ({ request }) => {
    const data = await request.formData();
    const text = data.get('text');

    if (!text) {
      return fail(400, { text, missing: true });
    }

    await db.todos.create({ data: { text, done: false } });
    return { success: true };
  },

  toggle: async ({ request }) => {
    const data = await request.formData();
    const id = data.get('id');

    const todo = await db.todos.findUnique({ where: { id } });
    await db.todos.update({
      where: { id },
      data: { done: !todo.done }
    });

    return { toggled: true };
  },

  delete: async ({ request }) => {
    const data = await request.formData();
    const id = data.get('id');

    await db.todos.delete({ where: { id } });
    return { deleted: true };
  }
} satisfies Actions;
```

```svelte
<!-- src/routes/todos/+page.svelte -->
<script lang="ts">
  import type { PageData, ActionData } from './$types';

  let { data, form } = $props<{ data: PageData, form?: ActionData }>();
</script>

<h1>Todos</h1>

{#if form?.success}
  <p class="success">Todo created!</p>
{/if}

<form method="POST" action="?/create">
  <input name="text" placeholder="What needs to be done?" required />
  <button type="submit">Add</button>
</form>

{#each data.todos as todo}
  <div>
    <form method="POST" action="?/toggle">
      <input type="hidden" name="id" value={todo.id} />
      <input
        type="checkbox"
        checked={todo.done}
        onchange={(e) => e.currentTarget.form?.requestSubmit()}
      />
      <span class:done={todo.done}>{todo.text}</span>
    </form>

    <form method="POST" action="?/delete">
      <input type="hidden" name="id" value={todo.id} />
      <button type="submit">Delete</button>
    </form>
  </div>
{/each}

<style>
  .done {
    text-decoration: line-through;
    opacity: 0.6;
  }
</style>
```

### Progressive Enhancement

```svelte
<!-- src/routes/search/+page.svelte -->
<script lang="ts">
  import { enhance } from '$app/forms';
  import type { PageData, ActionData } from './$types';

  let { data, form } = $props<{ data: PageData, form?: ActionData }>();
  let isLoading = $state(false);
</script>

<form
  method="POST"
  use:enhance={() => {
    isLoading = true;

    return async ({ update }) => {
      await update();
      isLoading = false;
    };
  }}
>
  <input name="query" placeholder="Search..." />
  <button type="submit" disabled={isLoading}>
    {isLoading ? 'Searching...' : 'Search'}
  </button>
</form>

{#if form?.results}
  <ul>
    {#each form.results as result}
      <li>{result.title}</li>
    {/each}
  </ul>
{/if}
```

## API Routes (+server.ts)

### REST Endpoints

```typescript
// src/routes/api/posts/+server.ts
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ url }) => {
  const limit = Number(url.searchParams.get('limit')) || 10;
  const offset = Number(url.searchParams.get('offset')) || 0;

  const posts = await db.posts.findMany({
    take: limit,
    skip: offset,
    orderBy: { createdAt: 'desc' }
  });

  return json(posts);
};

export const POST: RequestHandler = async ({ request, locals }) => {
  if (!locals.user) {
    return json({ error: 'Unauthorized' }, { status: 401 });
  }

  const data = await request.json();

  const post = await db.posts.create({
    data: {
      title: data.title,
      content: data.content,
      authorId: locals.user.id
    }
  });

  return json(post, { status: 201 });
};
```

### Dynamic API Routes

```typescript
// src/routes/api/posts/[id]/+server.ts
import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ params }) => {
  const post = await db.posts.findUnique({
    where: { id: params.id }
  });

  if (!post) {
    throw error(404, 'Post not found');
  }

  return json(post);
};

export const PATCH: RequestHandler = async ({ params, request, locals }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  const post = await db.posts.findUnique({ where: { id: params.id } });

  if (post.authorId !== locals.user.id) {
    throw error(403, 'Forbidden');
  }

  const data = await request.json();
  const updated = await db.posts.update({
    where: { id: params.id },
    data: { title: data.title, content: data.content }
  });

  return json(updated);
};

export const DELETE: RequestHandler = async ({ params, locals }) => {
  if (!locals.user) {
    throw error(401, 'Unauthorized');
  }

  const post = await db.posts.findUnique({ where: { id: params.id } });

  if (post.authorId !== locals.user.id) {
    throw error(403, 'Forbidden');
  }

  await db.posts.delete({ where: { id: params.id } });

  return new Response(null, { status: 204 });
};
```

## Hooks

### Server Hooks (hooks.server.ts)

```typescript
// src/hooks.server.ts
import { redirect, type Handle } from '@sveltejs/kit';
import { sequence } from '@sveltejs/kit/hooks';

// Authentication middleware
const auth: Handle = async ({ event, resolve }) => {
  const sessionToken = event.cookies.get('session');

  if (sessionToken) {
    event.locals.user = await getUserFromSession(sessionToken);
  }

  return resolve(event);
};

// Logging middleware
const logging: Handle = async ({ event, resolve }) => {
  const start = Date.now();
  const response = await resolve(event);
  const duration = Date.now() - start;

  console.log(`${event.request.method} ${event.url.pathname} ${response.status} ${duration}ms`);

  return response;
};

// Protected routes middleware
const protect: Handle = async ({ event, resolve }) => {
  if (event.url.pathname.startsWith('/admin')) {
    if (!event.locals.user?.isAdmin) {
      throw redirect(303, '/login');
    }
  }

  if (event.url.pathname.startsWith('/dashboard')) {
    if (!event.locals.user) {
      throw redirect(303, '/login');
    }
  }

  return resolve(event);
};

// Combine hooks in sequence
export const handle = sequence(auth, logging, protect);

// Error handling
export const handleError = async ({ error, event }) => {
  console.error('Error:', error);

  return {
    message: 'An unexpected error occurred',
    code: error?.code ?? 'UNKNOWN'
  };
};

// Fetch handling (modify requests)
export const handleFetch = async ({ request, fetch }) => {
  // Add auth headers to internal API calls
  if (request.url.startsWith('https://api.example.com')) {
    request.headers.set('Authorization', `Bearer ${process.env.API_TOKEN}`);
  }

  return fetch(request);
};
```

### Client Hooks (hooks.client.ts)

```typescript
// src/hooks.client.ts
import type { HandleClientError } from '@sveltejs/kit';

export const handleError: HandleClientError = async ({ error, event }) => {
  console.error('Client error:', error);

  // Send to error tracking service
  if (typeof window !== 'undefined') {
    // Sentry, LogRocket, etc.
  }

  return {
    message: 'Something went wrong',
  };
};
```

## Environment Variables

### Static Environment Variables

```typescript
// src/lib/config.ts
import { env } from '$env/static/public';
import { env as privateEnv } from '$env/static/private';

// Public variables (available in browser)
export const PUBLIC_API_URL = env.PUBLIC_API_URL;
export const PUBLIC_SITE_NAME = env.PUBLIC_SITE_NAME;

// Private variables (server-only)
export const DATABASE_URL = privateEnv.DATABASE_URL;
export const SECRET_KEY = privateEnv.SECRET_KEY;
```

### Dynamic Environment Variables

```typescript
// src/routes/+page.server.ts
import { env } from '$env/dynamic/private';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
  // Can change at runtime
  const apiUrl = env.API_URL;

  return {
    data: await fetch(apiUrl).then(r => r.json())
  };
};
```

**Environment file (.env)**:
```bash
# Public (exposed to browser)
PUBLIC_API_URL=https://api.example.com
PUBLIC_ANALYTICS_ID=UA-123456789

# Private (server-only)
DATABASE_URL=postgres://localhost:5432/mydb
SECRET_KEY=super-secret-key
STRIPE_SECRET_KEY=sk_live_abc123
```

## Prerendering and SSR

### Prerendering Options

```typescript
// src/routes/blog/+page.ts
export const prerender = true; // Prerender at build time
export const ssr = true;        // Server-side render (default)
export const csr = true;        // Client-side render (default)
```

**Prerender entire site**:
```javascript
// svelte.config.js
export default {
  kit: {
    prerender: {
      entries: ['*'],
      crawl: true
    }
  }
};
```

### Dynamic Prerendering

```typescript
// src/routes/blog/[slug]/+page.server.ts
import type { EntryGenerator, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params }) => {
  const post = await db.posts.findUnique({
    where: { slug: params.slug }
  });

  return { post };
};

// Generate static pages for all posts at build time
export const entries: EntryGenerator = async () => {
  const posts = await db.posts.findMany();

  return posts.map(post => ({
    slug: post.slug
  }));
};

export const prerender = true;
```

## Adapters

### Vercel Adapter

```bash
npm install -D @sveltejs/adapter-vercel
```

```javascript
// svelte.config.js
import adapter from '@sveltejs/adapter-vercel';

export default {
  kit: {
    adapter: adapter({
      runtime: 'edge', // or 'nodejs'
      regions: ['iad1', 'sfo1'],
      split: false
    })
  }
};
```

### Netlify Adapter

```bash
npm install -D @sveltejs/adapter-netlify
```

```javascript
// svelte.config.js
import adapter from '@sveltejs/adapter-netlify';

export default {
  kit: {
    adapter: adapter({
      edge: false, // true for edge functions
      split: false
    })
  }
};
```

### Node Adapter

```bash
npm install -D @sveltejs/adapter-node
```

```javascript
// svelte.config.js
import adapter from '@sveltejs/adapter-node';

export default {
  kit: {
    adapter: adapter({
      out: 'build',
      precompress: true,
      envPrefix: 'MY_'
    })
  }
};
```

**Run production server**:
```bash
npm run build
node build
```

### Static Adapter (SSG)

```bash
npm install -D @sveltejs/adapter-static
```

```javascript
// svelte.config.js
import adapter from '@sveltejs/adapter-static';

export default {
  kit: {
    adapter: adapter({
      pages: 'build',
      assets: 'build',
      fallback: '200.html', // SPA fallback
      precompress: false
    })
  }
};
```

### Cloudflare Pages

```bash
npm install -D @sveltejs/adapter-cloudflare
```

```javascript
// svelte.config.js
import adapter from '@sveltejs/adapter-cloudflare';

export default {
  kit: {
    adapter: adapter({
      routes: {
        include: ['/*'],
        exclude: ['<build>']
      }
    })
  }
};
```

## Testing

### Unit Tests with Vitest

```typescript
// src/lib/utils.test.ts
import { describe, it, expect } from 'vitest';
import { formatDate } from './utils';

describe('formatDate', () => {
  it('formats date correctly', () => {
    const date = new Date('2024-01-15');
    expect(formatDate(date)).toBe('January 15, 2024');
  });
});
```

### Component Tests

```typescript
// src/lib/components/Button.test.ts
import { render, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import Button from './Button.svelte';

describe('Button', () => {
  it('renders with text', () => {
    const { getByText } = render(Button, {
      props: { text: 'Click me' }
    });

    expect(getByText('Click me')).toBeInTheDocument();
  });

  it('calls onclick handler', async () => {
    const handleClick = vi.fn();
    const { getByText } = render(Button, {
      props: { text: 'Click me', onclick: handleClick }
    });

    const button = getByText('Click me');
    await fireEvent.click(button);

    expect(handleClick).toHaveBeenCalledOnce();
  });
});
```

### E2E Tests with Playwright

```typescript
// tests/login.test.ts
import { expect, test } from '@playwright/test';

test('user can log in', async ({ page }) => {
  await page.goto('/login');

  await page.fill('input[name="email"]', 'user@example.com');
  await page.fill('input[name="password"]', 'password123');
  await page.click('button[type="submit"]');

  await expect(page).toHaveURL('/dashboard');
  await expect(page.locator('h1')).toContainText('Dashboard');
});

test('login validation works', async ({ page }) => {
  await page.goto('/login');

  await page.click('button[type="submit"]');

  await expect(page.locator('.error')).toContainText('Please fill in all fields');
});
```

### Load Function Tests

```typescript
// src/routes/blog/+page.server.test.ts
import { describe, it, expect, vi } from 'vitest';
import { load } from './+page.server';

vi.mock('$lib/server/database', () => ({
  db: {
    posts: {
      findMany: vi.fn(() => Promise.resolve([
        { id: '1', title: 'Post 1' },
        { id: '2', title: 'Post 2' }
      ]))
    }
  }
}));

describe('blog page load', () => {
  it('loads posts', async () => {
    const result = await load({ params: {}, url: new URL('http://localhost') } as any);

    expect(result.posts).toHaveLength(2);
    expect(result.posts[0].title).toBe('Post 1');
  });
});
```

## Advanced Patterns

### Parallel Loading

```typescript
// src/routes/dashboard/+layout.server.ts
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals }) => {
  // Load data in parallel
  const [user, notifications, settings] = await Promise.all([
    db.users.findUnique({ where: { id: locals.user.id } }),
    db.notifications.findMany({ where: { userId: locals.user.id } }),
    db.settings.findUnique({ where: { userId: locals.user.id } })
  ]);

  return {
    user,
    notifications,
    settings
  };
};
```

### Dependent Loading

```typescript
// src/routes/profile/[username]/+page.server.ts
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, parent }) => {
  // Wait for parent layout data
  const { user } = await parent();

  const profile = await db.profiles.findUnique({
    where: { username: params.username }
  });

  if (!profile) {
    throw error(404, 'Profile not found');
  }

  // Load posts only if profile exists
  const posts = await db.posts.findMany({
    where: { authorId: profile.id },
    orderBy: { createdAt: 'desc' }
  });

  return {
    profile,
    posts,
    isOwnProfile: user?.id === profile.id
  };
};
```

### Invalidation and Reloading

```svelte
<script lang="ts">
  import { invalidate, invalidateAll } from '$app/navigation';
  import { page } from '$app/stores';

  async function refresh() {
    // Reload current page data
    await invalidateAll();
  }

  async function refreshPosts() {
    // Reload specific data
    await invalidate('/api/posts');
  }

  async function refreshUser() {
    // Reload data depending on specific URL
    await invalidate(url => url.pathname.startsWith('/api/user'));
  }
</script>

<button onclick={refresh}>Refresh All</button>
<button onclick={refreshPosts}>Refresh Posts</button>
```

### Page Options

```typescript
// src/routes/admin/+page.ts
export const ssr = false;      // Disable server-side rendering
export const csr = true;       // Enable client-side rendering
export const prerender = false; // Disable prerendering
export const trailingSlash = 'always'; // /page/ instead of /page
```

## Deployment Examples

### Vercel Deployment

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
vercel

# Production deploy
vercel --prod
```

**vercel.json**:
```json
{
  "buildCommand": "npm run build",
  "devCommand": "npm run dev",
  "framework": "sveltekit"
}
```

### Docker Deployment (Node Adapter)

**Dockerfile**:
```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
RUN npm prune --production

FROM node:20-alpine

WORKDIR /app
COPY --from=builder /app/build build/
COPY --from=builder /app/node_modules node_modules/
COPY package.json .

EXPOSE 3000
ENV NODE_ENV=production
CMD ["node", "build"]
```

```bash
docker build -t my-sveltekit-app .
docker run -p 3000:3000 my-sveltekit-app
```

### Static Hosting (Netlify, GitHub Pages)

```bash
# Build static site
npm run build

# Output in build/ directory
# Deploy build/ to static host
```

**netlify.toml**:
```toml
[build]
  command = "npm run build"
  publish = "build"

[[redirects]]
  from = "/*"
  to = "/200.html"
  status = 200
```

## Best Practices

1. **Use `+page.server.ts` for sensitive operations** - Keep secrets server-side
2. **Leverage progressive enhancement** - Forms work without JavaScript
3. **Use `$types` for type safety** - Auto-generated types from SvelteKit
4. **Implement error boundaries** - Use `+error.svelte` for graceful errors
5. **Optimize images** - Use `@sveltejs/enhanced-img` for automatic optimization
6. **Enable prerendering** - Static pages are faster and cheaper
7. **Use parallel loading** - `Promise.all()` for concurrent data fetching
8. **Validate form data** - Use Zod or similar for schema validation
9. **Set security headers** - Use hooks for CSP, CORS, etc.
10. **Test with Playwright** - E2E tests prevent regressions

## Common Patterns

### Authentication Flow

```typescript
// src/routes/login/+page.server.ts
export const actions = {
  default: async ({ request, cookies }) => {
    const data = await request.formData();
    const user = await authenticate(data.get('email'), data.get('password'));

    cookies.set('session', user.sessionToken, {
      path: '/',
      httpOnly: true,
      sameSite: 'strict',
      secure: true,
      maxAge: 60 * 60 * 24 * 7
    });

    throw redirect(303, '/dashboard');
  }
};
```

```typescript
// src/hooks.server.ts
export const handle: Handle = async ({ event, resolve }) => {
  const sessionToken = event.cookies.get('session');
  if (sessionToken) {
    event.locals.user = await getUserFromSession(sessionToken);
  }
  return resolve(event);
};
```

### Protected Routes

```typescript
// src/routes/dashboard/+page.server.ts
import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
  if (!locals.user) {
    throw redirect(303, '/login');
  }

  return {
    user: locals.user
  };
};
```

### Form Validation

```typescript
// src/routes/register/+page.server.ts
import { fail } from '@sveltejs/kit';
import { z } from 'zod';
import type { Actions } from './$types';

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  confirmPassword: z.string()
}).refine(data => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword']
});

export const actions = {
  default: async ({ request }) => {
    const data = await request.formData();
    const formData = Object.fromEntries(data);

    const result = schema.safeParse(formData);

    if (!result.success) {
      return fail(400, {
        errors: result.error.flatten().fieldErrors,
        data: formData
      });
    }

    await createUser(result.data);
    throw redirect(303, '/login');
  }
} satisfies Actions;
```

## Resources

- **SvelteKit Docs**: https://kit.svelte.dev/docs
- **Svelte Tutorial**: https://learn.svelte.dev
- **Adapters**: https://kit.svelte.dev/docs/adapters
- **Deployment**: https://kit.svelte.dev/docs/adapter-auto
- **Discord**: https://svelte.dev/chat

## Summary

- **SvelteKit** is the official full-stack framework for Svelte
- **File-based routing** with `+page.svelte`, `+layout.svelte`, `+server.ts`
- **Load functions** provide type-safe data fetching (universal and server-only)
- **Form actions** enable progressive enhancement with native HTML forms
- **SSR/SSG/SPA** modes with per-route control via `prerender`, `ssr`, `csr`
- **Adapters** deploy to any platform (Vercel, Netlify, Node, Cloudflare, static)
- **Hooks** provide middleware-like functionality for auth, logging, error handling
- **TypeScript-first** with auto-generated `$types` for complete type safety
- **Environment variables** with `$env/static` and `$env/dynamic` modules
- **Testing** with Vitest (unit) and Playwright (E2E)
