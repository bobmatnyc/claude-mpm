# Secret Detection with detect-secrets

This project uses [detect-secrets](https://github.com/Yelp/detect-secrets) to prevent credentials and API keys from being committed to the repository.

## Overview

The pre-commit hook automatically scans staged files for potential secrets before allowing commits. This provides an additional layer of security beyond gitignore patterns.

## How It Works

1. **Pre-commit Hook**: Every commit triggers a scan of staged files
2. **Baseline File**: `.secrets.baseline` stores known/allowed secrets
3. **27 Detectors**: Scans for AWS keys, API tokens, private keys, and more
4. **13 Filters**: Smart filtering to reduce false positives

## Secret Detectors Enabled

The following types of secrets are detected:

- **Cloud Providers**: AWS keys, Azure keys, IBM Cloud credentials
- **Version Control**: GitHub tokens, GitLab tokens
- **APIs**: OpenAI keys, Stripe keys, Twilio keys, SendGrid keys
- **Communication**: Slack tokens, Discord bot tokens, Telegram tokens
- **Package Managers**: npm tokens, PyPI tokens
- **Authentication**: Basic auth credentials, JWT tokens
- **Cryptographic**: Private keys (PEM format), high-entropy strings
- **General**: Password keywords, secret keywords

## Developer Workflow

### Normal Commits

If your files are clean, commits work normally:

```bash
git add myfile.py
git commit -m "Add new feature"
# ✅ No secrets detected - commit succeeds
```

### When Secrets Are Detected

If a secret is detected, the commit will be blocked:

```bash
git add config.py
git commit -m "Update config"
# ⛔ SECRETS DETECTED! Commit blocked.
# ERROR: Potential secrets about to be committed to git repo!
# Secret Type: Secret Keyword
# Location: config.py:12
```

**What to do:**

1. **Remove the secret** from your code
2. **Move to environment variables** or a secure secret manager
3. **Update .env.example** with placeholder values
4. **Try the commit again**

### Handling False Positives

Sometimes detect-secrets flags legitimate code:

```python
# False positive - this is not a real secret
EXAMPLE_API_KEY = "sk-example-key-for-documentation"  # pragma: allowlist secret
```

**Option 1: Inline Allowlist**
Add a comment to the line:
```python
API_KEY = "example-key"  # pragma: allowlist secret
```

**Option 2: Update Baseline**
If you have multiple false positives:
```bash
# Rescan and update baseline
detect-secrets scan --exclude-files '\.git/.*|venv/.*|\.venv/.*|node_modules/.*|__pycache__/.*|\.pyc$|\.egg-info/.*' > .secrets.baseline

# Commit the updated baseline
git add .secrets.baseline
git commit -m "docs: update secrets baseline for new examples"
```

**Option 3: Audit Baseline**
Interactively review detected secrets:
```bash
detect-secrets audit .secrets.baseline
```

## Files Excluded from Scanning

The following directories are automatically excluded:

- `.git/` - Git metadata
- `venv/`, `.venv/`, `env/` - Python virtual environments
- `node_modules/` - Node.js dependencies
- `__pycache__/` - Python bytecode
- `*.egg-info/` - Python package metadata

## Pre-commit Hook Details

The hook is located at `.git/hooks/pre-commit` and performs:

1. **Structure Linting**: Validates file placement per project conventions
2. **Secret Detection**: Scans staged files for credentials

Both checks must pass for the commit to succeed.

## Baseline File (.secrets.baseline)

The baseline file:

- **IS tracked in git** - it's configuration, not secrets
- **Contains hashed values** - actual secret values are not stored
- **Should be updated** when legitimate changes trigger false positives
- **Should be reviewed** periodically to ensure accuracy

## Example: Migrating Hardcoded Secrets

**Before (hardcoded - will be blocked):**
```python
# config.py
API_KEY = "sk-1234567890abcdef"  # ⛔ BLOCKED
DATABASE_URL = "postgresql://user:password@host/db"  # ⛔ BLOCKED
```

**After (environment variables - allowed):**
```python
# config.py
import os

API_KEY = os.getenv("API_KEY")  # ✅ ALLOWED
DATABASE_URL = os.getenv("DATABASE_URL")  # ✅ ALLOWED

# .env.example (for documentation)
# API_KEY=your-api-key-here
# DATABASE_URL=postgresql://user:pass@localhost/dbname
```

## Testing Secret Detection

To verify the hook is working:

```bash
# Create a test file with a fake secret
echo 'API_KEY = "sk-test-secret-key-12345"' > test_secret.py
git add test_secret.py
git commit -m "Test"
# Should be BLOCKED

# Remove the test file
git reset HEAD test_secret.py
rm test_secret.py
```

## Troubleshooting

### Hook Not Running

Check if the hook is executable:
```bash
ls -la .git/hooks/pre-commit
# Should show: -rwxr-xr-x
```

Make it executable if needed:
```bash
chmod +x .git/hooks/pre-commit
```

### Too Many False Positives

Adjust the entropy limits in `.secrets.baseline`:
```json
{
  "name": "Base64HighEntropyString",
  "limit": 4.5  // Increase to reduce sensitivity
}
```

Then rescan:
```bash
detect-secrets scan --exclude-files '\.git/.*|venv/.*|\.venv/.*|node_modules/.*|__pycache__/.*|\.pyc$|\.egg-info/.*' > .secrets.baseline
```

### Manual Scan

To scan without committing:
```bash
# Scan specific file
detect-secrets-hook --baseline .secrets.baseline myfile.py

# Scan all Python files
detect-secrets scan --baseline .secrets.baseline src/
```

## Security Best Practices

1. **Never commit real secrets** - use environment variables
2. **Use .env.example** for documentation with placeholders
3. **Rotate exposed secrets** immediately if accidentally committed
4. **Review baseline periodically** to ensure it's current
5. **Update baseline** when adding new example/test data
6. **Use secret managers** for production (AWS Secrets Manager, HashiCorp Vault, etc.)

## Related Documentation

- [Security Guide](/docs/reference/SECURITY.md)
- [Development Setup](/docs/developer/03-development/setup.md)
- [Project Structure](/docs/STRUCTURE.md)

## References

- [detect-secrets GitHub](https://github.com/Yelp/detect-secrets)
- [detect-secrets Documentation](https://detect-secrets.readthedocs.io/)
