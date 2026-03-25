# TypeScript Configuration Guide

Complete tsconfig.json reference for modern TypeScript projects.

## 2025 Recommended Configuration

### General-Purpose Projects

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "lib": ["ES2022"],
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "noPropertyAccessFromIndexSignature": true,
    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "dist",
    "rootDir": "src"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

### Next.js Projects

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "noUncheckedIndexedAccess": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

### Library Projects

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "lib": ["ES2020"],
    "strict": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "dist",
    "rootDir": "src",
    "isolatedModules": true,
    "verbatimModuleSyntax": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  }
}
```

## Local Repo Baselines (Examples)

### CLI / Node CommonJS (ai-code-review)

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "moduleResolution": "Node",
    "strict": true,
    "outDir": "dist",
    "declaration": true,
    "sourceMap": true,
    "types": ["vitest/globals", "node"],
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["dist", "**/*.test.ts"]
}
```

### NodeNext Strict (smarterthings)

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "noUncheckedIndexedAccess": true
  },
  "include": ["src/**/*"],
  "exclude": ["dist", "tests"]
}
```

### Next.js Bundler (matsuoka-com)

Use the Next.js example above with `moduleResolution: "bundler"` and `noEmit: true` for app builds.

### Node.js 22+ Type Stripping

```json
{
  "compilerOptions": {
    "target": "ESNext",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "erasableSyntaxOnly": true,
    "verbatimModuleSyntax": true,
    "noEmit": true
  }
}
```

## Key Options Explained

### Module System

| Option | When to Use |
|--------|-------------|
| `"module": "NodeNext"` | Node.js packages with ESM |
| `"module": "ESNext"` | Bundled apps (Vite, Webpack) |
| `"module": "CommonJS"` | Legacy Node.js packages |

| Resolution | When to Use |
|------------|-------------|
| `"moduleResolution": "NodeNext"` | Node.js ESM packages |
| `"moduleResolution": "bundler"` | Apps using Vite/Webpack/esbuild |
| `"moduleResolution": "node"` | Legacy CommonJS |

### Strictness Options

```json
{
  "compilerOptions": {
    // Core strict mode (enables all below)
    "strict": true,
    
    // Additional strictness (not in strict)
    "noUncheckedIndexedAccess": true,    // T | undefined for index access
    "exactOptionalPropertyTypes": true,   // Distinguish missing vs undefined
    "noPropertyAccessFromIndexSignature": true,  // Require bracket notation
    "noImplicitOverride": true            // Require override keyword
  }
}
```

**What `strict: true` enables:**
- `strictNullChecks`: `null` and `undefined` are distinct types
- `strictFunctionTypes`: Strict function parameter checking
- `strictBindCallApply`: Strict `bind`, `call`, `apply` methods
- `strictPropertyInitialization`: Class properties must be initialized
- `noImplicitAny`: Error on implicit `any`
- `noImplicitThis`: Error on implicit `this`
- `useUnknownInCatchVariables`: Catch variables are `unknown`
- `alwaysStrict`: Emit "use strict"

### Import/Export

```json
{
  "compilerOptions": {
    // Modern: explicit type imports required
    "verbatimModuleSyntax": true,
    
    // Legacy alternative (deprecated)
    "importsNotUsedAsValues": "error",
    "preserveValueImports": true
  }
}
```

With `verbatimModuleSyntax`:
```typescript
// ✅ Correct
import type { User } from './types';
import { createUser } from './utils';

// ❌ Error - type-only import not marked
import { User } from './types';
```

### Output Options

```json
{
  "compilerOptions": {
    "outDir": "dist",           // Output directory
    "rootDir": "src",           // Source directory
    "declaration": true,        // Generate .d.ts files
    "declarationMap": true,     // Source maps for .d.ts
    "sourceMap": true,          // Generate .js.map
    "inlineSources": true,      // Include source in maps
    "declarationDir": "types"   // Separate types directory
  }
}
```

### Path Mapping

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@components/*": ["src/components/*"],
      "@utils/*": ["src/utils/*"],
      "@types/*": ["src/types/*"]
    }
  }
}
```

**Note:** Path mappings require bundler/runtime support (tsconfig-paths for Node.js).

## Project References (Monorepos)

### Root tsconfig.json

```json
{
  "files": [],
  "references": [
    { "path": "packages/core" },
    { "path": "packages/cli" },
    { "path": "packages/web" }
  ]
}
```

### Package tsconfig.json

```json
{
  "compilerOptions": {
    "composite": true,
    "declaration": true,
    "declarationMap": true,
    "outDir": "dist",
    "rootDir": "src"
  },
  "references": [
    { "path": "../core" }
  ]
}
```

### Build Commands

```bash
# Build all projects
tsc --build

# Build with watch
tsc --build --watch

# Clean build artifacts
tsc --build --clean

# Force rebuild
tsc --build --force
```

## Configuration Inheritance

### Base Configuration

```json
// tsconfig.base.json
{
  "compilerOptions": {
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "moduleDetection": "force"
  }
}
```

### Extending Base

```json
// tsconfig.json
{
  "extends": "./tsconfig.base.json",
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "outDir": "dist"
  },
  "include": ["src"]
}
```

### Official Base Configs

```bash
npm install -D @tsconfig/node20 @tsconfig/strictest
```

```json
{
  "extends": ["@tsconfig/node20/tsconfig.json", "@tsconfig/strictest/tsconfig.json"],
  "compilerOptions": {
    "outDir": "dist"
  }
}
```

## Common Issues

### Issue: Cannot find module

**Cause:** Module resolution mismatch

**Fix:**
```json
{
  "compilerOptions": {
    "moduleResolution": "NodeNext",  // Or "bundler" for bundled apps
    "module": "NodeNext"
  }
}
```

### Issue: Type-only imports being emitted

**Cause:** Missing verbatimModuleSyntax

**Fix:**
```json
{
  "compilerOptions": {
    "verbatimModuleSyntax": true
  }
}
```

Then use:
```typescript
import type { SomeType } from './types';
```

### Issue: Index access returns T instead of T | undefined

**Cause:** Missing noUncheckedIndexedAccess

**Fix:**
```json
{
  "compilerOptions": {
    "noUncheckedIndexedAccess": true
  }
}
```

### Issue: ESM/CJS interop problems

**Cause:** Incorrect module settings

**Fix for ESM packages:**
```json
{
  "compilerOptions": {
    "module": "NodeNext",
    "moduleResolution": "NodeNext"
  }
}
```

And in package.json:
```json
{
  "type": "module"
}
```

### Issue: Slow type checking

**Fixes:**
```json
{
  "compilerOptions": {
    "skipLibCheck": true,           // Skip .d.ts checking
    "incremental": true,            // Incremental compilation
    "tsBuildInfoFile": ".tsbuildinfo"
  },
  "exclude": ["node_modules", "dist", "**/*.test.ts"]
}
```

## TypeScript 5.9 Features

### Deferred Module Evaluation

```typescript
// Module evaluated only when property accessed
import defer * as feature from "./some-feature.js";

// Module NOT loaded yet
console.log("Starting...");

// NOW module loads
console.log(feature.specialConstant);
```

### Improved Return Type Narrowing

```typescript
function getLength(x: string | number[]) {
  if (hasLength(x)) {
    return x.length;  // Better narrowing
  }
  return 0;
}

function hasLength(x: unknown): x is { length: number } {
  return typeof x === 'object' && x !== null && 'length' in x;
}
```

## Validation Checklist

- [ ] `strict: true` enabled
- [ ] `noUncheckedIndexedAccess: true` for array safety
- [ ] `verbatimModuleSyntax: true` for explicit type imports
- [ ] `skipLibCheck: true` for faster builds
- [ ] Module resolution matches runtime (NodeNext/bundler)
- [ ] Path mappings have runtime support
- [ ] `composite: true` for project references
