# Next.js Environment Variable Structure

Complete guide to Next.js environment variable management.

## File Structure

```
my-nextjs-app/
├── .env                      # Shared defaults (committed)
├── .env.local               # Local secrets (gitignored)
├── .env.development         # Development defaults (committed)
├── .env.development.local   # Local dev overrides (gitignored)
├── .env.production          # Production defaults (committed)
├── .env.production.local    # Production secrets (gitignored)
├── .env.test                # Test environment (committed)
└── .env.example             # Documentation (committed)
```

## File Precedence

Next.js loads files in this order (higher = higher precedence):

1. `.env.$(NODE_ENV).local` (e.g., `.env.production.local`)
2. `.env.local` (not loaded in test environment)
3. `.env.$(NODE_ENV)` (e.g., `.env.production`)
4. `.env`

**Example**: In production, if `DATABASE_URL` is defined in both `.env` and `.env.production.local`, the value from `.env.production.local` wins.

## Variable Types

### Client-Side Variables (NEXT_PUBLIC_*)

Exposed to the browser. Must prefix with `NEXT_PUBLIC_`.

```bash
# .env.local
NEXT_PUBLIC_API_URL=https://api.example.com
NEXT_PUBLIC_ANALYTICS_ID=UA-123456789
NEXT_PUBLIC_SITE_NAME=My Awesome Site
NEXT_PUBLIC_ENABLE_FEATURE_X=true
```

**Access in code**:
```javascript
// Works in both client and server
const apiUrl = process.env.NEXT_PUBLIC_API_URL;

// Usage in components
export default function MyComponent() {
  return <div>API: {process.env.NEXT_PUBLIC_API_URL}</div>;
}
```

**⚠️ Security Warning**: NEVER put secrets in `NEXT_PUBLIC_*` variables!

```bash
# ❌ WRONG - Secret exposed to browser
NEXT_PUBLIC_API_SECRET=sk_live_abc123

# ✅ CORRECT - Secret only on server
API_SECRET=sk_live_abc123
```

### Server-Side Variables

Only available in server-side code (API routes, getServerSideProps, etc.).

```bash
# .env.local
DATABASE_URL=postgres://localhost:5432/mydb
JWT_SECRET=super-secret-jwt-key-do-not-expose
STRIPE_SECRET_KEY=sk_live_abc123
SMTP_PASSWORD=email-password-here
```

**Access in code**:
```javascript
// ✅ Works in API routes
export default async function handler(req, res) {
  const dbUrl = process.env.DATABASE_URL;
  // Use dbUrl...
}

// ✅ Works in getServerSideProps
export async function getServerSideProps() {
  const secret = process.env.JWT_SECRET;
  // Use secret...
}

// ❌ Does NOT work in components (browser)
export default function MyComponent() {
  const dbUrl = process.env.DATABASE_URL; // undefined!
}
```

## Example Files

### .env (Committed - Shared Defaults)

```bash
# Shared defaults for all environments
NEXT_PUBLIC_APP_NAME=My Next.js App
NEXT_PUBLIC_DEFAULT_LOCALE=en

# Database (overridden in .env.local)
DATABASE_URL=postgres://localhost:5432/dev

# External services (no secrets)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_abc123
```

### .env.local (Gitignored - Local Secrets)

```bash
# Local development secrets
DATABASE_URL=postgres://localhost:5432/mylocal
JWT_SECRET=dev-jwt-secret-change-in-production
STRIPE_SECRET_KEY=sk_test_local_key

# Local overrides
NEXT_PUBLIC_API_URL=http://localhost:4000/api
```

### .env.production (Committed - Production Defaults)

```bash
# Production environment defaults
NEXT_PUBLIC_API_URL=https://api.production.com
NEXT_PUBLIC_ANALYTICS_ID=UA-PROD-123456

# These will be overridden by platform env vars
DATABASE_URL=set-this-in-vercel
JWT_SECRET=set-this-in-vercel
```

### .env.example (Committed - Documentation)

```bash
# Copy this to .env.local and fill in actual values

# Client-side (browser accessible)
NEXT_PUBLIC_API_URL=https://api.example.com
NEXT_PUBLIC_ANALYTICS_ID=your-analytics-id
NEXT_PUBLIC_SITE_NAME=Your Site Name

# Server-side (secrets)
DATABASE_URL=postgres://user:password@host:5432/database  # pragma: allowlist secret
JWT_SECRET=your-jwt-secret-32-chars-minimum
STRIPE_SECRET_KEY=sk_live_your_stripe_key
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-smtp-password
```

## Common Patterns

### Database Configuration

```bash
# Development (.env.local)
DATABASE_URL=postgres://localhost:5432/myapp_dev

# Production (Vercel Environment Variables)
DATABASE_URL=postgres://user:pass@prod-host:5432/myapp_prod  # pragma: allowlist secret
```

### API Keys

```bash
# Public keys (client-side)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_abc123

# Secret keys (server-side only)
STRIPE_SECRET_KEY=sk_live_xyz789
```

### Feature Flags

```bash
# Toggle features
NEXT_PUBLIC_ENABLE_DARK_MODE=true
NEXT_PUBLIC_ENABLE_BETA_FEATURES=false
```

## Deployment to Vercel

### Step 1: Add Environment Variables in Vercel

1. Go to Project Settings → Environment Variables
2. Add each variable:
   - **Key**: `DATABASE_URL`
   - **Value**: `postgres://...`
   - **Environments**: Production, Preview, Development

### Step 2: Separate Client vs Server Variables

Vercel automatically exposes `NEXT_PUBLIC_*` variables at build time.

```bash
# Vercel automatically handles:
NEXT_PUBLIC_API_URL=https://api.example.com  # ✅ Exposed to browser

# Server-only:
DATABASE_URL=postgres://...  # ✅ Not exposed to browser
```

### Step 3: Rebuild After Changing NEXT_PUBLIC_ Variables

⚠️ Important: `NEXT_PUBLIC_*` variables are **baked into the build** at build time.

If you change them in Vercel, you must **redeploy**:

```bash
vercel --prod
```

## Validation Workflow

### 1. Validate Local Environment

```bash
# Check structure
python scripts/validate_env.py .env.local --framework nextjs

# Compare with .env.example
python scripts/validate_env.py .env.local --compare-with .env.example

# Check for security issues
python scripts/scan_exposed.py --check-gitignore
```

### 2. Check File Precedence

```bash
# List all .env files
ls -la .env*

# Validate each
for file in .env*; do
  echo "=== $file ==="
  python scripts/validate_env.py $file --framework nextjs
done
```

### 3. Sync to Vercel

```bash
# Compare local vs Vercel
python scripts/sync_secrets.py --platform vercel --compare

# Sync (dry-run first)
python scripts/sync_secrets.py --platform vercel --sync --dry-run

# Actually sync
python scripts/sync_secrets.py --platform vercel --sync --confirm
```

## Common Issues

### Issue: Variable Undefined in Browser

**Symptom**: `process.env.MY_VAR` is `undefined` in component.

**Solution**: Add `NEXT_PUBLIC_` prefix:

```bash
# ❌ Wrong
API_URL=https://api.example.com

# ✅ Correct
NEXT_PUBLIC_API_URL=https://api.example.com
```

### Issue: Changed Variable Not Reflected

**Symptom**: Changed `NEXT_PUBLIC_*` variable in Vercel, but app still uses old value.

**Solution**: Redeploy (variables are baked into build):

```bash
vercel --prod
```

### Issue: Works Locally, Not in Production

**Symptom**: App works with `.env.local`, fails in production.

**Solution**: Ensure all variables from `.env.local` are set in Vercel:

```bash
# Compare
python scripts/sync_secrets.py --platform vercel --compare

# Find missing vars and add them in Vercel UI
```

## Security Checklist

- [ ] `.env.local` in `.gitignore`
- [ ] `.env.*.local` in `.gitignore`
- [ ] No secrets in `NEXT_PUBLIC_*` variables
- [ ] No `.env` files committed with real secrets
- [ ] `.env.example` has structure, not actual values
- [ ] Secrets set directly in Vercel (not in committed files)

## References

- [Next.js Environment Variables Documentation](https://nextjs.org/docs/basic-features/environment-variables)
- [Vercel Environment Variables](https://vercel.com/docs/environment-variables)

---

**Related**: [validation.md](../references/validation.md) | [security.md](../references/security.md) | [frameworks.md](../references/frameworks.md)
