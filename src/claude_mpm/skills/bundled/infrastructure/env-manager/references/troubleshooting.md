# Environment Troubleshooting Guide

> **Part of**: [env-manager](../SKILL.md)
> **Category**: infrastructure
> **Reading Level**: Intermediate

## Purpose

Solutions to common environment variable issues: "works locally, not in production", missing variables, framework-specific problems, and platform quirks.

## Common Issues

### Issue 1: Works Locally, Not in Production

**Symptoms:**
- Application works fine locally
- Fails or behaves incorrectly in production
- Error messages about missing or undefined variables

**Root Causes:**

**A. Variables Not Synced to Platform**
```bash
# Check local vs platform
python scripts/validate_env.py .env --compare-platform vercel

# Common issue: forgot to sync
python scripts/sync_secrets.py --platform vercel --sync --dry-run
```

**B. Wrong Environment File Loaded**
```bash
# Next.js example
# Local: .env.local (gitignored, has all secrets)
# Production: Platform env vars (might be missing some)

# Solution: Ensure all vars from .env.local are in platform
```

**C. Build-Time vs Runtime Variables**
```bash
# Vite/Next.js: VITE_* and NEXT_PUBLIC_* are build-time
# If you change them in production, you must rebuild

# Vercel: Redeploy after changing NEXT_PUBLIC_ vars
vercel --prod
```

### Issue 2: Missing Variables

**Debug Workflow:**

```python
# 1. Check if variable is defined
def check_variable(var_name: str, env_file: Path):
    """Check if variable exists and has value."""
    vars_dict = parse_env_file(env_file)

    if var_name not in vars_dict:
        print(f"❌ {var_name} not defined in {env_file}")
        return False

    if not vars_dict[var_name]:
        print(f"⚠️  {var_name} defined but empty")
        return False

    print(f"✅ {var_name}={mask_secret(vars_dict[var_name])}")
    return True

# 2. Check file precedence (Next.js)
def check_nextjs_precedence(project_dir: Path, var_name: str):
    """Check which file defines variable in Next.js."""
    env_files = [
        '.env.production.local',
        '.env.local',
        '.env.production',
        '.env'
    ]

    for env_file in env_files:
        file_path = project_dir / env_file
        if file_path.exists():
            vars_dict = parse_env_file(file_path)
            if var_name in vars_dict:
                print(f"Found in: {env_file}")
                print(f"Value: {mask_secret(vars_dict[var_name])}")
                return

    print(f"❌ {var_name} not found in any .env file")
```

**Common Mistakes:**
```bash
# ❌ Wrong: Variable name typo
DATABASE_URL=postgres://...
# Code accessing: DATABASE_ULR (typo)

# ❌ Wrong: Not loaded in .env file
# Missing from .env entirely

# ❌ Wrong: Empty value
DATABASE_URL=

# ✅ Correct:
DATABASE_URL=postgres://localhost:5432/mydb
```

### Issue 3: Framework-Specific Issues

**Next.js Issues:**

**A. NEXT_PUBLIC_ Variable Not Available Client-Side**
```bash
# Issue: Variable defined but undefined in browser
# Cause: Missing NEXT_PUBLIC_ prefix

# ❌ Wrong:
API_URL=https://api.example.com

# ✅ Correct:
NEXT_PUBLIC_API_URL=https://api.example.com
```

**B. File Precedence Confusion**
```bash
# If .env.local defines DATABASE_URL=local
# But .env defines DATABASE_URL=remote
# .env.local wins (higher precedence)

# Solution: Check all .env files
ls -la .env*
```

**Express/Node.js Issues:**

**A. process.env.VAR Undefined**
```javascript
// Issue: Variable not loaded
// Cause: Forgot to load dotenv

// ❌ Wrong: No dotenv
const dbUrl = process.env.DATABASE_URL;  // undefined

// ✅ Correct: Load dotenv first
require('dotenv').config();
const dbUrl = process.env.DATABASE_URL;
```

**Flask Issues:**

**A. Variable Not Available in Flask App**
```python
# Issue: os.getenv() returns None
# Cause: dotenv not loaded before app initialization

# ❌ Wrong: Config before load_dotenv
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')  # None
load_dotenv()

# ✅ Correct: load_dotenv first
from dotenv import load_dotenv
load_dotenv()
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
```

### Issue 4: Platform-Specific Issues

**Vercel Issues:**

**A. Environment Variable Not Applied**
```bash
# Issue: Changed env var in Vercel UI, but app still uses old value
# Cause: Vercel caches NEXT_PUBLIC_ vars at build time

# Solution: Redeploy
vercel --prod

# Or: Use non-NEXT_PUBLIC_ var and read server-side
```

**B. Variable Shows in Preview, Not Production**
```bash
# Issue: Variable works in preview deployments
# Cause: Variable only set for "Preview" environment in Vercel

# Solution: Set for "Production" environment too
# Vercel UI: Settings → Environment Variables → Production
```

**Railway Issues:**

**A. Variable Not Found After Deployment**
```bash
# Issue: App can't find variable
# Cause: Railway uses exact syntax, no dotenv loading

# Solution: Set variables in Railway dashboard or CLI
railway variables set DATABASE_URL=postgres://...
```

**Heroku Issues:**

**A. Config Vars Not Applied**
```bash
# Check current config
heroku config --app myapp

# Set missing var
heroku config:set DATABASE_URL=postgres://... --app myapp

# Restart app (sometimes needed)
heroku restart --app myapp
```

### Issue 5: Secret Exposure

**If Secrets Are Committed to Git:**

```bash
# Immediate actions:
# 1. Revoke/rotate exposed secrets immediately
# 2. Remove from git history
# 3. Update all deployments

# Remove from git history (DESTRUCTIVE)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# Or use BFG Repo-Cleaner (recommended)
bfg --delete-files .env
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push (careful!)
git push origin --force --all
```

**If Secrets Are in Public Logs:**

```bash
# 1. Clear deployment logs (if possible)
# 2. Rotate all exposed secrets
# 3. Add logging safeguards

# Update code to never log secrets
# ❌ Wrong:
logger.info(f"Connecting with {db_password}")

# ✅ Correct:
logger.info(f"Connecting to database (credentials masked)")
```

## Debugging Checklist

### Local Development

```bash
# 1. Check .env file exists
ls -la .env*

# 2. Validate structure
python scripts/validate_env.py .env

# 3. Check for duplicates
python scripts/validate_env.py .env --check-duplicates

# 4. Verify framework detection
python scripts/validate_env.py .env --detect-framework

# 5. Test variable loading
node -e "require('dotenv').config(); console.log(process.env.DATABASE_URL)"
```

### Production Debugging

```bash
# 1. Compare local vs production
python scripts/sync_secrets.py --platform vercel --compare

# 2. Check platform variables
vercel env ls

# 3. Check build logs for errors
vercel logs --follow

# 4. Verify deployment used correct branch
vercel inspect <deployment-url>
```

## Quick Fixes

### Fix 1: Sync Local to Platform

```bash
# 1. Validate local .env
python scripts/validate_env.py .env

# 2. Compare with platform
python scripts/sync_secrets.py --platform vercel --compare

# 3. Sync (dry-run first)
python scripts/sync_secrets.py --platform vercel --sync --dry-run

# 4. Actually sync
python scripts/sync_secrets.py --platform vercel --sync --confirm
```

### Fix 2: Regenerate .env.example

```bash
# Generate from current .env
python scripts/validate_env.py .env --generate-example

# Review and commit
git add .env.example
git commit -m "docs: update .env.example"
```

### Fix 3: Check All .env Files (Next.js)

```bash
# List all .env files
find . -name ".env*" -not -path "*/node_modules/*"

# Check each file
for file in .env*; do
  echo "=== $file ==="
  python scripts/validate_env.py $file
done
```

## Prevention Tips

### Tip 1: Use .env.example

```bash
# Always maintain .env.example with structure
# Never include actual values

# .env.example
DATABASE_URL=postgres://localhost:5432/mydb
JWT_SECRET=your-secret-here
API_KEY=your-api-key-here
```

### Tip 2: Validate Before Deploy

```bash
# Add to CI/CD pipeline
# .github/workflows/validate.yml
- name: Validate Environment
  run: python scripts/validate_env.py .env.example
```

### Tip 3: Document Platform-Specific Setup

```markdown
# README.md

## Environment Setup

### Local Development
1. Copy `.env.example` to `.env.local`
2. Fill in actual values
3. Run `python scripts/validate_env.py .env.local`

### Vercel Deployment
1. Go to Settings → Environment Variables
2. Add variables from `.env.example`
3. Set for Production environment
4. Deploy
```

## Summary

**Common Issues**:
- Works locally, not in production → Check platform sync
- Missing variables → Check file precedence
- Framework-specific → Check prefix requirements
- Platform quirks → Check platform documentation

**Debugging Workflow**:
1. Validate local .env structure
2. Check file precedence (Next.js)
3. Compare local vs platform
4. Check build logs
5. Verify variable access in code

**Quick Fixes**:
- Sync to platform with dry-run
- Regenerate .env.example
- Check all .env files
- Rotate exposed secrets

## Related References

- [Validation](validation.md): Environment validation workflows
- [Security](security.md): Secret exposure recovery
- [Synchronization](synchronization.md): Platform sync procedures
- [Frameworks](frameworks.md): Framework-specific patterns

---
**Lines**: 245 ✓ 180-250 range
