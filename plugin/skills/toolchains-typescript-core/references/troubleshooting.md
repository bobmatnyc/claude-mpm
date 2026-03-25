# TypeScript Troubleshooting Guide

Comprehensive troubleshooting guide for common TypeScript errors, build issues, and configuration problems.

## Table of Contents

- [Common TypeScript Errors](#common-typescript-errors)
- [Type Inference Issues](#type-inference-issues)
- [Module Resolution Problems](#module-resolution-problems)
- [tsconfig.json Misconfigurations](#tsconfigjson-misconfigurations)
- [Build Performance Issues](#build-performance-issues)
- [Type Compatibility Errors](#type-compatibility-errors)

---

## Common TypeScript Errors

### TS2339: Property does not exist on type

**Problem:**
```typescript
const user = { name: "Alice" };
console.log(user.age); // ❌ Property 'age' does not exist on type '{ name: string; }'
```

**Diagnosis:**
- TypeScript inferred a narrow type
- Property was accessed before being added
- Object type doesn't include the property

**Solutions:**

**Solution 1: Define proper interface**
```typescript
interface User {
  name: string;
  age?: number; // Optional property
}

const user: User = { name: "Alice" };
console.log(user.age); // ✅ OK (age is optional)
```

**Solution 2: Type assertion (use sparingly)**
```typescript
const user = { name: "Alice" } as any;
console.log(user.age); // ⚠️  Works but defeats type safety

// Better: Use unknown and validate
const user: unknown = getData();
if (isUser(user)) {
  console.log(user.age); // ✅ Type-safe
}
```

**Solution 3: Index signature for dynamic properties**
```typescript
interface User {
  name: string;
  [key: string]: unknown; // Allow arbitrary properties
}
```

---

### TS2345: Argument is not assignable to parameter

**Problem:**
```typescript
function greet(name: string): void {
  console.log(`Hello, ${name}`);
}

greet(123); // ❌ Argument of type 'number' is not assignable to parameter of type 'string'
```

**Diagnosis:**
- Type mismatch between argument and parameter
- Implicit `any` was converted to explicit type
- Function overload not matching

**Solutions:**

**Solution 1: Fix the argument type**
```typescript
greet("Alice"); // ✅ Correct type
greet(String(123)); // ✅ Convert to string
```

**Solution 2: Make function more flexible**
```typescript
function greet(name: string | number): void {
  console.log(`Hello, ${String(name)}`);
}

greet(123); // ✅ OK
greet("Alice"); // ✅ OK
```

**Solution 3: Use generics for type preservation**
```typescript
function identity<T>(value: T): T {
  return value;
}

const num = identity(123); // Type: number
const str = identity("test"); // Type: string
```

---

### TS2322: Type is not assignable to type

**Problem:**
```typescript
interface Config {
  apiUrl: string;
  timeout: number;
}

const config: Config = {
  apiUrl: "https://api.example.com",
  timeout: "5000" // ❌ Type 'string' is not assignable to type 'number'
};
```

**Diagnosis:**
- Property has wrong type
- Missing required properties
- Extra properties not allowed

**Solutions:**

**Solution 1: Fix property type**
```typescript
const config: Config = {
  apiUrl: "https://api.example.com",
  timeout: 5000 // ✅ Correct type
};
```

**Solution 2: Use type assertion (if you're certain)**
```typescript
const config = {
  apiUrl: "https://api.example.com",
  timeout: "5000"
} as Config; // ⚠️  Bypasses type checking
```

**Solution 3: Use Zod for runtime validation**
```typescript
import { z } from "zod";

const ConfigSchema = z.object({
  apiUrl: z.string().url(),
  timeout: z.number().int().positive()
});

// This will throw at runtime if types are wrong
const config = ConfigSchema.parse(data);
```

---

### TS2554: Expected X arguments, but got Y

**Problem:**
```typescript
function add(a: number, b: number): number {
  return a + b;
}

add(5); // ❌ Expected 2 arguments, but got 1
```

**Diagnosis:**
- Missing required parameters
- Optional parameters confused with required
- Destructuring issues

**Solutions:**

**Solution 1: Provide all required arguments**
```typescript
add(5, 10); // ✅ OK
```

**Solution 2: Make parameters optional**
```typescript
function add(a: number, b: number = 0): number {
  return a + b;
}

add(5); // ✅ OK, b defaults to 0
```

**Solution 3: Use rest parameters**
```typescript
function sum(...numbers: number[]): number {
  return numbers.reduce((acc, n) => acc + n, 0);
}

sum(5); // ✅ OK
sum(5, 10, 15); // ✅ OK
```

---

### TS2339: Property does not exist on Window

**Problem:**
```typescript
window.myGlobal = "test"; // ❌ Property 'myGlobal' does not exist on type 'Window & typeof globalThis'
```

**Diagnosis:**
- Adding custom properties to global objects
- TypeScript doesn't know about custom globals

**Solutions:**

**Solution 1: Extend Window interface**
```typescript
// types/global.d.ts
declare global {
  interface Window {
    myGlobal: string;
  }
}

export {}; // Make this a module

// Now this works
window.myGlobal = "test"; // ✅ OK
```

**Solution 2: Use type assertion (quick fix)**
```typescript
(window as any).myGlobal = "test"; // ⚠️  Works but not type-safe
```

---

### TS18048: Object is possibly 'undefined'

**Problem:**
```typescript
const users = [{ name: "Alice" }];
console.log(users.find(u => u.name === "Bob").name);
// ❌ Object is possibly 'undefined'
```

**Diagnosis:**
- Accessing property on potentially undefined value
- Array methods like `find()` can return `undefined`
- Enabled `strictNullChecks` or `noUncheckedIndexedAccess`

**Solutions:**

**Solution 1: Optional chaining**
```typescript
console.log(users.find(u => u.name === "Bob")?.name); // ✅ OK
```

**Solution 2: Nullish coalescing**
```typescript
const user = users.find(u => u.name === "Bob") ?? { name: "Unknown" };
console.log(user.name); // ✅ OK
```

**Solution 3: Type guard**
```typescript
const user = users.find(u => u.name === "Bob");
if (user) {
  console.log(user.name); // ✅ OK, narrowed to non-undefined
}
```

**Solution 4: Non-null assertion (use with caution)**
```typescript
console.log(users.find(u => u.name === "Bob")!.name);
// ⚠️  Asserts non-null, runtime error if actually undefined
```

---

## Type Inference Issues

### Issue: TypeScript infers wrong type

**Problem:**
```typescript
const config = {
  apiUrl: "https://api.example.com",
  retryCount: 3
};

// Later...
config.apiUrl = "https://new-api.example.com"; // ✅ OK
config.retryCount = "5"; // ❌ Type 'string' is not assignable to type 'number'

// TypeScript inferred: { apiUrl: string; retryCount: number }
```

**Diagnosis:**
- TypeScript inferred mutable object type
- Wanted literal types or stricter inference

**Solutions:**

**Solution 1: Use `as const` for literal types**
```typescript
const config = {
  apiUrl: "https://api.example.com",
  retryCount: 3
} as const;

// Type: { readonly apiUrl: "https://api.example.com"; readonly retryCount: 3 }
```

**Solution 2: Use `satisfies` to validate without widening**
```typescript
type Config = {
  apiUrl: string;
  retryCount: number;
};

const config = {
  apiUrl: "https://api.example.com",
  retryCount: 3
} satisfies Config;

// Type: { apiUrl: "https://api.example.com"; retryCount: 3 }
// Validates structure while preserving literals
```

**Solution 3: Explicit type annotation**
```typescript
const config: Config = {
  apiUrl: "https://api.example.com",
  retryCount: 3
};

// Type: Config
```

---

### Issue: Generic type not inferred correctly

**Problem:**
```typescript
function createArray<T>(items: T[]): T[] {
  return items;
}

const result = createArray([]); // Type: never[]
```

**Diagnosis:**
- TypeScript can't infer generic from empty array
- Need explicit type parameter

**Solutions:**

**Solution 1: Provide type parameter explicitly**
```typescript
const result = createArray<number>([]); // Type: number[]
```

**Solution 2: Pass non-empty array**
```typescript
const result = createArray([1, 2, 3]); // Type: number[]
```

**Solution 3: Use default type parameter**
```typescript
function createArray<T = unknown>(items: T[]): T[] {
  return items;
}

const result = createArray([]); // Type: unknown[]
```

---

## Module Resolution Problems

### Issue: Cannot find module 'X'

**Problem:**
```typescript
import { User } from './types'; // ❌ Cannot find module './types'
```

**Diagnosis:**
- Missing file extension
- Incorrect path
- Module resolution strategy mismatch

**Solutions:**

**Solution 1: Add file extension (ESM with NodeNext)**
```typescript
import { User } from './types.js'; // ✅ Note: .js, not .ts
```

**Solution 2: Check tsconfig module resolution**
```json
{
  "compilerOptions": {
    "module": "NodeNext",
    "moduleResolution": "NodeNext"
  }
}
```

**Solution 3: Use path mapping**
```json
{
  "compilerOptions": {
    "baseUrl": "./src",
    "paths": {
      "@types/*": ["types/*"]
    }
  }
}
```

```typescript
import { User } from '@types/user'; // ✅ Uses path mapping
```

---

### Issue: Module has no default export

**Problem:**
```typescript
import config from './config'; // ❌ Module has no default export
```

**Diagnosis:**
- File uses named exports, not default export
- Trying to import as default

**Solutions:**

**Solution 1: Use named import**
```typescript
import { config } from './config'; // ✅ Named import
```

**Solution 2: Import everything as namespace**
```typescript
import * as Config from './config'; // ✅ Namespace import
Config.config;
```

**Solution 3: Add default export to module**
```typescript
// config.ts
export const config = { /* ... */ };
export default config; // Add default export
```

---

### Issue: ESM/CommonJS interop problems

**Problem:**
```typescript
// Using NodeNext with .mts file
const express = require('express'); // ❌ require is not defined
```

**Diagnosis:**
- Mixing ESM and CommonJS syntax
- File extension determines module system

**Solutions:**

**Solution 1: Use ESM syntax**
```typescript
import express from 'express'; // ✅ ESM import
```

**Solution 2: Use CommonJS file (.cts)**
```typescript
// file.cts
const express = require('express'); // ✅ OK in .cts files
```

**Solution 3: Dynamic import for ESM**
```typescript
const express = await import('express'); // ✅ Dynamic ESM import
```

---

## tsconfig.json Misconfigurations

### Issue: Strict mode errors everywhere

**Problem:**
After enabling `"strict": true`, thousands of errors appear.

**Diagnosis:**
- Migrating from loose to strict mode
- Code written without strict checking

**Solutions:**

**Solution 1: Gradual strict mode adoption**
```json
{
  "compilerOptions": {
    "strict": false,
    "noImplicitAny": true,  // Enable one at a time
    "strictNullChecks": false,
    "strictFunctionTypes": false
  }
}
```

**Solution 2: Use `@ts-expect-error` for migration**
```typescript
// @ts-expect-error - TODO: Fix this type error
const result = legacyFunction(data);
```

**Solution 3: Fix gradually by file/directory**
```json
{
  "compilerOptions": {
    "strict": true
  },
  "exclude": [
    "src/legacy/**/*" // Exclude legacy code temporarily
  ]
}
```

---

### Issue: Index access unsafe with noUncheckedIndexedAccess

**Problem:**
```typescript
// tsconfig: "noUncheckedIndexedAccess": true
const users = ["Alice", "Bob"];
console.log(users[0].toUpperCase());
// ❌ Object is possibly 'undefined'
```

**Diagnosis:**
- `noUncheckedIndexedAccess` makes index access return `T | undefined`
- Good for safety, but requires null checks

**Solutions:**

**Solution 1: Add null check**
```typescript
const user = users[0];
if (user) {
  console.log(user.toUpperCase()); // ✅ OK
}
```

**Solution 2: Use optional chaining**
```typescript
console.log(users[0]?.toUpperCase()); // ✅ OK
```

**Solution 3: Use Array methods instead**
```typescript
users.forEach(user => {
  console.log(user.toUpperCase()); // ✅ OK, user is never undefined
});
```

---

### Issue: Cannot use JSX without proper configuration

**Problem:**
```typescript
const element = <div>Hello</div>; // ❌ Cannot use JSX unless the '--jsx' flag is provided
```

**Diagnosis:**
- Missing JSX configuration in tsconfig

**Solutions:**

**Solution 1: Configure JSX for React**
```json
{
  "compilerOptions": {
    "jsx": "react-jsx",
    "jsxImportSource": "react"
  }
}
```

**Solution 2: Use legacy React JSX**
```json
{
  "compilerOptions": {
    "jsx": "react"
  }
}
```

**Solution 3: Preserve JSX for other tools**
```json
{
  "compilerOptions": {
    "jsx": "preserve" // For Next.js, SWC, etc.
  }
}
```

---

## Build Performance Issues

### Issue: TypeScript compilation is slow

**Problem:**
`tsc` takes 30+ seconds on medium-sized project.

**Diagnosis:**
- Inefficient tsconfig settings
- Unnecessary file scanning
- Missing incremental compilation

**Solutions:**

**Solution 1: Enable incremental compilation**
```json
{
  "compilerOptions": {
    "incremental": true,
    "tsBuildInfoFile": ".tsbuildinfo"
  }
}
```

**Solution 2: Use project references for monorepos**
```json
{
  "compilerOptions": {
    "composite": true,
    "declaration": true
  },
  "references": [
    { "path": "../shared" }
  ]
}
```

**Solution 3: Optimize includes/excludes**
```json
{
  "include": ["src/**/*"],
  "exclude": [
    "node_modules",
    "dist",
    "**/*.test.ts",
    "**/*.spec.ts"
  ]
}
```

**Solution 4: Skip lib checking**
```json
{
  "compilerOptions": {
    "skipLibCheck": true // Skip type checking of .d.ts files
  }
}
```

**Solution 5: Use faster alternatives**
- **esbuild**: ~100x faster for bundling
- **swc**: ~20x faster for transpilation
- **Vite**: Uses esbuild for dev builds

---

### Issue: High memory usage during compilation

**Problem:**
TypeScript compiler uses 4GB+ RAM.

**Diagnosis:**
- Large project with many files
- Type checking entire node_modules

**Solutions:**

**Solution 1: Increase Node.js memory**
```bash
node --max-old-space-size=8192 node_modules/.bin/tsc
```

**Solution 2: Use skipLibCheck**
```json
{
  "compilerOptions": {
    "skipLibCheck": true
  }
}
```

**Solution 3: Split into smaller projects**
Use TypeScript project references to split codebase.

---

## Type Compatibility Errors

### Issue: Structural typing allows unexpected assignments

**Problem:**
```typescript
interface User {
  id: string;
  name: string;
}

interface Product {
  id: string;
  name: string;
}

const user: User = { id: "1", name: "Alice" };
const product: Product = user; // ✅ No error, but conceptually wrong
```

**Diagnosis:**
- TypeScript uses structural typing (duck typing)
- Two interfaces with same structure are compatible

**Solutions:**

**Solution 1: Nominal typing with branding**
```typescript
interface User {
  id: string;
  name: string;
  _brand: "User"; // Nominal brand
}

interface Product {
  id: string;
  name: string;
  _brand: "Product"; // Different brand
}

const user: User = { id: "1", name: "Alice", _brand: "User" };
const product: Product = user; // ❌ Error: brands don't match
```

**Solution 2: Use classes for nominal typing**
```typescript
class User {
  constructor(public id: string, public name: string) {}
}

class Product {
  constructor(public id: string, public name: string) {}
}

const user = new User("1", "Alice");
const product: Product = user; // ❌ Error: different classes
```

---

### Issue: Discriminated union not narrowing

**Problem:**
```typescript
type Result =
  | { success: true; data: string }
  | { success: false; error: string };

function handle(result: Result) {
  if (result.success) {
    console.log(result.data); // ❌ Property 'data' does not exist
  }
}
```

**Diagnosis:**
- `success` property is not a literal type
- TypeScript can't narrow without literal discriminant

**Solutions:**

**Solution 1: Use literal types**
```typescript
type Result =
  | { success: true; data: string }    // Literal true
  | { success: false; error: string }; // Literal false

function handle(result: Result) {
  if (result.success === true) { // Explicit literal check
    console.log(result.data); // ✅ OK
  }
}
```

**Solution 2: Use `as const` in object creation**
```typescript
const successResult = {
  success: true as const,
  data: "Hello"
};
```

---

## Quick Diagnostic Checklist

When encountering TypeScript errors:

1. **Read the full error message** - TypeScript errors are verbose but accurate
2. **Check tsconfig.json** - Many issues stem from configuration
3. **Verify imports** - Ensure correct paths and extensions
4. **Check strictness flags** - Know which strict modes are enabled
5. **Use IDE hover** - See inferred types by hovering in VS Code
6. **Simplify** - Create minimal reproduction to isolate issue
7. **Search TypeScript issues** - Many edge cases documented on GitHub
8. **Check TypeScript version** - Features and behaviors change between versions

---

## Related References

- **[Decision Trees](./decision-trees.md)** - Make better TypeScript design decisions
- **[Configuration](./configuration.md)** - Complete tsconfig.json reference
- **[Advanced Types](./advanced-types.md)** - Deep dive into complex type patterns
- **[Runtime Validation](./runtime-validation.md)** - Zod, TypeBox, Valibot patterns
