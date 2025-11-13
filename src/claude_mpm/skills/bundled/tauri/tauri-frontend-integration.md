---
name: tauri-frontend-integration
description: Frontend integration patterns for Tauri including TypeScript services, React hooks, Vue composition, Svelte stores, and framework-agnostic patterns
version: 1.0.0
category: development
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Frontend patterns: TypeScript service layer, React hooks for commands/events, Vue/Svelte integration, type safety across IPC boundary"
    when_to_use: "Building Tauri frontend with React, Vue, Svelte, or vanilla JS with proper TypeScript types and abstractions"
    quick_start: "1. Create typed service layer 2. Framework-specific hooks/composables 3. Event handling 4. Error boundaries"
context_limit: 700
tags:
  - tauri
  - frontend
  - react
  - vue
  - svelte
  - typescript
  - integration
requires_tools: []
---

# Tauri Frontend Integration

## TypeScript Service Layer

### Type-Safe Command Service

```typescript
// src/services/tauri.ts
import { invoke } from '@tauri-apps/api/core';

// Backend command types
export interface FileMetadata {
    name: string;
    size: number;
    modified: number;
    isDir: boolean;
}

export interface UserConfig {
    theme: 'light' | 'dark';
    language: string;
    autoSave: boolean;
}

// Command service with full typing
export class TauriService {
    static async readFile(path: string): Promise<string> {
        return await invoke<string>('read_file', { path });
    }

    static async writeFile(path: string, content: string): Promise<void> {
        await invoke('write_file', { path, content });
    }

    static async listFiles(directory: string): Promise<FileMetadata[]> {
        return await invoke<FileMetadata[]>('list_files', { directory });
    }

    static async getConfig(): Promise<UserConfig> {
        return await invoke<UserConfig>('get_config');
    }

    static async updateConfig(config: Partial<UserConfig>): Promise<void> {
        await invoke('update_config', { config });
    }

    static async performSearch(query: string, caseSensitive: boolean): Promise<string[]> {
        return await invoke<string[]>('perform_search', {
            query,
            caseSensitive
        });
    }
}
```

### Result Type Pattern

```typescript
// src/types/result.ts
export type Result<T, E = string> =
    | { ok: true; value: T }
    | { ok: false; error: E };

export function Ok<T>(value: T): Result<T> {
    return { ok: true, value };
}

export function Err<E = string>(error: E): Result<never, E> {
    return { ok: false, error };
}

// Service using Result type
export class SafeTauriService {
    static async readFile(path: string): Promise<Result<string>> {
        try {
            const content = await invoke<string>('read_file', { path });
            return Ok(content);
        } catch (error) {
            return Err(String(error));
        }
    }

    static async writeFile(path: string, content: string): Promise<Result<void>> {
        try {
            await invoke('write_file', { path, content });
            return Ok(undefined);
        } catch (error) {
            return Err(String(error));
        }
    }
}
```

## React Integration

### Custom Hooks for Commands

```typescript
// src/hooks/useTauriCommand.ts
import { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';

export interface CommandState<T> {
    data: T | null;
    loading: boolean;
    error: string | null;
}

export function useTauriCommand<T>(
    command: string,
    args?: Record<string, unknown>,
    immediate: boolean = true
): CommandState<T> & { refetch: () => Promise<void> } {
    const [state, setState] = useState<CommandState<T>>({
        data: null,
        loading: immediate,
        error: null
    });

    const execute = async () => {
        setState(prev => ({ ...prev, loading: true, error: null }));

        try {
            const data = await invoke<T>(command, args);
            setState({ data, loading: false, error: null });
        } catch (error) {
            setState({ data: null, loading: false, error: String(error) });
        }
    };

    useEffect(() => {
        if (immediate) {
            execute();
        }
    }, [command, JSON.stringify(args)]);

    return { ...state, refetch: execute };
}

// Usage
function FileList() {
    const { data: files, loading, error, refetch } = useTauriCommand<FileMetadata[]>(
        'list_files',
        { directory: '/home/user/documents' }
    );

    if (loading) return <div>Loading...</div>;
    if (error) return <div>Error: {error}</div>;

    return (
        <div>
            <button onClick={refetch}>Refresh</button>
            {files?.map(file => (
                <div key={file.name}>{file.name}</div>
            ))}
        </div>
    );
}
```

### Event Hooks

```typescript
// src/hooks/useTauriEvent.ts
import { useEffect, useState } from 'react';
import { listen, UnlistenFn } from '@tauri-apps/api/event';

export function useTauriEvent<T>(event: string): T | null {
    const [data, setData] = useState<T | null>(null);

    useEffect(() => {
        let unlisten: UnlistenFn;

        listen<T>(event, (e) => {
            setData(e.payload);
        }).then(fn => {
            unlisten = fn;
        });

        return () => {
            if (unlisten) unlisten();
        };
    }, [event]);

    return data;
}

// Usage
function ProgressBar() {
    const progress = useTauriEvent<{ current: number; total: number }>('download-progress');

    if (!progress) return null;

    const percentage = (progress.current / progress.total) * 100;

    return (
        <div className="progress-bar">
            <div style={{ width: `${percentage}%` }} />
            <span>{percentage.toFixed(0)}%</span>
        </div>
    );
}
```

### Bidirectional Event Hook

```typescript
// src/hooks/useTauriEventEmitter.ts
import { useCallback, useEffect } from 'react';
import { listen, emit, UnlistenFn } from '@tauri-apps/api/event';

export function useTauriEventEmitter<T, R>(
    emitEvent: string,
    listenEvent: string,
    handler: (data: R) => void
) {
    useEffect(() => {
        let unlisten: UnlistenFn;

        listen<R>(listenEvent, (e) => {
            handler(e.payload);
        }).then(fn => {
            unlisten = fn;
        });

        return () => {
            if (unlisten) unlisten();
        };
    }, [listenEvent, handler]);

    const send = useCallback(async (data: T) => {
        await emit(emitEvent, data);
    }, [emitEvent]);

    return send;
}

// Usage
function Chat() {
    const [messages, setMessages] = useState<string[]>([]);

    const sendMessage = useTauriEventEmitter<string, string>(
        'send-message',
        'receive-message',
        (msg) => setMessages(prev => [...prev, msg])
    );

    return (
        <div>
            {messages.map((msg, i) => <div key={i}>{msg}</div>)}
            <button onClick={() => sendMessage('Hello!')}>Send</button>
        </div>
    );
}
```

### Context Provider Pattern

```typescript
// src/contexts/TauriContext.tsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';

interface AppState {
    config: UserConfig | null;
    updateConfig: (config: Partial<UserConfig>) => Promise<void>;
}

const TauriContext = createContext<AppState | undefined>(undefined);

export function TauriProvider({ children }: { children: React.ReactNode }) {
    const [config, setConfig] = useState<UserConfig | null>(null);

    useEffect(() => {
        invoke<UserConfig>('get_config').then(setConfig);
    }, []);

    const updateConfig = async (newConfig: Partial<UserConfig>) => {
        await invoke('update_config', { config: newConfig });
        setConfig(prev => ({ ...prev!, ...newConfig }));
    };

    return (
        <TauriContext.Provider value={{ config, updateConfig }}>
            {children}
        </TauriContext.Provider>
    );
}

export function useTauri() {
    const context = useContext(TauriContext);
    if (!context) throw new Error('useTauri must be used within TauriProvider');
    return context;
}

// Usage
function App() {
    return (
        <TauriProvider>
            <SettingsPanel />
        </TauriProvider>
    );
}

function SettingsPanel() {
    const { config, updateConfig } = useTauri();

    return (
        <div>
            <label>
                <input
                    type="checkbox"
                    checked={config?.autoSave}
                    onChange={(e) => updateConfig({ autoSave: e.target.checked })}
                />
                Auto Save
            </label>
        </div>
    );
}
```

## Vue 3 Integration

### Composition API Composables

```typescript
// src/composables/useTauriCommand.ts
import { ref, Ref, onMounted } from 'vue';
import { invoke } from '@tauri-apps/api/core';

export function useTauriCommand<T>(
    command: string,
    args?: Record<string, unknown>,
    immediate: boolean = true
) {
    const data: Ref<T | null> = ref(null);
    const loading = ref(immediate);
    const error: Ref<string | null> = ref(null);

    const execute = async () => {
        loading.value = true;
        error.value = null;

        try {
            data.value = await invoke<T>(command, args);
        } catch (e) {
            error.value = String(e);
        } finally {
            loading.value = false;
        }
    };

    if (immediate) {
        onMounted(execute);
    }

    return { data, loading, error, refetch: execute };
}

// Usage in component
<script setup lang="ts">
import { useTauriCommand } from '@/composables/useTauriCommand';

const { data: files, loading, error } = useTauriCommand<FileMetadata[]>(
    'list_files',
    { directory: '/home/user' }
);
</script>

<template>
    <div v-if="loading">Loading...</div>
    <div v-else-if="error">Error: {{ error }}</div>
    <div v-else>
        <div v-for="file in files" :key="file.name">
            {{ file.name }}
        </div>
    </div>
</template>
```

### Event Composable

```typescript
// src/composables/useTauriEvent.ts
import { ref, Ref, onMounted, onUnmounted } from 'vue';
import { listen, UnlistenFn } from '@tauri-apps/api/event';

export function useTauriEvent<T>(event: string): Ref<T | null> {
    const data: Ref<T | null> = ref(null);
    let unlisten: UnlistenFn;

    onMounted(async () => {
        unlisten = await listen<T>(event, (e) => {
            data.value = e.payload;
        });
    });

    onUnmounted(() => {
        if (unlisten) unlisten();
    });

    return data;
}

// Usage
<script setup lang="ts">
const progress = useTauriEvent<{ current: number; total: number }>('download-progress');
</script>

<template>
    <div v-if="progress">
        {{ Math.floor((progress.current / progress.total) * 100) }}%
    </div>
</template>
```

### Provide/Inject Pattern

```typescript
// src/composables/useTauriApp.ts
import { provide, inject, InjectionKey, Ref, ref, onMounted } from 'vue';
import { invoke } from '@tauri-apps/api/core';

interface TauriApp {
    config: Ref<UserConfig | null>;
    updateConfig: (config: Partial<UserConfig>) => Promise<void>;
}

const TauriAppKey: InjectionKey<TauriApp> = Symbol('TauriApp');

export function provideTauriApp() {
    const config = ref<UserConfig | null>(null);

    onMounted(async () => {
        config.value = await invoke<UserConfig>('get_config');
    });

    const updateConfig = async (newConfig: Partial<UserConfig>) => {
        await invoke('update_config', { config: newConfig });
        config.value = { ...config.value!, ...newConfig };
    };

    const app: TauriApp = { config, updateConfig };
    provide(TauriAppKey, app);
}

export function useTauriApp(): TauriApp {
    const app = inject(TauriAppKey);
    if (!app) throw new Error('useTauriApp must be called within TauriApp provider');
    return app;
}
```

## Svelte Integration

### Svelte Stores

```typescript
// src/stores/tauri.ts
import { writable, derived, Readable } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

export function createCommandStore<T>(command: string, args?: Record<string, unknown>) {
    const { subscribe, set } = writable<{
        data: T | null;
        loading: boolean;
        error: string | null;
    }>({
        data: null,
        loading: true,
        error: null
    });

    const load = async () => {
        set({ data: null, loading: true, error: null });

        try {
            const data = await invoke<T>(command, args);
            set({ data, loading: false, error: null });
        } catch (error) {
            set({ data: null, loading: false, error: String(error) });
        }
    };

    load();

    return {
        subscribe,
        refetch: load
    };
}

// Usage
<script lang="ts">
import { createCommandStore } from '$lib/stores/tauri';

const files = createCommandStore<FileMetadata[]>('list_files', {
    directory: '/home/user'
});
</script>

{#if $files.loading}
    <div>Loading...</div>
{:else if $files.error}
    <div>Error: {$files.error}</div>
{:else}
    {#each $files.data ?? [] as file}
        <div>{file.name}</div>
    {/each}
{/if}
```

### Event Store

```typescript
// src/stores/events.ts
import { writable } from 'svelte/store';
import { listen, UnlistenFn } from '@tauri-apps/api/event';

export function createEventStore<T>(event: string) {
    const { subscribe, set } = writable<T | null>(null);

    let unlisten: UnlistenFn;

    listen<T>(event, (e) => {
        set(e.payload);
    }).then(fn => {
        unlisten = fn;
    });

    return {
        subscribe,
        cleanup: () => {
            if (unlisten) unlisten();
        }
    };
}

// Usage
<script lang="ts">
import { onDestroy } from 'svelte';

const progress = createEventStore<{ current: number; total: number }>('download-progress');

onDestroy(() => {
    progress.cleanup();
});
</script>

{#if $progress}
    <div>
        {Math.floor(($progress.current / $progress.total) * 100)}%
    </div>
{/if}
```

## Framework-Agnostic Patterns

### Observable Pattern

```typescript
// src/utils/observable.ts
export class TauriObservable<T> {
    private listeners: Set<(data: T) => void> = new Set();
    private value: T | null = null;

    subscribe(listener: (data: T) => void): () => void {
        this.listeners.add(listener);
        if (this.value !== null) listener(this.value);

        return () => this.listeners.delete(listener);
    }

    emit(data: T) {
        this.value = data;
        this.listeners.forEach(listener => listener(data));
    }

    getValue(): T | null {
        return this.value;
    }
}

// Command observable
export function createCommandObservable<T>(
    command: string,
    args?: Record<string, unknown>
): TauriObservable<T> {
    const observable = new TauriObservable<T>();

    invoke<T>(command, args)
        .then(data => observable.emit(data))
        .catch(err => console.error(err));

    return observable;
}

// Event observable
export function createEventObservable<T>(event: string): TauriObservable<T> {
    const observable = new TauriObservable<T>();

    listen<T>(event, (e) => {
        observable.emit(e.payload);
    });

    return observable;
}
```

## Error Boundaries

### React Error Boundary

```typescript
// src/components/TauriErrorBoundary.tsx
import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
    children: ReactNode;
    fallback?: (error: Error) => ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export class TauriErrorBoundary extends Component<Props, State> {
    state: State = {
        hasError: false,
        error: null
    };

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('Tauri Error:', error, errorInfo);

        // Log to backend
        import('@tauri-apps/api/core').then(({ invoke }) => {
            invoke('log_error', {
                error: error.toString(),
                info: errorInfo.componentStack
            }).catch(console.error);
        });
    }

    render() {
        if (this.state.hasError && this.state.error) {
            if (this.props.fallback) {
                return this.props.fallback(this.state.error);
            }

            return (
                <div className="error-boundary">
                    <h2>Something went wrong</h2>
                    <pre>{this.state.error.message}</pre>
                </div>
            );
        }

        return this.props.children;
    }
}

// Usage
<TauriErrorBoundary>
    <App />
</TauriErrorBoundary>
```

## Best Practices

1. **Type everything** - Full TypeScript types across IPC boundary
2. **Service layer** - Abstract Tauri commands into typed service
3. **Framework hooks/composables** - Idiomatic patterns for each framework
4. **Error boundaries** - Catch and log Tauri errors
5. **Loading states** - Always handle loading/error states
6. **Event cleanup** - Unlisten from events on unmount
7. **Result types** - Use Result<T, E> for explicit error handling
8. **Context/Provide** - Share Tauri state across component tree
9. **Observable pattern** - Framework-agnostic state management
10. **Async safety** - Handle race conditions and cancellation

## Common Pitfalls

❌ **Not unlistening from events**:
```typescript
// WRONG - memory leak
useEffect(() => {
    listen('my-event', handler);
}, []);

// CORRECT - cleanup
useEffect(() => {
    let unlisten: UnlistenFn;
    listen('my-event', handler).then(fn => unlisten = fn);
    return () => { if (unlisten) unlisten(); };
}, []);
```

❌ **Missing loading/error states**:
```typescript
// WRONG - no feedback
const data = await invoke('command');
return <div>{data}</div>;

// CORRECT - handle all states
const { data, loading, error } = useTauriCommand('command');
if (loading) return <div>Loading...</div>;
if (error) return <div>Error: {error}</div>;
return <div>{data}</div>;
```

❌ **Invoking in render**:
```typescript
// WRONG - invokes every render
function Component() {
    const data = invoke('command');  // DON'T DO THIS
}

// CORRECT - use hooks/effects
function Component() {
    const { data } = useTauriCommand('command');
}
```

## Summary

- **TypeScript service layer** for type-safe command abstraction
- **React hooks** (useTauriCommand, useTauriEvent) for declarative data
- **Vue composables** with Composition API patterns
- **Svelte stores** for reactive command/event data
- **Framework-agnostic** observable pattern
- **Error boundaries** to catch and log Tauri errors
- **Result types** for explicit error handling
- **Context patterns** for shared Tauri state
- **Event cleanup** to prevent memory leaks
- **Type safety** across entire IPC boundary
