---
name: env-manager
description: Environment variable validation, synchronization, and management across local development, CI/CD, and deployment platforms
version: 1.0.0
category: infrastructure
progressive_disclosure:
  entry_point:
    summary: "Validate, synchronize, and secure environment variables across local dev, CI/CD, and deployment platforms with framework-specific support"
    when_to_use: "When managing .env files, deploying to Vercel/Railway/Heroku, syncing with secret managers, or troubleshooting env-related issues"
    quick_start: "1. Validate local .env 2. Check security 3. Sync to platform 4. Verify deployment 5. Generate documentation"
  references:
    - validation.md
    - security.md
    - synchronization.md
    - frameworks.md
    - troubleshooting.md
author: Claude MPM Team
license: MIT
requires_tools:
  - bash
  - python
tags:
  - environment-variables
  - deployment
  - security
  - devops
  - nextjs
  - vercel
  - railway
context_limit: 800
---

# Environment Variable Manager

## Overview

Manage environment variables systematically across local development, CI/CD pipelines, and deployment platforms. Prevent common issues like missing variables, exposed secrets, platform misconfigurations, and framework-specific gotchas.

**Core capabilities:**
- **Validation**: Check structure, completeness, naming conventions
- **Security**: Scan for exposed secrets, validate .gitignore coverage
- **Synchronization**: Sync with deployment platforms and secret managers
- **Framework Support**: Next.js, Express, Flask, Django patterns
- **Documentation**: Auto-generate .env.example and setup guides

## When to Use This Skill

Activate when:
- Setting up new project environment configuration
- Deploying to Vercel, Railway, Heroku, or other platforms
- Troubleshooting "works locally but not in production"
- Managing secrets across multiple environments
- Syncing variables with 1Password, AWS Secrets Manager
- Creating .env.example documentation
- Onboarding new developers (environment setup)
- Migrating between deployment platforms
- Framework-specific env configuration (Next.js NEXT_PUBLIC_ prefix)

## Core Principles

1. **Never Log Secrets**: All operations must NEVER display actual secret values
2. **Validate Before Deploy**: Catch env issues locally, not in production
3. **Framework-Aware**: Respect framework conventions (Next.js, Express, Flask)
4. **Platform-Specific**: Generate correct configs for each deployment platform
5. **Security First**: Scan for exposed secrets, validate .gitignore

## Quick Start

### Validation Workflow
```bash
# 1. Check local .env structure
python scripts/validate_env.py .env

# 2. Check for missing variables
python scripts/validate_env.py .env --compare .env.example

# 3. Validate naming conventions
python scripts/validate_env.py .env --framework nextjs

# 4. Check for duplicates
python scripts/validate_env.py .env --check-duplicates
```

### Security Workflow
```bash
# 1. Scan for exposed secrets in code
python scripts/scan_exposed.py --scan-code

# 2. Check .gitignore coverage
python scripts/scan_exposed.py --check-gitignore

# 3. Validate secret formats
python scripts/scan_exposed.py --validate-formats .env
```

### Synchronization Workflow
```bash
# 1. Compare local vs platform
python scripts/sync_secrets.py --platform vercel --compare

# 2. Generate platform config
python scripts/sync_secrets.py --platform vercel --generate

# 3. Sync to platform (dry-run first)
python scripts/sync_secrets.py --platform vercel --sync --dry-run

# 4. Actual sync
python scripts/sync_secrets.py --platform vercel --sync
```

### Documentation Workflow
```bash
# Generate .env.example from .env
python scripts/validate_env.py .env --generate-example

# Generate setup documentation
python scripts/validate_env.py .env --generate-docs
```

## Navigation

For detailed workflows and patterns:
- **[Validation](references/validation.md)**: Complete validation workflows and checks
- **[Security](references/security.md)**: Secret scanning and security patterns
- **[Synchronization](references/synchronization.md)**: Platform sync and secret manager integration
- **[Frameworks](references/frameworks.md)**: Framework-specific patterns (Next.js, Express, Flask)
- **[Troubleshooting](references/troubleshooting.md)**: Common issues and solutions

## Framework-Specific Quick Reference

### Next.js
```bash
# Validate Next.js env structure
# - NEXT_PUBLIC_* for client-side vars
# - Check .env.local, .env.production precedence
python scripts/validate_env.py .env --framework nextjs

# Files to manage:
# - .env.local (local development, gitignored)
# - .env.production (production, usually from platform)
# - .env (shared defaults, committed)
# - .env.example (documentation, committed)
```

### Express/Node.js
```bash
# Validate Node.js env structure
python scripts/validate_env.py .env --framework nodejs

# Standard structure:
# - process.env.NODE_ENV
# - process.env.PORT
# - process.env.DATABASE_URL
```

### Python/Flask
```bash
# Validate Python env structure
python scripts/validate_env.py .env --framework python

# Standard structure:
# - FLASK_APP
# - FLASK_ENV
# - DATABASE_URL (SQLAlchemy format)
```

## Platform-Specific Quick Reference

### Vercel
```bash
# Generate vercel.json env config
python scripts/sync_secrets.py --platform vercel --generate

# Sync to Vercel project
python scripts/sync_secrets.py --platform vercel --sync

# Respects NEXT_PUBLIC_ prefix for client-side vars
```

### Railway
```bash
# Generate Railway config
python scripts/sync_secrets.py --platform railway --generate

# Sync to Railway project
python scripts/sync_secrets.py --platform railway --sync
```

### Heroku
```bash
# Generate Heroku config
python scripts/sync_secrets.py --platform heroku --generate

# Sync via Heroku CLI
python scripts/sync_secrets.py --platform heroku --sync
```

## Key Reminders

- **NEVER log actual secret values** - Always mask/redact in output
- **Validate before every deployment** - Catch issues locally
- **Use .env.example for documentation** - Keep it updated
- **Framework conventions matter** - Next.js NEXT_PUBLIC_, Django DJANGO_SETTINGS_MODULE
- **Platform-specific quirks exist** - Vercel auto-exposes NEXT_PUBLIC_*, Railway uses exact syntax
- **Secret managers are your friend** - 1Password, AWS Secrets Manager for team sync
- **.gitignore is critical** - NEVER commit .env files with secrets
- **Environment precedence can be tricky** - Know your framework's loading order

## Common Validation Checks

### Structure Validation
- [ ] No empty values (except explicitly allowed)
- [ ] No inline comments (some parsers don't support)
- [ ] Proper quoting for values with spaces
- [ ] No duplicate keys
- [ ] Valid key naming (UPPERCASE_WITH_UNDERSCORES)

### Security Validation
- [ ] No exposed secrets in code
- [ ] .env files in .gitignore
- [ ] No secrets in git history
- [ ] API keys match expected format
- [ ] No hardcoded URLs with credentials

### Framework Validation (Next.js)
- [ ] NEXT_PUBLIC_* for client-side vars only
- [ ] No secrets in NEXT_PUBLIC_* vars
- [ ] .env.local exists for local secrets
- [ ] .env.example documents all vars

### Platform Validation (Vercel)
- [ ] All required vars defined
- [ ] No conflicts between environments
- [ ] Correct variable names (Vercel conventions)
- [ ] Build-time vs runtime vars separated

## Integration with Other Skills

### Related Skills
- **docker-containerization** - Environment variables in containers
- **security-scanning** - Broader security checks including secrets
- **nextjs-local-dev** - Next.js specific development patterns
- **systematic-debugging** - Debug env-related issues

### Workflow Integration
```
1. Developer creates .env.local
2. env-manager validates structure
3. env-manager scans for security issues
4. Developer generates .env.example
5. Before deploy: env-manager compares local vs platform
6. env-manager generates platform config
7. Developer reviews and confirms sync
8. env-manager syncs to platform
9. Deployment proceeds with verified configuration
```

---

**Lines**: 197 (including frontmatter) ✓ <200
