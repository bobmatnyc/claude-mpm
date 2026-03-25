# GraphQL Patterns - Deep Dive

Advanced GraphQL schema design, resolver optimization, subscriptions, federation, and production best practices.

## Schema Design Best Practices

### Type System Fundamentals

**Scalar Types**:
```graphql
type User {
  id: ID!              # Unique identifier
  email: String!       # Required string
  age: Int             # Optional integer
  balance: Float       # Optional float
  isActive: Boolean!   # Required boolean
}
```

**Custom Scalars**:
```graphql
scalar DateTime
scalar URL
scalar EmailAddress
scalar JSON

type Post {
  id: ID!
  publishedAt: DateTime!
  website: URL
  content: JSON
}
```

**Implementation** (GraphQL Scalars library):
```typescript
import { DateTimeResolver, URLResolver, EmailAddressResolver, JSONResolver } from 'graphql-scalars';

const resolvers = {
  DateTime: DateTimeResolver,
  URL: URLResolver,
  EmailAddress: EmailAddressResolver,
  JSON: JSONResolver,
};
```

### Object Types and Interfaces

**Interface** (shared fields):
```graphql
interface Node {
  id: ID!
  createdAt: DateTime!
  updatedAt: DateTime!
}

type User implements Node {
  id: ID!
  createdAt: DateTime!
  updatedAt: DateTime!
  email: String!
  name: String
}

type Post implements Node {
  id: ID!
  createdAt: DateTime!
  updatedAt: DateTime!
  title: String!
  content: String!
  author: User!
}
```

**Query interface implementations**:
```graphql
query {
  node(id: "123") {
    id
    ... on User {
      email
      name
    }
    ... on Post {
      title
      author { name }
    }
  }
}
```

### Union Types

```graphql
union SearchResult = User | Post | Comment

type Query {
  search(query: String!): [SearchResult!]!
}
```

**Query with fragments**:
```graphql
query {
  search(query: "graphql") {
    ... on User {
      id
      name
      email
    }
    ... on Post {
      id
      title
      content
    }
    ... on Comment {
      id
      text
      author { name }
    }
  }
}
```

### Enums

```graphql
enum UserRole {
  ADMIN
  MODERATOR
  USER
  GUEST
}

enum OrderStatus {
  PENDING
  PROCESSING
  SHIPPED
  DELIVERED
  CANCELLED
}

type User {
  id: ID!
  role: UserRole!
  orders: [Order!]!
}

type Order {
  id: ID!
  status: OrderStatus!
}
```

### Input Types

```graphql
input CreateUserInput {
  email: String!
  name: String
  role: UserRole = USER  # Default value
}

input UpdateUserInput {
  email: String
  name: String
  role: UserRole
}

input UserFilterInput {
  role: UserRole
  isActive: Boolean
  createdAfter: DateTime
}

type Mutation {
  createUser(input: CreateUserInput!): User!
  updateUser(id: ID!, input: UpdateUserInput!): User!
}

type Query {
  users(filter: UserFilterInput): [User!]!
}
```

### Nullable vs Non-Null Fields

**Design philosophy**: Nullable by default, non-null where guaranteed

✅ **Good: Defensive nullability**
```graphql
type User {
  id: ID!                 # Always present
  email: String!          # Required, validated
  name: String            # Optional (nullable)
  profile: Profile        # May not exist
  posts: [Post!]!         # Array never null, posts never null
  # Can return empty array []
}
```

❌ **Bad: Over-promising with non-null**
```graphql
type User {
  id: ID!
  email: String!
  lastLoginAt: DateTime!  # What if never logged in?
  favoritePost: Post!     # What if no favorite?
  # Breaking change if needs to be nullable later
}
```

**Nullability rules**:
- `String`: Nullable string
- `String!`: Non-null string
- `[String]`: Nullable array of nullable strings
- `[String!]`: Nullable array of non-null strings
- `[String!]!`: Non-null array of non-null strings
- `[String]!`: Non-null array of nullable strings

## Resolver Patterns

### Basic Resolvers

```typescript
const resolvers = {
  Query: {
    user: async (_parent, { id }, context) => {
      return context.db.users.findUnique({ where: { id } });
    },
    users: async (_parent, { filter }, context) => {
      return context.db.users.findMany({ where: filter });
    },
  },

  User: {
    // Field resolver (computed field)
    fullName: (user) => `${user.firstName} ${user.lastName}`,

    // Async field resolver (database fetch)
    posts: async (user, _args, context) => {
      return context.db.posts.findMany({ where: { authorId: user.id } });
    },
  },

  Mutation: {
    createUser: async (_parent, { input }, context) => {
      return context.db.users.create({ data: input });
    },
  },
};
```

### DataLoader (N+1 Solution)

**Problem**: N+1 query pattern
```typescript
// BAD: Triggers separate query for each user's posts
const resolvers = {
  User: {
    posts: async (user, _args, context) => {
      // Called once PER user in result set
      return context.db.posts.findMany({ where: { authorId: user.id } });
    },
  },
};

// Query for 100 users = 1 query + 100 queries for posts = 101 queries!
```

**Solution**: DataLoader batches requests
```typescript
import DataLoader from 'dataloader';

// Create loader in context (per-request)
const createLoaders = (db) => ({
  postsLoader: new DataLoader(async (userIds: string[]) => {
    // Single query for all users
    const posts = await db.posts.findMany({
      where: { authorId: { in: userIds } },
    });

    // Group by userId
    const postsByUser = userIds.map(userId =>
      posts.filter(post => post.authorId === userId)
    );

    return postsByUser;
  }),

  userLoader: new DataLoader(async (userIds: string[]) => {
    const users = await db.users.findMany({
      where: { id: { in: userIds } },
    });

    // Maintain order matching userIds
    return userIds.map(id => users.find(user => user.id === id));
  }),
});

// Context setup
const context = ({ req }) => ({
  db: prisma,
  loaders: createLoaders(prisma),
  userId: req.userId,
});

// Resolver using DataLoader
const resolvers = {
  User: {
    posts: (user, _args, context) => {
      return context.loaders.postsLoader.load(user.id);
    },
  },
  Post: {
    author: (post, _args, context) => {
      return context.loaders.userLoader.load(post.authorId);
    },
  },
};

// Query for 100 users = 1 query + 1 batched query for posts = 2 queries!
```

### Resolver Chain and Parent

```typescript
const resolvers = {
  Query: {
    user: async (_parent, { id }, context) => {
      // Returns user object passed to User resolvers
      return context.db.users.findUnique({ where: { id } });
    },
  },

  User: {
    // parent is the user object from Query.user
    fullName: (parent) => `${parent.firstName} ${parent.lastName}`,

    // Can access parent fields
    posts: async (parent, _args, context) => {
      return context.db.posts.findMany({
        where: { authorId: parent.id },
      });
    },

    // Nested resolver chain
    profile: async (parent, _args, context) => {
      // Returns profile object passed to Profile resolvers
      return context.db.profiles.findUnique({
        where: { userId: parent.id },
      });
    },
  },

  Profile: {
    // parent is the profile object from User.profile
    avatarUrl: (parent) => {
      return parent.avatar
        ? `https://cdn.example.com/${parent.avatar}`
        : 'https://cdn.example.com/default-avatar.png';
    },
  },
};
```

### Error Handling

```typescript
import { GraphQLError } from 'graphql';

const resolvers = {
  Query: {
    user: async (_parent, { id }, context) => {
      const user = await context.db.users.findUnique({ where: { id } });

      if (!user) {
        throw new GraphQLError('User not found', {
          extensions: {
            code: 'NOT_FOUND',
            argumentName: 'id',
          },
        });
      }

      return user;
    },
  },

  Mutation: {
    createUser: async (_parent, { input }, context) => {
      // Validation error
      if (!input.email.includes('@')) {
        throw new GraphQLError('Invalid email format', {
          extensions: {
            code: 'INVALID_INPUT',
            field: 'email',
          },
        });
      }

      try {
        return await context.db.users.create({ data: input });
      } catch (error) {
        // Database unique constraint
        if (error.code === 'P2002') {
          throw new GraphQLError('Email already exists', {
            extensions: {
              code: 'DUPLICATE_EMAIL',
              field: 'email',
            },
          });
        }

        // Unexpected error
        throw new GraphQLError('Failed to create user', {
          extensions: {
            code: 'INTERNAL_ERROR',
          },
        });
      }
    },
  },
};
```

**Error response**:
```json
{
  "errors": [
    {
      "message": "User not found",
      "locations": [{ "line": 2, "column": 3 }],
      "path": ["user"],
      "extensions": {
        "code": "NOT_FOUND",
        "argumentName": "id"
      }
    }
  ],
  "data": {
    "user": null
  }
}
```

## Pagination Patterns

### Offset Pagination (Simple)

```graphql
type Query {
  users(limit: Int = 10, offset: Int = 0): UserConnection!
}

type UserConnection {
  nodes: [User!]!
  totalCount: Int!
  pageInfo: PageInfo!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
}
```

**Resolver**:
```typescript
const resolvers = {
  Query: {
    users: async (_parent, { limit, offset }, context) => {
      const [nodes, totalCount] = await Promise.all([
        context.db.users.findMany({ take: limit, skip: offset }),
        context.db.users.count(),
      ]);

      return {
        nodes,
        totalCount,
        pageInfo: {
          hasNextPage: offset + limit < totalCount,
          hasPreviousPage: offset > 0,
        },
      };
    },
  },
};
```

### Cursor Pagination (Relay Connection)

**Schema**:
```graphql
type Query {
  users(first: Int, after: String, last: Int, before: String): UserConnection!
}

type UserConnection {
  edges: [UserEdge!]!
  nodes: [User!]!
  pageInfo: PageInfo!
  totalCount: Int!
}

type UserEdge {
  cursor: String!
  node: User!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}
```

**Resolver** (using graphql-relay):
```typescript
import { connectionFromArraySlice, cursorToOffset } from 'graphql-relay';

const resolvers = {
  Query: {
    users: async (_parent, args, context) => {
      const { first, after, last, before } = args;

      // Decode cursors to offsets
      const afterOffset = after ? cursorToOffset(after) + 1 : 0;
      const beforeOffset = before ? cursorToOffset(before) : undefined;

      // Calculate limit and offset
      const limit = first || last || 10;
      const offset = afterOffset;

      // Fetch data
      const [users, totalCount] = await Promise.all([
        context.db.users.findMany({
          take: limit + 1, // Fetch one extra to check hasNextPage
          skip: offset,
        }),
        context.db.users.count(),
      ]);

      // Build connection
      const hasNextPage = users.length > limit;
      const nodes = hasNextPage ? users.slice(0, -1) : users;

      return connectionFromArraySlice(nodes, args, {
        sliceStart: offset,
        arrayLength: totalCount,
      });
    },
  },
};
```

**Query**:
```graphql
query {
  users(first: 10, after: "cursor123") {
    edges {
      cursor
      node {
        id
        name
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

## Mutations

### Input Object Pattern

✅ **Good: Single input object**
```graphql
input CreatePostInput {
  title: String!
  content: String!
  tags: [String!]
  publishedAt: DateTime
}

type Mutation {
  createPost(input: CreatePostInput!): CreatePostPayload!
}
```

❌ **Bad: Multiple arguments**
```graphql
type Mutation {
  createPost(
    title: String!
    content: String!
    tags: [String!]
    publishedAt: DateTime
  ): Post!
}
```

### Payload Object Pattern

**Include user errors and edge for optimistic updates**:
```graphql
type CreatePostPayload {
  post: Post
  postEdge: PostEdge
  errors: [UserError!]
  clientMutationId: String
}

type UserError {
  message: String!
  field: String
  code: String!
}

type PostEdge {
  cursor: String!
  node: Post!
}

type Mutation {
  createPost(input: CreatePostInput!): CreatePostPayload!
}
```

**Resolver**:
```typescript
const resolvers = {
  Mutation: {
    createPost: async (_parent, { input }, context) => {
      // Validation
      const errors = [];
      if (input.title.length < 3) {
        errors.push({
          message: 'Title must be at least 3 characters',
          field: 'title',
          code: 'TITLE_TOO_SHORT',
        });
      }

      if (errors.length > 0) {
        return { post: null, postEdge: null, errors };
      }

      // Create post
      const post = await context.db.posts.create({
        data: {
          ...input,
          authorId: context.userId,
        },
      });

      return {
        post,
        postEdge: {
          cursor: encodeCursor(post.id),
          node: post,
        },
        errors: [],
      };
    },
  },
};
```

### Optimistic Updates (Client)

```typescript
const [createPost] = useMutation(CREATE_POST, {
  optimisticResponse: {
    createPost: {
      __typename: 'CreatePostPayload',
      post: {
        __typename: 'Post',
        id: 'temp-id',
        title: variables.input.title,
        content: variables.input.content,
        createdAt: new Date().toISOString(),
      },
      errors: [],
    },
  },
  update: (cache, { data }) => {
    // Update cache with new post
    const existing = cache.readQuery({ query: GET_POSTS });
    cache.writeQuery({
      query: GET_POSTS,
      data: {
        posts: {
          ...existing.posts,
          edges: [
            data.createPost.postEdge,
            ...existing.posts.edges,
          ],
        },
      },
    });
  },
});
```

## Subscriptions (Real-Time)

### Schema

```graphql
type Subscription {
  postAdded: Post!
  postUpdated(id: ID!): Post!
  commentAdded(postId: ID!): Comment!
  userStatusChanged(userId: ID!): UserStatus!
}

type UserStatus {
  userId: ID!
  isOnline: Boolean!
  lastSeen: DateTime
}
```

### Resolver (with PubSub)

```typescript
import { PubSub } from 'graphql-subscriptions';

const pubsub = new PubSub();

const resolvers = {
  Subscription: {
    postAdded: {
      subscribe: () => pubsub.asyncIterator(['POST_ADDED']),
    },

    postUpdated: {
      subscribe: (_parent, { id }) => {
        return pubsub.asyncIterator([`POST_UPDATED_${id}`]);
      },
    },

    commentAdded: {
      subscribe: (_parent, { postId }, context) => {
        // Auth check
        if (!context.userId) {
          throw new GraphQLError('Unauthorized');
        }
        return pubsub.asyncIterator([`COMMENT_ADDED_${postId}`]);
      },
      // Optional resolve function
      resolve: (payload) => payload.comment,
    },
  },

  Mutation: {
    createPost: async (_parent, { input }, context) => {
      const post = await context.db.posts.create({ data: input });

      // Trigger subscription
      pubsub.publish('POST_ADDED', { postAdded: post });

      return { post };
    },

    updatePost: async (_parent, { id, input }, context) => {
      const post = await context.db.posts.update({
        where: { id },
        data: input,
      });

      pubsub.publish(`POST_UPDATED_${id}`, { postUpdated: post });

      return { post };
    },
  },
};
```

### Redis PubSub (Production)

```typescript
import { RedisPubSub } from 'graphql-redis-subscriptions';
import Redis from 'ioredis';

const options = {
  host: process.env.REDIS_HOST,
  port: process.env.REDIS_PORT,
  retryStrategy: (times) => Math.min(times * 50, 2000),
};

const pubsub = new RedisPubSub({
  publisher: new Redis(options),
  subscriber: new Redis(options),
});
```

### WebSocket Setup (Apollo Server)

```typescript
import { ApolloServer } from '@apollo/server';
import { expressMiddleware } from '@apollo/server/express4';
import { ApolloServerPluginDrainHttpServer } from '@apollo/server/plugin/drainHttpServer';
import { createServer } from 'http';
import { WebSocketServer } from 'ws';
import { useServer } from 'graphql-ws/lib/use/ws';
import { makeExecutableSchema } from '@graphql-tools/schema';
import express from 'express';

const schema = makeExecutableSchema({ typeDefs, resolvers });
const app = express();
const httpServer = createServer(app);

// WebSocket server
const wsServer = new WebSocketServer({
  server: httpServer,
  path: '/graphql',
});

const serverCleanup = useServer({ schema }, wsServer);

// Apollo Server
const server = new ApolloServer({
  schema,
  plugins: [
    ApolloServerPluginDrainHttpServer({ httpServer }),
    {
      async serverWillStart() {
        return {
          async drainServer() {
            await serverCleanup.dispose();
          },
        };
      },
    },
  ],
});

await server.start();

app.use('/graphql', express.json(), expressMiddleware(server));

httpServer.listen(4000);
```

### Client Subscription (Apollo Client)

```typescript
import { useSubscription } from '@apollo/client';

const POST_ADDED = gql`
  subscription OnPostAdded {
    postAdded {
      id
      title
      author { name }
    }
  }
`;

function RecentPosts() {
  const { data, loading } = useSubscription(POST_ADDED, {
    onData: ({ client, data }) => {
      // Update cache
      client.cache.modify({
        fields: {
          posts: (existing) => ({
            ...existing,
            edges: [
              { node: data.postAdded, cursor: '' },
              ...existing.edges,
            ],
          }),
        },
      });
    },
  });

  return <div>New post: {data?.postAdded.title}</div>;
}
```

## Directives

### Built-in Directives

```graphql
query GetUser($includeEmail: Boolean!, $skipProfile: Boolean!) {
  user(id: "123") {
    id
    name
    email @include(if: $includeEmail)
    profile @skip(if: $skipProfile) {
      bio
    }
  }
}
```

### Custom Directives

**Schema**:
```graphql
directive @auth(requires: UserRole!) on FIELD_DEFINITION
directive @deprecated(reason: String) on FIELD_DEFINITION
directive @length(min: Int, max: Int) on INPUT_FIELD_DEFINITION

type Query {
  users: [User!]! @auth(requires: ADMIN)
  me: User!
}

type User {
  id: ID!
  email: String! @deprecated(reason: "Use contactEmail instead")
  contactEmail: String!
}

input CreateUserInput {
  name: String! @length(min: 3, max: 50)
  email: String!
}
```

**Implementation** (using graphql-tools):
```typescript
import { mapSchema, getDirective, MapperKind } from '@graphql-tools/utils';

function authDirective(schema, directiveName) {
  return mapSchema(schema, {
    [MapperKind.OBJECT_FIELD]: (fieldConfig) => {
      const authDirective = getDirective(schema, fieldConfig, directiveName)?.[0];

      if (authDirective) {
        const { requires } = authDirective;
        const { resolve = defaultFieldResolver } = fieldConfig;

        fieldConfig.resolve = async (source, args, context, info) => {
          if (!context.user || context.user.role !== requires) {
            throw new GraphQLError('Unauthorized', {
              extensions: { code: 'FORBIDDEN' },
            });
          }

          return resolve(source, args, context, info);
        };
      }

      return fieldConfig;
    },
  });
}

let schema = makeExecutableSchema({ typeDefs, resolvers });
schema = authDirective(schema, 'auth');
```

## Performance Optimization

### Query Complexity Analysis

```typescript
import { createComplexityLimitRule } from 'graphql-validation-complexity';

const server = new ApolloServer({
  schema,
  validationRules: [
    createComplexityLimitRule(1000, {
      scalarCost: 1,
      objectCost: 10,
      listFactor: 10,
      introspectionListFactor: 10,
      onCost: (cost) => {
        console.log('Query cost:', cost);
      },
    }),
  ],
});
```

**Custom cost per field**:
```typescript
const typeDefs = gql`
  type Query {
    users: [User!]! @cost(complexity: 100)
    expensiveAnalytics: Analytics! @cost(complexity: 500)
  }
`;
```

### Query Depth Limiting

```typescript
import depthLimit from 'graphql-depth-limit';

const server = new ApolloServer({
  schema,
  validationRules: [depthLimit(10)],
});
```

### Persisted Queries

**Benefits**: Reduce payload size, prevent arbitrary queries in production

```typescript
import { ApolloServer } from '@apollo/server';

const server = new ApolloServer({
  schema,
  persistedQueries: {
    cache: new Map(), // Use Redis in production
  },
  allowBatchedHttpRequests: false,
  introspection: process.env.NODE_ENV !== 'production',
});
```

**Client sends hash**:
```http
POST /graphql
{
  "extensions": {
    "persistedQuery": {
      "version": 1,
      "sha256Hash": "abc123..."
    }
  }
}
```

### Response Caching

**HTTP caching**:
```typescript
import responseCachePlugin from '@apollo/server-plugin-response-cache';

const server = new ApolloServer({
  schema,
  plugins: [
    responseCachePlugin({
      sessionId: (context) => context.user?.id || null,
    }),
  ],
});
```

**Cache hints**:
```graphql
type Query {
  user(id: ID!): User @cacheControl(maxAge: 60, scope: PRIVATE)
  publicPosts: [Post!]! @cacheControl(maxAge: 300, scope: PUBLIC)
}
```

## Schema Stitching and Federation

### Apollo Federation

**Service 1 (Users)**:
```graphql
type User @key(fields: "id") {
  id: ID!
  email: String!
  name: String
}

extend type Query {
  user(id: ID!): User
}
```

**Service 2 (Posts)**:
```graphql
type Post @key(fields: "id") {
  id: ID!
  title: String!
  author: User!
}

extend type User @key(fields: "id") {
  id: ID! @external
  posts: [Post!]!
}

extend type Query {
  posts: [Post!]!
}
```

**Gateway**:
```typescript
import { ApolloGateway, IntrospectAndCompose } from '@apollo/gateway';
import { ApolloServer } from '@apollo/server';

const gateway = new ApolloGateway({
  supergraphSdl: new IntrospectAndCompose({
    subgraphs: [
      { name: 'users', url: 'http://localhost:4001/graphql' },
      { name: 'posts', url: 'http://localhost:4002/graphql' },
    ],
  }),
});

const server = new ApolloServer({ gateway });
```

## Testing

### Unit Testing Resolvers

```typescript
import { resolvers } from './resolvers';

describe('User Resolvers', () => {
  it('fetches user by ID', async () => {
    const mockDb = {
      users: {
        findUnique: jest.fn().mockResolvedValue({
          id: '123',
          email: 'test@example.com',
        }),
      },
    };

    const result = await resolvers.Query.user(
      {},
      { id: '123' },
      { db: mockDb }
    );

    expect(mockDb.users.findUnique).toHaveBeenCalledWith({
      where: { id: '123' },
    });
    expect(result).toEqual({
      id: '123',
      email: 'test@example.com',
    });
  });
});
```

### Integration Testing

```typescript
import { ApolloServer } from '@apollo/server';

const server = new ApolloServer({ typeDefs, resolvers });

it('creates a user', async () => {
  const response = await server.executeOperation({
    query: `
      mutation CreateUser($input: CreateUserInput!) {
        createUser(input: $input) {
          user {
            id
            email
          }
          errors {
            message
          }
        }
      }
    `,
    variables: {
      input: {
        email: 'test@example.com',
        name: 'Test User',
      },
    },
  });

  expect(response.body.kind).toBe('single');
  expect(response.body.singleResult.errors).toBeUndefined();
  expect(response.body.singleResult.data?.createUser.user).toHaveProperty('id');
});
```

## Best Practices Summary

✅ **Nullable by default**: Only use non-null (`!`) when guaranteed
✅ **Use DataLoader**: Batch queries to prevent N+1
✅ **Pagination**: Use cursor-based for large lists
✅ **Input objects**: Group mutation arguments
✅ **Payload objects**: Return errors with data
✅ **Custom scalars**: Use DateTime, Email, URL, JSON
✅ **Interfaces**: Share common fields across types
✅ **Query complexity**: Limit expensive queries
✅ **Persisted queries**: Reduce payload, improve security
✅ **Error handling**: Return specific error codes and fields

❌ **Avoid over-fetching**: Let clients request exact fields
❌ **Don't expose internal IDs**: Use opaque IDs or UUIDs
❌ **Don't ignore N+1**: Always use DataLoader for relationships
❌ **Don't make everything non-null**: Breaks schema evolution
❌ **Don't use query strings for mutations**: Use input objects
❌ **Don't skip authorization**: Check permissions in resolvers

## Additional Resources

- [GraphQL Official Documentation](https://graphql.org/learn/)
- [Apollo Server Documentation](https://www.apollographql.com/docs/apollo-server/)
- [GraphQL Best Practices](https://graphql.org/learn/best-practices/)
- [Relay Cursor Connections Specification](https://relay.dev/graphql/connections.htm)
- [Apollo Federation](https://www.apollographql.com/docs/federation/)
- [DataLoader Documentation](https://github.com/graphql/dataloader)
