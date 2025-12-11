# Claude MPM Dashboard (Svelte 5)

Real-time monitoring dashboard for Claude Multi-Agent Project Manager built with SvelteKit 5 and Svelte Runes API.

## Features

- **Real-time Event Stream**: WebSocket connection via Socket.IO
- **Svelte 5 Runes**: Modern reactive state management with `$state`, `$derived`, `$effect`
- **Type Safety**: Full TypeScript integration
- **Tailwind CSS**: Utility-first styling
- **Static Build**: Embeddable in Python package

## Development

```bash
# Install dependencies
npm install

# Run dev server
npm run dev

# Build for production
npm run build
```

## Architecture

- **Socket Store**: `src/lib/stores/socket.svelte.ts` - Runes-based WebSocket state
- **Components**: Minimal reactive components using Svelte 5 syntax
- **Build Output**: `../dashboard/static/svelte-build/` for Python embedding

## Svelte 5 Patterns Used

- `$state()`: Reactive state management
- `$derived()`: Computed values
- `$effect()`: Side effects with cleanup
- Type-safe component props with destructuring

## Integration

The dashboard connects to the Claude MPM monitor server at `http://localhost:8765` by default. Configure the URL in `src/lib/stores/socket.svelte.ts`.
