# Advanced TypeScript Types

Deep patterns for type system mastery: conditional types, mapped types, inference, and recursive types.

## Conditional Types

### Basic Syntax

```typescript
type IsString<T> = T extends string ? true : false;

type A = IsString<string>;  // true
type B = IsString<number>;  // false
```

### Distributive Behavior

Conditional types distribute over unions:

```typescript
type ToArray<T> = T extends unknown ? T[] : never;

type Result = ToArray<string | number>; // string[] | number[]
// NOT (string | number)[]
```

Prevent distribution with tuple wrapping:

```typescript
type ToArrayNonDistributive<T> = [T] extends [unknown] ? T[] : never;

type Result = ToArrayNonDistributive<string | number>; // (string | number)[]
```

### The `infer` Keyword

Extract types from complex structures:

```typescript
// Extract return type
type ReturnOf<T> = T extends (...args: any[]) => infer R ? R : never;

// Extract array element type
type ElementOf<T> = T extends (infer E)[] ? E : never;

// Extract Promise resolution type
type Awaited<T> = T extends Promise<infer U> ? Awaited<U> : T;

// Extract function parameters
type Parameters<T> = T extends (...args: infer P) => any ? P : never;

// Multiple infer positions
type FirstArg<T> = T extends (first: infer F, ...rest: any[]) => any ? F : never;
```

### Practical Conditional Types

```typescript
// Make all properties optional recursively
type DeepPartial<T> = T extends object 
  ? { [K in keyof T]?: DeepPartial<T[K]> }
  : T;

// Make all properties required recursively
type DeepRequired<T> = T extends object
  ? { [K in keyof T]-?: DeepRequired<T[K]> }
  : T;

// Extract only function properties
type FunctionProperties<T> = {
  [K in keyof T]: T[K] extends Function ? K : never
}[keyof T];

// Remove null/undefined from all properties
type NonNullableProperties<T> = {
  [K in keyof T]: NonNullable<T[K]>
};
```

## Mapped Types

### Basic Transformation

```typescript
type Readonly<T> = { readonly [K in keyof T]: T[K] };
type Partial<T> = { [K in keyof T]?: T[K] };
type Required<T> = { [K in keyof T]-?: T[K] };
type Mutable<T> = { -readonly [K in keyof T]: T[K] };
```

### Key Remapping (as clause)

```typescript
// Rename keys
type Getters<T> = {
  [K in keyof T as `get${Capitalize<string & K>}`]: () => T[K]
};

type User = { name: string; age: number };
type UserGetters = Getters<User>;
// { getName: () => string; getAge: () => number }

// Filter keys
type OnlyStrings<T> = {
  [K in keyof T as T[K] extends string ? K : never]: T[K]
};

// Exclude specific keys
type OmitByType<T, U> = {
  [K in keyof T as T[K] extends U ? never : K]: T[K]
};
```

### Combining with Template Literals

```typescript
type EventHandlers<T> = {
  [K in keyof T as `on${Capitalize<string & K>}Change`]: (value: T[K]) => void
};

type Form = { name: string; email: string };
type FormHandlers = EventHandlers<Form>;
// { onNameChange: (value: string) => void; onEmailChange: (value: string) => void }
```

## Template Literal Types

### String Manipulation

```typescript
type Uppercase<S extends string> = intrinsic;
type Lowercase<S extends string> = intrinsic;
type Capitalize<S extends string> = intrinsic;
type Uncapitalize<S extends string> = intrinsic;

// Pattern matching
type ExtractDomain<T extends string> = 
  T extends `${infer Protocol}://${infer Domain}/${infer Path}`
    ? Domain
    : never;

type Domain = ExtractDomain<"https://example.com/path">; // "example.com"
```

### Route Parameter Extraction

```typescript
type ExtractRouteParams<T extends string> = 
  T extends `${string}:${infer Param}/${infer Rest}`
    ? Param | ExtractRouteParams<`/${Rest}`>
    : T extends `${string}:${infer Param}`
      ? Param
      : never;

type Params = ExtractRouteParams<"/users/:userId/posts/:postId">;
// "userId" | "postId"

// Create params object type
type RouteParams<T extends string> = {
  [K in ExtractRouteParams<T>]: string
};

type UserPostParams = RouteParams<"/users/:userId/posts/:postId">;
// { userId: string; postId: string }
```

### Event Name Patterns

```typescript
type EventName<T extends string> = `${T}:${
  | 'start' 
  | 'end' 
  | 'error' 
  | 'progress'
}`;

type FileEvents = EventName<'upload' | 'download'>;
// "upload:start" | "upload:end" | "upload:error" | "upload:progress" | 
// "download:start" | "download:end" | "download:error" | "download:progress"
```

## Recursive Types

### JSON Type

```typescript
type JSONValue = 
  | string 
  | number 
  | boolean 
  | null 
  | JSONValue[] 
  | { [key: string]: JSONValue };
```

### Deep Object Paths

```typescript
type Paths<T, D extends number = 10> = [D] extends [never]
  ? never
  : T extends object
    ? {
        [K in keyof T]-?: K extends string | number
          ? `${K}` | `${K}.${Paths<T[K], Prev[D]>}`
          : never;
      }[keyof T]
    : never;

type Prev = [never, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

type User = {
  name: string;
  address: {
    city: string;
    zip: { code: string };
  };
};

type UserPaths = Paths<User>;
// "name" | "address" | "address.city" | "address.zip" | "address.zip.code"
```

### Get Value by Path

```typescript
type Get<T, P extends string> = P extends `${infer K}.${infer Rest}`
  ? K extends keyof T
    ? Get<T[K], Rest>
    : never
  : P extends keyof T
    ? T[P]
    : never;

type City = Get<User, "address.city">; // string
type ZipCode = Get<User, "address.zip.code">; // string
```

## Utility Type Implementations

### Pick and Omit

```typescript
type Pick<T, K extends keyof T> = { [P in K]: T[P] };
type Omit<T, K extends keyof any> = Pick<T, Exclude<keyof T, K>>;
```

### Record

```typescript
type Record<K extends keyof any, T> = { [P in K]: T };
```

### Extract and Exclude

```typescript
type Extract<T, U> = T extends U ? T : never;
type Exclude<T, U> = T extends U ? never : T;
```

### NonNullable

```typescript
type NonNullable<T> = T & {};
// Or: T extends null | undefined ? never : T;
```

### Parameters and ReturnType

```typescript
type Parameters<T extends (...args: any) => any> = 
  T extends (...args: infer P) => any ? P : never;

type ReturnType<T extends (...args: any) => any> = 
  T extends (...args: any) => infer R ? R : any;
```

## Type Guards

### User-Defined Type Guards

```typescript
function isString(value: unknown): value is string {
  return typeof value === 'string';
}

function isUser(value: unknown): value is User {
  return (
    typeof value === 'object' &&
    value !== null &&
    'id' in value &&
    'email' in value
  );
}

// Assertion functions
function assertIsUser(value: unknown): asserts value is User {
  if (!isUser(value)) {
    throw new Error('Not a user');
  }
}
```

### Narrowing Patterns

```typescript
// typeof narrowing
function process(value: string | number) {
  if (typeof value === 'string') {
    return value.toUpperCase(); // value is string
  }
  return value.toFixed(2); // value is number
}

// instanceof narrowing
function handleError(error: Error | string) {
  if (error instanceof Error) {
    return error.message;
  }
  return error;
}

// in operator narrowing
type Fish = { swim: () => void };
type Bird = { fly: () => void };

function move(animal: Fish | Bird) {
  if ('swim' in animal) {
    animal.swim();
  } else {
    animal.fly();
  }
}
```

## Variance Annotations

TypeScript 4.7+ supports explicit variance:

```typescript
// Covariant (output position) - use `out`
interface Producer<out T> {
  produce(): T;
}

// Contravariant (input position) - use `in`
interface Consumer<in T> {
  consume(value: T): void;
}

// Invariant - use both
interface Processor<in out T> {
  process(value: T): T;
}
```

## Best Practices

1. **Prefer `unknown` over `any`** for truly unknown types
2. **Use type guards** instead of type assertions
3. **Leverage inference** - let TypeScript infer when possible
4. **Add constraints** to generics for better error messages
5. **Document complex types** with JSDoc comments
6. **Test utility types** with type-level tests using `Expect<Equal<A, B>>`
