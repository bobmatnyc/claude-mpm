# env-manager Workflows and Real-World Examples

This guide demonstrates real-world workflows for using the env-manager skill across different development scenarios, frameworks, and deployment platforms.

## Table of Contents

- [Workflow 1: Next.js Developer - Local to Vercel](#workflow-1-nextjs-developer---local-to-vercel)
- [Workflow 2: CI/CD Integration - GitHub Actions](#workflow-2-cicd-integration---github-actions)
- [Workflow 3: Team Onboarding - New Developer Setup](#workflow-3-team-onboarding---new-developer-setup)
- [Workflow 4: Security Audit - Finding Exposed Secrets](#workflow-4-security-audit---finding-exposed-secrets)
- [Workflow 5: Multi-Environment Management](#workflow-5-multi-environment-management)
- [Workflow 6: React + Vite Application](#workflow-6-react--vite-application)
- [Workflow 7: Express.js API Backend](#workflow-7-expressjs-api-backend)
- [Workflow 8: Flask Application Deployment](#workflow-8-flask-application-deployment)
- [Workflow 9: Emergency Debugging - Production Issues](#workflow-9-emergency-debugging---production-issues)
- [Workflow 10: Documentation Maintenance](#workflow-10-documentation-maintenance)

---

## Workflow 1: Next.js Developer - Local to Vercel

**Scenario:** You're developing a Next.js app locally and preparing to deploy to Vercel.

### Step 1: Initial Local Development

```bash
# You have .env.local for local development
# .env.local
DATABASE_URL=postgresql://localhost/myapp_dev
STRIPE_SECRET_KEY=sk_test_abc123xyz
STRIPE_PUBLISHABLE_KEY=pk_test_abc123xyz
NEXT_PUBLIC_API_URL=http://localhost:3000/api
NEXTAUTH_SECRET=local-dev-secret-32-chars-min
NEXTAUTH_URL=http://localhost:3000
```

### Step 2: Pre-Deployment Validation

```bash
# Validate for Next.js specific issues
cd src/claude_mpm/skills/bundled/infrastructure/env-manager
python3 scripts/validate_env.py /path/to/.env.local --framework nextjs
```

**Expected output:**
```
✅ Validation successful!
   - 6 variables validated
   - 0 errors
   - 0 warnings

✅ Framework check (nextjs): All NEXT_PUBLIC_ variables are safe
✅ No secrets detected in client-exposed variables
```

### Step 3: Check for Missing Variables

```bash
# Compare with .env.example to ensure nothing is missing
python3 scripts/validate_env.py /path/to/.env.local --compare-with /path/to/.env.example
```

**If variables are missing:**
```
❌ Missing variables:
   - VERCEL_URL (required in .env.example)

Add these to your .env.local before deploying
```

**Fix it:**
```bash
# Add to .env.local
echo "VERCEL_URL=https://myapp.vercel.app" >> /path/to/.env.local
```

### Step 4: Security Check Before Deployment

```bash
# Final security validation
python3 scripts/validate_env.py /path/to/.env.local --framework nextjs --strict
```

**If security issues found:**
```
⚠️  Warning: NEXT_PUBLIC_STRIPE_SECRET contains potential secret pattern
   - This variable is exposed to client-side code
   - Users will see this value in their browser
   - Fix: Use STRIPE_PUBLISHABLE_KEY for client-side instead
```

**Fix it:**
```bash
# Remove NEXT_PUBLIC_STRIPE_SECRET
# Keep only STRIPE_SECRET_KEY (server-side)
# Use STRIPE_PUBLISHABLE_KEY for client
```

### Step 5: Generate .env.example for Team

```bash
# Create documentation for other developers
python3 scripts/validate_env.py /path/to/.env.local --generate-example /path/to/.env.example

# Review and commit
cat /path/to/.env.example
git add .env.example
git commit -m "docs: update .env.example with new variables"
```

### Step 6: Deploy to Vercel

```bash
# Environment is validated ✅
# Deploy with confidence
vercel --prod

# Or via Vercel dashboard:
# - Copy variables from .env.local
# - Paste into Vercel project settings
# - Deploy
```

**Result:** Smooth deployment with no environment-related issues! 🎉

---

## Workflow 2: CI/CD Integration - GitHub Actions

**Scenario:** You want to validate environment variables in your CI/CD pipeline to catch issues before deployment.

### Step 1: Create GitHub Actions Workflow

Create `.github/workflows/validate-env.yml`:

```yaml
name: Validate Environment Variables

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  validate-env:
    runs-on: ubuntu-latest
    name: Validate .env.example

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Validate .env.example structure
        run: |
          cd src/claude_mpm/skills/bundled/infrastructure/env-manager
          python3 scripts/validate_env.py \
            ${{ github.workspace }}/.env.example \
            --strict \
            --json > validation.json
        continue-on-error: false

      - name: Check validation results
        run: |
          cat validation.json
          # Exit with code from validation
          if [ $? -ne 0 ]; then
            echo "❌ Environment validation failed"
            exit 1
          fi
          echo "✅ Environment validation passed"

      - name: Validate framework-specific rules (Next.js)
        if: hashFiles('next.config.js') != ''
        run: |
          cd src/claude_mpm/skills/bundled/infrastructure/env-manager
          python3 scripts/validate_env.py \
            ${{ github.workspace }}/.env.example \
            --framework nextjs \
            --strict

      - name: Upload validation report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: env-validation-report
          path: validation.json
```

### Step 2: Test Locally

```bash
# Simulate what CI will do
cd src/claude_mpm/skills/bundled/infrastructure/env-manager
python3 scripts/validate_env.py /path/to/.env.example --strict --json > validation.json

# Check results
cat validation.json
echo "Exit code: $?"
```

### Step 3: Handle Validation Failures in CI

If validation fails in CI:

```
❌ Validation failed:
   - Line 12: DATABASE_URL: Empty value not allowed
   - Line 15: API_KEY: Invalid variable name (use UPPERCASE_WITH_UNDERSCORES)
```

**Fix in your repository:**
```bash
# Fix .env.example
vim .env.example

# Re-validate locally
python3 scripts/validate_env.py .env.example --strict

# Commit fixes
git add .env.example
git commit -m "fix: correct environment variable issues"
git push
```

### Step 4: Advanced - Validate Multiple Environments

```yaml
# In GitHub Actions
- name: Validate all environment files
  run: |
    for env_file in .env.example .env.production.example .env.staging.example; do
      if [ -f "$env_file" ]; then
        echo "Validating $env_file..."
        python3 scripts/validate_env.py "$env_file" --strict --json
      fi
    done
```

**Result:** Automated environment validation on every PR and push! 🚀

---

## Workflow 3: Team Onboarding - New Developer Setup

**Scenario:** A new developer joins your team and needs to set up their local environment.

### Step 1: Clone Repository

```bash
git clone https://github.com/yourteam/yourproject.git
cd yourproject
```

### Step 2: Copy .env.example

```bash
# Create local environment file
cp .env.example .env.local

# Open and review required variables
cat .env.example
```

**Example .env.example:**
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/dbname  # pragma: allowlist secret

# Authentication
NEXTAUTH_SECRET=your-secret-here-min-32-chars
NEXTAUTH_URL=http://localhost:3000

# Stripe (get from dashboard)
STRIPE_SECRET_KEY=sk_test_your_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_key_here

# API
NEXT_PUBLIC_API_URL=http://localhost:3000/api
```

### Step 3: Fill in Values

New developer fills in actual values:

```bash
# .env.local (filled in)
DATABASE_URL=postgresql://postgres:mypassword@localhost/myapp_dev  # pragma: allowlist secret
NEXTAUTH_SECRET=abc123xyz789abc123xyz789abc123xyz789
NEXTAUTH_URL=http://localhost:3000
STRIPE_SECRET_KEY=sk_test_51A1B2C3D4E5F6G7H8I9J0
STRIPE_PUBLISHABLE_KEY=pk_test_51K1L2M3N4O5P6Q7R8S9T0
NEXT_PUBLIC_API_URL=http://localhost:3000/api
```

### Step 4: Validate Setup

```bash
# Check if all required variables are present
cd src/claude_mpm/skills/bundled/infrastructure/env-manager
python3 scripts/validate_env.py /path/to/.env.local --compare-with /path/to/.env.example
```

**If missing variables:**
```
❌ Missing variables:
   - STRIPE_WEBHOOK_SECRET (required in .env.example)

⚠️  Extra variables not in .env.example:
   - DEBUG_MODE (consider adding to .env.example or removing)
```

### Step 5: Validate Values

```bash
# Validate structure and framework-specific rules
python3 scripts/validate_env.py /path/to/.env.local --framework nextjs
```

**If issues found:**
```
❌ Error on line 2: NEXTAUTH_SECRET: Value too short (minimum 32 characters)
⚠️  Warning: DATABASE_URL uses localhost (expected for local dev)
```

### Step 6: Fix and Re-validate

```bash
# Fix issues
vim .env.local

# Re-validate
python3 scripts/validate_env.py /path/to/.env.local --framework nextjs --compare-with .env.example
```

**Success:**
```
✅ Validation successful!
   - 6 variables validated
   - 0 errors
   - 0 warnings
✅ All required variables present (compared with .env.example)
✅ Ready for development!
```

### Step 7: Start Development

```bash
# Environment is properly configured ✅
npm run dev
```

**Result:** New developer onboarded with correct environment in <10 minutes! 🎉

---

## Workflow 4: Security Audit - Finding Exposed Secrets

**Scenario:** You need to perform a security audit to ensure no secrets are exposed in client-side code.

### Step 1: Audit Next.js Application

```bash
# Check for secrets in NEXT_PUBLIC_ variables
cd src/claude_mpm/skills/bundled/infrastructure/env-manager
python3 scripts/validate_env.py /path/to/.env.local --framework nextjs --strict
```

### Step 2: Review Security Warnings

**Example output:**
```
⚠️  Security Warning (Line 8): NEXT_PUBLIC_STRIPE_SECRET
    - Contains potential secret pattern
    - This variable is exposed to client-side code
    - Users can see this value in browser DevTools

⚠️  Security Warning (Line 12): NEXT_PUBLIC_API_TOKEN
    - Contains potential secret pattern (token)
    - Client-exposed variable with secret-like value
```

### Step 3: Investigate Each Warning

```bash
# Review the actual variables
grep "NEXT_PUBLIC_" .env.local
```

**Found issues:**
```bash
NEXT_PUBLIC_STRIPE_SECRET=sk_live_abc123xyz  # ❌ SECRET KEY EXPOSED!
NEXT_PUBLIC_API_TOKEN=secret_token_xyz       # ❌ PRIVATE TOKEN EXPOSED!
NEXT_PUBLIC_API_URL=https://api.example.com  # ✅ Safe (just a URL)
```

### Step 4: Fix Security Issues

```bash
# Fix .env.local
# BEFORE (❌ Insecure):
NEXT_PUBLIC_STRIPE_SECRET=sk_live_abc123xyz
NEXT_PUBLIC_API_TOKEN=secret_token_xyz

# AFTER (✅ Secure):
STRIPE_SECRET_KEY=sk_live_abc123xyz           # Server-side only
NEXT_PUBLIC_STRIPE_PUBLISHABLE=pk_live_xyz    # Safe for client
API_TOKEN=secret_token_xyz                     # Server-side only
NEXT_PUBLIC_API_URL=https://api.example.com   # Safe for client
```

### Step 5: Update Application Code

```javascript
// BEFORE (❌ Using exposed secret)
const stripe = new Stripe(process.env.NEXT_PUBLIC_STRIPE_SECRET);

// AFTER (✅ Secure approach)
// In API route (server-side):
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

// In client code:
const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE);
```

### Step 6: Re-validate

```bash
# Confirm security issues are resolved
python3 scripts/validate_env.py .env.local --framework nextjs --strict
```

**Success:**
```
✅ Validation successful!
   - 8 variables validated
   - 0 errors
   - 0 warnings
✅ No secrets detected in client-exposed variables
✅ Security audit passed
```

### Step 7: Rotate Exposed Secrets

```bash
# If secrets were committed to git or deployed:
# 1. Rotate all exposed secrets immediately
# 2. Update .env.local with new secrets
# 3. Update deployment platform (Vercel, etc.)
# 4. Deploy new version
```

**Result:** Security vulnerabilities identified and fixed before production exposure! 🔒

---

## Workflow 5: Multi-Environment Management

**Scenario:** You're managing multiple environments (development, staging, production) with different configurations.

### Environment Structure

```
.env.example          # Documentation (committed)
.env.local            # Local development (gitignored)
.env.staging          # Staging environment (gitignored)
.env.production       # Production environment (gitignored)
```

### Step 1: Validate Each Environment

```bash
cd src/claude_mpm/skills/bundled/infrastructure/env-manager

# Validate development
python3 scripts/validate_env.py /path/to/.env.local --framework nextjs --json > dev-validation.json

# Validate staging
python3 scripts/validate_env.py /path/to/.env.staging --framework nextjs --json > staging-validation.json

# Validate production
python3 scripts/validate_env.py /path/to/.env.production --framework nextjs --strict --json > prod-validation.json
```

### Step 2: Ensure Consistency Across Environments

```bash
# Check that all environments have the same variables (different values OK)
comm -3 \
  <(grep -v '^#' .env.local | cut -d'=' -f1 | sort) \
  <(grep -v '^#' .env.production | cut -d'=' -f1 | sort)
```

**If differences found:**
```
Variables only in .env.local:
  DEBUG_MODE

Variables only in .env.production:
  ANALYTICS_KEY
```

### Step 3: Create Environment-Specific Validation

```bash
# production.env.schema - Expected vars in production
cat > production.env.schema << 'EOF'
DATABASE_URL
REDIS_URL
STRIPE_SECRET_KEY
STRIPE_PUBLISHABLE_KEY
NEXT_PUBLIC_API_URL
NEXTAUTH_SECRET
NEXTAUTH_URL
ANALYTICS_KEY
SENTRY_DSN
EOF

# Validate production has all required vars
python3 scripts/validate_env.py .env.production --compare-with production.env.schema
```

### Step 4: Validate Before Deployment to Each Environment

```bash
# Before deploying to staging
python3 scripts/validate_env.py .env.staging --framework nextjs --strict
if [ $? -eq 0 ]; then
  echo "✅ Deploying to staging..."
  deploy_to_staging
fi

# Before deploying to production
python3 scripts/validate_env.py .env.production --framework nextjs --strict
if [ $? -eq 0 ]; then
  echo "✅ Deploying to production..."
  deploy_to_production
fi
```

### Step 5: Generate Environment-Specific Documentation

```bash
# Generate .env.example from production (sanitized)
python3 scripts/validate_env.py .env.production --generate-example .env.example

# Add environment-specific comments
cat > .env.example << 'EOF'
# Environment variables for MyApp
# Copy to .env.local and fill in values

# Database (use local for dev, managed DB for prod)
DATABASE_URL=postgresql://user:password@localhost/dbname

# Redis (use local for dev, managed Redis for prod)
REDIS_URL=redis://localhost:6379

# Stripe (use test keys for dev, live keys for prod)
STRIPE_SECRET_KEY=sk_test_your_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_key_here
NEXT_PUBLIC_STRIPE_PUBLISHABLE=pk_test_your_key_here

# API
NEXT_PUBLIC_API_URL=http://localhost:3000/api

# NextAuth
NEXTAUTH_SECRET=generate-with-openssl-rand-base64-32
NEXTAUTH_URL=http://localhost:3000

# Production only
ANALYTICS_KEY=your_analytics_key_here
SENTRY_DSN=your_sentry_dsn_here
EOF

git add .env.example
git commit -m "docs: update .env.example with environment-specific guidance"
```

**Result:** Consistent, validated environments across development, staging, and production! 🌍

---

## Workflow 6: React + Vite Application

**Scenario:** You're building a React app with Vite and need to manage environment variables correctly.

### Step 1: Create Vite Environment Files

```bash
# .env.local (local development)
VITE_API_URL=http://localhost:3001/api
VITE_APP_NAME=MyApp Dev
API_SECRET=dev-secret-key-not-exposed
```

### Step 2: Validate for Vite

```bash
cd src/claude_mpm/skills/bundled/infrastructure/env-manager
python3 scripts/validate_env.py /path/to/.env.local --framework vite
```

**Vite-specific checks:**
```
✅ Validation successful!
   - 3 variables validated
   - 0 errors
   - 0 warnings

ℹ️  Vite framework notes:
   - VITE_* variables are exposed to client code
   - Other variables (API_SECRET) are server-side only
   - Vite replaces import.meta.env.VITE_* at build time
```

### Step 3: Check for Exposed Secrets

```bash
# Strict mode to catch security issues
python3 scripts/validate_env.py .env.local --framework vite --strict
```

**If secret detected in VITE_ variable:**
```
⚠️  Warning: VITE_API_KEY contains potential secret pattern
   - This variable is exposed to client-side code via import.meta.env
   - Users can see this value in production build
   - Fix: Remove VITE_ prefix or use public API key
```

### Step 4: Production Build Validation

```bash
# .env.production
VITE_API_URL=https://api.production.com/api
VITE_APP_NAME=MyApp
API_SECRET=production-secret-key

# Validate before build
python3 scripts/validate_env.py .env.production --framework vite --strict
```

### Step 5: Vite-Specific Usage in Code

```javascript
// ✅ Correct: Using VITE_ prefixed vars
console.log(import.meta.env.VITE_API_URL);  // Accessible in client
console.log(import.meta.env.VITE_APP_NAME); // Accessible in client

// ❌ Won't work: Non-VITE_ vars not accessible in client
console.log(import.meta.env.API_SECRET);    // undefined in client

// ✅ Use API_SECRET in server/build scripts only
```

**Result:** Properly validated Vite environment with no exposed secrets! ⚡

---

## Workflow 7: Express.js API Backend

**Scenario:** You're building an Express.js API and need to manage environment variables for different deployment scenarios.

### Step 1: Create .env for Express

```bash
# .env
NODE_ENV=development
PORT=3000
DATABASE_URL=postgresql://localhost/myapp_dev
REDIS_URL=redis://localhost:6379
JWT_SECRET=your-jwt-secret-min-32-chars
API_KEY=your-api-key
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Step 2: Validate for Node.js

```bash
cd src/claude_mpm/skills/bundled/infrastructure/env-manager
python3 scripts/validate_env.py /path/to/.env --framework nodejs
```

**Node.js-specific checks:**
```
✅ Validation successful!
   - 7 variables validated
   - 0 errors
   - 0 warnings

ℹ️  Node.js best practices:
   - NODE_ENV detected: development
   - PORT detected: 3000
   - All variables available via process.env
```

### Step 3: Validate Production Configuration

```bash
# .env.production
NODE_ENV=production
PORT=8080
DATABASE_URL=postgresql://prod-host/myapp_prod
REDIS_URL=redis://prod-redis:6379
JWT_SECRET=production-secret-min-32-characters-long
API_KEY=production-api-key-xyz
ALLOWED_ORIGINS=https://myapp.com,https://www.myapp.com

# Validate
python3 scripts/validate_env.py .env.production --framework nodejs --strict
```

### Step 4: Check Environment Completeness

```bash
# Ensure production has all dev variables (and vice versa)
python3 scripts/validate_env.py .env.production --compare-with .env

# Generate .env.example for team
python3 scripts/validate_env.py .env --generate-example .env.example
```

### Step 5: Express.js Application Integration

```javascript
// config/env.js
require('dotenv').config();

const requiredEnvVars = [
  'NODE_ENV',
  'PORT',
  'DATABASE_URL',
  'REDIS_URL',
  'JWT_SECRET',
  'API_KEY',
  'ALLOWED_ORIGINS'
];

// Runtime validation
requiredEnvVars.forEach(varName => {
  if (!process.env[varName]) {
    console.error(`❌ Missing required environment variable: ${varName}`);
    console.error('Run: python3 scripts/validate_env.py .env --compare-with .env.example');
    process.exit(1);
  }
});

module.exports = {
  nodeEnv: process.env.NODE_ENV,
  port: parseInt(process.env.PORT, 10),
  databaseUrl: process.env.DATABASE_URL,
  redisUrl: process.env.REDIS_URL,
  jwtSecret: process.env.JWT_SECRET,
  apiKey: process.env.API_KEY,
  allowedOrigins: process.env.ALLOWED_ORIGINS.split(',')
};
```

**Result:** Robust Express.js API with validated environment configuration! 🚀

---

## Workflow 8: Flask Application Deployment

**Scenario:** You're deploying a Flask application and need to ensure environment variables are properly configured.

### Step 1: Create Flask .env

```bash
# .env
FLASK_APP=app.py
FLASK_ENV=development
DATABASE_URL=postgresql://localhost/flask_app
SECRET_KEY=your-secret-key-min-32-chars
REDIS_URL=redis://localhost:6379
MAIL_SERVER=localhost
MAIL_PORT=1025
```

### Step 2: Validate for Flask

```bash
cd src/claude_mpm/skills/bundled/infrastructure/env-manager
python3 scripts/validate_env.py /path/to/.env --framework flask
```

**Flask-specific checks:**
```
✅ Validation successful!
   - 7 variables validated
   - 0 errors
   - 0 warnings

ℹ️  Flask framework notes:
   - FLASK_APP detected: app.py
   - FLASK_ENV detected: development
   - SECRET_KEY detected (required for sessions)
   - DATABASE_URL detected (SQLAlchemy format)
```

### Step 3: Production Environment

```bash
# .env.production
FLASK_APP=app.py
FLASK_ENV=production
DATABASE_URL=postgresql://prod-db/flask_app
SECRET_KEY=production-secret-key-min-32-characters
REDIS_URL=redis://prod-redis:6379
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USERNAME=apikey
MAIL_PASSWORD=your-sendgrid-api-key

# Validate
python3 scripts/validate_env.py .env.production --framework flask --strict
```

### Step 4: Check for Security Issues

```bash
# Ensure FLASK_ENV is production
grep "FLASK_ENV=production" .env.production || echo "⚠️  Warning: FLASK_ENV should be 'production'"

# Validate SECRET_KEY length
python3 scripts/validate_env.py .env.production --framework flask --strict
```

### Step 5: Flask Application Configuration

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    REDIS_URL = os.getenv('REDIS_URL')

    # Mail configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False

# Validate required variables
required_vars = ['SECRET_KEY', 'DATABASE_URL', 'REDIS_URL']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(missing_vars)}\n"
        "Run: python3 scripts/validate_env.py .env --compare-with .env.example"
    )
```

**Result:** Production-ready Flask app with validated environment! 🐍

---

## Workflow 9: Emergency Debugging - Production Issues

**Scenario:** Your app works locally but fails in production with environment-related errors.

### Step 1: Reproduce Locally

```bash
# Copy production environment (sanitized secrets)
cp .env.production .env.production.debug

# Validate structure
cd src/claude_mpm/skills/bundled/infrastructure/env-manager
python3 scripts/validate_env.py .env.production.debug --framework nextjs --strict
```

### Step 2: Compare Environments

```bash
# Compare local vs production
diff <(grep -v '^#' .env.local | cut -d'=' -f1 | sort) \
     <(grep -v '^#' .env.production.debug | cut -d'=' -f1 | sort)
```

**Found differences:**
```
Missing in production:
  NEXT_PUBLIC_API_URL

Extra in production:
  VERCEL_URL
```

### Step 3: Identify the Issue

```bash
# Production environment is missing NEXT_PUBLIC_API_URL
# This causes API calls to fail

# Add to production
echo "NEXT_PUBLIC_API_URL=https://api.production.com" >> .env.production
```

### Step 4: Validate Fix

```bash
# Validate updated production config
python3 scripts/validate_env.py .env.production --framework nextjs --compare-with .env.local
```

### Step 5: Deploy Fix

```bash
# Update Vercel environment variables
vercel env add NEXT_PUBLIC_API_URL production
# Enter value: https://api.production.com

# Redeploy
vercel --prod
```

### Step 6: Prevent Future Issues

```bash
# Create pre-deployment validation script
cat > scripts/pre-deploy-check.sh << 'EOF'
#!/bin/bash
set -e

echo "🔍 Validating production environment..."

cd src/claude_mpm/skills/bundled/infrastructure/env-manager

# Validate production .env
python3 scripts/validate_env.py .env.production --framework nextjs --strict

# Compare with local to find missing vars
python3 scripts/validate_env.py .env.production --compare-with .env.local

if [ $? -eq 0 ]; then
  echo "✅ Environment validation passed"
  echo "✅ Safe to deploy"
  exit 0
else
  echo "❌ Environment validation failed"
  echo "❌ Fix issues before deploying"
  exit 1
fi
EOF

chmod +x scripts/pre-deploy-check.sh

# Add to deployment process
# Run this before every production deployment
```

**Result:** Production issue identified and fixed, prevention process in place! 🔧

---

## Workflow 10: Documentation Maintenance

**Scenario:** Your team adds new environment variables regularly, and .env.example gets out of sync.

### Step 1: Automated .env.example Generation

```bash
# Generate from current .env.local
cd src/claude_mpm/skills/bundled/infrastructure/env-manager
python3 scripts/validate_env.py /path/to/.env.local --generate-example /path/to/.env.example
```

**Generated .env.example:**
```bash
# Auto-generated from .env.local
# Last updated: 2025-11-13

DATABASE_URL=postgresql://user:password@localhost/dbname
REDIS_URL=redis://localhost:6379
STRIPE_SECRET_KEY=your_stripe_secret_key_here
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key_here
NEXT_PUBLIC_API_URL=http://localhost:3000/api
NEXTAUTH_SECRET=your_nextauth_secret_here_min_32_chars
NEXTAUTH_URL=http://localhost:3000
```

### Step 2: Add Helpful Comments

```bash
# Enhance .env.example with documentation
cat > .env.example << 'EOF'
# Environment Variables for MyApp
# Copy to .env.local and fill in actual values
# Last updated: 2025-11-13

# Database Configuration
# Get connection string from your local PostgreSQL installation
# Format: postgresql://username:password@host:port/database
DATABASE_URL=postgresql://user:password@localhost/dbname

# Redis Configuration (for caching and sessions)
# Local: redis://localhost:6379
# Production: Get from Redis Cloud or managed service
REDIS_URL=redis://localhost:6379

# Stripe Payment Integration
# Get from: https://dashboard.stripe.com/apikeys
# Use test keys (sk_test_...) for development
# Use live keys (sk_live_...) for production
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key_here

# API Configuration
# Development: http://localhost:3000/api
# Production: https://your-domain.com/api
NEXT_PUBLIC_API_URL=http://localhost:3000/api

# NextAuth Configuration
# Generate secret: openssl rand -base64 32
# Must be at least 32 characters
NEXTAUTH_SECRET=your_nextauth_secret_here_min_32_chars

# NextAuth URL
# Must match your application URL
# Development: http://localhost:3000
# Production: https://your-domain.com
NEXTAUTH_URL=http://localhost:3000
EOF
```

### Step 3: Set Up Git Pre-commit Hook

```bash
# Create pre-commit hook to keep .env.example in sync
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash

# Check if .env.local changed
if git diff --cached --name-only | grep -q ".env.local"; then
  echo "📝 .env.local changed, checking if .env.example needs update..."

  cd src/claude_mpm/skills/bundled/infrastructure/env-manager

  # Compare variable names
  local_vars=$(grep -v '^#' ../../../../../../.env.local | cut -d'=' -f1 | sort)
  example_vars=$(grep -v '^#' ../../../../../../.env.example | cut -d'=' -f1 | sort)

  if [ "$local_vars" != "$example_vars" ]; then
    echo "⚠️  .env.example is out of sync with .env.local"
    echo "Run: python3 scripts/validate_env.py .env.local --generate-example .env.example"
    echo "Or update .env.example manually"
    exit 1
  fi

  echo "✅ .env.example is in sync"
fi

exit 0
EOF

chmod +x .git/hooks/pre-commit
```

### Step 4: Regular Validation

```bash
# Weekly task: Validate .env.example is still accurate
python3 scripts/validate_env.py .env.example --framework nextjs --strict

# Ensure all team members can use it
python3 scripts/validate_env.py .env.example --compare-with .env.local
```

### Step 5: Team Documentation

Add to README.md:

```markdown
## Environment Setup

1. Copy environment template:
   ```bash
   cp .env.example .env.local
   ```

2. Fill in actual values:
   - See comments in .env.example for where to get each value
   - Use test/development keys for local development
   - Never commit .env.local to git

3. Validate your configuration:
   ```bash
   cd src/claude_mpm/skills/bundled/infrastructure/env-manager
   python3 scripts/validate_env.py ../../../../../../.env.local \
     --framework nextjs \
     --compare-with ../../../../../../.env.example
   ```

4. Start development:
   ```bash
   npm run dev
   ```

### Updating Environment Variables

When adding new environment variables:

1. Add to .env.local
2. Update .env.example (or regenerate):
   ```bash
   python3 scripts/validate_env.py .env.local --generate-example .env.example
   ```
3. Add helpful comments to .env.example
4. Commit .env.example (never .env.local)
5. Notify team to update their .env.local
```

**Result:** Maintained, documented, and validated environment configuration! 📚

---

## Summary

These workflows demonstrate how env-manager solves real-world environment variable management challenges across:

- **Frameworks**: Next.js, React + Vite, Express.js, Flask
- **Platforms**: Vercel, Railway, Heroku, local development
- **Scenarios**: Development, CI/CD, onboarding, security, debugging, documentation

**Key Takeaways:**

1. **Always validate before deploying** - Catch issues locally
2. **Use framework-specific validation** - Get targeted warnings
3. **Compare with .env.example** - Ensure completeness
4. **Never expose secrets in client variables** - Security first
5. **Automate validation in CI/CD** - Prevent production issues
6. **Keep .env.example in sync** - Enable smooth onboarding
7. **Use strict mode for production** - Enforce quality gates

**Next Steps:**

- Integrate env-manager into your development workflow
- Add validation to your CI/CD pipeline
- Set up pre-deployment checks
- Train your team on best practices
- Document your project-specific environment requirements

For more information:
- **Skill Documentation**: [README.md](../src/claude_mpm/skills/bundled/infrastructure/env-manager/README.md)
- **Agent Integration**: [INTEGRATION.md](../src/claude_mpm/skills/bundled/infrastructure/env-manager/INTEGRATION.md)
- **Reference Docs**: [references/](../src/claude_mpm/skills/bundled/infrastructure/env-manager/references/)
