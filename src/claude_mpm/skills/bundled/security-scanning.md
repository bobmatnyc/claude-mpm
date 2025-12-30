---
skill_id: security-scanning
skill_version: 0.1.0
description: Identify and fix common security vulnerabilities in code, eliminating redundant security guidance per agent.
updated_at: 2025-10-30T17:00:00Z
tags: [security, vulnerability, scanning, code-analysis]
---

# Security Scanning

Identify and fix common security vulnerabilities in code. Eliminates ~150-200 lines of redundant security guidance per agent.

## Core Security Principles

1. **Never trust user input** - Validate and sanitize everything
2. **Least privilege** - Grant minimum necessary permissions
3. **Defense in depth** - Multiple layers of security
4. **Fail securely** - Errors shouldn't expose sensitive data
5. **Keep secrets secret** - Never commit credentials

## Common Vulnerabilities (OWASP Top 10)

### 1. Injection Attacks

**SQL Injection:**
```python
# ❌ Vulnerable
query = f"SELECT * FROM users WHERE email = '{user_email}'"
# Attacker input: ' OR '1'='1

# ✅ Safe: Use parameterized queries
query = "SELECT * FROM users WHERE email = %s"
cursor.execute(query, (user_email,))
```

**Command Injection:**
```python
# ❌ Vulnerable
os.system(f"ping {user_input}")

# ✅ Safe: Use subprocess with list
subprocess.run(["ping", "-c", "1", user_input])
```

### 2. Authentication/Authorization

**Weak Password Storage:**
```python
# ❌ Vulnerable
password = user_input  # Plain text!

# ✅ Safe: Use strong hashing
from werkzeug.security import generate_password_hash
password_hash = generate_password_hash(user_input)
```

**Missing Authorization Checks:**
```python
# ❌ Vulnerable
def delete_user(user_id):
    User.delete(user_id)  # Anyone can delete!

# ✅ Safe: Check permissions
def delete_user(user_id, current_user):
    if not current_user.is_admin:
        raise PermissionError()
    User.delete(user_id)
```

### 3. Sensitive Data Exposure

```python
# ❌ Vulnerable: Logging sensitive data
logger.info(f"User logged in: {email}, password: {password}")

# ✅ Safe: Never log secrets
logger.info(f"User logged in: {email}")

# ❌ Vulnerable: Committing secrets
API_KEY = "sk-1234567890abcdef"  # In code!  # pragma: allowlist secret

# ✅ Safe: Use environment variables
API_KEY = os.getenv("API_KEY")

# ❌ CRITICAL: MCP config files with API keys
# NEVER commit these files:
# - .mcp-vector-search/config.json (OpenRouter API keys)
# - .mcp/config.json (MCP server credentials)
# - openrouter.json, anthropic-config.json
# - credentials.json, secrets.json, api-keys.json

# ✅ Safe: Verify .gitignore before committing
# Check file is ignored: git check-ignore <file_path>
# Check file not tracked: git ls-files <file_path>
```

**MCP Secret File Patterns (High Risk):**
```bash
# Files that commonly contain API keys:
.mcp-vector-search/config.json     # OpenRouter, OpenAI keys
.mcp/config.json                    # MCP server credentials
**/mcp-config.json
openrouter.json
anthropic-config.json
openai-config.json
credentials.json
secrets.json
api-keys.json

# ALWAYS add to .gitignore:
echo ".mcp-vector-search/" >> .gitignore
echo "credentials.json" >> .gitignore
echo "secrets.json" >> .gitignore
```

### 4. XML External Entities (XXE)

```python
# ❌ Vulnerable
import xml.etree.ElementTree as ET
tree = ET.parse(user_supplied_xml)  # Can read local files!

# ✅ Safe: Disable external entities
import defusedxml.ElementTree as ET
tree = ET.parse(user_supplied_xml)
```

### 5. Broken Access Control

```javascript
// ❌ Vulnerable: Client-side only check
if (user.isAdmin) {
  showAdminPanel();
}

// ✅ Safe: Server-side verification
fetch('/admin/data', {
  headers: { 'Authorization': `Bearer ${token}` }
}).then(response => {
  // Server validates token and permissions
});
```

### 6. Security Misconfiguration

```python
# ❌ Vulnerable: Debug mode in production
DEBUG = True  # Exposes stack traces!

# ✅ Safe: Disable debug in production
DEBUG = os.getenv("ENV") != "production"

# ❌ Vulnerable: Default credentials
DB_PASSWORD = "admin123"  # pragma: allowlist secret

# ✅ Safe: Strong, unique credentials
DB_PASSWORD = os.getenv("DB_PASSWORD")
```

### 7. Cross-Site Scripting (XSS)

```javascript
// ❌ Vulnerable: Unescaped user content
element.innerHTML = userInput;  // XSS attack!

// ✅ Safe: Escape or use textContent
element.textContent = userInput;

// Or use framework's safe rendering
<div>{{ userInput }}</div>  {/* React/Vue auto-escape */}
```

### 8. Insecure Deserialization

```python
# ❌ Vulnerable: Deserializing untrusted data
import pickle
data = pickle.loads(user_data)  # Can execute arbitrary code!

# ✅ Safe: Use JSON or validated formats
import json
data = json.loads(user_data)
validate_schema(data)
```

### 9. Using Components with Known Vulnerabilities

```bash
# Check for vulnerable dependencies
npm audit
pip check
cargo audit

# Update regularly
npm update
pip install --upgrade
```

### 10. Insufficient Logging & Monitoring

```python
# ✅ Log security events
logger.warning(f"Failed login attempt for user: {email} from IP: {ip}")
logger.error(f"Unauthorized access attempt to {resource} by {user}")

# Monitor for patterns
if failed_login_count > 5:
    alert_security_team()
```

## Secret Detection and Prevention

### Pre-commit Hooks with detect-secrets
```bash
# Install detect-secrets
pip install detect-secrets

# Create baseline of existing secrets
detect-secrets scan > .secrets.baseline

# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Add to .pre-commit-config.yaml:
# - repo: https://github.com/Yelp/detect-secrets
#   rev: v1.5.0
#   hooks:
#     - id: detect-secrets
#       args: ['--baseline', '.secrets.baseline']

# Scan for new secrets
detect-secrets scan --baseline .secrets.baseline

# Audit baseline (mark false positives)
detect-secrets audit .secrets.baseline
```

### Manual Secret Scanning
```bash
# Check if file is ignored by git
git check-ignore .mcp-vector-search/config.json
# Exit code 0 = ignored (safe)
# Exit code 1 = NOT ignored (DANGER!)

# Check if file is tracked by git
git ls-files .mcp-vector-search/config.json
# Output present = tracked (CRITICAL - remove immediately!)
# No output = not tracked (safe if also in .gitignore)

# Search git history for committed secrets
git log --all --full-history -- .mcp-vector-search/config.json

# Remove file from git history (if accidentally committed)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .mcp-vector-search/config.json' \
  --prune-empty --tag-name-filter cat -- --all
```

### Incident Response: Exposed API Key
If you've committed an API key to git:

1. **IMMEDIATELY rotate the exposed credential**
   - OpenRouter: https://openrouter.ai/settings/keys
   - Anthropic: https://console.anthropic.com/settings/keys
   - OpenAI: https://platform.openai.com/api-keys

2. **Remove from git history**
   ```bash
   # Using git-filter-repo (recommended)
   git filter-repo --path .mcp-vector-search/config.json --invert-paths

   # Force push to remote (WARNING: destructive)
   git push origin --force --all
   git push origin --force --tags
   ```

3. **Add to .gitignore** (if not already there)
   ```bash
   echo ".mcp-vector-search/" >> .gitignore
   git add .gitignore
   git commit -m "chore: add MCP config to gitignore"
   ```

4. **Verify cleanup**
   ```bash
   git log --all --full-history -- .mcp-vector-search/config.json
   # Should show no results
   ```

5. **Notify stakeholders** if the key had production access

## Security Scanning Tools

### Python
```bash
# Bandit: Find common security issues
bandit -r src/

# Safety: Check for vulnerable dependencies
safety check

# Semgrep: Pattern-based scanning
semgrep --config=auto .
```

### JavaScript
```bash
# npm audit: Check dependencies
npm audit
npm audit fix

# ESLint security plugin
npm install --save-dev eslint-plugin-security
```

### Go
```bash
# gosec: Security scanner
gosec ./...

# govulncheck: Known vulnerabilities
govulncheck ./...
```

### Rust
```bash
# cargo-audit: Check dependencies
cargo audit

# cargo-deny: Policy enforcement
cargo deny check
```

## Input Validation

```python
# Always validate user input
from pydantic import BaseModel, EmailStr, conint

class UserInput(BaseModel):
    email: EmailStr  # Validates email format
    age: conint(ge=0, le=150)  # Constrained integer
    username: str = Field(regex=r'^[a-zA-Z0-9_]+$')  # Alphanumeric only

# Use the validator
try:
    validated = UserInput(**user_data)
except ValidationError as e:
    return {"error": "Invalid input"}
```

## Secure API Design

```python
# Rate limiting
from flask_limiter import Limiter

limiter = Limiter(app, key_func=get_remote_address)

@app.route("/api/login")
@limiter.limit("5 per minute")  # Prevent brute force
def login():
    pass

# CORS configuration
from flask_cors import CORS

CORS(app, origins=["https://trusted-domain.com"])  # Don't use *

# HTTPS only
if not request.is_secure and app.env == "production":
    return redirect(request.url.replace("http://", "https://"))
```

## Cryptography Best Practices

```python
# ❌ Don't roll your own crypto
def my_encryption(data, key):
    return xor(data, key)  # Insecure!

# ✅ Use established libraries
from cryptography.fernet import Fernet

key = Fernet.generate_key()
cipher = Fernet(key)
encrypted = cipher.encrypt(data.encode())
decrypted = cipher.decrypt(encrypted).decode()

# ✅ Use strong random numbers
import secrets
token = secrets.token_urlsafe(32)  # Not random.randint()!
```

## Security Checklist

```
Authentication & Authorization:
□ Passwords are hashed (bcrypt, argon2)
□ MFA is supported
□ Session tokens are secure and expire
□ Authorization checks on all sensitive operations
□ Role-based access control implemented

Input Validation:
□ All user input is validated
□ SQL uses parameterized queries
□ XSS protection (output escaping)
□ CSRF tokens on state-changing operations
□ File uploads are validated and isolated

Data Protection:
□ Sensitive data is encrypted at rest
□ TLS/HTTPS for data in transit
□ Secrets are in environment variables
□ No secrets in version control
□ PII handling complies with regulations

Dependencies:
□ All dependencies are up to date
□ Security scanning in CI/CD
□ No known vulnerabilities
□ Minimal dependency footprint

Logging & Monitoring:
□ Security events are logged
□ Sensitive data not in logs
□ Anomaly detection in place
□ Incident response plan exists
```

## Remember

- **Security is ongoing** - Not a one-time fix
- **Assume breach** - Plan for when (not if) attacks happen
- **Update regularly** - Vulnerabilities are discovered constantly
- **Scan automatically** - Integrate security checks in CI/CD
- **Least surprise** - Secure defaults, explicit insecure options
