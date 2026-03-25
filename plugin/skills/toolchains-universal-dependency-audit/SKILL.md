---
name: dependency-audit
description: Dependency audit and cleanup workflow for maintaining healthy project dependencies. Use for regular maintenance, security updates, and removing unused packages.
progressive_disclosure:
  entry_point:
    - summary
    - when_to_use
    - quick_audit_process
  sections:
    - audit_commands
    - priority_matrix
    - common_replacements
    - update_strategy
    - cleanup_workflow
    - security_scanning
---

# Dependency Audit Skill

## Summary
Systematic workflow for auditing, updating, and cleaning up project dependencies. Covers security vulnerability scanning, outdated package detection, unused dependency removal, and migration from deprecated libraries.

## When to Use
- Weekly/monthly dependency maintenance
- After security advisories (CVE announcements)
- Before major releases
- When bundle size increases unexpectedly
- During code reviews for dependency changes
- Onboarding to legacy projects

## Quick Audit Process

### 1. Check Outdated Packages
```bash
# npm
npm outdated

# pnpm
pnpm outdated

# yarn
yarn outdated

# pip (Python)
pip list --outdated

# poetry (Python)
poetry show --outdated
```

### 2. Security Vulnerability Scan
```bash
# npm
npm audit
npm audit fix          # Auto-fix where possible
npm audit fix --force  # Force major version updates (risky)

# pnpm
pnpm audit
pnpm audit --fix

# yarn
yarn audit
yarn audit --fix

# Python
pip-audit              # Requires: pip install pip-audit
safety check           # Requires: pip install safety
```

### 3. Find Unused Dependencies
```bash
# JavaScript/TypeScript
npx depcheck

# Output example:
# Unused dependencies
# * lodash
# * moment
# Unused devDependencies
# * @types/old-package

# Python
pip-autoremove --list  # Requires: pip install pip-autoremove
```

---

## Audit Commands

### JavaScript/TypeScript/Node.js

#### npm
```bash
# Check what's outdated
npm outdated

# Update within semver range (safe)
npm update

# Update specific package to latest
npm install package@latest

# Check security vulnerabilities
npm audit

# Auto-fix vulnerabilities
npm audit fix

# View dependency tree
npm list
npm list --depth=0  # Top-level only

# Why is this package installed?
npm ls package-name

# Check for duplicate packages
npm dedupe
```

#### pnpm
```bash
# Check outdated
pnpm outdated

# Update all dependencies
pnpm update

# Update specific package
pnpm update package@latest

# Security audit
pnpm audit

# Deduplicate
pnpm dedupe

# List all packages
pnpm list
```

#### yarn
```bash
# Check outdated
yarn outdated

# Upgrade interactive (recommended)
yarn upgrade-interactive

# Update all
yarn upgrade

# Security audit
yarn audit

# Why is this here?
yarn why package-name
```

### Python

#### pip
```bash
# List outdated
pip list --outdated

# Update specific package
pip install --upgrade package-name

# Security audit
pip-audit  # Install: pip install pip-audit

# Freeze current dependencies
pip freeze > requirements.txt

# Check dependencies of a package
pip show package-name
```

#### poetry
```bash
# Show outdated
poetry show --outdated

# Update all
poetry update

# Update specific package
poetry update package-name

# Security check
poetry audit  # poetry-audit-plugin required

# Show dependency tree
poetry show --tree
```

#### pipenv
```bash
# Check for security vulnerabilities
pipenv check

# Update all
pipenv update

# Update specific
pipenv update package-name

# Show dependency graph
pipenv graph
```

---

## Priority Matrix

| Priority | Type | Action | Timeline | Example |
|----------|------|--------|----------|---------|
| **P0** | Critical CVE (actively exploited) | Patch immediately | Same day | Auth bypass, RCE |
| **P1** | High CVE or major framework update | Plan migration | 1-2 weeks | Next.js, React major version |
| **P2** | Deprecated with active usage | Find replacement | 2-4 weeks | moment.js → date-fns |
| **P3** | Minor/patch updates | Batch update | Monthly | Non-breaking updates |
| **P4** | Unused dependencies | Remove | Next cleanup PR | Dead imports |

### Priority Decision Tree

```
Is there a CVE?
├─ Yes → Is it critical/high severity?
│  ├─ Yes → P0 (patch immediately)
│  └─ No → P1 (plan update)
└─ No → Is package deprecated?
   ├─ Yes → Is it actively used?
   │  ├─ Yes → P2 (find replacement)
   │  └─ No → P4 (remove)
   └─ No → Is it outdated?
      ├─ Major version → P1 (plan migration)
      ├─ Minor/patch → P3 (batch update)
      └─ Unused → P4 (remove)
```

---

## Common Replacements

### Date/Time Libraries

#### JavaScript/TypeScript
```javascript
// ❌ moment.js (deprecated, 288KB minified)
import moment from 'moment';
const formatted = moment().format('YYYY-MM-DD');
const diff = moment(date1).diff(moment(date2), 'days');

// ✅ date-fns (tree-shakeable, 2-5KB per function)
import { format, differenceInDays } from 'date-fns';
const formatted = format(new Date(), 'yyyy-MM-dd');
const diff = differenceInDays(date1, date2);

// ✅ Native Intl (zero bundle cost)
const formatted = new Intl.DateTimeFormat('en-US').format(new Date());
const relative = new Intl.RelativeTimeFormat('en').format(-1, 'day'); // "1 day ago"
```

#### Python
```python
# ❌ arrow (overhead for simple tasks)
import arrow
now = arrow.now().format('YYYY-MM-DD')

# ✅ Native datetime
from datetime import datetime
now = datetime.now().strftime('%Y-%m-%d')

# ✅ pendulum (for complex timezone handling)
import pendulum
now = pendulum.now('America/New_York')
```

### Utility Libraries

#### JavaScript/TypeScript
```javascript
// ❌ Full lodash import (70KB)
import _ from 'lodash';
const value = _.get(obj, 'path.to.value');
const unique = _.uniq(array);

// ✅ Specific imports (5-10KB)
import get from 'lodash/get';
import uniq from 'lodash/uniq';

// ✅ Native alternatives (0KB)
const value = obj?.path?.to?.value;           // Optional chaining
const unique = [...new Set(array)];           // Set
const keys = Object.keys(obj);                // Object.keys
const flat = array.flat();                    // Array.flat()
const grouped = Object.groupBy(arr, fn);      // Object.groupBy
```

### HTTP Clients

#### JavaScript/TypeScript
```javascript
// ❌ axios (11KB) - often unnecessary
import axios from 'axios';
const { data } = await axios.get('/api/users');

// ✅ Native fetch (0KB) - built-in
const response = await fetch('/api/users');
const data = await response.json();

// ✅ ky (2KB) - if you need retries/timeout
import ky from 'ky';
const data = await ky.get('/api/users').json();
```

#### Python
```python
# ❌ requests (large for serverless)
import requests
response = requests.get('https://api.example.com')

# ✅ httpx (async support, same API)
import httpx
async with httpx.AsyncClient() as client:
    response = await client.get('https://api.example.com')

# ✅ urllib (native, for simple cases)
from urllib.request import urlopen
response = urlopen('https://api.example.com')
```

### Testing Libraries

#### JavaScript/TypeScript
```javascript
// Consider consolidating test runners

// If using Jest + Vitest + Playwright separately:
// ✅ Vitest can replace Jest in most projects (faster, native ESM)
// ✅ Keep Playwright for E2E, use Vitest for unit/integration
```

### Validation Libraries

#### JavaScript/TypeScript
```javascript
// ❌ Multiple validation libraries
import * as yup from 'yup';
import Joi from 'joi';
import { z } from 'zod';

// ✅ Pick one (Zod recommended for TypeScript)
import { z } from 'zod';
const schema = z.object({
  email: z.string().email(),
  age: z.number().min(0)
});
```

---

## Update Strategy

### Batch Related Updates
```bash
# Update all ESLint-related packages together
pnpm update eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin

# Update all testing packages together
pnpm update vitest @vitest/ui @vitest/coverage-v8

# Update all Next.js packages together
pnpm update next react react-dom @types/react @types/react-dom
```

### Test After Updates

#### Comprehensive Testing Checklist
```bash
# 1. Type check
pnpm tsc --noEmit

# 2. Lint
pnpm lint

# 3. Unit tests
pnpm test

# 4. Build verification
pnpm build

# 5. Dev server (smoke test)
pnpm dev
# Open browser, test key features

# 6. E2E tests (if available)
pnpm test:e2e
```

### Incremental Update Strategy

#### For Major Version Updates
```bash
# 1. Create branch
git checkout -b chore/update-nextjs-15

# 2. Update package.json
# Change "next": "^14.0.0" → "^15.0.0"

# 3. Install
pnpm install

# 4. Read migration guide
# Visit: nextjs.org/docs/upgrading

# 5. Address breaking changes
# Follow migration guide step-by-step

# 6. Test thoroughly
pnpm test && pnpm build

# 7. Commit and PR
git add .
git commit -m "chore: upgrade Next.js to v15"
```

---

## Cleanup Workflow

### Step 1: Identify Unused Dependencies
```bash
npx depcheck
```

**Example Output:**
```
Unused dependencies
* lodash
* moment
* old-library

Unused devDependencies
* @types/old-package
* unused-test-lib
```

### Step 2: Verify Not Used
```bash
# Search codebase for imports
rg "from 'lodash'" --type ts
rg "import.*lodash" --type ts
rg "require\('lodash'\)" --type js

# If no results → safe to remove
```

### Step 3: Remove Package
```bash
pnpm remove lodash
```

### Step 4: Update Lock File
```bash
# npm
rm package-lock.json
npm install

# pnpm
rm pnpm-lock.yaml
pnpm install

# yarn
rm yarn.lock
yarn install
```

### Step 5: Test
```bash
pnpm test
pnpm build
```

### Cleanup PR Template
```markdown
## Dependency Cleanup

### Security Updates (P0/P1)
- [ ] `next`: 14.0.4 → 14.2.3 (CVE-2024-XXXX)
- [ ] `jose`: 4.15.4 → 4.15.5 (CVE-2024-YYYY)

### Removed (Unused)
- [ ] `lodash` - replaced with native JS methods
- [ ] `moment` - replaced with date-fns
- [ ] `@types/old-package` - package no longer used

### Updated (Maintenance)
- [ ] `eslint`: 8.57.0 → 9.0.0
- [ ] `typescript`: 5.3.3 → 5.4.2

### Migration Notes
**lodash → Native**:
- `_.get()` → optional chaining `obj?.prop?.value`
- `_.uniq()` → `[...new Set(array)]`

**moment → date-fns**:
- `moment().format('YYYY-MM-DD')` → `format(new Date(), 'yyyy-MM-dd')`

### Testing
- [ ] All tests pass (`pnpm test`)
- [ ] Build succeeds (`pnpm build`)
- [ ] No runtime errors in dev (`pnpm dev`)
- [ ] E2E tests pass (if applicable)

### Bundle Size Impact
- Before: 2.4 MB
- After: 1.8 MB
- **Savings: 600 KB (25% reduction)**
```

---

## Security Scanning

### Automated Security Checks

#### GitHub Actions
```yaml
# .github/workflows/security.yml
name: Security Audit

on:
  schedule:
    - cron: '0 0 * * 1'  # Weekly on Monday
  pull_request:
  push:
    branches: [main]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm ci

      - name: Run security audit
        run: npm audit --audit-level=high

      - name: Check for outdated packages
        run: npm outdated || true

      - name: Dependency review
        uses: actions/dependency-review-action@v4
        if: github.event_name == 'pull_request'
```

#### Snyk Integration
```yaml
# .github/workflows/snyk.yml
name: Snyk Security

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Snyk to check for vulnerabilities
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
```

### Manual Security Commands
```bash
# npm security audit
npm audit

# Show only high/critical
npm audit --audit-level=high

# Get JSON report
npm audit --json > audit-report.json

# Snyk (requires: npm install -g snyk)
snyk test                    # Test for vulnerabilities
snyk monitor                 # Continuous monitoring
snyk wizard                  # Interactive fixing

# Socket.dev (supply chain security)
npx socket-npm audit
```

### CVE Response Process

1. **Notification**: Receive security advisory (GitHub, npm, Snyk)

2. **Assess Impact**:
   ```bash
   # Find where vulnerable package is used
   npm ls vulnerable-package

   # Check if we use vulnerable functionality
   rg "vulnerableFunction" --type ts
   ```

3. **Patch**:
   ```bash
   # Update to patched version
   npm install vulnerable-package@4.15.5

   # Or update dependency that depends on it
   npm update parent-package
   ```

4. **Verify Fix**:
   ```bash
   npm audit
   # Should show 0 vulnerabilities
   ```

5. **Test & Deploy**:
   ```bash
   pnpm test && pnpm build
   git commit -m "fix: patch CVE-2024-XXXX in vulnerable-package"
   ```

---

## Summary

### Monthly Maintenance Checklist
```markdown
## Dependency Maintenance - [YYYY-MM]

### Security
- [ ] Run `npm audit` and address high/critical issues
- [ ] Review GitHub security advisories
- [ ] Check Snyk dashboard (if integrated)

### Updates
- [ ] Check `npm outdated` for major updates
- [ ] Update patch versions: `npm update`
- [ ] Plan migration for deprecated packages

### Cleanup
- [ ] Run `npx depcheck` to find unused deps
- [ ] Remove packages with zero imports
- [ ] Deduplicate: `npm dedupe`

### Testing
- [ ] Run full test suite
- [ ] Check build succeeds
- [ ] Verify dev server works
- [ ] Test in production-like environment

### Documentation
- [ ] Update CHANGELOG.md
- [ ] Document breaking changes
- [ ] Update .env.example if needed
```

### Best Practices
- **Automate**: Set up GitHub Actions for weekly audits
- **Batch Updates**: Group related dependency updates
- **Test Thoroughly**: Never skip tests after updates
- **Document**: Keep CHANGELOG.md updated
- **Measure Impact**: Track bundle size changes
- **Stay Informed**: Subscribe to security advisories
- **Use Lock Files**: Commit package-lock.json/pnpm-lock.yaml
- **Gradual Migration**: Don't update everything at once
