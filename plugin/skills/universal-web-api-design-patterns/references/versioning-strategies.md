# API Versioning Strategies - Deep Dive

Comprehensive guide to API versioning patterns, migration strategies, and managing breaking changes across REST, GraphQL, and gRPC.

## Why Version APIs?

**Breaking changes**:
- Removing fields or endpoints
- Renaming fields or endpoints
- Changing field types
- Changing required/optional status
- Changing response structure
- Changing authentication methods
- Changing error formats

**Non-breaking changes**:
- Adding optional fields
- Adding new endpoints
- Adding new enum values (append-only)
- Expanding validation (less strict)
- Adding optional query parameters
- Adding new error codes (with graceful handling)

## URI Versioning

### Pattern

```
GET /v1/users
GET /v2/users
GET /v3/users
```

### Pros

✅ **Simple and explicit**: Version is immediately visible
✅ **Easy to route**: Straightforward load balancer/proxy rules
✅ **Browser-friendly**: Can test in browser address bar
✅ **Industry standard**: Used by Stripe, Twitter, GitHub
✅ **Clear deprecation**: Sunset entire version

### Cons

❌ **URL pollution**: Versions in every URL
❌ **Resource duplication**: `/v1/users/123` vs `/v2/users/123` same resource
❌ **Cache complications**: Separate cache keys per version
❌ **Not RESTful**: Violates resource identifier principle

### Implementation

```typescript
// Express routing
app.use('/v1', require('./routes/v1'));
app.use('/v2', require('./routes/v2'));
app.use('/v3', require('./routes/v3'));

// Redirect /users to latest version
app.get('/users', (req, res) => {
  res.redirect(301, '/v3/users');
});
```

**Nginx routing**:
```nginx
location /v1/ {
    proxy_pass http://api-v1:3000/;
}

location /v2/ {
    proxy_pass http://api-v2:3000/;
}

location /v3/ {
    proxy_pass http://api-v3:3000/;
}
```

### Versioning Scheme

**Major version only** (recommended):
```
/v1/users
/v2/users
```

**Semantic versioning** (overkill for APIs):
```
/v1.2.3/users  # Too granular
```

**Date-based versioning**:
```
/2024-01-15/users  # Stripe-style
```

## Header Versioning

### Accept Header

```http
GET /users
Accept: application/vnd.myapi.v2+json
```

**Vendor MIME types**:
```
application/vnd.myapi.v1+json
application/vnd.myapi.v2+json
application/vnd.github.v3+json
```

### Custom Header

```http
GET /users
API-Version: 2
```

Or:
```http
GET /users
X-API-Version: 2024-01-15
```

### Pros

✅ **Clean URLs**: Version separate from resource path
✅ **RESTful**: Resource identifiers unchanged
✅ **Flexible**: Can version per-resource
✅ **HTTP standard**: Uses existing headers

### Cons

❌ **Less visible**: Not in URL, harder to debug
❌ **Harder to test**: Can't test in browser easily
❌ **Documentation complexity**: Requires explanation
❌ **Client complexity**: More header management

### Implementation

```typescript
// Express middleware
app.use((req, res, next) => {
  const acceptHeader = req.get('Accept') || '';
  const versionMatch = acceptHeader.match(/vnd\.myapi\.v(\d+)\+json/);

  req.apiVersion = versionMatch ? parseInt(versionMatch[1]) : 1;
  next();
});

// Route based on version
app.get('/users', (req, res) => {
  if (req.apiVersion === 1) {
    return v1.getUsers(req, res);
  } else if (req.apiVersion === 2) {
    return v2.getUsers(req, res);
  } else {
    return res.status(400).json({ error: 'Unsupported API version' });
  }
});
```

**Default version fallback**:
```typescript
app.use((req, res, next) => {
  const apiVersion = req.get('API-Version');
  req.apiVersion = apiVersion ? parseInt(apiVersion) : 2; // Default to v2
  next();
});
```

## Content Negotiation

### Resource-Level Versioning

```http
GET /users
Accept: application/vnd.myapi.user.v2+json
```

Different resources can have different versions:
```http
Accept: application/vnd.myapi.user.v2+json
Accept: application/vnd.myapi.order.v3+json
```

### Pros

✅ **Granular**: Version per resource type
✅ **Evolutionary**: Resources evolve independently
✅ **Backward compatible**: Mix old and new versions

### Cons

❌ **Complexity**: More versions to manage
❌ **Testing burden**: Combinatorial explosion
❌ **Client confusion**: Which resource versions are compatible?

## Query Parameter Versioning

```
GET /users?version=2
GET /users?api_version=2
GET /users?v=2
```

### Pros

✅ **Simple**: Easy to implement
✅ **Visible**: In URL for debugging
✅ **Optional**: Can default to latest

### Cons

❌ **Pollutes query params**: Mixes versioning with filtering
❌ **Not RESTful**: Query params should be for filtering
❌ **Cache issues**: May need to handle in caching layer
❌ **Less professional**: Rarely used in production APIs

### Implementation

```typescript
app.get('/users', (req, res) => {
  const version = parseInt(req.query.version) || 2;

  if (version === 1) {
    return v1.getUsers(req, res);
  } else if (version === 2) {
    return v2.getUsers(req, res);
  } else {
    return res.status(400).json({ error: 'Invalid API version' });
  }
});
```

## Version Negotiation

### Default Version

**Option 1: Latest version by default**
```typescript
const version = req.apiVersion || LATEST_VERSION;
```

**Option 2: Require explicit version**
```typescript
if (!req.apiVersion) {
  return res.status(400).json({
    error: 'API version required',
    documentation: 'https://api.example.com/docs/versioning'
  });
}
```

**Option 3: Pin to first version on API key creation**
```typescript
// API key includes default version
const apiKey = await createAPIKey({ userId, defaultVersion: 2 });

// Use key's default version if not specified
const version = req.apiVersion || apiKey.defaultVersion;
```

### Version Discovery

**Include supported versions in response**:
```http
GET /

HTTP/1.1 200 OK
API-Version: 2
API-Versions-Supported: 1, 2, 3
API-Versions-Deprecated: 1

{
  "current_version": 2,
  "supported_versions": [1, 2, 3],
  "deprecated_versions": [1],
  "latest_version": 3,
  "documentation": "https://api.example.com/docs"
}
```

## Deprecation Strategy

### Deprecation Timeline

**Phase 1: Announce (3-6 months ahead)**
```json
{
  "version": "1",
  "status": "active",
  "sunset_date": "2025-12-31",
  "replacement_version": "2",
  "migration_guide": "https://api.example.com/docs/v1-to-v2"
}
```

**Phase 2: Warn (headers + docs)**
```http
HTTP/1.1 200 OK
Deprecation: true
Sunset: Sat, 31 Dec 2025 23:59:59 GMT
Link: <https://api.example.com/docs/v1-to-v2>; rel="deprecation"

{
  "data": [...],
  "meta": {
    "deprecation_warning": "API v1 will be sunset on 2025-12-31. Migrate to v2."
  }
}
```

**Phase 3: Limit (rate limiting)**
```
v1: 100 req/min → 50 req/min → 10 req/min
v2: 1000 req/min (normal limits)
```

**Phase 4: Sunset (remove)**
```http
GET /v1/users

HTTP/1.1 410 Gone
{
  "error": "API v1 has been sunset",
  "sunset_date": "2025-12-31",
  "replacement": "https://api.example.com/v2/users",
  "migration_guide": "https://api.example.com/docs/v1-to-v2"
}
```

### Deprecation Headers

```http
# Deprecation (RFC draft)
Deprecation: true
Deprecation: @1640995200  # Unix timestamp

# Sunset (RFC 8594)
Sunset: Sat, 31 Dec 2025 23:59:59 GMT

# Link to migration guide
Link: <https://api.example.com/docs/v1-to-v2>; rel="deprecation"
Link: <https://api.example.com/v2/users>; rel="alternate"
```

### Communication Channels

1. **Email notifications**: Contact all API key owners
2. **Changelog**: Document in API changelog
3. **Developer portal**: Banner on docs site
4. **Slack/Discord**: Developer community announcements
5. **Blog post**: Major version changes
6. **Status page**: Sunset timeline

## Migration Patterns

### Adapter Pattern (Shared Logic)

```typescript
// Shared domain logic
class UserService {
  async getUser(id: string) {
    return db.users.findUnique({ where: { id } });
  }
}

// V1 adapter
class V1UserAdapter {
  constructor(private service: UserService) {}

  async getUser(id: string) {
    const user = await this.service.getUser(id);
    return {
      user_id: user.id,  // V1 format: snake_case
      email: user.email,
      full_name: user.name,
    };
  }
}

// V2 adapter
class V2UserAdapter {
  constructor(private service: UserService) {}

  async getUser(id: string) {
    const user = await this.service.getUser(id);
    return {
      id: user.id,       // V2 format: camelCase
      email: user.email,
      name: user.name,
      createdAt: user.createdAt,
    };
  }
}
```

### Feature Flags

```typescript
// Gradual rollout of v2 features
const featureFlags = {
  v2NewAuthFlow: { rollout: 0.1 },  // 10% of users
  v2NewErrorFormat: { rollout: 0.5 }, // 50% of users
};

app.get('/v2/users', async (req, res) => {
  const user = await getUser(req.params.id);

  // Use feature flag for new auth flow
  if (isEnabled('v2NewAuthFlow', user)) {
    await checkAuthV2(req);
  } else {
    await checkAuthV1(req);
  }

  res.json(user);
});
```

### Dual-Write Pattern

**Write to both versions during migration**:
```typescript
async function updateUser(id: string, data: any) {
  // Write to v1 format (old database schema)
  await v1DB.users.update({
    where: { id },
    data: {
      full_name: data.name,
      email_address: data.email,
    },
  });

  // Write to v2 format (new database schema)
  await v2DB.users.update({
    where: { id },
    data: {
      name: data.name,
      email: data.email,
    },
  });
}
```

### Transformation Layer

```typescript
// Bidirectional transformations
class UserTransformer {
  static toV1(v2User: V2User): V1User {
    return {
      user_id: v2User.id,
      email: v2User.email,
      full_name: v2User.name,
      created: v2User.createdAt.toISOString(),
    };
  }

  static toV2(v1User: V1User): V2User {
    return {
      id: v1User.user_id,
      email: v1User.email,
      name: v1User.full_name,
      createdAt: new Date(v1User.created),
    };
  }
}

// V1 endpoint (transform v2 data to v1 format)
app.get('/v1/users/:id', async (req, res) => {
  const v2User = await getUserV2(req.params.id);
  const v1User = UserTransformer.toV1(v2User);
  res.json(v1User);
});
```

## GraphQL Versioning

### Schema Evolution (Preferred)

**Add new fields without breaking existing queries**:
```graphql
type User {
  id: ID!
  email: String!
  name: String!

  # Add new field (non-breaking)
  fullName: String! @deprecated(reason: "Use name instead")

  # Add new optional field (non-breaking)
  phoneNumber: String

  # Add new field with default (non-breaking)
  role: UserRole! = USER
}
```

### Field Deprecation

```graphql
type User {
  id: ID!
  email: String!

  # Deprecated field
  name: String! @deprecated(reason: "Use firstName and lastName instead")

  # New fields
  firstName: String!
  lastName: String!
}
```

**Clients see deprecation in introspection**:
```json
{
  "name": "name",
  "type": { "kind": "SCALAR", "name": "String" },
  "isDeprecated": true,
  "deprecationReason": "Use firstName and lastName instead"
}
```

### Schema Versioning (Alternative)

```graphql
# Schema v1
type Query {
  user(id: ID!): UserV1
  users: [UserV1!]!
}

type UserV1 {
  id: ID!
  email: String!
  name: String!
}

# Schema v2
type Query {
  userV2(id: ID!): UserV2
  usersV2: [UserV2!]!
}

type UserV2 {
  id: ID!
  email: String!
  firstName: String!
  lastName: String!
}
```

### Version in Query

```graphql
query GetUser($version: Int = 2) {
  user(id: "123", version: $version) {
    ... on UserV1 {
      id
      name
    }
    ... on UserV2 {
      id
      firstName
      lastName
    }
  }
}
```

## gRPC Versioning

### Package Versioning (Recommended)

```protobuf
// users/v1/user.proto
syntax = "proto3";
package users.v1;

service UserService {
  rpc GetUser (GetUserRequest) returns (User) {}
}

// users/v2/user.proto
syntax = "proto3";
package users.v2;

service UserService {
  rpc GetUser (GetUserRequest) returns (User) {}
}
```

**Server serves multiple versions**:
```go
v1Server := &v1.UserServiceServer{}
v2Server := &v2.UserServiceServer{}

v1pb.RegisterUserServiceServer(s, v1Server)
v2pb.RegisterUserServiceServer(s, v2Server)
```

### Field Evolution

**Add fields (non-breaking)**:
```protobuf
message User {
  string id = 1;
  string email = 2;
  string name = 3;

  // Add new optional field (non-breaking)
  string phone_number = 4;

  // Add new field with default (non-breaking)
  UserRole role = 5 [default = USER_ROLE_USER];
}
```

**Deprecate fields**:
```protobuf
message User {
  string id = 1;
  string email = 2;

  // Deprecated field
  string name = 3 [deprecated = true];

  // New fields
  string first_name = 4;
  string last_name = 5;
}
```

### Breaking Changes

**Reserve field numbers**:
```protobuf
message User {
  reserved 3;  // Field 3 removed
  reserved "old_field_name";

  string id = 1;
  string email = 2;
  // Field 3 cannot be reused
  string new_field = 4;
}
```

## Version Compatibility Matrix

| Change | REST URI | REST Header | GraphQL | gRPC |
|--------|----------|-------------|---------|------|
| Add optional field | ✅ Non-breaking | ✅ Non-breaking | ✅ Non-breaking | ✅ Non-breaking |
| Add required field | ❌ Breaking | ❌ Breaking | ❌ Breaking | ❌ Breaking |
| Remove field | ❌ Breaking | ❌ Breaking | ❌ Breaking | ❌ Breaking |
| Rename field | ❌ Breaking | ❌ Breaking | ❌ Breaking | ❌ Breaking |
| Change type | ❌ Breaking | ❌ Breaking | ❌ Breaking | ❌ Breaking |
| Add endpoint | ✅ Non-breaking | ✅ Non-breaking | ✅ Non-breaking | ✅ Non-breaking |
| Remove endpoint | ❌ Breaking | ❌ Breaking | ❌ Breaking | ❌ Breaking |
| Add enum value | ⚠️ Depends | ⚠️ Depends | ⚠️ Depends | ✅ Non-breaking |
| Remove enum value | ❌ Breaking | ❌ Breaking | ❌ Breaking | ❌ Breaking |

## Testing Multiple Versions

### Contract Testing

```typescript
// Pact contract test for v1
describe('User API v1', () => {
  it('gets a user', async () => {
    const provider = new Pact({
      consumer: 'Client',
      provider: 'UserAPI-v1',
    });

    await provider
      .given('user 123 exists')
      .uponReceiving('a request for user 123')
      .withRequest({
        method: 'GET',
        path: '/v1/users/123',
      })
      .willRespondWith({
        status: 200,
        body: {
          user_id: '123',
          email: 'test@example.com',
          full_name: 'Test User',
        },
      });
  });
});

// Pact contract test for v2
describe('User API v2', () => {
  it('gets a user', async () => {
    await provider
      .given('user 123 exists')
      .uponReceiving('a request for user 123')
      .withRequest({
        method: 'GET',
        path: '/v2/users/123',
      })
      .willRespondWith({
        status: 200,
        body: {
          id: '123',
          email: 'test@example.com',
          name: 'Test User',
        },
      });
  });
});
```

### Smoke Tests

```typescript
// Test all supported versions
const versions = ['v1', 'v2', 'v3'];

for (const version of versions) {
  describe(`API ${version} smoke tests`, () => {
    it('gets users', async () => {
      const response = await fetch(`https://api.example.com/${version}/users`);
      expect(response.status).toBe(200);
    });

    it('creates user', async () => {
      const response = await fetch(`https://api.example.com/${version}/users`, {
        method: 'POST',
        body: JSON.stringify({ email: 'test@example.com' }),
      });
      expect(response.status).toBe(201);
    });
  });
}
```

## Best Practices Summary

✅ **Version from day one**: Don't wait until you need to break things
✅ **Use URI versioning for REST**: Simple, explicit, industry standard
✅ **Use package versioning for gRPC**: `users.v1`, `users.v2`
✅ **Deprecate gracefully**: 3-6 month timeline with warnings
✅ **Document migration paths**: Provide clear upgrade guides
✅ **Support 2-3 versions max**: Don't accumulate technical debt
✅ **Test all versions**: Contract tests prevent regressions
✅ **Communicate early**: Email + docs + headers + blog posts
✅ **Use sunset headers**: `Deprecation`, `Sunset`, `Link`
✅ **Monitor version usage**: Track adoption before deprecating

❌ **Don't version minor changes**: Use feature flags instead
❌ **Don't break unexpectedly**: Always announce ahead of time
❌ **Don't support too many versions**: 2-3 active versions max
❌ **Don't remove versions suddenly**: Gradual deprecation timeline
❌ **Don't skip migration guides**: Document upgrade path clearly
❌ **Don't forget to sunset**: Old versions accumulate technical debt

## Decision Tree

```
Should you create a new version?

Breaking change?
├─ Yes → New version required
│  ├─ Removed fields/endpoints → New major version
│  ├─ Changed types → New major version
│  ├─ Changed auth → New major version
│  └─ Changed error format → New major version
│
└─ No → Add to current version
   ├─ Added optional fields → Non-breaking
   ├─ Added new endpoints → Non-breaking
   ├─ Relaxed validation → Non-breaking
   └─ Added enum values → Non-breaking (usually)

Which versioning strategy?

REST API?
├─ Public API → URI versioning (/v1/users)
├─ Internal API → Header versioning (API-Version: 2)
└─ Microservices → Package versioning (users.v1)

GraphQL API?
├─ Preferred → Schema evolution + @deprecated
└─ Alternative → Versioned types (UserV1, UserV2)

gRPC API?
└─ Always → Package versioning (users.v1, users.v2)
```

## Additional Resources

- [Semantic Versioning](https://semver.org/)
- [RFC 8594: Sunset HTTP Header](https://tools.ietf.org/html/rfc8594)
- [Stripe API Versioning](https://stripe.com/docs/api/versioning)
- [GraphQL Best Practices](https://graphql.org/learn/best-practices/#versioning)
- [gRPC Versioning Guide](https://grpc.io/docs/guides/api-versioning/)
- [HTTP API Problem Details (RFC 7807)](https://tools.ietf.org/html/rfc7807)
