# REST API Patterns - Deep Dive

Comprehensive REST API design patterns covering advanced resource modeling, filtering, field selection, HATEOAS, and optimization techniques.

## Resource Modeling

### Single vs Collection Resources

**Collection Resources** (plural nouns):
```
GET    /users              → List all users
POST   /users              → Create new user
```

**Single Resources** (with ID):
```
GET    /users/123          → Get specific user
PUT    /users/123          → Replace user
PATCH  /users/123          → Update user fields
DELETE /users/123          → Delete user
```

### Sub-Resources (Nested Relationships)

✅ **Good: Clear hierarchy, logical nesting**
```
GET    /users/123/orders          → User's orders
POST   /users/123/orders          → Create order for user
GET    /users/123/orders/456      → Specific order for user
DELETE /users/123/orders/456      → Cancel user's order
```

❌ **Bad: Excessive nesting**
```
GET /organizations/1/departments/2/teams/3/members/4/tasks/5
```
✅ **Better: Shallow hierarchy, use query params**
```
GET /tasks/5
GET /tasks?member_id=4&team_id=3
```

### Non-CRUD Actions

When operations don't map to CRUD:

**Option 1: Treat as sub-resource**
```
POST /orders/123/cancel           → Cancel order
POST /users/123/activate          → Activate user
POST /invoices/456/send           → Send invoice
```

**Option 2: Use controller-style endpoints** (less RESTful but pragmatic)
```
POST /search                      → Complex search
POST /bulk-operations             → Batch operations
```

**Option 3: Use status field updates**
```
PATCH /orders/123
{ "status": "cancelled", "reason": "Customer request" }
```

## HTTP Methods Deep Dive

### GET (Safe, Idempotent, Cacheable)

**Characteristics**:
- No side effects (safe)
- Multiple identical requests = same result (idempotent)
- Should be cached
- No request body

```http
GET /users?status=active&role=admin HTTP/1.1
Host: api.example.com
Accept: application/json
Authorization: Bearer token123
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=300
ETag: "abc123"

{
  "data": [
    { "id": "1", "name": "Alice", "role": "admin" }
  ],
  "meta": {
    "total": 1,
    "page": 1,
    "per_page": 20
  }
}
```

### POST (Not Safe, Not Idempotent)

**Use for**:
- Creating resources
- Operations with side effects
- Searches with complex body
- Bulk operations

```http
POST /users HTTP/1.1
Host: api.example.com
Content-Type: application/json

{
  "email": "alice@example.com",
  "name": "Alice",
  "role": "admin"
}
```

**Response**:
```http
HTTP/1.1 201 Created
Location: /users/123
Content-Type: application/json

{
  "id": "123",
  "email": "alice@example.com",
  "name": "Alice",
  "role": "admin",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### PUT (Idempotent, Full Replace)

**Characteristics**:
- Replaces entire resource
- Must include all fields
- Idempotent (same request multiple times = same result)
- Creates if doesn't exist (optional)

```http
PUT /users/123 HTTP/1.1
Content-Type: application/json
If-Match: "abc123"

{
  "email": "alice@example.com",
  "name": "Alice Smith",
  "role": "admin",
  "department": "engineering"
}
```

### PATCH (Idempotent, Partial Update)

**Use for**: Updating specific fields without replacing entire resource

```http
PATCH /users/123 HTTP/1.1
Content-Type: application/json

{
  "name": "Alice Smith"
}
```

**JSON Patch (RFC 6902)** - more expressive:
```http
PATCH /users/123 HTTP/1.1
Content-Type: application/json-patch+json

[
  { "op": "replace", "path": "/name", "value": "Alice Smith" },
  { "op": "add", "path": "/tags/-", "value": "premium" },
  { "op": "remove", "path": "/temporary_flag" }
]
```

### DELETE (Idempotent)

```http
DELETE /users/123 HTTP/1.1
```

**Response options**:
```http
# Option 1: No content
HTTP/1.1 204 No Content

# Option 2: Return deleted resource
HTTP/1.1 200 OK
Content-Type: application/json
{ "id": "123", "deleted_at": "2025-01-01T00:00:00Z" }

# Option 3: Already deleted (still success)
HTTP/1.1 204 No Content
```

### HEAD (Metadata Only)

Same as GET but no response body:
```http
HEAD /users/123 HTTP/1.1

HTTP/1.1 200 OK
Content-Length: 256
Last-Modified: Wed, 21 Oct 2025 07:28:00 GMT
ETag: "abc123"
```

### OPTIONS (CORS, API Discovery)

```http
OPTIONS /users HTTP/1.1

HTTP/1.1 204 No Content
Allow: GET, POST, HEAD, OPTIONS
Access-Control-Allow-Methods: GET, POST, HEAD, OPTIONS
Access-Control-Allow-Headers: Authorization, Content-Type
```

## Query Parameters

### Filtering

```
# Single filter
GET /users?status=active

# Multiple filters (AND logic)
GET /users?status=active&role=admin&department=engineering

# Range filters
GET /users?created_after=2025-01-01&created_before=2025-12-31

# IN filters
GET /users?id=1,2,3,4
GET /users?status=active,pending

# Pattern matching (use carefully, can be expensive)
GET /users?name_like=alice
GET /users?email_ends_with=@example.com
```

**Advanced filtering with query operators**:
```
GET /users?age[gte]=18&age[lte]=65
GET /products?price[gt]=100&price[lt]=1000
GET /posts?published[eq]=true
```

### Sorting

```
# Single field
GET /users?sort=created_at

# Descending
GET /users?sort=-created_at

# Multiple fields
GET /users?sort=last_name,first_name
GET /users?sort=-created_at,name
```

**Alternative formats**:
```
GET /users?order_by=created_at&order=desc
GET /users?sort[created_at]=desc&sort[name]=asc
```

### Field Selection (Sparse Fieldsets)

Reduce payload size by requesting only needed fields:

```
# Select specific fields
GET /users?fields=id,name,email

# Exclude fields
GET /users?fields_exclude=internal_notes,password_hash

# Nested field selection
GET /users?fields=id,name,profile(avatar,bio)
```

**Response**:
```json
{
  "data": [
    {
      "id": "123",
      "name": "Alice",
      "email": "alice@example.com"
    }
  ]
}
```

### Expansion (Include Related Resources)

Avoid N+1 queries by including related data:

```
# Basic expansion
GET /orders/123?expand=customer

# Multiple expansions
GET /orders/123?expand=customer,items

# Nested expansion
GET /orders/123?expand=customer,items.product

# Selective nested fields
GET /orders/123?expand=customer(name,email),items(quantity,price)
```

**Response**:
```json
{
  "id": "123",
  "total": 1500,
  "customer": {
    "id": "456",
    "name": "Alice",
    "email": "alice@example.com"
  },
  "items": [
    {
      "id": "789",
      "quantity": 2,
      "price": 750,
      "product": {
        "id": "101",
        "name": "Widget",
        "sku": "WDG-001"
      }
    }
  ]
}
```

## Pagination Patterns

### Offset Pagination

**Simple and familiar**:
```
GET /users?limit=20&offset=0   # Page 1
GET /users?limit=20&offset=20  # Page 2
GET /users?limit=20&offset=40  # Page 3
```

**Response format**:
```json
{
  "data": [...],
  "meta": {
    "total": 1543,
    "limit": 20,
    "offset": 40,
    "page": 3,
    "total_pages": 78
  },
  "links": {
    "first": "/users?limit=20&offset=0",
    "prev": "/users?limit=20&offset=20",
    "next": "/users?limit=20&offset=60",
    "last": "/users?limit=20&offset=1540"
  }
}
```

**Pros**:
- Easy to implement
- Supports random access (jump to page 10)
- Familiar to users

**Cons**:
- Performance degrades with high offsets (database skips rows)
- Inconsistent results if data changes (items shift between pages)
- Not suitable for real-time feeds

### Cursor Pagination

**Efficient and stable**:
```
GET /users?limit=20                        # First page
GET /users?limit=20&cursor=eyJpZCI6MjB9   # Next page
```

**Response format**:
```json
{
  "data": [...],
  "meta": {
    "limit": 20,
    "has_more": true
  },
  "cursors": {
    "before": "eyJpZCI6MX0",
    "after": "eyJpZCI6MjB9"
  },
  "links": {
    "next": "/users?limit=20&cursor=eyJpZCI6MjB9",
    "prev": "/users?limit=20&cursor=eyJpZCI6MX0&direction=prev"
  }
}
```

**Cursor encoding** (base64 JSON):
```typescript
// Encode cursor
const cursor = Buffer.from(JSON.stringify({ id: 20 })).toString('base64url');

// Decode cursor
const decoded = JSON.parse(Buffer.from(cursor, 'base64url').toString());
```

**Pros**:
- Consistent results even if data changes
- Efficient for large datasets
- No offset performance penalty

**Cons**:
- No random access (can't jump to page 10)
- More complex to implement
- Cursor reveals internal structure (encrypt if sensitive)

### Keyset Pagination

**Database-optimized**:
```
GET /users?limit=20&after_id=123&order=id
```

**SQL implementation**:
```sql
-- First page
SELECT * FROM users ORDER BY id ASC LIMIT 20;

-- Next page (after_id from last result)
SELECT * FROM users WHERE id > 123 ORDER BY id ASC LIMIT 20;
```

**Pros**:
- Most performant (uses database index)
- Simple implementation
- Stable results

**Cons**:
- Requires ordered, unique field
- No backward pagination (easily)
- Complex with multi-field sorting

### Page Number Pagination

**User-friendly**:
```
GET /users?page=1&per_page=20
GET /users?page=2&per_page=20
```

**Response**:
```json
{
  "data": [...],
  "meta": {
    "current_page": 2,
    "per_page": 20,
    "total": 1543,
    "total_pages": 78,
    "from": 21,
    "to": 40
  },
  "links": {
    "first": "/users?page=1&per_page=20",
    "prev": "/users?page=1&per_page=20",
    "next": "/users?page=3&per_page=20",
    "last": "/users?page=78&per_page=20"
  }
}
```

Same pros/cons as offset pagination (it's offset in disguise: `offset = (page - 1) * per_page`).

## HATEOAS (Hypermedia)

**Hypermedia As The Engine Of Application State**: Include links to related actions and resources.

### Basic HATEOAS

```json
{
  "id": "123",
  "name": "Alice",
  "email": "alice@example.com",
  "links": {
    "self": "/users/123",
    "orders": "/users/123/orders",
    "edit": "/users/123",
    "delete": "/users/123"
  }
}
```

### HAL (Hypertext Application Language)

```json
{
  "_links": {
    "self": { "href": "/orders/123" },
    "customer": { "href": "/customers/456" },
    "payment": { "href": "/payments/789" }
  },
  "id": "123",
  "total": 1500,
  "status": "shipped",
  "_embedded": {
    "customer": {
      "_links": { "self": { "href": "/customers/456" } },
      "id": "456",
      "name": "Alice"
    }
  }
}
```

### JSON:API

```json
{
  "data": {
    "type": "orders",
    "id": "123",
    "attributes": {
      "total": 1500,
      "status": "shipped"
    },
    "relationships": {
      "customer": {
        "links": {
          "self": "/orders/123/relationships/customer",
          "related": "/orders/123/customer"
        },
        "data": { "type": "customers", "id": "456" }
      }
    },
    "links": {
      "self": "/orders/123"
    }
  },
  "included": [
    {
      "type": "customers",
      "id": "456",
      "attributes": {
        "name": "Alice",
        "email": "alice@example.com"
      }
    }
  ]
}
```

## Batch Operations

### Batch Create

```http
POST /users/batch HTTP/1.1
Content-Type: application/json

{
  "items": [
    { "email": "alice@example.com", "name": "Alice" },
    { "email": "bob@example.com", "name": "Bob" }
  ]
}
```

**Response**:
```json
{
  "results": [
    {
      "status": 201,
      "id": "123",
      "email": "alice@example.com"
    },
    {
      "status": 201,
      "id": "124",
      "email": "bob@example.com"
    }
  ],
  "summary": {
    "total": 2,
    "succeeded": 2,
    "failed": 0
  }
}
```

### Batch Update

```http
PATCH /users/batch HTTP/1.1
Content-Type: application/json

{
  "updates": [
    { "id": "123", "status": "active" },
    { "id": "124", "status": "inactive" }
  ]
}
```

### Batch Get

```http
GET /users?id=123,124,125 HTTP/1.1

# Or POST for large lists
POST /users/batch/get HTTP/1.1
{ "ids": ["123", "124", "125", ...] }
```

## Async Operations

### Long-Running Operations

**Pattern**: Return 202 Accepted with status URL:

```http
POST /reports/generate HTTP/1.1
{ "type": "annual", "year": 2024 }

HTTP/1.1 202 Accepted
Location: /operations/op_abc123
Content-Type: application/json

{
  "operation_id": "op_abc123",
  "status": "pending",
  "status_url": "/operations/op_abc123",
  "estimated_completion": "2025-01-01T00:05:00Z"
}
```

**Status endpoint**:
```http
GET /operations/op_abc123

# While processing
HTTP/1.1 200 OK
{
  "id": "op_abc123",
  "status": "processing",
  "progress": 45,
  "message": "Generating report..."
}

# When complete
HTTP/1.1 303 See Other
Location: /reports/rep_xyz789
{
  "id": "op_abc123",
  "status": "completed",
  "result_url": "/reports/rep_xyz789"
}
```

## Compression

**Request compression** (rare, large request bodies):
```http
POST /data/import HTTP/1.1
Content-Encoding: gzip
Content-Type: application/json
```

**Response compression** (common):
```http
GET /users HTTP/1.1
Accept-Encoding: gzip, deflate, br

HTTP/1.1 200 OK
Content-Encoding: gzip
Content-Type: application/json
```

Enable compression for responses >1KB. Use Brotli (br) for best compression.

## Content Negotiation

```http
# Request JSON
GET /users/123
Accept: application/json

# Request XML
GET /users/123
Accept: application/xml

# Request specific version
GET /users/123
Accept: application/vnd.myapi.v2+json

# Multiple acceptable types (quality values)
GET /users/123
Accept: application/json; q=1.0, application/xml; q=0.8
```

## Conditional Requests

### ETags (Strong Validation)

```http
# Get with ETag
GET /users/123
Response: ETag: "abc123"

# Update only if unchanged
PUT /users/123
If-Match: "abc123"
{ "name": "Alice Smith" }

# Success if ETag matches
HTTP/1.1 200 OK

# Failure if ETag changed (concurrent update)
HTTP/1.1 412 Precondition Failed
{
  "error": "Resource was modified by another request",
  "current_etag": "def456"
}
```

### Last-Modified (Weak Validation)

```http
GET /users/123
Response: Last-Modified: Wed, 21 Oct 2025 07:28:00 GMT

PUT /users/123
If-Unmodified-Since: Wed, 21 Oct 2025 07:28:00 GMT
```

## Performance Optimization

### HTTP/2 and HTTP/3

- **Multiplexing**: Multiple requests over single connection
- **Server Push**: Proactively send resources (use carefully)
- **Header compression**: HPACK reduces overhead

Enable HTTP/2 in production:
```nginx
listen 443 ssl http2;
```

### Connection Pooling

Reuse TCP connections:
```typescript
import http from 'http';

const agent = new http.Agent({
  keepAlive: true,
  maxSockets: 50,
  maxFreeSockets: 10,
  timeout: 60000
});

fetch('https://api.example.com/users', { agent });
```

### Response Streaming

Stream large responses:
```typescript
app.get('/export', (req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.write('[');

  const stream = db.users.stream();
  let first = true;

  stream.on('data', (user) => {
    if (!first) res.write(',');
    res.write(JSON.stringify(user));
    first = false;
  });

  stream.on('end', () => {
    res.write(']');
    res.end();
  });
});
```

## Security Headers

```http
HTTP/1.1 200 OK
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Content-Security-Policy: default-src 'self'
X-XSS-Protection: 1; mode=block
```

## CORS (Cross-Origin Resource Sharing)

**Preflight request** (OPTIONS):
```http
OPTIONS /users HTTP/1.1
Origin: https://example.com
Access-Control-Request-Method: POST
Access-Control-Request-Headers: Content-Type, Authorization

HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://example.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 86400
```

**Actual request**:
```http
POST /users HTTP/1.1
Origin: https://example.com

HTTP/1.1 201 Created
Access-Control-Allow-Origin: https://example.com
Access-Control-Expose-Headers: Location, X-Request-Id
```

## REST API Testing

### Integration Tests

```typescript
import request from 'supertest';
import { app } from './app';

describe('User API', () => {
  it('creates a user', async () => {
    const response = await request(app)
      .post('/users')
      .send({ email: 'test@example.com', name: 'Test' })
      .expect(201)
      .expect('Content-Type', /json/);

    expect(response.body).toHaveProperty('id');
    expect(response.headers.location).toBe(`/users/${response.body.id}`);
  });

  it('returns 404 for non-existent user', async () => {
    await request(app)
      .get('/users/999')
      .expect(404);
  });

  it('validates email format', async () => {
    const response = await request(app)
      .post('/users')
      .send({ email: 'invalid', name: 'Test' })
      .expect(400);

    expect(response.body.error.details).toContainEqual(
      expect.objectContaining({ field: 'email' })
    );
  });
});
```

### API Schema Validation

```typescript
import Ajv from 'ajv';
import { openApiSchema } from './openapi.json';

const ajv = new Ajv();
const validate = ajv.compile(openApiSchema.components.schemas.User);

it('response matches OpenAPI schema', async () => {
  const response = await request(app).get('/users/123');
  const valid = validate(response.body);
  expect(valid).toBe(true);
});
```

## Best Practices Summary

✅ **Use plural nouns for collections**: `/users` not `/user`
✅ **Use HTTP methods correctly**: GET (read), POST (create), PUT/PATCH (update), DELETE (delete)
✅ **Return appropriate status codes**: 200, 201, 400, 404, 500, etc.
✅ **Version your API**: `/v1/users` or header-based
✅ **Support pagination**: Offset, cursor, or keyset
✅ **Include HATEOAS links**: Help clients discover actions
✅ **Use ETags for caching**: Conditional requests (If-Match, If-None-Match)
✅ **Compress responses**: gzip, Brotli for >1KB
✅ **Implement rate limiting**: Protect against abuse
✅ **Document with OpenAPI**: Interactive, machine-readable docs
✅ **Test thoroughly**: Unit, integration, contract, load tests

❌ **Avoid verbs in URLs**: `/getUser` should be `GET /users/{id}`
❌ **Don't ignore HTTP semantics**: Use correct methods and status codes
❌ **Don't over-nest resources**: Keep hierarchy shallow (2-3 levels max)
❌ **Don't return entire objects**: Support field selection for efficiency
❌ **Don't break existing versions**: Version breaking changes
❌ **Don't expose internal structure**: Abstract implementation details
❌ **Don't skip error details**: Provide actionable error messages

## Additional Resources

- [RFC 7231: HTTP/1.1 Semantics](https://tools.ietf.org/html/rfc7231)
- [RFC 6902: JSON Patch](https://tools.ietf.org/html/rfc6902)
- [RFC 5988: Web Linking](https://tools.ietf.org/html/rfc5988)
- [JSON:API Specification](https://jsonapi.org/)
- [HAL Specification](https://stateless.group/hal_specification.html)
- [OpenAPI 3.1.0 Specification](https://spec.openapis.org/oas/v3.1.0)
