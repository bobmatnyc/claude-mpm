# Advanced TypeScript Patterns (2025)

Modern TypeScript 5.2+ patterns including explicit resource management, stable decorators, and type-level programming.

## Explicit Resource Management (TS 5.2+)

The `using` keyword provides automatic resource disposal, replacing manual cleanup patterns.

### Basic Pattern

```typescript
// Disposable resource interface
interface Disposable {
  [Symbol.dispose](): void;
}

// File handle with automatic cleanup
class FileHandle implements Disposable {
  constructor(private path: string) {
    console.log(`Opening ${path}`);
  }

  write(data: string): void {
    console.log(`Writing to ${this.path}: ${data}`);
  }

  [Symbol.dispose](): void {
    console.log(`Closing ${this.path}`);
  }
}

// Automatic disposal at scope end
function processFile() {
  using file = new FileHandle("data.txt");
  file.write("Hello");
  // File automatically closed here, even if exception thrown
}
```

### Async Resource Management

```typescript
interface AsyncDisposable {
  [Symbol.asyncDispose](): Promise<void>;
}

class DatabaseConnection implements AsyncDisposable {
  constructor(private connectionString: string) {}

  async query(sql: string): Promise<any[]> {
    // Execute query
    return [];
  }

  async [Symbol.asyncDispose](): Promise<void> {
    console.log("Closing database connection");
    // Async cleanup
  }
}

async function queryDatabase() {
  await using db = new DatabaseConnection("postgres://...");
  const results = await db.query("SELECT * FROM users");
  // Connection automatically closed here
  return results;
}
```

### Multiple Resources

```typescript
async function processWithMultipleResources() {
  await using db = new DatabaseConnection("postgres://...");
  await using cache = new RedisConnection("redis://...");
  using file = new FileHandle("output.txt");
  
  // Use all resources
  const data = await db.query("SELECT * FROM users");
  await cache.set("users", data);
  file.write(JSON.stringify(data));
  
  // All disposed in reverse order: file, cache, db
}
```

### Real-World Pattern: Transaction Management

```typescript
class Transaction implements AsyncDisposable {
  constructor(private db: Database) {
    this.db.beginTransaction();
  }

  async commit(): Promise<void> {
    await this.db.commit();
  }

  async rollback(): Promise<void> {
    await this.db.rollback();
  }

  async [Symbol.asyncDispose](): Promise<void> {
    // Auto-rollback if not committed
    if (!this.committed) {
      await this.rollback();
    }
  }

  private committed = false;
}

async function transferFunds(from: string, to: string, amount: number) {
  await using tx = new Transaction(db);
  
  await db.debit(from, amount);
  await db.credit(to, amount);
  
  await tx.commit();
  // Auto-rollback if any error occurs before commit
}
```

## Stable Decorators (TS 5.0+)

TypeScript 5.0 ships stable decorators aligned with the TC39 proposal.

### Method Decorators

```typescript
// Logging decorator
function log(
  target: any,
  propertyKey: string,
  descriptor: PropertyDescriptor
) {
  const original = descriptor.value;
  
  descriptor.value = async function(...args: any[]) {
    console.log(`[${propertyKey}] Called with:`, args);
    const result = await original.apply(this, args);
    console.log(`[${propertyKey}] Returned:`, result);
    return result;
  };
  
  return descriptor;
}

class UserService {
  @log
  async createUser(email: string, name: string) {
    return { id: 123, email, name };
  }
}
```

### Class Decorators

```typescript
// Singleton decorator
function singleton<T extends { new(...args: any[]): {} }>(constructor: T) {
  return class extends constructor {
    private static instance: any;
    
    constructor(...args: any[]) {
      if ((constructor as any).instance) {
        return (constructor as any).instance;
      }
      super(...args);
      (constructor as any).instance = this;
    }
  };
}

@singleton
class DatabasePool {
  constructor(public connectionString: string) {
    console.log("Pool created");
  }
}

const pool1 = new DatabasePool("postgres://...");
const pool2 = new DatabasePool("postgres://...");
console.log(pool1 === pool2); // true
```

### Property Decorators with Metadata

```typescript
// Validation decorator
function validate(rules: { min?: number; max?: number; pattern?: RegExp }) {
  return function(target: any, propertyKey: string) {
    let value: any;
    
    Object.defineProperty(target, propertyKey, {
      get() { return value; },
      set(newValue: any) {
        if (rules.min !== undefined && newValue < rules.min) {
          throw new Error(`${propertyKey} must be >= ${rules.min}`);
        }
        if (rules.max !== undefined && newValue > rules.max) {
          throw new Error(`${propertyKey} must be <= ${rules.max}`);
        }
        if (rules.pattern && !rules.pattern.test(newValue)) {
          throw new Error(`${propertyKey} must match ${rules.pattern}`);
        }
        value = newValue;
      }
    });
  };
}

class User {
  @validate({ min: 0, max: 120 })
  age!: number;
  
  @validate({ pattern: /^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/i })
  email!: string;
}

const user = new User();
user.age = 25;     // ✅ Valid
user.age = 150;    // ❌ Error: age must be <= 120
```

### Decorator Factory Pattern

```typescript
function retry(maxAttempts: number, delayMs: number) {
  return function(
    target: any,
    propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const original = descriptor.value;
    
    descriptor.value = async function(...args: any[]) {
      let lastError: Error;
      
      for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        try {
          return await original.apply(this, args);
        } catch (error) {
          lastError = error as Error;
          if (attempt < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, delayMs));
          }
        }
      }
      
      throw lastError!;
    };
    
    return descriptor;
  };
}

class ApiClient {
  @retry(3, 1000)
  async fetchUser(id: string) {
    const response = await fetch(`/api/users/${id}`);
    if (!response.ok) throw new Error("Fetch failed");
    return response.json();
  }
}
```

## Import Type Behavior (TS 5.0+)

TypeScript 5.0 changes how type imports work with `verbatimModuleSyntax`.

### Type-Only Imports

```typescript
// Type-only import (erased at runtime)
import type { User } from "./types";

// Regular import (kept at runtime)
import { createUser } from "./user";

// Mixed import (AVOID - use separate imports)
import { type User, createUser } from "./user";
```

### verbatimModuleSyntax Enforcement

```json
// tsconfig.json
{
  "compilerOptions": {
    "verbatimModuleSyntax": true  // Enforces explicit type imports
  }
}
```

With this option:
```typescript
// ❌ ERROR with verbatimModuleSyntax
import { User } from "./types";  // User is only a type

// ✅ CORRECT
import type { User } from "./types";

// ✅ CORRECT for values
import { createUser } from "./user";
```

### Type-Only Exports

```typescript
// types.ts
export type User = {
  id: string;
  name: string;
};

export type { User as UserType };  // Re-export as type-only

// ❌ ERROR - can't export type as value
export { User };  // Fails with verbatimModuleSyntax
```

## Satisfies with Generics

Advanced `satisfies` patterns for type narrowing with generics.

### Generic Constraint with Inference

```typescript
function createTypedConfig<const T extends Record<string, unknown>>(
  config: T
): T {
  return config;
}

const config = createTypedConfig({
  api: {
    baseUrl: "https://api.example.com",
    timeout: 5000
  },
  features: {
    darkMode: true,
    betaAccess: false
  }
} satisfies Record<string, unknown>);

// Inferred type preserves literals:
config.api.baseUrl;  // Type: "https://api.example.com"
config.api.timeout;  // Type: 5000
```

### Builder Pattern with Satisfies

```typescript
type QueryBuilder<T> = {
  where: (condition: Partial<T>) => QueryBuilder<T>;
  select: <K extends keyof T>(...keys: K[]) => QueryBuilder<Pick<T, K>>;
  execute: () => Promise<T[]>;
};

function query<T>(): QueryBuilder<T> {
  return {
    where: (condition) => query<T>(),
    select: (...keys) => query() as any,
    execute: async () => []
  } satisfies QueryBuilder<T>;
}

type User = { id: string; name: string; email: string };

const users = await query<User>()
  .where({ name: "Alice" })
  .select("id", "email")
  .execute();

// Type: Pick<User, "id" | "email">[]
```

### Branded Types with Satisfies

```typescript
type Brand<T, B> = T & { __brand: B };
type UserId = Brand<string, "UserId">;
type Email = Brand<string, "Email">;

function createUserId(id: string): UserId {
  return id as UserId;
}

function createEmail(email: string): Email {
  if (!email.includes("@")) {
    throw new Error("Invalid email");
  }
  return email as Email;
}

// Use satisfies to ensure correct brand
const userId = createUserId("user-123") satisfies UserId;
const email = createEmail("user@example.com") satisfies Email;

// ❌ Type error - can't assign Email to UserId
const wrongType: UserId = email;
```

## Type-Level Programming

Advanced compile-time computation with TypeScript's type system.

### Recursive Type Utilities

```typescript
// Deep readonly
type DeepReadonly<T> = {
  readonly [P in keyof T]: T[P] extends object
    ? DeepReadonly<T[P]>
    : T[P];
};

// Deep partial
type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object
    ? DeepPartial<T[P]>
    : T[P];
};

// Deep required
type DeepRequired<T> = {
  [P in keyof T]-?: T[P] extends object
    ? DeepRequired<T[P]>
    : T[P];
};
```

### String Manipulation Types

```typescript
// Convert string to camelCase
type CamelCase<S extends string> = 
  S extends `${infer First}_${infer Rest}`
    ? `${Lowercase<First>}${Capitalize<CamelCase<Rest>>}`
    : Lowercase<S>;

type Test1 = CamelCase<"user_name">;  // "userName"
type Test2 = CamelCase<"api_base_url">;  // "apiBaseUrl"

// Extract path parameters
type ExtractPathParams<T extends string> = 
  T extends `${infer Start}:${infer Param}/${infer Rest}`
    ? { [K in Param | keyof ExtractPathParams<Rest>]: string }
    : T extends `${infer Start}:${infer Param}`
      ? { [K in Param]: string }
      : {};

type Params = ExtractPathParams<"/users/:userId/posts/:postId">;
// { userId: string; postId: string }
```

### Conditional Type Inference

```typescript
// Unwrap Promise type
type Awaited<T> = 
  T extends Promise<infer U> ? Awaited<U> : T;

type Test1 = Awaited<Promise<string>>;  // string
type Test2 = Awaited<Promise<Promise<number>>>;  // number

// Extract function return type
type ReturnTypeOf<T> = 
  T extends (...args: any[]) => infer R ? R : never;

async function fetchUser() { return { id: 1, name: "Alice" }; }
type User = Awaited<ReturnTypeOf<typeof fetchUser>>;
// { id: number; name: string }
```

## When to Use These Patterns

### Use `using` When:
- Managing file handles, database connections, locks
- Implementing transactional logic
- Ensuring cleanup even with exceptions
- Working with Node.js streams

### Use Decorators When:
- Cross-cutting concerns (logging, validation, caching)
- Framework integration (NestJS, TypeORM)
- Metadata-driven programming
- AOP (Aspect-Oriented Programming) patterns

### Use `satisfies` with Generics When:
- Building type-safe builders/fluent APIs
- Creating branded types
- Narrowing types while preserving literals
- Library API design requiring inference

### Use Type-Level Programming When:
- Building utility type libraries
- Transforming API types automatically
- Generating types from runtime values
- Advanced generic constraints

## Red Flags

Stop and reconsider if:
- Using `using` for non-resource objects (just use regular cleanup)
- Creating decorators without understanding execution order
- Over-engineering with type-level programming (keep it simple)
- Using branded types without validation functions
- Type utilities so complex that error messages are unreadable
