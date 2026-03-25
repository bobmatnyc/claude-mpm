# Runtime Validation in TypeScript

Deep patterns for Zod, TypeBox, and Valibot with error handling and integration strategies.

## Library Selection Guide

### Decision Matrix

| Requirement | Best Choice |
|-------------|-------------|
| Full-stack with tRPC | **Zod** |
| OpenAPI/JSON Schema generation | **TypeBox** |
| Edge/serverless (bundle size critical) | **Valibot** |
| Maximum validation speed | **TypeBox** (compiled) |
| Largest ecosystem/integrations | **Zod** |

### Bundle Size Comparison

```
Zod:     ~13.5kB minified
TypeBox: ~8kB minified
Valibot: ~1.4kB minified (tree-shakeable)
```

### Performance Comparison

```
TypeBox (compiled): 10x baseline
Valibot:            2x baseline
Zod:                1x baseline (reference)
```

## Zod Deep Patterns

### Schema Composition

```typescript
import { z } from 'zod';

// Base schemas
const EmailSchema = z.string().email();
const UUIDSchema = z.string().uuid();
const TimestampSchema = z.string().datetime();

// Compose into larger schemas
const BaseEntity = z.object({
  id: UUIDSchema,
  createdAt: TimestampSchema,
  updatedAt: TimestampSchema,
});

const UserSchema = BaseEntity.extend({
  email: EmailSchema,
  name: z.string().min(1).max(100),
  role: z.enum(['admin', 'user', 'guest']),
});

// Infer types
type User = z.infer<typeof UserSchema>;
```

### Transformations

```typescript
// Transform during parsing
const DateSchema = z.string().datetime().transform(s => new Date(s));

// Coercion (convert types)
const NumberFromString = z.coerce.number();
const BooleanFromString = z.coerce.boolean();

// Complex transformation
const APIResponseSchema = z.object({
  data: z.array(z.object({
    id: z.string(),
    created_at: z.string(),
  })),
}).transform(response => ({
  items: response.data.map(item => ({
    id: item.id,
    createdAt: new Date(item.created_at),
  })),
}));
```

### Refinements and Superrefine

```typescript
// Simple refinement
const PasswordSchema = z.string()
  .min(8)
  .refine(
    (val) => /[A-Z]/.test(val),
    { message: 'Must contain uppercase letter' }
  )
  .refine(
    (val) => /[0-9]/.test(val),
    { message: 'Must contain number' }
  );

// Superrefine for multiple errors
const FormSchema = z.object({
  password: z.string(),
  confirmPassword: z.string(),
}).superRefine((data, ctx) => {
  if (data.password !== data.confirmPassword) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Passwords must match',
      path: ['confirmPassword'],
    });
  }
});

// Async refinement
const UniqueEmailSchema = z.string().email().refine(
  async (email) => {
    const exists = await checkEmailExists(email);
    return !exists;
  },
  { message: 'Email already registered' }
);
```

### Discriminated Unions

```typescript
const EventSchema = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('click'),
    x: z.number(),
    y: z.number(),
  }),
  z.object({
    type: z.literal('keypress'),
    key: z.string(),
  }),
  z.object({
    type: z.literal('scroll'),
    direction: z.enum(['up', 'down']),
    delta: z.number(),
  }),
]);

type Event = z.infer<typeof EventSchema>;
```

### Error Handling

```typescript
// Safe parse with detailed errors
function validateUser(input: unknown) {
  const result = UserSchema.safeParse(input);
  
  if (!result.success) {
    // Format errors for API response
    const errors = result.error.issues.map(issue => ({
      field: issue.path.join('.'),
      message: issue.message,
      code: issue.code,
    }));
    return { success: false as const, errors };
  }
  
  return { success: true as const, data: result.data };
}

// Custom error map
const customErrorMap: z.ZodErrorMap = (issue, ctx) => {
  if (issue.code === z.ZodIssueCode.invalid_type) {
    if (issue.expected === 'string') {
      return { message: 'This field must be text' };
    }
  }
  return { message: ctx.defaultError };
};

z.setErrorMap(customErrorMap);
```

### Zod with Forms

```typescript
// React Hook Form integration
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';

const FormSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

type FormData = z.infer<typeof FormSchema>;

function SignupForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(FormSchema),
  });
  
  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('email')} />
      {errors.email && <span>{errors.email.message}</span>}
      {/* ... */}
    </form>
  );
}
```

## TypeBox Deep Patterns

### Schema Definition

```typescript
import { Type, Static } from '@sinclair/typebox';

// Basic types
const StringType = Type.String();
const NumberType = Type.Number();
const BooleanType = Type.Boolean();

// With constraints
const EmailType = Type.String({ format: 'email' });
const PositiveNumber = Type.Number({ minimum: 0 });
const BoundedString = Type.String({ minLength: 1, maxLength: 100 });

// Object schema
const UserSchema = Type.Object({
  id: Type.String({ format: 'uuid' }),
  email: Type.String({ format: 'email' }),
  name: Type.String({ minLength: 1 }),
  age: Type.Optional(Type.Number({ minimum: 0 })),
  role: Type.Union([
    Type.Literal('admin'),
    Type.Literal('user'),
  ]),
});

type User = Static<typeof UserSchema>;
```

### Compiled Validation (10x Speed)

```typescript
import { TypeCompiler } from '@sinclair/typebox/compiler';

const CompiledUser = TypeCompiler.Compile(UserSchema);

// Check (returns boolean)
if (CompiledUser.Check(input)) {
  // input is User
}

// Errors (returns iterator)
const errors = [...CompiledUser.Errors(input)];

// Decode (returns value or throws)
const user = CompiledUser.Decode(input);
```

### JSON Schema Output

```typescript
// TypeBox schemas ARE JSON Schema
const jsonSchema = UserSchema;

console.log(JSON.stringify(jsonSchema, null, 2));
// {
//   "type": "object",
//   "properties": {
//     "id": { "type": "string", "format": "uuid" },
//     "email": { "type": "string", "format": "email" },
//     ...
//   },
//   "required": ["id", "email", "name", "role"]
// }
```

### Fastify Integration

```typescript
import Fastify from 'fastify';
import { Type } from '@sinclair/typebox';
import { TypeBoxTypeProvider } from '@fastify/type-provider-typebox';

const server = Fastify().withTypeProvider<TypeBoxTypeProvider>();

const CreateUserBody = Type.Object({
  email: Type.String({ format: 'email' }),
  name: Type.String(),
});

const UserResponse = Type.Object({
  id: Type.String(),
  email: Type.String(),
  name: Type.String(),
});

server.post('/users', {
  schema: {
    body: CreateUserBody,
    response: { 200: UserResponse },
  },
}, async (request, reply) => {
  // request.body is typed as { email: string; name: string }
  const user = await createUser(request.body);
  return user;
});
```

### Transformations with Value Module

```typescript
import { Value } from '@sinclair/typebox/value';

// Clean extra properties
const cleaned = Value.Clean(UserSchema, input);

// Convert types
const converted = Value.Convert(UserSchema, { age: '25' });
// { age: 25 }

// Default values
const SchemaWithDefaults = Type.Object({
  name: Type.String({ default: 'Anonymous' }),
  count: Type.Number({ default: 0 }),
});

const withDefaults = Value.Default(SchemaWithDefaults, {});
// { name: 'Anonymous', count: 0 }
```

## Valibot Deep Patterns

### Schema Definition

```typescript
import * as v from 'valibot';

// Basic schemas
const StringSchema = v.string();
const NumberSchema = v.number();
const BooleanSchema = v.boolean();

// With validations
const EmailSchema = v.pipe(v.string(), v.email());
const PositiveSchema = v.pipe(v.number(), v.minValue(0));

// Object schema
const UserSchema = v.object({
  id: v.pipe(v.string(), v.uuid()),
  email: v.pipe(v.string(), v.email()),
  name: v.pipe(v.string(), v.minLength(1)),
  age: v.optional(v.pipe(v.number(), v.minValue(0))),
  role: v.union([v.literal('admin'), v.literal('user')]),
});

type User = v.InferOutput<typeof UserSchema>;
```

### Pipe Pattern

```typescript
// Build complex schemas with pipes
const PasswordSchema = v.pipe(
  v.string(),
  v.minLength(8, 'Minimum 8 characters'),
  v.maxLength(100, 'Maximum 100 characters'),
  v.regex(/[A-Z]/, 'Must contain uppercase'),
  v.regex(/[0-9]/, 'Must contain number'),
);

// Transform
const DateSchema = v.pipe(
  v.string(),
  v.isoDateTime(),
  v.transform((s) => new Date(s)),
);
```

### Error Handling

```typescript
// Safe parse
const result = v.safeParse(UserSchema, input);

if (result.success) {
  const user = result.output;
} else {
  const errors = v.flatten(result.issues);
  // { nested: { email: ['Invalid email'] } }
}

// Parse (throws)
try {
  const user = v.parse(UserSchema, input);
} catch (error) {
  if (error instanceof v.ValiError) {
    console.log(error.issues);
  }
}
```

### Tree-Shaking Advantage

```typescript
// Only imports what you use
import { string, email, parse } from 'valibot';

// vs Zod which imports everything
import { z } from 'zod';
```

## Integration Patterns

### API Validation Middleware

```typescript
// Generic validation middleware (works with any library)
import { z } from 'zod';
import { NextResponse } from 'next/server';

function validateBody<T>(schema: z.ZodSchema<T>) {
  return async (request: Request): Promise<T> => {
    const body = await request.json();
    const result = schema.safeParse(body);
    
    if (!result.success) {
      throw new ValidationError(result.error);
    }
    
    return result.data;
  };
}

// Usage in route handler
const CreateUserSchema = z.object({
  email: z.string().email(),
  name: z.string(),
});

export async function POST(request: Request) {
  try {
    const body = await validateBody(CreateUserSchema)(request);
    const user = await createUser(body);
    return NextResponse.json(user);
  } catch (error) {
    if (error instanceof ValidationError) {
      return NextResponse.json(
        { errors: error.format() },
        { status: 400 }
      );
    }
    throw error;
  }
}
```

### Environment Variable Validation

```typescript
import { z } from 'zod';

const envSchema = z.object({
  DATABASE_URL: z.string().url(),
  JWT_SECRET: z.string().min(32),
  NODE_ENV: z.enum(['development', 'production', 'test']),
  PORT: z.coerce.number().default(3000),
});

// Validate at startup
export const env = envSchema.parse(process.env);

// Type-safe environment access
declare global {
  namespace NodeJS {
    interface ProcessEnv extends z.infer<typeof envSchema> {}
  }
}
```

### Database Schema Sync

```typescript
// Shared schema between validation and database
import { z } from 'zod';
import { pgTable, text, timestamp, uuid } from 'drizzle-orm/pg-core';
import { createInsertSchema, createSelectSchema } from 'drizzle-zod';

// Drizzle schema
const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  email: text('email').notNull().unique(),
  name: text('name').notNull(),
  createdAt: timestamp('created_at').defaultNow(),
});

// Auto-generate Zod schemas from Drizzle
const insertUserSchema = createInsertSchema(users, {
  email: z.string().email(),
  name: z.string().min(1).max(100),
});

const selectUserSchema = createSelectSchema(users);

type InsertUser = z.infer<typeof insertUserSchema>;
type User = z.infer<typeof selectUserSchema>;
```

## Best Practices

1. **Define schemas once, derive types** - Never duplicate type definitions
2. **Validate at boundaries** - API routes, form submissions, external data
3. **Use safe parse** - Handle errors gracefully instead of throwing
4. **Compose schemas** - Build complex schemas from simple ones
5. **Test schemas** - Validate edge cases and error messages
6. **Consider bundle size** - Use Valibot for edge/serverless
7. **Use compiled validation** - TypeBox compiler for hot paths
