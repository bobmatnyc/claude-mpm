# API Authentication & Authorization - Deep Dive

Comprehensive authentication and authorization patterns for APIs including OAuth 2.0, JWT, API keys, RBAC, and security best practices.

## Authentication vs Authorization

**Authentication**: Who are you? (Identity verification)
**Authorization**: What can you do? (Permission checking)

```
Authentication → Who is making the request?
Authorization → Is this user allowed to perform this action?
```

## OAuth 2.0

### Grant Types

#### Authorization Code Flow (Most Secure)

**Use for**: Web applications, mobile apps with backend

```
1. User clicks "Login" on client
2. Client redirects to /authorize
3. User authenticates and grants permissions
4. Auth server redirects to callback with authorization code
5. Client exchanges code for access token (server-to-server)
6. Client uses access token for API requests
```

**Step-by-step**:

```http
# 1. Client redirects to authorization endpoint
https://auth.example.com/oauth/authorize?
  response_type=code&
  client_id=CLIENT_ID&
  redirect_uri=https://client.com/callback&
  scope=read:users write:orders&
  state=random_csrf_token

# 2. User authenticates and approves

# 3. Auth server redirects to callback
https://client.com/callback?
  code=AUTH_CODE&
  state=random_csrf_token

# 4. Client exchanges code for token (server-side)
POST https://auth.example.com/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code=AUTH_CODE&
redirect_uri=https://client.com/callback&
client_id=CLIENT_ID&
client_secret=CLIENT_SECRET

# 5. Response with access token
{
  "access_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "tGzv3JOkF0XG5Qx2TlKWIA",
  "scope": "read:users write:orders"
}

# 6. Use access token
GET https://api.example.com/users
Authorization: Bearer eyJhbGc...
```

#### Authorization Code Flow with PKCE

**Use for**: Mobile apps, SPAs (no client secret)

**PKCE (Proof Key for Code Exchange)** prevents authorization code interception.

```
1. Client generates code_verifier (random string)
2. Client creates code_challenge = SHA256(code_verifier)
3. Client includes code_challenge in /authorize request
4. Auth server stores code_challenge with authorization code
5. Client includes code_verifier in token exchange
6. Auth server verifies SHA256(code_verifier) == code_challenge
```

**Implementation**:

```typescript
import crypto from 'crypto';

// Generate code verifier (43-128 characters)
const codeVerifier = crypto.randomBytes(32).toString('base64url');

// Generate code challenge
const codeChallenge = crypto
  .createHash('sha256')
  .update(codeVerifier)
  .digest('base64url');

// Step 1: Redirect to authorization
const authUrl = new URL('https://auth.example.com/oauth/authorize');
authUrl.searchParams.set('response_type', 'code');
authUrl.searchParams.set('client_id', 'CLIENT_ID');
authUrl.searchParams.set('redirect_uri', 'https://client.com/callback');
authUrl.searchParams.set('code_challenge', codeChallenge);
authUrl.searchParams.set('code_challenge_method', 'S256');
authUrl.searchParams.set('scope', 'read:users');
authUrl.searchParams.set('state', crypto.randomBytes(16).toString('hex'));

// Step 2: Exchange code for token
const response = await fetch('https://auth.example.com/oauth/token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams({
    grant_type: 'authorization_code',
    code: authCode,
    redirect_uri: 'https://client.com/callback',
    client_id: 'CLIENT_ID',
    code_verifier: codeVerifier, // Send original verifier
  }),
});
```

#### Client Credentials Flow

**Use for**: Server-to-server, microservices, background jobs

```http
POST https://auth.example.com/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&
client_id=CLIENT_ID&
client_secret=CLIENT_SECRET&
scope=read:users

# Response
{
  "access_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "read:users"
}
```

**No user context** - acts as the application itself.

#### Implicit Flow (Deprecated)

**Do not use**: Replaced by Authorization Code + PKCE

```http
# Returns token directly in URL fragment (insecure)
https://client.com/callback#access_token=TOKEN&...
```

❌ **Security issues**:
- Token exposed in URL (browser history, referrer)
- No refresh token
- No client authentication

#### Resource Owner Password Credentials (Avoid)

**Use only for**: Trusted first-party apps (migration scenarios)

```http
POST https://auth.example.com/oauth/token

grant_type=password&
username=user@example.com&
password=secretpassword&
client_id=CLIENT_ID&
client_secret=CLIENT_SECRET
```

❌ **Avoid because**:
- Client handles user password (security risk)
- Doesn't support MFA
- No consent screen
- Use Authorization Code instead

### Token Types

#### Access Token

**Purpose**: Short-lived token for API access

```json
{
  "access_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Characteristics**:
- Short expiration (15 min - 1 hour)
- Contains permissions (scopes)
- Can be opaque or JWT
- Sent in Authorization header

#### Refresh Token

**Purpose**: Long-lived token to get new access tokens

```http
POST https://auth.example.com/oauth/token

grant_type=refresh_token&
refresh_token=tGzv3JOkF0XG5Qx2TlKWIA&
client_id=CLIENT_ID&
client_secret=CLIENT_SECRET

# Response: New access token
{
  "access_token": "new_access_token",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "new_refresh_token"
}
```

**Characteristics**:
- Long expiration (days to months)
- Stored securely (encrypted database)
- Can be revoked
- May rotate on use (refresh token rotation)

### Scopes

**Define permission boundaries**:

```
read:users         - Read user data
write:users        - Create/update users
delete:users       - Delete users
admin:users        - Full user management

read:orders        - Read orders
write:orders       - Create/update orders
```

**Request specific scopes**:
```http
GET /oauth/authorize?scope=read:users write:orders
```

**Check scopes in API**:
```typescript
function requireScope(requiredScope: string) {
  return (req, res, next) => {
    const tokenScopes = req.token.scope.split(' ');

    if (!tokenScopes.includes(requiredScope)) {
      return res.status(403).json({
        error: 'insufficient_scope',
        message: `Requires scope: ${requiredScope}`,
      });
    }

    next();
  };
}

app.get('/users', requireScope('read:users'), async (req, res) => {
  // Handler
});
```

### Implementation (Node.js)

**Auth server using oauth2-server**:
```typescript
import OAuth2Server from 'oauth2-server';

const oauth = new OAuth2Server({
  model: {
    // Get client by ID
    getClient: async (clientId, clientSecret) => {
      const client = await db.clients.findUnique({ where: { clientId } });

      if (!client || client.clientSecret !== clientSecret) {
        return null;
      }

      return {
        id: client.id,
        redirectUris: client.redirectUris,
        grants: client.grants,
      };
    },

    // Save authorization code
    saveAuthorizationCode: async (code, client, user) => {
      return db.authorizationCodes.create({
        data: {
          code: code.authorizationCode,
          expiresAt: code.expiresAt,
          redirectUri: code.redirectUri,
          clientId: client.id,
          userId: user.id,
        },
      });
    },

    // Get authorization code
    getAuthorizationCode: async (code) => {
      const authCode = await db.authorizationCodes.findUnique({
        where: { code },
        include: { client: true, user: true },
      });

      return {
        code: authCode.code,
        expiresAt: authCode.expiresAt,
        redirectUri: authCode.redirectUri,
        client: authCode.client,
        user: authCode.user,
      };
    },

    // Revoke authorization code
    revokeAuthorizationCode: async (code) => {
      await db.authorizationCodes.delete({ where: { code: code.code } });
      return true;
    },

    // Save access token
    saveToken: async (token, client, user) => {
      return db.accessTokens.create({
        data: {
          accessToken: token.accessToken,
          accessTokenExpiresAt: token.accessTokenExpiresAt,
          refreshToken: token.refreshToken,
          refreshTokenExpiresAt: token.refreshTokenExpiresAt,
          clientId: client.id,
          userId: user.id,
        },
      });
    },

    // Get access token
    getAccessToken: async (accessToken) => {
      const token = await db.accessTokens.findUnique({
        where: { accessToken },
        include: { client: true, user: true },
      });

      return {
        accessToken: token.accessToken,
        accessTokenExpiresAt: token.accessTokenExpiresAt,
        client: token.client,
        user: token.user,
      };
    },

    // Get refresh token
    getRefreshToken: async (refreshToken) => {
      const token = await db.accessTokens.findUnique({
        where: { refreshToken },
        include: { client: true, user: true },
      });

      return {
        refreshToken: token.refreshToken,
        refreshTokenExpiresAt: token.refreshTokenExpiresAt,
        client: token.client,
        user: token.user,
      };
    },

    // Revoke refresh token
    revokeToken: async (token) => {
      await db.accessTokens.delete({ where: { refreshToken: token.refreshToken } });
      return true;
    },
  },
});

// Endpoints
app.post('/oauth/authorize', async (req, res) => {
  const request = new OAuth2Server.Request(req);
  const response = new OAuth2Server.Response(res);

  try {
    const code = await oauth.authorize(request, response);
    res.redirect(`${code.redirectUri}?code=${code.authorizationCode}&state=${req.query.state}`);
  } catch (err) {
    res.status(err.code || 500).json({ error: err.name, message: err.message });
  }
});

app.post('/oauth/token', async (req, res) => {
  const request = new OAuth2Server.Request(req);
  const response = new OAuth2Server.Response(res);

  try {
    const token = await oauth.token(request, response);
    res.json(token);
  } catch (err) {
    res.status(err.code || 500).json({ error: err.name, message: err.message });
  }
});
```

## JWT (JSON Web Tokens)

### Structure

```
HEADER.PAYLOAD.SIGNATURE
```

**Header**:
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

**Payload** (claims):
```json
{
  "sub": "user_123",
  "iat": 1516239022,
  "exp": 1516242622,
  "iss": "https://auth.example.com",
  "aud": "https://api.example.com",
  "scope": "read:users write:orders"
}
```

**Signature**:
```
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  secret
)
```

### Standard Claims

- `iss` (Issuer): Who issued the token
- `sub` (Subject): User ID
- `aud` (Audience): Who the token is for
- `exp` (Expiration): Unix timestamp
- `nbf` (Not Before): Unix timestamp
- `iat` (Issued At): Unix timestamp
- `jti` (JWT ID): Unique token ID

### Custom Claims

```json
{
  "sub": "user_123",
  "email": "user@example.com",
  "role": "admin",
  "permissions": ["read:users", "write:users"],
  "org_id": "org_456"
}
```

### Creating JWTs

```typescript
import jwt from 'jsonwebtoken';

const payload = {
  sub: 'user_123',
  email: 'user@example.com',
  role: 'admin',
};

const token = jwt.sign(payload, process.env.JWT_SECRET, {
  expiresIn: '1h',
  issuer: 'https://auth.example.com',
  audience: 'https://api.example.com',
});
```

### Verifying JWTs

```typescript
import jwt from 'jsonwebtoken';

function verifyToken(token: string) {
  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET, {
      issuer: 'https://auth.example.com',
      audience: 'https://api.example.com',
    });

    return payload;
  } catch (error) {
    if (error.name === 'TokenExpiredError') {
      throw new Error('Token expired');
    } else if (error.name === 'JsonWebTokenError') {
      throw new Error('Invalid token');
    }
    throw error;
  }
}

// Middleware
app.use((req, res, next) => {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing or invalid authorization header' });
  }

  const token = authHeader.split(' ')[1];

  try {
    req.user = verifyToken(token);
    next();
  } catch (error) {
    return res.status(401).json({ error: error.message });
  }
});
```

### Asymmetric Keys (RS256)

**More secure**: Private key signs, public key verifies

```typescript
import fs from 'fs';

const privateKey = fs.readFileSync('private.key');
const publicKey = fs.readFileSync('public.key');

// Sign with private key
const token = jwt.sign(payload, privateKey, {
  algorithm: 'RS256',
  expiresIn: '1h',
});

// Verify with public key
const payload = jwt.verify(token, publicKey, {
  algorithms: ['RS256'],
});
```

**Benefits**:
- API servers only need public key (can't create tokens)
- Key rotation easier (distribute public keys)
- More secure (private key never leaves auth server)

### JWT Best Practices

✅ **Use short expiration**: 15 minutes to 1 hour
✅ **Use asymmetric keys (RS256)**: More secure than symmetric (HS256)
✅ **Include minimal claims**: Tokens sent with every request
✅ **Validate all claims**: `iss`, `aud`, `exp`, `nbf`
✅ **Use JTI for revocation**: Track token IDs in database
✅ **Store refresh tokens**: Don't extend JWT expiration

❌ **Don't store sensitive data**: JWTs are not encrypted (only signed)
❌ **Don't use long expiration**: Hard to revoke
❌ **Don't skip validation**: Always verify signature and claims
❌ **Don't trust client-provided JWTs**: Always verify signature

## API Keys

### Types

**Service-to-Service**:
```
sk_live_abc123...
sk_test_xyz789...
```

**User API Keys**:
```
pk_live_user123_abc...
pk_test_user123_xyz...
```

### Key Format

**Prefix** (identifies environment and type):
- `sk_live_`: Live secret key
- `sk_test_`: Test secret key
- `pk_live_`: Live publishable key
- `pk_test_`: Test publishable key

**Body** (random, URL-safe):
```typescript
import crypto from 'crypto';

function generateAPIKey(prefix: string): string {
  const randomBytes = crypto.randomBytes(32);
  const key = randomBytes.toString('base64url');
  return `${prefix}${key}`;
}

const liveKey = generateAPIKey('sk_live_');
// Example output: sk_live_[random_32_byte_base64url_string]
```

### Storage

**Hash keys before storage**:
```typescript
import bcrypt from 'bcrypt';

async function createAPIKey(userId: string): Promise<string> {
  const key = generateAPIKey('sk_live_');
  const hashedKey = await bcrypt.hash(key, 10);

  await db.apiKeys.create({
    data: {
      userId,
      keyHash: hashedKey,
      keyPrefix: key.substring(0, 15), // Store prefix for identification
      createdAt: new Date(),
    },
  });

  // Return unhashed key ONCE (user must store it)
  return key;
}

async function validateAPIKey(key: string): Promise<User | null> {
  const prefix = key.substring(0, 15);

  const apiKey = await db.apiKeys.findFirst({
    where: { keyPrefix: prefix },
    include: { user: true },
  });

  if (!apiKey) {
    return null;
  }

  const isValid = await bcrypt.compare(key, apiKey.keyHash);

  if (!isValid) {
    return null;
  }

  return apiKey.user;
}
```

### Key Rotation

**Support multiple active keys**:
```typescript
async function rotateAPIKey(oldKey: string): Promise<string> {
  const user = await validateAPIKey(oldKey);

  if (!user) {
    throw new Error('Invalid API key');
  }

  // Create new key
  const newKey = await createAPIKey(user.id);

  // Mark old key as deprecated (don't delete immediately)
  await db.apiKeys.update({
    where: { keyPrefix: oldKey.substring(0, 15) },
    data: {
      deprecated: true,
      deprecatedAt: new Date(),
      expiresAt: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), // 30 days grace period
    },
  });

  return newKey;
}
```

### Key Scopes

```typescript
interface APIKey {
  id: string;
  userId: string;
  keyHash: string;
  scopes: string[];  // ["read:users", "write:orders"]
  expiresAt: Date | null;
}

function requireAPIKeyScope(scope: string) {
  return async (req, res, next) => {
    const apiKey = req.apiKey; // Set by auth middleware

    if (!apiKey.scopes.includes(scope)) {
      return res.status(403).json({
        error: 'insufficient_scope',
        message: `This API key does not have the ${scope} scope`,
      });
    }

    next();
  };
}

app.get('/users', requireAPIKeyScope('read:users'), async (req, res) => {
  // Handler
});
```

### Usage

**Query parameter** (less secure, convenient for testing):
```http
GET /v1/users?api_key=sk_live_abc123
```

**Header** (recommended):
```http
GET /v1/users
Authorization: Bearer sk_live_abc123
```

Or custom header:
```http
GET /v1/users
X-API-Key: sk_live_abc123
```

## Role-Based Access Control (RBAC)

### Roles and Permissions

```typescript
interface Role {
  id: string;
  name: string;  // "admin", "editor", "viewer"
  permissions: Permission[];
}

interface Permission {
  id: string;
  resource: string;  // "users", "orders", "products"
  action: string;    // "read", "write", "delete"
}

// Example roles
const roles = {
  admin: {
    name: 'admin',
    permissions: [
      { resource: '*', action: '*' },  // All permissions
    ],
  },
  editor: {
    name: 'editor',
    permissions: [
      { resource: 'users', action: 'read' },
      { resource: 'users', action: 'write' },
      { resource: 'posts', action: 'read' },
      { resource: 'posts', action: 'write' },
      { resource: 'posts', action: 'delete' },
    ],
  },
  viewer: {
    name: 'viewer',
    permissions: [
      { resource: 'users', action: 'read' },
      { resource: 'posts', action: 'read' },
    ],
  },
};
```

### Permission Checking

```typescript
function hasPermission(
  user: User,
  resource: string,
  action: string
): boolean {
  const role = roles[user.role];

  return role.permissions.some(
    (perm) =>
      (perm.resource === '*' || perm.resource === resource) &&
      (perm.action === '*' || perm.action === action)
  );
}

function requirePermission(resource: string, action: string) {
  return (req, res, next) => {
    if (!hasPermission(req.user, resource, action)) {
      return res.status(403).json({
        error: 'forbidden',
        message: `Requires ${action} permission on ${resource}`,
      });
    }

    next();
  };
}

app.delete('/users/:id', requirePermission('users', 'delete'), async (req, res) => {
  // Handler
});
```

### Attribute-Based Access Control (ABAC)

**More granular**: Check user attributes, resource attributes, context

```typescript
interface Policy {
  resource: string;
  action: string;
  condition: (context: AccessContext) => boolean;
}

interface AccessContext {
  user: User;
  resource: any;
  environment: {
    ip: string;
    time: Date;
  };
}

const policies: Policy[] = [
  {
    resource: 'users',
    action: 'delete',
    condition: (ctx) =>
      ctx.user.role === 'admin' ||
      (ctx.user.role === 'editor' && ctx.resource.createdBy === ctx.user.id),
  },
  {
    resource: 'posts',
    action: 'write',
    condition: (ctx) =>
      ctx.user.role === 'admin' ||
      ctx.user.role === 'editor' ||
      (ctx.user.role === 'author' && ctx.resource.authorId === ctx.user.id),
  },
];

function checkAccess(context: AccessContext, resource: string, action: string): boolean {
  const policy = policies.find(
    (p) => p.resource === resource && p.action === action
  );

  if (!policy) {
    return false;
  }

  return policy.condition(context);
}
```

## Security Best Practices

### HTTPS/TLS Only

```typescript
// Redirect HTTP to HTTPS
app.use((req, res, next) => {
  if (!req.secure && process.env.NODE_ENV === 'production') {
    return res.redirect(`https://${req.hostname}${req.url}`);
  }
  next();
});

// Strict-Transport-Security header
app.use((req, res, next) => {
  res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
  next();
});
```

### Rate Limiting Per User

```typescript
import rateLimit from 'express-rate-limit';

const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // Limit each user to 100 requests per windowMs
  keyGenerator: (req) => req.user?.id || req.ip,
  handler: (req, res) => {
    res.status(429).json({
      error: 'too_many_requests',
      message: 'Rate limit exceeded. Try again later.',
    });
  },
});

app.use('/api/', limiter);
```

### Token Blacklisting

```typescript
// Blacklist JWT on logout
app.post('/logout', async (req, res) => {
  const token = req.headers.authorization?.split(' ')[1];
  const payload = jwt.decode(token);

  // Store token ID in blacklist until expiration
  await redis.setex(
    `blacklist:${payload.jti}`,
    payload.exp - Math.floor(Date.now() / 1000),
    '1'
  );

  res.json({ message: 'Logged out successfully' });
});

// Check blacklist
app.use(async (req, res, next) => {
  const token = req.headers.authorization?.split(' ')[1];
  const payload = jwt.decode(token);

  const isBlacklisted = await redis.get(`blacklist:${payload.jti}`);

  if (isBlacklisted) {
    return res.status(401).json({ error: 'Token has been revoked' });
  }

  next();
});
```

### IP Whitelisting

```typescript
const allowedIPs = ['192.168.1.1', '10.0.0.0/8'];

function ipWhitelist(req, res, next) {
  const clientIP = req.ip || req.connection.remoteAddress;

  if (!isIPAllowed(clientIP, allowedIPs)) {
    return res.status(403).json({
      error: 'forbidden',
      message: 'Access denied from this IP address',
    });
  }

  next();
}

app.use('/admin', ipWhitelist);
```

### CORS Configuration

```typescript
import cors from 'cors';

app.use(cors({
  origin: (origin, callback) => {
    const allowedOrigins = [
      'https://app.example.com',
      'https://dashboard.example.com',
    ];

    if (!origin || allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true,
  maxAge: 86400,
}));
```

## Best Practices Summary

✅ **Use OAuth 2.0 for third-party access**: Industry standard, secure delegation
✅ **Use JWT for stateless auth**: Microservices, mobile apps
✅ **Use API keys for service-to-service**: Simple, revocable
✅ **Always use HTTPS**: Encrypt all traffic
✅ **Hash API keys before storage**: bcrypt or scrypt
✅ **Use short-lived tokens**: 15 min - 1 hour for access tokens
✅ **Implement refresh tokens**: Avoid long-lived access tokens
✅ **Use asymmetric JWT signing**: RS256, not HS256
✅ **Validate all JWT claims**: iss, aud, exp, nbf
✅ **Implement rate limiting**: Per user, per IP
✅ **Use PKCE for mobile/SPA**: Prevents code interception
✅ **Support token revocation**: Blacklist or database check
✅ **Implement RBAC or ABAC**: Fine-grained permissions

❌ **Don't use Implicit Flow**: Use Authorization Code + PKCE
❌ **Don't use Resource Owner Password**: Use Authorization Code
❌ **Don't store passwords in JWT**: JWTs are not encrypted
❌ **Don't use long-lived JWTs**: Hard to revoke
❌ **Don't skip signature verification**: Always verify JWTs
❌ **Don't expose tokens in URLs**: Use headers
❌ **Don't reuse API keys**: Rotate compromised keys
❌ **Don't skip HTTPS**: Production must use TLS

## Additional Resources

- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [OAuth 2.0 Security Best Practices](https://tools.ietf.org/html/draft-ietf-oauth-security-topics)
- [JWT RFC 7519](https://tools.ietf.org/html/rfc7519)
- [PKCE RFC 7636](https://tools.ietf.org/html/rfc7636)
- [OAuth 2.0 Playground](https://www.oauth.com/playground/)
- [JWT.io Debugger](https://jwt.io/)
